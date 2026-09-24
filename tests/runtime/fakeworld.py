"""Kinematic fake world for runtime tests (no Isaac): TCP follows the command; grasp by pad position."""
import numpy as np

TZ = 0.85
HM, HR = 0.0475, 0.0075


class Kin:
    def __init__(self, w):
        self.w = w

    def tcp_pose(self):
        return self.w.tcp.copy(), np.array([np.cos(np.pi / 4), 0, 0, np.sin(np.pi / 4)])

    def ik(self, pos, quat, max_dq):
        return np.r_[pos, 0, 0, 0, 0]  # first three "joints" encode the TCP target (perfect tracking)


class FakeWorld:
    """TCP follows the command exactly; the mug is grasped when the closed pads are at the grasp height."""

    def __init__(self):
        self.tcp = np.array([0.34, -0.25, TZ + 0.25])
        self.width = 0.107
        self.mug = np.array([0.40, -0.20, HM])
        self.tray = np.array([0.45, -0.05, HR])
        self.held, self.t = False, 0.0
        self.a = np.r_[self.tcp, 0, 0, 0, 0, self.width]

    def g(self):
        return self.tcp - [0, 0, TZ]

    def m1(self):
        g = self.g()
        contacts, support = [], {}
        grasp_ok = (np.linalg.norm(g[:2] - self.mug[:2]) < 0.015 and abs(g[2] - (self.mug[2] + HM - 0.018)) < 0.012)
        if self.width < 0.08 and (self.held or grasp_ok):
            self.held = True
            contacts.append(["gripper", "o3"])
        elif self.held:  # released
            self.held = False
            if np.all(np.abs(self.mug[:2] - self.tray[:2]) < [0.09, 0.07]):
                self.mug[2] = 2 * HR + HM
        if self.held:
            self.mug = g - [0, 0, HM - 0.018]
        on_tray = (not self.held and abs(self.mug[2] - (2 * HR + HM)) < 1e-6)
        if on_tray:
            contacts.append(["o3", "o5"])
            support["o3"] = "o5"
        else:
            support["o3"] = "table" if self.mug[2] - HM <= 0.004 else None
        support["o5"] = "table"
        raw = {"grip": {"pos": list(g), "w": self.w_meas(), "effort": 5.0 if self.held else 0.0},
               "objs": {"o3": {"pos": list(self.mug), "quat": [1, 0, 0, 0], "he": [0.032, 0.032, HM]},
                        "o5": {"pos": list(self.tray), "quat": [1, 0, 0, 0], "he": [0.09, 0.07, HR]}},
               "contacts": contacts, "support": support}
        return {"raw": raw, "present": ["o3", "o5"]}

    def w_meas(self):
        """Measured pad gap: the pads stop on the mug (diameter 64 mm) while it is held."""
        return max(self.width, 0.064) if self.held else self.width

    def obs(self):
        m1 = self.m1()
        jp = self.a.copy()
        jp[7] = self.w_meas()
        return {"sim_time": self.t, "joint_pos": jp, "images": {}, "m1": m1, "kin": Kin(self),
                "table_z": TZ, "low": np.full(8, -10.0), "high": np.full(8, 10.0)}

    def step(self, a):
        self.a = np.asarray(a, float)
        self.tcp, self.width = self.a[:3].copy(), float(self.a[7])
        self.t = round(self.t + 0.01, 6)
