from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.database import utcnow


def get_quotation(session: Session, seller_id: int, quotation_id: int) -> models.Quotation:
    quotation = session.get(models.Quotation, quotation_id)
    if quotation is None or quotation.seller_id != seller_id:
        raise LookupError("Quotation not found")
    return quotation


def patch_quotation(
    session: Session,
    seller_id: int,
    quotation_id: int,
    *,
    terms: dict[str, Any] | None = None,
    valid_until=None,
    status: str | None = None,
    total_amount: Decimal | None = None,
    hits_floor: bool | None = None,
    items: list[dict[str, Any]] | None = None,
) -> models.Quotation:
    quotation = get_quotation(session, seller_id, quotation_id)
    if terms is not None:
        merged_terms = dict(quotation.terms or {})
        merged_terms.update(terms)
        quotation.terms = merged_terms
    if valid_until is not None:
        quotation.valid_until = valid_until
    if status is not None:
        quotation.status = status
    if hits_floor is not None:
        quotation.hits_floor = hits_floor
    if items is not None:
        quotation.items.clear()
        computed_total = Decimal("0")
        for item in items:
            quantity = int(item["quantity"])
            unit_price = _money(item["unit_price"])
            amount = _money(item.get("amount") or unit_price * Decimal(quantity))
            computed_total += amount
            quotation.items.append(
                models.QuotationItem(
                    product_id=int(item["product_id"]),
                    quantity=quantity,
                    unit_price=unit_price,
                    amount=amount,
                )
            )
        quotation.total_amount = _money(total_amount or computed_total)
    elif total_amount is not None:
        quotation.total_amount = _money(total_amount)

    session.add(
        models.AuditLog(
            seller_id=seller_id,
            actor="human",
            action_type="quotation_patched",
            target_type="quotation",
            target_id=quotation.id,
            is_auto=False,
            snapshot={"status": quotation.status, "total_amount": str(quotation.total_amount)},
        )
    )
    session.flush()
    return quotation


def send_quotation(
    session: Session,
    seller_id: int,
    quotation_id: int,
    *,
    approved: bool = False,
) -> dict:
    quotation = get_quotation(session, seller_id, quotation_id)
    if quotation.hits_floor and not approved:
        raise PermissionError("below_floor_price")

    conversation = session.scalar(
        select(models.Conversation).where(
            models.Conversation.seller_id == seller_id,
            models.Conversation.inquiry_id == quotation.inquiry_id,
        )
    )
    if conversation is None:
        raise LookupError("Conversation not found")

    content = _quote_message(quotation)
    message = models.Message(
        conversation_id=conversation.id,
        sender_role="ai",
        content=content,
        language=conversation.language,
        sent_at=utcnow(),
    )
    quotation.status = "sent"
    session.add(message)
    session.flush()
    session.add(
        models.AuditLog(
            seller_id=seller_id,
            actor="ai" if approved else "human",
            action_type="quotation_sent",
            target_type="quotation",
            target_id=quotation.id,
            is_auto=approved,
            snapshot={"message_id": message.id, "approved": approved},
        )
    )
    session.flush()
    return {"status": "sent", "quotation_id": quotation.id, "message_id": message.id}


def _quote_message(quotation: models.Quotation) -> str:
    terms = quotation.terms or {}
    if terms.get("message"):
        return str(terms["message"])
    return f"Quotation #{quotation.id}: {quotation.currency} {quotation.total_amount}"


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
