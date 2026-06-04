# Wave 2 Skills
> L3 | 父级: ./CLAUDE.md

<!--
/**
 * [INPUT]: 依赖 docs/SPECS.md、docs/WAVE2_SUBMISSION.md、app/agent_tools.py、scripts/demo_flow.py 与当前测试证据
 * [OUTPUT]: 对外提供复赛 Wave 2 可评审 Skills 索引，说明技能顺序、运行入口、验证命令与公开提交范围
 * [POS]: skills 的组合根，把供应链询盘核心能力拆成可审查、可运行、可测试的 Skill 交付物
 * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
 */
-->

## 目标

本目录是复赛 Wave 2 的 Skills 交付物。它把成交官 Closer 的供应链询盘闭环拆成 8 个可评审技能，每个技能都明确：

- 要解决的业务问题。
- 输入与输出。
- Agent 或 API 调用入口。
- 业务执行步骤。
- 可运行验证方式。

## Skills 顺序

| 顺序 | Skill | 路径 | 核心入口 |
| --- | --- | --- | --- |
| 1 | 多渠道询盘接入 | `skills/inquiry-intake/SKILL.md` | `POST /api/v1/webhooks/site_form` |
| 2 | 询盘甄别评分 | `skills/inquiry-qualification/SKILL.md` | `score_inquiry` |
| 3 | 客户画像与 CRM 建档 | `skills/customer-crm/SKILL.md` | `get_customer`、`GET /api/v1/customers/{id}` |
| 4 | 产品匹配与知识检索 | `skills/product-knowledge-match/SKILL.md` | `match_product`、`search_knowledge` |
| 5 | 报价与 PI 草稿 | `skills/quotation-pi-draft/SKILL.md` | `calc_quote`、`generate_pi` |
| 6 | 风险护栏与人工审批 | `skills/approval-guardrails/SKILL.md` | `send_message`、`request_handoff` |
| 7 | 投递记录、重试与跟进 | `skills/delivery-followup/SKILL.md` | `create_followup`、`POST /api/v1/workers/run-due` |
| 8 | 原型运维就绪检查 | `skills/ops-readiness/SKILL.md` | `GET /api/v1/ops/readiness` |

## 端到端 Workflow

```text
inquiry-intake
  -> inquiry-qualification
  -> customer-crm
  -> product-knowledge-match
  -> quotation-pi-draft
  -> approval-guardrails
  -> delivery-followup
  -> ops-readiness
```

公开 API 演示：

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python scripts/demo_flow.py --base-url http://127.0.0.1:8000 --approve --run-workers --json
```

Prototype：

```powershell
cd frontend
npm install
npm run dev -- --port 5173
```

打开：

```text
http://127.0.0.1:5173/
```

## 自动验证

```powershell
python -m pytest
cd frontend
npm run build
npm run test:e2e
```

2026-06-04 本地验证结果：

- `python -m pytest`: 169 passed
- `cd frontend && npm run build`: passed
- `cd frontend && npm run test:e2e`: 12 passed

## 公开提交说明

Wave 2 评审时应公开本目录、`docs/SPECS.md`、`docs/WAVE2_SUBMISSION.md`、源码、测试和 demo 脚本。公开前按 `docs/PUBLIC_REVIEW_CHECKLIST.md` 移除或脱敏原始 docx/xlsx/html、凭据、本地数据库和构建产物。
