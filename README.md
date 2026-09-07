# Build Fleet Credit Gate — RL Environment

## Executive summary

Agents must repair a containerized **CI build-slot credit gate** whose `simulate`/`resolve` CLI mis-handles layered TOML/env configuration, slot window boundaries, gold-tier borrow ceilings, settlement vs queue-drain ordering, and FIFO waiter scheduling. The verifier runs behavioral subprocess tests against sealed JSONL fixtures (not output grepping). The task is designed so partial fixes pass smoke but fail contract fixtures.

---

## 1. Capability mapping

| Capability | How this environment measures it |
|------------|----------------------------------|
| Repository-level debugging | Bugs span `gate.py`, `fleet_gate/engine.py`, `loader.py`, and `rollout.py` with misleading internal NOTES |
| Config cascade reasoning | `base.toml` → `site.toml` → optional overlays → `runtime.env` → process env; broken code re-pins site overlays |
| Stateful simulation | JSONL event processor with reclaim-before-event semantics and cross-event credit pools |
| Verification discipline | Oracle checks trace rows, ordering, and config resolution — not string patches |

**Practitioner scenario:** Platform SREs operate per-team CI concurrency gates in staging; a canary rollout introduced regressions in config pinning and settlement. Engineers must derive window and borrow rules from worked traces while ignoring stale NOTES.

---

## 2. Environment logic & stochasticity

- **Determinism:** No RNG, wall clock, or network. All state derives from config files, process env, and ordered JSONL events.
- **Isolation:** Docker image pins `python:3.13-slim-bookworm` and `pytest==8.4.1`. Tests run from a temp working directory.
- **Idempotency:** `docker build` + `verify.sh` reproduces broken=0 / oracle=1 locally.

Stochasticity is eliminated by fixed fixtures and integer millisecond timestamps.

---

## 3. Oracle strategy (behavior vs output)

The verifier launches `/app/src/gate.py` as a **subprocess** and inspects:

- Exit codes and JSON stdout for `resolve`
- Parsed JSONL trace rows for `simulate` (`ok`, `reason`, `available_after`, event order)
- Config precedence via `resolve` across teams and `SFG_*` env vars
- Window boundary outcomes on half-grid vs on-grid slot durations
- Borrow inclusivity at cap boundary (`borrowed + need <= borrow_cap` for gold)
- Settlement reclaim triggering same-turn multi-waiter drain in FIFO order

**Behavior over text:** A patch that hardcodes fixture filenames or prints static JSON without running the state machine fails. Smoke only checks schema + one happy path; sealed tests require full engine correctness.

---

## 4. Adversarial analysis (summary)

See `analysis/grader_attacks.md` for three documented attack vectors and mitigations:

1. Modifying files under `/tests/verifier/`
2. Hardcoding trace outputs per fixture basename
3. Disabling borrow/queue paths to satisfy smoke only

Mitigations: tests mounted read-only; behavioral assertions on numeric state; negative fixtures for partial fixes.

---

## 5. Directory layout

```
coding-rl-environment/
├── task/instruction.md          # Agent prompt
├── task/task.yaml               # Metadata
├── environment/Dockerfile       # Pinned runtime
├── environment/repo/            # Broken starting codebase → /app
├── solution/reference_solution/ # Oracle patches
├── tests/verifier/              # Pytest + fixtures
├── analysis/                    # grader_attacks.md, model_runs.md
└── verify.sh                    # Local broken/oracle gate
```

---

## 6. Local validation

```bash
cd coding-rl-environment
./verify.sh
# broken reward=0, oracle reward=1
```

Apply reference fix manually:

```bash
docker build -t fleet-credit-gate:dev -f environment/Dockerfile environment
docker run --rm -v "$PWD/tests:/tests:ro" -v "$PWD/solution:/solution:ro" \
  fleet-credit-gate:dev python3 /solution/reference_solution/apply_fix.py
```

---

## 7. Model evaluation

See `analysis/model_runs.md` for pass@k methodology, expected failure modes, and stump analysis template. **Run two models before submission** and fill observed numbers.

---

## 8. Originality note

Domain and naming are original (build-slot credit gate / `SFG_*` config). Engineering patterns are standard SRE gatekeeping, not copied from public benchmark task text.
