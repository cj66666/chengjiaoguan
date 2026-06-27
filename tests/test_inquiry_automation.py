"""
/* ========================================================================== */
/* GEB L3: 新询盘 Agent 自动处理测试                                           */
/* ========================================================================== */
/**
 * [INPUT]: 依赖 SQLite 会话夹具、app.models 与 inquiry_automation 服务
 * [OUTPUT]: 验证新询盘可自动进入 operating graph，并且重复 worker 运行不会重复处理
 * [POS]: tests 的 agent worker 证明文件，锁住“入站消息 -> 待审批草稿/报价”的闭环契约
 * [PROTOCOL]: 变更时同步更新 worker 与 scheduler 测试
 */
"""

from decimal import Decimal
from datetime import timedelta

from app import models
from app.database import utcnow
from app.services.inquiry_automation import run_new_inquiry_agent_jobs


def test_run_new_inquiry_agent_jobs_creates_approval_draft(db_session):
    inquiry, conversation = _seed_quoteable_inquiry(db_session)

    result = run_new_inquiry_agent_jobs(db_session, 1)

    assert len(result) == 1
    assert result[0]["status"] == "ok"
    assert result[0]["inquiry_id"] == inquiry.id
    assert result[0]["conversation_id"] == conversation.id
    assert result[0]["requires_human_review"] is True
    assert result[0]["approval_id"] is not None
    assert result[0]["quotation_id"] is not None
    assert db_session.get(models.Inquiry, inquiry.id).status == "pending_approval"

    approval = db_session.get(models.Approval, result[0]["approval_id"])
    assert approval.type == "message_send"
    assert approval.status == "pending"
    assert "Here is our quote" in approval.suggestion

    audit = db_session.query(models.AuditLog).filter_by(action_type="agent_auto_processed").one()
    assert audit.target_type == "inquiry"
    assert audit.target_id == inquiry.id
    assert audit.snapshot["approval_id"] == approval.id


def test_run_new_inquiry_agent_jobs_is_idempotent(db_session):
    inquiry, _ = _seed_quoteable_inquiry(db_session)

    first = run_new_inquiry_agent_jobs(db_session, 1)
    second = run_new_inquiry_agent_jobs(db_session, 1)

    assert len(first) == 1
    assert second == []
    assert db_session.query(models.Quotation).filter_by(inquiry_id=inquiry.id).count() == 1
    assert db_session.query(models.Approval).filter_by(inquiry_id=inquiry.id).count() == 1


def test_run_new_inquiry_agent_jobs_skips_human_takeover(db_session):
    _inquiry, conversation = _seed_quoteable_inquiry(db_session)
    conversation.is_human_takeover = True

    result = run_new_inquiry_agent_jobs(db_session, 1)

    assert result == []
    assert db_session.query(models.Approval).count() == 0


def test_run_new_inquiry_agent_jobs_prefers_latest_received_inquiry(db_session):
    older, _ = _seed_quoteable_inquiry(db_session, message_id="old@example.com", received_offset_minutes=-30)
    newer, _ = _seed_quoteable_inquiry(db_session, message_id="new@example.com", received_offset_minutes=0)

    result = run_new_inquiry_agent_jobs(db_session, 1, limit=1)

    assert len(result) == 1
    assert result[0]["inquiry_id"] == newer.id
    assert db_session.get(models.Inquiry, newer.id).status == "pending_approval"
    assert db_session.get(models.Inquiry, older.id).status == "new"


def test_run_new_inquiry_agent_jobs_skips_obvious_system_email_noise(db_session):
    noisy, _ = _seed_quoteable_inquiry(
        db_session,
        email="mailer-daemon@googlemail.com",
        message_id="bounce@example.com",
        raw_content="Delivery incomplete. Message not delivered to this recipient.",
    )
    real, _ = _seed_quoteable_inquiry(
        db_session,
        email="buyer@acme-trading.com",
        message_id="real@example.com",
        raw_content="Need 500 LED desk lamps shipped to US.",
    )

    result = run_new_inquiry_agent_jobs(db_session, 1, limit=1)

    assert len(result) == 1
    assert result[0]["inquiry_id"] == real.id
    assert db_session.get(models.Inquiry, noisy.id).status == "new"


def _seed_quoteable_inquiry(
    db_session,
    *,
    message_id: str | None = None,
    received_offset_minutes: int = 0,
    email: str | None = None,
    raw_content: str = "Need 500 LED desk lamps shipped to US.",
):
    seller = db_session.get(models.Seller, 1)
    if seller is None:
        seller = models.Seller(
            id=1,
            name="Demo Exporter",
            email="owner@example.com",
            settings={"large_order_approval_threshold": "1"},
        )
        db_session.add(seller)
    customer = models.Customer(
        seller_id=1,
        email=email or f"buyer-{(message_id or 'default').replace('@', '-')}@acme-trading.com",
        company="ACME Trading",
        country="US",
        status="active",
    )
    product = models.Product(
        seller_id=1,
        name="LED Desk Lamp",
        sku="LAMP-10W",
        cost=Decimal("2.00"),
        moq=100,
        description="10W aluminum LED desk lamp for office buyers.",
        status="active",
    )
    db_session.add_all([seller, customer, product])
    db_session.flush()
    inquiry = models.Inquiry(
        seller_id=1,
        customer_id=customer.id,
        source_channel="email",
        raw_content=raw_content,
        parsed={"product": "led desk lamp", "quantity": 500, "destination": "US"},
        status="new",
        language="en",
        received_at=utcnow() + timedelta(minutes=received_offset_minutes),
    )
    db_session.add(inquiry)
    db_session.flush()
    conversation = models.Conversation(
        seller_id=1,
        customer_id=customer.id,
        inquiry_id=inquiry.id,
        channel="email",
        language="en",
    )
    db_session.add(conversation)
    db_session.flush()
    if message_id:
        db_session.add(
            models.Message(
                conversation_id=conversation.id,
                sender_role="customer",
                channel_message_id=message_id,
                content=inquiry.raw_content,
                sent_at=inquiry.received_at,
            )
        )
    rule = models.PricingRule(
        seller_id=1,
        product_id=product.id,
        margin_rate=Decimal("0.25"),
        logistics_template={"unit_cost": "0.10"},
        valid_days=14,
        floor_price=Decimal("2.00"),
        currency="USD",
    )
    db_session.add(rule)
    db_session.flush()
    return inquiry, conversation
