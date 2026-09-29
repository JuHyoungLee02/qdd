#!/bin/bash
# Stop ONLY our gpt-5-mini proxy run (user: "노노 미니 돌리지마"): every process whose argv names the mini model or the
# mini out dir (driver loop first, then runner / ir_run / Isaac python). Other runs are never touched.
kill_matching() {
  for p in $(ls /proc | grep -E '^[0-9]+$'); do
    [ "$p" = "$$" ] && continue
    a=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null) || continue
    case "$a" in
      *"$1"*) echo "kill $p ${a:0:200}"; kill -9 $p 2>/dev/null ;;
    esac
  done
}
kill_matching "proxy4.sh /data/harvest/code_open_vlm_proxy_f37051c gpt-5-mini-2025-08-07"
kill_matching "open_vlm_proxy_mini"
kill_matching "gpt-5-mini-2025-08-07"
sleep 3
echo "left:"; ps -eo pid,args | grep -E "open_vlm_proxy_mini|gpt-5-mini" | grep -v grep || echo none
