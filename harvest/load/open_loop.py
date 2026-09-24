"""Open-loop periodic send every T_c; a slot is skipped when N_cap are in flight (E §2.3 load 2)."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor


def open_loop(call, make, T_c, duration_s, n_cap, meta):
    out, lock, live = [], threading.Lock(), [0]
    skipped, i = 0, 0

    def run(req, m):
        try:
            r = call(req, m)
            with lock:
                out.append(r)
        finally:
            with lock:
                live[0] -= 1

    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=n_cap) as ex:
        k = 0
        while k * T_c < duration_s:
            time.sleep(max(0.0, t0 + k * T_c - time.monotonic()))
            with lock:
                full = live[0] >= n_cap
                if not full:
                    live[0] += 1
            if full:
                skipped += 1
            else:
                ex.submit(run, make(i), {**meta, "T_c": T_c, "i": i, "slot_k": k})
                i += 1
            k += 1
    return out, skipped
