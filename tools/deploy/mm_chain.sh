#!/bin/bash
# E-DEP1 stage 1 (prereg_deploy1.md §1) on x2 GPU0 (user 10-01: ours until the JCR1 training wants it).
# For each model: vLLM (tools/teach_35b/vllm.sh, BF16 merged, thinking off, prefix caching) -> teach_pt.evaluate on the
# mid-motion rows (resumable replies) -> stop. YIELD: the JCR chain's "d1 complete" / "returned" event (training on
# GPU0 follows within minutes) or $R/YIELD -> stop vLLM + client at once, exit 3 (rerun resumes from the replies).
# usage: nohup bash mm_chain.sh <code dir> <rows.jsonl> <out dir> > /dev/null 2>&1 &
C=$1; ROWS=$2; OUT=$3
Q=/data/harvest; R=$Q/out/deploy; L=$Q/logs/deploy; CE=$Q/out/jcr/chain_events.log
M35C=/data/harvest/code_main35q_a5a915f
mkdir -p $L $OUT
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | DEP | $*" >> $R/events.log; }
yield_now() { [ -f $R/YIELD ] && return 0; [ -f $CE ] && grep -q "d1 complete\|returned to L9" $CE; }
PORT=8671
for spec in "q35_mm_ep1:/data/harvest/out/main35/merged_ep1" "q35_mm_f35d:/data/harvest/out/final35/merged_d"; do
  N=${spec%%:*}; M=${spec#*:}
  [ -f $OUT/$N/summary.json ] && continue
  yield_now && { ev "yield before $N"; exit 3; }
  bash $M35C/tools/teach_35b/vllm.sh 0 $M $N $PORT 0.85 &
  for i in $(seq 120); do curl -sf localhost:$PORT/v1/models > /dev/null && break; yield_now && break; sleep 10; done
  yield_now && { bash $M35C/tools/teach_35b/stop.sh $N > /dev/null; ev "yield while loading $N"; exit 3; }
  ev "$N serving on x2 GPU0 :$PORT"
  bash $M35C/tools/teach_35b/py.sh vllm - mm_eval_$N $C harvest.teach_pt.evaluate --data $ROWS --out $OUT/$N \
    --arm pt --kinds control --workers 8 --url http://127.0.0.1:$PORT --name $N &
  ep=$!
  while kill -0 $ep 2>/dev/null; do
    if yield_now; then bash $M35C/tools/teach_35b/stop.sh mm_eval_$N > /dev/null; bash $M35C/tools/teach_35b/stop.sh $N > /dev/null
      ev "yield during $N ($(wc -l < $OUT/$N/replies.jsonl) replies kept)"; exit 3; fi
    sleep 15
  done
  bash $M35C/tools/teach_35b/stop.sh $N > /dev/null
  ev "$N done: $(grep -h EVAL_DONE $Q/logs/teach_35b/mm_eval_$N.log | tail -1 | cut -c1-200)"
done
PYTHONPATH=$C $Q/venv_train/bin/python $C/tools/deploy/mm_summary.py --rows $ROWS --out $OUT >> $L/mm_summary.log 2>&1
ev "stage-1 summary: $(tail -1 $L/mm_summary.log | cut -c1-400)"
touch $OUT/DONE
