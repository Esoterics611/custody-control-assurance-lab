"""Access control, segregation-of-duties (four-eyes), and the admin-quorum governor.

Mirrors, in a small honest way, nexus-protocol's OZ ``AccessControl`` roles plus the
Governor/Timelock gate on privileged changes. No I/O; deterministic.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from cal.models import ROLE_ADMIN, ROLE_APPROVER, Account


class AuthorizationError(Exception):
    """Raised when a principal lacks the role required for an action."""


class QuorumError(Exception):
    """Raised when a privileged change has insufficient distinct admin approvals."""


@dataclass
class AccessControl:
    """An account directory with role checks and four-eyes approval collection."""

    accounts: dict[str, Account] = field(default_factory=dict)

    @classmethod
    def from_accounts(cls, accounts: Iterable[Account]) -> AccessControl:
        return cls(accounts={a.user_id: a for a in accounts})

    def add(self, account: Account) -> None:
        self.accounts[account.user_id] = account

    def has_role(self, user_id: str, role: str) -> bool:
        account = self.accounts.get(user_id)
        return account is not None and account.has_role(role)

    def is_admin(self, user_id: str) -> bool:
        return self.has_role(user_id, ROLE_ADMIN)

    def require_role(self, user_id: str, role: str) -> None:
        if not self.has_role(user_id, role):
            raise AuthorizationError(f"user '{user_id}' lacks required role '{role}'")

    def can_approve(self, approver_id: str, initiator_id: str) -> bool:
        """Four-eyes: an approver must hold APPROVER and not be the initiator."""
        return approver_id != initiator_id and self.has_role(approver_id, ROLE_APPROVER)

    def collect_valid_approvals(
        self, initiator_id: str, approver_ids: Sequence[str] | None
    ) -> list[str]:
        """De-dupe, drop the initiator, drop non-approvers; preserve order."""
        valid: list[str] = []
        seen: set[str] = set()
        for approver_id in approver_ids or ():
            if approver_id in seen:
                continue
            seen.add(approver_id)
            if self.can_approve(approver_id, initiator_id):
                valid.append(approver_id)
        return valid


@dataclass
class PolicyChangeGovernor:
    """Requires a quorum of DISTINCT admins to authorize a policy change."""

    quorum: int = 2

    def authorize_change(
        self, access: AccessControl, approver_ids: Sequence[str] | None
    ) -> set[str]:
        distinct_admins = {
            approver_id for approver_id in set(approver_ids or ()) if access.is_admin(approver_id)
        }
        if len(distinct_admins) < self.quorum:
            raise QuorumError(
                f"policy change requires {self.quorum} distinct admin approvals, "
                f"got {len(distinct_admins)}"
            )
        return distinct_admins
