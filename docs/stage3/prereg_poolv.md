# E-POOLV8 — 감사 후 공개 점 풀(17,131행) 대 옛 풀(31,202행) 비열등 (8B, 무료, 사전 등록)

- 작성: 작전T, 2026-09-29 (UTC 시각은 커밋 시각). **학습 전에** 커밋한다. 결과 `docs/stage3/results/poolv.md`.
- 근거: 통제자 09-29 승인(공개 점 라벨 감사 → RB2·RB3·MolmoBot `*_verified`, agibot_p0 → AgiBot v3 최종 1,384행; data_inventory 2026-09-29). user-log 165(정확도 우선, 비율 75 %에 못 미쳐도 됨), 186(비열등은 중앙값·>20 mm 실패율, A/A 보정 여유).
- 유료 0원. GPU = 78dc `juhyoung-q-78dc` GPU 0–3(렌더 불가 카드 — 학습·vLLM만), 한 장에 한 팔·시드.

## 0. 자체 검사
- **결정**: 35B 본 학습의 공개 점 풀을 새 풀로 바꿔도 되나(새 풀이 옛 풀보다 나쁘지 않나).
- **가를 수 있나**: G 1,577행 · L8-X dev 약 1,600상태 · OOD-O, 두 시드 짝 부트스트랩. 여유는 같은 학습 파일의 두 시드 차(A/A)로 잰다.
- **이미 본 것**: E-OPRATIO8(p75 대 p0), 오답 감사 표본(data_inventory 09-29). 새 풀 학습 결과는 아직 없다.

## 1. 팔 (차이는 공개 점 풀뿐, 레시피·기본 행 같음)
- 기본 = `/data/harvest/out/final35/data/train_d-min.jsonl`(78,745행, 두 팔 같음).
- **OLD** = 옛 풀 31,202행(커밋 2b312c0 이전 `open_pool.py`), 이미 만든 `/data/harvest/out/final35/dryrun2/train_open.jsonl`(공개 46,803행, 반복 1.5, 합 125,548행).
- **NEW** = 새 풀 17,131행(`open_pool.py` 2b312c0; AgiBot G 165행은 가드로 빠짐), `/data/harvest/out/poolv/train_new.jsonl`(공개 25,696행, 반복 상한 1.5, 합 104,441행).
- 걸음 = E-OPRATIO8 규칙(행 수 비례): S = round(1,632 × 행 수 / 78,745) → OLD 2,602, NEW 2,165. 미세 배치 8 × 누적 2.
- 레시피 = E-OPRATIO8 그대로: Qwen3-VL-8B-Instruct LoRA r16 α32, lr 1e-4 코사인 warmup 20, bf16, 비전 동결, `harvest.teach_l8.train --epochs 3`, `--save-every 200`.
- 시드 0·1 각 팔 → 4개 학습(GPU 0 OLD s0, 1 NEW s0, 2 OLD s1, 3 NEW s1).

## 2. 평가
- G 전체: `/data/harvest/out/opratio/g_eval.jsonl` 1,577행(`tools/teach_pt/geval.py`, E-OPRATIO8과 같은 파일·채점기). 하위 세트 6개(BEHAVIOR·MolmoBot Franka·MolmoBot RBY1·RB2·Where2Place·RefSpatial 3종 합) + 전체.
- L8-X: `x_dev_d-min_clean`, `x_ood_o_d-min_clean`(`harvest.teach_pt.evaluate --kinds control`, 접근 3D 오차).

## 3. 판정 (결과 전 고정) — `tools/teach_pt/poolv_compare.py`
- **L8-X (ni_judge, user-log 186)**: A/A 쌍 = (OLD s0, OLD s1), (NEW s0, NEW s1) → `ni_judge.aa` 여유(중앙값 mm·>20 mm 실패율). NEW 대 OLD를 두 시드 합친 짝으로 `ni_judge.judge`: dev·OOD-O 각각 중앙값 차·실패율 차 95 % 상한 ≤ A/A 여유면 비열등.
- **G (같은 A/A 방식)**: 하위 세트·전체마다 적중률 차(OLD − NEW)와 점 픽셀 오차 차(NEW − OLD, 공개 보류 4개만)를 두 시드 합친 짝 부트스트랩(10,000, 시드 0). A/A 여유 = 두 A/A 쌍 부트스트랩 |차|를 합친 95 번째 백분위. 비열등 = 상한 ≤ 여유(적중·픽셀 둘 다).
- **결론**: dev·OOD-O·G 7개(6 하위 + 전체) **모두 비열등이면 NONINFERIOR** → 본 학습은 새 풀. 하나라도 아니면 **WORSE(세트 목록)** — 이때도 정확도 우선 규칙상 옛 풀로 돌아가지 않는다(옛 풀의 오답 행은 감사로 확인됨); 대신 나빠진 세트를 통제·사용자에게 보고하고 결정을 받는다.
- 참고 지표(판정 밖): 세트별 적중률·중앙값·평균, 행 수.

## 4. 자원·규칙
- 코드 고정 사본 `/data/harvest/code_poolv_<커밋>`, 산출 `/data/harvest/out/poolv/`, 로그 `/data/harvest/logs/poolv/`. 재시작 시 `--resume`.
- 금지: heredoc·`python -`·`python -c`·유료 호출. events.log에 GPU 줄.

## 변경 기록
