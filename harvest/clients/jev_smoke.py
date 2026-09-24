"""One live Jev call to confirm the real response shape (plan T5 Step 6). Needs HARVEST_JEV_TOKEN_FILE."""
import json
import os
import pathlib

from harvest.clients.jev import JevClient
from harvest.jevcall import DIR_Z, build_choice, build_request

tok = pathlib.Path(os.environ["HARVEST_JEV_TOKEN_FILE"]).read_text().strip()
k, q = build_choice("ds1.dir_z", "The mug is 3 cm above the tray. Which vertical motion places it?", DIR_Z)
r = JevClient(tok).call(build_request("objects: o3 mug above o5 tray", [(k, q)]), {"experiment": "smoke"})
out = pathlib.Path(os.environ.get("HARVEST_SMOKE_OUT", "D:/tools/scratch_qdd/jev_smoke.json"))
out.write_text(json.dumps({"status": r.http_status, "latency": r.t_done - r.t_send,
                           "resp": r.raw_response, "err": r.error}, indent=1))
print(r.http_status, round(r.t_done - r.t_send, 3), r.error)
