#!/bin/bash
# E-OPRATIO8-S1 chain (prereg_opratio_s1.md): p0 and p75 at training seed 1 in parallel on 78dc GPU 0 / 1 (same
# training files as seed 0), each trained, merged and evaluated by opratio.sh arm, then the pooled verdict.
# usage: opratio_s1_chain.sh <code dir>
C=$1; O=/data/harvest/out/opratio; L=/data/harvest/logs/opratio; P=/data/harvest/venv_train/bin/python
bash $C/tools/teach_pt/opratio.sh $C arm 0 0 8510 1 > $L/arm_p0_s1.log 2>&1 &
bash $C/tools/teach_pt/opratio.sh $C arm 75 1 8511 1 > $L/arm_p75_s1.log 2>&1 &
wait
cd $C; PYTHONPATH=$C $P tools/teach_pt/opratio_s1_compare.py $O/eval $O/g_eval.jsonl /data/harvest/out/dist8/data_x $O/verdict_s1.json >> $L/score_s1.log 2>&1
echo "S1_DONE $? $(date -u +%FT%TZ)" >> $L/opratio.log
