---
name: closer-inquiry-intake
description: Standardize cross-border supply-chain inquiries from site forms, Email, and WhatsApp into customer, inquiry, conversation, and message records.
---

# 多渠道询盘接入

## Purpose

把来自独立站表单、Email、WhatsApp 的供应链询盘统一接入成交官 Closer，形成可追踪的 customer、inquiry、conversation、message。该技能解决“询盘散落在多个渠道，客户上下文断裂”的问题。

## Inputs

- `seller_id`: 租户 ID，由 `Authorization: Bearer seller:<id>` 或正式 `cak_` token 解析。
- `channel`: `site_form`、`email`、`whatsapp` 等渠道。
- `channel_message_id`: 渠道侧唯一消息 ID，用于幂等。
- `buyer`: 买家姓名、邮箱、电话、公司、国家。
- `content`: 询盘正文，通常包含产品、数量、目的地、认证、交期、目标价等供应链信息。

## Outputs

- `customer_id`
- `inquiry_id`
- `conversation_id`
- `message_id`
- 标准化后的 parsed inquiry payload

## Runtime Entrypoints

- API: `POST /api/v1/webhooks/site_form`
- Email polling: `POST /api/v1/channels/{id}/poll-email`
- Service: `app/services/channel_gateway.py`
- Models: `Customer`、`Inquiry`、`Conversation`、`Message`

## Steps

1. 验证租户上下文。
2. 根据 channel 和 `channel_message_id` 做幂等检查。
3. 标准化买家联系方式和询盘正文。
4. 创建或关联 customer。
5. 创建 inquiry，并写入初始 parsed 信息。
6. 创建或关联 conversation。
7. 写入 buyer message。
8. 返回公开 API 资源 ID。

## Guardrails

- 所有数据必须按 `seller_id` 隔离。
- 重复 webhook 不应创建重复 inquiry 或 message。
- 入站只创建事实记录，不自动发送对外消息。

## Validation

```powershell
python -m pytest tests/test_site_form_webhook.py tests/test_email_polling.py tests/test_whatsapp_adapter.py
```

端到端演示：

```powershell
python scripts/demo_flow.py --base-url http://127.0.0.1:8000 --json
```
