#!/bin/bash
# Stop ONLY the E-TEACH-L8 processes (pitfalls P27 / P57 / P70 / P76: no pkill -f, no pattern that can match a shell
# command line). Ours = environment IR_INST=teach_l8_<tag> (Isaac chain) or TEACH_L8_JOB=<name> (training / eval /
# vLLM, set by our launchers), plus their direct children. SIGTERM, SIGKILL after 20 s.
# usage: stop.sh [job name]   (no argument = all of ours)
want=${1:-}
me=$$; parent=$PPID
declare -A ours=()
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  { [ "$p" = "$me" ] || [ "$p" = "$parent" ]; } && continue
  env_lines=$(tr '\0' '\n' < $d/environ 2>/dev/null) || continue
  hit=0
  if [ -z "$want" ]; then
    echo "$env_lines" | grep -qE "^(IR_INST=teach_l8_[a-z0-9_]+|TEACH_L8_JOB=[a-z0-9_]+)$" && hit=1
  else
    echo "$env_lines" | grep -qxE "(IR_INST=teach_l8_$want|TEACH_L8_JOB=$want)" && hit=1
  fi
  [ $hit = 1 ] && ours[$p]=1
done
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  pp=$(awk '{print $4}' $d/stat 2>/dev/null)
  [ -n "$pp" ] && [ -n "${ours[$pp]:-}" ] && [ "$p" != "$me" ] && ours[$p]=1
done
[ ${#ours[@]} = 0 ] && { echo "nothing to stop"; exit 0; }
for p in "${!ours[@]}"; do echo "stop $p: $(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | cut -c1-160)"; done
kill -TERM "${!ours[@]}" 2>/dev/null
sleep 20
for p in "${!ours[@]}"; do
  [ -d /proc/$p ] && { echo "kill -9 $p"; kill -KILL $p 2>/dev/null; }
done
echo done
