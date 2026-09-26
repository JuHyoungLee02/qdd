"""No-depth (ND) prompt variants of E-PT (user-log: "거리정보나 이런거 없이도 되면 ...", prereg_pt.md §1): RGB only,
no depth, no scene distance information from code. Derived from astra-solo@v2 by removing everything that encodes the
scene's metric layout (the table height line, the table grid and the drop line, which code draws at the known table
height); the head image shows only the TCP ring (robot self-information from the calibration and joint angles, kept
per canon §97). The robot frame, gripper geometry, camera poses, definitions, task and object list stay.
  nd-xyz@v1       xyz eef output (v2 commands) without grid / table height
  nd-est@v1       first an "estimates" block (the model's own table height, target base xy / height / width, place xy /
                  top), then the v2 command -- trained on free sim ground truth (ND-2)
  nd-pt@v1        estimates, then a point command whose target top height `top_z` is the model's own estimate; code
                  lifts the pixel ray to that height (no depth)
The executor's workspace clip still uses the simulator table height (a code-side safety net, not shown to the model)."""
from __future__ import annotations

import hashlib

from ..astra_motion.executor import SAFE_X, SAFE_Y
from . import prompts as V2

_TABLE_V2 = ("- Table top surface: z = {tz:.3f} m. The code keeps the TCP inside x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f}, "
             "z {z0:.3f}..{z1:.3f} m (targets beyond are clipped, and you are told).")
_TABLE_ND = ("- The table height is not given: judge it from the images. The code keeps the TCP inside x {x0:.2f}..{x1:.2f}, "
             "y {y0:.2f}..{y1:.2f} m and between just above the table and 40 cm above it (targets beyond are clipped, "
             "and you are told).")
_OVL_V2 = V2.STATIC[V2.STATIC.index("HEAD IMAGE OVERLAY"):V2.STATIC.index("DEFINITIONS")]
_OVL_ND = ("HEAD IMAGE OVERLAY (drawn by code from the camera calibration and the robot's own joint angles)\n"
           "- White ring with a black outline: the TCP now. Nothing else is drawn; the wrist image has no drawing.\n\n")
STATIC = V2.STATIC.replace(_TABLE_V2, _TABLE_ND).replace(_OVL_V2, _OVL_ND)
assert _TABLE_V2 in V2.STATIC and _OVL_V2 in V2.STATIC

EST_FIELDS = '"estimates": {"table_z": number, "target_base_xy": [x, y], "target_height_m": number, "target_width_m": number, "place_xy": [x, y], "place_top_z": number}'
EST_TEXT = ("First estimate from the images, in the robot frame (metres): the table top height table_z; the object to "
            "move: the centre of its base on the table, its height and its width; the place target: its centre and "
            "the height of its top surface. Then assess and command.\n")
_ANS_V2 = V2.ANSWER
_JSON_V2 = 'Return JSON only: {"assessment"'
ANSWERS = {
    "nd-xyz@v1": _ANS_V2,
    "nd-est@v1": "\n" + EST_TEXT + _ANS_V2.lstrip("\n").replace(_JSON_V2, 'Return JSON only: {' + EST_FIELDS + ', "assessment"'),
    "nd-pt@v1": None,  # below
}
_PT_CMD = ('"command": {"mode": "point"|"edit"|"gripper"|"stop", "point_2d": [x, y] (point only; 0-1000 in image 1, '
           'on the TOP of the object you mean), "top_z": number (point only: your estimate of the height of that top, '
           'm), "height": "above"|"grasp"|"place"|"lift" (point only), "delta_m": [dx, dy, dz] (edit only), '
           '"gripper": "keep"|"open"|"close"}')
_CMD_V2 = _ANS_V2[_ANS_V2.index('"command": {'):_ANS_V2.index(', "reason"')]
ANSWERS["nd-pt@v1"] = ANSWERS["nd-est@v1"].replace(_CMD_V2, _PT_CMD)
PT_COMMANDS = ("POINT COMMAND (instead of eef)\n- point: point_2d = [x, y] in image 1 on a 0-1000 scale (x from the "
               "left edge, y from the top edge) at the centre of the TOP of the object you mean, top_z = your estimate "
               "of that top's height (m); code moves the TCP along that pixel's ray to the target:\n"
               "  above = TCP 8 cm above that top (while holding: the held object's bottom 8 cm above it); grasp = TCP "
               "2 cm below that top; place = the held object's bottom 1 cm above that top; lift = straight up to 22 cm "
               "above your table_z (point_2d / top_z not needed).\n")
VERSIONS = tuple(ANSWERS)
PROMPT_IDS = {v: hashlib.sha256((STATIC + (PT_COMMANDS if v == "nd-pt@v1" else "") + ANSWERS[v] + V2.NOW + v)
                                .encode()).hexdigest()[:12] for v in VERSIONS}


def static(info: dict, head, w_close: float, version: str) -> str:
    txt = STATIC.format(x0=SAFE_X[0], x1=SAFE_X[1], y0=SAFE_Y[0], y1=SAFE_Y[1], wc=w_close * 100,
                      head=V2._cam(head), instruction=info["instruction"], tgt_name=_name(info["tgt"]),
                      place_rule=_rule(info), objects=_objects(info), tz=0.0, z0=0.0, z1=0.0)
    if version == "nd-pt@v1":
        assert _EEF_V2 in txt
        txt = txt.replace(_EEF_V2, "- point: see POINT COMMAND above (there is no absolute-coordinate command).").replace(
            "COMMANDS (fixed code executes them; you never command joints)",
            PT_COMMANDS + "\nCOMMANDS (fixed code executes them; you never command joints)")
    return txt


_EEF_V2 = ("- eef: move the TCP in a straight line (smooth start and stop, about 8 cm/s on average) to the absolute "
           "position_m [x, y, z]; then apply gripper: close (0.6 s), open (0.5 s) or keep. Any distance.")


def _name(k):
    from ..astra_motion.prompts import OBJ_NAME
    return OBJ_NAME[k]


def _rule(info):
    from ..astra_motion.prompts import place_rule
    return place_rule(info["place"], _name(info["place"]))


def _objects(info):
    from ..astra_motion.prompts import OBJ_DESC, OBJ_NAME
    objs = [info["tgt"], info["place"]] + [k for k in info["present"] if k not in (info["tgt"], info["place"])]
    return "\n".join(f"- {OBJ_NAME.get(k, k)}: {OBJ_DESC.get(k, 'object')}"
                     + (" (the object to move)" if k == info["tgt"] else "")
                     + (" (where to put it)" if k == info["place"] else " (obstacle)" if k != info["tgt"] else "")
                     for k in objs)


def request(version: str, info: dict, head, w_close: float, now_text: str, note: str) -> str:
    return static(info, head, w_close, version) + now_text + ANSWERS[version] + note
