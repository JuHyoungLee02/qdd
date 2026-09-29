"""Ring on a peg V: pure layout / predicates / pairing (harvest.teach_l8d.xring) and the asset dimensions."""
import numpy as np

from harvest.teach_l8d import xring as XR
from tools.l8x_assets import ring_assets as RA

PEG = {"radius": RA.PEG_R, "height": RA.PEG_H, "top_z": RA.BASE_H + RA.PEG_H, "block_h": RA.BLOCK_H}


def test_ring_dims_and_check():
    for g in RA.GAPS:
        d = RA.ring_dims(g)
        assert not RA.check(d) and abs(d["inner_d"] - 2 * RA.PEG_R - g) < 1e-9 and d["outer_d"] <= 0.09


def test_layout_rails_leave_the_grasp_side_free():
    ring = RA.ring_dims(0.035)
    lay = XR.layout(ring, PEG, 35480)
    for (_, (y0, y1)) in lay["rails"]:
        assert min(abs(y0 - lay["ring_xy"][1]), abs(y1 - lay["ring_xy"][1])) >= 0.02  # pads (+-1 cm) clear
    rx = lay["ring_xy"][0]
    grasp_x = rx + ring["centre_r"]
    assert grasp_x > lay["ring_xy"][0]
    ys = sorted((y0 + y1) / 2 for (_, (y0, y1)) in lay["rails"])
    assert ys[0] < lay["ring_xy"][1] < ys[1]  # the rails carry the ring on both sides
    assert abs(lay["peg_top"] - (XR.STAND_TOP + PEG["top_z"])) < 1e-9


def test_predicates_threaded_and_released():
    ring = RA.ring_dims(0.035)
    lay = XR.layout(ring, PEG, 35480)
    c = np.array([*lay["peg_xy"], XR.STAND_TOP + 0.03])
    gp = c + [ring["centre_r"], 0, 0]
    p = XR.preds(c, c[2] - ring["tube_r"], 5.0, gp, gp + [0, 0, 0.3], 0.107, ring, PEG, lay)
    assert p["on"] and not p["holding"] and p["upright"]
    p = XR.preds(c + [0.04, 0, 0], c[2], 5.0, gp, gp + [0, 0, 0.3], 0.107, ring, PEG, lay)
    assert not p["on"]  # off the peg axis by more than inner radius - peg radius
    p = XR.preds(c, c[2] - ring["tube_r"], 5.0, gp, gp, 0.012, ring, PEG, lay)
    assert p["holding"] and not p["on"]


def test_pairs_use_different_colours():
    rings = {f"r{c}": dict(RA.ring_dims(0.035), colour=c, ok=True) for c in ("red", "black")}
    pegs = {f"p{c}": {"colour": c} for c in ("black", "wooden")}
    for s, (r, p) in XR.pairs(rings, pegs, list(range(35480, 35490))).items():
        assert rings[r]["colour"] != pegs[p]["colour"]
