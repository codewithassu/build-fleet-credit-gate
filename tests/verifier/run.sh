#!/bin/bash
SAFE_DIR=$(mktemp -d)
cd "$SAFE_DIR"
set +e
python3 -m pytest -rA /tests/verifier/test_gate.py
status=$?
set -e
if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit $status
