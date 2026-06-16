"""Run the on-chain assurance suite and aggregate into the shared AssuranceReport."""

from __future__ import annotations

from collections.abc import Mapping

from cal.assurance.runner import AssuranceReport, ControlOutcome, aggregate
from cal.assurance.simulations import SimResult
from cal.clock import Clock, system_clock
from cal.onchain.client import Context, OnchainContext
from cal.onchain.controls import ONCHAIN_CONTROL_REGISTRY
from cal.onchain.simulations import ONCHAIN_SIMULATIONS

UNAVAILABLE = (
    "on-chain target unavailable (install `uv sync --extra onchain` and/or set CAL_ONCHAIN_RPC_URL)"
)


def run_onchain(
    context: Context | None = None,
    *,
    rpc_url: str | None = None,
    baseline: Mapping[str, bool] | None = None,
    clock: Clock = system_clock,
) -> AssuranceReport:
    """Validate the live on-chain controls.

    If no context is supplied, one is connected from ``rpc_url`` / env / the vendored
    default. When the target is unreachable, every control is reported as SKIPPED
    (never FAILED) so offline runs and CI stay green.
    """
    ctx = context if context is not None else OnchainContext.connect(rpc_url)

    outcomes: list[ControlOutcome] = []
    for control in ONCHAIN_CONTROL_REGISTRY:
        if ctx is None:
            result = SimResult.skip(control.id, UNAVAILABLE)
        else:
            result = ONCHAIN_SIMULATIONS[control.simulation](ctx)
        outcomes.append(ControlOutcome(control=control, result=result))

    return aggregate(outcomes, baseline=baseline, clock=clock)
