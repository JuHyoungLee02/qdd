#!/bin/bash
# E-OPRATIO8 driver (prereg_opratio.md). prep: base d-min rows from L8-X b2, guarded open pool, the four training
# files, the G rows. arm: train one ratio on one GPU (--save-every 200, resume if a state exists), merge, then the
# G evaluation and the L8-X evaluation (dist8_eval.sh, d-min) with vLLM on the same GPU.
# usage: opratio.sh <code dir> prep | opratio.sh <code dir> arm <ratio 0|25|50|75> <gpu> <port> [seed, default 0]
C=$1; CMD=$2
O=/data/harvest/out/opratio; L=/data/harvest/logs/opratio; P=/data/harvest/venv_train/bin/python
mkdir -p $O $L
cd $C; export PYTHONPATH=$C
if [ "$CMD" = prep ]; then
  $P tools/teach_pt/convert_min.py /data/harvest/out/teach_l8d/data/b2/train_pt.jsonl $O d-min base_d-min.jsonl > $L/prep.log 2>&1
  $P tools/teach_pt/opratio_build.py pool $O >> $L/prep.log 2>&1
  $P tools/teach_pt/opratio_build.py train $O $O/base_d-min.jsonl >> $L/prep.log 2>&1
  $P tools/teach_pt/opratio_build.py geval $O /data/harvest/data/gbench >> $L/prep.log 2>&1
  PYTHONPATH=$C/tools $P -m xemb.gsplit check $O/train_p0.jsonl $O/train_p25.jsonl $O/train_p50.jsonl $O/train_p75.jsonl >> $L/prep.log 2>&1 \
    && echo "PREP_DONE $(date -u +%FT%TZ)" >> $L/opratio.log || echo "PREP_FAIL $(date -u +%FT%TZ)" >> $L/opratio.log
  exit 0
fi
R=$3; G=$4; PORT=$5; SEED=${6:-0}; A=op_p$R; [ "$SEED" != 0 ] && A=${A}_s$SEED
until grep -q PREP_DONE $L/opratio.log 2>/dev/null; do grep -q PREP_FAIL $L/opratio.log && exit 1; sleep 30; done
S=$(( 1632 * (100 + R) / 100 ))  # = train.counts.json steps (1632 / 2040 / 2448 / 2856)
RES=""; [ -d $O/run_$A/state ] && RES="--resume"
bash $C/tools/teach_pt/py.sh train $G train_$A $C harvest.teach_l8.train --data $O/train_p$R.jsonl --out $O/run_$A \
  --epochs 3 --max-steps $S --micro 8 --accum 2 --log-every 10 --save-every 200 --seed $SEED $RES
E=$(ls -d $O/run_$A/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] && bash $C/tools/teach_pt/py.sh train $G merge_$A $C harvest.teach_l8.merge --adapter $E --out $O/merged_$A
echo "TRAIN_DONE $A $E $(date -u +%FT%TZ)" >> $L/opratio.log
N=${A}_srv
setsid nohup bash $C/tools/teach_pt/vllm.sh $G $O/merged_$A $N $PORT 0.60 < /dev/null > /dev/null 2>&1 &
for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && break; sleep 10; done
bash $C/tools/teach_pt/py.sh vllm - geval_$A $C tools/teach_pt/geval.py --data $O/g_eval.jsonl --url http://127.0.0.1:$PORT \
  --name $N --out $O/eval/$A/g
for f in /data/harvest/out/dist8/data_x/x_*_d-min_clean.jsonl; do
  b=$(basename $f .jsonl)
  bash $C/tools/teach_pt/py.sh vllm - ev_${A}_$b $C harvest.teach_pt.evaluate --data $f --arm pt \
    --url http://127.0.0.1:$PORT --name $N --out $O/eval/$A/$b --kinds control
done
bash $C/tools/teach_pt/stop.sh $N >> $L/opratio.log 2>&1
echo "EVAL_DONE $A $(date -u +%FT%TZ)" >> $L/opratio.log
