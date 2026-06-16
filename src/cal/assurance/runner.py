"""Orchestrates the simulations, joins them to the registry, computes coverage + drift."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from cal.assurance.controls import CONTROL_REGISTRY, Control
from cal.assurance.simulations import SIMULATIONS, SimResult
from cal.clock import Clock, system_clock
from cal.custody.platform import CustodyPlatform
from cal.custody.reference import build_reference_platform


@dataclass
class ControlOutcome:
    control: Control
    result: SimResult

    @property
    def passed(self) -> bool:
        return self.result.passed

    @property
    def skipped(self) -> bool:
        return self.result.skipped

    @property
    def state(self) -> str:
        if self.skipped:
            return "skip"
        return "pass" if self.passed else "fail"

    def to_dict(self) -> dict:
        return {
            "id": self.control.id,
            "objective": self.control.objective,
            "stage": self.control.stage,
            "mitre_techniques": list(self.control.mitre_techniques),
            "csf_functions": list(self.control.csf_functions),
            "simulation": self.control.simulation,
            "severity": self.control.severity.value,
            "weight": self.control.weight,
            "passed": self.result.passed,
            "skipped": self.result.skipped,
            "state": self.state,
            "expected": self.result.expected,
            "observed": self.result.observed,
            "detail": self.result.detail,
        }


@dataclass
class AssuranceReport:
    generated_at: float
    outcomes: list[ControlOutcome]
    csf_coverage: dict[str, dict[str, int]] = field(default_factory=dict)
    mitre_coverage: dict[str, dict[str, int]] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    drift: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def passed(self) -> int:
        return sum(1 for o in self.outcomes if o.passed and not o.skipped)

    @property
    def skipped(self) -> int:
        return sum(1 for o in self.outcomes if o.skipped)

    @property
    def failed(self) -> int:
        return self.total - self.passed - self.skipped

    @property
    def all_passed(self) -> bool:
        # Skipped controls do not count as failures (e.g. on-chain target offline).
        return self.failed == 0

    @property
    def posture_score(self) -> int:
        """Severity-weighted pass rate over evaluated (non-skipped) controls, 0-100."""
        evaluated = [o for o in self.outcomes if not o.skipped]
        total_weight = sum(o.control.weight for o in evaluated)
        if not total_weight:
            return 0
        earned = sum(o.control.weight for o in evaluated if o.passed)
        return round(100 * earned / total_weight)

    @property
    def risk_rating(self) -> str:
        score = self.posture_score
        if score == 100:
            return "A — strong"
        if score >= 90:
            return "B — adequate"
        if score >= 75:
            return "C — needs attention"
        if score >= 50:
            return "D — at risk"
        return "F — critical exposure"

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "all_passed": self.all_passed,
                "posture_score": self.posture_score,
                "risk_rating": self.risk_rating,
            },
            "outcomes": [o.to_dict() for o in self.outcomes],
            "csf_coverage": self.csf_coverage,
            "mitre_coverage": self.mitre_coverage,
            "failures": self.failures,
            "drift": self.drift,
        }


def _coverage(outcomes: list[ControlOutcome], key: Callable[[Control], tuple[str, ...]]):
    coverage: dict[str, dict[str, int]] = {}
    for outcome in outcomes:
        if outcome.skipped:
            continue
        for tag in key(outcome.control):
            bucket = coverage.setdefault(tag, {"total": 0, "passed": 0})
            bucket["total"] += 1
            if outcome.passed:
                bucket["passed"] += 1
    return dict(sorted(coverage.items()))


def aggregate(
    outcomes: list[ControlOutcome],
    *,
    baseline: Mapping[str, bool] | None = None,
    clock: Clock = system_clock,
) -> AssuranceReport:
    """Build an AssuranceReport from outcomes (shared by mock + on-chain runners)."""
    failures = [o.control.id for o in outcomes if not o.passed and not o.skipped]

    drift: list[str] = []
    if baseline is not None:
        for outcome in outcomes:
            was_passing = baseline.get(outcome.control.id, False)
            if was_passing and not outcome.passed and not outcome.skipped:
                drift.append(outcome.control.id)

    return AssuranceReport(
        generated_at=clock(),
        outcomes=outcomes,
        csf_coverage=_coverage(outcomes, lambda c: c.csf_functions),
        mitre_coverage=_coverage(outcomes, lambda c: c.mitre_techniques),
        failures=failures,
        drift=drift,
    )


def run_all(
    platform_factory: Callable[[], CustodyPlatform] = build_reference_platform,
    *,
    baseline: Mapping[str, bool] | None = None,
    clock: Clock = system_clock,
) -> AssuranceReport:
    """Run every registered (mock) simulation against a fresh platform and aggregate."""
    outcomes = [
        ControlOutcome(control=control, result=SIMULATIONS[control.simulation](platform_factory()))
        for control in CONTROL_REGISTRY
    ]
    return aggregate(outcomes, baseline=baseline, clock=clock)


def baseline_from_report(report: AssuranceReport) -> dict[str, bool]:
    """Build a drift baseline (control_id -> passed) from a prior report."""
    return {o.control.id: o.passed for o in report.outcomes}
