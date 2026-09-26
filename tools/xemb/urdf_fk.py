"""Generic URDF forward kinematics for track T4 (render / silhouette alignment): all link poses from joint values
(revolute / continuous / prismatic / fixed, mimic joints), relative to any base link; visual mesh references.
Pure numpy + xml (the mesh files are read by the caller, e.g. trimesh)."""
from __future__ import annotations

import xml.etree.ElementTree as ET

import numpy as np


def _rpy(r, p, y):
    cr, sr, cp, sp, cy, sy = np.cos(r), np.sin(r), np.cos(p), np.sin(p), np.cos(y), np.sin(y)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]])


def _origin(el):
    T = np.eye(4)
    o = el.find("origin") if el is not None else None
    if o is not None:
        T[:3, 3] = [float(v) for v in o.get("xyz", "0 0 0").split()]
        T[:3, :3] = _rpy(*[float(v) for v in o.get("rpy", "0 0 0").split()])
    return T


def _axis_rot(axis, q):
    k = np.asarray(axis, float) / np.linalg.norm(axis)
    Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(q) * Kx + (1 - np.cos(q)) * Kx @ Kx


class Urdf:
    def __init__(self, text_or_path: str):
        self.root = ET.fromstring(text_or_path) if text_or_path.lstrip().startswith("<") \
            else ET.parse(text_or_path).getroot()
        self.joints = {}
        for j in self.root.findall("joint"):
            ax = j.find("axis")
            mm = j.find("mimic")
            self.joints[j.get("name")] = {
                "type": j.get("type"), "parent": j.find("parent").get("link"), "child": j.find("child").get("link"),
                "T": _origin(j), "axis": [float(v) for v in ax.get("xyz").split()] if ax is not None else [1, 0, 0],
                "mimic": None if mm is None else (mm.get("joint"), float(mm.get("multiplier", 1)),
                                                  float(mm.get("offset", 0)))}
        self.by_child = {j["child"]: n for n, j in self.joints.items()}
        self.links = [l.get("name") for l in self.root.findall("link")]

    def _q(self, name, q):
        j = self.joints[name]
        if j["mimic"]:
            lead, m, o = j["mimic"]
            return m * float(q.get(lead, 0.0)) + o
        return float(q.get(name, 0.0))

    def world(self, q: dict) -> dict:
        out = {}

        def pose(link):
            if link in out:
                return out[link]
            jn = self.by_child.get(link)
            if jn is None:
                out[link] = np.eye(4)
                return out[link]
            j = self.joints[jn]
            T = pose(j["parent"]) @ j["T"]
            v = self._q(jn, q)
            M = np.eye(4)
            if j["type"] in ("revolute", "continuous"):
                M[:3, :3] = _axis_rot(j["axis"], v)
            elif j["type"] == "prismatic":
                M[:3, 3] = np.asarray(j["axis"], float) / np.linalg.norm(j["axis"]) * v
            out[link] = T @ M
            return out[link]

        for l in self.links:
            pose(l)
        return out

    def poses(self, q: dict, base: str) -> dict:
        W = self.world(q)
        Bi = np.linalg.inv(W[base])
        return {k: Bi @ v for k, v in W.items()}

    def visuals(self) -> list:
        out = []
        for l in self.root.findall("link"):
            for v in l.findall("visual"):
                m = v.find("geometry/mesh")
                if m is None:
                    continue
                out.append({"link": l.get("name"), "file": m.get("filename"), "T": _origin(v),
                            "scale": [float(s) for s in m.get("scale", "1 1 1").split()]})
        return out
