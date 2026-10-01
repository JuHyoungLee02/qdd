#!/bin/bash
# Stop E-SIM0 lanes of one arm: lane shells (argv: bash .../tools/sim0/lane.sh <code> <arm> ...) then children by the
# environment tag LIB0_JOB=simlane_<prefix>N; no pkill -f.  usage: stop_lanes.sh <arm A|B> <lane prefix sa|sb>
arm=$1; want=$2; me=$$; parent=$PPID
declare -A sh=() ch=()
for d in /proc/[0-9]*; do
  p=${d#/proc/}; { [ "$p" = "$me" ] || [ "$p" = "$parent" ]; } && continue
  mapfile -d '' -t a < $d/cmdline 2>/dev/null || continue
  [ "${a[0]}" = bash ] && [[ "${a[1]}" == */tools/sim0/lane.sh ]] && [ "${a[3]}" = "$arm" ] && sh[$p]=1
done
[ ${#sh[@]} -gt 0 ] && { echo "lane shells: ${#sh[@]}"; kill -TERM "${!sh[@]}" 2>/dev/null; sleep 2; }
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  tr '\0' '\n' < $d/environ 2>/dev/null | grep -qE "^LIB0_JOB=simlane_${want}[0-9]+$" && ch[$p]=1
done
[ ${#ch[@]} -gt 0 ] && { echo "children: ${#ch[@]}"; kill -TERM "${!ch[@]}" 2>/dev/null; sleep 5; for p in "${!ch[@]}"; do [ -d /proc/$p ] && kill -KILL $p 2>/dev/null; done; }
echo done
