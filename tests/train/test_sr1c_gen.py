"""E-SR1c (prereg_sr1c): branch planning of one far snapshot (tools/sr1c/gen_branches.plan_snapshot)."""
import importlib.util
import os

import numpy as np

from harvest.train import sr1c_branch as B
from harvest.train.se2e_data import load_arm_chain

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("gen_branches", os.path.join(ROOT, "tools", "sr1c", "gen_branches.py"))
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
from .test_sr1c_branch import Q0, URDF  # noqa: E402


def _row(phase="approach"):
    a = [list(Q0) + [0.107]] * 15
    return {"seed": 10001, "kind": "P0", "k": 30, "hz": 30, "H": 15, "arm": "right", "skill_id": "pick",
            "phase_id": phase, "proprio": {"q": list(Q0), "qd": [0.0] * 7, "tau": [0.0] * 7, "grip": [0.107, 0.0]},
            "action_exec": a, "action_script": a, "valid": [1] * 15, "task": "mug_tray", "variant": "dr",
            "aux": {"reg": {"g2tgt_dx": 0.0, "g2tgt_dy": 0.3, "g2tgt_dz": -0.1, "g2tgt_dist": 0.316,
                            "tgt2place_dx": 0.0, "tgt2place_dy": -0.2, "tgt2place_dz": 0.04}, "cls": {}}}


def test_free_space_snapshot_gets_k_distinct_branches_following_the_forced_direction():
    ch, lim = load_arm_chain(URDF, "right"), B.joint_limits(URDF, "right")
    out = G.plan_snapshot(ch, lim, _row(), "plus_y", np.array([0.4, -0.3, 0.30]), {}, None,
                          np.random.default_rng(G.snap_seed("dr", "mug_tray", "P0", 10001, 30)))
    assert len(out) == G.K
    assert len({f["dir_xy"] for f, _, _ in out}) == G.K and all(f["dir_xy"] != "plus_y" for f, _, _ in out)
    for f, br, reason in out:
        assert reason is None and br["committed"] == f
        p, _ = B.fk_pose(ch, np.asarray(br["action_exec"])[:, :7])
        d = p[-1] - p[0]
        u = B.direction(f["dir_xy"], f["dir_z"])
        np.testing.assert_allclose(d, B.MAG_M[f["mag_coarse"]] * u, atol=2e-3)


def test_obstacle_below_and_near_end_reject():
    ch, lim = load_arm_chain(URDF, "right"), B.joint_limits(URDF, "right")
    tcp = np.array([0.4, -0.3, 0.12])
    box = {"o8": {"center": np.array([0.4, -0.3, 0.05]), "half": np.array([0.08, 0.08, 0.05])}}
    out = G.plan_snapshot(ch, lim, _row(), "plus_y", tcp, box, None, np.random.default_rng(0))
    assert all(r in ("object", "ik") for _, _, r in out) and any(r == "object" for _, _, r in out)  # the gripper already overlaps the (big) box at the start
    row = _row()
    row["aux"]["reg"].update(g2tgt_dx=0.0, g2tgt_dy=0.0, g2tgt_dz=-0.06, g2tgt_dist=0.06)
    out = G.plan_snapshot(ch, lim, row, "plus_y", np.array([0.4, -0.3, 0.30]), {}, None, np.random.default_rng(3))
    downs = [r for f, _, r in out if f["dir_z"] == "down" and f["mag_coarse"] in ("large", "xlarge")]
    assert all(r == "near_end" for r in downs)
