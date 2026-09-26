"""T3 re-check (before discarding, user rule): BEHAVIOR frames with GT depth, object / surface masks, and the FK
end-effector positions in the camera frame (the anchor for per-frame scale alignment). Parallel over episodes.
usage: t3b_prep.py ROOT OUT FRAMES_PER_EP WORKERS"""
import glob, json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
import numpy as np


def one(args):
    import cv2
    import pyarrow.parquet as pq
    from xemb import geom as G
    from xemb import src_behavior as B
    root, out, dp, per = args
    ep = os.path.basename(dp)[len("episode_"):-4]
    task = os.path.basename(os.path.dirname(os.path.dirname(dp)))
    try:
        meta = json.load(open(os.path.join(root, "meta", "episodes", task, f"episode_{ep}.json")))
        t = pq.read_table(os.path.join(root, "data", task, f"episode_{ep}.parquet"))
    except Exception:
        return []
    st = np.array(t.column("observation.state").to_pylist(), float)
    cr = np.array(t.column("observation.cam_rel_poses").to_pylist(), float)[:, 14:21]
    ti = np.array(t.column("observation.task_info").to_pylist(), float)
    inst = B._load(meta["config"])["scene"]["scene_file"]["metadata"]["task"]["inst_to_name"]
    lay = B.task_layout(B._load(meta["task_obs_keys"]))
    mapping = {int(k): v for k, v in B._load(meta["ins_id_mapping"]).items()}
    ids = B._load(meta[f"{B.HEAD_CAM}::unique_ins_ids"])
    name_of = {i: (mapping.get(i, "").split("/") + [""] * 4)[3] for i in ids}
    n = len(st)
    idx = [int(n * f) for f in np.linspace(0.25, 0.75, per)]
    rgb = B.decode(os.path.join(root, "videos", task, "observation.images.rgb.head", f"episode_{ep}.mp4"), idx, "rgb")
    dep = B.decode(dp, idx, "depth")
    seg = B.decode(os.path.join(root, "videos", task, "observation.images.seg_instance_id.head", f"episode_{ep}.mp4"),
                   idx, "seg", ids)
    grip_ids = {a: [i for i in ids if f"{a}_gripper" in mapping.get(i, "")] for a in ("left", "right")}
    rows = []
    for k in idx:
        if k not in rgb or k not in dep or k not in seg:
            continue
        Tbc = G.pose_to_T(cr[k, :3], G.quat_xyzw_to_mat(cr[k, 3:])) @ G.FLIP_GL_CV
        Ecb = G.inv_T(Tbc)
        Twb = G.pose_to_T(st[k, 140:143], G.yaw_mat(st[k, 149]))
        objs, surf = [], []
        for syn, nm in inst.items():
            if syn.startswith(("agent", "floor")) or syn not in lay or "pos" not in lay[syn]:
                continue
            m = np.isin(seg[k], [i for i, v in name_of.items() if v == nm])
            if m.sum() < 150:
                continue
            if syn.startswith(B.SURFACE_PREFIX):
                surf.append(m)
            elif "in_gripper_right" in lay[syn]:
                objs.append((nm, G.apply_T(Ecb, G.apply_T(G.inv_T(Twb), ti[k, lay[syn]["pos"]])), m))
        ee = {"left": G.apply_T(Ecb, st[k, 186:189]), "right": G.apply_T(Ecb, st[k, 225:228])}
        gm = {a: np.isin(seg[k], grip_ids[a]) for a in ("left", "right")}
        key = f"{task}_{ep}_{k}"
        cv2.imwrite(os.path.join(out, key + ".jpg"), rgb[k])
        np.savez_compressed(os.path.join(out, key + ".npz"), depth=dep[k].astype(np.float32),
                            objm=np.array([o[2] for o in objs]) if objs else np.zeros((0, 720, 720), bool),
                            surfm=np.array(surf) if surf else np.zeros((0, 720, 720), bool),
                            gml=gm["left"], gmr=gm["right"])
        rows.append({"key": key, "objs": [{"name": o[0], "gt_c": o[1].tolist()} for o in objs], "n_surf": len(surf),
                     "ee_cam": {a: v.tolist() for a, v in ee.items()}})
    return rows


if __name__ == "__main__":
    from multiprocessing import Pool
    root, out, per, wk = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    os.makedirs(out, exist_ok=True)
    dps = sorted(glob.glob(os.path.join(root, "videos", "task-*", "observation.images.depth.head", "*.mp4")))
    with Pool(wk) as p:
        res = p.map(one, [(root, out, d, per) for d in dps])
    index = [r for rr in res for r in rr]
    json.dump(index, open(os.path.join(out, "index.json"), "w"))
    print("frames", len(index), "objs", sum(len(i["objs"]) for i in index), "surfs", sum(i["n_surf"] for i in index))
