"""5-axis scene randomization for the v2 Isaac scene: variant 'random' (TEST pool, evaluation only) and 'dr'
(TRAIN pool, training-time domain randomization). canon 00-interfaces §34 D35 / §52 decision 2, EVAL §2.1.

Axes (RoboDojo definition, EVAL-evaluation-design.md §2.1): tabletop distractors, table material, floor material,
lighting (type, intensity, colour temperature), HDR background. The base layout (mug, tray, o8/o9) stays the
seed's standard layout (paired standard/random/dr per seed); the five axes are drawn deterministically from the
seed out of randomization_pools.json. The TEST and TRAIN pools share no asset and no numeric band (tests).

Pure part (sampling, keep-out placement, metadata) imports without Isaac and is unit-tested locally.
Isaac part (distractor rigid bodies, materials, floor, lights) imports Isaac lazily (pod only). Physics: only the
distractors' own colliders are added; robot, cameras, table, mug/tray/o8-o10 are untouched.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .perturb import P2_LATERAL_M
from .scene import OBJ_GEOM, TABLE_CENTER_XY, TABLE_SIZE, TABLE_TOP_Z, sample_layout, yaw_quat

POOLS_PATH = Path(__file__).with_name("randomization_pools.json")
VARIANTS = ("standard", "random", "dr")
VARIANT_POOL = {"random": "test", "dr": "train"}
META_SCHEMA = "qdd.randomization/v1"
_VCODE = {"random": 1, "dr": 2}
_AXIS = {"table": 1, "floor": 2, "hdr": 3, "light": 4, "distractors": 5}
_POOLS_CACHE: dict = {}


# ------------------------------------------------------------------------------------------------ pure part
def load_pools(path=POOLS_PATH) -> dict:
    key = str(path)
    if key not in _POOLS_CACHE:
        with open(path, encoding="utf-8") as f:
            _POOLS_CACHE[key] = json.load(f)
    return _POOLS_CACHE[key]


def pools_digest(pools: dict) -> str:
    return hashlib.sha256(json.dumps(pools, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def check_variant(variant: str) -> str:
    if variant not in VARIANTS:
        raise ValueError(f"variant {variant!r}: one of {VARIANTS}")
    return variant


def check_train_variant(variant: str) -> str:
    """Training data may use 'standard' or 'dr' only: random test scenes are never used for training (D35)."""
    check_variant(variant)
    if variant == "random":
        raise ValueError("variant 'random' is the TEST pool: never used for training (canon §34 D35); use 'dr'")
    return variant


def _rng(seed: int, variant: str, axis: str):
    return np.random.default_rng([int(seed), 31, _VCODE[variant], _AXIS[axis]])


def _band(rng, bands) -> float:
    w = np.array([b - a for a, b in bands], float)
    i = int(rng.choice(len(bands), p=w / w.sum()))
    return float(rng.uniform(*bands[i]))


def distractor_geom(d: dict, pools: dict) -> dict:
    """dims (x, y, z) m in the table frame, footprint_r (xy bounding radius), half_height; meshes: fit scale."""
    k = d["kind"]
    out = {}
    if k == "mesh":
        c = pools["common"]
        e = d["extent_m"]
        s = min(c["mesh_fit_max_xy_m"] / max(e[0], e[1]), c["mesh_fit_max_z_m"] / e[2])
        dims = [e[0] * s, e[1] * s, e[2] * s]
        out["fit_scale"] = s
    elif k == "sphere":
        dims = [2 * d["radius"]] * 3
    elif k == "cone" or k == "cylinder":
        dims = [2 * d["radius"], 2 * d["radius"], d["height"]]
    elif k == "capsule":
        dims = [2 * d["radius"], 2 * d["radius"], d["height"] + 2 * d["radius"]]
    elif k == "cuboid":
        dims = list(d["size"])
    else:
        raise ValueError(k)
    fr = math.hypot(dims[0], dims[1]) / 2 if k in ("mesh", "cuboid") else d["radius"]
    out.update(dims=[float(v) for v in dims], footprint_r=float(fr), half_height=float(dims[2] / 2))
    return out


def _seg_dist(p, a, b) -> float:
    p, a, b = (np.asarray(v, float) for v in (p, a, b))
    u = b - a
    t = float(np.clip(np.dot(p - a, u) / max(float(np.dot(u, u)), 1e-12), 0.0, 1.0))
    return float(np.linalg.norm(p - (a + t * u)))


def placement_ok(xy, r: float, layout: dict, placed: list, common: dict, path=("o3", "o5")) -> bool:
    """Keep-out for one random distractor of footprint radius r at xy:
    - on the table (edge margin) and inside the placement box;
    - outside the planner path + P2 spawn band: the mug->tray segment (P2 spawns beside it, perturb.p2_spawn_xy)
      widened by P2_LATERAL_M[1] + o10 footprint + r + margin (P1's 2 cm shift of the mug is inside the band);
    - clear of every layout object (mug, tray, o8, o9) and of the distractors already placed.
    path = (target, place) of the task (tasks.py); the default is the mug -> tray task."""
    x, y = xy
    em = common["table_edge_margin_m"]
    x0, x1 = TABLE_CENTER_XY[0] - TABLE_SIZE[0] / 2, TABLE_CENTER_XY[0] + TABLE_SIZE[0] / 2
    y0, y1 = TABLE_CENTER_XY[1] - TABLE_SIZE[1] / 2, TABLE_CENTER_XY[1] + TABLE_SIZE[1] / 2
    if not (x0 + r + em <= x <= x1 - r - em and y0 + r + em <= y <= y1 - r - em):
        return False
    if not (common["place_x"][0] <= x <= common["place_x"][1] and common["place_y"][0] <= y <= common["place_y"][1]):
        return False
    band = P2_LATERAL_M[1] + OBJ_GEOM["o10"]["footprint_r"] + r + common["keepout_margin_m"]
    for a, b in (path if isinstance(path[0], (tuple, list)) else (path,)):  # several paths: tasks.PAIR_PATHS
        if _seg_dist(xy, layout[a][:2], layout[b][:2]) < band:
            return False
    for k, p in layout.items():
        if math.dist(xy, p[:2]) < OBJ_GEOM[k]["footprint_r"] + r + common["object_clearance_m"]:
            return False
    return all(math.dist(xy, e["xy"]) >= e["footprint_r"] + r + common["distractor_clearance_m"] for e in placed)


def look_at_quat(pos, target) -> tuple:
    """(w, x, y, z) rotating the local -Z axis (USD light emission direction) onto target - pos."""
    z = np.asarray(pos, float) - np.asarray(target, float)
    z /= np.linalg.norm(z)
    up = np.array([0.0, 0.0, 1.0])
    if np.linalg.norm(np.cross(up, z)) < 1e-6:
        up = np.array([1.0, 0.0, 0.0])
    x = np.cross(up, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    m = np.stack([x, y, z], axis=1)  # columns = local axes in world
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = 2.0 * math.sqrt(tr + 1.0)
        q = (0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s)
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = 2.0 * math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2])
        q = ((m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s)
    elif m[1, 1] > m[2, 2]:
        s = 2.0 * math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2])
        q = ((m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s)
    else:
        s = 2.0 * math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1])
        q = ((m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s)
    q = np.array(q)
    q /= np.linalg.norm(q)
    return tuple(float(v) for v in q)


def _r(v, n=4):
    return round(float(v), n)


def sample_randomization(seed: int, variant: str, layout: dict | None = None, pools: dict | None = None,
                         path=("o3", "o5")) -> dict:
    """The five axes for (seed, variant). 'standard' -> no randomization (metadata only). Deterministic: every axis
    has its own RNG stream from (seed, variant, axis); nothing depends on earlier episodes of the process."""
    check_variant(variant)
    meta = {"schema": META_SCHEMA, "seed": int(seed), "variant": variant, "pool": VARIANT_POOL.get(variant),
            "pools_digest": None, "table_material": None, "floor_material": None, "light": None, "hdr": None,
            "distractors": None}
    if variant == "standard":
        return meta
    pools = pools or load_pools()
    layout = layout if layout is not None else sample_layout(seed)
    c, pool = pools["common"], pools["pools"][VARIANT_POOL[variant]]
    meta["pools_digest"] = pools_digest(pools)

    rng = _rng(seed, variant, "table")
    meta["table_material"] = dict(pool["table_materials"][int(rng.integers(len(pool["table_materials"])))])
    rng = _rng(seed, variant, "floor")
    meta["floor_material"] = dict(pool["floor_materials"][int(rng.integers(len(pool["floor_materials"])))])

    rng = _rng(seed, variant, "hdr")
    h = pool["hdr_maps"][int(rng.integers(len(pool["hdr_maps"])))]
    mult = _band(rng, pool["light"]["dome_mult_bands"])
    meta["hdr"] = {"name": h["name"], "file": h["file"], "intensity_mult": _r(mult),
                   "intensity": _r(h["base_intensity"] * c["dome_weight"] * mult, 2),
                   "rotation_deg": _r(rng.uniform(*pool["light"]["dome_rotation_deg"]), 2)}

    rng = _rng(seed, variant, "light")
    types = sorted(c["light_types"])
    lt = types[int(rng.integers(len(types)))]
    mult = _band(rng, pool["light"]["key_mult_bands"])
    ct = _band(rng, pool["light"]["color_temperature_bands_k"])
    az = _band(rng, pool["light"]["azimuth_bands_deg"])
    el = float(rng.uniform(*c["light_elevation_deg"]))
    dist = float(rng.uniform(*c["light_distance_m"]))
    tgt = np.asarray(c["light_target"], float)
    ca, sa, ce, se = math.cos(math.radians(az)), math.sin(math.radians(az)), math.cos(math.radians(el)), \
        math.sin(math.radians(el))
    pos = tgt + dist * np.array([ce * ca, ce * sa, se])
    meta["light"] = {"type": lt, "intensity_mult": _r(mult),
                     "intensity": _r(c["light_types"][lt]["base_intensity"] * c["key_weight"] * mult, 2),
                     "color_temperature_k": _r(ct, 1), "azimuth_deg": _r(az, 3), "elevation_deg": _r(el, 3),
                     "distance_m": _r(dist), "pos": [_r(v) for v in pos], "target": [_r(v) for v in tgt],
                     "quat_wxyz": [_r(v, 6) for v in look_at_quat(pos, tgt)],
                     "shape": {k: v for k, v in c["light_types"][lt].items() if k != "base_intensity"}}

    rng = _rng(seed, variant, "distractors")
    dists = pool["distractors"]
    n = int(rng.integers(c["n_distractors"][0], c["n_distractors"][1] + 1))
    order = [int(i) for i in rng.permutation(len(dists))]
    placed, dropped = [], []
    cols = pool["distractor_colors"]
    for i in order[:n]:
        d = dists[i]
        g = distractor_geom(d, pools)
        col = None if d.get("has_material") else cols[int(rng.integers(len(cols)))]["name"]
        for _ in range(3000):
            xy = (float(rng.uniform(*c["place_x"])), float(rng.uniform(*c["place_y"])))
            if placement_ok(xy, g["footprint_r"], layout, placed, c, path):
                placed.append({"name": d["name"], "kind": d["kind"], "xy": [_r(xy[0], 5), _r(xy[1], 5)],
                               "yaw": _r(rng.uniform(-math.pi, math.pi), 5), "footprint_r": _r(g["footprint_r"], 5),
                               "height": _r(g["dims"][2], 5), "half_height": _r(g["half_height"], 5),
                               "dims": [_r(v, 5) for v in g["dims"]], "color": col})
                break
        else:
            dropped.append(d["name"])
    meta["distractors"] = placed
    if dropped:
        meta["distractors_dropped"] = dropped
    return meta


_REQ = {"light": ("type", "intensity", "intensity_mult", "color_temperature_k", "pos", "elevation_deg",
                  "azimuth_deg", "distance_m"),
        "hdr": ("name", "file", "intensity", "intensity_mult", "rotation_deg"),
        "distractor": ("name", "kind", "xy", "yaw", "footprint_r", "height", "half_height", "color")}


def validate_meta(m: dict) -> list:
    """Problems with an episode's randomization metadata ([] = valid)."""
    bad = []
    for k in ("schema", "seed", "variant", "pool", "pools_digest", "table_material", "floor_material", "light",
              "hdr", "distractors"):
        if k not in m:
            bad.append(f"missing {k}")
    if bad:
        return bad
    if m["schema"] != META_SCHEMA:
        bad.append("schema")
    if m["variant"] not in VARIANTS:
        return bad + ["variant"]
    if m["pool"] != VARIANT_POOL.get(m["variant"]):
        bad.append("pool/variant mismatch")
    if m["variant"] == "standard":
        return bad + [f"{k} set" for k in ("table_material", "floor_material", "light", "hdr", "distractors")
                      if m[k] is not None]
    for ax in ("table_material", "floor_material"):
        if not isinstance(m[ax], dict) or "name" not in m[ax]:
            bad.append(ax)
    for ax in ("light", "hdr"):
        if not isinstance(m[ax], dict):
            bad.append(ax)
            continue
        bad += [f"{ax}.{k}" for k in _REQ[ax] if k not in m[ax]]
    if not isinstance(m["distractors"], list):
        bad.append("distractors")
    else:
        for d in m["distractors"]:
            bad += [f"distractor.{k}" for k in _REQ["distractor"] if k not in d]
    return bad


# ------------------------------------------------------------------------------------------------ Isaac (pod)
# Rule learned on the pod (2026-09-24 UTC): never change a material *binding* on a rigid-body prim after the sim has
# started -- omni.physx re-parses the prim and the body jumps back to its USD (parked) pose. Every material that
# changes per seed is therefore bound once at spawn time (before physics starts) and later only its shader
# inputs are edited (texture / colour / roughness / metallic).
ROOT = "/World/QddRand"
ENV0 = "/World/envs/env_0"
MAT = "Looks/QddMat"  # per-prim OmniPBR material path suffix (table, each distractor)
_RD_SPECS: dict = {}  # prim name -> spawn spec (read by spawn_rd; cfgs get deep-copied, so no closures)
MESH_FIT: dict = {}  # prim path -> measured mesh fit (logged)


def pool_of(variant: str, pools: dict | None = None) -> dict:
    pools = pools or load_pools()
    return pools["pools"][VARIANT_POOL[variant]]


def distractor_scene_cfgs(variant: str) -> dict:
    """{scene key 'rd_<name>': RigidObjectCfg} for every distractor of the variant's pool, parked off-table behind
    the robot (x -3.0.., y 3.6, out of every camera view) until a seed puts it on the table at reset."""
    import isaaclab.sim as sim_utils
    from isaaclab.assets import RigidObjectCfg

    pools = load_pools()
    c = pools["common"]
    out = {}
    for i, d in enumerate(pool_of(variant, pools)["distractors"]):
        g = distractor_geom(d, pools)
        common = dict(
            rigid_props=sim_utils.RigidBodyPropertiesCfg(max_depenetration_velocity=1.0),
            mass_props=sim_utils.MassPropertiesCfg(mass=c["distractor_mass_kg"]),
            collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.004, rest_offset=0.0),
            physics_material=sim_utils.RigidBodyMaterialCfg(static_friction=c["distractor_friction"],
                                                            dynamic_friction=c["distractor_friction"],
                                                            restitution=0.0),
            func=spawn_rd,
        )
        k = d["kind"]
        _RD_SPECS["RD_" + d["name"]] = {"kind": k, "usd": d.get("usd"), "up": d.get("up"), "dims": g["dims"],
                                        "own_material": bool(d.get("has_material"))}
        if k == "mesh":
            spawn = sim_utils.CuboidCfg(size=tuple(g["dims"]), **common)
        elif k == "sphere":
            spawn = sim_utils.SphereCfg(radius=d["radius"], **common)
        elif k == "cone":
            spawn = sim_utils.ConeCfg(radius=d["radius"], height=d["height"], axis="Z", **common)
        elif k == "capsule":
            spawn = sim_utils.CapsuleCfg(radius=d["radius"], height=d["height"], axis="Z", **common)
        elif k == "cylinder":
            spawn = sim_utils.CylinderCfg(radius=d["radius"], height=d["height"], axis="Z", **common)
        elif k == "cuboid":
            spawn = sim_utils.CuboidCfg(size=tuple(d["size"]), **common)
        else:
            raise ValueError(k)
        out["rd_" + d["name"]] = RigidObjectCfg(
            prim_path="{ENV_REGEX_NS}/RD_" + d["name"], spawn=spawn,
            init_state=RigidObjectCfg.InitialStateCfg(pos=(-3.0 - 0.3 * i, 3.6, g["half_height"] + 0.001)))
    return out


def _base_spawner(kind: str):
    from isaaclab.sim.spawners import shapes
    return {"mesh": shapes.spawn_cuboid, "cuboid": shapes.spawn_cuboid, "sphere": shapes.spawn_sphere,
            "cone": shapes.spawn_cone, "capsule": shapes.spawn_capsule, "cylinder": shapes.spawn_cylinder}[kind]


def _bind_new_material(stage, prim_path: str, target: str):
    """OmniPBR at <prim_path>/Looks/QddMat bound (strongest) to target -- spawn time only."""
    import isaaclab.sim as sim_utils
    mat = f"{prim_path}/{MAT}"
    _omnipbr(stage, mat, {"color": (0.5, 0.5, 0.5), "roughness": 0.5})
    sim_utils.bind_visual_material(target, mat, stage=stage, stronger_than_descendants=True)
    return mat


def spawn_rd(prim_path, cfg, translation=None, orientation=None, **kwargs):
    """Distractor spawner (runs inside InteractiveScene, before physics starts). Primitive: the Isaac Lab shape
    (own collider) + its own OmniPBR material. Mesh: an invisible cuboid collider + the bundled mesh referenced as
    a visual child, fitted into the collider box (scale from the bound measured after referencing, so unit and
    up-axis handling is checked), + its own OmniPBR material unless the asset brings one."""
    import omni.usd
    from pxr import Usd, UsdGeom

    path = prim_path.replace("env_.*", "env_0")
    spec = _RD_SPECS[path.rsplit("/", 1)[1]]
    prim = _base_spawner(spec["kind"])(path, cfg, translation=translation, orientation=orientation, **kwargs)
    stage = omni.usd.get_context().get_stage()
    if spec["kind"] != "mesh":
        _bind_new_material(stage, path, path + "/geometry")
        return prim
    for p in Usd.PrimRange(stage.GetPrimAtPath(path + "/geometry")):
        if p.GetTypeName() in ("Cube", "Mesh"):
            UsdGeom.Imageable(p).MakeInvisible()  # the collider box
    vis = UsdGeom.Xform.Define(stage, path + "/visual")
    asset = stage.DefinePrim(path + "/visual/asset")  # typeless: the referenced default prim's type wins (a Mesh
    # default prim under an Xform-typed prim lost its geometry: shoes/cap bbox came out empty)
    asset.GetReferences().AddReference(spec["usd"])
    units_ops = [n for n in asset.GetPropertyNames() if "unitsResolve" in n]
    rot = spec["up"] == "Y" and not any("rotate" in n for n in units_ops)
    if rot:
        vis.AddRotateXOp().Set(90.0)
    bb = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeRelativeBound(
        asset, stage.GetPrimAtPath(path))
    rg = bb.ComputeAlignedRange()
    lo, hi = np.array(rg.GetMin()), np.array(rg.GetMax())
    size, ctr = hi - lo, (hi + lo) / 2
    s = float(min(spec["dims"][i] / max(size[i], 1e-9) for i in range(3)))
    vis.ClearXformOpOrder()
    vis.AddTranslateOp().Set(tuple(float(v) for v in -ctr * s))
    if rot:
        vis.AddRotateXOp().Set(90.0)
    vis.AddScaleOp().Set((s, s, s))
    if not spec["own_material"]:
        _bind_new_material(stage, path, path + "/visual")
    MESH_FIT[path] = {"measured_size": [round(float(v), 5) for v in size], "scale": round(s, 6),
                      "fitted_dims": [round(float(v) * s, 4) for v in size], "target_dims": spec["dims"],
                      "units_resolve_ops": units_ops, "rotated_y_up": rot}
    return prim


def spawn_table_rand(prim_path, cfg, translation=None, orientation=None, **kwargs):
    """The standard table (same cuboid, collider, friction, pose) + its own OmniPBR material bound at spawn."""
    import omni.usd
    from isaaclab.sim.spawners.shapes import spawn_cuboid

    path = prim_path.replace("env_.*", "env_0")
    prim = spawn_cuboid(path, cfg, translation=translation, orientation=orientation, **kwargs)
    _bind_new_material(omni.usd.get_context().get_stage(), path, path)
    return prim


def randomized_table_cfg(table_cfg):
    """random/dr: the table cfg with only its spawn function swapped (spawn_table_rand)."""
    return table_cfg.replace(spawn=table_cfg.spawn.replace(func=spawn_table_rand))


def _omnipbr(stage, path: str, m: dict):
    import omni.kit.commands

    omni.kit.commands.execute("CreateMdlMaterialPrim", mtl_url="OmniPBR.mdl", mtl_name="OmniPBR", mtl_path=path,
                              select_new_prim=False)
    set_material(stage, path, m)
    return path


def set_material(stage, path: str, m: dict) -> None:
    """Shader-input edit of an OmniPBR material: texture (world-projected) or plain colour, roughness, metallic."""
    from pxr import Gf, Sdf, UsdShade

    sh = UsdShade.Shader(stage.GetPrimAtPath(path + "/Shader"))
    V = Sdf.ValueTypeNames
    tex = m.get("texture", "")
    sh.CreateInput("diffuse_texture", V.Asset).Set(Sdf.AssetPath(tex))
    sh.CreateInput("project_uvw", V.Bool).Set(bool(tex))
    sh.CreateInput("world_or_object", V.Bool).Set(True)
    sh.CreateInput("texture_scale", V.Float2).Set(Gf.Vec2f(*m.get("texture_scale", (1.0, 1.0))))
    sh.CreateInput("diffuse_color_constant", V.Color3f).Set(Gf.Vec3f(*m.get("color", (1.0, 1.0, 1.0))))
    sh.CreateInput("reflection_roughness_constant", V.Float).Set(float(m.get("roughness", 0.5)))
    sh.CreateInput("metallic_constant", V.Float).Set(float(m.get("metallic", 0.0)))


def _set_pose(prim, pos=None, quat_wxyz=None):
    from pxr import Gf, UsdGeom

    xf = UsdGeom.Xformable(prim)
    ops = {op.GetOpType(): op for op in xf.GetOrderedXformOps()}
    if pos is not None:
        op = ops.get(UsdGeom.XformOp.TypeTranslate) or xf.AddTranslateOp()
        op.Set(Gf.Vec3d(*pos) if op.GetPrecision() == UsdGeom.XformOp.PrecisionDouble else Gf.Vec3f(*pos))
    if quat_wxyz is not None:
        op = ops.get(UsdGeom.XformOp.TypeOrient) or xf.AddOrientOp()
        w, x, y, z = (float(v) for v in quat_wxyz)
        op.Set(Gf.Quatd(w, x, y, z) if op.GetPrecision() == UsdGeom.XformOp.PrecisionDouble else Gf.Quatf(w, x, y, z))


LIGHT_TYPES = ("sphere", "disk", "rect", "cylinder", "distant")


def setup_visuals(env) -> dict:
    """Once per env (no physics prim touched): the floor slab with its material, one key light per type (off),
    the grid ground's visual mesh hidden (its collision plane stays), render-side sync loads."""
    import carb
    import isaaclab.sim as sim_utils
    import omni.usd
    from pxr import UsdGeom, UsdLux

    stage = omni.usd.get_context().get_stage()
    c = load_pools()["common"]
    s = carb.settings.get_settings()
    for k in ("/rtx/materialDb/syncLoads", "/rtx/hydra/materialSyncLoads", "/omni.kit.plugin/syncUsdLoads"):
        s.set(k, True)  # render-side only: finish MDL/texture loads before a frame is produced
    UsdGeom.Scope.Define(stage, ROOT)
    fl = c["floor"]
    cube = UsdGeom.Cube.Define(stage, ROOT + "/Floor")  # visual only: no collision API
    cube.GetSizeAttr().Set(1.0)
    xf = UsdGeom.Xformable(cube)
    xf.AddTranslateOp().Set((fl["center_xy"][0], fl["center_xy"][1], -fl["thickness_m"] / 2))
    xf.AddScaleOp().Set((fl["size_m"][0], fl["size_m"][1], fl["thickness_m"]))
    _omnipbr(stage, ROOT + "/FloorMat", {"color": (0.5, 0.5, 0.5)})
    sim_utils.bind_visual_material(ROOT + "/Floor", ROOT + "/FloorMat", stage=stage, stronger_than_descendants=True)
    grid = stage.GetPrimAtPath("/World/GroundPlane/Environment")
    if grid.IsValid():
        UsdGeom.Imageable(grid).MakeInvisible()
    for t in LIGHT_TYPES:
        p = f"{ROOT}/Key_{t}"
        sh = c["light_types"][t]
        if t == "sphere":
            lt = UsdLux.SphereLight.Define(stage, p)
            lt.CreateRadiusAttr(sh["radius"])
        elif t == "disk":
            lt = UsdLux.DiskLight.Define(stage, p)
            lt.CreateRadiusAttr(sh["radius"])
        elif t == "rect":
            lt = UsdLux.RectLight.Define(stage, p)
            lt.CreateWidthAttr(sh["width"])
            lt.CreateHeightAttr(sh["height"])
        elif t == "cylinder":
            lt = UsdLux.CylinderLight.Define(stage, p)
            lt.CreateLengthAttr(sh["length"])
            lt.CreateRadiusAttr(sh["radius"])
        else:
            lt = UsdLux.DistantLight.Define(stage, p)
            lt.CreateAngleAttr(sh["angle"])
        UsdLux.LightAPI(lt).CreateIntensityAttr(0.0)  # off = intensity 0 (visibility toggles are not rendered
        # reliably: a light made invisible and visible again stopped lighting on the pod, dbg 2026-09-24 UTC)
        _set_pose(lt.GetPrim(), (0.0, 0.0, 3.0), (1.0, 0.0, 0.0, 0.0))
    return {"root": ROOT}


def apply_visuals(env, meta: dict) -> None:
    """Per-seed visual state: shader inputs, light attributes and light/dome transforms only (no binding change,
    no physics write)."""
    import omni.usd
    from pxr import Gf, Sdf, UsdLux

    stage = omni.usd.get_context().get_stage()
    set_material(stage, f"{ENV0}/Table/{MAT}", meta["table_material"])
    set_material(stage, ROOT + "/FloorMat", meta["floor_material"])
    cols = {c["name"]: c["color"] for c in pool_of(meta["variant"])["distractor_colors"]}
    for d in meta["distractors"]:
        if d["color"] is not None:
            set_material(stage, f"{ENV0}/RD_{d['name']}/{MAT}", {"color": cols[d["color"]], "roughness": 0.5})
    h = meta["hdr"]
    dome = UsdLux.DomeLight(stage.GetPrimAtPath("/World/light"))
    dome.CreateTextureFileAttr().Set(Sdf.AssetPath(h["file"]))
    dome.CreateTextureFormatAttr().Set(UsdLux.Tokens.latlong)
    dome.CreateIntensityAttr().Set(float(h["intensity"]))
    dome.CreateColorAttr().Set(Gf.Vec3f(1.0, 1.0, 1.0))
    a = math.radians(h["rotation_deg"])
    _set_pose(dome.GetPrim(), None, (math.cos(a / 2), 0.0, 0.0, math.sin(a / 2)))
    L = meta["light"]
    for t in LIGHT_TYPES:
        prim = stage.GetPrimAtPath(f"{ROOT}/Key_{t}")
        api = UsdLux.LightAPI(prim)
        if t != L["type"]:
            api.GetIntensityAttr().Set(0.0)
            continue
        api.GetIntensityAttr().Set(float(L["intensity"]))
        api.CreateEnableColorTemperatureAttr().Set(True)
        api.CreateColorTemperatureAttr().Set(float(L["color_temperature_k"]))
        _set_pose(prim, L["pos"], L["quat_wxyz"])


def write_distractor_poses(env, env_ids, meta) -> None:
    """Reset event part: put this seed's distractors on the table (one pose write each). The others stay where
    reset_scene_to_default put them (parked)."""
    import torch

    if not meta or not meta.get("distractors"):
        return
    for d in meta["distractors"]:
        o = env.scene["rd_" + d["name"]]
        p = torch.tensor([[d["xy"][0], d["xy"][1], TABLE_TOP_Z + d["half_height"] + 0.001, *yaw_quat(d["yaw"])]],
                         dtype=torch.float32, device=env.device)
        p[:, :3] += env.scene.env_origins[env_ids]
        o.write_root_pose_to_sim(p, env_ids=env_ids)
        o.write_root_velocity_to_sim(torch.zeros((len(env_ids), 6), device=env.device), env_ids=env_ids)


def distractor_positions(env) -> dict:
    meta = getattr(env, "randomization", None) or {}
    out = {}
    for d in meta.get("distractors") or []:
        o = env.scene["rd_" + d["name"]]
        out[d["name"]] = (o.data.root_pos_w[0] - env.scene.env_origins[0]).cpu().numpy()
    return out


def distractor_report(env, ref: dict | None = None) -> dict:
    """mm offsets of each distractor: vs the sampled spawn pose (ref None) or vs ref positions."""
    meta = getattr(env, "randomization", None) or {}
    pos = distractor_positions(env)
    out = {}
    for d in meta.get("distractors") or []:
        p = pos[d["name"]]
        if ref is None:
            q = np.array([d["xy"][0], d["xy"][1], TABLE_TOP_Z + d["half_height"]])
        else:
            q = ref[d["name"]]
        out[d["name"]] = {"dxy_mm": round(float(np.linalg.norm(p[:2] - q[:2])) * 1e3, 1),
                          "dz_mm": round(float(p[2] - q[2]) * 1e3, 1)}
    return out
