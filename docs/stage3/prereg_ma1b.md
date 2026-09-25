# E-MA1b 로봇 기준 좌표 미래 손끝 궤적 보조 손실(A3d) — 사전 등록 (2026-09-25T17:54:05Z, 학습 전)

작성 E-MA1 에이전트. E-MA1(`prereg_ma1.md`)의 관문 G0가 실패했고(명목 중앙값 100.9 px, PnP 뒤 86.9 px, 문턱 12 px — `results/ma1.md`), 등록된 대체 경로인 R2_TRAIN은 아직 준비되지 않았다. 메인 결정(2026-09-25, user-log 85 "옳은 방향으로 바꿔도 돼")에 따라 **카메라가 필요 없는 형태로 요인 A만** S-E2E에서 먼저 잰다. 이력 덧그림(O)과 영상 좌표 궤적(trace5)은 R2_TRAIN 뒤 E-MA1 재등록으로 남긴다. 이 문서는 **어느 A3d 판도 학습하기 전에** 목표 정의·설계·판정 규칙·자체 검사 관문을 고정한다. 결과는 `docs/stage3/results/ma1b.md`.

## 0. 성격, 이미 본 것, 자체 검사(user-log 87, CLAUDE.md)
- 확인형 요인 실험이다. 시드 2개 × 검증 전체 1,799 스냅샷. RB1 라이선스 미표기(§63 (6)) → 체크포인트 내부용.
- **이미 본 것(결과 쪽)**: 기준 칸으로 재사용할 움직임 줄 확인 실험의 결과 — `motion_s1` 검증 300 dec_acc **0.6956**(E-MA1 등록 때 우연히 봄), 이 등록을 쓰며 그 실험의 판정 파일에서 검증 1,799 정확도 `motion_s1` **0.7067**·`motion_s2` **0.7076**, 시드 간 효과 차이 −0.004, 부트스트랩 95 % 폭 ±0.010을 보았다. **문턱(+0.02, 하한 > 0, 전이 ≥ −0.01)은 메인이 이 값들을 보기 전에 정했고**(E-MA1 초안·움직임 줄 확인 규칙과 같은 틀) 여기서 바꾸지 않았다. A3d 판의 출력은 아직 없다.
- **이 결과로 바뀌는 결정**: 채택이면 본 학습(단계 B) 레시피에 A3d 보조 손실을 넣는다(학습 때만, 실행 경로·지연·프롬프트 불변). 불채택이면 S-E2E 기반 궤적 보조 손실은 레시피에서 빼고, 궤적 보조는 R2(카메라 정확) E-MA1 재등록의 trace5로만 다시 본다. steering 문서 E-SR1의 궤적 요인도 이 결과로 대체된다(§84).
- **이 표본으로 가를 수 있는가**: 움직임 줄 확인 실험(같은 데이터·스케줄·시드 1·2·검증 1,799)의 두 시드 합동 효과 부트스트랩 95 % 반폭 ≈ 0.010, 시드 간 효과 차이 0.004. 따라서 **+0.02 크기의 효과는 하한 > 0으로 가를 수 있고**(점 추정 0.02면 하한 ≈ +0.01), 효과가 0 근처면 불채택으로 분명히 떨어진다. 가를 수 없는 구간은 점 추정 +0.010–0.020(하한은 넘어도 점 문턱 미달) — 이 경우도 규칙상 불채택이며 "작은 효과 가능성"으로 보고한다.
- **싼 사전 실행**: 본 학습 전에 GPU 2에서 A3d 옵션으로 20스텝 소규모 판(학습 표본 64, 검증 원천별 5)을 돌려 (a) 보조 손실이 유한하고 줄어드는지, (b) 저장·재적재·예측이 되는지, (c) 학습 보기·기본 보기 예측 기록이 같은지를 먼저 확인한다. 실패하면 고치고 이 문서에 기록한 뒤 본 판을 시작한다.
- **도중 관문(멈추고 재설계, 변경은 UTC 시각과 함께 이 문서에 기록)**: (1) 기준 재사용 검사 실패 → 기준 두 판도 새로 학습(4판), (2) 보조 손실 NaN/발산(학습 기록의 `aux`가 NaN이거나 step 500 이후 초기값의 2배 초과), (3) 판 하나가 예상(약 37분, motion_s1 2,222 s)의 2배(75분) 초과, (4) 실행 경로 동일성 검사 실패.
- 비용: 유료 API·Astra 호출 0건(상한 0원). GPU 2만(GPU 3은 탐침의 Qwen 서버, GPU 0·1은 렌더 전용).

## 1. 질문
미래 손끝 궤적을 **로봇 기준 좌표(URDF FK, `arm_base_link`)** 의 보조 회귀 목표로 배우면, 움직임 줄(§83)을 켠 S-E2E 결정 정확도가 오르는가. 카메라 투영이 없으므로 G0의 카메라 오차는 들어오지 않는다.

## 2. A3d 목표 `aux: a3d@v1` (`harvest/train/se2e_a3d.py`)
- 점 p₁…p₅ = 활성 팔 손끝(`end_effector_{l|r}_link`)의 프레임 k + i·(e − k)/4(i = 0…4, FK 위치 선형 보간). 구간 끝 e = E-MA1과 같은 규칙(`se2e_trace.event_end`): k 뒤 처음으로 그리퍼 열림/닫힘 상태(프롬프트 규칙: 관절값 > 0.5 = 닫힘)가 k와 달라지는 프레임, 없으면 에피소드 끝, 상한 3 s(30프레임).
- 목표 = **p₂…p₅ − p₁**(현재 손끝 기준 xyz 변위, m, 4점 × 3 = 12값). p₁은 현재 손끝이라 변위가 항상 0이므로 회귀 출력에서 뺀다(5점 정의는 그대로, 학습되는 값은 12개). 마스크: 미래가 없으면(e = k, 에피소드 마지막 프레임) 4점 모두 0; 정의상 점이 에피소드 끝을 넘지 않는다(넘으면 마스크 0).
- 손실: 기존 `AuxGeomHead`(질의 4·폭 512·머리 8, 기울기 백본까지 — §58)의 회귀 출력을 11 → 23으로 늘린다(`se2e_trace_model.py`, `a3d@v1`). 단위 = m / **0.05**(`AUX_REG_SCALE`, 기존 aux와 같음), 마스크 smooth-L1, **λ_aux 0.1**. S-E2E 행의 원래 aux 목표는 모두 마스크 0 → aux 손실 = A3d 손실.
- 데이터: `/data/harvest/data/ma1b/conv/<kind>.a3d.jsonl`(도구 `tools/ma1/build_a3d.py`, 원본 parquet 10 Hz 전 프레임에서; `se2e_c1`는 읽기만). 모든 행에서 FK(k + label_steps) − FK(k)가 행의 `ee_delta`와 2e-5 m 안에서 같아야 한다(결정 라벨과 같은 FK·프레임 색인 확인, 어기면 멈춤).

## 3. 설계
- 판: **A3d 시드 1·2**(`a3d_s1`, `a3d_s2`) 새로 학습. **기준 = 움직임 줄 확인 실험의 `motion_s1`·`motion_s2` 재사용**(`/data/harvest/ckpt/se2e_confirm/`, `se2e_c1`, 움직임 줄 켬, 같은 시드) — 짝 비교(같은 시드 = 같은 데이터 순서·같은 움직임 줄 드롭아웃 난수).
- **기준 재사용 조건(모두 만족, 하나라도 어기면 `none_s1`·`none_s2`를 이 판 코드로 새로 학습해 4판)**: (1) 그 판 `config.args`가 A3d 판 인자와 `run`·`out_root`·`aux_extra`·`a3d_root` 밖에서 **전부 같음**(묶음 8, 2,000스텝, lr 1e-4/1e-4, 코사인, 워밍업 3 %, 시드, `--val-per-kind 150 --val-seed 0`, 움직임 줄·구간 파일·드롭아웃 0.3, `se2e_c1` 경로), (2) 이 판 코드 사본으로 그 판 `last/`를 `predict --val-per-kind 0`(검증 1,799)한 항목 기록이 그 실험의 `predfull_motion_s<s>.jsonl`과 **`utc` 밖 모든 필드 비트 동일**(요약 포함), (3) 학습 경로 코드가 줄 끝(그 사본은 CRLF, 이 판은 LF) 밖에서 같음 — `stageb_train.py`의 새 옵션은 끔일 때 동작 불변(시험), 나머지 학습 파일은 내용 동일.
- A3d 판이 기준과 다른 점: aux 머리 회귀 출력 23(다른 매개변수 초기화 뒤에 만들어짐 — 백본·LoRA·expert·확인 헤드 초기값은 기준과 같은 난수 흐름), aux 손실 항. 데이터·순서·드롭아웃·평가 집합 동일.
- 스케줄(기준과 같음): Qwen3-VL-4B@`ebb281ec` + LoRA r32 + 흐름 정합 expert + aux·확인 헤드, KI stop, IMG, λ 1/1/0.1/0.1, **2,000스텝, 묶음 8, lr 1e-4, 워밍업 3 % + 코사인, 시드 1·2**, `--data se2e --se2e-root se2e_c1/conv --se2e-t-root se2e_c1/conv --motion-line se2e-motion@v1 --motion-bins se2e_c1/motion_bins.json --aux-extra a3d@v1 --a3d-root /data/harvest/data/ma1b/conv`, 평가 500스텝마다 검증 300.
- 실행: 파드 `juhyoung-native-7a2a` **GPU 2**, `a3d_s1` → `a3d_s2` 순차(약 1.3 GPU시간 + 예측). `OMP_WAIT_POLICY=PASSIVE`, `OMP_NUM_THREADS=8`. 다른 작업이 GPU 2를 쓰면 기다린다(아무것도 죽이지 않음).
- 예측: 각 판 `last/`로 `predict --val-per-kind 0`(검증 1,799, 고정 잡음 시드 0) + `--extra-out`(보조 오차 cm·예측 보기 조건 청크 오차). 기준 두 판도 같은 코드로 예측(재사용 검사 겸).

## 4. 실행 경로 동일성 (A3d는 학습 전용 머리)
- (a) 이 판 변경은 옵션 파일(`se2e_a3d.py`, `se2e_trace_model.py`)과 `stageb_train.py` 옵션뿐 — `harvest/runtime`·`PROMPT_FILES`·`PROMPT_FILES_B`(`stageb_data.py`·`stageb_model.py`)·`stageb_expert.py`·`prefix_share.py`·`se2e_data.py`·`se2e_temporal*.py` 무수정(`git diff` 확인). (b) 시험 `test_base_view_decides_identically`: 같은 체크포인트를 학습 보기(`StageBTrace`)와 기본 보기(`StageB`, aux 머리는 기본 11회귀만 답함)로 평가하면 결정 항목 기록·청크가 **비트 동일**. (c) 파드: `a3d_s1` `last/`를 `predict --aux-view trained`와 `--aux-view base`로 검증 300에 돌려 항목 기록(`utc` 밖) 비트 동일.
- 프롬프트·질문·`question_id@vN`·이미지 입력 불변. `prompt_config`에 `aux: a3d@v1`과 옵션 파일 해시를 더해(없을 때는 키 자체가 없어 기본과 같음) 체크포인트가 섞이지 않게 한다; `stageb.json`에 `aux_extra`.

## 5. 지표와 판정 규칙 (고정)
- 항목 = 스냅샷 × 3질문. 정확도·NLL, **전체·전이 층·정상 층**(전이 층 = E-TC 사전 등록 4절, `se2e_c1/transition_val.json` sha 앞 12 `7bcfc8f609c2`).
- 시드 s 효과 e_s = acc(a3d, s) − acc(none, s)(짝), **합동 효과 = ½(e₁ + e₂)**. 스냅샷 군집 부트스트랩 10,000회(시드 0, 네 판 같은 추출, 95 % 백분위).
- **채택** ⇔ (1) 합동 전체 효과 **≥ +0.02** 그리고 (2) 그 부트스트랩 95 % 하한 **> 0** 그리고 (3) 합동 전이 층 효과 **≥ −0.01**. 문턱 비교는 상대 CMP_EPS 1e-12(하한 > 0은 엄격). 검증 전체 1,799에서만 판정.
- 판정 밖(보고 의무): NLL·정상 층·질문별, **원천별(RB1·RB2) 정확도와 합동 효과**, 시드별 효과·차이, 보조 오차(cm, 점별 평균·중앙값), 예측 보기 조건 청크 오차.
- 판정 스크립트 `tools/ma1/ma1b_verdict.py`(시험 `tests/test_ma1b_verdict.py`) — 이 절의 문턱을 상수로 담았다. 결과 뒤 고치지 않는다.
- **해석 한계(§84 보충 1, 등록)**: A3d 목표는 결정 라벨(미래 손끝 변위에서 규칙으로 만든 것)과 같은 정보를 더 촘촘한 연속값으로 준다 → 이득은 "같은 정보의 더 촘촘한 감독"일 수 있다. **일반화 주장(가설 H1)의 근거로 쓰지 않는다.** 원천별 정확도를 함께 보고한다.

## 6. 코드·출력
| 항목 | 값 |
|---|---|
| 이 등록과 함께 고정(LF 블롭 sha256 앞 16) | `harvest/train/se2e_a3d.py` `82353d67324e7215`, `harvest/train/se2e_trace_model.py` `67f7eab56c13f822`, `harvest/train/stageb_train.py` `98ff930ccb787ffe`, `tools/ma1/build_a3d.py` `8597de82548d2a40`, `tools/ma1/ma1b_verdict.py` `6bc198bfbab5d8ff`; 시험 `tests/train/test_se2e_a3d.py`, `tests/train/test_se2e_a3d_cli.py`, `tests/train/test_se2e_trace_model.py`, `tests/test_ma1b_verdict.py`, `tests/test_ma1b_build.py` |
| 코드 사본 | 파드 `/data/harvest/code_ma1b` = `git -c core.autocrlf=false archive`(LF) 이 등록 커밋, 판 폴더마다 `CODE_HASHES.txt` |
| 출력 | 체크포인트 `/data/harvest/ckpt/ma1b/a3d_s<seed>`(+ 필요 시 `none_s<seed>`), 로그·예측·판정 `/data/harvest/logs/ma1b/`, 데이터 `/data/harvest/data/ma1b/`, 작업 `/data/harvest/tmp/ma1b`, 로컬 사본 `D:\tools\scratch_qdd\ma1` |

## 7. 하지 않는 것
- 이력 덧그림(O)·영상 좌표 궤적(trace5)·카메라 보정 — R2_TRAIN 뒤 E-MA1 재등록. 시드 0 판, 검증 300 판정, 지연 측정(실행 경로 불변을 4절로 확인하므로 지연은 기준과 같다). `se2e`·`se2e_t`·`se2e_c1`·움직임 줄 확인 체크포인트 덮어쓰기, `harvest/runtime`·프롬프트 해시 파일 수정, GPU 0·1·3, 유료 API, CAL/TEST.

## 8. 변경 기록
- (없음 — 변경은 UTC 시각과 사유를 여기에 적는다.)
