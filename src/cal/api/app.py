"""FastAPI surface exposing the custody platform + the assurance harness.

Built around a single in-memory reference :class:`CustodyPlatform`. All endpoints
are exercised via Starlette's ``TestClient`` (no live server needed for tests).
``create_app()`` builds a fresh, isolated app so tests don't share mutable state.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from cal.api.metrics import CONTENT_TYPE, prometheus_metrics
from cal.assurance.history import load_history
from cal.assurance.runner import run_all
from cal.clock import system_clock
from cal.custody.platform import CustodyPlatform
from cal.custody.policy_engine import PolicyEngine, PolicyRule
from cal.custody.policy_loader import rule_from_dict
from cal.custody.rbac import QuorumError
from cal.custody.reference import build_reference_platform
from cal.models import DestinationType, TransactionRequest, TransactionType

CONSOLE_HTML = Path(__file__).resolve().parents[3] / "console" / "index.html"


class TransactionBody(BaseModel):
    initiator: str
    source_vault: str
    destination: str
    destination_type: DestinationType
    asset: str = "USDC"
    amount_usd: Decimal
    tx_type: TransactionType = TransactionType.TRANSFER
    approver_ids: list[str] | None = None


class PolicyChangeBody(BaseModel):
    new_rules: list[dict] = Field(default_factory=list)
    approver_ids: list[str] | None = None


def _serialize_rule(rule: PolicyRule) -> dict:
    """Sanitized, JSON-safe view of a policy rule (Decimals -> str)."""
    out: dict = {"name": rule.name, "action": rule.action.value}
    if rule.destination_types:
        out["destination_types"] = [d.value for d in rule.destination_types]
    if rule.tx_types:
        out["tx_types"] = [t.value for t in rule.tx_types]
    if rule.source_vaults:
        out["source_vaults"] = list(rule.source_vaults)
    if rule.min_amount_usd is not None:
        out["min_amount_usd"] = str(rule.min_amount_usd)
    if rule.period_sec is not None:
        out["period_sec"] = rule.period_sec
        out["window_limit_usd"] = str(rule.window_limit_usd)
    if rule.required_approvals:
        out["required_approvals"] = rule.required_approvals
        out["approver_group"] = rule.approver_group
    return out


def _serialize_policy(engine: PolicyEngine) -> list[dict]:
    return [_serialize_rule(r) for r in engine.rules]


def create_app() -> FastAPI:
    app = FastAPI(title="Custody Control Assurance Lab", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mutable holder so /admin/reset can swap in a fresh platform (used by the E2E
    # suite for per-test isolation and by the demo's "restore" step).
    holder: dict[str, object] = {
        "platform": build_reference_platform(),
        "last_report": None,
    }

    def current() -> CustodyPlatform:
        return holder["platform"]  # type: ignore[return-value]

    @app.get("/", include_in_schema=False)
    def index():
        if CONSOLE_HTML.exists():
            return FileResponse(CONSOLE_HTML)
        return JSONResponse({"service": "custody-control-assurance-lab"})

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "controls": "loaded"}

    @app.post("/admin/reset")
    def admin_reset():
        """Rebuild the in-memory reference platform (clears history + restores policy)."""
        holder["platform"] = build_reference_platform()
        holder["last_report"] = None
        return {"status": "reset"}

    @app.post("/transactions")
    def submit_transaction(body: TransactionBody):
        request = TransactionRequest(
            initiator=body.initiator,
            source_vault=body.source_vault,
            destination=body.destination,
            destination_type=body.destination_type,
            asset=body.asset,
            amount_usd=body.amount_usd,
            submitted_at=system_clock(),
            tx_type=body.tx_type,
        )
        result = current().submit(request, approver_ids=body.approver_ids)
        return result.to_dict()

    @app.get("/policy")
    def get_policy():
        return {"rules": _serialize_policy(current().policy_engine)}

    @app.post("/policy/change")
    def change_policy(body: PolicyChangeBody):
        try:
            rules = [rule_from_dict(r) for r in body.new_rules]
            admins = current().change_policy(rules, approver_ids=body.approver_ids)
        except QuorumError as exc:
            return JSONResponse(status_code=403, content={"error": str(exc)})
        return {
            "status": "applied",
            "authorized_by": sorted(admins),
            "rules": _serialize_policy(current().policy_engine),
        }

    @app.post("/assurance/run")
    def run_assurance():
        report = run_all()
        holder["last_report"] = report
        return report.to_dict()

    @app.get("/metrics")
    def metrics():
        # Prometheus scrape: run the mock suite fresh (deterministic, fast).
        return PlainTextResponse(prometheus_metrics(run_all()), media_type=CONTENT_TYPE)

    @app.get("/assurance/history")
    def assurance_history():
        return {"history": load_history(limit=50)}

    @app.get("/assurance/report")
    def last_report():
        report = holder["last_report"]
        if report is None:
            return JSONResponse(
                status_code=404, content={"error": "no report yet; POST /assurance/run"}
            )
        return report.to_dict()

    return app


app = create_app()
