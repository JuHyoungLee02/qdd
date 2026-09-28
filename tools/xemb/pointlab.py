"""Point-only labels for every D-suitable source (user-log 164). One row = one image + one named point:
  answer {"point": [x, y]} in 0-1000 image coordinates (x right, y down); NO xyz, depth or height-intent labels.
  qa_kind: "obj_point" (the named object; preferred when the source has a language instruction / annotation),
           "place_point" (the named place / receptacle), "ee_point" (the gripper tip; auxiliary).
Tags on every row: source ("<dataset>/<robot>"), frame "pixel", license, view ("head" | "wrist" | "third"),
nc (True for non-commercial licences: such rows are never sent to Astra), astra_ok (= not nc).
Gates applied by the converters before calling row():
  G-proj  projected point within 5 px of the verified position (exact sim / calibration: 0 px by construction; T1+T4
          self-calibration: its held-out gate; SAM verification sample: the point lies on the SAM mask of the name).
  G-name  generic names dropped (GENERIC); the noun must be checkable: objects_real.name_check when the source gives
          geometry, otherwise the lexical check below (a concrete head noun, not a place word).
usage: import only (converters build rows with row())."""
from __future__ import annotations

import json
import re

GENERIC = {"object", "objects", "target", "item", "items", "thing", "things", "place", "it", "them", "something",
           "designated object", "the object", "stuff", "one"}
PLACE_WORDS = {"left", "right", "front", "back", "middle", "center", "top", "bottom", "side", "table", "goal",
               "goal position", "position", "location", "area", "region", "here", "there"}
NC_LICENSES = ("cc-by-nc", "cc by-nc", "nc-sa", "non-commercial", "noncommercial")
_ART = re.compile(r"^(the|a|an|some|one)\s+", re.I)


def clean_name(name: str | None) -> str | None:
    """Lower-case, strip articles / punctuation; None when generic or not a concrete noun phrase."""
    if not name:
        return None
    n = _ART.sub("", re.sub(r"[_\s]+", " ", str(name)).strip().strip(".,;:").lower())
    n = re.sub(r"\s+", " ", n)
    if not n or n in GENERIC or n in PLACE_WORDS or len(n) > 60 or len(n.split()) > 6:
        return None
    if n.split()[-1] in GENERIC | {"position", "goal"}:
        return None
    return n


def is_nc(license_: str) -> bool:
    return any(k in (license_ or "").lower() for k in NC_LICENSES)


def row(source: str, license_: str, view: str, image: str, W: int, H: int, uv, name: str | None, kind: str, rid: str,
        arm: str = "", extra: dict | None = None) -> dict | None:
    """One point row, or None when the point is outside the image or the name fails G-name (ee_point needs no name)."""
    u, v = float(uv[0]), float(uv[1])
    if not (0 <= u < W and 0 <= v < H):
        return None
    if kind == "ee_point":
        what = f"the {arm + ' ' if arm else ''}gripper's fingertip centre"
    else:
        nm = clean_name(name)
        if nm is None:
            return None
        what = f"the {nm}" if kind == "obj_point" else f"the {nm} (where the held object goes)"
    nc = is_nc(license_)
    p = [int(round(u * 1000 / W)), int(round(v * 1000 / H))]
    prompt = (f"source: {source}\nframe: pixel\nImage 1: {view} camera, {W}x{H} px.\n"
              f"Point to {what} in image 1. Answer in 0-1000 normalised image coordinates (x to the right, y down).\n"
              f"Return JSON only.")
    r = {"id": rid, "kind": "qa_xemb", "qa_kind": kind, "source": source, "frame": "pixel", "license": license_,
         "view": view, "nc": nc, "astra_ok": not nc, "images": [image], "coords": "n1000", "prompt": prompt,
         "answer": json.dumps({"point": p})}
    if kind != "ee_point":
        r["name"] = clean_name(name)
    if extra:
        r.update(extra)
    return r
