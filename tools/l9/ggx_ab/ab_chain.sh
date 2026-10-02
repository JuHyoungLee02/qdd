#!/bin/bash
# GGX A/B chain on fe08: wait for the A/B objects' GGX generation -> sim test (GPU 5) -> 3 A/B lanes (GPU 5)
# -> bulk GGX generation of every other mesh on the three GGX servers.
B=/data/harvest/l9v2/ggx_int; C=/data/harvest/l9v2/ggx_int_code_600d9b9; AB=$B/ab; GPU=5
ngen() { ps -eo args | awk '/tools\/l9\/ggx_gen.py/ && !/awk/' | wc -l; }
while [ $(ngen) -gt 0 ]; do sleep 30; done
echo "GEN_DONE $(date -u +%FT%TZ) files $(ls /data/harvest/l9v2/grasps_ggx/*/*.npz | wc -l)"
for g in ffw_sg2 franka; do
  ls /data/harvest/l9v2/grasps_ggx/$g/ | grep 'npz$' | sed 's/.npz$//' | grep -xFf $AB/ids.txt > $AB/test_ids_$g.txt
  bash $C/tools/l9/isaac.sh $C $GPU ggxab_gt_$g tools.l9.grasp_test --grip $g --ids $AB/test_ids_$g.txt \
    --grasps /data/harvest/l9v2/grasps_ggx --out /data/harvest/l9v2/tested_ggx --envs 4096 --lowfric --collider auto
  echo "TEST_$g $(date -u +%FT%TZ) $(grep -a '\[gtest\] DONE' /data/harvest/logs/l9/ggxab_gt_$g.log | tail -1)"
done
: > $AB/q.txt
for t in A F; do while read -r l; do j=$(echo $l | awk '{print $4}'); p=$(echo $l | awk '{print $2}')
  echo "rule $p $j" >> $AB/q.txt; echo "ggx $p $j" >> $AB/q.txt; done < $AB/jobs_$t.txt; done
for k in 1 2 3; do nohup bash $B/ab_lane.sh $C $GPU $AB ggxab$k > $AB/lane$k.out 2>&1 & sleep 20; done
echo "LANES_UP $(date -u +%FT%TZ)"
bash $B/ggx_gen_run.sh all /data/harvest/l9v2/grasps_ggx 9
echo "BULK_GEN_UP $(date -u +%FT%TZ)"
