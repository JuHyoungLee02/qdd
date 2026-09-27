#!/bin/bash
# Stop one E-DIST8 open arm on this pod: its dist8_open.sh driver (argv[1] ends in dist8_open.sh and the arm is the
# only arm argument) and the training job of that arm (TEACH_PT_JOB=train_<arm>, via stop.sh). usage: stop_arm.sh <code dir> <arm>
C=$1; A=$2; me=$$
for d in /proc/[0-9]*; do
  p=${d#/proc/}; [ "$p" = "$me" ] && continue
  mapfile -d '' -t a < $d/cmdline 2>/dev/null || continue
  [ "${a[0]}" = "bash" ] || continue
  case "${a[1]}" in */dist8_open.sh) [ "${#a[@]}" = 5 ] && [ "${a[4]}" = "$A" ] && { echo "stop driver $p ($A)"; kill $p; };; esac
done
bash $C/tools/teach_pt/stop.sh train_$A
