"""E-M35CL pure helpers (harvest.teach_pt.run_closed_l8s): conditions, claims, yield files, job parsing."""
import os
import time

import pytest

from harvest.teach_pt import run_closed_l8s as R


def test_parse_cond():
    assert R.parse_cond("none") == {"kind": "none"}
    assert R.parse_cond("light:dim_warm") == {"kind": "light", "level": "dim_warm"}
    assert R.parse_cond("head:10:15") == {"kind": "head", "tilt_deg": 10.0, "pan_deg": 15.0}
    with pytest.raises(ValueError):
        R.parse_cond("head:10")
    assert R.cond_dir("head:-10:15") == "head_m10_15"


def test_claim_once_and_stale(tmp_path):
    od = str(tmp_path / "ep")
    assert R.claim(od, "a")
    assert not R.claim(od, "b")  # fresh claim held
    assert R.claim(od, "c", now=time.time() + R.STALE_S + 5)  # stale (D: mtime is 2 s coarse)
    open(os.path.join(od, "result.json"), "w").write("{}")
    assert R.done(od) and not R.claim(od, "d", now=time.time() + 10 * R.STALE_S)


def test_yield_reason(tmp_path):
    f = tmp_path / "GPU_WANTED"
    assert R.yield_reason(["", str(f)]) is None
    f.write_text("x")
    assert R.yield_reason(["", str(f)]) == str(f)


def test_job_args():
    j = R.job_args("--split ood_o --confirm-ood --variant drf --table-z 0.0 --ws-x 0.36,0.54 --furniture "
                   "thor_low_table --rooms --objset x --clutter 40 --plan /p.json --video-seeds 1,2 --out /o")
    assert (j.split, j.variant, j.table_z, j.furniture, j.rooms, j.clutter, j.plan, j.lift) == (
        "ood_o", "drf", 0.0, "thor_low_table", True, 40, "/p.json", None)


def test_head_patch_restores():
    class CX:
        HEAD_TILT0 = 0.785

        @staticmethod
        def head_pose(seed, attempt=0):
            return {"orig": True}
    undo = R.head_patch(CX, {"kind": "head", "tilt_deg": 10.0, "pan_deg": 15.0})
    h = CX.head_pose(1)
    assert h["random"] and abs(h["tilt"] - 0.9595) < 1e-3 and abs(h["pan"] - 0.2618) < 1e-3
    assert abs(CX.head_pose(1, 1)["pan"] - 0.1309) < 1e-3
    undo()
    assert CX.head_pose(1) == {"orig": True}


def test_server_error_and_served(tmp_path):
    assert R.server_error("ConnectError") and R.server_error("timeout") and R.server_error("http_503:x")
    assert R.server_error("http_404:no model") and not R.server_error("http_400:too long") and not R.server_error(None)
    f = tmp_path / "CURRENT"
    assert R.served(str(f)) is None
    f.write_text("f35d http://h:1 m35cl_f35d")
    assert R.served(str(f)) == "f35d"
