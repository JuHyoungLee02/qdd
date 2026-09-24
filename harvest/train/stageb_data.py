"""Stage-B data: one fused sample per snapshot (canon §51-§52, §57, §58; R4 of the e2e-ready plan).

A stage-B sample feeds the ONE Qwen3-VL-4B model three losses:
  (1) typed decision tokens  -> stage-A items (same prompts / option tries / renormalized set NLL as stage A),
  (2) action expert          -> an action chunk (H steps x 8-D: 7 right-arm joint position targets [rad] +
                                gripper width target [m], 30 Hz) by conditional flow matching,
  (3) auxiliary geometry head -> privileged sim geometry (gripper->object offsets, distances, predicates);
                                a TRAINING SIGNAL only, never a runtime input (§58).
Runtime prompt state default = "IMG": task sentence + contract summary + gripper open/closed + images (head +
active wrist, §57); no M1 coordinates, no predicate facts. S0 / S1 text states are ablations.

Action target modes: "absolute" (default, §58: the scripted skill S is the teacher, target = executed teacher
action) and "residual" (ablation, §35: target = executed - scripted, bounded per dim by xi; the expert then also
sees the scripted chunk). Task-space Jev-authority projection (§35) stays outside the model (R5 hook).

R2 CONTRACT (file <episode folder>.stageb.jsonl next to the pool folder, one row per snapshot, key (seed, kind, k)
= the pool line) -- see docs/stage3/results/r4_stageB.md §5 and `check_row`:
  seed, kind, k           join key to the pool line (images, text_state, split, decision flag)
  hz = 30, H              chunk rate / length (H = 15 -> 0.5 s)
  arm = "right"           active arm (selects the wrist camera, §57)
  skill_id, phase_id      scripted skill + FSM phase executing at t0
  proprio                 {"q": [7] rad, "qd": [7] rad/s, "tau": [7] N m (measured effort), "grip": [width m,
                           width velocity m/s]}
  action_exec [H][8]      the command actually sent (teacher S, or S+R after the §35 projection)
  action_script [H][8]    the scripted skill command (equal to action_exec when no residual was applied)
  valid [H]               1 = real step, 0 = padding after the episode end
  committed (optional)    {question: option name} the M4-confirmed decision, the option NAME shown in the DecCall
                          (= the decision token string); default = the single labels_v2 target of that question
  aux                     {"reg": {name: float|null}, "cls": {name: 0|1|null}}; names in AUX_REG / AUX_CLS
"""
from __future__ import annotations

import json
import math
import os
import re

import numpy as np

HZ = 30
H_DEFAULT = 15  # 0.5 s chunk (D19 §33) at 30 Hz
ACT_DIM = 8  # 7 right-arm joints + gripper width
PROPRIO_KEYS = (("q", 7), ("qd", 7), ("tau", 7), ("grip", 2))
PROPRIO_DIM = sum(n for _, n in PROPRIO_KEYS)
QUESTIONS = ("dir_xy", "dir_z", "mag_coarse", "target", "phase")  # = stagea_data.QUESTIONS
CAMS = {"right": "cam_wrist_right", "left": "cam_wrist_left"}
# auxiliary geometry (privileged sim state; meters / binary). "tgt" = the stage target object, "goal" = the
# sub-phase goal point of labels_v2 (§54), "place" = the placement object.
AUX_REG = ("g2tgt_dx", "g2tgt_dy", "g2tgt_dz", "g2tgt_dist", "g2goal_dx", "g2goal_dy", "g2goal_dz", "g2goal_dist",
           "tgt2place_dx", "tgt2place_dy", "tgt2place_dz")
AUX_CLS = ("gripper_open", "holding_tgt", "lifted_tgt", "upright_tgt", "near_tgt_place", "contact_tgt_place",
           "on_tgt_place")
AUX_REG_SCALE = 0.05  # m -> loss units (a 5 cm error = 1)
# §61 / §64 verification head V1h targets: the E-M4b-meas test predicates (= m4b.spec.PREDS, world 5 + robot 4),
# from R2 rows' verify.truth (datagen.rows.truth9); the runtime reads them through runtime.measure
VERIFY_PREDS = ("on_tp", "contact_tp", "lifted_t", "near_tp", "above_tp", "gripper_open", "holding_t",
                "lifted_holding", "contact_stall")


# ------------------------------------------------------------------------------------------ prompt state
_KEEP = re.compile(r"^(t_state:|stage S\d+:)")


def image_only_state(text_state: str) -> str:
    """§58 default runtime state: keep the header (time, contract, stage sentence) and the stage summary
    (exit / invariants / elapsed), reduce the robot line to gripper open/closed + arm moving/still, drop the
    object list, facts and change log (they are M1 / predicate outputs)."""
    out = []
    for ln in text_state.split("\n"):
        if _KEEP.match(ln):
            out.append(ln)
        elif ln.startswith("robot:"):
            g = re.search(r"gripper=(\w+)", ln)
            a = re.search(r"arm=(\w+)", ln)
            grip = "open" if g and g.group(1) == "open" else "closed"
            out.append(f"robot: gripper={grip}" + (f" arm={a.group(1)}" if a else ""))
    return "\n".join(out)


def prompt_state(line: dict, state: str = "IMG", step_cm: float = 0.1) -> str:
    """IMG (default, §58) | S0 (pool text_state) | S1 / S2 (E3-lite geometry block, ablation)."""
    if state == "IMG":
        return image_only_state(line["text_state"])
    if state == "S0":
        return line["text_state"]
    from .. import e3lite
    return e3lite.state_text(line, state, step_cm=step_cm)


CAM_LABEL = {"cam_head": "head camera:", "cam_wrist_right": "right wrist camera (active arm):",
             "cam_wrist_left": "left wrist camera (active arm):"}
CAMERA_LAYOUT = "D27v1"  # §59: system -> [label, native image]* (head, active wrist[s]) -> state -> question


def images_of(line: dict, arm: str = "right", wrist: bool = True, root: str = "") -> list:
    """[[label, path], ...]: head always, then the active arm's wrist (both wrists for a bimanual skill, arm =
    "both"), native resolution, Qwen3-VL multi-image in this order (§57, §59)."""
    cams = ["cam_head"]
    if wrist:
        cams += [CAMS["right"], CAMS["left"]] if arm == "both" else [CAMS[arm]]
    return [[CAM_LABEL[c], os.path.join(root, line["images"][c]) if root else line["images"][c]] for c in cams]


def camera_config(images) -> str:
    """Camera configuration string for the prompt / question_id hash (§59)."""
    return CAMERA_LAYOUT + ":" + "|".join(lab for lab, _ in images)


# ------------------------------------------------------------------------------------------ contract checks
def check_row(r: dict, hz: int = HZ) -> None:
    """Raise ValueError if an R2 row breaks the contract. `hz` = the dataset's action rate (§62: our data 30 Hz,
    S-E2E public data 10 Hz)."""
    for k in ("seed", "kind", "k", "hz", "H", "skill_id", "phase_id", "proprio", "action_exec", "action_script",
              "valid", "aux"):
        if k not in r:
            raise ValueError(f"missing field {k!r}")
    if r["hz"] != hz:
        raise ValueError(f"hz {r['hz']} != {hz}")
    H = r["H"]
    for k in ("action_exec", "action_script"):
        a = np.asarray(r[k], float)
        if a.shape != (H, ACT_DIM) or not np.isfinite(a).all():
            raise ValueError(f"{k}: shape {a.shape}, expected ({H}, {ACT_DIM}) finite")
    v = np.asarray(r["valid"])
    if v.shape != (H,) or not set(np.unique(v)) <= {0, 1} or v[0] != 1:
        raise ValueError("valid: H values in {0,1}, first step valid")
    if (np.diff(v) > 0).any():
        raise ValueError("valid: padding only at the end")
    for k, n in PROPRIO_KEYS:
        if len(r["proprio"].get(k, ())) != n:
            raise ValueError(f"proprio.{k}: {n} values")
    bad = set(r["aux"].get("reg", {})) - set(AUX_REG) | set(r["aux"].get("cls", {})) - set(AUX_CLS)
    if bad:
        raise ValueError(f"unknown aux names {sorted(bad)}")
    for q, key in (r.get("committed") or {}).items():
        if q not in QUESTIONS:
            raise ValueError(f"committed: unknown question {q}")


def proprio_vec(p: dict) -> np.ndarray:
    return np.concatenate([np.asarray(p[k], np.float32) for k, _ in PROPRIO_KEYS])


def aux_vecs(aux: dict):
    """(reg[AUX_REG] scaled, reg_mask, cls[AUX_CLS], cls_mask); null / missing -> masked."""
    reg = aux.get("reg", {})
    cls = aux.get("cls", {})
    r = np.array([0.0 if reg.get(n) is None else reg[n] / AUX_REG_SCALE for n in AUX_REG], np.float32)
    rm = np.array([reg.get(n) is not None for n in AUX_REG], np.float32)
    c = np.array([0.0 if cls.get(n) is None else float(cls[n]) for n in AUX_CLS], np.float32)
    cm = np.array([cls.get(n) is not None for n in AUX_CLS], np.float32)
    return r, rm, c, cm


def verify_vecs(truth: dict | None):
    """(y[VERIFY_PREDS], mask); a missing row / None value -> masked."""
    truth = truth or {}
    y = np.array([0.0 if truth.get(n) is None else float(truth[n]) for n in VERIFY_PREDS], np.float32)
    m = np.array([truth.get(n) is not None for n in VERIFY_PREDS], np.float32)
    return y, m


# ------------------------------------------------------------------------------------------ vocab / norm
class Vocab:
    """Discrete condition ids (0 = unknown / none). Saved in the checkpoint config."""

    def __init__(self, names=()):
        self.ids = {}
        for n in names:
            self.add(n)

    def add(self, n):
        if n not in self.ids:
            self.ids[n] = len(self.ids) + 1
        return self.ids[n]

    def get(self, n):
        return self.ids.get(n, 0)

    def __len__(self):
        return len(self.ids) + 1

    def to_json(self):
        return sorted(self.ids, key=self.ids.get)

    @classmethod
    def from_json(cls, names):
        return cls(names)


def dec_name(q, key):
    return f"{q}={key}"


def dec_ids(committed: dict, vocab: Vocab) -> list:
    """One id per QUESTIONS slot (0 if the question has no committed decision)."""
    return [vocab.get(dec_name(q, committed[q])) if committed.get(q) is not None else 0 for q in QUESTIONS]


class ActionNorm:
    """absolute: z = (a - mean) / std; residual: z = clip((exec - script) / xi, -1, 1). Proprio: (p - mean) / std."""

    XI_DEFAULT = [0.05] * 7 + [0.005]  # rad / m per 30 Hz step [assumption; §35 bound comes from the projection]

    def __init__(self, mode="absolute", mean=None, std=None, xi=None, p_mean=None, p_std=None):
        if mode not in ("absolute", "residual"):
            raise ValueError(mode)
        self.mode = mode
        self.mean = np.zeros(ACT_DIM, np.float32) if mean is None else np.asarray(mean, np.float32)
        self.std = np.ones(ACT_DIM, np.float32) if std is None else np.asarray(std, np.float32)
        self.xi = np.asarray(self.XI_DEFAULT if xi is None else xi, np.float32)
        self.p_mean = np.zeros(PROPRIO_DIM, np.float32) if p_mean is None else np.asarray(p_mean, np.float32)
        self.p_std = np.ones(PROPRIO_DIM, np.float32) if p_std is None else np.asarray(p_std, np.float32)

    @classmethod
    def fit(cls, rows, mode="absolute", xi=None):
        acts = np.concatenate([np.asarray(r["action_exec"], np.float32)[np.asarray(r["valid"]) > 0] for r in rows])
        pro = np.stack([proprio_vec(r["proprio"]) for r in rows])
        floor = np.array([1e-3] * 7 + [1e-4], np.float32)
        return cls(mode, acts.mean(0), np.maximum(acts.std(0), floor), xi, pro.mean(0),
                   np.maximum(pro.std(0), 1e-3))

    def target(self, exec_, script):
        """Normalized flow-matching target [H, 8] and the fraction of residual entries clipped by xi."""
        e, s = np.asarray(exec_, np.float32), np.asarray(script, np.float32)
        if self.mode == "absolute":
            return (e - self.mean) / self.std, 0.0
        z = (e - s) / self.xi
        return np.clip(z, -1.0, 1.0), float((np.abs(z) > 1.0 + 1e-6).mean())

    def cond_script(self, script):
        """Scripted chunk as an expert input (residual mode), normalized like absolute actions."""
        return (np.asarray(script, np.float32) - self.mean) / self.std

    def action(self, z, script=None):
        """Normalized expert output -> executable 8-D command chunk."""
        z = np.asarray(z, np.float32)
        if self.mode == "absolute":
            return z * self.std + self.mean
        return np.asarray(script, np.float32) + np.clip(z, -1.0, 1.0) * self.xi

    def proprio(self, p):
        return (proprio_vec(p) - self.p_mean) / self.p_std

    def to_json(self):
        return {"mode": self.mode, "mean": self.mean.tolist(), "std": self.std.tolist(), "xi": self.xi.tolist(),
                "p_mean": self.p_mean.tolist(), "p_std": self.p_std.tolist()}

    @classmethod
    def from_json(cls, d):
        return cls(**d)


# ------------------------------------------------------------------------------------------ samples
def make_sample(row: dict, line: dict | None, items: list, state: str = "IMG", wrist: bool = True,
                image_root: str = "", hz: int = HZ) -> dict:
    """Join one R2 row with its pool line and the stage-A decision items of that snapshot. The committed
    decisions default to the (single) decision labels of the items (training = teacher forcing)."""
    check_row(row, hz)
    committed = dict(row.get("committed") or {})
    for it in items:
        if it["question"] not in committed and len(it["target"]) == 1:
            committed[it["question"]] = it["target"][0]
    arm = row.get("arm", "right")
    ctx = None
    if line is not None:
        from ..jevcall import canonicalize  # the same state string the DecCall items carry
        ctx = {"text": canonicalize(prompt_state(line, state)), "images": images_of(line, arm, wrist, image_root)}
    return {"key": f"{row['kind']}_ep{row['seed']}_k{row['k']}", "split": items[0]["split"] if items else
            (line or {}).get("split"), "items": items, "context": ctx, "committed": committed,
            "skill_id": row["skill_id"], "phase_id": row["phase_id"], "proprio": row["proprio"],
            "action_exec": row["action_exec"], "action_script": row["action_script"], "valid": row["valid"],
            "aux": row["aux"], "H": row["H"], "verify": (row.get("verify") or {}).get("truth")}


def read_rows(path: str) -> dict:
    out = {}
    for x in open(path, encoding="utf-8"):
        r = json.loads(x)
        out[(r["seed"], r["kind"], r["k"])] = r
    return out


def stageb_path(folder: str) -> str:
    return folder.rstrip("/\\") + ".stageb.jsonl"


def load_stageb(pool_dir: str, rows_path: str | None = None, labels_v2: str | None = None, state: str = "IMG",
                wrist: bool = True, dev_val_seeds=None) -> list:
    """Stage-B samples of one pool folder: R2 rows (<folder>.stageb.jsonl) x pool lines x stage-A decision items
    (labels_v2 targets, same prompt state and images as the context). Pool `oracle` is never read (stagea_data)."""
    import glob
    from .stagea_data import build_items, labels_v2_factory
    rows = read_rows(rows_path or stageb_path(pool_dir))
    src_make = labels_v2_factory(labels_v2)
    out = []
    for p in sorted(glob.glob(f"{pool_dir}/ep*.jsonl"), key=lambda x: int(os.path.basename(x)[2:-6])):
        seed = int(os.path.basename(p)[2:-6])
        lines = [json.loads(x) for x in open(p, encoding="utf-8")]
        src = src_make(pool_dir, seed)
        for ln in lines:
            row = rows.get((ln["seed"], ln.get("kind"), ln["k"]))
            if row is None:
                continue
            items = []
            if src is not None and ln.get("decision"):
                items = build_items([ln], src, lambda x: prompt_state(x, state), 0, dev_val_seeds)
                ims = images_of(ln, row.get("arm", "right"), wrist, pool_dir)
                for it in items:
                    it["images"] = ims
            s = make_sample(row, ln, items, state, wrist, pool_dir)
            if s["split"] is None or s["split"] not in ("train", "val"):
                from .stagea_data import split_of
                s["split"] = split_of(ln, dev_val_seeds)
            out.append(s)
    return out


# ------------------------------------------------------------------------------------------ synthetic source
SYN_DIRS = {"dir_xy": ("plus_x", "minus_x"), "dir_z": ("up", "down"), "mag_coarse": ("small", "large")}


def synthetic_rows(n: int, H: int = H_DEFAULT, seed: int = 0, img_dir: str | None = None, native: bool = True):
    """Mock R2 data with learnable structure (smoke only; NOT a result): a hidden goal offset g (m) is drawn in
    the head image as a square (position = g), the decisions are sign/size of g, the aux targets are g, and the
    teacher chunk moves the joints toward a g-dependent pose. Returns samples in make_sample format."""
    rng = np.random.default_rng(seed)
    W = np.asarray(rng.normal(0, 1, (3, 7)), np.float32)
    out = []
    for i in range(n):
        g = rng.uniform(-0.1, 0.1, 3).astype(np.float32)
        q = rng.normal(0, 0.3, 7).astype(np.float32)
        grip = float(rng.choice([0.0, 0.08]))
        goal = q + 0.5 * (g @ W)
        s = np.linspace(1.0 / H, 1.0, H, dtype=np.float32)[:, None]
        arm = q + s * (goal - q)
        script = np.concatenate([arm, np.full((H, 1), grip, np.float32)], 1)
        exec_ = script.copy()
        exec_[:, :7] += 0.02 * np.tanh(g[0] * 10) * s  # a small consistent "correction" for residual mode
        valid = [1] * H
        if i % 7 == 3:
            valid = [1] * (H - 4) + [0] * 4
        committed = {"dir_xy": SYN_DIRS["dir_xy"][int(g[0] < 0)], "dir_z": SYN_DIRS["dir_z"][int(g[2] < 0)],
                     "mag_coarse": SYN_DIRS["mag_coarse"][int(np.linalg.norm(g) > 0.1)]}
        row = {"seed": 90000 + i, "kind": "SYN", "k": 0, "hz": HZ, "H": H, "arm": "right",
               "skill_id": "pick", "phase_id": ("approach", "grasp")[i % 2],
               "proprio": {"q": q.tolist(), "qd": rng.normal(0, 0.1, 7).tolist(), "tau": rng.normal(0, 1, 7).tolist(),
                           "grip": [grip, 0.0]},
               "action_exec": exec_.tolist(), "action_script": script.tolist(), "valid": valid,
               "aux": {"reg": {"g2goal_dx": float(g[0]), "g2goal_dy": float(g[1]), "g2goal_dz": float(g[2]),
                               "g2goal_dist": float(np.linalg.norm(g))},
                       "cls": {"gripper_open": int(grip > 0)}},
               "verify": {"truth": {"gripper_open": bool(grip > 0), "lifted_t": bool(g[2] > 0)}}}
        text = f"t_state: f{i}  contract: c1  stage: S1 \"pick up mug o3\"\nrobot: gripper=" \
               f"{'open' if grip > 0 else 'closed'} arm=moving"
        ims = []
        if img_dir is not None:
            ims = _syn_images(img_dir, i, g, native)
        split = "val" if i % 5 == 4 else "train"
        items = []
        for q_, key in committed.items():
            names = list(SYN_DIRS[q_])
            items.append({"key": row["kind"] + f"_ep{row['seed']}_k0", "question": q_, "split": split,
                          "text": f"{text}\n\nQuestion ({q_}): which option?\nOptions:\n" +
                          "\n".join(f"- {m}" for m in names), "images": ims, "names": names, "target": [key], "ne": False, "source": "synthetic"})
        smp = make_sample(row, None, items)
        smp["context"] = {"text": text, "images": ims}
        smp["split"] = split
        out.append(smp)
    return out


NATIVE = {"cam_head": (672, 376), "cam_wrist_right": (424, 240)}  # §59 native sizes (W, H)


def _syn_images(img_dir, i, g, native=True):
    from PIL import Image
    os.makedirs(img_dir, exist_ok=True)
    paths = []
    for cam, scale in (("cam_head", 1.0), ("cam_wrist_right", 2.0)):
        w, h = NATIVE[cam] if native else (96, 64)
        a = np.full((h, w, 3), 40, np.uint8)
        cx = int(w / 2 + scale * g[0] / 0.1 * w / 3)
        cy = int(h / 2 - scale * g[1] / 0.1 * h / 3)
        r = max(2, int((4 + 20 * (g[2] + 0.1)) * w / 96))
        a[max(0, cy - r):max(0, cy + r), max(0, cx - r):max(0, cx + r)] = (220, 40, 40)
        p = os.path.join(img_dir, f"syn{i:05d}_{cam}.png")
        Image.fromarray(a).save(p)
        paths.append([CAM_LABEL[cam], p])
    return paths


def split_samples(samples):
    return [s for s in samples if s["split"] == "train"], [s for s in samples if s["split"] == "val"]


def build_vocabs(samples):
    dec, skill, phase = Vocab(), Vocab(), Vocab()
    for s in samples:
        for q, k in s["committed"].items():
            dec.add(dec_name(q, k))
        for it in s["items"]:
            for n in it["names"]:
                dec.add(dec_name(it["question"], n))
        skill.add(s["skill_id"])
        phase.add(s["phase_id"])
    return {"dec": dec, "skill": skill, "phase": phase}


def isfinite_all(x) -> bool:
    return all(math.isfinite(v) for v in np.asarray(x, float).ravel())
