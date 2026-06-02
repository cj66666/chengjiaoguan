from app import models
from app.schemas import ChannelContact, InboundMessage
from app.services.channel_gateway import ingest_inbound_message


def _seed_inquiry(db_session, message_id="api-001", content="Need 5000 LED desk lamps to US."):
    inbound = InboundMessage(
        channel="site_form",
        channel_message_id=message_id,
        from_=ChannelContact(email="buyer@example.com", company="ACME Trading", country="US"),
        content=content,
        language="en",
    )
    inquiry, conversation, message, _ = ingest_inbound_message(db_session, 1, inbound)
    inquiry.grade = "A"
    inquiry.score = 88
    db_session.commit()
    return inquiry, conversation, message


def test_inquiries_list_detail_and_patch(client, db_session):
    inquiry, _, _ = _seed_inquiry(db_session)

    list_response = client.get("/api/v1/inquiries", params={"grade": "A", "q": "desk", "page_size": 10})
    detail_response = client.get(f"/api/v1/inquiries/{inquiry.id}")
    patch_response = client.patch(f"/api/v1/inquiries/{inquiry.id}", json={"grade": "B", "status": "qualifying"})

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["customer"]["company"] == "ACME Trading"
    assert detail_response.status_code == 200
    assert detail_response.json()["parsed"]["quantity"] == 5000
    assert patch_response.status_code == 200
    assert patch_response.json()["grade"] == "B"
    assert patch_response.json()["status"] == "qualifying"


def test_inquiry_api_is_tenant_scoped(client, db_session):
    inquiry, _, _ = _seed_inquiry(db_session)

    response = client.get(f"/api/v1/inquiries/{inquiry.id}", headers={"X-Seller-Id": "2"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "inquiry_not_found"


def test_conversation_detail_messages_takeover_release_and_human_send(client, db_session):
    _, conversation, first_message = _seed_inquiry(db_session)

    detail = client.get(f"/api/v1/conversations/{conversation.id}")
    messages = client.get(f"/api/v1/conversations/{conversation.id}/messages")
    blocked = client.post(
        f"/api/v1/conversations/{conversation.id}/messages",
        json={"content": "Manual reply before takeover"},
    )
    takeover = client.post(f"/api/v1/conversations/{conversation.id}/takeover")
    sent = client.post(
        f"/api/v1/conversations/{conversation.id}/messages",
        json={"content": "Thanks, I will confirm the quote.", "language": "en"},
    )
    release = client.post(f"/api/v1/conversations/{conversation.id}/release")

    assert detail.status_code == 200
    assert detail.json()["is_human_takeover"] is False
    assert messages.status_code == 200
    assert messages.json()["items"][0]["id"] == first_message.id
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "conversation_not_taken_over"
    assert takeover.json()["is_human_takeover"] is True
    assert sent.status_code == 201
    assert sent.json()["sender_role"] == "human"
    assert sent.json()["status"] == "sent"
    assert release.json()["is_human_takeover"] is False

    db_message = db_session.get(models.Message, sent.json()["id"])
    assert db_message.content == "Thanks, I will confirm the quote."

