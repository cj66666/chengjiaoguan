import hashlib
import math
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models


EMBEDDING_DIMENSIONS = 1536
TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]", re.IGNORECASE)


def chunk_text(text: str, *, max_chars: int = 800, overlap: int = 120) -> list[str]:
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        raise ValueError("content is required")
    if max_chars <= overlap:
        raise ValueError("max_chars must be greater than overlap")

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        if end < len(normalized):
            split_at = normalized.rfind("\n", start, end)
            if split_at <= start:
                split_at = normalized.rfind(" ", start, end)
            if split_at > start + max_chars // 2:
                end = split_at
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(end - overlap, 0)
    return chunks


def embed_text(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for token in _tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
        index = int.from_bytes(digest, "big") % EMBEDDING_DIMENSIONS
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def ingest_knowledge(
    session: Session,
    seller_id: int,
    *,
    source_type: str,
    source_ref: str | None,
    content: str,
) -> list[models.KnowledgeChunk]:
    records: list[models.KnowledgeChunk] = []
    for chunk in chunk_text(content):
        record = models.KnowledgeChunk(
            seller_id=seller_id,
            source_type=source_type,
            source_ref=source_ref,
            content=chunk,
            embedding=embed_text(chunk),
        )
        session.add(record)
        records.append(record)
    session.flush()
    session.add(
        models.AuditLog(
            seller_id=seller_id,
            actor="system",
            action_type="knowledge_ingested",
            target_type="knowledge_chunk",
            target_id=records[0].id if records else None,
            is_auto=True,
            snapshot={"source_type": source_type, "source_ref": source_ref, "chunks": len(records)},
        )
    )
    return records


def search_knowledge(
    session: Session,
    seller_id: int,
    *,
    query: str,
    source_type: str | None = None,
    limit: int = 5,
) -> list[dict]:
    if not query.strip():
        raise ValueError("query is required")
    limit = min(max(limit, 1), 20)
    query_vector = embed_text(query)

    statement = select(models.KnowledgeChunk).where(models.KnowledgeChunk.seller_id == seller_id)
    if source_type:
        statement = statement.where(models.KnowledgeChunk.source_type == source_type)

    scored = []
    for chunk in session.scalars(statement).all():
        score = _cosine(query_vector, chunk.embedding or [])
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda item: (item[0], item[1].id), reverse=True)

    return [
        {
            "chunk_id": chunk.id,
            "source_type": chunk.source_type,
            "source_ref": chunk.source_ref,
            "content": chunk.content,
            "score": round(score, 6),
        }
        for score, chunk in scored[:limit]
    ]


def _tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    length = min(len(left), len(right))
    return sum(left[index] * right[index] for index in range(length))
