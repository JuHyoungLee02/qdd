#!/bin/bash
# L9 v2 env render smoke chain: one Isaac at a time on GPU 1 (7a2a), jobs in order. Stop: touch $OUT/STOP.
# usage: smoke_chain.sh CODE ROWS OUT TAG job1 job2 ...
C=$1; ROWS=$2; OUT=$3; TAG=$4; shift 4
mkdir -p $OUT
for J in "$@"; do
  [ -e $OUT/STOP ] && { echo "STOP $(date -u +%FT%TZ)" >> $OUT/chain.log; exit 0; }
  echo "JOB $J $(date -u +%FT%TZ)" >> $OUT/chain.log
  L9_TIMEOUT=3600 bash $C/tools/l9/isaac.sh $C 1 ${TAG}_$J tools.l9v2env.smoke_render --rows $ROWS --job $J --out $OUT
  echo "END $J $(date -u +%FT%TZ)" >> $OUT/chain.log
done
echo "CHAIN_DONE $(date -u +%FT%TZ)" >> $OUT/chain.log
