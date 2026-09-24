#!/bin/bash
# Copy harvest/ tests/ tools/ third_party to the pod's R6 code dir (/data/harvest/code_r6, not the shared code dirs)
# and write CODE_VERSION (local git HEAD + dirty flag) so every R6 output records the commit it ran.
cd "$(dirname "$0")/../.."
C=$(git -c safe.directory="$(pwd)" rev-parse HEAD 2>/dev/null)
D=$(git -c safe.directory="$(pwd)" status --porcelain 2>/dev/null | wc -l)
DIRTY=false; [ "$D" -gt 0 ] && DIRTY=true
V="{\"commit\": \"$C\", \"dirty\": $DIRTY, \"dirty_files\": $D, \"synced_utc\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
tar czf - --exclude=__pycache__ harvest tests tools third_party pytest.ini | \
  kubectl -n p-test2 exec -i juhyoung-native-7a2a -- bash -c "mkdir -p /data/harvest/code_r6 && tar xzf - -C /data/harvest/code_r6 && echo '$V' > /data/harvest/code_r6/CODE_VERSION && chmod +x /data/harvest/code_r6/tools/r6/*.sh && echo synced \$(cat /data/harvest/code_r6/CODE_VERSION)"
