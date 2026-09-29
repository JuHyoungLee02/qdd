#!/bin/bash
# Copy harvest/ tests/ tools/ third_party to the pod's pre-R7 code dir (default /data/harvest/code_pre_r7, DEST=... for a
# frozen copy used by a long run; never the shared code dirs of other agents) and write CODE_VERSION (git HEAD + dirty).
cd "$(dirname "$0")/../.."
DEST=${DEST:-/data/harvest/code_pre_r7}
C=$(git -c safe.directory="$(pwd)" rev-parse HEAD 2>/dev/null)
D=$(git -c safe.directory="$(pwd)" status --porcelain 2>/dev/null | wc -l)
DIRTY=false; [ "$D" -gt 0 ] && DIRTY=true
V="{\"commit\": \"$C\", \"dirty\": $DIRTY, \"dirty_files\": $D, \"synced_utc\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
tar czf - --exclude=__pycache__ harvest tests tools third_party pytest.ini | \
  kubectl -n p-test2 exec -i juhyoung-native-7a2a -- bash -c "mkdir -p $DEST && tar xzf - -C $DEST && echo '$V' > $DEST/CODE_VERSION && chmod +x $DEST/tools/*/*.sh && echo synced $DEST \$(cat $DEST/CODE_VERSION)"
