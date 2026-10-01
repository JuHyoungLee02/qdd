#!/bin/bash
# JCR1-0 chain, part b (prereg_jcr1.md change 4): after the D0 FAIL of 10-01 08:00 -> validation filter
# (tools/jcr/select_data.py; criteria unchanged) -> D0 gate on the selection -> sweep stage 1 (CPU) + JCR1-0A / P
# training on x2 GPU0. Gate FAIL -> $R/ALERT_chain_d1b and stop.  usage: nohup bash chain_d1b.sh <code dir> &
C=$1
Q=/data/harvest; R=$Q/out/jcr; D=$R/d1; P=$Q/venv_train/bin/python; SEL=$R/d1_select.json
export JCR_JOB=chain_d1b
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | JCR | $*" >> $R/chain_events.log; }
cd $C
PYTHONPATH=$C $P tools/jcr/select_data.py --data $D --out $SEL >> $Q/logs/jcr/chain_d1b.log 2>&1 || { echo select > $R/ALERT_chain_d1b; ev "ALERT select failed"; exit 1; }
ev "change 4 selection: $(tail -1 $Q/logs/jcr/chain_d1b.log)"
PYTHONPATH=$C $P tools/jcr/data_gate.py --data $D --out $R/d1_gate_sel --select $SEL >> $Q/logs/jcr/chain_d1b.log 2>&1
ok=$($P -c "import json;g=json.load(open('$R/d1_gate_sel/gate.json'))['gate'];print(int(all(g.values())))" 2>/dev/null)
g=$(tr -d '\n ' < $R/d1_gate_sel/gate.json | grep -o '"normal_share":[^,]*\|"truth_a_max":[^,]*\|"joint_step_max_rad":[^,]*\|"gbr_mm":{[^}]*}\|"gate":{[^}]*}' | tr '\n' ' ')
[ "$ok" != 1 ] && { cp $R/d1_gate_sel/gate.json $R/ALERT_chain_d1b; ev "ALERT D0 gate (selected) FAIL: $g"; exit 1; }
rm -f $R/ALERT_chain_d1
ev "D0 gate (selected) PASS: $g"
PYTHONPATH=$C nice -n 19 $P tools/jcr/rule_sweep.py --data $D --out $R/sweep1 --n 300 --procs 6 >> $Q/logs/jcr/sweep1.log 2>&1 &
sp=$!
for L in A P; do
  env=$([ $L = A ] && echo A || echo B)
  bash $C/tools/jcr/train.sh $C 0 jcr1_0$L tools/jcr/train.py train --data $D --select $SEL --out $Q/ckpt/jcr/jcr1_0$L \
    --steps 4000 --batch 8 --K 2 --lr 2e-4 --lr-heads 5e-4 --envelope $env --max-val 400 --save-every 1000 &
  eval "tp_$L=\$!"
done
ev "training started on x2 GPU0: JCR1-0A (label A) + JCR1-0P (label P = rules B/C), sweep stage 1 (CPU)"
wait $tp_A; ev "JCR1-0A done: $(grep -h '^OFFLINE' $Q/logs/jcr/jcr1_0A.log | tail -1 | cut -c1-300)"
wait $tp_P; ev "JCR1-0P done: $(grep -h '^OFFLINE' $Q/logs/jcr/jcr1_0P.log | tail -1 | cut -c1-300)"
wait $sp; ev "sweep1 done: $(tail -1 $Q/logs/jcr/sweep1.log | cut -c1-400)"
touch $R/chain_d1.DONE
