from fastapi import Depends, FastAPI
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_session, utcnow
from app.dependencies import get_seller_id
from app.errors import add_error_handlers, api_error
from app.schemas import InboundMessage, InquiryPatch, MessageCreate, WebhookIngestResponse
from app.services.channel_gateway import ingest_inbound_message
from app.services.whatsapp_adapter import WhatsAppAdapter


def create_app(create_db_on_startup: bool = True) -> FastAPI:
    app = FastAPI(title="Closer API", version="0.1.0")
    add_error_handlers(app)

    @app.on_event("startup")
    def create_tables() -> None:
        if create_db_on_startup:
            Base.metadata.create_all(engine)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/webhooks/{channel}", response_model=WebhookIngestResponse, status_code=201)
    def ingest_webhook(
        channel: str,
        payload: dict,
        seller_id: int = Depends(get_seller_id),
        session: Session = Depends(get_session),
    ) -> WebhookIngestResponse:
        if payload.get("channel") and payload["channel"] != channel:
            raise api_error(400, "channel_mismatch", "Path channel must match payload channel")
        if channel == "site_form":
            inbound = InboundMessage.model_validate(payload)
        elif channel == "whatsapp":
            try:
                inbound = WhatsAppAdapter().normalize_webhook(payload)
            except ValueError as exc:
                raise api_error(400, "invalid_webhook_payload", str(exc)) from exc
        else:
            raise api_error(400, "unsupported_channel", f"{channel} webhook is not implemented")
        if channel != inbound.channel:
            raise api_error(400, "channel_mismatch", "Path channel must match payload channel")
        inquiry, conversation, message, duplicate = ingest_inbound_message(session, seller_id, inbound)
        session.commit()
        return WebhookIngestResponse(
            inquiry_id=inquiry.id,
            conversation_id=conversation.id,
            message_id=message.id,
            customer_id=inquiry.customer_id,
            duplicate=duplicate,
        )

    @app.get("/api/v1/inquiries")
    def list_inquiries(
        status: str | None = None,
        grade: str | None = None,
        channel: str | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 20,
        seller_id: int = Depends(get_seller_id),
        session: Session = Depends(get_session),
    ) -> dict:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        query = select(models.Inquiry).where(models.Inquiry.seller_id == seller_id)
        count_query = select(func.count()).select_from(models.Inquiry).where(models.Inquiry.seller_id == seller_id)
        for condition in _inquiry_filters(status, grade, channel, q):
            query = query.where(condition)
            count_query = count_query.where(condition)
        query = query.order_by(models.Inquiry.received_at.desc().nullslast(), models.Inquiry.id.desc())
        total = session.scalar(count_query) or 0
        inquiries = session.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
        return {
            "items": [_inquiry_list_item(session, inquiry) for inquiry in inquiries],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @app.get("/api/v1/inquiries/{inquiry_id}")
    def get_inquiry_detail(
        inquiry_id: int,
        seller_id: int = Depends(get_seller_id),
        session: Session = Depends(get_session),
    ) -> dict:
        inquiry = _require_inquiry(session, seller_id, inquiry_id)
        return _inquiry_detail(session, inquiry)

    @app.patch("/api/v1/inquiries/{inquiry_id}")
    def patch_inquiry(
        inquiry_id: int,
        patch: InquiryPatch,
        seller_id: int = Depends(get_seller_id),
        session: Session = Depends(get_session),
    ) -> dict:
        inquiry = _require_inquiry(session, seller_id, inquiry_id)
        if patch.grade is not None:
            if patch.grade not in {"A", "B", "C"}:
                raise api_error(422, "invalid_grade", "grade must be A, B, or C")
            inquiry.grade = patch.grade
        if patch.status is not None:
            inquiry.status = patch.status
        session.add(
            models.AuditLog(
                seller_id=seller_id,
                actor="human",
                action_type="inquiry_patched",
                target_type="inquiry",
                target_id=inquiry.id,
                is_auto=False,
                snapshot=patch.model_dump(exclude_none=True),
            )
        )
        session.commit()
        return _inquiry_detail(session, inquiry)

    @app.get("/api/v1/conversations/{conversation_id}")
    def get_conversation(
        conversation_id: int,
        seller_id: int = Depends(get_seller_id),
        session: Session = Depends(get_session),
    ) -> dict:
        conversation = _require_conversation(session, seller_id, conversation_id)
        customer = session.get(models.Customer, conversation.customer_id)
        return {
            "id": conversation.id,
            "inquiry_id": conversation.inquiry_id,
            "customer": _customer_summary(customer),
            "channel": conversation.channel,
            "language": conversation.language,
            "is_human_takeover": conversation.is_human_takeover,
            "status": conversation.status,
        }

    @app.get("/api/v1/conversations/{conversation_id}/messages")
    def list_messages(
        conversation_id: int,
        seller_id: int = Depends(get_seller_id),
        session: Session = Depends(get_session),
    ) -> dict:
        conversation = _require_conversation(session, seller_id, conversation_id)
        query = (
            select(models.Message)
            .where(models.Message.conversation_id == conversation.id)
            .order_by(models.Message.sent_at.asc().nullslast(), models.Message.id.asc())
        )
        messages = session.scalars(query).all()
        return {"items": [_message_item(message) for message in messages], "total": len(messages)}

    @app.post("/api/v1/conversations/{conversation_id}/messages", status_code=201)
    def create_message(
        conversation_id: int,
        payload: MessageCreate,
        seller_id: int = Depends(get_seller_id),
        session: Session = Depends(get_session),
    ) -> dict:
        conversation = _require_conversation(session, seller_id, conversation_id)
        if not conversation.is_human_takeover:
            raise api_error(409, "conversation_not_taken_over", "Human messages require takeover mode")
        message = models.Message(
            conversation_id=conversation.id,
            sender_role="human",
            content=payload.content,
            language=payload.language or conversation.language,
            sent_at=utcnow(),
        )
        session.add(message)
        session.add(
            models.AuditLog(
                seller_id=seller_id,
                actor="human",
                action_type="reply_sent",
                target_type="conversation",
                target_id=conversation.id,
                is_auto=False,
                snapshot={"content": payload.content},
            )
        )
        session.commit()
        return _message_item(message) | {"status": "sent"}

    @app.post("/api/v1/conversations/{conversation_id}/takeover")
    def takeover_conversation(
        conversation_id: int,
        seller_id: int = Depends(get_seller_id),
        session: Session = Depends(get_session),
    ) -> dict:
        conversation = _require_conversation(session, seller_id, conversation_id)
        conversation.is_human_takeover = True
        session.commit()
        return {"id": conversation.id, "is_human_takeover": True}

    @app.post("/api/v1/conversations/{conversation_id}/release")
    def release_conversation(
        conversation_id: int,
        seller_id: int = Depends(get_seller_id),
        session: Session = Depends(get_session),
    ) -> dict:
        conversation = _require_conversation(session, seller_id, conversation_id)
        conversation.is_human_takeover = False
        session.commit()
        return {"id": conversation.id, "is_human_takeover": False}

    return app


app = create_app()


def _inquiry_filters(status: str | None, grade: str | None, channel: str | None, q: str | None):
    filters = []
    if status:
        filters.append(models.Inquiry.status == status)
    if grade:
        filters.append(models.Inquiry.grade == grade)
    if channel:
        filters.append(models.Inquiry.source_channel == channel)
    if q:
        like = f"%{q}%"
        filters.append(or_(models.Inquiry.raw_content.ilike(like), models.Inquiry.source_channel.ilike(like)))
    return filters


def _require_inquiry(session: Session, seller_id: int, inquiry_id: int) -> models.Inquiry:
    inquiry = session.get(models.Inquiry, inquiry_id)
    if inquiry is None or inquiry.seller_id != seller_id:
        raise api_error(404, "inquiry_not_found", "Inquiry not found")
    return inquiry


def _require_conversation(session: Session, seller_id: int, conversation_id: int) -> models.Conversation:
    conversation = session.get(models.Conversation, conversation_id)
    if conversation is None or conversation.seller_id != seller_id:
        raise api_error(404, "conversation_not_found", "Conversation not found")
    return conversation


def _customer_summary(customer: models.Customer | None) -> dict | None:
    if customer is None:
        return None
    return {
        "id": customer.id,
        "company": customer.company,
        "name": customer.name,
        "country": customer.country,
        "email": customer.email,
        "phone": customer.phone,
    }


def _inquiry_list_item(session: Session, inquiry: models.Inquiry) -> dict:
    customer = session.get(models.Customer, inquiry.customer_id)
    return {
        "id": inquiry.id,
        "customer": _customer_summary(customer),
        "source_channel": inquiry.source_channel,
        "grade": inquiry.grade,
        "score": float(inquiry.score) if inquiry.score is not None else None,
        "status": inquiry.status,
        "summary": inquiry.raw_content[:160] if inquiry.raw_content else None,
        "received_at": inquiry.received_at,
    }


def _inquiry_detail(session: Session, inquiry: models.Inquiry) -> dict:
    return _inquiry_list_item(session, inquiry) | {
        "customer_id": inquiry.customer_id,
        "raw_content": inquiry.raw_content,
        "parsed": inquiry.parsed or {},
        "language": inquiry.language,
    }


def _message_item(message: models.Message) -> dict:
    return {
        "id": message.id,
        "sender_role": message.sender_role,
        "content": message.content,
        "language": message.language,
        "sent_at": message.sent_at,
    }
