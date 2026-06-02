from decimal import Decimal

from app import agent_tools, models


def _seed_conversation(db_session):
    seller = models.Seller(id=1, name="Demo Exporter", email="owner@example.com")
    customer = models.Customer(seller_id=1, email="buyer@example.com", status="active")
    product = models.Product(seller_id=1, name="LED Desk Lamp", cost=Decimal("2.00"), moq=100, status="active")
    db_session.add_all([seller, customer, product])
    db_session.flush()
    inquiry = models.Inquiry(seller_id=1, customer_id=customer.id, raw_content="Need 500 lamps", status="new")
    db_session.add(inquiry)
    db_session.flush()
    conversation = models.Conversation(
        seller_id=1,
        customer_id=customer.id,
        inquiry_id=inquiry.id,
        channel="email",
        language="en",
    )
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
    db_session.add_all([conversation, rule])
    db_session.flush()
    return inquiry, conversation, product


def test_approval_patch_and_approve_executes_message_send(client, db_session):
    _, conversation, _ = _seed_conversation(db_session)
    pending = agent_tools.send_message(db_session, 1, conversation.id, "We can offer USD 2.80 per unit.")

    listed = client.get("/api/v1/approvals")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == pending["approval_id"]

    patched = client.patch(
        f"/api/v1/approvals/{pending['approval_id']}",
        json={"payload": {"content": "We can offer USD 3.20 per unit after review."}},
    )
    assert patched.status_code == 200
    assert patched.json()["payload"]["content"].endswith("after review.")

    approved = client.post(f"/api/v1/approvals/{pending['approval_id']}/approve")

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["executed"] is True
    message = db_session.get(models.Message, approved.json()["result"]["message_id"])
    assert message.content.endswith("after review.")
    assert db_session.get(models.Conversation, conversation.id).is_human_takeover is False


def test_approval_reject_marks_pending_item_rejected(client, db_session):
    _, conversation, _ = _seed_conversation(db_session)
    pending = agent_tools.send_message(db_session, 1, conversation.id, "We guarantee delivery and contract terms.")

    rejected = client.post(
        f"/api/v1/approvals/{pending['approval_id']}/reject",
        json={"reason": "Owner will reply manually"},
    )

    assert rejected.status_code == 200
    approval = db_session.get(models.Approval, pending["approval_id"])
    assert approval.status == "rejected"
    assert approval.payload["reject_reason"] == "Owner will reply manually"


def test_quotation_detail_patch_and_send(client, db_session):
    inquiry, conversation, product = _seed_conversation(db_session)
    quote = agent_tools.calc_quote(db_session, 1, inquiry.id, [{"product_id": product.id, "quantity": 500}])

    detail = client.get(f"/api/v1/quotations/{quote['quotation_id']}")
    assert detail.status_code == 200
    assert detail.json()["items"][0]["quantity"] == 500

    patched = client.patch(
        f"/api/v1/quotations/{quote['quotation_id']}",
        json={
            "terms": {"message": "Updated reviewed quote."},
            "items": [{"product_id": product.id, "quantity": 1000, "unit_price": "3.10"}],
        },
    )
    assert patched.status_code == 200
    assert patched.json()["total_amount"] == 3100.0

    sent = client.post(f"/api/v1/quotations/{quote['quotation_id']}/send")

    assert sent.status_code == 200
    assert sent.json()["status"] == "sent"
    assert db_session.get(models.Quotation, quote["quotation_id"]).status == "sent"
    messages = client.get(f"/api/v1/conversations/{conversation.id}/messages").json()["items"]
    assert messages[-1]["content"] == "Updated reviewed quote."


def test_quotation_send_rejects_unapproved_floor_hit(client, db_session):
    inquiry, _, product = _seed_conversation(db_session)
    rule = db_session.query(models.PricingRule).filter_by(product_id=product.id).one()
    rule.tiered_prices = [{"min_qty": 500, "price": "2.50"}]
    quote = agent_tools.calc_quote(db_session, 1, inquiry.id, [{"product_id": product.id, "quantity": 500}])

    response = client.post(f"/api/v1/quotations/{quote['quotation_id']}/send")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "below_floor_price"
