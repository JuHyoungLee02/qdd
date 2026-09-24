"""Per-process pytest basetemp so concurrent runs (several agents) do not wipe each other's tmp dirs.

On Windows the base stays on D: (user rule: never write to C:). On the pod, scripts pass --basetemp under /data.
"""
import os
import sys

import pytest

_LOCAL_BASE = "D:/tools/scratch_qdd/pytest_tmp"

if sys.platform == "win32":
    # keep torch/inductor caches and tempfile off C: (user rule); must run before torch/tempfile are used
    _SCRATCH = "D:/tools/scratch_qdd/tmp_local"
    os.makedirs(_SCRATCH, exist_ok=True)
    for _k in ("TMP", "TEMP", "TMPDIR"):
        os.environ[_k] = _SCRATCH
    os.environ.setdefault("TORCHINDUCTOR_CACHE_DIR", "D:/tools/scratch_qdd/torchinductor")
    os.environ.setdefault("TRITON_CACHE_DIR", "D:/tools/scratch_qdd/triton")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if sys.platform != "win32":
        return
    bt = config.option.basetemp
    if bt is None or str(bt).replace("\\", "/").rstrip("/") == _LOCAL_BASE:
        config.option.basetemp = f"{_LOCAL_BASE}/p{os.getpid()}"
