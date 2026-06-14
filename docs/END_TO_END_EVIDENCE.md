# 端到端成交链路证据表

这张表用同一条演示询盘说明 8 个 Skill/Workflow 如何形成闭环，并标明哪些能力是确定性后端规则，哪些依赖 LLM/provider。

| Step | 业务动作 | 入口 | 能力类型 | 可验证证据 |
| --- | --- | --- | --- | --- |
| 1 | 多渠道询盘进入 | `POST /api/v1/webhooks/site_form`、email polling、WhatsApp adapter | 确定性 API/adapter | 创建 `customer`、`inquiry`、`conversation`、`message` |
| 2 | 询盘评分 | `score_inquiry` | 规则优先，可接 LLM 辅助 | `grade`、`score`、`signals`；测试 `tests/test_scoring_tool.py` |
| 3 | 客户档案 | `get_customer`、`GET /api/v1/customers/{id}` | 确定性聚合 | 历史询盘、会话、报价、跟进、客户 preferences |
| 4 | 产品匹配/知识检索 | `match_product`、`search_knowledge` | 产品匹配为确定性 token 证据；RAG provider 可替换 | `confidence`、备选产品、matched fields、knowledge chunks |
| 5 | 报价草稿 | `calc_quote` | 确定性报价引擎 | MOQ、阶梯价、物流、汇率缓存、floor price、`hard_min_price` |
| 6 | PI 生成 | `generate_pi`、approval `pi_generate` | 确定性审批与文档生成 | PI 必须先审批；硬底价触碰直接阻断 |
| 7 | 发送与跟进 | `send_message`、`create_followup`、`POST /api/v1/workers/run-due` | 确定性队列/投递边界 | delivery attempt、retry、follow-up task |
| 8 | 运维就绪 | `GET /api/v1/ops/readiness`、`GET /api/v1/ops/alerts` | 确定性诊断，可接外部 monitoring sink | provider 配置、渠道凭证、失败投递、待审批、汇率缓存风险 |

## 护栏证据

- 软底价：`floor_price` 命中后进入人工审批，不能由 Agent 自动发送。
- 硬底价：`logistics_template.hard_min_price` 触碰后直接阻断 PI 生成和报价发送，即使已有审批也会在执行时重新校验。
- 敏感承诺：`send_message` 会识别敏感承诺和低于底价的金额表达，创建 `message_send` approval。
- 未匹配产品：低置信度 `match_product` 返回 `needs_review`，引导销售从备选品中人工确认。

## Demo Seed 验证路径

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
cd frontend
npm run dev -- --port 5173
```

在线 Demo 可直接打开：

```text
https://cj66666.github.io/chengjiaoguan/
```

线上版本使用 GitHub Pages 静态托管和浏览器内置 mock 数据，保留 Wave 3 评审所需的主交互。完整后端验证打开 `http://127.0.0.1:5173/`，点击 `Demo Seed` 后依次查看：

1. 工作台指标与待审批提醒。
2. 询盘收件箱中的 A 级询盘。
3. 客户档案抽屉中的历史报价和时间线。
4. 产品库、价格规则与渠道配置。
5. 审批页中的底价/敏感承诺拦截。
6. readiness 与 alerts 的生产接线状态。
