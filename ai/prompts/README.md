# Build prompts

The numbered prompts used to build this repo with Claude Code, in order — one per phase,
committed after each went green. They show the working method: a `CLAUDE.md` anchor (see
the repo root) re-read every session, then a focused prompt per phase with a concrete
acceptance check.

| Phase | Prompt | Outcome |
|-------|--------|---------|
| 0 | [00-scaffold.md](00-scaffold.md) | project tree, tooling, CI skeleton, CLAUDE.md |
| 1 | [01-policy-engine.md](01-policy-engine.md) | domain model + TAP engine + unit tests |
| 2 | [02-screening-rbac-quorum.md](02-screening-rbac-quorum.md) | screening + RBAC/SoD + admin quorum |
| 3 | [03-platform-pipeline.md](03-platform-pipeline.md) | custody pipeline + integration tests |
| 4 | [04-assurance-framework.md](04-assurance-framework.md) | BAS runner + ATT&CK/CSF report (centerpiece) |
| 5 | [05-api-console.md](05-api-console.md) | FastAPI + security console |
| 6 | [06-playwright-e2e.md](06-playwright-e2e.md) | Playwright E2E (Page Object Model) |
| 7 | [07-ci-docs-polish.md](07-ci-docs-polish.md) | CI, README, atlas, demo polish |

[session-kickoff.md](session-kickoff.md) is the prompt pasted at the start of each session
to re-anchor context.
