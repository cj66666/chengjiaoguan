# 交叉评测议题响应计划

> 来源：Synnovator `cj66666/closer` 仓库 2026-06-05 的 6 个公开 issue。#5 与 #6 内容重复，本计划按 5 组建议合并执行。

## 议题归纳

| Issue | 主要建议 | 本轮处理 |
| --- | --- | --- |
| #1 | 补 Quick Start、LLM 选型、数据来源/导入、渠道接入、ROI 口径、架构图与护栏演示 | README 增加评审入口；新增数据运维说明与证据表 |
| #2 | 增加端到端证据表，区分确定性能力与 LLM 依赖能力，修正演示入口噪声 | 新增 `docs/END_TO_END_EVIDENCE.md` |
| #3 | 补客户长期关系沉淀、Demo 入口、服务对象边界、ROI 敏感性 | 新增数据运维说明，明确复购画像字段和 ROI 不成立条件 |
| #4 | 说明“录入一次、长期复用”、多语言询盘支持边界、30 秒录屏脚本 | 新增 `docs/DATA_OPERATIONS.md`，给出 CSV/JSON 模板和录屏脚本 |
| #5/#6 | 强化渠道凭证健康告警、后端硬底价熔断、低置信度模糊匹配备选 | 已落代码与 pytest：渠道 alerts/readiness、`hard_min_price`、产品匹配 confidence/alternatives |

## 已落地修复

1. 渠道凭证健康告警
   - `GET /api/v1/ops/readiness` 现在能识别 email/WhatsApp 凭证 token 过期或临近过期。
   - `GET /api/v1/ops/alerts` 现在会把渠道缺失凭证、token 过期、通道掉线、凭证未封存/待轮换置顶为告警。
   - 测试：`tests/test_readiness.py`、`tests/test_ops_alerts.py`。

2. 硬底价熔断
   - 价格规则支持在 `logistics_template.hard_min_price` 配置不可审批绕过的绝对硬底价。
   - `calc_quote` 返回 `hard_minimum_breached` 与每行 `hard_min_price`。
   - `generate_pi` 在创建审批前会直接阻断硬底价触碰的 PI 生成。
   - `generate_pi_document` 会在审批批准时再次读取当前数据库价格规则，防止先申请审批、后改规则绕过。
   - 测试：`tests/test_quote_engine.py`、`tests/test_quote_tools.py`、`tests/test_configuration_api.py`。

3. 非标询盘模糊匹配
   - `match_product` 现在返回 `confidence`、`confidence_threshold`、`match_status`、`requires_human_review`。
   - 当最高置信度低于阈值时，不给单一结论，返回 2-3 个备选产品与差异提示。
   - 测试：`tests/test_product_matching.py`。

## 仍需外部材料

- Hosted demo URL：需要部署平台后填写；本地入口仍为 `http://127.0.0.1:5173/`。
- 30 秒录屏：按 `docs/DATA_OPERATIONS.md` 的脚本录制，不应提交大视频文件到仓库。
- 真实渠道心跳：当前 readiness/alerts 不主动访问外部网络；生产环境可在 scheduler 中接入 WhatsApp/IMAP 轻量探针，并把结果写入 channel status 或 monitoring sink。

## 建议复核命令

```powershell
python -m pytest tests/test_quote_engine.py tests/test_quote_tools.py tests/test_product_matching.py tests/test_ops_alerts.py tests/test_readiness.py tests/test_configuration_api.py
cd frontend
npm run build
```
