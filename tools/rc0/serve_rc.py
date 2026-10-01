"""E-RC0: serve the official pi0.5 RoboCasa365 checkpoint with robocasa-benchmark/openpi's serve_policy.py, unchanged
except that the training-data directories of the config (pi05_pretrain_human300) are dropped: building the data config
would otherwise read every training dataset's meta/stats.json (not downloaded). Serving loads the norm stats from the
checkpoint's assets folder anyway (policy_config.create_trained_policy, asset_id None branch), so the policy is the same.
usage (from the openpi checkout): python serve_rc.py --port P policy:checkpoint --policy.config pi05_pretrain_human300
       --policy.dir <ckpt>"""
import dataclasses
import runpy
import sys

import openpi.training.config as C

name = "pi05_pretrain_human300"
cfg = C._CONFIGS_DICT[name]
C._CONFIGS_DICT[name] = dataclasses.replace(cfg, data=dataclasses.replace(cfg.data, data_dirs=None))
sys.argv = ["scripts/serve_policy.py"] + sys.argv[1:]
runpy.run_path("scripts/serve_policy.py", run_name="__main__")
