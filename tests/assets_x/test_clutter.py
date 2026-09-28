"""L8X-assets: cluttered scene sampler (pure)."""
from harvest.sim.assets_x import clutter as CL
from harvest.sim.assets_x import furniture as FU


def objects(n=40):
    return {f"o{i}": {"footprint_r": 0.03 + 0.002 * (i % 10), "root_above_bottom": 0.01 * (i % 3), "stable": i % 7 != 0,
                      "height": 0.04 + 0.006 * (i % 10),
                      "split": "train" if i % 5 else "ood_o", "pose": "upright", "task_name": f"thing {i}"}
            for i in range(n)}


def test_clutter_fills_tops_without_overlap_or_keep_free():
    objs = objects()
    for seed in range(20):
        sc = FU.sample_scene("counter", seed)
        keep = [((0.36, 0.48), (-0.30, -0.18))]
        c = CL.sample_clutter(sc, objs, seed, keep_free=keep)
        assert 5 <= c["n_target"] <= 12 and c["n_placed"] == c["n_target"], (seed, c["shortfall"])
        assert CL.overlaps(c["placements"]) == []
        for p in c["placements"]:
            assert objs[p["id"]]["stable"] and objs[p["id"]]["split"] == "train"
            (x0, x1), (y0, y1) = keep[0]
            assert not (x0 - p["r"] < p["x"] < x1 + p["r"] and y0 - p["r"] < p["y"] < y1 + p["r"])
    assert CL.sample_clutter(FU.sample_scene("counter", 3), objs, 3) == CL.sample_clutter(
        FU.sample_scene("counter", 3), objs, 3)


def test_clutter_skips_covered_tiers_and_bins():
    objs = objects()
    for seed in range(10):
        sc = FU.sample_scene("shelf_tall", seed)
        tiers = {s["id"]: s for s in sc["surfaces"] if s["covered_above"] is not None}
        c = CL.sample_clutter(sc, objs, seed)
        for p in c["placements"]:
            if p["surface"] in tiers:
                t = tiers[p["surface"]]
                assert t["covered_above"] - t["top_z"] >= max(CL.MIN_CLEAR, objs[p["id"]]["height"] + 0.05)
        b = FU.sample_scene("bin", seed)
        bins = {s["id"] for s in b["surfaces"] if s["container"]}
        assert all(p["surface"] not in bins for p in CL.sample_clutter(b, objs, seed)["placements"])
