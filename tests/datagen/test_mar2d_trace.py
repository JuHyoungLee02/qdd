"""MolmoAct R2 data (plan 2026-09-26-molmoact-r2-data Task 3): trace labels ending at the release (M1) from the sim
end-effector point, MolmoAct subsampling / 0-255 coordinates, and the R2-safe overlay colour (M5)."""
import importlib.util
import json
import math
import os

import numpy as np
import pytest

from harvest.datagen import trace as TR

W, H = 672, 376


def _mar2_lib():
    p = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "mar2", "mar2_lib.py")
    spec = importlib.util.spec_from_file_location("mar2_lib_ref", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_release_frame_is_last_open_frame():
    ph = ["approach"] * 5 + ["open"] * 3 + ["retreat"] * 4 + ["done"] * 2
    assert TR.release_frame(ph) == 7


def test_release_frame_none_without_retreat():
    assert TR.release_frame(["approach", "descend", "close", "lift", "fail"]) is None
    assert TR.release_frame(["approach", "open", "open"]) is None


def test_subsample_matches_molmoact_reference():
    ref = _mar2_lib()
    rng = np.random.default_rng(0)
    for n in range(0, 40):
        pts = [None if rng.random() < 0.2 else [int(rng.integers(256)), int(rng.integers(256))] for _ in range(n)]
        for fb in (None, [1, 2]):
            assert TR.molmo_subsample(pts, 5, fb) == ref.molmo_subsample(pts, 5, fb)


def test_u255_round_trip_and_reference():
    ref = _mar2_lib()
    for u, v in ((0.5, 0.5), (336.0, 188.0), (671.5, 375.5), (100.2, 300.9)):
        assert TR.to_u255(u, v, W, H) == ref.to_u255(u, v, W, H)
        q = TR.to_u255(u, v, W, H)
        u2, v2 = TR.from_u255(q, W, H)
        assert abs(u2 - u) <= (W - 1) / 255 / 2 + 1e-9 and abs(v2 - v) <= (H - 1) / 255 / 2 + 1e-9


def test_labels_end_at_release_and_none_after():
    uv = np.stack([np.linspace(100, 500, 30), np.linspace(300, 100, 30)], 1)
    lab = TR.labels(uv, 20, W, H)
    assert len(lab) == 30
    assert all(x is None for x in lab[21:])
    end = TR.to_u255(*uv[20], W, H)
    for t in range(21):
        assert lab[t][0] == TR.to_u255(*uv[t], W, H)
        assert lab[t][-1] == end
        assert len(lab[t]) == min(5, 21 - t)
    assert lab[20] == [end]


def test_labels_segments_per_frame_end():
    """Real data: each frame's trace ends at ITS segment end (the next release); None = no label (after the last
    release or an invalid point stream). Points may be missing (pointing failures)."""
    uv = [[10.0 + 10 * i, 20.0] for i in range(12)]
    uv[3] = None  # pointing failure at frame 3
    ends = [4, 4, 4, 4, 4, 9, 9, 9, 9, 9, None, None]
    lab = TR.labels_segments(uv, ends)
    assert lab[10] is None and lab[11] is None
    assert lab[0] == [TR.to_u255(10 + 10 * j, 20) for j in (0, 1, 2, 4)]
    assert lab[3] == [TR.to_u255(50, 20)]  # own point missing -> the future points only (MolmoAct drops None)
    assert lab[4] == [TR.to_u255(50, 20)]
    assert lab[5][0] == TR.to_u255(60, 20) and lab[5][-1] == TR.to_u255(100, 20) and len(lab[5]) == 5
    with pytest.raises(ValueError):
        TR.labels_segments(uv, [2] * 12)  # an end before its frame


def test_labels_drop_points_outside_image():
    uv = np.array([[10.0, 10.0], [-5.0, 10.0], [20.0, 20.0], [30.0, 700.0], [40.0, 40.0]])
    lab = TR.labels(uv, 4, W, H)
    assert lab[0] == [TR.to_u255(10, 10, W, H), TR.to_u255(20, 20, W, H), TR.to_u255(40, 40, W, H)]
    assert lab[1] == [TR.to_u255(20, 20, W, H), TR.to_u255(40, 40, W, H)]  # p1 missing -> fallback not used


def test_project_tcp_matches_perception_geom():
    from harvest.perception.geom import Intr, project
    from harvest.train.r2_ma2 import HEAD_K, HEAD_POS, HEAD_R, TABLE_TOP_Z
    tcp = np.array([[0.40, -0.20, 0.10], [0.45, -0.10, 0.02]])
    uv, d = TR.project_tcp(tcp)
    K = Intr(HEAD_K["fx"], HEAD_K["fy"], HEAD_K["cx"], HEAD_K["cy"], HEAD_K["width"], HEAD_K["height"])
    u, v, dd = project(tcp + [0, 0, TABLE_TOP_Z], K, HEAD_POS, HEAD_R)
    assert np.allclose(uv[:, 0], u) and np.allclose(uv[:, 1], v) and np.allclose(d, dd)


def test_overlay_colour_far_from_every_scene_colour():
    pal = TR.palette()
    assert {"o3", "o5", "o8", "o9", "o10", "o11", "col_cyan", "col_teal", "col_olive"} <= set(pal)
    assert len(pal) >= 21
    assert TR.min_palette_distance(TR.TRACE_RGB)[0] >= 120.0
    assert TR.min_palette_distance((0, 255, 255))[0] < 120.0  # MolmoAct cyan fails here (col_cyan)
    assert TR.min_palette_distance((170, 255, 0))[0] < 120.0  # readiness candidate fails (yellow box o9)


def test_object_colours_match_scene():
    from harvest.sim.scene import OBJ_GEOM
    for k, v in TR.OBJECT_RGB.items():
        assert tuple(OBJ_GEOM[k]["color"]) == v


def test_draw_puts_colour_with_dark_outline():
    img = np.full((H, W, 3), 128, np.uint8)
    out = TR.draw(img, [[20, 128], [235, 128]])
    assert out.shape == img.shape and out is not img and (img == 128).all()
    col = np.all(out == np.array(TR.TRACE_RGB, np.uint8), axis=-1)
    assert col.sum() > 300
    dark = np.all(out < 40, axis=-1)
    assert dark.sum() > 300
    assert np.array_equal(TR.draw(img, [[20, 128]]), img)  # one point: nothing drawn (MolmoAct >= 2 points)


def test_episode_trace_record(tmp_path):
    folder = tmp_path / "standard" / "mug_tray" / "P0"
    folder.mkdir(parents=True)
    n = 40
    tcp = np.stack([np.linspace(0.36, 0.44, n), np.linspace(-0.25, -0.10, n), np.full(n, 0.12)], 1)
    tcp[20:30, :2] = (0.442, -0.101)  # holding still over the place target while opening
    tcp[30:, 2] = np.linspace(0.12, 0.22, 10)  # retreat upwards
    ph = ["approach"] * 20 + ["open"] * 10 + ["retreat"] * 10
    np.savez_compressed(folder / "ep10001.npz", tcp=tcp.astype(np.float32),
                        phase_id=np.array([0] * 20 + [6] * 10 + [7] * 10, np.int8))
    meta = {"seed": 10001, "task": "mug_tray", "variant": "standard", "kind": "P0", "valid_for_training": True,
            "place": "o5", "split": "fit"}
    json.dump(meta, open(folder / "ep10001.meta.json", "w"))
    rec = TR.episode_trace(str(folder), 10001, place_xy=(0.44, -0.10))
    assert rec["k_release"] == 29 and rec["end_rule"] == "release" and rec["phase_at_end"] == "open"
    assert len(rec["trace255"]) == n and all(x is None for x in rec["trace255"][30:])
    assert rec["end_xy_to_place_cm"] < 1.0
    assert rec["ee_source"] == "sim_tcp"
