#!/bin/bash
# E-LIBFT: stop the chain shell (argv[1] ends with tools/libft/chain.sh) and the collectors (env LIB0_JOB=libft_*);
# training (TEACH_35B_JOB=libft_run) only with "train" as $1. No pkill -f.
me=$$; parent=$PPID; declare -A k=()
for d in /proc/[0-9]*; do
  p=${d#/proc/}; { [ "$p" = "$me" ] || [ "$p" = "$parent" ]; } && continue
  mapfile -d '' -t a < $d/cmdline 2>/dev/null || continue
  [[ "${a[1]:-}" == */tools/libft/chain.sh ]] && k[$p]=1
  e=$(tr '\0' '\n' < $d/environ 2>/dev/null)
  echo "$e" | grep -qE "^LIB0_JOB=libft_" && k[$p]=1
  [ "${1:-}" = train ] && echo "$e" | grep -qx "TEACH_35B_JOB=libft_run" && k[$p]=1
done
echo "stopping ${#k[@]}"; [ ${#k[@]} -gt 0 ] && kill -TERM "${!k[@]}" 2>/dev/null; sleep 5
for p in "${!k[@]}"; do [ -d /proc/$p ] && kill -KILL $p 2>/dev/null; done; echo done
