#!/bin/bash
# E-H2H-T add arms: L8-X evaluation (7 splits) of each add arm right after its E1 evaluation ends. usage: h2h_add_queue.sh <gpu> <port>
G=$1; PORT=$2
S=/data/harvest/code_h2h/tools/xemb/proto/h2h_eval_l8x.sh
for ARM in add_t1t4 add_cp; do
  until grep -q "EXIT eval" /data/harvest/logs/h2h/$ARM.log 2>/dev/null; do sleep 60; done
  bash $S $G $PORT $ARM dev_x ood_h ood_hl ood_d ood_s ood_o ood_t
done
