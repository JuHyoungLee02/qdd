#!/bin/bash
# E-POL0: stop our probe processes (argv match) and hand the floating render card back to L9.
for d in /proc/[0-9]*; do
  mapfile -d '' -t a < $d/cmdline 2>/dev/null || continue
  [[ "${a[1]:-}" == */probe_polaris.py || "${a[1]:-}" == */pol0dev/vkdbg.sh ]] && kill -KILL ${d#/proc/} 2>/dev/null
done
sleep 3
touch /data/harvest/out/render_float/DONE; rm -f /data/harvest/out/render_float/WANTED
echo released; nvidia-smi --query-gpu=index,memory.used --format=csv,noheader
