"""L8-X drawer runner path (prereg_l8x_tasks change 12; pure, fake world)."""
import json
import os

import numpy as np
import pytest

from harvest.astra_motion.geometry import Cam
from harvest.astra_motion.harness import Obs
from harvest.astra_solo import nd_prompts as NP
from harvest.astra_solo import prompts as V2
from harvest.teach_l8d import spec as S
from harvest.teach_l8d import xdrawer as XD
from harvest.teach_l8d import xdrawer_ep as XE
from harvest.teach_l8d import xdrawer_prompt as XP
from harvest.teach_l8d.dataset import load_rows, scene_of, with_lift

W_OPEN = 0.107
R_HEAD = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])  # looking along +x


class FakeWorld:
    """The TCP goes to each commanded point at once; a gripper closed on the grasp point drags the drawer."""
    dt = 0.05

    def __init__(self, target=0.2):
        self.target = target
        self.w_open, self.w_close = W_OPEN, 0.0
        self.quats = {"down": np.array([1.0, 0.0, 0.0, 0.0]), "front": np.array([0.7071, 0.0, 0.7071, 0.0])}

    def reset(self, seed, task):
        lay = XE.layout_of(seed)
        self.h0 = np.array([lay["handle_xy"][0], lay["handle_xy"][1], 0.94])
        self.table_z = 0.94 - 0.15
        self.tcp, self.w, self.q, self.t = np.array([0.34, -0.25, 1.05]), W_OPEN, 0.0, 0.0
        self.grab = None
        words = XP.instruction("Dresser_219_1", 1, 4, seed)
        return {"words": words, "open_target": self.target, "pull_dir": [-1.0, 0.0, 0.0], "piece": "Dresser_219_1",
                "handle": task.split("__")[2], "handle_xyz": self.h0.tolist(), "lift": -0.05, "layout": lay}

    def status(self):
        return {"t": self.t, "tcp": self.tcp.copy(), "grip_w": self.w, "handle": self.h0 + np.array([-self.q, 0, 0]),
                "joint": self.q, "root": np.zeros(3)}

    def step(self, pos, width, quat):
        self.t += self.dt
        h = self.h0 + np.array([-self.q, 0, 0])
        g = h + np.array([-XD.FRONT_GRASP, 0, 0])
        if width < 0.01 and self.w > 0.01 and np.linalg.norm(self.tcp - g) < 0.016:
            self.grab = self.tcp - h  # closing on the bar
        if width > 0.01:
            self.grab = None
        self.w = 0.012 if (width < 0.01 and self.grab is not None) else (0.0 if width < 0.01 else width)
        self.tcp = np.asarray(pos, float)
        if self.grab is not None:
            self.q = max(self.q, float(self.h0[0] + self.grab[0] - self.tcp[0]))

    def observe(self, depth=False):
        cam = Cam("head", 64, 48, 50.0, 50.0, 32.0, 24.0, R_HEAD, np.array([0.0, 0.0, 1.4]))
        wr = Cam("wrist", 32, 24, 30.0, 30.0, 16.0, 12.0, R_HEAD, self.tcp.copy())
        rgb = {"head": np.zeros((48, 64, 3), np.uint8), "wrist": np.zeros((24, 32, 3), np.uint8)}
        return Obs(self.t, rgb, {"head": np.ones((48, 64), np.float32)}, {"head": cam, "wrist": wr}, self.tcp.copy(),
                   self.w)

    def frame(self):
        return {"head": np.zeros((48, 64, 3), np.uint8), "wrist": np.zeros((24, 32, 3), np.uint8)}


TASK = "dr__Dresser_219_1__Dresser_219_1_handle_1_305mm_01"


def test_prompt_version_is_new_and_keeps_the_frame_line():
    assert XP.PROMPT_ID not in (V2.PROMPT_ID, *NP.PROMPT_IDS.values())
    assert '"orient": "down"|"front"' in XP.ANSWER and '"width_m"' in XP.ANSWER
    words = XP.instruction("Dresser_219_1", 1, 4, 34652)
    cam = Cam("head", 64, 48, 50.0, 50.0, 32.0, 24.0, R_HEAD, np.zeros(3))
    txt = XP.static(words, cam, 0.153)
    assert "second top drawer from the left" in txt and "at least 12 cm" in txt
    assert "-0.100" in with_lift(txt, -0.1)  # the dataset's self-lift line finds the robot-frame line
    assert XP.drawer_words(0, 2) == "top left drawer" and XP.drawer_words(0, 1) == "top drawer"


def test_episode_opens_the_drawer_and_writes_the_l8d_layout(tmp_path):
    out = str(tmp_path / "train" / "standard_dr_Dresser_219_1" / f"{TASK}_s34652")
    meta = XE.collect_drawer_episode(FakeWorld(), 34652, TASK, "standard", "train", out, 0.0, style="clean")
    assert meta["success"] and meta["judge"]["stopped"] and meta["prompt_version"] == XP.VERSION
    rows = [json.loads(x) for x in open(os.path.join(out, "labels.jsonl"))]
    steps = [r["step"] for r in rows]
    assert steps[-1] == "done" and set(steps) <= set(XD.STEPS_FRONT_ALL)
    for r in rows:
        c = json.loads(r["answer"])["command"]
        assert c["mode"] != "eef" or c["orient"] == "front"
        d = os.path.join(out, "calls", f"c{r['call']:03d}")
        v2, nd = (open(os.path.join(d, n), encoding="utf-8").read() for n in ("prompt_v2.txt", "prompt_nd-xyz@v1.txt"))
        assert v2 == nd and os.path.exists(os.path.join(d, "img1_head_ring.png"))
    built = load_rows(out, "train")  # the b3d build reads it (train seed / variant guard included)
    assert len(built) == len(rows) and scene_of(out)["n_distractors"] == 0


def test_perturbations_only_on_approach_moves(tmp_path):
    out = str(tmp_path / "e")
    meta = XE.collect_drawer_episode(FakeWorld(), 34653, TASK, "standard", "train", out, 1.0, max_perturb=4)
    rows = [json.loads(x) for x in open(os.path.join(out, "labels.jsonl"))]
    assert 1 <= meta["n_perturb"] <= 4
    assert all(r["step"] in XE.PERTURB_STEPS for r in rows if r["exec_kind"] != "clean")


def test_layout_keeps_the_retreat_inside_the_box():
    for s in range(34652, 34800):
        lay = XE.layout_of(s)
        x, y = lay["handle_xy"]
        assert XE.HANDLE_X[0] <= x <= XE.HANDLE_X[1] and XE.HANDLE_Y[0] <= y <= XE.HANDLE_Y[1]
        assert x - XD.FRONT_GRASP - XD.OPEN_TARGET - XD.FRONT_RETREAT >= 0.25
    assert XE.layout_of(34652) == XE.layout_of(34652)


def test_runner_switch_is_dr_only():
    assert not XE.is_drawer_run([]) and not XE.is_drawer_run([{"task": "mug_tray"}, {"task": "st__a__b"}])
    assert XE.is_drawer_run([{"task": TASK}])
    with pytest.raises(ValueError):
        XE.is_drawer_run([{"task": TASK}, {"task": "mug_tray"}])


def test_bundle_group_drawer_is_separate():
    assert S.bundle_task_ok(TASK, ["drawer"]) and not S.bundle_task_ok(TASK, ["all"])
    for t in ("mug_tray", "mug_stand", "ov_x", "cf_mug_tray"):
        assert not S.bundle_task_ok(t, ["drawer"])
    assert S.bundle_task_ok("mug_tray", ["all"]) and S.bundle_task_ok("cf_mug_tray", ["conf"])
