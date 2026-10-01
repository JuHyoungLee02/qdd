import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = importlib.util.spec_from_file_location("jv1_summary", os.path.join(ROOT, "tools", "jv1", "summary.py"))
S = importlib.util.module_from_spec(_s)
_s.loader.exec_module(S)


def make(root, name, succ):
    for v in ("standard", "dr"):
        for s in range(20):
            d = os.path.join(root, name, v, f"s{s}")
            os.makedirs(d)
            ok = succ(v, s)
            json.dump({"variant": v, "seed": s, "success": ok, "failure": None if ok else "x:timeout",
                       "exec_stats": {"grip_fallback": 0, "errors": 0}, "lat_p50_s": 0.1}, open(f"{d}/ep.json", "w"))
            with open(f"{d}/ticks.jsonl", "w") as f:
                for k in range(5):
                    f.write(json.dumps({"q": [0.01 * k] * 7, "cmd": [0.001 * k, 0, 1]}) + "\n")
            with open(f"{d}/samples.jsonl", "w") as f:
                f.write(json.dumps({"jcr": {"anomaly_p": [0, 0, 0, 0, 0, 0.9], "contact_p": 0.1}, "anomaly": ["x"],
                                    "contact": False}) + "\n")
                f.write(json.dumps({"jcr": {"anomaly_p": [0, 0, 0, 0, 0, 0.1], "contact_p": 0.9}, "anomaly": [],
                                    "contact": True}) + "\n")


def test_b_better_verdict(tmp_path):
    for st in ("clean", "dist"):
        for c in ("Z", "R"):
            make(tmp_path, f"A_{c}_{st}", lambda v, s: s < 10)
            make(tmp_path, f"B_{c}_{st}", lambda v, s: s < 16 if c == "R" else s < 10)
        make(tmp_path, f"C_Z_{st}", lambda v, s: True)
    out = tmp_path / "summary.json"
    S.main(["--eval", str(tmp_path), "--out", str(out)])
    r = json.load(open(out))
    assert r["verdict"] == "B_BETTER"
    assert r["arms"]["A_Z_clean"]["success"] == 20 and r["arms"]["A_Z_clean"]["anomaly_auroc"] == 1.0
    assert r["pairs"]["B-A_R_pooled"]["n"] == 80 and abs(r["pairs"]["B-A_R_pooled"]["diff"] - 0.3) < 1e-9
    assert not r["controller_limit"]
