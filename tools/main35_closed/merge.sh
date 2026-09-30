#!/bin/bash
# E-M35CL merges (7a2a CPU): main35 adapters epoch<e> -> main35_closed/merged_ep<e> (+ MERGE_OK), at most 2 merged
# copies on /data at a time (serve.sh removes each after its checkpoint is done).
# usage: merge.sh <code dir>
C=$1; R=/data/harvest/out/main35_closed; A=/data/harvest/out/main35/run; L=/data/harvest/logs/main35_closed
P=/data/harvest/venv_train/bin/python; mkdir -p $L
log() { echo "$(date -u +%FT%TZ) merge $*" >> $L/merge.log; }
for e in 0.5 1 1.5 2 2.5 3; do
  $P $C/tools/main35_closed/sched.py done $e && continue
  M=$R/merged_ep$e; [ -f $M/MERGE_OK ] && continue
  until [ -f $A/epoch$e/adapter_model.safetensors ]; do sleep 300; done
  sleep 60
  while [ $(ls -d $R/merged_ep*/ 2>/dev/null | wc -l) -ge 2 ]; do sleep 300; done
  rm -rf $M
  bash $C/tools/teach_35b/py.sh train - m35cl_merge_ep${e/./_} $C harvest.teach_35b.merge --adapter $A/epoch$e --out $M
  if [ -f $M/config.json ]; then touch $M/MERGE_OK; log "MERGED $e"; else log "MERGE_FAIL $e"; rm -rf $M; fi
done
