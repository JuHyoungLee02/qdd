#!/bin/bash
# Waits (on the pod) for BOOST1_DONE in the lanes log, stops the boost1 vLLM, then runs the boost2 chain on the same GPU.
# usage: after_boost1.sh <code dir> <gpu> <N per dir>
C=$1; G=$2; N=${3:-8}
L=/data/harvest/logs/strip8
until grep -q "BOOST1_DONE" $L/lanes.log; do sleep 60; done
bash $C/tools/teach_strip8/stop.sh bst_bd
B2_PICK_GREP=^drx B2_WAIT_MAIN=1 bash $C/tools/teach_strip8/boost2.sh $C $G $N
