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

    def to_dict(self) -> dict:
        return {
            "id": self.control.id,
            "objective": self.control.objective,
            "stage": self.control.stage,
            "mitre_techniques": list(self.control.mitre_techniques),
            "csf_functions": list(self.control.csf_functions),
            "simulation": self.control.simulation,
            "passed": self.result.passed,
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
        return sum(1 for o in self.outcomes if o.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def all_passed(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "all_passed": self.all_passed,
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
        for tag in key(outcome.control):
            bucket = coverage.setdefault(tag, {"total": 0, "passed": 0})
            bucket["total"] += 1
            if outcome.passed:
                bucket["passed"] += 1
    return dict(sorted(coverage.items()))


def run_all(
    platform_factory: Callable[[], CustodyPlatform] = build_reference_platform,
    *,
    baseline: Mapping[str, bool] | None = None,
    clock: Clock = system_clock,
) -> AssuranceReport:
    """Run every registered simulation against a fresh platform and aggregate."""
    outcomes: list[ControlOutcome] = []
    for control in CONTROL_REGISTRY:
        simulation = SIMULATIONS[control.simulation]
        result = simulation(platform_factory())
        outcomes.append(ControlOutcome(control=control, result=result))

    failures = [o.control.id for o in outcomes if not o.passed]

    drift: list[str] = []
    if baseline is not None:
        for outcome in outcomes:
            was_passing = baseline.get(outcome.control.id, False)
            if was_passing and not outcome.passed:
                drift.append(outcome.control.id)

    return AssuranceReport(
        generated_at=clock(),
        outcomes=outcomes,
        csf_coverage=_coverage(outcomes, lambda c: c.csf_functions),
        mitre_coverage=_coverage(outcomes, lambda c: c.mitre_techniques),
        failures=failures,
        drift=drift,
    )


def baseline_from_report(report: AssuranceReport) -> dict[str, bool]:
    """Build a drift baseline (control_id -> passed) from a prior report."""
    return {o.control.id: o.passed for o in report.outcomes}
