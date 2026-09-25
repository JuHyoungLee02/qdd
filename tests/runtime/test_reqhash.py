"""Request hashes for the closed-loop logs (canon §42 sidecar: request hash; §28 A6: image byte hashes)."""
import numpy as np

from harvest.runtime.reqhash import image_sha256, request_hash


def test_request_hash_is_canonical_and_covers_images():
    img = np.zeros((4, 5, 3), np.uint8)
    h1, ih1 = request_hash({"a": 1, "b": [1, 2], "api": "decide"}, {"cam_head": img})
    h2, ih2 = request_hash({"api": "decide", "b": [1, 2], "a": 1}, {"cam_head": img.copy()})
    assert h1 == h2 and ih1 == ih2 and len(h1) == 64 and set(ih1) == {"cam_head"}
    img2 = img.copy()
    img2[0, 0, 0] = 1  # one pixel changes the request
    assert request_hash({"a": 1, "b": [1, 2], "api": "decide"}, {"cam_head": img2})[0] != h1
    assert request_hash({"a": 2, "b": [1, 2], "api": "decide"}, {"cam_head": img})[0] != h1
    assert request_hash({"a": 1, "b": [1, 2], "api": "decide"}, {})[0] != h1  # no image != with image


def test_image_hash_of_bytes_and_arrays():
    b = b"\xff\xd8jpeg"
    import hashlib
    assert image_sha256(b) == hashlib.sha256(b).hexdigest()
    a = np.arange(24, dtype=np.uint8).reshape(2, 4, 3)
    assert image_sha256(a) != image_sha256(a.reshape(4, 2, 3))  # the shape is part of the digest
    assert image_sha256(a) == image_sha256(np.ascontiguousarray(a))
