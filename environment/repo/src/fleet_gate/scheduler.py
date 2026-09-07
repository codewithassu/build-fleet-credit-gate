"""Wait queue items."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WaitItem:
    slot_id: str
    team: str
    cost: int
    enqueue_ms: int
    event_id: str
    tier: str


def wait_sort_key(item: WaitItem) -> tuple:
    return (item.enqueue_ms, item.slot_id)
