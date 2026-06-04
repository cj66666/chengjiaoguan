---
name: closer-delivery-followup
description: Record outbound delivery attempts, retry failed sends, and schedule follow-up tasks for supply-chain inquiries.
---

# 投递记录、重试与跟进

## Purpose

把对外发送和后续跟进变成可审计状态机。发送不是“写一条消息就结束”，而是要记录 delivery attempt、失败原因、下一次重试时间和 follow-up 任务。

## Inputs

- `seller_id`
- `conversation_id`
- outbound payload
- channel account
- follow-up message
- delay hours
- retry policy

## Outputs

- delivery attempt
- delivery status
- next retry time
- follow-up task
- worker run result

## Runtime Entrypoints

- Agent tool: `create_followup`
- API: `GET /api/v1/delivery-attempts`
- API: `POST /api/v1/delivery-attempts/{id}/retry`
- API: `POST /api/v1/workers/run-due`
- Services: `app/services/channel_delivery.py`、`app/services/delivery_attempts.py`、`app/services/followups.py`、`app/services/workers.py`
- Tests: `tests/test_delivery_attempts.py`、`tests/test_delivery_attempts_api.py`、`tests/test_followups.py`、`tests/test_workers.py`

## Steps

1. 根据会话和渠道构造投递 payload。
2. 默认 payload-only，生产 live 模式才真实调用 SMTP 或 WhatsApp。
3. 写入 delivery attempt。
4. 失败时记录 response 和 `next_retry_at`。
5. 创建或更新 follow-up task。
6. `workers/run-due` 扫描到期 follow-up、delivery retry、email polling 和汇率刷新。
7. 输出 worker 调度结果。

## Guardrails

- 测试和 Demo 默认不触发真实外部发送。
- 真实发送必须显式设置 `CLOSER_DELIVERY_MODE=live` 和渠道凭据。
- 人工接管或客户擦除后应停止自动跟进。

## Validation

```powershell
python -m pytest tests/test_delivery_attempts.py tests/test_delivery_attempts_api.py tests/test_followups.py tests/test_workers.py
```

公开 API 演示：

```powershell
python scripts/demo_flow.py --base-url http://127.0.0.1:8000 --approve --run-workers --json
```
