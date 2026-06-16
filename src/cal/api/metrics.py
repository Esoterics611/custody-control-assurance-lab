"""Prometheus text-format metrics for the assurance report (no extra dependency)."""

from __future__ import annotations

from cal.assurance.runner import AssuranceReport

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def prometheus_metrics(report: AssuranceReport) -> str:
    lines: list[str] = []

    def gauge(name: str, help_text: str, value: float) -> None:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {value}")

    gauge("cal_controls_total", "Total controls evaluated", report.total)
    gauge("cal_controls_passing", "Controls passing", report.passed)
    gauge("cal_controls_failing", "Controls failing", report.failed)
    gauge("cal_controls_skipped", "Controls skipped", report.skipped)
    gauge("cal_posture_score", "Severity-weighted posture score (0-100)", report.posture_score)

    lines.append("# HELP cal_control_pass Per-control result (1 = control held, 0 = failed)")
    lines.append("# TYPE cal_control_pass gauge")
    for outcome in report.outcomes:
        labels = f'control="{outcome.control.id}",severity="{outcome.control.severity.value}"'
        lines.append(f"cal_control_pass{{{labels}}} {1 if outcome.passed else 0}")

    return "\n".join(lines) + "\n"
