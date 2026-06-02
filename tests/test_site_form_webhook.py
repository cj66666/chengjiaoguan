from sqlalchemy import select

from app import models


def test_site_form_webhook_ingests_customer_inquiry_conversation_and_message(client, db_session):
    payload = {
        "channel": "site_form",
        "channel_message_id": "site-001",
        "from": {
            "name": "Jane Buyer",
            "company": "ACME Trading",
            "country": "US",
            "email": "jane@example.com",
        },
        "content": "Hi, we need 5000 LED desk lamps shipped to US.",
        "language": "en",
        "attachments": [],
        "received_at": "2026-06-02T03:12:00Z",
    }

    response = client.post("/api/v1/webhooks/site_form", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["duplicate"] is False
    assert data["inquiry_id"] == 1
    assert data["conversation_id"] == 1
    assert data["message_id"] == 1

    inquiry = db_session.get(models.Inquiry, data["inquiry_id"])
    assert inquiry.source_channel == "site_form"
    assert inquiry.parsed["quantity"] == 5000
    assert inquiry.parsed["destination"] == "US"

    customer = db_session.get(models.Customer, data["customer_id"])
    assert customer.company == "ACME Trading"
    assert customer.email == "jane@example.com"

    message = db_session.get(models.Message, data["message_id"])
    assert message.sender_role == "customer"
    assert message.channel_message_id == "site-001"


def test_site_form_webhook_is_idempotent_by_channel_message_id(client, db_session):
    payload = {
        "channel": "site_form",
        "channel_message_id": "site-dup",
        "from": {"email": "buyer@example.com"},
        "content": "Need 1000 lamps.",
    }

    first = client.post("/api/v1/webhooks/site_form", json=payload)
    second = client.post("/api/v1/webhooks/site_form", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["duplicate"] is True
    assert second.json()["inquiry_id"] == first.json()["inquiry_id"]

    messages = db_session.scalars(select(models.Message)).all()
    inquiries = db_session.scalars(select(models.Inquiry)).all()
    assert len(messages) == 1
    assert len(inquiries) == 1


def test_site_form_rejects_path_payload_channel_mismatch(client):
    payload = {
        "channel": "site_form",
        "channel_message_id": "site-002",
        "from": {"email": "buyer@example.com"},
        "content": "Need a quote.",
    }

    response = client.post("/api/v1/webhooks/whatsapp", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "channel_mismatch"

