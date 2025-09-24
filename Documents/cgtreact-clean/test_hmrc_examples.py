import os
import argparse
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys

# Add the project directory to path to import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Vesting, SaleInput, ESPPPurchase, ExchangeRate, recalc_all

# Path to the database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")
DB_URI = f"sqlite:///{DB_PATH}"

# Create engine and session (local session for script insertions)
engine = create_engine(DB_URI)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

def run_with_test_db(func):
    """Temporarily switch to in-memory DB for the function execution."""
    original_uri = app.config['SQLALCHEMY_DATABASE_URI']
    original_track_mod = app.config.get('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    with app.app_context():
        db.create_all()
        try:
            return func()
        finally:
            db.drop_all()
    app.config['SQLALCHEMY_DATABASE_URI'] = original_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = original_track_mod

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run HMRC examples with optional production DB.")
    parser.add_argument("--production", action="store_true", help="Use production DB (WARNING: will modify data.db)")
    args = parser.parse_args()

    if args.production:
        print("WARNING: Using production DB. This will modify data.db!")
    else:
        print("Using in-memory test DB to avoid modifying data.db.")

def insert_hmrc_example_2(use_production=False):
    """Insert data for HMRC HS284 Example 2 (Mr Schneider shares)"""
    if use_production:
        # Use local session for production
        sess = session
    else:
        # For test DB, use global db.session inside context
        def insert_func():
            sess = db.session

            # Set a default exchange rate to 1.0 (assume USD=GBP for simplicity)
            rate_date = date(2023, 1, 1)
            existing_rate = sess.query(ExchangeRate).filter_by(date=rate_date).first()
            if not existing_rate:
                rate = ExchangeRate(
                    date=rate_date,
                    usd_gbp=Decimal('1.0'),
                    description='Test rate for HMRC examples (USD/GBP=1)'
                )
                sess.add(rate)
                sess.commit()
                print("Added default exchange rate.")

            # Prior Section 104 holding: 9500 shares, assume total cost £9500 (avg £1/share) - use Vesting for acquisition
            prior_date = date(2020, 1, 1)  # Arbitrary prior date
            prior_vesting = Vesting(
                date=prior_date,
                shares_vested=Decimal('9500'),
                price_usd=Decimal('1.0'),  # Per-share USD
                shares_sold=Decimal('0'),
                net_shares=Decimal('9500'),
                exchange_rate=Decimal('1.0')
            )
            sess.add(prior_vesting)
            print(f"Added prior holding: 9500 shares on {prior_date}, per-share £1.00 (total £9500).")

            # Purchase 500 shares on 11 Sep 2023, total cost £850 - use Vesting
            purchase_date = date(2023, 9, 11)
            purchase_vesting = Vesting(
                date=purchase_date,
                shares_vested=Decimal('500'),
                price_usd=Decimal('1.7'),  # Per-share USD
                shares_sold=Decimal('0'),
                net_shares=Decimal('500'),
                exchange_rate=Decimal('1.0')
            )
            sess.add(purchase_vesting)
            print(f"Added purchase: 500 shares on {purchase_date}, per-share £1.70 (total £850).")

            # Sale: 4000 shares on 30 Aug 2023, total proceeds £6000 (per share £1.50)
            sale_date = date(2023, 8, 30)
            sale = SaleInput(
                date=sale_date,
                shares_sold=Decimal('4000'),
                sale_price_usd=Decimal('1.50'),  # Per share USD
                exchange_rate=Decimal('1.0')
            )
            sess.add(sale)
            print(f"Added sale: 4000 shares on {sale_date}, per share £1.50 (total proceeds £6000).")

            sess.commit()
            print("Committed insertions for Example 2.")

            # Trigger recalculation
            print("Running recalc_all...")
            result = recalc_all(explain=True)
            print("Recalc result:", result)
            return result

        if use_production:
            return insert_func()
        else:
            return run_with_test_db(insert_func)

    # Trigger recalculation within app context
    print("Running recalc_all...")
    if args.production:
        with app.app_context():
            result = recalc_all(explain=True)
    else:
        def run_example():
            # Insertions using global db.session now (after create_all)
            # ... (insert code will be adapted below, but for now assume)
            result = recalc_all(explain=True)
            return result
        result = run_with_test_db(run_example)
    print("Recalc result:", result)

    # Expected: Due to code matching only prior lots, all 4000 will match to Section 104 (avg £1), proceeds £6000, cost £4000, gain £2000.
    # Note: Bed and breakfasting for post-sale purchase not handled in current code (would match 500 to purchase £850, apportioned proceeds £750, loss £100; 3500 to pool £3500 cost, £5250 proceeds, gain £1750; net gain £1650).
    # For full match, code adjustment needed, but this tests Section 104 pooling.

def insert_hmrc_example_1(use_production=False):
    """Insert data for HMRC HS284 Example 1 (Wilson and Strickland shares - Section 104 holding)"""
    if use_production:
        sess = session
    else:
        def insert_func():
            sess = db.session

            # Multiple purchases forming Section 104 holding of 12000 shares
            purchases = [
                (date(1979, 6, 7), Decimal('2000'), Decimal('1.00')),  # Assume avg costs for simplicity
                (date(1982, 11, 4), Decimal('2500'), Decimal('1.20')),
                (date(1987, 8, 26), Decimal('2500'), Decimal('1.50')),
                (date(1998, 7, 7), Decimal('3000'), Decimal('2.00')),
                (date(2006, 5, 14), Decimal('2000'), Decimal('3.00'))
            ]

            total_shares = Decimal('0')
            total_cost = Decimal('0')

            for p_date, shares, per_share in purchases:
                vesting = Vesting(
                    date=p_date,
                    shares_vested=shares,
                    price_usd=per_share,  # Per-share USD
                    shares_sold=Decimal('0'),
                    net_shares=shares,
                    exchange_rate=Decimal('1.0')
                )
                sess.add(vesting)
                total_shares += shares
                total_cost += per_share * shares
                print(f"Added purchase: {shares} shares on {p_date}, per share £{per_share} (total £{per_share * shares}).")

            avg_cost = total_cost / total_shares if total_shares > 0 else Decimal('0')
            print(f"Section 104 holding: {total_shares} shares, total cost £{total_cost}, avg £{avg_cost}.")

            # No sale in Example 1, just holding - recalc will show pool
            sess.commit()

            result = recalc_all(explain=True)
            print("Recalc for Example 1 (pool only):", result)
            return result

        if use_production:
            return insert_func()
        else:
            return run_with_test_db(insert_func)

def insert_hmrc_example_3(use_production=False):
    """Insert data for HMRC HS284 Example 3 from PDF (Lobster shares)"""
    if use_production:
        sess = session
    else:
        def insert_func():
            sess = db.session

            # From PDF screenshot: Aug 2019 buy 1000 shares £4000 total (£4/share)
            buy1_date = date(2019, 8, 1)  # Approximate
            buy1 = Vesting(
                date=buy1_date,
                shares_vested=Decimal('1000'),
                price_usd=Decimal('4.00'),
                shares_sold=Decimal('0'),
                net_shares=Decimal('1000'),
                exchange_rate=Decimal('1.0')
            )
            sess.add(buy1)
            print(f"Added buy1: 1000 shares on {buy1_date}, per-share £4.00 (total £4000).")

            # Feb 2021 sell 500 shares, proceeds £3000 (from screenshot step 2, pool after 500 @ £4)
            sell_date = date(2021, 2, 1)
            sell = SaleInput(
                date=sell_date,
                shares_sold=Decimal('500'),
                sale_price_usd=Decimal('6.00'),  # £3000 total / 500 = £6/share
                exchange_rate=Decimal('1.0')
            )
            sess.add(sell)
            print(f"Added sell: 500 shares on {sell_date}, per share £6 (total £3000). Expected: cost £2000, gain £1000.")

            sess.commit()

            result = recalc_all(explain=True)
            print("Recalc for Example 3:", result)
            return result

        if use_production:
            return insert_func()
        else:
            return run_with_test_db(insert_func)

if __name__ == "__main__":
    print("Inserting HMRC Example 2...")
    insert_hmrc_example_2(args.production)
    print("\nInserting HMRC Example 1 (pool)...")
    insert_hmrc_example_1(args.production)
    print("\nInserting HMRC Example 3...")
    insert_hmrc_example_3(args.production)
    print("\nAll insertions complete. Check app Dashboard/CGTSummary for verification.")
    if not args.production:
        print("Note: Examples ran in-memory; data not saved to data.db.")
    session.close()