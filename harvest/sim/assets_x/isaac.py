"""Pod only (Isaac Lab): spawn a furniture.sample_scene dict into an env as STATIC colliders.

Slots: the scene cfg gets N_SLOTS unit cuboids (collider + own OmniPBR material bound at spawn) and one prim per
licensed mesh asset (its static copy, usd_import.make_static), all parked far below the floor. author_scene() then
writes, while the sim runs, each part's USD pose / scale (cuboid slot: scale of the size-1 cube = the part size)
and colour. The NEXT env.reset() with hard_reset=True (the default) stops the timeline and rebuilds the PhysX scene
from USD, so the new furniture exists physically from that reset on -- furniture kind, size and pose can change
per episode inside one Isaac process (no per-bucket restart). Never call author_scene between reset and the end
of an episode.
without_table(): wraps harvest.sim.scene._build_cfg (monkeypatch in the calling process only; scene.py unchanged)
to drop the L8 table and add the slots.
"""
from __future__ import annotations

import numpy as np

N_SLOTS = 28
PARK = (-6.0, -6.0, -4.0)  # below the ground plane, outside every camera
ROOM_PARK = (-30.0, 30.0, -10.0)  # rooms: far away and below the ground plane
ROOT = "/World/envs/env_0"


def _slot_path(i):
    return f"{ROOT}/FX_{i}"


def _mesh_path(name):
    return f"{ROOT}/FM_{name}"


_FACES = (  # unit cube faces: (normal axis, sign) -> 4 corners counter-clockwise seen from outside
    (0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1))


def _cube_faces():
    """24 vertices (4 per face, -0.5..0.5), 6 quads, per-vertex normals and the two in-face axes per face."""
    P, N, axes = [], [], []
    for ax, sg in _FACES:
        u, v = ((1, 2), (2, 0), (0, 1))[ax]  # u x v = +ax: counter-clockwise seen from outside
        if sg < 0:
            u, v = v, u
        for cu, cv in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)):
            p = [0.0, 0.0, 0.0]
            p[ax], p[u], p[v] = 0.5 * sg, cu, cv
            P.append(p)
            n = [0.0, 0.0, 0.0]
            n[ax] = float(sg)
            N.append(n)
        axes.append((u, v))
    return P, N, axes


def box_uv(size) -> list:
    """Box-projected UVs (metres) of the unit visual cube scaled to `size`: on each face the two in-face axes x the
    part size, so a texture tiles by metre whatever the part size (materials.author uv_scale = tiles per metre)."""
    P, _, axes = _cube_faces()
    st = []
    for f, (u, v) in enumerate(axes):
        for k in range(4):
            p = P[4 * f + k]
            st.append((float((p[u] + 0.5) * size[u]), float((p[v] + 0.5) * size[v])))
    return st


def _add_visual_cube(stage, path: str) -> None:
    """Render mesh with UVs next to the collider cube (b4 textures: UsdGeom.Cube has no primvars:st, so a texture
    showed one average colour); the collider cube is made invisible and keeps its size / collider (physics
    unchanged). author_scene scales both and refreshes the UVs to the part size."""
    from pxr import Sdf, UsdGeom, Vt
    P, N, _ = _cube_faces()
    m = UsdGeom.Mesh.Define(stage, path + "/geometry/visual")
    m.CreatePointsAttr(Vt.Vec3fArray([tuple(p) for p in P]))
    m.CreateFaceVertexCountsAttr(Vt.IntArray([4] * 6))
    m.CreateFaceVertexIndicesAttr(Vt.IntArray(list(range(24))))
    m.CreateNormalsAttr(Vt.Vec3fArray([tuple(n) for n in N]))
    m.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    pv = UsdGeom.PrimvarsAPI(m).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex)
    pv.Set(Vt.Vec2fArray(box_uv((1.0, 1.0, 1.0))))
    UsdGeom.Imageable(stage.GetPrimAtPath(path + "/geometry/mesh")).MakeInvisible()


def spawn_fx(prim_path, cfg, translation=None, orientation=None, **kwargs):
    """Unit cuboid (Isaac Lab shape: collider on geometry/mesh, made invisible) + a UV render mesh
    (geometry/visual) + its own OmniPBR material, bound at spawn."""
    import omni.usd
    from isaaclab.sim.spawners.shapes import spawn_cuboid

    from ..randomize import _bind_new_material
    path = prim_path.replace("env_.*", "env_0")
    prim = spawn_cuboid(path, cfg, translation=translation, orientation=orientation, **kwargs)
    stage = omni.usd.get_context().get_stage()
    _add_visual_cube(stage, path)
    _bind_new_material(stage, path, path)
    return prim


def _set_visual(stage, i: int, size) -> None:
    """Scale the slot's UV mesh like its collider and refresh its UVs to the part size (render only)."""
    from pxr import UsdGeom, Vt
    vis = stage.GetPrimAtPath(_slot_path(i) + "/geometry/visual")
    if not vis:
        return
    _set_scale(vis, size)
    UsdGeom.PrimvarsAPI(vis).GetPrimvar("st").Set(Vt.Vec2fArray(box_uv(size)))


def slot_cfgs(mesh_assets: dict | None = None, n: int = N_SLOTS, rooms: dict | None = None) -> dict:
    import isaaclab.sim as sim_utils
    from isaaclab.assets import AssetBaseCfg
    out = {}
    for i in range(n):
        out[f"fx{i}"] = AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/FX_" + str(i),
            spawn=sim_utils.CuboidCfg(size=(1.0, 1.0, 1.0), collision_props=sim_utils.CollisionPropertiesCfg(),
                                      physics_material=sim_utils.RigidBodyMaterialCfg(static_friction=0.6,
                                                                                      dynamic_friction=0.6),
                                      func=spawn_fx),
            init_state=AssetBaseCfg.InitialStateCfg(pos=(PARK[0] - 1.2 * i, PARK[1], PARK[2])))
    for j, (name, a) in enumerate(sorted((mesh_assets or {}).items())):
        out[f"fm_{name}"] = AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/FM_" + name, spawn=sim_utils.UsdFileCfg(usd_path=a["dst"]),
            init_state=AssetBaseCfg.InitialStateCfg(pos=(PARK[0] - 3.0 * j, PARK[1] - 6.0, PARK[2])))
    for j, (name, r) in enumerate(sorted((rooms or {}).items())):  # render-only room backgrounds, parked
        out[f"fr_{name}"] = AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/FR_" + name, spawn=sim_utils.UsdFileCfg(usd_path=r["usd"]),
            init_state=AssetBaseCfg.InitialStateCfg(pos=(ROOM_PARK[0] - 12.0 * j, ROOM_PARK[1], ROOM_PARK[2])))
    return out


def without_table(mesh_assets: dict | None = None, rooms: dict | None = None):
    """Patch scene._build_cfg in this process: no L8 table, + furniture slots. Returns the undo function."""
    from .. import scene as SC
    orig = SC._build_cfg

    def patched(*a, **k):
        cfg, layout = orig(*a, **k)
        cfg.scene.table = None
        for name, c in slot_cfgs(mesh_assets, rooms=rooms).items():
            setattr(cfg.scene, name, c)
        return cfg, layout

    SC._build_cfg = patched
    return lambda: setattr(SC, "_build_cfg", orig)


def _set_scale(prim, s):
    from pxr import Gf, UsdGeom
    xf = UsdGeom.Xformable(prim)
    ops = {op.GetOpType(): op for op in xf.GetOrderedXformOps()}
    op = ops.get(UsdGeom.XformOp.TypeScale) or xf.AddScaleOp()
    v = tuple(float(x) for x in s)
    op.Set(Gf.Vec3d(*v) if op.GetPrecision() == UsdGeom.XformOp.PrecisionDouble else Gf.Vec3f(*v))


def yaw_quat(yaw: float):
    return (float(np.cos(yaw / 2)), 0.0, 0.0, float(np.sin(yaw / 2)))


def author_scene(env, scene: dict, mesh_assets: dict | None = None, rooms: dict | None = None) -> dict:
    """USD pose / scale / colour of every part of `scene` (furniture + walls); unused slots and meshes parked.
    Takes effect physically at the next hard reset. -> {slots_used, meshes_used}."""
    import omni.usd

    from ..randomize import MAT, _set_pose, set_material
    stage = omni.usd.get_context().get_stage()
    parts = list(scene["furniture"]) + list(scene["walls"])
    cub = [p for p in parts if p.get("usd") is None]
    msh = [p for p in parts if p.get("usd") is not None]
    if len(cub) > N_SLOTS:
        raise ValueError(f"{len(cub)} cuboid parts > {N_SLOTS} slots")
    for i in range(N_SLOTS):
        prim = stage.GetPrimAtPath(_slot_path(i))
        mesh = stage.GetPrimAtPath(_slot_path(i) + "/geometry/mesh")
        if i < len(cub):
            p = cub[i]
            _set_pose(prim, tuple(p["pos"]), yaw_quat(p.get("yaw", 0.0)))
            _set_scale(mesh, p["size"])
            _set_visual(stage, i, p["size"])
            set_material(stage, _slot_path(i) + "/" + MAT, {"color": tuple(p.get("color", (0.6, 0.6, 0.6))),
                                                              "roughness": 0.6})
        else:
            _set_pose(prim, (PARK[0] - 1.2 * i, PARK[1], PARK[2]), (1.0, 0.0, 0.0, 0.0))
            _set_scale(mesh, (0.1, 0.1, 0.1))
            _set_visual(stage, i, (0.1, 0.1, 0.1))
    used = set()
    for p in msh:
        name = p["asset"]
        a = mesh_assets[name]
        off = np.asarray(a["origin_offset"], float)
        yaw = float(p.get("yaw", 0.0))
        c, s = np.cos(yaw), np.sin(yaw)
        o = np.array([c * off[0] - s * off[1], s * off[0] + c * off[1], off[2]])
        _set_pose(stage.GetPrimAtPath(_mesh_path(name)), tuple(np.asarray(p["base_pos"], float) - o), yaw_quat(yaw))
        used.add(name)
    for j, name in enumerate(sorted(mesh_assets or {})):
        if name not in used:
            _set_pose(stage.GetPrimAtPath(_mesh_path(name)), (PARK[0] - 3.0 * j, PARK[1] - 6.0, PARK[2]),
                      (1.0, 0.0, 0.0, 0.0))
    room = scene.get("room")
    for j, name in enumerate(sorted(rooms or {})):
        prim = stage.GetPrimAtPath(f"{ROOT}/FR_{name}")
        if room is not None and room["name"] == name:  # +1 mm: no z-fighting with the grid ground plane
            _set_pose(prim, (room["pos"][0], room["pos"][1], room["pos"][2] + 0.001), yaw_quat(room["yaw"]))
        else:
            _set_pose(prim, (ROOM_PARK[0] - 12.0 * j, ROOM_PARK[1], ROOM_PARK[2]), (1.0, 0.0, 0.0, 0.0))
    return {"slots_used": len(cub), "meshes_used": sorted(used), "room": None if room is None else room["name"]}
