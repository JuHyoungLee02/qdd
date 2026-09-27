#!/bin/bash
# Build one L8-D training format of bundle b2 in K parallel processes (episode round robin) and join the parts into
# /data/harvest/out/final35/data/b2src/train_<fmt>.jsonl (the aux draws differ from a single-process build: the build rng
# runs per part). usage: split_build.sh <code dir> <fmt e.g. pt> <K> [pid of a slower single build to stop when done]
C=$1; F=$2; K=$3; KILL=$4
P=/data/harvest/venv_train/bin/python
S=/data/harvest/out/final35/data/b2src; W=/data/harvest/out/final35/data/split_$F; L=/data/harvest/logs/final35
mkdir -p $W $L
cd $C; export PYTHONPATH=$C
$P tools/final35/split_manifest.py /data/harvest/out/teach_l8d/bundles/b2.json $W $K >> $L/split_$F.log 2>&1
for i in $(seq 0 $((K - 1))); do
  nice $P tools/teach_l8d/build.py /data/harvest/out/teach_l8d/collect $W/p$i train $F --manifest $W/part$i.json \
    >> $L/split_${F}_$i.log 2>&1 &
done
wait
for i in $(seq 0 $((K - 1))); do [ -s $W/p$i/train_$F.jsonl ] || { echo "SPLIT_FAIL $F part $i $(date -u +%FT%TZ)" >> $L/chain.log; exit 1; }; done
[ -f $S/train_$F.jsonl ] && { echo "SPLIT_SKIP $F single build finished first $(date -u +%FT%TZ)" >> $L/chain.log; exit 0; }
cat $W/p*/train_$F.jsonl > $S/train_$F.jsonl.tmp && mv $S/train_$F.jsonl.tmp $S/train_$F.jsonl
echo "SPLIT_DONE $F $(wc -l < $S/train_$F.jsonl) rows $(date -u +%FT%TZ)" >> $L/chain.log
[ -n "$KILL" ] && kill $KILL 2>/dev/null && echo "SPLIT_STOPPED_SINGLE $KILL" >> $L/chain.log
