#!/bin/bash
# Local validation: broken repo should fail; reference solution should pass.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
IMAGE="fleet-credit-gate:dev"

docker build -t "$IMAGE" -f "$ROOT/environment/Dockerfile" "$ROOT/environment"

run_tests() {
  local label="$1"
  local apply="${2:-0}"
  echo "=== $label ==="
  docker run --rm \
    -v "$ROOT/tests:/tests:ro" \
    -v "$ROOT/solution:/solution:ro" \
    -e PYTHONPATH=/app/src \
    "$IMAGE" \
    bash -c "
      mkdir -p /logs/verifier
      if [ '$apply' = '1' ]; then python3 /solution/reference_solution/apply_fix.py; fi
      bash /tests/verifier/run.sh || true
      cat /logs/verifier/reward.txt
    "
}

echo "Expect reward 0 (broken):"
broken_reward=$(run_tests "broken" 0 | tail -1)
echo "broken reward=$broken_reward"

echo "Expect reward 1 (oracle):"
oracle_reward=$(run_tests "oracle" 1 | tail -1)
echo "oracle reward=$oracle_reward"

if [ "$broken_reward" != "0" ]; then
  echo "FAIL: broken repo should not pass verifier"
  exit 1
fi
if [ "$oracle_reward" != "1" ]; then
  echo "FAIL: reference solution should pass verifier"
  exit 1
fi
echo "OK: local validation passed"
