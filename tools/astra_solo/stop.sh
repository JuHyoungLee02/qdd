#!/bin/bash
# Stop ONLY the Astra-solo processes (pitfalls P27 / P57 / P70 / P76: no pkill -f, no pattern that can match a shell
# command line). Ours = environment IR_INST=astra_solo_<tag> (the Isaac chain) or argv with
# "--served-model-name qwen8b_solo" (our vLLM), plus their direct children. SIGTERM, SIGKILL after 20 s.
me=$$; parent=$PPID
declare -A ours=()
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  { [ "$p" = "$me" ] || [ "$p" = "$parent" ]; } && continue
  mapfile -d '' -t argv < $d/cmdline 2>/dev/null || continue
  [ ${#argv[@]} = 0 ] && continue
  hit=0
  for ((i = 0; i + 1 < ${#argv[@]}; i++)); do
    [ "${argv[$i]}" = "--served-model-name" ] && [ "${argv[$((i + 1))]}" = "qwen8b_solo" ] && hit=1
  done
  if [ $hit = 0 ] && tr '\0' '\n' < $d/environ 2>/dev/null | grep -qx "IR_INST=astra_solo_[a-z0-9_]*"; then hit=1; fi
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
