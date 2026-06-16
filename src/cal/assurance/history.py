"""Append-only run history for continuous control monitoring.

Each assurance run appends one compact JSON line to reports/history.jsonl. The HTML
report renders a posture trend from it, and the API exposes it at /assurance/history.
"""

from __future__ import annotations

import json
from pathlib import Path

from cal.assurance.runner import AssuranceReport

DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[3] / "reports" / "history.jsonl"


def record(report: AssuranceReport) -> dict:
    return {
        "generated_at": report.generated_at,
        "total": report.total,
        "passed": report.passed,
        "failed": report.failed,
        "skipped": report.skipped,
        "posture_score": report.posture_score,
        "risk_rating": report.risk_rating,
        "drift": list(report.drift),
    }


def append_history(report: AssuranceReport, path: Path | str = DEFAULT_HISTORY_PATH) -> dict:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = record(report)
    with path.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def load_history(
    path: Path | str = DEFAULT_HISTORY_PATH, *, limit: int | None = None
) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    entries = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return entries[-limit:] if limit else entries
