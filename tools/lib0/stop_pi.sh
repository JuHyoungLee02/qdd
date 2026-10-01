#!/bin/bash
# Stop ONLY the E-LIB0 pi0.5 servers (environment LIB0_JOB=pi_<arm>, set by serve_pi.sh) and their children; no pkill -f
# (pitfall: patterns match the shell's own command line). SIGTERM, SIGKILL after 20 s.  usage: stop_pi.sh [B|R]  (none = both)
want=${1:-}
me=$$; parent=$PPID
declare -A ours=()
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  { [ "$p" = "$me" ] || [ "$p" = "$parent" ]; } && continue
  env_lines=$(tr '\0' '\n' < $d/environ 2>/dev/null) || continue
  if [ -z "$want" ]; then echo "$env_lines" | grep -qxE "LIB0_JOB=pi_[BR]" && ours[$p]=1
  else echo "$env_lines" | grep -qx "LIB0_JOB=pi_$want" && ours[$p]=1; fi
done
[ ${#ours[@]} = 0 ] && { echo "nothing to stop"; exit 0; }
for p in "${!ours[@]}"; do echo "stop $p: $(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | cut -c1-160)"; done
kill -TERM "${!ours[@]}" 2>/dev/null
sleep 20
for p in "${!ours[@]}"; do [ -d /proc/$p ] && kill -KILL $p 2>/dev/null; done
echo done
