---
name: closer-product-knowledge-match
description: Match supply-chain inquiry requirements to products and retrieve knowledge evidence for quotation and reply drafting.
---

# 产品匹配与知识检索

## Purpose

根据询盘中的产品需求匹配产品库，并检索知识库证据，支撑准确报价、交期解释、认证说明和英文回复。

## Inputs

- `seller_id`
- product requirement text or parsed requirement object
- knowledge query
- optional source type
- limit

## Outputs

- product candidates
- match reasons
- knowledge chunks
- source metadata

## Runtime Entrypoints

- Agent tool: `match_product`
- Agent tool: `search_knowledge`
- Services: `app/services/product_matching.py`、`app/services/knowledge.py`
- Providers: `embedding_providers.py`、`knowledge_index_providers.py`、`knowledge_search_providers.py`
- Tests: `tests/test_product_matching.py`、`tests/test_knowledge.py`

## Steps

1. 从询盘中提取产品关键词、型号、规格、数量和用途。
2. 在产品库中做候选匹配。
3. 输出匹配解释，说明命中字段和置信信号。
4. 根据需求检索知识片段。
5. 将产品候选和知识证据交给报价或回复技能。

## Guardrails

- 未匹配产品不能自动承诺可供货，应触发 handoff 或人工确认。
- 默认 provider 是 deterministic/rule_based，保证评测环境可运行。
- 生产可接入真实 embedding、managed index 和 rerank provider。

## Validation

```powershell
python -m pytest tests/test_product_matching.py tests/test_knowledge.py tests/test_embedding_providers.py tests/test_knowledge_index_providers.py tests/test_knowledge_search_providers.py
```

Prototype 验证：运行 Demo seed 后查看产品页和报价详情中的产品信息。
