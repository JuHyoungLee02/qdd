"""Independent G1 team (g1b) diagnostics: per-call / per-close snapshots of the grasp state into the pick timeline
(meta grasp_v2.picks[*].timeline.g1b). Opt-in: run9 installs it when <run dir>/G1B_DIAG exists. Read-only."""
from __future__ import annotations

import numpy as np


def snap(rt, tag: str) -> dict:
    w, env = rt.w, rt.w.env
    tg = (rt.choice_key or (None,))[0]
    st = w.status()
    d = env.robot.data
    gids = list(getattr(env, "grip_ids", []))
    out = {"tag": tag, "t": round(float(st["t"]), 3), "grip_w": round(float(st["grip_w"]), 4)}
    if tag.startswith("plan:") and not rt.timeline.get("g1b"):
        out["root"] = [round(float(v), 4) for v in (d.root_pos_w[0] - env.scene.env_origins[0]).cpu().numpy()]
    if gids:
        out["eff"] = [round(float(x), 3) for x in d.applied_torque[0, gids].cpu().numpy()]
        out["qf"] = [round(float(x), 3) for x in d.joint_pos[0, gids].cpu().numpy()]
    if tg is not None:
        out["hold"] = st["pred"].get(f"holding({tg})")
        out["touch"] = tg in (st.get("gripper_contacts") or set())
        if tg in getattr(env, "contact", {}):
            mag = env.contact[tg].data.force_matrix_w[0, 0].norm(dim=-1).cpu().numpy()
            out["fmag"] = [round(float(x), 2) for x in mag[:4]]
        c, _ = env.object_pose(tg)
        tcp = np.asarray(st["tcp"], float)
        out["obj_z"] = round(float(c[2]), 4)
        out["tcp_obj"] = round(float(np.linalg.norm(tcp - np.asarray(c, float))), 4)
    return out


def install(rt) -> None:
    orig_plan, orig_done = rt.plan, rt.on_grip_done

    def plan(st, info, table_z, w_open):
        r = orig_plan(st, info, table_z, w_open)
        try:
            s = snap(rt, f"plan:{r[0]}")
            rt.timeline.setdefault("g1b", []).append(s)
        except Exception as ex:  # noqa: BLE001
            rt.timeline.setdefault("g1b_err", str(ex)[:200])
        return r

    def on_grip_done(action, t, ws):
        try:
            s = snap(rt, f"grip_done:{action}")
            if ws:
                s["ws_min"] = round(min(x[1] for x in ws), 4)
            rt.timeline.setdefault("g1b", []).append(s)
        except Exception as ex:  # noqa: BLE001
            rt.timeline.setdefault("g1b_err", str(ex)[:200])
        return orig_done(action, t, ws)

    rt.plan, rt.on_grip_done = plan, on_grip_done
