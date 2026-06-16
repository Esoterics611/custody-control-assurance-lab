"""Unit tests for RBAC, four-eyes segregation-of-duties, and the admin quorum."""

from __future__ import annotations

import pytest

from cal.custody.accounts import reference_access_control
from cal.custody.rbac import (
    AuthorizationError,
    PolicyChangeGovernor,
    QuorumError,
)
from cal.models import ROLE_INITIATOR

pytestmark = pytest.mark.unit


@pytest.fixture
def access():
    return reference_access_control()


class TestRBAC:
    def test_initiator_role_required_to_submit(self, access):
        # frank holds no roles -> requiring INITIATOR must raise.
        with pytest.raises(AuthorizationError):
            access.require_role("frank", ROLE_INITIATOR)
        # dave is an initiator -> no raise.
        access.require_role("dave", ROLE_INITIATOR)

    def test_unknown_user_is_denied(self, access):
        assert access.has_role("nobody", ROLE_INITIATOR) is False


class TestFourEyes:
    def test_initiator_cannot_self_approve(self, access):
        # alice is an APPROVER, but cannot approve a transaction she initiated.
        assert access.can_approve("alice", "alice") is False

    def test_non_approver_cannot_approve(self, access):
        # dave can initiate but is not an APPROVER.
        assert access.can_approve("dave", "alice") is False

    def test_collect_drops_initiator_and_dedupes(self, access):
        # alice initiates; supplied approvers include herself, a duplicate, a
        # non-approver (dave), and a clean approver listed twice.
        valid = access.collect_valid_approvals("alice", ["alice", "bob", "bob", "dave", "carol"])
        assert valid == ["bob", "carol"]

    def test_two_distinct_approvers_satisfy_four_eyes(self, access):
        valid = access.collect_valid_approvals("dave", ["bob", "carol"])
        assert len(valid) == 2


class TestAdminQuorum:
    def test_single_admin_cannot_change_policy(self, access):
        governor = PolicyChangeGovernor(quorum=2)
        with pytest.raises(QuorumError):
            governor.authorize_change(access, ["alice"])

    def test_duplicate_admin_counts_once(self, access):
        governor = PolicyChangeGovernor(quorum=2)
        with pytest.raises(QuorumError):
            governor.authorize_change(access, ["alice", "alice"])

    def test_non_admin_approver_does_not_count(self, access):
        # erin is an APPROVER but not an ADMIN -> does not count toward quorum.
        governor = PolicyChangeGovernor(quorum=2)
        with pytest.raises(QuorumError):
            governor.authorize_change(access, ["alice", "erin"])

    def test_two_distinct_admins_authorize(self, access):
        governor = PolicyChangeGovernor(quorum=2)
        admins = governor.authorize_change(access, ["alice", "bob"])
        assert admins == {"alice", "bob"}
