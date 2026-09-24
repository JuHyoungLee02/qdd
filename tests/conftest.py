"""Per-process pytest basetemp so concurrent runs (several agents) do not wipe each other's tmp dirs.

On Windows the base stays on D: (user rule: never write to C:). On the pod, scripts pass --basetemp under /data.
"""
import os
import sys

import pytest

_LOCAL_BASE = "D:/tools/scratch_qdd/pytest_tmp"


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if sys.platform != "win32":
        return
    bt = config.option.basetemp
    if bt is None or str(bt).replace("\\", "/").rstrip("/") == _LOCAL_BASE:
        config.option.basetemp = f"{_LOCAL_BASE}/p{os.getpid()}"
