"""Factory for a fully-wired reference custody platform (default config).

Constructs a platform with the default TAP policy, the synthetic account
directory, and the synthetic sanctions intel. Used by the integration tests, the
assurance simulations, and the API so they all validate the SAME configuration.
"""

from __future__ import annotations

from cal.custody.accounts import reference_access_control
from cal.custody.platform import CustodyPlatform
from cal.custody.policy_loader import load_policy
from cal.custody.rbac import PolicyChangeGovernor
from cal.custody.screening import ScreeningEngine


def build_reference_platform() -> CustodyPlatform:
    return CustodyPlatform(
        access=reference_access_control(),
        screening=ScreeningEngine.from_file(),
        policy_engine=load_policy(),
        governor=PolicyChangeGovernor(quorum=2),
    )
