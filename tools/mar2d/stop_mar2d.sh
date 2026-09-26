#!/bin/bash
# Stop ONLY this job's processes (P27/P70: no pkill -f): worker.sh whose argv is exactly "/bin/bash ./worker.sh ..."
# with a job file under /data/harvest/mar2d, and every process whose environ has IR_INST=mar2d_<one of the tags>.
# usage: ./stop_mar2d.sh [--kill]      (without --kill: list only)
TAGS="mar2d_p_wpS mar2d_p_wpD mar2d_gC_gdefS"
ME=$$
pids=""
for p in /proc/[0-9]*; do
  pid=${p#/proc/}
  [ "$pid" = "$ME" ] && continue
  args=$(tr '\0' ' ' < $p/cmdline 2>/dev/null)
  case "$args" in "/bin/bash ./worker.sh "*" /data/harvest/mar2d/jobs_"*) pids="$pids $pid"; echo "worker $pid: $args"; continue ;; esac
  env=$(tr '\0' '\n' < $p/environ 2>/dev/null | grep '^IR_INST=')
  for t in $TAGS; do
    if [ "$env" = "IR_INST=$t" ]; then pids="$pids $pid"; echo "$t $pid: ${args:0:120}"; fi
  done
done
if [ "${1:-}" = "--kill" ] && [ -n "$pids" ]; then
  kill -TERM $pids 2>/dev/null; sleep 5
  for pid in $pids; do [ -d /proc/$pid ] && kill -KILL $pid 2>/dev/null && echo "SIGKILL $pid"; done
fi
echo "listed:$pids"
