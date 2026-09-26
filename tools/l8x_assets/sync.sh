#!/bin/bash
# L8X-assets: copy the working tree's harvest/ tests/ tools/ third_party/ to the pod dev copy (exec tar, no kubectl cp).
# usage (Git Bash, repo root): MSYS_NO_PATHCONV=1 tools/l8x_assets/sync.sh [pod] [dst]
set -euo pipefail
POD=${1:-juhyoung-native-7a2a}; DST=${2:-/data/harvest/code_l8x_assets_dev}
cd "$(dirname "$0")/../.."
tar czf - --exclude=__pycache__ harvest tests tools third_party pytest.ini \
  | kubectl -n p-test2 exec -i $POD -- bash -c "mkdir -p $DST && tar xzf - -C $DST"
echo "synced -> $POD:$DST"
