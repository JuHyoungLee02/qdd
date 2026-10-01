#!/bin/bash
# shm_clean.sh [--dry]: remove stale carb shared-memory files from the chroot's /dev/shm.
# ir_run.sh bind-mounts the pod's /dev non-recursively, so Isaac's /dev/shm is the directory on the pod's 64 MB /dev
# tmpfs (not the 32 GB /dev/shm mount). Every Isaac process leaves carb-RStringInternals-<pid> (+ sem.) there when it
# is killed or leaves via os._exit; when the 64 MB fill up, every new Isaac start fails ("Error while opening shared
# memory carb-RStringInternals-<pid>"). Removes only files whose <pid> is not a running process.
D=/tmp/l9_devpeek_$$
mkdir -p $D && mount --bind /dev $D || exit 1
n=0; k=0
for f in $D/shm/carb-RStringInternals-* $D/shm/sem.carb-RStringInternals-*; do
  [ -e "$f" ] || continue
  pid=${f##*-}
  if [ -d /proc/$pid ]; then k=$((k + 1)); continue; fi
  [ "$1" = "--dry" ] || rm -f "$f"
  n=$((n + 1))
done
echo "removed $n stale, kept $k live"; df -h $D | tail -1
umount $D; rmdir $D
