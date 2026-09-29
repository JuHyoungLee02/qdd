"""Low open boxes for task C (coordinator, 2026-09-29): THOR boxes with their flap bodies removed (flaps and flap
joints deactivated in a flattened copy), made static (usd_import.make_static) and inspected on the CPU: the inside
(container surface) and the rim height; kept when the inside is at least MIN_SIDE on both sides and the rim at most
RIM_MAX above the bottom (the carry over the rim stays inside the executor box). Output rows use the bake_open
record format (xart fixtures of kind C). No rendering (the render cards go to L8S).
usage: python tools/l8x_assets/box_noflap.py THOR_USD_DIR OUT.json"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x import usd_import as UI  # noqa: E402

MIN_SIDE, RIM_MAX = 0.14, 0.22


def noflap(src: str, dst: str) -> int:
    from pxr import Usd
    layer = Usd.Stage.Open(src).Flatten()
    n = 0

    def visit(spec):
        nonlocal n
        if "flap" in spec.name.lower():
            spec.active = False
            n += 1
            return
        for c in spec.nameChildren:
            visit(c)
    for root in layer.rootPrims:
        visit(root)
    layer.Export(dst)
    return n


def main(argv=None):
    a = argv or sys.argv[1:]
    out = {}
    for pkg in sorted(os.listdir(a[0])):
        if not pkg.startswith("thor_Box_"):
            continue
        name = pkg[len("thor_"):]
        src = os.path.join(a[0], pkg, name, name + ".usda")
        if not os.path.exists(src):
            continue
        try:
            flat = os.path.join(os.path.dirname(src), name + "_noflap.usda")
            nf = noflap(src, flat)
            s = UI.make_static(flat, mode="thor")
            ins = UI.inspect(s["dst"])
            cont = [x for x in ins["surfaces"] if x["container"] and x["covered_above"] is None]
            best = max(cont, key=lambda x: x["area"]) if cont else None
            ok, why = False, None
            if best is None:
                why = "no open inside"
            else:
                (x0, x1), (y0, y1) = best["free_box"]
                if min(x1 - x0, y1 - y0) < MIN_SIDE:
                    why = f"inside {x1 - x0:.2f} x {y1 - y0:.2f} m"
                elif (best["rim_z"] or 0) > RIM_MAX:
                    why = f"rim {best['rim_z']:.3f} m"
                else:
                    ok = True
            out[name + "_noflap"] = dict(src=src, flaps_removed=nf, open=flat, **s, **ins, joints={},
                                         ok=ok, why=why, license="CC BY 4.0 (MolmoSpaces objects_thor, AI2-THOR)")
            print(name, "flaps", nf, "ok" if ok else why, flush=True)
        except Exception as e:  # noqa: BLE001
            out[name + "_noflap"] = {"error": f"{type(e).__name__}: {e}"[:200]}
    json.dump(out, open(a[1], "w"), indent=1)
    print("NOFLAP", sum(bool(r.get("ok")) for r in out.values()), "/", len(out))


if __name__ == "__main__":
    main()
