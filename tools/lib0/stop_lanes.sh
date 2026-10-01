#!/bin/bash
# Stop E-LIB0 sim lanes of one arm: the lane shells (cmdline "lane.sh <code> <arm> ...", matched on the argv fields, not
# a pattern on our own command line) first, then their children by environment tag LIB0_JOB=lane_<prefix>N; no pkill -f.
# usage: stop_lanes.sh <arm, e.g. Ab> <lane name prefix, e.g. ab>
arm=$1; want=$2; me=$$; parent=$PPID
declare -A sh=() ch=()
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  { [ "$p" = "$me" ] || [ "$p" = "$parent" ]; } && continue
  mapfile -d '' -t a < $d/cmdline 2>/dev/null || continue
  [ "${a[0]}" = bash ] && [ "${a[1]##*/}" = lane.sh ] && [ "${a[3]}" = "$arm" ] && sh[$p]=1
done
[ ${#sh[@]} -gt 0 ] && { echo "lane shells: ${#sh[@]}"; kill -TERM "${!sh[@]}" 2>/dev/null; sleep 2; }
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  tr '\0' '\n' < $d/environ 2>/dev/null | grep -qE "^LIB0_JOB=lane_${want}[0-9]+$" && ch[$p]=1
done
[ ${#ch[@]} -gt 0 ] && { echo "children: ${#ch[@]}"; kill -TERM "${!ch[@]}" 2>/dev/null; sleep 5; for p in "${!ch[@]}"; do [ -d /proc/$p ] && kill -KILL $p 2>/dev/null; done; }
echo done
