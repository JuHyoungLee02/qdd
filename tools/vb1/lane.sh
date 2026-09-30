#!/bin/bash
# E-VB1 render lane (docs/stage3/prereg_vb1.md change 1): runs groups of tools/vb1/eps.py on one render card, one Isaac
# process at a time. The lane only works while the card is free for VB1 (tools/vb1/card.py: not named in L9 GPU_WANTED
# and no non-VB1 process on it); otherwise it waits. While a group runs a watcher refreshes the group lock and, when
# the card becomes busy, touches the lane's yield file: rec.py ends after the current episode (exit 3). The last VB1
# lane yielding a card appends "<pod>:<gpu> freed by VB1 <UTC>" to /data/harvest/out/l9/GPU_FREED.
# Before the smoke group g0000 is checked (eps.py smoke) no other group is handed out.
# usage: nohup bash lane.sh <code dir> <pod: 7a2a|x2> <gpu> <lane tag> > /dev/null 2>&1 &     stop: touch $R/STOP
C=$1; POD=$2; G=$3; LANE=$4
Q=/data/harvest; R=$Q/out/vb1; LN=$R/lanes; P=$Q/venv_train/bin/python; CARD=$POD:$G
mkdir -p $LN $Q/logs/vb1
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | VB1 | $*" >> $R/events.log; }
eps() { CODE=$C PYTHONPATH=$C $P -m tools.vb1.eps "$@"; }
busy() { python3 $C/tools/vb1/card.py busy $CARD; }
echo "$(hostname) $$ $(date -u +%FT%TZ)" > $LN/$LANE.alive
ev "lane $LANE start on $CARD"
waiting=0; crashes=0
while true; do
  [ -f $R/STOP ] && { ev "lane $LANE STOP file"; break; }
  if why=$(busy); [ $? != 0 ]; then
    [ $waiting = 0 ] && ev "lane $LANE waits: $why"
    waiting=1; sleep 120; continue
  fi
  [ $waiting = 1 ] && ev "lane $LANE resumes on $CARD"
  waiting=0
  gid=$(eps next $LANE)
  case "$gid" in
    NONE) ev "lane $LANE LANE_DONE"; break;;
    WAIT) sleep 60; continue;;
    ALERT*) ev "lane $LANE stops: $gid"; break;;
  esac
  rm -f $LN/$LANE.WANTED; echo $CARD > $LN/$LANE.run
  ( while true; do sleep 30; eps touch $gid; busy > /dev/null || touch $LN/$LANE.WANTED; done ) &
  wp=$!
  bash $C/tools/vb1/isaac.sh $C $G ${LANE}_$gid --group $gid --card $CARD --lane $LANE --yield-file $LN/$LANE.WANTED
  rc=$?
  kill $wp 2> /dev/null; wait $wp 2> /dev/null
  eps release $gid; rm -f $LN/$LANE.run
  if [ "$gid" = g0000 ]; then
    res=$(eps smoke); ev "smoke check: $res"
  fi
  if [ $rc = 3 ] || [ -f $LN/$LANE.WANTED ]; then
    rm -f $LN/$LANE.WANTED
    ev "lane $LANE yielded $CARD during $gid ($(busy))"
    grep -qx "$CARD" $LN/*.run 2> /dev/null || echo "$(hostname | sed 's/juhyoung-native-//'):$G freed by VB1 $(date -u +%FT%TZ)" >> $Q/out/l9/GPU_FREED
    continue
  fi
  if [ $rc != 0 ]; then
    crashes=$((crashes + 1)); ev "lane $LANE group $gid exit $rc (crash $crashes)"
    [ $crashes -ge 3 ] && { echo "lane $LANE: 3 crashes, last $gid" > $R/ALERT_lane_$LANE; ev "ALERT lane $LANE 3 crashes -> stopped"; break; }
    sleep 60
  else
    crashes=0
  fi
done
rm -f $LN/$LANE.alive
