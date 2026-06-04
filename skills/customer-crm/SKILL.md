---
name: closer-customer-crm
description: Build a tenant-isolated customer profile from inquiries, conversations, quotations, and follow-up history.
---

# 客户画像与 CRM 建档

## Purpose

把买家的多渠道询盘、会话、报价和跟进聚合成客户档案，解决跨境销售团队“看不到客户完整上下文”的问题。

## Inputs

- `seller_id`
- `customer_id` or `inquiry_id`
- customer contact fields
- related inquiries, conversations, quotations, followups

## Outputs

- customer profile
- inquiry history
- conversation summary
- quotation history
- follow-up state

## Runtime Entrypoints

- Agent tool: `get_customer`
- API: `GET /api/v1/customers`
- API: `GET /api/v1/customers/{id}`
- Service: `app/services/crm.py`
- Tests: `tests/test_crm_tool.py`、`tests/test_customers_api.py`

## Steps

1. 用 seller scope 读取 customer。
2. 聚合同租户下的 inquiries。
3. 聚合 conversations 和 messages。
4. 聚合 quotations 和 followups。
5. 输出给 Agent 和前端客户页使用。

## Guardrails

- 严格租户隔离，不能跨 seller 读取客户。
- 客户擦除后，关联 PII、报价 payload、审批 payload 和通知需要脱敏或停止后续动作。
- 客户画像只提供事实和建议，不绕过审批发送。

## Validation

```powershell
python -m pytest tests/test_crm_tool.py tests/test_customers_api.py tests/test_data_exports_api.py
```

Prototype 验证：打开前端客户页，查看客户活动、报价详情和跟进状态。
