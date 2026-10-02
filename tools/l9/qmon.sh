#!/bin/bash
# L9v2-general pod-side quality-monitor loop (owner order 2026-10-03, no Claude in the loop): runs qmon9.py (same
# dir) once immediately, then every 7200 s, over the given collect roots. Stop file /data/harvest/out/l9/STOP_QMON
# ends the loop -- checked every 60 s inside the sleep, so a stop lands within a minute, not at the end of a 2 h wait.
#
# usage: qmon.sh <PYTHONPATH code dir> <collect root>... [-- <extra qmon9.py flags, e.g. --spec L9v2-general>]
# Deploy qmon.sh + qmon9.py + diversity9.py + robot_gate9.py + rate9.py together, all 5 files in the SAME dir
# (normally /data/harvest/out/l9/) -- qmon9.py imports the sibling tool scripts from its own directory; <PYTHONPATH
# code dir> only needs to resolve harvest.l9.{build9,specgate9,alloc9} (the label-spec / build code, which DOES
# track production code changes -- pass the collection pods' current code dir, e.g. $(cat
# /data/harvest/out/l9/CODE_CURRENT) if that pointer is kept fresh, otherwise a fixed known-good checkout).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
CODE="${1:?usage: qmon.sh <PYTHONPATH code dir> <collect root>... [-- extra qmon9.py flags]}"
shift
ROOTS=()
EXTRA=()
in_extra=0
for a in "$@"; do
  if [ "$a" = "--" ]; then in_extra=1; continue; fi
  if [ "$in_extra" = "1" ]; then EXTRA+=("$a"); else ROOTS+=("$a"); fi
done
STOP="${QMON_STOP:-/data/harvest/out/l9/STOP_QMON}"
PY="${QMON_PY:-/data/harvest/venv_sam3/bin/python}"
LOG="${QMON_LOG:-/data/harvest/out/l9/qmon_run.log}"
INTERVAL=7200

while :; do
  if [ -f "$STOP" ]; then
    echo "$(date -u +%FT%TZ) STOP_QMON seen before round, exiting" >>"$LOG"
    break
  fi
  echo "$(date -u +%FT%TZ) round start" >>"$LOG"
  PYTHONPATH="$CODE" "$PY" "$HERE/qmon9.py" "${ROOTS[@]}" "${EXTRA[@]}" >>"$LOG" 2>&1
  slept=0
  stopped=0
  while [ "$slept" -lt "$INTERVAL" ]; do
    if [ -f "$STOP" ]; then
      stopped=1
      break
    fi
    sleep 60
    slept=$((slept + 60))
  done
  [ "$stopped" = "1" ] && { echo "$(date -u +%FT%TZ) STOP_QMON seen during sleep, exiting" >>"$LOG"; break; }
done
