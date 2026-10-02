# E-GP2 조기 시범 — 손목 회전 라벨 기준틀: (a) 머리 영상 투영 대 (b) 로봇 기저 (8B, 사전 등록)

- **조기 시범(early pilot)이다.** 본 실행은 L9 v2 7,500편이 모인 뒤 같은 규칙으로 다시 돈다. 이 시범의 판정은 형식을 확정하지 않는다. 본 실행 전까지 잠정 판단으로만 쓴다. 이 시범은 v2 학습 경로(빌드 → 학습 → vLLM 평가)가 끝까지 도는지도 함께 확인한다.
- 작성: E-GP2 에이전트, 2026-10-02 KST. **데이터 빌드·학습·평가 전에** dev에 커밋한다. 결과는 `docs/stage3/results/gp2_pilot.md`에 적는다.
- 근거: `docs/research/grasp_point_learning_2026-10-02.md` §11.6 위험 4, §11.7, §11.8(V2-base 부속 팔). L9 v2 라벨 구현은 `docs/stage3/results/l9v2_gates.md`(`grasp9.rot_img`/`rot_base`, `rt9` pt_command 훅, `build9` GRASP 블록)를 따른다.
- 금지 그대로: 3인칭 영상, 교사 정책·Astra, 유료 API, 파드 생성·삭제, main 브랜치, L9 양산 프로세스, 78dc GPU0(다른 팀), 실행 중 스크립트 수정.

## 0. 질문
- 형식 v2의 `rot`(0–11, 15° 구간, 0–165°)를 다음 두 기준 중 무엇으로 정의할지 정한다.
  - **(a)** 머리 영상에 투영한 닫힘 축의 각. 지금 기본값이며 `rot_bin_img`이다.
  - **(b)** 로봇 기저 기준 각. `rot_bin_base`이다. 위 접근이면 위에서 본 yaw(0 = 로봇 x축, 왼쪽으로 증가)이고, 다른 접근이면 접근 축 둘레 각(0 = 수평, 6 = 수직)이다.
- 가설(§11.6 위험 4): 머리 카메라 팬이 ±30° 흔들리므로 (b)는 같은 영상에 팬만큼 다른 정답을 만든다. 그래서 (a)가 영상에서 더 잘 배워질 것이다 **[가설]**.

## 1. 데이터 (ego 전용, 3인칭 끔)
- 편: L9 v2 성공 편이다. 대상은 `/data/harvest/l9v2/pilot1/collect`(AI Worker 시범과 양산)와 `/data/harvest/l9v2/pilotF/collect`(Franka 시범과 양산)이다. L9 주인이 알려 준 run dir이다. G1·R1은 뺀다(build9 요청 문구가 두 로봇만 지원한다).
- 조건: `grasp_v2` 있음, `success`, `max_dq_rad ≤ 0.04`, 로봇 ∈ {ffw_sg2, franka_mast}, `gate_move` 제외.
- **동결**: 편 목록은 빌드 시작 때 한 번 고른다(`/data/harvest/out/gp2/data/episodes.json`). 그 뒤에 나온 편은 넣지 않는다. 시범 확인용 집계(10-02 오후)는 성공 1,032편이고, 이 가운데 954편이 조건을 통과했다(학습 749 / 보류 205, 정의 111 / 38).
- 빌더: `harvest.l9.build9.build`이다. `slots=False`, `external=False`, `third_person=False`, `camera_line=False`, `grasp_format=True`로 부른다. L9 주인이 알려 준 `tools/l9/build_v2.py … --third-person off --success-only --no-slots`와 같은 경로다. 코드 사본은 a277f83 이후(GRASP 블록 버그 수정 뒤) dev에서 만든다.
  - 학습 행은 `train=True`(L8 반복 규칙, 라벨 없는 행 제외)로, 보류 행은 `train=False`로 만든다.
- **보류 분할 = 과제 정의 단위**: `sha256("gp2:<task_id>") % 5 == 0`이면 보류 세트로 간다(약 20 %). 학습과 보류 사이에 겹치는 정의는 0이며, 코드가 단언한다.
- **두 팔의 차이는 둘뿐이다** (`tools/gp2/gp2_build.py arms`):
  1. 잡기 행(답에 `rot`가 있는 above_target·descend_close) 답의 `rot`. a = `rot_bin_img`(빌드 그대로), b = 그 호출에서 고른 pick의 `rot_bin_base`.
  2. 요청 GRASP 블록의 `rot` 설명 문장. a = 영상 문장(build9 그대로), b = 기저 문장(`ROT_BASE_TEXT`).
  - pick 연결: labels 행과 pick을 잇는 필드가 없다(L9 주인 확인). 그래서 같은 물체(`tgt` = `obj`)·같은 계열·같은 `rot_bin_img`인 pick으로 잇는다. 후보가 없거나 후보끼리 `rot_bin_base`가 다르면, 그 행을 **두 팔 모두에서** 뺀다(개수는 기록한다).
  - 단언: 두 팔의 행 id·순서는 같다. 답은 `rot`만 빼면 같다.
- 학습 파일: `train_<arm>.jsonl` = E-VIEW8 A0 116,235행 + 그 팔의 L9 v2 학습 행(`tools/l9r/hcam8_build.py combine`, E-HCAM8과 같은 바탕)이다. 걸음 = round(1,632 × 전체 행 / 78,745)이다. 두 팔의 걸음은 같아야 하며, 다르면 멈춘다.

## 2. 팔·시드·레시피
| 실행 | 팔 | 시드 | 카드 |
|---|---|---|---|
| a_s0 | (a) 영상 | 0 | 78dc GPU1 |
| b_s0 | (b) 기저 | 0 | 78dc GPU2 |
| a_s2 | (a) 영상 | 2 | 78dc GPU3 (A/A) |
- 레시피는 E-HCAM8 H0와 같다(`hcam8_worker.sh`의 학습 명령). Qwen3-VL-8B LoRA r16 α32, lr 1e-4 코사인, 미세 배치 8 × 누적 2, `--max-steps` = 위 걸음이다. 같은 행, 같은 걸음이고, a_s0와 b_s0는 같은 시드다.
- 카드 잠금은 `card_78dc_<g>.lock`(hcam8 방식)이다. `/data/harvest/out/vla/GPU_WANTED`가 내 카드를 부르면(GP2 표시 없는 줄) 그 실행을 멈춘다. 상태는 남기고 나중에 `--resume`한다.

## 3. 평가 (오프라인, vLLM)
- 서버 카드: x2 GPU0(a_s0), 7a2a GPU2(b_s0), x3 GPU0(a_s2). 서버 설정은 `teach_pt/vllm.sh` 그대로이고, 평가는 `harvest.teach_pt.evaluate --arm pt --kinds control`로 한다.
- 모델: 각 실행의 25 %·50 % 걸음 상태(학습 상태 스냅숏 → CPU 병합 `tools/gp2/gp2_export.py`)와 최종 모델.
- 세트:
  - **L9 v2 보류**(정의 단위): 그 팔의 형식으로 평가한다. 25 %, 50 %, 최종 모델 모두에서 잰다.
  - **L8-X 7세트**: E-HCAM8과 같은 `dist8/data_x/x_*_d-min_clean`(dev_x·OOD-H·OOD-D·OOD-O·OOD-S·OOD-T·OOD-H-lift)이다. 최종 모델만 잰다.

## 4. 지표 (`tools/gp2/gp2_report.py`)
- 보류 잡기 행(답에 rot가 있는 행, `truth_eval.jsonl`)마다 계산한다.
  1. **잡기 자세 일치**
     - 접근 계열 정확도: `approach` = 라벨 계열.
     - 회전 구간: 정확 일치, **±1구간 안(주 지표 `rot_pm1`)**, 원형 평균 구간 오차(12구간 원형, 0–6).
     - 정답은 각 팔 자기 라벨이다(a = `rot_bin_img`, b = `rot_bin_base`). 형식 위반·빠진 값은 오답(오차 6)으로 친다.
  2. **점 오차**: E-HCAM8과 같은 접근 3D 오차(mm)이며, 중앙값과 20 mm 초과율을 본다. 잡기 행과 보류 접근 행 전체 두 범위로 잰다.
  3. **L8-X 7세트**: 세트별 중앙값과 20 mm 초과율.
  4. **학습 효율**: 25 %·50 %·100 % 걸음의 1·2 곡선. 보고만 한다.
- 계열별·로봇별로도 나눠 보고하며, 이것도 보고만 한다.
- 이 시범은 물리 재생 잡기 성공(§11.8 주 지표)을 재지 않는다. 그것은 본 실행 몫이다.

## 5. 판정 (결과 전 고정, 최종 모델)
- 짝 부트스트랩: 행 단위 짝, 10,000회, 난수 시드 0(L8-X는 2,000회).
- **A/A 여유**: a_s2 − a_s0의 `rot_pm1` 차에서 m = max(3 %p, 95 % 구간 반폭, |관측 차|)로 정한다. 계열 정확도 여유 nf, 점 20 mm 초과율 여유 np도 같은 방식으로 구하되, 하한은 각각 3 %p와 2 %p다.
- **B_BETTER**(기저 채택): b_s0 − a_s0와 b_s0 − a_s2가 **둘 다** `rot_pm1` 차 ≥ m이고 95 % 하한 > 0이며, 다음 비열등을 만족할 때다.
  - 계열 정확도 차 하한 ≥ −nf
  - 점 20 mm 초과율 차 상한 ≤ np
  - L8-X 각 세트 20 mm 초과율 차 상한 ≤ max(2 %p, 그 세트 A/A 반폭)
- **B_BETTER_BUT_NI_FAIL**: 회전 이득은 있지만 비열등을 어긴 경우다. 채택하지 않고 본 실행에서 다시 본다.
- **A_BETTER**: 두 비교 모두 `rot_pm1` 차 ≤ −m이고 상한 < 0인 경우다.
- **SAME**: 위 어느 것도 아닌 경우다.
- 유지 규칙: B_BETTER일 때만 (b)로 바꾸고, 나머지는 (a)를 유지한다. 지금 기본값이고 §11.7 추천이다.
- **표본 한계**: 보류 잡기 행이 200행 미만이면 결과에 '표본 한계'를 붙이고 판정은 보고만 한다.
- **조기 시범**: 어떤 결과든 7,500편 본 실행에서 같은 규칙으로 다시 판정한다. 그 전에 형식 문구(build9 GRASP 블록)를 확정하지 않는다.

## 6. 실행
- 코드 사본: `/data/harvest/code_gp2_<sha>`(`git -c core.autocrlf=false archive`).
- 사슬: `tools/gp2/gp2_prep.sh`(78dc CPU: 선택 → 행 빌드 16+4조각 → 팔 → combine → 학습 3개 시작) + `tools/gp2/gp2_eval.sh`(서빙 파드 3개, 모델이 생기면 바로 평가).
- 출력은 `/data/harvest/out/gp2/`, 기록은 `/data/harvest/logs/gp2/gp2.log`, 평가 정지는 `touch /data/harvest/out/gp2/STOP_EVAL`이다.
- 끝나면 카드를 반납하고 `board/events.log`에 한 줄 적는다.

## 변경 기록

- **변경 1 (2026-10-02 15:16 KST, 학습 시작 시점·결과 보기 전): 빌드 명세**
  - 동결 편: 성공 1,100편 중 조건 통과 1,017편(학습 790 / 보류 227, 정의 111 / 38; AI Worker 656 · Franka 361). `/data/harvest/out/gp2/data/episodes.json`.
  - 첫 빌드가 `rot: null`인 잡기 행에서 멈췄다(그 pick에 영상 구간 기록 없음). `rot`가 정수가 아닌 잡기 행도 '연결 안 됨'으로 **두 팔 모두에서** 뺀다(0d8ada3). 학습 잡기 행 2,181(뺀 행 260), 보류 잡기 행 336(뺀 행 44).
  - L9 학습 행 9,365(control 5,356 / aux 4,009), 보류 1,525행(control). 행 검사 오류 0.
  - `train_a.jsonl` 125,600행 sha256 `5f95ee84…20ee8`, `train_b.jsonl` 125,600행 sha256 `57b04b31…7c51`, 걸음 2,603(두 팔 같음). 보류 `l9_eval_a` sha256 `c4496166…1964`, `l9_eval_b` `c8f9c92a…dc8`.
  - 학습 3개 시작 06:16Z(코드 `/data/harvest/code_gp2_0d8ada3`), 평가 사슬 3개(코드 `code_gp2_c17c298` = dev d27a760과 같은 내용).

- **변경 2 (2026-10-02 16:5x KST, 25 % 걸음(q650) 중간 결과를 본 뒤 — 최종 모델 결과 전)**: 주 지표와 점 비열등 검사를 고친다. 등록 규칙의 결과도 함께 보고한다.
  - 이유 1(라벨 성질, 모델과 무관): 보류 잡기 행 336행의 `rot_bin_base`는 0·11 구간에 84 %가 몰려 있다(위 접근 yaw ≈ 로봇 x축, 다른 접근은 수평 손가락). 그래서 상수 0만 내도 ±1 일치가 86 %다. `rot_bin_img`는 12구간에 퍼져 있다(최빈 14 %). 이 상태에서는 자기 라벨 ±1 일치(`rot_pm1`)를 두 팔 사이에서 비교할 수 없다.
  - 주 지표를 **`skill_pm1` = (rot_pm1 − prior_pm1) / (1 − prior_pm1)**로 바꾼다(우연 보정).
    - prior_pm1은 진짜 접근 계열을 아는 상수 추측이다. 학습 라벨(`truth_train.jsonl`)에서 계열마다 ±1 안에 가장 많이 드는 구간 하나를 고르고, 그것이 ±1 안에 맞는 비율을 쓴다.
    - 판정식(§5)은 같고 지표만 바뀐다. A/A 여유 m은 skill_pm1의 a_s2 − a_s0로 구한다.
  - 이유 2(채점기 성질, 모델과 무관): 라벨 답을 그대로 예측으로 넣어 채점해도 L9 v2 보류 접근 행의 3D 접근 오차 중앙값이 21.9 mm다(above_target 117 mm, descend_close 13 mm). v2 점(잡을 부위의 보이는 표면 점)이 above 높이 규칙과 맞지 않기 때문이다.
    - L9 v2 행의 점 비열등은 **라벨 점까지의 픽셀 오차 중앙값**(scores `point_px`)으로 본다. 차의 상한 ≤ max(3 px, A/A 반폭, |A/A 차|)이다.
    - 3D mm 지표는 L8-X 7세트에만 쓴다(등록 그대로). L9 3D 값은 참고로만 적는다.
  - 등록 원래 규칙(`rot_pm1`, 3D 20 mm)의 판정도 `decision_registered_rule`로 보고한다.
  - 메인 요청(78dc GPU0에서 b 시드 2를 더해 두 팔 모두 A/A)은 실행하지 못했다. 사용자 원 지시인 'GPU0 금지'와 충돌해 권한 단계에서 막혔기 때문이다. 사용자가 허락하면 같은 코드로 `gp2_worker.sh <code> 0 b 2`를 돌려 보탠다.

- **변경 3 (2026-10-02 17:15 KST, b 시드 2 추가 — 50 % 이후 결과 보기 전)**: 사용자가 메인에게 78dc GPU0 사용을 허락했다(10-02 17:4x 원문 "78dc GPU0을 E-GP2에 쓰는 건 … 허락", 메인 전달). 메인이 **b_s2**(팔 b, 시드 2)를 78dc GPU0에서 시작했다. 시작 기록은 08:15:03Z이고, 코드 사본 `/data/harvest/code_gp2_0d8ada3_g0`는 워커 카드 검사에 0을 더한 것이다. 행·걸음·레시피는 같다.
  - 두 팔 모두 A/A 쌍을 갖는다. 여유는 두 A/A 쌍(a_s2 − a_s0, b_s2 − b_s0) 가운데 큰 쪽이다.
  - B_BETTER·A_BETTER는 교차 비교 넷(b_s0·b_s2 × a_s0·a_s2)이 모두 조건을 만족해야 한다. 비열등도 넷 모두에 적용한다.
  - b_s2가 끝나지 않으면 변경 2 규칙(교차 둘)으로 판정하고, b_s2는 끝난 뒤 보탠다.
  - 평가: 7a2a GPU2에 두 번째 사슬(포트 8764, vLLM 메모리 0.30)을 둔다. b_s0 사슬(0.60)과 같은 카드를 나눠 쓴다.
