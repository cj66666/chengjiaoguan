---
name: closer-inquiry-qualification
description: Score and grade supply-chain inquiries by extracting purchasing signals, urgency, volume, budget, and product-match confidence.
---

# 询盘甄别评分

## Purpose

识别供应链询盘的采购价值，把询盘分为 A/B/C 等级，并输出可解释的信号，帮助销售优先处理高价值询盘。

## Inputs

- `seller_id`
- `inquiry_id`
- inquiry parsed payload
- inquiry raw content
- customer context

## Outputs

- `grade`: A/B/C
- `score`: 0 到 100
- `signals`: 采购数量、预算、交期、产品明确度、联系方式完整度、风险提示等

## Runtime Entrypoints

- Agent tool: `score_inquiry`
- Service: `app/services/scoring.py`
- API consumer: inbox and dashboard views
- Tests: `tests/test_scoring_tool.py`

## Steps

1. 读取 inquiry 和 customer。
2. 解析数量、目标价、目的地、交期、认证等供应链采购信号。
3. 计算采购强度、需求清晰度、产品相关性和风险扣分。
4. 输出 grade、score、signals。
5. 更新 inquiry，使高价值询盘在工作台置顶。

## Guardrails

- 评分是销售优先级建议，不等于自动承诺成交。
- 无法识别产品或需求模糊时，应降低评分或交给人工确认。
- 测试中使用确定性规则，不调用真实 LLM。

## Validation

```powershell
python -m pytest tests/test_scoring_tool.py tests/test_demo_api.py
```
