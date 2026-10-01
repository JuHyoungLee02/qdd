"""L9 v2 variation (spec §12.3): wider light families, outdoor lights for outdoor families, head look up / down for
high / low places, material appearance draw (UV scale, tint), axis record."""
from harvest.l9 import scene9 as S
from harvest.l9 import vary9 as V
from harvest.sim import randomize as R


def test_light_families_v2():
    assert len(V.LIGHT_FAMILIES) >= 20
    for f in V.LIGHT_FAMILIES.values():
        assert set(f.key_types) <= set(R.LIGHT_TYPES) and f.fills[1] <= 2
    assert set(V.OUTDOOR_LIGHTS) < set(V.LIGHT_NAMES) and set(V.INDOOR_LIGHTS) < set(V.LIGHT_NAMES)
    lo = min(f.color_k[0] for f in V.LIGHT_FAMILIES.values())
    hi = max(f.color_k[1] for f in V.LIGHT_FAMILIES.values())
    assert lo <= 2000 and hi >= 7500


def test_light_pick_indoor_outdoor():
    ind = {V.pick_light_family(s, "dining") for s in range(800)}
    out = {V.pick_light_family(s, S.OUTDOOR[0]) for s in range(400)}
    assert ind == set(V.INDOOR_LIGHTS) and out == set(V.OUTDOOR_LIGHTS)


def test_head_look_modes():
    for s in range(100):
        up, dn, st = V.head_pose(s, look="up"), V.head_pose(s, look="down"), V.head_pose(s)
        assert V.LOOK["up"][0] <= up["tilt"] <= V.LOOK["up"][1] and up["look"] == "up"
        assert V.LOOK["down"][0] <= dn["tilt"] <= V.LOOK["down"][1]
        assert st["look"] == "std" and abs(st["pan"]) <= 0.35
    assert V.LOOK["up"][0] >= -0.2317  # ffw_sg2.xml head_joint1 lower limit
    assert V.head_pose(3) == V.head_pose(3, 0, "std")


def test_look_of_episode():
    sc = {"nodes": [{"id": "a", "place_class": "desk"}, {"id": "b", "place_class": "high"},
                    {"id": "c", "place_class": "low"}]}
    assert V.look_of({"objects": {"x": {"node": "a"}}}, sc) == "std"
    assert V.look_of({"objects": {"x": {"node": "a"}}, "dst": {"V": {"node": "b"}}}, sc) == "up"
    assert V.look_of({"objects": {"x": {"node": "c"}}}, sc) == "down"
    assert V.look_of({"objects": {}}, {"nodes": []}) == "std"


def test_material_look():
    seen_s, seen_t = set(), set()
    for i in range(300):
        m = V.material_look(i, 2, "furniture")
        assert V.UV_SCALE[0] <= m["uv"] <= V.UV_SCALE[1] and len(m["tint"]) == 3
        assert all(0.0 < c <= 1.0 for c in m["tint"])
        seen_s.add(round(m["uv"], 1))
        seen_t.add(tuple(m["tint"]))
    assert len(seen_s) > 10 and len(seen_t) > 100
    assert V.material_look(5, 1, "wall") == V.material_look(5, 1, "wall")
