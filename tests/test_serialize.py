from harvest.serialize import SERIALIZER_VERSION, canonicalize, serialize_state

STAGE = {"id": "S2", "text": "place mug o3 on tray o5", "exit": "on(o3,o5)",
         "invariants": ["holding(o3)"], "elapsed": "normal"}


def test_facts_true_plus_named_false_sorted_and_unknown():
    s = serialize_state("f1287 (t=42.90s)", "c7", STAGE,
                        "gripper=closed_holding(o3) wrist_force=light arm=moving",
                        [("o3", "mug red", "held_by_gripper", "upright"), ("o5", "tray blue", "on(table)", "clear=yes")],
                        {"near(o3,o5)": True, "on(o3,o5)": False, "above(o3,o5)": False, "in_contact(o3,o5)": None},
                        {"on(o3,o5)", "in_contact(o3,o5)"},
                        [(-0.4, "aligned_x(o3,o5)", "no", "yes")])
    facts = [l for l in s.split("\n") if l.startswith("facts:")][0]
    assert facts == "facts: in_contact(o3,o5)=unknown near(o3,o5)=yes on(o3,o5)=no"
    assert "above(o3,o5)" not in s
    assert s.startswith("t_state: f1287 (t=42.90s)  contract: c7  stage: S2")
    assert SERIALIZER_VERSION == "ser-A-min-1"


def test_changes_capped_at_8_and_3s():
    ch = [(-0.1 * i, f"p{i}", "no", "yes") for i in range(40)]
    s = serialize_state("t", "c", {"id": "S1", "text": "x", "exit": "e", "invariants": [], "elapsed": "normal"},
                        "r", [], {}, set(), ch)
    items = s.split("changes (last 3s): ")[1].split("; ")
    assert len(items) == 8


def test_canonicalize_idempotent_and_crlf():
    a = "x  y \r\nz\t\n"
    assert canonicalize(a) == canonicalize(canonicalize(a)) == "x y\nz"
