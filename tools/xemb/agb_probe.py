"""AgiBot structure probe (user-log 163 step 1): for kept episodes, list the proprio file(s), h5 keys + shapes (end
effector position / gripper fields), head camera parameter files, and the head video frame count / size.
usage (pod): python -m xemb.agb_probe KEEP_DIR OUT_JSON"""
from __future__ import annotations

import glob
import json
import os
import sys


def h5_tree(path):
    import h5py
    out = {}
    with h5py.File(path, "r") as f:
        def visit(name, obj):
            if hasattr(obj, "shape"):
                out[name] = [list(obj.shape), str(obj.dtype)]
        f.visititems(visit)
    return out


def main(keep, outp):
    res = {}
    pro = sorted(glob.glob(os.path.join(keep, "proprio", "**", "*"), recursive=True))
    res["proprio_files"] = [p for p in pro if os.path.isfile(p)][:10]
    h5s = [p for p in pro if p.endswith((".h5", ".hdf5"))]
    if h5s:
        res["h5_example"] = h5s[0]
        res["h5_tree"] = h5_tree(h5s[0])
    par = sorted(glob.glob(os.path.join(keep, "params", "**", "head_*"), recursive=True))
    res["param_files"] = par[:10]
    vids = sorted(glob.glob(os.path.join(keep, "obs", "*", "*", "videos", "head_color.mp4")))
    res["head_videos"] = len(vids)
    try:
        import av
    except ImportError:  # venv_train has no PyAV: the video fields are filled by the converter's own decode
        av = None
    if vids and av is not None:
        with av.open(vids[0]) as c:
            s = c.streams.video[0]
            res["head_video"] = {"path": vids[0], "frames": s.frames, "w": s.codec_context.width,
                                 "h": s.codec_context.height, "fps": float(s.average_rate or 0)}
    json.dump(res, open(outp, "w"), indent=1)
    print(json.dumps(res, indent=1)[:3000])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
