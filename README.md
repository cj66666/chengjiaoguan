# 成交官 Closer

成交官 Closer 是面向跨境 B2B 出口卖家的 AI 询盘成交工作台。它不是单点的“询盘总结器”，而是把入站询盘、客户建档、产品匹配、报价、底价风控、人工审批、投递、跟进和生产就绪检查串成一条可审计的成交闭环。

## 复赛 Wave 2 提交定位

- 赛道：跨境 IT 服务赛道。
- 细分方向：供应链询盘。
- 阶段目标：提交 Specs 中关键 Skills/Workflow，跑通 Prototype。
- 提交主线：多渠道询盘进入 -> 客户建档 -> 询盘评分 -> 产品/知识匹配 -> 报价草稿 -> 风险审批 -> 投递记录 -> 跟进调度。

详见 `docs/WAVE2_SUBMISSION.md`。

核心 Skills 见 `skills/README.md`。

## Specs 基础说明

评审入口：

- 项目要解决的问题：多渠道供应链询盘分散、人工筛选和报价慢、AI 直接回复有底价和承诺风险。
- 目标用户：小微跨境 B2B 出口卖家、工贸一体企业、外贸销售团队。
- 使用场景：独立站、Email、WhatsApp 询盘进入后，完成客户建档、询盘评分、产品匹配、报价审批和跟进。
- 为什么值得做：供应链询盘响应速度和报价准确性直接影响成交，且小团队缺少可控的 AI 工作流。
- 如何验证有效：运行后端测试、前端 E2E 和 demo workflow，检查是否能完成询盘到审批发送的闭环。

完整 Specs 见 `docs/SPECS.md`。

## 核心价值

- 多渠道询盘进入后，系统自动创建或关联客户、询盘、会话和消息。
- Agent 通过服务层工具完成询盘评分、客户画像、产品匹配、知识检索、报价草稿和跟进建议。
- 底价、敏感承诺、大额合同、未匹配产品等风险动作必须进入人工审批，不能由 Agent 绕过。
- 前端工作台提供看板、收件箱、客户、产品、价格规则、渠道、审批、通知、设置和运维就绪视图。
- 后端提供租户隔离、正式 API key、delivery attempt、retry worker、readiness、alerts 和 production check 脚本。

## 已实现范围

- FastAPI 后端与 `/api/v1` 公共 API。
- SQLAlchemy ORM 与 PostgreSQL migration，本地测试使用 SQLite 确定性环境。
- PydanticAI runtime 与 Pydantic Graph 八步状态机。
- site form、Email、WhatsApp 入站/出站边界。
- 客户、询盘、会话、消息、报价、审批、通知、跟进、导出、设置、产品和价格规则 API。
- 知识切块、embedding provider、knowledge index/search provider 边界。
- 报价引擎、PI 生成、对象存储边界、汇率缓存刷新/确认。
- React/Vite 工作台与 Playwright 桌面/移动 E2E。

## 演示主链路

1. 创建演示数据：产品、价格规则、知识、A级询盘、报价、待审批消息和跟进任务。
2. 在工作台查看看板、询盘列表、客户档案和报价详情。
3. 展示报价/消息发送被护栏挂起，必须由人工审批。
4. 批准审批后，后端执行正常投递流程并记录 delivery attempt。
5. 进入设置、产品、渠道、readiness 和 workers 调度入口，展示产品化边界。

## 本地启动

安装后端依赖：

```powershell
python -m pip install -e .[dev]
```

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

常用地址：

- Backend health: `http://127.0.0.1:8000/api/v1/health`
- Frontend workbench: `http://127.0.0.1:5173/`
- Vite proxy check: `http://127.0.0.1:5173/api/v1/dashboard/metrics`

## 验证命令

后端：

```powershell
python -m pytest
```

前端：

```powershell
cd frontend
npm run build
npm run test:e2e
```

2026-06-04 本地验证结果：

- `python -m pytest`: 169 passed
- `npm run build`: passed
- `npm run test:e2e`: 12 passed

## 生产边界

仓库内已经提供 provider/client/API/脚本/readiness 边界，但真实生产闭环还需要外部系统接线：

- 真实 LLM key/model 与线上工具选择评估。
- 真实托管语义索引和 embedding/search/index provider。
- SMTP、IMAP、WhatsApp Cloud、外部汇率源、对象存储、监控 webhook 和 cron/queue。
- 生产域名下的最终 Demo 彩排和视觉 QA。

详见：

- `docs/COMPETITION_SUBMISSION.md`
- `docs/SPECS.md`
- `docs/WAVE2_SUBMISSION.md`
- `docs/PUBLIC_REVIEW_CHECKLIST.md`
- `skills/README.md`
- `docs/COMPLETION_AUDIT.md`
- `docs/DEMO_RUNBOOK.md`
- `docs/PRODUCTION_RUNBOOK.md`
- `docs/ENVIRONMENT.md`
