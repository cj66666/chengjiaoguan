"""
/* ========================================================================== */
/* GEB L3: 新询盘 Agent 自动处理                                               */
/* ========================================================================== */
/**
 * [INPUT]: 依赖 SQLAlchemy Session、app.models 与 closer operating graph
 * [OUTPUT]: 对外提供 run_new_inquiry_agent_jobs，自动处理未处理的新询盘并写入审计记录
 * [POS]: services 的 agent worker 边界，把“入站事实”推进到“待审批草稿/报价/跟进”的安全闭环
 * [PROTOCOL]: 变更时同步更新 worker、scheduler 与相关测试
 */
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic_graph.graph import GraphRunResult
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.agent.graph import run_closer_graph_result
from app.agent.graph_domain.policy import GraphDecisionProvider
from app.agent.types import CloserAgentOutput, CloserGraphState


AUTO_AGENT_ACTION = "agent_auto_processed"
ELIGIBLE_INQUIRY_STATUSES = {"new", "qualified"}
GraphRunner = Callable[..., GraphRunResult[CloserGraphState, CloserAgentOutput]]


def run_new_inquiry_agent_jobs(
    session: Session,
    seller_id: int,
    *,
    limit: int = 20,
    decision_provider: GraphDecisionProvider | None = None,
    graph_runner: GraphRunner | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    runner = graph_runner or _run_graph
    for inquiry, conversation in _eligible_inquiries(session, seller_id, limit):
        try:
            prompt = _prompt_for_inquiry(inquiry)
            graph_result = runner(
                session,
                seller_id,
                prompt,
                inquiry_id=inquiry.id,
                conversation_id=conversation.id,
                decision_provider=decision_provider,
            )
            _apply_status(inquiry, graph_result)
            _record_success(session, seller_id, inquiry, conversation, graph_result)
            results.append(_success_payload(inquiry, conversation, graph_result))
        except Exception as exc:
            _record_failure(session, seller_id, inquiry, conversation, exc)
            results.append(
                {
                    "status": "failed",
                    "inquiry_id": inquiry.id,
                    "conversation_id": conversation.id,
                    "error": str(exc),
                }
            )
    session.flush()
    return results


def _run_graph(
    session: Session,
    seller_id: int,
    user_prompt: str,
    *,
    inquiry_id: int | None = None,
    conversation_id: int | None = None,
    decision_provider: GraphDecisionProvider | None = None,
) -> GraphRunResult[CloserGraphState, CloserAgentOutput]:
    return run_closer_graph_result(
        session,
        seller_id,
        user_prompt,
        inquiry_id=inquiry_id,
        conversation_id=conversation_id,
        decision_provider=decision_provider,
    )


def _eligible_inquiries(session: Session, seller_id: int, limit: int) -> list[tuple[models.Inquiry, models.Conversation]]:
    capped_limit = min(max(limit, 1), 100)
    processed = (
        select(models.AuditLog.id)
        .where(models.AuditLog.seller_id == seller_id)
        .where(models.AuditLog.action_type == AUTO_AGENT_ACTION)
        .where(models.AuditLog.target_type == "inquiry")
        .where(models.AuditLog.target_id == models.Inquiry.id)
    )
    has_ai_message = (
        select(models.Message.id)
        .where(models.Message.conversation_id == models.Conversation.id)
        .where(models.Message.sender_role == "ai")
    )
    has_pending_approval = (
        select(models.Approval.id)
        .where(models.Approval.seller_id == seller_id)
        .where(models.Approval.inquiry_id == models.Inquiry.id)
        .where(models.Approval.status == "pending")
    )
    has_ai_quote = (
        select(models.Quotation.id)
        .where(models.Quotation.seller_id == seller_id)
        .where(models.Quotation.inquiry_id == models.Inquiry.id)
        .where(models.Quotation.created_by == "ai")
        .where(models.Quotation.deleted_at.is_(None))
    )
    has_followup = (
        select(models.FollowupTask.id)
        .where(models.FollowupTask.seller_id == seller_id)
        .where(models.FollowupTask.inquiry_id == models.Inquiry.id)
    )

    statement = (
        select(models.Inquiry, models.Conversation)
        .join(models.Conversation, models.Conversation.inquiry_id == models.Inquiry.id)
        .where(models.Inquiry.seller_id == seller_id)
        .where(models.Inquiry.deleted_at.is_(None))
        .where(models.Inquiry.status.in_(ELIGIBLE_INQUIRY_STATUSES))
        .where(models.Conversation.seller_id == seller_id)
        .where(models.Conversation.status == "open")
        .where(models.Conversation.is_human_takeover.is_(False))
        .where(~processed.exists())
        .where(~has_ai_message.exists())
        .where(~has_pending_approval.exists())
        .where(~has_ai_quote.exists())
        .where(~has_followup.exists())
        .order_by(models.Inquiry.id.asc())
        .limit(capped_limit)
    )
    return [(inquiry, conversation) for inquiry, conversation in session.execute(statement).all()]


def _prompt_for_inquiry(inquiry: models.Inquiry) -> str:
    if inquiry.raw_content and inquiry.raw_content.strip():
        return inquiry.raw_content.strip()
    if inquiry.parsed:
        return f"Handle this parsed inquiry: {inquiry.parsed}"
    return f"Handle inquiry #{inquiry.id}."


def _apply_status(inquiry: models.Inquiry, graph_result: GraphRunResult[CloserGraphState, CloserAgentOutput]) -> None:
    state = graph_result.state
    if state.requires_human_review:
        inquiry.status = "pending_approval"
    elif state.send_result:
        inquiry.status = "responded"
    elif state.quote:
        inquiry.status = "quoted"
    else:
        inquiry.status = "processing"


def _record_success(
    session: Session,
    seller_id: int,
    inquiry: models.Inquiry,
    conversation: models.Conversation,
    graph_result: GraphRunResult[CloserGraphState, CloserAgentOutput],
) -> None:
    state = graph_result.state
    session.add(
        models.AuditLog(
            seller_id=seller_id,
            actor="ai",
            action_type=AUTO_AGENT_ACTION,
            target_type="inquiry",
            target_id=inquiry.id,
            is_auto=True,
            snapshot={
                "status": "ok",
                "conversation_id": conversation.id,
                "steps": state.steps,
                "requires_human_review": state.requires_human_review,
                "quotation_id": (state.quote or {}).get("quotation_id"),
                "approval_id": (state.handoff or {}).get("approval_id"),
                "message_id": (state.send_result or {}).get("message_id"),
                "summary": graph_result.output.summary,
            },
        )
    )


def _record_failure(
    session: Session,
    seller_id: int,
    inquiry: models.Inquiry,
    conversation: models.Conversation,
    exc: Exception,
) -> None:
    session.add(
        models.AuditLog(
            seller_id=seller_id,
            actor="ai",
            action_type=AUTO_AGENT_ACTION,
            target_type="inquiry",
            target_id=inquiry.id,
            is_auto=True,
            snapshot={"status": "failed", "conversation_id": conversation.id, "error": str(exc)},
        )
    )


def _success_payload(
    inquiry: models.Inquiry,
    conversation: models.Conversation,
    graph_result: GraphRunResult[CloserGraphState, CloserAgentOutput],
) -> dict[str, Any]:
    state = graph_result.state
    return {
        "status": "ok",
        "inquiry_id": inquiry.id,
        "conversation_id": conversation.id,
        "inquiry_status": inquiry.status,
        "steps": state.steps,
        "requires_human_review": graph_result.output.requires_human_review,
        "quotation_id": (state.quote or {}).get("quotation_id"),
        "approval_id": (state.handoff or {}).get("approval_id"),
        "message_id": (state.send_result or {}).get("message_id"),
    }
