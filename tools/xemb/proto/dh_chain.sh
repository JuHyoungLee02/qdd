#!/bin/bash
# D/H depth pack chain (user-log 156): wait for the BEHAVIOR re-download and the ManiSkill shards, convert both, gate and
# merge into /data/harvest/out/xemb/dh_pack; writes DONE there at the end.
X=/data/harvest/out/xemb_proto
L=/data/harvest/logs/dh_chain.log
PY=/data/harvest/venv_e3st/bin/python
until grep -q "total MB" /data/harvest/logs/b1k_dh_fetch.log; do sleep 60; done
while pgrep -f "maniskill_dataset_converted_externally_to_rlds-train.tfrecord" > /dev/null; do sleep 60; done
cd $X/code
echo "START $(date -u +%FT%TZ)" >> $L
$PY -m xemb.src_behavior_dh /data/harvest/data/b1k_dh $X/dh_b1k 60 >> $L 2>&1
$PY -m xemb.src_maniskill "/data/harvest/data/oxe_depth/maniskill/shard-*" $X/dh_maniskill 2000 >> $L 2>&1
$PY -m xemb.dh_pack /data/harvest/out/xemb/dh_pack $X/dh_b1k $X/dh_maniskill >> $L 2>&1
echo "DONE $(date -u +%FT%TZ)" >> $L
touch /data/harvest/out/xemb/dh_pack/DONE
