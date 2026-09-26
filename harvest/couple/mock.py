"""Mock Astra for the coupling stream: answer() builds schema-valid answer dicts (tests, dry runs); no paid call."""
from __future__ import annotations


def answer(command: str = "continue", *, execution: str = "progressing", intent: str = "aligned",
           confidence: str = "high", evidence: str = "right wrist view: gripper above the mug",
           views=("cam_wrist_right",), claims=(), dp=(0.0, 0.0, 0.0), dr=(0.0, 0.0, 0.0), gripper: str = "keep",
           diff: str | None = None, info: str = "none", done=()) -> dict:
    d = {"assessment": {"task_progress": {"verified_completed": list(done), "currently_attempting": "pick the mug",
                                          "remaining": ["place the mug on the tray"]},
                        "execution": execution, "intent": intent, "confidence": confidence, "evidence": evidence,
                        "evidence_views": list(views), "claims": [{"kind": k, "view": v} for k, v in claims]},
         "info_request": info}
    if diff is not None:
        d["diff"] = diff
    if diff != "keep":
        d["command"] = command
        if command == "edit":
            d["edit"] = {"delta_position_m": list(dp), "delta_rotation_rad": list(dr), "gripper": gripper}
    return d
