"""
/* ========================================================================== */
/* GEB L3: 产品匹配服务                                                       */
/* ========================================================================== */
/**
 * [INPUT]: 依赖 json/re、SQLAlchemy Session 与 app.models.Product
 * [OUTPUT]: 对外提供 match_product
 * [POS]: services 的产品证据检索器，用字段 token 重叠、置信度和备选差异提示为 Agent 回复提供可解释 grounding
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
"""

import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models


TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]", re.IGNORECASE)
CONFIDENCE_THRESHOLD = 0.35


def match_product(
    session: Session,
    seller_id: int,
    requirement: str | dict[str, Any],
    *,
    limit: int = 5,
) -> list[dict]:
    query_text = _requirement_text(requirement)
    query_tokens = set(_tokens(query_text))
    if not query_tokens:
        raise ValueError("requirement is required")
    limit = min(max(limit, 1), 20)

    products = session.scalars(
        select(models.Product)
        .where(models.Product.seller_id == seller_id)
        .where(models.Product.status == "active")
        .where(models.Product.deleted_at.is_(None))
    ).all()

    candidates = []
    for product in products:
        score, fields = _score_product(product, query_tokens, query_text)
        candidates.append((score, product, fields))
    candidates.sort(key=lambda item: (item[0], item[1].id), reverse=True)

    if not candidates:
        return []

    top_confidence = _confidence(candidates[0][0])
    if top_confidence < CONFIDENCE_THRESHOLD:
        selected = candidates[: min(max(limit, 2), 3)]
        return [
            _match_payload(
                product,
                score,
                fields,
                query_tokens,
                match_status="needs_review",
                requires_human_review=True,
            )
            for score, product, fields in selected
        ]

    selected = [candidate for candidate in candidates if candidate[0] > 0][:limit]

    return [
        _match_payload(
            product,
            score,
            fields,
            query_tokens,
            match_status="matched",
            requires_human_review=False,
        )
        for score, product, fields in selected
    ]


def _match_payload(
    product: models.Product,
    score: float,
    fields: list[str],
    query_tokens: set[str],
    *,
    match_status: str,
    requires_human_review: bool,
) -> dict:
    return {
        "product_id": product.id,
        "name": product.name,
        "sku": product.sku,
        "score": round(score, 6),
        "confidence": _confidence(score),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "match_status": match_status,
        "requires_human_review": requires_human_review,
        "matched_fields": fields,
        "differences": _differences(product, query_tokens),
        "reason": _reason(fields, requires_human_review=requires_human_review),
    }


def _confidence(score: float) -> float:
    return round(min(max(score / 1.5, 0.0), 1.0), 6)


def _differences(product: models.Product, query_tokens: set[str]) -> dict[str, list[str]]:
    product_tokens = set(
        _tokens(
            " ".join(
                [
                    product.name,
                    product.sku or "",
                    product.description or "",
                    json.dumps(product.specs or {}, ensure_ascii=False, sort_keys=True),
                ]
            )
        )
    )
    unmatched_terms = sorted(query_tokens - product_tokens)[:8]
    differentiators = []
    for key, value in (product.specs or {}).items():
        text = f"{key}: {value}"
        if not (set(_tokens(text)) & query_tokens):
            differentiators.append(text)
    return {
        "unmatched_requirement_terms": unmatched_terms,
        "product_differentiators": differentiators[:5],
    }


def _requirement_text(requirement: str | dict[str, Any]) -> str:
    if isinstance(requirement, str):
        return requirement
    values: list[str] = []
    for value in requirement.values():
        if isinstance(value, (dict, list)):
            values.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
        elif value is not None:
            values.append(str(value))
    return " ".join(values)


def _score_product(product: models.Product, query_tokens: set[str], query_text: str) -> tuple[float, list[str]]:
    fields = {
        "name": product.name,
        "sku": product.sku or "",
        "description": product.description or "",
        "specs": json.dumps(product.specs or {}, ensure_ascii=False, sort_keys=True),
    }
    weighted_score = 0.0
    matched_fields: list[str] = []
    weights = {"name": 2.0, "sku": 2.0, "description": 1.0, "specs": 1.5}

    for field_name, field_text in fields.items():
        field_tokens = set(_tokens(field_text))
        if not field_tokens:
            continue
        overlap = query_tokens & field_tokens
        if overlap:
            matched_fields.append(field_name)
            weighted_score += weights[field_name] * (len(overlap) / len(query_tokens))

    if product.sku and product.sku.lower() in query_text.lower():
        weighted_score += 1.0
        if "sku" not in matched_fields:
            matched_fields.append("sku")

    return weighted_score, matched_fields


def _tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def _reason(fields: list[str], *, requires_human_review: bool = False) -> str:
    if requires_human_review:
        return "Low confidence product match; review alternatives before quoting."
    if not fields:
        return "No direct product evidence matched."
    return "Matched " + ", ".join(fields) + "."
