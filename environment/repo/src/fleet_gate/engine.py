"""Gate simulation engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fleet_gate.diagnostics import format_pool_warning
from fleet_gate.ledger import SlotState, TeamLedger
from fleet_gate.rollout import (
    allow_borrow,
    apply_rollout_envelope,
    queue_key,
    reclaim_unused,
    slot_active,
    slot_expired,
)
from fleet_gate.scheduler import WaitItem


class GateEngine:
    def __init__(self, cfg: dict[str, Any], config_dir: Path | None = None):
        root = config_dir or Path("/app/config")
        self.cfg = apply_rollout_envelope(cfg, root)
        self.ledgers: dict[str, TeamLedger] = {}
        self.queue: list[WaitItem] = []
        self._warn = format_pool_warning

    def _team_meta(self, team: str) -> dict[str, Any]:
        return dict(self.cfg.get("teams", {}).get(team, {}))

    def _ledger(self, team: str) -> TeamLedger:
        if team not in self.ledgers:
            meta = self._team_meta(team)
            self.ledgers[team] = TeamLedger(
                team=team,
                tier=str(meta.get("tier", "bronze")),
            )
        else:
            meta = self._team_meta(team)
            if "tier" in meta:
                self.ledgers[team].tier = str(meta["tier"])
        return self.ledgers[team]

    def resolve_team(self, team: str, at_ms: int) -> dict[str, Any]:
        meta = self._team_meta(team)
        led = self._ledger(team)
        return {
            "team": team,
            "tier": led.tier if led.tier else meta.get("tier", "bronze"),
            "default_grant": int(self.cfg.get("default_grant", 10)),
            "borrow_cap": int(self.cfg.get("borrow_cap", 0)),
            "grant": int(meta.get("grant", self.cfg.get("default_grant", 10))),
            "available": led.available,
            "borrowed": led.borrowed,
            "at_ms": at_ms,
        }

    def _reserve_slot(self, ev: dict[str, Any]) -> dict[str, Any]:
        team = ev["team"]
        slot_id = ev["slot_id"]
        meta = self._team_meta(team)
        grant = int(ev.get("grant", meta.get("grant", self.cfg.get("default_grant", 10))))
        led = self._ledger(team)
        st = SlotState(
            slot_id=slot_id,
            team=team,
            grant=grant,
            start_ms=int(ev["start_ms"]),
            end_ms=int(ev["end_ms"]),
        )
        led.slots[slot_id] = st
        led.available += grant
        return self._row(ev, True, led.available, "admitted")

    def _reclaim_due(self, t: int) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for led in self.ledgers.values():
            for st in list(led.slots.values()):
                if st.reclaimed:
                    continue
                if not slot_expired(st.start_ms, st.end_ms, t):
                    continue
                amt = reclaim_unused(st.grant, st.consumed)
                credit = amt
                led.available += credit
                st.reclaimed = True
                rows.append(
                    {
                        "event_id": f"reclaim:{st.slot_id}",
                        "action": "reclaim",
                        "team": led.team,
                        "ok": True,
                        "available_after": led.available,
                        "reason": "reclaimed",
                    }
                )
                rows.extend(self._drain_queue(t))
                repay = min(led.borrowed, amt)
                led.borrowed -= repay
                led.available = max(0, led.available - repay)
        return rows

    def _drain_queue(self, t: int) -> list[dict[str, Any]]:
        del t
        rows: list[dict[str, Any]] = []
        self.queue.sort(key=lambda it: queue_key(it.enqueue_ms, it.slot_id, it.tier))
        remaining: list[WaitItem] = []
        drained = False
        for item in self.queue:
            led = self._ledger(item.team)
            if not drained and led.available >= item.cost:
                led.available -= item.cost
                if item.slot_id in led.slots:
                    led.slots[item.slot_id].consumed += item.cost
                rows.append(
                    {
                        "event_id": item.event_id,
                        "action": "dequeue",
                        "team": item.team,
                        "ok": True,
                        "available_after": led.available,
                        "reason": "admitted",
                    }
                )
                drained = True
            else:
                remaining.append(item)
        self.queue = remaining
        return rows

    def _spend(self, ev: dict[str, Any]) -> dict[str, Any]:
        team = ev["team"]
        cost = int(ev["cost"])
        slot_id = ev.get("slot_id", ev["event_id"])
        led = self._ledger(team)
        cap = int(self.cfg.get("borrow_cap", 0))
        if led.available >= cost:
            led.available -= cost
            if slot_id in led.slots:
                led.slots[slot_id].consumed += cost
            return self._row(ev, True, led.available, "admitted")
        need = cost - led.available
        if allow_borrow(led.tier, cap, led.borrowed, need):
            if led.available:
                if slot_id in led.slots:
                    led.slots[slot_id].consumed += led.available
                led.available = 0
            led.borrowed += need
            if slot_id in led.slots:
                led.slots[slot_id].consumed += need
            return self._row(ev, True, led.available, "borrowed")
        self.queue.append(
            WaitItem(
                slot_id=slot_id,
                team=team,
                cost=cost,
                enqueue_ms=int(ev["ts"]),
                event_id=ev["event_id"],
                tier=led.tier,
            )
        )
        _ = self._warn(team, led.available)
        return self._row(ev, False, led.available, "enqueued")

    @staticmethod
    def _row(ev: dict[str, Any], ok: bool, available: int, reason: str) -> dict[str, Any]:
        return {
            "event_id": ev["event_id"],
            "action": ev["action"],
            "team": ev.get("team", ""),
            "ok": ok,
            "available_after": available,
            "reason": reason,
        }

    def simulate(self, events: list[dict[str, Any]], at_ms: int | None = None) -> list[dict[str, Any]]:
        trace: list[dict[str, Any]] = []
        for tid in self.cfg.get("teams", {}):
            self._ledger(tid)
        ordered = sorted(events, key=lambda e: (int(e["ts"]), str(e.get("event_id", ""))))
        for ev in ordered:
            t = int(ev["ts"])
            trace.extend(self._reclaim_due(t))
            action = ev["action"]
            if action == "reserve":
                trace.append(self._reserve_slot(ev))
            elif action == "spend":
                sid = ev.get("slot_id")
                led = self._ledger(ev["team"])
                if sid and sid in led.slots:
                    st = led.slots[sid]
                    if not slot_active(st.start_ms, st.end_ms, t):
                        trace.append(self._row(ev, False, led.available, "rejected"))
                        continue
                trace.append(self._spend(ev))
            elif action == "tick":
                trace.append(
                    self._row(ev, True, self._ledger(ev.get("team", "alpha")).available, "admitted")
                )
            else:
                trace.append(self._row(ev, False, 0, "rejected"))
        end_t = at_ms if at_ms is not None else (ordered[-1]["ts"] if ordered else 0)
        trace.extend(self._reclaim_due(int(end_t)))
        return trace
