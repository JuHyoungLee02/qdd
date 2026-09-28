#!/bin/bash
# L8X-assets: stop one of my Isaac validation runs by its output tag (…/videos/l8x_assets/<tag>); the pattern lives in
# this file, so it never matches the calling shell's command line.  usage: stop_run.sh <tag>
T=$1
[ -n "$T" ] || { echo "tag?"; exit 2; }
pkill -f "l8x_assets/[v]alidate.*videos/l8x_assets/$T( |$)" || true
pkill -f "videos/l8x_assets/$T( |$)" -9 2>/dev/null || true
sleep 2
pgrep -af "videos/l8x_assets/$T( |$)" | grep -v stop_run || echo "stopped $T"
