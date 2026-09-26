"""Controller ruling O2 (2026-09-26, docs/stage3/molmoact_r2_readiness.md C6/M5): the overlay's trace/next/offset
colours must stay far from every R2 pool + object colour so the VLA/Astra never mistakes a drawn cue for a real
object. Loads the live palette (distractor_colors from harvest/sim/randomization_pools.json's test+train pools,
object colours from harvest/sim/scene.py OBJ_GEOM) rather than a hard-coded copy, so this stays true if the palette
changes."""
import json
import math
import pathlib

from harvest.couple.overlay import NEXT_COLOR, OFFSET_COLOR, TRACE_COLOR
from harvest.sim.scene import OBJ_GEOM

POOLS_JSON = pathlib.Path(__file__).resolve().parents[2] / "harvest" / "sim" / "randomization_pools.json"
MIN_DIST = 120.0


def _live_palette() -> dict:
    data = json.loads(POOLS_JSON.read_text(encoding="utf-8"))
    pal = {}
    for pool_name, pool in data["pools"].items():
        for c in pool["distractor_colors"]:
            pal[f"{pool_name}.{c['name']}"] = tuple(round(v * 255) for v in c["color"])
    for obj, spec in OBJ_GEOM.items():
        if "color" in spec:
            pal[f"obj.{obj}"] = tuple(round(v * 255) for v in spec["color"])
    return pal


def _dist(a, b) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def test_live_palette_is_not_trivially_empty():
    pal = _live_palette()
    assert len(pal) >= 14 and "train.col_cyan" in pal and "obj.o11" in pal  # sanity: the two named collisions exist


def test_trace_next_offset_colours_clear_every_palette_colour():
    pal = _live_palette()
    for name, colour in (("TRACE_COLOR", TRACE_COLOR), ("NEXT_COLOR", NEXT_COLOR), ("OFFSET_COLOR", OFFSET_COLOR)):
        worst_name, worst_d = min(((k, _dist(colour, v)) for k, v in pal.items()), key=lambda kv: kv[1])
        assert worst_d >= MIN_DIST, f"{name}={colour} only {worst_d:.1f} from {worst_name}={pal[worst_name]}"


def test_the_previously_flagged_collisions_are_fixed():
    pal = _live_palette()
    # the two collisions named in molmoact_r2_readiness.md's "notify other tasks" note (P77/M5)
    assert _dist(NEXT_COLOR, pal["train.col_cyan"]) >= MIN_DIST
    assert _dist(OFFSET_COLOR, pal["obj.o11"]) >= MIN_DIST
