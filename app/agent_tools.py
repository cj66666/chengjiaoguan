from sqlalchemy.orm import Session

from app import models
from app.services.crm import get_customer_profile
from app.services.quote_engine import QuoteItemInput, calculate_quote
from app.services.quote_language import render_quote_message
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
        terms={"message": render_quote_message(result)},
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
            snapshot={"hits_floor": result.hits_floor, "total_amount": str(result.total_amount)},
        )
    )
    session.flush()
    return {
        "quotation_id": quotation.id,
        "currency": result.currency,
        "total_amount": float(result.total_amount),
        "valid_until": result.valid_until.isoformat(),
        "hits_floor": result.hits_floor,
        "message": quotation.terms["message"],
        "lines": [
            {
                "product_id": line.product_id,
                "quantity": line.quantity,
                "unit_price": float(line.unit_price),
                "amount": float(line.amount),
            }
            for line in result.lines
        ],
    }


def generate_pi(session: Session, seller_id: int, quotation_id: int) -> dict:
    quotation = session.get(models.Quotation, quotation_id)
    if quotation is None or quotation.seller_id != seller_id:
        raise LookupError("Quotation not found")
    pi_number = f"PI-{quotation.id:06d}"
    terms = dict(quotation.terms or {})
    terms["pi_number"] = pi_number
    quotation.terms = terms
    quotation.is_pi = True
    session.add(
        models.AuditLog(
            seller_id=seller_id,
            actor="ai",
            action_type="pi_generated",
            target_type="quotation",
            target_id=quotation.id,
            is_auto=True,
            snapshot={"pi_number": pi_number},
        )
    )
    session.flush()
    return {
        "quotation_id": quotation.id,
        "pi_number": pi_number,
        "is_pi": True,
        "status": quotation.status,
    }

