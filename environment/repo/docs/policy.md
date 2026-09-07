# Build fleet credit gate policy

Runtime behavior for the CI build-slot credit gate. Worked captures under
`/app/docs/examples/traces.md` are normative for slot window ends, borrow ceilings,
queue drain order, and settlement arithmetic.

## Configuration layers

Lowest → highest: built-in defaults (`default_grant=10`, `borrow_cap=0`, empty tenants);
`/app/config/base.toml`; `/app/config/site.toml`; optional `/app/config/overlays/*.toml` only
when process `SFG_ENABLE_OVERLAYS` is `1`/`true`/`yes`; `/app/config/runtime.env`
(`KEY=VALUE`, `#` comments); process environment variables beginning with `SFG_`. Overlays,
when enabled, sit after `site.toml` and before `runtime.env`. Scalars replace; `tenants.<id>`
deep-merges field-by-field. After the merge finishes, do not re-apply site or overlay files on
top of runtime or process values (including at the CLI entrypoint).

`SFG_DEFAULT_GRANT` → `default_grant`; `SFG_BORROW_CAP` → `borrow_cap`;
`SFG_TENANT_<ID>_TIER` → `tenants.<lowercase id>.tier`.

## Slots, admission, settlement

Slot window membership and expiry (including whether `end_ms` is inclusive) are defined by
the worked simulate captures under `/app/docs/examples/traces.md`. `simulate` must process
JSONL events in **file order** without reordering by timestamp. At each event timestamp `t`,
settle and drain every slot that expires at `t` **before** emitting any row for events at
`t` (including `spend`/`tick` at that same timestamp).

`reserve` always registers the slot. It credits `grant` (else `default_grant`) into that
team's pool only when the reserve's own timestamp falls inside the active window; out-of-window
reserves leave `available` unchanged. `spend` with `cost` pays from the team pool when
possible; otherwise gold may borrow within the configured ceiling, and other tiers enqueue with
`enqueue_ms` equal to the event timestamp. Exact borrow ceiling behavior and enqueue vs borrow
outcomes are pinned by the worked captures.

Settlement returns unused grant to the team pool without rescaling. Waiters must never spend
credit that settlement still owes to outstanding borrow. Never settle the same `slot_id`
twice. Whenever credit frees (in-window reserve or settlement), drain all payable waiters in
the same `simulate` turn before the next event — fair by arrival `(enqueue_ms, slot_id)`,
ignoring tier. Drain rows use `action=dequeue` and the original waiting `event_id`.

## Trace schema

`simulate` JSONL objects use exactly these keys: `event_id`, `action`, `team`, `ok`,
`available_after`, `reason`.

`tick` events emit one row with `ok=true`, `reason=admitted`, and `available_after` equal to
the current pool balance for the event's team (no credit change). Other `reason` values
include: `admitted`, `borrowed`, `enqueued`, `rejected`, `reclaimed`.
