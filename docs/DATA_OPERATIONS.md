# 数据维护、多语言与 ROI 说明

## 录入一次、长期复用

Closer 的报价质量取决于产品、价格规则、知识库和渠道凭证四类数据。建议按下面频率维护：

| 数据 | 入口 | 建议频率 | 责任人 |
| --- | --- | --- | --- |
| 产品库 | `POST /api/v1/products/import` 或产品库页面 | 新品上架/下架时；至少每月复核 | 销售运营 |
| 价格规则 | `POST /api/v1/pricing-rules` | 成本、阶梯价、汇率或物流变化时 | 报价负责人 |
| 知识库 | `POST /api/v1/knowledge` | FAQ、认证、质保、包装变化时 | 产品/售前 |
| 渠道凭证 | `POST /api/v1/channels`、`rotate-credentials` | token 过期前、人员交接时 | 管理员 |

## 产品 CSV 模板

`/products/import` 支持 CSV/XLSX，首行字段可用英文或部分中文别名。

```csv
name,sku,specs,cost,currency,moq,images,description,status
Aspen 5-Seater PE Rattan Corner Sofa Set,OF-RT-205,"{""material"":""PE rattan"",""frame"":""aluminum"",""certification"":""CE""}",128,USD,50,"[""https://example.com/aspen.jpg""]","Outdoor sofa set for garden retailers",active
```

## 价格规则 JSON 模板

`floor_price` 是需要人工审批的软底线；`logistics_template.hard_min_price` 是不可审批绕过的硬熔断线。

```json
{
  "product_id": 1,
  "currency": "USD",
  "floor_price": "168.00",
  "margin_rate": "0.28",
  "tiered_prices": [
    {"min_qty": 50, "price": "198.00"},
    {"min_qty": 200, "price": "182.00"},
    {"min_qty": 500, "price": "172.00"}
  ],
  "logistics_template": {
    "unit_cost": "12.00",
    "hard_min_price": "158.00",
    "exchange_rate_cache": {
      "confirmed": true,
      "expires_at": "2026-06-30",
      "rates": {"USD": {"EUR": "0.92"}}
    }
  },
  "valid_days": 14
}
```

## 多语言询盘边界

- 入站消息保留 `language` 字段，email、WhatsApp、site form 都可传入语言标记。
- 当前确定性报价、匹配、护栏不依赖英文；金额、MOQ、SKU、产品字段和价格规则按结构化数据工作。
- LLM/provider 相关能力会受模型多语言能力影响。生产环境建议使用同一批英文、西语、阿语、葡语样本复跑 `score_inquiry`、`match_product`、`calc_quote` 和 `send_message`。
- 对低置信度非标描述，`match_product` 会输出备选品和差异提示，不直接给唯一结论。

## ROI 口径与不成立条件

README 中“年增毛利约 7.2 万”的口径是可证伪假设：

- 月有效询盘：100 条。
- 年有效询盘：1200 条。
- 响应速度、优先级和跟进闭环带来成交率提升：3 个百分点。
- 年新增成交：36 单。
- 单均毛利：2000 元。
- 年增量毛利：约 72000 元。

这个测算在以下情况下不成立：

- 询盘质量很低，A 级询盘不足。
- 产品毛利不足以覆盖实施和维护成本。
- 产品/价格/知识库长期不更新，报价依据失真。
- 渠道凭证失效但无人处理，导致漏单。
- 团队不执行人工审批和跟进任务。

## 30 秒录屏脚本

1. 点击 `Demo Seed`，展示看板出现“待处理/护栏触发”。
2. 进入询盘收件箱，点开 A 级询盘。
3. 展示 AI 摘要、底价红线和敏感操作拦截。
4. 点击审批页，展示“采纳建议并发送/修改报价/我来接管”。
5. 切到产品库和 readiness，展示数据与生产接线边界。
