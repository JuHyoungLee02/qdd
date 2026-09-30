#!/bin/bash
# Stop ONLY E-CJ processes by environment (no pkill / pattern on a command line, NOW.md §4): COUPLE_JOB=<name>
# (VLA server, lane shells) or IR_INST=strip8_cj_<lane> / strip8_cjv0_<lane>_<variant> (Isaac chains), plus direct
# children. SIGTERM, SIGKILL after 20 s.   usage: stop.sh <name>   (name = COUPLE_JOB value or the IR_INST suffix)
want=$1; [ -z "$want" ] && { echo "usage: stop.sh <name>"; exit 2; }
me=$$; parent=$PPID
declare -A ours=()
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  { [ "$p" = "$me" ] || [ "$p" = "$parent" ]; } && continue
  e=$(tr '\0' '\n' < $d/environ 2>/dev/null) || continue
  echo "$e" | grep -qxE "(COUPLE_JOB=$want|IR_INST=strip8_$want)" && ours[$p]=1
done
for d in /proc/[0-9]*; do
  p=${d#/proc/}; pp=$(awk '{print $4}' $d/stat 2>/dev/null)
  [ -n "$pp" ] && [ -n "${ours[$pp]:-}" ] && [ "$p" != "$me" ] && ours[$p]=1
done
[ ${#ours[@]} = 0 ] && { echo "nothing to stop"; exit 0; }
kill -TERM "${!ours[@]}" 2>/dev/null; sleep 20
for p in "${!ours[@]}"; do [ -d /proc/$p ] && kill -KILL $p 2>/dev/null; done
echo "stopped ${#ours[@]}"
