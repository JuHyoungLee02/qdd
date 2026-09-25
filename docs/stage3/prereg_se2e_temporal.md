# S-E2E 시간 맥락 2×2 — 사전 등록 (2026-09-25T13:05:07Z, 학습 전)

작성 S-E2E 시간 맥락 에이전트. 사용자 규칙 user-log 70(성능이 낮으면 최근 논문이 한 것을 가져와 적용)과 user-log 71(권고 1 "2프레임 Qwen3-VL 비디오 입력"을 먼저)에 따라, 문헌 조사 `docs/research/temporal_context_2026-09-25.md` 권고 1·2와 그 2×2 설계를 S-E2E 공개 데이터에서 잰다. 이 문서는 **어느 칸도 학습하기 전에** 설계·지표·채택 규칙을 고정한다. 결과를 본 뒤 문턱·층 정의·검증 부분집합·구간값을 바꾸지 않는다. 결과는 `docs/stage3/results/se2e_temporal.md`.

## 0. 성격과 이미 본 것
- §56 소규모 시험의 **입력 절제**다. 시드 1개, 검증 300개라 수치는 논문 근거로 쓰지 않는다. RB1 라이선스 미표기(§63 (6)) → 체크포인트 내부용.
- 출발점(판정 밖): S-E2E A(1 에폭) 검증 결정 정확도 0.722, 오답은 거의 "움직이냐 마냐·크기 한 칸"(`se2e_diag.md` D3), 결정 프롬프트는 단일 시점(머리 + 활성 손목 이미지, 그리퍼 열림/닫힘·팔 문장).
- 등록 전에 본 것(모두 입력·라벨 쪽, 모델 출력 아님): (1) Qwen3-VL 처리기 탐침(2절 수치), (2) 입력 분포 — 움직임 값의 학습 분할 분위(3절 구간을 정하는 데 씀), (3) 검증 행 전이 층 비율 0.651(라벨만으로 계산, 4절), (4) 실데이터 점검(`/data/harvest/logs/se2e_temporal/check_data.json`: 옵션 끔 표본 = 기준 로더 표본, 과거 프레임 누락 0, 쌍 그림 `video2_pairs.jpg`로 [t−0.3 s, t]가 연속 프레임임을 눈으로 확인), (5) **우연히** 진행 중인 데이터 규모 판의 로그 꼬리(N = 1,000·9,371 판의 step ≤ 1000 평가 줄) — 이 실험의 어느 칸의 값도 아니고 문턱 선택에 쓰지 않았다.

## 1. 질문
결정 정확도 0.72의 일부가 "단일 시점이라 지금 움직이는 중인지 안 보임"에서 오는가. 두 요인을 같은 데이터·같은 스케줄에서 2×2로 잰다.
- **V**(시각 이력): single(기준) / **video2** = 카메라마다 2프레임 클립 [t−Δ, t], Δ = 0.3 s.
- **M**(움직임 문장): none(기준) / **motion** = 거친 움직임 한 줄 + 학습 때 줄 드롭아웃 p = 0.3.

## 2. V — video2 정의와 토큰 수 검증 (실제 처리기, 파드 transformers 5.17.0)
- Δ = 0.3 s → 10 Hz 원본에서 가장 가까운 프레임 **k − 3**(에피소드 시작에서는 0으로 자름; 전체 표본-카메라 81,672개 중 k − k_prev = 3이 78,885, = 0(k = 0 행)이 2,787). 과거 프레임은 현재 프레임과 같은 경로(av 디코드 → RB1 손목 90° 회전 → JPEG q90)로 새 폴더에 뽑았다.
- **구현**: 한 카메라 = `[label, now, prev]`. Qwen3-VL 이미지 처리기는 정지 이미지를 `temporal_patch_size` 2만큼 **복제**해 시간 패치 하나(grid_t = 1)를 만든다(탐침: 머리·손목 모두 두 시간 칸이 같음 확인). video2는 그 시간 칸 0에 과거 프레임, 칸 1에 현재 프레임을 넣는다(`harvest/train/se2e_temporal_model.VideoEncoder.pixels`).
- **검증한 수치**(`/data/harvest/logs/se2e_temporal/probe_proc.out`, 실제 S-E2E 프레임):

| 카메라(원본 크기) | 이미지: grid / LLM 시각 토큰 | 2프레임 비디오(Qwen3VLVideoProcessor, do_sample_frames=False): grid / 토큰 | 비디오 픽셀 = 우리 쌍 채움 | 채팅 템플릿 전체 길이(이미지 / 공식 비디오) |
|---|---|---|---|---|
| 머리 672×376 | [1, 24, 42] / **252** | [1, 24, 42] / **252** | **비트 동일(최대 차 0.0)** | 266 / 274 |
| 손목 424×240 | [1, 16, 26] / **104** | [1, 16, 26] / **104** | **비트 동일(최대 차 0.0)** | 118 / 126 |

  → **LLM 시각 토큰 수는 그대로(머리 + 손목 356)**. 공식 비디오 경로는 카메라마다 타임스탬프 문자열(`<0.1 seconds>` 등) + 표지로 텍스트 **+8토큰**을 더한다. 우리는 공식 `<|video_pad|>` 자리표 대신 `<|image_pad|>` 그대로 두고(프롬프트 해시 보호 파일 `prefix_share.py`를 건드리지 않기 위해, §71) 카메라 표지를 `"head camera (2 frames: t-0.3 s, t):"`처럼 바꿔 시간 정보를 텍스트로 준다(늘어난 텍스트 토큰 수는 5절 지연 측정 때 실측해 보고). 비전 타워가 받는 픽셀 텐서·grid는 공식 비디오 처리기 출력과 같다. grid_t = 1이라 mrope 위치도 이미지와 같다.
- 시험(`tests/train/test_se2e_temporal_qwen.py`, 파드): 쌍 픽셀 = 비디오 처리기 출력(비트), grid·토큰 252/104 불변, 이미지 토큰 356 = 356, 두 칸 중 칸 1은 정지 이미지와 같고 칸 0만 다름, 2요소 항목은 기준 인코더와 비트 동일, video2 공유 접두 경로 = 옛 경로(상대 1e-4).

## 3. M — 움직임 문장 정의
- **속도 출처 확인**: S-E2E 행의 `proprio.qd`·`grip[1]`은 **중앙 차분**(`np.gradient`, 프레임 k + 1을 읽음)이라 0.1 s 미래가 섞이고 런타임에 없다 → 쓰지 않는다. 원본 parquet 상태에서 **인과 후방 차분** (x[k] − x[k−1]) × 10 Hz를 새로 뽑았다(k = 0은 0). 팔 = 활성 팔 7관절 속도의 노름(rad/s), 그리퍼 = 활성 팔 그리퍼 관절 속도를 데이터셋별 [0, 1] 열림 정도 속도로(§63 (2) `grip_rate01`, + = 열림).
- **줄**: 상태의 로봇 줄 다음에 `motion: arm=<still|slow|fast> gripper=<closing|still|opening>`(맥락 문장과 세 질문 문장 모두에 같은 줄).
- **구간(학습 분할 37,484 표본, 결과 전 고정)** `/data/harvest/data/se2e_t/motion_bins.json`(sha256 앞 12 `e164719a92d5`): 팔 = 3분위 → still < **0.2179** ≤ slow < **0.6070** ≤ fast (rad/s). 그리퍼 = |열림 속도|의 **0.85 분위 = 0.1755 /s** 초과면 opening/closing, 아니면 still. 0.85를 고른 이유(입력 분포만 보고): 학습 행의 60.2 %가 정확히 0이고 0.80 분위 0.0405 /s는 잡음 수준, 0.85 분위 0.18 /s, 0.90 분위 0.78 /s. 학습 분할 줄 분포: arm still/slow/fast ≈ 1/3씩, gripper moving 15 %(closing 2,846·opening 2,765).
- **드롭아웃**: 학습 배치에서 표본마다 p = 0.3으로 줄을 `motion: arm=unknown gripper=unknown`으로 바꾼다(줄은 남기고 값만 모름, §77 C5' 읽기와 같은 방식). 난수는 (시드, 스텝)으로 따로 — 데이터 순서 난수는 건드리지 않는다. 평가에서는 끄지 않는다(항상 실제 줄).

## 4. 지표와 층
- 모든 칸: 학습 끝(step 2000) 체크포인트 `last/`로 `stageb_train predict`(같은 `evaluate()` 경로, 고정 잡음 시드 0) → 검증 300개(`--val-per-kind 150 --val-seed 0`, val_keys_sha `e22f6d8ef7fc`) × 3질문 = 900항목의 항목별 기록.
- **주 지표**: 결정 정확도 `dec_acc`(항목 argmax 정답률)와 결정 NLL `dec`(질문 보기 집합 재정규화 −log p(정답)), **전체**와 **전이 층**.
- **전이 층(라벨 규칙에서, 결과 전 정의)**: 스냅샷 k가 전이 = 어떤 질문이든 프레임 단위 라벨(같은 규칙 `se2e_heur_ee033@v1`, `se2e_data.episode_rows` stride 1)이 k와 k + j(j = 1, 2, 3; 0.1–0.3 s — 다음 결정까지 0.33 s의 10 Hz 최근접)에서 하나라도 다르면. `harvest/sim/snapshot.boundary_flags`의 "다음 결정 스냅샷과 술어가 바뀜"을 S-E2E 라벨에 옮긴 것. 도구 `tools/se2e_temporal.py transition` → `/data/harvest/data/se2e_t/transition_val.json`(sha 앞 12 `ee7b4fdb7962`; 행 라벨 재계산 = 원 행 라벨 전부 일치를 도구가 확인). val 행 1,921개 중 전이 **65.1 %** — 층이 크다는 점을 미리 적어 둔다. 나머지는 정상(steady) 층.
- 보조(판정 밖): 질문별 정확도(dir_xy·dir_z·mag_coarse), 질문별 **항목 전이**(그 질문의 라벨만 k..k+3에서 바뀜) 정확도, 정상 층, 스냅샷 군집 부트스트랩 95 % 구간(10,000회, 시드 0).
- 잡음 규모(미리 적음): 검증 300 스냅샷이면 정확도 표준오차 ≈ 0.02–0.03(항목이 스냅샷 안에서 상관). 아래 문턱 +0.02·−0.01은 요청된 사전 문턱이며 이 잡음보다 작다 — 판정은 규칙대로 내고 구간을 함께 보고한다.

## 5. 결정 지연 (같은 GPU 종류, 묶음 1)
- 도구 `tools/se2e/temporal_latency.py`: 결정 1회 = `forward_shared([표본])`(맥락 + 3질문 공유 접두 한 번, 융합 decide 호출과 같은 계산). **FULL** = 이미지 읽기·전처리(video2는 두 프레임 + 쌍 채움)·토큰화·GPU 순전파(cuda 동기), **GPU** = 미리 인코딩한 묶음의 순전파만.
- 검증에서 머리 + 손목 1대인 표본 50개(출처별 25, 시드 0), 네 형식을 **번갈아**(형식 순서 고정 라운드 로빈) 워밍업 30회 뒤 형식마다 200회. 가중치는 (single, none) 칸의 `last/` 하나(연산량은 가중치와 무관), 모든 칸 학습이 끝난 뒤 GPU 2 한 장(H200), 부하 평균 기록.
- 채택 규칙의 지연 = **FULL p95**(보수적: 런타임은 과거 프레임 전처리를 앞 호출에서 재사용할 수 있지만 여기서는 매번 한다). GPU p50/p95도 보고.

## 6. 채택 규칙 (고정)
- 칸 정확도 a(V, M). 주효과 V = ½[(a(v2,none) − a(s,none)) + (a(v2,mot) − a(s,mot))], M도 같은 식, 상호작용 V×M = [a(v2,mot) − a(v2,none)] − [a(s,mot) − a(s,none)].
- 요인마다 **채택** ⇔ (1) 전체 정확도 주효과 **≥ +0.02** 그리고 (2) 전이 층 정확도 주효과 **≥ −0.01** 그리고 (3) 결정 FULL p95 증가 **≤ 10 %**(V: (video2, none) / (single, none) − 1, M: (single, motion) / (single, none) − 1). 비교는 §74·§77 보충 2의 상대 CMP_EPS 1e-12.
- 상호작용은 전체·전이·정상 층 모두 보고한다(판정 밖). NLL 주효과도 보고한다(판정 밖).
- 판정 스크립트 `tools/se2e/temporal_verdict.py`(sha256 앞 16 `992d3e20198ca317`, 시험 `tests/test_se2e_temporal_verdict.py`) — 이 절의 문턱을 상수로 담았다. 결과 뒤 고치지 않는다.
- user-log 71 순서: (video2, none)이 끝나면 (single, none) 대비 **단순 효과**(전체·전이·지연)를 먼저 중간 보고한다 — 판정 밖 읽기이고, 채택 판정은 네 칸이 모두 끝난 뒤 위 규칙으로만.

## 7. 공통 설정
| 항목 | 값 |
|---|---|
| 코드 | 파드 `/data/harvest/code_se2e_temporal` = `/data/harvest/code_se2e_diag`(데이터 규모 판 사본) + 이 판 파일: `harvest/train/se2e_temporal.py`(sha256 앞 16 `d5babfb81ecdf64e`)·`se2e_temporal_model.py`(`28265152a392a400`)·`stageb_train.py`(`a79ed5473e74c345`, 옵션 추가; 기본값 동작은 그대로)·`tools/se2e_temporal.py`(`285a73200055414c`)·`tools/se2e/temporal_latency.py`(`a0dcafcfade80c70`)·`temporal_verdict.py`. **`stageb_data.py`(`be1e6214…`)·`stageb_model.py`(`5f3eba50…`)·`prefix_share.py`(`c231a0de…`)·`se2e_data.py`(`a08f7127…`)와 `PROMPT_FILES` 전부 무수정** → 기본 프롬프트 해시(`files_sha`)와 기본 동작 불변. 칸 폴더마다 `CODE_HASHES.txt` |
| 새 판 표지 | 카메라 배치 `D27v2-video2`(기본 `D27v1` 그대로), 움직임 줄 `se2e-motion@v1`. 옵션 판의 `prompt_config`는 `layout`·`motion`(구간 포함)과 옵션 파일(`se2e_temporal*.py`·`se2e_data.py`) 해시를 `files_sha`에 더해 기본 체크포인트와 섞이지 않는다. 런타임(`harvest/runtime`)은 건드리지 않았다 — 이 체크포인트는 폐루프에 쓰지 않는다 |
| 데이터 | `/data/harvest/data/se2e/conv`(읽기만) 행 + `/data/harvest/data/se2e_t/conv`(새: 같은 행 + `k_prev`·`dt_prev_s`·`images_prev`·`motion_src`, 원 필드 42,813행 전부 동일 확인, 과거 프레임 `img_prev/`). 현재 프레임은 원 변환 폴더에서 읽는다. train 37,484 / val 1,799 — 네 칸 같은 표본·같은 순서(키 목록 동일 확인) |
| 모델·손실 | S-E2E와 같음(Qwen3-VL-4B@`ebb281ec` + LoRA r32 + 흐름 정합 전문가 + aux·확인 헤드, KI stop, IMG 상태, λ 1/1/0.1/0.1), 기반 모델에서 새로 |
| 스케줄 | 네 칸 모두 **2,000스텝**, 묶음 8, lr LoRA·헤드 **1e-4**, 워밍업 3 % + 코사인 → 0, **시드 0**, 전체 train(부분집합 없음, ≈ 0.43 에폭), 평가 500스텝마다(0…2000) 같은 검증 300개 |
| (single, none) 칸 | **재사용**: `prereg_se2e_diag.md` §7의 N = 37,484 판(`/data/harvest/ckpt/se2e_scale/37484`, GPU 3, `code_se2e_diag`)이 같은 설정(`--data se2e --batch 8 --max-steps 2000 --lr 1e-4 --lr-heads 1e-4 --val-per-kind 150 --val-seed 0 --seed 0 --eval-every 500`, 부분집합 없음)이다. 이 판의 옵션 끔 경로는 그 코드와 같은 표본(실데이터 `off_equal` true)·같은 스텝 함수(`batch_fn` None)라 다시 돌리지 않는다. 재사용 조건: 그 판 `config` 사건의 args가 위 값과 같고 rc 0·step 2000 평가·`last/`가 있을 것, 그리고 이 사본으로 돌린 `predict`의 요약이 그 판 step 2000 평가 기록과 **같을 것**(다르면 이 사본에서 (single, none)을 새로 돌리고 그 값을 쓴다) |
| 실행 순서 | 데이터 규모 판 두 GPU가 모두 끝난 뒤(끼어들지 않음): GPU 2 = (video2, none), GPU 3 = (video2, motion), 먼저 끝난 GPU = (single, motion). 끝나면 네 칸 `predict`, 지연 측정(GPU 2). `OMP_WAIT_POLICY=PASSIVE`, `OMP_NUM_THREADS=8`, GPU 사용률 30 s 기록. GPU 0·1 사용 금지 |
| 출력 | `/data/harvest/ckpt/se2e_temporal/<cell>`(`video2_none`, `video2_motion`, `single_motion`), 로그 `/data/harvest/logs/se2e_temporal/` |

## 8. 하지 않는 것
- 기본 경로·프롬프트 해시 파일·`harvest/runtime`·`harvest/eval/common.py`·`harvest/train/stagea_data.py` 수정, `/data/harvest/data/se2e` 덮어쓰기, 커밋(메인 세션), GPU 0·1, 유료 API, CAL/TEST.
- 두 번째 시드·Δ = 0.1 s 칸·과거 프레임 드롭아웃(권고 문서가 언급) — 이번 등록 범위 밖. 필요하면 결과를 본 뒤 새 등록으로.
