#!/usr/bin/env bash
# E-VB1 pi0.5 fine-tuning on the re-collected L8S episodes (docs/stage3/prereg_vb1.md change 1; 78dc GPU 0-3 DDP).
# = /data/juhyoung_pi05/train_taskc_v6.sh (Task C v6 recipe: pi05_base, LR 2.5e-5, warmup 1k, batch 16 x 4, bf16,
# gradient checkpointing, image augmentation, seed 1000, relative actions through the lerobot_train_v6.py wrapper),
# changes: dataset vb1_l8s_train (camera keys already top / wrist_right: no rename map), relative actions on the
# 7 arm joints only (gripper absolute), 30k steps, save every 5k, outputs under /data/harvest/out/vb1/train.
# Internal baseline only (user-log 227): checkpoints stay under /data/harvest/out/vb1, never uploaded (push_to_hub off).
#   usage: bash train.sh <code dir>                 (RUN=vb1_pi05 STEPS=30000 SAVE_FREQ=5000)
#          SMOKE=1 bash train.sh <code dir>         (20 steps, wandb off)
set -euo pipefail
C=$1
GARO=/data/GARO_pi; BIN="$GARO/lerobot/.venv/bin"; MY=/data/juhyoung_pi05; R=/data/harvest/out/vb1
DATASET_ID="${DATASET_ID:-vb1_l8s_train}"; DATASET_ROOT="$R/lerobot/$DATASET_ID"; BASE="$MY/base_models/pi05_base"
SMOKE="${SMOKE:-0}"
if [ "$SMOKE" = 1 ]; then
  RUN="${RUN:-smoke_vb1_$(date +%m%d_%H%M)}"; STEPS="${STEPS:-20}"; WARMUP=5; DECAY=$STEPS; SAVE_FREQ=20; LOGF=5; WANDB_ON=false
else
  RUN="${RUN:-vb1_pi05}"; STEPS="${STEPS:-30000}"; WARMUP="${WARMUP:-1000}"; DECAY="${DECAY:-$STEPS}"; SAVE_FREQ="${SAVE_FREQ:-5000}"; LOGF=100; WANDB_ON=true
fi
RELATIVE_EXCLUDE='["gripper"]'
BATCH="${BATCH:-16}"; WORKERS="${WORKERS:-8}"; GPUS="${GPUS:-0,1,2,3}"; NPROC="${NPROC:-4}"
OUT="$R/train/$RUN"
[ -f "$DATASET_ROOT/meta/info.json" ] || { echo "!! no dataset: $DATASET_ROOT"; exit 1; }
[ -f "$DATASET_ROOT/meta/stats_lerobot_backup.json" ] || { echo "!! exact stats not written (convert.py stats)"; exit 1; }
UV_DIR=/home/irteam/.local/share/uv/python; mkdir -p "$UV_DIR"
ln -sfn "$MY/uvpython/cpython-3.12.13-linux-x86_64-gnu" "$UV_DIR/cpython-3.12.13-linux-x86_64-gnu"
export HF_LEROBOT_HOME="$R/lerobot" HF_HOME="$MY/.hf_cache" HF_HUB_OFFLINE=1 WANDB_DIR="$R/wandb" WANDB_PROJECT=qdd-vb1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES="$GPUS" TOKENIZERS_PARALLELISM=false
export TMPDIR=/data/harvest/tmp XDG_CACHE_HOME=/data/harvest/cache
if [ "$WANDB_ON" = true ] && [ -f /data/.wandb_token ]; then export WANDB_API_KEY="$(cat /data/.wandb_token)"; else export WANDB_MODE=offline; WANDB_ON=false; fi
mkdir -p "$WANDB_DIR" "$R/train"
if [ -d "$OUT" ]; then
  if [ -z "$(ls -A "$OUT" 2>/dev/null)" ]; then rmdir "$OUT"; else echo "!! $OUT exists (change RUN)"; exit 1; fi
fi
cd "$R"
echo "pi0.5 fine-tuning (DDP $NPROC GPU: $GPUS) run=$RUN dataset=$DATASET_ROOT steps=$STEPS save=$SAVE_FREQ batch=$BATCH x $NPROC relative exclude $RELATIVE_EXCLUDE"
"$BIN/python" "$C/tools/vb1/check_dataset.py" "$DATASET_ROOT" pyav
echo "--- train start $(date '+%F %T') ---"
export V6_RENAME_MAP=""
"$BIN/accelerate" launch --num_processes="$NPROC" --mixed_precision=bf16 \
  "$C/tools/vb1/lerobot_train_v6.py" \
  --policy.use_relative_actions=true --policy.relative_exclude_joints="$RELATIVE_EXCLUDE" \
  --policy.path="$BASE" --policy.device=cuda --policy.push_to_hub=false --policy.dtype=bfloat16 --policy.gradient_checkpointing=true \
  --policy.optimizer_lr=2.5e-5 --policy.scheduler_warmup_steps="$WARMUP" --policy.scheduler_decay_steps="$DECAY" \
  --dataset.repo_id="$DATASET_ID" --dataset.root="$DATASET_ROOT" \
  --dataset.video_backend=pyav --dataset.image_transforms.enable=true \
  --batch_size="$BATCH" --steps="$STEPS" --save_freq="$SAVE_FREQ" --log_freq="$LOGF" --num_workers="$WORKERS" --seed=1000 \
  --output_dir="$OUT" --job_name="$RUN" \
  --wandb.enable="$WANDB_ON" --wandb.project=qdd-vb1 --wandb.entity=ljhi0179 --wandb.disable_artifact=true
RC=$?
echo "--- train end $(date '+%F %T') rc=$RC ---"; ls "$OUT/checkpoints/" 2>/dev/null | tail -n 3; exit $RC
