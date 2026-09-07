#!/usr/bin/env python3
"""Weak agent-visible smoke: schema + happy-path mid-window admit."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

EVENTS = """\
{"event_id":"e1","action":"reserve","team":"beta","slot_id":"S1","ts":100,"start_ms":100,"end_ms":500,"grant":12}
{"event_id":"e2","action":"spend","team":"beta","slot_id":"S1","ts":200,"cost":3}
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        ev = Path(td) / "events.jsonl"
        out = Path(td) / "trace.jsonl"
        ev.write_text(EVENTS)
        proc = subprocess.run(
            [
                sys.executable,
                "/app/src/gate.py",
                "simulate",
                "--events",
                str(ev),
                "--at-ms",
                "200",
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(proc.stderr)
            return 1
        rows = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
        need = {"event_id", "action", "team", "ok", "available_after", "reason"}
        for row in rows:
            if not need.issubset(row):
                print("missing keys", row)
                return 1
        if not any(r["event_id"] == "e2" and r["ok"] is True for r in rows):
            print("spend not admitted")
            return 1
        print("smoke ok", len(rows))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
