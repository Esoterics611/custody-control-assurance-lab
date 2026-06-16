"""Integration tests: a request flowing through the full custody pipeline."""

from __future__ import annotations

from decimal import Decimal

import pytest

from cal.custody.policy_engine import PolicyRule
from cal.custody.rbac import QuorumError
from cal.custody.reference import build_reference_platform
from cal.models import Decision, DestinationType, TransactionRequest, TransactionType

pytestmark = pytest.mark.integration

T0 = 1_700_000_000.0

ADDR_SANCTIONED = "0xSANCTIONED00000000000000000000000000000001"
ADDR_CLEAN = "0xCLEAN0000000000000000000000000000000000099"


@pytest.fixture
def platform():
    return build_reference_platform()


def make_request(
    *,
    amount: str,
    initiator: str = "dave",
    destination: str = ADDR_CLEAN,
    destination_type: DestinationType = DestinationType.WHITELISTED,
    tx_type: TransactionType = TransactionType.TRANSFER,
    source_vault: str = "1",
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


def test_clean_under_limit_transfer_is_signed(platform):
    result = platform.submit(make_request(amount="5000"))
    assert result.decision is Decision.ALLOW
    assert result.stage == "signer"
    assert result.signed is True
    assert result.tx_hash is not None


def test_unauthorized_initiator_blocked_at_rbac(platform):
    # frank holds no INITIATOR role.
    result = platform.submit(make_request(amount="5000", initiator="frank"))
    assert result.decision is Decision.BLOCK
    assert result.stage == "rbac"
    assert any("unauthorized" in a.lower() for a in result.alerts)


def test_sanctioned_destination_blocked_at_screening_with_alert(platform):
    result = platform.submit(make_request(amount="5000", destination=ADDR_SANCTIONED))
    assert result.decision is Decision.BLOCK
    assert result.stage == "screening"
    assert result.signed is False
    assert any("SCREENING ALERT" in a for a in result.alerts)


class TestApproval:
    def test_over_limit_without_approvers_is_pending(self, platform):
        result = platform.submit(make_request(amount="150000"))
        assert result.decision is Decision.REQUIRE_APPROVAL
        assert result.stage == "approval"
        assert result.signed is False

    def test_over_limit_with_two_valid_approvers_is_signed(self, platform):
        result = platform.submit(make_request(amount="150000"), approver_ids=["alice", "bob"])
        assert result.decision is Decision.ALLOW
        assert result.signed is True

    def test_self_listed_initiator_does_not_count_as_approver(self, platform):
        # alice initiates and lists herself + one real approver: only 1 valid < 2.
        result = platform.submit(
            make_request(amount="150000", initiator="alice"),
            approver_ids=["alice", "bob"],
        )
        assert result.decision is Decision.REQUIRE_APPROVAL
        assert result.stage == "approval"


class TestVelocityThroughPipeline:
    def test_cumulative_window_breach_forces_approval(self, platform):
        # Three 90k transfers from vault "0"; the first two are signed (recorded),
        # the third pushes cumulative window spend over 250k -> REQUIRE_APPROVAL.
        for i in range(2):
            r = platform.submit(
                make_request(amount="90000", source_vault="0", submitted_at=T0 + i * 600)
            )
            assert r.decision is Decision.ALLOW
        breaching = platform.submit(
            make_request(amount="90000", source_vault="0", submitted_at=T0 + 1200)
        )
        assert breaching.decision is Decision.REQUIRE_APPROVAL
        assert breaching.policy.matched_rule == "velocity_cap_rolling_window"


class TestGovernanceProtectedPolicyChange:
    def _loosened_rules(self, platform):
        # A single permissive ALLOW-everything rule (would gut every policy control).
        return [PolicyRule(name="allow_all", action=Decision.ALLOW)]

    def test_single_admin_change_is_rejected(self, platform):
        with pytest.raises(QuorumError):
            platform.change_policy(self._loosened_rules(platform), approver_ids=["alice"])

    def test_two_admins_change_is_applied(self, platform):
        platform.change_policy(self._loosened_rules(platform), approver_ids=["alice", "bob"])
        # After the loosening, a previously-escalated large transfer now ALLOWs.
        result = platform.submit(make_request(amount="150000"))
        assert result.decision is Decision.ALLOW
