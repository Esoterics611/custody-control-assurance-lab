"""Control registry: each custody control mapped to MITRE ATT&CK + NIST CSF 2.0.

This is the single source of truth joined against simulation results to produce the
assurance report. It mirrors atlas/CONTROL_CATALOG.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Control:
    id: str
    objective: str
    stage: str
    mitre_techniques: tuple[str, ...]
    csf_functions: tuple[str, ...]
    simulation: str


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
    ),
    Control(
        "C-12",
        "Admin quorum required to change policy",
        "Governance",
        ("T1098",),
        ("GV.RR", "GV.PO"),
        "sim_quorum_bypass",
    ),
)


def control_by_id(control_id: str) -> Control:
    for control in CONTROL_REGISTRY:
        if control.id == control_id:
            return control
    raise KeyError(control_id)
