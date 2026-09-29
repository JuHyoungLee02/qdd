#!/bin/bash
# E-TEACH-35B per-epoch offline evaluation (prereg_teach_35b.md §7): merge <run>/epoch<k> (CPU, shard level) ->
# vLLM BF16 on <gpu> (thinking off) -> (i) harvest.teach_l8.evaluate on the L8 DEV 305 file (same snapshots as L8),
# (ii) harvest.teach_pt.evaluate --arm xyz on the E-PT dev_xyz / ood_h_xyz files (3D metrics) -> stop the server.
# usage: eval_epoch.sh <code dir> <run dir> <k> <gpu> <port> [gpu mem util]
#   merged -> /data/harvest/out/teach_35b/merged_<run>_ep<k> ; evals -> /data/harvest/out/teach_35b/eval/{dev305,dev,ood_h}_ep<k>
C=$1; R=$2; K=$3; G=$4; P=$5; U=${6:-0.85}
Q=/data/harvest; O=$Q/out/teach_35b; L=$Q/logs/teach_35b
M=$O/merged_$(basename $R)_ep$K; N=q35_ep$K; E=$O/eval; U8=http://127.0.0.1:$P
mkdir -p $L $E
log() { echo "$1 ep$K $(date -u +%FT%TZ)" >> $L/eval_epochs.log; }
if [ ! -f $M/config.json ]; then
  log MERGE_START
  bash $C/tools/teach_35b/py.sh train - merge_ep$K $C harvest.teach_35b.merge --adapter $R/epoch$K --out $M
  tail -1 $L/merge_ep$K.log | grep -q "^EXIT 0" || { log MERGE_FAIL; exit 1; }
fi
log SERVE_START
nohup bash $C/tools/teach_35b/vllm.sh $G $M $N $P $U > /dev/null 2>&1 &
for i in $(seq 90); do curl -sf $U8/v1/models > /dev/null && break; sleep 10; done
curl -sf $U8/v1/models > /dev/null || { log SERVE_FAIL; bash $C/tools/teach_35b/stop.sh $N; exit 1; }
log EVAL_START
bash $C/tools/teach_35b/py.sh vllm - ev_dev305_ep$K $C harvest.teach_l8.evaluate \
  --data $Q/out/teach_l8/data/dev.jsonl --url $U8 --name $N --out $E/dev305_ep$K
for s in dev ood_h; do
  bash $C/tools/teach_35b/py.sh vllm - ev_${s}_ep$K $C harvest.teach_pt.evaluate \
    --data $Q/out/teach_pt/data/${s}_xyz.jsonl --arm xyz --url $U8 --name $N --out $E/${s}_ep$K
done
bash $C/tools/teach_35b/stop.sh $N >> $L/eval_epochs.log 2>&1
log EVAL_DONE
