"""Unit tests for the TAP policy engine — boundaries, velocity, and rule-ordering."""

from __future__ import annotations

from decimal import Decimal

import pytest

from cal.custody.policy_engine import PolicyEngine, PolicyRule
from cal.custody.policy_loader import load_policy
from cal.models import Decision, DestinationType, TransactionRequest, TransactionType

pytestmark = pytest.mark.unit

T0 = 1_700_000_000.0  # fixed reference epoch; no wall-clock reads anywhere


def make_request(
    *,
    amount: str,
    destination_type: DestinationType = DestinationType.WHITELISTED,
    tx_type: TransactionType = TransactionType.TRANSFER,
    source_vault: str = "1",
    submitted_at: float = T0,
    initiator: str = "dave",
) -> TransactionRequest:
    return TransactionRequest(
        initiator=initiator,
        source_vault=source_vault,
        destination="0xDEST",
        destination_type=destination_type,
        asset="USDC",
        amount_usd=Decimal(amount),
        submitted_at=submitted_at,
        tx_type=tx_type,
    )


@pytest.fixture
def engine() -> PolicyEngine:
    return load_policy()


def test_clean_whitelisted_transfer_allows(engine: PolicyEngine):
    result = engine.evaluate(make_request(amount="5000"))
    assert result.decision is Decision.ALLOW
    assert result.matched_rule == "allow_whitelisted_internal"


def test_default_deny_on_no_match(engine: PolicyEngine):
    # A STAKE to a whitelisted dest matches no rule (allow rule is TRANSFER-only).
    result = engine.evaluate(make_request(amount="100", tx_type=TransactionType.STAKE))
    assert result.decision is Decision.BLOCK
    assert result.matched_rule is None
    assert "default-deny" in result.reason


def test_over_limit_requires_approval_with_group_and_count(engine: PolicyEngine):
    result = engine.evaluate(make_request(amount="100000"))
    assert result.decision is Decision.REQUIRE_APPROVAL
    assert result.matched_rule == "large_amount_dual_approval"
    assert result.required_approvals == 2
    assert result.approver_group == "treasury_admins"


@pytest.mark.parametrize(
    "amount,expected",
    [
        ("99999.99", Decision.ALLOW),  # one cent under the limit
        ("100000", Decision.REQUIRE_APPROVAL),  # exactly the limit (>=)
        ("100000.01", Decision.REQUIRE_APPROVAL),  # one cent over
    ],
)
def test_amount_limit_boundary(engine: PolicyEngine, amount, expected):
    assert engine.evaluate(make_request(amount=amount)).decision is expected


def test_one_time_destination_escalates_above_threshold(engine: PolicyEngine):
    result = engine.evaluate(
        make_request(amount="10000", destination_type=DestinationType.ONE_TIME)
    )
    assert result.decision is Decision.REQUIRE_APPROVAL
    assert result.matched_rule == "one_time_destination_approval"
    assert result.required_approvals == 1


def test_one_time_small_falls_to_default_deny(engine: PolicyEngine):
    # A non-allowlisted (one-time) destination below the escalation threshold is not
    # silently allowed — the allowlist baseline only covers WHITELISTED / INTERNAL.
    result = engine.evaluate(make_request(amount="1500", destination_type=DestinationType.ONE_TIME))
    assert result.decision is Decision.BLOCK
    assert result.matched_rule is None


def test_contract_call_to_unmanaged_is_governed(engine: PolicyEngine):
    # Type-confusion attempt: move value via CONTRACT_CALL instead of TRANSFER.
    result = engine.evaluate(
        make_request(
            amount="500",
            destination_type=DestinationType.UNMANAGED_CONTRACT,
            tx_type=TransactionType.CONTRACT_CALL,
        )
    )
    assert result.decision is Decision.REQUIRE_APPROVAL
    assert result.matched_rule == "govern_contract_interaction_unmanaged"


def test_raw_transfer_to_unmanaged_is_blocked(engine: PolicyEngine):
    result = engine.evaluate(
        make_request(amount="500", destination_type=DestinationType.UNMANAGED_CONTRACT)
    )
    assert result.decision is Decision.BLOCK
    assert result.matched_rule == "block_transfer_to_unmanaged_contract"


class TestVelocity:
    """Velocity fires on CUMULATIVE window spend, not per-transaction amount."""

    def _vault0(self, amount: str, at: float) -> TransactionRequest:
        return make_request(amount=amount, source_vault="0", submitted_at=at)

    def test_single_sub_cap_transfer_allows(self, engine: PolicyEngine):
        # 90k from vault 0 alone: under the 100k approval line and under the 250k cap.
        result = engine.evaluate(self._vault0("90000", T0))
        assert result.decision is Decision.ALLOW

    def test_cumulative_window_spend_triggers_escalation(self, engine: PolicyEngine):
        history = [
            self._vault0("90000", T0),
            self._vault0("90000", T0 + 600),
        ]  # 180k already spent in the window
        breaching = self._vault0("90000", T0 + 1200)  # would push cumulative to 270k
        result = engine.evaluate(breaching, history)
        assert result.decision is Decision.REQUIRE_APPROVAL
        assert result.matched_rule == "velocity_cap_rolling_window"

    def test_spend_outside_window_does_not_count(self, engine: PolicyEngine):
        # Prior spend is older than the 3600s window -> it must not accumulate.
        history = [
            self._vault0("90000", T0),
            self._vault0("90000", T0 + 600),
        ]
        later = self._vault0("90000", T0 + 5000)  # window no longer contains the priors
        result = engine.evaluate(later, history)
        assert result.decision is Decision.ALLOW

    def test_cap_is_exclusive_boundary(self, engine: PolicyEngine):
        # Exactly at the cap does NOT fire (rule says "exceeds"); one unit over does.
        at_cap = engine.evaluate(self._vault0("250000", T0))
        # 250k >= 100k also trips the large-amount rule, which sits ABOVE velocity —
        # so "at cap" is escalated by the amount rule, not velocity.
        assert at_cap.matched_rule == "large_amount_dual_approval"

        history = [self._vault0("200000", T0)]
        over = self._vault0("50001", T0 + 60)  # 250,001 cumulative, each tx < 100k
        result = engine.evaluate(over, history)
        assert result.decision is Decision.REQUIRE_APPROVAL
        assert result.matched_rule == "velocity_cap_rolling_window"


class TestRuleShadowing:
    """Ordering matters: a permissive rule placed above a restrictive one shadows it.

    The reference policy is ordered correctly (restrictive first), so a large
    whitelisted transfer is escalated. We then build a deliberately MIS-ordered engine
    to demonstrate the bypass these tests guard against.
    """

    def test_reference_ordering_restrictive_rule_wins(self, engine: PolicyEngine):
        result = engine.evaluate(make_request(amount="150000"))
        assert result.decision is Decision.REQUIRE_APPROVAL
        assert result.matched_rule == "large_amount_dual_approval"

    def test_misordered_allow_shadows_approval_rule(self):
        allow_first = PolicyRule(
            name="allow_whitelisted_internal",
            action=Decision.ALLOW,
            destination_types=(DestinationType.WHITELISTED, DestinationType.INTERNAL_VAULT),
            tx_types=(TransactionType.TRANSFER,),
        )
        large_approval = PolicyRule(
            name="large_amount_dual_approval",
            action=Decision.REQUIRE_APPROVAL,
            min_amount_usd=Decimal("100000"),
            required_approvals=2,
            approver_group="treasury_admins",
        )
        bad_engine = PolicyEngine(rules=[allow_first, large_approval])
        result = bad_engine.evaluate(make_request(amount="150000"))
        # Shadowed: the broad allow above the approval rule lets a large transfer pass.
        assert result.decision is Decision.ALLOW
        assert result.matched_rule == "allow_whitelisted_internal"
