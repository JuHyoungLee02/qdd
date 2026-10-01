#!/bin/bash
# E-HCAM8: stop earlier row builds of <tag>, then build the L9 rows of <episodes.json> in <n> parallel parts and merge.
# usage: hcam8_rows_par.sh <code dir> <episodes.json> <out dir> <tag> <n> [--camera-line]
# (process matching by /proc/<pid>/cmdline inside this file, never by a pattern on the calling command line)
C=$1; EPS=$2; OUT=$3; TAG=$4; N=$5; CL=$6
P=/data/harvest/venv_train/bin/python
for p in /proc/[0-9]*; do
  cmd=$(tr '\0' ' ' < $p/cmdline 2>/dev/null) || continue
  case "$cmd" in *hcam8_build.py\ rows*" $TAG "*) kill ${p#/proc/} 2>/dev/null;; esac
done
sleep 2
rm -rf $OUT; mkdir -p $OUT
cd $C
pids=""
for k in $(seq 0 $((N - 1))); do
  PYTHONPATH=$C $P tools/l9r/hcam8_build.py rows $EPS $OUT $TAG --part $k/$N $CL > $OUT/rows_p$k.log 2>&1 < /dev/null &
  pids="$pids $!"
done
fail=0
for p in $pids; do wait $p || fail=1; done
[ $fail = 0 ] || { echo "PARTS_FAIL $(date -u +%FT%TZ)" >> $OUT/rows.log; exit 1; }
PYTHONPATH=$C $P tools/l9r/hcam8_build.py merge $OUT $TAG $N $CL >> $OUT/rows.log 2>&1 && echo "ROWS_DONE $(date -u +%FT%TZ)" >> $OUT/rows.log
