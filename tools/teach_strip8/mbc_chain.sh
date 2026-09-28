#!/bin/bash
# D round 2 Mbc chain: wait for L8D conf1 (train_pt.jsonl + counts) and the RefSpatial pool -> d-min rows (min_format
# convert) -> Mbc file -> train on GPU <tg> -> merge -> serve on <tg> -> offline eval (x_dev / x_ood_h / x_ood_o d-min
# clean) -> closed loop (plan <plan>) on render GPU <rg> of this pod -> videos. usage: mbc_chain.sh <code> <tg> <rg> <plan>
C=$1; TG=$2; RG=$3; PLAN=$4
L=/data/harvest/logs/strip8; O=/data/harvest/out/strip8/mbc
CONF=/data/harvest/out/teach_l8d/data/conf1
P=/data/harvest/venv_train/bin/python
mkdir -p $O
cd $C; export PYTHONPATH=$C
S="bash $C/tools/teach_strip8"
until [ -s $CONF/train_pt.jsonl ] && ls $CONF/train_pt*counts.json > /dev/null 2>&1; do sleep 120; done
until grep -q "^POOL" $L/refsp_pool.log; do sleep 60; done
$S/py.sh train - mbc_conv $C tools/teach_strip8/conv_dmin.py $CONF/train_pt.jsonl $O/data
$S/py.sh train - mbc_build $C tools/teach_strip8/build_mbc.py $O/data/train_d-min.jsonl /data/harvest/data/refspatial/pool.jsonl $O/data
ST=$(grep -o '^STEPS [0-9]*' $L/mbc_build.log | tail -1 | cut -d' ' -f2)
[ -n "$ST" ] || { echo "MBC_FAIL build" >> $L/lanes.log; exit 1; }
$S/py.sh train $TG mbc_train $C harvest.teach_l8.train --data $O/data/train_mbc.jsonl --out $O/run --epochs 1 \
  --max-steps $ST --micro 8 --accum 2 --log-every 10 --workers 6
E=$(ls -d $O/run/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] || { echo "MBC_FAIL train" >> $L/lanes.log; exit 1; }
$S/py.sh train $TG mbc_merge $C harvest.teach_l8.merge --adapter $E --out $O/merged
echo "MBC_TRAIN_DONE $ST $(date -u +%FT%TZ)" >> $L/lanes.log
(bash $C/tools/teach_strip8/vllm.sh $TG $O/merged mbc 8425 0.30 &)
for i in $(seq 120); do curl -s -m 5 http://127.0.0.1:8425/v1/models | grep -q '"id"' && break; sleep 10; done
X=/data/harvest/out/dist8/data_x
for s in x_dev x_ood_h x_ood_o; do
  $S/py.sh vllm - mbc_ev_$s $C harvest.teach_pt.evaluate --data $X/${s}_d-min_clean.jsonl --arm pt --kinds control \
    --url http://127.0.0.1:8425 --name mbc --out $O/eval/$s
done
echo "MBC_EVAL_DONE $(date -u +%FT%TZ)" >> $L/lanes.log
B1B_OUT=/data/harvest/out/strip8/dround2_mbc bash $C/tools/teach_strip8/b1b_run_plan.sh $C $RG 8425 mbc $PLAN mbc
$S/stop.sh mbc
echo "MBC_DONE $(date -u +%FT%TZ)" >> $L/lanes.log
