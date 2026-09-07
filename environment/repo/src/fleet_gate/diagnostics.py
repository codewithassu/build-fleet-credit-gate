"""Diagnostics helpers."""

from __future__ import annotations


def format_pool_warning(team: str, available: int) -> str:
    return f"team={team} available={available}"
