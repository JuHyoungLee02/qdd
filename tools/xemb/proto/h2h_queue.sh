#!/bin/bash
# E-H2H-T evaluation queue on one GPU: late L8-X splits for base and t1t4, then the cp arm (h2h_cpg1) on every split
# once its merged model exists. usage: h2h_queue.sh <gpu> <port>
G=$1; PORT=$2
S=/data/harvest/code_h2h/tools/xemb/proto/h2h_eval_l8x.sh
D=/data/harvest/out/xemb/h2h
bash $S $G $PORT h2h_base ood_hl ood_o ood_t
bash $S $G $PORT h2h_t1t4 ood_hl ood_o ood_t
until [ -f $D/merged_h2h_cpg1/config.json ] && grep -q "EXIT eval" /data/harvest/logs/h2h/h2h_cpg1.log; do sleep 60; done
bash $S $G $PORT h2h_cpg1 ood_h ood_d ood_s ood_hl ood_o ood_t
