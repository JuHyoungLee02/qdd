#!/bin/bash
# After B-H (dist8_bh.sh) finishes its evaluation on the same GPU, run the B+px H arm there. usage: <code dir> <gpu>
C=$1; G=$2
until grep -q "EVAL_DONE b_h-min\|EVAL_FAIL b_h-min" /data/harvest/logs/dist8/dist8_eval.log 2>/dev/null; do sleep 60; done
bash $C/tools/teach_pt/dist8_open.sh $C $G b_px_h
