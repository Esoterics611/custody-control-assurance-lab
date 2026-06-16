"""Transaction Authorization Policy (TAP) engine.

Semantics (the contract the engine honors):

1. Rules are an ORDERED list, evaluated TOP-DOWN. The FIRST matching rule wins and
   is the only rule applied.
2. A rule matches on any subset of dimensions (``None`` == "any"): initiator group,
   source vault, destination type, asset, tx type, an amount threshold
   (``amount_usd >= min_amount_usd``), and an optional velocity cap. The velocity
   dimension fires when CUMULATIVE spend from the same source vault within the
   rolling window (including this request) EXCEEDS the cap.
3. Actions: ALLOW, BLOCK, REQUIRE_APPROVAL (carries ``required_approvals`` and an
   ``approver_group``).
4. No rule matches -> BLOCK (default-deny).
5. The engine is PURE: ``(request, history) -> PolicyResult``. No I/O, no wall clock.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from cal.models import (
    Decision,
    DestinationType,
    PolicyResult,
    TransactionRequest,
    TransactionType,
)

DEFAULT_DENY_REASON = "blocked by policy (default-deny)"


@dataclass(frozen=True)
class PolicyRule:
    """One TAP rule. Every dimension is optional; ``None`` means "match any"."""

    name: str
    action: Decision
    initiator_groups: tuple[str, ...] | None = None
    source_vaults: tuple[str, ...] | None = None
    destination_types: tuple[DestinationType, ...] | None = None
    assets: tuple[str, ...] | None = None
    tx_types: tuple[TransactionType, ...] | None = None
    min_amount_usd: Decimal | None = None
    # Velocity: both must be set together to enable the dimension.
    period_sec: int | None = None
    window_limit_usd: Decimal | None = None
    # Carried on REQUIRE_APPROVAL.
    required_approvals: int = 0
    approver_group: str | None = None

    @property
    def has_velocity(self) -> bool:
        return self.period_sec is not None and self.window_limit_usd is not None

    def matches(
        self,
        request: TransactionRequest,
        history: Sequence[TransactionRequest],
        group_membership: dict[str, tuple[str, ...]],
    ) -> bool:
        """True iff ALL specified dimensions match (logical AND)."""
        if self.initiator_groups is not None and not _in_any_group(
            request.initiator, self.initiator_groups, group_membership
        ):
            return False
        if self.source_vaults is not None and request.source_vault not in self.source_vaults:
            return False
        if (
            self.destination_types is not None
            and request.destination_type not in self.destination_types
        ):
            return False
        if self.assets is not None and request.asset not in self.assets:
            return False
        if self.tx_types is not None and request.tx_type not in self.tx_types:
            return False
        if self.min_amount_usd is not None and request.amount_usd < self.min_amount_usd:
            return False
        if self.has_velocity and not self._velocity_exceeded(request, history):
            return False
        return True

    def _velocity_exceeded(
        self, request: TransactionRequest, history: Sequence[TransactionRequest]
    ) -> bool:
        assert self.period_sec is not None and self.window_limit_usd is not None
        window_start = request.submitted_at - self.period_sec
        cumulative = request.amount_usd
        for prior in history:
            if prior.source_vault != request.source_vault:
                continue
            if window_start <= prior.submitted_at <= request.submitted_at:
                cumulative += prior.amount_usd
        return cumulative > self.window_limit_usd


def _in_any_group(
    user_id: str, groups: Iterable[str], group_membership: dict[str, tuple[str, ...]]
) -> bool:
    return any(user_id in group_membership.get(group, ()) for group in groups)


@dataclass
class PolicyEngine:
    """Holds the ordered rule set + group membership. Pure evaluation."""

    rules: list[PolicyRule] = field(default_factory=list)
    group_membership: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def evaluate(
        self,
        request: TransactionRequest,
        history: Sequence[TransactionRequest] = (),
    ) -> PolicyResult:
        for rule in self.rules:
            if rule.matches(request, history, self.group_membership):
                return PolicyResult(
                    decision=rule.action,
                    matched_rule=rule.name,
                    required_approvals=rule.required_approvals,
                    approver_group=rule.approver_group,
                    reason=f"matched rule '{rule.name}' -> {rule.action.value}",
                )
        return PolicyResult(decision=Decision.BLOCK, matched_rule=None, reason=DEFAULT_DENY_REASON)
