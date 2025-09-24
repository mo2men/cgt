# app.py
# Improved UK RSU/ESPP CGT calculator — single-file enhanced version
# Features:
# - Enhanced Audit Dashboard with interactive Transaction Detail table
# - recalc_all writes calculation_json per fragment for fast UI rendering
# - /api/transactions paginated endpoint and /api/transaction/<id> trace endpoint
# - Improved DB schema (calculation_json) with idempotent migrations
# - Lazy-load trace expansion in the UI, inline SVG micro-graphics, filtering and export links
#
# Setup:
#   pip install flask sqlalchemy flask_sqlalchemy
#   python app.py
#
# Backup data.db before running on live data

from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP, getcontext, InvalidOperation
import io, csv, os, sqlite3, json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import tempfile
import os
import time

import zipfile

import xml.etree.ElementTree as ET

from datetime import date
import statistics
from statistics import mean

getcontext().prec = 50

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")
DB_URI = f"sqlite:///{DB_PATH}"
DATE_FMT = "%Y-%m-%d"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get("FLASK_SECRET", "change-me-to-secret")
db = SQLAlchemy(app)
CORS(app)

# ---------- Models ----------
class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.String(256), nullable=False)

class ExchangeRate(db.Model):
    __tablename__ = "exchange_rates"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.String(200))
    usd_gbp = db.Column(db.Numeric(28,12), nullable=False)  # USD per GBP
    notes = db.Column(db.String(200))

class Vesting(db.Model):
    __tablename__ = "vesting"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    shares_vested = db.Column(db.Numeric(28,12), nullable=False)
    price_usd = db.Column(db.Numeric(28,12))
    total_usd = db.Column(db.Numeric(28,12))
    exchange_rate = db.Column(db.Numeric(28,12))
    total_gbp = db.Column(db.Numeric(28,12))
    tax_paid_gbp = db.Column(db.Numeric(28,12))
    incidental_costs_gbp = db.Column(db.Numeric(28,12), default=Decimal("0"))
    shares_sold = db.Column(db.Numeric(28,12), default=Decimal("0"))
    net_shares = db.Column(db.Numeric(28,12))

class ESPPPurchase(db.Model):
    __tablename__ = "espp"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    shares_retained = db.Column(db.Numeric(28,12), nullable=False)
    purchase_price_usd = db.Column(db.Numeric(28,12))
    market_price_usd = db.Column(db.Numeric(28,12))
    discount = db.Column(db.Numeric(28,12))
    exchange_rate = db.Column(db.Numeric(28,12))
    total_gbp = db.Column(db.Numeric(28,12))
    discount_taxed_paye = db.Column(db.Boolean, default=True)
    paye_tax_gbp = db.Column(db.Numeric(28,12), nullable=True)
    qualifying = db.Column(db.Boolean, default=True)
    incidental_costs_gbp = db.Column(db.Numeric(28,12), default=Decimal("0"))
    notes = db.Column(db.String(200))

class SaleInput(db.Model):
    __tablename__ = "sales_in"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    shares_sold = db.Column(db.Numeric(28,12), nullable=False)
    sale_price_usd = db.Column(db.Numeric(28,12))
    exchange_rate = db.Column(db.Numeric(28,12), nullable=True)
    incidental_costs_gbp = db.Column(db.Numeric(28,12), default=Decimal("0"))

class DisposalResult(db.Model):
    __tablename__ = "disposal_results"
    id = db.Column(db.Integer, primary_key=True)
    sale_date = db.Column(db.Date, index=True)
    sale_input_id = db.Column(db.Integer)
    matched_date = db.Column(db.Date)
    matching_type = db.Column(db.String(32))
    matched_shares = db.Column(db.Numeric(28,12))
    avg_cost_gbp = db.Column(db.Numeric(28,12))
    proceeds_gbp = db.Column(db.Numeric(28,12))
    cost_basis_gbp = db.Column(db.Numeric(28,12))
    gain_gbp = db.Column(db.Numeric(28,12))
    cgt_due_gbp = db.Column(db.Numeric(28,12))
    calculation_json = db.Column(db.Text)

class PoolSnapshot(db.Model):
    __tablename__ = "pool_snapshot"
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tax_year = db.Column(db.Integer, index=True, nullable=True)
    snapshot_json = db.Column(db.Text)
    total_shares = db.Column(db.Numeric(28,12))
    total_cost_gbp = db.Column(db.Numeric(28,12))
    avg_cost_gbp = db.Column(db.Numeric(28,12))

class CalculationStep(db.Model):
    __tablename__ = "calculation_steps"
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    sale_input_id = db.Column(db.Integer, nullable=True, index=True)
    step_order = db.Column(db.Integer, nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)

class CarryForwardLoss(db.Model):
    __tablename__ = "carry_forward_losses"
    tax_year = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(28,12), nullable=False)
    notes = db.Column(db.String(200))

class CalculationDetail(db.Model):
    __tablename__ = "calculation_details"
    id = db.Column(db.Integer, primary_key=True)
    disposal_id = db.Column(db.Integer, nullable=False, index=True)
    sale_input_id = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    equations = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=False)


# ---------- Utilities ----------
def to_date(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return datetime.strptime(v, DATE_FMT).date()

def safe_decimal(x, default=Decimal("0")):
    try:
        if x is None or x == "":
            return default
        if isinstance(x, Decimal):
            return x
        return Decimal(str(x))
    except (InvalidOperation, ValueError):
        return default

def q2(d) -> Decimal:
    return safe_decimal(d).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def q6(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

def get_aea(tax_year):
    """Get Annual Exempt Amount based on tax year (ending year, e.g., 2024 for 2024/25)"""
    if tax_year is None:
        return Decimal("12300")
    aea_map = {
        2024: Decimal("3000"),  # 2024/25
        2023: Decimal("6000"),  # 2023/24
    }
    for yr in range(2022, 2020, -1):  # 2022/23 to 2020/21: 12300
        aea_map[yr] = Decimal("12300")
    # Default for earlier or future: 12300 pre-2023, 3000 post-2024
    return aea_map.get(tax_year, Decimal("3000") if tax_year > 2024 else Decimal("12300"))

def load_rates_sorted():
    rows = ExchangeRate.query.order_by(ExchangeRate.date.asc()).all()
    year_map = {}
    for r in rows:
        year_map[r.date.year] = safe_decimal(r.usd_gbp)
    return sorted([(y, year_map[y]) for y in year_map.keys()], key=lambda x: x[0])

def get_rate_for_date(target_date, rates_list):
    if target_date is None:
        return Decimal("1")
    # First, try exact date from DB
    exact_rate = ExchangeRate.query.filter_by(date=target_date).first()
    if exact_rate:
        return safe_decimal(exact_rate.usd_gbp)
    # Fallback to year-based
    year = target_date.year
    if not rates_list:
        return Decimal("1")
    exact = [r for y, r in rates_list if y == year]
    if exact:
        return exact[0]
    earlier = [(y, r) for y, r in rates_list if y < year]
    if earlier:
        return earlier[-1][1]
    later = [(y, r) for y, r in rates_list if y > year]
    if later:
        return later[0][1]
    return Decimal("1")

def build_fragment_detail_struct(sale_price_usd: Decimal, lot, qty, rate_for_sale, fragment_index):
    sale_price_usd = safe_decimal(sale_price_usd)
    qty = safe_decimal(qty)
    lot_usd_total = safe_decimal(lot.get("usd_total")) if lot.get("usd_total") is not None else None
    lot_rate_used = safe_decimal(lot.get("rate_used")) if lot.get("rate_used") is not None else None
    lot_paye = safe_decimal(lot.get("paye")) if lot.get("paye") is not None else Decimal("0")

    proceeds_per_share_gbp = (sale_price_usd / safe_decimal(rate_for_sale)) if safe_decimal(rate_for_sale) != 0 else sale_price_usd
    proceeds_total = q2(proceeds_per_share_gbp * qty)

    cost_per_share_used = q2(safe_decimal(lot["avg_cost"]))
    cost_total = q2(cost_per_share_used * qty)

    equations = []
    equations.append(f"Proceeds per share (GBP) = round(sale_price_usd / rate) = round({sale_price_usd} / {rate_for_sale}) = {q2(proceeds_per_share_gbp)}")
    equations.append(f"Total proceeds = {q2(proceeds_per_share_gbp)} × {qty} = {proceeds_total}")
    equations.append(f"Cost per share used = {cost_per_share_used}")
    equations.append(f"Total cost = {cost_per_share_used} × {qty} = {cost_total}")
    if lot_usd_total is not None and lot_rate_used is not None:
        purchase_gbp = q2(lot_usd_total / lot_rate_used) if lot_rate_used != 0 else q2(lot_usd_total)
        equations.append(f"Lot USD total {lot_usd_total} → GBP = {lot_usd_total} / {lot_rate_used} = {purchase_gbp}")
        if lot_paye and lot_paye != 0:
            equations.append(f"PAYE added = £{q2(lot_paye)} → chosen lot total = £{q2(purchase_gbp + lot_paye)}")
    gain = q2(proceeds_total - cost_total)
    equations.append(f"Gain = {proceeds_total} − {cost_total} = {gain}")

    numeric_trace = {
        "sale_price_usd": str(sale_price_usd),
        "rate_for_sale": str(rate_for_sale),
        "proceeds_per_share_gbp": str(q2(proceeds_per_share_gbp)),
        "proceeds_total_gbp": str(proceeds_total),
        "cost_per_share_gbp": str(cost_per_share_used),
        "cost_total_gbp": str(cost_total),
        "gain_gbp": str(gain),
        "lot_usd_total": str(lot_usd_total) if lot_usd_total is not None else None,
        "lot_rate_used": str(lot_rate_used) if lot_rate_used is not None else None,
        "lot_paye_gbp": str(lot_paye) if lot_paye is not None else None,
        "shares_matched": str(q6(qty)),
        "fragment_index": int(fragment_index)
    }

    return {"equations": equations, "numeric_trace": numeric_trace}

# ---------- Core matching & snapshot logic (enhanced) ----------
def recalc_all(explain=False, tax_year_filter=None, sale_filter=None):
    """
    sale_filter: Optional list of sale_input_ids or date_from (str 'YYYY-MM-DD') to recompute only affected sales.
    If None, full recalc (default).
    """
    if sale_filter is None:
        # Full recalc: clear all
        DisposalResult.query.delete()
        PoolSnapshot.query.delete()
        CalculationStep.query.delete()
        CalculationDetail.query.delete()
        db.session.commit()
        full_mode = True
    else:
        full_mode = False
        # Partial: only delete affected results
        if isinstance(sale_filter, list):
            # Filter by sale IDs
            affected_sales = SaleInput.query.filter(SaleInput.id.in_(sale_filter)).all()
            affected_ids = [s.id for s in affected_sales]
            DisposalResult.query.filter(DisposalResult.sale_input_id.in_(affected_ids)).delete()
        elif isinstance(sale_filter, str):
            # Filter by date_from: delete results for sales on/after date
            date_from = to_date(sale_filter)
            affected_sales = SaleInput.query.filter(SaleInput.date >= date_from).all()
            affected_ids = [s.id for s in affected_sales]
            DisposalResult.query.filter(DisposalResult.sale_input_id.in_(affected_ids)).delete()
        else:
            raise ValueError("sale_filter must be list of IDs or date string")
        db.session.commit()

    rates = load_rates_sorted()
    lots = []
    explanation = []
    step_idx = 0
    errors_present = False

    def log_step(msg, sale_input_id=None):
        nonlocal step_idx
        step_idx += 1
        explanation.append((sale_input_id, step_idx, msg))
        if explain:
            cs = CalculationStep(sale_input_id=sale_input_id, step_order=step_idx, message=msg)
            db.session.add(cs)

    log_step("Building lots from Vestings and ESPP purchases (ordered).")

    for v in Vesting.query.order_by(Vesting.date.asc(), Vesting.id.asc()).all():
        net = safe_decimal(v.net_shares) if v.net_shares is not None else (safe_decimal(v.shares_vested) - safe_decimal(v.shares_sold or 0))
        if net <= 0:
            log_step(f"Skip vesting {v.id} net {net}")
            continue
        usd_total = safe_decimal(v.total_usd) if v.total_usd else (safe_decimal(v.price_usd) * safe_decimal(v.shares_vested) if v.price_usd else Decimal("0"))
        exc = safe_decimal(v.exchange_rate) if v.exchange_rate else (get_rate_for_date(v.date, rates) or Decimal("1"))
        if exc == 0: exc = Decimal("1")
        total_gbp = (usd_total / exc) + safe_decimal(v.incidental_costs_gbp or 0)
        avg_cost = (total_gbp / net) if net != 0 else Decimal("0")
        entry_key = f"V:{v.id}"
        tooltip = f"RSU {v.date}: USD {usd_total} / rate {exc} → £{q2(total_gbp - safe_decimal(v.incidental_costs_gbp or 0))}; incidental £{q2(v.incidental_costs_gbp or 0)}; per-share £{q2(avg_cost)}"
        lots.append({"date": v.date, "remaining": net, "avg_cost": avg_cost, "usd_total": usd_total, "rate_used": exc, "paye": None, "entry": entry_key, "source": "RSU", "tooltip": tooltip})
        log_step(f"Added RSU lot {entry_key} shares {net} per-share {q2(avg_cost)} (incidental {q2(v.incidental_costs_gbp or 0)})")

    for p in ESPPPurchase.query.order_by(ESPPPurchase.date.asc(), ESPPPurchase.id.asc()).all():
        shares = safe_decimal(p.shares_retained)
        if shares <= 0:
            log_step(f"Skip ESPP {p.id} retained {shares}"); continue
        purchase_price_usd = safe_decimal(p.purchase_price_usd) if p.purchase_price_usd else Decimal("0")
        exc = safe_decimal(p.exchange_rate) if p.exchange_rate else (get_rate_for_date(p.date, rates) or Decimal("1"))
        if exc == 0: exc = Decimal("1")
        usd_total = purchase_price_usd * shares
        purchase_gbp = (usd_total / exc) if exc != 0 else usd_total + safe_decimal(p.incidental_costs_gbp or 0)
        paye = safe_decimal(p.paye_tax_gbp) if p.paye_tax_gbp else Decimal("0")
        chosen_total_gbp = purchase_gbp + (paye if p.discount_taxed_paye else Decimal("0"))
        avg_cost = (chosen_total_gbp / shares) if shares != 0 else Decimal("0")
        entry_key = f"E:{p.id}"
        tooltip = f"ESPP {p.date}: USD {usd_total} / rate {exc} → purchase £{q2(purchase_gbp - safe_decimal(p.incidental_costs_gbp or 0))}; incidental £{q2(p.incidental_costs_gbp or 0)}; PAYE £{q2(paye)}; per-share £{q2(avg_cost)}"
        lots.append({"date": p.date, "remaining": shares, "avg_cost": avg_cost, "usd_total": usd_total, "rate_used": exc, "paye": (paye if p.paye_tax_gbp else None), "entry": entry_key, "source": "ESPP", "tooltip": tooltip})
        log_step(f"Added ESPP lot {entry_key} shares {shares} per-share {q2(avg_cost)} (incidental {q2(p.incidental_costs_gbp or 0)})")

    lots.sort(key=lambda x: (x["date"], x["entry"]))
    log_step(f"Total lots built: {len(lots)}")

    sa = Setting.query.get("CGT_Allowance"); sb = Setting.query.get("CGT_Rate"); sc = Setting.query.get("NonSavingsIncome"); sd = Setting.query.get("BasicBandThreshold")
    cgt_allowance = safe_decimal(sa.value) if sa and safe_decimal(sa.value) > 0 and (tax_year_filter is None or tax_year_filter < 2024) else get_aea(tax_year_filter)
    non_savings_income = safe_decimal(sc.value) if sc else Decimal("0")
    basic_threshold = safe_decimal(sd.value) if sd else Decimal("37700")
    cgt_rate_basic = Decimal("10") / Decimal("100")
    cgt_rate_higher = Decimal("20") / Decimal("100")
    basic_band_available = max(Decimal("0"), basic_threshold - non_savings_income)
    log_step(f"Using allowance £{q2(cgt_allowance)} for tax year {tax_year_filter if tax_year_filter else 'all'}, non-savings income £{q2(non_savings_income)}, basic band available £{q2(basic_band_available)} (threshold £{q2(basic_threshold)}).")

    per_sale_snapshots = []
    all_fragments = []

    # Filter sales if partial
    if full_mode:
        sales_all = SaleInput.query.order_by(SaleInput.date.asc(), SaleInput.id.asc()).all()
    else:
        if isinstance(sale_filter, list):
            sales_all = SaleInput.query.filter(SaleInput.id.in_(sale_filter)).order_by(SaleInput.date.asc(), SaleInput.id.asc()).all()
        elif isinstance(sale_filter, str):
            date_from = to_date(sale_filter)
            sales_all = SaleInput.query.filter(SaleInput.date >= date_from).order_by(SaleInput.date.asc(), SaleInput.id.asc()).all()
        else:
            sales_all = []  # Should not happen

    for s in sales_all:
        log_step(f"Process sale {s.id} date {s.date} shares {safe_decimal(s.shares_sold)}", s.id)
        remaining = safe_decimal(s.shares_sold)
        rate_for_sale = safe_decimal(s.exchange_rate) if s.exchange_rate else get_rate_for_date(s.date, rates)
        incidental_sale = safe_decimal(s.incidental_costs_gbp or 0)
        if rate_for_sale == Decimal("1") and not rates and not s.exchange_rate:
            log_step("No year-level FX configured; using 1.0", s.id)
        fragments = []
        changed = {}
        print(f"DEBUG: Processing sale {s.id}, remaining={remaining}, rate={rate_for_sale}, incidental={incidental_sale}, lots before match: {[(l['entry'], l['remaining']) for l in lots if l['remaining'] > 0]}")

        for lot in lots:
            if remaining <= 0: break
            if lot["date"] == s.date and lot["remaining"] > 0:
                before = safe_decimal(lot["remaining"])
                take = min(lot["remaining"], remaining)
                lot["remaining"] -= take
                after = safe_decimal(lot["remaining"])
                changed[lot["entry"]] = {"matching": "Same-day", "before": float(before), "after": float(after), "delta": float(after - before)}
                fragments.append(("Same-day", lot, take))
                remaining -= take

        if remaining > 0:
            window_start = s.date - timedelta(days=30)
            for lot in lots:
                if remaining <= 0: break
                if lot["date"] >= window_start and lot["date"] < s.date and lot["remaining"] > 0:
                    before = safe_decimal(lot["remaining"])
                    take = min(lot["remaining"], remaining)
                    lot["remaining"] -= take
                    after = safe_decimal(lot["remaining"])
                    changed[lot["entry"]] = {"matching": "30-day", "before": float(before), "after": float(after), "delta": float(after - before)}
                    fragments.append(("30-day", lot, take))
                    remaining -= take

        if remaining > 0:
            window_end = s.date + timedelta(days=30)
            for lot in lots:
                if remaining <= 0: break
                if lot["date"] > s.date and lot["date"] <= window_end and lot["remaining"] > 0:
                    before = safe_decimal(lot["remaining"])
                    take = min(lot["remaining"], remaining)
                    lot["remaining"] -= take
                    after = safe_decimal(lot["remaining"])
                    changed[lot["entry"]] = {"matching": "30-day forward", "before": float(before), "after": float(after), "delta": float(after - before)}
                    fragments.append(("30-day forward", lot, take))
                    remaining -= take
                    log_step(f"30-day forward match from {lot['entry']} {take} shares", s.id)

        if remaining > 0:
            # Section 104 pooling: compute average from all prior remaining lots
            prior_lots = [lot for lot in lots if lot["date"] < s.date and safe_decimal(lot["remaining"]) > 0]
            if prior_lots:
                prior_shares = sum(safe_decimal(lot["remaining"]) for lot in prior_lots)
                prior_cost = sum(safe_decimal(lot["avg_cost"]) * safe_decimal(lot["remaining"]) for lot in prior_lots)
                avg_cost_s104 = prior_cost / prior_shares if prior_shares > 0 else Decimal("0")
                take = remaining
                cost_total_s104 = avg_cost_s104 * take
                # Deplete prior lots FIFO
                depleted_take = Decimal("0")
                for lot in prior_lots:
                    if take <= 0: break
                    this_take = min(safe_decimal(lot["remaining"]), take)
                    before = safe_decimal(lot["remaining"])
                    lot["remaining"] -= this_take
                    after = safe_decimal(lot["remaining"])
                    changed[lot["entry"]] = {"matching": "Section 104", "before": float(before), "after": float(after), "delta": float(after - before)}
                    take -= this_take
                    depleted_take += this_take
                # Create virtual lot for fragment
                virtual_lot = {
                    "entry": "S104_POOL",
                    "date": s.date,
                    "source": "POOLED",
                    "avg_cost": avg_cost_s104,
                    "usd_total": None,
                    "rate_used": None,
                    "paye": None,
                    "tooltip": f"s104 average from prior lots: £{q2(avg_cost_s104)} for {depleted_take} shares"
                }
                fragments.append(("Section 104", virtual_lot, depleted_take))
                remaining = 0
                log_step(f"s104 match: {depleted_take} shares at avg £{q2(avg_cost_s104)}", s.id)
            else:
                log_step("s104: No prior lots available", s.id)

        if remaining > 0:
            dr = DisposalResult(sale_date=s.date, sale_input_id=s.id, matched_date=None, matching_type="ERROR: insufficient holdings",
                                matched_shares=Decimal("0"), avg_cost_gbp=Decimal("0"), proceeds_gbp=Decimal("0"),
                                cost_basis_gbp=Decimal("0"), gain_gbp=Decimal("0"), cgt_due_gbp=Decimal("0"),
                                calculation_json=json.dumps({"error": "insufficient holdings", "requested": str(s.shares_sold), "remaining_unmatched": str(remaining)}))
            db.session.add(dr); db.session.commit()
            log_step(f"ERROR sale {s.id} insufficient remaining {remaining}", s.id)
            errors_present = True
            pool_after = [{"entry": lot["entry"], "date": lot["date"].isoformat(), "source": lot["source"], "remaining": float(lot["remaining"]), "per_share_cost": float(q2(lot["avg_cost"])), "tooltip": lot.get("tooltip","")} for lot in lots]
            per_sale_snapshots.append({"sale": {"id": s.id, "date": s.date.isoformat(), "shares": float(s.shares_sold)}, "changed": changed, "pool_after": pool_after, "error": True})
            continue

        # Build raw fragments without db add
        raw_fragments = []
        frag_index = 0
        for mtype, lot, qty in fragments:
            frag_index += 1
            struct = build_fragment_detail_struct(s.sale_price_usd, lot, qty, rate_for_sale, frag_index)
            struct["inputs"] = {"sale_price_usd": str(s.sale_price_usd), "sale_rate_used": str(rate_for_sale), "lot": {"entry": lot["entry"], "date": str(lot["date"]), "source": lot["source"], "usd_total": str(lot.get("usd_total")), "rate_used": str(lot.get("rate_used")), "paye": str(lot.get("paye"))}}
            proceeds_total = Decimal(struct["numeric_trace"]["proceeds_total_gbp"])
            cost_total = Decimal(struct["numeric_trace"]["cost_total_gbp"])
            gain = Decimal(struct["numeric_trace"]["gain_gbp"])
            print(f"DEBUG: Raw Fragment {frag_index} for sale {s.id}: type={mtype}, qty={qty}, proceeds={proceeds_total}, cost={cost_total}, gain={gain}")
            raw_fragments.append((mtype, lot, qty, struct, proceeds_total, cost_total, gain, frag_index))

        # Apply incidental costs to proceeds
        if incidental_sale > 0 and raw_fragments:
            total_gross_proceeds = sum(f[4] for f in raw_fragments)
            if total_gross_proceeds > 0:
                net_proceeds = total_gross_proceeds - incidental_sale
                pro_rata = net_proceeds / total_gross_proceeds
                log_step(f"Applied incidental costs £{q2(incidental_sale)} to sale {s.id} (pro-rata {q2(pro_rata * 100)}%)", s.id)
                for i, (mtype, lot, qty, struct, gross_proceeds, cost_total, raw_gain, frag_index) in enumerate(raw_fragments):
                    adjusted_proceeds = q2(gross_proceeds * pro_rata)
                    adjusted_gain = q2(adjusted_proceeds - cost_total)
                    # Update equations
                    struct["equations"][1] = f"Adjusted total proceeds = {q2(gross_proceeds)} × {q2(pro_rata)} (after £{q2(incidental_sale)} incidental) = {adjusted_proceeds}"
                    struct["numeric_trace"]["proceeds_total_gbp"] = str(adjusted_proceeds)
                    struct["numeric_trace"]["gain_gbp"] = str(adjusted_gain)
                    # Add incidental to inputs
                    struct["inputs"]["incidental_sale"] = str(incidental_sale)
                    dr = DisposalResult(sale_date=s.date, sale_input_id=s.id, matched_date=lot["date"], matching_type=mtype,
                                        matched_shares=qty, avg_cost_gbp=safe_decimal(lot["avg_cost"]), proceeds_gbp=adjusted_proceeds,
                                        cost_basis_gbp=cost_total, gain_gbp=adjusted_gain, cgt_due_gbp=Decimal("0"),
                                        calculation_json=json.dumps({"inputs": struct["inputs"], "equations": struct["equations"], "numeric_trace": struct["numeric_trace"]}))
                    db.session.add(dr)
                    db.session.commit()
                    cd = CalculationDetail(disposal_id=dr.id, sale_input_id=s.id, equations="\n".join(struct["equations"]), explanation=f"Fragment {frag_index} matched {qty} shares from {lot['entry']} ({mtype}), adjusted for incidental costs")
                    db.session.add(cd)
                    db.session.commit()
                    all_fragments.append(dr)
            else:
                log_step(f"No proceeds to adjust for incidental £{q2(incidental_sale)} on sale {s.id}", s.id)
        else:
            for i, (mtype, lot, qty, struct, proceeds_total, cost_total, gain, frag_index) in enumerate(raw_fragments):
                dr = DisposalResult(sale_date=s.date, sale_input_id=s.id, matched_date=lot["date"], matching_type=mtype,
                                    matched_shares=qty, avg_cost_gbp=safe_decimal(lot["avg_cost"]), proceeds_gbp=proceeds_total,
                                    cost_basis_gbp=cost_total, gain_gbp=gain, cgt_due_gbp=Decimal("0"),
                                    calculation_json=json.dumps({"inputs": struct["inputs"], "equations": struct["equations"], "numeric_trace": struct["numeric_trace"]}))
                db.session.add(dr)
                db.session.commit()
                cd = CalculationDetail(disposal_id=dr.id, sale_input_id=s.id, equations="\n".join(struct["equations"]), explanation=f"Fragment {frag_index} matched {qty} shares from {lot['entry']} ({mtype})")
                db.session.add(cd)
                db.session.commit()
                all_fragments.append(dr)

        pool_after = [{"entry": lot["entry"], "date": lot["date"].isoformat(), "source": lot["source"], "remaining": float(lot["remaining"]), "per_share_cost": float(q2(lot["avg_cost"])), "tooltip": lot.get("tooltip","")} for lot in lots]
        per_sale_snapshots.append({"sale": {"id": s.id, "date": s.date.isoformat(), "shares": float(s.shares_sold)}, "changed": changed, "pool_after": pool_after, "error": False})
    
    # Only create snapshots if full recalc or if tax_year_filter specified
    if full_mode or tax_year_filter:
        snaps_by_ty = {}
        for snap in per_sale_snapshots:
            sale_date = datetime.fromisoformat(snap["sale"]["date"]).date()
            ty = sale_date.year if sale_date >= date(sale_date.year,4,6) else sale_date.year - 1
            snaps_by_ty.setdefault(ty, []).append(snap)
    
        for ty, snaps in snaps_by_ty.items():
            total_shares = sum([safe_decimal(lot["remaining"]) for lot in lots])
            total_cost = sum([safe_decimal(lot["avg_cost"]) * safe_decimal(lot["remaining"]) for lot in lots])
            avg_cost = (total_cost / total_shares) if total_shares != 0 else Decimal("0")
            ps = PoolSnapshot(timestamp=datetime.utcnow(), tax_year=ty, snapshot_json=json.dumps(snaps), total_shares=total_shares, total_cost_gbp=total_cost, avg_cost_gbp=avg_cost)
            db.session.add(ps)
    
        # Final snapshot only on full
        if full_mode:
            total_shares = sum([safe_decimal(lot["remaining"]) for lot in lots])
            total_cost = sum([safe_decimal(lot["avg_cost"]) * safe_decimal(lot["remaining"]) for lot in lots])
            avg_cost = (total_cost / total_shares) if total_shares != 0 else Decimal("0")
            ps_final = PoolSnapshot(timestamp=datetime.utcnow(), tax_year=None, snapshot_json=json.dumps(per_sale_snapshots), total_shares=total_shares, total_cost_gbp=total_cost, avg_cost_gbp=avg_cost)
            db.session.add(ps_final)
        db.session.commit()
        log_step("Stored snapshots and final pool snapshot.")
    else:
        db.session.commit()
        log_step(f"Partial recalc complete for {len(sales_all)} sales. No new snapshots created.")

    taxable_summary = None
    if tax_year_filter is not None and not errors_present:
        tax_start = date(tax_year_filter,4,6); tax_end = date(tax_year_filter+1,4,5)
        disposals = DisposalResult.query.filter(DisposalResult.sale_date >= tax_start, DisposalResult.sale_date <= tax_end).all()
        print(f"DEBUG: {len(disposals)} disposals for tax year {tax_year_filter}: {[ (d.sale_input_id, d.gain_gbp, type(d.gain_gbp)) for d in disposals ]}")
        gains = [safe_decimal(d.gain_gbp) for d in disposals if safe_decimal(d.gain_gbp) > 0]
        losses = [safe_decimal(d.gain_gbp) for d in disposals if safe_decimal(d.gain_gbp) < 0]
        pos = sum(gains)
        neg = sum([abs(l) for l in losses])
        print(f"DEBUG: pos={pos} (type {type(pos)}), neg={neg} (type {type(neg)})")
        net_gain = pos - neg
        excess_current_loss = max(Decimal("0"), neg - pos)
        if net_gain < 0: net_gain = Decimal("0")

        if excess_current_loss > 0 and tax_year_filter is not None:
            loss_year = tax_year_filter
            loss = CarryForwardLoss.query.filter_by(tax_year=loss_year).first()
            if loss:
                loss.amount += excess_current_loss
            else:
                loss = CarryForwardLoss(tax_year=loss_year, amount=excess_current_loss, notes=f"Excess loss from {tax_year_filter}")
                db.session.add(loss)
        
        # Apply carry-forward losses from previous years
        carry_forward_losses = CarryForwardLoss.query.filter(CarryForwardLoss.tax_year < tax_year_filter).all()
        total_carry_forward_loss = sum(safe_decimal(loss.amount) for loss in carry_forward_losses)
        
        # Subtract carry-forward losses from net gain before applying allowance
        net_gain_after_losses = max(Decimal("0"), net_gain - total_carry_forward_loss)
        
        sa = Setting.query.get("CGT_Allowance"); sc = Setting.query.get("NonSavingsIncome"); sd = Setting.query.get("BasicBandThreshold")
        cgt_allowance = safe_decimal(sa.value) if sa and safe_decimal(sa.value) > 0 and tax_year_filter < 2024 else get_aea(tax_year_filter)
        non_savings_income = safe_decimal(sc.value) if sc else Decimal("0")
        basic_threshold = safe_decimal(sd.value) if sd else Decimal("37700")
        basic_band_available = max(Decimal("0"), basic_threshold - non_savings_income)
        taxable_gain = net_gain_after_losses - cgt_allowance
        if taxable_gain < 0: taxable_gain = Decimal("0")
        basic_taxable = min(taxable_gain, basic_band_available)
        higher_taxable = taxable_gain - basic_taxable
        estimated_cgt = q2(basic_taxable * Decimal("0.10") + higher_taxable * Decimal("0.20"))
        taxable_summary = {
            "pos": float(q2(pos)), "neg": float(q2(neg)), "net_gain": float(q2(net_gain)),
            "cgt_allowance": float(q2(cgt_allowance)),
            "non_savings_income": float(q2(non_savings_income)),
            "basic_threshold": float(q2(basic_threshold)),
            "basic_band_available": float(q2(basic_band_available)),
            "total_carry_forward_loss": float(q2(total_carry_forward_loss)),
            "net_gain_after_losses": float(q2(net_gain_after_losses)),
            "taxable_gain": float(q2(taxable_gain)),
            "basic_taxable": float(q2(basic_taxable)),
            "higher_taxable": float(q2(higher_taxable)),
            "estimated_cgt": float(estimated_cgt)
        }
        if pos > 0 and estimated_cgt > 0:
            for d in disposals:
                g = safe_decimal(d.gain_gbp)
                if g > 0:
                    share = g / pos
                    alloc = q2(estimated_cgt * share)
                    d.cgt_due_gbp = alloc
                    db.session.add(d)
            db.session.commit()

            # Commit the new carry-forward loss if added
            if excess_current_loss > 0 and tax_year_filter is not None:
                db.session.commit()

    return {"per_sale_snapshots": per_sale_snapshots, "errors_present": errors_present, "taxable_summary": taxable_summary}

# ---------- Templates (Audit Dashboard + Editor) ----------
AUDIT_DASH_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Audit Dashboard</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    :root{
      --rsu:#2b7be4; --espp:#00b39f; --same:#198754; --thirty:#ffb703; --s104:#2b7be4; --err:#e03131;
    }
    .match-Same-day{background:var(--same);color:white;padding:3px 7px;border-radius:12px;font-size:0.85rem}
    .match-30-day{background:var(--thirty);color:black;padding:3px 7px;border-radius:12px;font-size:0.85rem}
    .match-Section-104{background:var(--s104);color:white;padding:3px 7px;border-radius:12px;font-size:0.85rem}
    .match-ERROR{background:var(--err);color:white;padding:3px 7px;border-radius:12px;font-size:0.85rem}
    .pool-bar{border:1px solid #e6e9ef;border-radius:4px}
    pre.eqbox{background:#f8f9fa;padding:8px;border-radius:4px;white-space:pre-wrap;}
    tr.trace-row td{background:#fbfdff}
    .small-muted{font-size:0.85rem;color:#6c757d}
  </style>
</head>
<body class="bg-light">
<div class="container py-3">
  <div class="d-flex align-items-center mb-3">
    <h1 class="me-auto">Audit Dashboard</h1>
    <div>
      <a class="btn btn-outline-primary me-2" href="{{ url_for('index_full') }}">Editor</a>
      <a class="btn btn-primary" id="recalc-btn" href="{{ url_for('recalculate') }}">Recalculate & store snapshots</a>
    </div>
  </div>

  <div class="row mb-3">
    <div class="col-md-4">
      <label class="form-label">Tax year</label>
      <select id="tax-year" class="form-select">
        <option value="">All</option>
        {% for y in tax_years %}
          <option value="{{ y }}" {% if y==sel_tax_year %}selected{% endif %}>{{ y }} → {{ (y+1) }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-4">
      <label class="form-label">Filter</label>
      <select id="filter-match" class="form-select">
        <option value="">All matches</option>
        <option value="Same-day">Same-day</option>
        <option value="30-day">30-day</option>
        <option value="Section 104">Section 104</option>
        <option value="ERROR">Error</option>
      </select>
    </div>
    <div class="col-md-4">
      <label class="form-label">Search</label>
      <input id="search" class="form-control" placeholder="lot id, sale id, date, etc">
    </div>
  </div>

  <div class="mb-3">
    <a id="export-csv" class="btn btn-sm btn-outline-secondary" href="{{ url_for('download_csv', kind='disposals') }}">Download Disposals CSV</a>
    <a id="export-pool" class="btn btn-sm btn-outline-secondary" href="{{ url_for('download_csv', kind='pool') }}">Download Pool CSV</a>
    <a id="export-summary" class="btn btn-sm btn-outline-secondary" href="{{ url_for('download_csv', kind='summary') }}">Download Summary CSV</a>
  </div>

  <div id="txn-table-wrapper">
    <table class="table table-sm table-hover" id="txn-table">
      <thead>
        <tr>
          <th>Disposal Date</th><th>Sale ID</th><th>Frag</th><th>Units</th><th>Match</th><th>Lot</th><th>Event Date</th>
          <th>Source</th><th>Rate</th><th>Cost/Share</th><th>Proceeds</th><th>Cost</th><th>Gain</th><th>Pool after</th><th></th>
        </tr>
      </thead>
      <tbody id="txn-body"></tbody>
    </table>
    <div id="no-data" class="text-muted">No transactions loaded. Use Recalculate to generate snapshots and transactions.</div>
  </div>

</div>

<script>
  const apiListUrl = "/api/transactions";
  const txBody = document.getElementById("txn-body");
  const noData = document.getElementById("no-data");
  const taxYearEl = document.getElementById("tax-year");
  const filterMatch = document.getElementById("filter-match");
  const searchEl = document.getElementById("search");

  function fmt(num, d=2){ return Number(num).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d}) }

  async function loadTransactions(){
    const params = new URLSearchParams();
    if(taxYearEl.value) params.set("tax_year", taxYearEl.value);
    if(filterMatch.value) params.set("matching", filterMatch.value);
    if(searchEl.value) params.set("q", searchEl.value);
    params.set("limit", "1000");
    const res = await fetch(apiListUrl + "?" + params.toString());
    const data = await res.json();
    txBody.innerHTML = "";
    if(!data.items || data.items.length===0){ noData.style.display="block"; return; } else { noData.style.display="none"; }
    for(const frag of data.items){
      const tr = document.createElement("tr");
      const matchClass = "match-" + (frag.matching_type ? frag.matching_type.replace(" ","-") : "ERROR");
      tr.innerHTML = `
        <td>${frag.sale_date}</td>
        <td><a href="#sale-${frag.sale_input_id}">${frag.sale_input_id}</a></td>
        <td>${frag.fragment_index}</td>
        <td>${fmt(frag.matched_shares,6)}</td>
        <td><span class="${matchClass}">${frag.matching_type}</span></td>
        <td><a href="#" class="lot-link" data-lot="${frag.lot_entry}">${frag.lot_entry || ''}</a></td>
        <td>${frag.matched_date || ''}</td>
        <td>${frag.source || ''}</td>
        <td>${frag.rate_used || ''}</td>
        <td>£${fmt(frag.avg_cost_gbp)}</td>
        <td>£${fmt(frag.proceeds_gbp)}</td>
        <td>£${fmt(frag.cost_basis_gbp)}</td>
        <td>£${fmt(frag.gain_gbp)}</td>
        <td><svg width="120" height="14" class="pool-bar" role="img" aria-label="pool"></svg></td>
        <td><button class="btn btn-sm btn-outline-secondary btn-trace" data-id="${frag.disposal_id}">View trace</button></td>
      `;
      txBody.appendChild(tr);

      const tr2 = document.createElement("tr");
      tr2.className = "trace-row";
      tr2.style.display = "none";
      tr2.innerHTML = `<td colspan="15"><div id="trace-${frag.disposal_id}">Loading trace...</div></td>`;
      txBody.appendChild(tr2);

      const svg = tr.querySelector("svg.pool-bar");
      try{
        const rsu = Number(frag.pool_rsu_pct || 0);
        const espp = Number(frag.pool_espp_pct || 0);
        const w = 120;
        svg.innerHTML = '';
        const ns = 'http://www.w3.org/2000/svg';
        const rectBg = document.createElementNS(ns,'rect');
        rectBg.setAttribute('x',0); rectBg.setAttribute('y',0); rectBg.setAttribute('width',w); rectBg.setAttribute('height',14); rectBg.setAttribute('fill','none'); rectBg.setAttribute('stroke','#e6e9ef');
        svg.appendChild(rectBg);
        let x = 0;
        if(rsu > 0){
          const rW = Math.max(1, Math.round(w * rsu));
          const rRect = document.createElementNS(ns,'rect');
          rRect.setAttribute('x',x); rRect.setAttribute('y',0); rRect.setAttribute('width',rW); rRect.setAttribute('height',14); rRect.setAttribute('fill','#2b7be4');
          svg.appendChild(rRect); x += rW;
        }
        if(espp > 0){
          const eW = Math.max(1, Math.round(w * espp));
          const eRect = document.createElementNS(ns,'rect');
          eRect.setAttribute('x',x); eRect.setAttribute('y',0); eRect.setAttribute('width',eW); eRect.setAttribute('height',14); eRect.setAttribute('fill','#00b39f');
          svg.appendChild(eRect); x += eW;
        }
      }catch(e){}
    }
  }

  async function fetchTrace(id){
    const el = document.getElementById('trace-' + id);
    if(!el) return;
    el.innerHTML = 'Loading trace...';
    const res = await fetch('/api/transaction/' + id);
    if(!res.ok){ el.innerHTML = '<div class="text-danger">Failed to load trace</div>'; return; }
    const data = await res.json();
    let html = '<div class="p-2">';
    html += `<h6>Disposal ${data.disposal_id} — Fragment</h6>`;
    if(data.calculation && data.calculation.equations){
      html += '<pre class="eqbox">' + data.calculation.equations.join('\\n') + '</pre>';
    } else if(data.details && data.details.length){
      for(const d of data.details){
        html += '<pre class="eqbox">' + d.equations + '</pre>';
      }
    } else {
      html += '<div class="small-muted">No detailed equations available.</div>';
    }
    if(data.calculation && data.calculation.numeric_trace){
      const nt = data.calculation.numeric_trace;
      html += '<dl class="row mt-2">';
      html += `<dt class="col-3">Sale price (USD)</dt><dd class="col-9">$${nt.sale_price_usd}</dd>`;
      html += `<dt class="col-3">Sale rate used</dt><dd class="col-9">${nt.rate_for_sale}</dd>`;
      html += `<dt class="col-3">Proceeds total (GBP)</dt><dd class="col-9">£${nt.proceeds_total_gbp}</dd>`;
      html += `<dt class="col-3">Cost total (GBP)</dt><dd class="col-9">£${nt.cost_total_gbp}</dd>`;
      html += `<dt class="col-3">Gain (GBP)</dt><dd class="col-9">£${nt.gain_gbp}</dd>`;
      html += '</dl>';
    }
    html += '<details class="mt-2"><summary class="small-muted">Raw JSON</summary><pre class="eqbox">' + JSON.stringify(data, null, 2) + '</pre></details>';
    html += '</div>';
    el.innerHTML = html;
  }

  document.addEventListener('click', function(e){
    if(e.target && e.target.classList.contains('btn-trace')){
      const id = e.target.getAttribute('data-id');
      const tr = e.target.closest('tr');
      const traceRow = tr.nextElementSibling;
      if(!traceRow) return;
      if(traceRow.style.display === 'none' || traceRow.style.display === ''){
        traceRow.style.display = '';
        fetchTrace(id);
      } else {
        traceRow.style.display = 'none';
      }
    }
  });

  document.getElementById('tax-year').addEventListener('change', loadTransactions);
  document.getElementById('filter-match').addEventListener('change', loadTransactions);
  document.getElementById('search').addEventListener('input', function(){ setTimeout(loadTransactions, 300); });

  loadTransactions();
</script>

</body>
</html>
"""

# ---------- CRUD and route handlers (Editor + Preview) ----------
INDEX_FULL_HTML = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>Editor</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light">
<div class="container py-3">
  <h1>Editor</h1>
  <p><a href="{{ url_for('index') }}">Preview</a> | <a href="{{ url_for('audit') }}">Audit</a></p>

  <h4>Exchange Rates</h4>
  <div class="mb-2">
    <form action="{{ url_for('upload_boe_csv') }}" method="post" enctype="multipart/form-data" class="row g-2">
      <div class="col-auto">
        <input type="file" name="csv_file" accept=".csv" class="form-control form-control-sm" required>
      </div>
      <div class="col-auto">
        <a href="https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp?Travel=NIxIRxRSxSUx&FromSeries=1&ToSeries=50&DAT=RNG&FD=1&FM=Jan&FY=2020&TD=31&TM=Dec&TY=2025&FNY=&CSVF=TT&html.x=265&html.y=40&C=C8P&Filter=N#" target="_blank" class="btn btn-sm btn-outline-secondary">Download BoE CSV</a>
      </div>
      <div class="col-auto">
        <button type="submit" class="btn btn-sm btn-secondary">Upload BoE CSV</button>
      </div>
    </form>
  </div>
  <form action="{{ url_for('add_rate') }}" method="post" class="row g-2 mb-2">
    <div class="col-4"><input name="date" type="date" class="form-control" required></div>
    <div class="col-4"><input name="rate" type="number" step="0.000001" class="form-control" required></div>
    <div class="col-4"><button class="btn btn-sm btn-primary">Add rate</button></div>
  </form>
  <table class="table table-sm"><thead><tr><th>Date</th><th>USD→GBP</th><th></th></tr></thead>
    <tbody>{% for r in rates %}<tr><td>{{ r.date }}</td><td>{{ r.usd_gbp }}</td><td><a class="btn btn-sm btn-outline-danger" href="{{ url_for('delete_rate', id=r.id) }}">Delete</a></td></tr>{% else %}<tr><td colspan=3>No rates</td></tr>{% endfor %}</tbody></table>

  <h4>Vestings</h4>
  <form action="{{ url_for('add_vesting') }}" method="post" class="row g-2 mb-2">
    <div class="col-3"><input name="date" type="date" class="form-control" required></div>
    <div class="col-3"><input name="shares_vested" type="number" step="0.000001" class="form-control" required></div>
    <div class="col-3"><input name="price_usd" type="number" step="0.000001" class="form-control" placeholder="price USD"></div>
    <div class="col-3"><input name="shares_sold" type="number" step="0.000001" class="form-control" placeholder="already sold"></div>
    <div class="col-12 mt-2"><button class="btn btn-sm btn-success">Add vesting</button></div>
  </form>
  <table class="table table-sm"><thead><tr><th>Date</th><th>Shares</th><th>Price USD</th><th></th></tr></thead>
    <tbody>{% for v in vestings %}<tr><td>{{ v.date }}</td><td>{{ v.shares_vested }}</td><td>{{ v.price_usd or '' }}</td><td><a class="btn btn-sm btn-outline-primary" href="{{ url_for('edit_vesting', id=v.id) }}">Edit</a> <a class="btn btn-sm btn-outline-danger" href="{{ url_for('delete_vesting', id=v.id) }}">Delete</a></td></tr>{% else %}<tr><td colspan=4>No vestings</td></tr>{% endfor %}</tbody></table>

  <h4>ESPP</h4>
  <form action="{{ url_for('add_espp') }}" method="post" class="row g-2 mb-2">
    <div class="col-3"><input name="date" type="date" class="form-control" required></div>
    <div class="col-3"><input name="shares_retained" type="number" step="0.000001" class="form-control" required></div>
    <div class="col-3"><input name="purchase_price_usd" type="number" step="0.000001" class="form-control"></div>
    <div class="col-3"><input name="market_price_usd" type="number" step="0.000001" class="form-control"></div>
    <div class="col-6 mt-2"><input name="paye_tax_gbp" class="form-control" placeholder="PAYE GBP (opt)"></div>
    <div class="col-6 mt-2"><input name="exchange_rate" class="form-control" placeholder="USD per GBP (opt)"></div>
    <div class="col-12 mt-2 form-check"><input class="form-check-input" type="checkbox" id="discount_taxed" name="discount_taxed" checked><label class="form-check-label" for="discount_taxed">Discount taxed under PAYE</label></div>
    <div class="col-12 mt-2"><button class="btn btn-sm btn-warning">Add ESPP</button></div>
  </form>
  <table class="table table-sm"><thead><tr><th>Date</th><th>Shares</th><th>Purchase</th><th></th></tr></thead>
    <tbody>{% for e in espps %}<tr><td>{{ e.date }}</td><td>{{ e.shares_retained }}</td><td>{{ e.purchase_price_usd or '' }}</td><td><a class="btn btn-sm btn-outline-primary" href="{{ url_for('edit_espp', id=e.id) }}">Edit</a> <a class="btn btn-sm btn-outline-danger" href="{{ url_for('delete_espp', id=e.id) }}">Delete</a></td></tr>{% else %}<tr><td colspan=4>No ESPP</td></tr>{% endfor %}</tbody></table>

  <h4>Sales</h4>
  <form action="{{ url_for('add_sale') }}" method="post" class="row g-2 mb-2">
    <div class="col-4"><input name="date" type="date" class="form-control" required></div>
    <div class="col-4"><input name="shares_sold" type="number" step="0.000001" class="form-control" required></div>
    <div class="col-4"><input name="sale_price_usd" type="number" step="0.000001" class="form-control" required></div>
    <div class="col-12 mt-2"><button class="btn btn-sm btn-danger">Add sale</button></div>
  </form>
  <table class="table table-sm"><thead><tr><th>Date</th><th>Shares</th><th>Price USD</th><th></th></tr></thead>
    <tbody>{% for s in sales %}<tr><td>{{ s.date }}</td><td>{{ s.shares_sold }}</td><td>{{ s.sale_price_usd }}</td><td><a class="btn btn-sm btn-outline-primary" href="{{ url_for('edit_sale', id=s.id) }}">Edit</a> <a class="btn btn-sm btn-outline-danger" href="{{ url_for('delete_sale', id=s.id) }}">Delete</a></td></tr>{% else %}<tr><td colspan=4>No sales</td></tr>{% endfor %}</tbody></table>

</div>
</body>
</html>
"""

INDEX_HTML = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>UK RSU/ESPP CGT</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>.lot-tooltip { cursor: help; text-decoration: underline dotted; }</style>
</head>
<body class="bg-light">
<div class="container py-3">
  <h1>UK RSU / ESPP CGT</h1>
  <div class="mb-2">
    <a class="btn btn-outline-secondary btn-sm" href="{{ url_for('index_full') }}">Editor</a>
    <a class="btn btn-outline-secondary btn-sm" href="{{ url_for('audit') }}">Audit</a>
  </div>
  <div class="row">
    <div class="col-md-8">
      <h5>Lot preview</h5>
      <table class="table table-sm">
        <thead><tr><th>Lot</th><th>Date</th><th>Source</th><th>Remaining</th><th>Per-share GBP</th><th>Info</th></tr></thead>
        <tbody>
          {% for lot in computed_lots %}
            <tr>
              <td>{{ lot.entry }}</td>
              <td>{{ lot.date }}</td>
              <td>{{ lot.source }}</td>
              <td>{{ '%.6f'|format(lot.remaining) }}</td>
              <td>£{{ '%.2f'|format(lot.avg_cost) }}</td>
              <td><span class="lot-tooltip" title="{{ lot.tooltip }}">details</span></td>
            </tr>
          {% else %}
            <tr><td colspan="6">No lots</td></tr>
          {% endfor %}
        </tbody>
      </table>
      <a class="btn btn-primary" href="{{ url_for('recalculate') }}">Recalculate & store snapshots</a>
    </div>
    <div class="col-md-4">
      <h5>Quick links</h5>
      <p><a class="btn btn-sm btn-secondary" href="{{ url_for('download_csv', kind='disposals') }}">Download Disposals CSV</a></p>
      <p><a class="btn btn-sm btn-secondary" href="{{ url_for('download_csv', kind='pool') }}">Download Pool CSV</a></p>
      <p><a class="btn btn-sm btn-secondary" href="{{ url_for('download_csv', kind='summary') }}">Download Summary CSV</a></p>
    </div>
  </div>
</div>
</body>
</html>
"""

# ---------- CRUD and route handlers ----------

@app.route("/upload_boe_csv", methods=["POST"])
def upload_boe_csv():
    if "csv_file" not in request.files:
        flash("No file part", "danger")
        return redirect(url_for("index_full"))
    file = request.files["csv_file"]
    if file.filename == "":
        flash("No selected file", "danger")
        return redirect(url_for("index_full"))
    if not file.filename.lower().endswith(".csv"):
        flash("File must be a CSV", "danger")
        return redirect(url_for("index_full"))
    try:
        content = file.read().decode("utf-8")
        stream = io.StringIO(content, newline=None)
        reader = csv.reader(stream)
        if not reader:  # empty file
            flash("Empty CSV file", "danger")
            return redirect(url_for("index_full"))
        next(reader, None)  # skip header
        existing_dates = set(r.date for r in ExchangeRate.query.all())
        inserted = 0
        for row in reader:
            if len(row) < 2:
                continue
            date_str = row[0].strip().strip('"')
            rate_str = row[1].strip().strip('"')
            if not date_str or not rate_str:
                continue
            try:
                dt = datetime.strptime(date_str, "%d %b %y").date()
                if dt.year < 2010 or dt.year > 2025:
                    continue
                usd_gbp = safe_decimal(rate_str)
                if usd_gbp and usd_gbp > 0 and dt not in existing_dates:
                    er = ExchangeRate(
                        date=dt,
                        usd_gbp=usd_gbp,
                        description=f"BoE daily spot {dt}",
                        notes="Uploaded from BoE CSV"
                    )
                    db.session.add(er)
                    inserted += 1
                    existing_dates.add(dt)
            except ValueError:
                continue
        db.session.commit()
        flash(f"Inserted {inserted} daily rates from BoE CSV", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error processing CSV: {str(e)}", "danger")
    return redirect(url_for("index_full"))

@app.route("/")
def index():
    rates = load_rates_sorted()
    lots = []
    for v in Vesting.query.order_by(Vesting.date.asc(), Vesting.id.asc()).all():
        net = safe_decimal(v.net_shares) if v.net_shares is not None else (safe_decimal(v.shares_vested) - safe_decimal(v.shares_sold or 0))
        if net <= 0: continue
        usd_total = safe_decimal(v.total_usd) if v.total_usd else (safe_decimal(v.price_usd) * safe_decimal(v.shares_vested) if v.price_usd else Decimal("0"))
        exc = safe_decimal(v.exchange_rate) if v.exchange_rate else (get_rate_for_date(v.date, rates) or Decimal("1"))
        if exc == 0: exc = Decimal("1")
        total_gbp = usd_total / exc
        avg_cost = (total_gbp / net) if net != 0 else Decimal("0")
        lots.append({"entry": f"V:{v.id}", "date": v.date, "source":"RSU", "remaining": float(net), "avg_cost": float(q2(avg_cost)), "tooltip": f"RSU {v.date}: USD {usd_total} / rate {exc} → £{q2(total_gbp)}; per-share £{q2(avg_cost)}"})
    for p in ESPPPurchase.query.order_by(ESPPPurchase.date.asc(), ESPPPurchase.id.asc()).all():
        shares = safe_decimal(p.shares_retained)
        if shares <= 0: continue
        purchase_price_usd = safe_decimal(p.purchase_price_usd)
        exc = safe_decimal(p.exchange_rate) if p.exchange_rate else (get_rate_for_date(p.date, rates) or Decimal("1"))
        if exc == 0: exc = Decimal("1")
        usd_total = purchase_price_usd * shares
        purchase_gbp = usd_total / exc
        paye = safe_decimal(p.paye_tax_gbp) if p.paye_tax_gbp else Decimal("0")
        chosen_total_gbp = purchase_gbp + (paye if p.discount_taxed_paye else Decimal("0"))
        avg_cost = (chosen_total_gbp / shares) if shares != 0 else Decimal("0")
        lots.append({"entry": f"E:{p.id}", "date": p.date, "source":"ESPP", "remaining": float(shares), "avg_cost": float(q2(avg_cost)), "tooltip": f"ESPP {p.date}: USD {usd_total} / rate {exc} → purchase £{q2(purchase_gbp)}; PAYE £{q2(paye)}; per-share £{q2(avg_cost)}"})
    rates_q = ExchangeRate.query.order_by(ExchangeRate.date.asc()).all()
    return render_template_string(INDEX_HTML, computed_lots=lots, rates=rates_q)

@app.route("/index-full")
def index_full():
    vestings = Vesting.query.order_by(Vesting.date.asc()).all()
    espps = ESPPPurchase.query.order_by(ESPPPurchase.date.asc()).all()
    sales = SaleInput.query.order_by(SaleInput.date.asc()).all()
    relevant_dates = set()
    for v in vestings:
        relevant_dates.add(v.date)
    for e in espps:
        relevant_dates.add(e.date)
    for s in sales:
        relevant_dates.add(s.date)
    rates = ExchangeRate.query.filter(ExchangeRate.date.in_(list(relevant_dates))).order_by(ExchangeRate.date.asc()).all()
    return render_template_string(INDEX_FULL_HTML, rates=rates, vestings=vestings, espps=espps, sales=sales)

# ExchangeRate CRUD
@app.route("/add_rate", methods=["POST"])
def add_rate():
    d = to_date(request.form.get("date"))
    rate = safe_decimal(request.form.get("rate"))
    if not d or rate <= 0: flash("Invalid rate", "danger"); return redirect(url_for("index_full"))
    db.session.add(ExchangeRate(date=d, usd_gbp=rate, description="", notes=""))
    db.session.commit(); flash("Rate added", "success"); return redirect(url_for("index_full"))

@app.route("/delete_rate/<int:id>")
def delete_rate(id):
    r = ExchangeRate.query.get(id)
    if r: db.session.delete(r); db.session.commit(); flash("Rate deleted", "info")
    return redirect(url_for("index_full"))

@app.route("/edit_rate/<int:id>", methods=["GET","POST"])
def edit_rate(id):
    r = ExchangeRate.query.get_or_404(id)
    if request.method=="POST":
        r.date = to_date(request.form.get("date")); r.usd_gbp = safe_decimal(request.form.get("rate"))
        db.session.add(r); db.session.commit(); flash("Rate updated","success"); return redirect(url_for("index_full"))
    return f"<form method='post'><input type='date' name='date' value='{r.date}' required><input type='number' step='0.000001' name='rate' value='{r.usd_gbp}' required><button>Save</button></form>"

# Vesting CRUD
@app.route("/add_vesting", methods=["POST"])
def add_vesting():
    d = to_date(request.form.get("date"))
    shares = safe_decimal(request.form.get("shares_vested"))
    price = request.form.get("price_usd")
    sold = safe_decimal(request.form.get("shares_sold") or "0")
    if not d or shares <= 0: flash("Invalid vesting", "danger"); return redirect(url_for("index_full"))
    v = Vesting(date=d, shares_vested=shares, price_usd=safe_decimal(price) if price else None, shares_sold=sold, net_shares=(shares - sold))
    db.session.add(v); db.session.commit(); flash("Vesting added","success")
    # Trigger partial recalc for sales after this date
    recalc_all(sale_filter=d.isoformat())
    return redirect(url_for("index_full"))

@app.route("/edit_vesting/<int:id>", methods=["GET","POST"])
def edit_vesting(id):
    v = Vesting.query.get_or_404(id)
    if request.method=="POST":
        v.date = to_date(request.form.get("date")); v.shares_vested = safe_decimal(request.form.get("shares_vested"))
        v.price_usd = safe_decimal(request.form.get("price_usd")) if request.form.get("price_usd") else None
        v.shares_sold = safe_decimal(request.form.get("shares_sold") or "0"); v.net_shares = v.shares_vested - v.shares_sold
        old_date = v.date  # Before update, but since date might change, use new date for filter
        db.session.add(v); db.session.commit(); flash("Vesting updated","success")
        # Partial recalc from min(old_date, new_date)
        new_date = v.date
        recalc_date = min(old_date, new_date).isoformat() if old_date and new_date else None
        if recalc_date:
            recalc_all(sale_filter=recalc_date)
        return redirect(url_for("index_full"))
    return f"<form method='post'><input type='date' name='date' value='{v.date}' required><input type='number' step='0.000001' name='shares_vested' value='{v.shares_vested}' required><input type='number' step='0.000001' name='price_usd' value='{v.price_usd or ''}'><input type='number' step='0.000001' name='shares_sold' value='{v.shares_sold or 0}'><button>Save</button></form>"

@app.route("/delete_vesting/<int:id>")
def delete_vesting(id):
    v = Vesting.query.get(id)
    if v: db.session.delete(v); db.session.commit(); flash("Vesting deleted","info")
    return redirect(url_for("index_full"))

# ESPP CRUD
@app.route("/add_espp", methods=["POST"])
def add_espp():
    d = to_date(request.form.get("date"))
    shares = safe_decimal(request.form.get("shares_retained"))
    purchase_str = request.form.get("purchase_price_usd")
    market_str = request.form.get("market_price_usd")
    paye = request.form.get("paye_tax_gbp")
    exch = request.form.get("exchange_rate")
    discount_taxed = True if request.form.get("discount_taxed")=="on" else False
    if not d or shares <= 0:
        flash("Invalid ESPP: Date and positive shares required","danger"); return redirect(url_for("index_full"))
    purchase = safe_decimal(purchase_str) if purchase_str else None
    market = safe_decimal(market_str) if market_str else None
    discount = Decimal("0")
    qualifying = True  # Default for HTML, user can edit later
    if market and purchase and market > 0 and purchase < market:
        discount = ((market - purchase) / market) * 100
        if discount > 15:
            flash(f"Error: ESPP discount {q2(discount)}% > 15%. This plan may not qualify for relief. Set qualifying=False in edit mode or consult HMRC. Submission blocked for accuracy.", "error")
            return redirect(url_for("index_full"))
        qualifying = discount <= 15
        if not qualifying:
            flash(f"Warning: ESPP discount {q2(discount)}% > 15%. Full market value treated as income; ensure PAYE is flagged.", "warning")
    p = ESPPPurchase(date=d, shares_retained=shares, purchase_price_usd=purchase, market_price_usd=market, discount=discount, paye_tax_gbp=safe_decimal(paye) if paye else None, exchange_rate=safe_decimal(exch) if exch else None, discount_taxed_paye=discount_taxed, qualifying=qualifying)
    db.session.add(p); db.session.commit(); flash("ESPP added","success")
    # Trigger partial recalc
    recalc_all(sale_filter=d.isoformat())
    return redirect(url_for("index_full"))

@app.route("/edit_espp/<int:id>", methods=["GET","POST"])
def edit_espp(id):
    p = ESPPPurchase.query.get_or_404(id)
    if request.method=="POST":
        new_shares = safe_decimal(request.form.get("shares_retained"))
        if new_shares <= 0:
            flash("Invalid: Positive shares required","danger")
            return redirect(url_for("index_full"))
        p.date = to_date(request.form.get("date"))
        p.shares_retained = new_shares
        purchase_str = request.form.get("purchase_price_usd")
        market_str = request.form.get("market_price_usd")
        purchase = safe_decimal(purchase_str) if purchase_str else None
        market = safe_decimal(market_str) if market_str else None
        discount = Decimal("0")
        qualifying = True  # Default, but check if form has it; for HTML, assume user sets
        if market and purchase and market > 0 and purchase < market:
            discount = ((market - purchase) / market) * 100
            if discount > 15:
                flash(f"Error: ESPP discount {q2(discount)}% > 15%. Set qualifying=False or adjust prices for submission.", "error")
                return redirect(url_for("index_full"))
            qualifying = discount <= 15
            if not qualifying:
                flash(f"Warning: ESPP discount {q2(discount)}% > 15%. Full market value treated as income; ensure PAYE flagged.", "warning")
        p.purchase_price_usd = purchase
        p.market_price_usd = market
        p.discount = discount
        p.qualifying = qualifying
        p.paye_tax_gbp = safe_decimal(request.form.get("paye_tax_gbp")) if request.form.get("paye_tax_gbp") else None
        p.exchange_rate = safe_decimal(request.form.get("exchange_rate")) if request.form.get("exchange_rate") else None
        p.discount_taxed_paye = True if request.form.get("discount_taxed")=="on" else False
        old_date = p.date
        db.session.add(p); db.session.commit(); flash("ESPP updated","success")
        new_date = p.date
        recalc_date = min(old_date, new_date).isoformat() if old_date and new_date else None
        if recalc_date:
            recalc_all(sale_filter=recalc_date)
        return redirect(url_for("index_full"))
    return f"<form method='post'><input type='date' name='date' value='{p.date}' required><input type='number' step='0.000001' name='shares_retained' value='{p.shares_retained}' required><input type='number' step='0.000001' name='purchase_price_usd' value='{p.purchase_price_usd or ''}'><input type='number' step='0.000001' name='market_price_usd' value='{p.market_price_usd or ''}'><input type='number' step='0.000001' name='paye_tax_gbp' value='{p.paye_tax_gbp or ''}'><input type='number' step='0.000001' name='exchange_rate' value='{p.exchange_rate or ''}'><label><input type='checkbox' name='discount_taxed' {'checked' if p.discount_taxed_paye else ''}> Discount taxed</label><button>Save</button></form>"

@app.route("/delete_espp/<int:id>")
def delete_espp(id):
    p = ESPPPurchase.query.get(id)
    if p: db.session.delete(p); db.session.commit(); flash("ESPP deleted","info")
    return redirect(url_for("index_full"))

# Sale CRUD
@app.route("/add_sale", methods=["POST"])
def add_sale():
    d = to_date(request.form.get("date"))
    shares = safe_decimal(request.form.get("shares_sold"))
    price = request.form.get("sale_price_usd")
    exch = request.form.get("exchange_rate")
    if not d or shares <= 0 or not price:
        flash("Invalid sale: Date, positive shares, and price required","danger"); return redirect(url_for("index_full"))
    s = SaleInput(date=d, shares_sold=shares, sale_price_usd=safe_decimal(price), exchange_rate=safe_decimal(exch) if exch else None)
    db.session.add(s); db.session.commit(); flash("Sale added","success")
    # Trigger partial recalc for this sale
    recalc_all(sale_filter=[s.id])
    return redirect(url_for("index_full"))

@app.route("/edit_sale/<int:id>", methods=["GET","POST"])
def edit_sale(id):
    s = SaleInput.query.get_or_404(id)
    if request.method=="POST":
        new_date = to_date(request.form.get("date"))
        new_shares = safe_decimal(request.form.get("shares_sold"))
        price = request.form.get("sale_price_usd")
        if not new_date or new_shares <= 0 or not price:
            flash("Invalid: Date, positive shares, and price required","danger")
            return redirect(url_for("index_full"))
        s.date = new_date
        s.shares_sold = new_shares
        s.sale_price_usd = safe_decimal(price)
        s.exchange_rate = safe_decimal(request.form.get("exchange_rate")) if request.form.get("exchange_rate") else None
        db.session.add(s); db.session.commit(); flash("Sale updated","success")
        # Recompute this sale
        recalc_all(sale_filter=[s.id])
        return redirect(url_for("index_full"))
    return f"<form method='post'><input type='date' name='date' value='{s.date}' required><input type='number' step='0.000001' name='shares_sold' value='{s.shares_sold}' required><input type='number' step='0.000001' name='sale_price_usd' value='{s.sale_price_usd}' required><input type='number' step='0.000001' name='exchange_rate' value='{s.exchange_rate or ''}'><button>Save</button></form>"

@app.route("/delete_sale/<int:id>")
def delete_sale(id):
    s = SaleInput.query.get(id)
    if s: db.session.delete(s); db.session.commit(); flash("Sale deleted","info")
    return redirect(url_for("index_full"))

# Carry-forward loss CRUD
@app.route("/add_carry_loss", methods=["POST"])
def add_carry_loss():
    tax_year = int(request.form.get("tax_year"))
    amount = safe_decimal(request.form.get("amount"))
    notes = request.form.get("notes", "")
    if not tax_year or amount is None:
        flash("Invalid carry-forward loss", "danger")
        return redirect(url_for("index_full"))
    # Update or add
    loss = CarryForwardLoss.query.filter_by(tax_year=tax_year).first()
    if loss:
        loss.amount = amount
        loss.notes = notes
    else:
        loss = CarryForwardLoss(tax_year=tax_year, amount=amount, notes=notes)
        db.session.add(loss)
    db.session.commit()
    flash(f"Carry-forward loss for {tax_year} updated to £{q2(amount)}", "success")
    return redirect(url_for("index_full"))

@app.route("/delete_carry_loss/<int:tax_year>")
def delete_carry_loss(tax_year):
    loss = CarryForwardLoss.query.filter_by(tax_year=tax_year).first()
    if loss:
        db.session.delete(loss)
        db.session.commit()
        flash(f"Carry-forward loss for {tax_year} deleted", "info")
    return redirect(url_for("index_full"))

# Recalculate & audit
@app.route("/recalculate")
def recalculate():
    explain_flag = True if request.args.get("explain") == "1" else False
    ty = request.args.get("tax_year")
    tax_year = int(ty) if ty and ty.isdigit() else None
    sale_filter = request.args.get("sale_id")  # Optional for partial
    if sale_filter:
        sale_filter = [int(sale_filter)]
    res = recalc_all(explain=explain_flag, tax_year_filter=tax_year, sale_filter=sale_filter)
    if res.get("errors_present"): flash("Recalc completed but errors detected. See Audit.", "danger")
    else: flash("Recalc completed and snapshots stored.", "success")
    return redirect(url_for("index"))

@app.route("/api/recalc_partial/<int:sale_id>", methods=["POST"])
def recalc_partial(sale_id):
    """Recompute only for a specific sale."""
    res = recalc_all(sale_filter=[sale_id])
    return jsonify(res)

@app.route("/audit")
def audit():
    ty = request.args.get("tax_year")
    sel_tax_year = int(ty) if ty and ty.isdigit() else None
    tax_years = list(range(datetime.utcnow().year - 9, datetime.utcnow().year + 1))
    return render_template_string(AUDIT_DASH_HTML, tax_years=tax_years, sel_tax_year=sel_tax_year)

# CSV exports
@app.route("/download/<kind>")
def download_csv(kind):
    tax_year_q = request.args.get("tax_year")
    today = datetime.utcnow().date()
    default_tax_year = today.year if today >= date(today.year,4,6) else today.year - 1
    tax_year = int(tax_year_q) if tax_year_q and tax_year_q.isdigit() else default_tax_year
    si = io.StringIO(); cw = csv.writer(si)
    if kind == "disposals":
        rows = DisposalResult.query.order_by(DisposalResult.sale_date.asc(), DisposalResult.id.asc()).all()
        cw.writerow(["disposal_id","sale_date","sale_input_id","matched_date","matching_type","matched_shares","avg_cost_gbp","proceeds_gbp","cost_basis_gbp","gain_gbp","cgt_due_gbp"])
        for r in rows:
            cw.writerow([r.id, r.sale_date.isoformat() if r.sale_date else "", r.sale_input_id, r.matched_date.isoformat() if r.matched_date else "", r.matching_type, float(r.matched_shares or 0), float(q2(safe_decimal(r.avg_cost_gbp))), float(q2(safe_decimal(r.proceeds_gbp))), float(q2(safe_decimal(r.cost_basis_gbp))), float(q2(safe_decimal(r.gain_gbp))), float(q2(safe_decimal(r.cgt_due_gbp)))])
        buf = io.BytesIO(); buf.write(si.getvalue().encode()); buf.seek(0); return send_file(buf, mimetype="text/csv", as_attachment=True, download_name="disposals.csv")
    elif kind == "pool":
        snaps = PoolSnapshot.query.order_by(PoolSnapshot.timestamp.desc()).limit(50).all()
        cw.writerow(["timestamp","tax_year","total_shares","total_cost_gbp","avg_cost_gbp","snapshot_json"])
        for s in snaps:
            cw.writerow([s.timestamp.isoformat(), s.tax_year if s.tax_year else "", float(q6(s.total_shares or 0)), float(q2(s.total_cost_gbp or 0)), float(q2(s.avg_cost_gbp or 0)), s.snapshot_json])
        buf = io.BytesIO(); buf.write(si.getvalue().encode()); buf.seek(0); return send_file(buf, mimetype="text/csv", as_attachment=True, download_name="pool_snapshots.csv")
    elif kind == "summary":
        tax_start = date(tax_year,4,6); tax_end = date(tax_year+1,4,5)
        disposals = DisposalResult.query.filter(DisposalResult.sale_date >= tax_start, DisposalResult.sale_date <= tax_end).order_by(DisposalResult.sale_date.asc()).all()
        total_proceeds = sum([safe_decimal(r.proceeds_gbp or 0) for r in disposals])
        total_cost = sum([safe_decimal(r.cost_basis_gbp or 0) for r in disposals])
        total_gain = sum([safe_decimal(r.gain_gbp or 0) for r in disposals])
        pos = sum([safe_decimal(r.gain_gbp) for r in disposals if safe_decimal(r.gain_gbp) > 0])
        neg = sum([abs(safe_decimal(r.gain_gbp)) for r in disposals if safe_decimal(r.gain_gbp) < 0])
        net_gain = pos - neg
        if net_gain < 0: net_gain = Decimal("0")
        sa = Setting.query.get("CGT_Allowance"); sb = Setting.query.get("CGT_Rate")
        cgt_allowance = safe_decimal(sa.value) if sa and safe_decimal(sa.value) > 0 and tax_year < 2024 else get_aea(tax_year)
        cgt_rate_pct = safe_decimal(sb.value) if sb else Decimal("20")
        cgt_rate = cgt_rate_pct / Decimal("100")
        taxable = net_gain - cgt_allowance
        if taxable < 0: taxable = Decimal("0")
        estimated_cgt = q2(taxable * cgt_rate)
        cw.writerow(["tax_year_start","tax_year_end","cgt_allowance_gbp","cgt_rate_percent","total_disposals","total_proceeds","total_cost","total_gain","net_gain","taxable_after_allowance","estimated_cgt"])
        cw.writerow([tax_start.isoformat(), tax_end.isoformat(), float(q2(cgt_allowance)), float(q2(cgt_rate_pct)), len(disposals), float(q2(total_proceeds)), float(q2(total_cost)), float(q2(total_gain)), float(q2(net_gain)), float(q2(taxable)), float(q2(estimated_cgt))])
        buf = io.BytesIO(); buf.write(si.getvalue().encode()); buf.seek(0); return send_file(buf, mimetype="text/csv", as_attachment=True, download_name=f"summary_{tax_year}.csv")
    else:
        return "Unknown kind", 404

@app.route("/clear_steps", methods=["POST"])
def clear_steps():
    CalculationStep.query.delete(); CalculationDetail.query.delete(); db.session.commit(); flash("Cleared steps and details", "info"); return redirect(url_for("audit"))

# ---------- API endpoints for UI ----------
@app.route("/api/transactions")
def api_transactions():
    ty = request.args.get("tax_year")
    matching = request.args.get("matching")
    q = request.args.get("q")
    limit = int(request.args.get("limit") or 500)
    items = []
    query = DisposalResult.query.order_by(DisposalResult.sale_date.asc(), DisposalResult.id.asc())
    rows = query.limit(5000).all()

    for r in rows:
        calc = {}
        if r.calculation_json:
            try:
                calc = json.loads(r.calculation_json)
            except Exception:
                calc = {}
        pool_rsu_pct = 0.0
        pool_espp_pct = 0.0
        frag_idx = None
        if calc.get("numeric_trace") and calc["numeric_trace"].get("fragment_index"):
            frag_idx = calc["numeric_trace"]["fragment_index"]
        item = {
            "disposal_id": r.id,
            "sale_date": r.sale_date.isoformat() if r.sale_date else None,
            "sale_input_id": r.sale_input_id,
            "fragment_index": frag_idx or 1,
            "matched_shares": float(q6(safe_decimal(r.matched_shares or 0))),
            "matching_type": r.matching_type,
            "lot_entry": calc.get("inputs",{}).get("lot",{}).get("entry") if calc.get("inputs") else None,
            "matched_date": r.matched_date.isoformat() if r.matched_date else None,
            "source": calc.get("inputs",{}).get("lot",{}).get("source") if calc.get("inputs") else None,
            "rate_used": calc.get("inputs",{}).get("sale_rate_used") if calc.get("inputs") else None,
            "avg_cost_gbp": float(q2(safe_decimal(r.avg_cost_gbp or 0))),
            "proceeds_gbp": float(q2(safe_decimal(r.proceeds_gbp or 0))),
            "cost_basis_gbp": float(q2(safe_decimal(r.cost_basis_gbp or 0))),
            "gain_gbp": float(q2(safe_decimal(r.gain_gbp or 0))),
            "pool_rsu_pct": pool_rsu_pct,
            "pool_espp_pct": pool_espp_pct,
            "calculation_snippet": (calc.get("equations")[:3] if calc.get("equations") else [])
        }
        items.append(item)

    if matching:
        items = [i for i in items if i.get("matching_type") == matching]
    if q:
        ql = q.lower()
        items = [i for i in items if ql in (str(i.get("lot_entry") or "")).lower() or ql in (str(i.get("sale_input_id") or ""))]
    items = items[:limit]
    return jsonify({"items": items, "count": len(items)})

@app.route("/api/transaction/<int:id>")
def api_transaction(id):
    r = DisposalResult.query.get_or_404(id)
    calc = {}
    if r.calculation_json:
        try:
            calc = json.loads(r.calculation_json)
        except Exception:
            calc = {"raw": r.calculation_json}
    details = CalculationDetail.query.filter_by(disposal_id=r.id).order_by(CalculationDetail.created_at.asc()).all()
    details_list = [{"equations": d.equations, "explanation": d.explanation} for d in details]
    return jsonify({
        "disposal_id": r.id,
        "sale_date": r.sale_date.isoformat() if r.sale_date else None,
        "sale_input_id": r.sale_input_id,
        "matched_date": r.matched_date.isoformat() if r.matched_date else None,
        "matching_type": r.matching_type,
        "matched_shares": str(r.matched_shares),
        "avg_cost_gbp": str(r.avg_cost_gbp),
        "proceeds_gbp": str(r.proceeds_gbp),
        "cost_basis_gbp": str(r.cost_basis_gbp),
        "gain_gbp": str(r.gain_gbp),
        "cgt_due_gbp": str(r.cgt_due_gbp),
        "calculation": calc,
        "details": details_list
    })

@app.route("/api/snapshot/<int:year>")
def api_snapshot(year):
    snapshot = PoolSnapshot.query.filter_by(tax_year=year).order_by(PoolSnapshot.timestamp.desc()).first()
    if not snapshot:
        return jsonify({"error": "No snapshot for year"}), 404
    return jsonify({
        "timestamp": snapshot.timestamp.isoformat(),
        "tax_year": snapshot.tax_year,
        "total_shares": float(q6(safe_decimal(snapshot.total_shares or 0))),
        "total_cost_gbp": float(q2(safe_decimal(snapshot.total_cost_gbp or 0))),
        "avg_cost_gbp": float(q2(safe_decimal(snapshot.avg_cost_gbp or 0))),
        "snapshot_json": snapshot.snapshot_json
    })

@app.route("/api/settings", methods=["POST"])
def api_update_settings():
    key = request.json.get("key")
    value = request.json.get("value")
    if not key or value is None:
        return jsonify({"error": "Missing key or value"}), 400
    setting = Setting.query.get(key)
    if setting:
        setting.value = str(value)
    else:
        setting = Setting(key=key, value=str(value))
        db.session.add(setting)
    db.session.commit()
    return jsonify({"success": True, "key": key, "value": value})

@app.route("/api/summary/<int:year>")
def api_summary(year):
    tax_start = date(year, 4, 6)
    tax_end = date(year + 1, 4, 5)
    disposals = DisposalResult.query.filter(
        DisposalResult.sale_date >= tax_start,
        DisposalResult.sale_date <= tax_end
    ).order_by(DisposalResult.sale_date.asc()).all()
    
    total_proceeds = sum([safe_decimal(r.proceeds_gbp or 0) for r in disposals])
    total_cost = sum([safe_decimal(r.cost_basis_gbp or 0) for r in disposals])
    total_gain = sum([safe_decimal(r.gain_gbp or 0) for r in disposals])
    pos = sum([safe_decimal(r.gain_gbp) for r in disposals if safe_decimal(r.gain_gbp) > 0])
    neg = sum([abs(safe_decimal(r.gain_gbp)) for r in disposals if safe_decimal(r.gain_gbp) < 0])
    net_gain = pos - neg
    if net_gain < 0:
        net_gain = Decimal("0")
    
    # Apply carry-forward losses from previous years
    carry_forward_losses = CarryForwardLoss.query.filter(CarryForwardLoss.tax_year < year).all()
    total_carry_forward_loss = sum(safe_decimal(loss.amount) for loss in carry_forward_losses)
    
    # Subtract carry-forward losses from net gain before applying allowance
    net_gain_after_losses = max(Decimal("0"), net_gain - total_carry_forward_loss)
    
    sa = Setting.query.get("CGT_Allowance")
    sc = Setting.query.get("NonSavingsIncome")
    sd = Setting.query.get("BasicBandThreshold")
    cgt_allowance = safe_decimal(sa.value) if sa and safe_decimal(sa.value) > 0 and year < 2024 else get_aea(year)
    non_savings_income = safe_decimal(sc.value) if sc else Decimal("0")
    basic_threshold = safe_decimal(sd.value) if sd else Decimal("37700")
    basic_band_available = max(Decimal("0"), basic_threshold - non_savings_income)
    taxable_gain = net_gain_after_losses - cgt_allowance
    if taxable_gain < 0:
        taxable_gain = Decimal("0")
    basic_taxable = min(taxable_gain, basic_band_available)
    higher_taxable = taxable_gain - basic_taxable
    estimated_cgt = q2(basic_taxable * Decimal("0.10") + higher_taxable * Decimal("0.20"))
    
    return jsonify({
        "tax_year_start": tax_start.isoformat(),
        "tax_year_end": tax_end.isoformat(),
        "cgt_allowance_gbp": float(q2(cgt_allowance)),
        "carry_forward_loss_gbp": float(q2(total_carry_forward_loss)),
        "net_gain_after_losses": float(q2(net_gain_after_losses)),
        "non_savings_income": float(q2(non_savings_income)),
        "basic_threshold": float(q2(basic_threshold)),
        "basic_band_available": float(q2(basic_band_available)),
        "total_disposals": len(disposals),
        "total_proceeds": float(q2(total_proceeds)),
        "total_cost": float(q2(total_cost)),
        "total_gain": float(q2(total_gain)),
        "pos": float(q2(pos)),
        "neg": float(q2(neg)),
        "net_gain": float(q2(net_gain)),
        "taxable_after_allowance": float(q2(taxable_gain)),
        "basic_taxable_gain": float(q2(basic_taxable)),
        "higher_taxable_gain": float(q2(higher_taxable)),
        "estimated_cgt": float(q2(estimated_cgt))
    })

@app.route("/api/tax_years", methods=["GET"])
def api_tax_years():
    """Return unique tax years from existing data."""
    from collections import defaultdict
    years = set()
    # From sales
    sales = SaleInput.query.all()
    for s in sales:
        ty = s.date.year if s.date >= date(s.date.year, 4, 6) else s.date.year - 1
        years.add(ty)
    # From disposals (if no sales)
    disposals = DisposalResult.query.all()
    for d in disposals:
        if d.sale_date:
            ty = d.sale_date.year if d.sale_date >= date(d.sale_date.year, 4, 6) else d.sale_date.year - 1
            years.add(ty)
    return jsonify(sorted(list(years)))

@app.route("/api/export/sa108/<int:year>")
def api_export_sa108(year):
    tax_start = date(year, 4, 6)
    tax_end = date(year + 1, 4, 5)
    disposals = DisposalResult.query.filter(
        DisposalResult.sale_date >= tax_start,
        DisposalResult.sale_date <= tax_end
    ).order_by(DisposalResult.sale_date.asc()).all()
    
    if not disposals:
        return jsonify({"error": "No disposals for the tax year"}), 404
    
    # Compute aggregates similar to summary
    total_proceeds = sum([safe_decimal(r.proceeds_gbp or 0) for r in disposals])
    total_cost = sum([safe_decimal(r.cost_basis_gbp or 0) for r in disposals])
    total_gain = sum([safe_decimal(r.gain_gbp or 0) for r in disposals])
    pos_gains = sum([safe_decimal(r.gain_gbp) for r in disposals if safe_decimal(r.gain_gbp) > 0])
    losses = sum([abs(safe_decimal(r.gain_gbp)) for r in disposals if safe_decimal(r.gain_gbp) < 0])
    net_gain = pos_gains - losses
    if net_gain < 0:
        net_gain = Decimal("0")
        allowable_loss = abs(net_gain)
        net_gain = Decimal("0")
    else:
        allowable_loss = Decimal("0")
    
    # Carry-forward losses
    carry_forward_losses = CarryForwardLoss.query.filter(CarryForwardLoss.tax_year < year).all()
    total_carry_forward_loss = sum(safe_decimal(loss.amount) for loss in carry_forward_losses)
    net_gain_after_losses = max(Decimal("0"), net_gain - total_carry_forward_loss)
    
    # Allowance and tax
    sa = Setting.query.get("CGT_Allowance")
    cgt_allowance = safe_decimal(sa.value) if sa and safe_decimal(sa.value) > 0 and year < 2024 else get_aea(year)
    chargeable_gain = max(Decimal("0"), net_gain_after_losses - cgt_allowance)
    
    # Simplified disposals list for SA108 Box 3 (UK assets)
    uk_disposals = []  # Assuming all are shares in UK-listed companies or treated as such
    for r in disposals:
        if safe_decimal(r.gain_gbp) != 0:  # Only include with gain/loss
            uk_disposals.append({
                "date": r.sale_date.isoformat() if r.sale_date else None,
                "description": f"Shares disposal (match: {r.matching_type})",
                "proceeds": float(q2(safe_decimal(r.proceeds_gbp or 0))),
                "cost": float(q2(safe_decimal(r.cost_basis_gbp or 0))),
                "gain_loss": float(q2(safe_decimal(r.gain_gbp or 0)))
            })
    
    sa108_data = {
        "tax_year": year,
        "tax_year_start": tax_start.isoformat(),
        "tax_year_end": tax_end.isoformat(),
        "total_proceeds": float(q2(total_proceeds)),
        "total_costs": float(q2(total_cost)),
        "total_gains": float(q2(pos_gains)),
        "total_losses": float(q2(losses)),
        "net_gain": float(q2(net_gain)),
        "allowable_loss": float(q2(allowable_loss)),
        "carry_forward_loss_used": float(q2(total_carry_forward_loss)),
        "net_gain_after_losses": float(q2(net_gain_after_losses)),
        "cgt_allowance_used": float(q2(min(cgt_allowance, net_gain_after_losses))),
        "chargeable_gain": float(q2(chargeable_gain)),
        "disposals": uk_disposals  # For Box 3 details
    }
    
    return jsonify(sa108_data)

# Helper to serialize model to dict
def model_to_dict(model):
    if isinstance(model, Vesting):
        return {
            'id': model.id,
            'date': model.date.isoformat() if model.date else None,
            'shares_vested': float(model.shares_vested) if model.shares_vested else None,
            'price_usd': float(model.price_usd) if model.price_usd else None,
            'total_usd': float(model.total_usd) if model.total_usd else None,
            'exchange_rate': float(model.exchange_rate) if model.exchange_rate else None,
            'total_gbp': float(model.total_gbp) if model.total_gbp else None,
            'tax_paid_gbp': float(model.tax_paid_gbp) if model.tax_paid_gbp else None,
            'incidental_costs_gbp': float(model.incidental_costs_gbp) if model.incidental_costs_gbp else None,
            'shares_sold': float(model.shares_sold) if model.shares_sold else None,
            'net_shares': float(model.net_shares) if model.net_shares else None,
        }
    elif isinstance(model, ESPPPurchase):
        return {
            'id': model.id,
            'date': model.date.isoformat() if model.date else None,
            'shares_retained': float(model.shares_retained) if model.shares_retained else None,
            'purchase_price_usd': float(model.purchase_price_usd) if model.purchase_price_usd else None,
            'market_price_usd': float(model.market_price_usd) if model.market_price_usd else None,
            'discount': float(model.discount) if model.discount else None,
            'exchange_rate': float(model.exchange_rate) if model.exchange_rate else None,
            'total_gbp': float(model.total_gbp) if model.total_gbp else None,
            'discount_taxed_paye': model.discount_taxed_paye,
            'paye_tax_gbp': float(model.paye_tax_gbp) if model.paye_tax_gbp else None,
            'qualifying': model.qualifying,
            'incidental_costs_gbp': float(model.incidental_costs_gbp) if model.incidental_costs_gbp else None,
            'notes': model.notes,
        }
    elif isinstance(model, SaleInput):
        return {
            'id': model.id,
            'date': model.date.isoformat() if model.date else None,
            'shares_sold': float(model.shares_sold) if model.shares_sold else None,
            'sale_price_usd': float(model.sale_price_usd) if model.sale_price_usd else None,
            'exchange_rate': float(model.exchange_rate) if model.exchange_rate else None,
            'incidental_costs_gbp': float(model.incidental_costs_gbp) if model.incidental_costs_gbp else None,
        }
    return {}

# ---------- CRUD APIs for Vestings ----------
@app.route('/api/vestings', methods=['POST'])
def create_vesting():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    try:
        shares_vested = safe_decimal(data.get('shares_vested'))
        if shares_vested <= 0:
            raise ValueError("Shares vested must be positive")
        date_val = to_date(data.get('date'))
        if not date_val:
            raise ValueError("Valid date required")
        v = Vesting(
            date=date_val,
            shares_vested=shares_vested,
            price_usd=safe_decimal(data.get('price_usd')),
            shares_sold=safe_decimal(data.get('shares_sold', 0)),
            total_usd=safe_decimal(data.get('total_usd')),
            exchange_rate=safe_decimal(data.get('exchange_rate')),
            total_gbp=safe_decimal(data.get('total_gbp')),
            tax_paid_gbp=safe_decimal(data.get('tax_paid_gbp')),
            incidental_costs_gbp=safe_decimal(data.get('incidental_costs_gbp', 0)),
            net_shares=safe_decimal(data.get('net_shares'))
        )
        db.session.add(v)
        db.session.commit()
        # Trigger partial recalc
        recalc_all(sale_filter=date_val.isoformat())
        return jsonify(model_to_dict(v)), 201
    except ValueError as ve:
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/vestings', methods=['GET'])
def get_vestings():
    vestings = Vesting.query.order_by(Vesting.date.asc()).all()
    return jsonify([model_to_dict(v) for v in vestings])

@app.route('/api/vestings/<int:id>', methods=['PUT'])
def update_vesting(id):
    v = Vesting.query.get_or_404(id)
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    try:
        new_date = to_date(data.get('date', v.date))
        if not new_date:
            raise ValueError("Valid date required")
        new_shares = safe_decimal(data.get('shares_vested', v.shares_vested))
        if new_shares <= 0:
            raise ValueError("Shares vested must be positive")
        v.date = new_date
        v.shares_vested = new_shares
        v.price_usd = safe_decimal(data.get('price_usd', v.price_usd))
        v.shares_sold = safe_decimal(data.get('shares_sold', v.shares_sold))
        v.total_usd = safe_decimal(data.get('total_usd', v.total_usd))
        v.exchange_rate = safe_decimal(data.get('exchange_rate', v.exchange_rate))
        v.total_gbp = safe_decimal(data.get('total_gbp', v.total_gbp))
        v.tax_paid_gbp = safe_decimal(data.get('tax_paid_gbp', v.tax_paid_gbp))
        v.incidental_costs_gbp = safe_decimal(data.get('incidental_costs_gbp', v.incidental_costs_gbp))
        v.net_shares = safe_decimal(data.get('net_shares', v.net_shares))
        db.session.commit()
        # Partial recalc from new_date
        recalc_all(sale_filter=new_date.isoformat())
        return jsonify(model_to_dict(v))
    except ValueError as ve:
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/vestings/<int:id>', methods=['DELETE'])
def api_delete_vesting(id):
    v = Vesting.query.get_or_404(id)
    db.session.delete(v)
    db.session.commit()
    return jsonify({'message': 'Vesting deleted'})

# ---------- CRUD APIs for ESPP ----------
@app.route('/api/espp', methods=['POST'])
def create_espp():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    try:
        shares_retained = safe_decimal(data.get('shares_retained'))
        if shares_retained <= 0:
            raise ValueError("Shares retained must be positive")
        date_val = to_date(data.get('date'))
        if not date_val:
            raise ValueError("Valid date required")
        purchase_price = safe_decimal(data.get('purchase_price_usd', 0))
        market_price = safe_decimal(data.get('market_price_usd', 0))
        qualifying = data.get('qualifying', True)
        if market_price > 0 and purchase_price < market_price and purchase_price > 0:
            discount = ((market_price - purchase_price) / market_price) * 100
            if discount > 15 and qualifying:
                raise ValueError(f"ESPP discount {discount:.2f}% > 15%. Set qualifying=False for non-qualifying plans or adjust prices.")
        else:
            discount = safe_decimal(data.get('discount', 0))
        p = ESPPPurchase(
            date=date_val,
            shares_retained=shares_retained,
            purchase_price_usd=purchase_price,
            market_price_usd=market_price,
            discount=discount,
            exchange_rate=safe_decimal(data.get('exchange_rate')),
            total_gbp=safe_decimal(data.get('total_gbp')),
            discount_taxed_paye=data.get('discount_taxed_paye', True),
            paye_tax_gbp=safe_decimal(data.get('paye_tax_gbp')),
            qualifying=qualifying,
            incidental_costs_gbp=safe_decimal(data.get('incidental_costs_gbp', 0)),
            notes=data.get('notes', '')
        )
        db.session.add(p)
        db.session.commit()
        # Trigger partial recalc
        recalc_all(sale_filter=date_val.isoformat())
        return jsonify(model_to_dict(p)), 201
    except ValueError as ve:
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/espp', methods=['GET'])
def get_espp():
    espps = ESPPPurchase.query.order_by(ESPPPurchase.date.asc()).all()
    return jsonify([model_to_dict(e) for e in espps])

@app.route('/api/espp/<int:id>', methods=['PUT'])
def update_espp(id):
    p = ESPPPurchase.query.get_or_404(id)
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    try:
        new_date = to_date(data.get('date', p.date))
        if not new_date:
            raise ValueError("Valid date required")
        new_shares = safe_decimal(data.get('shares_retained', p.shares_retained))
        if new_shares <= 0:
            raise ValueError("Shares retained must be positive")
        purchase_price = safe_decimal(data.get('purchase_price_usd', p.purchase_price_usd))
        market_price = safe_decimal(data.get('market_price_usd', p.market_price_usd))
        qualifying = data.get('qualifying', p.qualifying)
        if market_price > 0 and purchase_price < market_price and purchase_price > 0:
            discount = ((market_price - purchase_price) / market_price) * 100
            if discount > 15 and qualifying:
                raise ValueError(f"ESPP discount {discount:.2f}% > 15%. Set qualifying=False for non-qualifying plans or adjust prices.")
        else:
            discount = safe_decimal(data.get('discount', p.discount))
        p.date = new_date
        p.shares_retained = new_shares
        p.purchase_price_usd = purchase_price
        p.market_price_usd = market_price
        p.discount = discount
        p.exchange_rate = safe_decimal(data.get('exchange_rate', p.exchange_rate))
        p.total_gbp = safe_decimal(data.get('total_gbp', p.total_gbp))
        p.discount_taxed_paye = data.get('discount_taxed_paye', p.discount_taxed_paye)
        p.paye_tax_gbp = safe_decimal(data.get('paye_tax_gbp', p.paye_tax_gbp))
        p.qualifying = qualifying
        p.incidental_costs_gbp = safe_decimal(data.get('incidental_costs_gbp', p.incidental_costs_gbp))
        p.notes = data.get('notes', p.notes)
        db.session.commit()
        # Partial recalc
        recalc_all(sale_filter=new_date.isoformat())
        return jsonify(model_to_dict(p))
    except ValueError as ve:
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/espp/<int:id>', methods=['DELETE'])
def api_delete_espp(id):
    p = ESPPPurchase.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    return jsonify({'message': 'ESPP deleted'})

# ---------- CRUD APIs for Sales ----------
@app.route('/api/sales', methods=['POST'])
def create_sale():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    try:
        shares_sold = safe_decimal(data.get('shares_sold'))
        if shares_sold <= 0:
            raise ValueError("Shares sold must be positive")
        date_val = to_date(data.get('date'))
        if not date_val:
            raise ValueError("Valid date required")
        s = SaleInput(
            date=date_val,
            shares_sold=shares_sold,
            sale_price_usd=safe_decimal(data.get('sale_price_usd')),
            exchange_rate=safe_decimal(data.get('exchange_rate')),
            incidental_costs_gbp=safe_decimal(data.get('incidental_costs_gbp', 0))
        )
        db.session.add(s)
        db.session.commit()
        # Trigger partial recalc for this sale
        recalc_all(sale_filter=[s.id])
        return jsonify(model_to_dict(s)), 201
    except ValueError as ve:
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales', methods=['GET'])
def get_sales():
    sales = SaleInput.query.order_by(SaleInput.date.asc()).all()
    return jsonify([model_to_dict(s) for s in sales])

@app.route('/api/sales/<int:id>', methods=['PUT'])
def update_sale(id):
    s = SaleInput.query.get_or_404(id)
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    try:
        new_date = to_date(data.get('date', s.date))
        if not new_date:
            raise ValueError("Valid date required")
        new_shares = safe_decimal(data.get('shares_sold', s.shares_sold))
        if new_shares <= 0:
            raise ValueError("Shares sold must be positive")
        s.date = new_date
        s.shares_sold = new_shares
        s.sale_price_usd = safe_decimal(data.get('sale_price_usd', s.sale_price_usd))
        s.exchange_rate = safe_decimal(data.get('exchange_rate', s.exchange_rate))
        s.incidental_costs_gbp = safe_decimal(data.get('incidental_costs_gbp', s.incidental_costs_gbp))
        db.session.commit()
        # Recompute this sale
        recalc_all(sale_filter=[s.id])
        return jsonify(model_to_dict(s))
    except ValueError as ve:
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales/<int:id>', methods=['DELETE'])
def api_delete_sale(id):
    s = SaleInput.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    return jsonify({'message': 'Sale deleted'})

# ---------- Migration helper and bootstrap ----------
def ensure_db_schema():
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    def has_col(table, col):
        try:
            c.execute(f"PRAGMA table_info({table})")
            return col in [r[1] for r in c.fetchall()]
        except Exception:
            return False
    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='carry_forward_losses'")
        if not c.fetchone():
            c.execute("""
                CREATE TABLE carry_forward_losses (
                    tax_year INTEGER PRIMARY KEY,
                    amount NUMERIC NOT NULL,
                    notes VARCHAR(200)
                )
            """)
    except Exception:
        pass
    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vesting'")
        if c.fetchone():
            if not has_col("vesting", "incidental_costs_gbp"): c.execute("ALTER TABLE vesting ADD COLUMN incidental_costs_gbp NUMERIC DEFAULT 0")
    except Exception:
        pass
    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='espp'")
        if c.fetchone():
            if not has_col("espp", "shares_retained"): c.execute("ALTER TABLE espp ADD COLUMN shares_retained NUMERIC")
            if not has_col("espp", "purchase_price_usd"): c.execute("ALTER TABLE espp ADD COLUMN purchase_price_usd NUMERIC")
            if not has_col("espp", "market_price_usd"): c.execute("ALTER TABLE espp ADD COLUMN market_price_usd NUMERIC")
            if not has_col("espp", "discount_taxed_paye"): c.execute("ALTER TABLE espp ADD COLUMN discount_taxed_paye BOOLEAN")
            if not has_col("espp", "paye_tax_gbp"): c.execute("ALTER TABLE espp ADD COLUMN paye_tax_gbp NUMERIC")
            if not has_col("espp", "exchange_rate"): c.execute("ALTER TABLE espp ADD COLUMN exchange_rate NUMERIC")
            if not has_col("espp", "incidental_costs_gbp"): c.execute("ALTER TABLE espp ADD COLUMN incidental_costs_gbp NUMERIC DEFAULT 0")
            if not has_col("espp", "qualifying"): c.execute("ALTER TABLE espp ADD COLUMN qualifying BOOLEAN DEFAULT 1")
    except Exception:
        pass
    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sales_in'")
        if c.fetchone():
            if not has_col("sales_in", "exchange_rate"): c.execute("ALTER TABLE sales_in ADD COLUMN exchange_rate NUMERIC")
            if not has_col("sales_in", "incidental_costs_gbp"): c.execute("ALTER TABLE sales_in ADD COLUMN incidental_costs_gbp NUMERIC DEFAULT 0")
    except Exception:
        pass
    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pool_snapshot'")
        if c.fetchone():
            if not has_col("pool_snapshot", "tax_year"): c.execute("ALTER TABLE pool_snapshot ADD COLUMN tax_year INTEGER")
            if not has_col("pool_snapshot", "snapshot_json"): c.execute("ALTER TABLE pool_snapshot ADD COLUMN snapshot_json TEXT")
            if not has_col("pool_snapshot", "total_shares"): c.execute("ALTER TABLE pool_snapshot ADD COLUMN total_shares NUMERIC")
            if not has_col("pool_snapshot", "total_cost_gbp"): c.execute("ALTER TABLE pool_snapshot ADD COLUMN total_cost_gbp NUMERIC")
            if not has_col("pool_snapshot", "avg_cost_gbp"): c.execute("ALTER TABLE pool_snapshot ADD COLUMN avg_cost_gbp NUMERIC")
    except Exception:
        pass
    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disposal_results'")
        if c.fetchone():
            if not has_col("disposal_results", "calculation_json"): c.execute("ALTER TABLE disposal_results ADD COLUMN calculation_json TEXT")
    except Exception:
        pass
    conn.commit()
    conn.close()

def bootstrap():
    with app.app_context():
        ensure_db_schema()
        db.create_all()
        if not Setting.query.get("CGT_Allowance"): db.session.add(Setting(key="CGT_Allowance", value="0"))  # 0 means use dynamic
        if not Setting.query.get("CGT_Rate"): db.session.add(Setting(key="CGT_Rate", value="20"))
        if not Setting.query.get("NonSavingsIncome"): db.session.add(Setting(key="NonSavingsIncome", value="0"))
        if not Setting.query.get("BasicBandThreshold"): db.session.add(Setting(key="BasicBandThreshold", value="37700"))
        db.session.commit()

if __name__ == "__main__":
    bootstrap()
    app.run(debug=True, host="0.0.0.0", port=5002)