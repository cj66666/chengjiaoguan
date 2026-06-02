from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from sqlalchemy.orm import Session

from app import agent_tools


@dataclass
class CloserAgentDeps:
    seller_id: int
    session: Session
    inquiry_id: int | None = None
    conversation_id: int | None = None


class CloserAgentOutput(BaseModel):
    summary: str = Field(description="Concise result or recommendation for the seller.")
    draft_response: str | None = Field(default=None, description="Draft customer-facing response when useful.")
    next_actions: list[str] = Field(
        default_factory=list,
        description="Operational actions the seller or system should take.",
    )
    requires_human_review: bool = Field(
        default=False,
        description="Whether the next action must wait for human approval.",
    )


def get_inquiry(ctx: RunContext[CloserAgentDeps], inquiry_id: int | None = None) -> dict:
    target_id = _resolve_inquiry_id(ctx, inquiry_id)
    return agent_tools.get_inquiry(ctx.deps.session, ctx.deps.seller_id, target_id)


def score_inquiry(ctx: RunContext[CloserAgentDeps], inquiry_id: int | None = None) -> dict:
    target_id = _resolve_inquiry_id(ctx, inquiry_id)
    return agent_tools.score_inquiry(ctx.deps.session, ctx.deps.seller_id, target_id)


def get_customer(
    ctx: RunContext[CloserAgentDeps],
    customer_id: int | None = None,
    inquiry_id: int | None = None,
) -> dict:
    return agent_tools.get_customer(
        ctx.deps.session,
        ctx.deps.seller_id,
        customer_id=customer_id,
        inquiry_id=inquiry_id or ctx.deps.inquiry_id,
    )


def calc_quote(
    ctx: RunContext[CloserAgentDeps],
    items: list[dict[str, Any]],
    inquiry_id: int | None = None,
    destination: str | None = None,
    currency: str = "USD",
) -> dict:
    target_id = _resolve_inquiry_id(ctx, inquiry_id)
    return agent_tools.calc_quote(
        ctx.deps.session,
        ctx.deps.seller_id,
        target_id,
        items,
        destination=destination,
        currency=currency,
    )


def generate_pi(ctx: RunContext[CloserAgentDeps], quotation_id: int) -> dict:
    return agent_tools.generate_pi(ctx.deps.session, ctx.deps.seller_id, quotation_id)


def search_knowledge(
    ctx: RunContext[CloserAgentDeps],
    query: str,
    source_type: str | None = None,
    limit: int = 5,
) -> list[dict]:
    return agent_tools.search_knowledge(
        ctx.deps.session,
        ctx.deps.seller_id,
        query,
        source_type=source_type,
        limit=limit,
    )


def build_closer_agent(model: str | None = None) -> Agent[CloserAgentDeps, CloserAgentOutput]:
    return Agent(
        model,
        deps_type=CloserAgentDeps,
        output_type=CloserAgentOutput,
        instructions=(
            "You are the operating agent for a cross-border B2B seller. "
            "Use tools before making factual claims about inquiries, customers, or quotes. "
            "Never promise discounts, payment terms, delivery guarantees, or legal commitments "
            "unless a tool result explicitly supports them. Return structured output only."
        ),
        tools=[get_inquiry, score_inquiry, get_customer, calc_quote, generate_pi, search_knowledge],
    )


closer_agent = build_closer_agent()


def run_closer_agent(
    session: Session,
    seller_id: int,
    user_prompt: str,
    *,
    inquiry_id: int | None = None,
    conversation_id: int | None = None,
    model: Any | None = None,
) -> CloserAgentOutput:
    result = closer_agent.run_sync(
        user_prompt,
        deps=CloserAgentDeps(
            seller_id=seller_id,
            session=session,
            inquiry_id=inquiry_id,
            conversation_id=conversation_id,
        ),
        model=model,
    )
    return result.output


def _resolve_inquiry_id(ctx: RunContext[CloserAgentDeps], inquiry_id: int | None) -> int:
    target_id = inquiry_id or ctx.deps.inquiry_id
    if target_id is None:
        raise ValueError("inquiry_id is required")
    return target_id
