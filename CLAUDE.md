# CLAUDE.md — custody-control-assurance-lab

## What this is
A continuous security-control-validation / Breach & Attack Simulation lab for a
*mock* institutional digital-asset custody platform. We model the governance
controls (TAP policy engine, compliance screening, RBAC/SoD, admin quorum),
then run automated attacker-emulation simulations that PROVE each control is
effective, and report coverage mapped to MITRE ATT&CK + NIST CSF 2.0.

## Non-negotiable rules
- DEFENSIVE ONLY. We validate controls. We never build tooling to attack real
  systems. All data is SYNTHETIC: no real keys, no real sanctions feeds, no real
  exchange/API credentials.
- Money is ALWAYS `decimal.Decimal`. Never `float` for amounts.
- NO `time.sleep`, NO wall-clock reads inside business logic. Use src/cal/clock.py
  and pass timestamps into engines. Logic must be deterministic + unit-testable.
- The policy engine is PURE: (request, history) -> result. No I/O.
- Default-deny: anything not explicitly allowed by a matching rule is BLOCKED.
- Tests assert behavior of controls; they never reach into private internals.
- Playwright: Page Object Model. NO raw selectors in spec files — selectors live
  in page objects. NO hardcoded sleeps; use web-first assertions/auto-waiting.

## Stack
Python 3.12 · uv · pytest + pytest-xdist + allure-pytest · ruff + black ·
FastAPI + uvicorn (tested via TestClient) · Playwright + @playwright/test (TS) ·
GitHub Actions.

## Architecture / layering
src/cal/custody/* = System Under Test (the controls).
src/cal/assurance/* = the validation framework (registry, simulations, runner, report).
src/cal/api/app.py = FastAPI surface. console/index.html = demo UI + Playwright target.
Flow: API/console -> platform.submit() -> [RBAC -> screening -> policy -> approval/quorum -> mock signer].

## Where to add things
- New control  -> implement in custody/, register in assurance/controls.py
                  (with MITRE + CSF mapping), add a simulation in
                  assurance/simulations.py, add a pytest test, update
                  atlas/CONTROL_CATALOG.md.
- New attack scenario -> add a simulation that asserts the expected control
                  outcome; never weaken a control to make a sim pass.

## How to run
- make install        # uv sync + playwright install
- make test           # uv run pytest -n auto
- make assure         # uv run python scripts/run_assurance.py  (writes report)
- make serve          # uvicorn api.app:app + serve console/
- make e2e            # npx playwright test

## Anti-patterns to REFUSE
- float for money; time.sleep; wall-clock in logic; selectors in spec files;
  a simulation that passes by loosening a control; real/sensitive data of any kind;
  any code whose purpose is to attack a real external system.

## Provenance note
Control semantics in this lab are modeled on a real, independently-built
institutional digital-asset protocol (`nexus-protocol`: ERC-4626 vaults, a UUPS
stablecoin, an OFAC-style RestrictionList denylist, a KYCRegistry, a
MintController with per-minter ceilings, and an OZ Governor/Timelock). This repo
re-expresses those control *objectives* as a small, honest, synthetic Python
model so they can be attacked and validated offline. It is NOT a clone of any
vendor product and contains none of that protocol's keys, addresses, or data.
