---
name: closer-approval-guardrails
description: Enforce human approval for risky AI actions such as floor-price messages, sensitive commitments, large contracts, handoff, and PI generation.
---

# 风险护栏与人工审批

## Purpose

确保 Agent 不能绕过业务护栏。任何涉及底价、敏感承诺、大额合同、未匹配产品、PI 生成或人工接管的动作，都必须进入人工审批。

## Inputs

- `seller_id`
- `conversation_id`
- proposed outbound content
- quotation or PI context
- risk reason
- handoff summary and suggestion

## Outputs

- approval request
- pending status
- notification
- executed delivery after approval
- audit log

## Runtime Entrypoints

- Agent tool: `send_message`
- Agent tool: `request_handoff`
- API: `GET /api/v1/approvals`
- API: `POST /api/v1/approvals/{id}/approve`
- API: `POST /api/v1/approvals/{id}/reject`
- Services: `app/services/approvals.py`、`app/services/approval_execution.py`、`app/services/outbound.py`
- Tests: `tests/test_send_message_tool.py`、`tests/test_approvals_quotations_api.py`

## Steps

1. 接收 Agent 的拟发送内容或 handoff 请求。
2. 检查底价、敏感承诺、大额金额、未匹配产品、PI 等风险。
3. 无风险时进入正常投递边界。
4. 有风险时创建 pending approval，并把 conversation 切到人工接管语义。
5. 通知人工审批。
6. 批准后由后端执行器发送或生成 PI。
7. 拒绝后保持未执行并记录审计。

## Guardrails

- 前端和 Agent 都不能直接绕过 approval。
- 审批通过后的副作用必须由后端执行器完成。
- 审批 payload 和执行结果必须留痕。

## Validation

```powershell
python -m pytest tests/test_send_message_tool.py tests/test_approvals_quotations_api.py tests/test_notifications_api.py
```

Prototype 验证：运行 Demo seed，打开审批页，批准 pending message_send，再查看会话消息。
