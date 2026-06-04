---
name: closer-ops-readiness
description: Check whether the prototype and production provider boundaries are configured enough for evaluation, deployment, and monitoring.
---

# 原型运维就绪检查

## Purpose

让评审者看到项目不只是本地 Demo，还能解释真实生产接线边界。该技能输出 Agent、RAG、投递、凭据、汇率、对象存储、监控、调度和失败投递的 readiness/alerts。

## Inputs

- `seller_id`
- environment variables
- seller settings
- channel account state
- failed delivery attempts
- exchange rate cache

## Outputs

- readiness status: ready/degraded/unready
- readiness checks
- alerts status
- warning and critical items
- production check JSON

## Runtime Entrypoints

- API: `GET /api/v1/ops/readiness`
- API: `GET /api/v1/ops/alerts`
- API: `POST /api/v1/ops/scheduler/run`
- Script: `scripts/production_check.py`
- Services: `app/services/readiness.py`、`app/services/ops_alerts.py`、`app/services/ops_scheduler.py`
- Tests: `tests/test_readiness.py`、`tests/test_ops_alerts.py`、`tests/test_ops_scheduler.py`、`tests/test_production_check_script.py`

## Steps

1. 读取 Agent model 和 graph decision provider 配置。
2. 检查 embedding、knowledge index/search provider。
3. 检查 delivery mode、渠道凭据和 credential secret。
4. 检查对象存储、汇率源、exchange cache。
5. 检查 failed delivery、pending approval、due follow-up。
6. 输出 readiness 和 alerts。
7. production_check 脚本对外提供命令行检查入口。

## Guardrails

- readiness 是生产接线检查，不代表真实外部 provider 已自动可用。
- 本地 green tests 不等于 production ready。
- monitoring 上报失败不阻塞业务任务，但必须进入调度结果。

## Validation

```powershell
python -m pytest tests/test_readiness.py tests/test_ops_alerts.py tests/test_ops_scheduler.py tests/test_production_check_script.py
```

生产检查 dry run：

```powershell
python scripts/production_check.py --base-url http://127.0.0.1:8000 --token seller:1 --json
```
