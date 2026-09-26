#!/bin/bash
# E-H2H-T (prereg_h2h.md, 0c20e1f): train one or more arms in order on one GPU, then merge, serve (vLLM) and evaluate
# on E1 (E-PT DEV 305 / OOD-H 285, xyz arm, control) + frame-leak check. usage: h2h_run.sh <gpu> <port> <arm> [<arm> ...]
source /data/harvest/env.sh
G=$1; PORT=$2; shift 2
C=/data/harvest/code_h2h
X=/data/harvest/out/xemb_proto/code
D=/data/harvest/out/xemb/h2h
T=/data/harvest/out/teach_pt/data
L=/data/harvest/logs/h2h; mkdir -p $L $D/eval
export OMP_WAIT_POLICY=PASSIVE
for ARM in "$@"; do
  echo "START train $ARM $(date -u +%FT%TZ) gpu=$G" >> $L/$ARM.log
  CUDA_VISIBLE_DEVICES=$G PYTHONPATH=$C /data/harvest/venv_train/bin/python -m harvest.teach_l8.train \
    --data $D/$ARM.jsonl --out $D/run_$ARM --epochs 3 --max-steps 816 --micro 8 --accum 2 --log-every 10 --workers 3 \
    >> $L/$ARM.log 2>&1
  echo "EXIT train $ARM $? $(date -u +%FT%TZ)" >> $L/$ARM.log
  EP=$(ls -d $D/run_$ARM/epoch* 2>/dev/null | sort -V | tail -1)
  [ -z "$EP" ] && continue
  CUDA_VISIBLE_DEVICES=$G PYTHONPATH=$C /data/harvest/venv_train/bin/python -m harvest.teach_l8.merge --adapter $EP \
    --out $D/merged_$ARM >> $L/$ARM.log 2>&1
  bash $C/tools/teach_l8/vllm.sh $G $D/merged_$ARM h2h_$ARM $PORT 0.35 >> $L/vllm_$ARM.log 2>&1 &
  for i in $(seq 1 120); do curl -s -m 2 http://127.0.0.1:$PORT/v1/models > /dev/null && break; sleep 10; done
  for S in dev ood_h; do
    PYTHONPATH=$C /data/harvest/venv_vllm/bin/python -m harvest.teach_pt.evaluate --data $T/${S}_xyz.jsonl --arm xyz \
      --url http://127.0.0.1:$PORT --name h2h_$ARM --out $D/eval/${S}_$ARM --kinds control >> $L/$ARM.log 2>&1
    PYTHONPATH=$X:$C /data/harvest/venv_vllm/bin/python -m xemb.eval_open8 leak $D/eval/${S}_$ARM/replies.jsonl \
      $D/eval/${S}_$ARM/leak.json >> $L/$ARM.log 2>&1
  done
  /data/harvest/venv_vllm/bin/python /data/harvest/out/xemb_proto/scratch/killpy.py "h2h_$ARM" >> $L/$ARM.log 2>&1
  echo "EXIT eval $ARM $(date -u +%FT%TZ)" >> $L/$ARM.log
done
