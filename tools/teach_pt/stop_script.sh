#!/bin/bash
# Stop only the bash processes whose argv is exactly `bash <path ending in /$1> ...` (a driver script by name), never
# their children and never this script's own shell (P27 / P70 / P130). usage: stop_script.sh <script file name>
want=$1; me=$$; parent=$PPID
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  { [ "$p" = "$me" ] || [ "$p" = "$parent" ]; } && continue
  mapfile -d '' -t a < $d/cmdline 2>/dev/null || continue
  [ "${a[0]}" = "bash" ] || continue
  case "${a[1]}" in */$want) echo "stop $p ${a[*]:0:3}"; kill $p;; esac
done
