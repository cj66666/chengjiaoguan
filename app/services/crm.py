from sqlalchemy.orm import Session

from app import models


def get_customer_profile(
    session: Session,
    seller_id: int,
    *,
    customer_id: int | None = None,
    inquiry_id: int | None = None,
) -> dict:
    if customer_id is None and inquiry_id is not None:
        inquiry = session.get(models.Inquiry, inquiry_id)
        if inquiry is None or inquiry.seller_id != seller_id:
            raise LookupError("Inquiry not found")
        customer_id = inquiry.customer_id
    if customer_id is None:
        raise ValueError("customer_id or inquiry_id is required")

    customer = session.get(models.Customer, customer_id)
    if customer is None or customer.seller_id != seller_id:
        raise LookupError("Customer not found")

    return {
        "id": customer.id,
        "name": customer.name,
        "company": customer.company,
        "country": customer.country,
        "email": customer.email,
        "phone": customer.phone,
        "channels": customer.channels or {},
        "grade": customer.grade,
        "enrichment": customer.enrichment or {},
        "preferences": customer.preferences or {},
        "status": customer.status,
    }

