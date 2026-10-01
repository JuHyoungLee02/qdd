"""L9 task layer (spec §3): primitives -> task definitions (9 families, >= 75) -> one episode's objects, layout,
destinations, steps and instruction. Pure (numpy).

Every definition compiles to ordered L8-X steps (target, place[, xy offset]) whose place is one of the existing
predicate kinds (plan decision 3):
  container object  (kinematic, place_kind into / onto: holders, bowls, bins, baskets, plates, trays)
  stack base        (another rigid object with a flat top; "on" by rest contact)
  spot  s9_k        (invisible marker on the main surface; centre within 4 cm, standing on that surface)
  surface v9_k      (a furniture node as a virtual surface: another height, a cubby / slot / basin floor, a zone)
Objects standing on a node other than the main one get a layout support b9_k whose SUPPORT_TOP lifts them to it.

Definitions are declarative: `objs` (role + constraints + where it starts), `dst` (spots / nodes), `steps` and
`templates` (>= 5 English templates; {A} = the name of object A ...)."""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

import numpy as np

from . import reach9 as R9
from . import scene9 as S9

SPOT_R = 0.04  # = tasks.MARKER_ON_R
NARROW = ("mug", "cup", "jar", "vase", "pen_holder")
WIDE = ("bowl", "bin", "basket", "box", "tray", "jar")
FLAT = ("plate", "tray")
STACK_BASE = ("block", "box", "book", "can")
FOOD = ("fruit", "vegetable", "bread")
TOYISH = ("toy", "block", "shoe")
DRINK = ("can", "bottle", "cup", "mug")
MAX_SPOTS, MAX_SURF, MAX_SUPP = 6, 3, 4
CLUTTER_H_MAX = 0.13  # L8S clutter_x.MAX_H 0.14: the carried object passes ~14 cm above the surface (pilot 1:
# 25 cm clutter was hit while carrying -> collision, joint jumps up to 1.2 rad)
MAX_CONTAINER_R = 0.12  # container footprint radius (the work band is ~0.32 x 0.34 m)


@dataclass(frozen=True)
class TaskDef:
    id: str
    family: str
    objs: dict  # name -> {role: target|container|base, cats, ..., on: main|second|stacked:<name>|node:<kind>}
    dst: dict = field(default_factory=dict)  # name -> {type: spot|node, ...}
    steps: tuple = ()  # (object name, destination name)
    templates: tuple = ()
    judge: dict = field(default_factory=dict)  # extra L9 success rules (insert_upright tilt)
    needs: tuple = ()  # scene needs: "second" (another height), "higher" / "lower", "node:<kind>"


def _t(*xs):
    return tuple(xs)


# ------------------------------------------------------------------------------------------ definitions
def _defs():
    D = []

    def add(i, fam, objs, steps, templates, dst=None, judge=None, needs=()):
        D.append(TaskDef(i, fam, objs, dst or {}, tuple(steps), tuple(templates), judge or {}, tuple(needs)))

    T = {"role": "target"}
    SL = {"role": "target", "slender": True}
    up = {"upright_max_deg": 15.0}
    # 1. insert: upright into a holder (a furniture slot node: pen / utensil / cup holder, rack slot, stand)
    HV = {"type": "node", "kinds": ("slot",)}
    ins_t = _t("Put the {A} into the {V}.", "Stand the {A} up in the {V}.", "Insert the {A} into the {V}.",
               "Place the {A} upright inside the {V}.", "Could you put the {A} in the {V}?", "The {A} goes into the {V}.")
    add("ins_one", "insert", {"A": SL}, [("A", "V")], ins_t, dst={"V": HV}, judge=up, needs=("node:slot",))
    add("ins_two_holders", "insert", {"A": SL, "B": SL}, [("A", "V1"), ("B", "V2")],
        _t("Put the {A} into one holder and the {B} into the other.", "Insert the {A} and the {B} into the two holders.",
           "Stand the {A} in the {V1} and the {B} in the {V2}.",
           "First the {A} into a holder, then the {B} into the other one.",
           "Place the {A} and the {B} upright, one in each holder."),
        dst={"V1": HV, "V2": HV}, judge=up, needs=("node2:slot",))
    add("ins_by_side", "insert", {"A": SL}, [("A", "V")],
        _t("Put the {A} into the holder on the {Vside}.", "Insert the {A} in the {Vside} holder.",
           "Stand the {A} in the holder that is on the {Vside}.", "Use the {Vside} holder for the {A}.",
           "Place the {A} upright in the {Vside} holder."), dst={"V": dict(HV, side_of_two=True)}, judge=up,
        needs=("node2:slot",))
    add("ins_from_second", "insert", {"A": dict(SL, on="second")}, [("A", "V")],
        _t("Take the {A} from the {Asurf} and put it into the {V}.", "Move the {A} off the {Asurf} into the {V}.",
           "Put the {A} from the {Asurf} in the {V}.", "Stand the {A} from the {Asurf} in the {V}.",
           "Get the {A} and insert it into the {V}."), dst={"V": HV}, judge=up, needs=("second", "node:slot"))
    add("ins_among", "insert", {"A": dict(SL, colour_named=True), "X": dict(SL, decoy_of="A")}, [("A", "V")],
        _t("Put only the {A} into the {V}.", "Insert the {A}, not the other one, into the {V}.",
           "Stand the {A} in the {V}.", "Pick the {A} and put it in the {V}.", "The {A} goes into the {V}."),
        dst={"V": HV}, judge=up, needs=("node:slot",))
    add("ins_then_in", "insert", {"A": SL, "B": T, "H": {"role": "container", "kind": "wide"}},
        [("A", "V"), ("B", "H")],
        _t("Put the {A} into the {V}, then the {B} into the {H}.", "Insert the {A} in the {V} and drop the {B} in the {H}.",
           "First the {A} into the {V}; then the {B} into the {H}.",
           "Stand the {A} in the {V}, then put the {B} in the {H}.", "{A} into the {V}, {B} into the {H}."),
        dst={"V": HV}, judge=up, needs=("node:slot",))
    add("ins_from_plate", "insert", {"P0": {"role": "container", "kind": "flat"}, "A": dict(SL, on="on:P0")},
        [("A", "V")], _t("Take the {A} off the {P0} and stand it in the {V}.",
                         "Move the {A} from the {P0} into the {V}.", "Put the {A} that is on the {P0} into the {V}.",
                         "Get the {A} from the {P0}; insert it into the {V}.", "The {A} on the {P0} goes into the {V}."),
        dst={"V": HV}, judge=up, needs=("node:slot",))
    add("ins_jar", "insert", {"A": SL, "H": {"role": "container", "kind": "wide", "cats": ("jar", "vase", "mug", "cup")}},
        [("A", "H")], _t("Put the {A} into the {H}.", "Stand the {A} up in the {H}.", "Insert the {A} into the {H}.",
                         "Place the {A} upright inside the {H}.", "The {A} goes into the {H}."),
        judge={"upright_max_deg": 30.0})
    add("ins_slot", "insert", {"A": SL}, [("A", "V")],
        _t("Put the {A} into the {V}.", "Stand the {A} in the {V}.", "Insert the {A} into the {V}.",
           "Place the {A} upright in the {V}.", "Drop the {A} into the {V}."),
        dst={"V": {"type": "node", "kinds": ("slot", "cubby")}}, needs=("node:slot|cubby",))

    # 2. arrange / line up (정리·줄 세우기)
    ln_t2 = _t("Line up the {A} and the {B} side by side, {A} on the left.", "Put the {A} and the {B} in a row, left to right.",
               "Arrange the {A} then the {B} in a line from left to right.", "Place the {A} left and the {B} right, next to each other.",
               "Make a row: {A}, then {B}.")
    add("line2_y", "arrange", {"A": T, "B": T}, [("A", "P1"), ("B", "P2")], ln_t2,
        dst={"P1": {"type": "spot", "line": ("y", 0, 2)}, "P2": {"type": "spot", "line": ("y", 1, 2)}})
    add("line3_y", "arrange", {"A": T, "B": T, "C": T}, [("A", "P1"), ("B", "P2"), ("C", "P3")],
        _t("Line up the {A}, the {B} and the {C} from left to right.", "Put the {A}, {B} and {C} in one row, left to right.",
           "Arrange them in a row: {A}, {B}, {C}.", "Make a line of the {A}, the {B} and the {C}, left to right.",
           "Set the {A}, then the {B}, then the {C} side by side."),
        dst={"P1": {"type": "spot", "line": ("y", 0, 3)}, "P2": {"type": "spot", "line": ("y", 1, 3)},
             "P3": {"type": "spot", "line": ("y", 2, 3)}})
    add("line2_x", "arrange", {"A": T, "B": T}, [("A", "P1"), ("B", "P2")],
        _t("Put the {A} in front and the {B} behind it.", "Line up the {A} and the {B} front to back, {A} nearest to me.",
           "Place the {B} directly behind the {A} after moving both.", "Make a front-to-back row: {A}, then {B}.",
           "Arrange the {A} and the {B} one behind the other, {A} in front."),
        dst={"P1": {"type": "spot", "line": ("x", 0, 2)}, "P2": {"type": "spot", "line": ("x", 1, 2)}})
    add("line_next_to", "arrange", {"A": T, "R": T}, [("A", "P")],
        _t("Put the {A} right next to the {R}, on its right.", "Place the {A} beside the {R}, to the right.",
           "Move the {A} so it stands just right of the {R}.", "Line the {A} up on the right side of the {R}.",
           "Set the {A} next to the {R} on the right."), dst={"P": {"type": "spot", "rel": "right", "ref": "R", "gap": 0.02}})
    add("gather_zone", "arrange", {"A": T, "B": T}, [("A", "V"), ("B", "V")],
        _t("Gather the {A} and the {B} onto the {V}.", "Put the {A} and the {B} on the {V}.",
           "Collect the {A} and the {B} on the {V}.", "Move both the {A} and the {B} onto the {V}.",
           "Place the {A}, then the {B}, on the {V}."),
        dst={"V": {"type": "node", "kinds": ("zone", "seat"), "shared": True}}, needs=("node:zone|seat",))
    add("line_by_height", "arrange", {"A": dict(T, rank="short"), "B": dict(T, rank="tall")}, [("A", "P1"), ("B", "P2")],
        _t("Line up the {A} and the {B} from shortest to tallest, left to right.", "Put the shorter one ({A}) on the left and the taller ({B}) on the right.",
           "Order the {A} and the {B} by height, left to right.", "Make a row by height: {A} then {B}.",
           "Arrange the two by height, the {A} first on the left."),
        dst={"P1": {"type": "spot", "line": ("y", 0, 2)}, "P2": {"type": "spot", "line": ("y", 1, 2)}})
    add("to_front_left", "arrange", {"A": T}, [("A", "P")],
        _t("Move the {A} to the front left corner of the {Msurf}.", "Put the {A} near the front left of the {Msurf}.",
           "Slide... no, pick up the {A} and put it at the front left.", "Place the {A} in the front left area.",
           "Put the {A} closer to me, on the left."), dst={"P": {"type": "spot", "corner": "front_left"}})
    add("to_back_right", "arrange", {"A": T}, [("A", "P")],
        _t("Move the {A} to the back right of the {Msurf}.", "Put the {A} far back on the right.",
           "Place the {A} in the back right area.", "Put the {A} away from me, on the right.",
           "Move the {A} to the rear right corner."), dst={"P": {"type": "spot", "corner": "back_right"}})
    add("spread_out", "arrange", {"A": T, "B": T}, [("A", "P")],
        _t("Move the {A} away from the {B}, to its left.", "Give the {B} some room: put the {A} on the {B}'s left.",
           "Separate the {A} from the {B}; place it to the left.", "Put the {A} a little to the left of the {B}.",
           "Shift the {A} left of the {B}."), dst={"P": {"type": "spot", "rel": "left", "ref": "B", "gap": 0.06}})

    # 3. stack (쌓기)
    B_ = {"role": "base"}
    st_t = _t("Stack the {A} on the {B}.", "Put the {A} on top of the {B}.", "Place the {A} onto the {B}.",
              "Set the {A} on the {B}.", "Could you stack the {A} on top of the {B}?")
    add("stack2", "stack", {"A": T, "B": B_}, [("A", "B")], st_t)
    add("stack3", "stack", {"A": dict(B_, as_target=True), "B": B_, "C": T}, [("A", "B"), ("C", "A")],
        _t("Stack the {A} on the {B}, then the {C} on the {A}.", "Build a stack: {B} at the bottom, then {A}, then {C}.",
           "Put the {A} on the {B} and the {C} on top of the {A}.", "Make a tower of the {B}, {A} and {C}.",
           "First the {A} onto the {B}, then the {C} onto the {A}."))
    add("stack_by_colour", "stack", {"A": T, "B": dict(B_, colour_named=True), "X": dict(B_, decoy_of="B")},
        [("A", "B")], _t("Put the {A} on the {B}, not on the other one.", "Stack the {A} on the {B}.",
                         "Place the {A} on top of the {B}.", "The {A} goes on the {B}.", "Set the {A} onto the {B}."))
    add("stack_on_second", "stack", {"A": T, "B": dict(B_, on="second")}, [("A", "B")],
        _t("Put the {A} on the {B} on the {Bsurf}.", "Stack the {A} on top of the {B} over on the {Bsurf}.",
           "Take the {A} to the {Bsurf} and put it on the {B}.", "Place the {A} on the {B}.",
           "The {A} goes on top of the {B} on the {Bsurf}."), needs=("second",))
    add("unstack", "stack", {"B": B_, "A": dict(T, on="stacked:B")}, [("A", "P")],
        _t("Take the {A} off the {B} and put it to the right of the {B}.", "Unstack the {A}: place it right of the {B}.",
           "Move the {A} from the top of the {B} to its right.", "Lift the {A} off the {B} and set it on the right.",
           "Put the {A} next to the {B} on the right instead of on top."),
        dst={"P": {"type": "spot", "rel": "right", "ref": "B"}})
    add("restack", "stack", {"B": B_, "A": dict(T, on="stacked:B"), "C": B_}, [("A", "C")],
        _t("Move the {A} from the {B} onto the {C}.", "Take the {A} off the {B} and stack it on the {C}.",
           "Put the {A} on the {C} instead of the {B}.", "Restack the {A} onto the {C}.",
           "Shift the {A} from the {B} to the top of the {C}."))
    add("stack_on_bigger", "stack", {"A": dict(T, rank="small"), "B": dict(B_, rank="big")}, [("A", "B")],
        _t("Put the smaller {A} on the bigger {B}.", "Stack the {A} on top of the {B}, small on big.",
           "Place the {A} onto the {B}.", "The {A} goes on the {B}.", "Set the {A} on the {B}."))
    add("stack_then_in", "stack", {"A": T, "B": B_, "C": T, "H": {"role": "container", "kind": "wide"}},
        [("A", "B"), ("C", "H")], _t("Stack the {A} on the {B}, then put the {C} into the {H}.",
                                     "Put the {A} on the {B} and the {C} in the {H}.",
                                     "First the {A} onto the {B}; then the {C} into the {H}.",
                                     "Place the {A} on top of the {B}, then drop the {C} in the {H}.",
                                     "{A} on the {B}, {C} in the {H}."))

    # 4. sort (분류)
    W_ = {"role": "container", "kind": "wide"}
    add("sort2_colour", "sort", {"A": dict(T, colour_named=True), "B": dict(T, colour_named=True, other_colour="A"),
                                 "H": W_, "G": W_},
        [("A", "H"), ("B", "G")], _t("Put the {A} in the {H} and the {B} in the {G}.",
                                     "Sort by colour: {A} into the {H}, {B} into the {G}.",
                                     "The {A} goes in the {H}, the {B} in the {G}.",
                                     "Place the {A} into the {H}, then the {B} into the {G}.",
                                     "Sort the {A} and the {B} into the {H} and the {G}."))
    add("sort2_kind", "sort", {"A": dict(T, cats=FOOD), "B": dict(T, cats=TOYISH), "H": W_, "G": W_},
        [("A", "H"), ("B", "G")], _t("Food goes in the {H} and toys in the {G}: sort the {A} and the {B}.",
                                     "Put the {A} in the {H} and the {B} in the {G}.",
                                     "Sort the {A} into the {H} and the {B} into the {G}.",
                                     "The {A} belongs in the {H}, the {B} in the {G}.",
                                     "Separate them: {A} to the {H}, {B} to the {G}."))
    add("sort3_two", "sort", {"A": dict(T, cats=FOOD), "B": dict(T, cats=TOYISH), "C": dict(T, cats=FOOD),
                              "H": W_, "G": W_}, [("A", "H"), ("B", "G"), ("C", "H")],
        _t("Put the food in the {H} and the toy in the {G}: {A}, {B}, {C}.", "Sort: {A} and {C} into the {H}, {B} into the {G}.",
           "Place the {A} in the {H}, the {B} in the {G}, the {C} in the {H}.",
           "Put the {A} and the {C} in the {H}, and the {B} in the {G}.", "Sort the three objects: food in the {H}, the rest in the {G}."))
    add("sort_size", "sort", {"A": dict(T, rank="big"), "B": dict(T, rank="small"), "H": W_, "G": W_},
        [("A", "H"), ("B", "G")], _t("Put the bigger {A} in the {H} and the smaller {B} in the {G}.",
                                     "Sort by size: {A} into the {H}, {B} into the {G}.",
                                     "The large {A} goes in the {H}, the small {B} in the {G}.",
                                     "Place the {A} in the {H} and the {B} in the {G}.",
                                     "Big one ({A}) in the {H}, small one ({B}) in the {G}."))
    add("sort_odd_one", "sort", {"A": dict(T, cats=FOOD), "X": dict(T, cats=TOYISH), "Y": dict(T, cats=TOYISH), "H": W_},
        [("A", "H")], _t("Put the only food item, the {A}, into the {H}.", "Move the {A} into the {H}; leave the toys.",
                         "The {A} is the odd one out: put it in the {H}.", "Put the {A} in the {H}.",
                         "Take the {A} and place it into the {H}."))
    add("sort_same_colour", "sort", {"A": dict(T, colour_named=True), "B": dict(T, same_colour="A"),
                                     "H": W_}, [("A", "H"), ("B", "H")],
        _t("Put both {Acol} objects, the {A} and the {B}, into the {H}.", "Collect the {Acol} things in the {H}: {A} and {B}.",
           "Place the {A} and then the {B} in the {H}.", "Put the {A} and the {B} into the {H}.",
           "Everything {Acol} goes in the {H}: the {A} and the {B}."))
    add("sort_cubbies", "sort", {"A": dict(T, cats=FOOD), "B": dict(T, cats=TOYISH)}, [("A", "V1"), ("B", "V2")],
        _t("Put the {A} in one compartment and the {B} in another.", "Sort the {A} and the {B} into two compartments.",
           "Place the {A} in the {V1} and the {B} in the {V2}.", "Put the {A} and the {B} into separate compartments.",
           "The {A} goes in the {V1}, the {B} in the {V2}."),
        dst={"V1": {"type": "node", "kinds": ("cubby", "slot")}, "V2": {"type": "node", "kinds": ("cubby", "slot")}},
        needs=("node2:cubby|slot",))
    add("sort_left_right", "sort", {"A": dict(T, cats=FOOD), "B": dict(T, cats=TOYISH)}, [("A", "P1"), ("B", "P2")],
        _t("Put the food ({A}) on the left and the toy ({B}) on the right.", "Sort: {A} to the left side, {B} to the right side.",
           "Place the {A} on the left and the {B} on the right.", "Food left, toy right: move the {A} and the {B}.",
           "Move the {A} to the left and the {B} to the right."),
        dst={"P1": {"type": "spot", "line": ("y", 0, 2), "spacing": 0.18}, "P2": {"type": "spot", "line": ("y", 1, 2), "spacing": 0.18}})

    # 5. put into (넣기)
    in_t = _t("Put the {A} in the {H}.", "Place the {A} into the {H}.", "Drop the {A} into the {H}.",
              "Put the {A} inside the {H}.", "Could you put the {A} in the {H}?")
    add("in_wide", "put_in", {"A": T, "H": W_}, [("A", "H")], in_t)
    add("in_by_colour", "put_in", {"A": T, "H": dict(W_, colour_named=True), "X": dict(W_, decoy_of="H")}, [("A", "H")], in_t)
    add("in_cubby", "put_in", {"A": T}, [("A", "V")], _t("Put the {A} in the {V}.", "Place the {A} into the {V}.",
                                                         "Put the {A} inside the {V}.", "Store the {A} in the {V}.",
                                                         "Move the {A} into the {V}."),
        dst={"V": {"type": "node", "kinds": ("cubby", "container", "slot")}}, needs=("node:cubby|container|slot",))
    add("in_from_second", "put_in", {"A": dict(T, on="second"), "H": W_}, [("A", "H")],
        _t("Take the {A} from the {Asurf} and put it in the {H}.", "Move the {A} off the {Asurf} into the {H}.",
           "Put the {A} from the {Asurf} into the {H}.", "Get the {A} and drop it in the {H}.",
           "Place the {A} into the {H}."), needs=("second",))
    add("in_two_same", "put_in", {"A": T, "B": T, "H": dict(W_, big=True)}, [("A", "H"), ("B", "H")],
        _t("Put the {A} and the {B} in the {H}.", "Place both the {A} and the {B} into the {H}.",
           "Put the {A}, then the {B}, into the {H}.", "Drop the {A} and the {B} in the {H}.",
           "Both the {A} and the {B} go in the {H}."))
    add("in_left_one", "put_in", {"A": T, "H": W_, "X": W_}, [("A", "H")],
        _t("Put the {A} in the {Hside} container.", "Place the {A} into the container on the {Hside}.",
           "Use the {Hside} one of the two containers for the {A}.", "Drop the {A} in the {Hside} container.",
           "The {A} goes in the container on the {Hside}."), needs=("side_pair:H:X",))
    add("in_onto_tray", "put_in", {"A": T, "H": {"role": "container", "kind": "flat"}}, [("A", "H")],
        _t("Put the {A} on the {H}.", "Place the {A} onto the {H}.", "Set the {A} on the {H}.",
           "Move the {A} onto the {H}.", "Could you put the {A} on the {H}?"))
    add("in_second_container", "put_in", {"A": T, "H": dict(W_, on="second")}, [("A", "H")],
        _t("Put the {A} in the {H} on the {Hsurf}.", "Place the {A} into the {H} over on the {Hsurf}.",
           "Drop the {A} in the {H} that is on the {Hsurf}.", "Move the {A} into the {H}.",
           "The {A} goes into the {H} on the {Hsurf}."), needs=("second",))

    # 6. set the table (차리기)
    PL = {"role": "container", "kind": "flat"}
    add("set_food_on_plate", "set", {"A": dict(T, cats=FOOD), "H": PL}, [("A", "H")],
        _t("Serve the {A} on the {H}.", "Put the {A} on the {H}.", "Place the {A} onto the {H} for the meal.",
           "Set the {A} on the {H}.", "Put the {A} on the {H} at this place."))
    add("set_drink_right", "set", {"A": dict(T, cats=DRINK), "H": PL}, [("A", "P")],
        _t("Set the {A} to the right of the {H}.", "Put the {A} on the right side of the {H}.",
           "Place the {A} just right of the {H}.", "The {A} goes right of the {H}.",
           "Put the {A} beside the {H}, on the right."), dst={"P": {"type": "spot", "rel": "right", "ref": "H"}})
    add("set_drink_left", "set", {"A": dict(T, cats=DRINK), "H": PL}, [("A", "P")],
        _t("Set the {A} to the left of the {H}.", "Put the {A} on the left side of the {H}.",
           "Place the {A} just left of the {H}.", "The {A} goes left of the {H}.",
           "Put the {A} beside the {H}, on the left."), dst={"P": {"type": "spot", "rel": "left", "ref": "H"}})
    add("set_two_plates", "set", {"A": dict(T, cats=FOOD), "B": dict(T, cats=FOOD), "H": PL, "G": PL},
        [("A", "H"), ("B", "G")], _t("Serve the {A} on the {H} and the {B} on the {G}.",
                                     "Put the {A} on the {H}, then the {B} on the {G}.",
                                     "Set the {A} onto the {H} and the {B} onto the {G}.",
                                     "Place one each: {A} on the {H}, {B} on the {G}.",
                                     "Put food on both plates: the {A} and the {B}."))
    add("set_on_mat", "set", {"A": T}, [("A", "V")], _t("Put the {A} on the {V}.", "Set the {A} on the {V}.",
                                                        "Place the {A} onto the {V}.", "Move the {A} to the {V}.",
                                                        "The {A} goes on the {V}."),
        dst={"V": {"type": "node", "kinds": ("seat", "zone")}}, needs=("node:seat|zone",))
    add("set_food_in_bowl", "set", {"A": dict(T, cats=FOOD), "H": {"role": "container", "kind": "wide", "cats": ("bowl",)}},
        [("A", "H")], _t("Put the {A} in the {H}.", "Serve the {A} in the {H}.", "Place the {A} into the {H}.",
                         "Drop the {A} in the {H} for the meal.", "The {A} goes in the {H}."))
    add("set_pair", "set", {"A": dict(T, cats=FOOD), "B": dict(T, cats=DRINK), "H": PL}, [("A", "H"), ("B", "P")],
        _t("Put the {A} on the {H} and the {B} to its right.", "Serve the {A} on the {H}, then set the {B} right of the {H}.",
           "Place the {A} onto the {H} and the {B} beside it on the right.", "{A} on the {H}, {B} on the right of it.",
           "Set a place: {A} on the {H}, {B} to the right."), dst={"P": {"type": "spot", "rel": "right", "ref": "H"}})
    add("set_centre", "set", {"A": T}, [("A", "P")],
        _t("Put the {A} in the middle of the {Msurf}.", "Place the {A} at the centre of the {Msurf}.",
           "Move the {A} to the centre.", "Set the {A} in the middle.", "Put the {A} right in the middle of the area."),
        dst={"P": {"type": "spot", "corner": "centre"}})

    # 7. clear (치우기)
    add("clear_one", "clear", {"A": T, "H": W_}, [("A", "H")],
        _t("Clear the {A} away into the {H}.", "Tidy up: put the {A} in the {H}.", "Put the {A} away in the {H}.",
           "Clean up the {A} by putting it in the {H}.", "Get the {A} off the {Msurf} and into the {H}."))
    add("clear_two", "clear", {"A": T, "B": T, "H": dict(W_, big=True)}, [("A", "H"), ("B", "H")],
        _t("Clear the {A} and the {B} into the {H}.", "Tidy up both the {A} and the {B} into the {H}.",
           "Put the {A} and the {B} away in the {H}.", "Clean up: {A} and {B} into the {H}.",
           "Put the {A} in the {H}, then the {B}."))
    add("clear_three", "clear", {"A": T, "B": T, "C": T, "H": dict(W_, big=True)}, [("A", "H"), ("B", "H"), ("C", "H")],
        _t("Clear the {A}, the {B} and the {C} into the {H}.", "Tidy up: all three ({A}, {B}, {C}) into the {H}.",
           "Put the {A}, {B} and {C} away in the {H}.", "Clean the {Msurf}: {A}, {B}, {C} go in the {H}.",
           "One by one, put the {A}, the {B} and the {C} in the {H}."))
    add("clear_plate", "clear", {"P0": PL, "A": dict(T, on="on:P0"), "H": W_}, [("A", "H")],
        _t("Clear the {A} off the {P0} into the {H}.", "Take the {A} from the {P0} and put it in the {H}.",
           "Remove the {A} from the {P0}; it goes in the {H}.", "Put the {A} that is on the {P0} into the {H}.",
           "Empty the {P0}: the {A} goes in the {H}."))
    add("clear_to_second", "clear", {"A": T}, [("A", "V")],
        _t("Clear the {A} off the {Msurf} onto the {V}.", "Move the {A} out of the way onto the {V}.",
           "Put the {A} away on the {V}.", "Tidy the {A} onto the {V}.", "Place the {A} on the {V} to clear the space."),
        dst={"V": {"type": "node", "kinds": ("top", "zone"), "second": True}}, needs=("second",))
    add("clear_zone", "clear", {"A": dict(T, on="node:zone|seat")}, [("A", "P")],
        _t("Take the {A} off the {Asurf} and put it to its left.", "Clear the {Asurf}: move the {A} off to the side.",
           "Move the {A} off the {Asurf}.", "Get the {A} off the {Asurf} and set it aside.",
           "Remove the {A} from the {Asurf}."), dst={"P": {"type": "spot", "off_node": "A"}}, needs=("node:zone|seat",))
    add("clear_to_cubby", "clear", {"A": T, "B": T}, [("A", "V")],
        _t("Put the {A} away in the {V}.", "Clear the {A} into the {V}.", "Tidy up the {A}: it goes in the {V}.",
           "Store the {A} in the {V}.", "Move the {A} into the {V} to clear the {Msurf}."),
        dst={"V": {"type": "node", "kinds": ("cubby", "container", "slot")}}, needs=("node:cubby|container|slot",))
    add("clear_colour", "clear", {"A": dict(T, colour_named=True), "X": dict(T, other_colour="A"), "H": W_}, [("A", "H")],
        _t("Clear only the {Acol} object into the {H}.", "Put the {A} away in the {H}, leave the rest.",
           "Tidy the {A} into the {H}.", "Only the {A} goes into the {H}.", "Put the {Acol} {Anoun} in the {H}."))
    add("clear_to_basket_second", "clear", {"A": T, "B": T, "H": dict(W_, on="second", big=True)},
        [("A", "H"), ("B", "H")], _t("Clear the {A} and the {B} into the {H} on the {Hsurf}.",
                                     "Put both the {A} and the {B} away in the {H}.",
                                     "Tidy up: the {A} then the {B} into the {H}.",
                                     "Move the {A} and the {B} into the {H} over on the {Hsurf}.",
                                     "The {A} and the {B} go in the {H}."), needs=("second",))

    # 8. relations (위치 관계)
    for rel, words in (("left", ("to the left of", "on the left side of")), ("right", ("to the right of", "on the right side of")),
                       ("front", ("in front of", "on the near side of")), ("behind", ("behind", "on the far side of"))):
        add(f"rel_{rel}", "relation", {"A": T, "R": T}, [("A", "P")],
            _t(f"Put the {{A}} {words[0]} the {{R}}.", f"Place the {{A}} {words[1]} the {{R}}.",
               f"Move the {{A}} so it is {words[0]} the {{R}}.", f"Set the {{A}} {words[0]} the {{R}}, close to it.",
               f"The {{A}} should end up {words[0]} the {{R}}."), dst={"P": {"type": "spot", "rel": rel, "ref": "R"}})
    add("rel_between", "relation", {"A": T, "R": T, "Q": T}, [("A", "P")],
        _t("Put the {A} between the {R} and the {Q}.", "Place the {A} in the middle between the {R} and the {Q}.",
           "Move the {A} to halfway between the {R} and the {Q}.", "Set the {A} between the {R} and the {Q}.",
           "The {A} goes in between the {R} and the {Q}."), dst={"P": {"type": "spot", "between": ("R", "Q")}})
    add("rel_right_of_container", "relation", {"A": T, "H": W_}, [("A", "P")],
        _t("Put the {A} to the right of the {H}.", "Place the {A} next to the {H}, on its right.",
           "Set the {A} right of the {H}.", "Move the {A} beside the {H} on the right.",
           "The {A} goes on the right of the {H}."), dst={"P": {"type": "spot", "rel": "right", "ref": "H"}})
    add("rel_two_sides", "relation", {"A": T, "B": T, "R": T}, [("A", "P1"), ("B", "P2")],
        _t("Put the {A} left of the {R} and the {B} right of it.", "Place the {A} on the {R}'s left and the {B} on its right.",
           "Flank the {R}: {A} on the left, {B} on the right.", "Set the {A} to the left and the {B} to the right of the {R}.",
           "The {A} goes left of the {R}, the {B} right of it."),
        dst={"P1": {"type": "spot", "rel": "left", "ref": "R"}, "P2": {"type": "spot", "rel": "right", "ref": "R"}})
    add("rel_left_of_container", "relation", {"A": T, "H": W_}, [("A", "P")],
        _t("Put the {A} to the left of the {H}.", "Place the {A} next to the {H}, on its left.",
           "Set the {A} left of the {H}.", "Move the {A} beside the {H} on the left.",
           "The {A} goes on the left of the {H}."), dst={"P": {"type": "spot", "rel": "left", "ref": "H"}})
    add("rel_front_left", "relation", {"A": T, "R": T}, [("A", "P")],
        _t("Put the {A} in front of the {R}, a bit to the left.", "Place the {A} front-left of the {R}.",
           "Move the {A} to the near left side of the {R}.", "Set the {A} diagonally in front and left of the {R}.",
           "The {A} goes front-left of the {R}."), dst={"P": {"type": "spot", "rel": "front_left", "ref": "R"}})

    # 9. height moves (높이 옮기기)
    add("up_to_higher", "height", {"A": T}, [("A", "V")],
        _t("Move the {A} up onto the {V}.", "Put the {A} on the higher {V}.", "Lift the {A} onto the {V}.",
           "Place the {A} up on the {V}.", "The {A} goes up on the {V}."),
        dst={"V": {"type": "node", "kinds": ("top", "zone"), "higher": True}}, needs=("higher",))
    add("down_to_lower", "height", {"A": T}, [("A", "V")],
        _t("Bring the {A} down to the {V}.", "Put the {A} on the lower {V}.", "Move the {A} down onto the {V}.",
           "Place the {A} down on the {V}.", "The {A} goes down on the {V}."),
        dst={"V": {"type": "node", "kinds": ("top", "zone"), "lower": True}}, needs=("lower",))
    add("up_into_container", "height", {"A": T, "H": dict(W_, on="higher")}, [("A", "H")],
        _t("Put the {A} into the {H} up on the {Hsurf}.", "Lift the {A} into the {H} on the {Hsurf}.",
           "Move the {A} up into the {H}.", "Place the {A} in the {H} on the higher {Hsurf}.",
           "The {A} goes up into the {H}."), needs=("higher",))
    add("down_into_container", "height", {"A": dict(T, on="higher"), "H": W_}, [("A", "H")],
        _t("Take the {A} down from the {Asurf} into the {H}.", "Bring the {A} down into the {H}.",
           "Move the {A} from the {Asurf} into the {H}.", "Put the {A} from up on the {Asurf} in the {H}.",
           "The {A} goes down into the {H}."), needs=("higher",))
    add("swap_levels", "height", {"A": T, "B": dict(T, on="second")}, [("A", "V"), ("B", "P")],
        _t("Move the {A} onto the {V} and bring the {B} down to where the {A} was.",
           "Swap: {A} to the {V}, {B} to the {Msurf}.", "Put the {A} on the {V}, then the {B} on the {Msurf}.",
           "Exchange the places of the {A} and the {B}.", "Move the {A} to the {V} and the {B} to the {Msurf}."),
        dst={"V": {"type": "node", "kinds": ("top", "zone"), "of_obj": "B"}, "P": {"type": "spot", "at_obj": "A"}},
        needs=("second",))
    add("up_two", "height", {"A": T, "B": T}, [("A", "V"), ("B", "V")],
        _t("Put the {A} and the {B} up on the {V}.", "Move both the {A} and the {B} onto the {V}.",
           "Lift the {A}, then the {B}, onto the {V}.", "Place the {A} and the {B} on the higher {V}.",
           "Both the {A} and the {B} go up on the {V}."),
        dst={"V": {"type": "node", "kinds": ("top", "zone"), "higher": True, "shared": True}}, needs=("higher",))
    add("tier_to_tier", "height", {"A": dict(T, on="higher")}, [("A", "V")],
        _t("Move the {A} from the {Asurf} down to the {V}.", "Put the {A} from the upper level onto the {V}.",
           "Bring the {A} down one level to the {V}.", "Place the {A} on the {V}.", "The {A} goes onto the {V}."),
        dst={"V": {"type": "node", "kinds": ("top", "zone"), "lower_than_obj": "A"}}, needs=("higher",))
    add("down_next_to", "height", {"A": dict(T, on="higher"), "R": T}, [("A", "P")],
        _t("Bring the {A} down and put it right of the {R}.", "Move the {A} from the {Asurf} to the right of the {R}.",
           "Put the {A} down beside the {R}, on its right.", "Take the {A} down next to the {R}.",
           "The {A} goes down, right of the {R}."), dst={"P": {"type": "spot", "rel": "right", "ref": "R"}},
        needs=("higher",))
    # extra single-step definitions (headroom for the >= 75 passing G1, 2026-10-01)
    add("rel_behind_container", "relation", {"A": T, "H": W_}, [("A", "P")],
        _t("Put the {A} behind the {H}.", "Place the {A} on the far side of the {H}.", "Set the {A} just behind the {H}.",
           "Move the {A} so it stands behind the {H}.", "The {A} goes behind the {H}."),
        dst={"P": {"type": "spot", "rel": "behind", "ref": "H"}})
    add("rel_front_of_container", "relation", {"A": T, "H": W_}, [("A", "P")],
        _t("Put the {A} in front of the {H}.", "Place the {A} on the near side of the {H}.", "Set the {A} just in front of the {H}.",
           "Move the {A} so it stands in front of the {H}.", "The {A} goes in front of the {H}."),
        dst={"P": {"type": "spot", "rel": "front", "ref": "H"}})
    add("in_kind_food", "put_in", {"A": dict(T, cats=FOOD), "X": dict(T, cats=TOYISH), "H": W_}, [("A", "H")],
        _t("Put the food into the {H}.", "Put the {A} into the {H}, not the toy.", "Place the food item, the {A}, in the {H}.",
           "The {A} goes into the {H}.", "Drop the {A} into the {H}."))
    add("in_kind_toy", "put_in", {"A": dict(T, cats=TOYISH), "X": dict(T, cats=FOOD), "H": W_}, [("A", "H")],
        _t("Put the toy into the {H}.", "Put the {A} into the {H}, not the food.", "Place the toy, the {A}, in the {H}.",
           "The {A} goes into the {H}.", "Drop the {A} into the {H}."))
    add("set_drink_front", "set", {"A": dict(T, cats=DRINK), "H": PL}, [("A", "P")],
        _t("Set the {A} in front of the {H}.", "Put the {A} on the near side of the {H}.", "Place the {A} just in front of the {H}.",
           "The {A} goes in front of the {H}.", "Put the {A} before the {H}, close to me."),
        dst={"P": {"type": "spot", "rel": "front", "ref": "H"}})
    add("clear_food_bowl", "clear", {"A": dict(T, cats=FOOD), "H": {"role": "container", "kind": "wide", "cats": ("bowl",)}},
        [("A", "H")], _t("Clear the {A} into the {H}.", "Put the leftover {A} in the {H}.", "Tidy the {A} away into the {H}.",
                         "The {A} goes back into the {H}.", "Put the {A} in the {H} to clear up."))
    add("clear_toy_bin", "clear", {"A": dict(T, cats=TOYISH), "H": {"role": "container", "kind": "wide",
                                                                  "cats": ("bin", "basket", "box")}},
        [("A", "H")], _t("Tidy the {A} into the {H}.", "Put the {A} away in the {H}.", "Clear the {A} into the {H}.",
                         "The {A} belongs in the {H}.", "Put the {A} back in the {H}."))
    add("to_front_right", "arrange", {"A": T}, [("A", "P")],
        _t("Move the {A} to the front right of the {Msurf}.", "Put the {A} near the front right.", "Place the {A} closer to me, on the right.",
           "Put the {A} in the front right area.", "Move the {A} to the near right corner."),
        dst={"P": {"type": "spot", "corner": "front_right"}})
    add("to_back_left", "arrange", {"A": T}, [("A", "P")],
        _t("Move the {A} to the back left of the {Msurf}.", "Put the {A} far back on the left.", "Place the {A} away from me, on the left.",
           "Put the {A} in the back left area.", "Move the {A} to the rear left corner."),
        dst={"P": {"type": "spot", "corner": "back_left"}})
    add("spread_right", "arrange", {"A": T, "B": T}, [("A", "P")],
        _t("Move the {A} away from the {B}, to its right.", "Give the {B} room: put the {A} on the {B}'s right.",
           "Separate the {A} from the {B}; place it to the right.", "Put the {A} a little to the right of the {B}.",
           "Shift the {A} right of the {B}."), dst={"P": {"type": "spot", "rel": "right", "ref": "B", "gap": 0.06}})
    add("stack_named", "stack", {"A": dict(T, colour_named=True), "X": dict(T, decoy_of="A"), "B": B_}, [("A", "B")],
        _t("Stack the {A} on the {B}.", "Put the {A}, not the other one, on the {B}.", "Place the {A} on top of the {B}.",
           "The {A} goes on the {B}.", "Set the {A} onto the {B}."))
    add("down_left_of", "height", {"A": dict(T, on="higher"), "R": T}, [("A", "P")],
        _t("Bring the {A} down and put it left of the {R}.", "Move the {A} from the {Asurf} to the left of the {R}.",
           "Put the {A} down beside the {R}, on its left.", "Take the {A} down next to the {R}, on the left.",
           "The {A} goes down, left of the {R}."), dst={"P": {"type": "spot", "rel": "left", "ref": "R"}},
        needs=("higher",))
    add("down_front_of", "height", {"A": dict(T, on="higher"), "R": T}, [("A", "P")],
        _t("Bring the {A} down in front of the {R}.", "Move the {A} from the {Asurf} to the front of the {R}.",
           "Put the {A} down on the near side of the {R}.", "Take the {A} down and set it before the {R}.",
           "The {A} goes down, in front of the {R}."), dst={"P": {"type": "spot", "rel": "front", "ref": "R"}},
        needs=("higher",))
    add("ins_named", "insert", {"A": dict(SL, colour_named=True)}, [("A", "V")],
        _t("Put the {A} into the {V}.", "Stand the {Acol} one up in the {V}.", "Insert the {A} into the {V}.",
           "Place the {A} upright inside the {V}.", "The {A} goes into the {V}."), dst={"V": HV}, judge=up,
        needs=("node:slot",))
    # stack on parametric blocks / risers (node kind "stand"; pilot 5)
    SV = {"type": "node", "kinds": ("stand",)}
    add("block_stack", "stack", {"A": T}, [("A", "V")],
        _t("Stack the {A} on the {V}.", "Put the {A} on top of the {V}.", "Place the {A} onto the {V}.",
           "Set the {A} up on the {V}.", "The {A} goes on top of the {V}."), dst={"V": SV}, needs=("node:stand",))
    add("block_two", "stack", {"A": T, "B": T}, [("A", "V1"), ("B", "V2")],
        _t("Put the {A} on one block and the {B} on the other.", "Stack the {A} and the {B} on the two blocks.",
           "Place the {A} on the {V1} and the {B} on the {V2}.", "One object per block: the {A}, then the {B}.",
           "Put the {A} and the {B} on top of the two blocks."), dst={"V1": SV, "V2": SV}, needs=("node2:stand",))
    add("block_by_side", "stack", {"A": T}, [("A", "V")],
        _t("Put the {A} on the block on the {Vside}.", "Stack the {A} on the {Vside} block.",
           "Place the {A} on top of the block that is on the {Vside}.", "Use the {Vside} block for the {A}.",
           "The {A} goes on the {Vside} block."), dst={"V": dict(SV, side_of_two=True)}, needs=("node2:stand",))
    add("block_unstack", "stack", {"A": dict(T, on="node:stand")}, [("A", "P")],
        _t("Take the {A} off the block and put it on the {Msurf}.", "Unstack the {A}: set it down on the {Msurf}.",
           "Move the {A} from the top of the block down to the {Msurf}.", "Lift the {A} off the block and put it down.",
           "Put the {A} that is on the block onto the {Msurf}."), dst={"P": {"type": "spot", "off_node": "A"}},
        needs=("node:stand",))
    add("block_restack", "stack", {"A": dict(T, on="node:stand")}, [("A", "V")],
        _t("Move the {A} from one block to the other.", "Restack the {A} onto the other block.",
           "Take the {A} off its block and put it on the {V}.", "Shift the {A} to the other block.",
           "Put the {A} on the other block instead."), dst={"V": dict(SV, not_obj_node="A")}, needs=("node2:stand",))
    add("block_from_second", "stack", {"A": dict(T, on="second")}, [("A", "V")],
        _t("Take the {A} from the {Asurf} and stack it on the {V}.", "Move the {A} off the {Asurf} onto the {V}.",
           "Put the {A} from the {Asurf} on top of the {V}.", "Get the {A} and set it on the {V}.",
           "The {A} goes onto the {V}."), dst={"V": SV}, needs=("second", "node:stand"))
    add("block_then_in", "stack", {"A": T, "B": T, "H": {"role": "container", "kind": "wide"}}, [("A", "V"), ("B", "H")],
        _t("Stack the {A} on the {V}, then put the {B} into the {H}.", "Put the {A} on the {V} and the {B} in the {H}.",
           "First the {A} onto the {V}; then the {B} into the {H}.", "{A} on the {V}, {B} in the {H}.",
           "Place the {A} on top of the {V}, then drop the {B} in the {H}."), dst={"V": SV}, needs=("node:stand",))
    add("block_named", "stack", {"A": dict(T, colour_named=True), "X": dict(T, decoy_of="A")}, [("A", "V")],
        _t("Stack the {A} on the {V}.", "Put the {A}, not the other one, on the {V}.", "Place the {A} on top of the {V}.",
           "The {A} goes on the {V}.", "Set the {A} onto the {V}."), dst={"V": SV}, needs=("node:stand",))
    # sorting onto places on the surface (spots; pilot 5: spot destinations held 89 %)
    add("sort_front_back", "sort", {"A": dict(T, cats=FOOD), "B": dict(T, cats=TOYISH)}, [("A", "P1"), ("B", "P2")],
        _t("Put the food ({A}) in front and the toy ({B}) at the back.", "Sort: {A} to the near side, {B} to the far side.",
           "Place the {A} close to me and the {B} further away.", "Food in front, toy behind: move the {A} and the {B}.",
           "Move the {A} to the front and the {B} to the back."),
        dst={"P1": {"type": "spot", "line": ("x", 0, 2), "spacing": 0.16}, "P2": {"type": "spot", "line": ("x", 1, 2), "spacing": 0.16}})
    add("sort_colour_sides", "sort", {"A": dict(T, colour_named=True), "B": dict(T, colour_named=True, other_colour="A")},
        [("A", "P1"), ("B", "P2")],
        _t("Put the {Acol} one on the left and the {Bcol} one on the right.", "Sort by colour: {A} left, {B} right.",
           "Place the {A} on the left side and the {B} on the right side.", "Move the {A} to the left and the {B} to the right.",
           "Separate them by colour: the {A} goes left, the {B} goes right."),
        dst={"P1": {"type": "spot", "line": ("y", 0, 2), "spacing": 0.18}, "P2": {"type": "spot", "line": ("y", 1, 2), "spacing": 0.18}})
    add("sort_food_bowl_toy_side", "sort", {"A": dict(T, cats=FOOD), "B": dict(T, cats=TOYISH), "H": W_},
        [("A", "H"), ("B", "P")],
        _t("Put the food in the {H} and the toy to its right.", "Sort: the {A} into the {H}, the {B} beside it on the right.",
           "Place the {A} in the {H}; set the {B} right of the {H}.", "Food goes in the {H}, the toy next to it: {A}, {B}.",
           "Put the {A} into the {H} and the {B} on the right of the {H}."),
        dst={"P": {"type": "spot", "rel": "right", "ref": "H"}})
    add("sort_size_sides", "sort", {"A": dict(T, rank="big"), "B": dict(T, rank="small")}, [("A", "P1"), ("B", "P2")],
        _t("Put the bigger one on the left and the smaller one on the right.", "Sort by size: {A} left, {B} right.",
           "Place the large {A} on the left and the small {B} on the right.", "Move the {A} left and the {B} right.",
           "Big left, small right: the {A} and the {B}."),
        dst={"P1": {"type": "spot", "line": ("y", 0, 2), "spacing": 0.18}, "P2": {"type": "spot", "line": ("y", 1, 2), "spacing": 0.18}})
    return {d.id: d for d in D}


DEFS = _defs()
# object gate (L8S objv gate rule: clean truth pick-and-place, pass >= 2 of the tries): not a task definition
GATE_DEFS = {"gate_move": TaskDef("gate_move", "gate", {"A": {"role": "target"}}, {"P": {"type": "spot", "rel": "left",
                                                                                               "ref": "A", "gap": 0.06}},
                                  (("A", "P"),), ("Move the {A} a little to the left.",) * 5)}


def get_def(name: str) -> TaskDef:
    return DEFS.get(name) or GATE_DEFS[name]
FAMILIES = ("insert", "arrange", "stack", "sort", "put_in", "set", "clear", "relation", "height")


# ------------------------------------------------------------------------------------------ helpers
def name_of(row: dict) -> str:
    return " ".join(str(row.get("task_name") or row.get("name") or "").lower().split())


def clash(a: str, b: str) -> bool:
    wa, wb = set(a.split()), set(b.split())
    return bool(wa and wb) and (wa <= wb or wb <= wa)


def kind_of(row: dict) -> str | None:
    """Container kind of a pool row: narrow (holders) / wide (into, big opening) / flat (onto)."""
    if row.get("role9") != "container":
        return None
    pk = (row.get("inside") or {}).get("place_kind")
    cat = row.get("l9cat")
    if pk == "onto":
        return "flat"
    op = float((row.get("inside") or {}).get("opening_min_side", 0))
    if cat in NARROW and op < 0.11:
        return "narrow"
    return "wide"


FINGER_OPEN = 0.107  # open pad gap (scene.GRIP_MAX_W): the fingers must fit the opening, or stay above the rim


def fits_into(obj: dict, cont: dict) -> bool:
    """onto: the footprint inside the top; into: the object passes the opening (6 mm each side) and the released
    fingers either fit inside the opening (open gap + 2 cm) or stay above the rim (grasp 1.8 cm below the object's
    top: rim depth <= object height - 3 cm)."""
    ins = cont.get("inside") or {}
    if ins.get("place_kind") == "onto":
        ob = ins.get("opening_box") or [[0, 0], [0, 0]]
        side = min(ob[0][1] - ob[0][0], ob[1][1] - ob[1][0])
        return 2 * float(obj["footprint_r"]) <= side + 0.01
    op = float(ins.get("opening_min_side", 0))
    if 2 * float(obj["footprint_r"]) > op - 0.012:
        return False
    depth = float(ins.get("rim_z") or ins.get("inner_floor_z") or 0) - float(ins.get("inner_floor_z") or 0)
    return op >= FINGER_OPEN + 0.02 or depth <= float(obj["height"]) - 0.03


def is_slender(row: dict) -> bool:
    return float(row["footprint_r"]) <= 0.035


def flat_top(row: dict) -> bool:
    return row.get("l9cat") in STACK_BASE and float(row.get("boxiness", 0.5)) >= 0.3


FINGER_HALF_X = 0.0535 + 0.012 + 0.01  # open pad half-gap + finger thickness + margin (fingers close along world x)
FINGER_HALF_Y = 0.02


def finger_clear(d, f_other: float) -> bool:
    """The open fingers around a grasp / release point (offset d = point - other object's centre) miss an object of
    footprint radius f_other: apart in x by more than the finger reach, or in y by more than the finger half-width
    (pilot 3: 57 % of the failures tipped or knocked a neighbour at the approach)."""
    return abs(float(d[0])) >= f_other + FINGER_HALF_X or abs(float(d[1])) >= f_other + FINGER_HALF_Y


def rel_offset(rel: str, gap: float, fa: float, fr: float) -> np.ndarray:
    """World offset of a relational spot from its reference (robot's view: left = +y, front = -x)."""
    d = fa + fr + gap
    return {"left": np.array([0.0, d]), "right": np.array([0.0, -d]), "front": np.array([-d, 0.0]),
            "behind": np.array([d, 0.0]), "front_left": np.array([-0.7 * d, 0.7 * d])}[rel]


def surf_name(node: dict) -> str:
    if node["kind"] == "stand":
        return "block"
    if node["kind"] == "slot":
        if node["part"].startswith("holder"):
            return "holder"
        return "umbrella stand" if node["part"].startswith("umbrella") else "rack slot"
    return {"top": "surface", "zone": "mat", "seat": "place mat", "cubby": "compartment",
            "container": "open box"}.get(node["kind"], "surface")


def deps(spec: dict) -> set:
    out = {spec[k] for k in ("other_colour", "same_colour", "decoy_of") if spec.get(k)}
    on = str(spec.get("on", ""))
    if on.startswith(("stacked:", "on:")):
        out.add(on.split(":", 1)[1])
    return out


def needed_first(name: str, objs: dict) -> bool:
    """A container another object starts in / on must be picked (and placed) before that object."""
    return any(name in deps(sp) for sp in objs.values())


def dep_order(objs: dict) -> list:
    """Object names in pick / place order: dependencies first, containers before the rest, then by name."""
    out, left = [], dict(objs)
    while left:
        ready = sorted((n for n, sp in left.items() if deps(sp) <= set(out)),
                       key=lambda n: (left[n]["role"] == "container" and not needed_first(n, objs), n))
        if not ready:
            raise ValueError(f"cyclic object constraints {list(left)}")
        out.append(ready[0])
        del left[ready[0]]
    return out


# ------------------------------------------------------------------------------------------ instantiate
class Fail(Exception):
    pass


def instantiate(defn: TaskDef, scene: dict, pool: dict, seed: int, rm, tries: int = 40, fixed: dict | None = None):
    """-> episode dict, or None when this scene / pool cannot host the definition (the caller redraws).
    fixed: {object name: pool id} (the object gate)."""
    for k in range(tries):
        rng = np.random.default_rng([int(seed), 911, k, int(hashlib.sha256(defn.id.encode()).hexdigest()[:6], 16)])
        try:
            return _try(defn, scene, pool, rng, rm, fixed or {})
        except Fail:
            continue
    return None


def _nodes(scene, rm):
    """{node id: (node, reachable points, visible points)} of the nodes with >= 4 reachable points."""
    lift = scene["lift"]
    out = {}
    for n in scene["nodes"]:
        pts = S9.usable(n, scene, rm, lift)
        if len(pts) >= 4:
            out[n["id"]] = (n, pts, S9.usable(n, scene, rm, lift, reach=False))
    return out


def _try(defn, scene, pool, rng, rm, fixed=None):
    fixed = fixed or {}
    nodes = _nodes(scene, rm)
    flats = [v for v in nodes.values() if v[0]["kind"] in ("top", "zone", "seat")]
    if not flats:
        raise Fail("no flat node")
    w = np.array([len(v[1]) for v in flats], float)
    nobj = len(defn.objs) + len(defn.dst)
    w = w ** (1.0 + 0.5 * nobj)  # busy definitions prefer the roomiest flat node
    main = flats[int(rng.choice(len(flats), p=w / w.sum()))]
    mz = main[0]["top_z"]
    others = [v for v in flats if abs(v[0]["top_z"] - mz) >= 0.04]
    need = set(defn.needs)
    second = None
    if "higher" in need:
        c = [v for v in others if v[0]["top_z"] > mz]
        if not c:
            raise Fail("no higher")
        second = c[int(rng.integers(len(c)))]
    elif "lower" in need:
        c = [v for v in others if v[0]["top_z"] < mz]
        if not c:
            raise Fail("no lower")
        second = c[int(rng.integers(len(c)))]
    elif "second" in need or any(o.get("on") == "second" for o in defn.objs.values()):
        if not others:
            raise Fail("no second")
        second = others[int(rng.integers(len(others)))]
    elif others:
        second = others[int(rng.integers(len(others)))]
    ep = {"def": defn.id, "family": defn.family, "main": main[0]["id"], "table_z": mz, "objects": {}, "dst": {}}
    placed = []  # (xy, footprint_r, is_target)
    names = []
    chosen = {}
    names_used = set()

    def pick(spec, oname):
        role = spec["role"]
        cand = []
        for k, r in pool.items():
            if oname in fixed and k != fixed[oname]:
                continue
            if k in chosen.values():
                continue
            nm = name_of(r)
            if not nm or any(clash(nm, u) for u in names_used):
                continue
            if role in ("target", "base") or spec.get("as_target"):
                if r.get("role9") != "target":
                    continue
                if role == "base" and not flat_top(r):
                    continue
                if spec.get("slender") and not is_slender(r):
                    continue
            elif role == "container":
                if kind_of(r) != spec["kind"]:
                    continue
                if float(r["footprint_r"]) > MAX_CONTAINER_R or float(r["height"]) > CLUTTER_H_MAX:
                    continue
                if spec.get("big") and float((r.get("inside") or {}).get("opening_min_side", 0)) < 0.12:
                    continue
            if spec.get("cats") and r.get("l9cat") not in spec["cats"]:
                continue
            if spec.get("colour_named") and r.get("colour") not in ("red", "orange", "yellow", "green", "blue",
                                                                  "purple", "pink", "brown", "black", "white"):
                continue
            if spec.get("colour_named") and r.get("colour") not in nm.split():
                continue
            if spec.get("other_colour") and r.get("colour") == pool[chosen[spec["other_colour"]]].get("colour"):
                continue
            if spec.get("same_colour") and (r.get("colour") != pool[chosen[spec["same_colour"]]].get("colour")):
                continue
            if spec.get("decoy_of"):
                ref = pool[chosen[spec["decoy_of"]]]
                if r.get("colour") == ref.get("colour") or (role == "container" and kind_of(r) != kind_of(ref)):
                    continue
            if role == "container" and any(chosen.get(a) is not None and not fits_into(pool[chosen[a]], r)
                                           for a, dd in defn.steps if dd == oname):
                continue
            if role == "base" and any(chosen.get(a) is not None
                                      and float(pool[chosen[a]]["footprint_r"]) > float(r["footprint_r"]) * 1.3
                                      for a, dd in defn.steps if dd == oname):
                continue
            rk = spec.get("rank")
            if rk in ("tall", "big"):
                key = "height" if rk == "tall" else "footprint_r"
                lows = [chosen[o] for o, sp in defn.objs.items() if sp.get("rank") in ("short", "small") and o in chosen]
                if any(float(r[key]) < float(pool[x][key]) * 1.15 for x in lows):
                    continue
            for a, dname in defn.steps:  # the object must fit every container / base it goes to
                if a == oname and dname in chosen and defn.objs.get(dname, {}).get("role") == "container"                         and not fits_into(r, pool[chosen[dname]]):
                    break
                if a == oname and dname in chosen and defn.objs.get(dname, {}).get("role") == "base"                         and float(r["footprint_r"]) > float(pool[chosen[dname]]["footprint_r"]) * 1.3:
                    break
            else:
                cand.append(k)
        if not cand:
            raise Fail(f"no pool object for {oname}")
        k = cand[int(rng.integers(len(cand)))]
        chosen[oname] = k
        names_used.add(name_of(pool[k]))
        return k

    order = dep_order(defn.objs)
    for on in order:
        pick(defn.objs[on], on)
    # rank constraints (size / height)
    for on, spec in defn.objs.items():
        if spec.get("rank") in ("tall", "big"):
            partner = [o for o, s in defn.objs.items() if s.get("rank") in ("short", "small")]
            for p in partner:
                a, b = pool[chosen[on]], pool[chosen[p]]
                key = "height" if spec["rank"] == "tall" else "footprint_r"
                if float(a[key]) < float(b[key]) * 1.15:
                    raise Fail("rank")
    # fit checks for into / onto steps
    for a, d in defn.steps:
        if d in defn.objs and defn.objs[d]["role"] == "container":
            if not fits_into(pool[chosen[a]], pool[chosen[d]]):
                raise Fail("does not fit")
        if d in defn.objs and defn.objs[d]["role"] == "base":
            if float(pool[chosen[a]]["footprint_r"]) > float(pool[chosen[d]]["footprint_r"]) * 1.3:
                raise Fail("base too small")

    def node_for(spec):
        on = spec.get("on", "main")
        if on in ("second", "higher"):
            if second is None or (on == "higher" and second[0]["top_z"] <= mz):
                raise Fail("no second node")
            return second
        if on.startswith("node:"):
            kinds = on[5:].split("|")
            c = [v for v in nodes.values() if v[0]["kind"] in kinds]
            if not c:
                raise Fail("no node kind")
            return c[int(rng.integers(len(c)))]
        return main

    def free(xy, fr, target, extra=()):
        """Clear of placed objects; around a target the open fingers (10.7 cm, closing along world x) need
        >= 10 cm in x unless the two are apart in y by more than their footprints + 2 cm."""
        for (p, f, t) in list(placed) + list(extra):
            d = np.asarray(xy, float) - p
            base = fr + f + 0.02
            if np.hypot(*d) < base:
                return False
            if (t or target) and not finger_clear(d, f if target else fr):
                return False
        return True

    def inside(node, xy, fr):
        s = S9.s_of(xy, scene["yaw"])
        (x0, x1), (y0, y1) = node["box"]
        m = max(fr * 0.8, 0.02)
        return x0 + m <= s[0] <= x1 - m and y0 + m <= s[1] <= y1 - m

    def place_obj(on, spec):
        k = chosen[on]
        r = pool[k]
        fr = float(r["footprint_r"])
        tgt = spec["role"] in ("target", "base")
        where = spec.get("on", "main")
        if where.startswith(("stacked:", "on:")):
            host = where.split(":", 1)[1]
            hk = chosen[host]
            hx = ep["objects"][hk]
            hr = pool[hk]
            lift_top = nodes[hx["node"]][0]["top_z"] + (
                float(hr["height"]) if hr.get("role9") != "container" else
                float((hr.get("inside") or {}).get("inner_floor_z") or 0) - float(hr.get("root_above_bottom", 0) or 0)
                + float(hr["height"]) / 2)
            m = rm.at_lift(scene["lift"])
            if not R9.reach_points(m, scene["arm"], [hx["xy"][0]], [hx["xy"][1]], lift_top)[0]:
                raise Fail("stacked start out of reach")  # pilot 4: the approach above a stacked object got stuck
            ep["objects"][k] = {"xy": list(hx["xy"]), "node": hx["node"], "support": hk, "fr": fr}
            return
        node, pts, vis = node_for(spec)
        movers = {a for a, _ in defn.steps}
        dests = {d for _, d in defn.steps}
        refs = {sp.get("ref") for sp in defn.dst.values()} | {x for sp in defn.dst.values() for x in sp.get("between", ())}
        if on not in movers and on not in dests and on not in refs:  # only looked at: anywhere visible on the node
            pts = vis
        idx = rng.permutation(len(pts))
        for i in idx[:300]:
            xy = pts[i] + rng.uniform(-0.009, 0.009, 2)
            if inside(node, xy, fr) and free(xy, fr, tgt):
                placed.append((np.asarray(xy, float), fr, tgt))
                ep["objects"][k] = {"xy": [round(float(xy[0]), 4), round(float(xy[1]), 4)], "node": node["id"], "fr": fr}
                return
        raise Fail(f"no room for {on}")

    for on in order:
        place_obj(on, defn.objs[on])
    # side pairs: which of two is left / right
    for nd in defn.needs:
        if nd.startswith("side_pair:"):
            _, a, b = nd.split(":")
            ya, yb = ep["objects"][chosen[a]]["xy"][1], ep["objects"][chosen[b]]["xy"][1]
            if abs(ya - yb) < 0.08:
                raise Fail("side pair too close in y")
            ep.setdefault("words", {})[f"{a}side"] = "left" if ya > yb else "right"
    # destinations
    spots, surfs = {}, {}
    main_pts = main[1]

    def usable_spot(xy, fr, target_on_main=True):
        if not inside(main[0], xy, fr):
            return False
        if np.min(np.hypot(*(main_pts - np.asarray(xy)).T)) > 0.015:
            return False
        movers = {chosen[a] for a, _ in defn.steps}
        ex = [(np.asarray(v["xy"]), v["fr"], False) for kk, v in ep["objects"].items() if kk in movers]
        others = [(p, f, t) for (p, f, t) in placed if not any(np.allclose(p, e[0]) for e in ex)]
        for (p, f, t) in others:
            if np.hypot(*(np.asarray(xy) - p)) < fr + f + 0.02 or not finger_clear(np.asarray(xy) - p, f):
                return False
        for q in spots.values():
            if np.hypot(*(np.asarray(xy) - np.asarray(q["xy"]))) < 2 * SPOT_R + 0.02:
                return False
        return True

    def mover_of(dname):
        return next(a for a, d in defn.steps if d == dname)

    for dname, spec in defn.dst.items():
        mv = pool[chosen[mover_of(dname)]]
        fr = float(mv["footprint_r"])
        if spec["type"] == "spot":
            xy = None
            if "rel" in spec:
                ref = ep["objects"][chosen[spec["ref"]]]
                off = rel_offset(spec["rel"], spec.get("gap", float(rng.uniform(0.02, 0.05))), fr, ref["fr"])
                xy = np.asarray(ref["xy"]) + off
            elif "between" in spec:
                a, b = (ep["objects"][chosen[x]] for x in spec["between"])
                if np.hypot(*(np.asarray(a["xy"]) - b["xy"])) < a["fr"] + b["fr"] + 2 * fr + 0.06:
                    raise Fail("refs too close for between")
                xy = (np.asarray(a["xy"]) + np.asarray(b["xy"])) / 2
            elif "line" in spec:
                axis, i, n = spec["line"]
                key = "line_" + axis
                if key not in ep:
                    sp = spec.get("spacing", float(rng.uniform(0.11, 0.14)))
                    ep[key] = None
                    for ci in rng.permutation(len(main_pts))[:80]:
                        c = main_pts[ci]
                        pts = [c + (np.array([0.0, -(j - (n - 1) / 2) * sp]) if axis == "y"
                                    else np.array([(j - (n - 1) / 2) * sp, 0.0])) for j in range(n)]
                        if all(np.min(np.hypot(*(main_pts - q).T)) <= 0.015 for q in pts):
                            ep[key] = (c, sp)
                            break
                    if ep[key] is None:
                        raise Fail("no line fits")
                c, sp = ep[key]
                t = (i - (n - 1) / 2) * sp
                xy = c + (np.array([0.0, -t]) if axis == "y" else np.array([t, 0.0]))  # left first (+y), front first (-x)
            elif "corner" in spec:
                P = main_pts
                sc = {"front_left": P[:, 1] - P[:, 0], "back_right": P[:, 0] - P[:, 1], "front_right": -P[:, 1] - P[:, 0],
                      "back_left": P[:, 0] + P[:, 1], "centre": None}[spec["corner"]]
                if sc is None:
                    xy = P.mean(axis=0)
                    xy = P[np.argmin(np.hypot(*(P - xy).T))]
                else:
                    top = np.argsort(-sc)[: max(3, len(P) // 10)]
                    xy = P[top[int(rng.integers(len(top)))]]
            elif "off_node" in spec:
                c = [p for p in main_pts]
                rng.shuffle(c)
                xy = next((p for p in c if usable_spot(p, fr)), None)
                if xy is None:
                    raise Fail("no off-node spot")
            elif "at_obj" in spec:
                xy = np.asarray(ep["objects"][chosen[spec["at_obj"]]]["xy"])
            if xy is None or not usable_spot(xy, fr):
                raise Fail(f"spot {dname} unusable")
            spots[dname] = {"xy": [round(float(xy[0]), 4), round(float(xy[1]), 4)], "top": mz}
        else:  # node destination (virtual surface)
            kinds = spec["kinds"]
            c = [v for v in nodes.values() if v[0]["kind"] in kinds and v[0]["id"] != main[0]["id"]]
            if spec.get("higher"):
                c = [v for v in c if v[0]["top_z"] > mz + 0.03]
            if spec.get("lower"):
                c = [v for v in c if v[0]["top_z"] < mz - 0.03]
            if spec.get("second") and second is not None:
                c = [second] if second[0]["kind"] in kinds else []
            if spec.get("not_obj_node"):
                nid0 = ep["objects"][chosen[spec["not_obj_node"]]]["node"]
                c = [v for v in c if v[0]["id"] != nid0]
            if spec.get("of_obj"):
                nid = ep["objects"][chosen[spec["of_obj"]]]["node"]
                c = [v for v in c if v[0]["id"] == nid]
            if spec.get("lower_than_obj"):
                oz = nodes[ep["objects"][chosen[spec["lower_than_obj"]]]["node"]][0]["top_z"]
                c = [v for v in nodes.values() if v[0]["kind"] in kinds and v[0]["top_z"] < oz - 0.03]
            used = {s["node"] for s in surfs.values()}
            c = [v for v in c if v[0]["id"] not in used]
            if spec.get("side_of_two"):
                if len(c) < 2:
                    raise Fail("need two nodes for a side choice")
                two = [c[int(i)] for i in rng.choice(len(c), 2, replace=False)]
                ys = [float(np.mean(v[1][:, 1])) for v in two]
                if abs(ys[0] - ys[1]) < 0.08:
                    raise Fail("side nodes too close in y")
                c = [two[0]]
                ep.setdefault("words", {})[f"{dname}side"] = "left" if ys[0] > ys[1] else "right"
            if not c:
                raise Fail(f"no node for {dname}")
            node, pts, _ = c[int(rng.integers(len(c)))]
            pts = [p for p in pts if inside(node, p, fr)]
            rng.shuffle(pts)
            xy = next((p for p in pts if free(p, fr, True)), None)
            if xy is None:
                raise Fail(f"no free point on {dname}")
            (x0, x1), (y0, y1) = node["box"]
            half = float(np.clip(min(x1 - x0, y1 - y0) / 2 - fr, 0.03, 0.08))
            surfs[dname] = {"node": node["id"], "kind": node["kind"], "top": node["top_z"],
                            "xy": [round(float(xy[0]), 4), round(float(xy[1]), 4)], "half": round(half, 3),
                            "name": surf_name(node)}
            if spec.get("shared"):
                pass
    # carry paths: the straight move from each mover to its destination stays clear of tall parts (pilot 1)
    for a, d in defn.steps:
        src = np.asarray(ep["objects"][chosen[a]]["xy"], float)
        dst = spots.get(d, surfs.get(d, {})).get("xy") if d in spots or d in surfs else ep["objects"][chosen[d]]["xy"]
        top = max(mz, nodes[ep["objects"][chosen[a]]["node"]][0]["top_z"])
        for box in S9.tall_parts(scene, top):
            if S9.seg_box_dist(S9.s_of(src, scene["yaw"]), S9.s_of(dst, scene["yaw"]), box) < 0.08:
                raise Fail("carry path near a tall part")
    if len(spots) > MAX_SPOTS or len(surfs) > MAX_SURF:
        raise Fail("too many destinations")
    # shared node destinations: steps into the same surface get side-by-side offsets
    offs = {}
    for dname in surfs:
        users = [a for a, d in defn.steps if d == dname]
        if len(users) > 1:
            for j, a in enumerate(users):
                offs[(a, dname)] = [0.0, round(0.05 * (1 - 2 * j), 3)]
    # ids: objects keep their catalog ids; spots s9_i; surfaces v9_i
    sid = {d: f"s9_{i}" for i, d in enumerate(sorted(spots))}
    vid = {d: f"v9_{i}" for i, d in enumerate(sorted(surfs))}
    steps = []
    for a, d in defn.steps:
        place = chosen.get(d) or sid.get(d) or vid.get(d)
        off = offs.get((a, d))
        if place is None:
            raise Fail(f"unresolved destination {d}")
        if d in defn.objs and defn.objs[d]["role"] == "container" and sum(1 for _, x in defn.steps if x == d) > 1:
            j = [x for x, y in defn.steps if y == d].index(a)
            off = [0.0, round(0.04 * (1 - 2 * j), 3)]
        steps.append([chosen[a], place, off])
    names = {k: name_of(pool[k]) for k in chosen.values()}
    fmt = {}
    for on, k in chosen.items():
        fmt[on] = names[k]
        fmt[on + "col"] = pool[k].get("colour", "")
        fmt[on + "noun"] = " ".join(w for w in names[k].split() if w != pool[k].get("colour"))
        nd = ep["objects"][k]["node"]
        fmt[on + "surf"] = "upper " + surf_name(nodes[nd][0]) if nodes[nd][0]["top_z"] > mz + 0.03 else \
            ("lower " + surf_name(nodes[nd][0]) if nodes[nd][0]["top_z"] < mz - 0.03 else surf_name(nodes[nd][0]))
    for d, s in surfs.items():
        movers_d = [a for a, dd in defn.steps if dd == d]  # height words relative to where the object starts
        ref_z = nodes[ep["objects"][chosen[movers_d[0]]]["node"]][0]["top_z"] if movers_d else mz
        fmt[d] = ("upper " if s["top"] > ref_z + 0.03 else "lower " if s["top"] < ref_z - 0.03 else "") + s["name"]
    for w, v in ep.get("words", {}).items():
        fmt[w] = v
    fmt["Msurf"] = surf_name(main[0])
    ti = int(rng.integers(len(defn.templates)))
    try:
        instr = defn.templates[ti].format(**fmt)
    except KeyError as ex:
        raise Fail(f"template key {ex}")
    instr = instr[0].upper() + instr[1:]
    ep.update(steps=steps, spots={sid[d]: v for d, v in spots.items()}, surfaces={vid[d]: v for d, v in surfs.items()},
              roles={on: k for on, k in chosen.items()}, names=names, instruction=instr, template=ti,
              judge=dict(defn.judge), lift=scene["lift"])
    for d, v in surfs.items():
        v["rule_text"] = f"on the {fmt[d]} (standing on it, its centre within {v['half'] * 100:.0f} cm of the drop point)"
    for d, v in spots.items():
        v["rule_text"] = ("at the spot the instruction describes on the " + fmt["Msurf"] +
                          f" (its centre within {SPOT_R * 100:.0f} cm of that point, standing on the surface)")
    return ep


def definition_count() -> dict:
    from collections import Counter
    return dict(Counter(d.family for d in DEFS.values()))


def add_clutter(ep: dict, scene: dict, pool: dict, seed: int, rm, n_range=(2, 6)) -> dict:
    """Distractors (pool clutter + unused targets) on visible free points of the flat nodes, clear of every task
    object, spot and surface destination (>= footprints + 3 cm); names never clash with the task objects'.
    -> {id: {xy, node, fr, yaw}} (also stored in ep["clutter"])."""
    rng = np.random.default_rng([int(seed), 913])
    nodes = _nodes(scene, rm)
    flats = [v for v in nodes.values() if v[0]["kind"] in ("top", "zone", "seat")]
    used = set(ep["objects"])
    taken = set(ep["names"].values())
    busy = [(np.asarray(o["xy"], float), o["fr"]) for o in ep["objects"].values()]
    busy += [(np.asarray(s["xy"], float), 0.05) for s in ep["spots"].values()]
    busy += [(np.asarray(s["xy"], float), 0.07) for s in ep["surfaces"].values()]
    cand = [k for k, r in pool.items() if k not in used and r.get("role9") in ("clutter", "target")]
    rng.shuffle(cand)
    want = int(rng.integers(n_range[0], n_range[1] + 1))
    out = {}
    for k in cand:
        if len(out) >= want or not flats:
            break
        r = pool[k]
        nm = name_of(r)
        if not nm or any(clash(nm, t) for t in taken) or float(r["height"]) > CLUTTER_H_MAX:
            continue
        fr = float(r["footprint_r"])
        node, _, vis = flats[int(rng.integers(len(flats)))]
        if len(vis) == 0:
            continue
        for i in rng.permutation(len(vis))[:60]:
            xy = vis[i]
            s = S9.s_of(xy, scene["yaw"])
            (x0, x1), (y0, y1) = node["box"]
            if not (x0 + fr <= s[0] <= x1 - fr and y0 + fr <= s[1] <= y1 - fr):
                continue
            if all(np.hypot(*(xy - p)) >= fr + f + 0.03 and finger_clear(xy - p, fr)
                   for p, f in busy):
                out[k] = {"xy": [round(float(xy[0]), 4), round(float(xy[1]), 4)], "node": node["id"], "fr": fr,
                          "yaw": round(float(rng.uniform(-math.pi, math.pi)), 4)}
                busy.append((np.asarray(xy, float), fr))
                taken.add(nm)
                break
    ep["clutter"] = out
    return out
