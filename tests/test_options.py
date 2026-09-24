from harvest.options import Option, layer, to_option_key, variant

BASE = [Option("up", "up", "Move up."), Option("down", "down", "Move down."),
        Option("hold", "hold", "Keep position."), Option("NONE_ESCALATE", "NONE_ESCALATE", "None fits.")]
ALL = ["A0", "A1", "A2", "A3", "A4"]


def test_answer_maps_back_to_option_key_for_all_variants():
    for v in ALL:
        shown = variant(BASE, v, seed=7)
        for o in shown:
            assert to_option_key(shown, o.name) == o.key


def test_none_escalate_fixed_last_everywhere():
    for v in ALL:
        shown = variant(BASE, v, seed=1)
        assert shown[-1].key == shown[-1].name == "NONE_ESCALATE"


def test_a3_misaligns_names_but_keeps_desc_key_pairs():
    shown = variant(BASE, "A3", seed=0)
    assert [o.key for o in shown] == ["up", "down", "hold", "NONE_ESCALATE"]
    assert [o.desc for o in shown] == [o.desc for o in BASE]
    assert [o.name for o in shown[:3]] == ["down", "hold", "up"]


def test_a4_rotates_order_only():
    shown = variant(BASE, "A4", seed=0)
    assert [o.key for o in shown[:3]] == ["down", "hold", "up"]
    assert all(o.name == o.key for o in shown)


def test_a1_neutral_names_unique():
    shown = variant(BASE, "A1", seed=0)
    assert [o.name for o in shown[:3]] == ["opt_a", "opt_b", "opt_c"]


def test_a2_deterministic_by_seed_and_unique():
    names = [o.name for o in variant(BASE, "A2", 3)]
    assert names == [o.name for o in variant(BASE, "A2", 3)]
    assert len(set(names)) == len(names)


def test_layers():
    assert layer(2, "choice") == "L2" and layer(0, "noul") == "L2"
    assert layer(4, "choice") == "L3_6" and layer(10, "choice") == "L7_17"
