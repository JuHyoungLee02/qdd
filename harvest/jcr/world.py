"""JCR data world (pod only): the E-Couple SoloWorld with ONLY the cameras JCR reads -- head + right wrist, at their
native resolution (= JCR's input resolution) -- so the renderer never draws the unused left wrist camera (user 10-01:
render only what JCR needs). Everything else (task, depth for the point resolve, IK, status) is SoloWorld's."""
from __future__ import annotations

from ..astra_motion.harness import Obs
from ..astra_solo.world import SoloWorld

CAMS2 = ("cam_head", "cam_wrist_right")
KEYS2 = {"cam_head": "head", "cam_wrist_right": "wrist"}


class JcrWorld(SoloWorld):
    def __init__(self, variant: str = "standard", depth: bool = True):
        from ..astra_motion.world_isaac import NO_RENDER
        from ..sim.scene import GRIP_MAX_W, make_env
        self.variant = variant
        self.depth = bool(depth)
        self.env = make_env(0, headless=True, cameras=CAMS2, depth=self.depth, render_interval=NO_RENDER,
                            variant=variant)
        self.dt = float(self.env.step_dt)
        self.table_z = float(self.env.table_top_z)
        self.w_open = float(GRIP_MAX_W)
        self._st = None
        self.last_obs = None

    def _render(self):
        self.env.env.sim.render()
        for n in CAMS2:
            self.env.scene[n].update(0.0, force_recompute=True)

    def observe(self, depth: bool = False) -> Obs:
        self._render()
        cams = {KEYS2[n]: self._cam(n, KEYS2[n]) for n in CAMS2}
        rgb = {KEYS2[n]: self.env.camera_rgb(n) for n in CAMS2}
        st = self.status()
        self.last_obs = Obs(st["t"], rgb, None, cams, st["tcp"], st["grip_w"])
        if depth and self.depth:
            self.last_obs.depth = {"head": self.env.camera_depth("cam_head").copy()}
        return self.last_obs
