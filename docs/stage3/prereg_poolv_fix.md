# E-POOLV8-FIX — 수정 공개 점 풀(32,027행) 대 옛 풀(31,202행) 비열등 (8B, 무료, 사전 등록)

- 작성: 작전T, 2026-09-29 (UTC 시각은 커밋 시각). **학습 전에** 커밋한다. 결과는 `docs/stage3/results/poolv.md`에 절을 더한다.
- 근거: E-POOLV8 WORSE(results/poolv.md) — 손끝(ee) 행 대체 규칙이 벌린 그리퍼 손끝 중심을 뺀 결함. 통제자 09-29 승인(수정안).
- 유료 0원. GPU = 78dc GPU 0–1(FIX 시드 0·1). OLD 두 팔은 E-POOLV8에서 이미 학습·평가한 것을 그대로 쓴다(같은 학습 파일·코드·평가 파일이라 다시 돌리지 않음).

## 1. 팔
- **OLD** = E-POOLV8 OLD(`/data/harvest/out/final35/dryrun2/train_open.jsonl`, 풀 31,202, 합 125,548행, 2,602걸음), 결과 `poolv/eval/pv_old_s{0,1}`.
- **FIX** = `tools/teach_pt/poolv_fix_build.py`: RB2·RB3·MolmoBot RBY1은 원래 검증본에서 **물체·놓기 행 중 4중 검증 탈락분만** 뺀다(RB2 −220, RB3 −34, RBY1 −84; 손끝 행은 모두 유지). BEHAVIOR·ManiSkill 그대로, AgiBot은 v3 최종(G 가드로 1,219행). G 가드 통과. 풀 32,027, 공개 48,040(반복 상한 1.5), 합 126,785행 → `poolv/train_fix.jsonl`, 걸음 round(1,632 × 126,785 / 78,745) = 2,628.
- 레시피·시드(0·1)·평가(G 1,577행, L8-X dev·OOD-O)는 E-POOLV8과 같다.

## 2. 판정 (결과 전 고정)
- `poolv_compare.py … fix`: E-POOLV8과 같은 규칙(ni_judge A/A 여유 — OLD 쌍·FIX 쌍; G 6 하위 + 전체의 적중·px).
- **모든 세트 비열등(NONINFERIOR)일 때만 FIX 채택.** 아니면 본 학습은 **옛 풀에서 agibot_p0만 AgiBot v3 최종으로 바꾼 판**을 쓰고, 그 경우 AgiBot 교체만의 효과는 따로 확인되지 않았다고 적는다.

## 3. 규칙
- 코드 고정 사본 `/data/harvest/code_poolv_<커밋>`, 금지 명령 없음, events.log에 GPU 줄.

## 변경 기록
