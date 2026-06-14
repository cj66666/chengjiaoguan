# Competition Submission
<!--
/**
 * [INPUT]: 依赖 README.md、DEMO_RUNBOOK.md、COMPLETION_AUDIT.md、IMPLEMENTATION_AUDIT.md、PRODUCTION_RUNBOOK.md 与 2026-06-14 本地验证结果
 * [OUTPUT]: 对外提供比赛提交摘要、差异化、演示话术、验收证据与提交清单
 * [POS]: docs 的比赛提交镜像，把工程完成度翻译成评委可读的产品叙事和交付证据
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
-->

## 提交定位

项目名称：Closer 工作台

当前阶段：半决赛 Wave 3。

赛道：跨境 IT 服务赛道。

细分方向：供应链询盘。

一句话：面向跨境 B2B 出口卖家的 AI 询盘成交工作台，把询盘响应、客户建档、产品匹配、报价、风控审批、投递和跟进做成可审计闭环。

不要把项目包装成“跨境询盘管家”。更准确的定位是“询盘到成交的 AI 工作台”。这能避开同类项目只做询盘理解、报价生成或 CLI 演示的同质化叙事。

## 提交摘要

Closer 工作台服务小微工贸和跨境 B2B 出口卖家。买家询盘从站点表单、Email、WhatsApp 等渠道进入后，系统自动建档客户和会话，Closer Operating Agent 调用确定性业务工具完成询盘评分、产品匹配、知识检索、报价草稿和跟进建议。涉及底价、硬底价、敏感承诺、大额合同、未匹配产品和 PI 生成等风险动作时，后端强制进入人工审批，保证 Agent 不能绕过业务护栏。项目提供可运行的 FastAPI 后端、React/Vite 工作台、8 个 Skills、`/api/v1/demo/wave3` 提交 manifest、Demo seed、生产 readiness/alerts、调度入口和 E2E 测试证据。

## 目标用户

- 跨境 B2B 出口卖家、工贸一体企业、小型外贸团队。
- 每天面对多渠道英文询盘，但缺少专职售前、报价和 CRM 流程的人群。
- 对响应速度、报价准确性、底价保护、客户跟进和团队交接有强需求的业务团队。

## 解决的问题

- 询盘分散在表单、邮箱、WhatsApp，客户上下文断裂。
- 销售人员人工筛选询盘、查产品、算报价、写英文回复，响应慢且质量不稳定。
- AI 直接发报价有风险，可能触碰底价、错误承诺、条款越权或大额合同审批要求。
- 小团队缺少可落地的 CRM、跟进、审批、监控和生产运维闭环。

## 产品亮点

- 询盘到成交闭环：入站、建档、评分、匹配、报价、审批、发送、投递记录、跟进一体化。
- 后端强护栏：风险判断在服务端执行，前端和 Agent 都不能绕过审批。
- 人机协同：Agent 负责草拟和推荐，人类负责审批、接管、释放、发送和关键决策。
- 可审计：approval、notification、delivery_attempt、audit_log、readiness、alerts 共同记录关键行为。
- 可演示：`/api/v1/demo/seed` 可幂等生成完整演示数据，不依赖真实外部渠道。
- 可产品化：正式 API key、租户隔离、provider 边界、production check、scheduler 和 monitoring sink 已就位。

## 技术结构

- 后端：FastAPI、SQLAlchemy、Pydantic、PydanticAI、Pydantic Graph。
- 前端：React、Vite、Playwright。
- 数据：PostgreSQL/pgvector 生产形态，SQLite 本地确定性测试。
- Agent：八步状态机 receive、qualify、understand、quote、answer、followup、handoff、persist。
- Wave 3 manifest：`GET /api/v1/demo/wave3` 返回 Agent、Skills、Demo 与 verification 清单。
- 外部 provider：LLM、embedding、knowledge index/search、SMTP、IMAP、WhatsApp Cloud、汇率源、对象存储、monitoring webhook 均通过配置边界接入。

## 差异化表达

不要说：

- “我们也是一个跨境询盘助手。”
- “我们可以自动回复客户。”
- “我们能帮卖家生成报价。”

应该说：

- “我们做的是询盘到成交的 AI 工作台，重点是业务闭环和风险可控。”
- “Agent 只通过后端工具做事，底价、敏感承诺、大额合同和 PI 生成必须由人审批。”
- “这个项目不仅能演示 AI 对话，还能展示 API、工作台、租户、投递重试、readiness 和 E2E 验证。”

## 演示脚本

推荐控制在 4 到 6 分钟。

### 1. 开场

“跨境 B2B 卖家最大的问题不是缺一个聊天机器人，而是询盘来了以后，客户是谁、值不值得跟、产品能不能匹配、报价能不能发、底价有没有被碰、后面谁跟进，这些环节都断在不同工具里。Closer 工作台把这些动作收束到一个 AI 工作台里。”

### 2. 启动 Demo

在线 Demo：

```text
https://cj66666.github.io/chengjiaoguan/
```

线上版本由 GitHub Pages 托管，使用浏览器内置 mock 数据演示 Wave 3 主链路：看板、Demo Seed、询盘收件箱、接管、审批、产品库、报价规则和 readiness。完整 FastAPI/PydanticAI 后端仍可本地运行验证。

本地完整后端 Demo 打开 `http://127.0.0.1:5173/`，点击 Demo seed 或运行：

```powershell
python scripts/demo_flow.py --base-url http://127.0.0.1:8000 --approve --run-workers
```

说明：Demo seed 会生成演示产品、价格规则、知识、A级询盘、报价、待审批消息和跟进任务。

### 3. 看板和收件箱

展示看板指标和高价值询盘置顶。说明询盘不是简单列表，而是已经进入客户、会话、报价和审批链路。

### 4. 客户档案和报价

进入客户页，展示客户资料、询盘、会话、报价、跟进。打开报价详情，说明 MOQ、阶梯价、汇率、底价和 PI 文档都在服务端计算。

### 5. 人工审批护栏

进入审批页，展示待审批消息。说明 Agent 已生成建议，但发送必须经过人工批准；批准后由后端执行投递并记录 delivery attempt。

### 6. 产品化边界

切到产品、价格规则、渠道、设置和 readiness。说明这不是孤立 Demo，而是已经准备好了真实 provider、API key、渠道凭据、调度和监控边界。

### 7. 收尾

“当前仓库已经完成本地 MVP 机器相和生产接线边界，真实 LLM、语义索引、投递渠道、汇率源、cron 和监控只需要按环境变量接入。我们提交的是可运行、可测试、可扩展的成交工作台，不是一次性脚本。”

## 验收证据

2026-06-14 本地验证：

```powershell
python -m pytest
```

结果：182 passed，1 warning。

```powershell
cd frontend
npm run build
```

结果：passed。

```powershell
cd frontend
npm run test:e2e
```

结果：2026-06-04 浏览器回归记录为 12 passed。

## 建议提交材料

- 仓库链接：提交当前仓库。
- 在线 Demo：`https://cj66666.github.io/chengjiaoguan/`。
- 项目名称：Closer 工作台。
- 半决赛材料：优先使用 `docs/WAVE3_SUBMISSION.md`，突出可交付 Agent、Skills 集成和产品 Demo。
- 复赛材料：`docs/WAVE2_SUBMISSION.md` 可作为上一阶段补充材料。
- Specs 材料：使用 `docs/SPECS.md`，覆盖项目名称、应用场景、目标用户、核心问题、产品思路、AI 作用和评测标准。
- Skills 材料：使用 `skills/README.md` 和 8 个 `skills/*/SKILL.md`，每个技能都有输入输出、运行入口、护栏和验证命令。
- 项目简介：使用“提交摘要”第一段，可压缩到平台字数限制。
- 技术说明：使用“技术结构”和“产品亮点”。
- 演示说明：使用“演示脚本”。
- 验证说明：填写 182 passed、build passed；浏览器 E2E 历史记录为 12 passed。
- 风险说明：使用“生产边界”，明确真实 provider、渠道和监控还需要生产环境接线。

## 平台字段草稿

### 短简介

Closer 工作台是面向跨境 B2B 出口卖家的 AI 询盘成交工作台，把入站询盘、客户建档、产品匹配、报价、风控审批、投递和跟进串成可审计闭环，避免 Agent 绕过底价、敏感承诺和大额合同审批。

### 长简介

Closer 工作台服务小微工贸和跨境 B2B 出口团队。询盘从站点表单、Email、WhatsApp 等渠道进入后，系统自动创建客户、询盘、会话和消息，Agent 调用后端工具完成询盘评分、客户画像、产品匹配、知识检索、报价草稿和跟进建议。所有高风险动作都由服务端护栏拦截并进入人工审批，包括底价、敏感承诺、大额报价、未匹配产品和 PI 生成。项目包含 FastAPI 后端、React/Vite 工作台、PydanticAI/Pydantic Graph 编排、租户隔离、正式 API key、delivery retry、readiness/alerts、Demo seed、production check 和 Playwright E2E。

### 创新点

- 从“自动回复询盘”升级为“询盘到成交”的业务闭环。
- Agent 不直接越权执行业务动作，所有风险动作由服务端规则和人工审批兜底。
- 同时具备演示能力和生产接线边界：provider、调度、监控、投递和 readiness 都已抽象。
- 前端工作台可真实操作，不只是 API 文档或命令行 Demo。

### 技术关键词

FastAPI、React、Vite、PydanticAI、Pydantic Graph、SQLAlchemy、PostgreSQL、pgvector、Playwright、Human-in-the-loop、B2B CRM、Quotation Guardrails、Readiness Check。

## 提交前清单

- [ ] 确认仓库不包含 `.env`、真实 API key、生产凭据、本地数据库和构建产物。
- [ ] 按 `docs/PUBLIC_REVIEW_CHECKLIST.md` 清理公开仓库，只保留本赛段需要的 Specs/Skill/Agent/Demo。
- [ ] 确认 `skills/README.md` 和 8 个 `skills/*/SKILL.md` 已提交。
- [ ] 确认 `docs/WAVE3_SUBMISSION.md` 和 `/api/v1/demo/wave3` 已提交。
- [ ] 复跑 `python -m pytest`。
- [ ] 复跑 `cd frontend && npm run build`。
- [ ] 复跑 `cd frontend && npm run test:e2e`。
- [ ] 录制 4 到 6 分钟演示视频。
- [ ] 使用“平台字段草稿”填写比赛平台。
- [ ] 明确提交说明里写“真实 provider 需要生产接线”，不要虚标生产已闭环。
