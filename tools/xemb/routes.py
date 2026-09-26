"""Which sample types a public source may produce, from what it ships (howto 10: data condition -> routes -> samples).

Routes (user-log 123):
  1 pixel-only       no calibration: only pixel-frame samples (points, 2-D traces, format QA); nothing in metres
  2 detect gripper   pointing model / tracker + jump filter gives the gripper point when there is no projection
  3 self-calibrate   T1: FK 3-D gripper + detected 2-D -> PnP (+ focal) -> the source becomes 'calibrated'
  4 control w/o cam  C' targets come from FK in the robot base frame; the text says 'camera: unknown'
  5 no depth         metric 3-D answers only from depth or GT poses (T3 pseudo-depth only after its gates pass)
Tracks (user-log 123): T1 = route 3, T2 = routes 1/2/4 at scale (learn it implicitly), T3 = monocular metric depth.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Cond:
    fk: bool = False          # joint states + URDF/MJCF (or EE poses) in the robot base frame
    calib: bool = False       # camera intrinsics + extrinsics shipped
    selfcal_ok: bool = False  # T1 passed its gates for this rig
    depth: bool = False       # metric depth shipped (or rendered)
    gt_pose: bool = False     # object poses shipped
    pseudo_depth_ok: bool = False  # T3 passed its gates for this source


def allowed(c: Cond) -> set:
    s = {"ee_point_detected", "ee_trace_detected", "obj_point_detected", "format_qa"}  # routes 1-2
    if c.fk:
        s |= {"control_camera_unknown", "selfcal"}  # routes 4 and 3
    cal = c.calib or c.selfcal_ok
    if c.fk and cal:
        s |= {"ee_point_projected", "ee_trace_projected", "ee_approach_cam", "control_with_camera"}
    if cal and (c.depth or c.gt_pose):
        s |= {"obj_center_cam"}
    if cal and c.depth:
        s |= {"table_plane_cam"}
    if cal and c.pseudo_depth_ok:
        s |= {"obj_center_cam_pseudo", "table_plane_cam_pseudo"}
    return s
