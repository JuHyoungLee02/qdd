"""No-depth arms of E-PT on the fake world: the truth succeeds through each ND interface; the ND requests carry no
table height, grid or drop line (only the TCP ring); the estimates schema; every request of a state is saved; the
table-height argument leaves the default scene path unchanged."""
import inspect
import json

import numpy as np

from harvest.astra_solo import nd as ND
from harvest.astra_solo import nd_prompts as NP
from harvest.astra_solo.pt_episode import PtEpisode
from harvest.astra_solo.pt_truth import NdTruth

from astra_solo.test_pt_episode import A, PadWorld


def _run(tmp_path, iface, **kw):
    w = PadWorld()
    m = NdTruth(w, iface)
    ep = PtEpisode(w, m, 3, "mug_tray", str(tmp_path / iface), iface=iface, **kw)
    m.ep = ep
    return ep.run(), ep


def test_truth_succeeds_each_nd_iface(tmp_path):
    for iface in ("nd-xyz", "nd-est", "nd-pt"):
        res, ep = _run(tmp_path, iface)
        assert res["success"], (iface, res["end_reason"], res["history"])
        assert res["interface"] == iface and res["prompt_version"] == f"{iface}@v1"
        t = (tmp_path / iface / "calls" / "c000" / "prompt.txt").read_text(encoding="utf-8")
        assert "Table top surface" not in t and "WHITE GRID" not in t and "DROP LINE" not in t
        assert "table height is not given" in t and "White ring" in t
        assert ("estimates" in t) == (iface != "nd-xyz") and ('"top_z": number' in t) == (iface == "nd-pt")
    assert ep.est_table is not None and ep.grip_offset is not None


def test_collection_saves_every_request(tmp_path):
    from harvest.astra_solo.pt_truth import PtTruth
    w = PadWorld()
    m = PtTruth(w)
    ep = PtEpisode(w, m, 3, "mug_tray", str(tmp_path / "c"), save_v2=True, save_nd=True)
    m.ep = ep
    ep.run()
    d = tmp_path / "c" / "calls" / "c000"
    for v in NP.VERSIONS:
        assert (d / f"prompt_{v}.txt").exists()
    assert (d / "img1_head_ring.png").exists() and (d / "prompt_v2.txt").exists()
    a = (d / "prompt_nd-xyz@v1.txt").read_text(encoding="utf-8")
    b = (d / "prompt_v2.txt").read_text(encoding="utf-8")
    assert a.split("NOW\n")[1] == b.split("NOW\n")[1]  # same NOW / history / answer form


def test_nd_schema():
    est = {"table_z": 0.85, "target_base_xy": [0.4, -0.3], "target_height_m": 0.095, "target_width_m": 0.064,
           "place_xy": [0.47, -0.1], "place_top_z": 0.865}
    eef = {"mode": "eef", "position_m": [0.4, -0.3, 1.0], "gripper": "keep"}
    assert ND.validate(json.dumps({"assessment": A, "command": eef}), "nd-xyz@v1")[0] is not None
    assert ND.validate(json.dumps({"assessment": A, "command": eef}), "nd-est@v1")[0] is None
    p, e = ND.validate(json.dumps({"estimates": est, "assessment": A, "command": eef}), "nd-est@v1")
    assert e == [] and p["estimates"]["place_top_z"] == 0.865
    pt = {"mode": "point", "point_2d": [500, 500], "top_z": 0.945, "height": "grasp", "gripper": "close"}
    p, e = ND.validate(json.dumps({"estimates": est, "assessment": A, "command": pt}), "nd-pt@v1")
    assert e == [] and p["command"]["top_z"] == 0.945
    bad = dict(pt)
    del bad["top_z"]
    assert ND.validate(json.dumps({"estimates": est, "assessment": A, "command": bad}), "nd-pt@v1")[0] is None
    lift = {"mode": "point", "height": "lift", "gripper": "keep"}
    assert ND.validate(json.dumps({"estimates": est, "assessment": A, "command": lift}), "nd-pt@v1")[0] is not None


def test_resolve_est_exact_on_top():
    from harvest.astra_motion import geometry as G

    from astra_motion.fakeworld import HEAD
    from harvest.astra_solo import resolve as RS
    top = np.array([0.43, -0.30, 0.945])
    u, v, _ = G.project(HEAD, top)
    cmd = {"point_2d": RS.to_scaled(u, v, HEAD.W, HEAD.H), "top_z": 0.945, "height": "grasp"}
    g, info = ND.resolve_est(HEAD, cmd, 0.85, [0.3, -0.2, 1.1], False, None)
    assert np.hypot(g[0] - 0.43, g[1] + 0.30) < 0.004 and np.isclose(g[2], 0.925)


def test_table_z_default_path_unchanged():
    from harvest.sim import scene
    src = inspect.getsource(scene)
    assert "table_z: float | None = None) -> Env" in src and "table_z=table_z)" in src
    assert "tz = TABLE_TOP_Z if table_z is None else float(table_z)" in src
    assert "self.table_top_z = tz" in src and scene.TABLE_TOP_Z == 0.85
    assert '_LAYOUT.get("table_z", TABLE_TOP_Z)' in src
