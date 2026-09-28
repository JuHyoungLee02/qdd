"""L8X-assets: real-object descriptors and the name check (pure)."""
import math

import numpy as np

from harvest.sim.assets_x import objects_real as OR


def cylinder(r=0.04, h=0.10, n=60, m=20):
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    z = np.linspace(0, h, m)
    A, Z = np.meshgrid(a, z)
    return np.stack([r * np.cos(A).ravel(), r * np.sin(A).ravel(), Z.ravel()], 1)


def handle(r=0.04, h=0.10):
    t = np.linspace(-math.pi / 2, math.pi / 2, 40)
    return np.stack([r + 0.025 * np.cos(t), np.zeros_like(t), h / 2 + 0.03 * np.sin(t)], 1)


def box(x=0.06, y=0.12, z=0.08):
    g = np.linspace(0, 1, 12)
    P = np.array([[a * x, b * y, c * z] for a in g for b in g for c in (0, 1)] +
                 [[a * x, b * y, c * z] for a in g for c in g for b in (0, 1)] +
                 [[a * x, b * y, c * z] for b in g for c in g for a in (0, 1)])
    return P


def test_cup_mug_box_ball():
    d = OR.descriptors(cylinder())
    assert abs(d["grasp_width"] - 0.08) < 0.003 and abs(d["height"] - 0.10) < 1e-6
    assert d["circularity"] > 0.9 and d["handle_ratio"] < 1.1
    assert OR.name_check("mug", d)["noun"] == "cup"  # no handle -> renamed
    assert OR.name_check("cup", d) == {"claimed": "cup", "noun": "cup", "renamed": False, "reasons": []}
    dm = OR.descriptors(np.concatenate([cylinder(), handle()]))
    assert dm["handle_ratio"] >= OR.HANDLE_RATIO
    assert OR.name_check("cup", dm)["noun"] == "mug" and not OR.name_check("mug", dm)["renamed"]
    db = OR.descriptors(box())
    assert abs(db["grasp_width"] - 0.06) < 0.003 and db["circularity"] < 0.75
    assert OR.name_check("can", db)["noun"] == "container" and OR.name_check("box", db)["noun"] == "box"
    rng = np.random.default_rng(0)
    s = rng.normal(size=(2000, 3))
    s = 0.035 * s / np.linalg.norm(s, axis=1, keepdims=True)
    assert OR.name_check("ball", OR.descriptors(s))["noun"] == "ball"
    assert OR.name_check("ball", db)["noun"] == "toy"


def test_claims_colours_sizes():
    assert OR.claimed_noun("Threshold_Porcelain_Coffee_Mug_All_Over_Bead_White") == "mug"
    assert OR.claimed_noun("Nike_Air_Zoom_Pegasus", "Shoe") == "shoe"
    assert OR.claimed_noun("Utana_5_Porcelain_Ramekin_Large") == "bowl"
    assert OR.colour_word((200, 30, 30)) == "red" and OR.colour_word((30, 60, 200)) == "blue"
    assert OR.colour_word((240, 240, 240)) == "white" and OR.colour_word((20, 20, 20)) == "black"
    assert OR.colour_word((40, 160, 50)) == "green"
    objs = {f"o{i}": {"noun": "cup", "height": 0.05 + 0.01 * i, "grasp_width": 0.06, "length": 0.06}
            for i in range(6)}
    sw = OR.size_words(objs)
    assert sw["o0"] == "small" and sw["o5"] == "large" and sw["o2"] is None
    assert OR.task_name({"noun": "cup", "colour": "red"}, "small") == "small red cup"


def test_boxiness_and_shape_fallback():
    db, dc = OR.descriptors(box()), OR.descriptors(cylinder())
    assert db["boxiness"] >= 0.85 and dc["boxiness"] < 0.85
    assert OR.name_check(None, db)["noun"] == "box"
    assert OR.claimed_noun("Scissors_Red") == "SKIP" and OR.claimed_noun("Womens_Boat_Shoe", "Bottles and Cans") == "shoe"
