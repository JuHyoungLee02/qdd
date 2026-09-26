"""Point-then-act episode (astra-solo-pt@v1) on the kinematic fake world (ray-cast depth): the truth model succeeds
through pixels + height intents only; the prompt asks for points, not coordinates; the schema refuses absolute
targets from a model; the v2 request of the same state is saved next to the pt request; the pixel labels resolve to
the objects; the default astra-solo path is untouched."""
import json
import os

import numpy as np

from harvest.astra_solo import pt_prompts as PT
from harvest.astra_solo import pt_schema as PS
from harvest.astra_solo import prompts as V2
from harvest.astra_solo.pt_episode import PtEpisode
from harvest.astra_solo.pt_truth import PtTruth, label_pixel

from astra_motion.fakeworld import FakeWorld, GarbageModel

A = {"task_progress": {"verified_completed": [], "currently_attempting": "x", "remaining": []},
     "execution_status": "progressing", "evidence": "e", "evidence_view": "head", "confidence": "low"}


class PadWorld(FakeWorld):
    """The fake world with a measured pad gap: the pads stop on the held object (6.4 cm) instead of closing fully."""

    def status(self):
        s = super().status()
        if self.held:
            s["grip_w"] = max(s["grip_w"], 0.064)
        return s


def _run(tmp_path, world, **kw):
    m = PtTruth(world)
    ep = PtEpisode(world, m, 3, "mug_tray", str(tmp_path / "ep"), save_v2=True, **kw)
    m.ep = ep
    return ep.run(), ep


def test_truth_succeeds_through_points(tmp_path):
    res, ep = _run(tmp_path, PadWorld())
    assert res["success"] and res["end_reason"] in ("success", "stop")
    assert res["prompt_version"] == PT.VERSION and res["interface"] == "pt"
    assert res["modes"]["point"] >= 4 and "eef" not in res["modes"]
    assert ep.grip_offset is not None and 0.05 < ep.grip_offset < 0.10
    first = [c for c in res["calls"] if c.get("resolved")][0]
    assert first["resolved"]["kind"] == "object" and first["score"]["xy_err_mm"] < 8
    d = tmp_path / "ep" / "calls" / "c000"
    txt = (d / "prompt.txt").read_text(encoding="utf-8")
    assert "POINT, THEN ACT" in txt and "position_m" not in txt and '"mode": "point"' in txt
    v2 = (d / "prompt_v2.txt").read_text(encoding="utf-8")
    assert v2.startswith(txt[:60]) and "position_m" in v2 and "POINT, THEN ACT" not in v2
    assert np.load(d / "head_depth.npz")["depth"].shape == (376, 672)
    assert set(json.load(open(d / "cams.json"))) == {"head", "wrist", "wrist_left"}


def test_garbage_is_schema_end(tmp_path):
    w = FakeWorld()
    ep = PtEpisode(w, GarbageModel(), 1, "mug_tray", None)
    res = ep.run()
    assert res["end_reason"] == "schema" and not res["success"]


def test_schema():
    ok = {"assessment": A, "command": {"mode": "point", "point_2d": [500, 600], "height": "grasp", "gripper": "close"}}
    p, e = PS.validate(json.dumps(ok))
    assert e == [] and p["command"]["point_2d"] == [500.0, 600.0]
    lift = {"assessment": A, "command": {"mode": "point", "height": "lift"}}
    p, e = PS.validate(json.dumps(lift))
    assert e == [] and p["command"]["point_2d"] is None and p["command"]["gripper_defaulted"]
    for bad in ({"mode": "point", "point_2d": [500, 1200], "height": "above"},
                {"mode": "point", "point_2d": [500, 600], "height": "top"},
                {"mode": "point", "height": "above"},
                {"mode": "eef", "position_m": [0.4, -0.3, 1.0], "gripper": "keep"}):
        assert PS.validate(json.dumps({"assessment": A, "command": bad}))[0] is None, bad
    eef = {"assessment": A, "command": {"mode": "eef", "position_m": [0.4, -0.3, 1.0], "gripper": "keep"}}
    assert PS.validate(json.dumps(eef), allow_eef=True)[0]["command"]["mode"] == "eef"
    ed = {"assessment": A, "command": {"mode": "edit", "delta_m": [0, 0, 0.3], "gripper": "keep"}}
    assert PS.validate(json.dumps(ed))[0]["command"]["scaled"]


def test_label_pixel_resolves_to_object():
    w = FakeWorld()
    w.reset(3, "mug_tray")
    obs = w.observe(depth=True)
    st = w.status()
    for key in ("o3", "o5"):
        pt, info = label_pixel(obs.cams["head"], obs.depth["head"], w.table_z, st["obj"][key], key)
        assert pt is not None and info["xy_err_mm"] <= 12, (key, info)


def test_px_variant_and_ids():
    t = PT.STATIC + PT.ANSWER
    p = PT.px_variant(t, 672, 376)
    assert "0 (left edge) to 671" in p and "pixels of image 1" in p and "0-1000" not in p
    assert PT.PROMPT_ID != V2.PROMPT_ID and V2.VERSION == "astra-solo@v2"


def test_px_coords_scaled_back(tmp_path):
    class PxTruth(PtTruth):
        def ask(self, text, images, meta):
            r = super().ask(text, images, meta)
            d = json.loads(r.text)
            c = d["command"]
            if c.get("point_2d"):
                c["point_2d"] = [c["point_2d"][0] / 1000 * 672, c["point_2d"][1] / 1000 * 376]
            r.text = json.dumps(d)
            return r
    w = PadWorld()
    m = PxTruth(w)
    ep = PtEpisode(w, m, 3, "mug_tray", None, coords="px")
    m.ep = ep
    res = ep.run()
    assert res["success"] and res["prompt_version"].endswith("+px")


def test_default_world_path_unchanged():
    import inspect

    from harvest.astra_solo import episode, world
    src = inspect.getsource(world.SoloWorld.__init__)
    assert "depth=self.depth" in src and "depth: bool = False" in src
    assert "obs = super().observe()" in inspect.getsource(world.SoloWorld.observe)
    assert "pt_schema" not in inspect.getsource(episode) and "resolve" not in inspect.getsource(episode)
    assert os.path.basename(episode.__file__) == "episode.py"
