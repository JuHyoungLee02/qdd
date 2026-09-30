"""L9 object rows from fetched MolmoSpaces Objaverse packages (pod, pylib python: pxr + numpy + Pillow).

Per candidate (objv9_select.py output):
  size    USD render mesh (Y-up geometry -> z-up after the +90 deg x spawn rotation), then ONE uniform scale:
          target   (grasped top-down, 107 mm gripper) height 7-10 cm AND grasp width 2.5-8.5 cm AND long side
                   <= 25 cm, scale 0.3-3.0, not lying (height >= 0.6 x grasp width); scale closest to height 8.5 cm
          place    L9 container categories: the long horizontal side into the category range (PLACE_L)
          clutter  everything else: long side into 4-22 cm, height <= 22 cm
          The scaled USD is a copy next to the original (points / extents / translations x s; textures relative).
  colour  dominant basic colour of the UV-sampled diffuse texture (or the constant diffuse colour): red orange yellow
          green blue purple pink brown black white grey (objects_real.colour_word per sample, most common word).
  row     objv_table fields (usd visual copy, usd_physics, spawn_quat_wxyz, root_above_bottom, centre_from_root_xy,
          half_extents, height, grasp_width, length, footprint_r, mass, friction, category, name, split, license,
          attribution, source) + l9cat, role (target | place | clutter), colour, scale, height_orig.
  place   rows also get a KINEMATIC triangle-mesh wrapper (import_task_assets.wrap_kinematic) and a container row
          (import_task_assets.container_row: inside / place_kind into|onto / inner_floor_z / rim_z /
          opening_min_side) when an inside is found.
Workers run in parallel (--workers); output JSON {objects, containers, dropped}.
usage: python -m tools.l9.assets.objv9_build --sel sel.json --pkg PKG_DIR --out OUT.json [--start 0 --n 3000]"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

SOURCE = "MolmoSpaces (allenai/molmospaces, isaac/objects/objaverse/20260128), Objaverse 1.0 (ODC-BY) models"
Q_UP = [0.7071068, 0.7071068, 0.0, 0.0]
TGT_H, TGT_W, TGT_L, S_RANGE = (0.07, 0.10), (0.025, 0.085), 0.25, (0.3, 3.0)
PLACE_L = {"mug": (0.08, 0.13), "cup": (0.06, 0.10), "pen_holder": (0.06, 0.11), "utensil_holder": (0.08, 0.14),
           "vase": (0.07, 0.16), "jar": (0.07, 0.16), "bowl": (0.12, 0.22), "plate": (0.17, 0.27),
           "tray": (0.24, 0.40), "basket": (0.18, 0.36), "bin": (0.20, 0.32), "box": (0.12, 0.30)}
CLUTTER_L = (0.04, 0.22)
THIN_L, THIN_W, THIN_H = {"pen": (0.12, 0.19), "spoon_fork": (0.13, 0.20)}, (0.004, 0.035), 0.035
Q_LIE = [0.0, 1.0, 0.0, 0.0]  # (rotX +90) x Q_UP: a Y-up long object lies along canonical y (the task_items pen
# convention: gate_containers stands a pen by rotating canonical y to z)
COLOUR_ADJ = ("red", "orange", "yellow", "green", "blue", "purple", "pink", "brown", "black", "white", "grey", "gray",
              "beige", "golden", "gold", "silver", "dark", "light", "tan", "cream", "violet", "navy", "teal", "maroon",
              "turquoise", "bronze", "copper", "ivory", "colorful", "multicolored", "rainbow")
BLACK_TEX = "__black_texture__"
COLOURS = ("red", "orange", "yellow", "green", "blue", "purple", "pink", "brown", "black", "white", "grey")


def licence_name(lic: str) -> str:
    lic = lic.lower()
    if "cc0" in lic:
        return "CC0 1.0"
    return "CC BY-SA 4.0" if "sa" in lic else "CC BY 4.0"


def target_scale(h, g, L):
    lo = max(TGT_H[0] / h, TGT_W[0] / g, S_RANGE[0])
    hi = min(TGT_H[1] / h, TGT_W[1] / g, TGT_L / L, S_RANGE[1])
    if lo > hi or h < 0.6 * g:
        return None
    return float(np.clip(0.085 / h, lo, hi))


def place_scale(cat, L, h):
    lo, hi = PLACE_L[cat]
    s = lo / L if L < lo else (hi / L if L > hi else 1.0)
    return s if h * s <= 0.35 else None


def clutter_scale(L, h):
    M = max(L, h)
    s = CLUTTER_L[0] / M if M < CLUTTER_L[0] else (CLUTTER_L[1] / M if M > CLUTTER_L[1] else 1.0)
    return s if h * s >= 0.008 else None


def thin_scale(cat, h, g, L):
    """Pens / spoons / forks lying flat (the THOR pen rule of task_items: thin grasp, own size box)."""
    lo, hi = THIN_L[cat]
    s = lo / L if L < lo else (hi / L if L > hi else 1.0)
    if not (THIN_W[0] <= g * s <= THIN_W[1] and h * s <= THIN_H):
        return None
    return s


def write_scaled(src: str, dst: str, s: float) -> str:
    """Uniform scale about the origin: every Mesh's points / extent and every translate op x s (world = s x world)."""
    from pxr import Gf, Sdf, Usd, UsdGeom, Vt
    lay = Sdf.Layer.FindOrOpen(src)
    if os.path.exists(dst):
        os.remove(dst)
    new = Sdf.Layer.CreateNew(dst)
    new.TransferContent(lay)
    st = Usd.Stage.Open(new)
    for p in st.Traverse():
        if p.IsA(UsdGeom.Mesh):
            m = UsdGeom.Mesh(p)
            pts = m.GetPointsAttr().Get()
            if pts is not None:
                m.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(np.asarray(pts, np.float32) * s))
            ex = m.GetExtentAttr().Get()
            if ex is not None:
                m.GetExtentAttr().Set(Vt.Vec3fArray.FromNumpy(np.asarray(ex, np.float32) * s))
        a = p.GetAttribute("extentsHint")
        if a and a.Get() is not None:
            v = np.asarray(a.Get(), np.float64)
            v[np.abs(v) < 1e30] *= s
            a.Set(Vt.Vec3fArray.FromNumpy(v.astype(np.float32)))
        if p.IsA(UsdGeom.Xformable):
            for op in UsdGeom.Xformable(p).GetOrderedXformOps():
                if op.GetOpType() == UsdGeom.XformOp.TypeTranslate and op.Get() is not None:
                    op.Set(type(op.Get())(*(float(c) * s for c in op.Get())))
    new.Save()
    return dst


def colour_of(stage, d0: str):
    """Most common basic colour word over UV-sampled diffuse texels (or constant diffuse colours)."""
    from PIL import Image
    from pxr import Usd, UsdGeom, UsdShade

    from harvest.sim.assets_x import objects_real as OR
    words = Counter()
    n_tex, n_black = 0, 0
    for p in stage.Traverse(Usd.TraverseInstanceProxies()):
        if not p.IsA(UsdGeom.Mesh) or UsdGeom.Imageable(p).ComputePurpose() not in ("default", "render"):
            continue
        mat = UsdShade.MaterialBindingAPI(p).ComputeBoundMaterial()[0]
        tex, const = None, None
        if mat:
            for sh in Usd.PrimRange(mat.GetPrim()):
                if sh.GetTypeName() != "Shader":
                    continue
                f = sh.GetAttribute("inputs:file")
                if f and f.Get() is not None and tex is None:
                    tex = f.Get().resolvedPath or os.path.join(d0, str(f.Get().path))
                c = sh.GetAttribute("inputs:diffuseColor")
                if c and c.Get() is not None:
                    const = tuple(float(x) for x in c.Get())
        st_ = UsdGeom.PrimvarsAPI(p).GetPrimvar("st")
        uv = np.asarray(st_.Get(), float) if st_ and st_.Get() is not None else np.zeros((0, 2))
        n_pts = len(UsdGeom.Mesh(p).GetPointsAttr().Get() or [])
        if tex and os.path.exists(tex) and len(uv):
            im = np.asarray(Image.open(tex).convert("RGB"))
            H, W = im.shape[:2]
            n_tex += 1
            if im.max() < 5:  # MolmoSpaces placeholder (3 kB all-black PNG): the object renders black
                n_black += 1
                continue
            idx = np.random.default_rng(0).choice(len(uv), size=min(2000, len(uv)), replace=False)
            u = np.clip((uv[idx, 0] % 1.0) * (W - 1), 0, W - 1).astype(int)
            v = np.clip((1 - uv[idx, 1] % 1.0) * (H - 1), 0, H - 1).astype(int)
            for rgb in im[v, u]:
                w = OR.colour_word(rgb)
                if w:
                    words[w] += 1
        elif const is not None:
            w = OR.colour_word([c * 255 for c in const])
            if w:
                words[w] += max(1, n_pts)
    if n_tex and n_black == n_tex:
        return BLACK_TEX
    if not words:
        return None
    w = words.most_common(1)[0][0]
    return "grey" if w == "gray" else w


def build_one(args):
    s, pkg = args
    from pxr import Usd

    from harvest.sim.assets_x import usd_import as UI
    from tools.l8x_assets import import_task_assets as IT
    uid = s["uid"]
    d0 = os.path.join(pkg, s["package"].replace(".tar.zst", ""), "obja_" + uid)
    src = os.path.join(d0, "obja_" + uid + ".usda")
    if not os.path.exists(src):
        return uid, None, None, "not fetched"
    try:
        stage = Usd.Stage.Open(src)
        P, F = UI.render_mesh(stage)
        if len(F) == 0:
            return uid, None, None, "no render mesh"
        V = np.stack([P[:, 0], -P[:, 2], P[:, 1]], 1)  # Y-up geometry after the +90 deg x spawn rotation
        ext = V.max(0) - V.min(0)
        h, wx, wy = float(ext[2]), float(ext[0]), float(ext[1])
        g, L = min(wx, wy), max(wx, wy)
        if min(h, g) <= 1e-4:
            return uid, None, None, "degenerate"
        cat = s["l9cat"]
        role, sc, quat, rule = None, None, Q_UP, "topdown_7_10cm"
        if cat in THIN_L:
            if h > 1.5 * L:  # modelled standing: lay it down along canonical y
                V = np.stack([V[:, 0], -V[:, 2], V[:, 1]], 1)
                quat = Q_LIE
                ext = V.max(0) - V.min(0)
                h, wx, wy = float(ext[2]), float(ext[0]), float(ext[1])
                g, L = min(wx, wy), max(wx, wy)
            sc = thin_scale(cat, h, g, L)
            if sc is not None:
                role, rule = "target", "thin_pen"
        if role is None and cat in PLACE_L:
            sc = place_scale(cat, L, h)
            if sc is not None:
                role = "place"
                if cat in ("mug", "cup", "jar", "vase", "box") and (
                        TGT_H[0] <= h * sc <= TGT_H[1] and TGT_W[0] <= g * sc <= TGT_W[1]):
                    role = "target"
        if role is None:
            sc = target_scale(h, g, L)
            role = "target" if sc is not None else None
        if role is None:
            sc = clutter_scale(L, h)
            role = "clutter" if sc is not None else None
        if role is None:
            return uid, None, None, f"size h {h:.3f} g {g:.3f} L {L:.3f}"
        sc = round(float(sc), 4)
        usd = src if abs(sc - 1.0) < 1e-3 else write_scaled(src, os.path.join(d0, f"obja_{uid}_l9s{int(round(sc * 1000))}.usda"), sc)
        vis = UI.make_visual(usd)["visual"]
        V = V * sc
        lo, hi = V.min(0), V.max(0)
        h, wx, wy = float(hi[2] - lo[2]), float(hi[0] - lo[0]), float(hi[1] - lo[1])
        g, L = min(wx, wy), max(wx, wy)
        colour = colour_of(stage, d0)
        if colour == BLACK_TEX:
            return uid, None, None, "black_texture placeholder"
        li = s.get("license_info") or {}
        mass0 = float(s.get("mass") or 0.2) * (sc ** 3 if sc != 1.0 else 1.0)
        name = (s.get("name_short") or s.get("one_word") or s["category"]).strip().lower()
        nw = name.split()
        if any(w in COLOUR_ADJ and w != colour and not (w == "gray" and colour == "grey") for w in nw):
            name = " ".join(w for w in nw if w not in COLOUR_ADJ) or (s.get("one_word") or s["category"]).lower()
        r4 = lambda v: round(float(v), 4)  # noqa: E731
        oid = "l9o_" + uid[:16]
        row = {"uid": uid, "id": oid, "shape": "mesh", "usd": vis, "usd_physics": usd, "up": "Y",
               "body_rel": f"Geometry/obja_{uid}", "extent_m": [r4(wx), r4(h), r4(wy)],
               "spawn_quat_wxyz": quat, "grasp_rule": rule if role == "target" else None, "root_above_bottom": r4(-lo[2]),
               "centre_from_root_xy": [r4((lo[0] + hi[0]) / 2), r4((lo[1] + hi[1]) / 2)],
               "half_extents": [r4(wx / 2), r4(wy / 2), r4(h / 2)], "height": r4(h), "grasp_width": r4(g),
               "length": r4(L), "footprint_r": r4(math.hypot(wx, wy) / 2), "top_z_rel": r4(h),
               "grasp_axis": "x" if wx <= wy else "z_usd (turn yaw 90 deg)",
               "mass": round(min(1.0, max(0.05, mass0)), 3), "friction": [0.8, 0.8],
               "l9cat": cat, "category": s["category"], "name": name, "split": s["split"], "role": role,
               "colour": colour, "scale": sc, "height_orig": r4(h / sc),
               "license": licence_name(s["license"]),
               "attribution": {"creator": li.get("creator_username"), "uri": li.get("uri")}, "source": SOURCE}
        cont = None
        if cat in PLACE_L:
            kin = IT.wrap_kinematic(usd, os.path.join(d0, f"obja_{uid}_l9kin.usda"))
            c = IT.container_row("l9c_" + uid[:16], cat, SOURCE, uid, V, F, kin, row["license"],
                                 f"{li.get('creator_username')} ({li.get('uri')}), {row['license']}", quat=tuple(quat))
            if c.get("place_kind"):
                c.update(colour=colour, name=name, l9cat=cat, uid=uid, scale=sc, split=s["split"],
                         attribution=row["attribution"], object_id=oid,
                         opening_min_side=(c.get("inside") or {}).get("opening_min_side"))
                cont = c
        return uid, row, cont, None
    except Exception as e:  # noqa: BLE001
        return uid, None, None, f"{type(e).__name__}: {e}"[:160]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sel", required=True)
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--n", type=int, default=100000)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args(argv)
    sel = json.load(open(a.sel))[a.start:a.start + a.n]
    objs, conts, drop = {}, {}, {}
    with Pool(a.workers, maxtasksperchild=50) as pool:
        for k, (uid, row, cont, why) in enumerate(pool.imap(build_one, [(s, a.pkg) for s in sel], chunksize=4)):
            if row:
                objs[row["id"]] = row
            if cont:
                conts[cont["id"]] = cont
            if why:
                drop[uid] = why
            if k % 200 == 0:
                print("progress", k, len(sel), len(objs), len(conts), flush=True)
    json.dump({"license_rule": "CC0 / CC BY / CC BY-SA only (no NC, no ND); attribution per object",
               "source": SOURCE, "objects": objs, "containers": conts, "dropped": drop}, open(a.out, "w"))
    print("DONE objects", len(objs), dict(Counter(o["role"] for o in objs.values())), "containers", len(conts),
          "dropped", len(drop), Counter(w.split(" ")[0] for w in drop.values()).most_common(8), flush=True)
    print("colours", Counter(o["colour"] for o in objs.values()).most_common(), flush=True)


if __name__ == "__main__":
    main()
