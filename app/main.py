from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.database import Base, engine, get_session
from app.dependencies import get_seller_id
from app.errors import add_error_handlers, api_error
from app.schemas import InboundMessage, WebhookIngestResponse
from app.services.channel_gateway import ingest_inbound_message


def create_app() -> FastAPI:
    app = FastAPI(title="Closer API", version="0.1.0")
    add_error_handlers(app)

    @app.on_event("startup")
    def create_tables() -> None:
        Base.metadata.create_all(engine)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/webhooks/{channel}", response_model=WebhookIngestResponse, status_code=201)
    def ingest_webhook(
        channel: str,
        payload: InboundMessage,
        seller_id: int = Depends(get_seller_id),
        session: Session = Depends(get_session),
    ) -> WebhookIngestResponse:
        if channel != payload.channel:
            raise api_error(400, "channel_mismatch", "Path channel must match payload channel")
        if channel != "site_form":
            raise api_error(400, "unsupported_channel", f"{channel} webhook is not implemented yet")
        inquiry, conversation, message, duplicate = ingest_inbound_message(session, seller_id, payload)
        session.commit()
        return WebhookIngestResponse(
            inquiry_id=inquiry.id,
            conversation_id=conversation.id,
            message_id=message.id,
            customer_id=inquiry.customer_id,
            duplicate=duplicate,
        )

    return app


app = create_app()

