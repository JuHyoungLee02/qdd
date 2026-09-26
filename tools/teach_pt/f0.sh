#!/bin/bash
# E-PT F0 (prereg_pt.md §5.1) + G0(a): build the DEV per-arm files, score each arm's truth answers, then the zero-shot
# Qwen3-VL-8B (vLLM served as pt_zs on 127.0.0.1:8394) on DEV control rows: pt (0-1000, primary), pt (pixel wording),
# and the xyz request on the same E-PT images (paired baseline). usage: f0.sh <code dir>
C=$1
P=/data/harvest/venv_train/bin/python
D=/data/harvest/out/teach_pt/data
O=/data/harvest/out/teach_pt/eval
L=/data/harvest/logs/teach_pt
cd $C; export PYTHONPATH=$C
$P tools/teach_pt/build.py /data/harvest/out/teach_pt/collect $D dev --no-repeats > $L/build_dev.log 2>&1
for a in xyz pt nd-xyz nd-est nd-pt; do $P tools/teach_pt/truth_score.py $D/dev_$a.jsonl $a; done > $L/g0a_truth.log 2>&1
bash $C/tools/teach_pt/py.sh vllm - f0_pt_zs $C harvest.teach_pt.evaluate --data $D/dev_pt.jsonl --arm pt --url http://127.0.0.1:8394 --name pt_zs --out $O/dev_pt_zs --kinds control
bash $C/tools/teach_pt/py.sh vllm - f0_pt_zs_px $C harvest.teach_pt.evaluate --data $D/dev_pt.jsonl --arm pt --url http://127.0.0.1:8394 --name pt_zs --out $O/dev_pt_zs_px --kinds control --coords px
bash $C/tools/teach_pt/py.sh vllm - f0_xyz_zs $C harvest.teach_pt.evaluate --data $D/dev_xyz.jsonl --arm xyz --url http://127.0.0.1:8394 --name pt_zs --out $O/dev_xyz_zs --kinds control
echo "F0_DONE $(date -u +%FT%TZ)" >> $L/f0.log
