from sqlalchemy.orm import Session

from app import models
from app.services.crm import get_customer_profile
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

