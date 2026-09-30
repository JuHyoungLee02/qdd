#!/usr/bin/env python
"""lerobot-train 래퍼 (2026-09-21, v6): --policy.use_relative_actions=true 이면 lerobot 0.5.2 가 전처리기를 새로 만들면서
--rename_map 을 버린다(lerobot_train.py 294~304행). 새로 만든 파이프라인의 RenameObservationsProcessorStep 에 rename_map 을
다시 넣어 준다. lerobot 코드는 건드리지 않는다. 사용: accelerate launch ... lerobot_train_v6.py <lerobot-train 인자>"""
import json, os, sys
import lerobot.scripts.lerobot_train as T
from lerobot.processor import RenameObservationsProcessorStep

RENAME = json.loads(os.environ.get("V6_RENAME_MAP") or "{}")
_orig = T.make_pre_post_processors


def _patched(policy_cfg, pretrained_path=None, **kw):
    pre, post = _orig(policy_cfg, pretrained_path=pretrained_path, **kw)
    if pretrained_path is None and RENAME:
        n = 0
        for st in pre.steps:
            if isinstance(st, RenameObservationsProcessorStep):
                st.rename_map = dict(RENAME); n += 1
        print(f"[v6 wrapper] rename_map 재주입 {n}개 step: {RENAME}", flush=True)
        if n == 0:
            sys.exit("[v6 wrapper] RenameObservationsProcessorStep 이 없다 -- 중단")
    return pre, post


T.make_pre_post_processors = _patched
if __name__ == "__main__":
    T.main()
