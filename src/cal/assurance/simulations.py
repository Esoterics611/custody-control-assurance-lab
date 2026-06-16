"""Breach & Attack Simulations (BAS) — one attacker scenario per control objective.

Each simulation performs an ATTACKER ACTION against a freshly-built reference
platform and returns a :class:`SimResult`. ``passed`` means THE CONTROL BEHAVED
CORRECTLY (the attack was blocked / escalated / denied / flagged) — never that the
attack succeeded. We NEVER weaken a control to make a simulation pass.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from cal.custody.platform import CustodyPlatform
from cal.custody.policy_engine import PolicyRule
from cal.custody.rbac import QuorumError
from cal.custody.reference import build_reference_platform
from cal.models import Decision, DestinationType, TransactionRequest, TransactionType

# Deterministic reference epoch — sims never read the wall clock.
T0 = 1_700_000_000.0

# Synthetic intel addresses (mirrors data/sanctions.sample.json).
ADDR_SANCTIONED = "0xSANCTIONED00000000000000000000000000000001"
ADDR_MIXER = "0xMIXER0000000000000000000000000000000000002"
ADDR_EXTERNAL = "0xEXTERNAL0000000000000000000000000000000777"


@dataclass
class SimResult:
    control_id: str
    passed: bool
    expected: str
    observed: str
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "control_id": self.control_id,
            "passed": self.passed,
            "expected": self.expected,
            "observed": self.observed,
            "detail": self.detail,
        }


def _tx(
    *,
    amount: str,
    initiator: str = "dave",
    source_vault: str = "1",
    destination: str = ADDR_EXTERNAL,
    destination_type: DestinationType = DestinationType.WHITELISTED,
    tx_type: TransactionType = TransactionType.TRANSFER,
    submitted_at: float = T0,
) -> TransactionRequest:
    return TransactionRequest(
        initiator=initiator,
        source_vault=source_vault,
        destination=destination,
        destination_type=destination_type,
        asset="USDC",
        amount_usd=Decimal(amount),
        submitted_at=submitted_at,
        tx_type=tx_type,
    )


def _observed(result) -> str:
    return f"{result.decision.value} @ {result.stage}"


# --- C-01 -------------------------------------------------------------------
def sim_default_deny(platform: CustodyPlatform) -> SimResult:
    # Attacker submits an unmodeled action (STAKE) hoping it slips through ungoverned.
    result = platform.submit(
        _tx(amount="500", tx_type=TransactionType.STAKE, destination_type=DestinationType.ONE_TIME)
    )
    passed = result.decision is Decision.BLOCK and result.stage == "policy"
    return SimResult(
        "C-01",
        passed,
        expected="BLOCK @ policy (default-deny)",
        observed=_observed(result),
        detail=result.reason,
    )


# --- C-02 -------------------------------------------------------------------
def sim_non_whitelisted_dest(platform: CustodyPlatform) -> SimResult:
    # Attacker exfiltrates to a fresh, non-allowlisted external address at a
    # "normal" amount below the escalation threshold.
    result = platform.submit(_tx(amount="1500", destination_type=DestinationType.ONE_TIME))
    passed = result.decision is Decision.BLOCK and result.stage == "policy"
    return SimResult(
        "C-02",
        passed,
        expected="BLOCK @ policy (allowlist enforced)",
        observed=_observed(result),
        detail=result.reason,
    )


# --- C-03 -------------------------------------------------------------------
def sim_over_limit_approval(platform: CustodyPlatform) -> SimResult:
    # Attacker pushes a large transfer with NO approvers, hoping it auto-signs.
    result = platform.submit(_tx(amount="250000"))
    passed = result.decision is Decision.REQUIRE_APPROVAL and not result.signed
    return SimResult(
        "C-03",
        passed,
        expected="REQUIRE_APPROVAL (not signed)",
        observed=_observed(result),
        detail=result.reason,
    )


# --- C-04 -------------------------------------------------------------------
def sim_velocity_drain(platform: CustodyPlatform) -> SimResult:
    # Attacker splits a drain into sub-limit transfers to dodge the amount rule.
    for i in range(2):
        platform.submit(_tx(amount="90000", source_vault="0", submitted_at=T0 + i * 600))
    breaching = platform.submit(_tx(amount="90000", source_vault="0", submitted_at=T0 + 1200))
    passed = (
        breaching.decision is Decision.REQUIRE_APPROVAL
        and breaching.policy is not None
        and breaching.policy.matched_rule == "velocity_cap_rolling_window"
    )
    return SimResult(
        "C-04",
        passed,
        expected="REQUIRE_APPROVAL via velocity cap on the breaching tx",
        observed=_observed(breaching),
        detail=breaching.reason,
    )


# --- C-05 -------------------------------------------------------------------
def sim_rule_shadowing(platform: CustodyPlatform) -> SimResult:
    # A large whitelisted transfer must be caught by the approval rule, NOT shadowed
    # by the broad baseline allow (which sits below it in the ordering).
    result = platform.submit(_tx(amount="150000", destination_type=DestinationType.WHITELISTED))
    matched = result.policy.matched_rule if result.policy else None
    passed = (
        result.decision is Decision.REQUIRE_APPROVAL and matched == "large_amount_dual_approval"
    )
    return SimResult(
        "C-05",
        passed,
        expected="REQUIRE_APPROVAL via 'large_amount_dual_approval' (not shadowed)",
        observed=f"{result.decision.value} via {matched}",
        detail="ordering honored: restrictive rule wins over baseline allow",
    )


# --- C-06 -------------------------------------------------------------------
def sim_contract_call_bypass(platform: CustodyPlatform) -> SimResult:
    # Type confusion: move value via CONTRACT_CALL to an unmanaged contract instead
    # of a TRANSFER, hoping only TRANSFERs are governed.
    result = platform.submit(
        _tx(
            amount="500",
            destination_type=DestinationType.UNMANAGED_CONTRACT,
            tx_type=TransactionType.CONTRACT_CALL,
        )
    )
    passed = result.decision is not Decision.ALLOW and not result.signed
    return SimResult(
        "C-06",
        passed,
        expected="governed (escalated/blocked, not signed)",
        observed=_observed(result),
        detail=result.reason,
    )


# --- C-07 -------------------------------------------------------------------
def sim_sanctioned_dest(platform: CustodyPlatform) -> SimResult:
    result = platform.submit(_tx(amount="5000", destination=ADDR_SANCTIONED))
    has_alert = any("SCREENING ALERT" in a for a in result.alerts)
    passed = result.decision is Decision.BLOCK and result.stage == "screening" and has_alert
    return SimResult(
        "C-07",
        passed,
        expected="BLOCK @ screening + alert",
        observed=_observed(result),
        detail="; ".join(result.alerts),
    )


# --- C-08 -------------------------------------------------------------------
def sim_high_risk_score(platform: CustodyPlatform) -> SimResult:
    # Non-sanctioned category, but risk score >= ceiling must still block.
    result = platform.submit(_tx(amount="5000", destination=ADDR_MIXER))
    passed = (
        result.decision is Decision.BLOCK
        and result.stage == "screening"
        and result.screening is not None
        and result.screening.score >= 75
    )
    return SimResult(
        "C-08",
        passed,
        expected="BLOCK @ screening (risk score >= ceiling)",
        observed=_observed(result),
        detail=result.reason,
    )


# --- C-09 -------------------------------------------------------------------
def sim_travel_rule(platform: CustodyPlatform) -> SimResult:
    # A large one-time transfer must raise the Travel-Rule data-collection flag.
    result = platform.submit(_tx(amount="15000", destination_type=DestinationType.ONE_TIME))
    flagged = result.screening is not None and result.screening.travel_rule_required
    has_alert = any("Travel Rule" in a for a in result.alerts)
    passed = bool(flagged and has_alert)
    return SimResult(
        "C-09",
        passed,
        expected="travel_rule_required flag + alert raised",
        observed=f"travel_rule_required={flagged}",
        detail="; ".join(result.alerts),
    )


# --- C-10 -------------------------------------------------------------------
def sim_rbac_denied(platform: CustodyPlatform) -> SimResult:
    # 'frank' holds no INITIATOR role.
    result = platform.submit(_tx(amount="5000", initiator="frank"))
    passed = result.decision is Decision.BLOCK and result.stage == "rbac"
    return SimResult(
        "C-10",
        passed,
        expected="BLOCK @ rbac",
        observed=_observed(result),
        detail=result.reason,
    )


# --- C-11 -------------------------------------------------------------------
def sim_self_approval(platform: CustodyPlatform) -> SimResult:
    # 'alice' initiates a large transfer and lists ONLY herself as approver.
    result = platform.submit(
        _tx(amount="150000", initiator="alice"), approver_ids=["alice", "alice"]
    )
    passed = (
        result.decision is Decision.REQUIRE_APPROVAL
        and result.stage == "approval"
        and not result.signed
    )
    return SimResult(
        "C-11",
        passed,
        expected="REQUIRE_APPROVAL (self-approval rejected, still pending)",
        observed=_observed(result),
        detail=result.reason,
    )


# --- C-12 -------------------------------------------------------------------
def sim_quorum_bypass(platform: CustodyPlatform) -> SimResult:
    # A single admin tries to loosen the whole policy to ALLOW-everything.
    loosened = [PolicyRule(name="allow_all", action=Decision.ALLOW)]
    blocked = False
    detail = ""
    try:
        platform.change_policy(loosened, approver_ids=["alice"])
        detail = "policy change APPLIED under single admin — control FAILED"
    except QuorumError as exc:
        blocked = True
        detail = str(exc)
    # Confirm the policy was not mutated: a large transfer must still escalate.
    follow_up = platform.submit(_tx(amount="150000"))
    intact = follow_up.decision is Decision.REQUIRE_APPROVAL
    passed = blocked and intact
    return SimResult(
        "C-12",
        passed,
        expected="QuorumError raised + policy unchanged",
        observed=f"blocked={blocked}, policy_intact={intact}",
        detail=detail,
    )


SIMULATIONS: dict[str, Callable[[CustodyPlatform], SimResult]] = {
    "sim_default_deny": sim_default_deny,
    "sim_non_whitelisted_dest": sim_non_whitelisted_dest,
    "sim_over_limit_approval": sim_over_limit_approval,
    "sim_velocity_drain": sim_velocity_drain,
    "sim_rule_shadowing": sim_rule_shadowing,
    "sim_contract_call_bypass": sim_contract_call_bypass,
    "sim_sanctioned_dest": sim_sanctioned_dest,
    "sim_high_risk_score": sim_high_risk_score,
    "sim_travel_rule": sim_travel_rule,
    "sim_rbac_denied": sim_rbac_denied,
    "sim_self_approval": sim_self_approval,
    "sim_quorum_bypass": sim_quorum_bypass,
}


__all__ = ["SIMULATIONS", "SimResult", "build_reference_platform"]
