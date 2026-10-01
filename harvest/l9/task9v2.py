"""L9 v2 task layer (spec §12.7, user 10-02 02h: "여러로봇으로 … 그 테스크의 다양성 자체를 지금보다도 훨씬 더").

v1 (task9.DEFS, 108 definitions, 9 families) stays as it is; this module adds definitions taken from public benchmark
task lists (RoboTwin 2.0, RoboCasa, BEHAVIOR, LIBERO, CALVIN, RLBench, VIMA-Bench, SimplerEnv, BridgeData V2, DROID:
`SOURCE_REFS`, per definition `SOURCES`), kept only when they compile to our one-arm steps (target, place[, offset]).
Only the task TYPE is taken (spec §12.11 principle 1): scenes, assets, layouts and instruction text are our own, and a
benchmark instruction string never appears verbatim (BENCH_INSTR, avoid_bench). Articulated objects, pushing, wiping,
pouring, two-arm and tool tasks are listed in `NEXT_CANDIDATES` instead.

Per definition `extra`:
  requires   capabilities beyond the v1 executor / scenes (CAPS_ALL); plans include a definition only when every one is
             available (alloc9 / tools/l9/plan.py v2 --caps)
  place      {step index: {pose: upright|lying|leaning|oriented, orient: rot90|long_lr|handle_right, approach}}
  start      {object name: "lying"} (start pose, the world spawns it)
  recovery   {step, kind: off_target|tilted} (the executor perturbs that place; the next call re-grasps and fixes it)

`finish` (called by task9 instantiate with v2=True) adds to the episode: step_info (scene constraint for the grasp
label rule §12.8, place pose / approach / point / height, done predicate, recovery tag), done (the checkable stop
condition), instr_meta (base text, wrapper, instructed-approach candidate ~20 %; apply_approach puts it in the text once
the grasp selector knows it is executable), movable_containers, start_poses.
Rules marked [가설] are hypotheses to check in the pilot (G1 / G2 frames). Pure."""
from __future__ import annotations

import hashlib
import math

from . import task9 as T9
from .task9 import TaskDef

# ------------------------------------------------------------------------------------------------ constants
HOLLOW = ("bowl", "mug", "cup")  # movable hollow objects (rim / wall grasps)
HOLLOW_ANY = HOLLOW + ("basket", "jar", "vase", "pot")
SHELF_KINDS = ("shelf", "shelf_high", "shelf_low", "wall_shelf", "cupboard")  # blocked-above nodes (L9v2-ENV names)
SHELF_NEED = "node:" + "|".join(SHELF_KINDS)
CLEAR_ABOVE_MIN = 0.25  # a node whose free height above is below this is "blocked above" (top approach impossible)
CONSTRAINTS = ("blocked_above", "wide_hollow", "tall", "handle", "flat")  # priority order
PLACE_POSES = ("upright", "lying", "leaning", "oriented")
HEIGHT_BANDS = ("floor", "low", "mid", "high", "above_eye")
BAND_Z = ((0.25, "floor"), (0.60, "low"), (1.10, "mid"), (1.35, "high"))  # floor-based z [가설: AI Worker eye 1.40 m]
DONE_PREDS = ("on_spot", "on_surface", "in_container", "on_container", "stacked_on")
CAPS_ALL = ("node:shelf", "exec:approach_front", "exec:movable_container", "exec:place_pose", "exec:start_pose",
            "exec:recovery", "exec:push", "asset:ring_peg", "node:drawer_open")
RECOVERY_SHARE = 0.15  # owner 10-02: every definition gets recovery variants -> ~15 % of instances propose one [가설]
TALL_H, TALL_ASPECT = 0.15, 1.6  # [가설] tall = height >= 15 cm or height / width >= 1.6 (side grasp candidates)
HANDLE_RATIO = 1.6  # [가설] catalog handle_ratio of mugs with a handle
FLAT_H = 0.035
INSTRUCTED_SHARE = 0.20  # §12.8: ~20 % rows name the approach in the instruction
APPROACHES = ("top", "oblique", "front", "side")
ALLOWED_APPROACH = {None: APPROACHES, "blocked_above": ("front", "oblique", "side"),
                    "tall": ("side", "front", "oblique"), "wide_hollow": ("top", "oblique", "side"),
                    "handle": ("side", "oblique", "top"), "flat": ("top", "oblique")}
APPROACH_TEXT = {
    "top": ("Grasp the {X} from above.", "Pick the {X} up from the top.", "Reach down onto the {X} from above.",
            "Take the {X} with a top grasp."),
    "oblique": ("Grasp the {X} at an angle.", "Approach the {X} diagonally from above.",
                "Take the {X} with a tilted grasp.", "Reach for the {X} at an angle."),
    "front": ("Grasp the {X} from the front.", "Reach straight in and grab the {X} from the front.",
              "Take the {X} from its front side.", "Approach the {X} head-on from the front."),
    "side": ("Grasp the {X} from the side.", "Grab the {X} by its side.", "Approach the {X} from the side.",
             "Take the {X} with a side grasp."),
}
GENERAL_WRAP = ("{s}", "Your task: {s}", "Next: {s}")
IMPER_WRAP = ("Please {l}", "{l0}, please.", "Could you {l0}?", "Robot, {l}", "I need you to {l}")
IMPERATIVE = {"put", "place", "move", "set", "stack", "insert", "stand", "take", "bring", "lift", "line", "arrange",
              "sort", "clear", "tidy", "drop", "gather", "collect", "serve", "get", "make", "build", "pick", "lay",
              "lean", "rotate", "turn", "flank", "give", "separate", "shift", "store", "restack", "unstack", "swap",
              "use", "empty", "remove", "pack", "return", "load", "hang", "nest", "fill", "transfer", "keep", "find",
              "choose", "select", "throw", "grab", "first", "only", "leave"}
UNWRAPPED_SHARE = 0.40
# owner principle 1 (10-02, no benchmark sniping): benchmark instruction strings (LIBERO bddl names, CALVIN
# annotations, SimplerEnv prompts; fetched 2026-10-02) never appear verbatim — finish() moves to the next template
BENCH_INSTR = (
    "put the bowl on the plate", "put the bowl on the stove", "put the bowl on top of the cabinet",
    "put the cream cheese in the bowl", "put the wine bottle on the rack", "put the wine bottle on top of the cabinet",
    "put the white mug on the plate", "put both moka pots on the stove", "pick up the book and place it in the back "
    "compartment of the caddy", "put both the alphabet soup and the tomato sauce in the basket",
    "put both the cream cheese box and the butter in the basket",
    "put both the alphabet soup and the cream cheese box in the basket",
    "put the white mug on the left plate and put the yellow and white mug on the right plate",
    "put the white mug on the plate and put the chocolate pudding to the right of the plate",
    "pick up the black bowl next to the plate and place it on the plate",
    "pick up the black bowl on the cookie box and place it on the plate",
    "pick up the black bowl between the plate and the ramekin and place it on the plate",
    "grasp and lift the red block", "grasp and lift the blue block", "grasp and lift the pink block",
    "stack the grasped block", "remove the stacked block", "store the grasped block in the drawer",
    "store the grasped block in the sliding cabinet", "take the red block and rotate it to the right",
    "take the red block and rotate it to the left", "take the blue block and rotate it to the right",
    "take the blue block and rotate it to the left", "take the pink block and rotate it to the right",
    "take the pink block and rotate it to the left",
    "put the spoon on the towel", "put spoon on towel", "put carrot on plate", "put the carrot on the plate",
    "stack the green block on the yellow block", "put eggplant into yellow basket", "pick coke can")
for _o in ("alphabet soup", "bbq sauce", "butter", "chocolate pudding", "cream cheese", "ketchup", "milk",
           "orange juice", "salad dressing", "tomato sauce"):
    BENCH_INSTR += (f"pick up the {_o} and place it in the basket",)


def _norm(s: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in s).split())


BENCH_NORM = frozenset(_norm(s) for s in BENCH_INSTR)


def bench_clash(text: str) -> bool:
    return _norm(text) in BENCH_NORM


# robot profile max opening (m): robot9 names (ffw_sg2, franka_mast) and the L9v2-ROBOT names (franka, r1pro, g1)
GRIP_MAX = {"ffw_sg2": 0.107, "franka_mast": 0.08, "franka": 0.08, "r1pro": 0.10, "g1": 0.06}
GRIP_PROVISIONAL = ("r1pro", "g1")  # [가설] until the robot profiles give the measured pad gap (L9v2-ROBOT)


def grip_max_of(robot: str) -> float:
    """The robot profile's max pad gap: robot9.grip_max(robot) when the profile layer provides it, else GRIP_MAX."""
    try:
        from . import robot9
        f = getattr(robot9, "grip_max", None)
        if callable(f):
            v = f(robot)
            if v:
                return float(v)
    except Exception:  # noqa: BLE001  (pure fallback: the table)
        pass
    return float(GRIP_MAX[robot])


def _u(*parts) -> float:
    return int(hashlib.sha256(":".join(str(p) for p in parts).encode()).hexdigest()[:12], 16) / float(16 ** 12)


# ------------------------------------------------------------------------------------------------ sources
# GitHub stars / licence / last push read with the GitHub API on 2026-10-02. [기초] = older than 1.5 years (used as a
# task list only, user rule 2026-10-01).
SOURCE_REFS = {
    "v1": {"name": "L9 v1 (설계 §3 자체 정의)", "paper": "docs/superpowers/specs/2026-09-30-l9-diverse-datagen-design.md",
           "date": "2026-09-30", "repo": "-", "stars": None, "licence": "-", "basic": False},
    "RT2": {"name": "RoboTwin 2.0 (50 tasks)", "paper": "arXiv 2506.18088", "date": "2025-06",
            "repo": "RoboTwin-Platform/RoboTwin", "stars": 2935, "licence": "MIT", "basic": False},
    "RC": {"name": "RoboCasa (atomic PickPlace* + composite activities)", "paper": "RSS 2024 (arXiv 2406.02523)",
           "date": "2024-06", "repo": "robocasa/robocasa", "stars": 1773, "licence": "NOASSERTION", "basic": True},
    "B1K": {"name": "BEHAVIOR-1K / BEHAVIOR-100 activity manifest", "paper": "CoRL 2022 (arXiv 2403.09227)",
            "date": "2022-12", "repo": "StanfordVL/BEHAVIOR-1K", "stars": 1732, "licence": "MIT", "basic": True},
    "LIB": {"name": "LIBERO (object / spatial / goal / 10)", "paper": "NeurIPS 2023 (arXiv 2306.03310)",
            "date": "2023-06", "repo": "Lifelong-Robot-Learning/LIBERO", "stars": 2373, "licence": "MIT", "basic": True},
    "CAL": {"name": "CALVIN (34 tasks)", "paper": "RA-L 2022 (arXiv 2112.03227)", "date": "2021-12",
            "repo": "mees/calvin", "stars": 996, "licence": "MIT", "basic": True},
    "RLB": {"name": "RLBench (100 tasks)", "paper": "RA-L 2020 (arXiv 1909.12271)", "date": "2019-09",
            "repo": "stepjam/RLBench", "stars": 1823, "licence": "NOASSERTION", "basic": True},
    "VIMA": {"name": "VIMA-Bench (17 meta tasks)", "paper": "ICML 2023 (arXiv 2210.03094)", "date": "2022-10",
             "repo": "vimalabs/VIMABench", "stars": 328, "licence": "MIT", "basic": True},
    "SIMPLER": {"name": "SimplerEnv (Google robot / WidowX tasks)", "paper": "CoRL 2024 (arXiv 2405.05941)",
                "date": "2024-05", "repo": "simpler-env/SimplerEnv", "stars": 1174, "licence": "MIT", "basic": True},
    "BRIDGE": {"name": "BridgeData V2 skill list", "paper": "CoRL 2023 (arXiv 2308.12952)", "date": "2023-08",
               "repo": "rail-berkeley/bridge_data_v2", "stars": 292, "licence": "MIT", "basic": True},
    "DROID": {"name": "DROID verb taxonomy", "paper": "RSS 2024 (arXiv 2403.12945)", "date": "2024-03",
              "repo": "droid-dataset/droid", "stars": 446, "licence": "-", "basic": True},
}
V1_SOURCES = {  # the v1 families' nearest public tasks (v1 definitions were written from the L9 spec §3)
    "insert": (("RLB", "put_umbrella_in_umbrella_stand"), ("B1K", "organizing_school_stuff")),
    "arrange": (("VIMA", "rearrange"), ("B1K", "collect_misplaced_items")),
    "stack": (("RT2", "stack_blocks_two"), ("CAL", "stack_block")),
    "sort": (("RT2", "blocks_ranking_rgb"), ("B1K", "sorting_groceries")),
    "put_in": (("LIB", "pick_up_the_X_and_place_it_in_the_basket"), ("RT2", "place_object_basket")),
    "set": (("RLB", "set_the_table"), ("B1K", "serving_a_meal")),
    "clear": (("B1K", "clearing_the_table_after_dinner"), ("RC", "clearing_table")),
    "relation": (("LIB", "libero_spatial"), ("VIMA", "rearrange")),
    "height": (("LIB", "put_the_bowl_on_top_of_the_cabinet"), ("RC", "PickPlaceCabinetToCounter")),
}
NEXT_CANDIDATES = (  # need another command format (articulation, contact motion, two arms, tools) -> later
    ("RC", "PickPlaceCounterToMicrowave / Oven / ToasterOven / Drawer / Fridge*, kitchen_doors, kitchen_drawer, "
           "stove / sink knobs (doors, drawers, knobs)"),
    ("CAL", "open_drawer, close_drawer, move_slider_*, turn_on/off_lightbulb, turn_on/off_led, push_*_block, "
            "push_into_drawer"),
    ("LIB", "open_the_middle_drawer, open_the_top_drawer_and_put_the_bowl_inside, turn_on_the_stove, "
            "push_the_plate_to_the_front_of_the_stove, *_in_the_microwave_and_close_it"),
    ("RT2", "open_laptop, open_microwave, click_bell, click_alarmclock, press_stapler, turn_switch, stamp_seal, "
            "beat_block_hammer (tool), shake_bottle*, rotate_qrcode, scan_object, hanging_mug (hook pose), "
            "handover_block / handover_mic / lift_pot / pick_dual_bottles / place_dual_shoes / grab_roller (two arms)"),
    ("RLB", "put_item_in_drawer, put_bottle_in_fridge, put_tray_in_oven, close_*, open_*, wipe_desk, sweep_to_dustpan"),
    ("BRIDGE", "fold cloth, wipe, sweep, open / close (deformable / contact)"),
    ("DROID", "pour, wipe, open / close, turn"),
    ("B1K", "cleaning_* / mopping / vacuuming / washing_* (wipe, liquids), opening_packages, installing_*"),
    ("v1", "material-conditional picks (pick the metal / glass one): the catalog has no material labels"),
)

# ------------------------------------------------------------------------------------------------ definitions
NEW: dict = {}
SOURCES: dict = {}
T = {"role": "target"}
SL = {"role": "target", "slender": True}
TALL = {"role": "target", "tall": True}
B_ = {"role": "base"}
W_ = {"role": "container", "kind": "wide"}
WB = {"role": "container", "kind": "wide", "big": True}
PL = {"role": "container", "kind": "flat"}
BIN = {"role": "container", "kind": "wide", "cats": ("bin", "basket", "box")}
BOWL = {"role": "container", "kind": "wide", "cats": ("bowl",)}
NAR = {"role": "container", "kind": "narrow"}
FOOD, TOY, DRINK = T9.FOOD, T9.TOYISH, T9.DRINK
HV = {"type": "node", "kinds": ("slot",)}
SV = {"type": "node", "kinds": ("stand",)}
SH = {"type": "node", "kinds": SHELF_KINDS}
ZN = {"type": "node", "kinds": ("zone", "seat")}
UP = {"upright_max_deg": 15.0}
FRONT = ("node:shelf", "exec:approach_front")


def _t(*xs):
    return tuple(xs)


def add(i, fam, objs, steps, templates, src, dst=None, judge=None, needs=(), req=(), place=None, start=None,
        recovery=None):
    assert i not in NEW and i not in T9.DEFS, i
    ex = {}
    if req:
        ex["requires"] = tuple(req)
    if place:
        ex["place"] = dict(place)
    if start:
        ex["start"] = dict(start)
    if recovery:
        ex["recovery"] = dict(recovery)
    NEW[i] = TaskDef(i, fam, objs, dst or {}, tuple(steps), tuple(templates), judge or {}, tuple(needs), ex)
    SOURCES[i] = tuple(src)


def hollow(cats=HOLLOW, **kw):
    return dict({"role": "target", "hollow": True, "cats": tuple(cats)}, **kw)


# 10. shelf: compartments with a board above (front approach) — RoboCasa cabinets, RLBench cupboard / bookshelf
add("shelf_put_in", "shelf", {"A": T}, [("A", "V")],
    _t("Put the {A} into the {V}.", "Place the {A} inside the {V}.", "Store the {A} in the {V}.",
       "Slide the {A} into the {V}.", "The {A} goes in the {V}.", "Put the {A} away in the {V}."),
    [("RC", "PickPlaceCounterToCabinet"), ("RLB", "put_groceries_in_cupboard")], dst={"V": SH}, needs=(SHELF_NEED,),
    req=FRONT)
add("shelf_take_out", "shelf", {"A": dict(T, on=SHELF_NEED)}, [("A", "P")],
    _t("Take the {A} out of the {Asurf} and put it on the {Msurf}.", "Get the {A} from the {Asurf}.",
       "Bring the {A} out of the {Asurf} onto the {Msurf}.", "Remove the {A} from the {Asurf}.",
       "Pull the {A} out of the {Asurf} and set it down."),
    [("RC", "PickPlaceCabinetToCounter"), ("RLB", "take_cup_out_from_cabinet")],
    dst={"P": {"type": "spot", "off_node": "A"}}, needs=(SHELF_NEED,), req=FRONT)
add("shelf_high_put", "shelf", {"A": T}, [("A", "V")],
    _t("Put the {A} up on the high shelf.", "Place the {A} on the {V} up high.", "Store the {A} on the top shelf.",
       "Lift the {A} onto the high shelf.", "The {A} goes up on the {V}."),
    [("B1K", "re-shelving_library_books"), ("RC", "PickPlaceCounterToCabinet (upper)")],
    dst={"V": {"type": "node", "kinds": ("shelf_high", "wall_shelf", "cupboard")}},
    needs=("node:shelf_high|wall_shelf|cupboard",), req=FRONT)
add("shelf_high_take_down", "shelf", {"A": dict(T, on="node:shelf_high|wall_shelf|cupboard")}, [("A", "P")],
    _t("Take the {A} down from the {Asurf}.", "Bring the {A} down from the high shelf.",
       "Get the {A} off the {Asurf} and put it on the {Msurf}.", "Move the {A} from up high to the {Msurf}.",
       "Reach up, take the {A} and set it down here."),
    [("RC", "PickPlaceCabinetToCounter (upper)"), ("B1K", "putting_dishes_away_after_cleaning")],
    dst={"P": {"type": "spot", "off_node": "A"}}, needs=("node:shelf_high|wall_shelf|cupboard",), req=FRONT)
add("shelf_low_put", "shelf", {"A": T}, [("A", "V")],
    _t("Put the {A} on the low shelf.", "Place the {A} down in the {V}.", "Store the {A} on the bottom shelf.",
       "Put the {A} away low, in the {V}.", "The {A} goes on the lower shelf."),
    [("RC", "PickPlaceCounterToCabinet (lower)"), ("B1K", "putting_away_toys")],
    dst={"V": {"type": "node", "kinds": ("shelf_low",)}}, needs=("node:shelf_low",), req=FRONT)
add("shelf_low_take_up", "shelf", {"A": dict(T, on="node:shelf_low")}, [("A", "P")],
    _t("Take the {A} from the low shelf and put it on the {Msurf}.", "Get the {A} out of the {Asurf}.",
       "Bring the {A} up from the bottom shelf.", "Lift the {A} out of the {Asurf} onto the {Msurf}.",
       "Move the {A} from the low shelf up here."),
    [("RC", "PickPlaceCabinetToCounter (lower)"), ("B1K", "storing_the_groceries")],
    dst={"P": {"type": "spot", "off_node": "A"}}, needs=("node:shelf_low",), req=FRONT)
add("shelf_to_shelf", "shelf", {"A": dict(T, on=SHELF_NEED)}, [("A", "V")],
    _t("Move the {A} from the {Asurf} to the other shelf.", "Put the {A} on the {V} instead.",
       "Re-shelve the {A} into the {V}.", "Take the {A} out and put it in the {V}.",
       "Shift the {A} to the {V}."),
    [("B1K", "re-shelving_library_books"), ("RC", "arranging_cabinets")],
    dst={"V": dict(SH, not_obj_node="A")}, needs=(SHELF_NEED.replace("node:", "node2:"),), req=FRONT)
add("shelf_two_items", "shelf", {"A": T, "B": T}, [("A", "V"), ("B", "V")],
    _t("Put the {A} and the {B} in the {V}.", "Store both the {A} and the {B} in the {V}.",
       "First the {A}, then the {B}: put them in the {V}.", "Put away the {A} and the {B} in the {V}.",
       "Place the {A} and then the {B} inside the {V}."),
    [("B1K", "storing_food"), ("RLB", "put_groceries_in_cupboard")], dst={"V": dict(SH, shared=True)},
    needs=(SHELF_NEED,), req=FRONT)
add("shelf_by_colour", "shelf", {"A": dict(T, colour_named=True), "X": dict(T, other_colour="A")}, [("A", "V")],
    _t("Put the {Acol} one in the {V}.", "Store only the {A} in the {V}.", "The {Acol} {Anoun} goes in the {V}.",
       "Put the {A}, not the other one, in the {V}.", "Place the {Acol} object on the shelf."),
    [("RC", "PickPlaceCounterToCabinet"), ("CAL", "place_in_slider")], dst={"V": SH}, needs=(SHELF_NEED,), req=FRONT)
add("shelf_wall_put", "shelf", {"A": T}, [("A", "V")],
    _t("Put the {A} on the wall shelf.", "Place the {A} up on the {V}.", "Set the {A} on the shelf on the wall.",
       "Store the {A} on the {V}.", "The {A} goes on the wall shelf."),
    [("B1K", "putting_up_Christmas_decorations_inside"), ("RLB", "put_books_on_bookshelf")],
    dst={"V": {"type": "node", "kinds": ("wall_shelf",)}}, needs=("node:wall_shelf",), req=FRONT)
add("shelf_tall_put", "shelf", {"A": TALL}, [("A", "V")],
    _t("Put the {A} into the {V}.", "Store the tall {Anoun} in the {V}.", "Place the {A} upright in the {V}.",
       "Put the {A} away in the {V}.", "Stand the {A} in the {V}."),
    [("LIB", "put_the_wine_bottle_on_top_of_the_cabinet"), ("B1K", "storing_the_groceries")],
    dst={"V": SH}, needs=(SHELF_NEED,), req=FRONT)
add("shelf_from_bin", "shelf", {"H": W_, "A": dict(T, on="on:H")}, [("A", "V")],
    _t("Take the {A} out of the {H} and put it in the {V}.", "Unpack the {A} from the {H} onto the shelf.",
       "Move the {A} from the {H} to the {V}.", "Put the {A} that is in the {H} away in the {V}.",
       "Store the {A} from the {H} in the {V}."),
    [("B1K", "storing_the_groceries"), ("RC", "restocking_supplies")], dst={"V": SH}, needs=(SHELF_NEED,), req=FRONT)

# 11. select: conditional picks by colour / size / category — CALVIN lift_<colour>_block, LIBERO-Object, VIMA
add("sel_colour_in", "select", {"A": dict(T, colour_named=True), "X": dict(T, other_colour="A"),
                                "Y": dict(T, other_colour="A"), "H": W_}, [("A", "H")],
    _t("Put the {Acol} object in the {H}.", "Find the {Acol} one and drop it into the {H}.",
       "Only the {Acol} item goes in the {H}.", "Pick the {Acol} thing and place it in the {H}.",
       "Choose the {Acol} object and put it into the {H}."),
    [("CAL", "lift_red_block_table"), ("VIMA", "visual_manipulation")])
add("sel_colour_plate", "select", {"A": dict(T, colour_named=True), "X": dict(T, other_colour="A"), "H": PL},
    [("A", "H")], _t("Put the {Acol} one on the {H}.", "Place the {Acol} object onto the {H}.",
                     "Only the {Acol} item goes on the {H}.", "Find the {Acol} thing and set it on the {H}.",
                     "Move the {Acol} object to the {H}."),
    [("VIMA", "visual_manipulation"), ("LIB", "libero_object")])
add("sel_colour_left_of", "select", {"A": dict(T, colour_named=True), "X": dict(T, other_colour="A"), "R": T},
    [("A", "P")], _t("Put the {Acol} object to the left of the {R}.", "Move the {Acol} one left of the {R}.",
                     "Place the {Acol} item on the {R}'s left.", "Find the {Acol} thing and set it left of the {R}.",
                     "The {Acol} object goes to the left of the {R}."),
    [("VIMA", "rearrange"), ("CAL", "lift_blue_block_table")],
    dst={"P": {"type": "spot", "rel": "left", "ref": "R"}})
add("sel_bigger_in", "select", {"A": dict(T, rank="big"), "X": dict(T, rank="small"), "H": W_}, [("A", "H")],
    _t("Put the bigger object in the {H}.", "Of the two, drop the larger one into the {H}.",
       "Pick the bigger item and place it in the {H}.", "The larger one goes in the {H}.",
       "Find the bigger thing and put it into the {H}."),
    [("RT2", "blocks_ranking_size"), ("VIMA", "manipulate_old_neighbor")])
add("sel_smaller_in", "select", {"A": dict(T, rank="small"), "X": dict(T, rank="big"), "H": W_}, [("A", "H")],
    _t("Put the smaller object in the {H}.", "Of the two, drop the smaller one into the {H}.",
       "Pick the smaller item and place it in the {H}.", "The smaller one goes in the {H}.",
       "Find the smaller thing and put it into the {H}."),
    [("RT2", "blocks_ranking_size"), ("VIMA", "manipulate_old_neighbor")])
add("sel_bigger_front", "select", {"A": dict(T, rank="big"), "X": dict(T, rank="small")}, [("A", "P")],
    _t("Move the bigger object to the front edge.", "Bring the larger one close to me, at the front.",
       "Put the bigger item at the front of the {Msurf}.", "The larger one goes to the near edge.",
       "Pick the bigger thing and set it at the front."),
    [("RT2", "blocks_ranking_size"), ("BRIDGE", "pick-and-place")], dst={"P": {"type": "spot", "corner": "front_edge"}})
add("sel_food_plate", "select", {"A": dict(T, cats=FOOD), "X": dict(T, cats=TOY), "H": PL}, [("A", "H")],
    _t("Put the food on the {H}.", "Serve the food item on the {H}, not the toy.", "Only the food goes on the {H}.",
       "Find something to eat and put it on the {H}.", "Place the edible item onto the {H}."),
    [("LIB", "pick_up_the_X_and_place_it_in_the_basket"), ("B1K", "serving_a_meal")])
add("sel_drink_tray", "select", {"A": dict(T, cats=("can", "bottle")), "X": dict(T, cats=FOOD), "H": PL}, [("A", "H")],
    _t("Put the drink on the {H}.", "Serve the drink on the {H}, leave the food.", "Only the drink goes on the {H}.",
       "Find the drink and set it on the {H}.", "Place the {A} on the {H}; it is the drink."),
    [("B1K", "serving_hors_d_oeuvres"), ("RC", "serving_beverages")])
add("sel_toy_bin", "select", {"A": dict(T, cats=TOY), "X": dict(T, cats=FOOD), "H": BIN}, [("A", "H")],
    _t("Put the toy away in the {H}.", "Only the toy goes in the {H}, not the food.", "Find the toy and drop it in the {H}.",
       "Tidy the toy into the {H}.", "Pick up the toy and put it into the {H}."),
    [("B1K", "putting_away_toys"), ("LIB", "libero_object")])
add("sel_can_bin", "select", {"A": dict(T, cats=("can",)), "X": dict(T, cats=FOOD + TOY), "H": BIN}, [("A", "H")],
    _t("Put the can in the {H}.", "Recycle the can: drop it into the {H}.", "Only the can goes in the {H}.",
       "Find the can and put it into the {H}.", "Collect the can into the {H}, leave the rest."),
    [("B1K", "collecting_aluminum_cans"), ("RT2", "put_bottles_dustbin")])
add("sel_bottle_basket", "select", {"A": dict(T, cats=("bottle",)), "X": dict(T, cats=FOOD + TOY), "H": W_},
    [("A", "H")], _t("Put the bottle in the {H}.", "Pick out the bottle and drop it into the {H}.",
                     "Only the bottle goes in the {H}.", "Find the bottle and place it in the {H}.",
                     "Take the bottle, leave the rest, and put it in the {H}."),
    [("RT2", "pick_diverse_bottles"), ("LIB", "pick_up_the_ketchup_and_place_it_in_the_basket")])
add("sel_book_stand", "select", {"A": dict(T, cats=("book",)), "X": dict(T, cats=FOOD + TOY)}, [("A", "V")],
    _t("Put the book on the {V}.", "Find the book and set it on the {V}.", "Only the book goes on the {V}.",
       "Place the book on top of the {V}.", "Pick the book, not the other thing, and put it on the {V}."),
    [("B1K", "sorting_books"), ("RLB", "put_books_on_bookshelf")], dst={"V": SV}, needs=("node:stand",))
add("sel_box_corner", "select", {"A": dict(T, cats=("box",)), "X": dict(T, cats=FOOD + TOY)}, [("A", "P")],
    _t("Move the box to the back left corner.", "Put the box away at the back left.", "Only the box goes to the back left.",
       "Find the box and set it in the back left area.", "Take the box to the rear left of the {Msurf}."),
    [("B1K", "moving_boxes_to_storage"), ("B1K", "organizing_boxes_in_garage")],
    dst={"P": {"type": "spot", "corner": "back_left"}})

# 12. tall: tall / slender objects (side grasp candidates, scene constraint "tall") — RoboTwin bottles, SimplerEnv can
add("tall_left_of", "tall", {"A": TALL, "R": T}, [("A", "P")],
    _t("Put the {A} to the left of the {R}.", "Move the tall {Anoun} left of the {R}.", "Set the {A} on the {R}'s left.",
       "Place the {A} beside the {R}, on the left.", "The {A} goes to the left of the {R}."),
    [("RT2", "pick_diverse_bottles"), ("SIMPLER", "pick_coke_can (vertical)")],
    dst={"P": {"type": "spot", "rel": "left", "ref": "R"}})
add("tall_into_bin", "tall", {"A": TALL, "H": BIN}, [("A", "H")],
    _t("Put the {A} in the {H}.", "Drop the {A} into the {H}.", "Throw the {A} into the {H}.",
       "Place the tall {Anoun} in the {H}.", "The {A} goes in the {H}."),
    [("RT2", "put_bottles_dustbin"), ("B1K", "collecting_aluminum_cans")])
add("tall_on_tray", "tall", {"A": TALL, "H": PL}, [("A", "H")],
    _t("Stand the {A} on the {H}.", "Put the {A} upright on the {H}.", "Place the {A} onto the {H}.",
       "Set the tall {Anoun} on the {H}.", "Move the {A} onto the {H}."),
    [("B1K", "serving_a_meal"), ("RT2", "place_object_scale")])
add("tall_row_two", "tall", {"A": TALL, "B": TALL}, [("A", "P1"), ("B", "P2")],
    _t("Line up the {A} and the {B} side by side, {A} on the left.", "Put the two tall things in a row: {A}, then {B}.",
       "Stand the {A} on the left and the {B} on the right, next to each other.",
       "Make a row of the {A} and the {B}, left to right.", "Arrange the {A} and the {B} in a line."),
    [("B1K", "storing_the_groceries"), ("RT2", "pick_dual_bottles (one-arm variant)")],
    dst={"P1": {"type": "spot", "line": ("y", 0, 2)}, "P2": {"type": "spot", "line": ("y", 1, 2)}})
add("tall_up_higher", "tall", {"A": TALL}, [("A", "V")],
    _t("Put the {A} up on the {V}.", "Lift the tall {Anoun} onto the {V}.", "Place the {A} on the higher {V}.",
       "Move the {A} up onto the {V}.", "The {A} goes up on the {V}."),
    [("LIB", "put_the_wine_bottle_on_top_of_the_cabinet"), ("RC", "PickPlaceCounterToCabinet")],
    dst={"V": {"type": "node", "kinds": ("top", "zone"), "higher": True}}, needs=("higher",))
add("tall_down_lower", "tall", {"A": dict(TALL, on="higher")}, [("A", "V")],
    _t("Bring the {A} down to the {V}.", "Take the tall {Anoun} down from the {Asurf}.", "Move the {A} down onto the {V}.",
       "Put the {A} on the lower {V}.", "The {A} goes down to the {V}."),
    [("RC", "PickPlaceCabinetToCounter"), ("LIB", "put_the_wine_bottle_on_the_rack")],
    dst={"V": {"type": "node", "kinds": ("top", "zone"), "lower_than_obj": "A"}}, needs=("higher",))
add("tall_between", "tall", {"A": TALL, "R": T, "Q": T}, [("A", "P")],
    _t("Stand the {A} between the {R} and the {Q}.", "Put the {A} in between the {R} and the {Q}.",
       "Place the tall {Anoun} halfway between the {R} and the {Q}.", "Set the {A} between the {R} and the {Q}.",
       "The {A} goes between the {R} and the {Q}."),
    [("VIMA", "rearrange"), ("LIB", "pick_up_the_black_bowl_between_the_plate_and_the_ramekin")],
    dst={"P": {"type": "spot", "between": ("R", "Q")}})
add("tall_to_back", "tall", {"A": TALL}, [("A", "P")],
    _t("Put the {A} at the very back of the {Msurf}.", "Move the {A} far back, against the back edge.",
       "Store the {A} deep at the back.", "Carry the {A} all the way to the back of the {Msurf}.",
       "Place the tall {Anoun} at the back."),
    [("RC", "arranging_condiments"), ("B1K", "storing_the_groceries")], dst={"P": {"type": "spot", "corner": "deep_back"}})

# 13. hollow: bowls / mugs / cups moved by rim or wall grasps (scene constraint wide_hollow / handle) — LIBERO, RoboTwin
HM = ("mug", "cup")
add("hol_bowl_on_plate", "hollow", {"A": hollow(("bowl",)), "H": PL}, [("A", "H")],
    _t("Put the {A} on the {H}.", "Place the {A} onto the {H}.", "Set the {A} on top of the {H}.",
       "Move the {A} to the {H}.", "The {A} goes on the {H}."),
    [("LIB", "put_the_bowl_on_the_plate"), ("LIB", "pick_up_the_black_bowl_next_to_the_plate_and_place_it_on_the_plate")],
    req=("exec:movable_container",))
add("hol_mug_on_plate", "hollow", {"A": hollow(HM), "H": PL}, [("A", "H")],
    _t("Put the {A} on the {H}.", "Place the {A} onto the {H}.", "Set the {A} down on the {H}.",
       "Move the {A} to the {H}.", "The {A} goes on the {H}."),
    [("LIB", "put_the_white_mug_on_the_plate"), ("RT2", "place_container_plate")], req=("exec:movable_container",))
add("hol_bowl_nest2", "hollow", {"A": hollow(("bowl",)), "B": dict(BOWL, nest=True)}, [("A", "B")],
    _t("Stack the {A} into the {B}.", "Nest the {A} inside the {B}.", "Put the {A} in the {B}.",
       "Place the {A} into the {B} to stack them.", "Stack the two bowls: {A} into {B}."),
    [("RT2", "stack_bowls_two"), ("RC", "organizing_dishes_and_containers")], req=("exec:movable_container",))
add("hol_bowl_nest3", "hollow", {"A": hollow(("bowl",)), "B": dict(BOWL, nest=True), "C": hollow(("bowl",))},
    [("A", "B"), ("C", "A")],
    _t("Stack the three bowls: the {A} into the {B}, then the {C} on top.", "Nest the {A} in the {B} and the {C} in the {A}.",
       "Put the {A} into the {B}, then the {C} into the {A}.", "Make a stack of bowls: {B}, {A}, {C}.",
       "First the {A} into the {B}; then the {C} into the {A}."),
    [("RT2", "stack_bowls_three")], req=("exec:movable_container",))
add("hol_mug_next_to", "hollow", {"A": hollow(HM), "R": T}, [("A", "P")],
    _t("Put the {A} to the right of the {R}.", "Move the {A} beside the {R}, on the right.", "Set the {A} right of the {R}.",
       "Place the {A} next to the {R}, on its right.", "The {A} goes on the right of the {R}."),
    [("RT2", "place_empty_cup"), ("LIB", "put_the_white_mug_on_the_plate_and_put_the_chocolate_pudding_to_the_right")],
    dst={"P": {"type": "spot", "rel": "right", "ref": "R"}}, req=("exec:movable_container",))
add("hol_cup_on_mat", "hollow", {"A": hollow(HM)}, [("A", "V")],
    _t("Put the {A} on the {V}.", "Set the {A} down on the {V}.", "Place the {A} onto the {V}.",
       "Move the {A} to the {V}.", "The {A} goes on the {V}."),
    [("RT2", "place_empty_cup"), ("RC", "serving_beverages")], dst={"V": ZN}, needs=("node:zone|seat",),
    req=("exec:movable_container",))
add("hol_bowl_to_zone", "hollow", {"A": hollow(("bowl",))}, [("A", "V")],
    _t("Put the {A} on the {V}.", "Move the {A} onto the {V}.", "Place the {A} on the {V}.",
       "Set the {A} down on the {V}.", "The {A} goes on the {V}."),
    [("LIB", "put_the_bowl_on_the_stove"), ("RC", "PickPlaceCounterToStove")], dst={"V": ZN},
    needs=("node:zone|seat",), req=("exec:movable_container",))
add("hol_two_mugs_plates", "hollow", {"A": hollow(HM), "B": hollow(HM), "H": PL, "G": PL}, [("A", "H"), ("B", "G")],
    _t("Put the {A} on the {H} and the {B} on the {G}.", "Place one mug on each plate: {A} on the {H}, {B} on the {G}.",
       "First the {A} onto the {H}, then the {B} onto the {G}.", "Set the {A} on the {H}; set the {B} on the {G}.",
       "The {A} goes on the {H}, the {B} on the {G}."),
    [("LIB", "put_the_white_mug_on_the_left_plate_and_put_the_yellow_and_white_mug_on_the_right_plate")],
    req=("exec:movable_container",))
add("hol_bowl_up", "hollow", {"A": hollow(("bowl",))}, [("A", "V")],
    _t("Put the {A} up on the {V}.", "Lift the {A} onto the higher {V}.", "Place the {A} on top of the {V}.",
       "Move the {A} up onto the {V}.", "The {A} goes up on the {V}."),
    [("LIB", "put_the_bowl_on_top_of_the_cabinet")],
    dst={"V": {"type": "node", "kinds": ("top", "zone"), "higher": True}}, needs=("higher",),
    req=("exec:movable_container",))
add("hol_bowl_in_shelf", "hollow", {"A": hollow(("bowl",))}, [("A", "V")],
    _t("Put the {A} away in the {V}.", "Store the {A} in the {V}.", "Place the {A} inside the {V}.",
       "Slide the {A} into the {V}.", "The {A} goes in the {V}."),
    [("B1K", "putting_dishes_away_after_cleaning"), ("RC", "organizing_dishes_and_containers")], dst={"V": SH},
    needs=(SHELF_NEED,), req=("exec:movable_container",) + FRONT)

# 14. pose: place poses beyond upright (lying, leaning, oriented, standing up) — CALVIN rotate, VIMA rotate, RLBench
LIE = {"role": "target", "lie_ok": True}
LEAN = {"role": "target", "lean_ok": True}
ORI = {"role": "target", "orientable": True}
PP = ("exec:place_pose",)
add("pose_lay_down", "pose", {"A": LIE, "R": T}, [("A", "P")],
    _t("Lay the {A} down on its side, right of the {R}.", "Put the {A} lying down next to the {R}, on the right.",
       "Place the {A} on its side to the right of the {R}.", "Set the {A} down flat beside the {R}.",
       "Lay the {A} flat on the right of the {R}."),
    [("SIMPLER", "pick_coke_can (lying horizontally)"), ("BRIDGE", "reorient")],
    dst={"P": {"type": "spot", "rel": "right", "ref": "R", "gap": 0.04}}, place={0: {"pose": "lying"}}, req=PP)
add("pose_lay_in_box", "pose", {"A": LIE, "H": dict(W_, cats=("box", "tray", "bin", "basket"))}, [("A", "H")],
    _t("Lay the {A} down inside the {H}.", "Put the {A} in the {H} on its side.", "Place the {A} lying flat in the {H}.",
       "Pack the {A} into the {H}, lying down.", "Lay the {A} in the {H}."),
    [("RT2", "place_cans_plasticbox"), ("B1K", "boxing_books_up_for_storage")], place={0: {"pose": "lying"}}, req=PP)
add("pose_stand_up", "pose", {"A": LIE}, [("A", "P")],
    _t("Stand the {A} upright.", "The {A} fell over: stand it up.", "Put the {A} back on its base.",
       "Turn the {A} upright and leave it here.", "Set the {A} upright again."),
    [("BRIDGE", "flip pot upright"), ("SIMPLER", "pick_coke_can (lying -> standing)")],
    dst={"P": {"type": "spot", "at_obj": "A"}}, start={"A": "lying"}, req=PP + ("exec:start_pose",))
add("pose_lean_divider", "pose", {"A": LEAN}, [("A", "V")],
    _t("Lean the {A} against the back of the {V}.", "Stand the {A} in the {V}, leaning on the wall.",
       "Put the {A} in the {V} propped against the side.", "Prop the {A} up against the wall of the {V}.",
       "Place the {A} leaning against the {V}'s wall."),
    [("RLB", "put_books_on_bookshelf"), ("B1K", "re-shelving_library_books")],
    dst={"V": {"type": "node", "kinds": ("cubby",) + SHELF_KINDS}}, needs=("node:cubby|" + SHELF_NEED[5:],),
    place={0: {"pose": "leaning"}}, req=PP)
add("pose_rotate90", "pose", {"A": ORI}, [("A", "P")],
    _t("Rotate the {A} a quarter turn and put it back down.", "Turn the {A} by 90 degrees where it is.",
       "Pick up the {A}, turn it sideways and set it down again.", "Rotate the {A} 90 degrees to the right.",
       "Give the {A} a quarter turn."),
    [("CAL", "rotate_red_block_right"), ("VIMA", "rotate")], dst={"P": {"type": "spot", "at_obj": "A"}},
    place={0: {"pose": "oriented", "orient": "rot90"}}, req=PP)
add("pose_long_side_lr", "pose", {"A": ORI, "R": T}, [("A", "P")],
    _t("Put the {A} left of the {R}, long side facing me.", "Place the {A} on the {R}'s left, lengthwise left-right.",
       "Set the {A} to the left of the {R} with its long side towards me.",
       "Move the {A} left of the {R} and line its long side up with the edge.",
       "The {A} goes left of the {R}, parallel to the edge."),
    [("VIMA", "rearrange"), ("CAL", "rotate_blue_block_left")], dst={"P": {"type": "spot", "rel": "left", "ref": "R"}},
    place={0: {"pose": "oriented", "orient": "long_lr"}}, req=PP)
add("pose_handle_right", "pose", {"A": hollow(HM, handle=True), "R": T}, [("A", "P")],
    _t("Put the {A} in front of the {R} with the handle to the right.", "Place the {A} before the {R}, handle pointing right.",
       "Set the {A} in front of the {R}; turn its handle to the right.", "Move the {A} in front of the {R}, handle on the right.",
       "The {A} goes in front of the {R} with its handle facing right."),
    [("VIMA", "rotate"), ("RLB", "place_cups")], dst={"P": {"type": "spot", "rel": "front", "ref": "R"}},
    place={0: {"pose": "oriented", "orient": "handle_right"}}, req=PP + ("exec:movable_container",))
add("pose_lay_in_shelf", "pose", {"A": dict(LIE, cats=("bottle", "can"))}, [("A", "V")],
    _t("Lay the {A} down in the {V}.", "Put the {A} on its side in the {V}, like in a wine rack.",
       "Store the {A} lying down in the {V}.", "Slide the {A} into the {V} lying flat.", "Lay the {A} in the {V}."),
    [("RLB", "stack_wine"), ("LIB", "put_the_wine_bottle_on_the_rack")], dst={"V": SH}, needs=(SHELF_NEED,),
    place={0: {"pose": "lying", "approach": "front"}}, req=PP + FRONT)
add("pose_lay_two", "pose", {"A": LIE, "B": LIE}, [("A", "P1"), ("B", "P2")],
    _t("Lay the {A} and the {B} down side by side.", "Put the {A} and then the {B} on their sides, next to each other.",
       "Lay both down in a row: {A} on the left, {B} on the right.", "Place the {A} and the {B} lying flat, side by side.",
       "Lay the {A} down, then lay the {B} down next to it."),
    [("B1K", "boxing_books_up_for_storage"), ("SIMPLER", "pick_coke_can (lying)")],
    dst={"P1": {"type": "spot", "line": ("y", 0, 2), "spacing": 0.15},
         "P2": {"type": "spot", "line": ("y", 1, 2), "spacing": 0.15}},
    place={0: {"pose": "lying"}, 1: {"pose": "lying"}}, req=PP)
add("pose_stand_in_shelf", "pose", {"A": LEAN}, [("A", "V")],
    _t("Stand the {A} upright in the {V}, spine facing out.", "Put the {A} in the {V} standing up, facing me.",
       "Shelve the {A} upright in the {V}.", "Place the {A} standing in the {V}, front side out.",
       "Stand the {A} up in the {V}."),
    [("RLB", "put_books_on_bookshelf"), ("B1K", "sorting_books")], dst={"V": SH}, needs=(SHELF_NEED,),
    place={0: {"pose": "oriented", "orient": "long_lr", "approach": "front"}}, req=PP + FRONT)

# 15. kitchen: RoboCasa atomic pick-place between counter / sink / board / rack (open nodes only)
add("kit_to_sink", "kitchen", {"A": T}, [("A", "V")],
    _t("Put the {A} in the sink.", "Place the {A} into the {V}.", "Drop the {A} in the {V} to wash it.",
       "Move the {A} from the counter into the {V}.", "The {A} goes in the {V}."),
    [("RC", "PickPlaceCounterToSink"), ("B1K", "washing_dishes")],
    dst={"V": {"type": "node", "kinds": ("container",)}}, needs=("node:container",))
add("kit_from_sink", "kitchen", {"A": dict(T, on="node:container")}, [("A", "P")],
    _t("Take the {A} out of the {Asurf} and put it on the {Msurf}.", "Get the {A} out of the sink.",
       "Move the {A} from the {Asurf} onto the {Msurf}.", "Lift the {A} out of the {Asurf}.",
       "Put the {A} from the {Asurf} back on the counter."),
    [("RC", "PickPlaceSinkToCounter")], dst={"P": {"type": "spot", "off_node": "A"}}, needs=("node:container",))
add("kit_to_board", "kitchen", {"A": dict(T, cats=FOOD)}, [("A", "V")],
    _t("Put the {A} on the {V} for chopping.", "Place the {A} onto the {V}.", "Move the {A} to the {V}.",
       "Set the {A} on the {V} to prepare it.", "The {A} goes on the {V}."),
    [("RC", "chopping_food"), ("B1K", "chopping_vegetables")], dst={"V": ZN}, needs=("node:zone|seat",))
add("kit_board_to_bowl", "kitchen", {"A": dict(T, cats=FOOD, on="node:zone|seat"), "H": BOWL}, [("A", "H")],
    _t("Put the {A} from the {Asurf} into the {H}.", "Move the {A} off the {Asurf} into the {H}.",
       "Drop the prepared {A} in the {H}.", "Take the {A} from the {Asurf} and put it in the {H}.",
       "The {A} on the {Asurf} goes in the {H}."),
    [("B1K", "preparing_salad"), ("RC", "making_salads")], needs=("node:zone|seat",))
add("kit_sink_to_rack", "kitchen", {"A": dict(SL, on="node:container")}, [("A", "V")],
    _t("Take the {A} from the {Asurf} and stand it in the {V}.", "Move the {A} from the sink to the {V}.",
       "Put the washed {A} in the {V} to dry.", "Stand the {A} from the {Asurf} in the {V}.",
       "The {A} goes from the sink into the {V}."),
    [("B1K", "washing_dishes"), ("RLB", "put_plate_in_colored_dish_rack")], dst={"V": HV},
    judge={"upright_max_deg": 30.0}, needs=("node:container", "node:slot"))
add("kit_rack_to_counter", "kitchen", {"A": dict(SL, on="node:slot")}, [("A", "P")],
    _t("Take the {A} out of the {Asurf} and put it on the {Msurf}.", "Get the {A} out of the {Asurf}.",
       "Move the {A} from the {Asurf} to the counter.", "Lift the {A} out of the {Asurf}.",
       "Put the {A} from the {Asurf} down on the {Msurf}."),
    [("RLB", "take_plate_off_colored_dish_rack"), ("RC", "organizing_utensils")],
    dst={"P": {"type": "spot", "off_node": "A"}}, needs=("node:slot",))
add("kit_can_next_pot", "kitchen", {"A": dict(T, cats=("can", "bottle")), "H": BOWL}, [("A", "P")],
    _t("Move the {A} next to the {H}, on its left.", "Put the {A} beside the {H}, to the left.",
       "Set the {A} on the left of the {H}.", "Place the {A} left of the {H}, close to it.",
       "The {A} goes left of the {H}."),
    [("RT2", "move_can_pot"), ("RC", "arranging_condiments")], dst={"P": {"type": "spot", "rel": "left", "ref": "H"}})
add("kit_serve_two", "kitchen", {"A": dict(T, cats=FOOD), "B": dict(T, cats=FOOD), "H": BOWL, "G": PL},
    [("A", "H"), ("B", "G")],
    _t("Put the {A} in the {H} and the {B} on the {G}.", "Serve the {A} in the {H}, then the {B} on the {G}.",
       "Plate the food: {A} into the {H}, {B} onto the {G}.", "First the {A} into the {H}, then the {B} onto the {G}.",
       "The {A} goes in the {H}, the {B} on the {G}."),
    [("RC", "serving_food"), ("RC", "plating_food")])

# 16. tidy: tidying / packing several objects in order (2-3 steps) — BEHAVIOR, RoboCasa composite
add("tidy_return_two", "tidy", {"A": T, "B": T, "H": W_}, [("A", "H"), ("B", "V")],
    _t("Put the {A} back in the {H} and the {B} on the {V}.", "Tidy up: {A} into the {H}, {B} onto the {V}.",
       "Return the {A} to the {H}, then the {B} to the {V}.", "First the {A} in the {H}; then the {B} on the {V}.",
       "Put each away: the {A} in the {H}, the {B} on the {V}."),
    [("B1K", "collect_misplaced_items"), ("B1K", "cleaning_bedroom")], dst={"V": SV}, needs=("node:stand",))
add("tidy_desk", "tidy", {"A": SL, "B": T}, [("A", "V"), ("B", "P")],
    _t("Tidy the desk: the {A} into the {V}, the {B} to the back left.", "Put the {A} in the {V} and move the {B} to the back left.",
       "Stand the {A} in the {V}, then put the {B} at the back left.", "First the {A} into the {V}; then the {B} to the back.",
       "Clean up: {A} in the {V}, {B} back left."),
    [("B1K", "organizing_school_stuff"), ("RC", "organizing_utensils")],
    dst={"V": HV, "P": {"type": "spot", "corner": "back_left"}}, judge=UP, needs=("node:slot",))
add("tidy_pack_lunch", "tidy", {"A": dict(T, cats=FOOD), "B": dict(T, cats=("can", "bottle")), "H": WB},
    [("A", "H"), ("B", "H")],
    _t("Pack a lunch: put the {A} and the {B} in the {H}.", "Put the {A} and then the {B} into the {H}.",
       "Pack the {A} and the {B} in the {H}.", "Lunch goes in the {H}: first the {A}, then the {B}.",
       "Put the food and the drink into the {H}."),
    [("RC", "packing_lunches"), ("B1K", "packing_lunches")])
add("tidy_picnic", "tidy", {"A": dict(T, cats=FOOD), "B": dict(T, cats=("can", "bottle")), "C": dict(T, cats=FOOD),
                            "H": WB}, [("A", "H"), ("B", "H"), ("C", "H")],
    _t("Pack the picnic basket: {A}, {B} and {C} into the {H}.", "Put the {A}, the {B} and the {C} in the {H}.",
       "One by one, pack the {A}, the {B} and the {C} into the {H}.", "Load the {H} with the {A}, the {B} and the {C}.",
       "Pack everything for the picnic in the {H}: {A}, {B}, {C}."),
    [("B1K", "packing_picnics")])
add("tidy_gift_basket", "tidy", {"A": T, "B": T, "H": dict(WB, cats=("basket", "box", "bin"))},
    [("A", "H"), ("B", "H")],
    _t("Fill the gift basket with the {A} and the {B}.", "Put the {A} and the {B} into the {H} as a gift.",
       "Assemble the gift: {A} then {B} into the {H}.", "Place the {A} and the {B} in the {H}.",
       "Add the {A} and the {B} to the {H}."),
    [("B1K", "assembling_gift_baskets"), ("B1K", "filling_an_Easter_basket")])
add("tidy_trash_two", "tidy", {"A": T, "B": T, "H": dict(WB, cats=("bin",))}, [("A", "H"), ("B", "H")],
    _t("Throw the {A} and the {B} in the {H}.", "Pick up the trash: {A} and {B} into the {H}.",
       "Put the {A} in the {H}, then the {B}.", "Clean up by dropping the {A} and the {B} into the {H}.",
       "The {A} and the {B} go in the trash {H}."),
    [("B1K", "picking_up_trash"), ("B1K", "throwing_away_leftovers")])
add("tidy_toys_away", "tidy", {"A": dict(T, cats=TOY), "B": dict(T, cats=TOY), "H": dict(WB, cats=("bin", "basket", "box"))},
    [("A", "H"), ("B", "H")],
    _t("Put the toys away: {A} and {B} into the {H}.", "Tidy the {A} and the {B} into the {H}.",
       "Put the {A} in the {H}, then the {B}.", "Both toys go in the {H}: the {A} and the {B}.",
       "Clean up the toys into the {H}."),
    [("B1K", "putting_away_toys"), ("B1K", "cleaning_bedroom")])
add("tidy_clear_and_stack", "tidy", {"A": T, "C": B_, "B": T, "H": W_}, [("A", "H"), ("B", "C")],
    _t("Put the {A} in the {H} and stack the {B} on the {C}.", "Tidy up: {A} into the {H}, {B} onto the {C}.",
       "First the {A} into the {H}; then the {B} on top of the {C}.", "Drop the {A} in the {H}, then put the {B} on the {C}.",
       "The {A} goes in the {H}, the {B} on the {C}."),
    [("B1K", "cleaning_table_after_clearing"), ("B1K", "boxing_books_up_for_storage")])
add("tidy_clear_to_shelf", "tidy", {"A": T, "B": T, "H": BIN}, [("A", "V"), ("B", "H")],
    _t("Put the {A} away in the {V} and throw the {B} in the {H}.", "Clean up: {A} to the shelf, {B} into the {H}.",
       "First store the {A} in the {V}, then drop the {B} in the {H}.", "The {A} goes on the shelf, the {B} in the {H}.",
       "Tidy the {A} into the {V} and the {B} into the {H}."),
    [("B1K", "cleaning_up_after_a_meal"), ("RC", "clearing_table")], dst={"V": SH}, needs=(SHELF_NEED,), req=FRONT)
add("tidy_stock_shelf", "tidy", {"A": T, "B": T}, [("A", "V1"), ("B", "V2")],
    _t("Stock the shelves: the {A} in one compartment, the {B} in another.", "Put the {A} in the {V1} and the {B} in the {V2}.",
       "Restock: {A} into one shelf, {B} into the other.", "First the {A} onto one shelf, then the {B} onto the other.",
       "Store the {A} and the {B} on two different shelves."),
    [("RC", "restocking_supplies"), ("B1K", "storing_the_groceries")], dst={"V1": SH, "V2": SH},
    needs=(SHELF_NEED.replace("node:", "node2:"),), req=FRONT)
add("tidy_pack_bag", "tidy", {"A": dict(T, cats=("book", "box", "block")), "B": dict(T, cats=TOY + ("can", "bottle")),
                              "H": WB}, [("A", "H"), ("B", "H")],
    _t("Pack the bag: the {A} and the {B} go in the {H}.", "Put the {A} and the {B} into the {H} for school.",
       "Pack the {A} first, then the {B}, into the {H}.", "Load the {A} and the {B} into the {H}.",
       "Get the {H} ready: put in the {A} and the {B}."),
    [("B1K", "packing_child_s_bag"), ("B1K", "packing_bags_or_suitcase")])
add("tidy_two_mats", "tidy", {"A": T, "B": T}, [("A", "V1"), ("B", "V2")],
    _t("Put the {A} on one mat and the {B} on the other.", "Place one item per mat: {A} then {B}.",
       "Set the {A} on the {V1} and the {B} on the {V2}.", "Arrange the {A} and the {B} on the two mats.",
       "First the {A} onto a mat, then the {B} onto the other."),
    [("RC", "arranging_buffet"), ("B1K", "setting_up_candles")], dst={"V1": ZN, "V2": ZN},
    needs=("node2:zone|seat",))

# 17. transfer: out of / between containers and compartments — BEHAVIOR unpacking, RoboTwin plate / basket tasks
add("tr_out_of_basket", "transfer", {"H": W_, "A": dict(T, on="on:H")}, [("A", "P")],
    _t("Take the {A} out of the {H}.", "Unpack the {A} from the {H} onto the {Msurf}.", "Remove the {A} from the {H}.",
       "Get the {A} out of the {H} and set it down.", "Empty the {H}: the {A} goes on the {Msurf}."),
    [("B1K", "unpacking_suitcase"), ("RT2", "place_object_basket (reverse)")],
    dst={"P": {"type": "spot", "off_node": "A"}})
add("tr_basket_to_bowl", "transfer", {"H": W_, "A": dict(T, on="on:H"), "G": W_}, [("A", "G")],
    _t("Move the {A} from the {H} to the {G}.", "Take the {A} out of the {H} and put it in the {G}.",
       "Transfer the {A} into the {G}.", "The {A} in the {H} goes into the {G}.", "Put the {A} from the {H} in the {G}."),
    [("RC", "organizing_dishes_and_containers"), ("B1K", "storing_food")])
add("tr_plate_to_plate", "transfer", {"P0": PL, "A": dict(T, on="on:P0"), "H": PL}, [("A", "H")],
    _t("Move the {A} from the {P0} to the {H}.", "Transfer the {A} onto the {H}.", "Put the {A} from the {P0} on the {H}.",
       "Take the {A} off the {P0} and set it on the {H}.", "The {A} goes from the {P0} to the {H}."),
    [("RT2", "place_bread_skillet"), ("RT2", "place_burger_fries")])
add("tr_tray_to_bin", "transfer", {"P0": PL, "A": dict(T, on="on:P0"), "H": BIN}, [("A", "H")],
    _t("Clear the {A} from the {P0} into the {H}.", "Take the {A} off the {P0} and drop it in the {H}.",
       "Move the {A} from the {P0} to the {H}.", "Empty the {P0} into the {H}.", "The {A} on the {P0} goes in the {H}."),
    [("B1K", "clearing_the_table_after_dinner"), ("RC", "clearing_table")])
add("tr_out_of_cubby", "transfer", {"A": dict(T, on="node:cubby")}, [("A", "P")],
    _t("Take the {A} out of the {Asurf}.", "Get the {A} from the {Asurf} and put it on the {Msurf}.",
       "Remove the {A} from its compartment.", "Lift the {A} out of the {Asurf}.", "Move the {A} out onto the {Msurf}."),
    [("CAL", "lift_red_block_slider"), ("RC", "PickPlaceDrawerToCounter (open)")],
    dst={"P": {"type": "spot", "off_node": "A"}}, needs=("node:cubby",))
add("tr_cubby_to_cubby", "transfer", {"A": dict(T, on="node:cubby")}, [("A", "V")],
    _t("Move the {A} to the other compartment.", "Put the {A} in the {V} instead.", "Take the {A} out and put it in the {V}.",
       "Shift the {A} into the other compartment.", "Re-file the {A} into the {V}."),
    [("B1K", "organizing_file_cabinet"), ("LIB", "pick_up_the_book_and_place_it_in_the_back_compartment_of_the_caddy")],
    dst={"V": {"type": "node", "kinds": ("cubby",), "not_obj_node": "A"}}, needs=("node2:cubby",))
add("tr_slot_to_slot", "transfer", {"A": dict(SL, on="node:slot")}, [("A", "V")],
    _t("Move the {A} to the other holder.", "Take the {A} out and stand it in the {V}.", "Put the {A} in the other holder.",
       "Shift the {A} into the {V}.", "Swap the {A} over to the other holder."),
    [("B1K", "organizing_school_stuff")], dst={"V": dict(HV, not_obj_node="A")}, judge=UP, needs=("node2:slot",))
add("tr_out_two_containers", "transfer", {"H": W_, "A": dict(T, on="on:H"), "G": W_, "B": dict(T, on="on:G")},
    [("A", "P1"), ("B", "P2")],
    _t("Take the {A} out of the {H} and the {B} out of the {G}, and line them up.",
       "Unpack both: {A} from the {H}, {B} from the {G}.", "Empty the {H} and the {G} onto the {Msurf}, side by side.",
       "First get the {A} out of the {H}, then the {B} out of the {G}.", "Put the {A} and the {B} in a row on the {Msurf}."),
    [("B1K", "unpacking_suitcase"), ("B1K", "opening_presents")],
    dst={"P1": {"type": "spot", "line": ("y", 0, 2)}, "P2": {"type": "spot", "line": ("y", 1, 2)}})
add("tr_bin_to_plate", "transfer", {"H": W_, "A": dict(T, on="on:H"), "G": PL}, [("A", "G")],
    _t("Take the {A} out of the {H} and put it on the {G}.", "Move the {A} from the {H} onto the {G}.",
       "Serve the {A} from the {H} on the {G}.", "The {A} in the {H} goes on the {G}.", "Put the {A} on the {G}."),
    [("RC", "PickPlaceSinkToCounter"), ("RC", "serving_food")])
add("tr_stand_to_bowl", "transfer", {"A": dict(T, on="node:stand"), "H": W_}, [("A", "H")],
    _t("Take the {A} off the block and put it in the {H}.", "Move the {A} from the block into the {H}.",
       "Unstack the {A} and drop it in the {H}.", "The {A} on the block goes into the {H}.",
       "Put the {A} from the block in the {H}."),
    [("CAL", "unstack_block"), ("CAL", "place_in_slider")], needs=("node:stand",))

# 18. recovery: a deliberate perturbation of one place (off target / tilted) that the next call corrects
RCV = (("rel_left", "off_target"), ("in_wide", "off_target"), ("line2_x", "off_target"),
       ("set_food_on_plate", "off_target"), ("block_stack", "tilted"), ("ins_one", "tilted"),
       ("to_front_left", "off_target"), ("set_drink_right", "tilted"))
for _b, _k in RCV:
    _d = T9.DEFS[_b]
    add(f"rcv_{_b}_{'off' if _k == 'off_target' else 'tilt'}", "recovery", _d.objs, _d.steps, _d.templates,
        [("RT2", "domain randomisation + retry (expert replanning)"), ("DROID", "recovery / retry segments")],
        dst=_d.dst, judge=_d.judge, needs=_d.needs, req=("exec:recovery",), recovery={"step": 0, "kind": _k})

# v1 families: more relations / edges / gaps / ordered multi-step (VIMA, LIBERO-spatial, RoboTwin, CALVIN)
for _rel, _w in (("front_right", ("in front of and to the right of", "front-right of")),
                 ("behind_left", ("behind and to the left of", "back-left of")),
                 ("behind_right", ("behind and to the right of", "back-right of"))):
    add(f"rel_{_rel}", "relation", {"A": T, "R": T}, [("A", "P")],
        _t(f"Put the {{A}} {_w[0]} the {{R}}.", f"Place the {{A}} {_w[1]} the {{R}}.",
           f"Move the {{A}} so it ends up {_w[1]} the {{R}}.", f"Set the {{A}} diagonally {_w[0]} the {{R}}.",
           f"The {{A}} goes {_w[1]} the {{R}}."),
        [("LIB", "libero_spatial"), ("VIMA", "rearrange")], dst={"P": {"type": "spot", "rel": _rel, "ref": "R"}})
add("rel_between_containers", "relation", {"A": T, "H": W_, "G": W_}, [("A", "P")],
    _t("Put the {A} between the {H} and the {G}.", "Place the {A} in the middle of the {H} and the {G}.",
       "Set the {A} halfway between the {H} and the {G}.", "Move the {A} in between the two containers.",
       "The {A} goes between the {H} and the {G}."),
    [("LIB", "pick_up_the_black_bowl_between_the_plate_and_the_ramekin"), ("VIMA", "rearrange")],
    dst={"P": {"type": "spot", "between": ("H", "G")}})
for _c, _w in (("front_edge", ("near edge", "the front edge, closest to me")), ("deep_back", ("very back", "the back")),
               ("left_edge", ("left edge", "the far left")), ("right_edge", ("right edge", "the far right"))):
    add(f"arr_{_c}", "arrange", {"A": T}, [("A", "P")],
        _t(f"Move the {{A}} to the {_w[0]} of the {{Msurf}}.", f"Put the {{A}} at {_w[1]}.",
           f"Place the {{A}} along the {_w[0]}.", f"Set the {{A}} down at the {_w[0]} of the {{Msurf}}.",
           f"The {{A}} goes to the {_w[0]}."),
        [("RC", "arranging_condiments") if _c == "deep_back" else ("VIMA", "rearrange"), ("B1K", "rearranging_furniture")],
        dst={"P": {"type": "spot", "corner": _c}})
add("arr_gap_narrow", "arrange", {"A": T, "R": T, "Q": dict(T, beside={"ref": "R", "room_for": "A"})}, [("A", "P")],
    _t("Fit the {A} into the narrow gap between the {R} and the {Q}.", "Squeeze the {A} in between the {R} and the {Q}.",
       "Put the {A} in the small space between the {R} and the {Q}.", "Place the {A} carefully between the {R} and the {Q}.",
       "The {A} goes into the gap between the {R} and the {Q}."),
    [("LIB", "pick_up_the_black_bowl_between_the_plate_and_the_ramekin"), ("VIMA", "rearrange")],
    dst={"P": {"type": "spot", "between": ("R", "Q")}})
add("arr_line3_x", "arrange", {"A": T, "B": T, "C": T}, [("A", "P1"), ("B", "P2"), ("C", "P3")],
    _t("Line up the {A}, the {B} and the {C} from front to back.", "Make a front-to-back row: {A}, {B}, {C}.",
       "Put the {A} nearest to me, then the {B}, then the {C} behind.", "Arrange the {A}, {B} and {C} one behind the other.",
       "Set the {A}, the {B} and the {C} in a line going away from me."),
    [("VIMA", "rearrange"), ("B1K", "collect_misplaced_items")],
    dst={"P1": {"type": "spot", "line": ("x", 0, 3), "spacing": 0.10}, "P2": {"type": "spot", "line": ("x", 1, 3), "spacing": 0.10},
         "P3": {"type": "spot", "line": ("x", 2, 3), "spacing": 0.10}})
add("arr_diag", "arrange", {"A": T, "B": T}, [("A", "P1"), ("B", "P2")],
    _t("Put the {A} at the front left and the {B} at the back right.", "Move the {A} to the near left and the {B} to the far right.",
       "Place the {A} front-left, then the {B} back-right.", "Spread them out: {A} front left, {B} back right.",
       "First the {A} to the front left corner, then the {B} to the back right corner."),
    [("VIMA", "rearrange"), ("B1K", "rearranging_furniture")],
    dst={"P1": {"type": "spot", "corner": "front_left"}, "P2": {"type": "spot", "corner": "back_right"}})
add("arr_colour_row3", "arrange", {"A": dict(T, colour_named=True), "B": dict(T, colour_named=True, other_colour="A"),
                                   "C": dict(T, colour_named=True, other_colours=("A", "B"))},
    [("A", "P1"), ("B", "P2"), ("C", "P3")],
    _t("Line up the {Acol}, {Bcol} and {Ccol} objects from left to right.", "Make a row by colour: {Acol}, {Bcol}, {Ccol}.",
       "Put the {A}, the {B} and the {C} in a row, left to right.", "Order them by colour, left to right: {Acol}, {Bcol}, {Ccol}.",
       "Arrange the {Acol} one, the {Bcol} one and the {Ccol} one in a line."),
    [("RT2", "blocks_ranking_rgb"), ("VIMA", "rearrange")],
    dst={"P1": {"type": "spot", "line": ("y", 0, 3)}, "P2": {"type": "spot", "line": ("y", 1, 3)},
         "P3": {"type": "spot", "line": ("y", 2, 3)}})
add("st_tower_stand", "stack", {"A": dict(B_, as_target=True), "B": T}, [("A", "V"), ("B", "A")],
    _t("Build a tower on the {V}: the {A} first, then the {B} on top.", "Put the {A} on the {V} and the {B} on the {A}.",
       "Stack the {A} onto the {V}, then the {B} onto the {A}.", "Make a tower: {V}, {A}, {B}.",
       "First the {A} on the {V}; then the {B} on top of it."),
    [("RT2", "stack_blocks_two"), ("CAL", "stack_block")], dst={"V": SV}, needs=("node:stand",))
add("st_tower3_stand", "stack", {"A": dict(B_, as_target=True), "B": dict(B_, as_target=True), "C": T},
    [("A", "V"), ("B", "A"), ("C", "B")],
    _t("Build a three-level tower on the {V}: {A}, {B}, then {C}.", "Stack the {A} on the {V}, the {B} on the {A}, the {C} on the {B}.",
       "Make a tower of the {A}, the {B} and the {C} on the {V}.", "One by one, stack the {A}, {B} and {C} on the {V}.",
       "Put the {A} on the {V}, then the {B} on it, then the {C} on top."),
    [("RT2", "stack_blocks_three")], dst={"V": SV}, needs=("node:stand",))
add("st_on_book", "stack", {"A": T, "B": dict(B_, cats=("book", "box"))}, [("A", "B")],
    _t("Put the {A} on top of the {B}.", "Stack the {A} on the {B}.", "Set the {A} onto the {B}.",
       "Place the {A} on the {B}.", "The {A} goes on top of the {B}."),
    [("B1K", "boxing_books_up_for_storage"), ("RLB", "stack_blocks")])
add("st_colour_pair", "stack", {"A": dict(T, colour_named=True), "B": dict(B_, colour_named=True, other_colour="A")},
    [("A", "B")],
    _t("Stack the {Acol} one on the {Bcol} one.", "Put the {A} on top of the {B}.", "The {Acol} goes on the {Bcol}.",
       "Place the {Acol} {Anoun} onto the {Bcol} {Bnoun}.", "Set the {A} on the {B}."),
    [("CAL", "stack_block"), ("VIMA", "visual_manipulation")])
add("st_unstack_to_bin", "stack", {"B": B_, "A": dict(T, on="stacked:B"), "H": W_}, [("A", "H")],
    _t("Take the {A} off the {B} and drop it in the {H}.", "Unstack the {A} into the {H}.",
       "Remove the {A} from the top of the {B}; it goes in the {H}.", "Lift the {A} off the {B} and put it in the {H}.",
       "The {A} on the {B} goes into the {H}."),
    [("CAL", "unstack_block"), ("CAL", "place_in_drawer (open)")])
add("ins_two_one_holder", "insert", {"A": SL, "B": SL}, [("A", "V"), ("B", "V")],
    _t("Put the {A} and the {B} into the {V}.", "Stand both the {A} and the {B} in the {V}.",
       "Insert the {A}, then the {B}, into the {V}.", "The {A} and the {B} both go in the {V}.",
       "Put the {A} in the {V} and the {B} next to it in the same holder."),
    [("B1K", "organizing_school_stuff"), ("RC", "organizing_utensils")], dst={"V": dict(HV, shared=True)}, judge=UP,
    needs=("node:slot",))
add("ins_narrow_cont", "insert", {"A": SL, "H": NAR}, [("A", "H")],
    _t("Put the {A} into the {H}.", "Stand the {A} up in the {H}.", "Insert the {A} into the {H}.",
       "Place the {A} upright in the {H}.", "The {A} goes in the {H}."),
    [("B1K", "organizing_school_stuff"), ("RLB", "put_umbrella_in_umbrella_stand")], judge={"upright_max_deg": 30.0})
add("ins_candle", "insert", {"A": SL, "H": dict(NAR, cats=("vase", "jar", "cup", "mug"))}, [("A", "H")],
    _t("Set the {A} up in the {H}.", "Put the {A} upright into the {H}.", "Stand the {A} in the {H} like a candle.",
       "Insert the {A} in the {H}.", "Place the {A} into the {H}, standing."),
    [("B1K", "setting_up_candles")], judge={"upright_max_deg": 30.0})
add("ins_from_shelf", "insert", {"A": dict(SL, on=SHELF_NEED)}, [("A", "V")],
    _t("Take the {A} from the {Asurf} and stand it in the {V}.", "Get the {A} off the shelf and put it in the {V}.",
       "Move the {A} from the {Asurf} into the {V}.", "Put the {A} from the shelf in the {V}.",
       "The {A} on the shelf goes into the {V}."),
    [("RC", "PickPlaceCabinetToCounter"), ("B1K", "organizing_school_stuff")], dst={"V": HV}, judge=UP,
    needs=(SHELF_NEED, "node:slot"), req=FRONT)
add("ins_from_bin", "insert", {"H": W_, "A": dict(SL, on="on:H")}, [("A", "V")],
    _t("Take the {A} out of the {H} and stand it in the {V}.", "Move the {A} from the {H} into the {V}.",
       "Put the {A} that is in the {H} into the {V}.", "Get the {A} from the {H}; insert it into the {V}.",
       "The {A} in the {H} goes into the {V}."),
    [("B1K", "organizing_school_stuff"), ("B1K", "unpacking_suitcase")], dst={"V": HV}, judge=UP, needs=("node:slot",))
add("sort_colour3_bins", "sort", {"A": dict(T, colour_named=True), "B": dict(T, colour_named=True, other_colour="A"),
                                  "C": dict(T, same_colour="A"), "H": W_, "G": W_},
    [("A", "H"), ("B", "G"), ("C", "H")],
    _t("Sort by colour: the {Acol} things into the {H}, the {Bcol} one into the {G}.",
       "Put the {A} and the {C} in the {H}, and the {B} in the {G}.", "{Acol} goes in the {H}, {Bcol} in the {G}: {A}, {B}, {C}.",
       "Place the {A} in the {H}, the {B} in the {G}, then the {C} in the {H}.",
       "Separate the three by colour into the {H} and the {G}."),
    [("VIMA", "rearrange"), ("RT2", "blocks_ranking_rgb")])
add("sort_drink_food", "sort", {"A": dict(T, cats=("can", "bottle")), "B": dict(T, cats=FOOD), "H": PL, "G": BOWL},
    [("A", "H"), ("B", "G")],
    _t("Drinks on the {H}, food in the {G}: sort the {A} and the {B}.", "Put the {A} on the {H} and the {B} in the {G}.",
       "Sort the groceries: {A} onto the {H}, {B} into the {G}.", "The drink goes on the {H}, the food in the {G}.",
       "Place the {A} on the {H}, then the {B} in the {G}."),
    [("B1K", "sorting_groceries"), ("RC", "sorting_ingredients")])
add("sort_recycle", "sort", {"A": dict(T, cats=("can", "bottle")), "B": dict(T, cats=FOOD), "H": BIN, "G": BOWL},
    [("A", "H"), ("B", "G")],
    _t("Recycle the {A} in the {H} and keep the {B} in the {G}.", "Put the {A} in the {H} and the {B} in the {G}.",
       "Sort: the drink container into the {H}, the food into the {G}.", "The {A} goes to recycling ({H}), the {B} into the {G}.",
       "First the {A} into the {H}, then the {B} into the {G}."),
    [("B1K", "collecting_aluminum_cans"), ("RC", "organizing_recycling")])
add("sort_book_toy", "sort", {"A": dict(T, cats=("book",)), "B": dict(T, cats=TOY), "H": BIN}, [("A", "V"), ("B", "H")],
    _t("Put the book on the {V} and the toy in the {H}.", "Sort: {A} onto the {V}, {B} into the {H}.",
       "The {A} goes on the {V}, the {B} in the {H}.", "First the book on the {V}, then the toy in the {H}.",
       "Separate the {A} and the {B}: block for books, {H} for toys."),
    [("B1K", "sorting_books"), ("B1K", "putting_away_toys")], dst={"V": SV}, needs=("node:stand",))
add("sort_shelf_bin", "sort", {"A": dict(T, cats=FOOD), "B": dict(T, cats=TOY), "H": BIN}, [("A", "V"), ("B", "H")],
    _t("Food on the shelf, toys in the {H}: sort the {A} and the {B}.", "Put the {A} in the {V} and the {B} in the {H}.",
       "Store the {A} on the shelf and drop the {B} in the {H}.", "The {A} goes in the {V}, the {B} in the {H}.",
       "First the {A} onto the shelf, then the {B} into the {H}."),
    [("B1K", "storing_the_groceries"), ("B1K", "putting_away_toys")], dst={"V": SH}, needs=(SHELF_NEED,), req=FRONT)
add("set_place_three", "set", {"A": dict(T, cats=FOOD), "H": PL, "B": dict(T, cats=("can", "bottle")),
                               "C": dict(T, cats=FOOD), "G": BOWL}, [("A", "H"), ("B", "P"), ("C", "G")],
    _t("Set the place: {A} on the {H}, {B} to its right, {C} in the {G}.",
       "Put the {A} on the {H}, the {B} right of the {H}, and the {C} in the {G}.",
       "Serve a meal: first the {A} onto the {H}, then the {B} beside it, then the {C} into the {G}.",
       "Lay the table with the {A} on the {H}, the {B} on its right and the {C} in the {G}.",
       "Plate the {A}, place the {B} next to the plate, and put the {C} in the {G}."),
    [("RLB", "set_the_table"), ("B1K", "serving_a_meal")], dst={"P": {"type": "spot", "rel": "right", "ref": "H"}})
add("set_behind_plate", "set", {"A": dict(T, cats=DRINK), "H": PL}, [("A", "P")],
    _t("Set the {A} behind the {H}.", "Put the {A} on the far side of the {H}.", "Place the {A} just behind the {H}.",
       "The {A} goes behind the {H}.", "Put the {A} beyond the {H}, away from me."),
    [("RLB", "set_the_table"), ("B1K", "serving_a_meal")], dst={"P": {"type": "spot", "rel": "behind", "ref": "H"}})
add("set_hors_tray", "set", {"A": dict(T, cats=FOOD), "B": dict(T, cats=FOOD), "H": dict(PL, big=True)},
    [("A", "H"), ("B", "H")],
    _t("Serve the {A} and the {B} on the {H}.", "Put the {A} and then the {B} on the {H}.",
       "Arrange the {A} and the {B} on the {H} as snacks.", "Place both the {A} and the {B} onto the {H}.",
       "Set the {A} and the {B} out on the {H}."),
    [("B1K", "serving_hors_d_oeuvres"), ("RT2", "place_burger_fries")])
add("set_two_drinks", "set", {"A": dict(T, cats=DRINK), "B": dict(T, cats=DRINK), "H": PL}, [("A", "P1"), ("B", "P2")],
    _t("Put the {A} left of the {H} and the {B} right of it.", "Flank the {H} with drinks: {A} left, {B} right.",
       "Set the {A} on the {H}'s left, then the {B} on its right.", "Place one drink on each side of the {H}.",
       "The {A} goes left of the {H}, the {B} right of it."),
    [("RLB", "set_the_table"), ("LIB", "put_the_white_mug_on_the_left_plate_and_put_the_yellow_and_white_mug_on_the_right_plate")],
    dst={"P1": {"type": "spot", "rel": "left", "ref": "H"}, "P2": {"type": "spot", "rel": "right", "ref": "H"}})
add("set_coaster", "set", {"A": dict(T, cats=DRINK)}, [("A", "V")],
    _t("Put the {A} on the {V}.", "Set the drink down on the {V}.", "Place the {A} onto the {V}.",
       "Move the {A} to the {V} so it does not mark the table.", "The {A} goes on the {V}."),
    [("RT2", "place_empty_cup"), ("RC", "serving_beverages")], dst={"V": ZN}, needs=("node:zone|seat",))
add("clear_after_meal", "clear", {"P0": PL, "A": dict(T, on="on:P0"), "H": BIN, "B": dict(T, cats=DRINK)},
    [("A", "H"), ("B", "P")],
    _t("Clear up: the {A} from the {P0} into the {H}, the {B} to the back right.",
       "Throw the {A} on the {P0} in the {H}, then move the {B} to the back right.",
       "After the meal: {A} into the {H}, {B} out of the way at the back right.",
       "First empty the {P0} into the {H}; then put the {B} at the back right.",
       "Clear the table: {A} in the {H}, {B} back right."),
    [("B1K", "clearing_the_table_after_dinner"), ("RC", "clearing_table")],
    dst={"P": {"type": "spot", "corner": "back_right"}})
add("clear_cans", "clear", {"A": dict(T, cats=("can", "bottle")), "B": dict(T, cats=("can", "bottle")),
                            "H": dict(WB, cats=("bin", "basket", "box"))}, [("A", "H"), ("B", "H")],
    _t("Collect the {A} and the {B} into the {H}.", "Put both drink containers in the {H}.",
       "Clear the {A}, then the {B}, into the {H}.", "Gather the empties into the {H}: {A} and {B}.",
       "The {A} and the {B} go in the {H} for recycling."),
    [("B1K", "collecting_aluminum_cans"), ("RT2", "put_bottles_dustbin")])
add("clear_leftovers_shelf", "clear", {"P0": PL, "A": dict(T, cats=FOOD, on="on:P0")}, [("A", "V")],
    _t("Put the leftover {A} from the {P0} away in the {V}.", "Store the {A} on the shelf.",
       "Clear the {A} off the {P0} into the {V}.", "Take the {A} from the {P0} and put it in the {V}.",
       "The leftover {A} goes in the {V}."),
    [("B1K", "putting_leftovers_away"), ("RC", "storing_leftovers")], dst={"V": SH}, needs=(SHELF_NEED,), req=FRONT)
add("clear_zone_two", "clear", {"A": dict(T, on="node:zone|seat"), "B": T}, [("A", "P1"), ("B", "P2")],
    _t("Clear the {Asurf}: move the {A} aside, then the {B} next to it.", "Take the {A} off the {Asurf} and line the {B} up beside it.",
       "Move the {A} and the {B} to one side, in a row.", "Tidy the {A} off the {Asurf}, then the {B}, side by side.",
       "Put the {A} and the {B} next to each other out of the way."),
    [("B1K", "cleaning_table_after_clearing")],
    dst={"P1": {"type": "spot", "line": ("y", 0, 2)}, "P2": {"type": "spot", "line": ("y", 1, 2)}},
    needs=("node:zone|seat",))
add("down_two", "height", {"A": dict(T, on="higher"), "B": dict(T, on="higher")}, [("A", "V"), ("B", "V")],
    _t("Bring the {A} and the {B} down to the {V}.", "Move both the {A} and the {B} down onto the {V}.",
       "Take the {A}, then the {B}, down to the {V}.", "Put the {A} and the {B} on the lower {V}.",
       "Both the {A} and the {B} come down to the {V}."),
    [("RC", "PickPlaceCabinetToCounter"), ("B1K", "putting_away_Christmas_decorations")],
    dst={"V": {"type": "node", "kinds": ("top", "zone"), "lower_than_obj": "A", "shared": True}}, needs=("higher",))
add("up_onto_plate", "height", {"A": T, "H": dict(PL, on="higher")}, [("A", "H")],
    _t("Put the {A} on the {H} up on the {Hsurf}.", "Lift the {A} onto the {H} on the {Hsurf}.",
       "Place the {A} on the {H} that is up high.", "Move the {A} up onto the {H}.", "The {A} goes on the {H} up there."),
    [("LIB", "put_the_bowl_on_top_of_the_cabinet"), ("RC", "PickPlaceCounterToCabinet")], needs=("higher",))
add("down_onto_plate", "height", {"A": dict(T, on="higher"), "H": PL}, [("A", "H")],
    _t("Bring the {A} down from the {Asurf} onto the {H}.", "Take the {A} down and put it on the {H}.",
       "Move the {A} from the {Asurf} to the {H}.", "Put the {A} from up on the {Asurf} on the {H}.",
       "The {A} comes down onto the {H}."),
    [("RC", "PickPlaceCabinetToCounter"), ("LIB", "pick_up_the_black_bowl_on_the_wooden_cabinet_and_place_it_on_the_plate")],
    needs=("higher",))

# ordered 3-object episodes (owner 10-02: more post-grasp steps; LIBERO failures came after the grasp)
add("tidy_three_places", "tidy", {"A": T, "B": T, "C": T, "H": W_}, [("A", "H"), ("B", "V"), ("C", "P")],
    _t("Put everything where it belongs: {A} in the {H}, {B} on the {V}, {C} to the back right.",
       "First the {A} into the {H}, then the {B} onto the {V}, then the {C} to the back right.",
       "Tidy up three things: {A} into the {H}, {B} on the {V}, {C} at the back right.",
       "Return the {A} to the {H}, the {B} to the {V} and the {C} to the back right corner.",
       "One at a time: the {A} goes in the {H}, the {B} on the {V}, the {C} back right."),
    [("B1K", "collect_misplaced_items"), ("B1K", "cleaning_bedroom")],
    dst={"V": SV, "P": {"type": "spot", "corner": "back_right"}}, needs=("node:stand",))
add("tr_swap_containers", "transfer", {"H": W_, "A": dict(T, on="on:H"), "G": W_, "B": T}, [("A", "G"), ("B", "H")],
    _t("Move the {A} from the {H} to the {G}, then put the {B} in the {H}.",
       "Swap things around: {A} into the {G}, then {B} into the emptied {H}.",
       "First take the {A} out of the {H} into the {G}; then the {B} goes into the {H}.",
       "Put the {A} in the {G} and the {B} in the {H}, in that order.",
       "Empty the {H} into the {G}, then fill the {H} with the {B}."),
    [("B1K", "storing_food"), ("RC", "organizing_dishes_and_containers")])
add("set_two_plates_drink", "set", {"A": dict(T, cats=FOOD), "H": PL, "B": dict(T, cats=FOOD), "G": PL,
                                    "C": dict(T, cats=DRINK)}, [("A", "H"), ("B", "G"), ("C", "P")],
    _t("Serve two places: {A} on the {H}, {B} on the {G}, and the {C} right of the {H}.",
       "Put the {A} on the {H}, the {B} on the {G}, then set the {C} beside the {H} on the right.",
       "First the {A} onto the {H}, then the {B} onto the {G}, then the {C} to the right of the {H}.",
       "Lay out the meal: {A} on the {H}, {B} on the {G}, {C} next to the {H}.",
       "Plate the {A} and the {B}, then put the {C} on the right of the {H}."),
    [("B1K", "serving_a_meal"), ("RLB", "set_the_table")], dst={"P": {"type": "spot", "rel": "right", "ref": "H"}})
add("clear_three_mixed", "clear", {"A": T, "H": BIN, "B": dict(T, cats=FOOD), "G": BOWL, "C": T},
    [("A", "H"), ("B", "G"), ("C", "P")],
    _t("Clean up: {A} in the {H}, {B} in the {G}, {C} to the back left.",
       "Throw the {A} in the {H}, put the {B} in the {G}, and move the {C} to the back left.",
       "First the {A} into the {H}, then the {B} into the {G}, then the {C} out of the way at the back left.",
       "Clear three things: {A} into the {H}, {B} into the {G}, {C} back left.",
       "After the meal: trash {A} into the {H}, food {B} into the {G}, and {C} to the back left."),
    [("B1K", "cleaning_up_after_a_meal"), ("RC", "clearing_table")], dst={"P": {"type": "spot", "corner": "back_left"}})
add("rel_chain3", "relation", {"A": T, "B": T, "C": T, "R": T}, [("A", "P1"), ("B", "P2"), ("C", "P3")],
    _t("Around the {R}: the {A} on its left, the {B} on its right, the {C} behind it.",
       "Put the {A} left of the {R}, the {B} right of it, then the {C} behind it.",
       "First the {A} to the {R}'s left, then the {B} to its right, then the {C} behind it.",
       "Arrange the {A}, {B} and {C} around the {R}: left, right, behind.",
       "Surround the {R}: {A} left, {B} right, {C} behind."),
    [("VIMA", "rearrange"), ("LIB", "libero_spatial")],
    dst={"P1": {"type": "spot", "rel": "left", "ref": "R"}, "P2": {"type": "spot", "rel": "right", "ref": "R"},
         "P3": {"type": "spot", "rel": "behind", "ref": "R"}})
add("stack_then_two_in", "stack", {"A": T, "B": B_, "C": T, "D": T, "H": WB}, [("A", "B"), ("C", "H"), ("D", "H")],
    _t("Stack the {A} on the {B}, then put the {C} and the {D} in the {H}.",
       "First the {A} onto the {B}; then the {C} and the {D} into the {H}.",
       "Put the {A} on top of the {B}, and drop the {C} and then the {D} into the {H}.",
       "{A} on the {B}, then {C} and {D} into the {H}.",
       "Make a stack of the {A} on the {B}, then pack the {C} and the {D} in the {H}."),
    [("B1K", "boxing_books_up_for_storage"), ("CAL", "stack_block")])

# L8S kinds missing so far (owner 10-02 03h: the next training uses L9 v2 alone, so it must cover every L8S kind).
# 19. push: closed-finger push onto a place (L8S pu__<obj>: teach_l8d.xnew.plan_push = above_start / lower_behind /
# push / lift_away with the existing eef + gripper commands) — CALVIN push_*_block, LIBERO push_the_plate
PUSH = {0: {"mode": "push"}}
add("push_onto_mat", "push", {"A": T}, [("A", "V")],
    _t("Push the {A} onto the {V}.", "Slide the {A} over onto the {V} without lifting it.", "Nudge the {A} onto the {V}.",
       "Without picking it up, push the {A} onto the {V}.", "Shove the {A} until it sits on the {V}."),
    [("CAL", "push_red_block_right"), ("DROID", "push")], dst={"V": ZN}, needs=("node:zone|seat",), place=PUSH,
    req=("exec:push",))
add("push_left", "push", {"A": T}, [("A", "P")],
    _t("Push the {A} to the left.", "Slide the {A} a bit to the left without lifting it.", "Nudge the {A} leftwards.",
       "Without picking it up, move the {A} left by pushing it.", "Shove the {A} over to the left."),
    [("CAL", "push_blue_block_left"), ("BRIDGE", "push")], dst={"P": {"type": "spot", "rel": "left", "ref": "A",
                                                                       "gap": 0.03}}, place=PUSH, req=("exec:push",))
add("push_right", "push", {"A": T}, [("A", "P")],
    _t("Push the {A} to the right.", "Slide the {A} a bit to the right without lifting it.", "Nudge the {A} rightwards.",
       "Without picking it up, move the {A} right by pushing it.", "Shove the {A} over to the right."),
    [("CAL", "push_pink_block_right"), ("BRIDGE", "push")], dst={"P": {"type": "spot", "rel": "right", "ref": "A",
                                                                        "gap": 0.03}}, place=PUSH, req=("exec:push",))
add("push_to_front", "push", {"A": T}, [("A", "P")],
    _t("Push the {A} towards me, to the front edge.", "Slide the {A} to the front of the {Msurf}.",
       "Without lifting it, bring the {A} to the near edge.", "Push the {A} along until it reaches the front edge.",
       "Nudge the {A} to the front."),
    [("LIB", "push_the_plate_to_the_front_of_the_stove"), ("DROID", "push")],
    dst={"P": {"type": "spot", "corner": "front_edge"}}, place=PUSH, req=("exec:push",))
add("push_next_to", "push", {"A": T, "R": T}, [("A", "P")],
    _t("Push the {A} next to the {R}.", "Slide the {A} over until it is beside the {R}.",
       "Without lifting it, push the {A} up to the {R}'s right side.", "Nudge the {A} to the right of the {R}.",
       "Shove the {A} over next to the {R}, on its right."),
    [("CAL", "push_red_block_left"), ("VIMA", "sweep_without_exceeding")],
    dst={"P": {"type": "spot", "rel": "right", "ref": "R", "gap": 0.02}}, place=PUSH, req=("exec:push",))
add("push_to_back", "push", {"A": T}, [("A", "P")],
    _t("Push the {A} away from me, to the back of the {Msurf}.", "Slide the {A} to the back without lifting it.",
       "Nudge the {A} towards the back edge.", "Without picking it up, push the {A} to the far side.",
       "Shove the {A} back, out of the way."),
    [("CAL", "push_into_drawer (push part)"), ("BRIDGE", "push")], dst={"P": {"type": "spot", "corner": "deep_back"}},
    place=PUSH, req=("exec:push",))
# L8S stand_mug_tray (start on the white stand -> tray), ring on a peg (xring), open drawer / open-flap box (xart)
add("tr_stand_to_plate", "transfer", {"A": dict(T, on="node:stand"), "H": PL}, [("A", "H")],
    _t("Take the {A} off the block and put it on the {H}.", "Move the {A} from the block onto the {H}.",
       "Put the {A} that stands on the block on the {H}.", "Lift the {A} off the block; it goes on the {H}.",
       "The {A} on the block goes onto the {H}."),
    [("RT2", "place_object_stand (reverse)"), ("CAL", "unstack_block")], needs=("node:stand",))
add("ins_ring_peg", "insert", {"A": dict(T, cats=("ring",))}, [("A", "V")],
    _t("Put the {A} on the {V}.", "Drop the {A} over the {V}.", "Thread the {A} onto the {V}.",
       "Place the {A} around the {V}.", "The {A} goes onto the {V}."),
    [("RLB", "put_rubbish_in_bin -> ring variant: place_shape_in_shape_sorter"), ("RT2", "place_object_stand")],
    dst={"V": {"type": "node", "kinds": ("peg",)}}, needs=("node:peg",), req=("asset:ring_peg",))
add("in_open_drawer", "put_in", {"A": T}, [("A", "V")],
    _t("Put the {A} into the open drawer.", "Place the {A} inside the {V}.", "Drop the {A} in the open drawer.",
       "Store the {A} in the {V}.", "The {A} goes into the open drawer."),
    [("RC", "PickPlaceCounterToDrawer (drawer already open)"), ("LIB", "open_the_top_drawer_and_put_the_bowl_inside "
                                                                      "(put part only)")],
    dst={"V": {"type": "node", "kinds": ("drawer_open",)}}, needs=("node:drawer_open",), req=("node:drawer_open",))

for _k, _d in T9.DEFS.items():
    SOURCES[_k] = (("v1", "task9 " + _k),) + V1_SOURCES[_d.family]
DEFS_V2 = {**T9.DEFS, **NEW}
NEW_FAMILIES = ("shelf", "select", "tall", "hollow", "pose", "kitchen", "tidy", "transfer", "recovery", "push")

# L8S task kind (harvest/sim/tasks.py TASKS / X_TASKS / OBJV_TASK_KINDS / X_STEPS, teach_l8d xnew / xring / xart) ->
# L9 v2 definitions covering it (owner 10-02 03h)
L8S_COVERAGE = {
    "tray": ("in_onto_tray", "set_food_on_plate", "sel_colour_plate", "sel_food_plate", "tall_on_tray", "tr_plate_to_plate"),
    "bin": ("in_wide", "clear_one", "clear_toy_bin", "tall_into_bin", "sel_can_bin", "in_kind_toy"),
    "basket": ("in_cubby", "clear_to_cubby", "kit_to_sink", "sel_bottle_basket", "tidy_gift_basket"),
    "left": ("rel_left", "rel_left_of_container", "sel_colour_left_of", "tall_left_of", "spread_out"),
    "right": ("rel_right", "rel_right_of_container", "line_next_to", "spread_right", "set_drink_right"),
    "front": ("rel_front", "rel_front_of_container", "set_drink_front", "rel_front_left", "rel_front_right"),
    "behind": ("rel_behind", "rel_behind_container", "set_behind_plate", "rel_behind_left", "rel_behind_right"),
    "between": ("rel_between", "rel_between_containers", "tall_between", "arr_gap_narrow"),
    "upper": ("up_to_higher", "up_into_container", "up_two", "tall_up_higher", "up_onto_plate"),
    "marker": ("set_on_mat", "sort_kind_mat", "set_coaster", "kit_to_board", "tidy_two_mats", "to_front_left",
               "set_centre"),
    "stand": ("block_stack", "block_two", "block_by_side", "block_named", "sel_book_stand", "st_tower_stand"),
    "stand_then_place": ("block_unstack", "tr_stand_to_bowl", "tr_stand_to_plate", "ins_from_block", "block_restack"),
    "confuser_attribute": ("in_by_colour", "stack_by_colour", "ins_among", "sel_colour_in", "sel_smaller_in",
                           "clear_colour", "stack_named"),
    "multi_step": ("clear_two", "set_pair", "in_two_same", "tidy_pack_lunch", "set_place_three", "clear_three_mixed",
                   "rel_chain3", "line3_y"),
    "open_container": ("in_cubby", "kit_to_sink", "clear_to_cubby", "tr_out_of_cubby"),
    "stack": ("stack2", "stack_on_bigger", "stack_named", "st_on_book", "st_colour_pair", "stack_then_in"),
    "push": ("push_onto_mat", "push_left", "push_right", "push_to_front", "push_next_to"),
    "ring_peg": ("ins_ring_peg", "ins_one", "ins_slot"),
    "open_drawer_box": ("in_open_drawer", "in_cubby", "shelf_low_put"),
}
FAMILIES_V2 = T9.FAMILIES + NEW_FAMILIES


def runnable(d: TaskDef, caps=()) -> bool:
    return set(d.extra.get("requires", ())) <= set(caps)


def defs_for(caps=()) -> dict:
    return {k: d for k, d in DEFS_V2.items() if runnable(d, caps)}


# ------------------------------------------------------------------------------------------------ object rules
def _fr(r):
    return float(r["footprint_r"])


def is_tall(r: dict) -> bool:
    h = float(r["height"])
    return h >= TALL_H or h / max(2 * _fr(r), 1e-6) >= TALL_ASPECT


def can_lie(r: dict) -> bool:
    """[가설] stable lying: cylinders (bottle / can) or boxes / books / blocks whose upright height exceeds 1.2 x
    their width (lying then lowers the centre of mass)."""
    return r.get("l9cat") in ("bottle", "can", "box", "book", "block") and \
        float(r["height"]) / max(2 * _fr(r), 1e-6) >= 1.2


def can_lean(r: dict) -> bool:
    """[가설] leaning: thin books / boxes (smallest half extent <= 0.45 x the largest), >= 6 cm tall."""
    he = sorted(float(x) for x in (r.get("half_extents") or (0, 0, 0)))
    return r.get("l9cat") in ("book", "box") and he[2] > 0 and he[0] <= 0.45 * he[2] and float(r["height"]) >= 0.06


def is_orientable(r: dict) -> bool:
    """[가설] a visible long axis: one half extent >= 1.3 x the next one."""
    he = sorted(float(x) for x in (r.get("half_extents") or (0, 0, 0)))
    return he[0] > 0 and (he[2] >= 1.3 * he[1] or he[1] >= 1.3 * he[0])


def hollow_ok(r: dict, spec: dict) -> bool:
    if r.get("role9") != "container" or r.get("l9cat") not in spec.get("cats", HOLLOW):
        return False
    if T9.kind_of(r) == "flat" or _fr(r) > T9.MAX_CONTAINER_R or float(r["height"]) > T9.CLUTTER_H_MAX:
        return False
    return not spec.get("handle") or float(r.get("handle_ratio") or 0) >= HANDLE_RATIO


def spec_ok(r: dict, spec: dict, oname: str, defn: TaskDef, grip_max=None) -> bool:
    """v2 object filters (task9 pick): robot gripper width for movers, tall / lie / lean / orientable classes."""
    movers = {a for a, _ in defn.steps}
    if grip_max is not None and oname in movers and not spec.get("hollow"):
        if float(r.get("grasp_width") or 2 * _fr(r)) > float(grip_max) - T9.GRIP_MARGIN:
            return False
    if spec.get("tall") and not is_tall(r):
        return False
    if spec.get("lie_ok") and not can_lie(r):
        return False
    if spec.get("lean_ok") and not can_lean(r):
        return False
    if spec.get("orientable") and not is_orientable(r):
        return False
    return True


def category_word(r: dict) -> str:
    """The catalog category (l9cat); the object name only for l9cat 'other'. grasp9.natural_order matches substrings,
    so names alone mislead ('potato' -> pot / rim, 'pancake' -> pan, 'solid' -> lid)."""
    c = r.get("l9cat") or ""
    return c if c and c != "other" else str(r.get("name") or "")


def natural_class(r: dict) -> tuple:
    """The object's first natural (approach family, part) under grasp9.natural_order (natural_v1, owner 10-02)."""
    from . import grasp9 as G9
    return tuple(G9.natural_order(category_word(r), float(r.get("height") or 0.0))[0])


def balanced_pick(cand: list, pool: dict, rng) -> str:
    """v2 mover / object draw: a natural approach family uniformly, then a (family, part) class, then an object of that
    class, all uniform (easy classes do not dominate, top stays <= 1/2 when two or more families are present; spec
    §12.11 principle 2, natural_v1 gate top <= 50 %)."""
    by = {}
    for k in cand:
        c = natural_class(pool[k])
        by.setdefault(c[0], {}).setdefault(c, []).append(k)
    fams = sorted(by)
    cls = by[fams[int(rng.integers(len(fams)))]]
    keys = sorted(cls)
    ks = cls[keys[int(rng.integers(len(keys)))]]
    return ks[int(rng.integers(len(ks)))]


def _spec_rows(spec: dict, cat: dict) -> list:
    """Catalog rows a definition object spec may draw (scene-free approximation for planning reports)."""
    out = []
    for r in cat.values():
        if spec.get("hollow"):
            if not hollow_ok(r, spec):
                continue
        elif r.get("role9") != "target":
            continue
        if spec.get("cats") and r.get("l9cat") not in spec["cats"]:
            continue
        if spec.get("slender") and not T9.is_slender(r):
            continue
        if spec.get("role") == "base" and not T9.flat_top(r):
            continue
        if (spec.get("tall") and not is_tall(r)) or (spec.get("lie_ok") and not can_lie(r)) or \
                (spec.get("lean_ok") and not can_lean(r)) or (spec.get("orientable") and not is_orientable(r)):
            continue
        out.append(r)
    return out


def natural_expected(alloc: dict) -> dict:
    """Expected natural grasp family / part shares per definition (movers drawn class-balanced) and overall
    (episode- and step-weighted): {per_def: {id: {family: share}}, overall: {family: share}, parts: {part: share}}."""
    from collections import Counter

    from . import assets9 as A9
    cat = A9.catalog()
    per, tot, parts = {}, Counter(), Counter()
    for k, v in alloc.items():
        d = DEFS_V2[k]
        n = sum(v.values())
        fam = Counter()
        for a, _ in d.steps:
            classes = sorted({natural_class(r) for r in _spec_rows(d.objs[a], cat)})
            fams = sorted({c[0] for c in classes})
            for c in classes:  # family uniform, class uniform within its family (= balanced_pick)
                w = 1.0 / len(fams) / sum(1 for x in classes if x[0] == c[0])
                fam[c[0]] += w / len(d.steps)
                parts[c[1]] += n * w / len(d.steps)
        per[k] = {f: round(s, 4) for f, s in fam.items()}
        for f, s in fam.items():
            tot[f] += s * n
    z = sum(tot.values()) or 1.0
    zp = sum(parts.values()) or 1.0
    return {"per_def": per, "overall": {f: s / z for f, s in tot.items()},
            "parts": {p: round(s / zp, 4) for p, s in parts.items()}}


def blocked_above(node: dict | None) -> bool:
    if not node:
        return False
    if node.get("kind") in SHELF_KINDS or node.get("blocked_above"):
        return True
    ca = node.get("clear_above")
    return ca is not None and float(ca) < CLEAR_ABOVE_MIN


def constraints_of(r: dict, node: dict | None, grip_max=None) -> list:
    """Scene constraint kinds for the grasp label rule (§12.8 step 1), in priority order."""
    g = T9.FINGER_OPEN if grip_max is None else float(grip_max)
    gw = float(r.get("grasp_width") or 2 * _fr(r))
    out = []
    if blocked_above(node):
        out.append("blocked_above")
    if r.get("l9cat") in HOLLOW_ANY and r.get("role9") == "container" and gw > g - 0.02:
        out.append("wide_hollow")
    if is_tall(r):
        out.append("tall")
    if r.get("l9cat") in ("mug", "cup") and float(r.get("handle_ratio") or 0) >= HANDLE_RATIO:
        out.append("handle")
    if float(r["height"]) <= FLAT_H:
        out.append("flat")
    return out


def height_band(z: float) -> str:
    for lim, name in BAND_Z:
        if float(z) < lim:
            return name
    return "above_eye"


# ------------------------------------------------------------------------------------------------ instructions
def instructed_approach(seed: int, def_id: str, constraint) -> str | None:
    """Deterministic per seed: ~20 % of instances name an approach the scene constraint allows (the owner's executor
    decides whether it is reachable; an unreachable one falls back per §12.8)."""
    if _u("l9v2-instr", seed, def_id) >= INSTRUCTED_SHARE:
        return None
    opts = ALLOWED_APPROACH.get(constraint, APPROACHES)
    return opts[int(_u("l9v2-instr-a", seed, def_id) * len(opts))]


def wrap_instruction(seed: int, s: str) -> tuple:
    """(text, wrapper index) — deterministic phrasing variants around a template sentence (index 0 = unchanged)."""
    if _u("l9v2-wrap", seed) < UNWRAPPED_SHARE or not s:
        return s, 0
    first = s.split()[0].lower().strip(",:;")
    imper = first in IMPERATIVE and s.endswith(".") and "?" not in s
    opts = list(GENERAL_WRAP[1:]) + (list(IMPER_WRAP) if imper else [])
    i = int(_u("l9v2-wrap-i", seed) * len(opts))
    w = opts[i]
    lo = s[0].lower() + s[1:]
    out = w.format(s=s, l=lo, l0=lo.rstrip(".!"))
    return out[0].upper() + out[1:], 1 + (list(GENERAL_WRAP[1:]) + list(IMPER_WRAP)).index(w)


N_WRAPPERS = 1 + len(GENERAL_WRAP) - 1 + len(IMPER_WRAP)


def approach_text(seed: int, def_id: str, approach: str, name: str) -> tuple:
    """(sentence, position before|after): one of APPROACH_TEXT[approach] naming the grasped object, hashed per seed."""
    tpl = APPROACH_TEXT[approach]
    t = tpl[int(_u("l9v2-instr-t", seed, def_id) * len(tpl))].format(X=name)
    return t, ("before" if _u("l9v2-instr-o", seed, def_id) < 0.5 else "after")


def apply_approach(ep: dict, approach: str | None, step: int = 0) -> str:
    """Put an instructed approach into the episode instruction (called by the grasp selector once it knows the
    approach is executable; finish() only proposes instr_meta.approach_candidate). None = leave the text as it is."""
    m = ep["instr_meta"]
    if approach is None:
        return ep["instruction"]
    name = ep["names"][ep["steps"][step][0]]
    t, pos = approach_text(m["seed"], m["def"], approach, name)
    ep["instruction"] = f"{t} {m['wrapped']}" if pos == "before" else f"{m['wrapped']} {t}"
    m.update(approach=approach, approach_step=step, approach_text=t, approach_reason="instructed")
    return ep["instruction"]


def recovery_candidate(seed: int, def_id: str, n_steps: int) -> dict | None:
    """Every definition's recovery variant (owner 10-02): ~RECOVERY_SHARE of instances propose a perturbed release on
    one step (off target 5-9 cm or tilted 30-60 deg, hashed); the executor applies it when it can (exec:recovery) and
    the next call re-grasps. The labels never teach the perturbation."""
    if _u("l9v2-rcv-c", seed, def_id) >= RECOVERY_SHARE:
        return None
    step = int(_u("l9v2-rcv-s", seed, def_id) * n_steps)
    kind = "off_target" if _u("l9v2-rcv-k", seed, def_id) < 0.6 else "tilted"
    ang = 2 * math.pi * _u("l9v2-rcv-a", seed, def_id)
    mag = 0.05 + 0.04 * _u("l9v2-rcv-m", seed, def_id)
    return {"step": step, "kind": kind, "teach": False,
            "offset_m": [round(mag * math.cos(ang), 4), round(mag * math.sin(ang), 4)] if kind == "off_target" else None,
            "tilt_deg": round(30 + 30 * _u("l9v2-rcv-t", seed, def_id), 1) if kind == "tilted" else None,
            "fix": "the executor perturbs this release; the next call re-grasps the object and places it again "
                   "(labels keep the correct target)"}


def avoid_bench(defn: TaskDef, ep: dict, fmt: dict) -> tuple:
    """(instruction, clashed): a benchmark instruction verbatim moves to the next template that is not one (owner
    principle 1); sets ep["template"] to the template used."""
    base = ep["instruction"]
    if not bench_clash(base):
        return base, False
    n = len(defn.templates)
    for j in range(1, n):
        ti = (int(ep.get("template") or 0) + j) % n
        t = defn.templates[ti].format(**fmt)
        t = t[0].upper() + t[1:]
        if not bench_clash(t):
            ep["template"] = ti
            return t, True
    return base, True


# ------------------------------------------------------------------------------------------------ finish (step info)
def _done(kind: str, place: str, rec: dict, pose: dict, judge: dict, name: str, where: str) -> dict:
    d = {"pred": kind, "place": place}
    if kind == "on_spot":
        d.update(r_m=T9.SPOT_R, text=f"the {name} stands on the {where} with its centre within "
                                     f"{T9.SPOT_R * 100:.0f} cm of the spot")
    elif kind == "on_surface":
        d.update(half_m=rec.get("half"), text=f"the {name} stands on the {where} (centre within "
                                              f"{(rec.get('half') or 0) * 100:.0f} cm of the drop point)")
    elif kind == "in_container":
        d.update(text=f"the {name} is inside the {where}")
    elif kind == "on_container":
        d.update(text=f"the {name} rests on the {where}")
    else:
        d.update(text=f"the {name} rests on top of the {where}")
    pk = pose["kind"]
    if pk == "lying":
        d["pose"] = {"tilt_min_deg": 70.0}
        d["text"] += ", lying on its side (tilt >= 70 deg)"
    elif pk == "leaning":
        d["pose"] = {"tilt_deg": [10.0, 40.0], "touch": pose.get("against")}
        d["text"] += ", leaning 10-40 deg against the wall"
    elif pk == "oriented":
        d["pose"] = {"yaw_tol_deg": 20.0, "yaw": pose.get("yaw"), "delta_yaw": pose.get("delta_yaw")}
        d["text"] += ", turned as asked (yaw within 20 deg)"
    elif judge.get("upright_max_deg") is not None:
        d["pose"] = {"tilt_max_deg": judge["upright_max_deg"]}
        d["text"] += f", upright (tilt <= {judge['upright_max_deg']:.0f} deg)"
    d["text"] += ", and the gripper has let go"
    return d


def finish(defn: TaskDef, ep: dict, ctx: dict) -> None:
    """Add step_info / done / instr_meta / movable_containers / start_poses to an instantiated episode (no draws
    from the instantiate rng: everything here is hashed from the seed)."""
    chosen, pool, nodes, main = ctx["chosen"], ctx["pool"], ctx["nodes"], ctx["main"]
    spots, surfs, seed, fmt = ctx["spots"], ctx["surfs"], ctx["seed"], ctx["fmt"]
    gm = ctx["grip_max"]
    mz = float(main["top_z"])
    place_x = defn.extra.get("place", {})
    rcv = defn.extra.get("recovery")
    infos, done = [], []
    for i, (a, d) in enumerate(defn.steps):
        k = chosen[a]
        r = pool[k]
        o = ep["objects"][k]
        start_node = nodes[o["node"]][0] if o.get("support") is None else None
        cons = constraints_of(r, start_node, gm)
        px = dict(place_x.get(i, {}))
        if d in spots:
            pk, place_id, z, pnode = "on_spot", ctx["sid"][d], mz, main
            rec, where = spots[d], fmt.get("Msurf", "surface")
        elif d in surfs:
            pk, place_id, z, pnode = "on_surface", ctx["vid"][d], float(surfs[d]["top"]), nodes[surfs[d]["node"]][0]
            rec, where = surfs[d], fmt.get(d, surfs[d]["name"])
        else:
            dr = pool[chosen[d]]
            role = defn.objs[d]["role"]
            if role == "container":
                pk = "on_container" if T9.kind_of(dr) == "flat" else "in_container"
            else:
                pk = "stacked_on"
            place_id, rec, where = chosen[d], {}, fmt.get(d, "object")
            host = ep["objects"][chosen[d]]
            pnode = nodes[host["node"]][0]
            z = float(pnode["top_z"]) + float(dr["height"])
        blocked = blocked_above(pnode) if pk in ("on_surface",) else False
        approach = "front" if blocked else px.get("approach", "top")
        pose = {"kind": px.get("pose", "upright"), "support": place_id}
        if pose["kind"] == "lying":
            pose["yaw"] = round((math.pi / 2) * int(_u("l9v2-lie", seed, defn.id, i) * 2), 4)  # long axis x or y
            pose["axis"] = "horizontal"
        elif pose["kind"] == "leaning":
            pose["against"] = "back_wall"
            pose["tilt_deg"] = round(15.0 + 15.0 * _u("l9v2-lean", seed, defn.id, i), 1)
        elif pose["kind"] == "oriented":
            ori = px.get("orient")
            pose["orient"] = ori
            if ori == "rot90":
                pose["delta_yaw"] = round(math.pi / 2, 4)
            elif ori == "long_lr":
                pose["yaw"] = round(math.pi / 2, 4)  # long axis along the robot's y (left-right)
            elif ori == "handle_right":
                pose["yaw"] = round(-math.pi / 2, 4)  # handle direction = robot's right (-y)
        if pose["kind"] == "leaning":
            ppoint = "inner_wall"
        elif blocked:
            ppoint = "front_edge"
        else:
            ppoint = {"on_spot": "surface_point", "on_surface": "surface_point", "in_container": "container_opening",
                      "on_container": "container_top", "stacked_on": "object_top"}[pk]
        band = height_band(z)
        hint = {"name": "place", "ref": "support_top", "release_above_m": [0.004, 0.02]}
        if band in ("high", "above_eye") or blocked:
            hint.update(point="front_edge", note="the support top may be hidden: the point marks the visible front "
                                                  "edge, the release height comes from the support top (node top_z)")
        info = {"step": i, "target": k, "place": place_id, "place_kind": pk,
                "pick_node_kind": start_node["kind"] if start_node else ("stacked" if o.get("support") else None),
                "constraint": cons[0] if cons else None, "constraints": cons, "place_pose": pose,
                "place_approach": approach, "place_point": ppoint, "place_node_kind": pnode.get("kind"),
                "place_height": {"z": round(z, 4), "band": band, "rel_main": round(z - mz, 4)},
                "height_intent": hint, "recovery": None, "mode": px.get("mode", "pick_place")}
        if rcv and rcv.get("step") == i:
            ang = 2 * math.pi * _u("l9v2-rcv-a", seed, defn.id)
            mag = 0.05 + 0.04 * _u("l9v2-rcv-m", seed, defn.id)
            info["recovery"] = {"kind": rcv["kind"], "teach": False,
                                "offset_m": [round(mag * math.cos(ang), 4), round(mag * math.sin(ang), 4)]
                                if rcv["kind"] == "off_target" else None,
                                "tilt_deg": round(30 + 30 * _u("l9v2-rcv-t", seed, defn.id), 1)
                                if rcv["kind"] == "tilted" else None,
                                "fix": "the executor perturbs this release; the next call re-grasps the object and "
                                       "places it again (labels keep the correct target)"}
        info["done"] = _done(pk, place_id, rec, pose, defn.judge, ep["names"][k], where)
        infos.append(info)
        done.append(info["done"])
    base, clash = avoid_bench(defn, ep, fmt)
    c0 = infos[0]["constraint"] if infos else None
    appr = instructed_approach(seed, defn.id, c0)
    text, widx = wrap_instruction(seed, base)
    ep["instruction"] = text
    ep["instr_meta"] = {"base": base, "template": ep.get("template"), "wrapper": widx, "wrapped": text,
                        "bench_clash_avoided": clash, "seed": int(seed), "def": defn.id,
                        "approach_candidate": appr, "approach": None, "approach_step": None, "approach_text": None,
                        "approach_reason": None}
    ep["step_info"] = infos
    ep["done"] = {"all_of": done, "final": "every step predicate holds at the same time after the last release",
                  "text": "; ".join(x["text"] for x in done) + ". Stop only when all of this holds.",
                  "stop_label": "done: " + "; ".join(x["text"] for x in done)}
    ep["movable_containers"] = sorted(chosen[n] for n, sp in defn.objs.items() if sp.get("hollow"))
    ep["start_poses"] = {chosen[n]: p for n, p in defn.extra.get("start", {}).items()}
    ep["recovery_candidate"] = None if rcv else recovery_candidate(seed, defn.id, len(defn.steps))
    ep["requires"] = list(defn.extra.get("requires", ()))
    ep["task_v2"] = True


# ------------------------------------------------------------------------------------------------ static profile
def def_profile(d: TaskDef) -> dict:
    """Planned (pre-instantiation) features of a definition: steps, post-grasp calls, place poses / approaches,
    expected constraints and height class (for tools/l9/task_diversity.py)."""
    px = d.extra.get("place", {})
    poses, appr, heights, cons = [], [], [], set()
    for i, (a, dst) in enumerate(d.steps):
        poses.append(px.get(i, {}).get("pose", "upright"))
        spec = d.dst.get(dst, {})
        kinds = set(spec.get("kinds", ()))
        shelf = bool(kinds & set(SHELF_KINDS))
        appr.append("push" if px.get(i, {}).get("mode") == "push" else
                    "front" if shelf else px.get(i, {}).get("approach", "top"))
        if kinds & {"shelf_high", "wall_shelf", "cupboard"} or spec.get("higher") or \
                d.objs.get(dst, {}).get("on") == "higher":
            heights.append("high")
        elif kinds & {"shelf_low"} or spec.get("lower") or spec.get("lower_than_obj"):
            heights.append("low")
        elif kinds & {"container", "cubby", "slot"} or d.objs.get(dst, {}).get("role") == "container":
            heights.append("in_container")
        elif kinds & {"stand"} or d.objs.get(dst, {}).get("role") in ("base",) or dst in d.objs:
            heights.append("on_object")
        else:
            heights.append("main")
        o = d.objs[a]
        if o.get("hollow"):
            cons.add("wide_hollow_or_handle")
        if o.get("tall"):
            cons.add("tall")
        if any(k in str(o.get("on", "")) for k in SHELF_KINDS):
            cons.add("blocked_above")
    rec = 1 if d.extra.get("recovery") else 0
    n = len(d.steps)
    return {"family": d.family, "n_steps": n, "post_grasp_calls": 2 * n - 1 + 2 * rec, "place_poses": poses,
            "place_approach": appr, "place_height": heights, "constraints": sorted(cons), "recovery": bool(rec),
            "requires": list(d.extra.get("requires", ())), "n_templates": len(d.templates)}
