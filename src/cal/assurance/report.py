"""Emit the assurance report as JSON and as a standalone dark-console HTML file."""

from __future__ import annotations

import datetime as _dt
import html
import json
from pathlib import Path

from cal.assurance.runner import AssuranceReport


def write_json(report: AssuranceReport, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2))
    return path


def _ts(epoch: float) -> str:
    return _dt.datetime.fromtimestamp(epoch, tz=_dt.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _coverage_rows(coverage: dict[str, dict[str, int]]) -> str:
    rows = []
    for tag, stats in coverage.items():
        total, passed = stats["total"], stats["passed"]
        pct = round(100 * passed / total) if total else 0
        bar_class = "ok" if passed == total else "bad"
        rows.append(
            f'<div class="cov-row"><span class="cov-tag">{html.escape(tag)}</span>'
            f'<span class="cov-bar"><span class="cov-fill {bar_class}" style="width:{pct}%"></span></span>'
            f'<span class="cov-num">{passed}/{total}</span></div>'
        )
    return "\n".join(rows)


def _control_cards(report: AssuranceReport) -> str:
    cards = []
    for outcome in report.outcomes:
        c = outcome.control
        state = "pass" if outcome.passed else "fail"
        badge = "PASS" if outcome.passed else "FAIL"
        mitre = ", ".join(c.mitre_techniques) or "—"
        csf = ", ".join(c.csf_functions)
        cards.append(f"""
        <div class="card {state}" data-testid="control-card" data-control="{c.id}" data-state="{state}">
          <div class="card-head"><span class="cid">{c.id}</span><span class="badge {state}" data-testid="control-state">{badge}</span></div>
          <div class="obj">{html.escape(c.objective)}</div>
          <div class="meta"><span class="chip">{html.escape(c.stage)}</span><span class="chip att">{html.escape(mitre)}</span><span class="chip csf">{html.escape(csf)}</span></div>
          <div class="exp"><b>expected</b> {html.escape(outcome.result.expected)}</div>
          <div class="obs"><b>observed</b> {html.escape(outcome.result.observed)}</div>
        </div>""")
    return "\n".join(cards)


def _drift_section(report: AssuranceReport) -> str:
    if not report.drift:
        return '<div class="drift none" data-testid="drift">No control drift detected since baseline.</div>'
    items = ", ".join(html.escape(cid) for cid in report.drift)
    return (
        f'<div class="drift regressed" data-testid="drift">'
        f"⚠ DRIFT — {len(report.drift)} control(s) REGRESSED since baseline: {items}</div>"
    )


def render_html(report: AssuranceReport) -> str:
    pass_pct = round(100 * report.passed / report.total) if report.total else 0
    summary_state = "ok" if report.all_passed else "bad"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Custody Control Assurance — Report</title>
<style>
  :root {{ --bg:#0b0f14; --panel:#121a24; --line:#1f2b3a; --ink:#d7e2ef; --mut:#7f93a8;
           --amber:#ffb020; --green:#39d98a; --red:#ff5d6c; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
          font-family:"SFMono-Regular",ui-monospace,Menlo,Consolas,monospace; }}
  header {{ padding:24px 28px; border-bottom:1px solid var(--line);
            background:linear-gradient(180deg,#101824,#0b0f14); }}
  h1 {{ margin:0; font-size:18px; letter-spacing:.5px; }}
  h1 .amber {{ color:var(--amber); }}
  .sub {{ color:var(--mut); font-size:12px; margin-top:6px; }}
  .wrap {{ padding:24px 28px; max-width:1100px; margin:0 auto; }}
  .kpis {{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:22px; }}
  .kpi {{ background:var(--panel); border:1px solid var(--line); border-radius:10px;
          padding:16px 20px; min-width:130px; }}
  .kpi .n {{ font-size:30px; font-weight:700; }}
  .kpi .l {{ color:var(--mut); font-size:11px; text-transform:uppercase; letter-spacing:.8px; }}
  .kpi.ok .n {{ color:var(--green); }} .kpi.bad .n {{ color:var(--red); }}
  .section-title {{ color:var(--amber); font-size:12px; text-transform:uppercase;
                    letter-spacing:1px; margin:26px 0 12px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:12px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-left:4px solid var(--line);
           border-radius:8px; padding:14px; }}
  .card.pass {{ border-left-color:var(--green); }}
  .card.fail {{ border-left-color:var(--red); box-shadow:0 0 0 1px rgba(255,93,108,.25) inset; }}
  .card-head {{ display:flex; justify-content:space-between; align-items:center; }}
  .cid {{ font-weight:700; color:var(--amber); }}
  .badge {{ font-size:11px; font-weight:700; padding:2px 8px; border-radius:20px; }}
  .badge.pass {{ background:rgba(57,217,138,.14); color:var(--green); }}
  .badge.fail {{ background:rgba(255,93,108,.16); color:var(--red); }}
  .obj {{ margin:8px 0; font-size:13px; line-height:1.45; }}
  .meta {{ display:flex; gap:6px; flex-wrap:wrap; margin:8px 0; }}
  .chip {{ font-size:10px; color:var(--mut); border:1px solid var(--line);
           padding:2px 7px; border-radius:6px; }}
  .chip.att {{ color:#9fdcff; }} .chip.csf {{ color:#ffd79a; }}
  .exp,.obs {{ font-size:11px; color:var(--mut); margin-top:4px; }}
  .exp b,.obs b {{ color:var(--ink); font-weight:600; margin-right:6px; }}
  .cov {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 18px; }}
  .cov-row {{ display:flex; align-items:center; gap:12px; padding:5px 0; }}
  .cov-tag {{ width:72px; font-size:12px; color:var(--ink); }}
  .cov-bar {{ flex:1; height:8px; background:#0c141d; border-radius:6px; overflow:hidden; }}
  .cov-fill {{ display:block; height:100%; }}
  .cov-fill.ok {{ background:var(--green); }} .cov-fill.bad {{ background:var(--amber); }}
  .cov-num {{ width:48px; text-align:right; font-size:12px; color:var(--mut); }}
  .cols {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  .drift {{ margin-top:22px; padding:14px 18px; border-radius:10px; font-size:13px; }}
  .drift.none {{ background:rgba(57,217,138,.08); border:1px solid rgba(57,217,138,.3); color:var(--green); }}
  .drift.regressed {{ background:rgba(255,93,108,.1); border:1px solid rgba(255,93,108,.4); color:var(--red); }}
  footer {{ color:var(--mut); font-size:11px; padding:24px 28px; border-top:1px solid var(--line); }}
  @media (max-width:720px) {{ .cols {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header>
  <h1>CUSTODY CONTROL <span class="amber">ASSURANCE</span> // Breach &amp; Attack Simulation</h1>
  <div class="sub">Synthetic, defensive control-validation lab · mapped to MITRE ATT&amp;CK + NIST CSF 2.0 · generated {_ts(report.generated_at)}</div>
</header>
<div class="wrap">
  <div class="kpis">
    <div class="kpi"><div class="n" data-testid="kpi-total">{report.total}</div><div class="l">Controls</div></div>
    <div class="kpi ok"><div class="n" data-testid="kpi-passed">{report.passed}</div><div class="l">Passing</div></div>
    <div class="kpi {summary_state}"><div class="n" data-testid="kpi-failed">{report.failed}</div><div class="l">Failing</div></div>
    <div class="kpi {summary_state}"><div class="n">{pass_pct}%</div><div class="l">Coverage</div></div>
  </div>

  {_drift_section(report)}

  <div class="section-title">Control status</div>
  <div class="grid" data-testid="control-grid">
    {_control_cards(report)}
  </div>

  <div class="cols">
    <div>
      <div class="section-title">NIST CSF 2.0 coverage</div>
      <div class="cov" data-testid="csf-coverage">{_coverage_rows(report.csf_coverage)}</div>
    </div>
    <div>
      <div class="section-title">MITRE ATT&amp;CK coverage</div>
      <div class="cov" data-testid="mitre-coverage">{_coverage_rows(report.mitre_coverage)}</div>
    </div>
  </div>
</div>
<footer>
  All data synthetic · purely defensive · no real keys, sanctions feeds, or credentials.
  Control semantics modeled on the nexus-protocol institutional digital-asset compliance layer.
</footer>
</body>
</html>
"""


def write_html(report: AssuranceReport, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(report))
    return path
