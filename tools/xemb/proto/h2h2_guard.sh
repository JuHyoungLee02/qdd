#!/bin/bash
# E-H2H-T2: arms moved to fe08 GPU2 must not run again on e9f3. When an e9f3 lane logs START for a moved arm, stop that
# lane (its last arm) and anything started for that arm on this pod. usage (e9f3): h2h2_guard.sh <arm_sN> [...]
L=/data/harvest/logs/h2h2/lanes.log
K=/data/harvest/out/xemb_proto/scratch/killsh.py
PY=/data/juhyoung_pi05/uvpython/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12
left=("$@")
while [ ${#left[@]} -gt 0 ]; do
  rest=()
  for a in "${left[@]}"; do
    line=$(grep -E "START $a .*gpu=${GUARD_GPUS:-[4-7]}$" $L | head -n 1)  # e9f3 lane GPUs only (other pods reuse numbers: set GUARD_GPUS)
    if [ -n "$line" ]; then
      g=$(echo "$line" | grep -o "gpu=[0-9]*" | cut -d= -f2)
      $PY $K "h2h2_lane.sh $g " >> /data/harvest/logs/h2h2/guard.log 2>&1
      $PY $K "$a" >> /data/harvest/logs/h2h2/guard.log 2>&1
      echo "GUARD stopped e9f3 lane gpu=$g at $a $(date -u +%FT%TZ)" >> $L
    else
      rest+=("$a")
    fi
  done
  left=("${rest[@]}")
  sleep 30
done
