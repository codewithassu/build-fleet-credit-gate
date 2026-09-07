# Grader attack analysis — Build Fleet Credit Gate

Red-team of the verifier and environment. Each vector was attempted against the design and blocked as described.

---

## Attack 1: Modify sealed tests to always pass

**Vector:** Agent edits `/tests/verifier/test_gate.py` or replaces fixtures with trivial expectations.

**Why tempting:** Fastest path if tests are writable.

**Mitigation:**
- Evaluation mounts `tests/` **read-only** (`docker run -v ...:/tests:ro`).
- `run.sh` executes pytest from `mktemp` cwd but loads tests from the read-only mount; agent workspace under `/app` does not include verifier code.
- CI copies tests from submission archive into the container at grade time; agent cannot persist test edits across runs.

**Residual risk:** Host-side cheating outside Docker. Out of scope for in-container RL; submission review checks for test tampering in the repo branch.

---

## Attack 2: Hardcode fixture-specific trace outputs

**Vector:** Patch `gate.py simulate` to detect `--events` path basename and emit pre-baked JSONL matching each fixture.

**Why tempting:** Avoids understanding config cascade and settlement order.

**Mitigation:**
- Tests assert **cross-fixture invariants** (config `resolve` values, numeric `available_after`, ordering indices) not single golden files.
- `test_process_env_outranks_runtime_file` uses dynamic env vars not present in fixture paths.
- `test_simulate_file_order_not_timestamp_order` fails if agent sorts by timestamp (different `reason` / `ok`).
- Negative boundary tests (half-grid vs on-grid) share no single output template.

**Detection:** Add a synthetic fixture with a random `event_id` prefix in hidden evaluation (recommended for production); current public fixtures already vary timestamps and team IDs enough to break naive basename tables.

---

## Attack 3: Smoke-only shortcut (partial implementation)

**Vector:** Make `/app/data/smoke/run_smoke.py` pass while leaving config pinning, FIFO, and settlement bugs in place.

**Why tempting:** Smoke is agent-visible and documents a happy path.

**Mitigation:**
- Verifier always runs sealed pytest module after smoke-equivalent paths.
- Smoke passes on the **broken** starter code today; reward requires full suite.
- Tests cover: overlay gating, env precedence, file-order processing, borrow cap inclusivity, reclaim+drain coupling, FIFO tie-break.

**Example partial fix caught:** Removing `apply_rollout_envelope` alone fixes config tests but still fails FIFO and settlement until engine drain/settlement order is repaired.

---

## Attack 4 (bonus): Import verifier or reference solution

**Vector:** `from apply_fix import ...` or read `/solution` inside agent code.

**Mitigation:**
- Dockerfile does not `COPY solution/` into the agent image.
- Solution is mounted only during oracle validation.
- Tests subprocess the agent CLI; they do not import agent modules (no `importlib` of agent code).

---

## Hardening checklist

- [x] Subprocess-only verification
- [x] Read-only test mount
- [x] Solution excluded from agent image
- [x] Behavioral assertions on state and ordering
- [x] Smoke necessary but not sufficient
- [x] Multiple entangled bugs (no single-line fix)
