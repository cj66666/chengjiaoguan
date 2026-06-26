"""
/* ========================================================================== */
/* GEB L3: 运维告警聚合                                                       */
/* ========================================================================== */
/**
 * [INPUT]: 依赖 datetime、SQLAlchemy Session/select、app.models、channel credentials 与 pricing_rule.exchange_rate_cache
 * [OUTPUT]: 对外提供 list_ops_alerts，把失败投递、待审批、到期/暂停跟进、渠道凭证与汇率缓存风险折叠成只读告警列表
 * [POS]: services 的运行监控薄层，只读取既有状态并生成可观测信号，不拥有业务状态机
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.database import utcnow
from app.services.credentials import CredentialsError, credentials_key_status, reveal_credentials


REQUIRED_EMAIL_KEYS = ("username", "password")
REQUIRED_WHATSAPP_KEYS = ("access_token", "phone_number_id")


def list_ops_alerts(
    session: Session,
    seller_id: int,
    *,
    limit: int = 100,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or utcnow()
    alerts = (
        _failed_delivery_alerts(session, seller_id)
        + _pending_approval_alerts(session, seller_id)
        + _followup_alerts(session, seller_id, now)
        + _channel_credential_alerts(session, seller_id, now)
        + _exchange_cache_alerts(session, seller_id, now.date())
    )
    alerts = sorted(alerts, key=lambda item: (_severity_rank(item["severity"]), item["created_at"]), reverse=True)
    alerts = alerts[: min(max(limit, 1), 200)]
    counts = _counts(alerts)
    return {
        "status": _status(counts),
        "items": alerts,
        "total": len(alerts),
        "counts": counts,
    }


def _failed_delivery_alerts(session: Session, seller_id: int) -> list[dict[str, Any]]:
    attempts = session.scalars(
        select(models.DeliveryAttempt)
        .where(models.DeliveryAttempt.seller_id == seller_id)
        .where(models.DeliveryAttempt.status == "failed")
        .order_by(models.DeliveryAttempt.updated_at.desc(), models.DeliveryAttempt.id.desc())
        .limit(50)
    ).all()
    return [
        _alert(
            "critical",
            "failed_delivery_attempt",
            f"{attempt.channel} delivery failed",
            "delivery_attempt",
            attempt.id,
            attempt.updated_at,
            {
                "message_id": attempt.message_id,
                "channel": attempt.channel,
                "error": attempt.error,
                "next_retry_at": attempt.next_retry_at.isoformat() if attempt.next_retry_at else None,
            },
        )
        for attempt in attempts
    ]


def _pending_approval_alerts(session: Session, seller_id: int) -> list[dict[str, Any]]:
    approvals = session.scalars(
        select(models.Approval)
        .where(models.Approval.seller_id == seller_id)
        .where(models.Approval.status == "pending")
        .order_by(models.Approval.created_at.asc(), models.Approval.id.asc())
        .limit(50)
    ).all()
    return [
        _alert(
            "warning",
            "pending_approval",
            f"{approval.type} approval is waiting for human review",
            "approval",
            approval.id,
            approval.created_at,
            {
                "conversation_id": approval.conversation_id,
                "inquiry_id": approval.inquiry_id,
                "reason": approval.reason,
            },
        )
        for approval in approvals
    ]


def _followup_alerts(session: Session, seller_id: int, now: datetime) -> list[dict[str, Any]]:
    due = session.scalars(
        select(models.FollowupTask)
        .where(models.FollowupTask.seller_id == seller_id)
        .where(models.FollowupTask.status == "active")
        .where(models.FollowupTask.next_run_at <= now)
        .order_by(models.FollowupTask.next_run_at.asc(), models.FollowupTask.id.asc())
        .limit(50)
    ).all()
    paused = session.scalars(
        select(models.FollowupTask)
        .where(models.FollowupTask.seller_id == seller_id)
        .where(models.FollowupTask.status == "paused")
        .order_by(models.FollowupTask.updated_at.desc(), models.FollowupTask.id.desc())
        .limit(50)
    ).all()
    return [_due_followup_alert(task) for task in due] + [_paused_followup_alert(task) for task in paused]


def _channel_credential_alerts(session: Session, seller_id: int, now: datetime) -> list[dict[str, Any]]:
    channels = session.scalars(
        select(models.ChannelAccount)
        .where(models.ChannelAccount.seller_id == seller_id)
        .order_by(models.ChannelAccount.id.asc())
        .limit(100)
    ).all()
    alerts: list[dict[str, Any]] = []
    for channel in channels:
        alerts.extend(_channel_alerts(channel, now))
    return alerts


def _channel_alerts(channel: models.ChannelAccount, now: datetime) -> list[dict[str, Any]]:
    if channel.status in {"error", "expired", "disconnected"}:
        return [
            _channel_alert(
                "critical",
                "channel_disconnected",
                f"{channel.channel_type} channel is {channel.status}",
                channel,
                {"status": channel.status},
            )
        ]
    if channel.status != "connected":
        return []
    try:
        credentials = reveal_credentials(channel.credentials)
    except CredentialsError as exc:
        return [
            _channel_alert(
                "critical",
                "channel_credential_attention",
                f"{channel.channel_type} credentials cannot be opened",
                channel,
                {"error": str(exc)},
            )
        ]

    alerts: list[dict[str, Any]] = []
    missing = _missing_required_credentials(channel, credentials)
    if missing:
        alerts.append(
            _channel_alert(
                "critical",
                "channel_credential_attention",
                f"{channel.channel_type} channel is missing required credentials",
                channel,
                {"missing": missing},
            )
        )
    expiry = _credential_expiry_alert(channel, credentials, now)
    if expiry is not None:
        alerts.append(expiry)
    key_status = credentials_key_status(channel.credentials)
    if key_status in {"legacy", "plaintext"}:
        alerts.append(
            _channel_alert(
                "warning",
                "channel_credential_attention",
                f"{channel.channel_type} credentials need seal rotation",
                channel,
                {"credentials_key_status": key_status},
            )
        )
    return alerts


def _missing_required_credentials(channel: models.ChannelAccount, credentials: dict[str, Any]) -> list[str]:
    if channel.channel_type == "email":
        missing = [key for key in REQUIRED_EMAIL_KEYS if credentials.get(key) in (None, "")]
        if not any(credentials.get(key) not in (None, "") for key in ("imap_host", "host")):
            missing.append("imap_host")
        if not any(credentials.get(key) not in (None, "") for key in ("smtp_host", "host")):
            missing.append("smtp_host")
        return missing
    elif channel.channel_type == "whatsapp":
        required = REQUIRED_WHATSAPP_KEYS
    else:
        return []
    return [key for key in required if credentials.get(key) in (None, "")]


def _credential_expiry_alert(
    channel: models.ChannelAccount,
    credentials: dict[str, Any],
    now: datetime,
) -> dict[str, Any] | None:
    raw = (
        credentials.get("expires_at")
        or credentials.get("token_expires_at")
        or credentials.get("access_token_expires_at")
        or credentials.get("oauth_expires_at")
    )
    expires_at = _expiry_datetime(raw)
    if expires_at is None:
        return None
    if expires_at.tzinfo is None and now.tzinfo is not None:
        comparable_now = now.replace(tzinfo=None)
    elif expires_at.tzinfo is not None and now.tzinfo is None:
        comparable_now = now.replace(tzinfo=expires_at.tzinfo)
    elif expires_at.tzinfo is not None:
        comparable_now = now.astimezone(expires_at.tzinfo)
    else:
        comparable_now = now
    if expires_at <= comparable_now:
        return _channel_alert(
            "critical",
            "channel_credential_attention",
            f"{channel.channel_type} credential token has expired",
            channel,
            {"expires_at": expires_at.isoformat()},
        )
    if expires_at <= comparable_now + timedelta(days=3):
        return _channel_alert(
            "warning",
            "channel_credential_attention",
            f"{channel.channel_type} credential token expires soon",
            channel,
            {"expires_at": expires_at.isoformat()},
        )
    return None


def _exchange_cache_alerts(session: Session, seller_id: int, today: date) -> list[dict[str, Any]]:
    rules = session.scalars(
        select(models.PricingRule)
        .where(models.PricingRule.seller_id == seller_id)
        .where(models.PricingRule.deleted_at.is_(None))
        .order_by(models.PricingRule.id.asc())
        .limit(100)
    ).all()
    alerts = []
    for rule in rules:
        cache = (rule.logistics_template or {}).get("exchange_rate_cache")
        if not isinstance(cache, dict):
            continue
        status = _exchange_cache_status(cache, today)
        if status is None:
            continue
        severity, message = status
        alerts.append(
            _alert(
                severity,
                "exchange_rate_cache_attention",
                message,
                "pricing_rule",
                rule.id,
                rule.updated_at,
                {"exchange_source": rule.exchange_source, "currency": rule.currency},
            )
        )
    return alerts


def _due_followup_alert(task: models.FollowupTask) -> dict[str, Any]:
    return _alert(
        "warning",
        "due_followup",
        "Follow-up task is due and waiting for the worker",
        "followup_task",
        task.id,
        task.next_run_at or task.updated_at,
        {
            "inquiry_id": task.inquiry_id,
            "conversation_id": task.conversation_id,
            "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
        },
    )


def _paused_followup_alert(task: models.FollowupTask) -> dict[str, Any]:
    return _alert(
        "warning",
        "paused_followup",
        "Follow-up task is paused",
        "followup_task",
        task.id,
        task.updated_at,
        {
            "inquiry_id": task.inquiry_id,
            "conversation_id": task.conversation_id,
            "stop_reason": task.stop_reason,
        },
    )


def _exchange_cache_status(cache: dict[str, Any], today: date) -> tuple[str, str] | None:
    if cache.get("confirmed") is not True:
        return "warning", "Exchange rate cache is not manually confirmed"
    expires_at = _expiry_date(cache.get("expires_at"))
    if expires_at is None:
        return "critical", "Exchange rate cache is missing expires_at"
    if expires_at < today:
        return "warning", "Exchange rate cache has expired"
    return None


def _alert(
    severity: str,
    code: str,
    message: str,
    target_type: str,
    target_id: int,
    created_at,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "target_type": target_type,
        "target_id": target_id,
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
        "details": details,
    }


def _channel_alert(
    severity: str,
    code: str,
    message: str,
    channel: models.ChannelAccount,
    details: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "channel_type": channel.channel_type,
        "channel_name": channel.name,
        **details,
    }
    return _alert(severity, code, message, "channel_account", channel.id, channel.updated_at, payload)


def _expiry_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


def _expiry_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _counts(alerts: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "critical": sum(1 for alert in alerts if alert["severity"] == "critical"),
        "warning": sum(1 for alert in alerts if alert["severity"] == "warning"),
    }


def _status(counts: dict[str, int]) -> str:
    if counts["critical"]:
        return "critical"
    if counts["warning"]:
        return "attention"
    return "ok"


def _severity_rank(severity: str) -> int:
    return {"critical": 2, "warning": 1}.get(severity, 0)
