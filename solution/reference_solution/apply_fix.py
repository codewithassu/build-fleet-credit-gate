#!/usr/bin/env python3
"""Install policy-correct gate CLI and patched fleet_gate modules."""

from __future__ import annotations

import shutil
from pathlib import Path

FIXED = Path(__file__).resolve().parent
PATCHES = [
    (FIXED / "gate.py", Path("/app/src/gate.py")),
    (FIXED / "fleet_gate" / "engine.py", Path("/app/src/fleet_gate/engine.py")),
    (FIXED / "fleet_gate" / "loader.py", Path("/app/src/fleet_gate/loader.py")),
]


def main() -> None:
    for src, dst in PATCHES:
        if not src.is_file():
            raise SystemExit(f"missing reference file: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print("installed reference gate.py, fleet_gate/engine.py, fleet_gate/loader.py")


if __name__ == "__main__":
    main()
