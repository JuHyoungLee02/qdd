#!/bin/bash
# E-LIB0 pi0.5 policy server (openpi scripts/serve_policy.py, the official LIBERO example's server, config pi05_libero).
#   arm R: the pi05_libero checkpoint (LIBERO fine-tuned, reference row)
#   arm B: pi05_base params + the LIBERO action-normalisation stats of pi05_libero (data statistics, no weights)
#          assembled in /data/harvest/lib0/ckpt/pi05_base_liberonorm (params = symlink to the base checkpoint)
# JAX memory share XLA_PYTHON_CLIENT_MEM_FRACTION=0.3 (two servers on one card). Process tag LIB0_JOB=pi_<arm>.
# usage: serve_pi.sh <arm B|R|G|W|P0|PF> <gpu> <port>   log -> /data/harvest/logs/lib0/serve_<arm>.log
A=$1; G=$2; PORT=$3; CFG=pi05_libero
R=/data/harvest/lib0; CK=$R/openpi_data/openpi-assets/checkpoints; L=/data/harvest/logs/lib0; mkdir -p $L
if [ $A = R ]; then D=$CK/pi05_libero
elif [ $A = P0 ]; then D=$CK/pi0_libero; CFG=pi0_libero  # E-LIB1: official pi0 LIBERO checkpoint
elif [ $A = PF ]; then D=$CK/pi0_fast_libero; CFG=pi0_fast_libero  # E-LIB1: official pi0-FAST LIBERO checkpoint
elif [ $A = G ]; then  # E-SIM0 arm B: pi05_base + fractal action stats (tools/sim0/fractal_norm.py), prepared beforehand
  D=$R/ckpt/pi05_base_fractalnorm; [ -e $D/params ] || ln -s $CK/pi05_base/params $D/params
elif [ $A = W ]; then  # E-SIM1 arm B: pi05_base + bridge action stats (fractal_norm.py ... bridge_dataset)
  D=$R/ckpt/pi05_base_bridgenorm; [ -e $D/params ] || ln -s $CK/pi05_base/params $D/params
else
  D=$R/ckpt/pi05_base_liberonorm
  mkdir -p $D/assets/physical-intelligence/libero
  [ -e $D/params ] || ln -s $CK/pi05_base/params $D/params
  cp -n $CK/pi05_libero/assets/physical-intelligence/libero/norm_stats.json $D/assets/physical-intelligence/libero/
fi
export CUDA_VISIBLE_DEVICES=$G XLA_PYTHON_CLIENT_MEM_FRACTION=0.3 OPENPI_DATA_HOME=$R/openpi_data LIB0_JOB=pi_$A
export HOME=/data/harvest/home XDG_CACHE_HOME=$R/cache TMPDIR=/data/harvest/tmp HF_HOME=/data/harvest/cache/hf
cd $R/openpi
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G arm=$A dir=$D port=$PORT" >> $L/serve_$A.log
exec nice $R/openpi/.venv/bin/python scripts/serve_policy.py --port $PORT policy:checkpoint --policy.config $CFG \
  --policy.dir $D >> $L/serve_$A.log 2>&1
