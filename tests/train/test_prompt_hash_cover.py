"""ser-A-min-3 fix round 1 item 3: every source that shapes the DecCall / stage-B prompt text is in the checkpoint's
prompt_config files_sha -- the fused dir_xy / mag_coarse wording (labels_v2 constants, sim.planner.MAG_BINS), the
segment / stage text (sim.snapshot PHASE_ORDER, stage table, object names) and the S-E2E items (se2e_data). Constants
of large modules are hashed by value ("path.py:NAME"), so an unrelated planner edit does not refuse checkpoints."""
import pytest

from harvest.train import stagea_train as A


def test_prompt_files_cover_the_text_sources():
    for p in ("harvest/labels_v2.py", "harvest/sim/planner.py:MAG_BINS", "harvest/sim/snapshot.py:PHASE_ORDER",
              "harvest/sim/snapshot.py:_S1", "harvest/sim/snapshot.py:SPEC_NAMES", "harvest/intent.py"):
        assert p in A.PROMPT_FILES
    fs = A.file_sha(A.PROMPT_FILES)
    assert set(fs) == set(A.PROMPT_FILES) and all(len(v) == 12 for v in fs.values())


def test_constant_entries_hash_the_value(monkeypatch):
    from harvest.sim import planner, snapshot
    key = "harvest/sim/planner.py:MAG_BINS"
    h0 = A.file_sha((key,))[key]
    assert A.file_sha((key,))[key] == h0  # deterministic
    monkeypatch.setattr(planner, "MAG_BINS", planner.MAG_BINS[:-1])
    assert A.file_sha((key,))[key] != h0
    k2 = "harvest/sim/snapshot.py:PHASE_ORDER"
    h1 = A.file_sha((k2,))[k2]
    monkeypatch.setattr(snapshot, "PHASE_ORDER", tuple(reversed(snapshot.PHASE_ORDER)))
    assert A.file_sha((k2,))[k2] != h1
    with pytest.raises(AttributeError):
        A.file_sha(("harvest/sim/planner.py:NO_SUCH_NAME",))


def test_serializer_of_reads_constant_entries():
    from harvest.serialize import SERIALIZER_VERSION
    pc = {"files_sha": A.file_sha(A.PROMPT_FILES)}  # a config without the serializer field: files decide
    assert A.serializer_of(pc) == SERIALIZER_VERSION
    bad = dict(pc["files_sha"], **{"harvest/sim/planner.py:MAG_BINS": "000000000000"})
    assert A.serializer_of({"files_sha": bad}).startswith("older than")


def test_stage_b_files_include_the_s_e2e_item_builder():
    T = pytest.importorskip("harvest.train.stageb_train", exc_type=ImportError)  # imports torch
    assert "harvest/train/se2e_data.py" in T.PROMPT_FILES_B
