"""Summarise an L9 run9 cProfile dump (L9_PROFILE): wall split into physics step, rendering / camera readback, cuRobo
(planner IPC), episode writing and the rest (pure).
usage: python tools/l9/prof_summary.py <stats file> [--top 25]"""
import pstats
import sys

KEYS = {  # category -> substrings of "file:function" whose cumulative time counts (outermost match wins)
    "curobo_ipc": ("plan9_server.py:_call",),
    "render": ("simulation_context.py:render", "camera.py:_update_buffers", "camera.py:update", "camera_rgb",
               "camera_depth", "ext_capture"),
    "physics_step": ("simulation_context.py:step", "manager_based_env.py:step", "manager_based_rl_env.py:step"),
    "write": ("_save_call", "png_bytes", "savez_compressed"),
}


def main():
    a = sys.argv[1:]
    top = int(a[a.index("--top") + 1]) if "--top" in a else 25
    st = pstats.Stats(a[0])
    total = max(v[3] for v in st.stats.values())
    rows = []
    for (f, ln, fn), (cc, nc, tt, ct, callers) in st.stats.items():
        rows.append((ct, tt, nc, f"{f.split('/')[-1]}:{fn}"))
    rows.sort(reverse=True)
    print(f"total (largest cumulative) {total:.1f} s")
    for cat, keys in KEYS.items():
        best = max((r for r in rows if any(k in r[3] for k in keys)), default=None, key=lambda r: r[0])
        print(f"{cat:14s} {best[0] if best else 0:8.1f} s  ({100 * (best[0] if best else 0) / total:4.1f} %)  "
              f"{best[3] if best else '-'}")
    print("-- top cumulative")
    for ct, tt, nc, name in rows[:top]:
        print(f"{ct:8.1f} {tt:8.1f} {nc:9d}  {name}")
    print("-- top self time")
    for ct, tt, nc, name in sorted(rows, key=lambda r: -r[1])[:top]:
        print(f"{tt:8.1f} {ct:8.1f} {nc:9d}  {name}")


if __name__ == "__main__":
    main()
