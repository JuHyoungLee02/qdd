#!/bin/bash
# sem_reset.sh: unstick carb's global named semaphore (/carbonite-sharedmemory) in the chroot's /dev/shm (the pod's
# 64 MB /dev, P148). Isaac processes killed with SIGKILL while holding it leave it at 0 and every Isaac start then
# waits forever ("Waiting on global named semaphore /carbonite-sharedmemory ... may be in a stuck state", P149).
# Only acts when no Isaac (kit python) process is running on the pod; prints what it did.
if ps -eo args | awk '/kit\/python\/bin\/python3/ && !/awk/' | grep -q .; then
  echo "Isaac processes running: not resetting"; exit 1
fi
D=/tmp/l9_devpeek_$$
mkdir -p $D && mount --bind /dev $D || exit 1
ls $D/shm | grep -c carbonite
rm -f $D/shm/sem.carbonite-sharedmemory
echo "reset done"
umount $D; rmdir $D
