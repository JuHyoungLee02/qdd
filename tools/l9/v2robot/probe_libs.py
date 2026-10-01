"""Which helper libraries the Isaac python sees (cuRobo pylib on PYTHONPATH)."""
import importlib

for m in ("trimesh", "yourdfpy", "scipy", "collada", "curobo", "warp", "torch", "lxml", "yaml"):
    try:
        mod = importlib.import_module(m)
        print(m, getattr(mod, "__version__", "?"), getattr(mod, "__file__", ""))
    except Exception as e:  # noqa: BLE001
        print(m, "MISSING", e)
