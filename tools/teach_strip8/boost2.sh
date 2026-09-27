#!/bin/bash
# boost2 chain (prereg_boost2.md), all on one GPU <g> of the pod it runs on (Isaac + vLLM + training):
# 1 serve B-D -> DAgger collection on b1 TRAIN scenes (N per world dir) -> stop B-D
# 2 build d-min DAgger rows + aggregate (B-D rows + DAgger rows), steps = 816 x rows ratio
# 3 train 8B LoRA on the aggregate (L8 recipe, seed 0) -> merge
# 4 serve the DAgger model -> offline eval (L8-X dev_x / ood_h / ood_o, d-min clean, --arm pt)
# 5 closed loop on the boost1 episodes (OOD-H 0.98 x4, OOD-O x4), fixes off and on -> videos /data/harvest/videos/boost2
# usage: boost2.sh <code dir> <gpu> <N per dir>
C=$1; G=$2; N=${3:-8}
L=/data/harvest/logs/strip8; O=/data/harvest/out/strip8/boost2; D=$O/data
P=/data/harvest/venv_train/bin/python
mkdir -p $L $O $D
cd $C; export PYTHONPATH=$C
S="bash $C/tools/teach_strip8"
up() { for i in $(seq 120); do curl -s -m 5 http://127.0.0.1:$1/v1/models | grep -q '"id"' && return 0; sleep 10; done; return 1; }
# 1
(bash $C/tools/teach_strip8/vllm.sh $G /data/harvest/out/dist8/merged_b_d-min b2_bd 8403 0.30 &)
up 8403 || { echo "BOOST2_FAIL serve_bd" >> $L/lanes.log; exit 1; }
$P tools/teach_strip8/dagger_pick.py /data/harvest/out/teach_l8d/bundles/b1_phase1_x.json $N > $L/boost2_pick.txt
while read -r v eps; do
  [ -n "$eps" ] || continue
  $S/isaac.sh $C $G dg_${v//./} harvest.teach_strip8.run_dagger --qwen-url http://127.0.0.1:8403 --qwen-name b2_bd \
    --out $O/collect --episodes $eps
done < $L/boost2_pick.txt
$S/stop.sh b2_bd
echo "BOOST2_COLLECT_DONE $(date -u +%FT%TZ)" >> $L/lanes.log
# 2
$S/py.sh train - b2_build $C tools/teach_strip8/build_dagger.py $O/collect $D
ST=$(grep -o '^STEPS [0-9]*' $L/b2_build.log | tail -1 | cut -d' ' -f2)
[ -n "$ST" ] || { echo "BOOST2_FAIL build" >> $L/lanes.log; exit 1; }
# 3
$S/py.sh train $G b2_train $C harvest.teach_l8.train --data $D/train_agg.jsonl --out $O/run --epochs 1 \
  --max-steps $ST --micro 8 --accum 2 --log-every 10 --workers 6
E=$(ls -d $O/run/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] || { echo "BOOST2_FAIL train" >> $L/lanes.log; exit 1; }
$S/py.sh train $G b2_merge $C harvest.teach_l8.merge --adapter $E --out $O/merged
echo "BOOST2_TRAIN_DONE $ST $(date -u +%FT%TZ)" >> $L/lanes.log
# 4
(bash $C/tools/teach_strip8/vllm.sh $G $O/merged b2_dag 8404 0.30 &)
up 8404 || { echo "BOOST2_FAIL serve_dag" >> $L/lanes.log; exit 1; }
X=/data/harvest/out/dist8/data_x
for s in x_dev x_ood_h x_ood_o; do
  $S/py.sh vllm - b2_ev_$s $C harvest.teach_pt.evaluate --data $X/${s}_d-min_clean.jsonl --arm pt --kinds control \
    --url http://127.0.0.1:8404 --name b2_dag --out $O/eval/${s}
done
echo "BOOST2_EVAL_DONE $(date -u +%FT%TZ)" >> $L/lanes.log
# 5
for fix in off on; do
  while read -r v eps; do
    [ -n "$eps" ] || continue
    $S/isaac.sh $C $G b2cl_${fix}_${v//./} harvest.teach_strip8.run_boost --fix $fix --qwen-url http://127.0.0.1:8404 \
      --qwen-name b2_dag --arm dagger_$fix --out $O/closed --episodes $eps
  done < $L/boost1_pick.txt
done
$S/stop.sh b2_dag
for A in dagger_off dagger_on; do
  mkdir -p $O/vid_src/$A
  for s in ood_h ood_o; do ln -sfn $O/closed/$A/$s $O/vid_src/$A/$s; done
done
$P tools/astra_solo/make_videos.py /data/harvest/videos/boost2 dagger_off=$O/vid_src/dagger_off \
  dagger_on=$O/vid_src/dagger_on > $L/boost2_videos.log 2>&1
echo "BOOST2_DONE $(date -u +%FT%TZ)" >> $L/lanes.log
