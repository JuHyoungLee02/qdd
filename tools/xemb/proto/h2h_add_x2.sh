#!/bin/bash
# E-H2H-T add_cp moved to x2 GPU0 as arm 'add_cpx2' (md5-identical copy of add_cp.jsonl): train (1,066 steps) + E1, then
# the 7 L8-X splits. usage: h2h_add_x2.sh <gpu> <port>
G=$1; PORT=$2
P=/data/harvest/code_h2h/tools/xemb/proto
H2H_STEPS=1066 bash $P/h2h_run.sh $G $PORT add_cpx2
bash $P/h2h_eval_l8x.sh $G $((PORT + 1)) add_cpx2 dev_x ood_h ood_hl ood_d ood_s ood_o ood_t
