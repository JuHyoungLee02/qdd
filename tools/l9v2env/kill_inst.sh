#!/bin/bash
# kill my Isaac process(es) whose environment has IR_INST=$1 (P143 / P151: SIGTERM, 15 s, then SIGKILL)
want="IR_INST=$1"
pids=""
for d in /proc/[0-9]*; do
  if tr '\0' '\n' < $d/environ 2>/dev/null | grep -qx "$want"; then
    c=$(tr '\0' ' ' < $d/cmdline 2>/dev/null)
    case "$c" in *kit/python*) pids="$pids ${d#/proc/}";; esac
  fi
done
echo "pids:$pids"
[ -z "$pids" ] && exit 0
kill -TERM $pids 2>/dev/null; sleep 15
for p in $pids; do [ -d /proc/$p ] && { echo "KILL $p"; kill -KILL $p; }; done
