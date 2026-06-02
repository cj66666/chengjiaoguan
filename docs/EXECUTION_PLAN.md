# Execution Plan

## Source Documents Read

- Market research report.
- Product design document.
- Software requirements specification.
- Technical architecture design.
- Database design.
- Backend API contract.
- Agent tool interface list.
- Balanced two-person schedule, plan A.
- Offline Closer workspace prototype.

## Commit Plan

Each schedule task is completed with tests, a passing test run, and a commit.

1. Repository setup: public GitHub repository, `.gitignore`, `CLAUDE.md`, and this plan.
2. T02: SQLAlchemy models and PostgreSQL migration matching the database design.
3. T05: channel gateway plus site form webhook ingestion and idempotency.
4. T06: email IMAP/SMTP adapter boundary with parsing/sending tests.
5. T07: WhatsApp Cloud API adapter boundary and webhook normalization.
6. T08: inquiry scoring service and `score_inquiry` tool.
7. T09: customer/CRM creation and `get_customer` tool.
8. T10: inquiries, conversations, messages, takeover, and release APIs.
9. T11: quote engine with cost, margin, tiers, MOQ, valid days, and floor-price checks.
10. T12: `calc_quote` and `generate_pi` tools with deterministic quote language.
11. T13: knowledge ingestion, chunking, and lightweight RAG search.
12. T14: `match_product` tool.
13. T15: `send_message` tool with approval handoff for unsafe outbound content.
14. T18: approvals and quotations API.
15. T19: follow-up scheduler and `create_followup` tool.
16. Final verification and push.

## MVP Scope Decisions

- Real external channel calls are adapter boundaries, not live integrations, because credentials are not present.
- Real LLM calls are replaced by deterministic services for testability; the public API and tool interfaces remain compatible with later PydanticAI wiring.
- PostgreSQL/pgvector is represented by a production migration; tests run on SQLite to keep CI and local validation deterministic.

