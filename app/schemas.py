from datetime import date, datetime
from decimal import Decimal
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


class KnowledgeCreate(BaseModel):
    source_type: str = Field(default="faq", min_length=1, max_length=20)
    source_ref: str | None = Field(default=None, max_length=120)
    content: str = Field(min_length=1)


class ApprovalPatch(BaseModel):
    payload: dict[str, Any] | None = None
    suggestion: str | None = None
    summary: str | None = None


class ApprovalReject(BaseModel):
    reason: str | None = None


class QuotationItemPatch(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Decimal
    amount: Decimal | None = None


class QuotationPatch(BaseModel):
    terms: dict[str, Any] | None = None
    valid_until: date | None = None
    status: str | None = None
    total_amount: Decimal | None = None
    hits_floor: bool | None = None
    items: list[QuotationItemPatch] | None = None
