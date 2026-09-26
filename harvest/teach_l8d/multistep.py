"""L8-X multi-step tasks (prereg_l8d.md change 3; user decision: a SEPARATE prompt version, the old ones unchanged).

A multi-step task is an ordered list of (target, place[, place xy offset]) steps under one instruction. The episode
works on the current step: task info (tgt / place / support heights / offset) is the current step's, so the truth
labels, the behaviour policy and the monitor are the single-step ones; when the current step's success holds (the
monitor's 1 s rule) and it is not the last step, the episode advances to the next step instead of ending. The final
success additionally needs every earlier step to still hold (e.g. the mug still on the tray).

Prompts: the request of every interface is the single-step request with three text substitutions (versions
'<version>+m', PROMPT_ID_M): the success line lists all steps in order, the object list marks each step's object and
place ("the object to move first / second", "where to put it (step k)"), and nothing else changes. Pure except
XEpisode (a PtEpisode subclass; its run() is the parent's)."""
from __future__ import annotations

import hashlib

from ..astra_motion.prompts import OBJ_NAME, place_rule
from ..astra_solo.pt_episode import PtEpisode

ORDINAL = ("first", "second", "third", "fourth")
SUCCESS_M = "Success = every step is done, in this order: {steps}; each object stands upright and is released by the gripper, and all hold together for 1 s. Then answer stop."
STEP_M = "({k}) the {tgt} stands upright {rule}"
ROLE_T = " (the object to move {ord})"
ROLE_P = " (where to put it in step {k})"
ROLE_PS = " (where to put them)"
TEMPLATES_M = {"success": SUCCESS_M, "step": STEP_M, "role_t": ROLE_T, "role_p": ROLE_P, "role_ps": ROLE_PS}
PROMPT_ID_M = hashlib.sha256("\n".join(TEMPLATES_M[k] for k in sorted(TEMPLATES_M)).encode()).hexdigest()[:12]
VERSION_SUFFIX = "+m"


def success_line_single(info: dict) -> str:
    tn = OBJ_NAME[info["tgt"]]
    return (f"Success = the {tn} stands upright {place_rule(info['place'], OBJ_NAME[info['place']])}, released by "
            f"the gripper, for 1 s. Then answer stop.")


def success_line_multi(steps) -> str:
    parts = [STEP_M.format(k=i + 1, tgt=OBJ_NAME[s[0]], rule=place_rule(s[1], OBJ_NAME[s[1]]))
             for i, s in enumerate(steps)]
    return SUCCESS_M.format(steps="; ".join(parts))


def patch_static(text: str, info0: dict, steps) -> str:
    """The single-step static text built for step 1 (info0) -> the multi-step text. Raises if a line to patch is
    missing (the templates changed)."""
    s1 = success_line_single(info0)
    if s1 not in text:
        raise ValueError("single-step success line not found")
    out = text.replace(s1, success_line_multi(steps))
    lines = out.split("\n")
    places = [s[1] for s in steps]
    shared = len(set(places)) == 1
    for i, ln in enumerate(lines):
        if not ln.startswith("- "):
            continue
        name = ln[2:].split(":", 1)[0]
        key = next((k for k, v in OBJ_NAME.items() if v == name), None)
        if key is None:
            continue
        base = ln
        for suf in (" (the object to move)", " (where to put it)", " (obstacle)"):
            if base.endswith(suf):
                base = base[: -len(suf)]
                break
        else:
            continue
        tk = [j for j, s in enumerate(steps) if s[0] == key]
        pk = [j for j, s in enumerate(steps) if s[1] == key]
        if tk:
            lines[i] = base + ROLE_T.format(ord=ORDINAL[tk[0]])
        elif pk:
            lines[i] = base + (ROLE_PS if shared else ROLE_P.format(k=pk[0] + 1))
    return "\n".join(lines)


def step_info(base: dict, steps, k: int, extra: dict | None = None) -> dict:
    s = steps[k]
    out = dict(base, tgt=s[0], place=s[1], step_idx=k, n_steps=len(steps))
    if len(s) > 2 and s[2]:
        out["place_xy_offset"] = list(s[2])
    else:
        out.pop("place_xy_offset", None)
    out.update(extra or {})
    return out


class XEpisode(PtEpisode):
    """PtEpisode for a multi-step task: world.step_info(k) gives step k's task info (support heights included);
    the static request of each interface is patched once (patch_static); _check advances the step."""

    def __init__(self, world, model, seed, task, out_dir=None, steps=(), **kw):
        super().__init__(world, model, seed, task, out_dir, **kw)
        self.steps = list(steps)
        self.k = 0
        self.step_done_t: list = []
        self._mstatics = None

    def _request(self, obs, i, statics):
        if self.steps:
            if self._mstatics is None:
                info0 = self.w.step_info(0)
                self._mstatics = {v: patch_static(t, info0, self.steps) for v, t in statics.items()}
            statics = self._mstatics
        return super()._request(obs, i, statics)

    def _check(self):
        from ..sim.tasks import success_now
        r = super()._check()
        if not self.steps:
            return r
        if self.k < len(self.steps) - 1:
            # an intermediate step is done at its first tick of on / released / upright (no 1 s wait: the next call
            # must already be about the next step, else the truth would answer stop); the final check below still
            # needs every step to hold together
            if r not in (None, "success") or (
                    r is None and not success_now(self.w.status()["pred"], self.info["tgt"], self.info["place"])):
                return r
            self.step_done_t.append(round(self._t(), 3))
            self.k += 1
            self.info.clear()
            self.info.update(self.w.step_info(self.k))
            self.mon.tgt, self.mon.place = self.info["tgt"], self.info["place"]
            self.mon.success, self.mon.t_ok, self.t_success = False, None, None
            self._advance_gripper()
            return None
        if r != "success":
            return r
        pred = self.w.status()["pred"]
        if all(success_now(pred, s[0], s[1]) for s in self.steps[:-1]):
            return r
        self.mon.success, self.mon.t_ok, self.t_success = False, None, None  # an earlier step was undone
        return None

    def _advance_gripper(self):
        """The close width follows the current target (tasks.close_width), like OraclePlanner.w_close at reset."""
        from ..sim.tasks import close_width
        wc = float(close_width(self.info["tgt"]))
        for o in (self.w, getattr(self, "ex", None)):
            if o is not None and hasattr(o, "w_close"):
                o.w_close = wc

    def _save(self, res):
        if self.steps:
            res["steps"] = [list(s[:2]) for s in self.steps]
            res["steps_done"] = self.k + int(bool(res.get("success")))
            res["step_done_t"] = self.step_done_t
            res["prompt_version"] = str(res.get("prompt_version")) + VERSION_SUFFIX
            res["prompt_id_m"] = PROMPT_ID_M
        super()._save(res)
