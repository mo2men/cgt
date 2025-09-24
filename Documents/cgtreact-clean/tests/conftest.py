import os
import sys
import pytest
from datetime import date
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Vesting, ESPPPurchase, SaleInput, ExchangeRate, Setting, get_aea, build_fragment_detail_struct, load_rates_sorted, get_rate_for_date, recalc_all, DisposalResult

@pytest.fixture(scope="function")
def app_context():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        # Bootstrap settings
        if not Setting.query.get("CGT_Allowance"):
            db.session.add(Setting(key="CGT_Allowance", value="0"))
        if not Setting.query.get("CGT_Rate"):
            db.session.add(Setting(key="CGT_Rate", value="20"))
        db.session.commit()
        yield
        db.session.rollback()
        db.drop_all()

@pytest.fixture
def session(app_context):
    from app import db
    yield db.session
    db.session.rollback()

@pytest.fixture
def default_rate(app_context):
    rate = ExchangeRate(
        date=date(2023, 1, 1),
        usd_gbp=Decimal("1.0"),
        description="Test default rate"
    )
    db.session.add(rate)
    db.session.commit()
    yield rate
    db.session.delete(rate)
    db.session.commit()

@pytest.fixture
def client(app_context):
    return app.test_client()