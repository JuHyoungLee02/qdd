#!/bin/bash
# E-POL0: stop a leftover probe (argv match, not a pattern on our own command line), then a 2-minute Isaac start with
# Vulkan loader debug output to see why grep -i -E "loader|vkCreateInstance|^(camera cfgs|instruction|bodies|root|obs keys|info|depth|action space)|Error:|_cam K" /data/harvest/logs/lib0/pol0_vkdbg.log | head -20 | cut -c1-600 fails.
for d in /proc/[0-9]*; do
  mapfile -d '' -t a < $d/cmdline 2>/dev/null || continue
  [[ "${a[1]:-}" == */probe_polaris.py ]] && kill -KILL ${d#/proc/} 2>/dev/null
done
source /data/harvest/pol0dev/env_pol.sh 1
export VK_ICD_FILENAMES=/etc/vulkan/icd.d/nvidia_icd.json XDG_RUNTIME_DIR=/data/harvest/tmp/xdg VK_LOADER_DEBUG=error
export LD_PRELOAD=/data/harvest/simpler/vk/lib/libvulkan.so.1  # force the 1.4 loader over the bundled 1.2 one
cd /data/harvest/polaris
timeout 400 $PY /data/harvest/pol0dev/probe_polaris.py DROID-FoodBussing /data/harvest/out/pol0/probe > /data/harvest/logs/lib0/pol0_vkdbg.log 2>&1
grep -i -E "loader|vkCreateInstance|^(camera cfgs|instruction|bodies|root|obs keys|info|depth|action space)|Error:|_cam K" /data/harvest/logs/lib0/pol0_vkdbg.log | head -20 | cut -c1-600\|vkCreateInstance\|libvulkan" /data/harvest/logs/lib0/pol0_vkdbg.log | head -15 | cut -c1-300
