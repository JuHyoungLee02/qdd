"""E-SR1c (prereg_sr1c): distance-based authority a (user-log 93; research doc decision_adherence_0p8 §1.5)."""
import math

import numpy as np
import pytest

from harvest.train import sr1c_authority as A
from harvest.train import stageb_data as D


def _aux(dist=None, g=None, p=None, contact=None):
    reg = {}
    if dist is not None:
        reg["g2tgt_dist"] = dist
    if g is not None:
        reg.update(g2tgt_dx=g[0], g2tgt_dy=g[1], g2tgt_dz=g[2])
    if p is not None:
        reg.update(tgt2place_dx=p[0], tgt2place_dy=p[1], tgt2place_dz=p[2])
    cls = {} if contact is None else {"contact_tgt_place": contact}
    return {"reg": reg, "cls": cls}


def test_constants_match_runtime_and_datagen():
    from harvest.config import CFG
    from harvest.datagen.rows import PICK_PHASES
    assert A.NEAR_M == CFG.near_in_m and A.NEAR_OUT_M == CFG.near_out_m
    assert A.PICK_PHASES == PICK_PHASES
    assert A.FAR_M == 0.10
    assert A.AUX_REG == D.AUX_REG and A.AUX_CLS == D.AUX_CLS and A.AUX_REG_SCALE == D.AUX_REG_SCALE
    assert set(A.CONTACT_PHASES) == {"descend", "close", "place_descend", "open"}


def test_authority_ramp_and_contact_phase():
    assert A.authority(0.20, "approach") == 1.0
    assert A.authority(0.10, "carry") == 1.0
    assert A.authority(0.05, "approach") == 0.0
    assert A.authority(0.03, "approach") == 0.0
    assert A.authority(0.075, "approach") == pytest.approx(0.5)
    for ph in ("descend", "close", "place_descend", "open"):
        assert A.authority(0.50, ph) == 0.0  # contact phase: 0 whatever the distance
    assert A.authority(0.50, "carry", contact=True) == 0.0
    assert A.authority(None, "carry") is None


def test_stage_distance_pick_uses_target_and_place_uses_gripper_to_place():
    d, c = A.stage_distance(_aux(dist=0.22), "approach")
    assert d == pytest.approx(0.22) and c is False
    # place stage: gripper -> place = g2tgt (tgt - g) - tgt2place (tgt - place)
    d, c = A.stage_distance(_aux(g=(0.0, 0.0, -0.04), p=(0.0, 0.30, 0.04)), "carry")
    assert d == pytest.approx(math.hypot(0.30, 0.08)) and c is False
    d, c = A.stage_distance(_aux(g=(0.0, 0.0, -0.04), p=(0.0, 0.30, 0.04), contact=1), "carry")
    assert c is True
    assert A.stage_distance(_aux(), "approach") == (None, None)
    assert A.stage_distance(_aux(g=(0, 0, 0)), "carry") == (None, None)


def test_privileged_authority_matches_sr1b_near_snap_definition():
    aux = _aux(dist=0.04, g=(0.0, 0.0, -0.04), p=(0.0, 0.3, 0.0))
    assert A.privileged(aux, "approach") == 0.0
    aux = _aux(dist=0.30, g=(0.0, 0.0, -0.04), p=(0.0, 0.3, 0.0))
    assert A.privileged(aux, "approach") == 1.0


def test_estimated_authority_from_aux_head_outputs():
    reg = np.zeros(len(D.AUX_REG), np.float32)
    cls = np.full(len(D.AUX_CLS), -5.0, np.float32)
    reg[D.AUX_REG.index("g2tgt_dist")] = 0.20 / D.AUX_REG_SCALE
    assert A.estimated(reg, cls, "approach") == 1.0
    reg[D.AUX_REG.index("g2tgt_dist")] = 0.06 / D.AUX_REG_SCALE
    assert A.estimated(reg, cls, "approach") == pytest.approx(0.2)
    # place stage from the predicted offsets; a positive contact logit -> 0
    reg[:] = 0
    reg[D.AUX_REG.index("tgt2place_dy")] = -0.30 / D.AUX_REG_SCALE
    assert A.estimated(reg, cls, "carry") == 1.0
    cls[D.AUX_CLS.index("contact_tgt_place")] = 2.0
    assert A.estimated(reg, cls, "carry") == 0.0
    d = A.estimated_distance(reg, cls, "carry")
    assert d[0] == pytest.approx(0.30, abs=1e-6)


def test_stratum():
    assert A.stratum(1.0) == "far" and A.stratum(0.0) == "near" and A.stratum(0.4) == "band"
    assert A.stratum(None) == "unknown"


def test_runtime_hysteresis_and_rate_limit():
    h = A.Hysteresis(dt=0.33)
    assert h.step(0.20, "approach") == 0.5  # start at 0: increases are rate limited (+0.5 per 0.33 s)
    assert h.step(0.20, "approach") == 1.0
    # entering the near zone: decreases are immediate (the VLA takes over at once)
    assert h.step(0.04, "approach") == 0.0
    # inside the near zone: leaving needs > 6 cm (5.5 cm keeps a = 0)
    assert h.step(0.055, "approach") == 0.0
    # 7 cm: out of the near zone, ramp target (0.07 - 0.05) / 0.05 = 0.4 (within the rate limit)
    assert h.step(0.07, "approach") == pytest.approx(0.4)
    # contact phase -> 0 at once
    assert h.step(0.30, "descend") == 0.0
    assert h.step(None, "approach") == 0.0  # unknown distance: conservative 0
