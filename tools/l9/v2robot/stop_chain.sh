#!/bin/bash
# Stop the reach_all.sh chain loop (bash only; a running reach job keeps going -- stop it with stop.sh <tag>).
# Finds the chain by its script path in /proc/*/cmdline (P145: no pkill patterns on a command line).
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  [ "$p" = "$$" ] && continue
  c=$(tr '\0' ' ' < $d/cmdline 2>/dev/null)
  case "$c" in "bash "*tools/l9/v2robot/reach_all.sh*) echo "TERM chain $p: $c"; kill -TERM $p;; esac
done
