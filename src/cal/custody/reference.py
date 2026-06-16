"""Factory for a fully-wired reference custody platform (default config).

Constructs a platform with the default TAP policy, the synthetic account
directory, and the synthetic sanctions intel. Used by the integration tests, the
assurance simulations, and the API so they all validate the SAME configuration.
"""

from __future__ import annotations

from pathlib import Path

from cal.custody.accounts import reference_access_control
from cal.custody.platform import CustodyPlatform
from cal.custody.policy_loader import DEFAULT_POLICY_PATH, load_policy
from cal.custody.rbac import PolicyChangeGovernor
from cal.custody.screening import ScreeningEngine


def build_reference_platform(policy_path: Path | str = DEFAULT_POLICY_PATH) -> CustodyPlatform:
    """Build the fully-wired reference platform.

    ``policy_path`` defaults to the production reference policy; the assurance CLI
    can point it at a deliberately-loosened policy to demonstrate drift detection.
    """
    return CustodyPlatform(
        access=reference_access_control(),
        screening=ScreeningEngine.from_file(),
        policy_engine=load_policy(policy_path),
        governor=PolicyChangeGovernor(quorum=2),
    )
