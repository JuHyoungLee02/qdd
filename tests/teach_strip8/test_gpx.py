"""G-px (prereg_priv8.md change 1): a pixel-coordinate grid (0-1000 scale, every 100, labels on the top / left edges)
drawn on the head image of the E-DIST8 D (point) rows; the legend says exactly that; nothing else changes."""
import json

import numpy as np
from PIL import Image

from harvest.astra_solo import nd_prompts as NP
from harvest.teach_strip8 import gpx as G


def test_overlay_changes_only_grid_pixels(tmp_path):
    img = np.full((376, 672, 3), 90, np.uint8)
    out = G.px_grid(img)
    assert out.shape == img.shape and out.dtype == np.uint8
    diff = np.abs(out.astype(int) - img.astype(int)).max(-1) > 0
    x100 = round(100 / 1000 * 672)
    assert diff[200, x100 - 1:x100 + 2].any() and diff[round(500 / 1000 * 376), 300]
    assert 0.02 < diff.mean() < 0.25  # thin lines + labels, most of the image untouched
    assert not diff[5 + 40, 5 + 40:5 + 45].all()


def test_text_legend():
    t = "HEAD\n" + NP._OVL_ND + "DEFINITIONS\n"
    g = G.gpx_text(t)
    assert G.LEGEND in g and "Nothing else is drawn" not in g and g.count("White ring") == 1
    assert G.gpx_text(g) == g
    aux = "Image 1 is the robot's head camera (the white ring is the gripper's TCP).\nPoint to the red mug in image 1."
    assert G.AUX_LEGEND in G.gpx_aux(aux)


def test_build_rows(tmp_path):
    im = tmp_path / "ring.png"
    Image.fromarray(np.full((376, 672, 3), 90, np.uint8)).save(im)
    p = tmp_path / "p.txt"
    p.write_text("HEAD\n" + NP._OVL_ND + "DEFINITIONS\n", encoding="utf-8")
    rows = [{"id": "a", "kind": "control", "prompt_path": str(p), "images": [str(im), "w.png"], "answer": "{}"},
            {"id": "a", "kind": "control", "prompt_path": str(p), "images": [str(im), "w.png"], "answer": "{}"},
            {"id": "a_aux", "kind": "aux", "prompt": "Image 1 is the robot's head camera (the white ring is the "
             "gripper's TCP).\nq", "images": [str(im)], "answer": "{}"}]
    src = tmp_path / "train_d-min.jsonl"
    src.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    c = G.build(str(src), str(tmp_path / "o"), "train_g-px")
    out = [json.loads(x) for x in open(tmp_path / "o" / "train_g-px.jsonl")]
    assert len(out) == 3 and c["images_drawn"] == 1 and out[0]["images"][1] == "w.png"
    assert out[0]["images"][0] == out[2]["images"][0] != str(im)
    assert G.LEGEND in open(out[0]["prompt_path"], encoding="utf-8").read() and G.AUX_LEGEND in out[2]["prompt"]
    assert {k: v for k, v in out[0].items() if k not in ("prompt_path", "images", "arm")} == \
        {k: v for k, v in rows[0].items() if k not in ("prompt_path", "images")}
