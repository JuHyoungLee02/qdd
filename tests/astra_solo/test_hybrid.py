"""Track H (hybrid, user-approved design of docs/research/rgb_depth_hybrid_survey_2026-09-27.md §4): depth as a second
image (fixed metric 0.25-1.60 m greyscale, near = bright, invalid = 0, half resolution) with a depth tag; one answer
with the PT point + height intent AND the xyz target; runtime selector = PT converter when the depth is valid and the
point resolves to an object or table point, else the model's xyz (branch logged); the depth-off request equals the
R (nd-xyz) request apart from the depth line and the answer form."""
import json

import numpy as np

from harvest.astra_solo import hybrid as HY
from harvest.astra_solo import nd_prompts as NP

A = {"task_progress": {"verified_completed": [], "currently_attempting": "x", "remaining": []},
     "execution_status": "progressing", "evidence": "e", "evidence_view": "head", "confidence": "low"}


def test_encode_depth_fixed_metric_range():
    d = np.array([[0.25, 0.925, 1.60, 2.0], [0.1, np.nan, np.inf, 0.0]] * 2, float)
    g = HY.encode_depth(d, scale=1.0)
    assert g.dtype == np.uint8 and g.shape == d.shape
    assert g[0, 0] == 255 and g[0, 2] == 1 and 125 <= g[0, 1] <= 130  # near bright, far dark, mid ~128
    assert g[0, 3] == 0 and (g[1] == 0).all()  # out of range / invalid -> black
    h = HY.encode_depth(np.full((376, 672), 0.9), scale=0.5)
    assert h.shape == (188, 336)


def test_schema_both_fields():
    mv = {"mode": "move", "point_2d": [500, 600], "height": "grasp", "position_m": [0.4, -0.3, 0.93],
          "gripper": "close"}
    p, e = HY.validate(json.dumps({"assessment": A, "command": mv}))
    assert e == [] and p["command"]["point_2d"] == [500.0, 600.0] and p["command"]["position_m"][2] == 0.93
    only_xyz = dict(mv)
    del only_xyz["point_2d"]
    p, e = HY.validate(json.dumps({"assessment": A, "command": only_xyz}))
    assert e == [] and p["command"]["point_2d"] is None  # depth-off answer may omit the point
    only_pt = dict(mv)
    del only_pt["position_m"]
    p, e = HY.validate(json.dumps({"assessment": A, "command": only_pt}))
    assert e == [] and p["command"]["position_m"] is None
    neither = {"mode": "move", "height": "grasp", "gripper": "close"}
    assert HY.validate(json.dumps({"assessment": A, "command": neither}))[0] is None
    lift = {"mode": "move", "height": "lift", "position_m": [0.4, -0.3, 1.07], "gripper": "keep"}
    assert HY.validate(json.dumps({"assessment": A, "command": lift}))[0] is not None


def test_selector_branches():
    cmd = {"mode": "move", "point_2d": [500, 600], "height": "grasp", "position_m": [0.4, -0.3, 0.93],
           "gripper": "close"}
    goal, br, _ = HY.select(cmd, lambda c: ([0.41, -0.29, 0.925], {"kind": "object"}))
    assert br == "pt" and goal == [0.41, -0.29, 0.925]
    goal, br, _ = HY.select(cmd, None)  # no depth
    assert br == "xyz" and goal == [0.4, -0.3, 0.93]
    goal, br, info = HY.select(cmd, lambda c: (None, {"kind": "none"}))  # point does not resolve
    assert br == "xyz" and info["fallback"] == "unresolved"
    goal, br, _ = HY.select(dict(cmd, position_m=None), None)
    assert br == "none" and goal is None


def test_answer_merge_and_omit():
    xyz = json.dumps({"assessment": A, "command": {"mode": "eef", "position_m": [0.4, -0.3, 0.93], "gripper": "close"},
                      "reason": "r"})
    pt = json.dumps({"assessment": A, "command": {"mode": "point", "point_2d": [500, 600], "height": "grasp",
                                                  "gripper": "close"}, "reason": "r"})
    a = json.loads(HY.h_answer(xyz, pt))
    assert a["command"] == {"mode": "move", "point_2d": [500, 600], "height": "grasp",
                            "position_m": [0.4, -0.3, 0.93], "gripper": "close"}
    assert HY.validate(json.dumps(a))[0] is not None
    b = json.loads(HY.h_answer(xyz, None))  # unverified pixel -> xyz only
    assert "point_2d" not in b["command"] and b["command"]["mode"] == "move"
    c = json.loads(HY.h_answer(xyz, pt, omit_xyz=True))  # depth-less open sample: no xyz (loss masked by omission)
    assert "position_m" not in c["command"]
    stop = json.dumps({"assessment": A, "command": {"mode": "stop"}, "reason": "r"})
    assert json.loads(HY.h_answer(stop, stop))["command"] == {"mode": "stop"}


def test_request_depth_off_equals_r_request():
    body = NP.STATIC.format(x0=0.25, x1=0.65, y0=-0.5, y1=0.1, wc=4.0, head="H", instruction="I", tgt_name="red mug",
                            place_rule="on it", objects="- red mug", tz=0, z0=0, z1=0)
    now = "\nNOW\n- x\n"
    r = body + now + NP.ANSWERS["nd-xyz@v1"]
    off = HY.request(body, now, depth=False)
    on = HY.request(body, now, depth=True)
    assert off.replace("\n" + HY.TAG_OFF, "").replace(HY.HINT + HY.ANSWER, "") == r.replace(NP.ANSWERS["nd-xyz@v1"], "")
    assert HY.TAG_ON in on and HY.TAG_OFF not in on and HY.TAG_OFF in off
    assert '"position_m"' in HY.ANSWER and '"point_2d"' in HY.ANSWER


def test_episode_truth_each_depth_mode(tmp_path):
    """The H truth succeeds with depth (PT branch), with stereo-noise depth, and without depth (xyz branch); the
    branch counts and the fallback rate are recorded; the depth image is sent only when depth is on."""
    from harvest.astra_solo.pt_episode import PtEpisode
    from harvest.astra_solo.pt_truth import HTruth

    from astra_solo.test_pt_episode import PadWorld
    seen = {}
    for mode in ("on", "noisy", "off"):
        w = PadWorld()
        m = HTruth(w)
        ask = m.ask

        def spy(text, images, meta, _ask=ask, _mode=mode):
            seen.setdefault(_mode, []).append((len(images), HY.TAG_ON in text))
            return _ask(text, images, meta)
        m.ask = spy
        ep = PtEpisode(w, m, 3, "mug_tray", str(tmp_path / mode), iface="h", h_depth=mode)
        m.ep = ep
        res = ep.run()
        assert res["success"], (mode, res["end_reason"], res["history"])
        assert res["interface"] == "h" and res["h_depth"] == mode and res["prompt_version"] == HY.VERSION
        if mode == "off":
            assert res["h_branches"]["pt"] == 0 and res["fallback_rate"] == 1.0
            assert all(n == 2 and not tag for n, tag in seen[mode])
        else:
            assert res["h_branches"]["pt"] >= 3 and res["fallback_rate"] < 0.5
            assert all(n == 3 and tag for n, tag in seen[mode])


def test_drop_and_noise_assignment_deterministic():
    ids = [f"std_mug_s{i}_c{j:03d}" for i in range(40) for j in range(10)]
    modes = [HY.train_depth_mode(i) for i in ids]
    assert modes == [HY.train_depth_mode(i) for i in ids]
    n = len(ids)
    off, noisy, clean = modes.count("off") / n, modes.count("noisy") / n, modes.count("clean") / n
    assert 0.42 < off < 0.58 and 0.18 < noisy < 0.32 and 0.18 < clean < 0.32
