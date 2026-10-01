"""(pod) Inner-face profile of a finger: per 5 mm slab along the frame z axis, the min / max y of the link mesh.
usage: finger_profile.py <urdf> <frame> '<json q>' <link>"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from urdf_fk import Urdf  # noqa: E402

u = Urdf(sys.argv[1])
p = u.link_points(sys.argv[4], sys.argv[2], json.loads(sys.argv[3]), sample=20000)
for z in np.arange(p[:, 2].min(), p[:, 2].max(), 0.005):
    s = p[(p[:, 2] >= z) & (p[:, 2] < z + 0.005)]
    if len(s):
        print(f"z {z:+.3f}..{z + 0.005:+.3f}  y [{s[:, 1].min():+.4f}, {s[:, 1].max():+.4f}]  x [{s[:, 0].min():+.4f}, {s[:, 0].max():+.4f}]")
