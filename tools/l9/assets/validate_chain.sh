#!/bin/bash
# L9 object settle check chain (x2 pod, GPU 1 only, <= 2 Isaac processes): every chunk table CHUNKS/c*.json through
# tools.l8x_assets.validate_objects (all rows), lane L of N takes chunks i % N == L; finished chunks (objects_check.json)
# are skipped, so a rerun resumes. Stop: touch $VAL/STOP.
# usage: validate_chain.sh CODE_DIR CHUNKS_DIR VAL_DIR LANE NLANES
C=$1; CH=$2; VAL=$3; L=$4; N=$5
case "$(hostname)" in *x2) ;; *) echo "refused: run on juhyoung-native-7a2a-x2"; exit 2;; esac
i=0
for t in $(ls $CH/c*.json | sort); do
  if [ $((i % N)) -eq $L ] && [ ! -f $VAL/STOP ]; then
    b=$(basename $t .json)
    if [ ! -s $VAL/$b/objects_check.json ]; then
      bash $C/tools/l8x_assets/isaac.sh $C 1 l9v_$(basename $VAL)_$b tools.l8x_assets.validate_objects \
        --table $t --out $VAL/$b --n 100000
    fi
  fi
  i=$((i + 1))
done
echo "LANE_DONE $L $(date -u +%FT%TZ)" >> $VAL/lanes_done.txt
