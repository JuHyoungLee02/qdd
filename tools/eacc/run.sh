#!/bin/bash
# E-ACC pod driver (docs/stage3/prereg_eacc.md §4). CPU-side steps only (Isaac capture = capture.sh; Qwen server =
# tools/prompt_health/serve.sh on GPU 3, port 8381). Every file under /data.
# usage: run.sh <code dir> sheet <bench> <out.jpg> | mock <bench> | screen <bench> | paid <bench> <arms> <tag>
#        | sub <bench> <arms> <tag> | score <bench> <out.json> <rows...>
set -uo pipefail
source /data/harvest/env.sh
C=$1; MODE=$2; shift 2
PY=/data/harvest/venv_vllm/bin/python
L=/data/harvest/logs/eacc; O=/data/harvest/out/eacc
mkdir -p $L $O
cd $C
export PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4
case $MODE in
  sheet) $PY tools/eacc/sheet.py --bench $1 --out $2;;
  mock) $PY tools/eacc/run_eacc.py --bench $1 --set screen --arms v1,v2,v2cp,v2_2cam --model mock --out $O/mock_rows.jsonl --dump $O/prompts_mock;;
  screen) $PY tools/eacc/run_eacc.py --bench $1 --set screen --arms v1,v2,v2cp,v2_2cam,v2_noov,v2_noctx --model qwen \
            --url http://127.0.0.1:8381 --served qwen8b_eacc --out $O/screen_qwen8b.jsonl --tag screen --dump $O/prompts_screen >> $L/screen.log 2>&1
          echo "EXIT $? $(date -u +%FT%TZ)" >> $L/screen.log;;
  paid) $PY tools/eacc/run_eacc.py --bench $1 --set paid --arms $2 --model astra --out $O/astra_$3.jsonl --tag $3 \
          --ledger $L/astra_ledger.jsonl --prices $L/prices_2026-09-26.json --cap-krw 8000 >> $L/astra_$3.log 2>&1
        echo "EXIT $? $(date -u +%FT%TZ)" >> $L/astra_$3.log;;
  sub) $PY tools/eacc/run_eacc.py --bench $1 --set sub --arms $2 --model astra --out $O/astra_$3.jsonl --tag $3 \
         --ledger $L/astra_ledger.jsonl --prices $L/prices_2026-09-26.json --cap-krw 8000 >> $L/astra_$3.log 2>&1
       echo "EXIT $? $(date -u +%FT%TZ)" >> $L/astra_$3.log;;
  score) B=$1; J=$2; shift 2; $PY tools/eacc/score.py --bench $B --json $J --decide --rows "$@";;
  *) echo "mode?"; exit 2;;
esac
