# Session kickoff prompt

We're working in custody-control-assurance-lab — a DEFENSIVE, synthetic-data
security-control-validation / Breach & Attack Simulation lab for a MOCK
institutional custody platform. Read CLAUDE.md and atlas/CONTROL_CATALOG.md first
for full context, then confirm the current state by running `uv run pytest -n
auto`. House rules: Decimal for money (never float), no time.sleep / no wall-clock
in logic (use clock.py), default-deny in the policy engine, Playwright Page Object
Model with no selectors in specs, and NEVER weaken a control to make a test or
simulation pass. Today's task: [DESCRIBE THE PHASE]. Propose a short plan, then
implement, then show me the test run.
