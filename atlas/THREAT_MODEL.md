# Threat Model

What this lab defends, per pipeline stage. The "system under test" is the custody
governance stack — a TAP policy engine, compliance screening, RBAC/SoD, and an
admin-quorum gate — modeled synthetically. The adversary's goal is **unauthorized value
egress** or **disabling a control**.

## Trust boundary

```
   initiator / API client            ┌──────────────────────── custody platform ─────────────────────────┐
        (untrusted intent)  ──submit──►  RBAC → screening → TAP policy → approval/quorum → mock signer
                                       └────────────────────────────────────────────────────────────────┘
                                                              ▲
                                  admin (privileged) ──change_policy── governance quorum gate
```

Everything left of `submit()` is untrusted intent. Each stage is a control that must hold
independently (defense in depth): a single stage being weak should not, by itself, allow
egress.

## Per-stage threats → controls → validating simulation

| Stage | Asset at risk | Threat | Control | Simulation |
|-------|---------------|--------|---------|------------|
| RBAC | vault funds | unprivileged / compromised account initiates a withdrawal | INITIATOR role required to submit | `sim_rbac_denied` (C-10) |
| Screening | reputational / legal | send to sanctioned or high-risk destination | OFAC-style denylist + risk-score block + Travel-Rule flag | `sim_sanctioned_dest` (C-07), `sim_high_risk_score` (C-08), `sim_travel_rule` (C-09) |
| Policy | vault funds | unmatched tx, exfil to non-allowlisted dest, over-limit, velocity drain, rule shadowing, type confusion | ordered default-deny TAP engine with amount + velocity + ordering guarantees | `sim_default_deny` (C-01), `sim_non_whitelisted_dest` (C-02), `sim_over_limit_approval` (C-03), `sim_velocity_drain` (C-04), `sim_rule_shadowing` (C-05), `sim_contract_call_bypass` (C-06) |
| Approval | vault funds | insider self-approves their own payout | four-eyes / segregation of duties | `sim_self_approval` (C-11) |
| Governance | the entire control set | single admin loosens the policy | admin-quorum gate on policy change | `sim_quorum_bypass` (C-12) |
| Signer | private keys | premature / unauthorized signing | only fully-ALLOWed transactions reach the (mock) signer | implicit in every `signed` assertion |

The governance stage is the highest-leverage target: compromising it would let an attacker
disable every downstream control at once. It therefore carries the strongest control
(distinct-admin quorum) and the demo's drift scenario shows the systemic blast radius when
a policy control is weakened.

## MITRE ATT&CK techniques covered

| Technique | Name (paraphrased) | Controls |
|-----------|--------------------|----------|
| T1078 | Valid Accounts (unauthorized principal) | C-10 |
| T1098 | Account Manipulation (privileged change) | C-12 |
| T1548 | Abuse Elevation / control bypass (self-approval) | C-11 |
| T1567 | Exfiltration to external destination | C-01, C-02 |
| T1657 | Financial Theft (limits, velocity, screening, type confusion) | C-03, C-04, C-05, C-06, C-07, C-08 |

## NIST CSF 2.0 functions covered

| Function | Meaning | Controls |
|----------|---------|----------|
| GV.OC | Governance — Organizational Context (regulatory) | C-09 |
| GV.PO | Governance — Policy | C-01, C-03, C-05, C-12 |
| GV.RR | Governance — Roles & Responsibilities | C-11, C-12 |
| PR.AA | Protect — Identity, Authentication, Access | C-01, C-02, C-10 |
| PR.PS | Protect — Platform Security | C-06 |
| DE.AE | Detect — Adverse Event Analysis | C-07, C-08 |
| DE.CM | Detect — Continuous Monitoring | C-04 |
| RS.MA | Respond — Incident Management (alerting) | C-07 |

Coverage by technique and by function is computed at runtime and rendered in the assurance
report. A control with no MITRE mapping (C-09, a purely regulatory obligation) contributes
to CSF coverage only.

## Out of scope

No real keys, sanctions feeds, exchange credentials, or networks. No attacks against any
real system. No private-key cryptography (the signer is mocked). This is a control-
validation lab, not an exploit toolkit.
