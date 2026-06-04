---
name: closer-quotation-pi-draft
description: Generate quotation drafts and PI approval requests using MOQ, tiered pricing, exchange rates, logistics, and floor-price rules.
---

# 报价与 PI 草稿

## Purpose

根据供应链询盘中的产品和数量生成报价草稿，并在 PI 生成或底价风险出现时进入人工审批。

## Inputs

- `seller_id`
- `inquiry_id`
- `items`: product id and quantity
- `destination`
- `currency`
- pricing rules
- exchange rate cache

## Outputs

- `quotation_id`
- quotation lines
- total amount
- validity
- floor-price hit flag
- quote message draft
- PI generation approval when needed

## Runtime Entrypoints

- Agent tool: `calc_quote`
- Agent tool: `generate_pi`
- API: `GET /api/v1/quotations/{id}`
- API: `POST /api/v1/quotations/{id}/send`
- Services: `app/services/quote_engine.py`、`app/services/pi_documents.py`
- Tests: `tests/test_quote_engine.py`、`tests/test_quote_tools.py`、`tests/test_approvals_quotations_api.py`

## Steps

1. 校验 inquiry、product 和 pricing rule 属于当前 seller。
2. 按 MOQ 和阶梯价格计算行项目。
3. 应用物流、汇率、有效期和利润规则。
4. 检查 floor price 风险。
5. 创建 draft quotation 和 quotation items。
6. 渲染报价消息草稿。
7. PI 生成必须创建 approval，批准后才生成文档。

## Guardrails

- 金额使用 Decimal，不能用 float 计算报价。
- 汇率缓存必须确认且未过期。
- 命中底价、大额报价或 PI 生成不能直接发送。

## Validation

```powershell
python -m pytest tests/test_quote_engine.py tests/test_quote_tools.py tests/test_approvals_quotations_api.py
```

Prototype 验证：运行 Demo seed 后打开报价详情，检查金额、条款和审批状态。
