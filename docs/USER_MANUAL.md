# Custody Control Assurance Lab — Explanation & User Manual

A complete guide to what this project is, the ideas behind it, and how to run, read,
extend, and demo every part of it. For a one-screen overview see the
[README](../README.md); for the control reference see
[`atlas/CONTROL_CATALOG.md`](../atlas/CONTROL_CATALOG.md) and
[`atlas/THREAT_MODEL.md`](../atlas/THREAT_MODEL.md).

---

## Table of contents

1. [What this is (and why)](#1-what-this-is-and-why)
2. [Mental model & key concepts](#2-mental-model--key-concepts)
3. [Install & prerequisites](#3-install--prerequisites)
4. [The five-minute tour](#4-the-five-minute-tour)
5. [The submit pipeline, stage by stage](#5-the-submit-pipeline-stage-by-stage)
6. [The control catalog](#6-the-control-catalog)
7. [Running the assurance harness (CLI)](#7-running-the-assurance-harness-cli)
8. [Reading the HTML report](#8-reading-the-html-report)
9. [The drift demo](#9-the-drift-demo)
10. [The live on-chain target](#10-the-live-on-chain-target)
11. [The API](#11-the-api)
12. [The security console (UI)](#12-the-security-console-ui)
13. [Observability: metrics, history, trend](#13-observability-metrics-history-trend)
14. [Interop exports: Navigator, SARIF, JUnit](#14-interop-exports-navigator-sarif-junit)
15. [Testing](#15-testing)
16. [CI/CD & GitHub Pages](#16-cicd--github-pages)
17. [Docker](#17-docker)
18. [Extending the lab: add a control](#18-extending-the-lab-add-a-control)
19. [Project layout](#19-project-layout)
20. [Reference data: accounts, policy, addresses](#20-reference-data-accounts-policy-addresses)
21. [Troubleshooting & FAQ](#21-troubleshooting--faq)
22. [The 3-minute interview demo](#22-the-3-minute-interview-demo)

---

## 1. What this is (and why)

This is a **Breach & Attack Simulation (BAS) lab** for the **governance controls of an
institutional digital-asset custody platform**. It does three things:

- **Models** a small, honest version of a custody governance stack — a Transaction
  Authorization Policy (TAP) engine, compliance screening, RBAC with segregation of
  duties, an admin-quorum gate, and replay protection.
- **Attacks** those controls with automated simulations and asserts each one
  **blocks / escalates / denies / flags** the attacker correctly.
- **Reports** a severity-weighted **risk posture**, coverage mapped to **MITRE ATT&CK**
  and **NIST CSF 2.0**, and **drift** (a control that regressed) — as an HTML console,
  JSON, an ATT&CK Navigator layer, SARIF, and JUnit.

It runs against two targets: a **mock** platform (always available, deterministic) and,
read-only, a **real deployed** protocol on the Base Sepolia testnet.

**Everything is synthetic and defensive.** No real keys, no real sanctions feed, no
exchange/API credentials, and no tooling that attacks a real system. The on-chain target
is strictly read-only (`eth_call`) against a public testnet.

**Why it's built this way:** validating that a control *works* — and noticing the moment
it *stops* working — is the core of security assurance. Most demos show a control passing;
this one also proves it can **catch an ineffective control**, with evidence, in CI.

## 2. Mental model & key concepts

| Term | Meaning here |
|------|--------------|
| **Control** | A specific security guarantee (e.g. "amount limit forces approval"). Each has an id (`C-03`), a stage, a severity, and MITRE/CSF mappings. |
| **System under test (SUT)** | The mock custody platform in `src/cal/custody/` — the thing being validated. |
| **Simulation (BAS)** | A function that performs an attacker action and returns a `SimResult`. `passed=True` means **the control held**, never that the attack succeeded. |
| **Target** | What the harness validates: `mock` (the Python platform) or `onchain` (real contracts). |
| **Posture score** | A severity-weighted pass rate (0–100) over evaluated controls, with a letter rating (A…F). |
| **Drift** | A control that passed in a baseline run but fails now — a regression. |
| **Pipeline** | The ordered chain of controls a transaction passes through on `submit()`. |

Two non-negotiables baked into the code: **money is always `decimal.Decimal`** (never
`float`), and **business logic never reads the wall clock** (timestamps are injected). These
keep every result exact and deterministic.

## 3. Install & prerequisites

**Prerequisites**

- Python **3.12**
- [**uv**](https://docs.astral.sh/uv/) (env + dependency manager)
- **Node 20+** (only for the Playwright E2E suite)
- Optional: **Docker**, and a public Base Sepolia RPC URL for the live target

**Install**

```bash
git clone https://github.com/Esoterics611/custody-control-assurance-lab
cd custody-control-assurance-lab
make install          # uv sync + Playwright chromium
```

`make install` runs `uv sync` (creating `.venv` from the committed `uv.lock`) and installs
the Playwright browser. To add the optional live on-chain dependency (web3):

```bash
uv sync --extra onchain
```

## 4. The five-minute tour

```bash
make test            # 84 pytest tests (control logic, pipeline, API, exports, monitoring)
make assure          # run the BAS suite -> reports/ + a pass/fail + posture table
make serve           # API + security console at http://127.0.0.1:8000/
make e2e             # Playwright E2E (Page Object Model)
make lint            # ruff + black --check
```

`make assure` prints something like:

```
  MOCK TARGET — custody platform controls
  ----------------------------------------------------------------------
  ✓ C-01  [PASS]  Default-deny: unmatched transaction is bloc  BLOCK @ policy
  ...
  ✓ C-16  [PASS]  Approver-set integrity: duplicate approvers  REQUIRE_APPROVAL @ approval
  ----------------------------------------------------------------------
  16/16 passing | failing: 0
  posture score: 100/100  [A — strong]
```

## 5. The submit pipeline, stage by stage

Every transaction goes through `CustodyPlatform.submit()` (`src/cal/custody/platform.py`).
The pipeline **terminates at the first control that fires** (defense in depth):

```
submit(tx) → [0 replay] → [1 RBAC] → [2 screening] → [3 TAP policy] → [4 approval/quorum] → [5 mock signer]
```

| # | Stage | What it does | Terminal outcome |
|---|-------|--------------|------------------|
| 0 | **replay** | Rejects a `request_id` that already reached the signer | `BLOCK @ replay` |
| 1 | **RBAC** | Initiator must hold the `INITIATOR` role | `BLOCK @ rbac` |
| 2 | **screening** | Sanctions/risk denylist + risk score; Travel-Rule flag (flag does not block) | `BLOCK @ screening` + alert |
| 3 | **policy** | TAP engine: ordered, top-down, first-match, default-deny + velocity | `BLOCK @ policy` or escalate |
| 4 | **approval** | Four-eyes: collect distinct valid approvers vs the required count | `REQUIRE_APPROVAL @ approval` (pending) |
| 5 | **signer** | Mock signer — only fully-ALLOWed transactions reach it | `ALLOW @ signer`, `signed=True` |

The TAP engine is **pure**: `(request, history) → PolicyResult`, no I/O, no clock. Rules are
an ordered list; the first match wins; anything unmatched is **BLOCKed (default-deny)**. A
velocity rule fires when *cumulative* spend from a vault in a rolling window would exceed the
cap. Only signed transactions are recorded into history (so velocity sees prior spend).

## 6. The control catalog

**16 mock controls** validate the pipeline; **5 on-chain controls** validate the real
deployment. Each is mapped to MITRE ATT&CK + NIST CSF 2.0 and carries a severity.

| ID | Objective | Stage | Severity |
|----|-----------|-------|----------|
| C-01 | Default-deny: unmatched tx blocked | Policy | high |
| C-02 | Destination allowlist enforced | Policy | high |
| C-03 | Amount limit → approval (boundary-correct) | Policy | high |
| C-04 | Velocity cap on rolling window | Policy | high |
| C-05 | Rule-ordering / shadowing: intended rule wins | Policy | medium |
| C-06 | Type-confusion bypass blocked (CONTRACT_CALL/APPROVE governed) | Policy | high |
| C-07 | Sanctioned destination blocked + alert | Screening | **critical** |
| C-08 | High-risk score blocked (boundary-correct) | Screening | high |
| C-09 | Travel Rule flagged above threshold | Screening | medium |
| C-10 | RBAC: non-initiator cannot submit | Access | high |
| C-11 | Four-eyes: initiator cannot self-approve | Approval | **critical** |
| C-12 | Admin quorum required to change policy | Governance | **critical** |
| C-13 | Replay/idempotency: executed request cannot replay | Pipeline | **critical** |
| C-14 | Decimal-precision integrity (no float money) | Policy | medium |
| C-15 | Address-normalization: case-varied sanction still blocked | Screening | high |
| C-16 | Approver-set integrity: duplicates can't inflate count | Approval | high |
| OC-01 | Custody contracts deployed & reachable (decimals==6) | On-chain · Infra | medium |
| OC-02 | Restriction-list wiring intact (drift) | On-chain · Compliance | **critical** |
| OC-03 | KYC-registry wiring intact (drift) | On-chain · Compliance | **critical** |
| OC-04 | Denylist surface functional | On-chain · Screening | high |
| OC-05 | Mint-ceiling control present | On-chain · Governance | high |

Each control's threat and the exact simulation that validates it are described in
[`atlas/CONTROL_CATALOG.md`](../atlas/CONTROL_CATALOG.md).

## 7. Running the assurance harness (CLI)

`scripts/run_assurance.py` (also `make assure`) is the entry point.

```bash
uv run python scripts/run_assurance.py [--target mock|onchain|both]
                                       [--policy PATH]
                                       [--baseline PATH]
                                       [--rpc-url URL]
```

| Flag | Purpose |
|------|---------|
| `--target` | `mock` (default), `onchain` (live), or `both`. |
| `--policy` | Validate against an alternate TAP policy file (used by the drift demo). |
| `--baseline` | A prior `assurance.json` (or `{id: passed}` map) to compute **drift**. |
| `--rpc-url` | On-chain RPC URL (else `CAL_ONCHAIN_RPC_URL`, else the vendored default). |

**Outputs** (written to `reports/`):

| File | Target | Contents |
|------|--------|----------|
| `assurance.json` / `assurance.html` | mock | machine + human report |
| `navigator-layer.json` | mock | MITRE ATT&CK Navigator layer |
| `assurance.sarif` | mock | SARIF 2.1.0 (failing controls) |
| `assurance-junit.xml` | mock | JUnit test report |
| `history.jsonl` | mock | one appended line per run |
| `assurance-onchain.json` / `.html` | onchain | live target report |

**Exit code:** `0` if every evaluated control passed, `1` if any failed. **Skipped** controls
(e.g. the on-chain target offline) do **not** fail the run. This makes the CLI a CI gate.

## 8. Reading the HTML report

Open `reports/assurance.html` in a browser. Top to bottom:

- **KPIs** — Controls, Passing, Failing, Skipped, **Posture / 100**.
- **Risk posture** banner — the letter rating (A strong … F critical exposure), severity-weighted.
- **Drift** banner — green ("no drift") or red (lists regressed control ids), when a baseline was given.
- **Posture trend** — a sparkline of the posture score across the last runs (from `history.jsonl`).
- **Control status grid** — one card per control: id, PASS/FAIL/SKIP badge, a **severity chip**
  (critical=red, high=amber, medium=blue), stage, MITRE technique, CSF function, and the
  expected vs observed outcome. Green left-border = pass, red = fail, gray = skip.
- **Coverage** — pass rate per NIST CSF function and per MITRE ATT&CK technique.

The posture score is a **weighted** pass rate: critical controls are worth 10, high 5, medium
2, low 1. So failing one *critical* control hurts the score far more than failing a *medium*
one — which is exactly how you'd triage in practice.

## 9. The drift demo

The headline capability: prove the harness **catches a control that regressed**.

```bash
./scripts/demo.sh
```

It walks through: (1) a clean baseline (16/16, posture 100), (2) loosening the policy
(`policies/loosened_policy.yaml` raises the amount ceiling and removes the velocity rule),
(3) re-running with `--baseline` so the harness reports **drift** in red and the **posture
drops to 57/100 [D]**, exiting non-zero, then (4) restoring the clean policy.

Do it manually:

```bash
uv run python scripts/run_assurance.py --target mock          # baseline
cp reports/assurance.json reports/baseline.json
uv run python scripts/run_assurance.py \
    --policy policies/loosened_policy.yaml \
    --baseline reports/baseline.json                          # drift + exit 1
uv run python scripts/run_assurance.py --target mock          # restore
```

The same regression-detection is asserted as a unit test ("negative control") in
`tests/python/test_assurance_runner.py`, so the harness's ability to fail is itself tested.

## 10. The live on-chain target

The same harness, pointed read-only at the **real deployed** `nexus-protocol` compliance/
governance contracts on **Base Sepolia** (a public testnet). It never sends a transaction and
holds no key — it only issues `eth_call`s.

```bash
uv sync --extra onchain                                       # installs web3
export CAL_ONCHAIN_RPC_URL=https://base-sepolia-rpc.publicnode.com
uv run python scripts/run_assurance.py --target onchain       # or --target both
```

The 5 on-chain controls (OC-01…OC-05) check reachability, the **denylist/KYC wiring is
intact** (OC-02/OC-03 — catches a silently disconnected compliance control, i.e. drift on
production state), the denylist surface is functional, and the mint-ceiling control is present.

**Graceful degradation:** if web3 isn't installed or the RPC is unreachable, the on-chain
controls report **SKIPPED** (never FAILED), so offline runs and CI stay green. Contract
addresses + minimal ABIs are vendored (public testnet data, no secrets) in
`data/onchain/nexus_sepolia.json`.

## 11. The API

`make serve` starts FastAPI + the console at `http://127.0.0.1:8000/` (configurable via
`CAL_HOST` / `CAL_PORT`). All endpoints are also covered by `TestClient` tests, so no live
server is needed for testing.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Serves the security console |
| GET | `/healthz` | Liveness |
| POST | `/transactions` | Submit a transaction through the pipeline |
| GET | `/policy` | Current (sanitized) TAP rules |
| POST | `/policy/change` | Change the policy (403 + message if under admin quorum) |
| POST | `/assurance/run` | Run the BAS suite, return the report JSON |
| GET | `/assurance/report` | Last report (404 before first run) |
| GET | `/assurance/history` | Run history (for trends) |
| GET | `/metrics` | Prometheus metrics (text exposition format) |
| POST | `/admin/reset` | Rebuild the in-memory platform (demo "restore" / test isolation) |

**Submit a transaction:**

```bash
curl -s -X POST http://127.0.0.1:8000/transactions \
  -H 'Content-Type: application/json' \
  -d '{"initiator":"dave","source_vault":"1",
       "destination":"0xSANCTIONED00000000000000000000000000000001",
       "destination_type":"WHITELISTED","asset":"USDC","amount_usd":"5000","tx_type":"TRANSFER"}'
# -> {"decision":"BLOCK","stage":"screening","alerts":["SCREENING ALERT: sanctioned destination (OFAC_SANCTION) ..."], ...}
```

`amount_usd` is sent as a **string** to preserve exact `Decimal` value. `approver_ids` is an
optional array. A transaction over $100,000 returns `REQUIRE_APPROVAL` unless two valid
approvers are supplied.

**Attempt a policy change (quorum gate):**

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8000/policy/change \
  -H 'Content-Type: application/json' \
  -d '{"new_rules":[{"name":"allow_all","action":"ALLOW"}],"approver_ids":["alice"]}'
# -> 403  (one admin is below the quorum of 2; supply ["alice","bob"] for 200)
```

## 12. The security console (UI)

Served at `/`. Dark "security operations" theme with three panels:

- **Submit transaction** — fill the fields (or use a **preset**: `clean transfer`,
  `sanctioned dest`, `over-limit`, `large one-time`) and submit. The result shows the
  decision color-coded (green ALLOW / red BLOCK / amber REQUIRE_APPROVAL), the terminal
  stage, and any alerts.
- **Policy change · admin-quorum gate** — list approving admins and attempt a loosening
  change; one admin is denied (403, message shown), two distinct admins succeed.
- **Control assurance** — "Run assurance" renders the 16-control grid, CSF + ATT&CK coverage,
  and the posture score.

Every interactive element carries a stable `data-testid`, which is what the Playwright Page
Object Model drives (no selectors live in the spec files).

## 13. Observability: metrics, history, trend

- **Prometheus** — `GET /metrics` returns text-format gauges:
  `cal_controls_total`, `cal_controls_passing`, `cal_controls_failing`,
  `cal_controls_skipped`, `cal_posture_score`, and per-control
  `cal_control_pass{control="C-07",severity="critical"}`. Point a Prometheus scrape at it.
- **Run history** — every `make assure` appends a compact JSON line to
  `reports/history.jsonl` (`generated_at`, totals, posture, drift). `GET /assurance/history`
  serves it.
- **Trend** — the HTML report renders a posture sparkline from the history once there are ≥2
  runs.

## 14. Interop exports: Navigator, SARIF, JUnit

`make assure` writes three CI-native artifacts alongside the report:

- **`navigator-layer.json`** — a MITRE ATT&CK Navigator layer. Load it at
  <https://mitre-attack.github.io/attack-navigator/> to visualize which techniques are
  covered (green) vs failing (red).
- **`assurance.sarif`** — SARIF 2.1.0. A clean run has rules but **zero results**; failing
  controls become results with a `security-severity` derived from the control's severity. CI
  uploads it to the GitHub **code-scanning / Security** tab.
- **`assurance-junit.xml`** — JUnit. Failing/skipped controls render in any CI test UI.

## 15. Testing

```bash
make test                       # uv run pytest -n auto   (84 tests, 1 opt-in skipped)
uv run pytest -m unit           # only pure single-control tests
uv run pytest -m integration    # pipeline + API tests
uv run pytest -m assurance      # the BAS harness + exports
uv run pytest -m onchain        # opt-in live on-chain (needs CAL_ONCHAIN_RPC_URL + web3)
make e2e                        # Playwright E2E (self-starting; boots the API)
```

Markers are declared in `pytest.ini`. The on-chain live test is skipped unless
`CAL_ONCHAIN_RPC_URL` is set. The E2E suite runs serially and resets the in-memory platform
(`POST /admin/reset`) before each test so specs don't leak state.

## 16. CI/CD & GitHub Pages

`.github/workflows/ci.yml` has three jobs:

- **python** — ruff + black + `pytest -n auto` + `run_assurance.py`; uploads the SARIF to the
  Security tab and the report/exports as artifacts.
- **e2e** — installs Playwright + runs the E2E suite.
- **pages** — publishes `reports/assurance.html` to **GitHub Pages**. It is gated
  `if: github.ref == 'refs/heads/main' && github.event_name == 'push'`, so it deploys **only
  on push to main (i.e. when a PR is merged)** — pull requests run the validation jobs but
  skip the deploy. A `concurrency: { group: pages }` guard serializes deploys.

Live report: <https://esoterics611.github.io/custody-control-assurance-lab/>

## 17. Docker

```bash
docker build -t cal .
docker run --rm -p 8000:8000 cal      # API + console at http://localhost:8000/
```

The image uses uv with the committed lockfile, installs no dev dependencies, and serves the
console. `CAL_HOST` defaults to `0.0.0.0` inside the container.

## 18. Extending the lab: add a control

Adding a new control is a five-step, test-driven change:

1. **Implement** the guarantee in `src/cal/custody/` (a new policy rule, a screening check, a
   pipeline stage, …). Keep money `Decimal` and logic clock-free.
2. **Register** it in `src/cal/assurance/controls.py` — add a `Control(...)` to
   `CONTROL_REGISTRY` with its stage, MITRE techniques, CSF functions, simulation name, and
   `Severity`.
3. **Simulate** the attack in `src/cal/assurance/simulations.py` — a function returning a
   `SimResult` where `passed` means the control held; register it in `SIMULATIONS`.
4. **Test** it — a focused unit/integration test, and update any count assertions (the
   suite asserts `len(CONTROL_REGISTRY)`).
5. **Document** it in `atlas/CONTROL_CATALOG.md`.

Golden rule (from `CLAUDE.md`): **never weaken a control to make a simulation pass.** If a sim
fails, either the control is wrong or the sim is wrong — fix the right one.

An on-chain control is the same shape: add to `ONCHAIN_CONTROL_REGISTRY`, a read-only sim in
`src/cal/onchain/simulations.py` using `ctx.call(contract, fn, *args)`, and (if needed) the
function's ABI to `data/onchain/nexus_sepolia.json`.

## 19. Project layout

```
custody-control-assurance-lab/
├── CLAUDE.md                       persistent project rules
├── README.md                       overview
├── Dockerfile / .dockerignore      container image
├── Makefile                        install / test / lint / assure / serve / e2e
├── pyproject.toml / uv.lock        deps + tool config (+ [onchain] extra)
├── pytest.ini                      markers + pythonpath=src
├── .github/workflows/ci.yml        python + e2e + pages jobs
├── policies/
│   ├── default_policy.yaml         the reference TAP policy
│   └── loosened_policy.yaml        deliberately weakened (drift demo)
├── data/
│   ├── sanctions.sample.json       SYNTHETIC intel
│   └── onchain/nexus_sepolia.json  PUBLIC testnet addresses + ABIs
├── src/cal/
│   ├── models.py · clock.py
│   ├── custody/                    SYSTEM UNDER TEST
│   ├── assurance/                  controls · simulations · runner · report · exports · history
│   ├── onchain/                    live target (client · controls · simulations · runner)
│   └── api/                        app · serve · metrics
├── console/index.html              security console (E2E target)
├── scripts/run_assurance.py        the BAS CLI · scripts/demo.sh
├── tests/python/                   pytest
├── tests/e2e/                      Playwright (Page Object Model)
├── atlas/                          CONTROL_CATALOG.md · THREAT_MODEL.md
├── ai/prompts/                     the build prompts
└── docs/                           this manual + screenshots
```

## 20. Reference data: accounts, policy, addresses

**Synthetic accounts** (`src/cal/custody/accounts.py`):

| User | Roles | Notes |
|------|-------|-------|
| alice, bob | INITIATOR, APPROVER, ADMIN | treasury admins |
| carol | APPROVER, ADMIN | treasury admin |
| dave | INITIATOR | operator who can submit |
| erin | INITIATOR, APPROVER | senior operator |
| frank | (none) | used to demonstrate RBAC denial |

Admin quorum for policy changes is **2 distinct admins**.

**Default policy** (`policies/default_policy.yaml`, top-down, first match wins):

1. BLOCK transfers to `UNMANAGED_CONTRACT`
2. REQUIRE_APPROVAL (2 admins) for `CONTRACT_CALL`/`APPROVE` to `UNMANAGED_CONTRACT`
3. REQUIRE_APPROVAL (2 admins) when `amount_usd >= 100000`
4. REQUIRE_APPROVAL (1 admin) for `ONE_TIME` destinations `>= 10000`
5. REQUIRE_APPROVAL (2 admins) when vault `0` exceeds `250000` in `3600s` (velocity)
6. ALLOW transfers to `WHITELISTED` / `INTERNAL_VAULT`
7. anything else → default-deny BLOCK

**Screening** (`data/sanctions.sample.json`): sanctioned categories
(`OFAC_SANCTION`, `SANCTIONS`, `TERROR_FINANCING`) are an unconditional block; risk score
`>= 75` blocks; Travel Rule flags `ONE_TIME`/`UNMANAGED_CONTRACT` `>= 1000`. Useful synthetic
addresses:

| Address | Behavior |
|---------|----------|
| `0xSANCTIONED…01` | sanctioned (OFAC) → blocked |
| `0xMIXER…02` | score 90 → blocked on score |
| `0xWATCH74…06` / `0xWATCH75…05` | score boundary (74 passes, 75 blocks) |
| `0xCLEAN…99` | clean (used for ALLOW paths) |

## 21. Troubleshooting & FAQ

**`uv: command not found`** — install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

**On-chain controls show SKIPPED** — expected unless `uv sync --extra onchain` was run **and**
`CAL_ONCHAIN_RPC_URL` is reachable. SKIPPED never fails the run.

**`make assure` exits non-zero** — a control failed (or you ran `--policy loosened_policy.yaml`,
which is meant to fail). Open `reports/assurance.html` to see which.

**E2E fails to start** — it boots the API via uv on port 8071; ensure `make install` ran and
nothing else holds that port.

**Pages didn't update after my PR** — Pages deploys on **merge to main**, not on the PR. Check
the `pages` job in the post-merge CI run.

**Can I point the on-chain target elsewhere?** — yes: `--rpc-url` or `CAL_ONCHAIN_RPC_URL`, and
edit `data/onchain/nexus_sepolia.json` for different (public) addresses.

## 22. The 3-minute interview demo

> "I treated the custody governance like a system under test. This stands up a small honest
> model of the controls — TAP policy engine, screening, four-eyes, admin quorum, replay
> protection — and continuously *attacks* them to prove they hold."

1. **Console** (`make serve`): submit a clean transfer → ALLOW. Use the *sanctioned* preset →
   red BLOCK at screening with an alert. Use *over-limit* → REQUIRE_APPROVAL. Try a
   single-admin policy change → 403 quorum-denied.
2. **Run assurance** in the console → the 16-control grid goes green, with posture 100/100 and
   MITRE/CSF coverage.
3. **Drift** (`./scripts/demo.sh`): loosen one limit, re-run → the harness flags the regressed
   controls in **red**, posture drops to **57/100 [D]**, CI would fail. Restore → green.
4. **Live on-chain** (`--target onchain`): the *same* harness validates the real deployed
   protocol on Base Sepolia, including that the denylist/KYC wiring is still intact.

Lead with the **drift detection** — proving a control is *ineffective* is the whole point.
