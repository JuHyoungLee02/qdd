#!/bin/bash
# E-FUT1 change 6 (prereg_fut1.md §7 next step): second seed, F0 and F2 retrained together with 8,000 d1 rows
# (+ 4,000 replay, fut_rows.py --seed 1; trainer --seed 1), one GPU each like seed 0 (micro 4 x accum 6 = 24; F0s1 on
# 78dc:1, F2s1 on 78dc:2 -- 78dc:0 holds an E-VB1 server), merge, evaluation on the whole held-out pool (F0s1 'cur',
# F2s1 'roll') + the static sets split over two cards per arm (F0s1 1+3, F2s1 2+3; a part waits for its card to be
# free); then tools/fut1/rv2_summary.py (two seeds pooled, change 6 rule).
# YIELD: a GPU_WANTED line without FUT1 listing 78dc:<g> -> stop that arm's work, exit 3 (rerun resumes: --resume state,
# cached replies).  usage: nohup bash rv2.sh <code dir> > /dev/null 2>&1 &   (on juhyoung-q-78dc)
C=$1
Q=/data/harvest; F=$Q/out/fut1; D=$F/data_s1; L=$Q/logs/fut1; P=$Q/venv_train/bin/python
M35=$Q/out/main35/data; X=$Q/out/dist8/data_x
mkdir -p $L
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | FUT1 | rv2 | $*" >> $F/events.log; }
wanted() { for w in $Q/out/l9/GPU_WANTED $Q/out/vla/GPU_WANTED; do
  [ -f $w ] && grep -v FUT1 $w | grep -oE "(^|[[:space:]])78dc:[0-9,]+" | grep -qE "[:,]$1(,|$)" && return 0; done; return 1; }
free() { [ "$(nvidia-smi -i $1 --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 1000 ] && ! wanted $1; }
best=$($P -c "import json;print(json.load(open('$Q/out/main35/verdict/verdict_summary.json'))['best'])")
BASE=$Q/out/main35/merged_ep$best
if [ ! -f $D/DONE ]; then
  ev "rows seed 1: 8,000 d1 + 4,000 replay, eval = whole held-out pool"
  PYTHONPATH=$C $P $C/tools/fut1/fut_rows.py --data $Q/out/jcr/d1 --mm1 $Q/out/deploy/mm1/rows.jsonl \
    --replay $M35/train_main35.jsonl --out $D --workers 16 --eval-sites 100000 --n-d1 8000 --n-replay 4000 --seed 1 \
    >> $L/rv2_data.log 2>&1 || { ev "ALERT rows failed"; exit 1; }
  touch $D/DONE
  ev "rows done: $($P -c "import json;d=json.load(open('$D/rows_stats.json'));print(d['arms']['F2']['rows'], d['arms']['F2']['delta_hist'], d['eval_sites'])")"
fi
for v in cur roll; do
  $P - <<PY
import json, hashlib
rows=[json.loads(x) for x in open("$D/eval_$v.jsonl")]
for k in (0, 1):
    with open("$D/eval_${v}_p%d.jsonl" % k, "w") as f:
        for r in rows:
            if int(hashlib.sha256(f"{r['episode']}|{r['call']}".encode()).hexdigest(), 16) % 2 == k:
                f.write(json.dumps(r) + "\n")
PY
done
watch() {  # <pid> <gpus a,b> <job names...>: stop on a wanted card
  local p=$1 gs=$2; shift 2
  while kill -0 $p 2>/dev/null; do
    for g in ${gs//,/ }; do wanted $g && { for j in "$@"; do bash $C/tools/teach_35b/stop.sh $j > /dev/null; done
      ev "YIELD 78dc:$g ($*)"; return 3; }; done
    sleep 20
  done; return 0; }
serve_eval() {  # per-card lock (78dc:3 is shared by the two arms' second parts), then serve_eval_1
  until mkdir $F/rv2_lock_g$1 2>/dev/null; do sleep 30; done
  serve_eval_1 "$@"; local rc=$?
  rmdir $F/rv2_lock_g$1; return $rc; }
serve_eval_1() {  # <gpu> <arm> <merged> <part> <variant> <static sets...>
  local g=$1 arm=$2 m=$3 k=$4 v=$5; shift 5
  local port=$((8781 + g)) n=q35_fut1rv2_${arm,,}_$k A=$F/arms/$arm
  until free $g; do sleep 60; done
  setsid nohup bash $C/tools/teach_35b/vllm.sh $g $m $n $port 0.85 < /dev/null > /dev/null 2>&1 &
  for i in $(seq 120); do curl -sf 127.0.0.1:$port/v1/models | grep -q $n && break; sleep 10; done
  curl -sf 127.0.0.1:$port/v1/models | grep -q $n || { ev "ALERT serve $n"; bash $C/tools/teach_35b/stop.sh $n; return 1; }
  local sets=("mm_${v}_p$k:$D/eval_${v}_p$k.jsonl:pt" "$@")
  for s in "${sets[@]}"; do
    IFS=: read -r name data kind <<< "$s"
    local out=$A/eval/$name; [ -f $out/scores.jsonl ] && continue
    case $name in mm_*) out=$A/parts/$name;; esac
    [ -f $out/scores.jsonl ] && continue
    if [ $kind = geval ]; then
      bash $C/tools/teach_35b/py.sh vllm - fut1rv2_${arm,,}_$name $C tools/teach_pt/geval.py --data $data \
        --url http://127.0.0.1:$port --name $n --out $out &
    else
      bash $C/tools/teach_35b/py.sh vllm - fut1rv2_${arm,,}_$name $C harvest.teach_pt.evaluate --data $data --arm pt \
        --url http://127.0.0.1:$port --name $n --out $out --kinds control --workers 8 &
    fi
    watch $! $g fut1rv2_${arm,,}_$name $n || return 3
  done
  bash $C/tools/teach_35b/stop.sh $n > /dev/null
  ev "$arm part $k ($v + $# static sets) done on 78dc:$g"; }
run_arm() {  # <arm> <src arm F0|F2> <train gpu> <eval gpus a,b> <variant>
  local arm=$1 src=$2 gs=$3 v=$5 A=$F/arms/$1 R=$F/arms/$1/fut1_tr_${1,,} M=$F/merged/$1
  local g0=${4%,*} g1=${4#*,}
  mkdir -p $A
  until free $gs; do sleep 60; done
  if [ ! -f $M/MERGE_OK ]; then
    if [ ! -f $R/epoch1/adapter_model.safetensors ]; then
      local RES=""; [ -d $R/state ] && RES=--resume
      ev "$arm train start on 78dc:$gs ($(wc -l < $D/train_$src.jsonl) rows, seed 1) $RES"
      PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True bash $C/tools/teach_35b/train.sh $C $gs $D/train_$src.jsonl $R \
        --model $BASE --epochs 1 --micro 4 --accum 6 --save-every 100 --seed 1 $RES &
      watch $! $gs $(basename $R) || return 3
      [ -f $R/epoch1/adapter_model.safetensors ] || { ev "ALERT $arm TRAIN_FAIL"; return 1; }
      ev "$arm train done: $(tail -1 $R/log.jsonl | cut -c1-120)"
    fi
    bash $C/tools/teach_35b/py.sh train - fut1rv2_merge_${arm,,} $C harvest.teach_35b.merge --adapter $R/epoch1 \
      --out $M --model $BASE && touch $M/MERGE_OK
    [ -f $M/MERGE_OK ] || { ev "ALERT $arm MERGE_FAIL"; return 1; }
  fi
  serve_eval $g0 $arm $M 0 $v "x_val_l8s_d-min_clean:$M35/x_val_l8s_d-min_clean.jsonl:pt" \
    "g_val_open:$M35/val_open.jsonl:geval" "x_dev_d-min_clean:$X/x_dev_d-min_clean.jsonl:pt" \
    "x_ood_h_d-min_clean:$X/x_ood_h_d-min_clean.jsonl:pt" "x_ood_hl_d-min_clean:$X/x_ood_hl_d-min_clean.jsonl:pt" &
  local e0=$!
  serve_eval $g1 $arm $M 1 $v "g:$Q/out/opratio/g_eval.jsonl:geval" "x_ood_d_d-min_clean:$X/x_ood_d_d-min_clean.jsonl:pt" \
    "x_ood_o_d-min_clean:$X/x_ood_o_d-min_clean.jsonl:pt" "x_ood_s_d-min_clean:$X/x_ood_s_d-min_clean.jsonl:pt" \
    "x_ood_t_d-min_clean:$X/x_ood_t_d-min_clean.jsonl:pt" \
    "x_ood_o58_d-min_clean:$Q/out/c35/data/x_ood_o58_d-min_clean.jsonl:pt" &
  local e1=$!
  wait $e0; local r0=$?; wait $e1; local r1=$?
  [ $r0 = 0 ] && [ $r1 = 0 ] || return 3
  mkdir -p $A/eval/mm_$v
  cat $A/parts/mm_${v}_p0/scores.jsonl $A/parts/mm_${v}_p1/scores.jsonl > $A/eval/mm_$v/scores.jsonl
  touch $A/DONE; ev "$arm DONE"; }
run_arm F0s1 F0 1 1,3 cur & a0=$!
sleep 30  # the two eval parts that share 78dc:3 then start in a fixed order
run_arm F2s1 F2 2 2,3 roll & a2=$!
wait $a0; wait $a2
if [ -f $F/arms/F0s1/DONE ] && [ -f $F/arms/F2s1/DONE ]; then
  PYTHONPATH=$C $P $C/tools/fut1/rv2_summary.py --root $F >> $L/rv2_summary.log 2>&1
  ev "RV2 SUMMARY: $(tail -1 $L/rv2_summary.log | cut -c1-700)"
  touch $F/RV2_DONE
fi
