#!/bin/bash
# E-H2H-T2 (prereg_h2h2.md) one GPU lane: arms run in order. usage: h2h2_lane.sh <gpu> <port> <arm>:<seed> [...]
#   D / H arms (E-DIST8 tools + B-level eval sets): d_px d_base h_px h_cp h_both
#   xyz arms (E-H2H-T pipeline + 9 sets): add_t1t4 add_cp add_both
G=$1; PORT=$2; shift 2
C=/data/harvest/code_h2h2
P=/data/harvest/venv_train/bin/python
K=/data/harvest/out/xemb/dist8_packs; PX=$K/t1t4_pixel.jsonl; CP=$K/cp_pack.jsonl
DB=/data/harvest/out/dist8/data_b1
M=/data/harvest/out/xemb/h2h2/data; R=/data/harvest/out/xemb/h2h2
D2=/data/harvest/out/xemb/h2h
L=/data/harvest/logs/h2h2; mkdir -p $M $L
W=${WORKERS:-4}
cd $C; export PYTHONPATH=$C
for spec in "$@"; do
  IFS=: read -r arm seed <<< "$spec"
  name=${arm}_s$seed
  echo "START $name $(date -u +%FT%TZ) gpu=$G" >> $L/lanes.log
  case $arm in
    add_t1t4|add_cp|add_both)
      src=$arm; [ $arm = add_cp ] && src=add_cpx2
      steps=1066; [ $arm = add_both ] && steps=1191
      ln -sf $D2/$src.jsonl $D2/$name.jsonl
      SEED=$seed H2H_STEPS=$steps bash $C/tools/xemb/proto/h2h_run.sh $G $PORT $name
      bash $C/tools/xemb/proto/h2h_eval_l8x.sh $G $((PORT + 1)) $name dev_x ood_h ood_hl ood_d ood_s ood_o ood_t
      echo "DONE $name $(date -u +%FT%TZ)" >> $L/lanes.log
      continue;;
    d_px) base=$DB/train_d-min.jsonl; mix="$PX:0.25"; tr=d-min; steps=1088;;
    d_base) base=$DB/train_d-min.jsonl; mix=""; tr=d-min; steps=816;;
    h_px) base=$DB/train_h-min.jsonl; mix="$PX:0.25"; tr=h-min; steps=1088;;
    h_cp) base=$DB/train_h-min.jsonl; mix="$CP:0.25"; tr=h-min; steps=1088;;
    h_both) base=$DB/train_h-min.jsonl; mix="$CP:0.1667 $PX:0.0833"; tr=h-min; steps=1088;;
    *) echo "unknown $arm" >> $L/lanes.log; continue;;
  esac
  f=$M/train_$arm.jsonl
  if [ ! -f $f ]; then
    if [ -n "$mix" ]; then $P tools/teach_pt/mix_pack.py $base $f $mix >> $L/build.log 2>&1; else ln -sf $base $f; fi
  fi
  bash $C/tools/teach_pt/py.sh train $G h2h2_$name $C harvest.teach_l8.train --data $f --out $R/run_$name \
    --epochs 3 --max-steps $steps --micro 8 --accum 2 --log-every 10 --workers $W --seed $seed
  E=$(ls -d $R/run_$name/epoch* 2>/dev/null | sort -V | tail -1)
  [ -n "$E" ] && bash $C/tools/teach_pt/py.sh train $G h2h2_merge_$name $C harvest.teach_l8.merge --adapter $E \
    --out $R/merged_$name
  bash $C/tools/teach_pt/dist8_eval_seq.sh $C $G $PORT 0.60 h2h2_$name:$R/merged_$name:$tr
  echo "DONE $name $(date -u +%FT%TZ)" >> $L/lanes.log
done
