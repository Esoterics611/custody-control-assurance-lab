# Phase 0 — Scaffold

Scaffold a Python + Playwright security-control-validation project named
"custody-control-assurance-lab". DEFENSIVE assurance lab for a MOCK custody
platform — all data synthetic, no real systems.

Stack: Python 3.12, uv, pytest + pytest-xdist + allure-pytest, ruff + black,
FastAPI + uvicorn, Playwright + @playwright/test (TypeScript), GitHub Actions.

Create the full tree (src/cal/{custody,assurance,api}, console, policies, data,
tests/{python,e2e}, scripts, atlas, ai/prompts). Then: pyproject.toml (uv deps +
ruff/black config), pytest.ini (markers + pythonpath=src + strict-markers),
Makefile (install/test/assure/serve/e2e/lint), .env.example (NO real secrets),
.gitignore, README stub, .github/workflows/ci.yml skeleton, and CLAUDE.md with the
non-negotiable rules. No business logic yet. Verify `uv sync` clean and
`uv run pytest` collects 0 tests.

Acceptance: uv sync clean; pytest runs 0 tests with no import errors; CLAUDE.md present.
