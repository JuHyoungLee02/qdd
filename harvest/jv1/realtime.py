"""E-JV1 closed-loop client wrappers (docs/stage3/prereg_jv1.md §4). Pure numpy; they sit between harvest.jcr.exec_jcr
.JcrExec (unchanged) and a model client, so arms A / B / C run through the SAME executor, authority code (envelope /
priority blend, allowed gripper direction, grip fallback) and recorder.

DelayedClient -- condition R (real-time): the model is asked only every `period_dec` decisions (0.2 s each) and its
  answer, computed from the observation at t_j, takes effect at t_j + lat_s (the sim is paused during the call, so the
  delay is imposed here in sim time, fixed per arm from the latency bench). Until then the previous answer runs:
    A (chunk answer): row of the answer active at tick tau = p_cmd(t_j) + delta_j[(tau - t_j) / dt] (last row held
      past the chunk end) -- naive asynchronous chunk execution;
    B (waypoint answer, has 'c_hat'): the rule controller steps from the current commanded TCP / velocity toward the
      active waypoint every 20 Hz tick (truth.step via above) -- a stale waypoint is still an absolute target.
  The gripper event of an answer is re-indexed to the current decision and handed over once.
TruthWaypointClient -- arm C (ceiling of arm B's controller): the waypoint is the privileged true point (label rule P or
  A) passed through the same text quantisation (point 0-1000 + height mm) and the same controller; gripper event at
  arrival (truth.grip_event), stop when physically unrecoverable."""
from __future__ import annotations

import numpy as np

from ..jcr import features as FT
from ..jcr import truth as T
from . import text as X


class DelayedClient:
    def __init__(self, inner, lat_s: float, period_dec: int = 1, dt: float = T.DT, H: int = T.H):
        self.inner, self.lat, self.period, self.dt, self.H = inner, float(lat_s), max(1, int(period_dec)), dt, H
        self.hist = []
        self.n = 0
        self.calls = 0

    def bind(self, ex):
        if hasattr(self.inner, "bind"):
            self.inner.bind(ex)

    def _active(self, tau):
        a = None
        for h in self.hist:
            if h["t"] + self.lat <= tau + 1e-9:
                a = h
        return a

    def act(self, smp, head, wrist, seed: int = 0) -> dict:
        t = float(smp["t"])
        lat = None
        if self.n % self.period == 0:
            o = self.inner.act(smp, head, wrist, seed=seed)
            self.calls += 1
            lat = o.get("latency_s")
            if not o.get("error"):
                self.hist.append({"t": t, "p0": np.asarray(smp["p_cmd"], float), "o": o, "ev_used": False})
                self.hist = self.hist[-8:]
        self.n += 1
        p, v = np.asarray(smp["p_cmd"], float).copy(), np.asarray(smp["v"], float).copy()
        out = []
        for i in range(self.H):
            tau = t + i * self.dt
            h = self._active(tau)
            if h is None:
                q, v = p.copy(), np.zeros(3)
            elif "c_hat" in h["o"]:
                stop = FT.decode_event(int(np.argmax(h["o"]["event_p"])))[0] == "stop"
                q, v = T.step(p, v, T.via_above(p, np.asarray(h["o"]["c_hat"], float)), stop)
            else:
                d = np.asarray(h["o"]["delta"], float)
                r = int(round((tau - h["t"]) / self.dt))
                q = h["p0"] + d[min(max(r, 0), len(d) - 1)]
                v = (q - p) / self.dt
            out.append(q)
            p = q
        P = np.array(out)
        h = self._active(t)
        ev = np.zeros(FT.N_EVENT)
        ev[FT.EV_KEEP] = 1.0
        res = {"contact_p": 0.0, "anomaly_p": [0.0] * (len(T.ANOMALIES) + 1)}
        if h is not None:
            o = h["o"]
            kind, row = FT.decode_event(int(np.argmax(o["event_p"])))
            if kind == "stop":
                ev[:] = 0.0
                ev[FT.EV_STOP] = 1.0
            elif kind in ("close", "open") and not h["ev_used"]:
                r = max(0, int(round((h["t"] + row * self.dt - t) / self.dt)))
                if r < self.H:
                    ev[:] = 0.0
                    ev[1 + r if kind == "close" else 1 + self.H + r] = 1.0
                    h["ev_used"] = True
            res = {"contact_p": o.get("contact_p", 0.0), "anomaly_p": o.get("anomaly_p") or res["anomaly_p"]}
        res.update(delta=(P - np.asarray(smp["p_cmd"], float)).tolist(), event_p=ev.tolist(), latency_s=lat,
                   delayed={"lat_s": self.lat, "period_dec": self.period, "called": lat is not None})
        return res


def quantize(c) -> np.ndarray:
    return X.from_pt(*X.to_pt(c))


class TruthWaypointClient:
    """Arm C: privileged waypoint -> text quantisation -> rule controller. bind(executor) before the first act."""

    def __init__(self, label: str = "P"):
        self.label, self.ex = label, None

    def bind(self, ex):
        self.ex = ex

    def act(self, smp, head, wrist, seed: int = 0) -> dict:
        ex = self.ex
        st = ex.state_fn()
        gt = ex.true_point(st)
        c = T.project_ball(gt, smp["goal_cmd"], T.R_GOAL)[0] if self.label == "A" else np.asarray(gt, float)
        c = quantize(c)
        tz = float(np.asarray(st["obj"][ex.tgt], float)[2])
        hold = bool(st.get("holding"))
        stop = tz < ex.table_z - T.DROP_Z or (not bool(st.get("upright", True)) and not hold)
        ev = np.zeros(FT.N_EVENT)
        g = T.grip_event(smp.get("allow"), smp["tcp"], c)
        ev[FT.EV_STOP if stop else (1 if g == "close" else (1 + T.H if g == "open" else FT.EV_KEEP))] = 1.0
        P = X.rows(smp, smp["p_cmd"] if stop else c, stop=stop)
        touched = set(st.get("touched", ()))
        an = [float(k == "unexpected_contact" and bool(touched - {ex.tgt}) or k == "unrecoverable" and stop)
              for k in T.ANOMALIES]
        return {"delta": (P - np.asarray(smp["p_cmd"], float)).tolist(), "event_p": ev.tolist(), "c_hat": c.tolist(),
                "contact_p": float(ex.tgt in touched), "anomaly_p": an + [float(max(an))], "latency_s": 0.0}
