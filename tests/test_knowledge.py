import pytest

from app import agent_tools, models
from app.services.knowledge import chunk_text, embed_text, ingest_knowledge, search_knowledge


def test_chunk_text_splits_long_content_with_overlap():
    chunks = chunk_text("A" * 900 + "\n" + "B" * 900, max_chars=800, overlap=100)

    assert len(chunks) >= 2
    assert chunks[0].startswith("A")
    assert chunks[-1].endswith("B")


def test_embed_text_is_deterministic_and_1536_dimensions():
    first = embed_text("MOQ payment certification")
    second = embed_text("MOQ payment certification")

    assert first == second
    assert len(first) == 1536
    assert pytest.approx(sum(value * value for value in first), rel=1e-6) == 1.0


def test_ingest_and_search_knowledge_returns_ranked_matches(db_session):
    db_session.add(models.Seller(id=1, name="Demo Exporter", email="owner@example.com"))
    ingest_knowledge(
        db_session,
        1,
        source_type="faq",
        source_ref="shipping",
        content="Shipping to Germany usually takes 18 days by sea.\nPayment terms require 30% deposit.",
    )
    ingest_knowledge(
        db_session,
        1,
        source_type="product",
        source_ref="lamp",
        content="LED desk lamp has CE certification and adjustable brightness.",
    )

    results = search_knowledge(db_session, 1, query="CE certification lamp", limit=3)

    assert results[0]["source_ref"] == "lamp"
    assert results[0]["score"] > 0


def test_search_knowledge_is_tenant_scoped(db_session):
    db_session.add_all(
        [
            models.Seller(id=1, name="Demo Exporter", email="owner@example.com"),
            models.Seller(id=2, name="Other Exporter", email="other@example.com"),
        ]
    )
    ingest_knowledge(db_session, 2, source_type="faq", source_ref="private", content="Secret MOQ policy")

    assert agent_tools.search_knowledge(db_session, 1, "Secret MOQ policy") == []


def test_knowledge_api_ingests_and_searches(client):
    response = client.post(
        "/api/v1/knowledge",
        json={
            "source_type": "faq",
            "source_ref": "payment",
            "content": "We accept T/T payment with 30% deposit before production.",
        },
    )
    assert response.status_code == 201
    assert response.json()["total"] == 1

    search = client.get("/api/v1/knowledge", params={"q": "deposit payment"})

    assert search.status_code == 200
    assert search.json()["items"][0]["source_ref"] == "payment"
