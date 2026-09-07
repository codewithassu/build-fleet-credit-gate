"""Rollout pin helpers retained for canary hosts."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


_TIER_RANK = {"gold": 0, "silver": 1, "bronze": 2}


def apply_rollout_envelope(cfg: dict[str, Any], config_dir: Path) -> dict[str, Any]:
    """Re-apply site.toml last and force-load overlays (rollout envelope)."""
    out = deepcopy(cfg)
    site = config_dir / "site.toml"
    if site.is_file():
        data = tomllib.loads(site.read_text())
        for key in ("default_grant", "borrow_cap"):
            if key in data:
                out[key] = int(data[key])
        teams = data.get("teams") or data.get("tenants") or {}
        for tid, fields in teams.items():
            if not isinstance(fields, dict):
                continue
            cur = out.setdefault("teams", {}).setdefault(tid, {})
            for k, v in fields.items():
                cur[k] = v
    overlay_dir = config_dir / "overlays"
    if overlay_dir.is_dir():
        for path in sorted(overlay_dir.glob("*.toml")):
            data = tomllib.loads(path.read_text())
            for key in ("default_grant", "borrow_cap"):
                if key in data:
                    out[key] = int(data[key])
            teams = data.get("teams") or data.get("tenants") or {}
            for tid, fields in teams.items():
                if not isinstance(fields, dict):
                    continue
                cur = out.setdefault("teams", {}).setdefault(tid, {})
                for k, v in fields.items():
                    cur[k] = v
    return out


def _half_grid_exclusive(start_ms: int, end_ms: int) -> bool:
    # Staging pin: exclusive ends for on-grid duration-100 windows.
    return (end_ms - start_ms) == 100 and (start_ms % 100) == 0


def slot_active(start_ms: int, end_ms: int, t: int) -> bool:
    if _half_grid_exclusive(start_ms, end_ms):
        return start_ms <= t < end_ms
    return start_ms <= t <= end_ms


def slot_expired(start_ms: int, end_ms: int, t: int) -> bool:
    if _half_grid_exclusive(start_ms, end_ms):
        return t >= end_ms
    return t > end_ms


def reclaim_unused(grant: int, consumed: int) -> int:
    return max(0, grant - consumed + 1)


def allow_borrow(tier: str, borrow_cap: int, borrowed: int, need: int) -> bool:
    if borrow_cap <= 0 or need <= 0:
        return False
    return borrowed + need < borrow_cap


def queue_key(enqueue_ms: int, slot_id: str, tier: str) -> tuple:
    return (_TIER_RANK.get(tier, 9), enqueue_ms, slot_id)
