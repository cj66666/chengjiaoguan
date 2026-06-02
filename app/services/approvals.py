from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.database import utcnow
from app.services.quotations import send_quotation


def list_approvals(session: Session, seller_id: int, *, status: str | None = "pending") -> list[models.Approval]:
    statement = select(models.Approval).where(models.Approval.seller_id == seller_id)
    if status:
        statement = statement.where(models.Approval.status == status)
    return session.scalars(statement.order_by(models.Approval.id.desc())).all()


def patch_approval(
    session: Session,
    seller_id: int,
    approval_id: int,
    *,
    payload: dict[str, Any] | None = None,
    suggestion: str | None = None,
    summary: str | None = None,
) -> models.Approval:
    approval = _require_pending_approval(session, seller_id, approval_id)
    if payload is not None:
        merged_payload = dict(approval.payload or {})
        merged_payload.update(payload)
        approval.payload = merged_payload
    if suggestion is not None:
        approval.suggestion = suggestion
    if summary is not None:
        approval.summary = summary
    session.add(
        models.AuditLog(
            seller_id=seller_id,
            actor="human",
            action_type="approval_patched",
            target_type="approval",
            target_id=approval.id,
            is_auto=False,
            snapshot={"payload": approval.payload, "suggestion": approval.suggestion},
        )
    )
    session.flush()
    return approval


def approve_approval(session: Session, seller_id: int, approval_id: int) -> dict:
    approval = _require_pending_approval(session, seller_id, approval_id)
    result = _execute_approval(session, approval)
    approval.status = "approved"
    approval.executed = True
    session.add(
        models.AuditLog(
            seller_id=seller_id,
            actor="human",
            action_type="approval_approved",
            target_type="approval",
            target_id=approval.id,
            is_auto=False,
            snapshot={"result": result},
        )
    )
    session.flush()
    return {"id": approval.id, "status": approval.status, "executed": approval.executed, "result": result}


def reject_approval(session: Session, seller_id: int, approval_id: int, *, reason: str | None = None) -> dict:
    approval = _require_pending_approval(session, seller_id, approval_id)
    payload = dict(approval.payload or {})
    if reason:
        payload["reject_reason"] = reason
    approval.payload = payload
    approval.status = "rejected"
    approval.executed = False
    session.add(
        models.AuditLog(
            seller_id=seller_id,
            actor="human",
            action_type="approval_rejected",
            target_type="approval",
            target_id=approval.id,
            is_auto=False,
            snapshot={"reason": reason},
        )
    )
    session.flush()
    return {"id": approval.id, "status": approval.status, "executed": approval.executed}


def _require_pending_approval(session: Session, seller_id: int, approval_id: int) -> models.Approval:
    approval = session.get(models.Approval, approval_id)
    if approval is None or approval.seller_id != seller_id:
        raise LookupError("Approval not found")
    if approval.status != "pending":
        raise ValueError("Approval is not pending")
    return approval


def _execute_approval(session: Session, approval: models.Approval) -> dict:
    if approval.type == "message_send":
        return _execute_message_send(session, approval)
    if approval.type == "quotation_send":
        quotation_id = int((approval.payload or {})["quotation_id"])
        return send_quotation(session, approval.seller_id, quotation_id, approved=True)
    raise ValueError(f"Unsupported approval type: {approval.type}")


def _execute_message_send(session: Session, approval: models.Approval) -> dict:
    conversation = session.get(models.Conversation, approval.conversation_id)
    if conversation is None or conversation.seller_id != approval.seller_id:
        raise LookupError("Conversation not found")
    payload = approval.payload or {}
    content = payload.get("content") or approval.suggestion
    if not content:
        raise ValueError("Approval payload content is required")
    message = models.Message(
        conversation_id=conversation.id,
        sender_role="ai",
        content=content,
        language=payload.get("language") or conversation.language,
        sent_at=utcnow(),
    )
    conversation.is_human_takeover = False
    inquiry = session.get(models.Inquiry, approval.inquiry_id)
    if inquiry is not None:
        inquiry.status = "responded"
    session.add(message)
    session.flush()
    return {"status": "sent", "message_id": message.id, "conversation_id": conversation.id}
