# Build fleet credit gate repair

The CI build-slot credit gate under `/app/src/` admits pipeline work against per-team credit pools using layered configuration. Behavior is incorrect on several interacting paths. Repair the implementation in place (do not rewrite from an unrelated design). Configuration under `/app/config/` may be adjusted only when required for correct policy behavior.

Behavior contract: `/app/docs/policy.md` (including documents it incorporates by reference).

## Entry point

```bash
python3 /app/src/gate.py simulate --events /path/to/events.jsonl --at-ms <t> --out /app/output/trace.jsonl
python3 /app/src/gate.py resolve --team <id> --at-ms <t>
```

`simulate` processes events in file order and writes JSON lines to `--out` (create parent dirs). `resolve` prints one JSON object to stdout for the effective team view at `at-ms`.

Implement `simulate`/`resolve` so they match the behavior contract on config layering, slot windows, credits/reclaim, borrow, queue drain, and trace schema.

## Agent-visible checks

```bash
python3 /app/data/smoke/run_smoke.py
```

Smoke is necessary but not sufficient. Sealed verifier fixtures grade full contract compliance.

## Deliverable

Fixed sources under `/app/src/` (and config under `/app/config/` if needed) so contract-compliant `simulate`/`resolve` behavior holds.
