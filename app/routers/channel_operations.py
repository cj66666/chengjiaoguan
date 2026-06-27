"""
/* ========================================================================== */
/* GEB L3: 渠道运维路由                                                       */
/* ========================================================================== */
/**
 * [INPUT]: 依赖 FastAPI APIRouter/Depends、email_polling、channel_receipts 服务与租户依赖
 * [OUTPUT]: 对外提供 router，暴露 email channel 的 poll-email 入站轮询接口与渠道 delivery receipt 同步接口
 * [POS]: routers 的渠道运维边界，连接渠道配置、入站轮询任务与出站回执同步
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
"""

import imaplib
import socket

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_session
from app.dependencies import get_seller_id
from app.errors import api_error
from app.schemas import ChannelDeliveryTest
from app.services.channel_receipts import sync_channel_receipts
from app.services.channel_test_delivery import test_channel_delivery
from app.services.email_polling import poll_email_channel


router = APIRouter(prefix="/api/v1")


@router.post("/channels/{channel_account_id}/poll-email")
def poll_email_channel_endpoint(
    channel_account_id: int,
    limit: int = 20,
    seller_id: int = Depends(get_seller_id),
    session: Session = Depends(get_session),
) -> dict:
    try:
        result = poll_email_channel(session, seller_id, channel_account_id, limit=limit)
    except LookupError as exc:
        raise api_error(404, "channel_not_found", "Email channel account not found") from exc
    except imaplib.IMAP4.error as exc:
        raise api_error(422, "email_poll_failed", _friendly_email_poll_error(exc)) from exc
    except (OSError, socket.timeout) as exc:
        raise api_error(422, "email_poll_failed", _friendly_email_poll_error(exc)) from exc
    except ValueError as exc:
        raise api_error(422, "email_poll_failed", _friendly_email_poll_error(exc)) from exc
    session.commit()
    return result


@router.post("/channels/{channel_account_id}/sync-receipts")
def sync_channel_receipts_endpoint(
    channel_account_id: int,
    payload: dict,
    seller_id: int = Depends(get_seller_id),
    session: Session = Depends(get_session),
) -> dict:
    try:
        result = sync_channel_receipts(session, seller_id, channel_account_id, payload)
    except LookupError as exc:
        raise api_error(404, "channel_not_found", "Channel account not found") from exc
    except ValueError as exc:
        raise api_error(422, "invalid_delivery_receipt", str(exc)) from exc
    session.commit()
    return result


@router.post("/channels/{channel_account_id}/test-delivery")
def test_channel_delivery_endpoint(
    channel_account_id: int,
    payload: ChannelDeliveryTest,
    seller_id: int = Depends(get_seller_id),
    session: Session = Depends(get_session),
) -> dict:
    try:
        result = test_channel_delivery(session, seller_id, channel_account_id, payload.model_dump(by_alias=True))
    except LookupError as exc:
        raise api_error(404, "channel_not_found", "Channel account not found") from exc
    except ValueError as exc:
        raise api_error(422, "invalid_test_delivery", str(exc)) from exc
    return result


def _friendly_email_poll_error(exc: Exception) -> str:
    message = str(exc)
    lower = message.lower()
    if "imap_host" in lower or "smtp_host" in lower or "username" in lower or "password" in lower or "credential is required" in lower:
        return "邮箱通道凭据不完整，请检查 IMAP/SMTP 主机、账号和应用专用密码。"
    if "authenticationfailed" in lower or "invalid credentials" in lower or "application-specific password" in lower or "login failed" in lower:
        return "Gmail 登录失败。请确认 IMAP 已开启，并使用 Gmail 应用专用密码，不是普通登录密码。"
    if "timed out" in lower or "timeout" in lower or "getaddrinfo" in lower or "network is unreachable" in lower or "name or service not known" in lower:
        return "无法连接邮箱服务器。请确认网络可用，IMAP 主机为 imap.gmail.com、端口为 993，并已勾选 SSL。"
    return message
