#!/bin/bash
# AgiBot chain runner (pod juhyoung-q-78dc, CPU 48, /data shared). usage: agb_run.sh sample | all
#   sample: task 327's smallest obs tar -> the proprio / parameters tars covering its episodes -> structure probe
#   all   : every selected task (resumes from chain_state.json)
X=/data/harvest/out/xemb_proto
PY=/data/harvest/venv_train/bin/python
export PYTHONPATH=$X/code:/data/harvest/pylib_xemb_train HF_HUB_ENABLE_HF_TRANSFER=0  # h5py from pylib_xemb_train (python 3.11)
cd $X/code
if [ "$1" = sample ]; then
  $PY -m xemb.agb_chain obs 1 && $PY -m xemb.agb_chain proprio && $PY -m xemb.agb_chain params
  $PY -m xemb.agb_probe /data/harvest/data/agibot/keep /data/harvest/data/agibot/probe.json
else
  $PY -m xemb.agb_chain all
fi
echo "RUN_END $1 $(date -u +%FT%TZ)" >> /data/harvest/data/agibot/chain.log
