#!/bin/bash
# attach_x2.sh: run inside a recreated juhyoung-native-7a2a-x2 to put L9 production back on x2 GPU1 with the current
# code (CODE_CURRENT, human-like motion l9m-2). At most 2 Isaac lanes (each ~13 GB RSS; the pod is 128 Gi and also
# hosts vLLM / other lanes); the supervisor's memory guard skips a lane when < 24 GiB are free.
L=/data/harvest/out/l9
C=$(cat $L/CODE_CURRENT)
[ -d "$C" ] || { echo "no code dir $C on this pod's /data"; exit 1; }
bash $C/tools/l9/shm_clean.sh
grep -q 'x2:1' $L/GPU_WANTED || sed -i 's/$/ x2:1/' $L/GPU_WANTED
R=$L/prod1
[ -f $R/supervisor_x2.pid ] && kill $(cat $R/supervisor_x2.pid) 2>/dev/null
nohup setsid bash $C/tools/l9/supervisor.sh $C $R "1:xa 1:xb" >> /data/harvest/logs/l9/supervisor_prod1_$(hostname).log 2>&1 < /dev/null &
echo $! > $R/supervisor_x2.pid
echo "x2:1 attached to L9 production on $C $(date -u +%FT%TZ)" | tee -a $L/GPU_FREED
