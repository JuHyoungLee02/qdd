#!/bin/bash
# E-PT Isaac lanes (prereg_pt.md §2, §5.0): each lane runs its jobs one after another on one GPU via isaac.sh.
# usage: lane.sh <code dir> <lane>   lanes: main0 | main1 | x2g1   (GPU from the lane name; logs per job)
C=$1; LANE=$2
I="bash $C/tools/teach_pt/isaac.sh $C"
RC="harvest.teach_pt.run_collect"
CL="harvest.teach_pt.run_closed"
T="/data/harvest/out/teach_pt/closed_truth"
case $LANE in
  main0)
    $I 0 dev_std $RC --split dev --variant standard --seeds 0-19
    $I 0 oodh_082 $RC --split ood_h --variant standard --table-z 0.82 --seeds 0-9
    $I 0 tr_dr_a $RC --split train --variant dr --seeds 20300-20374
    for f in pt nd-xyz nd-est nd-pt; do $I 0 truth_${f}_std $CL --iface $f --model truth --variant standard --seeds 0,1 --out $T; done
    ;;
  main1)
    $I 1 dev_dr $RC --split dev --variant dr --seeds 0-19
    $I 1 oodh_088 $RC --split ood_h --variant standard --table-z 0.88 --seeds 0-9
    $I 1 tr_dr_b $RC --split train --variant dr --seeds 20375-20449
    for f in pt nd-xyz nd-est nd-pt; do $I 1 truth_${f}_dr $CL --iface $f --model truth --variant dr --seeds 0,1 --out $T; done
    ;;
  x2g1)
    $I 1 tr_std $RC --split train --variant standard --seeds 20100-20249
    for z in 0.82 0.88; do for f in v2 pt; do $I 1 truth_${f}_tz$z $CL --iface $f --model truth --table-z $z --seeds 0,1 --out $T; done; done
    ;;
esac
echo "LANE_DONE $LANE $(date -u +%FT%TZ)" >> /data/harvest/logs/teach_pt/lanes.log
