# Phase 5 — FastAPI API + static security console

api/app.py: POST /transactions -> PipelineResult.to_dict(); GET /policy; POST /policy/change
(200 / 403 + QuorumError message); POST /assurance/run; GET /assurance/report; GET /healthz.
Single in-memory reference CustodyPlatform; CORS; tests via Starlette TestClient.
console/index.html: self-contained dark SOC console (amber accent, monospace) — submit panel
(color-coded decision/stage/alerts), assurance panel (12-control grid + CSF/ATT&CK coverage),
policy-change panel (quorum gate). Stable data-testid on interactive elements. Copy names
things by what the user does.
Tests (TestClient): healthz; sanctioned -> BLOCK @ screening; over-limit -> REQUIRE_APPROVAL;
single-admin policy change -> 403; assurance/run returns 12 controls.

Acceptance: API tests green; make serve serves console + API.
