# Phase 7 — CI, docs, atlas, demo polish

ci.yml: job 1 (Python 3.12 + uv) ruff + black --check + pytest -n auto + run_assurance.py,
upload reports/assurance.html artifact; job 2 (Node + Playwright) runs e2e. README badge.
README showcase: scope note, pipeline diagram, control catalog, quickstart, how the assurance
report works (+ screenshots), how this maps to security-assurance practice.
atlas/CONTROL_CATALOG.md (table + paragraph per control); atlas/THREAT_MODEL.md (per-stage
asset/threat/control/sim + MITRE + CSF maps). ai/prompts/ (these prompts).
scripts/demo.sh: baseline -> loosen policy -> re-run assurance, harness catches drift (red
cells) -> restore. Commit screenshots into docs/img and embed in README.

Acceptance: clean checkout make install/test/assure/e2e all pass; CI green; README complete.
