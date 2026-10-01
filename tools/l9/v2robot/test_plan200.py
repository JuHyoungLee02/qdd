"""(pod) Owner check (10-02): from a start q, plan_pose (harvest.l9.plan9.Planner9, empty world) to (a) the TCP 10 cm
above and (b) 200 random reachable tool poses (FK of random joint configurations inside the config limits, TCP kept
in a box in front of the arm). usage: test_plan200.py <profile> <arm> q1..q7 [x0 x1 y0 y1 z0 z1]"""
import sys

import numpy as np
import torch

from harvest.l9 import curobo9 as C
from harvest.l9 import plan9 as P9

profile, arm = sys.argv[1], sys.argv[2]
q0 = np.array([float(v) for v in sys.argv[3:10]])
box = [float(v) for v in sys.argv[10:16]] if len(sys.argv) > 15 else None
pl = P9.Planner9(C.load_config(profile, arm), self_collision=True)
pl.world({"cuboid": {}})
lo, hi = pl._limits()
print("start inside limits:", bool(np.all((q0 >= lo) & (q0 <= hi))))
from curobo.types import JointState  # noqa: E402
kin = pl.ik_solver.kinematics if hasattr(pl, "ik_solver") else None
if kin is None:
    from curobo._src.robot.kinematics.kinematics import Kinematics
    from curobo._src.robot.kinematics.kinematics_cfg import KinematicsCfg
    kin = Kinematics(KinematicsCfg.from_data_dict(C.load_config(profile, arm)["robot_cfg"]["kinematics"]))
tf = C.tool_frame(profile, arm)


def fk(Q):
    st = kin.compute_kinematics(JointState.from_position(torch.tensor(Q, device="cuda", dtype=torch.float32),
                                                         joint_names=list(pl.joint_names)))
    p = st.tool_poses.get_link_pose(tf)
    pos, qt = p.position.cpu().numpy(), p.quaternion.cpu().numpy()
    out = []
    for a, b in zip(pos, qt):
        w, x, y, z = b
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        T = np.eye(4)
        T[:3, :3], T[:3, 3] = R, a
        out.append(T)
    return out


T0 = fk(q0[None])[0]
T1 = T0.copy()
T1[2, 3] += 0.10
Q = pl.pose(q0, T1)
print("plan to +10 cm:", "ok" if Q is not None else "FAIL", "" if Q is None else f"{len(Q)} pts, max step "
      f"{P9.max_step(Q):.3f} rad")
rng = np.random.default_rng(11)
targets = []
while len(targets) < 200:
    Qr = lo + (hi - lo) * rng.random((2000, len(lo)))
    for T in fk(Qr):
        if box is None or (box[0] <= T[0, 3] <= box[1] and box[2] <= T[1, 3] <= box[3] and box[4] <= T[2, 3] <= box[5]):
            targets.append(T)
            if len(targets) == 200:
                break
ok_ik = pl.ik(np.array(targets))[0]
reach = [T for T, o in zip(targets, ok_ik) if o]
n_ok = sum(pl.pose(q0, T) is not None for T in reach)
print(f"random reachable poses (FK of random q, box {box}): collision-free IK {len(reach)}/200, "
      f"plan_pose from start {n_ok}/{len(reach)} = {100.0 * n_ok / max(1, len(reach)):.1f} %")
