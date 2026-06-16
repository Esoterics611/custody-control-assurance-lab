"""Core domain model for the mock custody platform.

All monetary amounts are ``decimal.Decimal`` — never ``float``. Enums are
str-valued so they serialise cleanly to JSON for the API / console / report.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum


class TransactionType(StrEnum):
    TRANSFER = "TRANSFER"
    CONTRACT_CALL = "CONTRACT_CALL"
    APPROVE = "APPROVE"
    MINT = "MINT"
    BURN = "BURN"
    STAKE = "STAKE"


class DestinationType(StrEnum):
    WHITELISTED = "WHITELISTED"
    ONE_TIME = "ONE_TIME"
    INTERNAL_VAULT = "INTERNAL_VAULT"
    UNMANAGED_CONTRACT = "UNMANAGED_CONTRACT"


class Decision(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


# Canonical role names (mirrors nexus-protocol's AccessControl roles in spirit).
ROLE_INITIATOR = "INITIATOR"
ROLE_APPROVER = "APPROVER"
ROLE_ADMIN = "ADMIN"


@dataclass(frozen=True)
class Account:
    """A platform principal with a fixed set of roles."""

    user_id: str
    roles: tuple[str, ...] = ()

    def has_role(self, role: str) -> bool:
        return role in self.roles


@dataclass
class TransactionRequest:
    """A request to move value out of a custody vault."""

    initiator: str
    source_vault: str
    destination: str
    destination_type: DestinationType
    asset: str
    amount_usd: Decimal  # MUST be Decimal
    submitted_at: float  # POSIX epoch — injected, never read from wall clock here
    tx_type: TransactionType = TransactionType.TRANSFER
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        # Defensive: catch float money at the boundary so it can never leak in.
        if not isinstance(self.amount_usd, Decimal):
            raise TypeError(f"amount_usd must be Decimal, got {type(self.amount_usd).__name__}")


@dataclass
class ScreeningResult:
    passed: bool
    score: int = 0
    categories: tuple[str, ...] = ()
    travel_rule_required: bool = False
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "categories": list(self.categories),
            "travel_rule_required": self.travel_rule_required,
            "reason": self.reason,
        }


@dataclass
class PolicyResult:
    decision: Decision
    matched_rule: str | None = None
    required_approvals: int = 0
    approver_group: str | None = None
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "matched_rule": self.matched_rule,
            "required_approvals": self.required_approvals,
            "approver_group": self.approver_group,
            "reason": self.reason,
        }


@dataclass
class PipelineResult:
    """The terminal outcome of running a request through every control."""

    request_id: str
    decision: Decision
    stage: str  # which control stage produced the terminal decision
    reason: str = ""
    screening: ScreeningResult | None = None
    policy: PolicyResult | None = None
    alerts: list[str] = field(default_factory=list)
    signed: bool = False
    tx_hash: str | None = None

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "decision": self.decision.value,
            "stage": self.stage,
            "reason": self.reason,
            "screening": self.screening.to_dict() if self.screening else None,
            "policy": self.policy.to_dict() if self.policy else None,
            "alerts": list(self.alerts),
            "signed": self.signed,
            "tx_hash": self.tx_hash,
        }
