#!/bin/bash
# Final 35B (prereg_final35.md): training files from the frozen L8-X bundle b2 (docs/stage3/l8d_bundle_b2.json).
#   b2 -> train_pt / train_nd-xyz (tools/teach_l8d/build.py --manifest) -> d-min / h-min (tools/teach_pt/convert_min.py)
#   -> + open point packs, additive (tools/teach_pt/mix_pack.py). usage: build.sh <code dir> <d|h> [<pack>:<share> ...]
C=$1; T=$2; shift 2
P=/data/harvest/venv_train/bin/python
S=/data/harvest/out/final35/data/b2src; D=/data/harvest/out/final35/data; L=/data/harvest/logs/final35
MAN=/data/harvest/out/teach_l8d/bundles/b2.json
mkdir -p $S $D $L
cd $C; export PYTHONPATH=$C
case $T in d|dn) F=pt; TR=d-min;; h|hc) F=nd-xyz; TR=h-min;; esac
[ -f $S/train_$F.jsonl ] || nice $P tools/teach_l8d/build.py /data/harvest/out/teach_l8d/collect $S train $F \
  --manifest $MAN >> $L/build_$T.log 2>&1
[ -f $D/train_$TR.jsonl ] || nice $P tools/teach_pt/convert_min.py $S/train_$F.jsonl $D $TR train_$TR.jsonl >> $L/build_$T.log 2>&1
if [ $# -gt 0 ]; then
  rm -f $D/train_${T}_mix.jsonl  # never write through the no-pack symlink onto the base file
  nice $P tools/teach_pt/mix_pack.py $D/train_$TR.jsonl $D/train_${T}_mix.jsonl "$@" >> $L/build_$T.log 2>&1
else
  ln -sfn $D/train_$TR.jsonl $D/train_${T}_mix.jsonl
fi
echo "BUILD_DONE $T $(wc -l < $D/train_${T}_mix.jsonl) rows $(date -u +%FT%TZ)" >> $L/chain.log
