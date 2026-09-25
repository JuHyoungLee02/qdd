"""Aggregator: F1 adoption rule, staggered flip metrics, paired bootstrap, grasp-probe scoring."""
import math

from harvest.astra_motion import agg as A
from harvest.astra_motion.grasp_probe import score


def e(dp, g="keep"):
    return {"decision": "edit", "edit": {"delta_position_cm": dp, "delta_rotation_rad": [0, 0, 0], "gripper": g}}


def test_f1_rule():
    t = {("astra-low", "S-stream-F0"): {"n": 2, "success": 1, "stream_flips_pooled": 0.40},
         ("astra-low", "S-stream-F1"): {"n": 2, "success": 1, "stream_flips_pooled": 0.20}}
    assert A.f1_rule(t)["verdict"] == "F1"
    t[("astra-low", "S-stream-F1")]["stream_flips_pooled"] = 0.21
    assert A.f1_rule(t)["verdict"] == "F0"
    t[("astra-low", "S-stream-F1")].update(stream_flips_pooled=0.1, success=0)
    assert A.f1_rule(t)["verdict"] == "F0"
    assert A.f1_rule({})["verdict"] == "incomplete"


def test_stagger_flips_and_unjustified():
    ans = [{"valid": True, "send_t": 0.0, "arr_t": 3.0, "latency_s": 3.0, "effective": e([3, 0, 0])},
           {"valid": True, "send_t": 1.0, "arr_t": 4.0, "latency_s": 3.0, "effective": e([3, 0.5, 0])},
           {"valid": True, "send_t": 2.0, "arr_t": 5.0, "latency_s": 3.0, "effective": e([0, 3, 0])},  # flip
           {"valid": True, "send_t": 3.0, "arr_t": 6.0, "latency_s": 3.0, "effective": e([0, 3, 0], "close")}]  # flip
    r = {"stream": {"answers": ans, "gripper_events": [2.5], "exec_sim_s": 30.0, "rtf": 1.0}, "hold_changes": [],
         "cost_usd": 0.6}
    m = A.stream_metrics(r)
    assert m["flip_rate"] == round(2 / 3, 3) and m["unjustified_flip_rate"] == round(1 / 3, 3)
    assert m["gap_p50_s"] == 1.0 and m["cost_krw_per_robot_min"] == round(0.6 * A.KRW_PER_USD / 0.5, 1)


def test_paired_bootstrap_identical_is_zero():
    a = {f"e{i}": {"success": i % 2 == 0} for i in range(10)}
    r = A.paired_bootstrap(a, a)
    assert r["diff"] == 0 and r["ci95"] == [0.0, 0.0] and r["n"] == 10
    b = {f"e{i}": {"success": False} for i in range(10)}
    r = A.paired_bootstrap(a, b)
    assert r["diff"] == 0.5 and r["ci95"][0] > 0


def test_grasp_score():
    rows = []
    for snap, state, gt in (("a/pre", "pre", False), ("a/grasped", "grasped", True), ("a/miss", "miss", False)):
        for rep, ans in enumerate(("grasped", "grasped")):
            rows.append({"snap": snap, "state": state, "gt_holding": gt, "views": "all3", "overlay": True, "rep": rep,
                         "model": "m", "valid": True, "answer": {"grasp_state": ans}, "cost_usd": 0.01})
    s = score(rows)["m|all3|overlay"]
    assert s["false_grasped"] == "4/4" and s["missed_grasped"] == "0/2" and s["miss_false_grasped"] == "2/2"
    assert s["repeat_agree"] == "3/3"
    assert A.grasp_err({"first_close": None}) == math.inf
