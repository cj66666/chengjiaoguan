from decimal import Decimal

import pytest

from app import models
from app.services.quote_engine import QuoteItemInput, calculate_quote


def _seed_quote_data(db_session, *, moq=500, tiers=None, floor_price="3.20"):
    seller = db_session.get(models.Seller, 1) or models.Seller(id=1, name="Demo Exporter", email="owner@example.com")
    customer = models.Customer(seller_id=1, email="buyer@example.com", status="active")
    product = models.Product(
        seller_id=1,
        name="LED Desk Lamp 10W",
        sku="LED-10W",
        cost=Decimal("2.10"),
        moq=moq,
        currency="USD",
        status="active",
    )
    db_session.add_all([seller, customer, product])
    db_session.flush()
    inquiry = models.Inquiry(
        seller_id=1,
        customer_id=customer.id,
        source_channel="email",
        raw_content="Need lamps",
        status="new",
    )
    db_session.add(inquiry)
    db_session.flush()
    rule = models.PricingRule(
        seller_id=1,
        product_id=product.id,
        margin_rate=Decimal("0.30"),
        logistics_template={"unit_cost": "0.20", "destination_unit_costs": {"US": "0.25"}},
        tiered_prices=tiers or [{"min_qty": 1000, "price": "3.30"}, {"min_qty": 5000, "price": "3.05"}],
        valid_days=16,
        floor_price=Decimal(floor_price),
        currency="USD",
    )
    db_session.add(rule)
    db_session.flush()
    return inquiry, product


def test_calculate_quote_uses_tiered_price_and_destination_logistics(db_session):
    inquiry, product = _seed_quote_data(db_session)

    result = calculate_quote(
        db_session,
        1,
        inquiry.id,
        [QuoteItemInput(product_id=product.id, quantity=1000)],
        destination="US",
    )

    assert result.currency == "USD"
    assert result.total_amount == Decimal("3550.00")
    assert result.lines[0].unit_price == Decimal("3.55")
    assert result.valid_until is not None
    assert result.hits_floor is False


def test_calculate_quote_detects_floor_price_hit(db_session):
    inquiry, product = _seed_quote_data(db_session)

    result = calculate_quote(db_session, 1, inquiry.id, [QuoteItemInput(product_id=product.id, quantity=5000)])

    assert result.lines[0].unit_price == Decimal("3.25")
    assert result.hits_floor is False

    inquiry2, product2 = _seed_quote_data(db_session, tiers=[{"min_qty": 500, "price": "2.90"}], floor_price="3.20")
    result2 = calculate_quote(db_session, 1, inquiry2.id, [QuoteItemInput(product_id=product2.id, quantity=500)])
    assert result2.hits_floor is True


def test_calculate_quote_rejects_below_moq_quantity(db_session):
    inquiry, product = _seed_quote_data(db_session, moq=1000)

    with pytest.raises(ValueError, match="below MOQ"):
        calculate_quote(db_session, 1, inquiry.id, [QuoteItemInput(product_id=product.id, quantity=500)])


def test_calculate_quote_uses_cost_margin_when_no_tier_matches(db_session):
    inquiry, product = _seed_quote_data(db_session, tiers=[])

    result = calculate_quote(db_session, 1, inquiry.id, [QuoteItemInput(product_id=product.id, quantity=500)])

    assert result.lines[0].unit_price == Decimal("2.93")
    assert result.total_amount == Decimal("1465.00")
