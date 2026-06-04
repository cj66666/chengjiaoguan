# Public Review Checklist
> L3 | 父级: ./CLAUDE.md

<!--
/**
 * [INPUT]: 依赖比赛公开仓库说明、git ls-files、.gitignore 与当前 Wave 2 提交范围
 * [OUTPUT]: 对外提供公开评审前清理清单，区分必须公开、建议公开、公开前应移除或脱敏的材料
 * [POS]: docs 的公开评审风险镜像，防止把本赛段不要求的内部资料误公开
 * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
 */
-->

## 公开原则

W1/W2/W3 主要展示团队 AI 实战能力，评审关注 Specs、Skill、Agent 和 Prototype 是否完整、有效、可运行。公开仓库应只保留本赛段评分所需材料，不要把内部产品文档、排期、商业资料或凭据一起公开。

本项目建议使用一个专门的公开提交分支或公开镜像仓库，而不是直接把日常开发仓库长期公开。

## Wave 2 必须公开

- `README.md`
- `docs/SPECS.md`
- `docs/WAVE2_SUBMISSION.md`
- `skills/`
- `docs/DEMO_RUNBOOK.md`
- `app/`
- `frontend/`
- `scripts/demo_flow.py`
- `scripts/production_check.py`
- `tests/`
- `pyproject.toml`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/playwright.config.js`

这些材料足以让评委理解项目、运行 Skills/Workflow、打开 Prototype 并进行 AI 评测。

## 建议公开

- `docs/COMPLETION_AUDIT.md`
- `docs/IMPLEMENTATION_AUDIT.md`
- `docs/ENVIRONMENT.md`
- `docs/PRODUCTION_RUNBOOK.md`
- `docs/VISUAL_QA.md`
- `migrations/001_initial.sql`

这些材料能证明工程完整度和生产边界，但公开前仍应检查是否包含内部信息。

## 公开前应移除或脱敏

当前仓库中以下已被 git 跟踪的材料可能超出 Wave 2 评分范围，公开前建议移到私有仓库、删除出公开分支，或替换为摘要版：

- `docs/source/成交官_需求规格说明书_V1.0.docx`
- `docs/source/成交官_产品设计文档_V1.1.docx`
- `docs/source/成交官_技术架构设计文档_V1.1.docx`
- `docs/source/成交官_数据库设计文档_V1.0.docx`
- `docs/source/成交官_后端API契约_V1.0.docx`
- `docs/source/成交官_Agent工具接口清单_V1.0.docx`
- `docs/source/跨境B2B_AI询盘成交Agent_市场调研报告.docx`
- `docs/reference/Closer 工作台（离线版）.html`

原因：这些文件包含完整产品规格、原始调研或离线原型，不是 Wave 2 必需的 Specs/Skill/Agent 交付物。公开它们会增加信息泄露和评审噪音。

## 绝不能公开

`.gitignore` 已覆盖以下类型，但公开前仍要人工确认：

- `.env`、`.env.*`
- 真实 API key、access token、cookie、账号密码
- `*.db`、本地数据库和演示数据
- `node_modules/`
- `.venv/`
- `frontend/dist/`
- `frontend/playwright-report/`
- `frontend/test-results/`
- `tmp/`、`temp/`
- 日志文件和失败截图

## 建议公开分支流程

1. 从当前开发分支创建 `codex/wave2-public-submission`。
2. 保留 Wave 2 必须公开和建议公开的源码、测试、脚本、README 与 docs。
3. 从公开分支移除或脱敏“公开前应移除或脱敏”列表中的原始文档。
4. 复跑：

```powershell
python -m pytest
cd frontend
npm run build
npm run test:e2e
```

5. 检查：

```powershell
git status --short
git ls-files
git diff --check
```

6. 确认平台提交链接指向公开分支或公开镜像仓库。
7. 评审结束后，如平台允许，可重新设为私有。

## 平台说明建议

公开仓库说明可以写：

“本仓库为 Wave 2 复赛评审版本，仅包含 Specs、核心 Skills、Agent/Workflow、Prototype、测试和运行说明。完整商业文档、内部排期和生产凭据未公开。”
