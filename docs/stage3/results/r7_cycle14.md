# R7 객관 검증 순회 — 14회차 (cycle 14, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님; `r7_cycle13.md` §5 표나 `r7c13_fixes.md`의 시험에 기대지 않고 사전 등록 원문에서 대조표를 다시 만들고, 행마다 **구성한 입력 → 실제 함수·런타임 출력**으로 확인함). 작성 2026-09-25 12:30 UTC 무렵(`date -u`; 로컬 시작 약 11:57 UTC, 파드 첫 명령 11:58:40 UTC, 파드 정리 끝 12:25:18 UTC).
- 대상: `D:\qdd` `dev` 커밋 `2c4a30d`(= 태그 `stage3-r7fix13`, 커밋 시각 2026-09-25 11:56:18 UTC). 다른 에이전트의 커밋 안 된 S-E2E 진단 작업(`harvest/train/stageb_train.py`·`tests/train/test_stageb_torch.py` 수정, `docs/stage3/results/se2e_diag.md` 새 파일)이 작업 트리에 있어 **작업 트리는 읽지도 쓰지도 않고**(이 보고서 한 파일만 씀; 예외 — `prereg_se2e_diag.md` 파일의 수정 시각 메타데이터만 읽음) `git -c safe.directory=D:/qdd -c core.autocrlf=false archive 2c4a30d`(sha256 `728fdbff…`)을 Python tarfile로 `D:\tools\scratch_qdd\r7c14\repo`에 풀어 검토했다. `e6ab856..2c4a30d` = 13회차 보고서·S-E2E 판정 스크립트 커밋(0b056b8), CLAUDE.md user-log 68–70·handoff 번호(93c68d7), **PhysX 하드 리셋**(e8e1864, 정본 §78), 논문 갱신(b59d488·8d9380c), **13회차 수정**(2c4a30d, 정본 §79) + S-E2E 진단 사전 등록(`prereg_se2e_diag.md`). 파드 사본 = 같은 archive + JSON `CODE_VERSION`(`2c4a30d8…`, dirty false); 모든 파드 산출 `meta.git.commit` = `2c4a30d8…`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle7.md`–`r7_cycle13.md`, `r7c7_fixes.md`–`r7c13_fixes.md`, 정본 `00-interfaces.md` §1–§79(뒤 절 우선; [사용자] 제목 절은 그대로; 논문 .tex는 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`·`M4-overlap-commit.md`(조건 정의 §4·§5).
- 분류(13회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋과 다르고 정정 표시가 없는 것(후속 정본이 이미 정한 "[결정 필요]" 포함), 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 정본에 없는 것. 정본이 "나중에 할 일"로 적은 것(예: §79 (3) 런타임 `flip_th` 질문별화 — J4를 켜기 전)은 SCOPED.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory`로만 호출, 전역 설정 쓰기 없음). 로컬 임시 = `D:\tools\scratch_qdd\r7c14`(스크립트는 모두 Write 도구로 쓰고 경로로 실행). **절차 메모 2건**: (i) 파드 사전 점검 스크립트 초안에 heredoc·`python3 -` 한 줄이 들어갔으나 업로드 전에 지워 실행되지 않았다. (ii) 첫 로컬 pytest를 PowerShell에서 돌려 `test_cli_e0.py` 하나가 셸 실행 파일을 못 찾아 멈췄다(`-x`) → Git Bash에서 다시 돌림(아래 §6.5, 12회차와 같은 방식). 파드 = `/data/harvest/tmp/r7c14`(코드 사본·pytest·산출·카나리 가짜 루트, 380 MB)와 내 Isaac 판(12:17:06–12:22:49 UTC)이 만든 `ir/kitcache/cyclo-r7c14_standard`·`cache/pyc_r6/data/harvest/tmp/{r7c14,tmpqvevn0ex}`·`tmp/{carb.7dIZ5k,tmpqvevn0ex}`, LeRobot 시험이 만든 `cache/hf/datasets/parquet/default-c7ccaf4e2181c7ab`(+ 잠금 파일, `dataset_info.json`에 r7c14 경로) — 시작 전 목록과 대조하고 생성 시각·내용으로 가려 **모두 지웠다**. 같은 시각대의 다른 새 항목(`kitcache/cyclo-r2t_*` = R2_TRAIN·결정성 작업)은 남의 것이라 두었다. 공유 로그 `home/.nvidia-omniverse/logs/*`(모든 Isaac 프로세스가 덧붙임)는 두었다. GPU: Isaac = GPU 1(`closed --isaac-gpu 1` → `IR_ROOT=cyclo`, 고유 `IR_INST` = `r7c14_standard`, `CUDA_VISIBLE_DEVICES=1`, Isaac 프로세스 1개), GPU 0(R2_TRAIN)·2·3(S-E2E 진단 D1·D2) 건드리지 않음. **GPU 학습 확인(단계 B 재적재·CUDA 시험)은 빈 GPU가 없어 하지 않았고 CPU로 대신했다**(§6.3). CPU: 시작 전 파드 cgroup `cpu.stat` 10 s 측정 = **32/32코어, 주기 100/100 스로틀, 스로틀 72–93 s/10 s**(R2_TRAIN Isaac 5개) → 결정성 행렬(`harvest.sim.determinism`)은 **CPU 쿼터가 허락하지 않아 돌리지 않고**, 꼭 필요한 폐루프 한 판(C5 → C5' 같은 워커)으로 §78을 대신 확인했다. 내 작업은 `OMP_WAIT_POLICY=PASSIVE`·스레드 2. 시드 DEV·POOL만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 `=dev`·`=cal`만). 유료 API 없음(Astra 모의, `--astra mock`). 비밀값 출력·검색 없음. 남의 프로세스 건드리지 않음(읽기: `ps`, `/proc/<pid>/environ`의 `OMP_*`·`IR_INST`·`CUDA_VISIBLE_DEVICES`만).

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 1 |
| DOC | 2 |
| SCOPED | 18 |
| NOTE | 13 |

13회차 수정(정본 §79)의 핵심은 **모두 동작으로 확인했다**: FLIP_TH = 질문별 split conformal(손으로 센 순위 17건 일치, n 47·α 0.01 → 순위 48 > 47 → 문턱 없음·`n_needed` 99; 파드 실제 모의 e05도 다섯 질문 모두 n 47 → None), 카나리 기준일 = 같은 세트 × 같은 `question_id@vN` 집합의 첫날(파드 실제 `dev_v1` 세트: 새 판본 첫 판 기준 없음, 같은 판본의 더 이른 날이 있으면 그날 — 더 이른 옛 판본 날은 건너뜀), 표류 의심 뒤 J5는 재보정 전까지 꺼짐(10경우 + 파드), 경계 틱 호출의 `last_step` = 방금 끝난 스텝(가짜 세계 240판 요청 7,734개 독립 재구성과 불일치 0; 옛 코드는 경계 틱 호출 1,770개 중 233개가 앞 스텝 범주), 없는 `--data` 거부, Isaac 워커 환경 `OMP_WAIT_POLICY=PASSIVE`(실제 워커 `/proc/environ`). **PhysX 하드 리셋(§78)**: 같은 Isaac 워커에서 C5 → C5'(모의 선택기는 `last_step`을 읽지 않음) 두 판의 행동 1,592개가 **비트 동일**(13회차 e6ab856에서는 스텝 17부터 갈렸다). 그러나 §78 (1)의 **라벨 신뢰 기준(재생 비트 동일)을 결과 라벨을 읽는 코드가 적용하지 않는다**(D1). 문서 2건: `r7c12_fixes.md:17`의 옛 §77 (ii) 문장(D-1), §78 (2)가 불가능하다고 정한 "새 빌드로 29편 재라벨" 계획(`labeler.md:40` 등, D-2). 연속 무결은 **0회 그대로**.

---

## 1. DEFECT

### D1. 결과 라벨 소비 코드가 §78 (1) 라벨 신뢰 기준(재생 비트 동일)을 적용하지 않는다 — `harvest/eval/common.py:375-400`(`load_truth`의 `outcome:` 분기 :390-400), `harvest/train/stagea_data.py:49-55`·`:186-196`(`target_keys`·`outcome_factory`)
- 정본: §78 데이터 처리 (1)(`00-interfaces.md:688`) "라벨 신뢰 기준 = 재생 **비트 동일**(1 mm 아님); 풀 `replay_maxabs > 0` 886행(29편) 거부권 제외(labeler.md)", `labeler.md:39-40` "처리: `replay_maxabs > 0`인 행 전부(886 / 6,627, 29편)를 거부권에서 뺀다". 결과 기반 라벨의 쓰임은 거부권뿐이고(§65, §77 N4 "결과 기반 라벨은 … 거부권 용도"), §77 N4는 E0.5 결과 문서에 `--truth outcome:plan` 판의 값을 싣도록 정했다.
- 코드: 라벨러는 행마다 `replay_maxabs`를 기록하고(`cli_label.py:50`, `REPLAY_TOL = 0.0` `labeler.py:313`), `poolsum`은 최댓값만 요약한다(`cli_label.py:200`). 라벨을 **읽는** 두 곳 — `e05`·`rd`·`calib`의 `--truth outcome:<rule>`(`common.load_truth`)과 단계 A `OutcomeLabels`(`stagea_data.outcome_factory`·`target_keys`) — 은 `replay_maxabs`를 보지 않는다. 저장소 어디에도 `replay_maxabs > 0` 행을 거르는 코드가 없다(grep: 기록·요약 2곳뿐).
- 행동 확인(`trust14.py`): 같은 편 두 행(k3 `replay_maxabs` 0.0, k4 0.37)을 `load_truth(eps, "outcome:plan", [dir])`에 넣으면 **두 행 모두 정답으로 쓰인다**(`('P0', 2027, 4)` 포함). 지금 파드 풀 라벨(`/data/harvest/data/pool/labels`)에는 정본이 믿을 수 없다고 정한 886행이 그대로 있으므로(재라벨은 §78 (2)대로 R2_TRAIN 뒤 결정), §77 N4가 요구한 `e05 --truth outcome:plan` 판을 지금 코드로 돌리면 13.4 %의 무효 행이 정답에 섞인다.
- 정본 기록: 거르는 위치나 "지금은 쓰지 않음"을 정한 결정이 없다(§78 (1)은 규칙만, `labeler.md:40`은 처리 계획만). 잠재 결함(아직 E0.5 본 판 전)이지만 13회차 D2와 같은 종류로 센다.

## 2. DOC

### D-1. `docs/stage3/results/r7c12_fixes.md:17` — "같은 틱 호출은 경계 판정 전에 만들어지므로 다음 호출부터(…)"에 §79 정정 표시 없음
- 정본 §79 N1(`00-interfaces.md:696`)이 "**§77 (ii) 정정**: … → 이 절부터 경계 틱의 호출에 실린다"로 바꿨고 코드도 바뀌었다(`core.act:486-503`, 아래 행 79). 같은 파일의 :20·:21·:22·§8에는 13회차 수정이 [해결 R7 13회차 D-1…]·[R7 13회차 D2, 정본 §79] 표시를 달았지만 :17 "런타임 값" 행은 그대로다(13회차 D-2 `r6_eval.md:46`와 같은 모양). 정본 §77 :667의 같은 문장은 §79가 명시적으로 정정해 "뒤 절 우선"으로 해결됨.

### D-2. `docs/stage3/results/labeler.md:40` — "29편은 장면 재생성 빌드(진행 중) + 고친 라벨러로 별도 폴더에 다시 라벨해 전 행 `replay_maxabs == 0` 확인 뒤 교체"에 §78 정정 표시 없음 (같은 사실: `pool_replay_debug.md:17`·`:134-135`, `r2_datagen.md:147`)
- 정본 §78 (2)(`:688`) "기존 풀·R2 DEV·E0.5 스냅샷은 옛 물리로 녹화 → **새 코드로 재생되지 않는다**; 풀 29편 재라벨은 `hard_reset=False`(옛 체제)로 하거나 풀과 라벨을 함께 다시 만든다(R2_TRAIN 뒤 결정)", `physx_hard_reset.md:16`·`:89` "29편 재라벨을 새 코드로 하면 안 된다(16회 재시도 뒤 어긋난 분기)". 기본값이 `hard_reset=True`가 된 2c4a30d에서 `labeler.md:40`의 처리 계획은 `replay_maxabs == 0`에 도달할 수 없다(`cli_label`에 `hard_reset` 옵션도 없음). `pool_replay_debug.md:134-135`의 "방법: `cli_label label`을 이 시드들로 별도 폴더에" 권고와 `r2_datagen.md:147` "새 이력 재생은 이력 의존 — 체인 재생으로만 비트 재현 보장"(하드 리셋 뒤 새 녹화는 새 이력 재생도 비트 동일, 옛 R2 DEV 녹화는 체인 재생으로도 재현 안 됨)도 같은 사실이다. 정본 §78 외에는 §78을 가리키는 문서 표시가 하나도 없다(grep `§78`·`physx_hard_reset` → 정본 :685만).

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬 `test_latency_ctrl.py:11` 건너뜀, 파드도 같음. EVAL H1–H3 기준선 비교.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드에서 하드 리셋 빌드(`code_r2train_e8e1864`)로 진행 중(읽기만); `gen gen --seeds 10005-10006` 확인 인자 없이 rc 1.
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8(검사기·계획 서명·편집 거리, 확인 헤드 보정 파일 기본 미보정, M9 복구).
- S6. Astra 카나리 "none"(§67 보충) — 파드 C5·C5' `astra` 행 `canary_id` "none".
- S7. S-E2E 체크포인트의 런타임 tau 마스크·DecCall 형식 차이와 새 코드의 거부(§77 보충 (2)).
- S8. CONTRADICT-soft(§68 K6).
- S9. §73 D5 M4 설계 확장.
- S10. §73 N5 E1 범위(`calib` = 판정 1·8).
- S11. §74 보충 E-M4-lat 비례 STALE_MAX, 런타임에 없는 조건 C2'·C2'-S·C2-match·C3'·C3''·C5-A3·C-FIX(파드 `closed.json` `meta.not_in_runtime` 그대로).
- S12. §75 보충 (2) E-M4 판정 7.
- S13. §77 N8 (13): E0.5 `fine_dir`, Jev-L E0 측정 도구, 결정 호출 이미지 원본 저장 안 함, 완료 정의 밖 사전 등록 실험.
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31`·`:117-121` "boundary (ambiguous)" 주석 — 2c4a30d에 그대로(e8e1864는 `scene.py`만 고침).
- **S15**. §79 [Claude 결정] (3): 런타임 `M4Params.flip_th`는 한 값이고 지금 꺼짐(None) — J4대로 켜기 전에 `question_id@vN`별 값을 받게 바꾼다(정본이 적은 나중 할 일).
- **S16**. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬("본 실험 전에 확인") — 파드에 메인의 `cyclo-r2t_det_*` 작업이 진행 중(읽기만).
- **S17**. §78 (2): 기존 풀·R2 DEV·E0.5 스냅샷(옛 물리 녹화)의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- **S18**. `prereg_se2e_diag.md` D1–D3의 구현(`stageb_train.py` 진단 옵션, `d3_analyze.py`)은 커밋 밖(작업 트리·파드) — 2c4a30d 검토 범위 밖. 사전 등록 시각만 확인(행 106).

## 4. NOTE
- N1. **S-E2E 판정 스크립트(`tools/se2e/se2e_verdict.py`)의 입력 검사 빈틈 3가지**(구성 로그 29건 — §6.1): (i) (e)가 재개 창을 보지 않는다 — 재개 로그가 1–50스텝이나 3001–3050스텝이어도 원래 판과 같으면 "bit"(사전 등록 §4 (e) "step 2001–2050의 50스텝"; 인자 `mid`는 (c2)에만 쓰임). (ii) (b)의 "처음"·"끝 3점"을 `ev[0]`·`ev[-3:]`로 잡고 스텝을 확인하지 않는다 — 4500 eval이 빠지면 [3500, 4000, 4686], 4686 행이 두 번이면 [4500, 4686, 4686]로 계산(출력 `last3_steps`에는 드러남). (iii) 드라이버 폴더 인자를 빼면 (a)의 rc 검사가 통째로 빠지고 `a.pass` 참(출력에 `rc_all_zero` 키가 없음으로만 드러남; §77 보충 2는 rc를 드라이버 출력에서 판정한다고 정함). **실제 S-E2E 로그에는 영향 없음**: 커밋 판(sha256 `476e4098…` = 파드 `logs/se2e/se2e_verdict.py`)을 읽기 전용으로 돌리니 재개 창 [2001, 2050]·50스텝, eval 11점·끝 3점 [4000, 4500, 4686], rc 6개 모두 0, 결과 = 파드 `verdict.json`과 바이트 동일((d) 참, (e) A·B 모두 "tolerance", 총손실 상대차 중앙값 0.46 %·0.39 %, 최대 1.62 %·1.53 %). 다른 판에 다시 쓸 때 창·스텝 단언과 드라이버 인자 필수화를 권함. 경계 값은 사전 등록대로 동작(0.65·0.65·0.80 → b1 통과, 0.7003 불합격, 끝 0.8000001 불합격, 상대차 정확히 1 %·5 % 통과, 5.01 %·1.01 % 불합격, 재적재 1e-9 불합격, idx·첫 스텝·49스텝 불합격).
- N2. **경계 틱 수정(§79 N1)의 영향 범위**: 가짜 세계 240판(8조건 × 30, 모듈형·융합, H 1·3, W 0–2, 지연 고정·흔들림, Astra 모의 유무, 무작위 틱 DEVIATE·LAG·CONTRADICT 1–5회) e6ab856 대비 — C0–C3 **120/120 비트 동일**(행동·원장·호출 시각·요청 상태), C4 0/30·C5 0/30(줄만 다른 판 12·13), **C5' 9/30**, C6 16/30. C5'도 원장이 바뀐다(경계 틱 호출이 확인 뒤 epoch를 달아 표 폐기 감소: `dropped_epoch` 합 C4 1,255 → 800, C5 1,320 → 830, C5' 1,510 → 865, C6 710 → 290), 성공 여부는 239/240 같음(C6 1판 다름). 정본 §79의 "C5' 20/20 비트 동일"은 그 표본(강제 DEVIATE만)의 결과이고, C5'도 새 동작의 영향을 받는다 — C5와 C5'가 같은 규칙을 받으므로 판정 3 짝 비교는 공정하다. (대조 도구 메모: 첫 판에서 호출 기록을 작업 스레드에서 모으고 지연을 메인 루프에서 바꾸어 판끼리 가짜 차이가 났다 — 메인 스레드 기록으로 고친 뒤 옛·새 코드 모두 판 간 240/240 재현.)
- N3. 빈 입력 거부의 남은 틈: 있는 폴더에서 `--seeds`가 한 편도 고르지 않으면 `load_episodes`가 0편을 돌려주고 `e05`는 rc 0 `claim insufficient_data`(`n5res.py`; 정직한 결과라 NOTE). `harvest.sim.determinism fresh --seed 500`은 시드 거부 전에 `--out` 폴더를 만든다(13회차 N6과 같은 모양).
- N4. handoff §2.8 13회차 줄(`docs/handoff.md:105`)과 `r7c13_fixes.md:3`·`draft-log.md:452`는 수정을 "커밋 안 함"으로 적고 커밋·태그(2c4a30d, `stage3-r7fix13`)가 없다 — 수정 에이전트 시점의 기록(12회차 `draft-log.md:451`도 같은 모양)이라 NOTE. handoff에는 §78(하드 리셋·R2_TRAIN 재기동)과 S-E2E 종료(11:34–11:37 UTC 드라이버 rc 0, 파드 `verdict.json` 통과) 줄이 없다(범위 표기 §1~§79만); `se2e_train.md`는 2c4a30d에 없다(검토 중 `bc1bd54`로 커밋됨 — 범위 밖).
- N5. `prereg_se2e_diag.md`: 작업 트리 파일의 마지막 수정 11:48:08 UTC(문서 머리 11:47:14Z) < D1 시작(11:52 UTC)·D3 예측 `pred.jsonl`(11:53:19 UTC) < 커밋 11:56:18 UTC — 결과 전 고정은 맞다. 다만 D3 판정 계산 스크립트(`logs/se2e_diag/d3_analyze.py`, 11:54:35 UTC)는 예측이 나온 뒤에 쓰였고 저장소 밖이다 — 커밋 때 사전 등록 §4 여백·밴드 정의와 줄 단위 대조를 권함.
- N6. **논문(매시간 갱신 때)**: `paper/sec/X_suppl.tex:27` FLIP_TH "구현 수정 중", `:129` 13회차 행 "(수정 중)", `:132` "13회차 결함 셋의 수정은 진행 중"(2c4a30d에서 구현됨), `paper/mindmap/sec/3_method.tex:194` "같은 틱 호출은 경계 판정 전에 만들어져 다음 호출부터 실림"(§79로 정정됨), `paper/sec/6_prelim.tex:30` 하드 리셋 빌드로 R2_TRAIN 재시작 "(예정)"(파드에서 진행 중).
- N7. 폐루프 수치가 바뀌었다: 같은 DEV 7 C5 모의 판이 13회차 16.58 s → 이번 15.91 s(DEVIATE 호출 13 대 8) — 하드 리셋(물리 시작 상태)과 §79 N1이 함께 바뀐 결과. §78 (4)대로 이전 폐루프 수치는 새 빌드 수치와 짝 비교하지 않는다.
- N8. 하드 리셋 뒤 라벨러의 `REPLAY_HISTORIES`(16회 재시도)는 모든 이력이 같은 결과를 내므로 새 녹화에는 불필요하고, 옛 풀에는 항상 16회를 다 쓴 뒤 어긋난 분기를 남긴다(`physx_hard_reset.md:78`) — §78 "prefix/warmup 제거 후보"와 함께 정리 권함.
- N9. §78 결정성 행렬은 CPU 쿼터 포화로 돌리지 않았다(머리 규칙 줄). 대신 확인한 것은 한 워커 안의 두 이력(같은 시드 C5 뒤 C5')과 로컬 모의 시험 8개(§6.1) — "다른 시드 부분 실행 뒤"·"새 프로세스 대비"는 `physx_hard_reset.md`의 24/24 보고에 기댄다.
- N10. 13회차 N7(표류 의심이면 모든 질문의 J5 끔), N8(`serializer_of` 메시지), N9(`e05` P3·P4 "perturbed"), N14(§76 N3 격자 밖 H = 1 표 수, 카나리 `dev_v1` `stale`, TEST2가 `splits.RANGES`에 없음, 1차판 RD Score [가정], E0.5 분당 400 [가정]) 그대로.
- N11. 시험 수: 로컬 **953 passed / 13 skipped**(`r7c13_fixes.md:42`와 같음), 파드 CPU **1001 passed / 4 skipped**(`:43`과 같음), LeRobot 6 passed. 파드 CUDA 시험·`tests/sim/test_determinism_isaac.py`(Isaac 파이썬)는 돌리지 않았다.
- N12. 단계 B 소형 CPU 스모크(`smoke --backbone tiny --device cpu --steps 30`): 학습 총손실 처음 5 평균 3.044 → 끝 5 평균 2.986, eval fm 2.438 → 2.202, dec 0.787 → 0.676, `save_load` `max_abs_action_diff` 0.0·eval 같음, KI(흐름 정합 → 백본) 기울기 0.0.
- N13. user-log 62·67("최대 gpu 효율")은 CLAUDE.md에 없다(67은 질문 + 병행 승인이라 제약이 아닐 수 있음; 13회차 D-4의 괄호 항목). 69·70은 93c68d7에서 추가됨(13회차 D-4 해소 확인).

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` OK, 파드 산출 `meta.prereg.check` = "OK"(e05·rd·calib·closed). 사전 등록 문서는 `e6ab856..2c4a30d`에서 `prereg_se2e_diag.md`가 새로 들어온 것 말고 바뀌지 않았다. 코드 줄은 `2c4a30d` 기준. "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c14\hand14.py`(52건 중 51 — 남은 1건은 내 입력 오류: `question_ids=None`을 넣은 경우로 런타임은 늘 dict를 넘김), `hand14b.py`(49건 — `step_votes` 2건은 내 색인 오류, 값 4·3은 맞음), `rt_diff.py`·`rt_cmp.py`(가짜 세계 240판 × 옛·새 코드), `verdict14.py`(29건 — 24 기대대로, 1건은 내 기대 오류(끝 0.90 정확히 = 통과가 맞음), 4건 N1), `trust14.py`(D1), `n5res.py`(N3); **파드** = §6(`pod_*.sh`, `closed_check.py`). 굵게 = 이번에 처음 대조한 행.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 (E :113-120, 정본 §66) | `eval/splits.py:19-42` | `split_of` 경계 16건(29 dev·30 None·499 None·500 cal·549·550·1000·1149·1150·1300·1329·1330·2000·2119·2120); 파드 가드 17건 rc 1(§6.4) | 일치 |
| 2 | POOL 120 × 10, 경계 사례 30 % 과표집 (E :121, §76 D-2) | `sim/snapshot.py:102-136` | 시험 묶음 | 일치(주석 S14) |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` | 시험 묶음 | 일치 |
| 4 | 분할 = 에피소드 (E :122) | `pool_split`, `calib.halves` | 파드 calib `CALIB_DONE`(fit POOL·heldout DEV) | 일치 |
| 5 | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py:26-38` | 시험 묶음; 파드 Isaac C5·C5' 성공 15.91 s | 일치 |
| 6 | 호출 기록: 질문별 확률·요청/응답 원문(E :125), Astra A6(E :126, §28 :255) | `core.py:289-322,408-418` | 파드 C5·C5' 호출 96행: `request_blob` = `request_sha256` = sha256(blob) 96/96, blob 안 이미지 해시 = 행 `image_sha256` 96/96, `response_blob` 해시·`probs` 질문 = `answers` 질문·합 1 96/96; Astra 4행 요청·JPEG 해시·`output_text`·`max_output_tokens`·`effort` 4/4 | 일치 |
| 7 | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `stats.py:4` | 파드 closed `meta.bootstrap.n_boot` 10000·단위 layout seed | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate` | 파드 C5 대 C5' 같은 워커: 물리 이력 차 없음(행 99) | 일치 |
| 9–12 | 판정 2 Holm, 판정 10, 카나리 Holm, 판정 절 해시 (E :131, :265, :139, :133) | `e05`, `harvest/canary.py:31-55`, `eval/common.py` | 시험 묶음; 파드 e05 판정 키, 카나리 가짜 루트 `compare` Holm 키, `meta.prereg` OK | 일치 |
| 13 | 카나리 기준일 = 세트를 처음 돌린 날 (E :140) | `eval/canary.py:168-175,227-228` | 행 85 | **일치(§79)** |
| 14 | 모델 식별 필드가 바뀌어도 같은 처리 (E :139) | `Calibration.load` | 시험 묶음; 다른 지문의 표류는 J5에 안 셈(`hand14.py`) | 일치 |
| 15–17 | E0.5 표·재시험·같은 시각 K = 3 (E :236-238) | `e05.vote_steps`, `e05.py` | 시험 묶음; `analyze` 독립 재계산에 `vote_steps` 사용(행 90) | 일치 |
| 18 | γ 2/3 (E :240, M4 :276) | `m4.share_at_least:72` | 2/3·4/6·66/99·200/300 참, 66/100·3/5·1/2·199/300 거짓 | 일치 |
| 19–20 | `C_flip` 두 식, A0–A4·층 (E :242, :246) | `e05.py` | 시험 묶음 | 정본 기록(§73) / 일치 |
| 21–28 | 판정 1–10 경계 (E :256-265) | `replay.judge_e05`, `e05.py` | 시험 묶음; 파드 e05 `E05_DONE` | 일치 |
| 29 | FLIP_TH 후보 α 0.01 (E :253, :487; M4 :285) | `e05.py:437-446` | 파드·로컬 키 q0.99·q0.999·q0.95, `flip_th_initial.alpha` 0.01·key q0.99 | 일치 |
| 30 | 같은 시각 뒤집힘 성공·섭동 따로 (E :253, §27) | `e05.py:352-383` | 시험 묶음 | 일치(N10) |
| 31–33 | d_p95 = E0 값, 분당 400 [가정], E1 반분 | `e05 --d-p95`, `calib.halves` | — | 정본 기록 / N10 |
| 34–35 | ECE 15 동일 질량, 오답 < 30 판정 불가 (E :320) | `calibration.py` | 시험 묶음 | 일치 |
| 36 | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat` | n 10·α .1 → 10, n 5 → inf, n 19 → 18 | 일치 |
| 37–40 | log p 자름·질문별 온도·원 확률·판정 1 (E :333-339) | `calibration.py` | 시험 묶음; 파드 calib `CALIB_DONE` | 일치 |
| 41 | 판정 7 재보정 결속 (E :345-346) | `Calibration.load`, `core.py:128-130` | 시험 묶음(qid 해시 거부) | 일치 |
| 42–43 | 판정 8 J5, `ambiguous` ECE 제외 | `calibration.py` | 시험 묶음 | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| 45 | N_max = ⌈d̂/T_c⌉+1 (M4 :258) | `m4.py:178-182` | d̂ 0.307 → 2, 0.33 → 2, 0.34 → 3, 0.66 → 3, 0.9 → 4 | 일치 |
| 46–49 | γ·W·비가역 W+1·τ (E :487, M4 :276, :291, §7) | `m4.py` | 시험 묶음 | 일치 |
| 50 | conformal α 0.01·w 5 ((b) 경계) | 확인 헤드 보정 파일 | 기본 미보정 | SCOPED S5 |
| 51 | STALE_MAX 1.5 s (E :487) | `m4.older_than:56` | 1.5 유지·1.5000001 폐기·0.1+0.2+1.2 유지 | 일치 |
| 52 | C2 = VLM Stream (E :495, M4 :332) | `conditions.py`, `m4.py:220-226` | 가짜 세계 C2 30판 요청 1,110개 모두 `none`, 옛 코드와 30/30 비트 동일 | 일치 |
| 53 | C0·C1·C3·C4·C5·C6 설정 (M4 :329-345) | `conditions.py:23-32` | 가짜 세계 8조건 실행 | 일치 |
| 54 | C5 = §4.2 전체, C5' = (b) 범주 뺌, 판정 3 (M4 :155, :232, :340-342, :361) | `core.b_line:199-205` | 행 77–82 | 일치(§77) |
| 55 | H 1과 3 (정본 §2, M4 :188-189) | `m4.early_ask_steps:61` | (0, 0.307, 0.33, 1.0) → [1, 2, 3], lead 1.5 → [1, 2, 3, 4]; 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 |
| 56–58 | n_LA 2·조기 호출 당겨 씀·FLIP_TH 끔 (M4 :275, :262, :287) | `m4.py`, `core.py:459-503` | 시험 묶음; 조기 호출 시각은 옛 코드와 같음(가짜 세계 C4 12·C5 13판 호출 시각 동일) | 일치 |
| 59 | 경계 직후 W 2·γ 1.0 등 | 없음 | §73 D5 | SCOPED S9 |
| 60 | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.select_rule:131` | 0.8999 → None, 차 0.02 → plan, 0.0201 → short1 | 일치 |
| 61–62 | 폐루프 RD 재표집 = layout 짝, 주 RD = Score (EVAL :182-184) | `closed.py`, `rd.py` | 파드 rd `drop.random` n 135 | 일치 / N10 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | §71 보충 | SCOPED S1 |
| 64–65 | M4b 2,000회, E-M4-lat 비례 STALE_MAX | `m4b/*` / 없음 | §72 예외 / §74 보충 | 일치 / SCOPED S11 |
| 66–67 | H = 1 창·`lead_max` 유한한 양수 (§75, §76 N4) | `m4.py:106-113`, `closed.py` | inf·0·−1·NaN 거부, 1e-9·1.5 받음; 파드 `--m4-lead-max inf`·`--m4-h 0` rc 1 | 일치 |
| 68 | E0 판정 4 (E :183, :197) | `analysis/latency.py` | 행 94 | 일치 |
| 69 | E-M4 판정 7 | 다스텝 DecCall 없음 | §75 보충 (2) | SCOPED S12 |
| 70 | FROZEN = 송신 시각 기준 (M4 :150) | `m4.py:228` | §77 N3 | 정본 기록 |
| 71 | 카나리 표류 → 분리 보고·재보정 뒤 재사용 (E :139, :347) | `closed.j5_after_canary:169-185` | 행 93 | **일치(§79)** |
| 72–76 | 응답 모델 필드·재시도 기록, E0.5 정답, `fine_dir`, Astra 카나리 | `models`, `common` | §77 N4·N5, §67 보충 | 일치 / SCOPED S13·S6 |
| 77 | (b) 범주 줄: C4·C5·C6 실음, C0–C3·C5' none (M4 :340-342, §77 (iii)) | `core.b_line`, `conditions.py` | 가짜 세계 240판 요청 7,734개: 모든 요청의 마지막 줄 = 독립 재구성(그 시각까지 끝난 마지막 경계 범주 + 늦은 T2 올림, C0–C3·C5'는 none) **불일치 0**(값 none 4,874·OK 2,534·DEVIATE 172·CONTRADICT 105·LAG 49), `last_step:` 줄 정확히 1개; 파드 Isaac C5 {none 1, OK 31, DEVIATE 13, LAG 3}·C5' none 48, blob 상태 마지막 줄 = 행 `last_step` 96/96 | 일치 |
| 78 | 런타임 값 = 마지막으로 끝난 스텝 범주, T1 CONTRADICT, 늦은 T2 DEVIATE 올림 (§77 (ii)) | `core.py:350-355,537-558` | 행 77 재구성에 포함 | 일치 |
| 79 | 경계 틱 호출 = 방금 끝난 스텝 범주 (§79 N1; M4 §4.2 :232) | `core.act:455-503` | 새 코드: 경계 틱 호출 5,206개 모두 그 틱에서 확인한 범주(C0–C3·C5'는 none); 옛 e6ab856: C4–C6 경계 틱 호출 1,770개 중 233개가 앞 스텝 범주; 틱 시작 값(in-flight·슬롯·조기 깃발) 유지 → C0–C3 120/120 옛 코드와 비트 동일 | **일치(§79)**, 영향 범위 N2 |
| 80–82 | 학습 자료 값, 학습 항목 상태, C5' none 줄 (§77 (i)(iii)(iv)) | `deccall_snap.py`, `stagea_data`, `core.b_line` | 시험 묶음(13회차 실측 그대로 — 학습 자료 유도 코드 불변) | 일치 |
| 83–84 | ser-A-min-2, 옛 체크포인트 거부 (§77) | `serialize.py`, `stagea_train.serializer_of` | 시험 묶음; 파드 e05 `question_ids` = 13회차 파드 새 판본 값(`8e7762b83477@v1` …) | 일치 |
| 85 | 카나리 세트 = 고정 `question_id@vN`, 판본 바뀌면 새 기준일 (E :137-140, §77, §79 D2) | `canary.select_baseline:168-175`, `run_canary:227-228` | 로컬 순수 4경우(같은 세트·qid 첫날, 새 판본 → 그 판본 첫날, 다른 세트 건너뜀, 본 적 없는 판본 → None); 파드 실제 `dev_v1` 세트·가짜 루트: 옛 ser-A-min-1 기준(09-24, qid `02e56df7dd80@v1` …)만 있을 때 첫 판 `baseline` null·`drift_suspect` null; 같은 판본 09-23 판과 옛 판본 09-22 판을 두면 `--force` 판 `baseline` = 09-23(더 이른 옛 판본 건너뜀), 답을 바꿔 둔 기준이라 `drift_suspect` 참 | **일치(§79)** |
| 86–88 | 결정 호출 행 `probs`·blob·`last_step`, Astra 원응답, 결정 이미지는 해시만 (E :125, §28 A6, §77 D4) | `core.py`, `reqhash.request_body` | 행 6; 파드 blob 폴더 = 요청·응답 json + Astra jpg | 일치 / 정본 기록 |
| 89 | FLIP_TH 후보 α 범위 {0.001, 0.01, 0.05} (M4 :285) | `e05.py:437-446` | 행 29 | 일치 |
| 90 | FLIP_TH = 성공 실행 flip_score의 1−α 분위(split conformal), `question_id@vN`별 (M4 :287, :44; §28 J4 :260; §79 D1) | `e05.flip_th_conformal:271-281`, `analyze:293,326-328,437-446`, `main:695` | 손 계산(정수 산술) 17건: n 47·98 (α .01) → 순위 48·99 > n → None, n 99·100·150 → 99·100·150번째, n 199 → 198번째, α .05 n 18 → None·19·20·39·100 → 19·20·38·96번째, α .001 n 998 → None·999·1000 → 999·1000번째, n 0 → None; `n_needed` 99·19·999 모두 일치; 같은 저장소 J5 `conformal_qhat`과 같은 값 4/4; `analyze`에 무작위 표(성공 P0 + 실패 P0 + P1 섞음)를 넣고 질문별 TV를 따로 세어(`vote_steps` + 다중집합 TV) 순위 값 비교 — n 72 → None, n 112 → 112번째 값 일치, 실패 P0·P1 제외 확인; 파드 모의 e05(`jsel_dev` P0·P1 2편): 다섯 질문 모두 n 47·순위 48·`finite` false·`n_needed` 99, `c_flip.question_ids` 기록 | **일치(§79)** |
| 91–92 | 같은 시각 뒤집힘 성공·섭동, 층별 A0 대비 flip (§2A.4, §27) | `e05.py` | 시험 묶음 | 일치 |
| 93 | 카나리 표류 의심 → J5 끔, 재보정 뒤 재사용 (E :139, :347, §77 N6, §79 D3) | `canary.latest_canary:149-165`, `closed.j5_after_canary:169-185`, `closed.py:407-410` | 실제 파일 읽기(`latest_canary`) 10경우: 09-21 표류·09-22 깨끗·보정 09-20 → **끔**, 보정 09-21T13 → 켬, 표류 뒤 깨끗 3일·보정 이전 → 끔, 표류 두 번(09-21·09-23)·보정 09-22 → 끔(최근 표류 기준), 보정 09-23 → 켬, 표류 없음 → 켬, 같은 날 23:59:59 → 끔·00:00 → 켬, `utc` 없음 → 끔, 다른 지문 표류 → 안 셈; 파드 가짜 루트에서 표류 판 → `last_drift` 채워지고 보정 09-20이면 끔 | **일치(§79)**(N10) |
| 94 | E0 판정 4 (E :183, :197, §77 N7) | `latency.step_votes:93`, `judgment4:108` | 지연 0.2 s: lead 1.5 → 스텝당 4표, lead 1.0 → 3표, `judgment4` 중앙값 4·3 → 가능 | 일치 |
| 95 | S-E2E 설정 (`prereg_se2e.md` §3) | 파드 실행 로그 | 13회차 N4 그대로(설정 변경 없음), 드라이버 rc 모두 0 | 일치 |
| 96 | S-E2E 판정 (a)–(e) (`prereg_se2e.md` §4, §77 보충 2) | `tools/se2e/se2e_verdict.py` | 구성 로그 29건(N1): 경계·실패 사례 모두 사전 등록대로, 입력 검사 빈틈 3가지 | 일치(빈틈 N1) |
| 97 | S-E2E 재개·evalck | `stageb_train` | 파드 CPU `test_stageb_torch.py` 통과(1001 중), 실제 로그 `evalck` 같음·재적재 차 0.0 | 일치 |
| 98 | 라벨 복원 기준(계획 DC4 ≤ 1 mm → §78 (1) 비트 동일) | `sim/labeler.py:177-221,313` | `REPLAY_TOL` 0.0, 시험 묶음(`test_labeler_logic.py`) | 일치(소비 쪽은 행 100) |
| **99** | **에피소드마다 PhysX 장면 재생성, 모든 호출자 기본 (§78 결정)** | `sim/scene.py:418-425,501-535,621-635` | 로컬 모의 시험 8개(리셋마다 `sim.reset(soft=False)`가 `env.reset` 앞, 물리 자산 재초기화·카메라 렌더 프로덕트 불변, 멈춘 동안 이 시드 자세 기록·앱 제어 깃발 복구, 렌더 카운터 0, `hard_reset=False` 옛 동작); grep: `make_env` 호출 13곳 모두 기본값(`hard_reset=False` 호출 0), `Env.reset` 우회 0; **파드 Isaac 한 워커 C5 → C5'(DEV 7, 모의 선택기)**: 행동 1,592개 비트 동일, 호출 48개 시각·답 동일(13회차 e6ab856: 스텝 17부터 TCP 0.2 mm, 28번째 호출부터 답 다름) | 일치(행렬은 N9) |
| **100** | **라벨 신뢰 = 재생 비트 동일, `replay_maxabs > 0` 행 제외 (§78 (1))** | `eval/common.load_truth`(outcome), `train/stagea_data.outcome_factory`·`target_keys` | `replay_maxabs` 0.37 행이 `outcome:plan` 정답에 들어감(`trust14.py`); 거르는 코드 없음 | **불일치 → D1** |
| **101** | **R2_TRAIN은 하드 리셋 빌드로 재기동, 옛 녹화 처리 결정 보류 (§78 (2)(3))** | 파드 실행(읽기만) | 도는 `datagen.gen` 프로세스 `PYTHONPATH` = `code_r2train_e8e1864`, `OMP_WAIT_POLICY=PASSIVE` | 일치 / SCOPED S17 |
| **102** | **빈 입력 거부 (§79 N5)** | `eval/common.load_episodes:344-352`, `rd.expand_dirs:40` | 로컬 `main()` 호출: `e05` 없는 폴더·빈 폴더·`","` → rc 1, `--data` 없음 → argparse rc 2, `rd` 없는 변형 폴더·`calib` 없는 fit 폴더 → rc 1 | 일치(`--seeds` 0편은 N3) |
| **103** | **Isaac 워커 `OMP_WAIT_POLICY=PASSIVE` (§79)** | `closed.worker_cmd:188-199` | 명령의 안쪽 `env …` 목록에 `/isaac-sim/python.sh`보다 앞에 있음; 파드 실제 워커(`python3 -m harvest.eval.closed --worker`)의 `/proc/<pid>/environ`에 `OMP_WAIT_POLICY=PASSIVE`·`IR_INST=r7c14_standard`·`CUDA_VISIBLE_DEVICES=1`; GPU 2 → ValueError | 일치 |
| **104** | **e05 qid 등록부 기본 = `<out>` (§79 곁)** | `e05.py:680` | 시험 묶음(`test_r7c13_data_paths.py`) — 내 파드 판은 `HARVEST_QID_REGISTRY`를 scratch로 지정해 기본값은 안 탐 | 일치 |
| **105** | **S-E2E 판정 실행 = 커밋 스크립트, 결과 전 고정 (§77 보충 2)** | `tools/se2e/se2e_verdict.py` | 커밋 0b056b8(11:07:43 UTC) < 주 학습 끝(드라이버 `main rc=0` 11:34 UTC); 파드 사본 sha256 같음; 읽기 전용 재실행 결과 = `verdict.json` 바이트 동일 | 일치 |
| **106** | **S-E2E 진단 사전 등록은 결과 전 (`prereg_se2e_diag.md` 머리)** | 문서 | 파일 수정 11:48:08 UTC < D1 시작 11:52 UTC·D3 예측 11:53:19 UTC(파드 파일 시각) | 일치(구현 S18, N5) |
| **107** | **판정 4 AUROC = 질문 평균 점수 (§79 [Claude 결정] (1))** | `e05.py:348,428-431` | 사전 등록이 질문별을 적지 않음 | 정본 기록 |
| **108** | **FLIP_TH 창(직전 스텝 3표) 대 런타임 창(4 대 4) (§73, §79 (2))** | `e05.py`, `m4._update_flip` | 척도 [0, 1] 같음 | 정본 기록 |

### 5.1 13회차 표(`r7_cycle13.md` §5)와의 차이
- 행 13·71·85·90·93: 13회차 불일치(D2·D3·D2·D1·D3) → 이번에 동작으로 일치(§79).
- 행 79: 13회차 "같은 틱 호출은 경계 전 → 다음 호출부터" → §79 N1로 규칙이 바뀌어 "경계 틱 호출 = 방금 끝난 스텝"으로 다시 대조, 일치.
- 행 8·99: 13회차 N2(같은 워커 안 물리 이력 차) → 하드 리셋으로 C5·C5' 비트 동일.
- 행 98 → 새 행 100: §78 (1) 신뢰 기준의 소비 쪽을 대조해 **불일치(D1)**.
- 새 행 101–108: §78 데이터 처리, §79 N5·워커 환경·qid 등록부, S-E2E 판정 실행·진단 사전 등록 시각, §79 [Claude 결정].

## 6. 확인한 것 (근거)

### 6.1 13회차 수정(정본 §79)과 §78의 독립 확인 (과제 2)
- **D1 FLIP_TH**: 행 29·89·90. 손 계산은 `(n+1)(1000−α‰)/1000` 정수 올림으로 따로 셌다(부동소수 없음).
- **D2 카나리 기준일**: 행 13·85(로컬 순수 + 파드 실제 세트, 모의 모델, 가짜 루트 `canroot`).
- **D3 J5**: 행 71·93(`latest_canary`가 실제 파일을 읽게 하고 `j5_after_canary`에 그대로 넘김).
- **N1 경계 틱**: 행 77·79. 가짜 세계 도구(`rt_diff.py`)는 `tests/runtime/fakeworld.py`만 빌리고 기록기·주입·검사식·재구성은 새로 썼다; 같은 입력을 e6ab856(13회차 추출본 `D:\tools\scratch_qdd\r7c13\repo`, `core.py` 블롭 `36cee23a…` = e6ab856 확인)과 2c4a30d에 넣어 비교. 두 코드 모두 판 간 재현 240/240.
- **N5·워커 환경·qid 등록부**: 행 102–104.
- **§78 하드 리셋**: 행 99(로컬 모의 8개 + 파드 Isaac 한 판 — `closed --model mock --split dev --seeds 7 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c14`, 12:17:06–12:22:49 UTC → `CLOSED_DONE` C5·C5' 성공 1.0, 15.91 s, 행동 1,592개). 결정성 행렬은 N9.
- **S-E2E 판정 스크립트**: 행 96·105, 구성 로그 29건(`verdict14.py`, 결과 `verdict14.txt`).

### 6.2 앞 회차 동작 재확인
- 분할 경계 16건, γ 8건, STALE_MAX 4건, N_max 5건, J5 q̂ 3건, H = 1 조기 호출 2건, 라벨 규칙 3건, `lead_max` 6건, E0 판정 4(`hand14b.py`). C2 요청 모두 none·C0–C3 옛 코드와 비트 동일(행 52·79). 파드 `meta.m4_H` 3·`m4_lead_max` 1.0·`not_in_runtime`·`j5_*`·`canary`(id "none", 이유 기록).

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st` + 코드 사본으로 R2 DEV `/data/harvest/r2/dev/*/*/P0` 전 편 `validate_episode`: **36/36 errors 없음**(standard·dr × mug_tray·mug_marker·bottle_tray 각 6). LeRobot 내보내기 시험 **6 passed**. (옛 물리 녹화지만 구조 검사는 물리와 무관; 재녹화는 S17.) |
| 2 모델 | 충족(CPU) | GPU 없음(0·1 = R2_TRAIN·내 Isaac, 2·3 = S-E2E 진단) → CUDA 시험·GPU 재적재는 건너뜀. 파드 CPU `stageb_train smoke --backbone tiny --device cpu --steps 30`(12:21 UTC): 손실 감소·`save_load` 차 0.0·KI 0.0(N12); CPU 묶음의 `test_stageb_torch.py`(재개 비트 재현·설정 변경 거부)·`test_r7c12_last_step.py` 통과. 실제 GPU 학습은 S-E2E 로그(행 105: 재적재 차 0.0, evalck 같음). |
| 3 폐루프 | 충족 | §6.1 Isaac 판(`CLOSED_DONE`, 호출·Astra 행 필드·blob 확인, `meta.bootstrap` 10000, `meta.prereg` OK, 하드 리셋 빌드). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 절대 경로, 12:21–12:23 UTC): `e05 --data …/jsel_dev/P0,…/P1 --split dev --episodes 2` → `E05_DONE`(n_success_steps 47, 질문별 FLIP_TH 모두 None·`n_needed` 99, `question_ids` 기록), `rd --variants standard=…/jsel_dev,random=…/gen_dev/random/P0 --episodes 1` → `RD_DONE`(n 135), `calib --fit-data …/pool --fit-split pool --heldout …/jsel_dev/P0 --heldout-split dev --episodes 4` → `CALIB_DONE`. 모두 rc 0, prereg OK, git `2c4a30d8`. 결과 라벨 정답(`--truth outcome:`) 경로는 D1. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`(`1ae0402399e00e90`)·카나리·시드·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`j5_*`; 정리 뒤 흔적 없음(머리 규칙 줄). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`)
- `e05 --split cal|test|test_p5`, `calib --fit-split cal`, `rd --split test`, `closed --split test --seeds 1000`, `closed --split cal --seeds 549` → "--split X refused: set HARVEST_ALLOW_SPLIT=X (main session only …)". `closed --split dev --seeds 30`·`--split pool --seeds 5` → "not in split … (refused, never opened)". `--isaac-gpu 2`, `--conditions C5p`, `--m4-lead-max inf`, `--m4-h 0` → "refused before any worker". `HARVEST_ALLOW_SPLIT=dev closed --split test`, `HARVEST_ALLOW_SPLIT=cal e05 --split test` 거부. `gen gen --seeds 10005-10006`(확인 인자 없음), `harvest.sim.determinism fresh --seed 500`(CAL 시드) 거부. **17건 모두 rc 1**, 출력 폴더는 `determinism`의 빈 폴더 1개뿐(N3).

### 6.5 A. 테스트
- 로컬(`…\r7c14\repo` = 2c4a30d archive, Git Bash, `python -m pytest -q -rs -p no:cacheprovider -o addopts="" --basetemp=…\r7c14\tmp\pt1`, TMP·TEMP·TMPDIR = scratch): EXIT 0, **953 passed · 13 skipped**(torch 없음 8, inspect_robots 2, pyarrow 1, isaaclab 1, TODO(P3) 1).
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, TMPDIR·pyc·카나리·qid 등록부 = scratch, 12:00–12:02 UTC): **1001 passed, 4 skipped**(isaaclab·pyarrow·CUDA 없음·TODO(P3)), EXIT 0.

### 6.6 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외, §72–§79)
- §79 N1(경계 틱): `r7c12_fixes.md:17`(**D-1**), 논문 마인드맵(N6); 코드 주석(`core.py:455-503`)·시험 설명·`r7c13_fixes.md`는 새 동작과 맞음.
- §79 D1–D3: `canary.py:10-12` 머리 설명 갱신됨, `closed.py:169-175` 설명 갱신됨; 정본 §77 N6(:678)의 "최신 카나리"는 §79 D3이 덮음(뒤 절 우선); `run_r5.py:71`·`core.py:110`의 "latest canary"는 로그용 id라 맞음. 논문 `X_suppl.tex:27`·`:129`·`:132`(N6).
- §78: `labeler.md:40`, `pool_replay_debug.md:17`·`:134-135`, `r2_datagen.md:147`(**D-2**); `physx_hard_reset.md`는 §78과 맞음(`:3`의 "worker_cmd … 이 설정이 빠졌다"는 그 실험 조건 서술, §79가 고침); `gen.py`·`cli_pool.py`의 prefix·warmup·chain 설명은 여전히 사실(제거 후보, N8); 논문 `6_prelim.tex:30`(N6).
- §78 (1) 신뢰 기준: 코드 소비처(**D1**).
- 13회차 DOC 4건 해소 확인: handoff 12회차 줄·`r7c12_fixes.md` :20·:22·§8 해결 표시, `r6_eval.md:46` [정정 R7 13회차 D-2], handoff `:12` user-log "70번", CLAUDE.md user-log 68·69·70.
- 정본 범위: handoff `:3`·`:5`·`:83` = §79(맞음). 날짜: 정본 §78 11:14·§79 11:50 UTC, handoff 머리 11:50 UTC, 커밋 e8e1864 11:14:54·2c4a30d 11:56:18 UTC — 순서 맞음.

### 6.7 F. 규칙·위생
- 저장소: 작업 트리는 읽지 않고(시작 `git status` = S-E2E 진단 에이전트의 3개 항목; 검토 중에 다른 세션이 `bc1bd54`(S-E2E 판정, 11:58 UTC)·`a4a6257`(S-E2E 진단, 12:32 UTC)을 커밋해 끝 `git status`에는 이 보고서만 미추적 — 두 커밋은 검토 범위 밖; 파일 시각 메타데이터 1건만 읽음) 이 보고서 한 파일만 추가. 로컬 C:: 이 검토의 산출물 없음(하네스 작업 출력 파일만). 파드: 시작 전 목록과 대조해 내 항목만 삭제(머리 규칙 줄), 끝에 내 프로세스 0, `/data` 밖 새 파일 0(`find / -xdev … -newermt 11:58 UTC`). 남의 파일(`/data/harvest/canary`, `r2/dev`, `data/*`, `ckpt/se2e*`, `logs/se2e*`)은 읽기만(카나리 시험은 scratch 복사본, S-E2E 판정 재실행 출력은 scratch).
- 규칙 쪽: 이상 없음(CLAUDE.md user-log 68–70 반영 확인).

## 7. 다음 순회 전에 할 일 (제안)
1. **D1**: 결과 라벨을 읽는 곳(`common.load_truth`의 `outcome:`, 단계 A `OutcomeLabels`)이 `replay_maxabs > 0` 행을 빼고 뺀 수를 기록하게 하거나(§78 (1)), 정본에 "재라벨 전에는 `--truth outcome:`을 쓰지 않음" 같은 결정을 적는다.
2. **D-1·D-2**: `r7c12_fixes.md:17`에 [정정 R7 14회차, 정본 §79 N1] 표시; `labeler.md:40`·`pool_replay_debug.md:17`·`:134-135`·`r2_datagen.md:147`에 [정정, 정본 §78 (2)] 표시.
3. NOTE N1(판정 스크립트 입력 단언 — 다른 판에 다시 쓸 때), N2(§79의 "C5' 20/20" 표본 한계 한 줄), N4(handoff에 §78·S-E2E 종료·13회차 커밋/태그), N5(D3 분석 스크립트를 사전 등록과 대조해 커밋), N6(논문 매시간 갱신 때) 처리 권함.
