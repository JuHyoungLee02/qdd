#!/bin/bash
# wait for each epoch adapter of run_l8e4 and run tools/teach_35b/eval_epoch.sh on main GPU 2 (E-TEACH-35B)
C=/data/harvest/code_teach_35b_5ecb030; R=/data/harvest/out/teach_35b/run_l8e4
export TEACH_35B_JOB=auto_eval
for k in 2 3 4; do
  until [ -f $R/epoch$k/adapter_model.safetensors ] && grep -q "^EPOCH $k " /data/harvest/logs/teach_35b/run_l8e4.log; do sleep 30; done
  sleep 20
  bash $C/tools/teach_35b/eval_epoch.sh $C $R $k 2 8420 0.85
done
echo "AUTO_EVAL_DONE $(date -u +%FT%TZ)" >> /data/harvest/logs/teach_35b/eval_epochs.log
