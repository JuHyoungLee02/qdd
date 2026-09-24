"""R1 DEV set (Isaac, pod only): DEV episodes in the pool format with the head + right-wrist RGB (JPEG, as the pool)
plus, per snapshot, the renderer depth (distance_to_image_plane, float16 m) of the same two cameras and their
world poses = parent link pose x mount_transform() (the camera prim's data.pos_w is also saved, as `stale_*`, to
show it is not used).

  IR_ROOT=cyclo ./ir_run.sh env ... /isaac-sim/python.sh -m harvest.perception.gen_dev --seeds 0-9 --kinds P0 \
      --out /data/harvest/r1/dev

Output per episode (in <out>/<kind>/): ep<seed>.jsonl / .npz / .meta.json / img/ (cli_pool.write_episode) and
ep<seed>.r1.npz {k, depth_<cam> (N,H,W) f16, campos_<cam> (N,3), camR_<cam> (N,3,3), link_<cam> (N,7),
stale_<cam> (N,7)}. DEV seeds 0-29 only.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

from ..sim import snapshot as S


def _seeds(spec: str):
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    for s in out:
        if s not in S.DEV_SEEDS:
            raise SystemExit(f"seed {s}: DEV 0-29 only")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0-9")
    ap.add_argument("--kinds", default="P0,P1,P2")
    ap.add_argument("--out", default="/data/harvest/r1/dev")
    a = ap.parse_args(argv)
    assert a.out.startswith("/data/harvest/"), "every file under /data/harvest"

    from ..cli_pool import run_snapshot_episode, write_episode
    from ..sim.scene import RECORD_CAMERAS, load_realcam, make_env
    from .geom import cam_pose

    cams = tuple(RECORD_CAMERAS)  # head + right wrist (the active arm)
    rc = load_realcam()
    env = None
    for kind in a.kinds.split(","):
        if kind not in S.POOL_KINDS:
            raise SystemExit("DEV perturbations P0-P2 only")
        d = f"{a.out}/{kind}"
        os.makedirs(d, exist_ok=True)
        for s in _seeds(a.seeds):
            if os.path.exists(f"{d}/ep{s}.r1.npz"):
                continue
            if env is None:
                env = make_env(s, headless=True, cameras=cams, depth=True)
                body = {n: env.robot.body_names.index(rc.CAMERA_SPECS[n]["parent"]) for n in cams}
            ext = {"k": []}
            for n in cams:
                for f in ("depth", "campos", "camR", "link", "stale"):
                    ext[f"{f}_{n}"] = []

            def on_snap(env_, pl, rec, st, imgs):
                ext["k"].append(rec["k"])
                rd = env_.robot.data
                for n in cams:
                    ext[f"depth_{n}"].append(env_.camera_depth(n).astype(np.float16))
                    lp = rd.body_pos_w[0, body[n]].cpu().numpy().astype(float)
                    lq = rd.body_quat_w[0, body[n]].cpu().numpy().astype(float)
                    p, R = cam_pose(lp, lq, rc.mount_transform(n))
                    ext[f"campos_{n}"].append(p)
                    ext[f"camR_{n}"].append(R)
                    ext[f"link_{n}"].append(np.concatenate([lp, lq]))
                    cd = env_.scene[n].data
                    ext[f"stale_{n}"].append(np.concatenate([cd.pos_w[0].cpu().numpy(),
                                                             cd.quat_w_world[0].cpu().numpy()]))
                return False

            res = run_snapshot_episode(env, s, kind, cams=cams, on_snapshot=on_snap)
            meta = write_episode(res, d, cams)
            np.savez_compressed(f"{d}/ep{s}.r1.npz", **{k: np.asarray(v) for k, v in ext.items()})
            print("EP " + json.dumps({k: meta[k] for k in ("seed", "kind", "success", "stage", "sim_time_s",
                                                           "wall_s", "n_snapshots")}), flush=True)
    # env.close() hangs in this chroot (seen 2026-09-24: all four processes stuck > 10 min after the last episode);
    # every file is written and closed above, so leave without tearing Kit down.
    os._exit(0)


if __name__ == "__main__":
    main()
