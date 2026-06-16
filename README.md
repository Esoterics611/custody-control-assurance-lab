# custody-control-assurance-lab

A **synthetic, purely defensive** Breach & Attack Simulation (BAS) lab that models the
governance stack of an institutional digital-asset **custody** platform — a Transaction
Authorization Policy (TAP) engine, pre-signing compliance screening, RBAC with
segregation-of-duties, and an admin-quorum gate on policy changes — and then
**continuously attacks those controls to prove they hold**, reporting coverage mapped to
**MITRE ATT&CK** and **NIST CSF 2.0**. There are no real keys, no real sanctions feeds,
and no real exchange or API credentials anywhere in this repository; the "system under
test" is a small, honest model of the controls, and every simulation validates that a
control **blocks, escalates, or detects** an attacker action — it never attacks a real
system.

> Status: scaffolding. The control engine, assurance harness, API, console, and E2E
> suite are built out across the phased commits that follow.
