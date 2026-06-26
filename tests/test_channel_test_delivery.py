"""
/* ========================================================================== */
/* GEB L3: 渠道测试投递测试                                                   */
/* ========================================================================== */
/**
 * [INPUT]: 依赖 FastAPI TestClient、SQLite 会话夹具、app.models 与 channel_test_delivery 服务
 * [OUTPUT]: 验证测试投递默认 dry-run、live 显式确认、租户隔离和输入校验
 * [POS]: tests 的外部发送安全门证明文件，防止配置页测试动作误触真实渠道发送
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
"""

from app import models
from app.services.credentials import seal_credentials


def _seed_email_channel(db_session):
    seller = models.Seller(id=1, name="Demo Exporter", email="owner@example.com")
    channel = models.ChannelAccount(
        seller_id=1,
        channel_type="email",
        name="Sales inbox",
        credentials=seal_credentials(
            {
                "smtp_host": "smtp.example.com",
                "smtp_port": 465,
                "username": "sales@example.com",
                "password": "secret",
            }
        ),
        status="connected",
    )
    db_session.add_all([seller, channel])
    db_session.flush()
    return channel


def test_channel_test_delivery_defaults_to_dry_run(client, db_session, monkeypatch):
    monkeypatch.setenv("CLOSER_DELIVERY_MODE", "live")
    channel = _seed_email_channel(db_session)

    response = client.post(
        f"/api/v1/channels/{channel.id}/test-delivery",
        json={"to": "buyer@example.com", "body": "Test"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "dry_run"
    assert payload["live_enabled"] is True
    assert payload["client"]["client"] == "payload_only"
    assert payload["payload"]["to"] == "buyer@example.com"
    assert payload["payload"]["from"] == "sales@example.com"


def test_channel_test_delivery_can_confirm_live_send(client, db_session, monkeypatch):
    channel = _seed_email_channel(db_session)
    sent = []

    def fake_send(channel_type, payload, credentials):
        sent.append((channel_type, payload, credentials))
        return {"status": "sent", "client": "fake_smtp", "provider_message_id": "test-1"}

    monkeypatch.setenv("CLOSER_DELIVERY_MODE", "live")
    monkeypatch.setattr("app.services.channel_test_delivery.send_with_delivery_client", fake_send)

    response = client.post(
        f"/api/v1/channels/{channel.id}/test-delivery",
        json={"to": "buyer@example.com", "subject": "Probe", "body": "Test", "confirm_live": True},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "live"
    assert response.json()["client"]["status"] == "sent"
    assert sent[0][0] == "email"
    assert sent[0][1]["subject"] == "Probe"
    assert sent[0][2]["smtp_host"] == "smtp.example.com"


def test_channel_test_delivery_requires_recipient_and_tenant_scope(client, db_session):
    channel = _seed_email_channel(db_session)

    missing = client.post(f"/api/v1/channels/{channel.id}/test-delivery", json={"body": "Test"})
    cross_tenant = client.post(
        f"/api/v1/channels/{channel.id}/test-delivery",
        headers={"Authorization": "Bearer seller:2"},
        json={"to": "buyer@example.com"},
    )

    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "invalid_test_delivery"
    assert cross_tenant.status_code == 404
    assert cross_tenant.json()["error"]["code"] == "channel_not_found"
