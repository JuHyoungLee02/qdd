#!/bin/bash
# E-VIEW8 final verdict: wait until all six seed-0/1 arms of A0-A2 are evaluated (on any pod), then judge.
# usage: view8_judge_wait.sh <code dir>
C=$1; L=/data/harvest/logs/view8
until [ $(grep -cE "^EVAL_DONE (A0|A1|A2)_s[01] " $L/view8.log) -ge 6 ]; do sleep 300; done
bash $C/tools/teach_pt/view8.sh $C judge
echo "JUDGE_FINAL $(date -u +%FT%TZ)" >> $L/view8.log
