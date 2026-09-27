#!/bin/bash
# Final 35B chain for one arm (prereg_final35.md, change 2): build -> LoRA 2 epochs, DDP on the free cards of this pod
# (global batch 24 for every arm: 6 cards micro 4, 4 cards micro 3 x accum 2, 3 cards micro 4 x accum 2, 2 cards micro 4
# x accum 3) -> merge the last epoch -> offline L8-X evaluation -> boost1 closed loop (8 episodes) + videos. Every step
# waits for free cards among its candidates (tools/final35/free_gpus.sh) and takes them when they free up.
# usage: chain.sh <code dir> <d|h|hc> <train candidates> <min train cards> <eval cand> <cl serve cand> <cl render cand>
#                 <port> [<pack>:<share> ...]
C=$1; T=$2; TC=$3; TMIN=$4; EC=$5; SC=$6; RC=$7; PORT=$8; shift 8
D=/data/harvest/out/final35; L=/data/harvest/logs/final35; mkdir -p $L
FG=$C/tools/final35/free_gpus.sh
export TEACH_35B_JOB=f35chain_$T
case $T in d|dn) TR=d-min;; h|hc) TR=h-min;; esac
echo "CHAIN_START $T host=$(hostname) train=$TC(min $TMIN) eval=$EC cl=$SC/$RC $(date -u +%FT%TZ)" >> $L/chain.log
bash $C/tools/final35/build.sh $C $T "$@"
RUN=$D/run_$T
if [ ! -f $RUN/train.json ]; then
  F=$(bash $FG $TC $TMIN); n=$(echo $F | tr ',' '\n' | wc -l)
  for k in 6 4 3 2 1; do [ $n -ge $k ] && break; done
  TG=$(echo $F | cut -d, -f1-$k)
  case $k in 6) MI=4; AC=1;; 4) MI=3; AC=2;; 3) MI=4; AC=2;; 2) MI=4; AC=3;; 1) MI=4; AC=6;; esac
  echo "TRAIN_START $T gpus=$TG micro=$MI accum=$AC $(date -u +%FT%TZ)" >> $L/chain.log
  bash $C/tools/teach_35b/train.sh $C $TG $D/data/train_${T}_mix.jsonl $RUN --epochs 2 --micro $MI --accum $AC \
    --workers ${WORKERS:-6}
fi
[ -f $RUN/train.json ] || { echo "TRAIN_FAIL $T $(date -u +%FT%TZ)" >> $L/chain.log; exit 1; }
E=$(ls -d $RUN/epoch* | sort -V | tail -1)
echo "TRAIN_DONE $T $E $(date -u +%FT%TZ)" >> $L/chain.log
M=$D/merged_$T
[ -f $M/config.json ] || bash $C/tools/teach_35b/py.sh train - f35merge_$T $C harvest.teach_35b.merge --adapter $E --out $M
EG=$(bash $FG $EC 1 | cut -d, -f1)
bash $C/tools/final35/eval.sh $C $EG f35_$T $M $TR $PORT 0.85
SG=$(bash $FG $SC 1 | cut -d, -f1); RG=$(bash $FG $RC 1 | cut -d, -f1)
bash $C/tools/final35/closed.sh $C $SG $RG f35_$T $M $TR $((PORT + 1)) on
echo "CHAIN_DONE $T $(date -u +%FT%TZ)" >> $L/chain.log
