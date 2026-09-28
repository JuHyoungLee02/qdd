#!/bin/bash
# prereg_limits.md change 3: the noise fix (nf). Waits for pid <wait pid> (the v2g lane) to end, then on render GPU <rg>:
# the 6 limit-map episodes x {noise:1:nf, noise:2:nf} (the 'before' arms noise_1 / noise_2 already exist in map/ and
# are skipped), then the first 8 dev_x episodes of the v2 set x none:nf (the 'before' arm is v2/none).
# Same STOP file as the limits chain. usage: nf_chain.sh <code dir> <render gpu> <x2 pod ip> <wait pid>
C=$1; RG=$2; H=$3; W=$4
L=/data/harvest/logs/strip8; O=/data/harvest/out/strip8/limits
cd $C; export PYTHONPATH=$C
while kill -0 $W 2>/dev/null; do sleep 60; done
echo "NF_START $(date -u +%FT%TZ)" >> $L/lanes.log
stop() { [ -f $L/limits.STOP ] && { echo "NF_STOPPED $(date -u +%FT%TZ)" >> $L/lanes.log; exit 0; }; }
k=0
while read -r eps; do
  [ -n "$eps" ] || continue; stop; k=$((k + 1))
  bash $C/tools/teach_strip8/isaac.sh $C $RG lim_nf_map_$k harvest.teach_strip8.run_limits --conds noise:1,noise:1:nf,noise:2,noise:2:nf \
    --qwen-url http://$H:8431 --qwen-name lim_bobj --out $O/map --episodes $eps
done < $L/limits_map.txt
awk 'BEGIN{n=0} {out=""; for(i=1;i<=NF && n<8;i++){out=out (out==""?"":" ") $i; n++} if(out!="") print out}' \
  $L/limits_v2set.txt > $L/limits_nf_reg.txt
k=0
while read -r eps; do
  [ -n "$eps" ] || continue; stop; k=$((k + 1))
  bash $C/tools/teach_strip8/isaac.sh $C $RG lim_nf_reg_$k harvest.teach_strip8.run_limits --conds none,none:nf \
    --qwen-url http://$H:8431 --qwen-name lim_bobj --out $O/v2 --episodes $eps
done < $L/limits_nf_reg.txt
echo "NF_DONE $(date -u +%FT%TZ)" >> $L/lanes.log
