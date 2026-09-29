#!/bin/bash
# Stop ONLY the dry run's own processes (pitfalls P27 / P70 / P76: no pkill -f, no pattern that matches a shell
# command line). A process is ours when
#   - its argv has "--served-model-name qwen8b_dry" (our vLLM), or
#   - argv[0] is a python and argv has tools/couple_dry/dry_closed.py (outer run / Isaac worker), or
#   - argv has "harvest.runtime.fused_model serve" and its cwd is /data/harvest/code_couple_dry_* (our fused server), or
#   - its environment has IR_INST=couple_dry_<variant> (the Isaac worker chain);
# plus the direct children of those (vLLM EngineCore). SIGTERM, SIGKILL after 20 s for survivors (P57).
me=$$; parent=$PPID
declare -A ours=()
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  { [ "$p" = "$me" ] || [ "$p" = "$parent" ]; } && continue
  mapfile -d '' -t argv < $d/cmdline 2>/dev/null || continue
  [ ${#argv[@]} = 0 ] && continue
  cmd="${argv[*]}"
  hit=0
  case "$cmd" in *"--served-model-name qwen8b_dry"*) hit=1;; esac
  case "${argv[0]}" in *python*) case "$cmd" in *tools/couple_dry/dry_closed.py*) hit=1;; esac;; esac
  case "$cmd" in *"harvest.runtime.fused_model serve"*)
    case "$(readlink $d/cwd 2>/dev/null)" in /data/harvest/code_couple_dry_*) hit=1;; esac;; esac
  if [ $hit = 0 ] && tr '\0' '\n' < $d/environ 2>/dev/null | grep -qx "IR_INST=couple_dry_[a-z]*"; then hit=1; fi
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
