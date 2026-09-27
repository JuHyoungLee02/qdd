#!/bin/bash
# Final 35B learning-curve evaluation (change 2, descriptive): when <run dir>/epoch<k> appears, merge it (CPU) and run
# tools/final35/eval.sh on the first free card among <candidates> of this pod (tag f35_<arm>_ep<k>).
# usage: ep_eval.sh <code dir> <arm d|h|hc> <k> <candidates> <port>
C=$1; T=$2; K=$3; CAND=$4; PORT=$5
D=/data/harvest/out/final35; R=$D/run_$T; M=$D/merged_${T}_ep$K
export TEACH_35B_JOB=f35ep_${T}_$K
case $T in d) TR=d-min;; h|hc) TR=h-min;; esac
until [ -f $R/epoch$K/adapter_model.safetensors ]; do sleep 120; done
sleep 60
[ -f $M/config.json ] || bash $C/tools/teach_35b/py.sh train - f35merge_${T}_ep$K $C harvest.teach_35b.merge --adapter $R/epoch$K --out $M
G=$(bash $C/tools/final35/free_gpus.sh $CAND 1 | cut -d, -f1)
bash $C/tools/final35/eval.sh $C $G f35_${T}_ep$K $M $TR $PORT 0.85
