"""L8-X ring on a peg, variant V (upright peg; coordinator 2026-09-29, ~3 % of L8S; helper L8X-assets).

A flat ring (tools/l8x_assets/ring_assets.py: torus, inner diameter = peg diameter + gap) lies on a 7 cm source block
that carries its -x part; the pads pinch its tube at the +x side (the grasp point). The L8-D collection path runs on
a RingWorld (IsaacWorld protocol) with the xlabels truth plan, the ring presented as a pseudo object "centred" at the
grasp point (height = tube radius + 1.8 cm, so the plan's grasp z is the tube centre) and the place target = the peg
axis + the same grasp offset, released 5 cm above the peg top (centred over it), then it falls around the peg.
Judge (on(ring, peg)): the ring's axis within (inner radius - peg radius) of the peg axis, the ring bottom below the
peg top - 1 cm, released; upright = ring tilt <= 35 deg. Task id rp__<ring>__<peg>; names "<colour> ring" /
"<colour> peg" (different colours: unique names). Lighting / head / exposure as xart (drf + CC0 HDRI, 0.785 rad)."""
from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np

STAND_TOP, STAND_SIZE, STAND_CENTRE = 0.80, (0.50, 0.70), (0.50, -0.18)
PEG_XY, RING_XY = (0.50, -0.08), (0.42, -0.36)
BLOCK_HALF_Y = 0.05
RAIL_W = 0.010
RELEASE_ABOVE, TILT_UP = 0.05, 35.0  # pilot 3: releasing 3 cm below the top jammed (the far side of the one-side pinch sags onto the peg top); drop from above
LIFT0, REL_TABLE = -0.0993, 0.85
PARK = (-7.0, 7.0, 0.3)
PEG_ID, RING_ID = "rp_peg", "rp_ring"
OPEN_W = 0.030  # pads open only 3 cm around the tube: the inner finger passes beside the source block


def task_id(ring: str, peg: str) -> str:
    return f"rp__{ring}__{peg}"


def parse(task: str) -> tuple:
    _, ring, peg = task.split("__")
    return ring, peg


def layout(ring: dict, peg: dict, seed: int) -> dict:
    """Seeded layout (pure): peg base on the stand, the ring on its source block, the block box."""
    rng = np.random.default_rng([int(seed), 186, 5])
    jy = float(rng.uniform(-0.02, 0.02))
    px, py = PEG_XY[0], PEG_XY[1] + jy
    rx, ry = RING_XY[0], RING_XY[1] + jy
    rc, t = float(ring["centre_r"]), float(ring["tube_r"])
    # two rails along x under the ring's +-y tube (gate 1: a block under the -x half put the inner finger on it);
    # the +x tube (the grasp point) and both fingers stay clear of them
    rails = [[[rx - rc - t, rx + rc + t], [ry + s * rc - RAIL_W / 2, ry + s * rc + RAIL_W / 2]] for s in (-1, 1)]
    block = rails[0]
    top = STAND_TOP + float(peg["top_z"])
    lift = float(np.clip(LIFT0 + ((STAND_TOP + 0.20) - (REL_TABLE + 0.155)) + rng.uniform(-0.02, 0.02), -0.5, 0.0))
    return {"peg_xy": [round(px, 4), round(py, 4)], "ring_xy": [round(rx, 4), round(ry, 4)],
            "block": [[round(v, 4) for v in b] for b in block],
            "rails": [[[round(v, 4) for v in b] for b in r] for r in rails],
            "block_top": round(STAND_TOP + peg["block_h"], 4),
            "peg_top": round(top, 4), "work_z": STAND_TOP, "lift": round(lift, 4), "jy": round(jy, 4)}


def preds(ring_c, ring_bottom, tilt, grasp_pt, tcp, grip_w, ring: dict, peg: dict, lay: dict) -> dict:
    ring_c, grasp_pt, tcp = (np.asarray(v, float) for v in (ring_c, grasp_pt, tcp))
    gw = 2 * float(ring["tube_r"])
    hold = 0.003 < grip_w < gw + 0.008 and float(np.linalg.norm(grasp_pt - tcp)) < 0.03
    d = float(np.linalg.norm(ring_c[:2] - np.asarray(lay["peg_xy"], float)))
    around = d <= float(ring["inner_d"]) / 2 - float(peg["radius"])
    on = (not hold) and around and ring_bottom < lay["peg_top"] - 0.01
    return {"holding": hold, "on": on, "upright": tilt <= TILT_UP, "lifted": ring_bottom > lay["block_top"] + 0.02}


# ============================================================================ Isaac (pod)
def make_ring_world(rings: dict, pegs: dict, meta: dict, rooms: dict | None = None):
    from ..astra_motion import prompts as P
    from ..astra_motion.world_isaac import CAMS, NO_RENDER, PRE_RENDER, IsaacWorld
    from ..sim import scene as SC
    from tools.l8x_assets.validate_objects import tilt_deg

    from .xart import l8s_step, place_room, preroll_arm, room_cfgs  # L8S audit 3: rooms, ARM_START, joints

    rids, pids = sorted(rings), sorted(pegs)
    peg_meta = dict(meta["peg"], block_h=meta["block_h"])
    orig = SC._build_cfg

    def patched(*x, **k):
        import isaaclab.sim as sim_utils
        from isaaclab.assets import AssetBaseCfg, RigidObjectCfg
        cfg, lay = orig(*x, **k)
        cfg.scene.table = None
        room_cfgs(cfg, rooms)
        cfg.scene.stand = AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/STAND",
            spawn=sim_utils.CuboidCfg(
                size=(STAND_SIZE[0], STAND_SIZE[1], STAND_TOP), collision_props=sim_utils.CollisionPropertiesCfg(),
                visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.62, 0.52, 0.40))),
            init_state=AssetBaseCfg.InitialStateCfg(pos=(STAND_CENTRE[0], STAND_CENTRE[1], STAND_TOP / 2)))
        for j in (0, 1):  # the two source rails (scaled / posed per episode)
            setattr(cfg.scene, f"rail_{j}", AssetBaseCfg(
                prim_path="{ENV_REGEX_NS}/RAIL_%d" % j,
                spawn=sim_utils.CuboidCfg(
                    size=(1.0, 1.0, 1.0), collision_props=sim_utils.CollisionPropertiesCfg(),
                    visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.35, 0.35, 0.38))),
                init_state=AssetBaseCfg.InitialStateCfg(pos=(PARK[0], -PARK[1] - j, -3.0))))
        for i, n in enumerate(pids):
            setattr(cfg.scene, f"peg_{i}", AssetBaseCfg(prim_path="{ENV_REGEX_NS}/PEG_%d" % i,
                                                         spawn=sim_utils.UsdFileCfg(usd_path=pegs[n]["usd"]),
                                                         init_state=AssetBaseCfg.InitialStateCfg(
                                                             pos=(PARK[0] - 0.5 * i, -PARK[1], -3.0))))
        for i, n in enumerate(rids):
            setattr(cfg.scene, f"ring_{i}", RigidObjectCfg(
                prim_path="{ENV_REGEX_NS}/RING_%d" % i,
                spawn=sim_utils.UsdFileCfg(usd_path=rings[n]["usd"],
                                           mass_props=sim_utils.MassPropertiesCfg(mass=rings[n]["mass"])),
                init_state=RigidObjectCfg.InitialStateCfg(pos=(PARK[0] - 0.3 * i, PARK[1], PARK[2]))))
        return cfg, lay

    class RingWorld(IsaacWorld):
        def __init__(self):
            from ..sim.scene import GRIP_MAX_W, make_env
            SC._build_cfg = patched
            try:
                self.env = make_env(0, headless=True, cameras=CAMS, depth=True, render_interval=NO_RENDER)
            finally:
                SC._build_cfg = orig
            env = self.env
            # gate 1 (0/10): fully open (10.7 cm) the inner finger landed on the source block / the ring and tipped it
            self.dt, self.w_open = float(env.step_dt), OPEN_W
            self._st, self.last_obs = None, None
            env.layout = {}
            SC._LAYOUT["layout"] = {}
            self._head_limit()
            self.furniture_scene = None

        def _head_limit(self, upper_deg: float = 57.0):
            import omni.usd
            from pxr import Usd
            stage = omni.usd.get_context().get_stage()
            for p in Usd.PrimRange(stage.GetPrimAtPath("/World/envs/env_0/Robot")):
                if p.GetName() == "head_joint1":
                    a = p.GetAttribute("physics:upperLimit")
                    if a and a.Get() is not None and a.Get() < upper_deg:
                        a.Set(upper_deg)

        def _usd_pose(self, path, pos, scale=None):
            import omni.usd

            from ..sim.assets_x.isaac import _set_scale
            from ..sim.randomize import _set_pose
            stage = omni.usd.get_context().get_stage()
            prim = stage.GetPrimAtPath(path)
            _set_pose(prim, tuple(float(v) for v in pos), (1.0, 0.0, 0.0, 0.0))
            if scale is not None:
                _set_scale(stage.GetPrimAtPath(path + "/geometry/mesh"), scale)

        def reset(self, seed, task):
            from ..sim.perturb import perturb
            from ..sim.planner import OraclePlanner
            from .clutter_x import HEAD_TILT0
            env = self.env
            rid, pid = parse(task)
            self.rid, self.pid = rid, pid
            ring, peg = rings[rid], pegs[pid]
            lay = layout(ring, peg_meta, seed)
            self.lay = lay
            for i, n in enumerate(pids):  # the episode's peg on the stand, the others parked (USD, hard reset)
                self._usd_pose(f"/World/envs/env_0/PEG_{i}", (*lay["peg_xy"], STAND_TOP) if n == pid
                               else (PARK[0] - 0.5 * i, -PARK[1], -3.0))
            for j, ((bx0, bx1), (by0, by1)) in enumerate(lay["rails"]):
                self._usd_pose(f"/World/envs/env_0/RAIL_{j}", ((bx0 + bx1) / 2, (by0 + by1) / 2,
                                                              STAND_TOP + peg_meta["block_h"] / 2),
                               (bx1 - bx0, by1 - by0, peg_meta["block_h"]))
            room = place_room(rooms, seed, STAND_CENTRE[0], STAND_CENTRE[1], 0.5 * max(STAND_SIZE))
            rob = env.robot
            for jn, v in (("lift_joint", lay["lift"]), ("head_joint1", HEAD_TILT0), ("head_joint2", 0.0)):
                if jn in rob.joint_names:
                    rob.data.default_joint_pos[0, rob.joint_names.index(jn)] = v
                    rob.cfg.init_state.joint_pos[jn] = v
            env.table_top_z = self.table_z = STAND_TOP
            SC._LAYOUT["table_z"] = STAND_TOP
            env.lift = lay["lift"]
            env.task = "mug_tray"  # the OraclePlanner (IK / TCP helper) needs a registered task
            env.layout = {RING_ID: (*lay["ring_xy"], 0.0), PEG_ID: (*lay["peg_xy"], 0.0)}
            env.present = [RING_ID, PEG_ID]
            env.randomization = None
            self._register(ring, peg)
            env.reset(settle_s=0.1)
            ir = rids.index(rid)
            for i, n in enumerate(rids):
                ob = env.scene[f"ring_{i}"]
                p = ([*lay["ring_xy"], lay["block_top"] + ring["tube_r"] + 0.002, 1.0, 0.0, 0.0, 0.0] if i == ir
                     else [PARK[0] - 0.3 * i, PARK[1], PARK[2], 1.0, 0.0, 0.0, 0.0])
                ob.write_root_pose_to_sim(env.torch.tensor([p], dtype=env.torch.float32, device=env.env.device))
                ob.write_root_velocity_to_sim(env.torch.zeros((1, 6), device=env.env.device))
            self.i_ring = ir
            hold = np.concatenate([env.arm_q(), [SC.GRIP_MAX_W]])
            for _ in range(15):
                env.step(hold)
            perturb(env, "P0", seed)
            self._dome(seed)
            self.pl = OraclePlanner(env)
            self.cmd_quat = np.asarray(self.pl.cmd_quat, float)
            self.quat0 = np.asarray(self.pl.goal_quat, float)
            arm_start = preroll_arm(self)  # L8D change 21: the right arm starts out of the head view
            self._jlog = []  # change 20: joints.npz from here (collect_episode saves world._jlog)
            for _ in range(PRE_RENDER):
                env.env.sim.render()
            self.iso = self._auto_exposure()
            self.w_close = max(0.0, 2 * float(ring["tube_r"]) - 0.008)
            self._st = None
            self.furniture_scene = {"kind": "ring_peg_V", "ring": rid, "peg": pid, "layout": lay, "iso": self.iso,
                                    "hdr": self.hdr, "head": {"tilt": HEAD_TILT0, "pan": 0.0}, "surface": "stand",
                                    "room": room, "room_skip": None if room else "no rooms loaded",
                                    "arm_start": arm_start}

        def step(self, cmd_pos, width: float, quat=None) -> None:
            l8s_step(self, cmd_pos, width, quat)

        def _register(self, ring, peg):
            h = float(ring["tube_r"]) + 0.018  # the plan grasps at h - 1.8 cm above the support: the tube centre
            SC.OBJ_GEOM[RING_ID] = {"shape": "cuboid", "size": [2 * ring["tube_r"], 0.03, h], "height": h,
                                   "footprint_r": 0.02, "grasp_width": 2 * ring["tube_r"]}
            SC.OBJ_GEOM[PEG_ID] = {"shape": "cuboid", "size": [0.04, 0.04, 0.002], "height": 0.002,
                                  "footprint_r": 0.02, "place_kind": "around"}
            SC.SUPPORT_TOP[PEG_ID] = 0.0
            P.OBJ_NAME[RING_ID], P.OBJ_DESC[RING_ID] = ring["name"], f"flat ring, {ring['outer_d'] * 100:.1f} cm across"
            P.OBJ_NAME[PEG_ID], P.OBJ_DESC[PEG_ID] = peg["name"], "upright peg on a round base"

        def _dome(self, seed):
            from ..sim import randomize as R
            from ..sim.assets_x import materials as M
            from .clutter_x import material_ok
            if not hasattr(self, "_hdrs"):
                cat = {k: r for k, r in M.usable(M.load()).items() if material_ok(k, r)}
                self._hdrs = [k for k, r in sorted(cat.items()) if r["role"] == "env" and M.split_of(k) == "train"]
                self._cat = cat
                R.setup_visuals(self.env)
            k = self._hdrs[int(hashlib.sha256(f"ring-hdr:{int(seed)}".encode()).hexdigest()[:8], 16) % len(self._hdrs)]
            m = R.sample_randomization(seed, "drf", self.env.layout)
            m["distractors"] = []
            if m.get("hdr"):
                m["hdr"]["file"] = os.path.join(M.ROOT, self._cat[k]["files"]["hdr"])
                m["hdr"]["name"] = k
            R.apply_visuals(self.env, m)
            self.env.randomization = m
            self.hdr = k

        def _auto_exposure(self):
            import carb

            from .clutter_x import DARK_MEAN, ISO0, SAT_MAX
            st = carb.settings.get_settings()
            iso = ISO0 * float(((self.env.randomization or {}).get("lighting") or {}).get("exposure", 1.0))
            for k in range(6):
                st.set("/rtx/post/tonemap/filmIso", iso)
                for _ in range(PRE_RENDER):
                    self.env.env.sim.render()
                self.env.scene["cam_head"].update(0.0, force_recompute=True)
                rgb = self.env.scene["cam_head"].data.output["rgb"][0].cpu().numpy()[..., :3].astype(float)
                sat, mean = float((rgb.max(axis=2) >= 250).mean()), float(rgb.mean())
                if sat > SAT_MAX:
                    iso *= 0.6
                elif mean < DARK_MEAN:
                    iso *= 1.6
                else:
                    return {"iso": round(iso, 2), "sat": round(sat, 4), "mean": round(mean, 1), "tries": k + 1}
            return {"iso": round(iso, 2), "sat": round(sat, 4), "mean": round(mean, 1), "tries": 6,
                    "overexposed": sat > SAT_MAX}

        def task_info(self):
            ring, lay = rings[self.rid], self.lay
            return {"instruction": f"Put the {ring['name']} on the {pegs[self.pid]['name']}.", "tgt": RING_ID,
                    "place": PEG_ID, "present": [RING_ID, PEG_ID], "sup_tgt": lay["block_top"],
                    "sup_place": lay["peg_top"], "place_top": lay["peg_top"] + RELEASE_ABOVE}

        def _status_from(self, pl):
            env = self.env
            d = env.scene[f"ring_{self.i_ring}"].data
            c = d.root_pos_w[0].cpu().numpy().copy()
            q = d.root_quat_w[0].cpu().numpy()
            ring = rings[self.rid]
            from ..sim.objv import qrot
            gp = c + np.asarray(qrot(tuple(q), (float(ring["centre_r"]), 0.0, 0.0)), float)  # the +x tube point
            bottom = float(c[2] - ring["tube_r"])
            h = float(ring["tube_r"]) + 0.018
            tgt = np.array([gp[0], gp[1], bottom + h / 2])
            off = gp[:2] - c[:2]
            place = np.array([self.lay["peg_xy"][0] + off[0], self.lay["peg_xy"][1] + off[1], self.lay["peg_top"]])
            tcp = pl.tcp_pose()[0]
            w = float(env.gripper_width())
            p = preds(c, bottom, tilt_deg(q, (1.0, 0.0, 0.0, 0.0)), gp, tcp, w, ring, peg_meta, self.lay)
            pred = {f"holding({RING_ID})": p["holding"], f"on({RING_ID},{PEG_ID})": p["on"],
                    f"upright({RING_ID})": p["upright"], f"lifted({RING_ID})": p["lifted"]}
            return {"t": round(float(env.sim_time), 6), "tcp": tcp, "grip_w": w, "pred": pred,
                    "obj": {RING_ID: tgt, PEG_ID: place}, "gripper_contacts": set()}

        def observe(self, depth: bool = False):
            obs = IsaacWorld.observe(self)
            if depth:
                obs.depth = {"head": self.env.camera_depth("cam_head").copy()}
            return obs

    return RingWorld()


def pairs(rings: dict, pegs: dict, seeds: list, gaps=None) -> dict:
    """Seeded (ring, peg) per seed: rings of the allowed gaps, peg colour different from the ring colour."""
    ok = sorted(k for k, r in rings.items() if r["ok"] and (gaps is None or r["gap"] in gaps))
    out = {}
    for s in seeds:
        h = int(hashlib.sha256(f"rp:{s}".encode()).hexdigest()[:8], 16)
        r = ok[h % len(ok)]
        ps = sorted(p for p, v in pegs.items() if v["colour"] != rings[r]["colour"])
        out[s] = (r, ps[(h // 7) % len(ps)])
    return out


def run_ring(out: str, rings_json: str, seeds: list, split: str = "train", clean: bool = False, p: float = 0.35,
             gaps=None, video: set = frozenset()) -> list:
    from ..teach_l8.run_collect import style_of
    from . import spec as S
    from .collect import collect_episode
    meta = json.load(open(rings_json))
    pick = pairs(meta["rings"], meta["pegs"], seeds, gaps)
    use_r = {r for r, _ in pick.values()}
    from .fx import rooms_of  # L8S: every episode has a room background (train-split iTHOR rooms)
    rooms = rooms_of(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim", "assets_x"),
                     "train")
    world = make_ring_world({k: meta["rings"][k] for k in use_r}, meta["pegs"], meta, rooms)
    res = []
    for s in seeds:
        r, pg = pick[s]
        task = task_id(r, pg)
        od = os.path.join(out, split, "ring_V", f"{task}_s{s}")
        if os.path.exists(os.path.join(od, "meta.json")):
            continue
        style = "clean" if clean else style_of(s, S.CLEAN_SHARE)
        m = collect_episode(world, s, task, "drf", split, od, 0.0 if style == "clean" else p, 4, 40, 120.0, style,
                            video=s in video)
        m["ring"] = world.furniture_scene
        json.dump(m, open(os.path.join(od, "meta.json"), "w"))
        res.append(m)
        print("EP " + json.dumps({k: m[k] for k in ("seed", "task", "success", "end_reason", "n_calls")}), flush=True)
    return res
