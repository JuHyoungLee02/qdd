# MolmoAct 실데이터 준비·검증 (S-E2E + Molmo2-ER 포인팅) 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MolmoAct 이식을 실데이터로 하기 위한 준비·검증(학습 없음): S-E2E 머리 영상 프레임마다 Molmo2-ER 그리퍼 포인팅 → 궤적 라벨(1–5점, 구간 끝 = 놓기), 라벨 품질 측정·거르개, 덧그림 눈 검사, 조종 데이터(같은 장면·다른 경로) 부족 정도, E-MAR-real 사전 등록 초안. 결과 문서 `docs/stage3/molmoact_real_readiness.md`.

**Architecture:** 순수 모듈 `harvest/train/se2e_molmo.py`(그리퍼 구간·DLT 강건 적합·거르개·경로 다양성, 시험 먼저) + `harvest/datagen/trace.py`(이미 커밋: `labels_segments`·색·그리기) + 파드 도구 `tools/marr/`(프레임 풀기·포인팅·분석·시트). 포인팅 = E-MA1 G0와 같은 모델·문장(`point to the {left|right} robot gripper`, 탐욕 복호).

**Tech Stack:** 파드 `venv_e3st`(PyAV·PIL·cv2), `venv_train` + `/data/harvest/pylib_molmo2`(transformers 4.57.1, Molmo2-ER `dab2256`), 메인 파드 **GPU 0만**, 로컬 pytest.

**Spec:** user-log 99·정본 §89(실데이터 + 모델 라벨), MolmoAct arXiv 2508.07917 §3.1(프레임별 포인팅, None 버림, 평활 없음)·부록 D.7(조종 데이터), `docs/stage3/molmoact_r2_readiness.md`(성립 조건 C1–C14, M1 끝 규칙, M5 색), `docs/stage3/results/ma1.md`(G0: 다른 팔 14/119, 명목 FK 투영 100 px), `docs/stage3/results/se2e_data.md`(데이터·활성 팔·그리퍼 관절값).

## Global Constraints

- 학습 없음. 유료 API 0. GPU = 메인 파드 GPU 0만(Molmo2-ER 추론), 남의 프로세스 건드리지 않음, `OMP_WAIT_POLICY=PASSIVE`, `nice 10`.
- 파드 `/data`만(`source /data/harvest/env.sh`), 출력 `/data/harvest/data/marr/`·`/data/harvest/logs/marr/`. 로컬 D:만(`D:\tools\scratch_qdd\marr`).
- Write 도구 스크립트만, heredoc·`python -`·`python -c`·자기 일치 `pkill -f` 금지, `MSYS_NO_PATHCONV=1`.
- 커밋은 `git -c safe.directory=D:/qdd commit -F <msg> -- <paths>`; 끝 두 줄 Co-Authored-By / Claude-Session.
- 궤적 규칙: MolmoAct 5점 부분표집·0–255(`trace.py`), 끝 = **그 팔의 다음 놓기 프레임**(그리퍼 관절값이 닫힘 > 0.5 → 열림으로 바뀐 첫 프레임), 마지막 놓기 뒤 프레임은 라벨 없음(M1 번역); 포인팅 실패(None)는 버림.

## 표본 (측정 전 고정)

- 에피소드: RB1 24편 + RB2 24편(시드 0 무작위, RB2 ep 46 제외, 머리 영상 `cam_head` 있는 편), **모든 프레임(10 Hz)**, 두 팔 모두 포인팅(프레임당 2회). 예상 약 6,600프레임 × 2 = 약 13,000회. 근거: 거르개·끝점·다양성 통계에 편 48개면 원천별 24편(편 군집 부트스트랩 가능), 눈 검사 표본 144장을 뽑기에 충분; 전량(211,220프레임)은 E-MAR-real 등록 뒤.
- 눈 검사 144장: 원천 2 × 팔 2 × 36장(서로 다른 편 우선, 시드 0), 판정 = {지정한 그리퍼 위 / 다른 팔 그리퍼 / 그 밖 / 그리퍼 안 보임}. 판정은 포인팅 결과만 보고(거르개 결과를 보지 않고) 먼저 적는다.

## 관문 (측정 전 고정 — 이 계획 커밋 시각)

- **G-rate(측정)**: 눈 검사 144장에서 포인팅 오류율(= 그리퍼가 보이는 프레임 중 '지정한 그리퍼 위'가 아닌 비율)과 다른 팔 비율, 95 % 구간. 기준 비교: E-MA1 G0 다른 팔 14/119.
- **거르개(측정 전 고정)**: (F1) 실패 — 답에 점 없음; (F2) 좌우 충돌 — 같은 프레임 두 팔 점 거리 < 25 px(한쪽이 틀림) → 두 점 모두 버림; (F3) 시간 튐 — 점이 앞뒤 2프레임씩 이웃의 중앙값에서 > 40 px(0.2 s 안); (F4) 고유감각 불일치 — 편별로 그 팔의 FK 말단(URDF) 3D ↔ 점 2D를 RANSAC DLT(3×4, 문턱 15 px, 1,000회, 시드 0)로 맞춘 뒤 잔차 > 20 px. 한 편에서 DLT 정상점 < 50 %면 그 편의 그 팔 점 전부 버림(카메라 관계를 못 세움).
- **G-filter**: 눈 검사 표본에서 거르개를 통과한 점의 오류율 ≤ **5 %** 그리고 올바른 점 유지율 ≥ **80 %**. 미달 → 거르개 재설계(변경 기록) 또는 보고.
- **G-trace**: 거른 점으로 `trace.labels_segments` 라벨 — 라벨 있는 프레임 비율, 점 수 분포(1–5), 끝점 = 놓기 프레임 점(그 점이 거르개 통과인 비율 보고). 시트 3장(원천 × 구간 시작·중간·놓기 직전)을 Read로 보고 칸마다 적는다: 선이 그리퍼에서 시작해 놓는 곳에서 끝나는가.
- **G-colour**: 실영상 머리 프레임 200장에서 후보 색(MolmoAct 청록 (0,255,255), R2 색 (110,255,0), 자홍 (255,0,255), 노랑 (255,255,0))마다 RGB 거리 < 60 화소 비율 — ≤ 0.1 %인 색 중 가장 낮은 것을 실데이터 덧그림 색으로. 덧그린 16장 눈 검사.
- **G-diversity(기술 통계)**: (a) 같은 원천·같은 지시문·같은 팔의 구간 쌍 중 시작점·끝점이 각각 40 px 안인 쌍(= 같은 목표)의 경로 차(방향 하우스도르프, px) 분포, (b) RB2 첫 프레임이 거의 같은(축소 영상 평균 절대 차 ≤ 문턱) 편 쌍 중 지시문이 다른 쌍 수(= 같은 장면 다른 대상), (c) 이것으로 MolmoAct D.7(대상별 50 + 대체 경로 50)·조종 평가 n ≥ 300에 모자란 양과 새 실물 수집 설계.
- 비용 상한: GPU 0 ≤ 2 GPU-h(넘으면 멈추고 표본 축소 기록).

## Tasks

### Task 1: `harvest/train/se2e_molmo.py` (시험 먼저)
- `grip_segment_ends(g) -> list[int|None]`, `ransac_dlt(P3, uv, thr, iters, seed) -> (M, inlier, resid)`, `dlt_project(M, P3)`, `side_conflict(uv_l, uv_r, d)`, `jump_flags(uv, win, px)`, `filter_points(...) -> (keep, reasons)`, `path_divergence_px(a, b)`. 시험 `tests/train/test_se2e_molmo.py`.

### Task 2: 파드 도구 `tools/marr/`
- `select_decode.py`(편 고르기·프레임 풀기·상태·FK 저장), `point.py`(Molmo2-ER 일괄, GPU 0), `analyze.py`(거르개·라벨·통계·시트·색·다양성), `run_marr.sh`.

### Task 3: 실행·관문·눈 검사 → 결과 문서
- 포인팅 → 눈 검사 144장(판정 기록 `docs/stage3/results/marr_eye.json`) → 거르개 → G-filter → 시트 → 색 → 다양성.

### Task 4: 문서·기록
- `docs/stage3/molmoact_real_readiness.md`(성립 조건 대응표·관문 결과·조종 데이터 판단·E-MAR-real 사전 등록 초안·자체 검사) + 같은 커밋에 책 01·02·04·06 줄, draft-log 줄.

## 변경 기록

(측정 뒤 바뀌는 것은 `date -u` 시각과 함께 여기에 적는다.)

- **변경 1(2026-09-26 06:10 UTC, G-filter 실패 뒤)**: 눈 검사 표본 1(144장, 판정 `docs/stage3/results/marr_eye.json`)에서 거르개 v1은 남긴 점 오류 1/18(보수 기준 5.6 %)·올바른 점 유지 **18 %**로 G-filter 실패(유지율 80 % 미달; 원인: 좌우 충돌이 맞는 점까지 버림, 시간 튐 40 px가 맞는 점 16개 버림, 편 DLT가 48편 중 28편에서 정상점 50 % 미만 — 같은 편 안에서도 포인팅 위치(손끝·몸통·가장자리 잘림)가 DLT 한 개로 안 맞음). 판정 중 부호 `u`(그리퍼 위지만 어느 팔인지 판단 불가)를 더했다(보수 오류율에서는 오류로 셈). 진단(판정 밖): 명목 URDF 머리 카메라 투영 + 편별 2-D 오프셋으로 보면 맞는 점은 지정 팔까지 중앙값 51 px·다른 팔까지 301 px, 다른 팔 점은 반대(323 / 57 px). **거르개 v2**(`se2e_molmo.filter_nominal`): 실패 → 좌우(보정된 명목 투영에서 다른 팔에 더 가까우면 버림) → 관문(지정 팔 보정 투영에서 > 150 px면 버림, 150 = 표본 1 맞는 점 p90 136 올림); 편 오프셋 = 지정 팔 쪽으로 40 px 넘게 가까운 내부 점(가장자리 12 px 제외)의 (점 − 명목) 중앙값, 2회 반복, 10개 미만이면 그 편 전부 버림. v2 문턱은 표본 1에서 정했으므로 **검증은 새 눈 검사 표본 2**(시드 1, 원천 × 팔마다 24장 = 96장, 표본 1 프레임 제외, 거르개 결과를 보기 전 판정)로 하고, G-filter 문턱(남긴 점 오류 ≤ 5 %·올바른 점 유지 ≥ 80 %)은 그대로. 궤적 라벨은 v2가 남긴 **포인팅 점**(MolmoAct 방식)이다 — 명목 투영(중앙값 51 px 오차)은 거르기에만 쓴다.
- 2026-09-26 05:4x UTC(Task 1 구현 중, 측정 전): F4 DLT는 **한 편의 두 팔 점을 함께** 한 카메라로 맞춘다(한 팔 경로만으로는 3D 점이 거의 한 곡선·평면이라 3×4 DLT가 퇴화 — 합성 시험에서 확인). 한 팔의 후보 중 잔차 ≤ 20 px가 50 % 미만이면 그 팔 점 전부 버림(`dlt_arm`), 편 전체 적합 실패면 `dlt_episode`. 문턱 값(15·20 px, 50 %)은 그대로.
