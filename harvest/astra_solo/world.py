"""Isaac world of the Astra-solo arm (pod only): the probe's IsaacWorld (harvest/astra_motion/world_isaac.py: hard
reset, three real-robot cameras, camera pose = live parent link x mount transform, OraclePlanner only for IK / TCP /
predicates) built for one scene variant per process (standard or dr, like the closed-loop evaluation's embodiment),
with the E-Couple task: mug_tray on the DEV layout seeds (AIWorkerEmbodiment.reset: env.set_seed(layout seed) = the
mug -> tray task).
depth=True (the point-then-act interface, canon §97 보충 2) adds the renderer's `distance_to_image_plane` annotator
to the cameras, and observe(depth=True) returns the head z-depth map in Obs.depth["head"]; depth=False (default)
builds the env exactly as before and observe() returns the parent's Obs unchanged."""
from __future__ import annotations

from ..astra_motion.world_isaac import CAMS, NO_RENDER, IsaacWorld

TASK = "mug_tray"


class SoloWorld(IsaacWorld):
    def __init__(self, variant: str = "standard", depth: bool = False, table_z: float | None = None):
        from ..sim.scene import GRIP_MAX_W, make_env
        self.variant = variant
        self.depth = bool(depth)
        kw = {} if table_z is None else {"table_z": float(table_z)}  # E-PT OOD-H; default call unchanged
        self.env = make_env(0, headless=True, cameras=CAMS, depth=self.depth, render_interval=NO_RENDER,
                            variant=variant, **kw)
        self.dt = float(self.env.step_dt)
        self.table_z = float(self.env.table_top_z)
        self.w_open = float(GRIP_MAX_W)
        self._st = None
        self.last_obs = None

    def reset(self, seed: int, task: str = TASK) -> None:
        if task != TASK:
            raise ValueError(f"E-Couple task only ({TASK})")
        super().reset(seed, task)

    def observe(self, depth: bool = False):
        obs = super().observe()
        if depth and self.depth:  # read right after observe()'s render: the same frame as the RGB
            obs.depth = {"head": self.env.camera_depth("cam_head").copy()}
        return obs
