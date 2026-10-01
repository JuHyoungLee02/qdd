#!/bin/bash
# E-FUT1 change 5: re-verification before discarding (prereg_fut1.md §7) on 78dc GPU0-3. No training: the existing
# merged arms F0 (input 'cur') and F2 (input 'roll') are evaluated on the WHOLE held-out pool (all held-out sites,
# rows built by the same fut_rows.py with --eval-sites 100000 into out/fut1/data_rv), each arm on 2 GPUs (rows split
# by site hash), then tools/fut1/rv_summary.py applies P1-P3 + P4a on the full pool (P4b-e = result 1, unchanged).
# YIELD: a GPU_WANTED line without FUT1 listing 78dc:<g> -> that card's evaluation stops (rerun resumes the replies).
# usage: nohup bash rv.sh <code dir> > /dev/null 2>&1 &   (on juhyoung-q-78dc)
C=$1
Q=/data/harvest; F=$Q/out/fut1; D=$F/data_rv; L=$Q/logs/fut1; P=$Q/venv_train/bin/python
mkdir -p $L
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | FUT1 | rv | $*" >> $F/events.log; }
wanted() { for w in $Q/out/l9/GPU_WANTED $Q/out/vla/GPU_WANTED; do
  [ -f $w ] && grep -v FUT1 $w | grep -oE "(^|[[:space:]])78dc:[0-9,]+" | grep -qE "[:,]$1(,|$)" && return 0; done; return 1; }
if [ ! -f $D/DONE ]; then
  ev "rows: whole held-out pool (fut_rows.py --eval-sites 100000, 16 processes)"
  PYTHONPATH=$C $P $C/tools/fut1/fut_rows.py --data $Q/out/jcr/d1 --mm1 $Q/out/deploy/mm1/rows.jsonl \
    --replay $Q/out/main35/data/train_main35.jsonl --out $D --workers 16 --eval-sites 100000 >> $L/rv_data.log 2>&1 \
    || { ev "ALERT rows failed"; exit 1; }
  touch $D/DONE
  ev "rows done: $($P -c "import json;d=json.load(open('$D/rows_stats.json'));print(d['eval_sites'], d['eval_delta_hist'])")"
fi
# split each variant file into 2 parts by site
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
job() {  # <gpu> <arm> <variant> <part>
  local g=$1 arm=$2 v=$3 k=$4 port=$((8771 + $1)) n=q35_fut1rv_${2,,}_$4 out=$F/arms/${2}rv/parts/mm_${3}_p$4
  [ -f $out/scores.jsonl ] && return 0
  until [ "$(nvidia-smi -i $g --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 1000 ] && ! wanted $g; do sleep 60; done
  setsid nohup bash $C/tools/teach_35b/vllm.sh $g $F/merged/$arm $n $port 0.85 < /dev/null > /dev/null 2>&1 &
  for i in $(seq 120); do curl -sf 127.0.0.1:$port/v1/models | grep -q $n && break; sleep 10; done
  curl -sf 127.0.0.1:$port/v1/models | grep -q $n || { ev "ALERT serve $n"; bash $C/tools/teach_35b/stop.sh $n; return 1; }
  bash $C/tools/teach_35b/py.sh vllm - fut1rv_ev_${arm,,}_$k $C harvest.teach_pt.evaluate --data $D/eval_${v}_p$k.jsonl \
    --arm pt --url http://127.0.0.1:$port --name $n --out $out --kinds control --workers 8 &
  local p=$!
  while kill -0 $p 2>/dev/null; do
    wanted $g && { bash $C/tools/teach_35b/stop.sh fut1rv_ev_${arm,,}_$k > /dev/null; bash $C/tools/teach_35b/stop.sh $n > /dev/null; ev "YIELD 78dc:$g"; return 3; }
    sleep 20
  done
  bash $C/tools/teach_35b/stop.sh $n > /dev/null
  ev "$arm $v part $k scored on 78dc:$g"
}
ev "eval start: F0 cur on 78dc:0,1, F2 roll on 78dc:2,3"
job 0 F0 cur 0 & job 1 F0 cur 1 & job 2 F2 roll 0 & job 3 F2 roll 1 &
wait
for a in F0:cur F2:roll; do
  arm=${a%%:*}; v=${a#*:}; o=$F/arms/${arm}rv/eval/mm_$v; mkdir -p $o
  cat $F/arms/${arm}rv/parts/mm_${v}_p0/scores.jsonl $F/arms/${arm}rv/parts/mm_${v}_p1/scores.jsonl > $o/scores.jsonl
done
PYTHONPATH=$C $P $C/tools/fut1/rv_summary.py --root $F >> $L/rv_summary.log 2>&1
ev "RV SUMMARY: $(tail -1 $L/rv_summary.log | cut -c1-600)"
touch $F/RV_DONE
