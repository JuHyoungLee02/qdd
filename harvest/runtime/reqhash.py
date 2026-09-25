"""Request hashes for the closed-loop logs (canon §42: per-trial sidecar "요청 해시"; §28 A6: image byte hashes).

request_hash(payload, images) = sha256 of the canonical JSON (sorted keys, compact separators, UTF-8) of
{"payload": payload, "images": {name: image_sha256}} -- key order, dict insertion order and array identity do not
change it; any change of the text, the options, the model-facing parameters or one pixel does. Image digests:
bytes (the JPEG actually sent) -> sha256 of the bytes; an array (a raw frame) -> sha256 of "shape|dtype|" + its
C-contiguous bytes (the runtime JPEG-encodes frames deterministically, so the raw frame identifies the sent bytes).
"""
from __future__ import annotations

import hashlib
import json

import numpy as np


def image_sha256(img) -> str:
    if isinstance(img, (bytes, bytearray, memoryview)):
        return hashlib.sha256(bytes(img)).hexdigest()
    a = np.ascontiguousarray(img)
    h = hashlib.sha256(f"{a.shape}|{a.dtype}|".encode())
    h.update(a.tobytes())
    return h.hexdigest()


def request_hash(payload: dict, images: dict | None = None) -> tuple[str, dict]:
    """(sha256 hex of the canonical request, {image name: sha256})."""
    h, ims, _ = request_body(payload, images)
    return h, ims


def request_body(payload: dict, images: dict | None = None) -> tuple[str, dict, bytes]:
    """request_hash + the canonical body itself (UTF-8): the raw-request blob whose sha256 is the request hash
    (canon §28 A6 / E §1.6 "요청 원문", images by byte hash; canon §77)."""
    ims = {str(k): image_sha256(v) for k, v in sorted((images or {}).items()) if v is not None}
    body = json.dumps({"payload": payload, "images": ims}, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      default=_default).encode("utf-8")
    return hashlib.sha256(body).hexdigest(), ims, body


def json_blob(obj) -> tuple[str, bytes]:
    """(sha256, canonical JSON bytes) of a raw response (same canonical form as request_body)."""
    b = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_default).encode("utf-8")
    return hashlib.sha256(b).hexdigest(), b


def _default(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.floating, np.integer, np.bool_)):
        return x.item()
    if isinstance(x, (set, frozenset, tuple)):
        return sorted(x) if isinstance(x, (set, frozenset)) else list(x)
    return str(x)
