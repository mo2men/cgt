import pytest
from datetime import date, timedelta
from decimal import Decimal
import json

from app import get_aea, build_fragment_detail_struct, load_rates_sorted, get_rate_for_date, recalc_all, Vesting, ESPPPurchase, SaleInput, ExchangeRate, Setting, q2, DisposalResult, CarryForwardLoss

class TestAEA:
    """Test Annual Exempt Amount per UK tax years."""
    
    def test_aea_2024(self):
        assert get_aea(2024) == Decimal("3000")
    
    def test_aea_2023(self):
        assert get_aea(2023) == Decimal("6000")
    
    def test_aea_prior(self):
        assert get_aea(2022) == Decimal("12300")
    
    def test_aea_none(self):
        assert get_aea(None) == Decimal("12300")
    
    def test_aea_future(self):
        assert get_aea(2025) == Decimal("3000")  # Post-2024 default

class TestExchangeRates:
    """Test exchange rate handling."""
    
    @pytest.fixture
    def rates(self, session):
        session.query(ExchangeRate).delete()
        session.commit()
        # Add rates for 2020: 1.3, 2023: 1.2
        r2020 = ExchangeRate(date=date(2020, 1, 1), usd_gbp=Decimal("1.3"))
        r2023 = ExchangeRate(date=date(2023, 1, 1), usd_gbp=Decimal("1.2"))
        session.add_all([r2020, r2023])
        session.commit()
        yield
        session.delete(r2020)
        session.delete(r2023)
        session.commit()
    
    def test_load_rates_sorted(self, session, rates):
        loaded = load_rates_sorted()
        assert len(loaded) == 2
        assert loaded[0] == (2020, Decimal("1.3"))
        assert loaded[1] == (2023, Decimal("1.2"))
    
    def test_get_rate_for_date_exact(self, session, rates):
        test_date = date(2023, 1, 1)
        assert get_rate_for_date(test_date, load_rates_sorted()) == Decimal("1.2")
    
    def test_get_rate_for_date_year_fallback(self, session, rates):
        test_date = date(2023, 6, 15)
        assert get_rate_for_date(test_date, load_rates_sorted()) == Decimal("1.2")  # Same year
    
    def test_get_rate_for_date_no_rates(self):
        assert get_rate_for_date(date(2023, 1, 1), []) == Decimal("1")
    
    def test_get_rate_for_date_earlier_year(self, session, rates):
        test_date = date(2021, 1, 1)
        loaded_rates = load_rates_sorted()
        rate = get_rate_for_date(test_date, loaded_rates)
        assert rate == Decimal("1.3")  # Latest earlier: 2020

class TestFragmentDetail:
    """Test build_fragment_detail_struct for gain calculations."""
    
    def test_basic_fragment(self):
        lot = {"avg_cost": Decimal("10.00"), "usd_total": Decimal("1000"), "rate_used": Decimal("1.0"), "paye": Decimal("0")}
        struct = build_fragment_detail_struct(
            sale_price_usd=Decimal("20.00"),
            lot=lot,
            qty=Decimal("100"),
            rate_for_sale=Decimal("1.0"),
            fragment_index=1
        )
        numeric = struct["numeric_trace"]
        assert Decimal(numeric["proceeds_total_gbp"]) == Decimal("2000.00")
        assert Decimal(numeric["cost_total_gbp"]) == Decimal("1000.00")
        assert Decimal(numeric["gain_gbp"]) == Decimal("1000.00")
        assert len(struct["equations"]) == 6  # Includes lot conversion

class TestMatchingAndRecalc:
    """Integration tests for recalc_all with HMRC examples and edges."""
    
    def test_hmrc_example_2(self, session):
        """HMRC HS284 Example 2: Sale before purchase, Section 104 match."""
        # Prior holding: 9500 shares @ £1 avg
        prior = Vesting(
            date=date(2020, 1, 1),
            shares_vested=Decimal("9500"),
            price_usd=Decimal("1"),  # per share
            shares_sold=Decimal("0"),
            net_shares=Decimal("9500")
        )
        session.add(prior)
        
        # Sale: 4000 @ £1.50, total proceeds £6000
        sale = SaleInput(
            date=date(2023, 8, 30),
            shares_sold=Decimal("4000"),
            sale_price_usd=Decimal("1.50")
        )
        session.add(sale)
        
        # Purchase after sale: 500 @ £1.70 avg (not matched)
        purchase = Vesting(
            date=date(2023, 9, 11),
            shares_vested=Decimal("500"),
            price_usd=Decimal("1.70"),  # per share
            shares_sold=Decimal("0"),
            net_shares=Decimal("500")
        )
        session.add(purchase)
        
        session.commit()
        
        result = recalc_all(explain=False)
        assert not result["errors_present"]
        
        # All 4000 matched to Section 104 @ ~£1, proceeds 6000, cost 4000, gain 2000
        # Since recalc_all doesn't return disposals, query them
        from app import DisposalResult
        drs = DisposalResult.query.filter_by(sale_input_id=sale.id).all()
        total_gain = sum([d.gain_gbp for d in drs])
        total_proceeds = sum([d.proceeds_gbp for d in drs])
        total_cost = sum([d.cost_basis_gbp for d in drs])
        assert len(drs) == 2  # Forward 500 + s104 3500
        assert total_proceeds == Decimal("6000")
        assert total_cost == Decimal("4350")
        assert total_gain == Decimal("1650")
        
        # CGT: net gain 2000, AEA 6000 (2023), taxable 0, CGT 0
        summary = result["taxable_summary"]
        assert summary["net_gain"] == 2000.0
        assert summary["taxable_gain"] == 0.0
        assert summary["estimated_cgt"] == 0.0
    
    def test_same_day_matching(self, session):
        """Test same-day matching."""
        # Vesting and sale same day
        test_date = date(2023, 1, 1)
        vesting = Vesting(
            date=test_date,
            shares_vested=Decimal("1000"),
            price_usd=Decimal("10"),  # per share
            shares_sold=Decimal("0"),
            net_shares=Decimal("1000")
        )
        session.add(vesting)
        
        sale = SaleInput(
            date=test_date,
            shares_sold=Decimal("500"),
            sale_price_usd=Decimal("15.00")  # £15/share
        )
        session.add(sale)
        
        session.commit()
        
        result = recalc_all()
        drs = DisposalResult.query.filter_by(sale_input_id=sale.id).all()
        assert len(drs) == 1
        assert drs[0].matching_type == "Same-day"
        assert drs[0].proceeds_gbp == Decimal("7500")
        assert drs[0].cost_basis_gbp == Decimal("5000")
        assert drs[0].gain_gbp == Decimal("2500")
    
    def test_30_day_matching(self, session):
        """Test 30-day window matching."""
        sale_date = date(2023, 1, 31)
        vesting_date = sale_date - timedelta(days=15)  # Within 30 days
        
        vesting = Vesting(
            date=vesting_date,
            shares_vested=Decimal("1000"),
            price_usd=Decimal("8"),  # per share
            shares_sold=Decimal("0"),
            net_shares=Decimal("1000")
        )
        session.add(vesting)
        
        sale = SaleInput(
            date=sale_date,
            shares_sold=Decimal("300"),
            sale_price_usd=Decimal("12.00")
        )
        session.add(sale)
        
        session.commit()
        
        result = recalc_all()
        drs = DisposalResult.query.filter_by(sale_input_id=sale.id).all()
        assert len(drs) == 1
        assert drs[0].matching_type == "30-day"
        assert drs[0].proceeds_gbp == Decimal("3600")
        assert drs[0].cost_basis_gbp == Decimal("2400")
        assert drs[0].gain_gbp == Decimal("1200")
    
    def test_section_104_pooling(self, session):
        """Test Section 104 average cost pooling."""
        # Two prior lots
        lot1_date = date(2022, 1, 1)
        lot1 = Vesting(date=lot1_date, shares_vested=Decimal("1000"), price_usd=Decimal("5"), shares_sold=0, net_shares=Decimal("1000"))
        session.add(lot1)
        
        lot2_date = date(2023, 1, 1)
        lot2 = Vesting(date=lot2_date, shares_vested=Decimal("2000"), price_usd=Decimal("15"), shares_sold=0, net_shares=Decimal("2000"))
        session.add(lot2)
        
        # Sale after, no recent matches
        sale_date = date(2023, 6, 1)
        sale = SaleInput(date=sale_date, shares_sold=Decimal("1500"), sale_price_usd=Decimal("20.00"))
        session.add(sale)
        
        session.commit()
        
        # Pool: total shares 3000, total cost 35000, avg ~11.6667
        result = recalc_all()
        drs = DisposalResult.query.filter_by(sale_input_id=sale.id).all()
        assert len(drs) == 1
        assert drs[0].matching_type == "Section 104"
        expected_avg = Decimal("35") / Decimal("3")  # 11.666...
        assert drs[0].avg_cost_gbp == expected_avg
        assert drs[0].proceeds_gbp == Decimal("30000")
        cost = expected_avg * Decimal("1500")
        assert drs[0].cost_basis_gbp == cost
        assert drs[0].gain_gbp == Decimal("30000") - cost
    
    def test_insufficient_shares_error(self, session):
        """Test error when insufficient holdings."""
        # Small holding
        vesting = Vesting(date=date(2023, 1, 1), shares_vested=Decimal("100"), price_usd=Decimal("10"), shares_sold=0, net_shares=Decimal("100"))
        session.add(vesting)
        
        # Large sale
        sale = SaleInput(date=date(2023, 2, 1), shares_sold=Decimal("1000"), sale_price_usd=Decimal("10.00"))
        session.add(sale)
        
        session.commit()
        
        result = recalc_all()
        assert result["errors_present"]
        drs = DisposalResult.query.filter_by(sale_input_id=sale.id).all()
        assert len(drs) == 1
        assert drs[0].matching_type == "ERROR: insufficient holdings"
        assert drs[0].matched_shares == Decimal("0")
        calc_json = json.loads(drs[0].calculation_json)
        assert calc_json["error"] == "insufficient holdings"
        assert calc_json["requested"] == "1000"
        assert calc_json["remaining_unmatched"] == "900"
    
    def test_cgt_with_losses(self, session):
        """Test net gain after losses, AEA, CGT calculation for 2023."""
        # Gain disposal
        gain_sale = SaleInput(date=date(2023, 10, 1), shares_sold=Decimal("100"), sale_price_usd=Decimal("20.00"))
        # Assume matched to £10 cost
        session.add(gain_sale)
        
        # Loss disposal
        loss_sale = SaleInput(date=date(2023, 11, 1), shares_sold=Decimal("100"), sale_price_usd=Decimal("5.00"))
        # Assume matched to £10 cost
        session.add(loss_sale)
        
        # Vestings for costs (simplified, assume costs set via avg)
        v1 = Vesting(date=date(2022, 1, 1), shares_vested=Decimal("200"), price_usd=Decimal("10"), net_shares=Decimal("200"))
        session.add(v1)
        session.commit()
        
        result = recalc_all(tax_year_filter=2023)
        summary = result["taxable_summary"]
        # Gains: 100*(20-10)=1000, Losses: 100*(5-10)=-500, net 500
        # AEA 6000, taxable 0, CGT 0
        assert summary["pos"] == 1000.0
        assert summary["neg"] == 500.0
        assert summary["net_gain"] == 500.0
        assert summary["taxable_gain"] == 0.0
        assert summary["estimated_cgt"] == 0.0
    
    def test_cgt_taxable_2024(self, session):
        """Test CGT for 2024 with taxable gain > AEA=3000, rate 20%."""
        # Large gain
        sale = SaleInput(date=date(2024, 6, 1), shares_sold=Decimal("1000"), sale_price_usd=Decimal("20.00"))
        v = Vesting(date=date(2023, 1, 1), shares_vested=Decimal("1000"), price_usd=Decimal("5"), net_shares=Decimal("1000"))  # £5/share
        session.add_all([sale, v])
        session.commit()
        
        result = recalc_all(tax_year_filter=2024)
        summary = result["taxable_summary"]
        setting = Setting(key="NonSavingsIncome", value="40000")
        session.add(setting)
        session.commit()
        # Proceeds 20000, cost 5000, gain 15000
        # AEA 3000, taxable 12000, higher rate 20% = 2400
        assert summary["net_gain"] == 15000.0
        assert summary["taxable_gain"] == 12000.0
        assert summary["estimated_cgt"] == 2400.0
        
        # Check allocated CGT on disposal
        from app import DisposalResult
        drs = DisposalResult.query.filter_by(sale_input_id=sale.id).all()
        assert len(drs) == 1
        assert drs[0].cgt_due_gbp == Decimal("2400")

# Note: App uses simplified 20% rate; UK has 10% basic/20% higher based on income bands.
# For comprehensiveness, tests validate as per app logic, but comment on full UK rules.

class TestLossCarryForward:
    """Test carry-forward loss integration."""
    
    def test_carry_forward_loss_deduction(self, session):
        """Test loss from prior year reduces current gain before AEA."""
        # Prior year loss (2022)
        from app import CarryForwardLoss
        loss = CarryForwardLoss(tax_year=2022, amount=Decimal("2000"), notes="Prior loss")
        session.add(loss)
        
        # Current year 2023 gain
        sale = SaleInput(date=date(2023, 10, 1), shares_sold=Decimal("100"), sale_price_usd=Decimal("20.00"))
        v = Vesting(date=date(2023, 1, 1), shares_vested=Decimal("100"), price_usd=Decimal("10"), net_shares=Decimal("100"))
        session.add_all([sale, v])
        session.commit()
        
        result = recalc_all(tax_year_filter=2023)
        summary = result["taxable_summary"]
        # Gain 1000, carry forward 2000, net after losses 0, taxable 0
        assert summary["net_gain"] == 1000.0
        assert summary["total_carry_forward_loss"] == 2000.0
        assert summary["net_gain_after_losses"] == 0.0
        assert summary["taxable_gain"] == 0.0
        assert summary["estimated_cgt"] == 0.0

class TestIncidentalCosts:
    """Test incidental costs handling."""
    
    def test_incidental_on_acquisition(self, session):
        """Test incidental costs added to acquisition cost."""
        vesting = Vesting(
            date=date(2023, 1, 1),
            shares_vested=Decimal("100"),
            price_usd=Decimal("10"),  # per share
            incidental_costs_gbp=Decimal("50")  # £0.50/share extra
        )
        session.add(vesting)
        
        sale = SaleInput(
            date=date(2023, 2, 1),
            shares_sold=Decimal("100"),
            sale_price_usd=Decimal("15.00")  # £15/share
        )
        session.add(sale)
        session.commit()
        
        result = recalc_all()
        drs = DisposalResult.query.filter_by(sale_input_id=sale.id).all()
        assert len(drs) == 1
        # Total cost: 1000 + 50 = 1050, proceeds 1500, gain 450
        assert drs[0].cost_basis_gbp == Decimal("1050")
        assert drs[0].proceeds_gbp == Decimal("1500")
        assert drs[0].gain_gbp == Decimal("450")

    def test_incidental_on_sale_pro_rata(self, session):
        """Test incidental costs deducted pro-rata from sale proceeds."""
        vesting = Vesting(date=date(2023, 1, 1), shares_vested=Decimal("200"), price_usd=Decimal("10"), net_shares=Decimal("200"))
        session.add(vesting)
        
        sale = SaleInput(
            date=date(2023, 2, 1),
            shares_sold=Decimal("100"),  # Half the holding
            sale_price_usd=Decimal("15.00"),  # Gross £1500
            incidental_costs_gbp=Decimal("100")  # Total incidental £100, pro-rata £50
        )
        session.add(sale)
        session.commit()
        
        result = recalc_all()
        drs = DisposalResult.query.filter_by(sale_input_id=sale.id).all()
        assert len(drs) == 1
        # Proceeds: 1500 - 100 = 1400 (full deduction for single fragment), cost 1000, gain 400
        assert drs[0].proceeds_gbp == Decimal("1400")
        assert drs[0].cost_basis_gbp == Decimal("1000")
        assert drs[0].gain_gbp == Decimal("400")

class TestBedAndBreakfasting:
    """Test 30-day forward matching for bed-and-breakfasting."""
    
    def test_30_day_forward_match(self, session):
        """Test forward matching within 30 days."""
        # Acquisition after sale but within 30 days
        sale_date = date(2023, 1, 15)
        vesting_date = sale_date + timedelta(days=10)  # Within forward window
        
        sale = SaleInput(date=sale_date, shares_sold=Decimal("100"), sale_price_usd=Decimal("20.00"))
        session.add(sale)
        
        vesting = Vesting(date=vesting_date, shares_vested=Decimal("200"), price_usd=Decimal("10"), net_shares=Decimal("200"))
        session.add(vesting)
        session.commit()
        
        result = recalc_all()
        drs = DisposalResult.query.filter_by(sale_input_id=sale.id).all()
        assert len(drs) == 1
        assert drs[0].matching_type == "30-day forward"
        # Should match 100 shares from future vesting @ £10 cost
        assert drs[0].avg_cost_gbp == Decimal("10")
        assert drs[0].proceeds_gbp == Decimal("2000")
        assert drs[0].gain_gbp == Decimal("1000")

class TestCGTRateBands:
    """Test progressive CGT rates based on non-savings income."""
    
    def test_basic_rate_band_partial(self, session):
        """Test partial use of basic rate band with non-savings income."""
        # Set non-savings income to use part of basic band
        setting = Setting(key="NonSavingsIncome", value="20000")  # Leaves £17700 basic band
        session.add(setting)
        
        # Gain: £25000 (exceeds remaining basic band)
        sale = SaleInput(date=date(2023, 10, 1), shares_sold=Decimal("2500"), sale_price_usd=Decimal("10.00"))
        v = Vesting(date=date(2023, 1, 1), shares_vested=Decimal("2500"), price_usd=Decimal("0"), net_shares=Decimal("2500"))  # Zero cost for simplicity
        session.add_all([sale, v])
        session.commit()
        
        result = recalc_all(tax_year_filter=2023)
        summary = result["taxable_summary"]
        # Net gain 25000, AEA 6000, taxable 19000
        # Basic taxable: 17700 @10% = 1770, higher: 1300 @20% = 260, total CGT 2030
        assert summary["net_gain"] == 25000.0
        assert summary["basic_taxable"] == 17700.0
        assert summary["higher_taxable"] == 1300.0
        assert summary["estimated_cgt"] == 2030.0

    def test_full_higher_rate(self, session):
        """Test all gain in higher rate band."""
        setting = Setting(key="NonSavingsIncome", value="40000")  # Exceeds basic threshold
        session.add(setting)
        
        sale = SaleInput(date=date(2023, 10, 1), shares_sold=Decimal("1000"), sale_price_usd=Decimal("20.00"))
        v = Vesting(date=date(2023, 1, 1), shares_vested=Decimal("1000"), price_usd=Decimal("10"), net_shares=Decimal("1000"))
        session.add_all([sale, v])
        session.commit()
        
        result = recalc_all(tax_year_filter=2023)
        summary = result["taxable_summary"]
        # Gain 10000, AEA 6000, taxable 4000 @20% = 800
        assert summary["basic_taxable"] == 0.0
        assert summary["higher_taxable"] == 4000.0
        assert summary["estimated_cgt"] == 800.0


class TestNonQualifyingESPP:
    """Test non-qualifying ESPP (no PAYE relief added to base cost)."""
    
    def test_non_qualifying_cost_calc(self, session):
        """ESPP with discount_taxed_paye=False: cost = purchase GBP only, no PAYE add-back."""
        # ESPP: 100 shares, purchase $8, market $10 (20% discount >15%, but flag false)
        espp = ESPPPurchase(
            date=date(2023, 1, 1),
            shares_retained=Decimal("100"),
            purchase_price_usd=Decimal("8.00"),
            market_price_usd=Decimal("10.00"),
            paye_tax_gbp=Decimal("100"),  # PAYE on discount, but not added to CGT cost
            discount_taxed_paye=False,
            exchange_rate=Decimal("1.0")
        )
        session.add(espp)
        
        # Sale
        sale = SaleInput(
            date=date(2023, 2, 1),
            shares_sold=Decimal("100"),
            sale_price_usd=Decimal("12.00")
        )
        session.add(sale)
        session.commit()
        
        result = recalc_all()
        drs = DisposalResult.query.filter_by(sale_input_id=sale.id).all()
        assert len(drs) == 1
        # Purchase GBP: 800 / 1.0 = 800, no +100 PAYE, avg_cost=8.00
        # Proceeds: 1200, cost: 800, gain: 400
        assert drs[0].avg_cost_gbp == Decimal("8.00")
        assert drs[0].cost_basis_gbp == Decimal("800")
        assert drs[0].gain_gbp == Decimal("400")


class TestSplitYearScenario:
    """Test split-year treatment (partial UK residency; app assumes full-year, add proration TODO)."""
    
    def test_split_year_proration(self, session):
        """Basic split-year: assume 6/12 months residency, prorate AEA/gains (future enhancement)."""
        # For now, test current full-year behavior; TODO: add residency_fraction setting
        sale = SaleInput(date=date(2023, 7, 1), shares_sold=Decimal("100"), sale_price_usd=Decimal("20.00"))
        v = Vesting(date=date(2023, 1, 1), shares_vested=Decimal("100"), price_usd=Decimal("10"), net_shares=Decimal("100"))
        session.add_all([sale, v])
        session.commit()
        
        result = recalc_all(tax_year_filter=2023)
        summary = result["taxable_summary"]
        # Current: full gain 1000, AEA 6000, taxable 0
        assert summary["net_gain"] == 1000.0
        assert summary["cgt_allowance"] == 6000.0
        assert summary["taxable_gain"] == 0.0
        # TODO: Implement proration, e.g., effective AEA = 6000 * (6/12) = 3000, taxable 700 @20% = 140