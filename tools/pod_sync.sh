#!/bin/bash
# Copy harvest/ + tests/ to the pod via exec tar (kubectl cp times out on large files) and run the suite there.
set -euo pipefail
POD=${POD:-juhyoung-native-7a2a}; NS=p-test2; DST=/data/juhyoung_qdd/code
cd "$(dirname "$0")/.."
tar czf - --exclude=__pycache__ harvest tests tools pytest.ini docs/stage3/prereg.json docs/design/E-first-experiments.md \
  | kubectl -n $NS exec -i $POD -- bash -c "mkdir -p $DST && tar xzf - -C $DST"
kubectl -n $NS exec $POD -- bash -c "cd $DST && PYTHONPATH=/data/juhyoung_qdd/pylib:$DST python3 -m pytest -q -p no:cacheprovider --ignore=tests/test_stereo_metrics.py 2>&1 | tail -3"
