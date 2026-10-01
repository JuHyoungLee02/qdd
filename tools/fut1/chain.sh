#!/bin/bash
# E-FUT1 automation (prereg_fut1.md §4). One script, three roles (one per pod):
#   data  <code>                 (7a2a, CPU 8 workers) wait for the JCR chain's 'd1 complete' -> tools/fut1/fut_rows.py
#                                -> out/fut1/data/DONE
#   a     <code>                 (x3 GPU0) stage A after data DONE: request x3:0 ('x3:0 FUT1' in vla/GPU_WANTED; the
#                                E-M35CL server yields per card), smoke train 5 steps on train_F4 (ep1.5 base), arm Z15
#                                (main35 ep1.5 untouched: cur / roll / rt + mm1), release x3:0
#   b     <code> <key> "<gpu:arm ...>"   stage B after the main35 judge (JUDGE_DONE) and the visual data check
#                                (a person looked at data/visual_check.png and touched data/VISUAL_OK); base = main35 best merged;
#                                78dc "0:F0 1:F1 2:F2 3:F3", x3 "0:F4 0:Zb" (same gpu = one after the other);
#                                an arm that yielded (exit 3) is retried when its card is free and not wanted;
#                                the last pod to finish writes the summary (tools/fut1/fut_summary.py)
# Never touches the main35 run: stage B starts only after JUDGE_DONE and only on cards with < 1000 MiB in use.
# usage: nohup bash chain.sh <role> <code dir> [...] > /dev/null 2>&1 &
ROLE=$1; C=$2
Q=/data/harvest; F=$Q/out/fut1; L=$Q/logs/fut1; P=$Q/venv_train/bin/python
VW=$Q/out/vla/GPU_WANTED; M35L=$Q/logs/main35/main35.log
mkdir -p $F $L
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | FUT1 | $*" >> $F/events.log; }
mem() { nvidia-smi -i $1 --query-gpu=memory.used --format=csv,noheader,nounits; }
want_line() { mkdir -p $(dirname $VW); touch $VW; grep -q "^$1 FUT1" $VW || echo "$1 FUT1 $(date -u +%FT%TZ)" >> $VW; }
drop_line() { [ -f $VW ] && sed -i "/^$1 FUT1/d" $VW; }
others_want() {  # <key> <gpu>: a GPU_WANTED line without FUT1 lists this card
  for w in $Q/out/l9/GPU_WANTED $VW; do
    [ -f $w ] && grep -v FUT1 $w | grep -oE "(^|[[:space:]])$1:[0-9,]+" | grep -qE "[:,]$2(,|$)" && return 0; done; return 1; }
run_arm() {  # <key> <gpu> <arm> <base> <variants>; retries after a yield
  local k=$1 g=$2 arm=$3
  until [ -f $F/arms/$arm/DONE ]; do
    until [ "$(mem $g)" -lt 1000 ] && ! others_want $k $g; do sleep 120; done
    bash $C/tools/fut1/arm.sh $C $k $g $arm $4 "$5"; rc=$?
    [ $rc = 1 ] && { echo "$arm" > $F/ALERT_$arm; ev "ALERT $arm failed (see events)"; return 1; }
  done
  return 0; }  # fix (change 4): the until loop's status was that of '[ $rc = 1 ]' (1), so '|| exit 1' ended the
               # per-card list after its first arm (x3 '0:F4 0:Zb' never ran Zb, the summary waited for Zb)
vars_of() { case $1 in F0) echo "cur roll";; F1) echo cur;; F2|F4) echo roll;; F3) echo rt;; Z*) echo "cur roll rt";; esac; }

case $ROLE in
data)
  until grep -q "d1 complete" $Q/out/jcr/chain_events.log 2>/dev/null; do sleep 300; done
  ev "data build start (d1 complete)"
  PYTHONPATH=$C $P $C/tools/fut1/fut_rows.py --data $Q/out/jcr/d1 --mm1 $Q/out/deploy/mm1/rows.jsonl \
    --replay $Q/out/main35/data/train_main35.jsonl --out $F/data --workers 8 --eval-sites 600 >> $L/data.log 2>&1 \
    || { ev "ALERT data build failed"; echo data > $F/ALERT_data; exit 1; }
  PYTHONPATH=$C $P $C/tools/fut1/visual_sheet.py --data $F/data --out $F/data/visual_check.png >> $L/data.log 2>&1
  if ! $P -c "import json,sys;sys.exit(0 if json.load(open('$F/data/rows_stats.json'))['gate']['pass'] else 1)"; then
    ev "ALERT data gate FAIL: $($P -c "import json;print(json.load(open('$F/data/rows_stats.json'))['gate'])")"
    echo gate > $F/ALERT_data; exit 1
  fi
  touch $F/data/DONE
  ev "data done, gate PASS: $($P -c "import json;d=json.load(open('$F/data/rows_stats.json'));print(d['gate'], d['arms']['F1'])" | cut -c1-400). Visual check: look at $F/data/visual_check.png, then touch $F/data/VISUAL_OK (stage B waits for it)"
  ;;
a)
  until [ -f $F/data/DONE ]; do sleep 120; done
  B15=$Q/out/deploy/merged_ep1.5
  want_line x3:0; ev "stage A: x3:0 requested (vla/GPU_WANTED 'x3:0 FUT1')"
  until [ "$(mem 0)" -lt 1000 ]; do sleep 30; done
  if [ ! -f $F/smoke_train/epoch1/adapter_model.safetensors ] && ! grep -q "^EXIT 0" $Q/logs/teach_35b/smoke_train.log 2>/dev/null; then
    head -200 $F/data/train_F4.jsonl > $F/smoke_F4.jsonl
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True bash $C/tools/teach_35b/train.sh $C 0 $F/smoke_F4.jsonl \
      $F/smoke_train --model $B15 --epochs 1 --micro 4 --accum 6 --max-steps 5
    ev "smoke train: $(grep -E '^EXIT' $Q/logs/teach_35b/smoke_train.log | tail -1) $(tail -1 $F/smoke_train/log.jsonl 2>/dev/null | cut -c1-200)"
  fi
  run_arm x3 0 Z15 $B15 "$(vars_of Z15)"
  drop_line x3:0; echo "x3:0 freed by FUT1 stage A $(date -u +%FT%TZ)" >> $Q/out/vla/GPU_FREED
  touch $F/STAGE_A_DONE; ev "stage A done, x3:0 released"
  ;;
b)
  KEY=$3; PAIRS=$4
  until grep -q "^JUDGE_DONE" $M35L 2>/dev/null && [ -f $F/data/VISUAL_OK ]; do sleep 300; done
  best=$($P -c "import json;print(json.load(open('$Q/out/main35/verdict/verdict_summary.json'))['best'])")
  BASE=$Q/out/main35/merged_ep$best
  if [ ! -f $BASE/config.json ]; then
    BASE=$F/base_ep$best
    if mkdir $F/base_lock 2>/dev/null; then
      bash $C/tools/teach_35b/py.sh train - fut1_merge_base $C harvest.teach_35b.merge \
        --adapter $Q/out/main35/run/epoch$best --out $BASE && touch $BASE/MERGE_OK
    fi
    until [ -f $BASE/MERGE_OK ]; do sleep 30; done
  fi
  ev "stage B on $KEY ($PAIRS): base = main35 best ep$best ($BASE)"
  [ $KEY = x3 ] && { until [ -f $F/STAGE_A_DONE ]; do sleep 120; done; want_line x3:0; }
  declare -A chains=()
  for pr in $PAIRS; do chains[${pr%%:*}]+="${pr#*:} "; done
  for g in "${!chains[@]}"; do
    ( for arm in ${chains[$g]}; do run_arm $KEY $g $arm $BASE "$(vars_of $arm)" || exit 1; done ) &
  done
  wait
  [ $KEY = x3 ] && { drop_line x3:0; echo "x3:0 freed by FUT1 stage B $(date -u +%FT%TZ)" >> $Q/out/vla/GPU_FREED; }
  ev "stage B on $KEY finished"
  if [ -f $F/arms/F0/DONE ] && [ -f $F/arms/F1/DONE ] && [ -f $F/arms/F2/DONE ] && [ -f $F/arms/F3/DONE ] && \
     [ -f $F/arms/F4/DONE ] && mkdir $F/summary_lock 2>/dev/null; then  # Zb is reported, not judged (change 4)
    PYTHONPATH=$C $P $C/tools/fut1/fut_summary.py --root $F >> $L/summary.log 2>&1
    ev "SUMMARY: $(tail -1 $L/summary.log | cut -c1-500)"
    touch $F/ALL_DONE
  fi
  ;;
z)  # change 4: Zb only (x3 GPU0), then refresh the summary with the Zb curves
  KEY=$3; G=$4
  best=$($P -c "import json;print(json.load(open('$Q/out/main35/verdict/verdict_summary.json'))['best'])")
  run_arm $KEY $G Zb $Q/out/main35/merged_ep$best "$(vars_of Zb)" || exit 1
  PYTHONPATH=$C $P $C/tools/fut1/fut_summary.py --root $F >> $L/summary.log 2>&1
  ev "SUMMARY (with Zb): $(tail -1 $L/summary.log | cut -c1-500)"
  ;;
esac
