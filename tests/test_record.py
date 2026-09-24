import json

from harvest.clients.jev import CallRecord, JevClient
from harvest.record import Recorder


def test_jsonl_roundtrip_has_no_auth_header(tmp_path):
    rec = CallRecord(call_id="c1", raw_request={"model": "jev-1.13.0"}, raw_response={})
    p = tmp_path / "x.jsonl"
    with Recorder(p) as w:
        w.write(rec)
        w.write(rec)
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["call_id"] == "c1"
    assert "authorization" not in lines[0].lower() and "bearer" not in lines[0].lower()
