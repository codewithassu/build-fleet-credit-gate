#!/usr/bin/env python3
"""Grade an agent workspace copy of the fleet credit gate."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE = "fleet-credit-gate:dev"


def grade(workspace: Path) -> dict:
    """Build image if needed, copy workspace src into container, run verifier."""
    subprocess.run(
        ["docker", "build", "-t", IMAGE, "-f", str(ROOT / "environment/Dockerfile"), str(ROOT / "environment")],
        check=True,
        capture_output=True,
    )
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "stage"
        shutil.copytree(ROOT / "environment/repo", stage)
        # overlay agent edits (src + config if present)
        agent_src = workspace / "src"
        if agent_src.is_dir():
            shutil.copytree(agent_src, stage / "src", dirs_exist_ok=True)
        agent_cfg = workspace / "config"
        if agent_cfg.is_dir():
            shutil.copytree(agent_cfg, stage / "config", dirs_exist_ok=True)
        proc = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{stage}:/app",
                "-v",
                f"{ROOT / 'tests'}:/tests:ro",
                IMAGE,
                "bash",
                "-c",
                "mkdir -p /logs/verifier && bash /tests/verifier/run.sh; cat /logs/verifier/reward.txt",
            ],
            capture_output=True,
            text=True,
        )
        lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        reward = lines[-1] if lines else "?"
        passed = reward == "1"
        return {
            "passed": passed,
            "reward": reward,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-2000:],
            "exit_code": proc.returncode,
        }


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <workspace_dir>", file=sys.stderr)
        return 2
    result = grade(Path(sys.argv[1]))
    print("PASS" if result["passed"] else "FAIL", "reward=", result["reward"])
    if not result["passed"]:
        print(result["stdout"])
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
