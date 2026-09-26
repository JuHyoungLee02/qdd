#!/bin/bash
# E-OPEN8 evaluation (prereg §4) for one arm on one GPU: merge -> vLLM -> DEV + OOD-H (teach_pt.evaluate, arm xyz,
# control) -> open held-out -> frame-leak check. usage: open8_eval.sh <gpu> <code dir> <arm oa|ob> <port>
source /data/harvest/env.sh
G=$1; C=$2; ARM=$3; PORT=$4
D=/data/harvest/out/xemb/open8; L=/data/harvest/logs/open8; mkdir -p $L
T=/data/harvest/out/teach_pt/data
EP=$(ls -d $D/run_$ARM/epoch* | sort -V | tail -1)
echo "START eval $ARM $(date -u +%FT%TZ) adapter=$EP" >> $L/eval_$ARM.log
if [ ! -f $D/merged_$ARM/config.json ]; then
  CUDA_VISIBLE_DEVICES=$G PYTHONPATH=$C /data/harvest/venv_train/bin/python -m harvest.teach_l8.merge --adapter $EP \
    --out $D/merged_$ARM >> $L/eval_$ARM.log 2>&1
fi
bash $C/tools/teach_l8/vllm.sh $G $D/merged_$ARM open8_$ARM $PORT 0.35 &
for i in $(seq 1 120); do curl -s -m 2 http://127.0.0.1:$PORT/v1/models > /dev/null && break; sleep 10; done
for S in dev ood_h; do
  PYTHONPATH=$C /data/harvest/venv_vllm/bin/python -m harvest.teach_pt.evaluate --data $T/${S}_xyz.jsonl --arm xyz \
    --url http://127.0.0.1:$PORT --name open8_$ARM --out $D/eval_${ARM}_$S --kinds control >> $L/eval_$ARM.log 2>&1
  PYTHONPATH=/data/harvest/out/xemb_proto/code:$C /data/harvest/venv_vllm/bin/python -m xemb.eval_open8 leak $D/eval_${ARM}_$S/replies.jsonl \
    $D/eval_${ARM}_$S/leak.json >> $L/eval_$ARM.log 2>&1
done
PYTHONPATH=/data/harvest/out/xemb_proto/code:$C /data/harvest/venv_vllm/bin/python -m xemb.eval_open8 heldout $D/heldout.jsonl \
  http://127.0.0.1:$PORT open8_$ARM $D/eval_${ARM}_heldout.json >> $L/eval_$ARM.log 2>&1
pkill -f "served-model-name open8_$ARM" || true
echo "EXIT eval $ARM $(date -u +%FT%TZ)" >> $L/eval_$ARM.log
