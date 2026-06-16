# Phase 4 — Assurance framework (BAS runner + ATT&CK/CSF report)  [CENTERPIECE]

controls.py: Control{id, objective, stage, mitre_techniques, csf_functions, simulation};
CONTROL_REGISTRY C-01..C-12 exactly matching the catalog.
simulations.py: one function per sim; each performs the attacker action against a fresh
reference platform and returns SimResult{control_id, passed, expected, observed, detail}.
"passed" means THE CONTROL HELD, never that the attack succeeded. build_reference_platform().
runner.py: run_all() -> AssuranceReport (totals, pass/fail, coverage by CSF + by MITRE,
failures, DRIFT vs an optional baseline).
report.py: write_json + write_html (standalone dark security-console HTML, amber accent,
control grid green/red, coverage, drift). scripts/run_assurance.py CLI (writes reports,
prints table, exit non-zero on any fail).
Tests: all 12 pass against reference; a NEGATIVE CONTROL deliberately loosens a rule and
asserts the relevant sim now FAILS and run_all reports the regression + drift.

Acceptance: make assure writes json+html, prints 12-row table; negative control catches a
loosened control. Make the report look sharp.
