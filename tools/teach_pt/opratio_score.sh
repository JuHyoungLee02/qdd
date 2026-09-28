#!/bin/bash
# E-OPRATIO8 scoring after the runs: G re-score from cached replies (geval --score-only; the in-run scoring crashed on
# the Where2Place .jpg masks, prereg change 2) and the verdict (opratio_compare.py).
# usage: opratio_score.sh <code dir>
C=$1; O=/data/harvest/out/opratio; L=/data/harvest/logs/opratio; P=/data/harvest/venv_train/bin/python
cd $C; export PYTHONPATH=$C
for a in op_p0 op_p25 op_p50 op_p75; do
  $P tools/teach_pt/geval.py --score-only --data $O/g_eval.jsonl --out $O/eval/$a/g >> $L/score.log 2>&1
done
$P tools/teach_pt/opratio_compare.py $O/eval $O/g_eval.jsonl /data/harvest/out/dist8/data_x $O/verdict.json >> $L/score.log 2>&1
echo "SCORE_DONE $? $(date -u +%FT%TZ)" >> $L/score.log
