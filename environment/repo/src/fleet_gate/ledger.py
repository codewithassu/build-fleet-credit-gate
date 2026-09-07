"""Per-team slot ledger."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SlotState:
    slot_id: str
    team: str
    grant: int
    start_ms: int
    end_ms: int
    consumed: int = 0
    reclaimed: bool = False


@dataclass
class TeamLedger:
    team: str
    tier: str
    available: int = 0
    borrowed: int = 0
    slots: dict[str, SlotState] = field(default_factory=dict)


def can_borrow(tier: str, borrow_cap: int, borrowed: int, need: int) -> bool:
    if tier != "gold" or borrow_cap <= 0 or need <= 0:
        return False
    return borrowed + need <= borrow_cap


def reclaim_amount(grant: int, consumed: int) -> int:
    return max(0, grant - consumed)
