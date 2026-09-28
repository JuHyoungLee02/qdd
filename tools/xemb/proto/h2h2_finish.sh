#!/bin/bash
# E-H2H-T2: finish one D / H arm whose lane was stopped while it trained: wait for its training to exit, then merge and
# evaluate (same steps as h2h2_lane.sh). usage: h2h2_finish.sh <gpu> <port> <arm>:<seed>
G=$1; PORT=$2; IFS=: read -r arm seed <<< "$3"
C=/data/harvest/code_h2h2; R=/data/harvest/out/xemb/h2h2; L=/data/harvest/logs/h2h2
name=${arm}_s$seed
case $arm in d_*) tr=d-min;; h_*) tr=h-min;; esac
until grep -q "^EXIT" /data/harvest/logs/teach_pt/h2h2_$name.log 2>/dev/null; do sleep 60; done
cd $C; export PYTHONPATH=$C
E=$(ls -d $R/run_$name/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] && bash $C/tools/teach_pt/py.sh train $G h2h2_merge_$name $C harvest.teach_l8.merge --adapter $E --out $R/merged_$name
bash $C/tools/teach_pt/dist8_eval_seq.sh $C $G $PORT 0.60 h2h2_$name:$R/merged_$name:$tr
echo "DONE $name $(date -u +%FT%TZ) (finish)" >> $L/lanes.log
