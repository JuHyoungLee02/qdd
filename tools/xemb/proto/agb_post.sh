#!/bin/bash
# AgiBot full conversion (approved v3), pod 7a2a: waits for the 78dc chain to finish (CHAIN_END what=all ok=True),
# dumps proprio npz (python 3.11 + h5py), converts every selected task with kept episodes (python 3.12, SAM 3.1 +
# CoTracker3 on the first free GPU), then draws 30 random check rows (3 sheets). usage: agb_post.sh
R=/data/harvest/data/agibot
X=/data/harvest/out/xemb_proto
O=$X/points/agibot
L=/data/harvest/logs/agb_post.log
until grep -q "CHAIN_END what=all ok=True" $R/chain.log; do
  grep -q "CHAIN_END what=all ok=False" $R/chain.log && { echo "chain stopped (STOP_DISK?)" >> $L; exit 1; }
  sleep 300
done
echo "START $(date -u +%FT%TZ)" >> $L
cd $X/code
PYTHONPATH=.:/data/harvest/pylib_xemb_train /data/harvest/venv_train/bin/python -m xemb.agb_dump $R/keep >> $L 2>&1
TASKS=$(ls $R/keep/npz | sort -n | paste -sd, -)
G=""
while [ -z "$G" ]; do
  G=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' '$2 < 1000 {print $1; exit}')
  [ -z "$G" ] && sleep 120
done
echo "GPU $G tasks $TASKS" >> $L
SP=/data/harvest/venv_sam3/lib/python3.12/site-packages:/data/harvest/venv_e3st/lib/python3.12/site-packages
PY=/data/juhyoung_pi05/uvpython/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12
mkdir -p $O
TORCH_HOME=/data/harvest/cache/torch CUDA_VISIBLE_DEVICES=$G PYTHONPATH=.:/data/harvest/code_open8_b057c5a:/data/harvest/src/sam3:$SP \
  $PY -m xemb.agb_objpts $R/keep $R/meta $O $TASKS >> $L 2>&1
cat $O/records.jsonl $O/records_G.jsonl > $O/all.jsonl
$PY $X/scratch/agb_chk_sheet.py $O/all.jsonl $O/check 3 >> $L 2>&1
echo "DONE $(date -u +%FT%TZ) rows $(wc -l < $O/records.jsonl) G $(wc -l < $O/records_G.jsonl) tasks $(cut -d'"' -f0- $O/all.jsonl | grep -o '"task": "[0-9]*"' | sort -u | wc -l)" >> $L
