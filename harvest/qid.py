"""question_id@vN (canon §28 J1): hash of wording + option_key order + descriptions + display + legend + serializer.

vN is the registry ordinal of the content hash, so any change to wording, options, display strings
(spaces included) or serializer version yields a new id.
"""
import hashlib
import json
import os
import pathlib

from .serialize import SERIALIZER_VERSION, canonicalize


def _registry() -> pathlib.Path:
    return pathlib.Path(os.environ.get("HARVEST_QID_REGISTRY", "docs/stage3/qid_registry.json"))


def question_id(text, option_keys, option_desc, display, legend):
    payload = json.dumps({"q": canonicalize(text), "keys": list(option_keys),
                          "desc": {k: canonicalize(option_desc[k]) for k in option_keys},
                          "display": {k: display[k] for k in option_keys},  # exact, not canonicalized
                          "legend": legend, "ser": SERIALIZER_VERSION}, sort_keys=True, ensure_ascii=False)
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    reg = _registry()
    data = json.loads(reg.read_text(encoding="utf-8")) if reg.exists() else {}
    if h not in data:
        data[h] = len(data) + 1
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return f"{h}@v{data[h]}"
