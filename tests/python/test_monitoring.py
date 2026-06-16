"""Tests for continuous monitoring: run history + Prometheus metrics + API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cal.api.app import create_app
from cal.api.metrics import prometheus_metrics
from cal.assurance.history import append_history, load_history
from cal.assurance.runner import run_all
from cal.clock import FixedClock

pytestmark = pytest.mark.integration

CLOCK = FixedClock(1_700_000_500.0)


class TestHistory:
    def test_append_then_load_roundtrips(self, tmp_path):
        path = tmp_path / "history.jsonl"
        for i in range(3):
            append_history(run_all(clock=FixedClock(1_700_000_000.0 + i)), path=path)
        history = load_history(path)
        assert len(history) == 3
        assert all(h["posture_score"] == 100 for h in history)
        assert history[0]["total"] == 16

    def test_load_limit_returns_most_recent(self, tmp_path):
        path = tmp_path / "history.jsonl"
        for i in range(5):
            append_history(run_all(clock=FixedClock(1_700_000_000.0 + i)), path=path)
        assert len(load_history(path, limit=2)) == 2

    def test_missing_history_is_empty(self, tmp_path):
        assert load_history(tmp_path / "nope.jsonl") == []


class TestPrometheus:
    def test_metrics_text_has_expected_gauges(self):
        text = prometheus_metrics(run_all(clock=CLOCK))
        assert "cal_posture_score 100" in text
        assert "cal_controls_total 16" in text
        assert "cal_controls_passing 16" in text
        # Per-control labelled series present.
        assert 'cal_control_pass{control="C-07",severity="critical"} 1' in text
        # Prometheus exposition format: HELP/TYPE headers.
        assert "# TYPE cal_posture_score gauge" in text


class TestMonitoringEndpoints:
    @pytest.fixture
    def client(self):
        return TestClient(create_app())

    def test_metrics_endpoint(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        assert "cal_posture_score" in resp.text

    def test_history_endpoint(self, client):
        resp = client.get("/assurance/history")
        assert resp.status_code == 200
        assert "history" in resp.json()
