from decimal import Decimal

import pytest

from app import agent_tools, models


def _seed(db_session):
    seller = models.Seller(id=1, name="Demo Exporter", email="owner@example.com")
    customer = models.Customer(seller_id=1, email="buyer@example.com", status="active")
    product = models.Product(seller_id=1, name="LED Desk Lamp", cost=Decimal("2.00"), moq=100, status="active")
    db_session.add_all([seller, customer, product])
    db_session.flush()
    inquiry = models.Inquiry(seller_id=1, customer_id=customer.id, raw_content="Need 500 lamps", status="new")
    db_session.add(inquiry)
    db_session.flush()
    rule = models.PricingRule(
        seller_id=1,
        product_id=product.id,
        margin_rate=Decimal("0.25"),
        logistics_template={"unit_cost": "0.10"},
        tiered_prices=[{"min_qty": 500, "price": "3.20"}],
        valid_days=10,
        floor_price=Decimal("3.00"),
        currency="USD",
    )
    db_session.add(rule)
    db_session.flush()
    return inquiry, product


def test_calc_quote_tool_creates_draft_quotation_and_lines(db_session):
    inquiry, product = _seed(db_session)

    result = agent_tools.calc_quote(
        db_session,
        1,
        inquiry.id,
        [{"product_id": product.id, "quantity": 500}],
        destination="US",
    )
    db_session.commit()

    assert result["quotation_id"] == 1
    assert result["total_amount"] == 1650.0
    assert result["hits_floor"] is False
    assert "Thanks for your inquiry" in result["message"]

    quotation = db_session.get(models.Quotation, result["quotation_id"])
    assert quotation.status == "draft"
    assert quotation.created_by == "ai"
    assert quotation.items[0].quantity == 500


def test_generate_pi_marks_existing_quotation_as_pi(db_session):
    inquiry, product = _seed(db_session)
    quote = agent_tools.calc_quote(db_session, 1, inquiry.id, [{"product_id": product.id, "quantity": 500}])

    pi = agent_tools.generate_pi(db_session, 1, quote["quotation_id"])

    assert pi["pi_number"] == "PI-000001"
    assert pi["is_pi"] is True
    assert db_session.get(models.Quotation, quote["quotation_id"]).is_pi is True


def test_generate_pi_is_tenant_scoped(db_session):
    inquiry, product = _seed(db_session)
    quote = agent_tools.calc_quote(db_session, 1, inquiry.id, [{"product_id": product.id, "quantity": 500}])

    with pytest.raises(LookupError):
        agent_tools.generate_pi(db_session, 2, quote["quotation_id"])

