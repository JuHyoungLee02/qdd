"""(pod) World9 + procedural fixtures. One process holds one fixture per family slot (art_<family>, parked away
from the scene); an episode moves its fixture onto the table (default root state + USD pose before the hard reset,
the start joint values after it). harvest.l9 is used as is: the Isaac Lab scene cfg (_build_cfg) and
world9.tabletop_parts are wrapped inside this process only (restored after the world is built / never written to
disk), nothing in harvest/l9 changes."""
from __future__ import annotations

import math
import os

import numpy as np

from . import fixtures as FX

PARK = (-6.0, 9.0, 0.0)  # slot i parks at PARK + (-1.5 i, 0, 0)
ASSET_DIR = "/data/harvest/l9v2/art_assets"
SETTLE_STEPS = 6


def write_usd(spec: dict, out_dir: str = ASSET_DIR) -> str:
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, f"{spec['name']}_{spec.get('version', 'fx')}.usda")  # versioned: running lanes keep their files
    txt = FX.usda(spec)
    if not os.path.exists(p) or open(p).read() != txt:
        tmp = p + f".tmp{os.getpid()}"
        with open(tmp, "w") as f:
            f.write(txt)
        os.replace(tmp, p)
    return p


def _actuators(spec: dict):
    from isaaclab.actuators import ImplicitActuatorCfg
    out = {}
    for jn, J in spec["joints"].items():
        d = J["drive"]
        out[jn] = ImplicitActuatorCfg(joint_names_expr=[jn], stiffness=float(d["stiffness"]),
                                      damping=float(d["damping"]), friction=float(d.get("friction", 0.0)))
    return out


def make_art_world(arm: str, pool: dict, rooms: dict, mesh: dict | None, robot: str, specs: dict, hcam=None):
    """specs: {family: fixture spec}. -> World9 with .fx (slot table) and the fixture helpers below."""
    from ..l9 import world9 as W9
    from ..sim import scene as SC
    paths = {fam: write_usd(sp) for fam, sp in specs.items()}
    fams = sorted(specs)
    orig = SC._build_cfg

    def patched(*x, **k):
        import isaaclab.sim as sim_utils
        from isaaclab.assets import ArticulationCfg
        cfg, layout = orig(*x, **k)
        for i, fam in enumerate(fams):
            setattr(cfg.scene, f"art_{fam}", ArticulationCfg(
                prim_path="{ENV_REGEX_NS}/ART_%s" % fam,
                spawn=sim_utils.UsdFileCfg(
                    usd_path=paths[fam],
                    articulation_props=sim_utils.ArticulationRootPropertiesCfg(fix_root_link=True)),
                init_state=ArticulationCfg.InitialStateCfg(pos=(PARK[0] - 1.5 * i, PARK[1], PARK[2])),
                actuators=_actuators(specs[fam])))
        return cfg, layout

    orig_top = W9.tabletop_parts

    def tabletop(mesh_, vseed, furniture, arm_):  # tabletop decor must not overlap the fixture (ghost part)
        g = getattr(W9, "_ART_GHOST", None)
        return orig_top(mesh_, vseed, furniture + ([g] if g else []), arm_)
    W9.tabletop_parts = tabletop
    SC._build_cfg = patched
    try:
        world = W9.make_world9(arm, pool, rooms, mesh=mesh, robot=robot, hcam=hcam)
    finally:
        SC._build_cfg = orig
    world.fx = {fam: {"spec": specs[fam], "key": f"art_{fam}", "slot": i, "usd": paths[fam]} for i, fam in enumerate(fams)}
    world.fx_cur = None
    return world


def _set_prim_pose(path: str, pos, quat):
    import omni.usd

    from ..sim.randomize import _set_pose
    stage = omni.usd.get_context().get_stage()
    _set_pose(stage.GetPrimAtPath(path), tuple(float(v) for v in pos), tuple(float(v) for v in quat))


def stage_fixture(world, fam: str | None, T_WF, start: dict | None = None) -> None:
    """Before World9.reset: the episode's fixture at T_WF (start joint values in its defaults), every other slot parked."""
    import torch
    for f, s in world.fx.items():
        art = world.env.scene[s["key"]]
        if f == fam:
            T = np.asarray(T_WF, float)
            pos, quat = T[:3, 3], FX._mat_quat(T[:3, :3])
        else:
            pos, quat = np.array([PARK[0] - 1.5 * s["slot"], PARK[1], PARK[2]]), np.array([1.0, 0, 0, 0])
        dev, dt = art.data.default_root_state.device, art.data.default_root_state.dtype
        art.data.default_root_state[0, :3] = torch.tensor(pos, dtype=dt, device=dev)
        art.data.default_root_state[0, 3:7] = torch.tensor(quat, dtype=dt, device=dev)
        art.cfg.init_state.pos = tuple(float(v) for v in pos)
        art.cfg.init_state.rot = tuple(float(v) for v in quat)
        q = torch.zeros_like(art.data.default_joint_pos[0])
        if f == fam and start:
            for jn, v in start.items():
                q[art.joint_names.index(jn)] = float(v)
        art.data.default_joint_pos[0] = q
        art.cfg.init_state.joint_pos = {jn: float(q[i]) for i, jn in enumerate(art.joint_names)}
        _set_prim_pose(f"/World/envs/env_0/ART_{f}", pos, quat)
    world.fx_cur = fam


def settle_fixture(world, start: dict | None = None) -> dict:
    """After World9.reset: write the start joint values (when the reset did not), zero joint targets; -> measured
    root pose error (m) and joint values."""
    import torch
    fam = world.fx_cur
    if fam is None:
        return {}
    art = world.env.scene[world.fx[fam]["key"]]
    want = torch.zeros_like(art.data.joint_pos[0])
    for jn, v in (start or {}).items():
        want[art.joint_names.index(jn)] = float(v)
    if float((art.data.joint_pos[0] - want).abs().max()) > 1e-3:
        art.write_joint_state_to_sim(want.unsqueeze(0), torch.zeros_like(want).unsqueeze(0))
    tgt = want.clone()
    for i, jn in enumerate(art.joint_names):
        if world.fx[fam]["spec"]["joints"][jn]["kind"] == "button":
            tgt[i] = 0.0
    art.set_joint_position_target(tgt.unsqueeze(0))
    return {"joints": joints(world), "root_err_m": root_err(world)}


def T_WF_now(world) -> np.ndarray:
    fam = world.fx_cur
    art = world.env.scene[world.fx[fam]["key"]]
    o = world.env.scene.env_origins[0].cpu().numpy()
    return FX.T_of(FX.qmat(art.data.root_quat_w[0].cpu().numpy()), art.data.root_pos_w[0].cpu().numpy() - o)


def root_err(world) -> float:
    fam = world.fx_cur
    art = world.env.scene[world.fx[fam]["key"]]
    o = world.env.scene.env_origins[0].cpu().numpy()
    return float(np.linalg.norm(art.data.root_pos_w[0].cpu().numpy() - o - art.data.default_root_state[0, :3].cpu().numpy()))


def joints(world) -> dict:
    fam = world.fx_cur
    if fam is None:
        return {}
    art = world.env.scene[world.fx[fam]["key"]]
    return {jn: float(art.data.joint_pos[0, i]) for i, jn in enumerate(art.joint_names)}


def link_world(world, link: str) -> np.ndarray:
    fam = world.fx_cur
    art = world.env.scene[world.fx[fam]["key"]]
    k = art.body_names.index(link)
    o = world.env.scene.env_origins[0].cpu().numpy()
    return FX.T_of(FX.qmat(art.data.body_quat_w[0, k].cpu().numpy()), art.data.body_pos_w[0, k].cpu().numpy() - o)


def ghost_part(spec: dict, T_WF) -> dict:
    """A furniture-like box over the fixture (tabletop decor clash test only; never authored)."""
    from .scene_art import fixture_aabb
    (x0, x1), (y0, y1) = fixture_aabb(spec, T_WF, 0.03)
    tz = float(np.asarray(T_WF)[2][3])
    H = float(spec["dims"]["H"])
    return {"id": "art_ghost", "prim": "cuboid", "size": [x1 - x0, y1 - y0, H], "pos": [(x0 + x1) / 2, (y0 + y1) / 2, tz + H / 2],
            "yaw": 0.0, "role": "ghost", "usd": "ghost"}
