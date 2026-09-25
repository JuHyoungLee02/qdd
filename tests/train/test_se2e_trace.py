"""E-MA1 (docs/stage3/prereg_ma1.md): head-camera projection, trace5 targets, history overlay, overlay dropout,
G0 selection / statistics / extrinsic correction. Pure functions (numpy + PIL, no torch)."""
import json
import math

import numpy as np
import pytest

from harvest.train import se2e_data as S
from harvest.train import se2e_trace as TR
from harvest.train import stageb_data as D

# the head chain of ffw_bg2_rev4_follower.urdf (ROBOTIS-GIT/ai_worker 897ef34)
HEAD_URDF = """<robot name="t">
<joint name="head_joint1" type="revolute"><parent link="arm_base_link"/><child link="head_link1"/>
  <origin rpy="0 0 0" xyz="0.049483 0 0.102130"/><axis xyz="0 1 0"/></joint>
<joint name="head_joint2" type="revolute"><parent link="head_link1"/><child link="head_link2"/>
  <origin rpy="0 0 0" xyz="0.040 0 0.054"/><axis xyz="0 0 1"/></joint>
<joint name="zed_camera_center_joint" type="fixed"><parent link="zed_camera_link"/><child link="zed_camera_center"/>
  <origin rpy="0 0 0" xyz="0 0 0.01325"/></joint>
<joint name="zed_left_camera_joint" type="fixed"><parent link="zed_camera_center"/><child link="zed_left_camera_frame"/>
  <origin rpy="0 0 0" xyz="0 0.0315 0"/></joint>
<joint name="zed_left_camera_optical_joint" type="fixed">
  <origin rpy="-1.57079632679 0.0 -1.57079632679" xyz="0 0 0"/>
  <parent link="zed_left_camera_frame"/><child link="zed_left_camera_optical_frame"/></joint>
<joint name="zed_joint" type="fixed"><parent link="head_link2"/><child link="zed_camera_link"/>
  <origin rpy="0 0 0" xyz="0.0238122 -0.00651797 -0.0242094"/></joint>
</robot>"""
CAM0 = np.array([0.049483 + 0.040 + 0.0238122, -0.00651797 + 0.0315, 0.102130 + 0.054 - 0.0242094 + 0.01325])


def _cam(q=(0.0, 0.0)):
    return TR.head_camera(TR.load_head_chain(HEAD_URDF), q)


# ------------------------------------------------------------------------------------------ camera
def test_head_camera_at_zero_looks_forward():
    R, t = _cam()
    np.testing.assert_allclose(t, CAM0, atol=1e-9)
    # optical frame: z forward (= base +x), x right (= base -y), y down (= base -z)
    np.testing.assert_allclose(R[:, 2], [1, 0, 0], atol=1e-9)
    np.testing.assert_allclose(R[:, 0], [0, -1, 0], atol=1e-9)
    np.testing.assert_allclose(R[:, 1], [0, 0, -1], atol=1e-9)


def test_head_pitch_turns_the_view_down():
    R, _ = _cam((0.5, 0.0))
    np.testing.assert_allclose(R[:, 2], [math.cos(0.5), 0, -math.sin(0.5)], atol=1e-9)


def test_project_center_and_right_offset():
    cam = _cam()
    K = TR.INTRINSICS
    P = np.array([CAM0 + [1.0, 0, 0], CAM0 + [1.0, -0.1, 0], CAM0 + [1.0, 0, -0.1], CAM0 - [1.0, 0, 0]])
    uv, z = TR.project(cam, P, K)
    np.testing.assert_allclose(uv[0], [K["cx"], K["cy"]], atol=1e-9)
    np.testing.assert_allclose(uv[1], [K["cx"] + 0.1 * K["fx"], K["cy"]], atol=1e-9)  # robot right = image right
    np.testing.assert_allclose(uv[2], [K["cx"], K["cy"] + 0.1 * K["fy"]], atol=1e-9)  # down = image down
    assert z[3] < 0


def test_nominal_intrinsics_and_rb1_head_are_registered_values():
    assert (TR.INTRINSICS["fx"], TR.INTRINSICS["fy"], TR.INTRINSICS["cx"], TR.INTRINSICS["cy"]) == (367.0, 367.0,
                                                                                                    336.0, 188.0)
    assert (TR.INTRINSICS["W"], TR.INTRINSICS["H"]) == (672, 376)
    assert TR.RB1_HEAD == (0.5492, 0.0)


def test_head_q_from_state_or_fixed():
    st19 = np.zeros((3, 19))
    st19[:, 16], st19[:, 17] = 0.55, -0.01
    assert TR.head_q(st19[1], S.FEATURE_NAMES_19) == (0.55, -0.01)
    assert TR.head_q(np.zeros(16), S.FEATURE_NAMES_16) == TR.RB1_HEAD


def test_correction_identity_and_apply():
    cam = _cam()
    P = CAM0 + np.array([[1.0, 0.05, -0.2], [0.8, -0.1, -0.3]])
    uv0, _ = TR.project(cam, P, TR.INTRINSICS)
    uv1, _ = TR.project(cam, P, TR.INTRINSICS, corr=np.zeros(6))
    np.testing.assert_allclose(uv0, uv1, atol=1e-12)
    uv2, _ = TR.project(cam, P, TR.INTRINSICS, corr=np.array([0, 0, 0, 0.01, 0, 0]))  # +1 cm along camera x
    assert (uv2[:, 0] > uv0[:, 0]).all()


def test_fit_correction_recovers_a_known_offset():
    rng = np.random.default_rng(0)
    cams, pts = [], []
    for _ in range(30):
        cams.append(_cam())
        pts.append(CAM0 + np.array([rng.uniform(0.3, 1.2), rng.uniform(-0.3, 0.3), rng.uniform(-0.6, -0.1)]))
    pts = np.array(pts)
    true = np.array([0.02, -0.03, 0.01, 0.01, -0.02, 0.015])
    uv = np.array([TR.project(c, p[None], TR.INTRINSICS, corr=true)[0][0] for c, p in zip(cams, pts)])
    nominal = np.array([TR.project(c, p[None], TR.INTRINSICS)[0][0] for c, p in zip(cams, pts)])
    assert np.linalg.norm(nominal - uv, axis=1).mean() > 10  # the offset matters
    reproj = lambda x: np.array([TR.project(c, p[None], TR.INTRINSICS, corr=x)[0][0]  # noqa: E731
                                 for c, p in zip(cams, pts)])
    fit = TR.fit_correction(cams, pts, uv, TR.INTRINSICS)
    assert np.linalg.norm(reproj(fit) - uv, axis=1).max() < 0.05  # clean references: exact
    obs = uv.copy()
    obs[0] += [80.0, -60.0]  # one reference-point outlier: the robust loss keeps the inliers within ~1 px
    fit = TR.fit_correction(cams, pts, obs, TR.INTRINSICS)
    assert np.linalg.norm(reproj(fit) - uv, axis=1)[1:].max() < 2.0


# ------------------------------------------------------------------------------------------ trace5
def test_gripper_event_end():
    g = np.array([0.1] * 6 + [0.9] * 60)
    assert TR.event_end(g, 0, 10) == 6  # first frame whose closed/open state differs from k's
    assert TR.event_end(g, 6, 10) == 36  # no event -> cap 3 s
    assert TR.event_end(g, 60, 10) == 65  # episode end
    assert TR.event_end(g, 65, 10) == 65


def test_trace5_even_points_and_mask():
    cam = _cam()
    T = 40
    ee = np.stack([CAM0 + [0.8, -0.01 * i, -0.2] for i in range(T)])  # moves to the robot's right
    g = np.array([0.1] * 20 + [0.9] * 20)
    tr = TR.trace5(ee, g, 4, cam, TR.INTRINSICS, fps=10)
    assert tr["end"] == 20 and tr["mask"] == [1, 1, 1, 1, 1]
    uv, _ = TR.project(cam, ee[[4, 8, 12, 16, 20]], TR.INTRINSICS)
    np.testing.assert_allclose(np.reshape(tr["uv"], (5, 2)), uv / [672, 376], atol=1e-9)
    ee2 = ee.copy()
    ee2[8:] = CAM0 + [0.1, -3.0, 0.0]  # far right: out of the image
    tr2 = TR.trace5(ee2, g, 4, cam, TR.INTRINSICS, fps=10)
    assert tr2["mask"] == [1, 0, 0, 0, 0] and tr2["uv"][2:] == [0.0] * 8


def test_trace5_behind_camera_masked():
    cam = _cam()
    ee = np.stack([CAM0 - [0.5, 0, 0]] * 10)
    tr = TR.trace5(ee, np.zeros(10), 0, cam, TR.INTRINSICS, fps=10)
    assert tr["mask"] == [0] * 5


def test_trace_aux_vecs_appends_scaled_trace():
    s = {"aux": {"reg": {}, "cls": {}}, "trace5": {"uv": [0.5, 0.25] * 5, "mask": [1, 0, 1, 1, 0]}}
    r, rm, c, cm = TR.trace_aux_vecs(s)
    n = len(D.AUX_REG)
    assert r.shape == (n + 10,) and rm.shape == (n + 10,)
    assert rm[:n].sum() == 0
    np.testing.assert_allclose(r[n:n + 2], [0.5 / TR.TRACE_SCALE, 0.25 / TR.TRACE_SCALE])
    assert rm[n:].tolist() == [1, 1, 0, 0, 1, 1, 1, 1, 0, 0]
    assert r[n + 2] == 0.0  # masked point: target zeroed
    assert c.shape == (len(D.AUX_CLS),) and cm.sum() == 0


# ------------------------------------------------------------------------------------------ overlay
def test_history_frames_past_only():
    assert TR.history_frames(30) == list(range(10, 31))
    assert TR.history_frames(5) == list(range(0, 6))


def test_render_overlay_draws_past_path_only(tmp_path):
    from PIL import Image
    img = Image.new("RGB", (672, 376), (0, 0, 0))
    uv = np.array([[100.0 + 20 * i, 200.0] for i in range(21)])  # oldest -> newest (current = last)
    z = np.ones(21)
    out = TR.render_overlay(img, uv, z)
    a = np.asarray(out).astype(int)
    assert out.size == (672, 376) and a.shape == (376, 672, 3)
    assert a[200, 110, 0] > 30 and a[200, 110, 1] < a[200, 110, 0]  # old segment: faint red
    assert a[200, 480, 0] > a[200, 110, 0]  # newest segment: stronger
    assert a[200, 504, 0] > 100  # current-point ring (radius 4 around x = 500)
    assert a[100, 300].sum() == 0 and a[200, 600].sum() == 0  # nothing elsewhere / after the current point
    assert np.asarray(img).sum() == 0  # input not modified


def test_render_overlay_breaks_at_points_behind_camera():
    from PIL import Image
    img = Image.new("RGB", (672, 376))
    uv = np.array([[100.0, 100.0], [300.0, 100.0], [500.0, 100.0]])
    out = np.asarray(TR.render_overlay(img, uv, np.array([1.0, -1.0, 1.0]))).astype(int)
    assert out[100, 200].sum() == 0 and out[100, 400].sum() == 0


def _sample(key, head="img/h.jpg"):
    ims = [["head camera:", head], ["right wrist camera (active arm):", "img/w.jpg"]]
    return {"key": key, "context": {"text": "t", "images": ims},
            "items": [{"text": "t q", "images": ims}, {"text": "t q2", "images": ims}],
            "overlay_head": {"on": "ov/" + head, "off": head}}


def test_overlay_dropout_seeded_and_consistent():
    batch = [_sample(f"k{i}") for i in range(2000)]
    for s in batch:
        TR.set_overlay(s, True)
    out = TR.overlay_dropout(batch, step=7, seed=0, p=0.3)
    off = [s["context"]["images"][0][1] == s["overlay_head"]["off"] for s in out]
    assert 0.26 < np.mean(off) < 0.34
    assert [s["context"]["images"][0][1] for s in TR.overlay_dropout(batch, 7, 0, 0.3)] == \
        [s["context"]["images"][0][1] for s in out]
    for s in out:
        assert all(it["images"] == s["context"]["images"] for it in s["items"])
        assert s["context"]["images"][1][1] == "img/w.jpg"
    assert all(s["context"]["images"][0][1].startswith("ov/") for s in batch)  # inputs untouched
    assert TR.overlay_dropout(batch, 7, 0, 0.0) == batch


def test_set_overlay_on_off():
    s = _sample("k")
    TR.set_overlay(s, True)
    assert s["context"]["images"][0][1] == "ov/img/h.jpg" and s["items"][1]["images"][0][1] == "ov/img/h.jpg"
    TR.set_overlay(s, False)
    assert s["context"]["images"][0][1] == "img/h.jpg"


# ------------------------------------------------------------------------------------------ G0
def _g0_rows():
    rows = []
    for kind in ("RB1", "RB2"):
        for ep in range(80):
            for k in (0, 5, 10):
                rows.append({"kind": kind, "seed": ep, "k": k, "arm": "left" if ep % 2 else "right",
                             "bimanual": ep % 7 == 0, "split": "val" if ep < 70 else "train",
                             "images": {"cam_head": f"img/{kind}/{ep}/{k}.jpg"}})
    return rows


def test_g0_select_per_source_arm_distinct_episodes():
    sel = TR.g0_select(_g0_rows(), n_per=30, seed=0)
    assert len(sel) == 120
    for kind in ("RB1", "RB2"):
        for arm in ("left", "right"):
            xs = [r for r in sel if r["kind"] == kind and r["arm"] == arm]
            assert len(xs) == 30 and len({r["seed"] for r in xs}) == 30
    assert all(r["split"] == "val" and not r["bimanual"] for r in sel)
    assert TR.g0_select(_g0_rows(), 30, 0) == sel
    assert TR.g0_select(list(reversed(_g0_rows())), 30, 0) == sel  # input order does not matter


def test_g0_select_fills_from_chosen_episodes_when_short():
    rows = [r for r in _g0_rows() if r["seed"] < 20]
    sel = TR.g0_select(rows, n_per=12, seed=0)
    xs = [r for r in sel if r["kind"] == "RB1" and r["arm"] == "right"]
    assert len(xs) == 12 and len({(r["seed"], r["k"]) for r in xs}) == 12


def test_g0_calibration_half():
    sel = TR.g0_select(_g0_rows(), 30, 0)
    cal = TR.g0_cal_half(sel)
    assert sum(cal) == 60
    for kind in ("RB1", "RB2"):
        for arm in ("left", "right"):
            idx = [i for i, r in enumerate(sel) if r["kind"] == kind and r["arm"] == arm]
            assert [cal[i] for i in idx] == [True] * 15 + [False] * 15


def test_g0_stats_and_rule():
    st = TR.g0_stats([1.0] * 49 + [12.0, 20.0] + [20.0] * 40 + [31.0] * 9)
    assert st["n"] == 100 and st["median"] == pytest.approx(16.0)
    ok = TR.g0_pass({"median": 12.0, "p90": 30.0})
    assert ok and not TR.g0_pass({"median": 12.0001, "p90": 10.0}) and not TR.g0_pass({"median": 1.0, "p90": 30.01})
    st = TR.g0_stats(np.arange(1, 11, dtype=float))
    assert st["median"] == 5.5 and st["p90"] == pytest.approx(9.1)


def test_point_parse_official_format():
    txt = 'Sure. <points coords="1 1 523 412">right gripper</points>'
    assert TR.parse_point(txt, 672, 376) == pytest.approx((523 / 1000 * 672, 412 / 1000 * 376))
    txt2 = '<points coords="1 1 100 200 2 900 900">g</points>'  # several points: the first
    assert TR.parse_point(txt2, 672, 376) == pytest.approx((67.2, 75.2))
    assert TR.parse_point("I cannot see a gripper.", 672, 376) is None


def test_constants_registered():
    assert TR.AUX_VER == "trace5@v1" and TR.OVERLAY_VER == "eetrace@v1"
    assert TR.LAYOUT_OVERLAY == "D27v1+eetrace@v1"
    assert (TR.TRACE_CAP_S, TR.TRACE_SCALE, TR.HIST_STEPS, TR.OVERLAY_DROPOUT) == (3.0, 0.05, 20, 0.3)
    assert (TR.G0_MEDIAN_PX, TR.G0_P90_PX, TR.G0_MIN_VALID) == (12.0, 30.0, 90)
    assert json.loads(json.dumps(TR.OVERLAY_STYLE)) == TR.OVERLAY_STYLE
