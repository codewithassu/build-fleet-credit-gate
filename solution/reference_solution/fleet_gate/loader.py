"""Layered configuration loader (policy-correct)."""

from __future__ import annotations

import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


_DEFAULTS: dict[str, Any] = {
    "default_grant": 10,
    "borrow_cap": 0,
    "teams": {},
}


def _deep_merge_teams(dst: dict[str, Any], src: dict[str, Any]) -> None:
    for tid, fields in src.items():
        if tid not in dst:
            dst[tid] = {}
        if not isinstance(fields, dict):
            continue
        for k, v in fields.items():
            dst[tid][k] = v


def _apply_toml(cfg: dict[str, Any], path: Path) -> None:
    if not path.is_file():
        return
    data = tomllib.loads(path.read_text())
    for key in ("default_grant", "borrow_cap"):
        if key in data:
            cfg[key] = int(data[key])
    teams = data.get("teams") or data.get("tenants") or {}
    if isinstance(teams, dict):
        _deep_merge_teams(cfg["teams"], teams)


def _apply_env_file(cfg: dict[str, Any], path: Path) -> None:
    if not path.is_file():
        return
    mapping: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        mapping[k.strip()] = v.strip()
    _apply_sfg_mapping(cfg, mapping)


def _apply_sfg_mapping(cfg: dict[str, Any], mapping: dict[str, str]) -> None:
    if "SFG_DEFAULT_GRANT" in mapping:
        cfg["default_grant"] = int(mapping["SFG_DEFAULT_GRANT"])
    if "SFG_BORROW_CAP" in mapping:
        cfg["borrow_cap"] = int(mapping["SFG_BORROW_CAP"])
    pat = re.compile(r"^SFG_TENANT_([A-Z0-9]+)_TIER$")
    for k, v in mapping.items():
        m = pat.match(k)
        if not m:
            continue
        tid = m.group(1).lower()
        cfg["teams"].setdefault(tid, {})
        cfg["teams"][tid]["tier"] = v.strip().lower()


def _apply_process_env(cfg: dict[str, Any]) -> None:
    sfg = {k: v for k, v in os.environ.items() if k.startswith("SFG_")}
    _apply_sfg_mapping(cfg, sfg)


def _apply_overlays(cfg: dict[str, Any], config_dir: Path) -> None:
    overlay_dir = config_dir / "overlays"
    if not overlay_dir.is_dir():
        return
    for path in sorted(overlay_dir.glob("*.toml")):
        _apply_toml(cfg, path)


def _overlays_enabled() -> bool:
    val = os.environ.get("SFG_ENABLE_OVERLAYS", "").strip().lower()
    return val in ("1", "true", "yes")


def load_effective_config(config_dir: Path) -> dict[str, Any]:
    """Merge config layers for the gate."""
    cfg = deepcopy(_DEFAULTS)
    cfg["teams"] = {}
    _apply_toml(cfg, config_dir / "base.toml")
    _apply_toml(cfg, config_dir / "site.toml")
    if _overlays_enabled():
        _apply_overlays(cfg, config_dir)
    _apply_env_file(cfg, config_dir / "runtime.env")
    _apply_process_env(cfg)
    return cfg
