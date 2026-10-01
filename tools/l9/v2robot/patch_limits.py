"""Add cspace.position_limit_clip (LIMIT_MARGIN on the 7 arm joints, 0 elsewhere) to built configs in place.
usage: python tools/l9/v2robot/patch_limits.py <yml>..."""
import sys

import yaml

MARGIN = 0.03
for path in sys.argv[1:]:
    txt = open(path).read()
    head = "".join(line + "\n" for line in txt.splitlines() if line.startswith("#"))
    d = yaml.safe_load(txt)
    k = d["robot_cfg"]["kinematics"]
    lock = set(k["lock_joints"])
    names = k["cspace"]["joint_names"]
    k["cspace"]["position_limit_clip"] = MARGIN  # scalar: v0.8.0 applies it to the active (unlocked) joints only
    with open(path, "w", newline="\n") as f:
        f.write(head)
        yaml.safe_dump(d, f, sort_keys=False, default_flow_style=None)
    print(path, "position_limit_clip", MARGIN)
