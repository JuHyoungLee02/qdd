#!/bin/bash
# E-GP2 early pilot training run (prereg_gp2 §4): one "<arm> <seed>" run on one 78dc card (1-3 only; GPU0 belongs to
# another team), same recipe as tools/l9r/hcam8_worker.sh (Qwen3-VL-8B LoRA r16, micro 8 x accum 2, steps from
# steps.txt), card lock, learning-curve snapshots at 25 % and 50 % of the steps (exported to merged models on CPU by
# tools/gp2/gp2_export.py), final adapter merged with harvest.teach_l8.merge.
# Yields the card when /data/harvest/out/vla/GPU_WANTED names "78dc:<card>" (a line without "GP2"): stops the run
# (state kept, --resume later). usage: gp2_worker.sh <code dir> <gpu 1|2|3> <arm a|b> <seed>
C=$1; G=$2; ARM=$3; SEED=$4
O=/data/harvest/out/gp2; L=/data/harvest/logs/gp2; R=${ARM}_s$SEED; RUN=$O/run_$R
mkdir -p $L $O/snap $O/merged
log() { echo "$(date -u +%FT%TZ) 78dc gpu$G $*" >> $L/gp2.log; }
case "$(hostname)-$G" in *78dc-1|*78dc-2|*78dc-3) ;; *) echo "refused: $(hostname) GPU $G"; exit 2;; esac
wanted() {  # GPU_WANTED line "<host>:<cards> ..." naming this card (cards = list with commas, or g = all)
  [ -f /data/harvest/out/vla/GPU_WANTED ] || return 1
  while read -r tok rest; do
    case "$tok $rest" in *GP2*) continue;; esac
    [ "${tok%%:*}" = 78dc ] || continue
    c=${tok#*:}; [ "$c" = g ] && return 0
    case ",$c," in *",$G,"*) return 0;; esac
  done < /data/harvest/out/vla/GPU_WANTED
  return 1
}
S=$(grep "^$ARM " $O/steps.txt | tail -n 1 | cut -d' ' -f2)
[ -z "$S" ] && { log "NO_STEPS $R"; exit 1; }
exec 9> $O/card_78dc_$G.lock; flock 9
log "START $R steps=$S"
RES=""; [ -d $RUN/state ] && RES="--resume"
J=train_gp2_$R
setsid nohup bash $C/tools/teach_pt/py.sh train $G $J $C harvest.teach_l8.train --data $O/train_$ARM.jsonl --out $RUN \
  --epochs 3 --max-steps $S --micro 8 --accum 2 --log-every 10 --save-every 100 --seed $SEED $RES < /dev/null > /dev/null 2>&1 &
sleep 60
Q1=$((S / 4)); Q2=$((S / 2))
# watch: snapshots, GPU_WANTED, end of training (py.sh writes EXIT to the job log)
while true; do
  if wanted; then
    log "GPU_WANTED 78dc:$G -> stopping $R (state kept)"; bash $C/tools/teach_pt/stop.sh $J >> $L/gp2.log 2>&1
    touch $O/YIELDED_$R; flock -u 9; exit 0
  fi
  st=$(grep -o '"step": [0-9]*' $RUN/state/meta.json 2>/dev/null | grep -o '[0-9]*$')
  for q in $Q1 $Q2; do
    if [ -n "$st" ] && [ "$st" -ge "$q" ] && [ ! -d $O/snap/${R}_q$q ]; then
      mkdir -p $O/snap/${R}_q$q.tmp && cp $RUN/state/trainable.pt $RUN/state/meta.json $O/snap/${R}_q$q.tmp/ \
        && mv $O/snap/${R}_q$q.tmp $O/snap/${R}_q$q && log "SNAP $R q$q at step $st"
      # CPU export in the background (CUDA hidden): merged_<run>_q<steps>
      CUDA_VISIBLE_DEVICES= setsid nohup bash $C/tools/teach_pt/py.sh train - export_gp2_${R}_q$q $C tools/gp2/gp2_export.py \
        $O/snap/${R}_q$q $O/merged/${R}_q$q < /dev/null > /dev/null 2>&1 &
    fi
  done
  grep -q '^EXIT' /data/harvest/logs/teach_pt/$J.log 2>/dev/null && \
    [ "$(grep -c '^START' /data/harvest/logs/teach_pt/$J.log)" -le "$(grep -c '^EXIT' /data/harvest/logs/teach_pt/$J.log)" ] && break
  sleep 60
done
E=$(ls -d $RUN/epoch* 2>/dev/null | sort -V | tail -1)
[ -z "$E" ] && { log "TRAIN_FAIL $R"; flock -u 9; exit 1; }
bash $C/tools/teach_pt/py.sh train $G merge_gp2_$R $C harvest.teach_l8.merge --adapter $E --out $O/merged/${R}_final.tmp \
  && mv $O/merged/${R}_final.tmp $O/merged/${R}_final
log "TRAIN_DONE $R $E"
flock -u 9; exec 9>&-
