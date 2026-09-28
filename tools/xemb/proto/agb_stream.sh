#!/bin/bash
# AgiBot World Beta: stream one tar from HF straight into tar -x and keep only the listed episode ids (nothing of the
# tar is written to disk except the selected members). Disk rule as in xemb/agb_fetch.py: stop (STOP_DISK) when
# du(ROOT) >= 2.7 TB; never delete anything. usage: agb_stream.sh <repo path of tar> <out subdir> <episode id> [...]
ROOT=/data/harvest/data/agibot
P=$1; SUB=$2; shift 2
USED=$(du -sb $ROOT | cut -f1)
if [ "$USED" -ge 2700000000000 ]; then
  echo "$(date -u +%FT%TZ) STOP_DISK used=$USED before stream $P" >> $ROOT/disk.log
  touch $ROOT/STOP_DISK; exit 3
fi
OUT=$ROOT/extract/$SUB; mkdir -p $OUT
PAT=(); for e in "$@"; do PAT+=("*$e*"); done
HF=/data/harvest/data/agibot/.hf_hdr  # token via a header file (mode 600): never in argv / ps
[ -f $HF ] || { umask 077; printf 'Authorization: Bearer %s\n' "$(cat /data/.hf_token)" > $HF; }
curl -s -L -m 36000 -H @$HF "https://huggingface.co/datasets/agibot-world/AgiBotWorld-Beta/resolve/main/$P" \
  | tar -x -C $OUT --wildcards "${PAT[@]}" 2>> $ROOT/stream_err.log
echo "$(date -u +%FT%TZ) STREAM $P -> $SUB ids=$* used_after=$(du -sb $ROOT | cut -f1)" >> $ROOT/disk.log
