"""List the files (and sizes) of the HF dataset JingkunAn/RefSpatial, and print the licence field of its card.
usage: python refsp_list.py"""
import os

from huggingface_hub import HfApi

tok = open("/data/.hf_token").read().strip() if os.path.exists("/data/.hf_token") else None
api = HfApi(token=tok)
info = api.dataset_info("JingkunAn/RefSpatial", files_metadata=True)
print("LICENSE", (info.card_data or {}).get("license") if info.card_data else None)
tot = 0
for s in info.siblings:
    sz = s.size or 0
    tot += sz
    print(f"{sz / 1e9:8.2f} GB  {s.rfilename}")
print("TOTAL_GB", round(tot / 1e9, 1))
for rid in ("allenai/pixmo-points",):
    try:
        i2 = api.dataset_info(rid)
        print("PIXMO_LICENSE", (i2.card_data or {}).get("license") if i2.card_data else None)
    except Exception as e:  # noqa: BLE001
        print("PIXMO_ERR", type(e).__name__)
