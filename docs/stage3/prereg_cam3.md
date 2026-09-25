# E-CAM3 VLA 결정 입력에 양 손목 카메라 — 사전 등록 (2026-09-25T20:30:33Z, 학습 전)

작성 E-CAM3·E-MA3 에이전트. 설계 근거: 결합 설계 §12 끝 항목(`docs/superpowers/specs/2026-09-26-astra-vla-coupling-design.md`, `d6d9c20`, user-log 83 "VLA도 사진을 보는것도 좋을 것 같구"). 이 문서는 **어느 cam3 판도 학습하기 전에** 입력 정의·설계·판정 규칙·자체 검사 관문을 고정한다. 결과는 `docs/stage3/results/cam3.md`. 같은 시각에 E-MA3(`prereg_ma3.md`)가 GPU 3에서 따로 돈다(서로 다른 판, 같은 기준 체크포인트를 읽기만 함).

## 0. 성격, 이미 본 것, 자체 검사(user-log 87, CLAUDE.md)
- 확인형 요인 실험. 시드 2개 × 검증 전체 1,799 스냅샷, 기준 = 움직임 줄 확인 실험의 `motion_s1`·`motion_s2`(E-MA1b와 같은 짝 재사용 방식). RB1 라이선스 미표기(§63 (6)) → 체크포인트 내부용.
- **먼저 한 확인(등록 전, 결과 아님)**: ROBOTIS 데이터가 양 손목 영상을 담는가 → **담는다.** 원본 `verify.json`에서 손목 영상이 빠진 에피소드는 RB2 200편(617–816)뿐이고 그때는 **두 손목이 함께** 빠진다(기준 로더가 이미 건너뜀). 기준이 쓰는 39,283행(RB1 25,433 + RB2 13,850) 전부에서 반대 손목 영상이 있고 프레임 수가 모자란 행 0(`/data/harvest/logs/cam3/feasibility.json`; 양팔 행 3,106은 이미 두 손목). 변환은 활성 손목만 풀어 두었으므로 반대 손목 36,177장을 새로 풀었다(4절) — "S-E2E에서 시험 불가"가 아니다.
- **이미 본 것(결과 쪽)**: 기준 재사용 판의 결과 — `results/se2e_motion_confirm.md`(motion_s1 0.7067·motion_s2 0.7076, 합동 효과 부트스트랩 반폭 약 0.010, 시드 간 효과 차 0.004)와 `results/ma1b.md`. 문턱(+0.02, 하한 > 0, 전이 ≥ −0.01, FULL p95 ≤ +10 %)은 **설계 §12(`d6d9c20`, 2026-09-25 16:41 UTC)가 이 값들보다 먼저 정했고** 여기서 바꾸지 않았다. 20스텝 사전 실행(파이프라인 확인, 결과 아님)의 출력은 봤다(0.3절). cam3 본 판의 출력은 아직 없다.
- **이 결과로 바뀌는 결정**: 채택이면 융합 VLA 결정 입력을 머리 + 양 손목(§57 개정 후보, 시각 토큰 약 +29 %)으로 바꾸는 정본 보충과 런타임 직렬화 판본 작업을 연다(런타임은 이 실험에서 건드리지 않음). 불채택이면 §57(머리 + 활성 손목)을 유지하고, 양 손목은 Astra 요청(§12)에만 쓴다.
- **이 표본으로 가를 수 있는가**: 같은 데이터·스케줄·시드·검증 1,799에서 두 시드 합동 효과의 부트스트랩 95 % 반폭 ≈ 0.010, 시드 간 효과 차 0.004–0.009(전체·전이). **+0.02 크기면 하한 > 0으로 가를 수 있고**, 0 근처면 분명히 불채택이다. 가를 수 없는 구간은 점 추정 +0.010–0.020(규칙상 불채택, "작은 효과 가능성"으로 보고). 지연 조건은 같은 표본 50개 × 4회 교차 측정(E-TC와 같은 도구 방식)으로 p95 비율이 10 %에서 멀면 분명하다; 10 % 근처(±2 %)면 한 번 더 재지 않고 규칙대로 판정하고 보고서에 근접을 적는다.
- **싼 사전 실행**(0.3절): 20스텝(학습 64·검증 원천별 5) + 예측 + 지연 도구 소규모.
- **도중 관문(멈추고 재설계 → 이 문서 8절에 UTC와 함께 기록·커밋 → 재개)**: (1) 기준 재사용 비트 동일 검사 실패 → none 두 판을 이 코드로 새로 학습(4판), (2) NaN·발산(학습 기록 `total`이 NaN, 또는 step ≥ 500 검증 `dec`가 step 0보다 큼), (3) 판 하나의 학습이 예상의 2배 초과(예상 약 45분 = motion_s1 2,222 s × 시각 토큰 증가분 → **90분 초과**면 멈춤), (4) 실행 경로 검사 실패(5절).
- 비용: 유료 API 0건. GPU 2만(GPU 0·1 = R2_TRAIN Isaac 작업자, GPU 3 = E-MA3).

### 0.3 사전 실행 결과(등록 전, 파이프라인 확인)
- 2026-09-25 20:22–20:25 UTC, 개발 사본 `/data/harvest/tmp/cam3ma3/repo`, GPU 2: 20스텝(학습 64, 검증 원천별 5) rc 0 — `cam3_apply` 39,283표본 중 36,177에 반대 손목 덧붙임·양팔 3,106 그대로, 학습 손실 유한(step 1 total 5.68 → step 20 3.74), 저장·예측 rc 0(항목 30 + 요약). 지연 도구 소규모(4표본 × 1회) rc 0 — 시각 토큰 **356 → 460**(설계 §12 추정과 같음), 문맥 프롬프트 토큰 평균 463.5 → 576.5. 정확도·지연 비율 값은 파이프라인 확인용이라 판정·문턱에 쓰지 않는다. 로그 `/data/harvest/logs/cam3/dry/`.
- 시험: 로컬 전체 1,132 통과·20 건너뜀(torch 없는 로컬), 파드(작은 Qwen3-VL, CPU) `tests/train/test_se2e_cam3_cli.py` 4개 + `test_se2e_cam3.py` 8개 통과(세 이미지 표본의 공유 접두 경로 = 문맥별 경로 포함).

## 1. 질문
결정 입력에 반대 손목 영상을 더하면(머리 + 활성 손목 → 머리 + 양 손목), 움직임 줄을 켠 S-E2E 결정 정확도가 오르는가, 그 대가로 결정 지연이 얼마나 느는가.

## 2. 입력 정의 `cam3@v1` (`harvest/train/se2e_cam3.py`)
- 한 손 행: 이미지 목록 = **[머리, 활성 손목(기준과 같은 이름표), 반대 손목]**, 반대 손목 이름표 `"<left|right> wrist camera (other arm):"`. 앞 두 이미지와 이름표는 기준과 **완전히 같고** 세 번째가 덧붙는다(순서 효과를 줄이려고 기준 접두를 보존). 양팔 행(이미 머리 + 오른 + 왼 손목, 3,106행)은 그대로.
- 프레임: 같은 k의 반대 손목 원본 영상 프레임, `tools/se2e_convert.py`와 **같은 디코더·회전(RB1 손목 90° 시계)·JPEG 품질 90**. 없는 프레임은 오류(0장).
- 프롬프트 설정 `prompt_config`에 `cam3: cam3@v1`, `layout3: D27v3-cam3`, 옵션 파일 해시를 더해 sha를 바꾼다(기준 체크포인트와 섞이지 않음). 텍스트 줄(과제·그리퍼·팔·움직임 줄)과 질문은 불변.

## 3. 설계
- 판: **cam3 시드 1·2**(`cam3_s1`, `cam3_s2`) 새로 학습. 기준 = `/data/harvest/ckpt/se2e_confirm/motion_s{1,2}` 재사용(짝: 같은 시드 = 같은 데이터 순서·같은 움직임 줄 드롭아웃 난수).
- **기준 재사용 조건(하나라도 어기면 none 두 판을 이 코드로 새로 학습)**: (1) 기준 `config.args`가 cam3 판 인자와 `run`·`out_root`·`cam3`·`cam3_root` 밖에서 전부 같음, (2) 이 등록 커밋의 코드 사본(LF)으로 기준 `last/`를 `predict --val-per-kind 0`(검증 1,799)한 항목 기록·요약이 `logs/se2e_confirm/predfull_motion_s<s>.jsonl`과 `utc` 밖 **비트 동일**, (3) 기준 학습 경로 파일(`stageb_train.py` 등)은 이 판에서 **무수정**(옵션은 새 파일의 CLI 포장 `python -m harvest.train.se2e_cam3`이 `stageb_train`의 `_load_data`·`prompt_config_t`를 옵션 켬일 때만 감싼다).
- 스케줄(기준과 같음): Qwen3-VL-4B@`ebb281ec` + LoRA r32 + 흐름 정합 expert + aux·확인 헤드, KI stop, λ 1/1/0.1/0.1, **2,000스텝, 묶음 8, lr 1e-4/1e-4, 워밍업 3 % + 코사인, 시드 1·2**, `--data se2e --se2e-root/--se2e-t-root se2e_c1/conv --motion-line se2e-motion@v1 --motion-bins se2e_c1/motion_bins.json --cam3 cam3@v1 --cam3-root /data/harvest/data/cam3`, 평가 500스텝마다 검증 300(`--val-per-kind 150 --val-seed 0`).
- 실행: 파드 `juhyoung-native-7a2a` **GPU 2**, 기준 재사용 예측 → `cam3_s1` → `cam3_s2`(각 학습 + 검증 1,799 예측, 잡음 시드 0) → 지연. `OMP_WAIT_POLICY=PASSIVE`, `OMP_NUM_THREADS=8`. 드라이버 `/data/harvest/logs/cam3/run_cam3.sh`.

## 4. 데이터(등록 전 준비, 결과 아님)
- `tools/cam3/build_cam3.py` → `/data/harvest/data/cam3/img_cam3/<kind>/ep<N>/k<K>_<cam>.jpg`: RB1 22,378장(718편)·RB2 13,799장(656편), 빠진 프레임 0. **같은 방식 확인**: 원본 에피소드 원천별 20편의 활성 손목 프레임 881장을 같은 코드로 다시 풀어 기존 변환 JPEG와 **바이트 동일**(불일치 0) — 방향·색인·품질이 기준 프레임과 같다. 기록 `/data/harvest/data/cam3/build_cam3.json`, `logs/cam3/build_cam3.out`. `se2e_c1` 행 파일은 읽기만.

## 5. 실행 경로 동일성
- (a) 이 판 변경은 새 파일뿐 — `harvest/runtime`·`PROMPT_FILES`·`PROMPT_FILES_B`(`stageb_data.py`·`stageb_model.py`)·`stageb_expert.py`·`prefix_share.py`·`stageb_train.py`·`se2e_data.py`·`se2e_temporal*.py` 무수정(`git diff` 확인). (b) 시험: 옵션 끔일 때 CLI 포장의 인자 = `stageb_train` 인자(옵션 키 밖), `stageb_train` 함수가 바뀌지 않음(`test_se2e_cam3_cli.py`); 세 이미지 표본의 공유 접두(R3) 경로 = 문맥별 경로(작은 Qwen3-VL, 상대 1e-4). (c) 파드: 기준 재사용 비트 동일(3절 (2))이 기본 경로가 그대로임을 보인다.

## 6. 지표와 판정 규칙 (고정)
- 항목 = 스냅샷 × 3질문. 정확도·NLL, 전체·전이 층·정상 층(전이 층 = E-TC 사전 등록 4절, `se2e_c1/transition_val.json` sha 앞 12 `7bcfc8f609c2`).
- 시드 s 효과 e_s = acc(cam3, s) − acc(none, s), **합동 = ½(e₁ + e₂)**. 스냅샷 군집 부트스트랩 10,000회(시드 0, 네 판 같은 추출, 95 % 백분위).
- 지연: `tools/cam3/cam3_latency.py` — `tools/se2e/temporal_latency.py`와 같은 방식(결정 1회 = `forward_shared([표본])`, FULL = 이미지 읽기·전처리·토큰화·GPU 순전파, cuda 동기, 묶음 1, 움직임 줄 켬, 같은 검증 한 손 스냅샷 50개(원천별 25, 시드 0), 두 형식 교차, 예열 30, 4회), 가중치 = motion_s1(계산량은 가중치와 무관), GPU 2.
- **채택** ⇔ (1) 합동 전체 효과 **≥ +0.02** 그리고 (2) 부트스트랩 95 % 하한 **> 0** 그리고 (3) 합동 전이 층 효과 **≥ −0.01** 그리고 (4) FULL p95(cam3) / FULL p95(cam2) − 1 **≤ 0.10**. 상대 CMP_EPS 1e-12(하한 > 0은 엄격). 검증 1,799에서만.
- 판정 밖(보고 의무): NLL·정상 층·질문별, 원천별(RB1·RB2) 합동 효과, 시드별 효과·차이, GPU p50/p95, 시각 토큰 수(평균·범위), 학습 시간.
- 판정 스크립트 `tools/cam3/cam3_verdict.py`(공통부 `tools/se2e/paired_verdict.py`, 시험 `tests/test_paired_verdicts.py` — 경계값 포함). 입력 검사: 네 판 키 집합 같음·1,799개·(키, 질문) 중복 없음·항목 기록이 요약을 재현. 결과 뒤 고치지 않는다.
- **해석 한계**: 결정 라벨은 휴리스틱(활성 팔 말단 변위)이고 반대 손목은 대개 쉬는 팔을 본다 → 이득이 없어도 "파지 판단에 손목 근거" 가설(§12)의 반증은 아니다(이 라벨은 파지·접촉을 묻지 않음). 채택이어도 §56 소규모 학습(2,000스텝) 결과다.

## 7. 코드·출력
| 항목 | 값 |
|---|---|
| 이 등록과 함께 고정(LF 블롭 sha256 앞 16) | `harvest/train/se2e_cam3.py` `de4089a955fb408f`, `tools/cam3/build_cam3.py` `04c20ad0b8921f3a`, `tools/cam3/cam3_latency.py` `3d6a2c6d6a6c818a`, `tools/cam3/cam3_verdict.py` `0c2366dae76e3077`, `tools/se2e/paired_verdict.py` `37422bb2912fbfbc`, `tests/train/test_se2e_cam3.py` `cfa0f7cb5812ca11`, `tests/train/test_se2e_cam3_cli.py` `74f6449f55156cac`, `tests/test_cam3_build.py` `eebabe67a85f2bdb`, `tests/test_paired_verdicts.py` `0bcbd90658797afe` |
| 코드 사본 | 파드 `/data/harvest/code_cam3` = `git -c core.autocrlf=false archive` 이 등록 커밋(LF), 판 폴더마다 `CODE_HASHES.txt` |
| 출력 | 체크포인트 `/data/harvest/ckpt/cam3/cam3_s<seed>`, 로그·예측·지연·판정 `/data/harvest/logs/cam3/`, 데이터 `/data/harvest/data/cam3/`, 로컬 요약 `D:\tools\scratch_qdd\cam3_ma3` |

## 8. 하지 않는 것 / 변경 기록
- 하지 않음: 시드 0·검증 300 판정, 이미지 해상도·순서 변형, 런타임 직렬화 변경, 기준·`se2e_c1` 덮어쓰기, GPU 0·1·3, 유료 API.
- 변경 기록: (없음 — 변경은 UTC 시각과 사유를 여기에 적는다.)
