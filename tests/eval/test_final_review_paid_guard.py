"""Plan 2026-09-26 final whole-branch review (controller ruling FF): I3 paid guard gaps (user-log 114) in run_r5 and
the closed-loop worker, M6 the missing-hz guard of a motion-trained checkpoint. No network, no Isaac, no paid call."""
import json

import pytest

import harvest.clients.astra as astra_mod
from harvest.eval import closed as CL
from harvest.runtime import run_r5 as R5


class _Boom:
    def __init__(self, *a, **k):
        raise AssertionError("a real AstraClient was built")


def test_run_r5_defaults_to_the_mock_astra():
    assert R5._args(["--out", "x"]).astra == "mock"
    assert R5._args(["--out", "x"]).approval == ""


def test_run_r5_refuses_a_real_client_without_approval(tmp_path, monkeypatch):
    tok = tmp_path / "tok"
    tok.write_text("sk-test")
    monkeypatch.setattr(astra_mod, "AstraClient", _Boom)
    for choice in ("auto", "api"):
        with pytest.raises(SystemExit, match="approval"):
            R5.build_astra(choice, "", str(tok))
    astra, mode = R5.build_astra("mock", "", str(tok))
    assert mode == "mock" and astra.model.startswith("mock:")
    astra, mode = R5.build_astra("auto", "", str(tmp_path / "missing"))  # no token: the ack mock, as before
    assert mode == "mock"


def test_run_r5_builds_the_real_client_only_with_approval(tmp_path, monkeypatch):
    tok = tmp_path / "tok"
    tok.write_text("sk-test")
    built = []
    monkeypatch.setattr(astra_mod, "AstraClient", lambda *a, **k: built.append(a) or "client")
    assert R5.build_astra("api", "user approval: test", str(tok)) == ("client", "api")
    assert built and built[0][0] == "sk-test"


def test_closed_worker_coupling_arm_builds_no_throwaway_client(monkeypatch):
    """I3: with a coupling arm the stream client is the only Astra client (the heartbeat client that stream_client
    used to overwrite is never built)."""
    monkeypatch.setattr(astra_mod, "AstraClient", _Boom)
    monkeypatch.setattr(CL.os.path, "exists", lambda p: True)
    spec = {"astra": "api", "couple_upper": "astra", "approval": ""}
    monkeypatch.setattr("harvest.eval.couple.stream_client", lambda s: ("stream", "api"))
    assert CL.worker_astra(spec, "serial", ["off", "serial"]) == ("stream", "api")
    assert CL.worker_astra(spec, "off", ["off", "serial"]) == (None, "none")  # A0 = VLA alone


def test_closed_worker_heartbeat_needs_approval(monkeypatch):
    monkeypatch.setattr(astra_mod, "AstraClient", _Boom)
    monkeypatch.setattr(CL.os.path, "exists", lambda p: True)
    for choice in ("auto", "api"):
        with pytest.raises(SystemExit, match="approval"):
            CL.worker_astra({"astra": choice, "approval": ""}, "off", ["off"])
    astra, mode = CL.worker_astra({"astra": "mock", "approval": ""}, "off", ["off"])
    assert mode == "mock"


def test_closed_run_refuses_astra_api_without_approval(tmp_path):
    a = CL._args(["--model", "mock", "--out", str(tmp_path), "--astra", "api"])
    with pytest.raises(SystemExit, match="approval"):
        CL.run(a)


def test_motion_trained_checkpoint_without_hz_is_refused(tmp_path):
    """M6: stageb.json carries a motion record but no 'hz' -> motion_config's missing-rate guard fires (no silent
    30 Hz default)."""
    from harvest.runtime.motion import MOTION_VER
    sb = {"prompt_config": {"motion": {"version": MOTION_VER, "arm_speed": [0.01, 0.05], "grip_rate": 0.01}}}
    (tmp_path / "stageb.json").write_text(json.dumps(sb))
    with pytest.raises(ValueError, match="hz"):
        CL.stageb_motion(str(tmp_path))
    (tmp_path / "stageb.json").write_text(json.dumps({**sb, "hz": 10}))
    bins, win = CL.stageb_motion(str(tmp_path))
    assert bins["version"] == MOTION_VER and win == pytest.approx(0.1)
    (tmp_path / "stageb.json").write_text(json.dumps({"prompt_config": {}}))
    assert CL.stageb_motion(str(tmp_path)) == (None, 0.1)
