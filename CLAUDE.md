# CLAUDE.md - Closer 项目级指令

本文件是给 Claude/Codex/其他开发 agent 的项目级操作手册。先读本文件，再按改动目录读取局部 `CLAUDE.md`。不要把它当 README；它记录的是项目架构边界、编码约定、坑点、测试和部署路径。

## 项目目标

Closer 是跨境 B2B 出口卖家的 AI 询盘成交工作台。核心链路是：

1. 询盘从站点表单、Email、WhatsApp 等渠道进入。
2. 系统创建或关联客户、询盘、会话和消息。
3. 服务层做客户/询盘评分、产品匹配、知识检索和报价。
4. Agent 编排工具调用，但不绕过业务服务。
5. 底价、敏感承诺、大单、合同条款等风险必须进入审批。
6. 人工可以查看、接管、审批、发送和跟进。
7. 前端工作台只消费公开 `/api/v1` API，展示并验证这条主链路。

## 目录结构

```text
app/                    FastAPI 后端、Agent 编排、ORM、schemas、routers、services
app/agent/              PydanticAI runtime 与 Pydantic Graph 八步状态机
app/routers/            HTTP 边界层，只处理参数、依赖、错误和响应组装
app/services/           确定性业务规则层，报价、CRM、渠道、知识、审批、投递等
app/services/catalog_domain/
                        产品、价格规则、渠道、dashboard catalog 子域
frontend/               React/Vite 工作台
frontend/src/           App 组合根、API client、UI primitives、样式和页面
frontend/e2e/           Playwright 桌面/移动 E2E
tests/                  后端 API、服务、工具、Agent/Graph 契约测试
migrations/             PostgreSQL/pgvector 生产 DDL
scripts/                demo_flow 与 production_check 等公开 API 脚本
docs/                   环境、部署、审计、视觉 QA、执行计划等过程文档
Closer 工作台（离线版）.html
                        前端离线视觉参考真源，不是运行中的正式前端
```

局部文件：

- `app/CLAUDE.md`: 后端组合根和服务边界。
- `app/agent/CLAUDE.md`: Agent runtime、tools、graph 和 policy 边界。
- `app/routers/CLAUDE.md`: HTTP 资源域约定。
- `app/services/CLAUDE.md`: 确定性业务服务约定。
- `frontend/CLAUDE.md` 与 `frontend/src/CLAUDE.md`: 前端 API-only、设计参考和 UI 约定。
- `tests/CLAUDE.md`: 测试域约定。
- `docs/CLAUDE.md`: 文档用途边界。

## 架构边界

后端：

- `app/main.py` 只做 FastAPI 应用装配、lifespan、错误处理和 router 注册。
- `app/routers/*` 是 HTTP 边界，不放核心业务规则。
- `app/services/*` 是业务规则真源，不依赖 FastAPI，不直接读请求对象。
- `app/agent_tools.py` 是 Agent 工具稳定门面。Role B 或 Agent runtime 调工具时走这里，不直接调用杂散服务函数；`send_message` 必须保留审批护栏和 handoff 语义。
- `app/agent/*` 只负责 PydanticAI / Graph 编排、工具绑定和状态流转，不重写报价、审批、投递等业务规则。
- `app/models.py` 是 ORM 真源；`app/schemas.py` 是 HTTP/Pydantic 契约真源。
- 生产形态是 PostgreSQL/pgvector；测试用 SQLite 内存库保持确定性。

前端：

- `frontend/src/api.js` 是 API client 边界，统一 seller token、JSON 和错误处理。
- `frontend/src/App.jsx` 是工作台组合根，承载导航状态、数据加载和页面装配。
- `frontend/src/ui.jsx` 是通用 UI primitives，修改时注意所有页面共享影响。
- `frontend/src/styles.css` 对齐离线设计真源，桌面要接近 `Closer 工作台（离线版）.html`，移动端必须无横向溢出。
- 前端不能直接访问数据库，不能复制后端业务判断，不能绕过审批发送。

## API 和鉴权默认契约

- API base path: `/api/v1`。
- 本地 MVP token: `Authorization: Bearer seller:<id>`。
- 正式 API key: `Authorization: Bearer cak_...`。
- 测试兼容: `X-Seller-Id`，默认 seller `1`。
- 错误形状: `{ "error": { "code": "...", "message": "..." } }`。
- 分页形状: `{ "items": [...], "total": n, "page": n, "page_size": n }`。
- 所有租户数据必须受 `seller_id` 隔离。新增 API 和服务测试必须覆盖或继承这一点。

## 编码规范

- 保持 routers thin、services deterministic、agent orchestration-only。
- 金额使用 `Decimal`，不要用 float 做报价、底价、汇率和 PI 金额。
- 测试中禁止真实调用 LLM、IMAP、SMTP、WhatsApp、对象存储、汇率或监控 webhook。
- 外部 provider 要通过配置和 adapter 边界接入，默认 disabled/rule_based/payload_only 要保持本地可测。
- 改 API schema 时同步 `app/schemas.py`、相关 router/service、测试和前端消费点。
- 改 ORM 时同步 `app/models.py`、迁移 SQL、schema/API 测试。
- 改 Agent 工具签名时同步 `app/agent_tools.py`、`app/agent/tools.py`、Graph/runtime 测试。
- 前端页面切换必须清理不属于新页面的局部状态，尤其是 `selectedCustomer`、`quoteDetail` 这类详情状态。
- 共享 UI class 要小心：例如 `.row` 是 flex 工具类，列表卡片样式应限定到 `.rows > .row`。
- 很多源码文件顶部有 `[INPUT] / [OUTPUT] / [POS] / [PROTOCOL]` 注释，改文件职责时要同步更新。
- 不提交 secrets、`.env`、本地数据库、缓存、构建产物、Playwright 失败产物、`tmp/`。

## 关键坑点

- `Closer 工作台（离线版）.html` 是视觉和交互参考，不是正式应用。正式前端在 `http://127.0.0.1:5173/`，不要在 `file://...html` 上判断 API 功能是否已接好。
- Vite dev server 通过 `/api` 代理 FastAPI。后端重启时页面可能残留 502，先刷新并确认 `/api/v1/health`。
- Playwright 配置默认 `CLOSER_E2E_PYTHON=.venv/bin/python`，并会给 E2E FastAPI 进程注入 `CLOSER_ALLOW_DEV_AUTH=1` 与 `CLOSER_ALLOW_DEV_CREDENTIALS=1`。Windows 下如 E2E 找不到 Python，设置为 `.venv\Scripts\python.exe`。
- MiniMax 中国 OpenAI-compatible base URL 用 `https://api.minimaxi.com/v1`。不要把用户给过的 key 写进代码、文档或提交。
- `CLOSER_DELIVERY_MODE=payload_only` 只产生投递 payload；只有 `live` 才允许真实外部发送。
- 底价、敏感承诺、未匹配产品、大额合同等场景必须走 approval/handoff，不能让 Agent 直接发。
- SQLite 测试不等于生产 pgvector 完整能力。涉及向量、迁移、provider 的变更要同时看 `migrations/` 和 docs。
- `readiness.status=ready` 与 `alerts.status=ok` 才能认为生产配置干净；本地 green tests 不代表真实 provider 已接通。

## 本地开发

安装后端：

```powershell
python -m pip install -e .[dev]
```

启动后端：

```powershell
$env:CLOSER_ALLOW_DEV_AUTH='1'
$env:CLOSER_ALLOW_DEV_CREDENTIALS='1'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

启动前端：

```powershell
cd frontend
npm install
npm run dev -- --port 5173
```

常用本地地址：

- Backend health: `http://127.0.0.1:8000/api/v1/health`
- Frontend workbench: `http://127.0.0.1:5173/`
- Vite proxy check: `http://127.0.0.1:5173/api/v1/dashboard/metrics`

## 测试策略

后端测试：

```powershell
python -m pytest
```

建议按风险分层跑：

- 改 router/API: 跑对应 `tests/test_*_api.py`，再跑全量 `python -m pytest`。
- 改 service: 跑对应 service/tool 测试，必要时加 API 集成测试。
- 改 Agent/Graph: 跑 `tests/test_agent_runtime.py`、`tests/test_graph_policy.py` 和相关 tool/service 测试。
- 改 provider 配置/readiness: 跑 readiness、production_check、provider 相关测试。

前端测试：

```powershell
cd frontend
npm run build
npm run test:e2e
```

前端 E2E 会自动启动 FastAPI 与 Vite，并跑 desktop/mobile 两个项目。涉及布局、导航、共享 UI、移动端或 API 接缝时必须跑 E2E。移动端要求无横向溢出。

提交前最低检查：

```powershell
git diff --check
```

## Demo 和生产检查

本地 demo 主链路：

```powershell
python scripts/demo_flow.py
```

生产只读检查：

```powershell
python scripts/production_check.py --base-url https://api.example.com --token "$env:CLOSER_PRODUCTION_TOKEN" --json
```

调度彩排：

```powershell
python scripts/production_check.py --base-url https://api.example.com --token "$env:CLOSER_PRODUCTION_TOKEN" --run-scheduler --json
```

生产关键环境变量地图见 `docs/ENVIRONMENT.md`，部署判定见 `docs/PRODUCTION_RUNBOOK.md`。

## 部署判定

上线前必须核对：

- `CLOSER_AGENT_MODEL` 和对应 API key env 已配置。
- Graph decision provider 不再依赖纯本地默认，或明确记录演示风险。
- Embedding、knowledge index/search、exchange rate、monitoring、document storage、delivery mode 都有生产决策。
- `CLOSER_CREDENTIALS_SECRET` 已配置且不使用开发默认密钥。
- `/api/v1/ops/readiness` 为 ready，`/api/v1/ops/alerts` 为 ok。
- production_check 通过，真实外部 cron/monitoring 已彩排。

## Git 工作规则

- 每个任务完成后要有针对性测试；测试通过再提交。
- Every completed schedule task must include focused tests and a commit after tests pass.
- 不要回滚用户或队友已有改动，除非用户明确要求。
- 发现设计参考和正式前端不一致时，优先保持正式 API 工作流，同时用参考页对齐视觉和交互。
- 修改根项目契约时，检查相关子目录 `CLAUDE.md` 是否需要同步；修改子目录职责时，也要回看本文件是否过期。
