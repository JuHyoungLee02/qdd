"""Minimal URDF reader + forward kinematics (pure numpy / xml; no Isaac, no cuRobo).

Used by the L9 v2 robot tools to measure TCPs, pads and hand synergies from the same URDF that cuRobo and the Isaac
URDF importer read. Joint types: fixed, revolute, continuous, prismatic (mimic tags honoured)."""
from __future__ import annotations

import math
import os
import xml.etree.ElementTree as ET

import numpy as np


def rpy_R(rpy) -> np.ndarray:
    r, p, y = (float(v) for v in rpy)
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]])


def R_rpy(R) -> tuple:
    R = np.asarray(R, float)
    p = math.asin(max(-1.0, min(1.0, -R[2, 0])))
    if abs(math.cos(p)) < 1e-9:
        return (math.atan2(-R[1, 2], R[1, 1]), p, 0.0)
    return (math.atan2(R[2, 1], R[2, 2]), p, math.atan2(R[1, 0], R[0, 0]))


def T_of(xyz=(0, 0, 0), rpy=(0, 0, 0)) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = rpy_R(rpy)
    T[:3, 3] = np.asarray(xyz, float)
    return T


def axis_angle(axis, ang) -> np.ndarray:
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K


def _vec(s, n=3, default=0.0):
    if s is None:
        return [default] * n
    return [float(v) for v in s.split()]


class Urdf:
    def __init__(self, path: str):
        self.path = path
        self.dir = os.path.dirname(os.path.abspath(path))
        self.root_el = ET.parse(path).getroot()
        self.joints = {}
        for j in self.root_el.findall("joint"):
            o = j.find("origin")
            a = j.find("axis")
            lim = j.find("limit")
            m = j.find("mimic")
            self.joints[j.get("name")] = {
                "type": j.get("type"), "parent": j.find("parent").get("link"), "child": j.find("child").get("link"),
                "T": T_of(_vec(o.get("xyz") if o is not None else None), _vec(o.get("rpy") if o is not None else None)),
                "axis": np.array(_vec(a.get("xyz") if a is not None else None) if a is not None else [1.0, 0, 0]),
                "lower": float(lim.get("lower", 0)) if lim is not None else 0.0,
                "upper": float(lim.get("upper", 0)) if lim is not None else 0.0,
                "mimic": (m.get("joint"), float(m.get("multiplier", 1)), float(m.get("offset", 0))) if m is not None
                else None}
        self.links = {k.get("name"): k for k in self.root_el.findall("link")}
        self.child_joint = {j["child"]: n for n, j in self.joints.items()}
        kids = {j["child"] for j in self.joints.values()}
        roots = [k for k in self.links if k not in kids]
        self.root = roots[0]

    def parent_chain(self, link: str) -> list:
        """Joint names from the root to `link`."""
        out = []
        while link in self.child_joint:
            jn = self.child_joint[link]
            out.append(jn)
            link = self.joints[jn]["parent"]
        return out[::-1]

    def descendants(self, link: str) -> list:
        out, stack = [], [link]
        while stack:
            k = stack.pop()
            out.append(k)
            stack += [j["child"] for j in self.joints.values() if j["parent"] == k]
        return out

    def actuated(self) -> list:
        return [n for n, j in self.joints.items() if j["type"] in ("revolute", "continuous", "prismatic")
                and j["mimic"] is None]

    def qval(self, name: str, q: dict) -> float:
        j = self.joints[name]
        if j["mimic"] is not None:
            src, mult, off = j["mimic"]
            return mult * self.qval(src, q) + off
        return float(q.get(name, 0.0))

    def joint_T(self, name: str, q: dict) -> np.ndarray:
        j = self.joints[name]
        T = j["T"].copy()
        if j["type"] in ("revolute", "continuous"):
            M = np.eye(4)
            M[:3, :3] = axis_angle(j["axis"], self.qval(name, q))
            T = T @ M
        elif j["type"] == "prismatic":
            M = np.eye(4)
            ax = j["axis"] / np.linalg.norm(j["axis"])
            M[:3, 3] = ax * self.qval(name, q)
            T = T @ M
        return T

    def T_root(self, link: str, q: dict | None = None) -> np.ndarray:
        q = q or {}
        T = np.eye(4)
        for jn in self.parent_chain(link):
            T = T @ self.joint_T(jn, q)
        return T

    def T_rel(self, link: str, frame: str, q: dict | None = None) -> np.ndarray:
        """Pose of `link` in `frame`."""
        return np.linalg.inv(self.T_root(frame, q)) @ self.T_root(link, q)

    def geoms(self, link: str, kind: str = "visual") -> list:
        """[(abs mesh path or None, scale, T_link_geom, primitive dict)] of a link's visual / collision elements."""
        out = []
        el = self.links[link]
        for g in el.findall(kind):
            o = g.find("origin")
            T = T_of(_vec(o.get("xyz") if o is not None else None), _vec(o.get("rpy") if o is not None else None))
            geo = g.find("geometry")
            m = geo.find("mesh")
            if m is not None:
                fn = m.get("filename").replace("package://", "")
                if not os.path.isabs(fn):
                    fn = os.path.join(self.dir, fn)
                out.append((fn, _vec(m.get("scale"), 3, 1.0), T, None))
            else:
                prim = {c.tag: dict(c.attrib) for c in geo}
                out.append((None, [1, 1, 1], T, prim))
        return out

    def link_points(self, link: str, frame: str, q: dict | None = None, kind: str = "visual",
                    sample: int = 0) -> np.ndarray:
        """Mesh vertices of `link` (all its `kind` meshes) expressed in `frame` (N x 3)."""
        import trimesh
        T = self.T_rel(link, frame, q)
        pts = []
        for fn, sc, Tg, prim in self.geoms(link, kind):
            if fn is None:
                continue
            m = trimesh.load(fn, force="mesh", process=False)
            v = np.asarray(m.vertices if not sample else trimesh.sample.sample_surface(m, sample, seed=0)[0],
                           float) * np.asarray(sc, float)
            v = (Tg[:3, :3] @ v.T).T + Tg[:3, 3]
            pts.append((T[:3, :3] @ v.T).T + T[:3, 3])
        return np.concatenate(pts) if pts else np.zeros((0, 3))
