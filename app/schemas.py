from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChannelContact(BaseModel):
    name: str | None = None
    company: str | None = None
    country: str | None = None
    email: str | None = None
    phone: str | None = None


class InboundMessage(BaseModel):
    channel: Literal["site_form", "email", "whatsapp"]
    channel_message_id: str
    from_: ChannelContact = Field(alias="from")
    content: str
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    received_at: datetime | None = None
    language: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class WebhookIngestResponse(BaseModel):
    inquiry_id: int
    conversation_id: int
    message_id: int
    customer_id: int
    duplicate: bool = False


class InquiryPatch(BaseModel):
    grade: str | None = None
    status: str | None = None


class MessageCreate(BaseModel):
    content: str
    language: str | None = None
