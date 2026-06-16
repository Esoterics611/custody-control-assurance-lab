#!/usr/bin/env python3
"""CLI: run the Breach & Attack Simulation suite and write the assurance report.

Usage:
    uv run python scripts/run_assurance.py [--target mock|onchain|both]
                                           [--policy policies/loosened_policy.yaml]
                                           [--baseline reports/baseline.json]
                                           [--rpc-url URL]

Writes reports/assurance.json + reports/assurance.html (and *-onchain.* for the
on-chain target), prints a pass/fail table, and exits non-zero if ANY control
fails — SKIPPED controls (e.g. on-chain target offline) do not fail the run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make `cal` importable when run as a plain script (mirrors pythonpath=src).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cal.assurance.exports import (  # noqa: E402
    write_junit,
    write_navigator_layer,
    write_sarif,
)
from cal.assurance.report import write_html, write_json  # noqa: E402
from cal.assurance.runner import AssuranceReport, run_all  # noqa: E402
from cal.custody.reference import build_reference_platform  # noqa: E402
from cal.onchain.runner import run_onchain  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def _load_baseline(path: Path | None) -> dict[str, bool] | None:
    if not path or not path.exists():
        return None
    data = json.loads(path.read_text())
    if "outcomes" in data:
        return {o["id"]: o["passed"] for o in data["outcomes"]}
    return {k: bool(v) for k, v in data.items()}


def _print_table(title: str, report: AssuranceReport) -> None:
    print(f"\n  {title}")
    print("  " + "-" * 70)
    for outcome in report.outcomes:
        mark = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}[outcome.state]
        sym = {"pass": "✓", "fail": "✗", "skip": "–"}[outcome.state]
        print(
            f"  {sym} {outcome.control.id}  [{mark}]  {outcome.control.objective[:44]:<44}"
            f"  {outcome.result.observed}"
        )
    print("  " + "-" * 70)
    line = f"  {report.passed}/{report.total} passing | failing: {report.failed}"
    if report.skipped:
        line += f" | skipped: {report.skipped}"
    print(line)
    print(f"  posture score: {report.posture_score}/100  [{report.risk_rating}]")
    if report.drift:
        print(f"  ⚠ DRIFT — regressed controls: {', '.join(report.drift)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run custody control assurance (BAS).")
    parser.add_argument("--target", choices=["mock", "onchain", "both"], default="mock")
    parser.add_argument("--baseline", type=Path, default=None, help="prior report for drift")
    parser.add_argument(
        "--policy", type=Path, default=None, help="alternate TAP policy file (drift demo)"
    )
    parser.add_argument("--rpc-url", default=None, help="on-chain RPC (or CAL_ONCHAIN_RPC_URL)")
    args = parser.parse_args()
    baseline = _load_baseline(args.baseline)

    failed = False

    if args.target in ("mock", "both"):
        if args.policy:

            def factory():
                return build_reference_platform(policy_path=args.policy)

        else:
            factory = build_reference_platform
        report = run_all(factory, baseline=baseline)
        write_json(report, REPORTS_DIR / "assurance.json")
        write_html(report, REPORTS_DIR / "assurance.html")
        write_navigator_layer(report, REPORTS_DIR / "navigator-layer.json")
        write_sarif(report, REPORTS_DIR / "assurance.sarif")
        write_junit(report, REPORTS_DIR / "assurance-junit.xml")
        _print_table("MOCK TARGET — custody platform controls", report)
        failed = failed or not report.all_passed

    if args.target in ("onchain", "both"):
        report = run_onchain(rpc_url=args.rpc_url, baseline=baseline)
        write_json(report, REPORTS_DIR / "assurance-onchain.json")
        write_html(report, REPORTS_DIR / "assurance-onchain.html")
        _print_table("ON-CHAIN TARGET — nexus-protocol (Base Sepolia, read-only)", report)
        failed = failed or not report.all_passed

    print(f"\n  reports written to {REPORTS_DIR}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
