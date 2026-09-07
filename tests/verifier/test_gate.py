"""Behavioral verifier for build-fleet-credit-gate (subprocess only)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

GATE = Path("/app/src/gate.py")
FIXTURES = Path("/tests/verifier/fixtures")
PYTHON = sys.executable


def _run_simulate(events: Path, at_ms: int, env: dict | None = None) -> list[dict]:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "trace.jsonl"
        e = os.environ.copy()
        if env:
            e.update(env)
        proc = subprocess.run(
            [
                PYTHON,
                str(GATE),
                "simulate",
                "--events",
                str(events),
                "--at-ms",
                str(at_ms),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            env=e,
        )
        assert proc.returncode == 0, proc.stderr
        return [json.loads(line) for line in out.read_text().splitlines() if line.strip()]


def _run_resolve(team: str, at_ms: int = 0, env: dict | None = None) -> dict:
    e = os.environ.copy()
    if env:
        e.update(env)
    proc = subprocess.run(
        [PYTHON, str(GATE), "resolve", "--team", team, "--at-ms", str(at_ms)],
        capture_output=True,
        text=True,
        env=e,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_gate_entrypoint_exists():
    assert GATE.is_file()


def test_smoke_script_passes():
    proc = subprocess.run([PYTHON, "/app/data/smoke/run_smoke.py"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_config_precedence_runtime_over_site():
    view = _run_resolve("gamma")
    assert view["default_grant"] == 11
    assert view["borrow_cap"] == 4
    assert view["tier"] == "gold"
    alpha = _run_resolve("alpha")
    assert alpha["tier"] == "bronze"
    assert alpha["grant"] == 10


def test_overlays_inert_by_default():
    view = _run_resolve("gamma")
    assert view["default_grant"] != 3
    assert view["borrow_cap"] != 99
    beta = _run_resolve("beta")
    assert beta["grant"] == 12


def test_overlays_enabled_between_site_and_runtime():
    beta = _run_resolve("beta", env={"SFG_ENABLE_OVERLAYS": "1"})
    assert beta["grant"] == 1
    assert beta["default_grant"] == 11
    assert beta["borrow_cap"] == 4


def test_process_env_outranks_runtime_file():
    view = _run_resolve(
        "beta",
        env={
            "SFG_DEFAULT_GRANT": "99",
            "SFG_BORROW_CAP": "7",
            "SFG_TENANT_BETA_TIER": "gold",
        },
    )
    assert view["default_grant"] == 99
    assert view["borrow_cap"] == 7
    assert view["tier"] == "gold"


def test_simulate_file_order_not_timestamp_order():
    rows = _run_simulate(FIXTURES / "file_order.jsonl", at_ms=600)
    early = next(r for r in rows if r["event_id"] == "early")
    assert early["ok"] is False
    assert early["reason"] == "enqueued"


def test_half_grid_exclusive_end():
    rows = _run_simulate(FIXTURES / "half_grid_window.jsonl", at_ms=300)
    s1 = next(r for r in rows if r["event_id"] == "s1")
    s2 = next(r for r in rows if r["event_id"] == "s2")
    assert s1["ok"] is True
    assert s2["ok"] is False
    assert s2["reason"] == "rejected"


def test_on_grid_inclusive_end():
    rows = _run_simulate(FIXTURES / "on_grid_window.jsonl", at_ms=300)
    s1 = next(r for r in rows if r["event_id"] == "s1")
    s2 = next(r for r in rows if r["event_id"] == "s2")
    assert s1["ok"] is True
    assert s2["ok"] is False


def test_borrow_cap_inclusive_for_gold():
    rows = _run_simulate(FIXTURES / "borrow_cap.jsonl", at_ms=400)
    s4 = next(r for r in rows if r["event_id"] == "s4")
    assert s4["ok"] is True
    assert s4["reason"] == "borrowed"


def test_settlement_drains_waiters_same_turn():
    rows = _run_simulate(FIXTURES / "settle_drain.jsonl", at_ms=501)
    reclaim = [r for r in rows if r["action"] == "reclaim"]
    dequeue = [r for r in rows if r["event_id"] == "w1" and r["action"] == "dequeue"]
    assert reclaim
    assert dequeue
    assert rows.index(reclaim[0]) < rows.index(dequeue[0])


def test_fifo_queue_ignores_tier():
    """Queue drain is FIFO by (enqueue_ms, slot_id); tier must not reorder waiters."""
    rows = _run_simulate(FIXTURES / "fifo_ignore_tier.jsonl", at_ms=51)
    dequeues = [r for r in rows if r["action"] == "dequeue"]
    assert len(dequeues) == 2
    assert dequeues[0]["event_id"] == "t6"
    assert dequeues[1]["event_id"] == "t5"


def test_trace_schema_keys():
    rows = _run_simulate(FIXTURES / "on_grid_window.jsonl", at_ms=300)
    need = {"event_id", "action", "team", "ok", "available_after", "reason"}
    for row in rows:
        assert set(row.keys()) == need
