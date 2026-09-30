#!/bin/bash
# The E-CJ VLA server code: copy of the runtime that served E-SR1c C1 in E-Couple dry / E-VLA-solo
# (/data/harvest/code_couple_dry_9322853) with ONE change: fused_model serve binds 0.0.0.0 (other pods' lanes).
# usage: make_srv.sh <dest dir>
S=/data/harvest/code_couple_dry_9322853; D=$1
[ -e $D ] && { echo "exists: $D"; exit 1; }
cp -a $S $D
sed -i 's/ThreadingHTTPServer(("127.0.0.1", a.port)/ThreadingHTTPServer(("0.0.0.0", a.port)/' $D/harvest/runtime/fused_model.py
grep -c '"0.0.0.0", a.port' $D/harvest/runtime/fused_model.py
diff -r -q $S $D
