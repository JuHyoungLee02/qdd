#!/bin/bash
# Stop E-M35CL controller shells (lane.sh / serve.sh / merge.sh bash processes) of one code copy, leaving their Isaac
# runners and vLLM servers alone (P27: the pattern lives in this file, never on a command line; self and parent skipped).
# usage: stop_shells.sh <code dir> <lane|serve|merge>
D=$1; K=$2; me=$$; parent=$PPID
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  { [ "$p" = "$me" ] || [ "$p" = "$parent" ]; } && continue
  c=$(tr '\0' ' ' < $d/cmdline 2>/dev/null) || continue
  case "$c" in "bash $D/tools/main35_closed/$K.sh "*) echo "stop $p: $c"; kill -TERM $p;; esac
done
