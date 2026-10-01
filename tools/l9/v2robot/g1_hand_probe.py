"""(pod) G1 Dex3-1 hand geometry probe: fingertip points of thumb / index / middle in the palm frame at a few joint
postures, to decide whether a thumb-vs-(index+middle) pinch can be modelled as a parallel gripper."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from urdf_fk import Urdf  # noqa: E402

U = Urdf("/data/harvest/l9v2/pylib/curobo/content/assets/robot/g1/g1_29dof_with_hand_rev_1_0.urdf")
for side in ("right", "left"):
    palm = f"{side}_hand_palm_link"
    print("==", side)
    for k in ("palm", "thumb_0", "thumb_1", "thumb_2", "index_0", "index_1", "middle_0", "middle_1"):
        ln = palm if k == "palm" else f"{side}_hand_{k}_link"
        p = U.link_points(ln, palm, {})
        print(f"{k:9s} min {np.round(p.min(0), 4)} max {np.round(p.max(0), 4)}")
    for j in ("thumb_0", "thumb_1", "thumb_2", "index_0", "index_1", "middle_0", "middle_1"):
        jj = U.joints[f"{side}_hand_{j}_joint"]
        print(j, "axis", jj["axis"], "lim", jj["lower"], jj["upper"])
