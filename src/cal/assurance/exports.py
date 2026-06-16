"""Interop exports for the assurance report:

- MITRE ATT&CK Navigator layer (load into the official Navigator to visualize coverage)
- SARIF 2.1.0 (failing controls surface in the GitHub code-scanning / Security tab)
- JUnit XML (failed/skipped controls render in any CI test UI)

All are pure functions of an :class:`AssuranceReport`.
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from cal.assurance.controls import Severity
from cal.assurance.runner import AssuranceReport

GREEN = "#39d98a"
RED = "#ff5d6c"
GRAY = "#7f93a8"

# SARIF security-severity (CVSS-like) by control severity.
_SECURITY_SEVERITY = {
    Severity.CRITICAL: "9.0",
    Severity.HIGH: "7.0",
    Severity.MEDIUM: "5.0",
    Severity.LOW: "3.0",
}
CONTROLS_SOURCE = "src/cal/assurance/controls.py"


def _write(path: Path | str, text: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# --- MITRE ATT&CK Navigator -------------------------------------------------
def navigator_layer(report: AssuranceReport) -> dict:
    agg: dict[str, dict] = {}
    for outcome in report.outcomes:
        if outcome.skipped:
            continue
        for technique in outcome.control.mitre_techniques:
            bucket = agg.setdefault(technique, {"total": 0, "passed": 0, "controls": []})
            bucket["total"] += 1
            bucket["controls"].append(outcome.control.id)
            if outcome.passed:
                bucket["passed"] += 1

    techniques = []
    for technique, b in sorted(agg.items()):
        all_pass = b["passed"] == b["total"]
        controls = ", ".join(b["controls"])
        techniques.append(
            {
                "techniqueID": technique,
                "enabled": True,
                "score": round(100 * b["passed"] / b["total"]),
                "color": GREEN if all_pass else RED,
                "comment": f"{b['passed']}/{b['total']} controls passing: {controls}",
            }
        )

    return {
        "name": "Custody Control Assurance",
        "versions": {"layer": "4.5", "navigator": "4.9.1", "attack": "14"},
        "domain": "enterprise-attack",
        "description": "Coverage from the custody-control-assurance-lab BAS suite.",
        "techniques": techniques,
        "gradient": {"colors": [RED, GREEN], "minValue": 0, "maxValue": 100},
        "legendItems": [
            {"label": "all mapped controls passing", "color": GREEN},
            {"label": "one or more controls failing", "color": RED},
        ],
    }


def write_navigator_layer(report: AssuranceReport, path: Path | str) -> Path:
    return _write(path, json.dumps(navigator_layer(report), indent=2))


# --- SARIF 2.1.0 ------------------------------------------------------------
def sarif(report: AssuranceReport) -> dict:
    rules = []
    results = []
    for outcome in report.outcomes:
        control = outcome.control
        rules.append(
            {
                "id": control.id,
                "name": control.simulation,
                "shortDescription": {"text": control.objective},
                "defaultConfiguration": {"level": "error"},
                "properties": {
                    "security-severity": _SECURITY_SEVERITY[control.severity],
                    "tags": ["security", "control-validation", *control.mitre_techniques],
                },
            }
        )
        if not outcome.passed and not outcome.skipped:
            text = (
                f"Control {control.id} FAILED — {control.objective}. "
                f"expected: {outcome.result.expected}; "
                f"observed: {outcome.result.observed}."
            )
            results.append(
                {
                    "ruleId": control.id,
                    "level": "error",
                    "message": {"text": text},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": CONTROLS_SOURCE},
                                "region": {"startLine": 1},
                            }
                        }
                    ],
                }
            )

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "custody-control-assurance",
                        "informationUri": "https://github.com/Esoterics611/custody-control-assurance-lab",
                        "version": "2.0.0",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


def write_sarif(report: AssuranceReport, path: Path | str) -> Path:
    return _write(path, json.dumps(sarif(report), indent=2))


# --- JUnit XML --------------------------------------------------------------
def junit_xml(report: AssuranceReport) -> str:
    cases = []
    for outcome in report.outcomes:
        c = outcome.control
        name = quoteattr(f"{c.id} {c.objective}")
        classname = quoteattr(f"assurance.{c.stage}")
        if outcome.skipped:
            cases.append(
                f"    <testcase classname={classname} name={name}>"
                f"<skipped message={quoteattr(outcome.result.detail)}/></testcase>"
            )
        elif outcome.passed:
            cases.append(f"    <testcase classname={classname} name={name}/>")
        else:
            msg = quoteattr(
                f"expected {outcome.result.expected}, observed {outcome.result.observed}"
            )
            cases.append(
                f"    <testcase classname={classname} name={name}>"
                f"<failure message={msg}>{escape(outcome.result.detail)}</failure></testcase>"
            )
    body = "\n".join(cases)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<testsuites name="custody-control-assurance" tests="{report.total}" '
        f'failures="{report.failed}" skipped="{report.skipped}">\n'
        f'  <testsuite name="control-assurance" tests="{report.total}" '
        f'failures="{report.failed}" skipped="{report.skipped}">\n'
        f"{body}\n"
        "  </testsuite>\n</testsuites>\n"
    )


def write_junit(report: AssuranceReport, path: Path | str) -> Path:
    return _write(path, junit_xml(report))
