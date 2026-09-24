"""DC1 gate: implementation constants match the canonical protocol text."""
import pathlib
import re

CANON = pathlib.Path(__file__).parents[1].joinpath("docs/design/E-first-experiments.md").read_text(encoding="utf-8")


def test_endpoint_and_model_match_canon():
    from harvest.config import CFG
    assert CFG.jev_url in CANON and f'"model": "{CFG.jev_model}"' in CANON


def test_question_key_scheme_in_canon():
    assert re.search(r"`ds<번호>\.<질문>` / `mon\.progress` / `mon\.t3b`", CANON)


def test_dir_split_option_counts():
    # M3 §4.2 (D4 C-6): dir_xy = 8 + none_xy + NONE_ESCALATE = 10, dir_z = 4
    from harvest.jevcall import DIR_XY, DIR_Z
    assert len(DIR_XY) == 10 and len(DIR_Z) == 4
    assert DIR_XY[-1].key == DIR_Z[-1].key == "NONE_ESCALATE"
