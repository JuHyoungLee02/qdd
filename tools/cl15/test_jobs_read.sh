#!/bin/bash
# CPU check of the lane job loop (bug 10-01: the Isaac child read the loop's stdin = jobs.txt, so the next job ids
# lost their first bytes, e.g. eps__side_table__ov_behind.json). Same loop shape as lane.sh, with a child that eats
# stdin (head -c 40) in place of Isaac: every job id must map to an existing eps file. Also shows the old shape fails.
# usage: test_jobs_read.sh <root> [jobs file]
R=$1; J=${2:-$R/jobs.txt}; ok=1
while IFS=$'\t' read -r -u 3 GID JOB; do
  head -c 40 > /dev/null < /dev/null
  if [ -f $R/eps_$GID.json ]; then echo "found eps_$GID.json"; else echo "MISSING eps_$GID.json"; ok=0; fi
done 3< $J
old=0
while IFS=$'\t' read -r GID JOB; do
  head -c 40 > /dev/null
  [ -f $R/eps_$GID.json ] || old=$((old + 1))
done < $J
echo "old loop shape: $old missing (expected > 0 when there are >= 2 jobs)"
[ $ok = 1 ] && echo PASS || { echo FAIL; exit 1; }
