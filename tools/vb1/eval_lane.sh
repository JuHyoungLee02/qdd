#!/bin/bash
# E-VB1 closed-loop lane (docs/stage3/prereg_vb1.md change 1): runs groups of tools/vb1/evalq.py for the served
# checkpoint (<eval root>/SERVER, written by chain_eval.sh) on one render card, with the same card rule and yield as
# the render lane (tools/vb1/card.py). Waits while no server is announced or the card is busy.
# usage: nohup bash eval_lane.sh <code dir> <pod: 7a2a|x2> <gpu> <lane tag> > /dev/null 2>&1 &   stop: touch $R/STOP_EVAL
C=$1; POD=$2; G=$3; LANE=$4
Q=/data/harvest; R=$Q/out/vb1; E=$R/eval; LN=$E/lanes; P=$Q/venv_train/bin/python; CARD=$POD:$G
mkdir -p $LN $Q/logs/vb1
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | VB1 | $*" >> $R/events.log; }
q() { CODE=$C PYTHONPATH=$C $P -m tools.vb1.evalq "$@"; }
busy() { python3 $C/tools/vb1/card.py busy $CARD; }
echo "$(hostname) $$ $(date -u +%FT%TZ)" > $LN/$LANE.alive
ev "eval lane $LANE start on $CARD"
waiting=0; crashes=0
while true; do
  [ -f $R/STOP_EVAL ] && { ev "eval lane $LANE STOP_EVAL"; break; }
  if [ ! -f $E/SERVER ]; then sleep 120; continue; fi
  if why=$(busy); [ $? != 0 ]; then
    [ $waiting = 0 ] && ev "eval lane $LANE waits: $why"
    waiting=1; sleep 120; continue
  fi
  waiting=0
  gid=$(q next $LANE)
  case "$gid" in
    NONE|WAIT) sleep 60; continue;;
  esac
  read -r URL CK SETS < $E/SERVER
  rm -f $LN/$LANE.WANTED; echo $CARD > $LN/$LANE.run
  ( while true; do sleep 30; q touch $gid; busy > /dev/null || touch $LN/$LANE.WANTED; done ) &
  wp=$!
  bash $C/tools/vb1/isaac_eval.sh $C $G e${LANE}_${CK}_$gid --group $gid --ckpt $CK --server $URL --card $CARD \
    --lane $LANE --yield-file $LN/$LANE.WANTED
  rc=$?
  kill $wp 2> /dev/null; wait $wp 2> /dev/null
  q release $gid; rm -f $LN/$LANE.run
  if [ $rc = 3 ] || [ -f $LN/$LANE.WANTED ]; then
    rm -f $LN/$LANE.WANTED
    ev "eval lane $LANE yielded $CARD during $gid"
    grep -qx "$CARD" $LN/*.run $R/lanes/*.run 2> /dev/null || echo "$(hostname | sed 's/juhyoung-native-//'):$G freed by VB1 $(date -u +%FT%TZ)" >> $Q/out/l9/GPU_FREED
    continue
  fi
  if [ $rc != 0 ]; then
    crashes=$((crashes + 1)); ev "eval lane $LANE group $gid exit $rc (crash $crashes)"
    [ $crashes -ge 3 ] && { echo "eval lane $LANE: 3 crashes, last $gid" > $R/ALERT_eval_lane_$LANE; ev "ALERT eval lane $LANE 3 crashes -> stopped"; break; }
    sleep 60
  else
    crashes=0
  fi
done
rm -f $LN/$LANE.alive
