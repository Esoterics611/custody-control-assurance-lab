"""Tests for the interop exports: ATT&CK Navigator layer, SARIF, JUnit."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from cal.assurance.exports import junit_xml, navigator_layer, sarif
from cal.assurance.runner import run_all
from cal.clock import FixedClock
from cal.custody.policy_engine import PolicyRule
from cal.custody.reference import build_reference_platform
from cal.models import Decision

pytestmark = pytest.mark.assurance

CLOCK = FixedClock(1_700_000_500.0)


def _loosened_factory():
    def factory():
        platform = build_reference_platform()
        platform.policy_engine.rules = [PolicyRule(name="allow_all", action=Decision.ALLOW)]
        return platform

    return factory


class TestNavigator:
    def test_layer_is_valid_and_covers_techniques(self):
        layer = navigator_layer(run_all(clock=CLOCK))
        assert layer["domain"] == "enterprise-attack"
        ids = {t["techniqueID"] for t in layer["techniques"]}
        assert "T1657" in ids and "T1078" in ids
        # All green when everything passes.
        assert all(t["score"] == 100 for t in layer["techniques"])

    def test_failing_technique_turns_red(self):
        layer = navigator_layer(run_all(_loosened_factory(), clock=CLOCK))
        t1657 = next(t for t in layer["techniques"] if t["techniqueID"] == "T1657")
        assert t1657["color"] == "#ff5d6c"
        assert t1657["score"] < 100


class TestSarif:
    def test_clean_run_has_rules_but_no_results(self):
        doc = sarif(run_all(clock=CLOCK))
        run = doc["runs"][0]
        assert doc["version"] == "2.1.0"
        assert len(run["tool"]["driver"]["rules"]) == 16
        assert run["results"] == []  # no findings when all controls pass

    def test_failing_controls_become_sarif_results(self):
        doc = sarif(run_all(_loosened_factory(), clock=CLOCK))
        results = doc["runs"][0]["results"]
        assert results, "expected SARIF results for failing controls"
        rule_ids = {r["ruleId"] for r in results}
        assert "C-03" in rule_ids
        assert all(r["level"] == "error" for r in results)
        # Critical controls carry a higher security-severity than medium ones.
        rules = {r["id"]: r for r in doc["runs"][0]["tool"]["driver"]["rules"]}
        assert rules["C-12"]["properties"]["security-severity"] == "9.0"


class TestJUnit:
    def test_junit_is_well_formed_and_counts_match(self):
        report = run_all(clock=CLOCK)
        root = ET.fromstring(junit_xml(report))
        assert root.tag == "testsuites"
        assert root.attrib["tests"] == "16"
        assert root.attrib["failures"] == "0"

    def test_junit_marks_failures(self):
        xml = junit_xml(run_all(_loosened_factory(), clock=CLOCK))
        root = ET.fromstring(xml)
        assert int(root.attrib["failures"]) > 0
        assert root.find(".//failure") is not None
