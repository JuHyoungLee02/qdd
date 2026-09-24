"""Closed-loop concurrency sweep: keep N requests in flight (E §2.3 load 1)."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait


def closed_loop(call, make, n_inflight, n_total, meta):
    out, i = [], 0
    with ThreadPoolExecutor(max_workers=n_inflight) as ex:
        live = set()
        while i < n_total or live:
            while i < n_total and len(live) < n_inflight:
                live.add(ex.submit(call, make(i), {**meta, "N": n_inflight, "i": i}))
                i += 1
            done, live = wait(live, return_when=FIRST_COMPLETED)
            out.extend(f.result() for f in done)
    return out
