#!/usr/bin/env python3
"""CLI entry for the build fleet credit gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fleet_gate.engine import GateEngine  # noqa: E402
from fleet_gate.loader import load_effective_config  # noqa: E402
from fleet_gate.rollout import apply_rollout_envelope  # noqa: E402


def _load_cfg() -> dict:
    root = Path("/app/config")
    cfg = load_effective_config(root)
    return apply_rollout_envelope(cfg, root)


def _cmd_resolve(args: argparse.Namespace) -> int:
    cfg = _load_cfg()
    eng = GateEngine(cfg, config_dir=Path("/app/config"))
    view = eng.resolve_team(args.team, args.at_ms)
    print(json.dumps(view, sort_keys=True))
    return 0


def _cmd_simulate(args: argparse.Namespace) -> int:
    cfg = _load_cfg()
    eng = GateEngine(cfg, config_dir=Path("/app/config"))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    events_path = Path(args.events)
    lines = []
    with events_path.open() as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            lines.append(json.loads(raw))
    trace = eng.simulate(lines, at_ms=args.at_ms)
    with out.open("w") as fh:
        for row in trace:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gate")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("resolve")
    r.add_argument("--team", required=True)
    r.add_argument("--at-ms", type=int, required=True)
    r.set_defaults(func=_cmd_resolve)

    s = sub.add_parser("simulate")
    s.add_argument("--events", required=True)
    s.add_argument("--at-ms", type=int, required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(func=_cmd_simulate)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
