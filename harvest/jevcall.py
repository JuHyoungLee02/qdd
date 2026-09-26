"""JevCall request builder (E §1.2).

Shown option names follow canon §27 R1 (no polarity/judgment words); option keys stay the
canonical meaning ids (R5) so logs and M7/M6 code keep one vocabulary.
"""
from .config import CFG
from .options import Option
from .serialize import canonicalize

NE = Option("NONE_ESCALATE", "NONE_ESCALATE", "None of the options fits the situation.")

_XY = {
    "plus_x": "Move toward +x (away from the robot).",
    "minus_x": "Move toward -x (toward the robot).",
    "plus_y": "Move toward +y (robot left).",
    "minus_y": "Move toward -y (robot right).",
    "plus_x_plus_y": "Move diagonally toward +x and +y.",
    "plus_x_minus_y": "Move diagonally toward +x and -y.",
    "minus_x_plus_y": "Move diagonally toward -x and +y.",
    "minus_x_minus_y": "Move diagonally toward -x and -y.",
}
DIR_XY = [Option(k, k, d) for k, d in _XY.items()] + [Option("none_xy", "none_xy", "No horizontal motion."), NE]
DIR_Z = [Option("up", "up", "Move up."), Option("down", "down", "Move down."),
         Option("none_z", "none_z", "No vertical motion."), NE]
# cm values are [가정] (E §1.2: M3 fixes only "5 log-spaced bins")
MAG = [Option("tiny", "tiny", "about 0.5 cm"), Option("small", "small", "about 1 cm"),
       Option("medium", "medium", "about 2 cm"), Option("large", "large", "about 4 cm"),
       Option("xlarge", "xlarge", "about 8 cm"), NE]
# canon §87 gripper decision question (fused VLA only, ser-A-min-3): the intent; execution stays behind the two-layer
# gate + T1 premise (canon §84 / §86)
GRIPPER = [Option("close", "close", "Close the gripper on the object now (grasp)."),
           Option("open", "open", "Open the gripper now (release)."),
           Option("keep", "keep", "Keep the gripper as it is."), NE]
# M7 PROGRESS_OPTIONS (canon §11.2); shown names renamed per §27 R1, keys unchanged
PROGRESS = [
    Option("valid_progress", "advancing", "The stage is moving toward its exit as expected."),
    Option("allowed_change", "side_change", "Something changed that the stage allows; no effect on the exit."),
    Option("failure", "regressed", "The stage can no longer reach its exit without recovery."),
    Option("recovering", "recovering", "A recovery step is in progress."),
    Option("NONE_ESCALATE", "NONE_ESCALATE", "Cannot tell from the state."),
]


def build_choice(key, instructions, opts):
    return key, {"type": "choice", "instructions": instructions,
                 "criteria": {o.name: o.desc for o in opts}}


def build_request(state, questions):
    return {"model": CFG.jev_model, "state": canonicalize(state), "questions": dict(questions)}
