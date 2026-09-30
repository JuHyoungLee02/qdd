#!/usr/bin/env python
"""v6 델타 액션 통계 — 정확 계산 (2026-09-21).
lerobot 0.5.2 의 recompute_stats(relative_action) 는 RunningQuantileStats 가 float32 로 axis=0 누적을 해서 2.7M 프레임에서 틀린다
(상수 0.7854 채널이 mean 0.775 std 0.150 으로 나옴 — /tmp/chk2.py 재현). 그래서 같은 정의를 float64 로 직접 센다.
정의(lerobot compute_relative_action_stats 와 동일): 한 에피소드 안에 들어가는 모든 청크 시작 t 에 대해 k=0..49,
  rel[t,k,d] = action[t+k,d] - state[t,d]   (d 가 델타 채널이면)   /  action[t+k,d]  (제외 채널이면 절대값)
mean/std/min/max 는 전 청크 정확 누적, q01/q10/q50/q90/q99 는 청크 시작 10개마다 1개 표본으로 계산(정규화는 MEAN_STD 라 참고용).
결과: meta/stats.json 의 action 항목만 교체(원본은 stats_abs_backup.json).
  python exact_relative_stats_v6.py --root .../taskC_v6_train --exclude gripper base head lift [--dry]"""
import argparse, glob, json, os, time
import numpy as np, pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--exclude", nargs="*", default=["gripper"])
ap.add_argument("--chunk-size", type=int, default=50); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
t0 = time.time()
info = json.load(open(os.path.join(a.root, "meta/info.json"))); names = info["features"]["action"]["names"]
files = sorted(glob.glob(os.path.join(a.root, "data/*/*.parquet")))
df = pd.concat([pd.read_parquet(f, columns=["index", "episode_index", "action", "observation.state"]) for f in files]).sort_values("index")
assert (df["index"].values == np.arange(len(df))).all() and len(df) == info["total_frames"]
A = np.stack(df["action"].values).astype(np.float64); S = np.stack(df["observation.state"].values).astype(np.float64); ep = df["episode_index"].values
# 마스크: lerobot RelativeActionsProcessorStep._build_mask 와 같은 규칙 (소문자 부분일치 → 제외)
tok = [t.lower() for t in a.exclude]
mask = np.array([not any(t == n.lower() or t in n.lower() for t in tok) for n in names], dtype=np.float64)
print("델타 채널:", [n for n, m in zip(names, mask) if m], "\n절대 채널:", [n for n, m in zip(names, mask) if not m], flush=True)
C = a.chunk_size; N = len(A); starts = np.arange(N - C + 1); starts = starts[ep[starts] == ep[starts + C - 1]]
print(f"프레임 {N}, 유효 청크 {len(starts)} ({time.time()-t0:.0f}s)", flush=True)
D = A.shape[1]; s1 = np.zeros(D); s2 = np.zeros(D); mn = np.full(D, np.inf); mx = np.full(D, -np.inf); cnt = 0
S0 = S[starts] * mask   # (M, D)
for k in range(C):
    R = A[starts + k] - S0
    s1 += R.sum(0); s2 += (R * R).sum(0); mn = np.minimum(mn, R.min(0)); mx = np.maximum(mx, R.max(0)); cnt += len(R)
mean = s1 / cnt; var = np.maximum(0.0, s2 / cnt - mean ** 2); std = np.sqrt(var)
# 분위: 청크 시작 10개마다 1개
sub = starts[::10]; Rs = np.concatenate([A[sub + k] - S[sub] * mask for k in range(C)], 0)
qs = {f"q{int(q*100):02d}": np.quantile(Rs, q, axis=0) for q in (0.01, 0.10, 0.50, 0.90, 0.99)}
print(f"누적 {cnt} 행, 분위 표본 {len(Rs)} 행 ({time.time()-t0:.0f}s)")
for i, n in enumerate(names):
    print(f"  {n:18s} mean {mean[i]:+.5f} std {std[i]:.3e} min {mn[i]:+.4f} max {mx[i]:+.4f} q01 {qs['q01'][i]:+.4f} q99 {qs['q99'][i]:+.4f}")
if a.dry:
    print("DRY -- 쓰지 않음"); raise SystemExit
st = json.load(open(os.path.join(a.root, "meta/stats.json")))
old = st["action"]; print("기존 action 키:", list(old.keys()))
new = {"min": mn.tolist(), "max": mx.tolist(), "mean": mean.tolist(), "std": std.tolist(), "count": [int(cnt)]}
new.update({k: v.tolist() for k, v in qs.items()})
st["action"] = new
json.dump(st, open(os.path.join(a.root, "meta/stats.json"), "w"), indent=4)
print(f"written action keys: {list(new.keys())} | 총 {time.time()-t0:.0f}s"); print("EXACT_STATS_DONE")
