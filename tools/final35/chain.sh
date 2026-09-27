#!/bin/bash
# Final 35B chain for one arm (prereg_final35.md): build -> LoRA 2 epochs (tools/teach_35b/train.sh, N GPUs = DDP with
# global batch 16) -> merge the last epoch -> offline L8-X evaluation -> boost1 closed loop (8 episodes) + videos.
# usage: chain.sh <code dir> <d|h> <train gpus e.g. 0,1,3,4> <eval gpu> <cl serve gpu> <cl render gpu> <port> [<pack>:<share> ...]
C=$1; T=$2; TG=$3; EG=$4; SG=$5; RG=$6; PORT=$7; shift 7
D=/data/harvest/out/final35; L=/data/harvest/logs/final35; mkdir -p $L
export TEACH_35B_JOB=f35chain_$T
case $T in d) TR=d-min; IF=d-min;; h) TR=h-min; IF=h-min;; esac
echo "CHAIN_START $T host=$(hostname) train=$TG eval=$EG cl=$SG/$RG $(date -u +%FT%TZ)" >> $L/chain.log
bash $C/tools/final35/build.sh $C $T "$@"
N=$(echo $TG | tr ',' '\n' | wc -l); ACC=$((4 / N)); [ $ACC -lt 1 ] && ACC=1
RUN=$D/run_$T
[ -f $RUN/train.json ] || bash $C/tools/teach_35b/train.sh $C $TG $D/data/train_${T}_mix.jsonl $RUN --epochs 2 --accum $ACC \
  --workers ${WORKERS:-6}
[ -f $RUN/train.json ] || { echo "TRAIN_FAIL $T $(date -u +%FT%TZ)" >> $L/chain.log; exit 1; }
E=$(ls -d $RUN/epoch* | sort -V | tail -1)
echo "TRAIN_DONE $T $E $(date -u +%FT%TZ)" >> $L/chain.log
M=$D/merged_$T
[ -f $M/config.json ] || bash $C/tools/teach_35b/py.sh train - f35merge_$T $C harvest.teach_35b.merge --adapter $E --out $M
bash $C/tools/final35/eval.sh $C $EG f35_$T $M $TR $PORT 0.85
bash $C/tools/final35/closed.sh $C $SG $RG f35_$T $M $IF $((PORT + 1)) on
echo "CHAIN_DONE $T $(date -u +%FT%TZ)" >> $L/chain.log
