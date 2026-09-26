"""T3 prep (CPU): BEHAVIOR head frames with GT depth, K, movable task-object masks + GT centres (camera frame) and
support-surface masks, for the monocular metric-depth check. usage: t3_prep.py ROOT OUT [FRAMES_PER_EP]"""
import glob, json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
import cv2
import numpy as np
import pyarrow.parquet as pq
from xemb import geom as G
from xemb import src_behavior as B

root, out = sys.argv[1], sys.argv[2]
per = int(sys.argv[3]) if len(sys.argv) > 3 else 2
os.makedirs(out, exist_ok=True)
index = []
for dp in sorted(glob.glob(os.path.join(root, "videos", "task-*", "observation.images.depth.head", "*.mp4")))[::3]:
    ep = os.path.basename(dp)[len("episode_"):-4]
    task = os.path.basename(os.path.dirname(os.path.dirname(dp)))
    try:
        meta = json.load(open(os.path.join(root, "meta", "episodes", task, f"episode_{ep}.json")))
        t = pq.read_table(os.path.join(root, "data", task, f"episode_{ep}.parquet"))
    except Exception:
        continue
    st = np.array(t.column("observation.state").to_pylist(), float)
    cr = np.array(t.column("observation.cam_rel_poses").to_pylist(), float)[:, 14:21]
    ti = np.array(t.column("observation.task_info").to_pylist(), float)
    cfg = B._load(meta["config"])
    inst = cfg["scene"]["scene_file"]["metadata"]["task"]["inst_to_name"]
    lay = B.task_layout(B._load(meta["task_obs_keys"]))
    mapping = {int(k): v for k, v in B._load(meta["ins_id_mapping"]).items()}
    ids = B._load(meta[f"{B.HEAD_CAM}::unique_ins_ids"])
    name_of = {i: (mapping.get(i, "").split("/") + [""] * 4)[3] for i in ids}
    n = len(st)
    idx = [int(n * f) for f in np.linspace(0.3, 0.7, per)]
    rgb = B.decode(os.path.join(root, "videos", task, "observation.images.rgb.head", f"episode_{ep}.mp4"), idx, "rgb")
    dep = B.decode(dp, idx, "depth")
    seg = B.decode(os.path.join(root, "videos", task, "observation.images.seg_instance_id.head", f"episode_{ep}.mp4"),
                   idx, "seg", ids)
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
            if "in_gripper_right" in lay[syn] and not syn.startswith(B.SURFACE_PREFIX):
                gt_c = G.apply_T(Ecb, G.apply_T(G.inv_T(Twb), ti[k, lay[syn]["pos"]]))
                objs.append({"name": nm, "gt_c": gt_c.tolist(), "mask": m})
            elif syn.startswith(B.SURFACE_PREFIX):  # tables carry in_gripper fields too
                surf.append({"name": nm, "mask": m})
        if not objs and not surf:
            continue
        key = f"{task}_{ep}_{k}"
        cv2.imwrite(os.path.join(out, key + ".jpg"), rgb[k])
        np.savez_compressed(os.path.join(out, key + ".npz"), depth=dep[k].astype(np.float32),
                            objm=np.array([o["mask"] for o in objs]) if objs else np.zeros((0, 720, 720), bool),
                            surfm=np.array([s["mask"] for s in surf]) if surf else np.zeros((0, 720, 720), bool),
                            Tbc=Tbc)
        index.append({"key": key, "objs": [{"name": o["name"], "gt_c": o["gt_c"]} for o in objs],
                      "surfs": [s["name"] for s in surf]})
json.dump(index, open(os.path.join(out, "index.json"), "w"))
print("frames", len(index), "objs", sum(len(i["objs"]) for i in index), "surfs", sum(len(i["surfs"]) for i in index))
