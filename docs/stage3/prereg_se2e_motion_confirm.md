# S-E2E 움직임 줄 확인 (속도 누수 수정 판, 시드 2개 × 검증 전체) — 사전 등록 (2026-09-25T15:52:12Z, 학습 전)

작성 S-E2E 움직임 확인 에이전트. 정본 §83(user-log 80: 사용자가 움직임 줄 `se2e-motion@v1`을 결정 입력에 채택)의 "확인(권고)" 항목을 수행한다. 이 문서는 **어느 판도 학습하기 전에** 데이터 판본·설계·지표·판정 규칙을 고정한다. 결과를 본 뒤 문턱·층 정의·검증 집합·구간값을 바꾸지 않는다. 결과는 `docs/stage3/results/se2e_motion_confirm.md`.

## 0. 성격과 이미 본 것
- **확인 실험**이다. 채택은 이미 사용자 결정(§83)이고 이 판정은 채택을 뒤집지 않는다. "확인 안 됨"이면 채택은 그대로 두고 논문에 "확인되지 않았다"고 적는다. RB1 라이선스 미표기(§63 (6)) → 체크포인트 내부용.
- 등록 전에 본 것: (1) E-TC 결과(`se2e_temporal.md`: 시드 0, 검증 300, M 주효과 +0.025 [+0.003, +0.047], (single, none) 0.683 → (single, motion) 0.708), (2) 이 판의 데이터 점검(1절 — 입력·라벨·구간값만, 모델 출력 아님). 새 데이터 판본에서 돌린 모델 출력은 아직 없다.

## 1. 속도 누수 수정과 새 데이터 판본 `se2e_c1`
- **수정**: `harvest/train/se2e_data.finite_velocity`를 중앙 차분(`np.gradient`, 프레임 k+1 = 0.1 s 미래를 읽음)에서 **인과 후방 차분** v[k] = (x[k] − x[k−1]) × 10 Hz, **에피소드 첫 프레임 v[0] = 0**으로 바꿨다. 움직임 줄의 출처 `se2e_temporal.backward_velocity`와 같은 식이라 이제 행의 `proprio.qd`·`proprio.grip[1]` = `motion_src.qd_bwd`·`grip_rate_bwd`(전 행 비트 동일 확인). 시험(TDD, 먼저 실패 확인): `tests/train/test_se2e_data.py`(k+1 프레임을 바꿔도 k 행 속도 불변, 첫 프레임 0, 움직임 출처와 같음), `tests/train/test_se2e_reconvert.py`.
- **재변환**(`tools/se2e_convert.py reconvert --hist`, 새 명령): 원 변환 `/data/harvest/data/se2e/conv`(읽기만)의 행마다 parquet 상태에서 `episode_rows`를 다시 계산하고, **`proprio.qd`와 `proprio.grip[1]` 외의 모든 필드가 원 행과 같지 않으면 멈춘다**(라벨·행동·분할·이미지 경로 불변). 같은 행에 `se2e_temporal.hist_fields`(움직임 출처, 과거 프레임 경로)를 붙인다. 현재 프레임은 복사하지 않고 `se2e_c1/conv/img → /data/harvest/data/se2e/conv/img` 심볼릭 링크(프레임은 속도와 무관). `img_prev` 경로 문자열은 `se2e_t`와 같지만 이 판에서는 쓰지 않는다(단일 프레임 설계, 과거 프레임 미복사).
- **판본 id `se2e_c1`** (`/data/harvest/data/se2e_c1`, `SHA256SUMS.txt`):

| 파일 | sha256 앞 12 | 행 |
|---|---|---|
| `conv/RB1.stageb.jsonl` | `c4169181d556` | 25,433 (에피소드 718) |
| `conv/RB2.stageb.jsonl` | `45cd14ae3179` | 17,380 (에피소드 856) |
| `motion_bins.json` | `e164719a92d5` | 학습 37,484 |
| `transition_val.json` | `7bcfc8f609c2` | val 행 1,921, 전이 65.07 % |

- **점검**(`se2e_c1/check_c1.json`, `se2e_t` 대비): 42,813행 전부 `proprio.qd`·`grip[1]` 외 필드 동일, seed·k·split 동일, `motion_src` = `se2e_t`와 동일, 행 속도 = 움직임 출처(전부), k = 0 행 1,574개 속도 0. 속도가 바뀐 행 RB1 25,278·RB2 17,197(나머지는 정지 구간). 관절 속도 변화 노름 중앙값 RB1 0.053·RB2 0.048 rad/s, p95 0.174·0.180 rad/s; 그리퍼 속도 변화 중앙값 0, p95 0.149·0.138 (관절 단위/s).
- **분할·키 불변**: 로더 train 37,484 / val 1,799(판본 간 같음), train 키 sha `cf0f400ee688`, val 1,799 키 sha `f03062db4b1d`, 검증 300(`--val-per-kind 150 --val-seed 0`) 키 sha **`e22f6d8ef7fc`**(E-TC와 같음).
- **움직임 구간 재계산(같은 규칙: 팔 3분위, 그리퍼 |열림 속도| q0.85, 학습 분할)**: 팔 still < **0.2179** ≤ slow < **0.6070** ≤ fast rad/s, 그리퍼 **0.1755 /s** — **옛 값과 비트 동일**(파일 sha도 같음 `e164719a92d5`). 움직임 줄은 원래부터 원본 parquet에서 인과 후방 차분을 따로 뽑았기 때문이다(누수는 줄이 아니라 행동 전문가 고유감각 입력에만 있었다). 전이 층 플래그도 E-TC와 전부 같음(파일 sha 차이는 키 순서).
- 결정 프롬프트 입력은 판본 간 같다(맥락 문장은 그리퍼 **값**만 읽음). 바뀐 것은 행동 전문가의 고유감각 입력(qd·그리퍼 속도)이다.

## 2. 설계
- 데이터 `se2e_c1`, 칸 **(single, none)**과 **(single, motion)**, 시드 **1과 2** → 4판. 2프레임 비디오는 없음(단일 프레임).
- 스케줄은 E-TC와 같음: **2,000스텝**, 묶음 8, lr LoRA·헤드 **1e-4**, 워밍업 3 % + 코사인 → 0, 전체 train(부분집합 없음), 평가 500스텝마다 검증 300(`--val-per-kind 150 --val-seed 0`). motion 칸은 `--motion-line se2e-motion@v1 --motion-bins se2e_c1/motion_bins.json`, 학습 때 줄 드롭아웃 p 0.3(기본값, 난수 (시드, 스텝)), 평가에서는 끄지 않음.
- 모델·손실은 S-E2E·E-TC와 같음(Qwen3-VL-4B + LoRA r32 + 흐름 정합 전문가 + aux·확인 헤드, KI stop, IMG 상태, 기반 모델에서 새로).
- 예측: 각 판 step 2000 `last/`로 `stageb_train predict`(고정 잡음 시드 0, E-TC와 같음)를 **검증 300**(`--val-per-kind 150`)과 **검증 전체 1,799**(`--val-per-kind 0`) 두 번.
- 실행: 파드 `juhyoung-native-7a2a`, **GPU 2** = none_s1 → motion_s1, **GPU 3** = none_s2 → motion_s2(각 GPU 순차). `OMP_WAIT_POLICY=PASSIVE`, `OMP_NUM_THREADS=8`. GPU 0·1 사용 금지. GPU가 다른 작업에 쓰이면 비기를 기다린다(아무것도 죽이지 않음). GPU 사용률 30 s 기록.

## 3. 지표
- 항목 = 스냅샷 × 3질문(dir_xy·dir_z·mag_coarse). 결정 정확도 `acc`(항목 argmax 정답률)와 NLL(보기 집합 재정규화 −log p(정답)), **전체·전이 층·정상 층**(층 정의는 E-TC 사전 등록 4절 그대로: 어떤 질문의 프레임 단위 라벨이 k와 k+1..k+3 사이에서 바뀌면 전이).
- 시드 s의 효과 e_s = acc(motion, s) − acc(none, s). **합동 효과** = ½(e_1 + e_2).
- 스냅샷 군집 부트스트랩: 스냅샷을 복원 추출(네 판에 같은 추출), 추출마다 합동 효과, 10,000회, 시드 0, 95 % 백분위.
- 시드 간 변동: e_2 − e_1(층별), (none) 칸끼리·(motion) 칸끼리의 시드 간 정확도 차.

## 4. 판정 규칙 (고정)
- **검증 전체 1,799**에서: **확인됨** ⇔ (1) 합동 전체 효과 **≥ +0.015** 그리고 (2) 그 부트스트랩 95 % 하한 **> 0** 그리고 (3) 합동 전이 층 효과 **≥ −0.01**. 하나라도 어기면 **확인 안 됨**(보고; 사용자 채택은 유지, 논문에는 확인되지 않았다고 적는다). 문턱 비교는 §74·§77 보충 2의 상대 CMP_EPS 1e-12(하한 > 0은 엄격 비교).
- 검증 300 결과, NLL, 정상 층, 질문별 값, 시드별 효과는 보고만 한다(판정 밖).
- 판정 스크립트 `tools/se2e/motion_confirm_verdict.py`(sha256 앞 16 `fa7299062cc5e1d1`, 시험 `tests/test_se2e_motion_confirm_verdict.py`) — 이 절의 문턱을 상수로 담았다. 결과 뒤 고치지 않는다.

## 5. 공통 설정
| 항목 | 값 |
|---|---|
| 코드 | 파드 `/data/harvest/code_se2e_confirm` = `git archive` HEAD(`874cb338`) + 이 판 변경(LF): `harvest/train/se2e_data.py`(sha256 앞 16 `c6adc96fbd312984`), `tools/se2e_convert.py`(`1438b8f7dd594ff2`), `tools/se2e/motion_confirm_verdict.py`(`fa7299062cc5e1d1`), 시험 3개. 판 폴더마다 `CODE_HASHES.txt` |
| 무수정 | `harvest.train.stagea_train.PROMPT_FILES` 전부·`stageb_data.py`(`a61a7cf67f9b5066`)·`stageb_model.py`(`255c78cfd4d3e4df`)(§71), `se2e_temporal.py`(`9fd650fc59ba7982`), `stageb_train.py`, `harvest/runtime` |
| 새 판 표지 | (single, motion) 판의 `prompt_config`는 옵션 파일 해시에 `se2e_data.py`를 넣으므로 E-TC 판과 sha가 다르다(의도) |
| 출력 | `/data/harvest/ckpt/se2e_confirm/<cell>_s<seed>`(`none_s1`, `motion_s1`, `none_s2`, `motion_s2`), 로그·예측·판정 `/data/harvest/logs/se2e_confirm/`(`run.sh`, `pred300_*.jsonl`, `predfull_*.jsonl`, `verdict_full.json`, `verdict_300.json`), 로컬 사본 `D:\tools\scratch_qdd\se2e_confirm` |

## 6. 하지 않는 것
- `/data/harvest/data/se2e`·`/data/harvest/data/se2e_t` 덮어쓰기, `PROMPT_FILES`·`stageb_data.py`·`stageb_model.py`·`harvest/runtime` 수정, 2프레임 비디오 칸, 시드 0 재실행, GPU 0·1, 유료 API, CAL/TEST, 커밋(메인 세션).
