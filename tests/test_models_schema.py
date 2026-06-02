from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa: F401


ROOT = Path(__file__).resolve().parents[1]


def test_sqlalchemy_models_create_core_tables():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    expected = {
        "seller",
        "channel_account",
        "product",
        "pricing_rule",
        "customer",
        "inquiry",
        "conversation",
        "message",
        "quotation",
        "quotation_item",
        "followup_task",
        "knowledge_chunk",
        "audit_log",
        "approval",
    }

    assert expected.issubset(set(inspector.get_table_names()))


def test_business_tables_carry_tenant_and_audit_columns():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    tenant_tables = {
        "channel_account",
        "product",
        "pricing_rule",
        "customer",
        "inquiry",
        "conversation",
        "quotation",
        "followup_task",
        "knowledge_chunk",
        "audit_log",
        "approval",
    }
    for table in tenant_tables:
        columns = {column["name"] for column in inspector.get_columns(table)}
        assert "seller_id" in columns
        assert "created_at" in columns


def test_key_constraints_match_contract():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    message_columns = {column["name"] for column in inspector.get_columns("message")}
    assert {"channel_message_id", "sender_role", "sent_at"}.issubset(message_columns)

    quotation_item_columns = {column["name"] for column in inspector.get_columns("quotation_item")}
    assert {"quantity", "unit_price", "amount"}.issubset(quotation_item_columns)

    approval_columns = {column["name"] for column in inspector.get_columns("approval")}
    assert {"type", "reason", "summary", "payload", "status", "executed"}.issubset(approval_columns)


def test_models_can_insert_minimal_seller():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)

    with Session() as session:
        seller = app.models.Seller(name="Demo Exporter", email="owner@example.com")
        session.add(seller)
        session.commit()

        assert seller.id == 1
        assert seller.plan == "free"
        assert seller.ai_disclosure is True


def test_postgres_migration_contains_pgvector_and_required_tables():
    sql = (ROOT / "migrations" / "001_initial.sql").read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql
    assert "embedding vector(1536)" in sql
    for table in [
        "seller",
        "channel_account",
        "product",
        "pricing_rule",
        "customer",
        "inquiry",
        "conversation",
        "message",
        "quotation",
        "quotation_item",
        "followup_task",
        "knowledge_chunk",
        "audit_log",
        "approval",
    ]:
        assert f"CREATE TABLE {table}" in sql

