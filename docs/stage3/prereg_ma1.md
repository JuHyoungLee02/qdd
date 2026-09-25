# E-MA1 MolmoAct식 손끝 궤적 2×2 (미래 궤적 보조 손실 × 이력 덧그림) — 사전 등록 (2026-09-25T17:32:31Z, G0·학습 전)

작성 E-MA1 에이전트. 정본 §84(user-log 85: "1~3 다 허용할게 몰모엑트 많이 참고하고" — E-MA1 승인)와 §84 보충 1(해석 주의·O 불채택 규칙), 연구 문서 `docs/research/molmoact_deepdive_2026-09-26.md` §4.1–§4.2·§5·§6.1 초안을 등록 문서로 옮긴다. 형식·판정 방식은 E-TC(`prereg_se2e_temporal.md`)와 움직임 줄 확인(`prereg_se2e_motion_confirm.md`)을 따른다. 이 문서는 **관문 G0의 어떤 결과도 보기 전, 어느 칸도 학습하기 전에** 관문 절차·설계·지표·채택 규칙을 고정한다. 결과를 본 뒤 문턱·층 정의·검증 집합·카메라 모델 규칙·그리기 형식을 바꾸지 않는다. 결과는 `docs/stage3/results/ma1.md`.

## 0. 성격과 이미 본 것
- §56 소규모 시험 틀의 **입력·보조 목표 절제**다. 시드 0(통과 요인만 시드 1 반복), 검증 300 스냅샷 — 수치는 논문 근거로 쓰지 않는다. RB1 라이선스 미표기(§63 (6)) → 체크포인트 내부용, 폐루프·`harvest/runtime` 미사용.
- 등록 전에 본 것(모두 입력·라벨·환경 쪽, E-MA1 칸의 출력 아님): (1) URDF 머리 사슬(`ffw_bg2_rev4_follower.urdf`, ai_worker `897ef34`: `arm_base_link → head_joint1(피치, y축) → head_joint2(요, z축) → zed_joint → zed_camera_center → zed_left_camera_frame → 광학 프레임`), (2) 데이터 차원: RB1 상태 16차원(머리 관절 없음), RB2 19차원(`head_joint1/2`, `lift_joint`), (3) RB2 학습 분할 16,612행의 머리 관절 분포 — `head_joint1` 중앙값 0.5492 rad(최소 0.5476·5 % 0.5492·95 % 0.5507·최대 0.5522), `head_joint2` 0(−0.006…0.003) → 머리가 사실상 고정, (4) **우연히** GPU 점유를 확인하다 움직임 줄 확인 실험의 `motion_s1` step 2000 평가 로그 한 줄(dec_acc 0.6956, 검증 300)을 보았다 — 그 판은 아래 7.3절 시드 1 기준 칸 재사용 후보다. 문턱은 초안(연구 문서 §6.1, 사용자 승인) 그대로이고 이 값으로 정하지 않았다.
- Molmo2-ER 출처·신뢰도(1.5년 규칙): `allenai/Molmo2-ER`(HF 생성 2026-05-04, Apache-2.0, MolmoAct2 논문 arXiv 2605.02881의 백본, AI2) — 기간 안·1차 출처.

## 1. 질문
- **A**(미래 궤적 보조 손실): 미래 손끝 궤적을 보조 목표로 배우면 결정 정확도가 오르는가(실행 비용 0 — 실행 때 보조 머리를 돌리지 않는다).
- **O**(이력 덧그림): 과거 손끝 궤적을 머리 영상에 그려 주면 움직임 줄(§83) 위에 추가 이득이 있는가.
- 모든 칸은 움직임 줄 `se2e-motion@v1`을 켠다(§83 채택 반영).

## 2. 관문 G0 — 머리 카메라 투영 검증 (학습 전)
- **카메라 모델(명목)**: `harvest/train/se2e_trace.py` — 활성 팔 손끝 = `se2e_data` URDF FK의 `end_effector_{l|r}_link`(`arm_base_link` 좌표) → URDF 머리 사슬로 ZED 왼쪽 광학 프레임(녹화된 `cam_head` = ZED Mini 왼쪽 정류 영상 672×376) → 핀홀 투영, 내부값 **fx = fy = 367, cx = 336, cy = 188**(정본 §47 VGA 명목값; 왜곡 없음 — 정류 영상). 머리 각: RB2 = 그 행의 `head_joint1/2`, RB1 = 고정 **(0.5492, 0.0)**(0절 (3)의 RB2 중앙값; RB1 녹화 자세는 모름 → [가정]). `lift_joint`는 팔과 머리가 같은 `arm_base_link` 위라 투영에 무관.
- **표본**(`tools/ma1/g0.py select`): `se2e_c1` 검증 분할, 양손 행 제외, 머리 프레임 있는 행에서 원천(RB1·RB2) × 활성 팔(좌·우)마다 30장 = **120장**(RB1 60 + RB2 60, 좌우 반반). 칸마다 서로 다른 에피소드 30개를 무작위(시드 0) 고르고 에피소드마다 행 하나(모자라면 고른 에피소드의 다른 행으로 채움). 칸마다 선택 순서 앞 15장 = 보정 반, 뒤 15장 = 검사 반.
- **기준점**(`tools/ma1/g0_point.py`): Molmo2-ER(로컬 사본, `REVISION.json`에 커밋 sha 기록, bf16, 탐욕 복호, 최대 64토큰)에 이미지 한 장과 문장 `point to the <left|right> robot gripper`(MolmoAct 프롬프트 형식, 로봇 기준 좌우 = 그 행의 활성 팔). 답은 모델 카드의 파서(`<points coords="…">`, 1000 척도)로 픽셀로 바꾸고 첫 점을 쓴다. **점이 없으면 기준점 실패** — 초안의 "사람이 한 번 표시로 대체"는 이 실행에서 할 수 없으므로(에이전트 실행) **사람 대체 0, 실패는 제외하고 수를 기록**한다. 유효 기준점이 **90장 미만**이면 판단 불가 → 실패 경로(아래).
- **오차**: 기준점과 명목 투영의 유클리드 픽셀 거리(672×376 원 해상도).
- **통과** ⇔ 유효 프레임 전체의 오차 **중앙값 ≤ 12 px 그리고 90분위(선형 보간) ≤ 30 px**(비교 CMP_EPS 1e-12). 원천별 값도 보고한다(판정은 전체).
- **실패 → PnP 보정**: 원천마다 보정 반(유효분)으로 카메라 프레임 6자유도 보정(p′ = R(ω)·p + t, 로버스트 soft-L1, 척도 10 px, Levenberg–Marquardt; `se2e_trace.fit_correction`)을 맞추고, **검사 반 60장(유효분)** 에서 같은 문턱으로 재판정. 원천의 보정 반 유효 기준점이 10장 미만이면 실패. 통과하면 이 보정이 카메라 모델이 된다(원천별).
- **그래도 실패 → R2 시뮬로 이동**: R2_TRAIN 데이터가 준비돼 있으면 E-MA1을 R2로 옮기는 새 등록을 쓰고, 준비돼 있지 않으면 **보고하고 멈춘다**(이 등록의 칸은 돌리지 않는다).
- 판정 코드 `tools/ma1/g0.py judge`(아래 8절 해시). 결과 파일 `/data/harvest/logs/ma1/g0.json`(+ `g0_frames.jsonl`, `g0_points.jsonl`, 그림 한 장).

## 3. 요인 정의
### 3.1 A = `aux: trace5@v1` (보조 회귀 10 + 마스크 5)
- 점 = 현재 손끝 p₁ + **구간 끝**까지 시간 등간격 4점(p₁…p₅ = 프레임 k + i·(e − k)/4, i = 0…4, 손끝 3D 위치를 선형 보간한 뒤 투영). 구간 끝 e = k 뒤 처음으로 그리퍼 **열림/닫힘 상태가 k와 달라지는 프레임**(상태 = 프롬프트 규칙 `gripper=closed` ⇔ 관절값 > 0.5, `se2e_data.GRIP_CLOSED`), 없으면 에피소드 끝, **상한 3 s**(30프레임).
- 모든 점은 **프레임 k의 카메라**(그때 머리 각)로 투영, 좌표 = (u/672, v/376) ∈ [0, 1]. 카메라 뒤(깊이 ≤ 0.05 m)이거나 영상 밖이면 그 점 마스크 0(목표 0).
- 손실: 기존 `AuxGeomHead`(질의 4·폭 512·머리 8, 기울기는 백본까지 — §58)의 회귀 출력을 `len(AUX_REG)` 11 → 21로 늘린다(새 옵션 파일 `se2e_trace_model.py`; `stageb_model.py` 무수정). 목표 단위 = 좌표 / **0.05**(기존 `AUX_REG_SCALE` 5 cm = 1과 같은 관례: 영상 크기의 5 % = 1), 마스크 smooth-L1, **λ_aux 0.1**(기존 aux와 같은 λ). S-E2E 행은 특권 기하가 없어 원래 11회귀·7분류 목표는 모두 마스크 0 → aux 손실 = 궤적 손실. A = none 칸은 지금 S-E2E와 같다(aux 머리 11회귀, 목표 없음).
- 실행 때 궤적을 생성하지 않는다(프롬프트·질문·`question_id@vN` 불변).

### 3.2 O = 카메라 배치 `D27v1+eetrace@v1` (이력 덧그림, 머리 영상에만)
- 프레임 max(0, k−20)…k(10 Hz, 2.0 s, **과거만**)의 활성 팔 손끝을 프레임 k의 카메라로 투영한 폴리라인: 색 RGB(255, 32, 32), 두께 2 px, 선분 불투명도 = 가장 새 선분 1.0 → 20프레임 전 0.25 선형(PEEK식 시간 색 변화를 과거 쪽으로), 현재점에 반지름 4 px·두께 1 px 고리, 깊이 ≤ 0.05 m 점에서 선을 끊는다(`se2e_trace.OVERLAY_STYLE`·`render_overlay`).
- 원 현재 프레임 JPEG(`se2e/conv/img`)을 풀어 그린 뒤 **같은 q90으로 다시 저장**(새 폴더 `/data/harvest/data/ma1/overlay`; 원 프레임은 건드리지 않음). 카메라 표지 문장·프롬프트 텍스트는 그대로(이미지 토큰 수 불변).
- **학습 때만** 표본마다 p **0.3**으로 덧그림을 빼고 원 프레임을 쓴다(난수 = (`eetrace@v1`, 시드, 스텝) 문자열 시드, 데이터 순서·움직임 줄 드롭아웃 난수와 따로). **평가 때는 항상 그린다.**
- 정답 누수 방지: 미래(예정) 궤적·다음 청크 화살표는 그리지 않는다(연구 문서 §4.1 누수 주의). 활성 팔 선택 규칙은 기존 행 그대로(기준 프롬프트의 `arm=`와 같은 한계).

### 3.3 데이터 판본 `ma1_c1`
- `/data/harvest/data/ma1/`(새로 만듦; `se2e`·`se2e_t`·`se2e_c1`는 읽기만): `conv/<kind>.ma1.jsonl`(행 키마다 `trace5` {uv, mask, end, span_s}, 덧그림 경로, 카메라 모델 표지), `overlay/<kind>/ep…/k…_cam_head.jpg`, `camera.json`(G0 결과의 카메라 모델: 명목 또는 원천별 보정), `SHA256SUMS.txt`. 원 행·표본·분할·순서는 `se2e_c1`와 같다(키 목록 동일 확인, 옵션 끔 표본 = 기준 로더 표본 확인).
- 파생값은 원본 parquet 상태(10 Hz 전 프레임)에서 계산한다(행은 5프레임 간격이라 이력·궤적에 모자람).

## 4. 칸과 스케줄
| | O = none | O = 이력 덧그림 |
|---|---|---|
| **A = none** | `none+none` 기준(`se2e_c1`로 새로 학습 — E-TC `single_motion`은 옛 데이터판이라 재사용 불가) | `none+O` |
| **A = trace5** | `A+none` | `A+O` |

- 공통: Qwen3-VL-4B@`ebb281ec` + LoRA r32 + 흐름 정합 expert + aux·확인 헤드, KI stop, IMG 상태, λ dec/act/aux/ver = 1/1/0.1/0.1, 기반 모델에서 새로. `--data se2e --se2e-root se2e_c1/conv --se2e-t-root se2e_c1/conv --motion-line se2e-motion@v1 --motion-bins se2e_c1/motion_bins.json`(움직임 줄 드롭아웃 0.3 기본).
- **2,000스텝, 묶음 8, lr LoRA·헤드 1e-4, 워밍업 3 % + 코사인 → 0, 시드 0**, 전체 train(부분집합 없음), 검증 **300 스냅샷**(`--val-per-kind 150 --val-seed 0`, val_keys_sha `e22f6d8ef7fc` 기대) × 3질문 = 900항목, 평가 500스텝마다.
- 실행: 파드 `juhyoung-native-7a2a`, **GPU 2** = `none+none` → `A+none`, **GPU 3** = `none+O` → `A+O`(각 GPU 순차; 움직임 줄 확인 실험이 두 GPU를 비운 것 확인 후 — 2026-09-25 17:30Z 확인). `OMP_WAIT_POLICY=PASSIVE`, `OMP_NUM_THREADS=8`. GPU 0·1 사용 금지. 다른 작업이 GPU를 쓰면 기다린다(아무것도 죽이지 않음).
- 예측: 각 칸 step 2000 `last/`로 `stageb_train predict`(고정 잡음 시드 0) 검증 300. O 칸은 **덧그림 없이도** 한 번 더(의존도, 판정 밖).

## 5. 지표와 층
- **주 지표**: 결정 정확도 `dec_acc`(항목 argmax 정답률) — **전체**와 **전이 층**(E-TC 사전 등록 4절 정의 그대로: 어떤 질문의 프레임 단위 라벨이 k와 k+1…k+3에서 바뀌면 전이; `se2e_c1/transition_val.json` sha 앞 12 `7bcfc8f609c2`, 라벨 규칙만으로 결과 전 계산).
- 판정 밖(보고 의무): 결정 NLL, 정상 층, 질문별·항목 전이 정확도, 상호작용 A×O, **원천별(RB1·RB2) 정확도와 주효과**(§84 보충 1), 스냅샷 군집 부트스트랩 **10,000회**(시드 0, 95 % 백분위; A·O·A×O, 전체·전이), 궤적 보조 오차(A 칸: 보조 머리 출력의 픽셀 오차 — 조작 확인), **확정 보기 대신 예측 보기(argmax)로 조건을 준 expert 청크 오차**(정규화 단위 MSE, 같은 고정 잡음; steering 문서 E-SR1 주 지표), O 칸 덧그림 제거 평가 하락폭.

## 6. 결정 지연
- 도구 `tools/ma1/ma1_latency.py`(E-TC `temporal_latency.py` 방식): 결정 1회 = `forward_shared([표본])`. **FULL** = 이미지 읽기·(O: 과거 21프레임 손끝 FK + 머리 카메라 FK + 투영 + 그리기 + JPEG q90 인코딩 후 그 파일을 읽음)·전처리·토큰화·GPU 순전파(cuda 동기). **GPU** = 미리 인코딩한 묶음의 순전파만.
- 검증에서 머리 + 손목 1대인 표본 50개(원천별 25, 시드 0), 네 형식(`none+none`, `A+none`, `none+O`, `A+O`)을 **번갈아**, 워밍업 30회 뒤 형식마다 200회(50 × 4). A 형식은 실행 때 보조 머리를 돌리지 않으므로 기준과 같은 경로를 따로 잰다. 가중치는 `none+none` 칸 `last/` 하나(연산량은 가중치와 무관), 모든 칸 학습 뒤 GPU 2(H200), 부하 평균 기록.

## 7. 채택 규칙 (고정)
### 7.1 시드 0 규칙
- 칸 정확도 a(A, O). 주효과 A = ½[(a(A, none) − a(none, none)) + (a(A, O) − a(none, O))], O도 같은 식, 상호작용 A×O = [a(A, O) − a(none, O)] − [a(A, none) − a(none, none)].
- 요인마다 **통과** ⇔ (1) 전체 정확도 주효과 **≥ +0.02** 그리고 (2) 전이 층 주효과 **≥ −0.01** 그리고 (3) 결정 FULL p95 증가 **≤ 10 %**(A: `A+none`/`none+none` − 1, O: `none+O`/`none+none` − 1). 비교는 §74·§77 보충 2의 상대 **CMP_EPS 1e-12**.
### 7.2 잡음과 시드 1 반복 (이 규칙도 지금 등록)
- 검증 300이면 표준오차 ≈ 0.02–0.03(E-TC). **시드 0 규칙을 통과한 요인만** 시드 1로 다시 돌리고 **두 시드 평균**으로 최종 판정한다: 최종 **채택** ⇔ 두 시드 평균 전체 주효과 ≥ +0.02 그리고 두 시드 평균 전이 층 주효과 ≥ −0.01 그리고 (3)(시드 0 지연 측정). 통과 못 한 요인은 시드 1을 돌리지 않고 불채택.
- 주효과는 다른 요인의 두 수준을 모두 쓰므로 시드 1도 **네 칸 전부**가 필요하다(초안의 "시드 1 칸 2개"를 이렇게 바로잡는다). `none+none` 시드 1 = 움직임 줄 확인 실험의 `motion_s1`(`se2e_c1`, 시드 1, 같은 스케줄·같은 인자)을 **재사용**한다 — 조건: 그 판 `config` 인자가 이 등록의 기준 칸 인자와 같고 rc 0·step 2000 평가·`last/`가 있을 것, 그리고 이 판 코드 사본으로 돌린 `predict` 요약이 그 판 step 2000 평가 기록과 **모든 필드 같을 것**(다르면 `none+none_s1`을 새로 학습해 그 값을 쓴다). 나머지 세 칸은 새로 학습(GPU 2·3).
### 7.3 결과에 따른 처리 (등록)
- **O 불채택이면 VLA 입력 덧그림은 버리고 Astra 영상 덧그림(설계 §13)만 남긴다.**
- **A 해석 한계**(§84 보충 1): A의 목표는 결정 라벨(미래 손끝 움직임에서 규칙으로 만든 것)과 같은 정보를 연속값으로 담는다 → 정확도 이득은 "같은 정보의 더 촘촘한 감독"일 수 있다. 실행 비용이 0이라 채택에는 문제없지만 **일반화 주장(가설 H1)의 근거로 쓰지 않는다**. 원천별 정확도를 함께 보고한다.
- O 칸 덧그림 제거 평가 하락이 **0.05를 넘으면** "덧그림 의존 — 런타임 투영 실패 시 위험"으로 표시(판정 밖, 보고 의무).
- 판정 스크립트 `tools/ma1/ma1_verdict.py`(시험 `tests/test_ma1_verdict.py`) — 이 절의 문턱을 상수로 담았다. 결과 뒤 고치지 않는다.

## 8. 공통 설정
| 항목 | 값 |
|---|---|
| 이 등록과 함께 고정한 코드(LF 블롭 sha256 앞 16) | `harvest/train/se2e_trace.py` `86a4831c6d64d7e6`(카메라·투영·보정·trace5·덧그림·드롭아웃·G0 선택/판정 함수), `tools/ma1/g0.py` `1876c5cad61766f4`, `tools/ma1/g0_point.py` `fa4905ed42e990f4`, `tools/ma1/ma1_verdict.py` `a4859739452818a4`; 시험 `tests/train/test_se2e_trace.py`, `tests/test_ma1_g0.py`, `tests/test_ma1_verdict.py` |
| 이후 구현(TDD, 이 등록의 정의를 따름) | `harvest/train/se2e_trace_model.py`(보조 머리 21회귀·손실), 데이터 도구 `tools/ma1/build_data.py`, `harvest/train/stageb_train.py` 옵션(`--aux-trace trace5@v1`, `--overlay eetrace@v1`, `--ma1-root`, `--overlay-dropout 0.3`; 기본값 동작 불변), 지연 `tools/ma1/ma1_latency.py`. 위 고정 파일을 고쳐야 하면 결과 전에 이 문서에 사유와 새 해시를 적는다 |
| 무수정 | `harvest.train.stagea_train.PROMPT_FILES` 전부·`stageb_data.py`·`stageb_model.py`(§71 `PROMPT_FILES_B`), `se2e_data.py`, `se2e_temporal*.py`, `prefix_share.py`, `harvest/runtime` |
| 새 판 표지 | `prompt_config`에 `aux: trace5@v1`(A 칸), 카메라 배치 `D27v1+eetrace@v1`(O 칸), 카메라 모델(`camera.json` sha), 옵션 파일 해시를 `files_sha`에 더함 → 기본 체크포인트와 섞이지 않음 |
| 코드 사본 | 파드 `/data/harvest/code_ma1` = `git -c core.autocrlf=false archive`(LF) 한 커밋, 칸 폴더마다 `CODE_HASHES.txt` |
| 출력 | `/data/harvest/ckpt/ma1/<cell>_s<seed>`, 로그·예측·지연·판정 `/data/harvest/logs/ma1/`, 데이터 `/data/harvest/data/ma1/`, 작업 `/data/harvest/tmp/ma1`, 로컬 사본 `D:\tools\scratch_qdd\ma1` |
| 비용 상한 | 유료 API·Astra 호출 **0건, 상한 0원**(§84 보충 1 "실험마다 예산 상한"). GPU: 4칸 × 약 40분 ≈ 2.7 GPU시간 + 예측·지연 + G0 수 분(+ 통과 시 시드 1 세 칸 ≈ 2 GPU시간) |

## 9. 하지 않는 것
- 기본 경로·프롬프트 해시 파일·`harvest/runtime` 수정, `se2e`·`se2e_t`·`se2e_c1` 덮어쓰기, GPU 0·1, 유료 API, CAL/TEST 분할, 사람 기준점 표시(이 실행에서 불가 — 실패로 셈), 예정 궤적·청크 화살표를 VLA 입력에 그리기, 깊이 보조 목표(연구 문서 §4.3, 별도 등록), R7 23회차 검토 작업·Astra 탐침·R2_TRAIN 작업자 건드리기.
