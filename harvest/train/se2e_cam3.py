"""E-CAM3 OPT-IN input: head + BOTH wrists for the fused VLA decision (docs/stage3/prereg_cam3.md; spec
2026-09-26-astra-vla-coupling-design §12). Nothing here is read by the default training / runtime path.

The baseline S-E2E sample shows head + the ACTIVE wrist (§57; both wrists already for bimanual rows). `cam3@v1`
appends the OTHER wrist after them, so the first two images and their labels stay exactly the baseline's:
  [head camera:, <arm> wrist camera (active arm):, <other> wrist camera (other arm):]
Bimanual samples (already head + right + left) are unchanged. The other-wrist frames are decoded from the raw ROBOTIS
videos by tools/cam3/build_cam3.py (same decoder / rotation / JPEG quality as tools/se2e_convert.py) into
<cam3-root>/img_cam3/<kind>/ep<NNNNNN>/k<KKKK>_<cam>.jpg; a missing frame is an error (the feasibility check found
none). Layout id LAYOUT_CAM3 and the file hash go into prompt_config (new sha: a cam3 checkpoint never passes as a
two-camera one).

CLI (same commands / options as stageb_train, plus --cam3 cam3@v1 --cam3-root DIR):
  python -m harvest.train.se2e_cam3 train|predict|evalck ... --cam3 cam3@v1 --cam3-root /data/harvest/data/cam3
With --cam3 off (default) this is stageb_train.main unchanged (test).
"""
from __future__ import annotations

import hashlib
import json
import os

CAM3_VER = "cam3@v1"
LAYOUT_CAM3 = "D27v3-cam3"
CAM3_FILES = ("harvest/train/se2e_cam3.py",)
CAM3_ROOT = "/data/harvest/data/cam3"
OTHER_LABEL = {"cam_wrist_left": "left wrist camera (other arm):", "cam_wrist_right": "right wrist camera (other arm):"}
ACTIVE_LABEL = {"right": "right wrist camera (active arm):", "left": "left wrist camera (active arm):"}


def frame_rel(kind: str, ep: int, k: int, cam: str) -> str:
    return f"img_cam3/{kind}/ep{int(ep):06d}/k{int(k):04d}_{cam}.jpg"


def key_parts(key: str):
    kind, ep, k = key.split("_")
    return kind, int(ep[2:]), int(k[1:])


def other_wrist(s: dict):
    """The wrist camera the baseline does not show (None for bimanual samples: both wrists already shown)."""
    if len(s["context"]["images"]) == 3:
        return None
    return "cam_wrist_" + ("left" if s.get("arm", "right") == "right" else "right")


def apply_cam3(samples, cam3_root: str = CAM3_ROOT) -> dict:
    """In place: append the other wrist to every non-bimanual sample's context and item images (one shared list)."""
    st = {"n": 0, "added": 0, "bimanual_unchanged": 0}
    for s in samples:
        st["n"] += 1
        ims = s["context"]["images"]
        cam = other_wrist(s)
        if cam is None:
            st["bimanual_unchanged"] += 1
            continue
        if len(ims) != 2 or ims[1][0] != ACTIVE_LABEL[s.get("arm", "right")]:
            raise ValueError(f"{s['key']}: images {[x[0] for x in ims]} do not match arm {s.get('arm')}")
        kind, ep, k = key_parts(s["key"])
        path = os.path.join(cam3_root, frame_rel(kind, ep, k, cam))
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        new = [list(x) for x in ims] + [[OTHER_LABEL[cam], path]]
        s["context"]["images"] = new
        for it in s["items"]:
            it["images"] = new
        st["added"] += 1
    return st


def _file_sha(paths):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return {p: hashlib.sha256(open(os.path.join(root, p), "rb").read()).hexdigest()[:12] for p in paths}


def mark_prompt_config(cfg: dict) -> dict:
    """A copy of a prompt_config with the cam3 marker, layout id and option-file hash; sha recomputed as
    stageb_train.prompt_config_t does (sha256 of the sorted json without 'sha')."""
    out = {k: v for k, v in cfg.items() if k != "sha"}
    out.update(cam3=CAM3_VER, layout3=LAYOUT_CAM3, cam3_files_sha=_file_sha(CAM3_FILES))
    out["sha"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()[:12]
    return out


# ------------------------------------------------------------------------------------------ CLI wrapper
def build_parser():
    from . import stageb_train as TR
    ap = TR.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    for name in ("train", "predict", "evalck"):
        p = sub.choices[name]
        p.add_argument("--cam3", default="off", choices=("off", CAM3_VER), help="E-CAM3: head + both wrists")
        p.add_argument("--cam3-root", default=CAM3_ROOT, help="<root>/img_cam3/... other-wrist frames")
    return ap


def install(TR, a) -> None:
    """Patch stageb_train for a --cam3 run: the loaded samples get the other wrist, prompt_config gets the marker."""
    if getattr(a, "cam3", "off") == "off":
        return
    if a.data != "se2e":
        raise SystemExit("--cam3: --data se2e only")
    if not TR.temporal_on(a):
        raise SystemExit("--cam3: with the motion line (prereg_cam3 cells)")
    load0, pc0 = TR._load_data, TR.prompt_config_t

    def _load_data(args):
        samples, hz, tr, va = load0(args)
        st = apply_cam3(samples, args.cam3_root)
        print(json.dumps({"event": "cam3_apply", **st}), flush=True)
        return samples, hz, tr, va

    def prompt_config_t(*x, **kw):
        return mark_prompt_config(pc0(*x, **kw))
    TR._load_data, TR.prompt_config_t = _load_data, prompt_config_t


def main(argv=None):
    from . import stageb_train as TR
    a = build_parser().parse_args(argv)
    install(TR, a)
    {"smoke": TR.cmd_smoke, "train": TR.cmd_train, "evalck": TR.cmd_evalck, "predict": TR.cmd_predict}[a.cmd](a)


if __name__ == "__main__":
    main()
