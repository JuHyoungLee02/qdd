"""E0 one-session CLI (plan T8). Token is read from HARVEST_JEV_TOKEN_FILE; never printed.

Frozen: Jev is unusable (user-log 46, canon §44); the E0 latency test of the replacement is jevl_latency.md."""
import argparse
import json
import os
import pathlib
import subprocess
import sys

from .analysis.latency import judge_e0, records_to_rows
from .load.rate import RateLimiter
from .load.session import curl_breakdown, run_session


def _client():
    from .clients.jev import JevClient
    return JevClient(pathlib.Path(os.environ["HARVEST_JEV_TOKEN_FILE"]).read_text().strip())


def _prereg():
    p = pathlib.Path(__file__).resolve().parents[1] / "docs/stage3/prereg.json"
    return json.loads(p.read_text(encoding="utf-8"))["hashes"] if p.exists() else None


def main(argv=None, client_factory=_client, curl_fn=curl_breakdown):
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", required=True)
    ap.add_argument("--site", choices=["pod", "pc"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rps", type=float, default=18.0)
    ap.add_argument("--quick", action="store_true", help="tiny session for tests/smoke")
    a = ap.parse_args(argv)
    client, limiter = client_factory(), RateLimiter(a.rps)

    def call(req, meta):
        limiter.wait()
        return client.call(req, {**meta, "experiment": "E0"})

    stamp = subprocess.run(["date", "-u", "+%Y%m%dT%H%M"], capture_output=True, text=True).stdout.strip()
    out = pathlib.Path(a.out) / f"e0_{stamp}_{a.site}_{a.slot}.jsonl"
    kw = dict(per_cell=3, ns=(1, 2), open_dur_s=0.3, open_Tcs=(0.1,), det_n=2, curl_n=1) if a.quick else {}
    run_session(call, out, a.slot, a.site, curl_fn=curl_fn, prereg=_prereg(), **kw)
    summary = judge_e0(records_to_rows(out))
    out.with_name(out.stem + "_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("case", "d_p95_S1", "d_p95_S3", "fail_rate_S1", "N_max")}, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
