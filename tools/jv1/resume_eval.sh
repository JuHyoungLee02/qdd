#!/bin/bash
# E-JV1 closed-loop resume on the recreated x2 pod (10-01 21:5x KST; the old pod was OOMKilled 18:44 with 6 servers +
# 4 render lanes + 2 L9 lanes). User approval "고" covers x2 GPU1. Memory budget: pod <= 100 GiB.
#  0. finished episodes (ep.json) are kept; directories with garbled job names (lane stdin bug, fixed in this code) and
#     unfinished episode dirs (no ep.json) are moved to eval/_aside_<UTC> (not deleted)
#  1. servers on x2 GPU0: A x1 (:8181) + B x2 (:8171-8172) [JV1_NB]; SERVERS.json rewritten with this pod's IP
#  2. smoke: ONE lane, wait for its first new ep.json (Isaac chroot check on the new pod) -> then lanes up to JV1_LANES
#     (2), each lane starts an Isaac run only under the memory guard (tools/jv1/lane_eval.sh mem_ok)
#  3. end = all lanes exited, or JV1_CAP_S (8 h), or eval/STOP_EVAL -> servers down -> summary.json
#  4. x2:1 back to L9: bash $(cat /data/harvest/out/l9/CODE_CURRENT)/tools/l9/attach_x2.sh, then check that an L9
#     Isaac process appears on this pod within 20 min (events.log)
# usage: JCR_JOB=jv1_resume setsid nohup bash resume_eval.sh <code dir> > /dev/null 2>&1 < /dev/null &
C=$1; Q=/data/harvest; O=$Q/out/jv1; E=$O/eval; P=$Q/venv_train/bin/python
NL=${JV1_LANES:-2}; NB=${JV1_NB:-2}; CAP_S=${JV1_CAP_S:-28800}
CK_A=$Q/ckpt/jcr/jcr1_0P/last; CK_B=$Q/ckpt/jv1/b_P/last
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | JV1 | $*" >> $O/events.log; }
memg() { echo $(( $(cat /sys/fs/cgroup/memory.current) / 1073741824 )); }
n_ep() { ls $E/[ABC]_[ZR]_*/*/s*/ep.json 2>/dev/null | wc -l; }
lanes_alive() { for d in /proc/[0-9]*; do tr '\0' ' ' < $d/cmdline 2>/dev/null | grep -qF tools/jv1/lane_eval.sh && echo ${d#/proc/}; done; }
cd $C
A=$E/_aside_$(date -u +%Y%m%dT%H%M%S); mkdir -p $A
for d in $E/*/; do b=$(basename $d)
  case "$b" in lanes|_aside_*) continue;; esac
  echo "$b" | grep -qE '^[ABC]_[ZR]_(clean|dist)$' || { mv $d $A/; continue; }
  for e in $d*/s*/; do [ -f $e/ep.json ] || { mkdir -p $A/$b/$(basename $(dirname $e)); mv $e $A/$b/$(basename $(dirname $e))/; }; done
done
rm -f $E/lanes/*.WANTED $E/STOP_EVAL
ev "resume (code $C): kept $(n_ep)/400 finished episodes, garbled / unfinished dirs -> $(basename $A)"
for p in 8181; do bash tools/jcr/train.sh $C 0 jv1_srv_A$p -m harvest.jcr.serve --ckpt $CK_A --port $p & done
for k in $(seq $NB); do p=$((8170 + k)); bash tools/jcr/train.sh $C 0 jv1_srv_B$p -m harvest.jv1.serve --ckpt $CK_B --port $p & done
for p in 8181 $(seq 8171 $((8170 + NB))); do
  for i in $(seq 90); do curl -s localhost:$p/health >/dev/null && break; sleep 10; done
done
IP=$(hostname -i | awk '{print $1}')
$P -c "import json;json.dump({'A':['http://$IP:8181'],'B':['http://$IP:%d'%p for p in range(8171,8171+$NB)]},open('$E/SERVERS.json','w'))"
ev "servers up on x2 GPU0 ($IP): A x1, B x$NB; pod memory $(memg) GiB"
n0=$(n_ep)
bash tools/jv1/start_lanes.sh $C 1 1 >> $Q/logs/jcr/jv1_eval.log 2>&1
for i in $(seq 60); do [ $(n_ep) -gt $n0 ] && break; [ -z "$(lanes_alive)" ] && break; sleep 30; done
if [ $(n_ep) -le $n0 ]; then
  ev "ALERT smoke: no new episode in 30 min on x2:1 (see /data/harvest/logs/strip8/jcr_jv1_x2_g1_1.log); stopping"
  touch $E/lanes/jv1_x2_g1_1.WANTED; echo smoke > $E/ALERT_resume
else
  ev "smoke OK (1 new episode on x2:1), pod memory $(memg) GiB -> lanes to $NL"
  for k in $(seq 2 $NL); do
    LN=jv1_x2_g1_$k
    setsid nohup bash tools/jv1/lane_eval.sh $C 1 $LN > /dev/null 2>&1 < /dev/null &
    sleep 120
  done
fi
t0=$(date +%s)
while [ -n "$(lanes_alive)" ] && [ $(( $(date +%s) - t0 )) -lt $CAP_S ] && [ ! -f $E/STOP_EVAL ]; do
  sleep 600; ev "progress $(n_ep)/400, pod memory $(memg) GiB"
done
for k in $(seq $NL); do touch $E/lanes/jv1_x2_g1_$k.WANTED; done
for i in $(seq 30); do [ -z "$(lanes_alive)" ] && break; sleep 30; done
for k in $(seq $NL); do bash tools/jcr/stop.sh jv1_x2_g1_$k >> $Q/logs/jcr/jv1_eval.log 2>&1; done
for p in 8181 $(seq 8171 $((8170 + NB))); do bash tools/jcr/stop.sh jv1_srv_$([ $p = 8181 ] && echo A || echo B)$p >> $Q/logs/jcr/jv1_eval.log 2>&1; done
PYTHONPATH=$C $P tools/jv1/summary.py --eval $E --out $E/summary.json >> $Q/logs/jcr/jv1_eval.log 2>&1
ev "eval end: $(n_ep)/400 -> $(tail -1 $Q/logs/jcr/jv1_eval.log | cut -c1-400)"
L9C=$(cat $Q/out/l9/CODE_CURRENT)
bash $L9C/tools/l9/attach_x2.sh >> $Q/logs/jcr/jv1_eval.log 2>&1
ev "attach_x2.sh ($L9C) exit $?: $(tail -1 $Q/logs/jcr/jv1_eval.log | cut -c1-200)"
for i in $(seq 20); do
  n=$(for d in /proc/[0-9]*; do tr '\0' '\n' < $d/environ 2>/dev/null | grep -q '^IR_INST=l9_' && echo x; done | wc -l)
  [ $n -gt 0 ] && break; sleep 60
done
[ $n -gt 0 ] && ev "L9 back on x2:1 ($n Isaac procs)" || { ev "ALERT L9 not back on x2:1 20 min after attach_x2.sh"; touch $E/ALERT_l9_attach; }
