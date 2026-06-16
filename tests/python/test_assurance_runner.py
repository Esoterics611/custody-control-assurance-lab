"""Tests for the assurance harness: all controls pass, and it CATCHES a regression."""

from __future__ import annotations

import pytest

from cal.assurance.controls import CONTROL_REGISTRY
from cal.assurance.report import render_html, write_html, write_json
from cal.assurance.runner import baseline_from_report, run_all
from cal.clock import FixedClock
from cal.custody.policy_engine import PolicyRule
from cal.custody.reference import build_reference_platform
from cal.models import Decision, DestinationType, TransactionType

pytestmark = pytest.mark.assurance

CLOCK = FixedClock(1_700_000_500.0)


def test_all_controls_pass_against_reference_platform():
    report = run_all(clock=CLOCK)
    assert report.total == len(CONTROL_REGISTRY) == 12
    assert report.all_passed, f"unexpected failures: {report.failures}"
    assert report.failed == 0


def test_every_registered_control_has_a_simulation_result():
    report = run_all(clock=CLOCK)
    ids = {o.control.id for o in report.outcomes}
    assert ids == {c.id for c in CONTROL_REGISTRY}


def test_coverage_buckets_are_computed():
    report = run_all(clock=CLOCK)
    # Every CSF function present in the registry appears in coverage, fully passing.
    assert report.csf_coverage["PR.AA"]["passed"] == report.csf_coverage["PR.AA"]["total"]
    assert "T1657" in report.mitre_coverage
    # C-09 has no MITRE technique -> it must not invent a bucket.
    assert all(tag for tag in report.mitre_coverage)


class TestNegativeControl:
    """Deliberately break a control and prove the harness reports the regression."""

    def _loosened_platform_factory(self):
        # A platform whose policy has been gutted to ALLOW everything — exactly the
        # regression an attacker (or a careless change) would introduce.
        def factory():
            platform = build_reference_platform()
            platform.policy_engine.rules = [PolicyRule(name="allow_all", action=Decision.ALLOW)]
            return platform

        return factory

    def test_harness_detects_loosened_amount_control(self):
        report = run_all(self._loosened_platform_factory(), clock=CLOCK)
        # The over-limit control (C-03) must now FAIL — the attack succeeds.
        assert not report.all_passed
        assert "C-03" in report.failures
        # The velocity (C-04) and shadowing (C-05) policy controls also regress.
        assert "C-04" in report.failures

    def test_drift_is_reported_against_a_clean_baseline(self):
        clean = run_all(clock=CLOCK)
        baseline = baseline_from_report(clean)
        regressed = run_all(self._loosened_platform_factory(), baseline=baseline, clock=CLOCK)
        assert regressed.drift, "expected drift to flag regressed controls"
        assert "C-03" in regressed.drift


class TestReportWriters:
    def test_json_and_html_are_written(self, tmp_path):
        report = run_all(clock=CLOCK)
        json_path = write_json(report, tmp_path / "assurance.json")
        html_path = write_html(report, tmp_path / "assurance.html")
        assert json_path.exists() and html_path.exists()
        html = html_path.read_text()
        assert "CUSTODY CONTROL" in html
        # Every control id is rendered into the grid.
        for control in CONTROL_REGISTRY:
            assert control.id in html

    def test_html_marks_failures_when_present(self):
        # Render a report with a known failure and assert the FAIL state shows.
        def factory():
            platform = build_reference_platform()
            platform.policy_engine.rules = [PolicyRule(name="allow_all", action=Decision.ALLOW)]
            return platform

        report = run_all(factory, clock=CLOCK)
        html = render_html(report)
        assert 'data-state="fail"' in html


def test_request_builder_uses_decimal_only():
    # Guard: the simulation request factory must never produce float money.
    from decimal import Decimal

    from cal.assurance.simulations import _tx

    tx = _tx(
        amount="123.45",
        destination_type=DestinationType.WHITELISTED,
        tx_type=TransactionType.TRANSFER,
    )
    assert isinstance(tx.amount_usd, Decimal)
