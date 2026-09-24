from harvest.deccall_snap import build_snapshot_request
from harvest.e3lite import code_rule, geometry_block, mag_bin, parse_geometry, rotate, state_text
from harvest.jevcall import DIR_XY, NE

S0 = ("t_state: f0 (t=0.00s)  contract: c1  stage: S1 \"pick up mug o3\"\nrobot: gripper=open arm=still\nobjects:\n"
      "  o3 mug red | on(table) | upright\n  o5 tray blue | on(table) | upright\nfacts: gripper_open=yes\n"
      "stage S1: exit=holding(o3) lifted(o3) invariants= elapsed=normal\nchanges (last 3s): ")


def _line(grip=(0.334, -0.248, 0.244), o3=(0.428, -0.382, 0.0475), o5=(0.477, -0.174, 0.0075), text=S0,
          present=("o3", "o5")):
    objs = {"o3": {"pos": list(o3)}, "o5": {"pos": list(o5)}}
    return {"seed": 0, "kind": "P0", "k": 0, "ds_id": "ds0", "phase": "approach", "text_state": text,
            "state": {"present": list(present), "obs": {"raw": {"objs": objs, "grip": {"pos": list(grip)}}}},
            "oracle": {"dir_xy": "plus_x_minus_y", "dir_z": "down", "mag_coarse": "xlarge", "target": "o3",
                       "phase_choice": "continue", "progress": "valid_progress"}}


def test_mag_bin_matches_oracle_bins():
    assert mag_bin(0.001) == "tiny" and mag_bin(0.011) == "small" and mag_bin(0.019) == "medium"
    assert mag_bin(0.035) == "large" and mag_bin(0.30) == "xlarge"


def test_s1_block_frame_line_gripper_and_offsets_in_cm():
    g = geometry_block(_line()["state"], bins=False)
    lines = g.split("\n")
    assert lines[0].startswith("geometry (robot base frame: +x forward away from the robot, +y robot left, +z up")
    assert lines[1] == "  gripper: x=33 y=-25 z=24 (z = height above the table top)"
    # o3 - grip = (+9.4, -13.5, -19.7) cm, dist 25.7
    assert lines[2] == "  o3 mug red: dx=+9 dy=-13 dz=-20 dist=26"
    assert lines[3].startswith("  o5 tray blue: dx=+14 dy=+7 dz=-24 dist=")
    assert "bins" not in g


def test_s2_adds_bin_names_with_sign():
    g = geometry_block(_line()["state"], bins=True)
    assert "  o3 mug red: dx=+9 dy=-13 dz=-20 dist=26 bins: dx=+xlarge dy=-xlarge dz=-xlarge dist=xlarge" in g


def test_state_text_s0_unchanged_s1_s2_append_block():
    ln = _line()
    assert state_text(ln, "S0") == S0
    s1, s2 = state_text(ln, "S1"), state_text(ln, "S2")
    assert s1.startswith(S0 + "\ngeometry") and s2.startswith(S0 + "\ngeometry") and "bins:" in s2
    assert "bins:" not in s1


def test_only_present_objects_in_number_order():
    ln = _line(present=("o5", "o3"))
    ln["state"]["obs"]["raw"]["objs"]["o10"] = {"pos": [0.5, 0.0, 0.04]}
    g = geometry_block(ln["state"])
    assert g.index("o3 mug") < g.index("o5 tray") and "o10" not in g


def test_rotate_keeps_ne_last_and_shifts_cyclically():
    r = rotate(DIR_XY, 2)
    body = [o.key for o in DIR_XY if o.key != NE.key]
    assert [o.key for o in r][:-1] == body[2:] + body[:2] and r[-1].key == NE.key
    assert [o.key for o in rotate(DIR_XY, len(body))] == [o.key for o in DIR_XY]


def test_build_request_with_state_and_shift():
    ln = _line()
    req, oracle, shown = build_snapshot_request(ln, text_state=state_text(ln, "S1"), shift=1)
    assert "geometry" in req["state"]
    assert list(req["questions"]["ds0.dir_z"]["criteria"]) == ["down", "none_z", "up", "NONE_ESCALATE"]
    assert list(req["questions"]["ds0.target"]["criteria"]) == ["o5", "o3", "NONE_ESCALATE"]
    req0, _, _ = build_snapshot_request(ln)
    assert list(req0["questions"]["ds0.dir_z"]["criteria"]) == ["up", "down", "none_z", "NONE_ESCALATE"]


def test_parse_geometry_reads_rounded_numbers():
    g = parse_geometry(state_text(_line(), "S1"))
    assert g["gripper"] == (33, -25, 24) and g["o3"] == (9, -13, -20) and g["stage"] == "S1"
    assert g["gripper_state"] == "open"


def test_code_rule_approach_moves_toward_mug_top_fast():
    a = code_rule(state_text(_line(), "S1"))
    # goal = mug xy, 14.75 cm above the mug centre: (+9, -13, -20 + 14.75) -> 0.066 m step, mostly +x -y, down
    assert a["dir_xy"] == "plus_x_minus_y" and a["dir_z"] == "down" and a["mag_coarse"] == "xlarge"
    assert a["target"] == "o3" and a["phase_choice"] == "continue" and a["progress"] == "valid_progress"


def test_code_rule_descend_when_above_mug():
    ln = _line(grip=(0.428, -0.382, 0.0475 + 0.12))
    a = code_rule(state_text(ln, "S1"))
    assert a["dir_xy"] == "none_xy" and a["dir_z"] == "down" and a["mag_coarse"] == "medium"  # 0.06*0.33=2 cm


def test_code_rule_lift_and_carry_and_place():
    hold = S0.replace("gripper=open", "gripper=closed_holding(o3)")
    ln = _line(grip=(0.428, -0.382, 0.08), o3=(0.428, -0.382, 0.05), text=hold)
    a = code_rule(state_text(ln, "S1"))
    assert a["dir_z"] == "up" and a["dir_xy"] == "none_xy" and a["target"] == "o5"
    s2 = hold.replace("stage: S1", "stage: S2")
    ln = _line(grip=(0.40, -0.38, 0.20), o3=(0.40, -0.38, 0.17), o5=(0.48, -0.30, 0.0075), text=s2)
    a = code_rule(state_text(ln, "S1"))
    assert a["dir_xy"] == "plus_x_plus_y" and a["dir_z"] == "none_z" and a["target"] == "o5"
    ln = _line(grip=(0.48, -0.17, 0.20), o3=(0.48, -0.17, 0.17), o5=(0.48, -0.17, 0.0075), text=s2)
    a = code_rule(state_text(ln, "S1"))
    assert a["dir_xy"] == "none_xy" and a["dir_z"] == "down"


def test_code_rule_raw_uses_unrounded_values():
    ln = _line(grip=(0.428, -0.382, 0.0475 + 0.0295 + 0.008))  # 8 mm above the descend goal
    a = code_rule(state_text(ln, "S1"), raw=ln["state"])
    assert a["dir_xy"] == "none_xy" and a["dir_z"] == "down" and a["mag_coarse"] == "small"
    ln = _line(grip=(0.428, -0.382, 0.0475 + 0.0295 + 0.004))  # 4 mm: inside the 6 mm reach tolerance -> close
    a = code_rule(state_text(ln, "S1"), raw=ln["state"])
    assert a["dir_z"] == "none_z" and a["mag_coarse"] == "tiny"
