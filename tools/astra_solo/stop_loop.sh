#!/bin/bash
# Stop only the full.sh / pilot.sh loop driver (argv[1] ends with tools/astra_solo/full.sh or pilot.sh), so no new
# episode starts; the episode in flight (IR_INST=astra_solo_*) finishes normally. Exact argv match, no pkill -f (P27/P70).
me=$$; parent=$PPID
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  { [ "$p" = "$me" ] || [ "$p" = "$parent" ]; } && continue
  mapfile -d '' -t argv < $d/cmdline 2>/dev/null || continue
  [ ${#argv[@]} -ge 2 ] || continue
  [ "${argv[0]}" = "bash" ] || [ "${argv[0]}" = "/bin/bash" ] || continue
  case "${argv[1]}" in
    */tools/astra_solo/full.sh|*/tools/astra_solo/pilot.sh) echo "stop loop $p: ${argv[*]}"; kill -TERM $p ;;
  esac
done
echo done
