"""build9 external-view rows (ext9): paired rows of the same call, excluded by default."""
import json
import os

import numpy as np
import pytest
from PIL import Image

from harvest.l9 import build9 as B9
from harvest.l9 import ext9 as E
from harvest.l9 import tp9 as TP

FX = os.path.join(os.path.dirname(__file__), "fixtures")
P3 = np.array([0.50, -0.10, 0.80])


def _head():
    R = E.look_at(np.array([0.05, 0.0, 1.40]), np.array([0.5, 0.0, 0.8]))
    K = E.K_of(85.0)
    return {"name": "head", "W": E.W, "H": E.H, "fx": K[0, 0], "fy": K[1, 1], "cx": K[0, 2], "cy": K[1, 2],
            "R": E.optical(R).tolist(), "t": [0.05, 0.0, 1.40]}


def _plane_depth(rec, z_plane=0.8):
    Ro, t = np.asarray(rec["R"], float), np.asarray(rec["t"], float)
    u, v = np.meshgrid(np.arange(E.W) + 0.5, np.arange(E.H) + 0.5)
    rays = np.stack([(u - rec["cx"]) / rec["fx"], (v - rec["cy"]) / rec["fy"], np.ones_like(u)], -1) @ Ro.T
    s = (z_plane - t[2]) / rays[..., 2]
    return np.where(s > 0, s, np.inf).astype(np.float32)


def _pt(rec, p):
    u, v, _ = E.project(np.asarray(rec["R"]) @ E.M_OPT.T, np.asarray(rec["t"]),
                        np.array([[rec["fx"], 0, rec["cx"]], [0, rec["fy"], rec["cy"]], [0, 0, 1.0]]), p)
    return [int(round(u / E.W * 1000)), int(round(v / E.H * 1000))]


def _episode(root, ext=True, hide=False):
    ep = os.path.join(root, "train", "dining", "d_s1234567_right")
    c = os.path.join(ep, "calls", "c000")
    os.makedirs(c)
    head = _head()
    cams = {"head": head, "wrist": dict(head, name="wrist")}
    ctx = E.Ctx(look_ws=P3, robot_pts=[np.array([0.05, 0.0, 1.4]), np.array([0.34, -0.25, 1.03])], ws_pts=[P3])
    rec = E.record("ext0", E.draw(4, 0, ctx))
    if ext:
        cams["external0"] = dict(rec, pair="d_s1234567_right/c000")
        ed = _plane_depth(rec)
        if hide:
            q = _pt(rec, P3)
            u, v = int(q[0] / 1000 * E.W), int(q[1] / 1000 * E.H)
            ed[v - 4:v + 5, u - 4:u + 5] = 0.3
        np.savez_compressed(os.path.join(c, "external0_depth.npz"), depth_mm=E.depth_to_mm(ed))
        Image.fromarray(np.full((E.H, E.W, 3), 90, np.uint8)).save(os.path.join(c, "img1_external0.png"))
    json.dump(cams, open(os.path.join(c, "cams.json"), "w"))
    np.savez_compressed(os.path.join(c, "head_depth.npz"), depth=_plane_depth(head))
    for f in ("img1_head_ring.png", "img2_right_wrist_camera.png"):
        Image.fromarray(np.zeros((E.H, E.W, 3), np.uint8)).save(os.path.join(c, f))
    open(os.path.join(c, "prompt_v2.txt"), "w", encoding="utf-8").write(
        open(os.path.join(FX, "l9_v2_1.txt"), encoding="utf-8").read())
    cmd = {"mode": "point", "point_2d": _pt(head, P3), "height": "grasp", "gripper": "close"}
    a = {"assessment": {}, "command": cmd, "reason": "x"}
    row = {"seed": 1234567, "call": 0, "drop": None, "task": "l9_task", "variant": "drf", "step": "descend_close",
           "prev_kind": "clean", "tgt": "o1", "place": "o2", "hand": "right",
           "gt": {"tgt": P3.tolist(), "place": [0.4, 0.1, 0.8], "tcp": [0.45, -0.1, 0.95], "others": {}},
           "answer": json.dumps({"assessment": {}, "command": {"mode": "eef"}}), "pt_answer": json.dumps(a)}
    open(os.path.join(ep, "labels.jsonl"), "w").write(json.dumps(row) + "\n")
    meta = {"robot": "ffw_sg2", "arm": "right", "head_cam": {"mode": "std"}}
    if ext:
        meta["external_cams"] = [{"name": "ext0"}]
    json.dump(meta, open(os.path.join(ep, "meta.json"), "w"))
    return ep, rec


def test_external_rows_only_with_the_flag(tmp_path):
    ep, rec = _episode(str(tmp_path / "src"))
    rng = np.random.default_rng(0)
    off, _, c_off = B9.episode_rows(ep, str(tmp_path / "o1"), "l9train", False, rng)
    on, _, c_on = B9.episode_rows(ep, str(tmp_path / "o2"), "l9train", False, rng, external=True)
    assert len(off) == 1 and "view" not in off[0] and "external_rows" not in c_off
    head = [r for r in on if r.get("view") != "external"]
    ext = [r for r in on if r.get("view") == "external"]
    assert len(head) == 1 and len(ext) == 1 and c_on["external_rows"] == 1
    assert {k: v for k, v in head[0].items() if k != "prompt_path"} == {k: v for k, v in off[0].items()
                                                                          if k != "prompt_path"}
    x = ext[0]
    assert x["pair_of"] == head[0]["id"] and x["pair_id"] == "d_s1234567_right/c000" and x["id"].endswith("_ext0")
    assert x["camera"].startswith("camera: external,") and x["camera"] == E.line(rec, "l9/ffw_sg2")
    text = open(x["prompt_path"], encoding="utf-8").read()
    assert "- " + x["camera"] in text and "- Image 1: external camera, fixed in the room" in text
    assert "head camera" not in text
    q = json.loads(x["answer"])["command"]["point_2d"]
    exp = _pt(rec, P3)
    assert abs(q[0] - exp[0]) <= 3 and abs(q[1] - exp[1]) <= 3
    assert json.loads(x["answer"])["command"]["hand"] == "right"
    assert os.path.exists(x["images"][0]) and x["images"][1] == head[0]["images"][1]
    chk = B9.check_rows(on, camera_line=False)
    assert chk["n_errors"] == 0, chk


def test_hidden_point_drops_the_external_row(tmp_path):
    ep, _ = _episode(str(tmp_path / "src"), hide=True)
    on, _, c = B9.episode_rows(ep, str(tmp_path / "o"), "l9train", False, np.random.default_rng(0), external=True)
    assert [r.get("view") for r in on] == [None] and c["external_hidden"] == 1


def test_unpaired_episode_unchanged_with_the_flag(tmp_path):
    ep, _ = _episode(str(tmp_path / "src"), ext=False)
    on, _, c = B9.episode_rows(ep, str(tmp_path / "o"), "l9train", False, np.random.default_rng(0), external=True)
    assert len(on) == 1 and "external_rows" not in c


def test_check_rows_catches_a_head_line_on_an_external_row(tmp_path):
    ep, _ = _episode(str(tmp_path / "src"))
    on, _, _ = B9.episode_rows(ep, str(tmp_path / "o"), "l9train", False, np.random.default_rng(0), external=True)
    x = [r for r in on if r.get("view") == "external"][0]
    bad = B9.check_rows([dict(x, camera="camera: head, x")])
    assert bad["n_errors"] == 1


@pytest.mark.parametrize("flag", [False, True])
def test_build_counts(tmp_path, flag):
    ep, _ = _episode(str(tmp_path / "src"))
    c = B9.build([ep], str(tmp_path / "out"), "l9train", "x", train=False, external=flag)
    # user 10-02: the ego shard never holds third-person rows; they go to their own shard only with the switch on
    assert c["control_rows"] == 1 and c["third_person_rows"] == (1 if flag else 0)
    ego = [json.loads(x) for x in open(c["path"])]
    assert not [x for x in ego if x.get("view") == "external"]
    tp = str(tmp_path / "out" / "x_third_person.jsonl")
    assert os.path.exists(tp) is flag
    if flag:
        assert len(open(tp).readlines()) == len(TP.index(str(tmp_path / "src")))
    assert ("views" in c) is flag


def test_migrate_moves_external_views_and_build_reads_them(tmp_path):
    ep, _ = _episode(str(tmp_path / "src"))
    c0 = os.path.join(ep, "calls", "c000")
    before, _, _ = B9.episode_rows(ep, str(tmp_path / "o1"), "l9train", False, np.random.default_rng(0), external=True)
    assert TP.migrate(str(tmp_path / "src")) == {"calls": 1, "views": 1}
    t = TP.tp_dir(c0)
    assert t == str(tmp_path / "third_person" / "train" / "dining" / "d_s1234567_right" / "calls" / "c000")
    assert os.path.exists(os.path.join(t, "img1_external0.png")) and os.path.exists(os.path.join(t, "external0_depth.npz"))
    assert not [f for f in os.listdir(c0) if "external" in f]
    assert not [k for k in json.load(open(os.path.join(c0, "cams.json"))) if k.startswith("external")]
    idx = TP.index(str(tmp_path / "src"))
    assert len(idx) == 1 and idx[0]["legacy"] is False and idx[0]["camera"] == "external0"
    after, _, _ = B9.episode_rows(ep, str(tmp_path / "o2"), "l9train", False, np.random.default_rng(0), external=True)
    assert [x["answer"] for x in after] == [x["answer"] for x in before]
    assert TP.migrate(str(tmp_path / "src")) == {"calls": 0, "views": 0}  # idempotent


def _set_rot(ep, rot_entry):
    c = os.path.join(ep, "calls", "c000")
    cams = json.load(open(os.path.join(c, "cams.json")))
    if rot_entry is not None:
        cams["external0"]["grasp_rot"] = rot_entry
    json.dump(cams, open(os.path.join(c, "cams.json"), "w"))
    rows = [json.loads(x) for x in open(os.path.join(ep, "labels.jsonl"))]
    for r in rows:
        a = json.loads(r["pt_answer"])
        a["command"].update(approach="side", rot=3)
        r["pt_answer"] = json.dumps(a)
    open(os.path.join(ep, "labels.jsonl"), "w").write("".join(json.dumps(r) + "\n" for r in rows))


def test_v2_rot_is_the_external_image_angle(tmp_path):
    ep, _ = _episode(str(tmp_path / "src"))
    _set_rot(ep, {"rot_bin_img": 9, "rot_deg_img": 140.0})
    on, _, c = B9.episode_rows(ep, str(tmp_path / "o"), "l9train", False, np.random.default_rng(0), external=True)
    h = [r for r in on if r.get("view") != "external"][0]
    x = [r for r in on if r.get("view") == "external"][0]
    assert json.loads(h["answer"])["command"]["rot"] == 3
    cmd = json.loads(x["answer"])["command"]
    assert cmd["rot"] == 9 and cmd["approach"] == "side"


def test_v2_rot_without_external_angle_drops_the_row(tmp_path):
    ep, _ = _episode(str(tmp_path / "src"))
    _set_rot(ep, None)
    on, _, c = B9.episode_rows(ep, str(tmp_path / "o"), "l9train", False, np.random.default_rng(0), external=True)
    assert [r.get("view") for r in on] == [None] and c["external_no_rot"] == 1


def test_grasp_rot_matches_projection():
    rec = E.record("ext0", E.draw(4, 0, E.Ctx(look_ws=P3, robot_pts=[np.array([0.05, 0.0, 1.4])], ws_pts=[P3])))
    c1, c2 = P3 + np.array([0.0, -0.03, 0.0]), P3 + np.array([0.0, 0.03, 0.0])
    g = E.grasp_rot(rec, c1, c2)
    a, b = np.array(_pt(rec, c1), float), np.array(_pt(rec, c2), float)
    d = (b - a) * np.array([E.W, E.H]) / 1000.0
    deg = np.degrees(np.arctan2(d[1], d[0])) % 180.0
    assert abs(((g["rot_deg_img"] - deg) + 90) % 180 - 90) < 3.0 and g["rot_bin_img"] == int(g["rot_deg_img"] // 15) % 12


def test_tp_write_keeps_ego_call_clean(tmp_path):
    c = tmp_path / "run" / "collect" / "train" / "dining" / "ep_s1_right" / "calls" / "c003"
    os.makedirs(c)
    t = TP.write(str(c), 0, b"png", lambda p: np.savez_compressed(p, depth_mm=np.zeros((2, 2), np.uint16)),
                 {"R": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "t": [0, 0, 1], "pair": "ep_s1_right/c003"})
    assert t == str(tmp_path / "run" / "third_person" / "train" / "dining" / "ep_s1_right" / "calls" / "c003")
    assert os.listdir(c) == []
    d, cams = TP.external_cams(str(c))
    assert d == t and list(cams) == ["external0"] and os.path.exists(os.path.join(t, "external0_depth.npz"))


@pytest.mark.parametrize("on", [False, True])
def test_slot_build_schema_and_third_person_switch(tmp_path, on):
    from harvest.l9 import views9 as V
    ep, _ = _episode(str(tmp_path / "src"))
    TP.migrate(str(tmp_path / "src"))
    c = B9.build([ep], str(tmp_path / "out"), "l9train", "x", train=False, slots=True, third_person=on)
    ego = [json.loads(x) for x in open(c["path"])]
    ctrl = [x for x in ego if x.get("kind", "control") == "control" and x.get("image_views")]
    assert ctrl and c["rows_without_head"] == 0
    for x in ctrl:
        V.parse_slots(open(x["prompt_path"], encoding="utf-8").read())
        assert "third_person" not in x["image_views"] and json.loads(x["answer"])["command"]["arm"] == "right"
    assert c["third_person_rows"] == (len(TP.index(str(tmp_path / "src"))) if on else 0)
    if on:
        tp = [json.loads(x) for x in open(str(tmp_path / "out" / "x_third_person.jsonl"))]
        assert tp[0]["image_views"][-1] == "third_person" and tp[0]["images"][-1].endswith("img1_external0.png")
