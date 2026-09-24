#!/bin/bash
# Copy harvest/ tests/ tools/r5 to the pod's R5 code dir (not the shared /data/harvest/code).
cd "$(dirname "$0")/../.."
tar czf - --exclude=__pycache__ harvest tests tools/r5 third_party pytest.ini | \
  kubectl -n p-test2 exec -i juhyoung-native-7a2a -- bash -c "mkdir -p /data/harvest/code_r5cl && tar xzf - -C /data/harvest/code_r5cl && chmod +x /data/harvest/code_r5cl/tools/r5/*.sh && echo synced"
