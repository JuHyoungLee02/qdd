#!/bin/bash
# boost2 extra DAgger collection lane (a second GPU): serve B-D, collect the picked world dirs matching <grep>, stop,
# mark BOOST2_MAIN_COLLECT_DONE (the main chain waits for it before building). usage: dagger_lane.sh <code> <gpu> <N> <grep>
C=$1; G=$2; N=$3; PAT=$4
L=/data/harvest/logs/strip8; O=/data/harvest/out/strip8/boost2
P=/data/harvest/venv_train/bin/python
cd $C; export PYTHONPATH=$C
(bash $C/tools/teach_strip8/vllm.sh $G /data/harvest/out/dist8/merged_b_d-min b2_bdm 8405 0.30 &)
for i in $(seq 120); do curl -s -m 5 http://127.0.0.1:8405/v1/models | grep -q '"id"' && break; sleep 10; done
$P tools/teach_strip8/dagger_pick.py /data/harvest/out/teach_l8d/bundles/b1_phase1_x.json $N | grep -E "$PAT" > $L/boost2_pick_main.txt
while read -r v eps; do
  [ -n "$eps" ] || continue
  bash $C/tools/teach_strip8/isaac.sh $C $G dgm_${v//./} harvest.teach_strip8.run_dagger --qwen-url http://127.0.0.1:8405 \
    --qwen-name b2_bdm --out $O/collect --episodes $eps
done < $L/boost2_pick_main.txt
bash $C/tools/teach_strip8/stop.sh b2_bdm
echo "BOOST2_MAIN_COLLECT_DONE $(date -u +%FT%TZ)" >> $L/lanes.log
