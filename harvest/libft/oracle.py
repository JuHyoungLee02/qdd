"""E-LIBFT (docs/stage3/prereg_libft.md): turn an official LIBERO training demonstration into our planner's training rows.

The demo is NOT replayed. Keyframes are read from it (gripper close / open times, the end-effector path, which object
moved with the gripper, where it was released), then the E-LIB0b episode class (exactly the evaluation prompt path:
Franka facts, d-min request, head = agentview 512, wrist 256, depth resolver, executor, loop break) runs from the demo's
first sim state with an ORACLE in place of the model: at each call the oracle answers, in the trained answer format, the
next command toward the demo's keyframes (sim truth of the demo + the live robot state; no policy, no teacher model).
Kept for training only when the episode reaches LIBERO success (the validation filter: a command sequence our command
set cannot express -- knob turning, pushing along a curve -- simply fails and is dropped, and that is reported).

Commands produced (all in the trained vocabulary, labels worded like harvest.teach_l8.labels):
  pick-and-place segment (an object moved with the closed gripper and was lifted >= LIFT_M):
      point above the object -> point grasp + close [-> reopen + retry if the close caught nothing]
      -> point lift -> point above the place object (or the table spot) -> point place + open -> edit up 10 cm
  other closed segment (drawer, door, articulated, slide): edits along the demo end-effector path to the grasp
      keyframe, close, edits along the closed path, open, edit up
  open-gripper segment that ends a demo without any close (push): edits along the demo path
Pixels: the object's visible pixels (segmentation of its geoms in the head render) -> their median pixel, 0-1000 scale."""
from __future__ import annotations

import json

import numpy as np

from ..astra_motion.models import Reply
from ..teach_l8.labels import _texts, evidence_of, status_of

LIFT_M = 0.03  # the grasped object rose at least this much: pick-and-place
MOVE_M = 0.02  # an object counts as moved with the gripper
KEY_STEP_M = 0.08  # path keyframes every ~8 cm
EDIT_MAX = 0.10
REACH_M = 0.015
PLACE_NEAR_M = 0.10


def edges(g: np.ndarray):
    """Gripper command +1 close / -1 open -> [(t_close, t_open or None)]."""
    s = np.sign(g)
    out, t_c = [], None
    for t in range(1, len(s)):
        if s[t - 1] <= 0 < s[t]:
            t_c = t
        elif s[t - 1] > 0 >= s[t] and t_c is not None:
            out.append((t_c, t))
            t_c = None
    if t_c is not None:
        out.append((t_c, None))
    return out


def path_keys(P: np.ndarray, step: float = KEY_STEP_M) -> list:
    """Points along a path every ~step metres (chord), always ending at the last point."""
    if len(P) == 0:
        return []
    keys, last = [], P[0]
    for p in P[1:]:
        if np.linalg.norm(p - last) >= step:
            keys.append(p.copy())
            last = p
    if not keys or np.linalg.norm(keys[-1] - P[-1]) > 1e-3:
        keys.append(P[-1].copy())
    return keys


class DemoPlan:
    """Keyframes of one demo, in the robot base frame of a LiberoWorld (positions via the demo's own sim states)."""

    def __init__(self, world, demo):
        sim = world.sim
        acts, states = np.asarray(demo["actions"]), np.asarray(demo["states"])
        names = list(world.rs.obj_body_id.keys())

        def objs_at(t):
            sim.set_state_from_flattened(states[t])
            sim.forward()
            return {n: world.to_base(sim.data.body_xpos[world.rs.obj_body_id[n]]) for n in names}, \
                world.to_base(sim.data.site_xpos[sim.model.site_name2id("gripper0_grip_site")])

        T = len(acts)
        eef = []
        for t in range(T):
            sim.set_state_from_flattened(states[t])
            sim.forward()
            eef.append(world.to_base(sim.data.site_xpos[sim.model.site_name2id("gripper0_grip_site")]))
        eef = np.asarray(eef)
        self.segments = []
        for t_c, t_o in edges(acts[:, 6]):
            t_end = t_o if t_o is not None else T - 1
            o0, _ = objs_at(t_c)
            o1, _ = objs_at(t_end)
            zmax = {n: max(objs_at(t)[0][n][2] for t in range(t_c, t_end + 1, max(1, (t_end - t_c) // 10)))
                    for n in names}
            moved = {n: float(np.linalg.norm(o1[n][:2] - o0[n][:2])) + max(0.0, zmax[n] - o0[n][2]) for n in names}
            obj = max(moved, key=moved.get) if names else None
            lifted = obj is not None and zmax[obj] - o0[obj][2] >= LIFT_M and moved[obj] >= MOVE_M
            if lifted:
                place = None
                for n in names:
                    if n != obj and np.linalg.norm(o1[n][:2] - o1[obj][:2]) < PLACE_NEAR_M and o1[n][2] < o1[obj][2]:
                        if place is None or np.linalg.norm(o1[n][:2] - o1[obj][:2]) < np.linalg.norm(o1[place][:2] - o1[obj][:2]):
                            place = n
                self.segments.append({"kind": "pick", "obj": obj, "place": place, "place_xyz": o1[obj].tolist()})
            else:
                pre = path_keys(eef[: t_c + 1][max(0, t_c - 60):])
                self.segments.append({"kind": "manip", "obj": obj, "approach": [p.tolist() for p in pre],
                                      "path": [p.tolist() for p in path_keys(eef[t_c: t_end + 1])]})
        if not self.segments:
            self.segments.append({"kind": "push", "obj": None, "path": [p.tolist() for p in path_keys(eef)]})
        sim.set_state_from_flattened(states[0])
        sim.forward()


class Oracle:
    """A LocalVLM drop-in (ask(text, images, meta) -> Reply) answering from a DemoPlan and the live state."""
    name = "oracle"

    def __init__(self, world, plan: DemoPlan, names: dict):
        self.w, self.plan, self.names = world, plan, names
        self.ep = None
        self.seg, self.sub, self.ki, self.retries = 0, 0, 0, 0
        self.first, self.last_cmd, self.errors = True, None, 0
        self.rim_goal = None

    # ---------------------------------------------------------------- geometry
    def _pixel(self, name: str):
        """Median visible pixel of an object's geoms in the head render -> [x, y] on the 0-1000 scale (None if hidden)."""
        from ..lib0.world import HEAD_CAM, HEAD_PX
        sim = self.w.sim
        m = sim.model
        bid = self.w.rs.obj_body_id[name]
        bodies = {bid}
        for b in range(m.nbody):  # descendants
            p = b
            while p > 0:
                if p in bodies:
                    bodies.add(b)
                    break
                p = int(m.body_parentid[p])
        geoms = np.array([g for g in range(m.ngeom) if int(m.geom_bodyid[g]) in bodies], int)
        sg = np.asarray(sim.render(width=HEAD_PX, height=HEAD_PX, camera_name=HEAD_CAM, segmentation=True))[::-1]
        mask = (sg[..., 0] == 5) & np.isin(sg[..., 1], geoms)
        if mask.sum() < 4:
            return None
        vv, uu = np.nonzero(mask)
        c = np.array([np.median(uu), np.median(vv)])
        k = int(np.argmin((uu - c[0]) ** 2 + (vv - c[1]) ** 2))
        return [round((uu[k] + 0.5) / HEAD_PX * 1000), round((vv[k] + 0.5) / HEAD_PX * 1000)]

    def _touching(self, name: str) -> bool:
        """Sim truth: a finger geom of the gripper is in contact with a geom of the object (or its sub-bodies)."""
        sim = self.w.sim
        m = sim.model
        bid = self.w.rs.obj_body_id[name]
        geoms = set()
        for g in range(m.ngeom):
            b = int(m.geom_bodyid[g])
            while b > 0:
                if b == bid:
                    geoms.add(g)
                    break
                b = int(m.body_parentid[b])
        fingers = {g for g in range(m.ngeom) if "finger" in (m.geom_id2name(g) or "")}
        for i in range(sim.data.ncon):
            c = sim.data.contact[i]
            if (c.geom1 in geoms and c.geom2 in fingers) or (c.geom2 in geoms and c.geom1 in fingers):
                return True
        return False

    def _rim(self, px):
        """Rim grasp target for a hollow object pointed at px (harvest.lib0.rim on the live head depth), else None."""
        from ..lib0.rim import region_points, rim_of
        if self.ep is None or self.ep.depth is None:
            return None
        P, _plane, _r = region_points(self.ep.head, self.ep.depth, self.w.table_z, px, tcp=self.w.status()["tcp"])
        v = rim_of(P, self.w.status()["tcp"])
        return None if not v["hollow"] else [v["xy"][0], v["xy"][1], v["z"]]

    def _table_pixel(self, xyz):
        from ..astra_motion.geometry import pixel_of
        iu, iv, ins = pixel_of(self.ep.head, np.asarray(xyz, float))
        if not ins:
            return None
        return [round((iu + 0.5) / self.ep.head.W * 1000), round((iv + 0.5) / self.ep.head.H * 1000)]

    # ---------------------------------------------------------------- labels
    def _answer(self, step: str, cmd: dict, tn: str, pn: str, doing: str | None = None) -> str:
        st = self.w.status()
        if step in ("above_target", "descend_close", "reopen", "carry_up", "carry_over", "lower_open", "retreat", "done"):
            d, remaining, done = _texts(step, tn, pn)
        else:
            d, remaining, done = doing, [], []
        last = (self.ep.history[-1] if self.ep and self.ep.history else "")
        status = status_of(step, self.first, last, False)
        ans = {"assessment": {"task_progress": {"verified_completed": done, "currently_attempting": d,
                                                "remaining": remaining},
                              "execution_status": status, "evidence": evidence_of(step, st, tn, last),
                              "evidence_view": "both", "confidence": "high"},
               "command": cmd, "reason": f"Next: {d}."}
        self.first = False
        self.last_cmd = cmd
        return json.dumps(ans)

    def _edit_to(self, goal, gripper="keep"):
        tcp = np.asarray(self.w.status()["tcp"], float)
        d = np.asarray(goal, float) - tcp
        n = float(np.linalg.norm(d))
        if n > EDIT_MAX:
            d = d / n * EDIT_MAX
        return {"mode": "edit", "delta_m": [round(float(v), 3) for v in d], "gripper": gripper}, n <= EDIT_MAX + 1e-6

    # ---------------------------------------------------------------- policy over keyframes
    def next(self) -> str:
        from ..lib0.world import obj_name
        if self.seg >= len(self.plan.segments):
            return self._answer("done", {"mode": "stop"}, "object", "target")
        s = self.plan.segments[self.seg]
        tn = obj_name(s["obj"]) if s.get("obj") else "object"
        pn = obj_name(s["place"]) if s.get("place") else "target spot"
        hold = self._touching(s.get("obj")) if s.get("obj") else self.w.holding()
        if s["kind"] == "pick":
            if self.sub == 0:
                px = self._pixel(s["obj"])
                if px is None:
                    return self._fail()
                self.sub = 1
                return self._answer("above_target", {"mode": "point", "point_2d": px, "height": "above", "gripper": "keep"}, tn, pn)
            if self.sub == 1:
                px = self._pixel(s["obj"])
                if px is None:
                    return self._fail()
                if getattr(self, "rim_goal", None) is None:
                    self.rim_goal = self._rim(px) or False  # computed once per attempt (the arm later hides the rim)
                rim = self.rim_goal or None
                if rim is not None:  # hollow object (bowl, basket): grasp its wall with edits (natural grasp)
                    cmd, final = self._edit_to(rim, "keep")
                    if final:
                        cmd["gripper"] = "close"
                        self.sub = 2
                    return self._answer("rim", cmd, tn, pn, doing=f"lower onto the rim of the {tn} and close on it"
                                        if final else f"move over the rim of the {tn}")
                self.sub = 2
                return self._answer("descend_close", {"mode": "point", "point_2d": px, "height": "grasp", "gripper": "close"}, tn, pn)
            if self.sub == 2:
                if not hold:
                    self.retries += 1
                    if self.retries > 2:
                        return self._fail()
                    self.sub, self.rim_goal = 0, None
                    return self._answer("reopen", {"mode": "gripper", "gripper": "open"}, tn, pn)
                self.sub = 3
                return self._answer("carry_up", {"mode": "point", "point_2d": None, "height": "lift", "gripper": "keep"}, tn, pn)
            if self.sub == 3:
                px = self._pixel(s["place"]) if s["place"] else self._table_pixel(s["place_xyz"])
                if px is None:
                    return self._fail()
                self.sub = 4
                return self._answer("carry_over", {"mode": "point", "point_2d": px, "height": "above", "gripper": "keep"}, tn, pn)
            if self.sub == 4:
                px = self._pixel(s["place"]) if s["place"] else self._table_pixel(s["place_xyz"])
                if px is None:
                    return self._fail()
                self.sub = 5
                return self._answer("lower_open", {"mode": "point", "point_2d": px, "height": "place", "gripper": "open"}, tn, pn)
            self.seg, self.sub, self.retries, self.rim_goal = self.seg + 1, 0, 0, None
            return self._answer("retreat", {"mode": "edit", "delta_m": [0.0, 0.0, 0.1], "gripper": "keep"}, tn, pn)
        # manip / push: edits along keyframes (manip: approach keys -> close -> closed path keys -> open -> up)
        keys = (s.get("approach", []) + [None] + s["path"] + [None]) if s["kind"] == "manip" else s["path"]
        while self.ki < len(keys):
            k = keys[self.ki]
            if k is None:  # gripper toggle
                self.ki += 1
                closing = self.ki <= len(s.get("approach", [])) + 1
                return self._answer("toggle", {"mode": "gripper", "gripper": "close" if closing else "open"}, tn, pn,
                                    doing=f"{'close the gripper on' if closing else 'release'} the {tn}")
            tcp = np.asarray(self.w.status()["tcp"], float)
            if np.linalg.norm(np.asarray(k) - tcp) < REACH_M:
                self.ki += 1
                continue
            cmd, final = self._edit_to(k, "keep")
            if final:
                self.ki += 1
            return self._answer("path", cmd, tn, pn, doing=f"move the gripper along the path with the {tn}")
        self.seg, self.ki = self.seg + 1, 0
        return self._answer("retreat", {"mode": "edit", "delta_m": [0.0, 0.0, 0.1], "gripper": "keep"}, tn, pn)

    def _fail(self):
        self.seg = len(self.plan.segments)
        return self._answer("done", {"mode": "stop"}, "object", "target")

    def ask(self, text, images, meta):
        r = Reply()
        try:
            r.text = self.next()
        except Exception as ex:  # noqa: BLE001
            r.error = f"oracle:{ex!r}"
        r.model_field = "oracle"
        return r
