"""One E0 session (E §2.3): curl breakdown → closed-loop sweep → X8 → open loop → determinism probe."""
import dataclasses
import json
import pathlib
import subprocess
import time

from ..config import CFG
from . import payloads
from .closed_loop import closed_loop
from .open_loop import open_loop


def _tz(fmt_tz):
    return subprocess.run(["date", "+%Y-%m-%dT%H:%M"], capture_output=True, text=True,
                          env={"TZ": fmt_tz}).stdout.strip()


def curl_breakdown():
    """Network breakdown against the endpoint without credentials (status will be 401/404; timing is what we need)."""
    fmt = '{"namelookup":%{time_namelookup},"connect":%{time_connect},"appconnect":%{time_appconnect},' \
          '"starttransfer":%{time_starttransfer},"total":%{time_total},"code":%{http_code}}'
    r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-X", "POST", "-w", fmt, CFG.jev_url],
                       capture_output=True, text=True, timeout=10)
    return json.loads(r.stdout or "{}")


def run_session(call, out_path, slot, site, sizes=("S1", "S3", "G1"), ns=(1, 2, 3, 4, 6, 8), per_cell=300,
                x8_ns=(1, 4), open_sizes=("S1", "S3"), open_Tcs=(0.2, 0.33, 0.5), open_dur_s=60.0, det_n=20,
                curl_fn=curl_breakdown, curl_n=20, prereg=None):
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a", encoding="utf-8") as f:
        def put(obj):
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            f.flush()

        def put_recs(recs):
            for r in recs:
                put({"kind": "call", **dataclasses.asdict(r)})

        put({"kind": "header", "prereg": prereg, "slot": slot, "site": site, "utc": _tz("UTC"),
             "kst": _tz("Asia/Seoul"), "pdt": _tz("America/Los_Angeles"), "monotonic0": time.monotonic()})
        for _ in range(curl_n):
            put({"kind": "curl", **curl_fn()})
        base = {"slot": slot, "site": site}
        for size in sizes:
            for n in ns:
                put_recs(closed_loop(call, lambda i, s=size: payloads.make(s, i), n, per_cell,
                                     {**base, "phase": "closed", "size": size}))
        for n in x8_ns:
            put_recs(closed_loop(call, lambda i: payloads.make("X8", i), n, per_cell,
                                 {**base, "phase": "closed", "size": "X8"}))
        for size in open_sizes:
            for T_c in open_Tcs:
                recs, skipped = open_loop(call, lambda i, s=size: payloads.make(s, i), T_c, open_dur_s, 6,
                                          {**base, "phase": "open", "size": size})
                put_recs(recs)
                put({"kind": "open_summary", "size": size, "T_c": T_c, "skipped": skipped, "sent": len(recs)})
        put_recs([call(payloads.fixed(j), {**base, "phase": "determinism", "size": "S1", "j": j, "N": 1})
                  for j in range(det_n)])
