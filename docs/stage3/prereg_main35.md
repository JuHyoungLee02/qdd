# E-MAIN35 — 본 35B 학습 (무료, 사전 등록, 결과 전 고정)

- 작성: 작전T, 2026-09-30 (UTC 시각은 커밋 시각). 레시피 정본 [main35_recipe.md](main35_recipe.md). 결과 `docs/stage3/results/main35.md`.
- 자동 체인: `tools/final35/main35_super.sh` → `main35_chain.sh`(78dc), 체크포인트 평가 큐 `main35_evalq.sh`(x2 GPU0 학습 중 + 78dc 학습 뒤), 판정 `main35_judge.py`. 산출 `/data/harvest/out/main35/`, 로그 `/data/harvest/logs/main35/main35.log`.

## 0. 기동 조건
- E-C35 `JUDGE_DONE`(c35.log) **그리고** `c35/verdict/verdict_summary.json`의 **b 대 f35_d = NONINFERIOR**. 아니면 멈추고 `ALERT_GATE_FAIL`을 남긴다(통제자 확인).
- L8S 양산 끝(`l8s_prod/PROD_DONE`, L8D가 만든다) → 선행 빌드 정지 → 남은 편 병렬 빌드.
- 8장 확장은 이번에 하지 않는다(78dc 4장).

## 1. 데이터
- **L8S 전량**: 선행 빌드 조각(`main35/prebuild/chunks/c*`, main root; 첫 481편 포함; dq > 0.04·overexposed·occluded·tipped·실패 편 done 행 드롭은 `teach_l8d.dataset`) + 고리 V는 `prebuild/RING_OK`(BUILD_CHECK_C29에서 거짓 reopen 없음 확인)일 때만. **drawer b3d 제외**(user-log 213).
- **검증 분할(학습 제외)**: L8S 편 단위 sha256("m35|<시드>") % 100 < 3, 공개 점 id 3 %(`c35_prep.py pool`, E-C35와 같은 규칙). G와 겹치지 않음(가드).
- **공개 점**: 채택 풀(옛 검증본 + AgiBot v3 최종, G 가드 뒤 32,365행; `open_pool.py` 117cb86)에서 검증 3 %를 뺀 나머지. 비율 = **min(0.75, 2.0 × 풀 / 기본)**, 반복 상한 2.0×(user-log 195·197). 실제 행·비율·반복은 BUILD_DONE 줄에 적는다.

## 2. 학습
- Qwen3.5-35B-A3B LoRA r16 α32, lr 1e-4 warmup 20, 4장 DDP global batch 24(micro 2 × accum 3), expandable_segments, `--save-every 200`(재개), **3 에폭**.
- 체크포인트: 반 에폭마다 어댑터(`--save-half-epoch`, 이번 커밋에서 추가) → epoch1·1.5·2·2.5·3을 평가(0.5는 평가 안 함).

## 3. 평가 (자동, 오프라인 점)
- 순서: 체크포인트가 생기는 대로 **2 → 1.5 → 2.5 → 1 → 3**. 학습 중에는 x2 GPU0(렌더 불가 카드)에서, 학습 뒤에는 78dc에서(`main35_evalq.sh`, mkdir 잠금).
- 세트: L8S 검증 + 공개 점 검증, G 1,577행, L8-X 7세트(d-min clean), 새 물체 OOD-O 58편(448상태).
- **최적 체크포인트**: L8S 검증 >20 mm 실패율 최저 → 같으면 공개 점 검증 적중 높은 쪽 → 같으면 뒤 체크포인트.
- **판정**(`main35_judge.py`, ni_judge 규칙 user-log 186): 최적 체크포인트 대 f35_d. 여유 = E-C35 팔 b 두 시드 A/A(35B). 대상: L8-X dev·OOD-H·OOD-O·OOD-O58(중앙값·>20 mm 실패율), G 6 하위 + 전체(적중·px). 나머지 L8-X 4세트(OOD-D·S·T·H-lift)는 35B A/A가 없어 **보고만** 한다.
- **자동 체인 밖(후속, 결과 문서에 따로)**: Inspect Robots 하네스 1차 평가 + RD(정본 §41), 손목 영상 이상 강건성(대비 A: 손목 사진 검게·흐리게·빠짐 → L8-X·새 물체 58편 오프라인 점 오차 + 새 물체 폐루프), 폐루프·한계 지도. 모두 렌더 카드가 비어 있을 때만, 최적 체크포인트로. 방법은 main35_recipe 그대로이고 판정 규칙 없이 보고한다.

## 4. 결론
- NONINFERIOR면 본 35B를 f35_d 대체 후보로 올린다. WORSE면 나빠진 세트를 보고하고 결정은 통제·사용자.

## 변경 기록
- **변경 1 (2026-09-30 KST, 기동 전 — 학습·평가 결과 없음)**: 사용자 결정(2026-09-30, 0300a0 세션 경유).
  - **게이트 이탈**: E-C35가 b 대 f35_d WORSE(dev·OOD-H·G MolmoBot Franka·RBY1·G 전체)로 §0 기동 조건을 못 넘었다. 원인 진단(재학습 없음): Franka G 보류 300행은 전부 3인칭·어안이라 머리 시점 규칙(user-log 165·169)과 안 맞고, RBY1은 C35 실사용 280행으로 적었고, L8-X dev·OOD-H는 옛 L8-X 도메인·양 차이다(E-L8SW에서 L8S 25→100 %로 OOD-H 실패율 29→24 %). 사용자가 소규모 재실행 없이 본 학습 기동을 결정했다. 체인은 `/data/harvest/out/main35/GATE_OVERRIDE`(결정 원문 한 줄)가 있으면 게이트 대신 `GATE_OVERRIDE`를 기록하고 넘어간다(main35_chain.sh).
  - **G Franka 판정 제외**: §4 판정의 주 결론은 G에서 MolmoBot Franka를 뺀 행(G 전체 포함 다시 계산)으로 낸다(`verdict_main_vs_f35d_nofranka.json`). Franka를 넣은 판정은 `with_franka`로 함께 보고한다(main35_judge.py).
  - **RBY1**: 4중 검증 통과 RBY1 행(700)은 이미 채택 풀에 전부 있다. f35_d가 더 쓴 dist8 팩 행은 검증 탈락분이라 넣지 않는다. 본 학습은 공개 풀을 반복 2배 상한까지 써서 RBY1 노출이 C35의 약 5배다.
  - 옛 L8-X b2는 넣지 않는다. 데이터·학습·평가 세트는 그대로.
