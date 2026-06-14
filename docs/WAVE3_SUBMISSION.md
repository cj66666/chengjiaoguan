# Wave 3 Submission
<!--
/**
 * [INPUT]: 依赖 README.md、skills/README.md、docs/DEMO_RUNBOOK.md、/api/v1/demo/wave3 与当前测试证据
 * [OUTPUT]: 对外提供半决赛 Wave 3 的 Agent、Skills、Demo 提交材料和验收路径
 * [POS]: docs 的 Wave 3 提交入口，把可运行工程转译为评审可快速执行的产品演示说明
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
-->

## 阶段定位

当前阶段：半决赛 Wave 3。

赛段任务：提交可交付最终结果的智能体 Agents，整合 Skills 技能，并完成产品演示 Demo。

Closer 的提交物不是单一 prompt 或脚本，而是一个可运行的询盘成交智能体工作台：

- Agent：PydanticAI runtime + Pydantic Graph 八步编排。
- Skills：8 个可审查、可运行、可测试的业务技能。
- Demo：GitHub Pages 在线工作台 + React/Vite 本地工作台 + `/api/v1/demo/seed` 一键生成主链路数据。
- Evidence：pytest、frontend build、Playwright E2E、readiness/alerts、交叉评测响应文档。

## Agent 交付物

Agent 名称：Closer Operating Agent。

运行入口：

- `app.agent.runtime.run_closer_agent`
- `app.agent.graph.run_closer_graph`
- `POST /api/v1/demo/seed`
- `GET /api/v1/demo/wave3`

八步工作流：

```text
receive -> qualify -> understand -> quote -> answer -> followup -> handoff -> persist
```

关键约束：

- Agent 必须通过后端工具读取客户、询盘、产品、知识和报价事实。
- 底价、硬底价、敏感承诺、大额合同、低置信度产品匹配、PI 生成都在服务端兜底。
- Agent 可以生成建议和草稿，但不能绕过 approval、delivery attempt 和 audit 记录。

## Skills 集成

`skills/README.md` 是 Skills 总入口，8 个技能分别对应主链路的 8 个业务动作：

| 顺序 | Skill | 入口 |
| --- | --- | --- |
| 1 | 多渠道询盘接入 | `POST /api/v1/webhooks/site_form` |
| 2 | 询盘甄别评分 | `score_inquiry` |
| 3 | 客户画像与 CRM 建档 | `get_customer` |
| 4 | 产品匹配与知识检索 | `match_product`、`search_knowledge` |
| 5 | 报价与 PI 草稿 | `calc_quote`、`generate_pi` |
| 6 | 风险护栏与人工审批 | `send_message`、`request_handoff` |
| 7 | 投递记录、重试与跟进 | `create_followup`、`workers/run-due` |
| 8 | 原型运维就绪检查 | `ops/readiness` |

机器可读 Skills manifest：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/demo/wave3
```

## Demo 演示路径

在线 Demo：

```text
https://cj66666.github.io/chengjiaoguan/
```

在线 Demo 由 GitHub Pages 托管。由于 Pages 只能运行静态文件，线上版本使用 `VITE_DEMO_MODE=mock` 的浏览器内置数据，保留看板、Demo Seed、收件箱、接管、审批、产品库、报价规则、设置和 readiness 的主要交互。完整后端、PydanticAI runtime、Pydantic Graph 和服务端护栏通过本地 API、测试和脚本验证。

启动后端：

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

启动前端：

```powershell
cd frontend
npm install
npm run dev -- --port 5173
```

浏览器打开：

```text
http://127.0.0.1:5173/
```

演示顺序：

1. 看板顶部确认 `Wave 3 Agent Demo` 卡片。
2. 点击 `Demo Seed` 或 `运行演示`。
3. 进入 `询盘收件箱`，查看 A 级询盘、客户对话和护栏卡片。
4. 点击 `接管`，证明人工可在风险动作前介入。
5. 点击 `采纳建议并发送` 或进入审批队列，展示 human-in-the-loop。
6. 打开 `产品库`、`报价规则`、`设置`，展示产品、价格、渠道凭据、readiness 和运维边界。

命令行演示：

```powershell
python scripts/demo_flow.py --base-url http://127.0.0.1:8000 --approve --run-workers --json
```

## 平台提交文案

短简介：

Closer 工作台是面向跨境 B2B 出口卖家的 AI 询盘成交智能体，把入站询盘、客户建档、产品匹配、报价、风控审批、投递和跟进串成可审计闭环。

长简介：

Closer Operating Agent 基于 PydanticAI 与 Pydantic Graph 编排，整合 8 个 Skills：询盘接入、评分、CRM、产品匹配、知识检索、报价、审批护栏、投递跟进和 readiness。评审可通过 React 工作台点击 Demo Seed，也可通过 `scripts/demo_flow.py` 或 `/api/v1/demo/wave3` 验证 Agent、Skills 与 Demo 的完整性。所有高风险动作都由服务端护栏拦截，确保 Agent 不能越权承诺价格、账期、交付或 PI。

## 验收证据

2026-06-14 本地基线：

- `python -m pytest`: 182 passed, 1 warning。
- `cd frontend && npm run build`: passed。
- `cd frontend && npm run test:e2e`: 2026-06-04 historical run, 12 passed。

本文件变更后应至少复跑：

```powershell
python -m pytest tests/test_demo_api.py tests/test_project_contract.py
cd frontend
npm run build
```

## 提交清单

- [ ] 仓库已推送 Synnovator。
- [ ] GitHub Pages 在线 Demo 可访问：`https://cj66666.github.io/chengjiaoguan/`。
- [ ] `docs/WAVE3_SUBMISSION.md` 已作为半决赛入口。
- [ ] `skills/README.md` 和 8 个 `SKILL.md` 已提交。
- [ ] `/api/v1/demo/wave3` 返回 Agent、Skills、Demo 和 verification manifest。
- [ ] 工作台首页可见 `Wave 3 Agent Demo` 卡片。
- [ ] 真实 API key、token、数据库和本地构建产物没有提交。
