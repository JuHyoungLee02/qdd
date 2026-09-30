"""E-VB1 render-card check (stdlib only): may VB1 use this card now?
  python3 card.py busy <pod>:<gpu>  -> prints 'free' (exit 0) or the reason (exit 1)
Busy when L9's GPU_WANTED names the card (an empty file = every card, 'all' too) or a process that is not VB1
(no 'tools.vb1' in its command line) holds memory on the card (L9 / JCR / E-M35CL lanes, gate tools)."""
from __future__ import annotations

import re
import subprocess
import sys

L9_WANTED = "/data/harvest/out/l9/GPU_WANTED"


def card_wanted(card: str, path: str = L9_WANTED) -> bool:
    try:
        txt = open(path).read()
    except OSError:
        return False
    if not txt.strip() or re.search(r"(^|\W)all(\W|$)", txt, re.I):
        return True
    pod, gpu = card.split(":")
    for m in re.finditer(r"(7a2a-x2|7a2a-x3|7a2a|x2|x3):([0-9][0-9,]*)", txt):
        p = {"7a2a-x2": "x2", "7a2a-x3": "x3"}.get(m.group(1), m.group(1))
        if p == pod and gpu in m.group(2).split(","):
            return True
    return False


def foreign_procs(gpu: str) -> list:
    """Non-VB1 compute processes on GPU index gpu of this pod."""
    q = subprocess.run(["nvidia-smi", "--query-gpu=index,pci.bus_id", "--format=csv,noheader"],
                       capture_output=True, text=True).stdout
    bus = {i.strip(): b.strip() for i, b in (ln.split(",") for ln in q.strip().splitlines() if "," in ln)}
    apps = subprocess.run(["nvidia-smi", "--query-compute-apps=gpu_bus_id,pid", "--format=csv,noheader"],
                          capture_output=True, text=True).stdout
    out = []
    for ln in apps.strip().splitlines():
        if "," not in ln:
            continue
        b, pid = (x.strip() for x in ln.split(",", 1))
        if b != bus.get(gpu):
            continue
        try:
            cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue  # gone (or another pid namespace): not ours to judge
        if "tools.vb1" not in cmd:
            out.append(f"{pid}:{cmd[:80]}")
    return sorted(set(out))


def busy(card: str) -> str | None:
    if card_wanted(card):
        return f"GPU_WANTED names {card}"
    f = foreign_procs(card.split(":")[1])
    return f"foreign process {f[0]}" if f else None


if __name__ == "__main__":
    if sys.argv[1] == "busy":
        why = busy(sys.argv[2])
        print(why or "free")
        sys.exit(1 if why else 0)
