# custody-control-assurance-lab

[![ci](https://github.com/Esoterics611/custody-control-assurance-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/Esoterics611/custody-control-assurance-lab/actions/workflows/ci.yml)

A **synthetic, purely defensive** Breach & Attack Simulation (BAS) lab that models the
governance stack of an institutional digital-asset **custody** platform — a Transaction
Authorization Policy (TAP) engine, pre-signing compliance screening, RBAC with
segregation-of-duties, and an admin-quorum gate on policy changes — and then
**continuously attacks those controls to prove they hold**, reporting coverage mapped to
**MITRE ATT&CK** and **NIST CSF 2.0**. There are **no real keys, no real sanctions feeds,
and no real exchange or API credentials** anywhere in this repository; the "system under
test" is a small, honest model of the controls, and every simulation validates that a
control **blocks, escalates, or detects** an attacker action — it never attacks a real
system.

> **Why this exists.** Most candidates *talk* about validating controls. This *runs* the
> validate-and-verify loop: it stands up the controls, emulates the attacker, asserts each
> control holds, and — the part that matters — **catches a control the moment it
> regresses**, with executive-readable evidence, in CI.

![Security console](docs/img/console.png)

---

## What it does

1. **Models the custody governance stack** (`src/cal/custody/`) — the *system under test*:
   a pure TAP policy engine, compliance screening, RBAC + four-eyes, and an admin-quorum
   governor, wired into a single `submit()` pipeline.
2. **Runs 12 Breach & Attack Simulations** (`src/cal/assurance/`) — one attacker scenario
   per control objective — and asserts the control **blocks / escalates / denies / flags**
   correctly.
3. **Produces an assurance report** mapped to MITRE ATT&CK + NIST CSF 2.0 — coverage,
   pass/fail, and **drift vs a baseline** — as JSON and a standalone dark HTML console.
4. Is exercised by **pytest** (control/API level) and **Playwright** (UI/E2E, Page Object
   Model), all wired into **GitHub Actions CI**.

## Architecture — the submit pipeline

Each stage is a control the assurance layer validates:

```
submit(tx) → [1 RBAC] → [2 screening] → [3 TAP policy] → [4 approval/quorum] → [5 mock signer]
              authz fail    sanction →BLOCK   rule →ALLOW /        needs X-of-Y &     only if fully
              → BLOCK       risk →BLOCK        BLOCK / ESCALATE     four-eyes / quorum  ALLOWed
                            travel-rule flag
```

```
src/cal/
├── models.py            TransactionRequest, Decision, enums, results (Decimal money)
├── clock.py             injectable clock — no wall-clock reads in business logic
├── custody/             ← SYSTEM UNDER TEST
│   ├── policy_engine.py   TAP: ordered, top-down first-match, default-deny, velocity
│   ├── screening.py       sanctions / risk score / Travel Rule
│   ├── rbac.py            roles, four-eyes SoD, admin-quorum governor
│   └── platform.py        submit pipeline wiring every control together
├── assurance/           ← THE VALIDATION FRAMEWORK
│   ├── controls.py        registry: control → MITRE ATT&CK + NIST CSF 2.0
│   ├── simulations.py     12 BAS scenarios (one per control objective)
│   ├── runner.py          orchestrate sims, compute coverage + drift
│   └── report.py          emit JSON + standalone HTML assurance report
└── api/app.py           FastAPI surface  ·  console/index.html  security console (E2E target)
```

## The control catalog

| ID | Control objective | Stage | MITRE | NIST CSF 2.0 | Validated by |
|----|------------------|-------|-------|--------------|--------------|
| C-01 | Default-deny: unmatched tx is blocked | Policy | T1567 | PR.AA / GV.PO | `sim_default_deny` |
| C-02 | Destination allowlist enforced | Policy | T1567 | PR.AA | `sim_non_whitelisted_dest` |
| C-03 | Amount limit triggers approval (boundary-correct) | Policy | T1657 | GV.PO | `sim_over_limit_approval` |
| C-04 | Velocity cap on rolling window | Policy | T1657 | DE.CM | `sim_velocity_drain` |
| C-05 | Rule-ordering / shadowing: intended rule wins | Policy | T1657 | GV.PO | `sim_rule_shadowing` |
| C-06 | Type-confusion bypass blocked (CONTRACT_CALL/APPROVE governed) | Policy | T1657 | PR.PS | `sim_contract_call_bypass` |
| C-07 | Sanctioned destination blocked + alert | Screening | T1657 | DE.AE / RS.MA | `sim_sanctioned_dest` |
| C-08 | High-risk score blocked (boundary-correct) | Screening | T1657 | DE.AE | `sim_high_risk_score` |
| C-09 | Travel Rule flagged above threshold | Screening | — | GV.OC | `sim_travel_rule` |
| C-10 | RBAC: non-initiator role cannot submit | Access | T1078 | PR.AA | `sim_rbac_denied` |
| C-11 | Four-eyes / SoD: initiator cannot self-approve | Approval | T1548 | GV.RR | `sim_self_approval` |
| C-12 | Admin quorum required to change policy | Governance | T1098 | GV.RR / GV.PO | `sim_quorum_bypass` |

Full prose per control: [`atlas/CONTROL_CATALOG.md`](atlas/CONTROL_CATALOG.md). Per-stage
threats: [`atlas/THREAT_MODEL.md`](atlas/THREAT_MODEL.md).

## Quickstart

```bash
make install     # uv sync + Playwright chromium
make test        # uv run pytest -n auto         (63 control/API tests)
make assure      # run the BAS suite -> reports/assurance.{json,html} + prints the table
make serve       # API + security console at http://127.0.0.1:8000/
make e2e         # Playwright E2E (Page Object Model)
make lint        # ruff + black --check
```

## How the assurance report works

`make assure` runs every simulation against a freshly-built reference platform, joins the
results to the control registry, computes per-CSF and per-ATT&CK coverage, and writes a
standalone HTML report (plus JSON). Pass `--baseline reports/baseline.json` to compute
**drift** — controls that regressed since the last run. The CLI exits non-zero if any
control fails, so it gates CI.

| All controls green | A regression detected (drift) |
|---|---|
| ![report](docs/img/assurance-report.png) | ![drift](docs/img/assurance-drift.png) |

### See the drift loop yourself

```bash
./scripts/demo.sh        # baseline → regress the policy → harness catches drift → restore
```

This is the centerpiece: weaken one limit and the harness immediately turns the affected
controls **red** and reports them as drift — proving it actually detects an *ineffective*
control, not just a passing one. (The same behavior is asserted as a "negative control"
unit test in `tests/python/test_assurance_runner.py`.)

## How this maps to security-assurance practice

- **Control validation / continuous assurance** — controls are *tested*, not assumed;
  every run is evidence.
- **Breach & Attack Simulation** — automated attacker emulation per control objective.
- **MITRE ATT&CK + NIST CSF 2.0** — each control is mapped, and coverage is reported by
  technique and by CSF function.
- **Drift detection** — a baseline + diff catches a control the moment it regresses.
- **Defense in depth** — the pipeline terminates at the first control that fires; the
  drift demo shows how weakening one layer degrades several.

## Scope & safety

Everything here is **synthetic and defensive**. No real private keys, no real sanctions
or OFAC feed (`data/sanctions.sample.json` is fabricated and labelled `SYNTHETIC TEST
DATA`), no real exchange/API credentials, and no tooling that attacks any real system.
Money is always `decimal.Decimal`; business logic never reads the wall clock. The control
*semantics* are modeled on a real, independently-built institutional digital-asset
compliance layer (an OFAC-style restriction list, a KYC registry, per-minter mint
ceilings, and a Governor/Timelock), re-expressed here as a small honest model so the
controls can be attacked and validated offline.
