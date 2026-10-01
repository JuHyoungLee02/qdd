#!/bin/bash
# Throttle MY ProcTHOR room import (tools.l9.assets.rooms9_table, procthor-10k-train) without losing its work:
# renice the parent and its pool workers to 19 and let only half the workers run at any moment (the other half
# SIGSTOPped, rotated every 30 s so every task finishes; new pool workers are picked up each cycle). Exits (and
# SIGCONTs everything) when the import parent is gone. Owner decision 10-02: CPU quota is saturated.
PY="/opt/conda/bin/python3 -m tools.l9.assets.rooms9_table --set procthor-10k-train"
cmd_of() { tr '\000' ' ' < /proc/$1/cmdline 2>/dev/null; }
find_parent() {  # the import's main python (its parent is the launching bash, not another import python)
  for d in /proc/[0-9]*; do
    p=${d#/proc/}
    c=$(cmd_of $p)
    case "$c" in
      "$PY"*)
        pp=$(awk '{print $4}' $d/stat 2>/dev/null)
        case "$(cmd_of $pp)" in "/opt/conda/bin/python3"*) ;; *) echo $p; return;; esac;;
    esac
  done
}
P=$(find_parent)
[ -z "$P" ] && { echo "no import running"; exit 0; }
echo "parent $P"
renice -n 19 -p $P >/dev/null
k=0
while [ -d /proc/$P ]; do
  kids=$(for d in /proc/[0-9]*; do [ "$(awk '{print $4}' $d/stat 2>/dev/null)" = "$P" ] && echo ${d#/proc/}; done | sort -n)
  n=$(echo $kids | wc -w); half=$(( (n + 1) / 2 )); i=0
  for c in $kids; do
    renice -n 19 -p $c >/dev/null 2>&1
    if [ $(( (i + k) % n )) -lt $half ]; then kill -CONT $c 2>/dev/null; else kill -STOP $c 2>/dev/null; fi
    i=$((i + 1))
  done
  echo "$(date -u +%FT%TZ) workers=$n running=$half"
  k=$((k + 1)); sleep 30
done
for d in /proc/[0-9]*; do case "$(cmd_of ${d#/proc/})" in *rooms9_table*) kill -CONT ${d#/proc/} 2>/dev/null;; esac; done
echo "import ended $(date -u +%FT%TZ)"
