"""S-E2E real-robot data: ROBOTIS AI Worker LeRobot v2.1 episodes -> stage-B rows (R2 contract of stageb_data).

Source (plan e2e-ready S-E2E, user-log 61): HF ROBOTIS/Task_0001_CoffeeClassification_lerobot (kind "RB1", 16-D)
and ROBOTIS/Task_0002_OrderPicking_lerobot (kind "RB2", 19-D = 16 + head_joint1/2 + lift_joint); 10 fps; cameras
cam_head (ZED left, 672x376), cam_head_right, cam_wrist_left / cam_wrist_right (D405, 424x240) = the §59 native
sizes, so frames are used as they are.

One row per sampled frame k (stride), same fields as stageb_data.check_row(row, hz=10) plus extras:
  hz = 10, H = 5            §62 (user-log 66): the native 10 Hz is kept, no resampling; chunk = 0.5 s = the next
                            5 recorded actions a[k..k+4]; valid = 0 past the last recorded action (held value)
  arm                       active arm = larger end-effector path length over the next 1 s (FK of the measured
                            state); bimanual = both arms move >= 2 cm and the smaller >= half the larger
  action_exec / _script     8-D of the active arm (7 joints rad + gripper joint value as recorded); equal (teleop,
                            no scripted skill)
  proprio                   q, qd (causal backward difference of the 10 fps state, 0 at k = 0; §83 -- data
                            versions before se2e_c1 used a central difference), tau = 0 (not recorded,
                            proprio_mask.tau = 0), grip = [gripper joint value, its velocity] (joint units, NOT
                            the sim's width in m; stageb_data.make_sample maps both datasets to [0, 1] openness,
                            canon §63 (2), and drops masked tau from statistics and input, §63 (3))
  action_full [H][D]        all recorded action dims (bimanual expert option), state_full [D]
  committed (labels mode)   HEURISTIC decision tokens (LABEL_SRC): Δ = FK(state[k + 3]) - FK(state[k]) (0.33 s ->
                            nearest step count, 3 steps = 0.30 s at 10 Hz, `label_steps`) of
                            the active arm's end_effector link in arm_base_link (x forward, y left, z up); signs
                            with the labels_v2 1 cm dead band and the labels_v2 MAG bins. Not a typed decision
                            label -- the data has none. labels=False = "actions only" mode (no committed, no items).
  aux                       empty (no privileged geometry in real data)
"""
from __future__ import annotations

import json
import math
import os
import xml.etree.ElementTree as ET
import zlib

import numpy as np

from ..jevcall import DIR_XY, DIR_Z, GRIPPER, MAG, build_choice
from ..clients.jevl import question_text
from ..labels_v2 import dir_xy_label, dir_z_label, mag_label

CHUNK_S = 0.5  # action chunk length in time (D19 §33); steps = round(CHUNK_S * fps)
LABEL_SRC = "se2e_heur_ee033@v1"
HORIZON_S = 1.0 / 3.0  # decision label window; steps = round(HORIZON_S * fps)
ARM_WINDOW_S = 1.0
MOVE_MIN_M = 0.02
ARM_NAMES = {a: [f"arm_{a[0]}_joint{i}" for i in range(1, 8)] + [f"gripper_{a[0]}_joint1"] for a in ("left", "right")}
FEATURE_NAMES_16 = ARM_NAMES["left"] + ARM_NAMES["right"]
FEATURE_NAMES_19 = FEATURE_NAMES_16 + ["head_joint1", "head_joint2", "lift_joint"]
QUESTIONS = ("dir_xy", "dir_z", "mag_coarse")  # the heuristic motion labels (E-TC transition strata read these)
# ser-A-min-3 (canon §87): the stage-B items also ask the gripper decision, labelled from the recorded gripper
# command (gripper_label, harvest.intent.from_openness)
ITEM_QUESTIONS = QUESTIONS + ("gripper",)
_OPTS = {"dir_xy": DIR_XY, "dir_z": DIR_Z, "mag_coarse": MAG, "gripper": GRIPPER}
_QTEXT = {"dir_xy": "Which horizontal direction should the active gripper move during the next {w:.2f} s?",
          "dir_z": "Which vertical direction should the active gripper move during the next {w:.2f} s?",
          "mag_coarse": "How far should the active gripper move during the next {w:.2f} s?",
          "gripper": "Should the active gripper close (grasp), open (release), or keep its state during the next "
                     "{w:.2f} s?"}


# ------------------------------------------------------------------------------------------ kinematics
def _rpy(r, p, y):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]])


def _axis_rot(axis, q):
    """Batched Rodrigues: axis (3,), q (N,) -> (N, 3, 3)."""
    k = np.asarray(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    s, c = np.sin(q)[:, None, None], np.cos(q)[:, None, None]
    return np.eye(3) + s * K + (1 - c) * (K @ K)


def load_arm_chain(urdf: str, arm: str, base: str = "arm_base_link") -> list:
    """Joints from `base` to end_effector_{r|l}_link: [(type, xyz, R_origin, axis)]. `urdf` = XML text or path."""
    root = ET.fromstring(urdf) if urdf.lstrip().startswith("<") else ET.parse(urdf).getroot()
    by_child = {j.find("child").get("link"): j for j in root.findall("joint")}
    link, out = f"end_effector_{arm[0]}_link", []
    while link != base:
        j = by_child.get(link)
        if j is None:
            raise ValueError(f"no joint chain from {base} to end_effector_{arm[0]}_link (stuck at {link})")
        o = j.find("origin")
        xyz = [float(v) for v in (o.get("xyz", "0 0 0") if o is not None else "0 0 0").split()]
        rpy = [float(v) for v in (o.get("rpy", "0 0 0") if o is not None else "0 0 0").split()]
        ax = j.find("axis")
        axis = [float(v) for v in ax.get("xyz").split()] if ax is not None else None
        out.append((j.get("type"), np.array(xyz), _rpy(*rpy), axis))
        link = j.find("parent").get("link")
    out = out[::-1]
    if sum(t == "revolute" for t, *_ in out) != 7:
        raise ValueError("expected 7 revolute arm joints")
    return out


def fk_ee(chain: list, q) -> np.ndarray:
    """End-effector position in the base link; q (7,) or (N, 7) -> (3,) or (N, 3)."""
    q = np.asarray(q, float)
    single = q.ndim == 1
    q = q.reshape(-1, 7)
    n = len(q)
    R = np.broadcast_to(np.eye(3), (n, 3, 3)).copy()
    p = np.zeros((n, 3))
    i = 0
    for typ, xyz, Ro, axis in chain:
        p = p + R @ xyz
        R = R @ Ro
        if typ in ("revolute", "continuous"):
            R = R @ _axis_rot(axis, q[:, i])
            i += 1
    return p[0] if single else p


# ------------------------------------------------------------------------------------------ time series
def interp_at(x, t: float) -> np.ndarray:
    """Linear interpolation of rows of x at fractional index t (clamped to [0, T-1])."""
    x = np.asarray(x, float)
    t = min(max(t, 0.0), len(x) - 1.0)
    i = int(math.floor(t))
    if i >= len(x) - 1:
        return x[-1].copy()
    w = t - i
    return (1 - w) * x[i] + w * x[i + 1]


def resample_chunk(a, src_hz: float, t0_index: int, dst_hz: float, H: int):
    """H targets at t0 + i/dst_hz from a src_hz stream (linear); valid = 0 past the last sample (held)."""
    a = np.asarray(a, float)
    ts = t0_index + np.arange(H) * (src_hz / dst_hz)
    ch = np.stack([interp_at(a, t) for t in ts])
    valid = (ts <= len(a) - 1 + 1e-9).astype(int)
    return ch, valid


def finite_velocity(x, hz: float) -> np.ndarray:
    """Causal backward difference (canon §83): v[k] = (x[k] - x[k-1]) * hz, v[0] = 0 -- never reads frame k + 1
    (= se2e_temporal.backward_velocity, the motion line's source). Was np.gradient (central, 0.1 s of future)."""
    x = np.asarray(x, float)
    v = np.zeros_like(x)
    v[1:] = np.diff(x, axis=0) * hz
    return v


# ------------------------------------------------------------------------------------------ labels
def decision_labels(delta) -> dict:
    """HEURISTIC (LABEL_SRC) decision tokens from an end-effector displacement (m), labels_v2 bins/dead band."""
    return {"dir_xy": dir_xy_label(delta), "dir_z": dir_z_label(delta), "mag_coarse": mag_label(delta)}


def gripper_label(row: dict) -> str | None:
    """canon §87 gripper decision of a row from its recorded gripper JOINT COMMAND (action_exec dim 7) over the
    decision-label window (label_steps, the direction labels' 1/3 s): openness (stageb_data.GRIP_CAL of the row's
    dataset) at k and k + label_steps -> harvest.intent.from_openness. None (not derivable) for a row without the
    label window fields (episode_rows always writes them)."""
    from ..intent import from_openness
    from .stageb_data import grip_open01, grip_source
    if "label_steps" not in row or "label_window_s" not in row:
        return None
    n, a = int(row["label_steps"]), row["action_exec"]
    if not 0 < n < len(a):
        raise ValueError(f"label_steps {n}: needs 0 < n < chunk length {len(a)}")
    src = grip_source(row)
    return from_openness(grip_open01(a[0][7], src), grip_open01(a[n][7], src), float(row["label_window_s"]))


def segment_lines(rows: list) -> dict:
    """canon §90 segment-intent line of every row, per episode (kind, seed) in frame order, from the rows' gripper
    labels (harvest.intent.segments_from_events). {row key: line}."""
    from ..intent import segments_from_events
    by = {}
    for r in rows:
        by.setdefault((r["kind"], r["seed"]), []).append(r)
    out = {}
    for ep in by.values():
        ep = sorted(ep, key=lambda r: r["k"])
        for r, s in zip(ep, segments_from_events([gripper_label(r) for r in ep])):
            out[f"{r['kind']}_ep{r['seed']}_k{r['k']}"] = s
    return out


def _travel(p):
    p = np.asarray(p, float)
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()) if len(p) > 1 else 0.0


def active_arm(ee_left, ee_right, move_min: float = MOVE_MIN_M):
    """(arm, bimanual) from the two end-effector paths over a window; right when neither moves."""
    tl, tr = _travel(ee_left), _travel(ee_right)
    if max(tl, tr) < move_min:
        return "right", False
    arm = "left" if tl > tr else "right"
    return arm, bool(min(tl, tr) >= move_min and min(tl, tr) >= 0.5 * max(tl, tr))


def arm_index(names, arm: str) -> list:
    return [list(names).index(n) for n in ARM_NAMES[arm]]


def split_of(kind: str, episode: int, val_pct: int = 5) -> str:
    """Deterministic per-episode split (hash), ~val_pct % val within every dataset."""
    return "val" if zlib.crc32(f"{kind}:{episode}".encode()) % 100 < val_pct else "train"


# ------------------------------------------------------------------------------------------ rows
def episode_rows(state, action, fps: float, chain: dict, seed: int, kind: str, task: str, stride: int = 1,
                 labels: bool = True, H: int | None = None, hz: int | None = None, names=None, image_ref=None,
                 timestamps=None) -> list:
    """R2 rows (stageb_data.check_row(row, hz)) for frames 0, stride, 2*stride, ... of one episode. Default
    hz = the dataset fps (§62, no resampling), H = round(CHUNK_S * hz)."""
    hz = int(round(fps)) if hz is None else hz
    H = int(round(CHUNK_S * hz)) if H is None else H
    lsteps = int(round(HORIZON_S * fps))
    st, act = np.asarray(state, float), np.asarray(action, float)
    names = list(names or (FEATURE_NAMES_19 if st.shape[1] == 19 else FEATURE_NAMES_16))
    idx = {a: arm_index(names, a) for a in ("left", "right")}
    ee = {a: fk_ee(chain[a], st[:, idx[a][:7]]) for a in ("left", "right")}
    vel = finite_velocity(st, fps)
    win = int(round(ARM_WINDOW_S * fps))
    split = split_of(kind, seed)
    rows = []
    for k in range(0, len(st), stride):
        arm, both = active_arm(ee["left"][k:k + win + 1], ee["right"][k:k + win + 1])
        ix = idx[arm]
        full, valid = resample_chunk(act, fps, k, hz, H)
        r = {"seed": int(seed), "kind": kind, "k": int(k), "hz": hz, "H": H, "arm": arm, "bimanual": both,
             "skill_id": "teleop", "phase_id": "na", "split": split, "task": task, "fps_src": fps,
             "t_src": float(timestamps[k]) if timestamps is not None else k / fps,
             "proprio": {"q": st[k, ix[:7]].tolist(), "qd": vel[k, ix[:7]].tolist(), "tau": [0.0] * 7,
                         "grip": [float(st[k, ix[7]]), float(vel[k, ix[7]])]},
             "proprio_mask": {"q": 1, "qd": 1, "tau": 0, "grip": 1},
             "action_exec": full[:, ix].tolist(), "action_script": full[:, ix].tolist(), "valid": valid.tolist(),
             "action_full": full.tolist(), "state_full": st[k].tolist(), "names_full": names,
             "aux": {"reg": {}, "cls": {}}}
        d = interp_at(ee[arm], k + lsteps) - ee[arm][k]
        r["ee_delta"] = [round(float(v), 5) for v in d]
        r["label_steps"], r["label_window_s"] = lsteps, lsteps / fps
        if labels:
            r["committed"] = decision_labels(d)
            r["labels_src"] = LABEL_SRC
        if image_ref is not None:
            r["images"] = image_ref(k)
        rows.append(r)
    return rows


# ------------------------------------------------------------------------------------------ samples
GRIP_CLOSED = 0.5  # gripper joint value above which the prompt says "closed" [assumption: 0 open .. ~1.1 closed]


def context_text(row: dict) -> str:
    g = "closed" if row["proprio"]["grip"][0] > GRIP_CLOSED else "open"
    return f'task: "{row["task"]}"\nrobot: gripper={g} arm={row["arm"]}'


def decision_items(committed: dict, ctx: str, split: str, key: str, window_s: float) -> list:
    out = []
    for q in ITEM_QUESTIONS:
        if committed.get(q) is None:
            continue
        qid, spec = build_choice(f"se2e.{q}@v1", _QTEXT[q].format(w=window_s), _OPTS[q])
        out.append({"key": key, "question": q, "split": split, "text": question_text(ctx, qid, spec),
                    "images": [], "names": [o.name for o in _OPTS[q]], "target": [committed[q]], "ne": False,
                    "source": LABEL_SRC})
    return out


def needed_cams(row: dict, wrist: bool = True) -> list:
    """§57: head always + active wrist (both wrists for bimanual rows)."""
    if not wrist:
        return ["cam_head"]
    return ["cam_head"] + ([f"cam_wrist_{a}" for a in ("right", "left")] if row.get("bimanual")
                           else [f"cam_wrist_{row['arm']}"])


def load_se2e(rows_path: str, image_root: str = "", labels: bool = True, wrist: bool = True,
              hz: int | None = None) -> list:
    """Stage-B samples (stageb_data.make_sample format) from a converted rows file. Rows missing a needed camera
    (e.g. Task_0002 episodes 617-816 have no wrist videos) are skipped. hz = the dataset rate every row must have
    (None = each row's own hz). make_sample maps the gripper joint to [0, 1] openness (canon §63 (2), GRIP_CAL).
    ser-A-min-3: labels mode adds the canon §87 gripper decision (gripper_label) to `committed` and the items; the
    context ends with the canon §90 segment-intent line (segment_lines, from the episode's gripper events)."""
    from .stageb_data import images_of, make_sample
    out = []
    rows = [json.loads(x) for x in open(rows_path, encoding="utf-8")]
    segs = segment_lines(rows)
    for r in rows:
        if not set(needed_cams(r, wrist)) <= set(r.get("images") or {}):
            continue
        if not labels:
            r.pop("committed", None)
        elif r.get("committed") is not None and "gripper" not in r["committed"]:
            g = gripper_label(r)
            if g is not None:
                r["committed"] = {**r["committed"], "gripper": g}
        key = f"{r['kind']}_ep{r['seed']}_k{r['k']}"
        ctx = context_text(r) + "\n" + segs[key]
        ims = images_of({"images": r["images"]}, "both" if r.get("bimanual") else r["arm"], wrist, image_root)
        items = decision_items(r.get("committed") or {}, ctx, r["split"], key, r["label_window_s"]) if labels else []
        for it in items:
            it["images"] = ims
        s = make_sample(r, None, items, hz=r["hz"] if hz is None else hz)
        s["context"] = {"text": ctx, "images": ims}
        s["split"] = r["split"]
        out.append(s)
    return out


def rows_path(root: str, kind: str) -> str:
    return os.path.join(root, f"{kind}.stageb.jsonl")
