# Wave 2 Submission
<!--
/**
 * [INPUT]: 依赖用户提供的复赛 Wave 2 规则、README.md、DEMO_RUNBOOK.md、COMPLETION_AUDIT.md、IMPLEMENTATION_AUDIT.md 与 2026-06-14 本地验证结果
 * [OUTPUT]: 对外提供复赛阶段提交包，映射赛道、关键 Skills、Prototype、AI 评测入口与交叉评审准备
 * [POS]: docs 的 Wave 2 评测镜像，把供应链询盘产品能力折叠成可运行的 Specs/Skills/Prototype 提交说明
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
-->

## 阶段对齐

- 当前阶段：复赛 | Wave 2。
- 后续阶段：半决赛 | Wave 3、决赛 | Wave 4。
- 赛道：跨境 IT 服务赛道。
- 细分方向：供应链询盘。
- Wave 2 核心目标：验证技术可行性，实现核心业务逻辑的功能闭环。
- Wave 2 提交重点：提交 Specs 中关键技能或工作流 Skills，跑通产品原型 Prototype。

本项目在复赛阶段的提交定位是：供应链询盘成交工作台，而不是泛化客服机器人。核心闭环是“多渠道询盘进入 -> 客户建档 -> 询盘评分 -> 产品/知识匹配 -> 报价草稿 -> 风险审批 -> 投递记录 -> 跟进调度”。

## 提交物总览

| 规则要求 | 本项目提交物 | 评测入口 |
| --- | --- | --- |
| 初赛晋级材料 | 项目简介、应用场景、目标用户、核心问题、产品思路、AI 作用、评测标准 | `README.md`、`docs/SPECS.md` |
| 关键 Skills | 8 个供应链询盘核心技能，覆盖入站、甄别、匹配、报价、审批、投递、跟进、运维 | `skills/README.md` 与各 `SKILL.md` |
| 工作流 Workflow | Demo seed + approve + workers 串联完整闭环 | `scripts/demo_flow.py --approve --run-workers` |
| Prototype | React/Vite 工作台，包含看板、收件箱、客户、产品、审批、设置、readiness | `http://127.0.0.1:5173/` |
| AI 评测可运行 | 后端测试、前端 build、Playwright E2E、公开 API 演示脚本 | `python -m pytest`、`npm run build`、`npm run test:e2e` |
| 交叉评审准备 | 明确演示路径、评测标准、差异化说明和风险边界 | 本文件“交叉评审说明” |

## 关键 Skills

仓库中已提供可评审的 Skill 交付物：

- `skills/inquiry-intake/SKILL.md`
- `skills/inquiry-qualification/SKILL.md`
- `skills/customer-crm/SKILL.md`
- `skills/product-knowledge-match/SKILL.md`
- `skills/quotation-pi-draft/SKILL.md`
- `skills/approval-guardrails/SKILL.md`
- `skills/delivery-followup/SKILL.md`
- `skills/ops-readiness/SKILL.md`

### Skill 1: 多渠道询盘接入

目标：把站点表单、Email、WhatsApp 等供应链询盘标准化为客户、询盘、会话和消息。

入口：

- API: `POST /api/v1/webhooks/site_form`
- 服务：`app/services/channel_gateway.py`
- 测试：`tests/test_site_form_webhook.py`、`tests/test_email_polling.py`、`tests/test_whatsapp_adapter.py`

通过标准：同一租户内按 `channel_message_id` 幂等入站，自动创建或关联 customer、inquiry、conversation、message。

### Skill 2: 询盘甄别评分

目标：识别采购意图、数量、预算、时效、产品匹配信号，把供应链询盘分成 A/B/C 等级。

入口：

- 工具：`score_inquiry`
- 服务：`app/services/scoring.py`
- 测试：`tests/test_scoring_tool.py`

通过标准：高价值询盘在收件箱置顶，评分结果包含 grade、score、signals，便于销售优先跟进。

### Skill 3: 客户画像与 CRM 建档

目标：沉淀买家公司、联系人、历史询盘、会话、报价、跟进状态，避免多渠道上下文断裂。

入口：

- API: `GET /api/v1/customers`、`GET /api/v1/customers/{id}`
- 工具：`get_customer`
- 测试：`tests/test_customers_api.py`、`tests/test_crm_tool.py`

通过标准：客户详情可聚合资料、询盘、会话、报价与跟进，并保持租户隔离。

### Skill 4: 产品匹配与知识检索

目标：根据询盘内容匹配产品，检索知识片段，支撑准确报价和回复。

入口：

- 工具：`match_product`
- 服务：`app/services/product_matching.py`、`app/services/knowledge.py`
- 测试：`tests/test_product_matching.py`、`tests/test_knowledge.py`、`tests/test_knowledge_search_providers.py`

通过标准：返回产品候选、匹配解释、知识证据；生产可切换 embedding/search/index provider。

### Skill 5: 报价与 PI 草稿

目标：按 MOQ、阶梯价、物流、汇率、底价和有效期生成报价草稿与 PI 文档。

入口：

- 工具：`calc_quote`、`generate_pi`
- API: `GET /api/v1/quotations/{id}`、`POST /api/v1/quotations/{id}/send`
- 测试：`tests/test_quote_engine.py`、`tests/test_quote_tools.py`、`tests/test_approvals_quotations_api.py`

通过标准：报价金额使用 Decimal 计算；命中底价或 PI 生成风险时进入审批，不直接执行。

### Skill 6: 风险护栏与人工审批

目标：防止 Agent 越权发送底价、敏感承诺、大额合同、未匹配产品或 PI。

入口：

- 工具：`send_message`、`request_handoff`
- API: `GET /api/v1/approvals`、`POST /api/v1/approvals/{id}/approve`
- 测试：`tests/test_send_message_tool.py`、`tests/test_approvals_quotations_api.py`

通过标准：风险动作创建 pending approval；批准后由后端执行器完成投递；拒绝或接管时停止自动发送。

### Skill 7: 投递记录、重试与跟进

目标：把发送动作落到 delivery attempt，失败可重试，到期跟进可由 worker 调度。

入口：

- API: `GET /api/v1/delivery-attempts`、`POST /api/v1/workers/run-due`
- 服务：`app/services/delivery_attempts.py`、`app/services/followups.py`、`app/services/workers.py`
- 测试：`tests/test_delivery_attempts_api.py`、`tests/test_followups.py`、`tests/test_workers.py`

通过标准：投递结果有状态、payload、response、next_retry_at；workers 统一触发 due follow-up、retry 和 email polling。

### Skill 8: 原型运维就绪检查

目标：让评测者看到项目不只是 Demo，还具备生产接线边界。

入口：

- API: `GET /api/v1/ops/readiness`、`GET /api/v1/ops/alerts`
- 脚本：`scripts/production_check.py`
- 测试：`tests/test_readiness.py`、`tests/test_ops_alerts.py`、`tests/test_production_check_script.py`

通过标准：readiness 能展示 LLM、RAG、投递、凭据、汇率、对象存储、monitoring 和 failed delivery 风险状态。

## 核心 Workflow

Wave 2 主工作流建议作为评测主线：

1. Demo seed 创建供应链询盘、客户、产品、价格规则、知识、报价和待审批消息。
2. 询盘评分为 A 级，高价值置顶。
3. 客户页展示询盘、会话、报价和跟进。
4. 报价详情展示产品、数量、金额、条款和审批状态。
5. 审批页批准 pending message_send。
6. 后端执行投递，消息进入会话，delivery attempt 落库。
7. workers run-due 证明调度入口可运行。

命令入口：

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python scripts/demo_flow.py --base-url http://127.0.0.1:8000 --approve --run-workers --json
```

## Prototype

前端原型是 React/Vite 工作台，不是静态图。

启动：

```powershell
cd frontend
npm install
npm run dev -- --port 5173
```

访问：

```text
http://127.0.0.1:5173/
```

推荐演示页面顺序：

1. 看板：总览询盘、审批、报价、投递、跟进和 readiness。
2. 收件箱：展示高价值供应链询盘和会话。
3. 客户：展示客户档案、活动、报价和跟进。
4. 产品：展示供应链产品库、价格规则和版本。
5. 审批：展示 Agent 建议被人工审批护栏拦住。
6. 设置/运维：展示 API key、渠道、readiness、workers。

## AI 评测入口

最小自动评测命令：

```powershell
python -m pytest
```

前端原型自动评测命令：

```powershell
cd frontend
npm run build
npm run test:e2e
```

公开 API 工作流评测命令：

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python scripts/demo_flow.py --base-url http://127.0.0.1:8000 --approve --run-workers --json
```

2026-06-14 本地结果：

- `python -m pytest`: 182 passed，1 warning
- `cd frontend && npm run build`: passed
- `cd frontend && npm run test:e2e`: 2026-06-04 浏览器回归记录为 12 passed

## 评测标准对应

| 晋级要求 | 本项目对应 |
| --- | --- |
| Skills 完整 | 8 个 Skills 覆盖供应链询盘闭环，不停在单点回复 |
| Skills 有效 | 每个 Skill 都有 API/服务/工具入口和测试文件 |
| Skills 可运行 | 本地无真实外部 key 也能通过 deterministic provider 跑通 |
| 核心产品需求 | 覆盖供应链询盘的接入、甄别、产品匹配、报价、审批、投递、跟进 |
| Prototype 跑通 | React/Vite 工作台 + Demo seed + Playwright E2E |
| AI 评测可执行 | pytest、build、E2E、demo_flow 都是命令行入口 |

## 平台提交文案

### 项目标题

Closer 工作台 - 跨境供应链询盘成交工作台

### 复赛短简介

Closer 工作台面向跨境 B2B 供应链询盘场景，把多渠道询盘接入、客户建档、询盘评分、产品匹配、报价、人工审批、投递记录和跟进调度做成可运行闭环。Wave 2 提交包含 8 个核心 Skills、公开 API 工作流、React/Vite 原型和自动化测试证据。

### Skills 摘要

本项目提交的关键 Skills 包括：多渠道询盘接入、询盘甄别评分、客户画像与 CRM 建档、产品匹配与知识检索、报价与 PI 草稿、风险护栏与人工审批、投递记录与跟进调度、原型运维就绪检查。每个 Skill 都在 `skills/*/SKILL.md` 中单独成文，包含后端服务入口、公开 API 或 Agent 工具入口，并配套确定性测试。

### Prototype 摘要

Prototype 是可操作的 React/Vite 工作台，包含看板、收件箱、客户档案、产品与价格规则、审批队列、通知、设置、readiness 和 Demo 操作。评测者可通过 `/api/v1/demo/seed` 或 `scripts/demo_flow.py` 生成演示数据，完整走通供应链询盘到审批发送的闭环。

## 交叉评审说明

我们评审其他项目时应重点看三件事：

- Specs/Skills 是否真的可运行，而不是只写想法。
- Prototype 是否能跑通核心业务闭环，而不是只展示静态页面。
- 是否清楚区分本地 mock、deterministic provider、真实生产 provider，避免虚标能力。

对本项目的交叉评审引导：

- 优先运行 `python -m pytest` 和 `scripts/demo_flow.py`。
- 如果看 UI，先运行 Demo seed，再看审批页和客户页。
- 评价重点放在供应链询盘闭环、人工审批护栏、工作台完整性和可运行证据。

## 提交前清单

- [ ] `README.md` 与 `docs/SPECS.md` 已覆盖项目问题、目标用户、使用场景、价值和验证标准。
- [ ] `skills/README.md` 和 8 个 `skills/*/SKILL.md` 已包含在公开提交范围内。
- [ ] 仓库不包含 `.env`、真实 API key、本地数据库、构建产物和测试报告产物。
- [ ] 按 `docs/PUBLIC_REVIEW_CHECKLIST.md` 移除或脱敏本赛段不要求公开的原始 docx/xlsx/html。
- [ ] 复跑 `python -m pytest`。
- [ ] 复跑 `cd frontend && npm run build`。
- [ ] 复跑 `cd frontend && npm run test:e2e`。
- [ ] 本文件中的 8 个 Skills 与平台 Specs 字段保持一致。
- [ ] 上传或填写 Prototype 运行说明。
- [ ] 完成平台分配的交叉评审任务，给其他项目写具体、可复核的评论。
