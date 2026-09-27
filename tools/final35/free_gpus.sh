#!/bin/bash
# Print the GPUs of <candidates e.g. 0,1,2> on this pod that are free (used memory < 1 GB), comma separated; with
# <min> given, wait (checking every 60 s) until at least <min> of them are free. usage: free_gpus.sh <candidates> [min]
CAND=$1; MIN=${2:-1}
while true; do
  F=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | tr -d ' ' |
      awk -F, -v c=",$CAND," 'index(c, "," $1 ",") && $2 < 1000 {print $1}' | paste -sd, -)
  n=$(echo "$F" | tr ',' '\n' | grep -c .)
  [ "$n" -ge "$MIN" ] && { echo "$F"; exit 0; }
  sleep 60
done
