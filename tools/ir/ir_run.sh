#!/bin/bash
# Inspect Robots P0 runner -- /data/juhyoung_pi05/native_run.sh (V4-250) 방식 그대로:
# unshare -m 전용 마운트 네임스페이스 + bind + chroot. 파드 본체에 흔적 없음.
#   IR_ROOT=isaac  : /data/juhyoung_infra/isaac-sim-5.1.0-rootfs (Isaac Sim 5.1.0, Isaac Lab 없음)
#   IR_ROOT=cyclo  : /data/juhyoung_infra/rootfs/cyclo-lab-2.0.0 (같은 Isaac Sim 5.1.0-rc.19 + Isaac Lab 2.3.0)
#                    cyclo_lab 저장소(/data/newproj/rep_v3test)를 읽기전용으로 /workspace/cyclo_lab 에 바인드
# 사용: IR_ROOT=cyclo IR_INST=boot0 ir_run.sh bash -lc "..."
set -u
IR_ROOT=${IR_ROOT:-isaac}
case "$IR_ROOT" in
  isaac) R=/data/juhyoung_infra/isaac-sim-5.1.0-rootfs; ENVF= ;;
  cyclo) R=/data/juhyoung_infra/rootfs/cyclo-lab-2.0.0; ENVF=/data/juhyoung_infra/rootfs/cyclo-lab-2.0.0.env ;;
  *) echo "IR_ROOT?" >&2; exit 1 ;;
esac
REPO=${IR_REPO:-/data/newproj/rep_v3test}
NVLIBS=/data/juhyoung_infra/nvidia_libs
INST=${IR_INST:-ir0}
CACHE=/data/juhyoung_qdd/ir/kitcache/$IR_ROOT-$INST

if [ "${_IR_INNER:-}" != "1" ]; then
  mkdir -p "$CACHE/cache" "$CACHE/data" "$CACHE/logs"
  export _IR_INNER=1
  exec unshare -m "$0" "$@"
fi
mount --make-rprivate / 2>/dev/null || true
b()  { [ -e "$1" ] || return 0; mkdir -p "$2" 2>/dev/null; mount --bind "$1" "$2" || { echo "[IR] bind fail $1 -> $2" >&2; return 1; }; }
bf() { [ -e "$1" ] || return 0; [ -e "$2" ] || { mkdir -p "$(dirname "$2")"; : > "$2"; }; mount --bind "$1" "$2" || { echo "[IR] bind fail $1 -> $2" >&2; return 1; }; }

b /dev  "$R/dev"; b /proc "$R/proc"; b /sys "$R/sys"; b /data "$R/data"
if [ "$IR_ROOT" = cyclo ]; then
  b "$REPO" "$R/workspace/cyclo_lab" && mount -o remount,bind,ro "$R/workspace/cyclo_lab"
fi
b "$NVLIBS" "$R/nvidia-driver"
bf "$NVLIBS/nvidia-smi"              "$R/usr/bin/nvidia-smi"
bf /etc/vulkan/icd.d/nvidia_icd.json "$R/etc/vulkan/icd.d/nvidia_icd.json"
bf /usr/share/nvidia/nvoptix.bin     "$R/usr/share/nvidia/nvoptix.bin"
bf /etc/resolv.conf                  "$R/etc/resolv.conf"
b "$CACHE/cache" "$R/isaac-sim/kit/cache"
b "$CACHE/data"  "$R/isaac-sim/kit/data"
b "$CACHE/logs"  "$R/isaac-sim/kit/logs"
# user-log 45: nothing outside /data. Kit/carb write to /tmp and $HOME/.nvidia-omniverse inside the chroot;
# overlay them with per-instance /data dirs (only inside this private mount namespace, shared rootfs untouched).
mkdir -p "$CACHE/tmp" "$CACHE/omniverse"
b "$CACHE/tmp"       "$R/tmp"
b "$CACHE/omniverse" "$R/root/.nvidia-omniverse"

declare -a E=()
if [ -n "$ENVF" ]; then
  while IFS= read -r line; do case "$line" in ''|'#'*) continue;; esac; E+=("$line"); done < "$ENVF"
else
  E+=("PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" "ISAACSIM_PATH=/isaac-sim" "LANG=C.UTF-8")
fi
for v in $(compgen -v | grep -E '^(IR_|CUDA_|PYTHONPATH$|PIP_)' || true); do E+=("$v=${!v}"); done
E+=("LD_LIBRARY_PATH=/nvidia-driver:/root/cyclonedds/install/lib" "ACCEPT_EULA=Y" "PRIVACY_CONSENT=Y" "OMNI_KIT_ALLOW_ROOT=1"
    "NVIDIA_VISIBLE_DEVICES=all" "NVIDIA_DRIVER_CAPABILITIES=all")
# GPU 0 만. 호출자가 안 주면 0 으로 고정 (GPU2 금지)
[ -z "${CUDA_VISIBLE_DEVICES:-}" ] && E+=("CUDA_VISIBLE_DEVICES=0")
exec chroot "$R" env -i "${E[@]}" HOME=/root "$@"
