# E-MAR-real 요인 A — MolmoAct식 2D 손끝 궤적 보조 손실(실데이터 포인팅 라벨) — 사전 등록 (학습 전)

작성 E-MAR-real 에이전트, 2026-09-26 UTC. 메인 지시(user-log 105 "go"): **요인 A만** 실행한다. 이력 덧그림 O는 보류 — 런타임 손끝 점(명목 투영 + 편별 오프셋)의 절대 오차 중앙값이 51 px라 덧그림으로 쓰기에 부정확하다(`molmoact_real_readiness.md` 4.2). 이 문서는 **어느 A 판도 학습하기 전에**(20스텝 사전 실행 포함) 라벨 규칙·설계·판정 규칙·관문·변경 절차를 고정한다. 초안 = `docs/stage3/molmoact_real_readiness.md` 6절(2×2); 이 등록이 그 초안을 A 단독으로 대체한다. 결과는 `docs/stage3/results/marr.md`.

## 0. 성격, 이미 본 것, 자체 검사(user-log 87, CLAUDE.md)

- 확인형 요인 실험. 시드 2개 × 검증 전체 1,799 스냅샷(E-MA1b와 같은 틀). RB1·RB2 라이선스 미표기(§63 (6)) → 체크포인트 내부용. 유료 API 0원.
- **이미 본 것(결과 쪽)**: 기준 C0로 재사용할 `motion_s1`·`motion_s2`의 검증 1,799 정확도(0.7067·0.7076)와 원천별 값(RB2 0.6981·0.6894), E-MA1b의 A3d 결과(+0.0031, 불채택), 준비 작업의 라벨 품질(거르개 v2 남긴 점 오류 3.7 %·RB2 2.2 %). **문턱(+0.02, 하한 > 0, 전이 ≥ −0.01, 런타임 지연 불변)은 메인이 지시문에서 정했고**(E-MA1b와 같은 틀) 여기서 바꾸지 않는다. A 판의 출력·전량 라벨의 눈 검사는 아직 없다. 포인팅(아래 2절)은 등록 전에 시작했다(06:35Z). 등록 전에 본 것은 개수 파일(필요 프레임 48,016·호출 96,032)과 **라벨 도구 시험용 부분 통계**(06:46Z, 포인팅 약 11 %: 거르개 남김 0.726·실패 0.009, 포인팅이 끝난 편의 구간 있는 행 중 라벨 행 1,048/1,068)뿐이고, 눈 검사·A 출력은 없다.
- **이 결과로 바뀌는 결정**: **MolmoAct 궤적 보조(`trace5-point@v1`)를 실데이터 학습 레시피(단계 B 본 학습, 정본 §92 '학습' 줄)에 넣는가.** 채택이면 레시피에 이 보조 머리를 더한다(학습 때만 — 런타임 경로·지연·프롬프트 불변). 불채택이면 실데이터 MolmoAct 이식은 궤적 보조 없이 조종 데이터(대체 경로 시연, 준비 문서 4.6 (c)) 수집 뒤 E-MAR-S로만 다시 연다. O는 어느 쪽이든 보류(런타임 손끝 점 문제 해결 전).
- **이 표본으로 가를 수 있는가**: 같은 데이터·스케줄·시드·검증의 E-MA1b에서 합동 효과 95 % 구간 폭이 ±0.005, 움직임 줄 확인에서 ±0.010 → **전체 +0.02 크기의 효과는 하한 > 0으로 가를 수 있고**, 0 근처면 불채택으로 분명히 떨어진다. **한계(등록)**: 라벨은 RB2 행에만 있고(RB1은 C3 위반으로 빼고 마스크), 그중 구간 끝이 있는 행만 라벨이 생긴다(RB2 17,380행 중 9,518행에 구간 끝; 거르개 뒤 더 준다). 효과가 RB2 라벨 행에만 있다면 검증 전체에서 약 1/4–1/5로 묽어진다 — 전체 +0.02는 RB2 라벨 행에서 약 +0.08–0.10에 해당한다. 그래서 **RB2 층·RB2 라벨 행 층의 효과와 95 % 구간을 판정 밖으로 반드시 보고**하고, RB2 층에서만 보이는 작은 효과는 "가능성"으로만 적는다(판정은 전체에서만). 가를 수 없는 구간은 전체 점 추정 +0.010–0.020(하한은 넘어도 점 문턱 미달) — 규칙상 불채택이며 "작은 효과 가능성"으로 보고한다.
- **더 싼 사전 실행**: (1) 준비 작업(48편 포인팅 0.37 GPU-h — 라벨 품질·거르개·구간 끝·색); (2) 이 등록의 **20스텝 사전 실행**(학습 표본 64, 검증 원천별 5, 부분 라벨 — 포인팅이 끝난 편만): 보조 손실 유한, 라벨 붙임 수 출력, 저장·재적재·예측, 학습 보기 = 기본 보기 예측 기록 동일(G-dry). 실패하면 고치고 8절에 기록한 뒤 본 판.

## 1. 질문

MolmoAct의 미래 손끝 궤적(머리 영상 2D 폴리라인, 5점, 0–255, 구간 끝 = 놓기)을 **실영상 위 포인팅 모델 라벨**로 만들어 보조 회귀 목표로 배우면, 움직임 줄(§83)을 켠 S-E2E 결정 정확도가 오르는가. E-MA1b(로봇 기준 3D, 끝 = 다음 그리퍼 상태 변화·상한 3 s)와 달리 목표가 **영상 좌표**이고 끝이 **놓는 곳**(장기 목표)이다 — P66("라벨에 없는 정보인가")에 대한 답: 0.3 s 결정 라벨에 없는 놓을 곳 위치를 담는다.

## 2. 라벨 `trace5-point@v1` (고정)

- **포인팅**: Molmo2-ER(`/data/harvest/models/Molmo2-ER`, 준비 작업과 같은 판 `dab2256`), 문장 "point to the {left|right} robot gripper", bf16·탐욕 복호·최대 64토큰·일괄 16, `tools/marr/point.py` 그대로. 메인 파드 GPU 0(두 프로세스, 줄 번호 기준 2분할 — 결과는 키로 합침). 대상 = **se2e_c1 RB2 행(856편 17,380행, 학습 16,612·검증 768)** 이 필요로 하는 프레임 전부: 행(편, 프레임 k, 활성 팔 a)의 구간 끝 e = a의 다음 놓기(`se2e_molmo.grip_segment_ends`, `require_grasp`)일 때 [k, e]의 합집합 = **48,016프레임 × 두 팔 = 96,032호출**(`tools/marr_real/jobs.py`; 거르개 v2가 두 팔 포인팅으로 편별 오프셋을 재므로 두 팔 모두). 행과 parquet의 프레임 대응 확인: |FK(k + label_steps) − FK(k) − ee_delta| 최대 5.0e-6 m(문턱 2e-5, 통과).
- **거르개 v2**(준비 문서 고정값: 오프셋 분리 40 px·관문 150 px·가장자리 12 px, `se2e_molmo.filter_nominal`): 명목 URDF 머리 카메라(`se2e_trace`, RB1_HEAD = RB2 중앙값)로 두 팔 FK를 투영 + 편별 2-D 오프셋 → 다른 팔에 더 가까우면 `side`, 지정 팔에서 > 150 px면 `gate`, 실패 `fail`. 포인팅하지 않은 프레임은 없는 점.
- **궤적**: 팔마다 `trace.labels_segments(남은 점, 구간 끝)` — 프레임 t의 궤적 = t…e의 남은 점을 MolmoAct 규칙(`molmo_subsample`, ≤ 5점, 첫·끝 포함 등간격)으로 1–5점, 0–255 정수. **행 라벨 = 행의 활성 팔(`arm`) 궤적의 프레임 k 값.** 라벨 없음(마스크) = 마지막 놓기 뒤·구간 끝 없음, 구간 안에 남은 점 없음, **RB1 전 행**(C3 위반: 놓을 때 그리퍼가 영상 밖, 준비 문서 4.4).
- **목표 벡터**(`harvest/train/se2e_tracept.py`): 점 i → (u/255, v/255) ∈ [0, 1], `TRACE_SCALE` 0.05 단위(E-MA1 `trace5@v1`와 같은 척도: 영상 5 % = 1), 없는 점 마스크 0 → 회귀 10값 + 마스크. 파일 `/data/harvest/data/marr_real/conv/RB2.tracept.jsonl`(행마다 key·arm·split·k·end·trace255·reason; `tools/marr_real/labels.py build`).
- **관문 G-label(본 판 전, 멈춤 규칙)**: 전량 라벨에서 **새 눈 검사 표본 96장**(RB2 × 두 팔 × 48, 시드 2, 준비 작업 표본 1·2의 RB2 (편, k, 팔)과 겹치지 않음, 포인팅한 프레임에서 무작위, 거르개 결과를 모른 채 시트로 판정 — 부호 g/o/x/n/u, u는 오류) → **남긴 점 오류 ≤ 0.05 그리고 올바른 점 유지 ≥ 0.80**(준비 작업 G-filter와 같은 규칙, `labels.py eye`). 실패 → 멈추고 원인 진단 → 거르개 변경을 8절에 커밋 → **새 표본**으로 재검증 → 재개.
- **관문 G-count**: 학습 분할 라벨 행 ≥ 2,000(보조 신호가 너무 희박하면 가를 수 없음) — 미달이면 멈추고 재설계.
- 보고(판정 밖): 거르개 사유 분포, 라벨 행 수(학습·검증), 점 수 분포, 라벨 행의 놓기 프레임 점 유지율, 궤적 시트 한 장 눈 확인.

## 3. 설계

- **판**: **A 시드 1·2**(`a_s1`, `a_s2`) 새로 학습. **C0 = 움직임 줄 확인 실험의 `motion_s1`·`motion_s2` 재사용**(`/data/harvest/ckpt/se2e_confirm/`) — 짝 비교(같은 시드 = 같은 데이터 순서·같은 움직임 줄 드롭아웃 난수).
- **A가 C0와 다른 점**: aux 머리 회귀 출력 +10(다른 매개변수 초기화 뒤에 생성 — 백본·LoRA·expert·확인 헤드 초기값은 같은 난수 흐름, E-MA1b와 같음), 보조 손실 항 λ_aux 0.1 × 마스크 smooth-L1(라벨 있는 행만; S-E2E 행의 원래 aux 목표는 모두 마스크 → aux 손실 = 궤적 손실), 기울기는 백본까지(§58). 데이터(`se2e_c1` RB1 + RB2 전 행)·순서·드롭아웃·평가 집합 동일.
- **코드 기준 = `1b68a6a`**(직렬화기 `ser-A-min-3` 커밋 `340c5dc` 바로 앞). 이유: `340c5dc`·`a761b2b`가 `stageb_data.py`·`se2e_data.py`·`stageb_train.py`의 프롬프트(구간 줄·그리퍼 질문·`prompt_config` 형식)를 바꿨고, C0는 그 전 코드로 학습됐으며 handoff §0이 PH-A 1 전 ser-A-min-3 재학습을 막는다. 파드 사본 = `git -c core.autocrlf=false archive 1b68a6a`(harvest·tools/ma1·tools/se2e·tools/sr0) + 이 등록 커밋의 새 파일(`harvest/train/se2e_tracept.py`·`tools/marr_real/`·`tools/marr/point.py`)을 LF로 덮음, `CODE_VERSION` JSON(P73). `1b68a6a`의 학습 경로 파일은 E-MA1b 사본 `ded38d7`과 같다(`git log ded38d7..1b68a6a`에 해당 파일 변경 없음).
- **기준 재사용 조건(모두 만족; 하나라도 어기면 `c0new_s1`·`c0new_s2`를 이 사본으로 새로 학습해 4판)**: (1) `motion_s<s>` `config.args`가 A 판 인자와 `run`·`out_root`·`aux_extra`·`a3d_root`·`tracept_root` 밖에서 **전부 같음**(`reuse_check.py args`); (2) 이 사본으로 `motion_s<s>/last`를 `predict --val-per-kind 0`(검증 1,799)한 기록이 E-MA1b의 `predfull_none_s<s>.jsonl`(= 원 실험 기록과 비트 동일로 확인된 것)과 `utc` 밖 **비트 동일**. 예외 규칙: 파드가 다르다(이번 x2, 그때 메인 GPU 2)는 이유로 비트가 다르면 — 항목 순서 같음·argmax 일치 ≥ 0.999·최대 |Δ log-prob| ≤ 1e-3이면 '장치 수준 차'로 기록하고 재사용을 유지(판정의 C0 입력은 어느 경우든 **이 사본·같은 파드에서 새로 낸 예측**), 그보다 크면 멈추고 조사(8절); (3) 학습 경로 파일(`reuse_check.py code`의 16개)이 `code_se2e_confirm`과 줄 끝(CR) 밖에서 같음 — `stageb_train.py`는 E-MA1b에서 옵션만 더해 기본 경로 불변으로 확인됨(그 등록 3절·결과 3절), 이 판은 그 파일을 고치지 않는다.
- **스케줄**(C0와 같음): Qwen3-VL-4B@`ebb281ec` + LoRA r32 + 흐름 정합 expert + aux·확인 헤드, KI stop, IMG, λ 1/1/0.1/0.1, **2,000스텝, 묶음 8, lr 1e-4/1e-4, 워밍업 3 % + 코사인, 시드 1·2**, `--data se2e --se2e-root se2e_c1/conv --se2e-t-root se2e_c1/conv --motion-line se2e-motion@v1 --motion-bins se2e_c1/motion_bins.json --val-per-kind 150 --val-seed 0 --eval-every 500 --aux-extra trace5-point@v1 --tracept-root /data/harvest/data/marr_real/conv`, 진입점 `python -m harvest.train.se2e_tracept train`(= `stageb_train` + 실행 시 등록, 4절).
- **실행**: x2 파드(`juhyoung-native-7a2a-x2`) GPU 0 = `a_s1`, GPU 1 = `a_s2` 동시(E-SR1d가 비운 뒤, `nvidia-smi` 메모리 < 2 GB일 때만 시작 — 아무것도 선점하지 않음). 이어 같은 GPU에서 검증 1,799 예측(+ `--extra-out`)과 C0 예측(재사용 검사 (2) 겸), GPU 0에서 보기 확인(4절 (c)). `OMP_WAIT_POLICY=PASSIVE`, `OMP_NUM_THREADS=8`. 스크립트 `tools/marr_real/run_train.sh`.

## 4. 실행 경로 동일성 (A는 학습 전용 머리)

- (a) **기존 파일 무수정**: 이 판의 코드는 새 파일 `harvest/train/se2e_tracept.py`뿐이다. `install()`이 실행 때 `stageb_train`(AUX_CHOICES·AUX_FILES·`attach_aux_targets`·`--tracept-root`·RESUME_KEYS)과 `se2e_trace_model`(EXTRA·`extra_metrics`)에 새 판을 등록하고 되돌리기 함수를 준다 — import만으로는 아무것도 바뀌지 않는다(시험). 등록 커밋의 `harvest/` 변경은 이 새 파일 하나이고(`git show --stat`), 파드 사본의 `harvest/`는 `1b68a6a`와 이 파일 하나만 다르다(파일 목록·내용 비교를 결과에 적는다) — 체크포인트 해시 파일 `PROMPT_FILES`·`PROMPT_FILES_B`·`TEMPORAL_FILES`·`AUX_FILES`·`harvest/runtime` 무수정.
- (b) 시험 `tests/train/test_se2e_tracept.py::test_runtime_path_base_view_identical`: 같은 체크포인트를 학습 보기(`StageBTrace`)와 기본 보기(`StageB`)로 평가하면 결정 항목 기록·청크가 **비트 동일**. 그 밖 시험: 목표 변환·붙임(RB1 마스크, 빠진 키 KeyError)·등록/되돌리기(기본 인자 불변)·`prompt_config` 표지·손실 = λ × 마스크 smooth-L1·백본 기울기·저장/재적재·`extra_metrics` 화소 오차.
- (c) 파드: `a_s1/last`를 `--aux-view trained`와 `--aux-view base`로 검증 300 예측 → 항목 기록·요약이 `utc`·`aux`·`ckpt` 밖 **비트 동일**(`reuse_check.py pred`).
- **지연**: 런타임은 기본 보기(`StageB`)만 쓰고 보조 머리는 결정·청크 경로에 들어가지 않으므로 (a)–(c)가 통과하면 **런타임 지연 변화 0**이 구성으로 성립한다 — 채택 조건 (4) = (c) 통과. 별도 지연 측정은 하지 않는다(E-MA1b와 같음).
- 프롬프트·질문·`question_id@vN`·이미지 입력 불변. `prompt_config`에 `aux: trace5-point@v1`과 옵션 파일 해시(`AUX_FILES` + `se2e_tracept.py`)가 들어가 체크포인트가 섞이지 않는다.

## 5. 지표와 판정 규칙 (고정)

- 항목 = 스냅샷 × 3질문. 정확도·NLL, **전체·전이 층·정상 층**(전이 층 = `se2e_c1/transition_val.json`).
- 시드 s 효과 e_s = acc(A, s) − acc(C0, s)(짝), **합동 효과 = ½(e₁ + e₂)**. 스냅샷 군집 부트스트랩 10,000회(시드 0, 네 판 같은 추출, 95 % 백분위).
- **채택** ⇔ (1) 합동 전체 효과 **≥ +0.02** 그리고 (2) 부트스트랩 95 % 하한 **> 0** 그리고 (3) 합동 전이 층 효과 **≥ −0.01** 그리고 (4) **런타임 지연 불변**(4절 (c) 통과). 문턱 비교는 상대 CMP_EPS 1e-12(하한 > 0은 엄격). 검증 전체 1,799에서만 판정.
- 판정 스크립트 `tools/marr_real/verdict.py`(E-MA1b `ma1b_verdict.py`의 효과·부트스트랩 함수를 그대로 불러 씀; 입력 크기·중복 검사 P25; 시험 `tests/test_marr_verdict.py`) — 결과 뒤 고치지 않는다.
- **판정 밖(보고 의무)**: **RB2 층**·**RB2 라벨 행 층**·RB2 라벨 없는 행 층·RB1 층의 합동 효과와 같은 방식의 95 % 구간, NLL, 정상 층, 질문별, 시드별 효과·차이; **청크 MSE**(`extra_metrics`: 확정 보기·예측 보기 조건, 정규화 MSE, 고정 잡음); **보조 궤적 오차**(검증 RB2 라벨 행, 점별 화소 평균·중앙값, 0–255 단위, 첫 점·끝점) + 참고 기준(학습 분할 점별 평균 궤적을 답했을 때의 오차); **준수(E-SR0 도구, 싸면)**: `tools/sr0/sr0_eval.py`를 A 두 판에 수정 없이 돌려 S-E2E 강제 방향 준수(cos > 0.5)를 C0의 기존 값(`/data/harvest/logs/sr0/sr0_motion_s{1,2}.jsonl`)과 비교 — "싸다" = 판당 ≤ 40분·x2 GPU가 비어 있을 때; 아니면 '미실행'으로 보고(E-SR1d 도구는 분기 데이터 전용이라 이 판에 맞지 않아 쓰지 않음).
- **해석 한계(§84 보충 1, 등록)**: 궤적 목표는 결정 라벨(미래 손끝 변위)과 겹치는 정보를 더 촘촘하게 주며, 놓을 곳이라는 장기 정보가 더해질 뿐이다 → 이득은 "더 촘촘한 감독" 몫일 수 있다. **어떤 결과도 일반화 주장(가설 H1)의 근거로 쓰지 않는다.** 라벨 오류(RB2 약 2–7 %), 원격조작 시연의 경로 다양성 부족(준비 문서 4.6), 머리 카메라 깊이축 모호함, 2,000스텝·λ 0.1 한 설정.

## 6. 자체 검사 관문 (도중 — 멈추고 재설계, 변경은 UTC 시각과 함께 8절에 커밋한 뒤 재개)

| 관문 | 멈춤 조건 |
|---|---|
| G-label | 2절(눈 검사 96장: 남긴 점 오류 > 0.05 또는 유지 < 0.80) |
| G-count | 학습 분할 라벨 행 < 2,000 |
| G-dry | 20스텝 사전 실행에서 aux NaN, 라벨 붙임 실패, 저장·재적재·예측 실패, 보기 기록 불일치 |
| G-reuse | 3절 (1)·(3) 실패 → C0 재학습(4판); (2)는 3절 예외 규칙 |
| G-nan | 학습 기록 `aux`가 NaN이거나 step 500 이후 평가 aux가 step 0 값의 2배 초과 |
| G-time | 판 하나가 예상(약 40분, C0 2,222 s)의 2배(80분) 초과 |
| G-view | 4절 (c) 불일치(= 채택 조건 (4) 실패; 멈추고 원인 조사) |
| 무효 답 | 포인팅 실패(점 없음) > 10 %(준비 작업 2.0 %) |

- **변경 절차**: 관문 실패 → 그 단계 산출물 보존·원인 진단 → 이 문서 8절에 변경(무엇·왜·UTC)을 적어 **커밋한 뒤** 재개. 판정 규칙(5절)·문턱은 결과를 본 뒤 바꾸지 않는다. 결과 뒤 새 아이디어(λ·스텝·라벨 판)는 새 등록으로만.
- 끝(결과 뒤): 판정 입력 파일의 항목 수·키 집합을 로컬에서 따로 세어 판정 파일과 대조, 로컬 시험, 기계 검사.

## 7. 코드·출력

| 항목 | 값 |
|---|---|
| 이 등록과 함께 고정(LF 블롭 sha256 앞 16) | `harvest/train/se2e_tracept.py` `d4a8cebcf1705501`, `tools/marr_real/jobs.py` `2693758d5033ca47`, `tools/marr_real/labels.py` `9307e8272a41300a`, `tools/marr_real/verdict.py` `932aca1fc0ca1169`, `tools/marr_real/reuse_check.py` `76f35e94f8166ce8`, `tools/marr_real/run.sh` `2fe73ae25873fa36`, `tools/marr_real/run_train.sh` `30fca1b06e706b20`, `tools/marr/point.py` `6741357ae9d33935`(무수정); 시험 `tests/train/test_se2e_tracept.py` `60d8faee32ed6ee7`, `tests/test_marr_verdict.py` `039b3b7b43fe166f` |
| 코드 사본 | 파드 `/data/harvest/code_marr_real` = 3절(기준 `1b68a6a` + 이 커밋 새 파일), 판 폴더마다 `CODE_HASHES.txt` |
| 데이터 | `/data/harvest/data/marr_real/`(frames 48,016장·eps npz·`point_jobs.jsonl`·`points.shard{0,1}.jsonl`·`conv/RB2.tracept.jsonl`) |
| 출력 | 체크포인트 `/data/harvest/ckpt/marr_real/a_s{1,2}`, 로그·예측·판정 `/data/harvest/logs/marr_real/`, 사전 실행 `/data/harvest/tmp/marr_real/smoke`, 로컬 사본 `D:\tools\scratch_qdd\marr` |
| 비용 | 유료 0원. GPU 추정: 포인팅 약 1.5 h(메인 GPU 0) + 학습 2 × 약 0.7 h + 예측·확인 약 0.8 h(x2) ≈ 3.7 GPU-h |

## 7a. 하지 않는 것
- 이력 덧그림 O, 궤적 조건 학습(C4), 조종(E-MAR-S), RB1 라벨, 시드 0 판, 검증 300 판정, 별도 지연 측정. `se2e_c1`·움직임 줄 확인·E-MA1b 체크포인트 덮어쓰기, 기존 파일(특히 `stageb_*`·`se2e_trace*`·`harvest/runtime`) 수정, ser-A-min-3 코드로 학습, 남의 GPU 프로세스 선점, 유료 API.

## 8. 변경 기록
- (없음 — 변경은 UTC 시각과 사유를 여기에 적는다.)
