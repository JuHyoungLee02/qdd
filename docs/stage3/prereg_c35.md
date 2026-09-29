# E-C35 — L8S 양산 초반분으로 35B 소규모 확인 판 (무료, 사전 등록)

- 작성: 작전T, 2026-09-29 (UTC 시각은 커밋 시각). **학습 전에** 커밋한다. 결과 `docs/stage3/results/c35.md`.
- 근거: user-log 192(본 학습 전에 L8S 양산 초반분으로 35B 소규모 확인 판 한 번). 레시피는 [main35_recipe.md](main35_recipe.md).
- 유료 0원. GPU = 78dc `juhyoung-q-78dc` 0–3(렌더 불필요). 코드 고정 사본 `/data/harvest/code_c35_<커밋>`, 산출 `/data/harvest/out/c35/`, 로그 `/data/harvest/logs/c35/`.

## 0. 자체 검사
- **결정**: L8S 양산 데이터로 만든 35B가 09-28 f35_d보다 나쁘지 않은가 — 본 학습 전 데이터·파이프라인 확인. 나쁘면 본 학습 전에 원인을 찾는다.
- **가를 수 있나**: L8-X dev·OOD-H·OOD-O(각 수백 상태), 새 OOD-O 58편(448상태), G 1,577행. 35B 두 시드 A/A로 여유를 잰다.
- **한계**: f35_d는 한 시드뿐이다(Y 쪽은 두 c35 시드와 같은 f35_d를 짝지음). 학습 양이 본 학습보다 작다(약 3 h × 시드).

## 1. 데이터 (`tools/final35/c35_chain.sh` 2단계)
- **시작 조건**: `/data/harvest/out/teach_l8d/l8s_prod/AUDIT300.json`의 `"verdict": "PASS"`(첫 300편 독립 검수, 통제자·L8D가 기록) **그리고** 끝난 양산 편(meta.json) ≥ **1,000**. FAIL이면 체인을 멈춘다.
- **L8S**: `l8s_prod/train` + `l8s_prod_ring/train`에서 meta.json 시각 순 **앞 1,000편**(`c35_prep.py l8s`). 편 단위 검증 분할 = sha256("c35|<시드>") % 100 < 3. 학습 행 = `tools/teach_l8d/build.py … train pt --manifest` → `convert_min.py d-min`(L8D 코드; 팔 튐 >0.04 rad 편·행 drop은 빌드가 뺌). L8S-simple 850편은 같은 경로에 섞여 나온다.
- **L8S-drawer**: `b3d_drawer` 번들(`docs/stage3/l8d_bundle_b3d.json`, 148편) 전부 학습.
- **공개 점**: E-POOLV8-FIX 판정(`/data/harvest/out/poolv/verdict_fix.json`)이 NONINFERIOR면 FIX 풀, 아니면 옛 풀 + agibot_p0 대신 AgiBot v3 최종. 어느 쪽이든 AgiBot v3와 RB2(G에서 옮긴 약 4,000행 포함 records_verified_v2 계열)가 들어간다. G 행 제거·가드 후 id 해시 3 %를 검증용으로 떼고(`val_open.jsonl`, geval 형식), 나머지를 `open_pool.main`(p 0.75, 반복 상한 1.5)으로 기본 행에 더한다. 최종 파일 `gsplit check` 통과 필수.
- b2(L8-X 옛 번들)는 넣지 않는다(main35_recipe 데이터 표에 없음).

## 2. 학습
- `tools/teach_35b/train.sh` 4장 DDP, main35 설정: Qwen3.5-35B-A3B LoRA r16 α32 lr 1e-4 warmup 20, global batch 24(micro 2 × accum 3 × 4), expandable_segments, `--save-every 200`(재개).
- 걸음: `--epochs 2 --max-steps 3500`(3.1 s/step → 약 3 h). 체크포인트 = epoch1, epoch2(최대 걸음에서 끝나면 그 시점).
- 시드 0, 그다음 시드 1(A/A 쌍).

## 3. 평가
- **검증(체크포인트마다)**: L8S 검증 편(`x_val_l8s_d-min_clean`, 접근 3D) + 공개 점 검증(`val_open`, geval 적중). 시드마다 **L8S 검증 >20 mm 실패율이 낮은 epoch**(같으면 공개 적중 높은 쪽, 같으면 뒤 epoch)를 고른다(`c35_select.py`). G와 겹치지 않음(가드).
- **본 평가(고른 체크포인트)**: L8-X dev·OOD-H·OOD-O(`dist8/data_x/x_*_d-min_clean`), 새 OOD-O 58편(`/data/harvest/out/c35/data/x_ood_o58_d-min_clean.jsonl`, eval_list.json의 참값 성공 58편, 448상태), G 1,577행. 모두 점 오프라인(`c35_eval.sh full`). 기준선 f35_d(`/data/harvest/out/final35/merged_d`)도 같은 스크립트로 평가(09-29 밤 GPU2).
- **폐루프**: 렌더 카드 여유가 있을 때만 새 OOD-O 10편(보고용, 판정 밖).

## 4. 판정 (결과 전 고정) — `tools/final35/c35_judge.py`
- ni_judge 규칙(user-log 186). A/A 여유 = c35 시드 0·1 쌍(35B 재측정).
  - L8-X dev·OOD-H·OOD-O·OOD-O58: 중앙값 차·>20 mm 실패율 차 95 % 상한 ≤ 여유.
  - G 6 하위 + 전체: 적중(f35_d − c35)·px(c35 − f35_d, 공개 보류 4개) 95 % 상한 ≤ 여유(E-POOLV8 방식).
- **NONINFERIOR**(모든 세트 비열등)면 L8S 데이터·파이프라인 확인 통과. **WORSE**면 나빠진 세트를 보고하고 본 학습 전에 원인 조사(판정만으로 본 학습을 막지는 않으며 결정은 통제·사용자).

## 5. 일정
- L8S 1,000편(시간당 약 100편, 23:30 KST 시작 가정) → 약 09:30–10:00 KST 9/30 시작 → 준비 0.5 h + 학습 2 × 3 h + 병합·검증 1 h + 본 평가 1 h → **약 18:30 KST 9/30 결과**. 양산 1차분(2,400시드) 완료 전이라 본 학습을 늦추지 않는다(78dc를 본 학습이 쓰지 않는 한).

## 변경 기록
- **변경 1 (2026-09-29 UTC, 체인 시작 전 — 데이터 빌드 전, 결과 없음)**: 사용자 결정 user-log 195(본 35B 공개/기본 = 0.75, main35_recipe d11ebb2). §1의 '반복 상한 1.5'를 바꾼다: 공개 행 = **정확히 0.75 × 기본 행**(기본 = L8S 1,000편 + drawer; 공개 점 풀은 FIX 판정 결과 풀), 반복 상한은 막음장치 3.0만 둔다(`c35_prep.py mix … 3.0`). 실제 반복 배수는 빌드 기록(`train_c35.jsonl.tmp.counts.json` → PREP_DONE 줄)과 결과 문서에 적는다.
  - 예상: 시범2 실측 약 30행/편 → 기본 약 30,000 + drawer 약 4,400 ≈ 34,000행 → 공개 약 25,500행. 풀(검증 3 % 뺀 뒤) 약 31,000행(FIX) / 약 30,800행(옛+AgiBot) → **반복 약 0.8×(풀에서 부분 추출, 반복 없음)**. 기본이 약 62,000행을 넘을 때만 1.5×를 넘는다(상한 3.0).
  - 1.5× 초과 반복이 생기면 새 조건이다. 목적은 본 학습 비율(0.75)을 소규모 판에서 그대로 검증하는 것이고, 과적합 신호(공개 점 검증 적중이 epoch2에서 떨어짐)를 결과에 따로 보고한다. 판정 규칙은 그대로.
- **변경 2 (2026-09-29 UTC, 체인 시작 전 — 데이터 빌드 전, 결과 없음)**: 사용자 결정 user-log 197(본 학습 규칙: 비율 = min(0.75, 2.0 × 공개 풀 행 / 시뮬 기본 행), 반복 상한 2.0×). 반복의 효과를 떼어 보려고 **두 팔 짝 비교**로 바꾼다.
  - **팔 b (반복 없음)**: 지금 설계 그대로 — 기본(L8S 1,000편 + drawer)에 공개 = 0.75 × 기본을 전체 풀(검증 3 % 뺀 뒤)에서 뽑는다. 예상 반복 약 0.8×(막음장치 3.0). **시드 0·1**(A/A).
  - **팔 a (반복 약 2.5×)**: 같은 풀에서 sha256("c35a|<id>") % 3 == 0인 1/3 부분집합만 쓰고 같은 비율 0.75가 되게 반복한다(`c35_prep.py subset`; 막음장치 4.0). 예상 부분집합 약 10,300행 → 반복 약 2.5×. **시드 0만**.
  - 실제 행 수·비율(open_over_base)·반복 배수는 팔마다 PREP_DONE 줄(`/data/harvest/logs/c35/c35.log`)과 결과 문서에 적는다. 두 팔의 비율이 같지 않으면(막음장치에 걸리면) 결과에 적는다.
  - 학습 순서: b s0 → a s0 → b s1. 체크포인트 선택·평가 세트는 §3 그대로(팔·시드마다).
  - **판정** (`c35_judge.py`, ni_judge, A/A 여유 = 팔 b 시드 0·1): (1) b 대 f35_d (b 두 시드 × f35_d), (2) a 대 f35_d, (3) **a 대 b**(시드 0 짝). 모든 세트 비열등이면 각각 NONINFERIOR. (3)이 WORSE면 '반복 2.5×가 해롭다'는 신호로 보고한다.
  - **과적합 신호(보고, 판정 밖)**: 실행마다 epoch1 → epoch2 공개 점 검증 적중(`val_open`) 변화(`select_*.json`); 팔 a에서 떨어지고 b에서 안 떨어지면 반복 과적합으로 적는다.
  - 일정: 학습 3회 × 약 3 h → 결과 약 21:45 KST 9/30(1,000편이 약 10:00에 모인다는 가정).
