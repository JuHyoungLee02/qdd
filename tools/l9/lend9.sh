#!/bin/bash
# L9 card lending (pod-local watcher). Lends one GPU of THIS pod to another job and takes it back:
#   lend9.sh <gpu> <ready file> <start cmd ("-" = none)> <done file> <max lent s> <return cmd ("-" = none)> <tag>
#            <supervisor restart cmd>
# 1. waits for <ready file>; creates /data/harvest/out/l9/yield/<host>_<gpu> (run9 stops between episodes, lanes stop
#    before their next job, supervisors do not restart lanes there); waits until no L9 Isaac process uses the card;
#    removes the card from GPU_WANTED; runs <start cmd>.
# 2. waits for <done file> or <max lent s>; runs <return cmd>; removes the yield file; adds the card back to
#    GPU_WANTED; appends "<card> returned by <tag>" to GPU_FREED; runs <supervisor restart cmd>.
G=$1; READY=$2; START=$3; DONE=$4; MAX=$5; RET=$6; TAG=$7; RESTART=$8
L=/data/harvest/out/l9
H=$(hostname)
case "$H" in *-x2) CARD="x2:$G";; *-x3) CARD="x3:$G";; *) CARD="7a2a:$G";; esac
log() { echo "$(date -u +%FT%TZ) lend9 $CARD $TAG: $*" >> $L/lend9.log; }
wanted() {  # wanted add|remove
  python3 - "$1" "$CARD" <<'EOF'
import sys
op, card = sys.argv[1], sys.argv[2]
host, g = card.split(":")
p = "/data/harvest/out/l9/GPU_WANTED"
toks = open(p).read().split() if __import__("os").path.exists(p) else []
cards = {}
for t in toks:
    h, cs = t.split(":")
    cards[h] = [c for c in cs.split(",") if c]
cur = cards.setdefault(host, [])
if op == "remove" and g in cur:
    cur.remove(g)
if op == "add" and g not in cur:
    cur.append(g)
    cur.sort()
open(p, "w").write(" ".join(f"{h}:{','.join(cs)}" for h, cs in cards.items() if cs) + "\n")
EOF
}
busy() {  # an L9 Isaac process on this card
  for p in /proc/[0-9]*; do
    e=$(tr '\0' '\n' < $p/environ 2>/dev/null) || continue
    echo "$e" | grep -q '^IR_INST=l9_' || continue
    echo "$e" | grep -q "^CUDA_VISIBLE_DEVICES=$G$" && return 0
  done
  return 1
}
log "waiting for $READY"
until [ -f "$READY" ]; do sleep 30; done
mkdir -p $L/yield && touch $L/yield/${H}_$G
log "yield file set; waiting for the running episodes to end"
n=0
while busy; do sleep 20; n=$((n + 20)); [ $n -ge 1800 ] && { log "still busy after 30 min: proceeding"; break; }; done
wanted remove
[ "$START" != "-" ] && { log "start: $START"; bash -c "$START" >> $L/lend9.log 2>&1; }
log "lent"
t0=$(date +%s)
until [ -f "$DONE" ] || [ $(( $(date +%s) - t0 )) -ge $MAX ]; do sleep 60; done
[ -f "$DONE" ] && log "done file seen" || log "max lent time reached"
[ "$RET" != "-" ] && { log "return: $RET"; bash -c "$RET" >> $L/lend9.log 2>&1; }
rm -f $L/yield/${H}_$G
wanted add
echo "$CARD returned by $TAG $(date -u +%FT%TZ)" >> $L/GPU_FREED
log "returned; restarting lanes"
bash -c "$RESTART" >> $L/lend9.log 2>&1
log "end"
