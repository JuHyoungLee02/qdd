from harvest.l9 import curobo9 as C
from harvest.l9 import robot9 as RB


def test_cspace_ready_g1(monkeypatch):
    monkeypatch.delenv("L9_CSPACE_READY", raising=False)
    k0 = C.load_config("g1", "right")["robot_cfg"]["kinematics"]["cspace"]
    monkeypatch.setenv("L9_CSPACE_READY", "1")
    k1 = C.load_config("g1", "right")["robot_cfg"]["kinematics"]["cspace"]
    n = k1["joint_names"]
    j = RB.V2["g1"]["arms"]["right"]["joints"]
    assert [k1["default_joint_position"][n.index(x)] for x in j] == list(RB.V2_READY["g1"]["right"])
    jl = RB.V2["g1"]["arms"]["left"]["joints"]
    assert [k1["default_joint_position"][n.index(x)] for x in jl] == list(RB.V2_STOW["g1"]["left"])
    hand = [i for i, x in enumerate(n) if "hand" in x]
    assert all(k1["default_joint_position"][i] == k0["default_joint_position"][i] for i in hand)


def test_cspace_ready_leaves_ffw(monkeypatch):
    monkeypatch.setenv("L9_CSPACE_READY", "1")
    a = C.load_config("ffw_sg2", "right")["robot_cfg"]["kinematics"]["cspace"]["default_joint_position"]
    monkeypatch.delenv("L9_CSPACE_READY")
    assert a == C.load_config("ffw_sg2", "right")["robot_cfg"]["kinematics"]["cspace"]["default_joint_position"]
