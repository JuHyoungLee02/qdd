#!/bin/bash
# Stop the drawer gate chain and its Isaac process (patterns live in this file: no self-match).
pkill -f "dr_[c]hain.sh" || true
pkill -9 -f "l8x_assets.[g]ate_drawer" || true
sleep 2
pgrep -af "gate_drawer|dr_chain" | grep -v stop_drawer || echo stopped
