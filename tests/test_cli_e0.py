import json

from harvest.clients.jev import CallRecord
from harvest.cli_e0 import main


class FakeClient:
    def call(self, req, meta):
        return CallRecord(t_send=0.0, t_first_byte=0.2, t_done=0.25, http_status=200, meta=meta)


def test_main_writes_session_and_summary(tmp_path):
    rc = main(["--slot", "KST02", "--site", "pod", "--out", str(tmp_path), "--quick"],
              client_factory=lambda: FakeClient(), curl_fn=lambda: {"total": 0.1})
    assert rc == 0
    summ = json.loads(next(tmp_path.glob("*_summary.json")).read_text(encoding="utf-8"))
    assert summ["case"] == "b" and summ["N_max"] >= 1
