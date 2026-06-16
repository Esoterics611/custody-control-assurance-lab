"""Reference synthetic account directory for the lab.

Roles align with the ``groups`` in policies/default_policy.yaml: treasury_admins
(alice, bob, carol) and traders (dave, erin). ``frank`` holds no roles and exists
only to demonstrate the RBAC denial control.
"""

from __future__ import annotations

from cal.custody.rbac import AccessControl
from cal.models import ROLE_ADMIN, ROLE_APPROVER, ROLE_INITIATOR, Account

REFERENCE_ACCOUNTS: tuple[Account, ...] = (
    Account("alice", (ROLE_INITIATOR, ROLE_APPROVER, ROLE_ADMIN)),
    Account("bob", (ROLE_INITIATOR, ROLE_APPROVER, ROLE_ADMIN)),
    Account("carol", (ROLE_APPROVER, ROLE_ADMIN)),
    Account("dave", (ROLE_INITIATOR,)),
    Account("erin", (ROLE_INITIATOR, ROLE_APPROVER)),
    Account("frank", ()),
)


def reference_access_control() -> AccessControl:
    return AccessControl.from_accounts(REFERENCE_ACCOUNTS)
