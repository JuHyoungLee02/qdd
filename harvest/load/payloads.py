"""Payloads by size class (E §1.3). Synthetic but realistic until the snapshot pool exists (E §2.3)."""
from ..jevcall import DIR_XY, DIR_Z, MAG, NE, PROGRESS, build_choice, build_request
from ..options import Option

_OBJ = "  o3 mug red | held_by_gripper | upright\n  o5 tray blue | on(table) | clear=yes"
_FILL = "\n".join(f"  o{k} distractor_{k} | on(table) | upright" for k in range(10, 90))


def _state(i, extra=""):
    return (f"t_state: f{i} (t={i * 0.33:.2f}s)  contract: c7  stage: S2 \"place mug o3 on tray o5\"\n"
            "robot: gripper=closed_holding(o3) wrist_force=light arm=moving\n"
            f"objects:\n{_OBJ}{extra}\n"
            "facts: near(o3,o5)=yes aligned_xy(o3,o5)=no in_contact(o3,o5)=no\n"
            "stage S2: exit=on(o3,o5) invariants=holding(o3) elapsed=normal\n"
            "changes (last 3s): -0.4s aligned_x(o3,o5): no->yes")


def _dzoom(n):
    q = f"Which direction should the gripper move during step {n} to make progress toward the exit of stage S2?"
    return [build_choice(f"{n}.dir_xy", q, DIR_XY), build_choice(f"{n}.dir_z", q, DIR_Z),
            build_choice(f"{n}.mag_coarse", f"How far should the gripper move during step {n}?", MAG)]


_MON = [build_choice("mon.progress", "Considering the change since the last step, how is stage S2 going?", PROGRESS)]
_TARGET = [Option("o5", "o5", "The blue tray."), Option("o8", "o8", "The green bottle."), NE]


def make(size, i):
    if size == "S1":
        qs = _dzoom("ds412") + _MON
    elif size == "S3":
        qs = _dzoom("ds412") + _dzoom("ds413") + _dzoom("ds414") + _MON
    elif size == "G1":
        qs = [build_choice("ds.target", "Which object is the place target for stage S2?", _TARGET)] + _MON
    elif size == "X8":
        return build_request(_state(i, "\n" + "\n".join([_FILL] * 3)), _dzoom("ds412") + _MON)
    else:
        raise ValueError(size)
    return build_request(_state(i), qs)


def fixed(j):
    """Byte-identical payloads for the determinism probe (E §2.3)."""
    return make("S1", 100000 + j)
