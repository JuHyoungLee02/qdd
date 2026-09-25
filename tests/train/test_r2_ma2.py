"""E-MA2 (prereg_ma2): pure parts of the command option -- hindsight command, 50 % assignment, evaluation (rotated)
commands, the text line, the head-camera arrow and the sample transform (no torch)."""
import os

import numpy as np
import pytest

from harvest.train import r2_ma2 as M


def test_hindsight_command_is_next_second_displacement_clipped_per_axis():
    tcp = np.zeros((100, 3))
    tcp[:, 0] = np.arange(100) * 0.001        # 3 cm per second
    tcp[:, 1] = -np.arange(100) * 0.004       # -12 cm per second -> clipped to -5 cm
    c = M.hindsight_cmd(tcp, 10)
    assert c == pytest.approx([0.03, -0.05, 0.0])
    # near the end the window stops at the last frame
    assert M.hindsight_cmd(tcp, 90) == pytest.approx([0.009, -0.036, 0.0])


def test_give_is_deterministic_and_about_half():
    ids = [f"standard/mug_tray/P0/ep{s}/k{k}" for s in range(10000, 10040) for k in range(0, 300, 10)]
    g = [M.give(i) for i in ids]
    assert g == [M.give(i) for i in ids]
    assert 0.45 < np.mean(g) < 0.55


def test_eval_command_rotates_xy_and_caps_at_2cm():
    c = np.array([0.04, 0.0, 0.03])
    e0 = M.eval_cmd(c, 0)
    assert e0 == pytest.approx([0.02, 0.0, 0.02])
    e90 = M.eval_cmd(c, 90)
    assert e90 == pytest.approx([0.0, 0.02, 0.02], abs=1e-12)
    e180 = M.eval_cmd(np.array([0.012, 0.005, -0.001]), 180)
    assert e180 == pytest.approx([-0.012, -0.005, -0.001])


def test_command_line_text():
    assert M.cmd_line([0.012, -0.004, 0.0]) == "astra edit: move fingertip dx=+1.2 dy=-0.4 dz=+0.0 cm (robot frame)"


def test_head_projection_puts_the_optical_axis_at_the_principal_point():
    # a point 1 m along the camera X axis (Isaac world convention) projects to (cx, cy)
    p_world = M.HEAD_POS + M.HEAD_R[:, 0] * 1.0
    p_table = p_world - np.array([0, 0, M.TABLE_TOP_Z])
    u, v = M.project_head(p_table[None])[0]
    assert (u, v) == pytest.approx((M.HEAD_K["cx"], M.HEAD_K["cy"]), abs=1e-3)
    # the table-frame +y (robot left) goes to smaller u (image left), +z (up) to smaller v
    u2, v2 = M.project_head((p_table + [0, 0.05, 0])[None])[0]
    u3, v3 = M.project_head((p_table + [0, 0, 0.05])[None])[0]
    assert u2 < u and v3 < v


def test_draw_arrow_marks_pixels_near_the_projected_points():
    from PIL import Image
    im = Image.new("RGB", (672, 376), (0, 0, 0))
    p0 = np.array([0.45, -0.15, 0.10])
    out = M.draw_arrow(im, p0, np.array([0.0, 0.05, 0.0]))
    a = np.asarray(out)
    (u0, v0), (u1, v1) = M.project_head(np.stack([p0, p0 + [0, 0.05, 0]]))
    def near(u, v):
        win = a[int(v) - 1:int(v) + 2, int(u) - 1:int(u) + 2].reshape(-1, 3)
        return any(p.tolist() == list(M.ARROW_RGB) for p in win)
    assert near(u0, v0) and near(u1, v1)
    assert (a.reshape(-1, 3) == M.ARROW_RGB).all(1).sum() > 3 * np.hypot(u1 - u0, v1 - v0)
    assert np.asarray(im).max() == 0  # the input image is not modified


def test_sample_id_from_the_head_image_path():
    p = "/data/harvest/data/ma2/view/dr/bottle_tray/P1/img/ep10613/f0120_cam_head.jpg"
    assert M.sample_id(p) == "dr/bottle_tray/P1/ep10613/k120"
    with pytest.raises(ValueError):
        M.sample_id("/x/img/ep1/f0001_cam_wrist_right.jpg")


def _sample(ctx="t_state: x\nrobot: gripper=open"):
    ims = [["head camera:", "/v/standard/mug_tray/P0/img/ep10001/f0030_cam_head.jpg"],
           ["right wrist camera (active arm):", "/v/standard/mug_tray/P0/img/ep10001/f0030_cam_wrist_right.jpg"]]
    items = [{"question": q, "text": ctx + "\n\nQuestion " + q, "images": ims, "names": ["a"], "target": [t]}
             for q, t in (("dir_xy", "plus_y"), ("dir_z", "down"), ("mag_coarse", "large"))]
    return {"key": "P0_ep10001_k30", "context": {"text": ctx, "images": ims}, "items": items,
            "committed": {"dir_xy": "plus_y", "dir_z": "down", "mag_coarse": "large"}}


def test_with_command_c1_adds_the_line_to_context_and_questions_and_relabels_direction():
    s = _sample()
    c = np.array([0.03, 0.0, 0.02])
    out = M.with_command(s, "c1", c, relabel=True)
    line = M.cmd_line(c)
    assert out["context"]["text"] == s["context"]["text"] + "\n" + line
    for it in out["items"]:
        assert it["text"].startswith(out["context"]["text"] + "\n\nQuestion")
    tg = {it["question"]: it["target"] for it in out["items"]}
    assert tg == {"dir_xy": ["plus_x"], "dir_z": ["up"], "mag_coarse": ["large"]}
    assert out["committed"] == {"dir_xy": "plus_x", "dir_z": "up", "mag_coarse": "large"}
    assert s["items"][0]["target"] == ["plus_y"] and s["committed"]["dir_xy"] == "plus_y"  # input untouched
    assert out["context"]["images"] == s["context"]["images"]


def test_with_command_c2_swaps_the_head_image_only():
    s = _sample()
    out = M.with_command(s, "c2", np.array([0.0, 0.0, 0.0]), arrow_path="/a/k0030_true.jpg", relabel=True)
    assert out["context"]["text"] == s["context"]["text"]
    assert out["context"]["images"][0] == ["head camera:", "/a/k0030_true.jpg"]
    assert out["context"]["images"][1] == s["context"]["images"][1]
    assert all(it["images"] == out["context"]["images"] for it in out["items"])
    tg = {it["question"]: it["target"] for it in out["items"]}
    assert tg["dir_xy"] == ["none_xy"] and tg["dir_z"] == ["none_z"]


def test_with_command_c0_or_no_relabel():
    s = _sample()
    assert M.with_command(s, "c0", np.array([0.03, 0, 0])) is s
    out = M.with_command(s, "c1", np.array([0.03, 0, 0]), relabel=False)
    assert out["committed"] == s["committed"]


def test_with_command_refuses_a_question_text_that_does_not_extend_the_context():
    s = _sample()
    s["items"][0]["text"] = "other"
    with pytest.raises(ValueError):
        M.with_command(s, "c1", np.array([0.03, 0, 0]))


def test_apply_ma2_uses_the_table_give_flags(tmp_path):
    s1, s2 = _sample(), _sample()
    s2["context"]["images"] = [[l, p.replace("f0030", "f0040")] for l, p in s2["context"]["images"]]
    for it in s2["items"]:
        it["images"] = s2["context"]["images"]
    table = {"standard/mug_tray/P0/ep10001/k30": {"cmd": [0.03, 0.0, 0.0], "give": True},
             "standard/mug_tray/P0/ep10001/k40": {"cmd": [0.03, 0.0, 0.0], "give": False}}
    out, st = M.apply_ma2([s1, s2], "c2", table, str(tmp_path))
    assert st == {"n": 2, "given": 1, "missing": 0}
    assert out[0]["context"]["images"][0][1] == os.path.join(str(tmp_path), M.arrow_rel(
        "standard/mug_tray/P0/ep10001/k30", "true"))
    assert out[1] is s2
    with pytest.raises(KeyError):
        M.apply_ma2([s1], "c1", {}, str(tmp_path))
