from decimal import Decimal

import pytest

from app import agent_tools, models


def _seed_conversation(db_session, *, takeover: bool = False):
    seller = models.Seller(id=1, name="Demo Exporter", email="owner@example.com")
    customer = models.Customer(seller_id=1, email="buyer@example.com", status="active")
    db_session.add_all([seller, customer])
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
        is_human_takeover=takeover,
    )
    db_session.add(conversation)
    db_session.flush()
    return inquiry, conversation


def test_send_message_creates_ai_message_when_safe(db_session):
    _, conversation = _seed_conversation(db_session)

    result = agent_tools.send_message(
        db_session,
        1,
        conversation.id,
        "Thanks for your inquiry. We will confirm the exact lead time shortly.",
    )

    assert result["status"] == "sent"
    message = db_session.get(models.Message, result["message_id"])
    assert message.sender_role == "ai"
    assert message.content.startswith("Thanks for your inquiry")


def test_send_message_below_floor_creates_pending_approval(db_session):
    inquiry, conversation = _seed_conversation(db_session)
    db_session.add(
        models.PricingRule(
            seller_id=1,
            product_id=None,
            floor_price=Decimal("3.00"),
            currency="USD",
        )
    )

    result = agent_tools.send_message(db_session, 1, conversation.id, "We can offer USD 2.80 per unit.")

    assert result["status"] == "pending_approval"
    assert result["reason"] == "below_floor_price"
    approval = db_session.get(models.Approval, result["approval_id"])
    assert approval.type == "message_send"
    assert approval.payload["content"].startswith("We can offer")
    assert db_session.get(models.Conversation, conversation.id).is_human_takeover is True
    assert db_session.get(models.Inquiry, inquiry.id).status == "pending_approval"
    assert db_session.query(models.Message).count() == 0


def test_send_message_sensitive_commitment_creates_pending_approval(db_session):
    _, conversation = _seed_conversation(db_session)

    result = agent_tools.send_message(
        db_session,
        1,
        conversation.id,
        "We guarantee delivery and can sign the contract today.",
    )

    assert result["status"] == "pending_approval"
    assert result["reason"] == "sensitive_commitment"


def test_send_message_is_tenant_scoped(db_session):
    _, conversation = _seed_conversation(db_session)

    with pytest.raises(LookupError):
        agent_tools.send_message(db_session, 2, conversation.id, "Hello")
