#!/bin/bash
# Resume check on one GPU (full-state checkpoints, harvest/teach_l8/ckpt.py): for a trainer module, run
#   A = straight, B = straight again (GPU noise floor), C = stopped after the checkpoint at step S then --resume,
# all with the same small data / steps, and compare the final adapters (tools/teach_35b/cmp_adapters.py).
# usage: resume_check.sh <code dir> <gpu> <teach_l8|teach_35b> <data jsonl> <out root> [steps 6] [stop 3]
C=$1; G=$2; M=$3; D=$4; O=$5; N=${6:-6}; S=${7:-3}
source /data/harvest/env.sh
P=/data/harvest/venv_train/bin/python
export CUDA_VISIBLE_DEVICES=$G PYTHONPATH=$C TEACH_35B_JOB=resume_check TRITON_CACHE_DIR=/data/harvest/cache/triton
export CC=/data/harvest/jevl/bin/cc
[ $M = teach_35b ] && export PYTHONPATH=$C:/data/harvest/pylib_fla052
COMMON=(--data $D --limit 48 --epochs 1 --micro 2 --accum 2 --max-steps $N --save-every $S --workers 0 --warmup 2)
[ $M = teach_35b ] && COMMON+=(--label-check warn)
rm -rf $O; mkdir -p $O; cd $C
$P -m harvest.$M.train "${COMMON[@]}" --out $O/A > $O/A.log 2>&1
$P -m harvest.$M.train "${COMMON[@]}" --out $O/B > $O/B.log 2>&1
$P -m harvest.$M.train "${COMMON[@]}" --out $O/C --stop-after $S > $O/C1.log 2>&1
$P -m harvest.$M.train "${COMMON[@]}" --out $O/C --resume > $O/C2.log 2>&1
grep -h "STOPPED_AT\|RESUME" $O/C1.log $O/C2.log
$P tools/teach_35b/cmp_adapters.py $O/A/epoch1 $O/B/epoch1 $O/C/epoch1
