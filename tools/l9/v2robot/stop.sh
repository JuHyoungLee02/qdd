#!/bin/bash
# Stop MY job only: processes whose environment has IR_INST=l9v2robot_<tag> (P143/P145: no pkill patterns).
# SIGTERM, then SIGKILL after 30 s for what is left (P149). usage: stop.sh <tag>
TAG=$1
[ -n "$TAG" ] || { echo "usage: stop.sh <tag>"; exit 1; }
find_pids() {
  for d in /proc/[0-9]*; do
    p=${d#/proc/}
    [ "$p" = "$$" ] && continue
    tr '\0' '\n' < $d/environ 2>/dev/null | grep -qx "IR_INST=l9v2robot_$TAG" && echo $p
  done
}
P=$(find_pids)
[ -n "$P" ] || { echo "no process for l9v2robot_$TAG"; exit 0; }
echo "TERM $P"; kill -TERM $P 2>/dev/null
for i in $(seq 30); do sleep 1; P=$(find_pids); [ -z "$P" ] && { echo stopped; exit 0; }; done
echo "KILL $P"; kill -KILL $P 2>/dev/null
