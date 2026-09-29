#!/bin/bash
# Supervisor for main35_chain.sh: restart it after an unexpected exit (up to 20 times, 10 min apart); stop for good on
# MAIN35_DONE or a gate failure (exit 3). usage: main35_super.sh <code dir>
C=$1; O=/data/harvest/out/main35; L=/data/harvest/logs/main35; mkdir -p $L
for n in $(seq 1 20); do
  [ -f $O/MAIN35_DONE ] && break
  bash $C/tools/final35/main35_chain.sh $C; rc=$?
  [ -f $O/MAIN35_DONE ] && break
  [ $rc = 3 ] && { echo "SUPER_STOP gate $(date -u +%FT%TZ)" >> $L/main35.log; exit 3; }
  echo "SUPER_RESTART $n rc=$rc $(date -u +%FT%TZ)" >> $L/main35.log
  sleep 600
done
echo "SUPER_END $(date -u +%FT%TZ)" >> $L/main35.log
