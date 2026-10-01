#!/bin/bash
# E-JV1 closed-loop lane (docs/stage3/prereg_jv1.md §4, §8) on an APPROVED render card (7a2a GPU 0/1/3 or x2 GPU 1).
# Walks $E/jobs.txt in order; each job = one arm x condition x set x variant over DEV seeds 0-19 (harvest.jcr.record
# --mode eval --src truth = P0 commands); episodes are claimed per directory, so any number of lanes share the jobs.
# Yields like the JCR lanes: /data/harvest/out/l9/GPU_WANTED naming this card (or empty / all) or $E/lanes/<lane>.WANTED
# -> the running episode finishes, the lane exits and appends a GPU_FREED line.
# usage: lane_eval.sh <code dir> <gpu> <lane>      (IR_INST=strip8_jcr_<lane>: tools/jcr/stop.sh <lane> stops it)
C=$1; G=$2; LN=$3
Q=/data/harvest; E=$Q/out/jv1/eval; L=$Q/logs/jcr; VID=$Q/videos/jv1; DIST=$Q/out/jcr/upper_err_dist.json
W1=$Q/out/l9/GPU_WANTED; W2=$E/lanes/$LN.WANTED
POD=$(hostname); case "$POD" in *x2*) TAG=x2;; *x3*) TAG=x3;; *) TAG=7a2a;; esac
mkdir -p $E/lanes $L $VID
log() { echo "$(date -u +%FT%TZ) $LN $*" >> $L/jv1_lanes.log; }
wanted() { [ -f $W2 ] && return 0; [ -f $W1 ] || return 1; [ -s $W1 ] || return 0
  grep -qiE "(^|[^a-z0-9-])($TAG:([0-9,]*,)?$G(,|[^0-9]|$)|all)" $W1; }
url() {  # replica of arm $1 for this lane (SERVERS.json written by chain_eval.sh)
  /data/harvest/venv_train/bin/python -c "import json,zlib;u=json.load(open('$E/SERVERS.json'))['$1'];print(u[zlib.crc32(b'$LN')%len(u)])" < /dev/null; }
# memory guard (x2 OOMKilled 10-01 18:44 with 6 servers + 4 render lanes + 2 L9 lanes): an Isaac run starts only while
# the pod's cgroup memory + one Isaac (JV1_ISAAC_GB, 15) stays under JV1_MEM_BUDGET_GB (100)
mem_ok() { local cur; cur=$(cat /sys/fs/cgroup/memory.current 2>/dev/null || echo 0)
  [ $(( cur / 1073741824 + ${JV1_ISAAC_GB:-15} )) -le ${JV1_MEM_BUDGET_GB:-100} ]; }
log "LANE_START gpu=$G code=$C"
# jobs on fd 3: commands inside the loop must not eat the job lines (10-01 bug: names like '_Z_clean')
while read -r NAME V EXE ARM LAT PER DIS <&3; do
  [ -z "$NAME" ] || [ "${NAME:0:1}" = "#" ] && continue
  for try in 1 2 3; do
    wanted && { echo "$POD:$G freed $(date -u +%FT%TZ) (jv1 $LN)" >> $Q/out/l9/GPU_FREED; log "YIELD_EXIT"; exit 0; }
    n=$(ls $E/$NAME/$V/s*/ep.json 2>/dev/null | wc -l); [ "$n" -ge 20 ] && break
    X="--executor $EXE"; [ "$ARM" != - ] && X="$X --jcr-url $(url $ARM)"
    [ "$LAT" != - ] && X="$X --rt-lat $LAT --rt-period $PER"
    [ "$DIS" = 1 ] && X="$X --eval-disturb"
    until mem_ok; do sleep 30; done
    bash $C/tools/teach_strip8/isaac.sh $C $G jcr_$LN harvest.jcr.record --mode eval --src truth --variant $V \
      --seeds 0-19 --out $E/$NAME --vid-root $VID/$NAME --dist $DIST --envelope B $X --yield-files $W2 --owner $LN       < /dev/null
    log "JOB $NAME/$V try=$try done=$(ls $E/$NAME/$V/s*/ep.json 2>/dev/null | wc -l)/20"
  done
done 3< $E/jobs.txt
log "LANE_DONE"
