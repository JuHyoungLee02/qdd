#!/bin/bash
# Start E-JV1 eval lanes on ONE approved render card of THIS pod (docs/stage3/prereg_jv1.md §8; user approval needed:
# the render cards belong to L9 production). Needs out/jv1/eval/READY_FOR_LANES (chain_eval.sh).
# usage: bash start_lanes.sh <code dir> <gpu> <n lanes>     stop: touch out/jv1/eval/lanes/<lane>.WANTED
C=$1; G=$2; N=${3:-4}
E=/data/harvest/out/jv1/eval
[ -f $E/READY_FOR_LANES ] || { echo "not ready: $E/READY_FOR_LANES missing"; exit 1; }
case "$(hostname)" in *x2*) T=x2;; *x3*) T=x3;; *) T=7a2a;; esac
for i in $(seq $N); do
  LN=jv1_${T}_g${G}_$i
  nohup bash $C/tools/jv1/lane_eval.sh $C $G $LN > /dev/null 2>&1 &
  echo "lane $LN started"; sleep 20
done
echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | JV1 | lanes x$N on $T:$G" >> /data/harvest/out/jv1/events.log
