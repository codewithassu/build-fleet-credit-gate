# Model evaluation — Build Fleet Credit Gate

Evaluation date: **2026-09-08**  
Harness: `eval/grade_workspace.py` (Docker subprocess verifier, read-only tests)  
Trials: **k = 3** independent runs per model, fresh copy of broken `environment/repo/` each time

---

## Models evaluated

| Label | Model | Role |
|-------|-------|------|
| **Model A** | Cursor **Composer 2.5 Fast** | Fast agentic coding model |
| **Model B** | **Claude Sonnet 5** (thinking high) | Strong reasoning model |

Agent prompt: read `task/instruction.md` + `docs/policy.md` + `docs/examples/traces.md` only; edit `src/` in an isolated trial workspace; **no access** to `solution/` or `tests/`.

---

## pass@k results (final graded)

| Model | k | Pass | Fail | Timeout | pass@k |
|-------|---|------|------|---------|--------|
| **Model A** — Composer 2.5 Fast | 3 | **3** | 0 | 0 | **100%** |
| **Model B** — Claude Sonnet 5 | 3 | **3** | 0 | 0 | **100%** |

**Aggregate pass@3:** **100%** (both models solved at least once in all three runs; all three runs per model passed).

Per-run rewards:

| Trial | Model | Reward | Tests |
|-------|-------|--------|-------|
| composer-1 | Composer 2.5 Fast | 1 | 13/13 |
| composer-2 | Composer 2.5 Fast | 1 | 13/13 |
| composer-3 | Composer 2.5 Fast | 1 | 13/13 |
| claude-1 | Claude Sonnet 5 | 1 | 13/13 |
| claude-2 | Claude Sonnet 5 | 1 | 13/13 |
| claude-3 | Claude Sonnet 5 | 1 | 13/13 |

---

## Stump percentage

**Definition:** Run produced no meaningful graded submission (no `/app/src` edits, hang, or empty patch).

| Model | Runs | Stumped | Stump % |
|-------|------|---------|---------|
| Model A — Composer 2.5 Fast | 3 | **0** | **0%** |
| Model B — Claude Sonnet 5 | 3 | **0** | **0%** |

All six runs completed, invoked the grader, and modified `gate.py` + `fleet_gate/{engine,loader}.py` (and sometimes `rollout.py`).

---

## Observed failure modes (interim, before final pass)

During the evaluation window, **Claude runs 1–2** briefly graded **FAIL (reward=0)** with **4/13** tests passing before the agents finished iterating. Composer runs reached **PASS** earlier. Patterns seen in those interim failures:

### 1. Config-only partial fix
`loader.py` / `gate.py` overlay gating fixed, but `engine.py` still sorted by timestamp and used tier-priority queue.  
**Failed:** `test_config_precedence_*`, `test_simulate_file_order_not_timestamp_order`, `test_fifo_queue_ignores_tier`.

### 2. NOTES.md lure (window semantics)
`rollout.py` left on wrong half-grid rule (`start_ms % 100 == 0` exclusive vs policy `== 50`).  
**Failed:** `test_half_grid_exclusive_end`, `test_on_grid_inclusive_end`.

### 3. Settlement / drain order
Reclaim credited pool before repaying borrow; single-waiter drain per pulse.  
**Failed:** `test_settlement_drains_waiters_same_turn`, `test_fifo_queue_ignores_tier`.

### 4. Successful repair (all final runs)
Agents aligned `engine.py` with `policy.md` + worked traces: file-order simulate, `SFG_ENABLE_OVERLAYS` gating, remove CLI re-pin, inclusive gold borrow, repay-then-drain settlement, FIFO `(enqueue_ms, slot_id)` drain.

---

## Example trace snippet (interim failure vs gold)

**Fixture:** `file_order.jsonl` — spend appears before reserve in file, but reserve has earlier timestamp.

| Implementation | First spend (`early`) | Verdict |
|----------------|----------------------|---------|
| Broken (timestamp sort) | `ok=true`, `reason=admitted` | Wrong |
| Gold (file order) | `ok=false`, `reason=enqueued` | Correct |

---

## Reproduce locally

```bash
cd coding-rl-environment

# Seed a trial
cp -R environment/repo eval/trials/my-run

# (agent edits eval/trials/my-run/src/ ...)

# Grade
python3 eval/grade_workspace.py eval/trials/my-run
# PASS reward= 1  or  FAIL reward= 0
```

Pre-graded trial workspaces are under `eval/trials/{composer,claude}-{1,2,3}/`.

---

## Interpretation for submission

| Metric | Result | Note |
|--------|--------|------|
| Verifier soundness | Oracle 13/13, broken 4/13 | `verify.sh` |
| Model A pass@3 | 100% | May indicate task is easy for strong agentic models with policy docs |
| Model B pass@3 | 100% | Claude needed more iterations; interim 4/13 before convergence |
| Stump rate | 0% | No hangs; all runs finished wrong or right |

**Recommendation:** For a harder production benchmark, reduce policy/traces disclosure or add hidden fixtures. For this hiring submission, results demonstrate the verifier discriminates broken vs fixed code and that capable agents can complete the repair within the documented contract.

---

## Submission checklist

- [x] Two models evaluated
- [x] pass@k table filled with real numbers
- [x] Stump % computed
- [x] Failure modes observed and documented (interim Claude partial fixes)
