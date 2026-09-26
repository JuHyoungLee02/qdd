#!/bin/bash
# Run several dist8_eval.sh jobs one after another on one GPU / port (avoids nested quoting in remote launches).
# usage: dist8_eval_seq.sh <code dir> <gpu> <port> <mem> <tag>:<merged dir>:<track> [...]
C=$1; G=$2; PORT=$3; U=$4; shift 4
for spec in "$@"; do
  IFS=: read -r tag m t <<< "$spec"
  bash $C/tools/teach_pt/dist8_eval.sh $C $G $tag $m $t $PORT $U
done
