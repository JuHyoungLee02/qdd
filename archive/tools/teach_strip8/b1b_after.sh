#!/bin/bash
# boost1b: after lane <wait tag> is done, run <plan> on GPU <g> as lane <tag> (the same served B-D).
# usage: b1b_after.sh <code dir> <gpu> <port> <served name> <plan file> <tag> <wait tag>
C=$1; W=$7
until grep -q "B1B_LANE_DONE $W " /data/harvest/logs/strip8/lanes.log; do sleep 30; done
bash $C/tools/teach_strip8/b1b_run_plan.sh $1 $2 $3 $4 $5 $6
