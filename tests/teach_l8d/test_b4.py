"""b4 realistic scenes (prereg_l8d change 12): variant drf = look randomization for furniture scenes (HDR dome,
key light type / colour temperature / pose from the train_x pool; no L8 table / floor slab / pool distractors), real
clutter on the work surface of a furniture scene."""
import hashlib
import json

import pytest

from harvest.sim import randomize as R
from harvest.sim.tasks import layout_for
from harvest.teach_l8d import clutter_x as CX


def test_drf_samples_light_and_hdr_only():
    lay = layout_for(36001, "mug_tray", "task")
    m = R.sample_randomization(36001, "drf", lay)
    assert m["variant"] == "drf" and m["pool"] == "train_x" and m["pools_digest"]
    assert m["table_material"] is None and m["floor_material"] is None and m["distractors"] == []
    assert m["hdr"]["file"] and m["light"]["type"] in R.LIGHT_TYPES
    assert m == R.sample_randomization(36001, "drf", lay)
    assert m["hdr"] != R.sample_randomization(36002, "drf", lay)["hdr"] or \
        m["light"] != R.sample_randomization(36002, "drf", lay)["light"]
    assert R.check_train_variant("drf") == "drf" and not R.validate_meta(m)


def test_other_variants_unchanged():
    h = hashlib.sha256()
    for v in ("dr", "drx", "random", "randx"):
        for s in (30001, 31777, 36123):
            h.update(json.dumps(R.sample_randomization(s, v, layout_for(s, "mug_tray", "task")), sort_keys=True)
                     .encode())
    assert h.hexdigest()[:16] == "50422935f3bb841f"  # snapshot before change 12


def test_clutter_on_a_furniture_surface():
    rows = CX.load_real()
    pool = CX.pool_for(rows, "drf|0.000|shelf", n=30)
    surf = {"id": "s1", "top_z": 0.91, "xy_box": [[0.30, 0.70], [-0.55, 0.15]], "covered_above": 1.05}
    ws = ((0.40, 0.52), (-0.40, -0.10))
    lay = {"o3": (0.45, -0.20, 0.0), "o5": (0.48, -0.33, 0.0)}
    fr = {"o3": 0.032, "o5": 0.114}
    for seed in range(36400, 36410):
        out, placed = CX.add_clutter(dict(lay), seed, pool, ws, fr, surface=surf)
        for p in placed:
            r = pool[p["id"]]["footprint_r"]
            assert 0.30 + r <= p["x"] <= 0.70 - r and -0.55 + r <= p["y"] <= 0.15 - r
            assert pool[p["id"]]["height"] + 0.05 <= 1.05 - 0.91 + 1e-9  # fits under the shelf above
    with pytest.raises(ValueError):
        CX.add_clutter(dict(lay), 1, pool, ws, fr, surface={"id": "x"})


def test_drf_rows_allowed_in_train():
    from harvest.teach_l8d import dataset as D
    D.check_row({"seed": 36900, "variant": "drf", "task": "mug_tray"}, "train")


def test_b4_seed_block():
    from harvest.teach_l8d import spec as S
    assert S.check_seed(40000, "train") == 40000 and S.is_train_seed(44999) and not S.is_train_seed(45000)
    assert not S.is_train_seed(39999)
