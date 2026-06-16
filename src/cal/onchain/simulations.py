"""On-chain Breach & Attack Simulations — READ-ONLY validations via eth_call.

Each takes a context (live or fake) and returns a :class:`SimResult`. ``passed``
means the real on-chain control is present / responsive / correctly wired. No state
is ever changed; no transaction is ever sent.
"""

from __future__ import annotations

from collections.abc import Callable

from cal.assurance.simulations import SimResult
from cal.onchain.client import DEAD_ADDRESS, OTHER_ADDRESS, Context


def _safe(control_id: str, expected: str, fn: Callable[[], SimResult]) -> SimResult:
    """Wrap a check so an RPC/decoding error becomes a clean FAIL, not a crash."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — surface any RPC error as a control failure
        return SimResult(control_id, False, expected=expected, observed="error", detail=str(exc))


def oc_reachability(ctx: Context) -> SimResult:
    def run():
        decimals = ctx.call("stablecoin", "decimals")
        return SimResult(
            "OC-01",
            passed=decimals == 6,
            expected="stablecoin reachable, decimals == 6 (USDC convention)",
            observed=f"decimals={decimals}",
        )

    return _safe("OC-01", "stablecoin reachable, decimals == 6", run)


def oc_restriction_wiring(ctx: Context) -> SimResult:
    def run():
        wired = ctx.call("transferRestrictions", "restrictionList")
        expected = ctx.addr("restrictionList")
        return SimResult(
            "OC-02",
            passed=wired.lower() == expected.lower(),
            expected=f"restrictionList == {expected}",
            observed=f"wired={wired}",
            detail="catches a silently-disconnected denylist (config drift)",
        )

    return _safe("OC-02", "restrictionList wiring intact", run)


def oc_kyc_wiring(ctx: Context) -> SimResult:
    def run():
        wired = ctx.call("transferRestrictions", "kycRegistry")
        expected = ctx.addr("kycRegistry")
        return SimResult(
            "OC-03",
            passed=wired.lower() == expected.lower(),
            expected=f"kycRegistry == {expected}",
            observed=f"wired={wired}",
            detail="catches a silently-disconnected KYC gate (config drift)",
        )

    return _safe("OC-03", "kycRegistry wiring intact", run)


def oc_denylist_functional(ctx: Context) -> SimResult:
    def run():
        restricted = ctx.call("restrictionList", "isRestricted", DEAD_ADDRESS)
        allowed = ctx.call(
            "transferRestrictions", "isTransferAllowed", DEAD_ADDRESS, OTHER_ADDRESS, 0
        )
        # The surface must be live: an unknown address is not restricted, and the
        # transfer-check returns a real bool (not bricked to always-deny).
        passed = restricted is False and isinstance(allowed, bool)
        return SimResult(
            "OC-04",
            passed=passed,
            expected="isRestricted(unknown)==False and isTransferAllowed returns bool",
            observed=f"isRestricted={restricted}, isTransferAllowed={allowed}",
        )

    return _safe("OC-04", "denylist surface functional", run)


def oc_mint_ceiling(ctx: Context) -> SimResult:
    def run():
        remaining = ctx.call("mintController", "remainingAllocation", DEAD_ADDRESS)
        passed = isinstance(remaining, int) and remaining >= 0
        return SimResult(
            "OC-05",
            passed=passed,
            expected="MintController.remainingAllocation callable, returns uint",
            observed=f"remainingAllocation(probe)={remaining}",
        )

    return _safe("OC-05", "mint-ceiling control present", run)


ONCHAIN_SIMULATIONS: dict[str, Callable[[Context], SimResult]] = {
    "oc_reachability": oc_reachability,
    "oc_restriction_wiring": oc_restriction_wiring,
    "oc_kyc_wiring": oc_kyc_wiring,
    "oc_denylist_functional": oc_denylist_functional,
    "oc_mint_ceiling": oc_mint_ceiling,
}
