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


class BoostEpisode(PtEpisode):
    def __init__(self, *a, fix_mem: bool = False, fix_loop: bool = False, **kw):
        kw.setdefault("iface", "d-min")
        super().__init__(*a, **kw)
        self.fix_mem, self.fix_loop = fix_mem, fix_loop
        self.mem, self.guard = PlaceMemory(), LoopGuard()
        self.boost_log = []

    def resolve(self, cmd: dict, st: dict) -> dict:
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
            sw = self.guard.check(cmd, probe.get("goal"), st["tcp"], self.holding(st))
            if sw is not None:
                self.boost_log.append({"call": len(self.calls), "switch": sw, "from": cmd.get("height")})
                cmd.update(sw)
            evs = super()._execute(cmd)
            if self.last_res is not None and sw is not None:
                self.last_res["loop_switch"] = sw
            above = cmd["height"] == "above" and self.last_res is not None
            self.guard.done(self.last_res.get("goal") if above else None)
            return evs
        return super()._execute(cmd)

    def _save(self, res):
        res["boost"] = {"fix_mem": self.fix_mem, "fix_loop": self.fix_loop, "switches": self.boost_log,
                        "n_memory_resolves": sum(1 for c in self.calls if (c.get("resolved") or {}).get("memory")
                                                 or ((c.get("resolved") or {}).get("resolved") or {}).get("memory"))}
        super()._save(res)
