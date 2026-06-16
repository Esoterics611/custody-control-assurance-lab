# Phase 1 — Domain models + TAP policy engine + unit tests

clock.py: injectable Clock + FixedClock (business logic takes timestamps as input).
models.py: enums (TransactionType, DestinationType, Decision), Account.has_role,
TransactionRequest (amount_usd MUST be Decimal), ScreeningResult, PolicyResult,
PipelineResult with to_dict().
policy_engine.py: PolicyRule (optional dims; amount threshold amount_usd >= min;
velocity period_sec + window_limit on CUMULATIVE source-vault window spend) +
PolicyEngine.evaluate(request, history) — ordered top-down, first match wins, no
match -> BLOCK (default-deny). PURE: (request, history) -> PolicyResult.
policies/default_policy.yaml + loader.
Tests: clean allow; default-deny; over-limit -> REQUIRE_APPROVAL with X + group;
BOUNDARY at/under/over the limit; one-time path; velocity on cumulative window;
RULE-SHADOWING (permissive above restrictive); contract-call to unmanaged. FixedClock.

Acceptance: all policy tests green; default-deny, boundary, velocity, shadowing present.
