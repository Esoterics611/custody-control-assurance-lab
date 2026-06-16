# Phase 2 — Screening + RBAC/SoD + admin quorum + tests

data/sanctions.sample.json: SYNTHETIC — header says NOT A REAL SANCTIONS LIST.
screening.py: ScreeningEngine.from_file(); screen(request) -> ScreeningResult.
Sanctioned categories (OFAC_SANCTION/SANCTIONS/TERROR_FINANCING) -> hard block;
else score >= risk_ceiling (75) -> block; unknown -> pass. travel_rule_required
when destination_type in {ONE_TIME,UNMANAGED_CONTRACT} and amount >= 1000.
rbac.py: AccessControl (require_role raises AuthorizationError; can_approve = APPROVER
and approver != initiator; collect_valid_approvals de-dupes/drops initiator/non-approvers);
PolicyChangeGovernor(quorum=2).authorize_change raises QuorumError unless >= 2 distinct ADMINs.
Tests: sanctioned blocked; risk boundary 74 vs 75; unknown clean; Travel-Rule 999 vs 1000
+ destination-type dependence; wrong role can't submit; no self-approval; duplicate approver
counts once; single admin can't change, two distinct can.

Acceptance: screening + rbac/quorum tests green with boundary cases.
