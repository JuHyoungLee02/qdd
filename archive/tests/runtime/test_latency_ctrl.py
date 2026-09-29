import pytest

from harvest.runtime.latency_ctrl import LatencyChargingController


def test_stub_raises_until_implemented():
    with pytest.raises(NotImplementedError):
        LatencyChargingController(100.0).next_action(None, None, 0, {})


@pytest.mark.skip(reason="TODO(P3): a 0.25 s act() at 100 Hz must prepend ceil(0.25*100)=25 hold actions (canon §42)")
def test_latency_is_charged_as_hold_actions():
    raise AssertionError
