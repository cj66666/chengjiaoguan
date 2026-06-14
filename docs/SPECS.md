# Specs
<!--
/**
 * [INPUT]: 依赖比赛初赛/复赛提交说明、README.md、WAVE2_SUBMISSION.md 与当前 Closer 产品实现
 * [OUTPUT]: 对外提供 AI+应用项目提案 Specs，覆盖项目名称、应用场景、目标用户、核心问题、产品思路、AI 作用与评测标准
 * [POS]: docs 的 Specs 提交镜像，满足评审者快速理解项目完整性的基础说明
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
-->

## 2.1 项目名称

Closer 工作台 - 跨境供应链询盘成交工作台

## 2.2 应用场景

赛道：跨境 IT 服务赛道。

细分方向：供应链询盘。

真实场景：跨境 B2B 出口卖家每天从独立站表单、Email、WhatsApp 等渠道收到海外买家的采购询盘。询盘往往包含产品型号、数量、交期、目标价格、认证要求、目的港、付款方式和售后条款。销售团队需要快速判断询盘价值、匹配产品、查询知识库、生成报价、控制底价风险并持续跟进。

Closer 工作台将这些动作收束到一个 AI 工作台中，服务“询盘进入到报价审批和后续跟进”的核心流程。

## 2.3 目标用户

- 小微跨境 B2B 出口卖家。
- 工贸一体企业和外贸团队。
- 缺少专职售前、报价、CRM 和自动化运维能力的供应链型商家。
- 需要同时处理独立站、邮箱、WhatsApp 等多渠道询盘的销售人员和业务负责人。

## 2.4 核心问题

- 多渠道询盘分散，客户上下文断裂，销售很难知道同一个买家的历史沟通、报价和跟进状态。
- 人工筛选询盘、查产品、算报价、写英文回复耗时，响应速度直接影响成交机会。
- 普通 AI 自动回复容易越权，可能误报底价、承诺敏感条款、处理超范围产品或绕过大额合同审批。
- 小团队缺少可审计的审批、投递、重试、跟进和运维就绪机制，Demo 容易跑通，真实业务难落地。

## 2.5 产品思路

核心流程：

1. 买家询盘从 site form、Email、WhatsApp 等渠道进入。
2. 系统按租户创建或关联 customer、inquiry、conversation、message。
3. Agent 通过后端工具完成询盘评分、客户画像、产品匹配、知识检索和报价草稿。
4. 报价引擎按 MOQ、阶梯价、物流、汇率、底价和有效期生成 quotation。
5. 底价、敏感承诺、大额合同、未匹配产品、PI 生成等风险动作进入 approval。
6. 人工批准后，后端执行投递并记录 delivery attempt；失败投递进入 retry。
7. workers 统一调度到期跟进、投递重试、邮件轮询和汇率缓存刷新。
8. 前端工作台展示看板、收件箱、客户、产品、报价、审批、通知、设置和 readiness。

Wave 2 原型通过 `POST /api/v1/demo/seed` 和 `scripts/demo_flow.py --approve --run-workers` 跑通这条闭环。

## 2.6 AI 在哪里发挥作用

本项目不是普通 CRM 或表单工具，AI 作用在“理解、判断、生成、协同”四个环节：

- 理解询盘：从自然语言询盘中识别采购意图、产品需求、数量、交期、认证、目的地和风险信号。
- 判断优先级：结合数量、预算、产品匹配、客户画像和历史上下文生成 A/B/C 询盘等级。
- 生成业务草稿：生成报价草稿、英文回复、PI 草稿和后续跟进建议。
- 协同人工：AI 只提出建议和草稿，真正高风险动作由服务端护栏进入人工审批，保证可控和可审计。

当前仓库默认使用 deterministic/rule_based provider，确保评测环境无需真实 LLM key 也能跑通；生产环境可通过 `CLOSER_AGENT_MODEL`、Graph decision provider、embedding/search/index provider 接入真实模型和语义索引。

## 2.7 评测标准

建议评测问题：

- 是否能通过公开 API 创建一条供应链询盘，并自动生成客户、询盘、会话和消息？
- 是否能对询盘输出可解释的等级、分数和信号？
- 是否能匹配产品和知识片段，并给出报价草稿？
- 是否能在底价、敏感承诺、大额合同、未匹配产品或 PI 生成风险下强制进入人工审批？
- 是否能在审批通过后发送消息并记录 delivery attempt？
- 是否能通过 Prototype 查看看板、收件箱、客户、报价、审批、产品、设置和 readiness？
- 是否能在无真实外部 key 的评测环境中通过自动化测试和 demo workflow？

可执行验证：

```powershell
python -m pytest
```

```powershell
cd frontend
npm run build
npm run test:e2e
```

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python scripts/demo_flow.py --base-url http://127.0.0.1:8000 --approve --run-workers --json
```

2026-06-14 本地验证结果：

- `python -m pytest`: 182 passed，1 warning
- `cd frontend && npm run build`: passed
- `cd frontend && npm run test:e2e`: 2026-06-04 浏览器回归记录为 12 passed

## 2.8 项目提交

提交当前仓库时，平台项目说明优先引用：

- `README.md`
- `docs/SPECS.md`
- `docs/WAVE2_SUBMISSION.md`
- `skills/README.md`
- `docs/DEMO_RUNBOOK.md`

公开评审前必须先检查 `docs/PUBLIC_REVIEW_CHECKLIST.md`，避免把本赛段不要求公开的原始规格文档、排期表、本地数据库、凭据或构建产物一起公开。
