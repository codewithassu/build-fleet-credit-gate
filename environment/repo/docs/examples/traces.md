# Worked traces (normative)

## Half-grid window (duration 100, start_ms % 100 == 50)

Exclusive end: active when `start_ms <= t < end_ms`; expires when `t >= end_ms`.

```
reserve slot S1 team beta start=150 end=250 ts=150 grant=10
spend  cost 4 at ts=200 inside window -> admitted, available 6
spend  cost 1 at ts=250 at end boundary -> rejected (exclusive end)
```

## On-grid window (duration 100, start_ms % 100 == 0)

Closed-closed: active when `start_ms <= t <= end_ms`; expires when `t > end_ms`.

```
reserve slot S2 team beta start=100 end=200 ts=100 grant=10
spend  cost 3 at ts=200 at end -> admitted
spend  cost 1 at ts=201 after end -> rejected
```

## Gold borrow (inclusive cap)

With `borrow_cap=4`, gold may borrow while `borrowed + need <= borrow_cap`.

```
reserve + spend leaving borrowed=3; further spend need=1 -> borrowed (total 4)
further spend need=1 -> enqueued (would exceed cap)
```

## Settlement + drain order

On reclaim, repay outstanding borrow from returned credit first; credit the remainder to
`available`, then drain FIFO waiters in the same turn.

```
Team gold: borrowed=2, waiter enqueue_ms=500 slot_id=W1 cost=3
Reclaim returns 5 -> repay 2, available=3 -> dequeue W1 (available=0)
```

## FIFO queue (ignore tier)

Two waiters: silver at 100, gold at 200 — silver dequeues first regardless of tier.
