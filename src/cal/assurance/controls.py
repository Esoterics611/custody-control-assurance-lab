"""Control registry: each custody control mapped to MITRE ATT&CK + NIST CSF 2.0.

This is the single source of truth joined against simulation results to produce the
assurance report. It mirrors atlas/CONTROL_CATALOG.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Weight each control by severity for the posture score (a weighted pass rate).
SEVERITY_WEIGHT: dict[Severity, int] = {
    Severity.CRITICAL: 10,
    Severity.HIGH: 5,
    Severity.MEDIUM: 2,
    Severity.LOW: 1,
}


@dataclass(frozen=True)
class Control:
    id: str
    objective: str
    stage: str
    mitre_techniques: tuple[str, ...]
    csf_functions: tuple[str, ...]
    simulation: str
    severity: Severity = Severity.HIGH

    @property
    def weight(self) -> int:
        return SEVERITY_WEIGHT[self.severity]


CONTROL_REGISTRY: tuple[Control, ...] = (
    Control(
        "C-01",
        "Default-deny: unmatched transaction is blocked",
        "Policy",
        ("T1567",),
        ("PR.AA", "GV.PO"),
        "sim_default_deny",
    ),
    Control(
        "C-02",
        "Destination allowlist enforced (non-whitelisted blocked)",
        "Policy",
        ("T1567",),
        ("PR.AA",),
        "sim_non_whitelisted_dest",
    ),
    Control(
        "C-03",
        "Amount limit triggers approval above threshold (boundary-correct)",
        "Policy",
        ("T1657",),
        ("GV.PO",),
        "sim_over_limit_approval",
    ),
    Control(
        "C-04",
        "Velocity cap on rolling window",
        "Policy",
        ("T1657",),
        ("DE.CM",),
        "sim_velocity_drain",
    ),
    Control(
        "C-05",
        "Rule-ordering / shadowing: intended rule wins",
        "Policy",
        ("T1657",),
        ("GV.PO",),
        "sim_rule_shadowing",
        Severity.MEDIUM,
    ),
    Control(
        "C-06",
        "Type-confusion bypass blocked (CONTRACT_CALL/APPROVE governed)",
        "Policy",
        ("T1657",),
        ("PR.PS",),
        "sim_contract_call_bypass",
    ),
    Control(
        "C-07",
        "Sanctioned destination blocked + alert",
        "Screening",
        ("T1657",),
        ("DE.AE", "RS.MA"),
        "sim_sanctioned_dest",
        Severity.CRITICAL,
    ),
    Control(
        "C-08",
        "High-risk score blocked (boundary-correct)",
        "Screening",
        ("T1657",),
        ("DE.AE",),
        "sim_high_risk_score",
    ),
    Control(
        "C-09",
        "Travel Rule flagged above threshold for one-time destination",
        "Screening",
        (),
        ("GV.OC",),
        "sim_travel_rule",
        Severity.MEDIUM,
    ),
    Control(
        "C-10",
        "RBAC: non-initiator role cannot submit",
        "Access",
        ("T1078",),
        ("PR.AA",),
        "sim_rbac_denied",
    ),
    Control(
        "C-11",
        "Four-eyes / SoD: initiator cannot self-approve",
        "Approval",
        ("T1548",),
        ("GV.RR",),
        "sim_self_approval",
        Severity.CRITICAL,
    ),
    Control(
        "C-12",
        "Admin quorum required to change policy",
        "Governance",
        ("T1098",),
        ("GV.RR", "GV.PO"),
        "sim_quorum_bypass",
        Severity.CRITICAL,
    ),
    Control(
        "C-13",
        "Replay/idempotency: an executed request cannot be replayed",
        "Pipeline",
        ("T1565",),
        ("PR.DS",),
        "sim_replay_protection",
        Severity.CRITICAL,
    ),
    Control(
        "C-14",
        "Decimal-precision integrity: sub-cent amounts handled exactly (no float)",
        "Policy",
        (),
        ("PR.DS",),
        "sim_decimal_precision",
        Severity.MEDIUM,
    ),
    Control(
        "C-15",
        "Address-normalization: case-varied sanctioned address still blocked",
        "Screening",
        ("T1657",),
        ("DE.AE",),
        "sim_address_normalization_bypass",
    ),
    Control(
        "C-16",
        "Approver-set integrity: duplicate approvers cannot inflate the count",
        "Approval",
        ("T1548",),
        ("GV.RR",),
        "sim_approver_set_integrity",
    ),
)


def control_by_id(control_id: str) -> Control:
    for control in CONTROL_REGISTRY:
        if control.id == control_id:
            return control
    raise KeyError(control_id)
