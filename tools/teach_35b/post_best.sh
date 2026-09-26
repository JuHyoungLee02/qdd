#!/bin/bash
# E-TEACH-35B after the 4 epoch evals.
#   latency mode: best epoch BF16 then FP8-online latency (probe, one request at a time) on <vllm gpu>, servers stopped.
#   closed mode : FP8-online server on <vllm gpu> + the 4 registered DEV closed-loop episodes with Isaac on <isaac gpu>
#                 (same pod), server stopped, then videos + report.
# usage: post_best.sh <best epoch k> <latency|closed> <vllm gpu> [isaac gpu]
K=$1; MODE=$2; GV=$3; GI=$4
C=/data/harvest/code_teach_35b_5ecb030; Q=/data/harvest; O=$Q/out/teach_35b; L=$Q/logs/teach_35b
M=$O/merged_run_l8e4_ep$K; P=8420; U=http://127.0.0.1:$P
export TEACH_35B_JOB=post_best
log() { echo "$1 $(hostname) $(date -u +%FT%TZ)" >> $L/post_best.log; }
up() {  # $1 served name, $2 mem util, rest = extra vllm args
  local n=$1 u=$2; shift 2
  nohup bash $C/tools/teach_35b/vllm.sh $GV $M $n $P $u "$@" > /dev/null 2>&1 &
  for i in $(seq 90); do curl -sf $U/v1/models > /dev/null && return 0; sleep 10; done
  return 1
}
log "START best=ep$K mode=$MODE gv=$GV gi=$GI"
if [ "$MODE" = latency ]; then
  for q in bf16 fp8; do
    N=q35_ep${K}_$q
    if [ $q = fp8 ]; then up $N 0.85 --quantization fp8 || { log "SERVE_FAIL $N"; exit 1; }
    else up $N 0.85 || { log "SERVE_FAIL $N"; exit 1; }; fi
    log "SERVED $N"
    bash $C/tools/teach_35b/py.sh vllm - lat_ep${K}_$q $C harvest.teach_35b.probe --data $Q/out/teach_l8/data/dev.jsonl \
      --url $U --name $N --out $O/latency/ep${K}_$q --n 60 --warmup 2
    log "LATENCY_DONE $N"
    bash $C/tools/teach_35b/stop.sh $N >> $L/post_best.log 2>&1
  done
  log "LATENCY_ALL_DONE"
  exit 0
fi
N=q35_ep${K}_fp8
up $N 0.45 --quantization fp8 || { log "SERVE_FAIL $N"; bash $C/tools/teach_35b/stop.sh $N; exit 1; }
log "SERVED $N"
for v in standard dr; do
  for s in 0 1; do
    bash $C/tools/teach_35b/closed.sh $C $GI ep$K $N $P $v $s
    log "CLOSED_DONE $v $s"
  done
done
bash $C/tools/teach_35b/stop.sh $N >> $L/post_best.log 2>&1
mkdir -p $Q/videos/teach_35b
cd $C
$Q/venv_train/bin/python tools/astra_solo/make_videos.py $Q/videos/teach_35b q35_ep$K=$O/closed/ep$K > $L/videos.log 2>&1
log "VIDEOS_DONE"
$Q/venv_train/bin/python tools/astra_solo/report.py --out $O/closed/ep$K --model qwen8b > $O/closed/ep$K/report.md 2>> $L/post_best.log
log "ALL_DONE"
