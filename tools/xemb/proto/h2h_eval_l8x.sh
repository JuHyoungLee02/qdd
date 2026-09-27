#!/bin/bash
# E-H2H-T E2 (prereg_h2h.md §2): serve a merged arm and evaluate it on the L8-X v2 split files in
# /data/harvest/out/xemb/h2h/l8x (<split>_v2.jsonl, built from L8D's collect with tools/teach_l8d/build.py) + leak.
# usage: h2h_eval_l8x.sh <gpu> <port> <arm> <split> [<split> ...]
source /data/harvest/env.sh
G=$1; PORT=$2; ARM=$3; shift 3
C=/data/harvest/code_h2h
X=/data/harvest/out/xemb_proto/code
D=/data/harvest/out/xemb/h2h
L=/data/harvest/logs/h2h; mkdir -p $L $D/eval
echo "START e2 $ARM $* $(date -u +%FT%TZ) gpu=$G" >> $L/e2_$ARM.log
if curl -s -m 2 http://127.0.0.1:$PORT/v1/models > /dev/null; then  # another team's server on this port (E1 base bug)
  echo "PORT_BUSY $PORT" >> $L/e2_$ARM.log; exit 1
fi
bash $C/tools/teach_l8/vllm.sh $G $D/merged_$ARM h2h_$ARM $PORT 0.35 >> $L/vllm_e2_$ARM.log 2>&1 &
for i in $(seq 1 120); do curl -s -m 2 http://127.0.0.1:$PORT/v1/models | grep -q "\"h2h_$ARM\"" && break; sleep 10; done
curl -s -m 2 http://127.0.0.1:$PORT/v1/models | grep -q "\"h2h_$ARM\"" || { echo "SERVE_FAIL" >> $L/e2_$ARM.log; exit 1; }
for S in "$@"; do
  PYTHONPATH=$C /data/harvest/venv_vllm/bin/python -m harvest.teach_pt.evaluate --data $D/l8x/${S}_v2.jsonl --arm xyz \
    --url http://127.0.0.1:$PORT --name h2h_$ARM --out $D/eval/x${S}_$ARM --kinds control >> $L/e2_$ARM.log 2>&1
  PYTHONPATH=$X:$C /data/harvest/venv_vllm/bin/python -m xemb.eval_open8 leak $D/eval/x${S}_$ARM/replies.jsonl \
    $D/eval/x${S}_$ARM/leak.json >> $L/e2_$ARM.log 2>&1
done
/data/harvest/venv_vllm/bin/python /data/harvest/out/xemb_proto/scratch/killpy.py "h2h_$ARM" >> $L/e2_$ARM.log 2>&1
echo "EXIT e2 $ARM $(date -u +%FT%TZ)" >> $L/e2_$ARM.log
