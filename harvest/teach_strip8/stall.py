"""Loop break for the closed-loop runner (docs/stage3/prereg_main35_closed2.md; diagnosis
docs/stage3/results/m35cl_stagecap_diag.md fix 1). Code only, no retraining, the planner's input format unchanged.

The E-M35CL diagnosis: 58 % of the call-cap failures are stall loops (the same command, the same result, ~27 calls).
The boost1 LoopGuard missed them: it compares the raw (pre-clip) 'above' target with the TCP, and a clipped / out-of-
reach target is never within its 15 mm; it also counts consecutive 'above' only, so the ep0.5 above <-> lift 2-cycle
over the tray is never seen. The LoopGuard (intent switch after a reached 'above') is left as it is; this adds:

StallGuard (pure, per call): a call = the command key (mode, height, gripper, EXECUTED target = the resolved target
after the workspace clip) + its outcome (settled TCP, holding, pad gap). A call repeats with period p (1 or 2) when its
key matches call i-p and its outcome did not change against call i-p (TCP moved < MOVE_TOL_M, same holding, pad gap
within GRIP_TOL_M, and the TCP did not get >= PROGRESS_M nearer its target -- genuine convergence is progress).
  K_HINT repeats in a row (3 calls with the same result, or 4 calls of a 2-cycle) -> one adapter sentence appended to
  that call's result in the history (the planner's existing "previous command and result" slot).
  After the hint, a command that repeats the cycle (key of call i-p) is NOT executed: its result line says so.
  N_END more stalled calls after the hint (skipped or executed repeats) -> the episode ends with 'stall' (not the
  call cap). Any call with a changed outcome resets everything (a new stall needs the full count again).

with_loop_break(cls) adds it to an episode class (LimitEpisode in run_closed_l8s); loop_break=False = the class
unchanged (same history, no 'stall' block in the result)."""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from ..astra_motion.executor import clip_box
from ..astra_solo.episode import SAG_MM

K_HINT = 2  # repeats in a row before the hint (1-cycle: 3 calls with the same result; 2-cycle: 4 calls)
N_END = 3  # stalled calls after the hint before the episode ends with 'stall'
KEY_TOL_M = 0.015  # executed targets this close = the same command (= the LoopGuard's tol)
MOVE_TOL_M = 0.010  # settled TCP moved less than this = the same result (diagnosis: 'TCP moved < 10 mm')
GRIP_TOL_M = 0.005
PROGRESS_M = 0.005  # the TCP got this much nearer its target = converging, not stalled

SKIP_EVENT = "stall_skip"


def executed_target(goal, table_z: float):
    """The target the executor really drives to (the safety-box clip of executor.MotionExec.load)."""
    return None if goal is None else clip_box(goal, table_z)[0]


@dataclass
class Call:
    mode: str
    height: str | None
    gripper: str | None
    target: np.ndarray | None  # executed (post-clip) target
    tcp: np.ndarray  # settled TCP after the call
    holding: bool
    grip_w: float
    kind: str = "other"  # reach | blocked | other (for the hint wording)
    extra: str | None = None  # exact key of commands without a target (edit / gripper)
    skipped: bool = False

    @property
    def err(self):
        return None if self.target is None else float(np.linalg.norm(self.tcp - self.target))


def same_cmd(a: Call, b: Call) -> bool:
    if (a.mode, a.height, a.gripper, a.extra) != (b.mode, b.height, b.gripper, b.extra):
        return False
    if a.target is None or b.target is None:
        return a.target is None and b.target is None
    return float(np.linalg.norm(a.target - b.target)) <= KEY_TOL_M


def same_outcome(new: Call, old: Call) -> bool:
    if float(np.linalg.norm(new.tcp - old.tcp)) >= MOVE_TOL_M or new.holding != old.holding:
        return False
    if abs(new.grip_w - old.grip_w) > GRIP_TOL_M:
        return False
    if new.err is not None and old.err is not None and new.err <= old.err - PROGRESS_M:
        return False
    return True


def event_kind(evs: list) -> str:
    """From the executor events of one call: blocked (clipped, timeout, or settled > SAG_MM short) / reach / other."""
    for e in evs:
        if e["event"] in ("clipped", "timeout") or (e["event"] == "settled" and e.get("err_mm", 0) > SAG_MM):
            return "blocked"
    return "reach" if any(e["event"] == "reach" for e in evs) else "other"


class StallGuard:
    def __init__(self, k_hint: int = K_HINT, n_end: int = N_END):
        self.k_hint, self.n_end = k_hint, n_end
        self.calls: list[Call] = []
        self._reset()

    def _reset(self):
        self.period, self.streak, self.hinted, self.after = 0, 0, False, 0

    def _period(self, c: Call) -> int:
        if self.calls and same_cmd(c, self.calls[-1]) and same_outcome(c, self.calls[-1]):
            return 1
        if (len(self.calls) >= 2 and not same_cmd(c, self.calls[-1]) and same_cmd(c, self.calls[-2])
                and same_outcome(c, self.calls[-2])):
            return 2
        return 0

    def _state(self, action):
        return {"action": action, "period": self.period, "streak": self.streak, "after": self.after}

    def observe(self, c: Call) -> dict:
        """An executed call with its outcome -> {action: None | 'hint' | 'still' | 'end', period, streak, after}."""
        p = self._period(c)
        self.calls.append(c)
        if p == 0:
            self._reset()
            return self._state(None)
        if p != self.period:
            self.period, self.streak, self.hinted, self.after = p, 1, False, 0
        else:
            self.streak += 1
        if self.hinted:
            self.after += 1
            return self._state("end" if self.after >= self.n_end else "still")
        if self.streak >= self.k_hint:
            self.hinted = True
            return self._state("hint")
        return self._state(None)

    def would_repeat(self, c: Call) -> bool:
        """After the hint: is this (not yet executed) command the next one of the stalled cycle?"""
        return bool(self.hinted and self.period and len(self.calls) >= self.period
                    and same_cmd(c, self.calls[-self.period]))

    def skip(self, c: Call) -> dict:
        """The command was not executed (would_repeat): nothing moved, the stall goes on."""
        c.skipped = True
        self.calls.append(c)
        self.streak += 1
        self.after += 1
        return self._state("end" if self.after >= self.n_end else "still")

    def n_same(self) -> int:
        return self.streak + self.period

    def hint_text(self) -> str:
        n, last = self.n_same(), self.calls[-1]
        if self.period == 2:
            return (f"NO CHANGE: the last {n} calls alternated between the same two commands and the robot keeps "
                    "returning to the same poses (the task step did not change) -- do the next step, or choose a "
                    "different point or object")
        if last.kind == "blocked":
            return (f"NO CHANGE: {n} calls in a row gave the same result (BLOCKED: the arm cannot get closer to this "
                    "target) -- point at a different spot or object, or choose another step")
        if last.kind == "reach":
            return (f"NO CHANGE: {n} calls in a row gave the same result (the target was reached, but the task step "
                    "did not change) -- do the next step, or choose a different point or object")
        return f"NO CHANGE: {n} calls in a row gave the same result -- choose a different point, object or step"

    def skip_text(self) -> str:
        return (f"not executed: this command already gave the same result {self.n_same() - 1} times and would change "
                "nothing -- choose a different point, object or step")


def hint_line(line: str, text: str) -> str:
    """'<i>: <desc> -> <result>; TCP now ...' with '; <text>' appended to the result."""
    head, sep, tail = line.rpartition("; TCP now")
    return f"{head}; {text}{sep}{tail}" if sep else f"{line}; {text}"


def skip_line(line: str, text: str) -> str:
    """The result of a history line replaced by text."""
    head, sep, tail = line.rpartition("; TCP now")
    if not sep:
        return line
    desc, arrow, _ = head.rpartition(" -> ")
    return f"{desc}{arrow}{text}{sep}{tail}" if arrow else line


def with_loop_break(cls):
    """cls (a PtEpisode subclass, e.g. boost.LimitEpisode) + the loop break, switched by loop_break=(False)."""

    class LoopBreak(cls):
        def __init__(self, *a, loop_break: bool = False, stall_n: int = N_END, **kw):
            super().__init__(*a, **kw)
            self.loop_break = loop_break
            self.sguard = StallGuard(n_end=stall_n)
            self._pend = None
            self.stall_log = {"hints": [], "skips": [], "end_call": None, "calls": []}

        def _key(self, cmd: dict, goal):
            mode = cmd.get("mode")
            tgt = mode in ("point", "move")
            extra = None if tgt else json.dumps({k: v for k, v in cmd.items()}, sort_keys=True, default=str)
            return dict(mode=mode, height=cmd.get("height") if tgt else None, gripper=cmd.get("gripper"),
                        target=executed_target(goal, self.w.table_z) if tgt else None, extra=extra)

        def _probe(self, cmd: dict, st: dict):
            """The target this command would get (without executing it)."""
            if cmd.get("mode") == "point":
                return self.resolve(dict(cmd), st)
            if cmd.get("mode") == "move":
                from ..astra_solo import hybrid as HY
                goal, branch, info = HY.select(dict(cmd), self._h_resolver(st))
                return dict(info, branch=branch, goal=None if goal is None else [round(v, 4) for v in goal])
            return None

        def _execute(self, cmd) -> list:
            if not self.loop_break:
                return super()._execute(cmd)
            st = self.w.status()
            i, ev0 = len(self.history) + 1, len(self.events)
            if self.sguard.hinted:
                probe = self._probe(cmd, st)
                cand = Call(**self._key(cmd, (probe or {}).get("goal")), tcp=np.asarray(st["tcp"], float),
                            holding=self.holding(st), grip_w=float(st["grip_w"]))
                if self.sguard.would_repeat(cand):
                    self.last_res = probe
                    self._pend = {"i": i, "skip": cand}
                    return [{"t": round(float(st["t"]), 3), "event": SKIP_EVENT}]
            evs = super()._execute(cmd)
            goal = (self.last_res or {}).get("goal") if cmd.get("mode") in ("point", "move") else None
            self._pend = {"i": i, "key": self._key(dict(cmd), goal), "ev0": ev0}
            return evs

        def _stall_step(self):
            p, self._pend = self._pend, None
            st = self.w.status()
            if "skip" in p:
                a = self.sguard.skip(p["skip"])
                self.history[-1] = skip_line(self.history[-1], self.sguard.skip_text())
                self.stall_log["skips"].append(p["i"])
            else:
                c = Call(**p["key"], tcp=np.asarray(st["tcp"], float), holding=self.holding(st),
                         grip_w=float(st["grip_w"]), kind=event_kind(self.events[p["ev0"]:]))
                a = self.sguard.observe(c)
                if a["action"] == "hint":
                    self.history[-1] = hint_line(self.history[-1], self.sguard.hint_text())
                    self.stall_log["hints"].append(p["i"])
                elif a["action"] in ("still", "end"):
                    self.history[-1] = hint_line(self.history[-1], "still NO CHANGE")
            self.stall_log["calls"].append(dict(a, call=p["i"], skipped="skip" in p))
            if a["action"] == "end":
                self.stall_log["end_call"] = p["i"]
                return "stall"
            return None

        def _check(self):
            r = super()._check()
            if r or not self.loop_break or self._pend is None or len(self.history) < self._pend["i"]:
                return r
            return self._stall_step()  # the call's history line is written: its settled outcome

        def _save(self, res):
            if self.loop_break:
                res["stall"] = dict(self.stall_log, k_hint=self.sguard.k_hint, n_end=self.sguard.n_end,
                                    tol={"key_m": KEY_TOL_M, "move_m": MOVE_TOL_M, "grip_m": GRIP_TOL_M,
                                         "progress_m": PROGRESS_M})
            super()._save(res)

    LoopBreak.__name__ = LoopBreak.__qualname__ = cls.__name__ + "LB"
    return LoopBreak
