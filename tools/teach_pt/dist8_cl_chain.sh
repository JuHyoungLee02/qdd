#!/bin/bash
# E-DIST8 change-7 closed-loop chain on one pod: after <wait marker> appears, run each spec one after another with
# dist8_cl_boost.sh on the same 8 L8-X episodes as the first closed loop (pick_b_d-min.txt).
# usage: dist8_cl_chain.sh <code dir> <serve gpu> <render gpu> <port> <tag>:<merged>:<iface>:<h_depth> [...]
C=$1; SG=$2; RG=$3; PORT=$4; shift 4
EPS=$(cut -d' ' -f2- /data/harvest/logs/dist8/pick_b_d-min.txt | tr '\n' ' ')
for spec in "$@"; do
  IFS=: read -r tag m ifc hd <<< "$spec"
  until [ -f $m/config.json ]; do sleep 60; done
  bash $C/tools/teach_pt/dist8_cl_boost.sh $C $SG $RG $tag $m $ifc $PORT $hd $EPS
done
