#!/usr/bin/env python3
"""CLI: run the full Breach & Attack Simulation suite and write the assurance report.

Usage:
    uv run python scripts/run_assurance.py [--baseline reports/baseline.json]

Writes reports/assurance.json + reports/assurance.html, prints a pass/fail table,
and exits non-zero if ANY control fails (so it gates CI).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make `cal` importable when run as a plain script (mirrors pythonpath=src).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cal.assurance.report import write_html, write_json  # noqa: E402
from cal.assurance.runner import run_all  # noqa: E402
from cal.custody.reference import build_reference_platform  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def _load_baseline(path: Path | None) -> dict[str, bool] | None:
    if not path or not path.exists():
        return None
    data = json.loads(path.read_text())
    # Accept either a prior full report or a flat {control_id: passed} map.
    if "outcomes" in data:
        return {o["id"]: o["passed"] for o in data["outcomes"]}
    return {k: bool(v) for k, v in data.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run custody control assurance (BAS).")
    parser.add_argument("--baseline", type=Path, default=None, help="prior report for drift")
    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="alternate TAP policy file (used to demonstrate drift detection)",
    )
    args = parser.parse_args()

    if args.policy:

        def factory():
            return build_reference_platform(policy_path=args.policy)

    else:
        factory = build_reference_platform

    report = run_all(factory, baseline=_load_baseline(args.baseline))

    json_path = write_json(report, REPORTS_DIR / "assurance.json")
    html_path = write_html(report, REPORTS_DIR / "assurance.html")

    print("\n  CUSTODY CONTROL ASSURANCE — Breach & Attack Simulation")
    print("  " + "-" * 64)
    for outcome in report.outcomes:
        mark = "PASS" if outcome.passed else "FAIL"
        sym = "✓" if outcome.passed else "✗"
        print(
            f"  {sym} {outcome.control.id}  [{mark}]  {outcome.control.objective[:46]:<46}"
            f"  {outcome.result.observed}"
        )
    print("  " + "-" * 64)
    print(f"  {report.passed}/{report.total} controls passing | failing: {report.failed}")
    if report.drift:
        print(f"  ⚠ DRIFT — regressed controls: {', '.join(report.drift)}")
    print(f"  report: {json_path}  |  {html_path}\n")

    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
