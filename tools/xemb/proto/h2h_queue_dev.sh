#!/bin/bash
# E-H2H-T: L8-X DEV (dev_x, L8D 09:32 KST build) for all three arms on one GPU, after the cp lane (E1) has finished.
# usage: h2h_queue_dev.sh <gpu> <port>
G=$1; PORT=$2
S=/data/harvest/code_h2h/tools/xemb/proto/h2h_eval_l8x.sh
until grep -q "EXIT eval" /data/harvest/logs/h2h/h2h_cpg1.log; do sleep 60; done
for ARM in h2h_base h2h_t1t4; do bash $S $G $PORT $ARM dev_x; done
# the other queue serves h2h_cpg1 too, and each eval ends by killing its served name: never overlap the same arm
until grep -q "EXIT e2 h2h_cpg1" /data/harvest/logs/h2h/e2_h2h_cpg1.log 2>/dev/null; do sleep 60; done
bash $S $G $PORT h2h_cpg1 dev_x
