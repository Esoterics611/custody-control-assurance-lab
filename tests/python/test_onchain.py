"""On-chain assurance tests.

The default suite uses a FakeContext (no network): it asserts the sims pass against
healthy on-chain state, fail on a wiring regression, and SKIP when the target is
unavailable. A separate opt-in `onchain` test hits the real Base Sepolia deployment
when CAL_ONCHAIN_RPC_URL is set and web3 is installed.
"""

from __future__ import annotations

import os

import pytest

from cal.clock import FixedClock
from cal.onchain.client import FakeContext
from cal.onchain.controls import ONCHAIN_CONTROL_REGISTRY
from cal.onchain.runner import run_onchain
from cal.onchain.simulations import ONCHAIN_SIMULATIONS

pytestmark = pytest.mark.assurance

CLOCK = FixedClock(1_700_000_500.0)

RL = "0xEa1EA3239aC1731AcB6CffbE666fA6FF55e5A669"
KYC = "0xaDac3b940503626d5c72e202bf165c572d3eA11A"
ADDRS = {"restrictionList": RL, "kycRegistry": KYC}


def _healthy_context(overrides: dict | None = None) -> FakeContext:
    responses = {
        ("stablecoin", "decimals"): 6,
        ("transferRestrictions", "restrictionList"): RL,
        ("transferRestrictions", "kycRegistry"): KYC,
        ("restrictionList", "isRestricted"): False,
        ("transferRestrictions", "isTransferAllowed"): True,
        ("mintController", "remainingAllocation"): 0,
    }
    responses.update(overrides or {})
    return FakeContext(responses=responses, addresses=ADDRS)


def test_all_onchain_controls_pass_against_healthy_state():
    report = run_onchain(_healthy_context(), clock=CLOCK)
    assert report.total == len(ONCHAIN_CONTROL_REGISTRY) == 5
    assert report.all_passed, report.failures
    assert report.skipped == 0


def test_wiring_drift_is_detected():
    # TransferRestrictions repointed away from the expected RestrictionList.
    ctx = _healthy_context(
        {("transferRestrictions", "restrictionList"): "0x0000000000000000000000000000000000000000"}
    )
    report = run_onchain(ctx, clock=CLOCK)
    assert not report.all_passed
    assert "OC-02" in report.failures


def test_bricked_decimals_fails_reachability():
    ctx = _healthy_context({("stablecoin", "decimals"): 18})
    report = run_onchain(ctx, clock=CLOCK)
    assert "OC-01" in report.failures


def test_unavailable_target_skips_not_fails():
    # No context and connect() returns None (web3 missing / RPC down) -> all SKIPPED.
    report = run_onchain(context=None, rpc_url="http://127.0.0.1:1", clock=CLOCK)
    assert report.skipped == report.total
    assert report.all_passed  # skipped controls never fail the run
    assert report.failed == 0


def test_rpc_error_becomes_a_clean_failure():
    def boom(*_args):
        raise RuntimeError("rpc exploded")

    ctx = _healthy_context({("stablecoin", "decimals"): boom})
    result = ONCHAIN_SIMULATIONS["oc_reachability"](ctx)
    assert result.passed is False
    assert result.skipped is False
    assert "rpc exploded" in result.detail


@pytest.mark.onchain
@pytest.mark.skipif(
    not os.getenv("CAL_ONCHAIN_RPC_URL"),
    reason="set CAL_ONCHAIN_RPC_URL (+ uv sync --extra onchain) to run live on-chain checks",
)
def test_live_onchain_controls():
    report = run_onchain()
    # Live target must be reachable and the compliance wiring intact.
    assert report.skipped == 0, "expected a live connection"
    assert report.all_passed, report.failures
