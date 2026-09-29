#!/bin/bash
# Stop ONLY our waiting E-PT chain scripts (post_arm.sh / main_post.sh, and the `bash -c` wrapper that runs them) by
# exact argv comparison from /proc (pitfalls P27 / P70 / P76: no pkill -f). usage: kill_waiters.sh
me=$$
for d in /proc/[0-9]*; do
  p=${d#/proc/}; [ "$p" = "$me" ] && continue
  mapfile -d '' -t a < $d/cmdline 2>/dev/null || continue
  [ "${a[0]}" = "bash" ] || continue
  case "${a[1]}" in
    */tools/teach_pt/post_arm.sh|*/tools/teach_pt/main_post.sh) echo "kill $p ${a[*]:0:4}"; kill $p;;
    -c) case "${a[2]}" in
          *kill_waiters.sh*) ;;  # the shell that runs this script (P70: it killed its own kubectl exec once)
          *tools/teach_pt/post_arm.sh*) echo "kill $p (bash -c wrapper)"; kill $p;;
        esac;;
  esac
done
