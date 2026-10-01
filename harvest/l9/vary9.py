"""L9 variation layer (spec §5, §0): light families, head pose (every episode), unrealistic mode (off by default),
environment combination hash (user 2026-09-30: every episode's environment combination is unique). Pure.

Lighting is written through the L8S drf path: randomize.sample_randomization(seed, "drf", layout) gives the dome /
key / fill structure that randomize.apply_visuals reads; light_meta() overwrites its numbers with the family's
distributions (key type, strength, colour temperature, direction, softness, tint, fills, dome strength / rotation)."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

import numpy as np

HEAD_TILT0 = 0.785  # 45 deg, the real robot
HEAD_TILT_RANGE = math.radians(15.0)
HEAD_PAN_RANGE = 0.34  # spec §4 asked +-30 deg; the robot's head_joint2 range is +-0.35 rad (20 deg, USD / MJCF): hardware wins
HEAD_TILT_MAX = math.radians(57.0) - 0.01  # the raised USD limit (L8S _head_limit)
HEAD_TRIES = 5  # spec §4: redraw while the task objects leave the view, then the default pose


@dataclass(frozen=True)
class LightFamily:
    name: str
    key_types: tuple  # randomize.LIGHT_TYPES subset
    key_mult: tuple  # x base intensity x key_weight
    color_k: tuple  # key colour temperature
    azimuth: tuple  # deg around the work area (0 = in front of the robot, from +x); world frame
    elevation: tuple  # deg
    soft: tuple  # key size scale (small = hard shadows)
    dome_mult: tuple  # x the pool's dome intensity
    fills: tuple  # (min, max) fill lights (<= 2)
    fill_mult: tuple  # x key intensity
    tint_p: float  # chance of a coloured key tint
    tint_sat: tuple = (0.10, 0.30)


LIGHT_FAMILIES = {f.name: f for f in (
    LightFamily("window_sun", ("distant",), (1.1, 1.8), (5200, 6500), (-140, -40), (25, 55), (0.3, 0.8), (0.6, 1.1),
                (0, 1), (0.10, 0.30), 0.0),
    LightFamily("overcast", ("rect", "disk"), (0.4, 0.8), (6200, 7500), (-180, 180), (55, 85), (2.0, 3.0), (1.0, 1.5),
                (1, 2), (0.30, 0.60), 0.0),
    LightFamily("evening_warm", ("sphere", "disk"), (0.6, 1.1), (2400, 3300), (-180, 180), (20, 45), (0.8, 2.0),
                (0.3, 0.6), (0, 2), (0.20, 0.50), 0.25, (0.10, 0.25)),
    LightFamily("office_fluorescent", ("rect", "cylinder"), (0.8, 1.3), (4000, 5000), (-60, 60), (70, 88),
                (1.5, 3.0), (0.7, 1.0), (1, 2), (0.40, 0.70), 0.0),
    LightFamily("store_spot", ("sphere", "disk"), (1.2, 2.0), (3000, 4200), (-90, 90), (55, 80), (0.3, 0.7),
                (0.4, 0.8), (2, 2), (0.30, 0.60), 0.0),
    LightFamily("dark_lamp", ("sphere",), (0.5, 0.9), (2600, 3200), (-150, 150), (30, 60), (0.5, 1.2), (0.15, 0.35),
                (0, 1), (0.10, 0.25), 0.1),
    LightFamily("backlight", ("distant", "rect"), (1.0, 1.6), (4800, 6500), (-30, 30), (15, 40), (0.5, 1.5),
                (0.5, 0.9), (1, 2), (0.20, 0.40), 0.0),
    LightFamily("colored", ("sphere", "disk", "rect"), (0.7, 1.2), (3500, 6500), (-180, 180), (30, 75), (0.8, 2.5),
                (0.5, 0.9), (1, 2), (0.30, 0.60), 1.0, (0.25, 0.45)),
    LightFamily("hard_shadow", ("distant", "sphere"), (1.2, 1.9), (4500, 6000), (-180, 180), (35, 65), (0.2, 0.4),
                (0.3, 0.6), (0, 0), (0.0, 0.0), 0.0),
    LightFamily("soft_diffuse", ("rect",), (0.4, 0.7), (4800, 6200), (-180, 180), (60, 88), (2.5, 3.0), (1.1, 1.6),
                (2, 2), (0.40, 0.70), 0.0),
    LightFamily("kitchen_mixed", ("cylinder", "rect", "sphere"), (0.8, 1.3), (3000, 5500), (-120, 120), (45, 80),
                (1.0, 2.5), (0.6, 1.0), (1, 2), (0.25, 0.55), 0.15),
    # L9 v2 (spec §12.3, "every axis as wide as possible"): 12 more families; the shapes / ranges are our own
    # [hypothesis, judged by the G4 v2 SigLIP spread], colour temperatures from common lamp types (1,800 K candle
    # .. 7,500 K overcast sky).
    LightFamily("golden_hour", ("distant",), (0.9, 1.5), (1900, 2900), (-180, 180), (5, 18), (0.3, 0.9), (0.5, 0.9),
                (0, 1), (0.10, 0.30), 0.15, (0.08, 0.20)),
    LightFamily("noon_skylight", ("distant", "rect"), (1.0, 1.6), (5600, 7000), (-180, 180), (75, 89), (0.4, 1.5),
                (0.9, 1.4), (0, 1), (0.20, 0.40), 0.0),
    LightFamily("night_led", ("disk", "rect"), (0.5, 1.0), (5500, 7000), (-120, 120), (60, 88), (0.6, 1.6),
                (0.10, 0.30), (0, 2), (0.15, 0.40), 0.10, (0.05, 0.15)),
    LightFamily("candle_dim", ("sphere",), (0.25, 0.55), (1800, 2300), (-180, 180), (20, 50), (0.4, 1.0),
                (0.10, 0.25), (0, 1), (0.10, 0.30), 0.20, (0.10, 0.25)),
    LightFamily("neon_mixed", ("rect", "cylinder", "sphere"), (0.6, 1.1), (3000, 7500), (-180, 180), (20, 70),
                (0.6, 2.0), (0.3, 0.7), (2, 2), (0.40, 0.80), 1.0, (0.35, 0.60)),
    LightFamily("clinical_bright", ("rect",), (1.2, 1.8), (5000, 6500), (-40, 40), (75, 89), (2.0, 3.0), (0.9, 1.3),
                (2, 2), (0.50, 0.80), 0.0),
    LightFamily("sodium_highbay", ("sphere", "disk"), (1.0, 1.6), (1900, 2400), (-180, 180), (70, 89), (0.4, 1.0),
                (0.3, 0.6), (1, 2), (0.30, 0.60), 0.3, (0.10, 0.20)),
    LightFamily("track_spots", ("disk", "sphere"), (1.3, 2.2), (2700, 4000), (-100, 100), (45, 75), (0.2, 0.5),
                (0.3, 0.6), (2, 2), (0.40, 0.80), 0.05),
    LightFamily("side_window", ("rect", "distant"), (0.9, 1.5), (5000, 7000), (60, 120), (10, 35), (1.0, 3.0),
                (0.6, 1.0), (0, 1), (0.15, 0.35), 0.0),
    LightFamily("rim_backlight", ("rect", "sphere"), (1.3, 2.0), (3500, 6500), (-25, 25), (25, 50), (0.4, 1.2),
                (0.3, 0.6), (1, 1), (0.10, 0.25), 0.2, (0.10, 0.30)),
    LightFamily("sunny_outdoor", ("distant",), (1.4, 2.2), (5200, 6500), (-180, 180), (30, 75), (0.2, 0.6),
                (0.9, 1.5), (0, 1), (0.10, 0.25), 0.0),
    LightFamily("outdoor_shade", ("rect", "distant"), (0.3, 0.7), (6500, 8000), (-180, 180), (40, 85), (2.0, 3.0),
                (1.3, 1.9), (0, 1), (0.20, 0.50), 0.0),
)}
LIGHT_NAMES = tuple(LIGHT_FAMILIES)
OUTDOOR_LIGHTS = ("sunny_outdoor", "outdoor_shade", "golden_hour", "overcast", "hard_shadow")
INDOOR_LIGHTS = tuple(n for n in LIGHT_NAMES if n not in ("sunny_outdoor", "outdoor_shade"))


def _r(v, n=4):
    return round(float(v), n)


def _tint(rng, sat) -> list:
    h = float(rng.uniform(0.0, 2 * math.pi))
    s = float(rng.uniform(*sat))
    return [_r(1.0 - s * (0.5 + 0.5 * math.cos(h + k * 2.094)), 3) for k in range(3)]


def pick_light_family(seed: int, env_family: str) -> str:
    """Seeded family choice: uniform over INDOOR_LIGHTS (every indoor environment family sees every one), over
    OUTDOOR_LIGHTS for the outdoor families (scene9.OUTDOOR)."""
    from .scene9 import OUTDOOR
    names = OUTDOOR_LIGHTS if env_family in OUTDOOR else INDOOR_LIGHTS
    h = int(hashlib.sha256(f"l9-light:{int(seed)}:{env_family}".encode()).hexdigest()[:8], 16)
    return names[h % len(names)]


def light_meta(meta: dict, family: str, seed: int, target, common: dict) -> dict:
    """The drf randomisation meta with this light family's numbers (a new dict; `meta` unchanged).
    target: the work area centre (world); common: randomization pools 'common' (light_types, key/dome weights,
    light_distance_m)."""
    from ..sim.randomize import look_at_quat
    f = LIGHT_FAMILIES[family]
    rng = np.random.default_rng([int(seed), 919, LIGHT_NAMES.index(family)])
    m = json.loads(json.dumps(meta))
    lt = f.key_types[int(rng.integers(len(f.key_types)))]
    spec = common["light_types"][lt]
    mult = float(rng.uniform(*f.key_mult))
    az, el = float(rng.uniform(*f.azimuth)), float(rng.uniform(*f.elevation))
    dist = float(rng.uniform(*common["light_distance_m"]))
    tgt = np.asarray(target, float)
    ca, sa, ce, se = math.cos(math.radians(az)), math.sin(math.radians(az)), math.cos(math.radians(el)), \
        math.sin(math.radians(el))
    pos = tgt + dist * np.array([ce * ca, ce * sa, se])
    key = spec["base_intensity"] * common["key_weight"] * mult
    m["light"] = {"type": lt, "intensity_mult": _r(mult), "intensity": _r(key, 2),
                  "color_temperature_k": _r(rng.uniform(*f.color_k), 1), "azimuth_deg": _r(az, 3),
                  "elevation_deg": _r(el, 3), "distance_m": _r(dist), "pos": [_r(v) for v in pos],
                  "target": [_r(v) for v in tgt], "quat_wxyz": [_r(v, 6) for v in look_at_quat(pos, tgt)],
                  "shape": {k: v for k, v in spec.items() if k != "base_intensity"}}
    dm = float(rng.uniform(*f.dome_mult))
    m["hdr"]["intensity"] = _r(m["hdr"]["intensity"] * dm, 2)
    m["hdr"]["rotation_deg"] = _r(rng.uniform(-180.0, 180.0), 2)
    fills = []
    for _ in range(int(rng.integers(f.fills[0], f.fills[1] + 1))):
        faz, fel = float(rng.uniform(-180.0, 180.0)), float(rng.uniform(15.0, 80.0))
        fd = float(rng.uniform(*common["light_distance_m"]))
        c1, s1, c2, s2 = (math.cos(math.radians(faz)), math.sin(math.radians(faz)), math.cos(math.radians(fel)),
                          math.sin(math.radians(fel)))
        fp = tgt + fd * np.array([c2 * c1, c2 * s1, s2])
        tinted = bool(rng.random() < f.tint_p * 0.5)
        fills.append({"pos": [_r(v) for v in fp], "azimuth_deg": _r(faz, 3), "elevation_deg": _r(fel, 3),
                      "intensity": _r(key * float(rng.uniform(*f.fill_mult)), 2),
                      "radius": _r(float(rng.uniform(0.05, 0.4))), "tinted": tinted,
                      "color": _tint(rng, f.tint_sat) if tinted else [1.0, 1.0, 1.0]})
    m["lighting"] = {"exposure": 1.0, "key_tint": _tint(rng, f.tint_sat) if rng.random() < f.tint_p else None,
                     "key_radius_scale": _r(rng.uniform(*f.soft)), "fills": fills[:2], "family": family}
    return m


# head tilt (head_joint1, rad) per look mode, AI Worker FFW-SG2: ffw_sg2.xml head_joint1 range -0.2317..0.6951 (the
# L8S worlds raise the USD upper limit to 57 deg, HEAD_TILT_MAX; the real robot works at 45 deg). "up": places above
# eye level (scene9 place_class high) need a level / slightly lowered gaze; "down": low places (place_class low).
# Ranges inside the joint limits are our own [hypothesis; the world's in-view check (target and place inside the
# image by 5 %) still redraws]. Other robots: their own neck / mast rules (robot9 / hcam9, L9v2-ROBOT).
LOOK = {"std": (HEAD_TILT0 - HEAD_TILT_RANGE, HEAD_TILT_MAX), "up": (-0.2317, 0.35), "down": (0.80, HEAD_TILT_MAX)}


def head_pose(seed: int, attempt: int = 0, look: str = "std") -> dict:
    """Every L9 episode moves the neck: std = tilt 45 deg +- 15 deg (clipped below the raised limit), pan +- 20 deg;
    look "up" / "down" (high / low places) draw the tilt from LOOK; later attempts (the objects left the view)
    redraw; after HEAD_TRIES the caller uses head_default()."""
    if look == "std":
        rng = np.random.default_rng([int(seed), 431, int(attempt)])
        tilt = float(np.clip(HEAD_TILT0 + rng.uniform(-HEAD_TILT_RANGE, HEAD_TILT_RANGE), 0.40, HEAD_TILT_MAX))
    else:
        rng = np.random.default_rng([int(seed), 432, int(attempt), ("up", "down").index(look)])
        tilt = float(rng.uniform(*LOOK[look]))
    pan = float(rng.uniform(-HEAD_PAN_RANGE, HEAD_PAN_RANGE))
    return {"tilt": _r(tilt), "pan": _r(pan), "random": True, "attempt": int(attempt), "look": look}


def _node_ids(x, out: set) -> set:
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "node" and isinstance(v, str):
                out.add(v)
            else:
                _node_ids(v, out)
    elif isinstance(x, (list, tuple)):
        for v in x:
            _node_ids(v, out)
    return out


def look_of(ep: dict, scene: dict) -> str:
    """Head look mode of an episode: "up" when a node it uses is above eye level (place_class high), else "down"
    when one is low, else "std"."""
    cls = {n["id"]: n.get("place_class", "desk") for n in scene.get("nodes", [])}
    used = {cls.get(i, "desk") for i in _node_ids(ep, set())}
    return "up" if "high" in used else "down" if "low" in used else "std"


def head_default() -> dict:
    return {"tilt": HEAD_TILT0, "pan": 0.0, "random": False, "fallback": True}


UV_SCALE = (0.4, 3.0)  # texture tiles per metre (box-projected UVs are in metres) [hypothesis]
TINT_P = {"furniture": 0.5, "wall": 0.6, "fabric": 0.6, "floor": 0.3}  # share of tinted slots per material role
TINT_SAT = (0.05, 0.35)


def material_look(vseed: int, slot: int, role: str) -> dict:
    """Per-slot appearance draw on top of the texture choice: UV scale (log-uniform in UV_SCALE) and a diffuse tint
    (UsdUVTexture scale; 1,1,1 = none) -> {uv, tint}. Seeded by (visual seed, slot)."""
    rng = np.random.default_rng([int(vseed), 937, int(slot)])
    uv = float(math.exp(rng.uniform(math.log(UV_SCALE[0]), math.log(UV_SCALE[1]))))
    tint = [1.0, 1.0, 1.0]
    if rng.random() < TINT_P.get(role, 0.4):
        tint = _tint(rng, TINT_SAT)
        v = float(rng.uniform(0.75, 1.0))  # also a little darker / lighter
        tint = [_r(min(1.0, c * v), 3) for c in tint]
    return {"uv": _r(uv, 3), "tint": tint}


UNREAL_P = 0.0  # production default: off (spec §5; later_problems 22)
UNREAL_STYLES = ("flat_colour", "loud_colour", "pattern", "inverted_light")


def unreal_style(seed: int, p: float = UNREAL_P):
    """None (realistic) or one unrealistic style name; off by default."""
    rng = np.random.default_rng([int(seed), 433])
    if rng.random() >= p:
        return None
    return UNREAL_STYLES[int(rng.integers(len(UNREAL_STYLES)))]


COMBO_KEYS = ("room", "furniture", "materials", "light_family", "hdr", "robot_pose", "head_pose")


def combo_hash(rec: dict) -> str:
    """Hash of the environment combination (spec §0 user rule): room, furniture set (asset ids + parametric spec),
    materials, light family, HDRI, robot pose (distance / yaw, 1 cm / 1 deg) and head pose (1 deg)."""
    missing = [k for k in COMBO_KEYS if k not in rec]
    if missing:
        raise KeyError(f"combo record lacks {missing}")
    return hashlib.sha256(json.dumps({k: rec[k] for k in COMBO_KEYS}, sort_keys=True, default=str).encode()).hexdigest()[:20]


def pose_key(robot_pose: dict, head: dict) -> tuple:
    """Rounded (robot distance cm, robot yaw deg) and (head tilt deg, pan deg) for combo_hash."""
    return ([round(robot_pose["distance"] * 100), round(math.degrees(robot_pose["yaw"]))],
            [round(math.degrees(head["tilt"])), round(math.degrees(head["pan"]))])


class ComboLedger:
    """Append-only file of used combination hashes (one per line). A lane loads every ledger of the run, so a repeat
    anywhere in the run is redrawn (seen / add)."""

    def __init__(self, path: str, others=()):
        import os
        self.path = path
        self.seen_set = set()
        for p in (path, *others):
            if os.path.exists(p):
                self.seen_set |= {ln.strip() for ln in open(p) if ln.strip()}

    def seen(self, h: str) -> bool:
        return h in self.seen_set

    def add(self, h: str) -> None:
        if h in self.seen_set:
            raise ValueError(f"combo {h} already used")
        self.seen_set.add(h)
        with open(self.path, "a") as f:
            f.write(h + "\n")


COLOUR_WORDS = ("red", "orange", "yellow", "green", "blue", "purple", "pink", "brown", "black", "white", "grey",
                "gray", "magenta", "cyan")


def keep_named_colours(instruction: str, names: dict) -> set:
    """Object ids whose colour is named in the instruction (their look may not change, L8S rule; unreal mode too)."""
    low = instruction.lower()
    return {k for k, n in names.items() if n.lower() in low and any(c in n.lower().split() for c in COLOUR_WORDS)}
