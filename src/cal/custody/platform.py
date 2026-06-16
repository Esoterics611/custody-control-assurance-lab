"""The custody platform facade: runs a request through every control in order.

    submit(tx) -> [1 RBAC] -> [2 screening] -> [3 TAP policy] -> [4 approval] -> [5 signer]

Each stage can terminate the pipeline. Only a request that is fully ALLOWed reaches
the mock signer and is recorded into history (so the velocity control sees prior
spend). ``change_policy`` is the governance-protected path: it requires admin quorum
before the rule set can be swapped.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cal.custody.policy_engine import PolicyEngine, PolicyRule
from cal.custody.rbac import AccessControl, PolicyChangeGovernor
from cal.custody.screening import ScreeningEngine
from cal.models import (
    ROLE_INITIATOR,
    Decision,
    PipelineResult,
    PolicyResult,
    TransactionRequest,
)


@dataclass
class CustodyPlatform:
    access: AccessControl
    screening: ScreeningEngine
    policy_engine: PolicyEngine
    governor: PolicyChangeGovernor
    history: list[TransactionRequest] = field(default_factory=list)
    processed_ids: set[str] = field(default_factory=set)

    def submit(
        self, request: TransactionRequest, approver_ids: list[str] | None = None
    ) -> PipelineResult:
        result = PipelineResult(
            request_id=request.request_id, decision=Decision.BLOCK, stage="rbac"
        )

        # --- Stage 0: replay / idempotency -------------------------------------
        # A request_id that already reached the signer cannot be executed again.
        if request.request_id in self.processed_ids:
            result.stage = "replay"
            result.decision = Decision.BLOCK
            result.reason = f"replay rejected: request_id {request.request_id} already executed"
            result.alerts.append(f"REPLAY ALERT: duplicate request_id {request.request_id}")
            return result

        # --- Stage 1: RBAC / authorization -------------------------------------
        if not self.access.has_role(request.initiator, ROLE_INITIATOR):
            result.stage = "rbac"
            result.decision = Decision.BLOCK
            result.reason = f"authorization denied: '{request.initiator}' lacks {ROLE_INITIATOR}"
            result.alerts.append(f"RBAC: unauthorized submit attempt by '{request.initiator}'")
            return result

        # --- Stage 2: pre-signing compliance screening -------------------------
        screening = self.screening.screen(request)
        result.screening = screening
        if screening.travel_rule_required:
            result.alerts.append(f"Travel Rule: data collection required ({screening.reason})")
        if not screening.passed:
            result.stage = "screening"
            result.decision = Decision.BLOCK
            result.reason = screening.reason
            result.alerts.append(f"SCREENING ALERT: {screening.reason} ({request.destination})")
            return result

        # --- Stage 3: TAP policy ----------------------------------------------
        policy = self.policy_engine.evaluate(request, self.history)
        result.policy = policy
        if policy.decision is Decision.BLOCK:
            result.stage = "policy"
            result.decision = Decision.BLOCK
            result.reason = policy.reason
            return result
        if policy.decision is Decision.REQUIRE_APPROVAL:
            return self._handle_approval(request, policy, approver_ids, result)

        # policy ALLOW -> straight to signing
        return self._sign(request, result)

    def _handle_approval(
        self,
        request: TransactionRequest,
        policy: PolicyResult,
        approver_ids: list[str] | None,
        result: PipelineResult,
    ) -> PipelineResult:
        # --- Stage 4: approval / four-eyes ------------------------------------
        valid = self.access.collect_valid_approvals(request.initiator, approver_ids)
        if len(valid) >= policy.required_approvals:
            return self._sign(request, result)
        result.stage = "approval"
        result.decision = Decision.REQUIRE_APPROVAL
        result.reason = (
            f"pending approval: {len(valid)}/{policy.required_approvals} valid "
            f"approvals from group '{policy.approver_group}'"
        )
        return result

    def _sign(self, request: TransactionRequest, result: PipelineResult) -> PipelineResult:
        # --- Stage 5: mock signer (no real signing) ---------------------------
        result.stage = "signer"
        result.decision = Decision.ALLOW
        result.signed = True
        result.tx_hash = f"0xMOCKSIG{request.request_id.replace('-', '')[:24]}"
        result.reason = "approved and signed (mock)"
        self.history.append(request)
        self.processed_ids.add(request.request_id)
        return result

    def change_policy(
        self, new_rules: list[PolicyRule], approver_ids: list[str] | None
    ) -> set[str]:
        """Governance-protected policy swap. Raises QuorumError if under quorum."""
        admins = self.governor.authorize_change(self.access, approver_ids)
        self.policy_engine.rules = list(new_rules)
        return admins
