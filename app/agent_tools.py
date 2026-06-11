"""
/* ========================================================================== */
/* GEB L3: Agent 工具门面                                                     */
/* ========================================================================== */
/**
 * [INPUT]: 依赖 SQLAlchemy Session、app.models 与 services 的确定性业务能力、notifications 审批提醒
 * [OUTPUT]: 对外提供 get_inquiry、score_inquiry、get_customer、calc_quote、generate_pi、search_knowledge、match_product、send_message、create_followup、request_handoff
 * [POS]: app 的 Agent 工具稳定签名层，被 app.agent.tools 和 Role B 编排层调用
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
"""

from sqlalchemy.orm import Session

from app import models
from app.services.approvals import request_handoff as request_handoff_service
from app.services.crm import get_customer_profile
from app.services.followups import create_followup as create_followup_service
from app.services.knowledge import search_knowledge as search_knowledge_service
from app.services.notifications import notify_approval_requested
from app.services.outbound import send_message as send_message_service
from app.services.product_matching import match_product as match_product_service
from app.services.quote_engine import QuoteItemInput, calculate_quote
from app.services.quote_language import render_quote_message
from app.services.quotations import quotation_hard_minimum_violations
from app.services.scoring import score_inquiry as score_inquiry_service


def get_inquiry(session: Session, seller_id: int, inquiry_id: int) -> dict:
    inquiry = session.get(models.Inquiry, inquiry_id)
    if inquiry is None or inquiry.seller_id != seller_id:
        raise LookupError("Inquiry not found")
    return {
        "id": inquiry.id,
        "parsed": inquiry.parsed or {},
        "grade": inquiry.grade,
        "language": inquiry.language,
    }


def score_inquiry(session: Session, seller_id: int, inquiry_id: int) -> dict:
    result = score_inquiry_service(session, seller_id, inquiry_id)
    return {
        "grade": result.grade,
        "score": float(result.score),
        "signals": result.signals,
    }


def get_customer(
    session: Session,
    seller_id: int,
    customer_id: int | None = None,
    inquiry_id: int | None = None,
) -> dict:
    return get_customer_profile(
        session,
        seller_id,
        customer_id=customer_id,
        inquiry_id=inquiry_id,
    )


def calc_quote(
    session: Session,
    seller_id: int,
    inquiry_id: int,
    items: list[dict],
    destination: str | None = None,
    currency: str = "USD",
) -> dict:
    inputs = [
        QuoteItemInput(product_id=int(item["product_id"]), quantity=int(item["quantity"]))
        for item in items
    ]
    result = calculate_quote(
        session,
        seller_id,
        inquiry_id,
        inputs,
        destination=destination,
        currency=currency,
    )
    inquiry = session.get(models.Inquiry, inquiry_id)
    if inquiry is None:
        raise LookupError("Inquiry not found")
    guardrails = {
        "hits_floor": result.hits_floor,
        "hard_minimum_breached": result.hard_minimum_breached,
        "lines": [
            {
                "product_id": line.product_id,
                "floor_price": str(line.floor_price),
                "hard_min_price": str(line.hard_min_price) if line.hard_min_price is not None else None,
                "hits_floor": line.hits_floor,
                "hard_minimum_breached": line.hard_minimum_breached,
            }
            for line in result.lines
        ],
    }
    quotation = models.Quotation(
        seller_id=seller_id,
        inquiry_id=inquiry.id,
        customer_id=inquiry.customer_id,
        currency=result.currency,
        total_amount=result.total_amount,
        valid_until=result.valid_until,
        is_pi=False,
        status="draft",
        created_by="ai",
        hits_floor=result.hits_floor,
        terms={"message": render_quote_message(result), "guardrails": guardrails},
    )
    session.add(quotation)
    session.flush()
    for line in result.lines:
        session.add(
            models.QuotationItem(
                quotation_id=quotation.id,
                product_id=line.product_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                amount=line.amount,
            )
        )
    session.add(
        models.AuditLog(
            seller_id=seller_id,
            actor="ai",
            action_type="quote_drafted",
            target_type="quotation",
            target_id=quotation.id,
            is_auto=True,
            snapshot={
                "hits_floor": result.hits_floor,
                "hard_minimum_breached": result.hard_minimum_breached,
                "total_amount": str(result.total_amount),
            },
        )
    )
    session.flush()
    return {
        "quotation_id": quotation.id,
        "currency": result.currency,
        "total_amount": float(result.total_amount),
        "valid_until": result.valid_until.isoformat(),
        "hits_floor": result.hits_floor,
        "hard_minimum_breached": result.hard_minimum_breached,
        "message": quotation.terms["message"],
        "lines": [
            {
                "product_id": line.product_id,
                "quantity": line.quantity,
                "unit_price": float(line.unit_price),
                "amount": float(line.amount),
                "floor_price": float(line.floor_price),
                "hard_min_price": float(line.hard_min_price) if line.hard_min_price is not None else None,
                "hard_minimum_breached": line.hard_minimum_breached,
            }
            for line in result.lines
        ],
    }


def generate_pi(session: Session, seller_id: int, quotation_id: int) -> dict:
    quotation = session.get(models.Quotation, quotation_id)
    if quotation is None or quotation.seller_id != seller_id:
        raise LookupError("Quotation not found")
    violations = quotation_hard_minimum_violations(session, seller_id, quotation)
    if violations:
        session.add(
            models.AuditLog(
                seller_id=seller_id,
                actor="ai",
                action_type="pi_generation_blocked",
                target_type="quotation",
                target_id=quotation.id,
                is_auto=True,
                snapshot={"reason": "hard_minimum_price", "violations": violations},
            )
        )
        session.flush()
        return {
            "quotation_id": quotation.id,
            "status": "blocked",
            "reason": "hard_minimum_price",
            "violations": violations,
        }
    conversation = session.query(models.Conversation).filter_by(
        seller_id=seller_id,
        inquiry_id=quotation.inquiry_id,
    ).one_or_none()
    if conversation is None:
        raise LookupError("Conversation not found")
    approval = models.Approval(
        seller_id=seller_id,
        conversation_id=conversation.id,
        inquiry_id=quotation.inquiry_id,
        type="pi_generate",
        reason="pi_requires_approval",
        summary=f"Generate PI for quotation #{quotation.id} before sending formal invoice content.",
        suggestion="Review buyer, item, amount, validity, and terms before approving PI generation.",
        payload={"quotation_id": quotation.id},
        status="pending",
        executed=False,
    )
    conversation.is_human_takeover = True
    session.add(
        approval,
    )
    session.flush()
    notify_approval_requested(session, approval)
    session.add(
        models.AuditLog(
            seller_id=seller_id,
            actor="ai",
            action_type="approval_requested",
            target_type="approval",
            target_id=approval.id,
            is_auto=True,
            snapshot={"type": "pi_generate", "quotation_id": quotation.id},
        )
    )
    session.flush()
    return {
        "quotation_id": quotation.id,
        "status": "pending_approval",
        "approval_id": approval.id,
        "reason": approval.reason,
    }


def search_knowledge(
    session: Session,
    seller_id: int,
    query: str,
    source_type: str | None = None,
    limit: int = 5,
) -> list[dict]:
    return search_knowledge_service(
        session,
        seller_id,
        query=query,
        source_type=source_type,
        limit=limit,
    )


def match_product(
    session: Session,
    seller_id: int,
    requirement: str | dict,
    limit: int = 5,
) -> list[dict]:
    return match_product_service(session, seller_id, requirement, limit=limit)


def send_message(
    session: Session,
    seller_id: int,
    conversation_id: int,
    content: str,
    language: str | None = None,
) -> dict:
    return send_message_service(
        session,
        seller_id,
        conversation_id=conversation_id,
        content=content,
        language=language,
    )


def create_followup(
    session: Session,
    seller_id: int,
    inquiry_id: int,
    conversation_id: int | None = None,
    delay_hours: int = 24,
    message: str | None = None,
    max_attempts: int = 3,
) -> dict:
    return create_followup_service(
        session,
        seller_id,
        inquiry_id=inquiry_id,
        conversation_id=conversation_id,
        delay_hours=delay_hours,
        message=message,
        max_attempts=max_attempts,
    )


def request_handoff(
    session: Session,
    seller_id: int,
    conversation_id: int,
    reason: str,
    summary: str,
    suggestion: str | None = None,
    payload: dict | None = None,
) -> dict:
    approval = request_handoff_service(
        session,
        seller_id,
        conversation_id=conversation_id,
        reason=reason,
        summary=summary,
        suggestion=suggestion,
        payload=payload,
    )
    return {"approval_id": approval.id, "status": approval.status, "reason": approval.reason}
