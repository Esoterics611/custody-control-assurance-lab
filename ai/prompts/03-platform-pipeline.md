# Phase 3 — Custody platform pipeline + integration tests

platform.py: CustodyPlatform holding AccessControl, ScreeningEngine, PolicyEngine,
PolicyChangeGovernor. submit(request, approver_ids=None) -> PipelineResult, executing in
order: (1) RBAC -> BLOCK @ rbac; (2) screening -> BLOCK @ screening + alert (Travel-Rule
recorded, not blocking); (3) policy -> BLOCK / proceed / REQUIRE_APPROVAL; (4) approval via
collect_valid_approvals >= required; (5) mock signer (signed=True, fake hash). Record every
ALLOWed transfer into history (so velocity sees prior spend). change_policy(new_rules,
approver_ids) -> governor.authorize_change first (QuorumError), then swap rules.
Tests end-to-end: clean -> signed; sanctioned -> BLOCK @ screening + alert; over-limit no
approvers -> pending, with two valid approvers -> signed; self-listed initiator doesn't
count; velocity cumulative breach -> REQUIRE_APPROVAL; single-admin change raises, two succeed.

Acceptance: full-pipeline integration tests green.
