# E-DIST8 결과 (중간: 수준 A·B, 오프라인) — 출력 줄기 R·H·D × 데이터 수준

- 사전 등록 `docs/stage3/prereg_dist8.md` `1f1db1e` + 변경 1 `7f74f04`. 유료 0원. 작성 2026-09-27 02:5x UTC. **중간 결과**: +px·C 수준(공개 팩 대기)과 폐루프 영상은 아직 없다.
- 팔: A-R = STRIP8 S-min(옛 L8), A-D·A-H(새, 816걸음), B-R = STRIP8 S-min(b1), B-D(새, L8-X b1 1,196편).
- 세트: 옛 DEV 305·OOD-H 285, L8-X dev_x 1,613, OOD-H 860, OOD-D 282, OOD-O 394, OOD-S 253, OOD-T 369, OOD-H-lift 60편. 채점 `harvest/teach_pt/metrics.py`, 비교 `tools/teach_pt/dist8_compare.py`(스냅숏 짝 부트스트랩 10,000회). 원 표: `/data/harvest/out/dist8/cmp_a.jsonl`·`cmp_b.jsonl`.

## 1. Q1 D 대 R (접근 3D 오차 중앙, mm; 판정)
| 세트 | A-D | A-R | A 판정 | B-D | B-R | B 판정 |
|---|---|---|---|---|---|---|
| 옛 OOD-H | 3.6 | 36.9 | BETTER | — | — | — |
| dev_x | 4.6 | 50.0 | BETTER | 4.7 | 5.1 | SAME |
| L8-X OOD-H | 4.2 | 43.0 | BETTER | 4.2 | 20.1 | BETTER |
| OOD-H-lift | 4.3 | 131.8 | BETTER | 4.4 | 11.2 | BETTER |
| OOD-S | 4.2 | 32.3 | BETTER | 4.5 | 7.5 | BETTER |
| OOD-T | 4.0 | 34.7 | BETTER | 4.0 | 7.1 | BETTER |
| OOD-D | 3.6 | 2.0 | SAME | 3.8 | 2.0 | SAME |
| **OOD-O(새 물체 범주)** | 98.0 | 89.0 | SAME | **96.9** | **25.9** | **WORSE** |

- OOD-O에서 D의 참값 상한은 3.5 mm(변환기 정상) → **모델이 본 적 없는 물체에 점을 못 찍는다**(A·B 모두). R은 L8-X 학습으로 새 물체에 26 mm까지 온다. 원인 분해(점 픽셀 오차, 어느 물체를 찍었나)는 다음.

## 2. Q2 데이터 효과
- R: A → B에서 크게 좋아짐(OOD-H 43.0 → 20.1, OOD-O 89.0 → 25.9, S 32.3 → 7.5, T 34.7 → 7.1, HL 131.8 → 11.2, 모두 BETTER).
- D: A ≈ B(모든 세트 SAME) — 높이·장면 일반화는 이미 깊이 변환이 해결했고, 새 물체는 다양화 데이터(b1)로도 안 풀렸다.

## 3. Q4 H (수준 A, 예비)
- H-on 대 D: 옛 DEV·OOD-H·L8-X OOD-H 비열등(+2 mm), dev_x·OOD-H-lift는 WORSE(평균 차 +6–26 mm, 중앙은 같음), OOD-D·O 판정 못 함.
- H-off 대 R: 비열등(옛 OOD-H 33.7 vs 36.9, L8-X OOD-H 39.1 vs 43.0, HL 110.5 vs 131.8). H-noisy 대 D-noisy 대부분 비열등.
- 잠정 결론 칸: `H_DEPTH_ONLY`에 가까움(깊이 있을 때 일부 세트에서 D보다 꼬리가 나쁨) — B+px 수준 H로 확정.

## 4. Q5 깊이 잡음(zed_mini)
- D-noisy − D-on: 중앙 +1–3 mm, 평균 차 구간 모두 WORSE이지만 OOD-H·S·T·HL에서 D-noisy도 R보다 BETTER, OOD-D·dev_x(B)에서는 R과 SAME.

## 5. 한계·다음
- 한 시드, 8B, 오프라인만(폐루프 영상 아직). +px·C 수준 없음. 최소 요청은 STRIP8b 판정(KEEP_PRIVILEGED: 입력에는 넣지 않음)대로 유지.
- 다음: D의 새 물체 점 실패 분해 → 폐루프(L8-X OOD-H·O 4판씩, 영상) → 공개 팩이 오면 +px·C.
