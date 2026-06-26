"""
/* ========================================================================== */
/* GEB L3: 渠道测试投递                                                       */
/* ========================================================================== */
/**
 * [INPUT]: 依赖 os、SQLAlchemy Session、channel account、credentials 与 delivery client
 * [OUTPUT]: 对外提供 test_channel_delivery，生成安全测试 payload，并在显式确认时执行真实投递
 * [POS]: services 的渠道上线前探针，避免把真实 SMTP/WhatsApp 发送藏在普通配置动作里
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
"""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from app import models
from app.services.channel_delivery_clients import PayloadOnlyDeliveryClient, send_with_delivery_client
from app.services.credentials import reveal_credentials
from app.services.whatsapp_adapter import WhatsAppAdapter


def test_channel_delivery(
    session: Session,
    seller_id: int,
    channel_account_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    account = session.get(models.ChannelAccount, channel_account_id)
    if account is None or account.seller_id != seller_id:
        raise LookupError("Channel account not found")
    credentials = reveal_credentials(account.credentials)
    test_payload = _payload_for(account, payload, credentials)
    live_requested = bool(payload.get("confirm_live"))
    live_enabled = os.getenv("CLOSER_DELIVERY_MODE") == "live"
    if live_requested and live_enabled:
        client = send_with_delivery_client(account.channel_type, test_payload, credentials)
        mode = "live"
    else:
        client = PayloadOnlyDeliveryClient().send(test_payload, credentials)
        mode = "dry_run"
    return {
        "channel_account_id": account.id,
        "channel_type": account.channel_type,
        "mode": mode,
        "live_enabled": live_enabled,
        "live_requested": live_requested,
        "payload": test_payload,
        "client": client,
    }


def _payload_for(account: models.ChannelAccount, payload: dict[str, Any], credentials: dict[str, Any]) -> dict[str, Any]:
    if account.channel_type == "email":
        to_email = _required(payload, "to")
        return {
            "from": str(payload.get("from") or credentials.get("username") or "seller@example.com"),
            "to": to_email,
            "subject": str(payload.get("subject") or "Closer channel test"),
            "message_id": f"closer:test:{account.id}",
            "body": str(payload.get("body") or "Closer channel test message."),
        }
    if account.channel_type == "whatsapp":
        to_phone = _required(payload, "to")
        return WhatsAppAdapter().compose_text_payload(to_phone, str(payload.get("body") or "Closer channel test message."))
    return {"content": str(payload.get("body") or "Closer channel test message.")}


def _required(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value in (None, ""):
        raise ValueError(f"{key} is required")
    return str(value)
