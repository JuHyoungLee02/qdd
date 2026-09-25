"""Kinematic fake world + a geometry-cheating fake model for the probe's end-to-end tests (no Isaac).

Scene: textured table plane (z = TZ) and objects as axis-aligned boxes, ray-cast for RGB (texture = stereo-matchable)
and z-depth. TCP follows the command exactly; the target is grasped when the pads close around it."""

import numpy as np

from harvest.astra_motion import geometry as G
from harvest.astra_motion.harness import Obs, obj_height
from harvest.sim.scene import OBJ_GEOM
from harvest.sim.tasks import TASKS

TZ = 0.85
W_OPEN, W_CLOSE = 0.107, 0.050


def look_at(pos, target, name, W, H, fx):
    z = np.asarray(target, float) - np.asarray(pos, float)
    z /= np.linalg.norm(z)
    x = np.cross(z, [0, 0, 1.0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return G.Cam(name, W, H, fx, fx, W / 2, H / 2, np.stack([x, y, z], 1), np.asarray(pos, float))


HEAD = look_at((0.08, 0.02, 1.55), (0.45, -0.15, TZ), "head", 672, 376, 367.0)
LEFT = look_at((0.20, 0.30, TZ + 0.35), (0.45, 0.0, TZ), "wrist_left", 424, 240, 223.4)


def _tex(a, b):
    i, j = np.floor(a / 0.002).astype(np.int64), np.floor(b / 0.002).astype(np.int64)
    return (((i * 73856093) ^ (j * 19349663)) % 251).astype(np.float64)


def raycast(cam, boxes):
    iu, iv = np.meshgrid(np.arange(cam.W) + G.PIX_C, np.arange(cam.H) + G.PIX_C)
    dc = np.stack([(iu - cam.cx) / cam.fx, (iv - cam.cy) / cam.fy, np.ones_like(iu)], -1)
    d = dc @ cam.R.T
    o = cam.t
    with np.errstate(divide="ignore", invalid="ignore"):
        s = (TZ - o[2]) / d[..., 2]
    s[~np.isfinite(s) | (s <= 0)] = np.inf
    face = np.zeros(s.shape, int)
    for lo, hi in boxes:
        with np.errstate(divide="ignore", invalid="ignore"):
            t1, t2 = (lo - o) / d, (hi - o) / d
        tmin, tmax = np.nanmax(np.minimum(t1, t2), -1), np.nanmin(np.maximum(t1, t2), -1)
        hit = (tmax >= tmin) & (tmin > 0) & (tmin < s)
        s = np.where(hit, tmin, s)
        face = np.where(hit, 1, face)
    p = o + d * np.where(np.isfinite(s), s, 0)[..., None]
    img = _tex(p[..., 0] + 0.3 * p[..., 2], p[..., 1] + 0.7 * p[..., 2])
    img = np.where(np.isfinite(s), img, 0)
    return np.repeat(img[..., None], 3, -1).astype(np.uint8), s


class FakeWorld:
    dt = 0.05
    table_z = TZ
    w_open, w_close = W_OPEN, W_CLOSE
    quat0 = (0.7071067811865476, 0.0, 0.0, 0.7071067811865476)  # top-down grasp yaw pi/2

    def reset(self, seed, task):
        self.task = TASKS[task]
        rng = np.random.default_rng(seed)
        self.pos = {self.task.target: np.array([0.42 + rng.uniform(-0.02, 0.02), -0.20, TZ]),
                    self.task.place: np.array([0.44, -0.38, TZ])}
        if self.task.target != "o3":
            self.pos["o3"] = np.array([0.55, -0.05, TZ])
        for k in self.pos:  # centres
            self.pos[k][2] = TZ + obj_height(k) / 2 if k != "o11" else TZ + 0.001
        self.tcp = np.array([0.34, -0.25, TZ + 0.25])
        self.width, self.held, self.offset, self.on_place, self.t = W_OPEN, False, None, False, 0.0
        self.last_obs = None

    def task_info(self):
        return {"instruction": self.task.instruction, "tgt": self.task.target, "place": self.task.place,
                "present": list(self.pos)}

    def _boxes(self):
        out = []
        for k, c in self.pos.items():
            he = np.array(OBJ_GEOM[k]["half_extents"])
            out.append((c - he, c + he))
        return out

    def wrist_cam(self):
        return look_at(self.tcp + [-0.06, 0, 0.10], self.tcp + [0.12, 0, -0.15], "wrist", 424, 240, 223.4)

    def observe(self, depth=False):
        cams = {"head": HEAD, "wrist_left": LEFT, "wrist": self.wrist_cam()}
        rgb, dep = {}, {}
        for n, c in cams.items():
            rgb[n], dep[n] = raycast(c, self._boxes())
        self.last_obs = Obs(self.t, rgb, dep if depth else None, cams, self.tcp.copy(), self.width)
        return self.last_obs

    def frame(self):
        return {"head": raycast(HEAD, self._boxes())[0], "wrist": raycast(self.wrist_cam(), self._boxes())[0],
                "wrist_cam": self.wrist_cam()}

    def step(self, cmd, width, quat=None):
        self.tcp, self.width = np.asarray(cmd, float).copy(), float(width)
        tg = self.task.target
        h = obj_height(tg)
        if not self.held and self.width < W_OPEN - 0.005:
            c = self.pos[tg]
            top = c[2] + h / 2
            if np.linalg.norm(self.tcp[:2] - c[:2]) <= 0.015 and top - 0.045 <= self.tcp[2] <= top:
                self.held, self.offset, self.on_place = True, c - self.tcp, False
        if self.held and self.width >= W_OPEN - 0.005:
            self.held = False
            c, p = self.pos[tg], self.pos[self.task.place]
            he = OBJ_GEOM[self.task.place]["half_extents"]
            inside = abs(c[0] - p[0]) <= he[0] and abs(c[1] - p[1]) <= he[1]
            base = TZ + (obj_height(self.task.place) if inside and self.task.place != "o11" else 0.0)
            c[2] = base + h / 2
            self.on_place = inside
        if self.held:
            self.pos[tg] = self.tcp + self.offset
        self.t += self.dt

    def status(self):
        tg, pl = self.task.target, self.task.place
        c = self.pos[tg]
        hold = self.held and self.width < W_OPEN - 0.005
        pred = {f"holding({tg})": hold, f"lifted({tg})": bool(hold and c[2] - obj_height(tg) / 2 >= TZ + 0.03),
                f"on({tg},{pl})": bool(self.on_place and not self.held), f"upright({tg})": True}
        return {"t": round(self.t, 6), "tcp": self.tcp.copy(), "grip_w": self.width, "pred": pred,
                "obj": {k: v.copy() for k, v in self.pos.items()}, "gripper_contacts": {tg} if self.held else set()}

    def run_oracle(self, on_tick):
        from harvest.astra_motion.executor import MotionExec, Target
        ex = MotionExec(self.dt, TZ, self.tcp, W_OPEN, W_CLOSE)
        phase = "approach"
        while self.t < 60:
            if not ex.busy:
                pts = TruthModel(self).remaining_points()
                if not pts:
                    break
                ex.load([Target(p, g) for p, g in pts], self.t)
            cmd, w, ev = ex.tick(self.t, self.tcp)
            for e in ev:
                if e["event"] in ("close", "open"):
                    phase = e["event"]
            self.step(cmd, w)
            on_tick(self.status(), phase)
            if self.status()["pred"].get(f"on({self.task.target},{self.task.place})") and self.t > 1 and \
                    not self.held and phase == "open" and not ex.busy:
                for _ in range(30):
                    self.step(self.tcp, W_OPEN)
                    on_tick(self.status(), phase)
                break
        return {"n_ticks": int(self.t / self.dt)}


from harvest.astra_motion.truth import Rep, TruthModel  # noqa: E402

CheatModel = TruthModel  # the package's ground-truth model runs on the fake world too


class GarbageModel:
    name = "garbage"

    def ask(self, text, images, meta):
        return Rep("I think the robot should grab the mug.")
