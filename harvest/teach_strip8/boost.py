"""boost1 (docs/stage3/prereg_boost1.md): two code-side fixes of the E-DIST8 D (d-min, point + depth converter) closed
loop, no retraining, from the PT-ND failure decomposition (results/dist8.md 5b, f703243):
  (a) PlaceMemory: the head depth frame (with the TCP and table plane) of the last call before the grasp is kept; while
      holding, point targets are resolved on that frame, so the held object cannot occlude / bias the place target
      (the head camera is fixed on the head; the place object does not move while carried).
  (b) LoopGuard: an 'above' point whose target is within tol of the previous 'above' target, after the arm has
      reached that target (TCP within tol), counts as a repeat; at the n-th repeat the command is turned into the next
      intent: holding -> place + open, not holding -> grasp + close (same point). Any other command resets the count.
BoostEpisode(fix_mem, fix_loop): both False = the teach_pt episode unchanged (the 'before' arm). H (h-min, move
commands): the same two fixes on the PT branch only (memory = the depth H saw before the grasp); the xyz branch (no
depth / unresolved) is never touched."""
from __future__ import annotations

import numpy as np

from ..astra_solo import resolve as RS
from ..astra_solo.pt_episode import PtEpisode

N_REPEAT = 2
TOL = 0.015


class LoopGuard:
    def __init__(self, n: int = N_REPEAT, tol: float = TOL):
        self.n, self.tol, self.count, self.last = n, tol, 0, None

    def check(self, cmd: dict, goal, tcp, holding: bool):
        """-> None (keep the command) or {"height", "gripper"} to use instead."""
        if cmd.get("mode") != "point" or cmd.get("height") != "above" or goal is None:
            self.count, self.last = 0, None
            return None
        g, t = np.asarray(goal, float), np.asarray(tcp, float)
        if self.last is not None and np.linalg.norm(g - self.last) <= self.tol and np.linalg.norm(t - self.last) <= self.tol:
            self.count += 1
        else:
            self.count = 0
        if self.count >= self.n:
            self.count, self.last = 0, None
            return {"height": "place", "gripper": "open"} if holding else {"height": "grasp", "gripper": "close"}
        return None

    def done(self, goal):
        """After executing: remember the 'above' target just commanded (None = nothing to remember)."""
        if goal is not None:
            self.last = np.asarray(goal, float)


class PlaceMemory:
    def __init__(self):
        self.depth = self.tcp = self.plane = None

    def update(self, depth, tcp, plane, holding: bool):
        if not holding and depth is not None:
            self.depth, self.tcp, self.plane = depth, list(tcp), plane

    def frame(self, holding: bool, live):
        """-> (depth to resolve on, TCP for the robot mask or None = caller's, used memory?)."""
        if holding and self.depth is not None:
            return self.depth, self.tcp, True
        return live, None, False


CHANGE_MM = 7.0  # boost1b scene-change threshold on the 80th percentile of |live - memory| depth
CHANGE_Q = 80
WIN_PX = 50  # half size of the check window around the pointed pixel
TCP_EXCL_M = 0.15  # live points this close to the TCP (gripper + held object) are not compared
N_MIN = 50


def px_of(cam, p) -> list:
    """Pixel (u, v) of a base-frame point (the same pixel convention as resolve.depth_points)."""
    from ..astra_motion.geometry import PIX_C
    pc = (np.asarray(p, float) - np.asarray(cam.t, float)) @ np.asarray(cam.R, float)
    return [cam.fx * pc[0] / pc[2] + cam.cx - PIX_C, cam.fy * pc[1] / pc[2] + cam.cy - PIX_C]


class PointMemory:
    """boost1b: the pre-grasp head depth kept as base-frame points (capture-time camera from the FK), re-rendered
    into the current head camera with a z-buffer (1-pixel splat, then one 3x3 min fill of holes)."""

    def __init__(self):
        self.P = self.tcp = self.plane = None

    def capture(self, cam, depth, tcp, plane):
        P = RS.depth_points(cam, depth).reshape(-1, 3)
        hgt = P[:, 2] - plane
        keep = np.isfinite(P).all(1) & ~RS.robot_mask(hgt, plane, tcp)  # the robot itself is not remembered
        self.P, self.tcp, self.plane = P[keep], list(tcp), plane

    def render(self, cam) -> np.ndarray:
        from ..astra_motion.geometry import PIX_C
        pc = (self.P - np.asarray(cam.t, float)) @ np.asarray(cam.R, float)
        z = pc[:, 2]
        ok = z > 0.05
        u = np.floor(cam.fx * pc[ok, 0] / z[ok] + cam.cx - PIX_C + 0.5).astype(int)
        v = np.floor(cam.fy * pc[ok, 1] / z[ok] + cam.cy - PIX_C + 0.5).astype(int)
        z = z[ok]
        ins = (u >= 0) & (u < cam.W) & (v >= 0) & (v < cam.H)
        D = np.full((cam.H, cam.W), np.inf)
        np.minimum.at(D, (v[ins], u[ins]), z[ins])
        hole = ~np.isfinite(D)
        if hole.any():
            pad = np.pad(D, 1, constant_values=np.inf)
            nb = np.min(np.stack([pad[1 + dy:1 + dy + cam.H, 1 + dx:1 + dx + cam.W]
                                  for dy in (-1, 0, 1) for dx in (-1, 0, 1)]), 0)
            D = np.where(hole, nb, D)
        return np.where(np.isfinite(D), D, np.nan)

    def check(self, cam, live, px, tcp) -> tuple:
        """-> (keep memory?, info). Compares the live depth with the re-rendered memory in a window around the
        pointed pixel, only where both are valid and the live point is neither the robot nor within TCP_EXCL_M of
        the TCP (gripper, held object). Too few pixels (< N_MIN) -> keep (unverified)."""
        mem = self.render(cam)
        u, v = int(round(px[0])), int(round(px[1]))
        sl = (slice(max(v - WIN_PX, 0), max(min(v + WIN_PX + 1, cam.H), 0)),
              slice(max(u - WIN_PX, 0), max(min(u + WIN_PX + 1, cam.W), 0)))
        L = RS.depth_points(cam, live)[sl]
        dl, dm = np.asarray(live, float)[sl], mem[sl]
        near = np.linalg.norm(L - np.asarray(tcp, float), axis=-1) < TCP_EXCL_M
        rob = RS.robot_mask(L[..., 2] - self.plane, self.plane, tcp)
        m = np.isfinite(dl) & np.isfinite(dm) & np.isfinite(L).all(-1) & ~near & ~rob
        n = int(m.sum())
        if n < N_MIN:
            return True, {"n": n, "stat_mm": None, "unverified": True}
        stat = float(np.percentile(np.abs(dl[m] - dm[m]), CHANGE_Q)) * 1e3
        return stat <= CHANGE_MM, {"n": n, "stat_mm": round(stat, 1)}


DESC_XY_M = 0.02  # DescendGuard: the TCP is above the pointed object (xy)
DESC_ABOVE_M = 0.03  # ... and more than this above the grasp height (top - 0.02)
DESC_DZ_M = 0.01  # a call 'descended' when the TCP went down more than this


class DescendGuard:
    """(d) Not holding, the command points at an object whose footprint centre is within DESC_XY_M of the TCP, the
    TCP is still DESC_ABOVE_M above the grasp height, the intent is not grasp, and the previous such call did not
    descend: n such calls in a row -> grasp + close at the same point."""

    def __init__(self, n: int = N_REPEAT):
        self.n, self.count, self.z = n, 0, None

    def check(self, cmd: dict, res: dict | None, tcp, holding: bool):
        t = np.asarray(tcp, float)
        ok = (not holding and cmd.get("mode") == "point" and cmd.get("height") not in ("grasp", None)
              and res is not None and res.get("kind") == "object" and res.get("xy") is not None
              and np.hypot(*(t[:2] - np.asarray(res["xy"], float))) <= DESC_XY_M
              and t[2] > float(res["top"]) - 0.02 + DESC_ABOVE_M)
        if not ok or (self.z is not None and t[2] < self.z - DESC_DZ_M):
            self.count, self.z = (1, float(t[2])) if ok else (0, None)
            return None if self.count < self.n else self._fire()
        self.count, self.z = self.count + 1, float(t[2])
        return self._fire() if self.count >= self.n else None

    def _fire(self):
        self.count, self.z = 0, None
        return {"height": "grasp", "gripper": "close"}


def crop_png(png: bytes, point_2d, half: int = 64, out: int = 256) -> bytes:
    """(a) A square crop of the head image around point_2d (0-1000 scale), a small cross at the point, resized."""
    import io

    from PIL import Image, ImageDraw
    im = Image.open(io.BytesIO(png)).convert("RGB")
    W, H = im.size
    u, v = point_2d[0] / RS.SCALE * W, point_2d[1] / RS.SCALE * H
    box = (int(u) - half, int(v) - half, int(u) + half, int(v) + half)
    c = Image.new("RGB", (2 * half, 2 * half), (0, 0, 0))
    c.paste(im.crop((max(box[0], 0), max(box[1], 0), min(box[2], W), min(box[3], H))),
            (max(-box[0], 0), max(-box[1], 0)))
    d = ImageDraw.Draw(c)
    for w_, col in ((3, (0, 0, 0)), (1, (0, 255, 255))):
        d.line([(half - 8, half), (half + 8, half)], fill=col, width=w_)
        d.line([(half, half - 8), (half, half + 8)], fill=col, width=w_)
    b = io.BytesIO()
    c.resize((out, out)).save(b, format="PNG")
    return b.getvalue()


VERIFY_Q = ("Image 1 is a crop of the robot's head camera around a point marked with a small cyan cross. Is the marked "
            "point on the {name} (the object to move)? Answer JSON only: {{\"yes\": true}} or {{\"yes\": false}}.")
RECHECK_NOTE = ("\nNOTE: your point ({x:.0f}, {y:.0f}) was checked and it is not on the {name}. Point at the {name} "
                "itself.")


class BoostEpisode(PtEpisode):
    def __init__(self, *a, fix_mem: bool = False, fix_loop: bool = False, mem_points: bool = False,
                 fix_descend: bool = False, recheck: bool = False, **kw):
        """mem_points (boost1b, D point commands only): the memory is a base-frame point cloud re-rendered into the
        current head camera, with the scene-change check (implies the memory fix). fix_descend (round 2 d):
        DescendGuard. recheck (round 2 a): verify the pointed pixel before the grasp and re-ask once."""
        kw.setdefault("iface", "d-min")
        super().__init__(*a, **kw)
        self.fix_mem, self.fix_loop, self.mem_points = fix_mem or mem_points, fix_loop or fix_descend, mem_points
        self.fix_descend, self.recheck = fix_descend, recheck
        self.mem, self.guard, self.pmem, self.dguard = PlaceMemory(), LoopGuard(), PointMemory(), DescendGuard()
        self.boost_log, self.mem_log, self.recheck_log = [], [], []
        self._loop_on = fix_loop

    def _ask(self, text, images, i):
        parsed, rec = super()._ask(text, images, i)
        if not self.recheck or parsed is None:
            return parsed, rec
        c = parsed["command"]
        st = self.w.status()
        if (c.get("mode") != "point" or c.get("point_2d") is None or c.get("height") not in ("above", "grasp")
                or self.holding(st)):
            return parsed, rec
        from ..astra_motion.prompts import OBJ_NAME
        name = OBJ_NAME.get(self.info["tgt"], "object to move")
        crop = crop_png(images[0][1], c["point_2d"])
        rep = self.model.ask(VERIFY_Q.format(name=name), [("head camera crop", crop)],
                             {"seed": self.seed, "task": self.task, "call": len(self.calls), "site": i, "verify": True})
        ans = None
        try:
            from ..astra_motion.schema import extract_json
            ans = bool(extract_json(rep.text or "").get("yes"))
        except Exception:  # noqa: BLE001 - an unreadable verdict keeps the command
            ans = None
        self.recheck_log.append({"call": len(self.calls), "site": i, "point": list(c["point_2d"]), "answer": ans})
        if ans is not False:
            return parsed, rec
        p2, rec2 = super()._ask(text + RECHECK_NOTE.format(x=c["point_2d"][0], y=c["point_2d"][1], name=name), images, i)
        self.recheck_log[-1]["reasked"] = p2 is not None
        return (p2, rec2) if p2 is not None else (parsed, rec)

    def _resolve_points(self, cmd: dict, st: dict) -> dict:
        hold = self.holding(st)
        if not hold:
            if self.depth is not None:
                self.pmem.capture(self.head, self.depth, st["tcp"], self.plane if self.plane is not None
                                  else self.w.table_z)
            return PtEpisode.resolve(self, cmd, st)
        if cmd.get("height") == "lift" or self.pmem.P is None:
            return PtEpisode.resolve(self, cmd, st)
        px = RS.to_pixel(cmd["point_2d"], self.head.W, self.head.H)
        ok, info = self.pmem.check(self.head, self.depth, px, st["tcp"])
        self.mem_log.append(dict(info, call=len(self.calls), kept=ok))
        if not ok:
            self.pmem.P = None  # the scene changed: drop the memory, live depth from now on
            return dict(PtEpisode.resolve(self, cmd, st), memory_dropped=True)
        depth = self.pmem.render(self.head)
        res = RS.resolve_point(self.head, depth, self.w.table_z, cmd["point_2d"], tcp=self.pmem.tcp)
        if res["kind"] == "none":
            return {"kind": "none", "goal": None, "holding": hold, "memory": True}
        goal, notes = RS.target_of(cmd["height"], res, res["plane"], st["tcp"], hold, self.grip_offset)
        return dict(res, goal=[round(float(v), 4) for v in goal], holding=hold, notes=notes, memory=True,
                    grip_offset=None if self.grip_offset is None else round(self.grip_offset, 4))

    def resolve(self, cmd: dict, st: dict) -> dict:
        if self.mem_points:
            return self._resolve_points(cmd, st)
        hold = self.holding(st)
        if self.fix_mem:
            self.mem.update(self.depth, st["tcp"], self.plane, hold)
        if not (self.fix_mem and hold and cmd.get("height") != "lift"):
            return super().resolve(cmd, st)
        depth, mtcp, used = self.mem.frame(hold, self.depth)
        if not used:
            return super().resolve(cmd, st)
        res = RS.resolve_point(self.head, depth, self.w.table_z, cmd["point_2d"], tcp=mtcp)
        if res["kind"] == "none":
            return {"kind": "none", "goal": None, "holding": hold, "memory": True}
        goal, notes = RS.target_of(cmd["height"], res, res["plane"], st["tcp"], hold, self.grip_offset)
        return dict(res, goal=[round(float(v), 4) for v in goal], holding=hold, notes=notes, memory=True,
                    grip_offset=None if self.grip_offset is None else round(self.grip_offset, 4))

    def _h_resolver(self, st):
        """H (move): the PT converter bound to H's depth; with fix_mem, while holding, bound to the depth H saw on
        the last call before the grasp (H's own depth: on / noisy). No depth -> None (xyz branch, no fix)."""
        base = super()._h_resolver(st)
        if base is None or not self.fix_mem:
            return base
        hold = self.holding(st)
        self.mem.update(self.h_used_depth, st["tcp"], self.plane, hold)
        depth, mtcp, used = self.mem.frame(hold, self.h_used_depth)
        if not used:
            return base

        def res(cmd):
            if cmd["height"] == "lift":
                return base(cmd)
            r = RS.resolve_point(self.head, depth, self.w.table_z, cmd["point_2d"], tcp=mtcp)
            if r["kind"] == "none":
                return None, dict(r, memory=True)
            g, notes = RS.target_of(cmd["height"], r, r["plane"], st["tcp"], hold, self.grip_offset)
            return g, dict(r, notes=notes, memory=True)
        return res

    def _execute_move(self, cmd) -> list:
        from ..astra_solo import hybrid as HY
        st = self.w.status()
        goal, branch, _ = HY.select(dict(cmd), self._h_resolver(st))
        sw = None
        if branch == "pt":
            sw = self.guard.check(dict(cmd, mode="point"), goal, st["tcp"], self.holding(st))
        else:
            self.guard.check({"mode": "none"}, None, st["tcp"], False)  # xyz / none branch: reset, no fix
        if sw is not None:
            self.boost_log.append({"call": len(self.calls), "switch": sw, "from": cmd.get("height")})
            cmd.update(sw)
        evs = super()._execute(cmd)
        if self.last_res is not None and sw is not None:
            self.last_res["loop_switch"] = sw
        above = (branch == "pt" and cmd.get("height") == "above" and self.last_res is not None
                 and self.last_res.get("branch") == "pt")
        self.guard.done(self.last_res.get("goal") if above else None)
        return evs

    def _execute(self, cmd) -> list:
        if cmd.get("mode") == "move" and self.fix_loop:
            return self._execute_move(cmd)
        if cmd.get("mode") == "point" and self.fix_loop:
            st = self.w.status()
            probe = self.resolve(cmd, st)
            sw = self.guard.check(cmd, probe.get("goal"), st["tcp"], self.holding(st)) if self._loop_on else None
            if sw is not None:
                self.boost_log.append({"call": len(self.calls), "switch": sw, "from": cmd.get("height"),
                                       "guard": "above"})
                cmd.update(sw)
            elif self.fix_descend:
                sw = self.dguard.check(cmd, probe, st["tcp"], self.holding(st))
                if sw is not None:
                    self.boost_log.append({"call": len(self.calls), "switch": sw, "from": cmd.get("height"),
                                           "guard": "descend"})
                    cmd.update(sw)
            evs = super()._execute(cmd)
            if self.last_res is not None and sw is not None:
                self.last_res["loop_switch"] = sw
            above = cmd["height"] == "above" and self.last_res is not None
            self.guard.done(self.last_res.get("goal") if above else None)
            return evs
        return super()._execute(cmd)

    def _save(self, res):
        res["boost"] = {"fix_mem": self.fix_mem, "fix_loop": self.fix_loop, "mem_points": self.mem_points,
                        "switches": self.boost_log, "mem_checks": self.mem_log, "rechecks": self.recheck_log,
                        "fix_descend": self.fix_descend, "recheck": self.recheck,
                        "perturb": getattr(self, "perturb_log", None),
                        "n_memory_resolves": sum(1 for c in self.calls if (c.get("resolved") or {}).get("memory")
                                                 or ((c.get("resolved") or {}).get("resolved") or {}).get("memory"))}
        super()._save(res)


PERTURBS = ("tray", "lift", "head")
LIFT_AFTER_M = 0.10  # the disturbance comes once the held object is this far above the table (carrying)
SETTLE_TICKS = 60  # 3 s at 20 Hz, the executor holding its target


def draw_perturb(kind: str, seed: int) -> dict:
    """boost1b disturbances (prereg_boost1b.md §2), deterministic per (kind, seed):
    tray = the place object moved horizontally 3-8 cm in a random direction; lift = lift joint -0.10..-0.20 m;
    head = head pitch +-5 degrees."""
    rng = np.random.default_rng([int(seed), PERTURBS.index(kind), 41])
    if kind == "tray":
        a, m = rng.uniform(0, 2 * np.pi), rng.uniform(0.03, 0.08)
        return {"kind": kind, "dxy": [round(m * np.cos(a), 4), round(m * np.sin(a), 4)], "mag_m": round(m, 4)}
    if kind == "lift":
        return {"kind": kind, "joint": "lift_joint", "delta": round(-rng.uniform(0.10, 0.20), 4)}
    return {"kind": kind, "joint": "head_joint1", "delta": round(float(np.deg2rad(5.0) * rng.choice([-1, 1])), 5)}


def apply_perturb(world, info: dict, p: dict) -> None:
    env = world.env
    if p["kind"] == "tray":
        k = info["place"]
        pos, quat = env.object_pose(k)
        env.write_object_pose(k, [pos[0] + p["dxy"][0], pos[1] + p["dxy"][1], pos[2]], quat)
        return
    rob = env.robot
    idx = rob.joint_names.index(p["joint"])
    tgt = rob.data.joint_pos_target.clone()
    tgt[0, idx] += p["delta"]
    rob.set_joint_position_target(tgt)


class PerturbEpisode(BoostEpisode):
    """BoostEpisode with one disturbance between the grasp and the place: at the first loop check where the robot
    holds the object and the TCP is LIFT_AFTER_M above the table, apply_perturb, then SETTLE_TICKS executor ticks."""

    def __init__(self, *a, perturb: str | None = None, **kw):
        super().__init__(*a, **kw)
        if perturb is not None and perturb not in PERTURBS:
            raise ValueError(perturb)
        self.perturb, self.perturb_log = perturb, None

    def _check(self):
        r = super()._check()
        if r or self.perturb is None or self.perturb_log is not None:
            return r
        st = self.w.status()
        if self.holding(st) and float(st["tcp"][2]) > self.w.table_z + LIFT_AFTER_M:
            p = draw_perturb(self.perturb, self.seed)
            apply_perturb(self.w, self.info, p)
            for _ in range(SETTLE_TICKS):
                self._tick()
            self.perturb_log = dict(p, call=len(self.calls), t=round(self._t(), 2))
            return super()._check()
        return r


CORRUPTS = ("hole", "noise", "light", "occl")
OBJ_R = {"tgt": 0.06, "place": 0.12}
REMEASURE_DXYZ = (-0.03, 0.0, 0.05)  # re-observe: back 3 cm and up 5 cm


class LimitEpisode(PerturbEpisode):
    """user-log 171 (prereg_limits.md). corrupt = (kind, level) applied to every head observation of the episode
    (seeded by the episode seed): hole = object regions (target + place) depth 0 for a fraction `level`; noise =
    zed_mini x `level`; light = lighting level name; occl = grey box over `level` of the target's image box.
    rescue = the D depth rescue (limits.rescue_resolve) in the point resolver, a 'remeasure' target when all fails."""

    def __init__(self, *a, corrupt=None, rescue: bool = False, resolver: str = "v1", **kw):
        super().__init__(*a, **kw)
        if corrupt is not None and corrupt[0] not in CORRUPTS:
            raise ValueError(corrupt)
        if resolver not in ("v1", "v2", "v2g"):
            raise ValueError(resolver)
        self.corrupt, self.rescue, self.resolver = corrupt, rescue, resolver
        self.corrupt_log, self.rescue_log = [], []

    def _corrupt(self, obs):
        from . import limits as LM
        kind, lv = self.corrupt
        cam = obs.cams["head"]
        d = (obs.depth or {}).get("head")
        rgb = obs.rgb["head"]
        st = self.w.status()
        s = int(self.seed)
        if kind in ("hole", "occl") and d is not None:
            masks = {k: LM.object_mask(cam, d, self.w.table_z, st["obj"][self.info[k]][:2], OBJ_R[k])
                     for k in ("tgt", "place")}
        if kind == "hole" and d is not None:
            for k, m in masks.items():
                d = LM.depth_holes(d, m, float(lv), seed=s + (k == "place"))
        elif kind == "noise" and d is not None:
            d = LM.depth_noise(d, rgb, float(cam.fx), float(lv), seed=s * 1000 + len(self.corrupt_log))
        elif kind == "light":
            rgb = LM.lighting(rgb, lv, seed=s)
        elif kind == "occl" and d is not None:
            rgb = LM.occlude(rgb, masks["tgt"], float(lv), seed=s)
        if d is not None:
            obs.depth["head"] = d
        obs.rgb["head"] = rgb
        self.corrupt_log.append(len(self.calls))
        return obs

    def run(self) -> dict:
        from . import limits as LM
        orig, rp0 = self.w.observe, RS.resolve_point

        def observe(*a, **kw):
            return self._corrupt(orig(*a, **kw))
        if self.corrupt is not None:
            self.w.observe = observe
        if self.resolver == "v2":  # every resolver call of this episode (live, memory, rescue) uses v2
            RS.resolve_point = LM.resolve_point_v2
        elif self.resolver == "v2g":  # v2 before the grasp (grasp points), v1 while holding (place targets)
            def _v2g(*a, **kw):
                return (rp0 if self.holding(self.w.status()) else LM.resolve_point_v2)(*a, **kw)
            RS.resolve_point = _v2g
        try:
            return super().run()
        finally:
            self.w.observe, RS.resolve_point = orig, rp0

    def resolve(self, cmd: dict, st: dict) -> dict:
        if not self.rescue or cmd.get("height") == "lift" or cmd.get("point_2d") is None or self.depth is None:
            return super().resolve(cmd, st)
        from . import limits as LM
        mem = self.pmem.render(self.head) if self.pmem.P is not None else None
        r = LM.rescue_resolve(self.head, self.depth, self.w.table_z, cmd["point_2d"], tcp=st["tcp"], memory=mem)
        if r["rescue"] == "none":
            return super().resolve(cmd, st)
        hold = self.holding(st)
        self.rescue_log.append({"call": len(self.calls), "step": r["rescue"], "hole_frac": r["hole_frac"]})
        if r["kind"] == "remeasure":
            g = np.asarray(st["tcp"], float) + np.asarray(REMEASURE_DXYZ)
            return {"kind": "remeasure", "goal": [round(float(v), 4) for v in g], "holding": hold, "rescue": "remeasure"}
        if self.mem_points and not hold:
            self.pmem.capture(self.head, self.depth, st["tcp"], self.plane if self.plane is not None else self.w.table_z)
        goal, notes = RS.target_of(cmd["height"], r, r["plane"], st["tcp"], hold, self.grip_offset)
        return dict(r, goal=[round(float(v), 4) for v in goal], holding=hold, notes=notes,
                    grip_offset=None if self.grip_offset is None else round(self.grip_offset, 4))

    def _save(self, res):
        res["limits"] = {"corrupt": list(self.corrupt) if self.corrupt else None, "rescue": self.rescue,
                         "resolver": self.resolver,
                         "n_corrupted_obs": len(self.corrupt_log), "rescues": self.rescue_log}
        super()._save(res)
