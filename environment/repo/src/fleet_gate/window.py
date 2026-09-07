"""Slot window helpers."""

from __future__ import annotations


def _half_grid_exclusive(start_ms: int, end_ms: int) -> bool:
    return (end_ms - start_ms) == 100 and (start_ms % 100) == 50


def slot_active(start_ms: int, end_ms: int, t: int) -> bool:
    if _half_grid_exclusive(start_ms, end_ms):
        return start_ms <= t < end_ms
    return start_ms <= t <= end_ms


def slot_expired(start_ms: int, end_ms: int, t: int) -> bool:
    if _half_grid_exclusive(start_ms, end_ms):
        return t >= end_ms
    return t > end_ms
