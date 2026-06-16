"""API tests via Starlette TestClient — no live server required."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cal.api.app import create_app

pytestmark = pytest.mark.integration

ADDR_SANCTIONED = "0xSANCTIONED00000000000000000000000000000001"
ADDR_CLEAN = "0xCLEAN0000000000000000000000000000000000099"


@pytest.fixture
def client():
    # Fresh app per test -> isolated in-memory platform state.
    return TestClient(create_app())


def _tx(**overrides):
    body = {
        "initiator": "dave",
        "source_vault": "1",
        "destination": ADDR_CLEAN,
        "destination_type": "WHITELISTED",
        "asset": "USDC",
        "amount_usd": "5000",
        "tx_type": "TRANSFER",
    }
    body.update(overrides)
    return body


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_admin_reset_restores_default_policy(client):
    # Apply a loosening change, then reset and confirm the default policy is back.
    client.post(
        "/policy/change",
        json={
            "new_rules": [{"name": "allow_all", "action": "ALLOW"}],
            "approver_ids": ["alice", "bob"],
        },
    )
    assert client.post("/admin/reset").json()["status"] == "reset"
    names = [r["name"] for r in client.get("/policy").json()["rules"]]
    assert "large_amount_dual_approval" in names


def test_clean_transfer_is_signed(client):
    resp = client.post("/transactions", json=_tx())
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "ALLOW"
    assert data["signed"] is True


def test_sanctioned_destination_blocks_at_screening(client):
    resp = client.post("/transactions", json=_tx(destination=ADDR_SANCTIONED))
    data = resp.json()
    assert data["decision"] == "BLOCK"
    assert data["stage"] == "screening"
    assert any("SCREENING ALERT" in a for a in data["alerts"])


def test_over_limit_requires_approval(client):
    resp = client.post("/transactions", json=_tx(amount_usd="250000"))
    data = resp.json()
    assert data["decision"] == "REQUIRE_APPROVAL"
    assert data["stage"] == "approval"


def test_over_limit_with_two_approvers_signs(client):
    resp = client.post(
        "/transactions",
        json=_tx(amount_usd="250000", approver_ids=["alice", "bob"]),
    )
    data = resp.json()
    assert data["decision"] == "ALLOW"
    assert data["signed"] is True


def test_get_policy_lists_rules(client):
    resp = client.get("/policy")
    assert resp.status_code == 200
    names = [r["name"] for r in resp.json()["rules"]]
    assert "large_amount_dual_approval" in names


def test_single_admin_policy_change_is_forbidden(client):
    resp = client.post(
        "/policy/change",
        json={"new_rules": [{"name": "allow_all", "action": "ALLOW"}], "approver_ids": ["alice"]},
    )
    assert resp.status_code == 403
    assert "admin approvals" in resp.json()["error"].lower()


def test_two_admin_policy_change_succeeds(client):
    resp = client.post(
        "/policy/change",
        json={
            "new_rules": [{"name": "allow_all", "action": "ALLOW"}],
            "approver_ids": ["alice", "bob"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"


class TestAssuranceEndpoints:
    def test_run_returns_twelve_controls_all_passing(self, client):
        resp = client.post("/assurance/run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total"] == 16
        assert data["summary"]["all_passed"] is True
        assert len(data["outcomes"]) == 16

    def test_report_404_before_first_run(self, client):
        assert client.get("/assurance/report").status_code == 404

    def test_report_available_after_run(self, client):
        client.post("/assurance/run")
        resp = client.get("/assurance/report")
        assert resp.status_code == 200
        assert resp.json()["summary"]["total"] == 16
