"""R7 cycle 14 N3: a --seeds that selects no episode fails (rc != 0) like a missing --data (canon §79 N5, §80), and
harvest.sim.determinism refuses a bad seed before it creates the output folder."""
import pytest

from harvest.eval import common, e05, rd


def test_load_episodes_refuses_seeds_selecting_nothing(dev_dirs):
    with pytest.raises(SystemExit, match="no episode selected"):
        common.load_episodes([dev_dirs["P0"], dev_dirs["P1"]], "dev", seeds={7})


def test_load_episodes_keeps_a_selection_found_in_one_folder_only(dev_dirs):
    eps = common.load_episodes([dev_dirs["P0"], dev_dirs["P1"]], "dev", seeds={2})
    assert [(e["kind"], e["seed"]) for e in eps] == [("P0", 2)]


def test_e05_seeds_selecting_nothing_fails(dev_dirs, tmp_path, monkeypatch):
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "qid.json"))
    with pytest.raises(SystemExit):
        e05.main(["--model", "mock", "--out", str(tmp_path / "o"), "--data", dev_dirs["P0"], "--split", "dev",
                  "--seeds", "7"])


def test_rd_seeds_selecting_nothing_fails(dev_dirs, tmp_path):
    with pytest.raises(SystemExit):
        rd.main(["--model", "mock", "--out", str(tmp_path / "o"), "--variants", f"standard={dev_dirs['P0']}",
                 "--split", "dev", "--seeds", "9"])


@pytest.mark.parametrize("argv", [["fresh", "--seed", "500"], ["fresh"], ["fresh", "--seed", "1000"],
                                  ["history", "--seeds", "3,500"], ["history", "--first", "549"],
                                  ["history", "--partial", "2000"]])
def test_determinism_refuses_bad_seeds_before_creating_the_output_folder(tmp_path, argv):
    from harvest.sim import determinism
    out = tmp_path / "det"
    with pytest.raises((SystemExit, ValueError)):
        determinism.main(argv + ["--out", str(out)])
    assert not out.exists()


def test_determinism_compare_still_creates_its_folder(tmp_path):
    from harvest.sim import determinism
    out = tmp_path / "det"
    determinism.main(["compare", "--out", str(out)])
    assert (out / "matrix.json").exists()
