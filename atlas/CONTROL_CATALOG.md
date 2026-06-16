# Control Catalog

The authoritative map of control objective → pipeline stage → MITRE ATT&CK → NIST CSF 2.0
→ validating simulation. This table is mirrored in `src/cal/assurance/controls.py`
(`CONTROL_REGISTRY`); the two must stay in sync.

| ID | Control objective | Stage | MITRE | NIST CSF 2.0 | Simulation |
|----|------------------|-------|-------|--------------|------------|
| C-01 | Default-deny: unmatched transaction is blocked | Policy | T1567 | PR.AA / GV.PO | `sim_default_deny` |
| C-02 | Destination allowlist enforced (non-whitelisted blocked) | Policy | T1567 | PR.AA | `sim_non_whitelisted_dest` |
| C-03 | Amount limit triggers approval above threshold (boundary-correct) | Policy | T1657 | GV.PO | `sim_over_limit_approval` |
| C-04 | Velocity cap on rolling window | Policy | T1657 | DE.CM | `sim_velocity_drain` |
| C-05 | Rule-ordering / shadowing: intended rule wins | Policy | T1657 | GV.PO | `sim_rule_shadowing` |
| C-06 | Type-confusion bypass blocked (CONTRACT_CALL/APPROVE governed) | Policy | T1657 | PR.PS | `sim_contract_call_bypass` |
| C-07 | Sanctioned destination blocked + alert | Screening | T1657 | DE.AE / RS.MA | `sim_sanctioned_dest` |
| C-08 | High-risk score blocked (boundary-correct) | Screening | T1657 | DE.AE | `sim_high_risk_score` |
| C-09 | Travel Rule flagged above threshold for one-time destination | Screening | — | GV.OC | `sim_travel_rule` |
| C-10 | RBAC: non-initiator role cannot submit | Access | T1078 | PR.AA | `sim_rbac_denied` |
| C-11 | Four-eyes / SoD: initiator cannot self-approve | Approval | T1548 | GV.RR | `sim_self_approval` |
| C-12 | Admin quorum required to change policy | Governance | T1098 | GV.RR / GV.PO | `sim_quorum_bypass` |

A simulation **passes** when the control behaved correctly (the attack was blocked,
escalated, denied, or flagged) — never when the attack succeeded. We never weaken a
control to make a simulation pass.

---

## C-01 — Default-deny
**Objective.** Anything not explicitly allowed by a matching rule is BLOCKED.
**Threat.** An attacker crafts a transaction that matches no rule (an un-modeled
`tx_type`, an exotic destination) hoping it falls through to "allow". 
**Validation.** `sim_default_deny` submits a `STAKE` to a one-time destination; the engine
matches no rule and returns `BLOCK @ policy`. This is the backstop behind every other
policy control.

## C-02 — Destination allowlist
**Objective.** Egress is only permitted to allowlisted / internal destinations; a fresh
external (one-time) destination below the escalation threshold is not silently allowed.
**Threat.** Exfiltration to an attacker-controlled address at a "normal" amount.
**Validation.** `sim_non_whitelisted_dest` sends a modest transfer to a one-time external
address; the baseline allow rule covers only WHITELISTED/INTERNAL, so it defaults to
`BLOCK @ policy`.

## C-03 — Amount limit → approval (boundary-correct)
**Objective.** Transfers at or above the threshold require dual approval.
**Threat.** A large single transfer auto-signing without human review.
**Validation.** `sim_over_limit_approval` submits a large transfer with no approvers and
asserts `REQUIRE_APPROVAL` (not signed). Unit tests pin the boundary: one cent under
allows, exactly at the limit escalates (`>=`).

## C-04 — Velocity cap (rolling window)
**Objective.** Cumulative egress from a vault within a rolling window cannot exceed the cap
without escalation.
**Threat.** Draining a vault via many sub-limit transfers to dodge the per-transaction
amount rule.
**Validation.** `sim_velocity_drain` sends several sub-limit transfers from one vault; the
transfer that pushes cumulative window spend over the cap returns `REQUIRE_APPROVAL` via
`velocity_cap_rolling_window`. The cap is evaluated on *cumulative* spend, not per-tx.

## C-05 — Rule ordering / shadowing
**Objective.** The intended (restrictive) rule wins; a broad allow cannot shadow it.
**Threat.** A mis-ordered policy where a permissive rule sits above a restrictive one, so a
large transfer is silently allowed.
**Validation.** `sim_rule_shadowing` submits a large whitelisted transfer and asserts it is
escalated by `large_amount_dual_approval` — proving the reference ordering places the
restrictive rule above the baseline allow. A unit test builds a deliberately mis-ordered
engine to demonstrate the bypass this guards against.

## C-06 — Type-confusion bypass
**Objective.** `CONTRACT_CALL` / `APPROVE` to an unmanaged contract are governed, not just
plain `TRANSFER`s.
**Threat.** Moving value via a contract interaction (e.g. an ERC-20 `approve` to a
malicious spender) to dodge transfer controls.
**Validation.** `sim_contract_call_bypass` submits a `CONTRACT_CALL` to an unmanaged
contract; the engine escalates it (`REQUIRE_APPROVAL`), never `ALLOW`.

## C-07 — Sanctioned destination
**Objective.** A sanctioned destination is blocked pre-signing and raises an alert.
**Threat.** Sending funds to an OFAC-sanctioned / terror-financing address.
**Validation.** `sim_sanctioned_dest` sends to a synthetic sanctioned address; screening
returns `BLOCK @ screening` with a `SCREENING ALERT`. Sanctioned categories are an
unconditional block regardless of numeric score.

## C-08 — High-risk score (boundary-correct)
**Objective.** A destination whose risk score meets the ceiling is blocked even without a
sanctions category.
**Threat.** Mixers / high-risk counterparties that are risky but not formally sanctioned.
**Validation.** `sim_high_risk_score` sends to a high-score address and asserts
`BLOCK @ screening`. Unit tests pin the boundary: score 74 passes, 75 blocks.

## C-09 — Travel Rule
**Objective.** A one-time/unmanaged destination at or above the threshold is flagged for
Travel-Rule data collection.
**Threat.** Regulatory non-compliance on cross-VASP transfers.
**Validation.** `sim_travel_rule` submits a large one-time transfer and asserts
`travel_rule_required` plus a Travel-Rule alert. This is a flag, not a block (defense in
depth: the policy may still escalate or deny).

## C-10 — RBAC submit
**Objective.** Only principals holding the INITIATOR role can submit.
**Threat.** A compromised or unprivileged account initiating withdrawals.
**Validation.** `sim_rbac_denied` submits as a roleless principal and asserts
`BLOCK @ rbac`.

## C-11 — Four-eyes / segregation of duties
**Objective.** An initiator cannot approve their own transaction; approvals must come from
distinct APPROVER principals.
**Threat.** A single insider both initiating and approving a payout.
**Validation.** `sim_self_approval` has the initiator list only themselves as approver;
self-approval is dropped, leaving the transaction `REQUIRE_APPROVAL` (pending).

## C-12 — Admin quorum on policy change
**Objective.** Changing the policy requires a quorum of distinct admins.
**Threat.** A single admin unilaterally loosening controls (the highest-leverage attack).
**Validation.** `sim_quorum_bypass` attempts a single-admin policy change; the governor
raises `QuorumError` and the simulation confirms the policy is unchanged afterwards.

---

# On-chain control catalog (live target)

The same control-validation discipline, pointed at a **real deployed** institutional
digital-asset protocol — `nexus-protocol` on **Base Sepolia** (public testnet). Strictly
READ-ONLY (`eth_call`): no transaction is ever sent, no key is held. When web3 isn't
installed or the RPC is unreachable, these report **SKIPPED** (never failed) so CI stays
green. Run with `uv run python scripts/run_assurance.py --target onchain`.

| ID | Control objective | Stage | MITRE | NIST CSF 2.0 | Simulation |
|----|------------------|-------|-------|--------------|------------|
| OC-01 | Custody contracts deployed & reachable (stablecoin decimals == 6) | Infra | — | ID.AM / GV.OC | `oc_reachability` |
| OC-02 | Restriction-list wiring intact (TransferRestrictions → expected RestrictionList) | Compliance | T1565 | PR.PS / DE.CM | `oc_restriction_wiring` |
| OC-03 | KYC-registry wiring intact (TransferRestrictions → expected KYCRegistry) | Compliance | T1565 | PR.AA / DE.CM | `oc_kyc_wiring` |
| OC-04 | Denylist surface functional (unknown not restricted, transfer-check live) | Screening | T1657 | DE.AE | `oc_denylist_functional` |
| OC-05 | Mint-ceiling control present (MintController.remainingAllocation callable) | Governance | T1657 | GV.PO | `oc_mint_ceiling` |

**OC-02 / OC-03 are genuine drift detection on production state:** if an operator repointed
`TransferRestrictions` away from the real `RestrictionList`/`KYCRegistry` (silently disabling
the denylist or KYC gate), these turn red — the on-chain analogue of the mock drift demo.
