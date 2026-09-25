# R7 객관 검증 순회 — 15회차 (cycle 15, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle14.md` §5 표나 `r7c14_fixes.md`의 시험에 기대지 않고 사전 등록 원문에서 대조표를 다시 만들고, 행마다 **구성한 입력 → 실제 함수·런타임 출력**으로 확인함). 작성 2026-09-25 13:25 UTC 무렵(로컬 시작 약 12:58 UTC, 파드 첫 명령 13:00:59 UTC, 파드 정리 끝 13:22:11 UTC).
- 대상: `D:\qdd` `dev` 커밋 `9cee78b`(커밋 시각 2026-09-25 12:57:49 UTC; 태그 `stage3-r7fix14` = `0790dd4`). `2c4a30d..9cee78b` = S-E2E 판정(bc1bd54, `se2e_train.md`), S-E2E 진단 D1–D3(a4a6257, `se2e_diag.md` + `stageb_train.py` 진단 옵션·`predict`), 연구 문서 `docs/research/temporal_context_2026-09-25.md`(118def0), 논문·user-log 71(01d74a9–56f9c0d), **14회차 수정**(0790dd4, 정본 §80), 데이터 규모 곡선 사전 등록 추가(9cee78b, `prereg_se2e_diag.md` §7). 다른 에이전트의 커밋 안 된 작업(시간 맥락 실험)이 작업 트리에 있어 **작업 트리는 읽지 않고**(이 보고서 한 파일만 씀; 예외 — `prereg_se2e_diag.md`·`prereg_se2e.md`의 수정 시각 메타데이터와 `git status`만 읽음) `git -c safe.directory=D:/qdd -c core.autocrlf=false archive 9cee78b`(sha256 `150b18d3…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c15\repo`에 풀어 검토했다. 파드 사본 = 같은 archive + JSON `CODE_VERSION`(`9cee78b1…`, dirty false); 모든 파드 산출 `meta.git.commit` = `9cee78b1…`. 검토 중에 다른 세션이 `b283da2`(논문)·`0b853c2`(E-TC 사전 등록·코드)를 커밋했다 — 범위 밖.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle7.md`–`r7_cycle14.md`, `r7c7_fixes.md`–`r7c14_fixes.md`, 정본 `00-interfaces.md` §1–§80(뒤 절 우선; [사용자] 제목 절은 그대로; 논문 .tex는 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`(§7 추가 등록 포함)·`M4-overlap-commit.md`(조건 정의).
- 분류(14회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본과 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 정본에 없는 것. 정본이 "나중에 할 일"로 적은 것은 SCOPED.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory`로만, 전역 설정 쓰기 없음). 로컬 임시 = `D:\tools\scratch_qdd\r7c15`(스크립트는 모두 Write 도구로 쓰고 경로로 실행; heredoc·`python -`·표준 입력 `cat >` 없음). 로컬 pytest는 저장소 `tests/conftest.py`가 TMP를 `D:\tools\scratch_qdd\tmp_local`로 돌린다(C: 쓰기 없음). 파드 = `/data/harvest/tmp/r7c15`(코드 사본·pytest·산출, 정리 전 398 MB). GPU: Isaac = GPU 1만, 한 번에 Isaac 프로세스 1개(아래 **절차 사고** 참고), GPU 0(R2_TRAIN)·2·3(S-E2E 데이터 규모 곡선 — 다른 세션) 건드리지 않음, GPU 학습 없음. CPU: 시작 전 파드 cgroup `cpu.stat` 10 s = 사용 약 20코어, 스로틀 증가 0 → 내 작업은 `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`, 한 번에 한 묶음. 시드 DEV·POOL만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 `=dev`·`=test`만). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. 남의 프로세스·파일 건드리지 않음(읽기: `ps`, `/proc/<pid>/{cmdline,environ}`의 `CUDA_VISIBLE_DEVICES`·`IR_INST`, `ckpt/se2e*`·`logs/se2e*`·`data/*`).
- **절차 사고 1건**: 가드 음성 시험 목록에 넣은 `closed --model mock --split dev --seeds 0 --m4-h 2`가 거부되지 않았다(정본 §76은 H ≥ 1만 요구, H = 2는 사전 등록 비교값이 아닐 뿐 금지값이 아님 — 내 기대 오류). 그래서 **계획하지 않은 Isaac 모의 한 판**(GPU 1, DEV 0 C5, 13:14:15–13:15:28 UTC, 기본 `--inst-prefix r6` → 기존 공유 kitcache `cyclo-r6_standard` 사용)이 돌았다. 그 시각 내 다른 Isaac 프로세스는 없었고(계획한 판은 13:16:09 시작), `r6` 접두사를 쓰는 다른 작업도 없었다(R2_TRAIN = `r2t_*`). 산출·`carb.*`·`tmp*`·pyc 캐시는 지웠고, 공유 kitcache `cyclo-r6_standard` 안의 캐시 갱신분은 가려낼 수 없어 두었다.

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 2 |
| SCOPED | 18 |
| NOTE | 15 |

14회차 수정(정본 §80)은 **모두 동작으로 확인했다**: 결과 라벨을 읽는 모든 곳(`load_truth` → `e05`·`rd`·`calib`, 단계 A `OutcomeLabels`·기본 `load_pool`, `labels_v2_eval.selfcheck_rows`)이 `replay_maxabs`가 정확히 0인 행만 쓰고 뺀 수를 기록한다 — 로컬 구성 입력(`check15.py`: −0.0·5e-324·inf·NaN·bool·문자열·필드 없음, 다른 폴더의 신뢰 재라벨이 불신 행을 대신함, kind 거름이 먼저, `e05`·`rd`·`calib` `main`의 `meta` 값 = 독립 계산) + **파드 실제 풀 라벨**(6,627행 중 불신 886행·29편 = 정본 수; 고른 3편에서 `load_truth` 133/17 = 독립 계산, 불신 행이 정답에 든 경우 0, 실제 `e05 --truth outcome:plan` `meta.truth_label_trust` 같은 값). 판정 스크립트 입력 검사(구성 로그 22건), `--seeds` 0편 거부(6건)·`determinism` 시드 검사가 `--out` 앞(로컬 10건 + 파드 2건)도 확인. S-E2E 판정은 커밋 스크립트(9cee78b)로 실제 로그에서 다시 계산해 `verdict_v2.json`과 **바이트 동일**, 진단 D1–D3은 원 로그·예측 파일에서 사전 등록 규칙으로 **모든 수를 다시 얻었다**(D3 오답 중 밴드 86/250 = 0.344 등). 새 시드(DEV 12)에서 하드 리셋(§78): 같은 Isaac 워커 C5 → C5' 행동 **1,877개 비트 동일**. 남은 것은 문서 2건 — §78의 사실("고정 선행 실행으로는 이력 의존을 못 없앤다")과 어긋나는 `pool.md`의 채택 서술(D-1), 정본 §80·`r7c14_fixes.md`의 "597행·13편"(실제 13시드·20편, D-2). 연속 무결은 **0회 그대로**.

---

## 1. DEFECT

없음.

## 2. DOC

### D-1. `docs/stage3/results/pool.md:32`·`:57`(같은 사실: `docs/stage3/results/e_m4b_meas.md:19`, 설계 `docs/design/D28-m4-critic-measurement.md:149`) — 고정 선행 실행이 재실행 복원을 비트 동일하게 만든다는 채택 서술에 §78 정정 표시 없음
- 문서: `pool.md:32` "선행 실행을 첫 carry 스냅샷에서 끊고(6가지 이력 뒤 다음 편 비트 동일) … 고친 뒤 풀 전체를 다시 만들었다", `:57` "3.2 재실행 복원: 합격 — 채택 … 조건: CPU PhysX는 같은 프로세스 안에서 리셋 + 재실행이 비트 단위로 같다. 다만 … 모든 편 앞에 고정 선행 실행 … 을 두고", `e_m4b_meas.md:19`·`D28:149` "풀과 같은 결정적 재실행 경로(선행 실행 warmup, 비트 동일)".
- 정본: §78 사실(`00-interfaces.md:686`) "CPU PhysX는 `env.reset()` 뒤에도 장면 내부 상태를 이어 가, 같은 시드가 프로세스 이력에 따라 몇 개의 이산 궤적 중 하나로 간다(풀 재실행 불일치 20편 …)", `pool_replay_debug.md:15` "고정 선행 실행(`canonical_prefix`)이 그것을 항상 같은 값으로 되돌리지 못한다", `:82-89`(K0 prefix 6/20). 다시 만든 지금의 풀에서도 886행·29편이 비트 동일이 아니다(파드 실측, 아래 행 100). `pool.md`에는 정정 표시가 하나도 없다(grep `정정`·`§78`·`pool_replay_debug` → 0건). 14회차 D-2가 같은 사실(§78)로 `labeler.md`·`pool_replay_debug.md`·`r2_datagen.md`를 고쳤지만 이 세 곳은 빠졌다(정본 §69 정정 절차 "같은 사실을 적은 곳을 모두").

### D-2. `docs/design/00-interfaces.md:705`(정본 §80 [Claude 결정] (1)) · `docs/stage3/results/r7c14_fixes.md:24` — "`pool_selfcheck` 4,970행 중 > 0 597행·13편"
- 파드 실측(읽기 전용): `data/pool_selfcheck/dev*_P*.jsonl` 90파일(= DEV 자체 점검 90편, 정본 §65 제목의 "90편"과 같은 단위: 시드 × 섭동) 4,970행 중 불신 **597행**(수는 맞음)은 **13시드 · 20편**(3P1, 4P1, 6P0, 6P2, 9P0, 9P2, 10P1, 13P0, 13P2, 16P1, 17P1, 20P1, 21P1, 24P0, 24P1, 24P2, 25P1, 26P0, 26P1, 26P2)에 있다. 풀(시드마다 한 편)의 "29편"과 달리 자체 점검은 편 ≠ 시드라 "13편"은 틀린 수다. 판정에 쓰이는 수는 아니다(정본 문장 안의 근거 수치).

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀. EVAL H1–H3 기준선 비교.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드에서 진행 중(읽기만: `datagen.gen` 워커 5개, GPU 0·1); `gen gen --seeds 10007-10008` 확인 인자 없이 rc 1.
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8(검사기·계획 서명·편집 거리, 확인 헤드 보정 파일 기본 미보정, M9 복구).
- S6. Astra 카나리 "none"(§67 보충) — 파드 C5·C5' `astra` 행 `canary_id` "none".
- S7. S-E2E 체크포인트의 런타임 형식 차이와 새 코드의 거부(§77 보충 (2)).
- S8. CONTRADICT-soft(§68 K6).
- S9. §73 D5 M4 설계 확장.
- S10. §73 N5 E1 범위(`calib` = 판정 1·8).
- S11. §74 보충 E-M4-lat 비례 STALE_MAX, 런타임에 없는 조건 C2'·C2'-S·C2-match·C3'·C3''·C5-A3·C-FIX(파드 `closed.json` `meta.not_in_runtime`).
- S12. §75 보충 (2) E-M4 판정 7.
- S13. §77 N8 (13): E0.5 `fine_dir`, Jev-L E0 측정 도구, 결정 호출 이미지 원본 저장 안 함, 완료 정의 밖 사전 등록 실험.
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` "boundary (ambiguous)" 주석 — 9cee78b에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화(J4를 켜기 전 필수 작업).
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬(본 실험 전).
- S17. §78 (2): 옛 물리 녹화(풀·R2 DEV·E0.5 스냅샷)의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정 — 그때까지 `--truth outcome:`은 886행을 뺀 정답(§80).
- **S18**. `prereg_se2e_diag.md` §7 데이터 규모 곡선의 구현(`--train-fraction`, `--eval-train-per-kind`)은 커밋 밖(파드 `code_se2e_diag/harvest/train/stageb_train.py` sha256 `11e11795…` ≠ 커밋 `2991f46c…`, 판 폴더 `CODE_HASHES.txt`에 기록) — 9cee78b 검토 범위 밖, 결과도 아직 없음. 사전 등록 시각만 확인(행 114). (14회차 S18 — D1–D3 구현이 커밋 밖 — 은 a4a6257로 해소: D1·D2·D3 `CODE_HASHES.txt`의 `stageb_train.py`·`test_stageb_torch.py` = 커밋 블롭 `2991f46c…`·`3db6f476…`.)

## 4. NOTE
- N1. **`--m4-h`는 1 이상이면 받는다**(`closed.py:310` 도움말 "1 and 3"; 정본 §76은 H < 1 거부만 정함): 위 절차 사고의 원인. 결함 아님 — 사전 등록 비교는 H 1·3이고 다른 값은 탐색용으로 돌 수 있다. 도움말에 "다른 값은 사전 등록 밖"을 적으면 오해가 준다. 같은 줄의 내 입력 오류 하나 더: 파드 `e05 --seeds 29`를 "0편 선택" 시험으로 넣었으나 `jsel_dev/P0`에 ep29가 있어 정상 실행(rc 0)이었다 — 0편 거부는 로컬 구성 폴더로 확인(행 102·120).
- N2. **`stageb_train` 재개 검사가 새 진단 옵션을 보지 않는다**: `RESUME_KEYS`(`stageb_train.py:219-221`)에 `lr_schedule`·`warmup_steps`·`train_subset`·`train_subset_seed`가 없어, 파드에서 `check_resume_args(base, {…, 이 값 변경})`이 모두 **받아들여졌다**(`lr` 변경은 거부). 이 옵션을 바꾸고 `--resume`하면 스케줄·데이터 순서(`order`는 부분집합 색인)가 조용히 달라진다. 재개를 쓴 진단 판은 없어 결과 영향 없음. 넣기를 권함(작업 트리의 `--train-fraction`도).
- N3. **같은 자료에서 두 "뺀 수"**: `load_truth`는 5질문(QUESTIONS) 행만 세고, 단계 A `OutcomeLabels`는 `fine_dir`를 포함한 모든 행을 센다 — 파드 전체 풀에서 단계 A `label_trust` = 5,741 / **886**, 5질문 기준 불신 행 = **805**. 정본 §80의 "886행"은 단계 A 쪽 수와 같다. 결과 문서에 어느 기준인지 적기를 권함.
- N4. **`se2e_train.md` 표 반올림**(판정 무관 — 판정은 로그에서 스크립트가 계산): §2 표 88칸 중 5칸이 셋째 자리에서 1 차이 — A 500 fm 0.30349 → "0.304", A 3500 fm 0.07749 → "0.078"·mse 0.01649 → "0.017", B 500 fm 0.23248 → "0.233", B 4000 mse 0.01348 → "0.014"(두 번 반올림 모양). 나머지 83칸·(b) 끝 3점 평균·학습 dec 4000–4500 평균 0.7008 일치. `:40`의 "진단 … (진행 중, 결과 `se2e_diag.md`)"는 a4a6257에서 끝났다(작성 시점 기록).
- N5. **사전 등록 커밋 시각**: 세 사전 등록 모두 파일 내용은 실행 전에 고정됐지만 커밋은 실행 시작 뒤다 — `prereg_se2e.md` 커밋 989cc05 09:45:19 UTC > 학습 시작 09:40:41Z(파드 사본 `ckpt/se2e/prereg_se2e.md` 09:40:40, sha256 = 커밋 블롭 `29191168…`), `prereg_se2e_diag.md` 커밋 2c4a30d 11:56:18 > D1·D3 시작 11:52:17Z(파일 수정 11:48:08, 14회차 N5), §7 추가 등록 커밋 9cee78b 12:57:49 > 규모 곡선 시작 12:36:17Z(작업 트리 파일 수정 12:33:46Z, 지금 파일 = 커밋 블롭 11,465바이트, 추가 31줄·삭제 0줄). 결과 전 고정은 맞다. 실행 전에 커밋(또는 파드 사본 해시 기록)을 권함.
- N6. **진단 구현·해석 확인**: `prereg_se2e_diag.md` §1은 "`code_se2e_run`의 `stageb_train.py` 교체"인데 실제는 복사본 `code_se2e_diag`(S-E2E 사본 보존, `se2e_diag.md:16`에 적음; `stageb_data`·`stageb_model` 블롭 = S-E2E 매니페스트) — 무해. D3 분석 스크립트(`logs/se2e_diag/d3_analyze.py`)는 여전히 저장소 밖(14회차 N5)이지만, 내가 `pred.jsonl` + 행 파일 `ee_delta`에서 사전 등록 정의(D 1 cm, 밴드 2 mm·상대 0.10, MAG 경계 = `labels_v2.MAG_EDGES_M` 0.707·1.414·2.828·5.657 cm)로 따로 계산한 값이 문서와 모두 같다(아래 행 112). 5.4절 인접 프레임 일관성(판정 밖)은 다시 계산하지 않았다.
- N7. handoff: `docs/handoff.md:108` 14회차 수정을 "커밋 안 함"으로 적었으나 0790dd4·태그 `stage3-r7fix14`로 커밋됨(수정 에이전트 시점 기록, 13·14회차와 같은 모양); 9cee78b(규모 곡선 사전 등록)·진행 중 규모 곡선 판 줄 없음; `:12` user-log "70번"(지금 71 — `r7c14_fixes.md:39`가 알고 둠).
- N8. user-log 71(시간 맥락 1순위 선호, 논문·그림 바로 반영)은 CLAUDE.md에 없다 — 선호·지시라 제약이 아닐 수 있다(14회차 N13과 같은 종류).
- N9. **논문(매시간 갱신 때)**: `paper/sec/X_suppl.tex:130` 14회차 행 "(수정 중)"(0790dd4에서 구현됨). `paper/sec/6_prelim.tex:61` "비트 동일 아닌 행 13.4 %(886) 거부권 제외"는 §80과 맞음.
- N10. 라벨을 **쓰는** 쪽 `cli_label.py:50` `max([o.get("replay_maxabs") or 0.0 …])`는 값이 없는 결과를 0.0(= 신뢰)으로 적는다 — §80 [Claude 결정] (1)("필드 없음 = 불신")과 반대 방향의 잠재 틈. 지금 두 호출(`label_pool`·`selfcheck`)은 늘 `replay`·`state`를 넘겨(`cli_label.py:82-83`·`:148-149`) 모든 결과에 값이 있으므로 영향 없음(`r7c14_fixes.md:37`에만 기록, 정본에는 없음).
- N11. 시험 수: 로컬 **987 passed / 13 skipped**(`r7c14_fixes.md:28`의 커밋분과 같음; torch 없음 8, inspect_robots 2, pyarrow 1, isaaclab 1, TODO(P3) 1), 파드 CPU **1041 passed / 4 skipped**(`:29`와 같음), LeRobot 6 passed. 파드 CUDA 시험·`tests/sim/test_determinism_isaac.py`는 돌리지 않았다(GPU 없음·CPU 쿼터 보호).
- N12. 단계 B 소형 CPU 스모크(`smoke --backbone tiny --device cpu --steps 40`): 학습 총손실 처음 5 평균 3.055 → 끝 5 2.903, eval fm 2.438 → 2.132, dec 0.787 → 0.655, `save_load` `max_abs_action_diff` 0.0·eval 같음, KI(흐름 정합 → 백본) 기울기 0.0.
- N13. 14회차 N10(13회차 N7–N9·N14 모음) 그대로.
- N14. 검토 중 파드: S-E2E 규모 곡선 두 판(GPU 2·3, `se2e_scale/1000`·`9371`)과 시간 맥락 준비(`logs/se2e_temporal`)가 진행 중이었다 — 읽기만.
- N15. **기록 시각이 커밋보다 늦다**: 정본 §80 제목(`00-interfaces.md:703`) "2026-09-25 13:10 UTC", `r7c14_fixes.md:3` "작성 13:10 UTC", `handoff.md:3` "마지막 갱신 13:10 UTC"인데 이 내용을 담은 커밋 0790dd4의 시각은 12:57:49 UTC이고(9cee78b도 같은 초) 내가 12:58 UTC에 이미 그 커밋을 받았다 — 짐작 시각으로 보인다(7회차 N1과 같은 종류; 정본 §21–§24의 "처음 …로 잘못 적음" 관례로 정정 권함).

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 파드 산출 `meta.prereg.check` = "OK"(e05·rd·calib·closed). 사전 등록 문서는 `2c4a30d..9cee78b`에서 `prereg_se2e_diag.md`에 §7(31줄 추가, 삭제 0) 말고 바뀌지 않았다. 코드 줄은 `9cee78b` 기준. "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c15\check15.py`(47건 중 46 — 남은 1건은 내 기대 오류: `np.float64(0.0)`에 대해 함수는 참(numpy bool)을 돌려주는데 `is True`로 비교함; JSON 행에는 numpy 값이 없다), `verdict15.py`(22/22), `hand15.py`(56/56); **파드** = §6(`se2e_check.py`, `se2e_check2.py`, `trust_pod.py`, `pod_defs15.sh`, `resume15.py`, `closed15_check.py`, `pod_misc15.sh`). "시험 묶음" = 해당 행의 구현을 부르는 저장소 시험이 로컬 987·파드 1041 묶음에서 통과(이번에 행동을 따로 만들지 않은 행). 굵게 = 이번에 처음 대조하거나 판정이 바뀐 행.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 (E :113-120, 정본 §66) | `eval/splits.py:19-42` | `split_of` 경계 20건(−1·0·29·30·499·500·549·550·999·1000·1149·1150·1299·1300·1329·1330·1999·2000·2119·2120); 파드 가드 19건 rc 1(§6.4) | 일치 |
| 2 | POOL 120 × 10, 경계 사례 30 % 과표집 (E :121, §76 D-2) | `sim/snapshot.py:102-136` | 시험 묶음; 파드 풀 `ep*.jsonl` 120개 | 일치(주석 S14) |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` | 시험 묶음 | 일치 |
| 4 | 분할 = 에피소드 (E :122) | `pool_split`, `calib.halves` | 파드 calib `CALIB_DONE`(fit POOL·heldout DEV P1) | 일치 |
| 5 | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py:26-38` | 시험 묶음; 파드 Isaac C5·C5' 성공 18.76 s | 일치 |
| 6 | 호출 기록: 질문별 확률·요청/응답 원문(E :125), Astra A6(E :126, §28 :255) | `core.py:289-322,408-418` | 파드 C5·C5' 호출 112행: `request_blob` = `request_sha256` = sha256(blob) 112/112, blob 이미지 해시 = 행 `image_sha256` 112/112, `response_blob` 해시·`probs` 질문 = `answers` 질문·합 1 112/112; Astra 4행 요청 해시·JPEG 해시·`output_text`·`max_output_tokens`·`effort` 4/4 | 일치 |
| 7 | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `stats.py:4` | 파드 closed `meta.bootstrap.n_boot` 10000·단위 layout seed | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate` | 파드 C5 대 C5' 같은 워커 물리 이력 차 없음(행 99) | 일치 |
| 9–12 | 판정 2 Holm, 판정 10, 카나리 Holm, 판정 절 해시 (E :131, :265, :139, :133) | `e05`, `canary.py`, `eval/common.py` | 시험 묶음; 파드 `meta.prereg` OK | 일치 |
| 13 | 카나리 기준일 = 세트를 처음 돌린 날 (E :140, §79 D2) | `eval/canary.py:168-175,227-228` | 시험 묶음(`test_r7c13_canary.py`) | 일치 |
| 14 | 모델 식별 필드가 바뀌어도 같은 처리 (E :139) | `Calibration.load` | 시험 묶음 | 일치 |
| 15–17 | E0.5 표·재시험·같은 시각 K = 3 (E :236-238) | `e05.vote_steps`, `e05.py` | 시험 묶음; 파드 e05 `E05_DONE`(DEV P0·P2 3편씩) | 일치 |
| 18 | γ 2/3 (E :240, M4 :276) | `m4.share_at_least:72` | 2/3·4/6·66/99·200/300·667/1000·1/1 참, 66/100·3/5·1/2·199/300·666/1000·0/1 거짓 | 일치 |
| 19–20 | `C_flip` 두 식, A0–A4·층 (E :242, :246) | `e05.py` | 시험 묶음 | 정본 기록(§73) / 일치 |
| 21–28 | 판정 1–10 경계 (E :256-265) | `replay.judge_e05`, `e05.py` | 시험 묶음; 파드 e05 `E05_DONE` | 일치 |
| 29, 89 | FLIP_TH 후보 α 0.01·범위 {0.001, 0.01, 0.05} (E :253, :487; M4 :285) | `e05.py:437-446` | 행 90 | 일치 |
| 30 | 같은 시각 뒤집힘 성공·섭동 따로 (E :253, §27) | `e05.py:352-383` | 시험 묶음 | 일치 |
| 31–33 | d_p95 = E0 값, 분당 400 [가정], E1 반분 | `e05 --d-p95`, `calib.halves` | — | 정본 기록 |
| 34–35 | ECE 15 동일 질량, 오답 < 30 판정 불가 (E :320) | `calibration.py` | 시험 묶음 | 일치 |
| 36 | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat:59` | α ∈ {0.001, 0.01, 0.05, 0.1, 0.2, 0.3} × n 0–3000(18,006경우)를 유리수 순위와 대조 → 불일치 0(부동소수 `(n+1)*(1-α)`가 정수 경계에서 어긋나는 경우 없음) | **일치** |
| 37–43 | log p 자름·질문별 온도·원 확률·판정 1·판정 7 결속·판정 8 J5·`ambiguous` ECE 제외 (E :333-346) | `calibration.py`, `core.py:128-130` | 시험 묶음; 파드 calib `CALIB_DONE` | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| 45 | N_max = ⌈d̂/T_c⌉+1 (M4 :258) | `m4.py:178-182` | 시험 묶음(14회차 경계 5건과 코드 불변) | 일치 |
| 46–49 | γ·W·비가역 W+1·τ (E :487, M4 :276, :291, §7) | `m4.py` | 시험 묶음 | 일치 |
| 50 | conformal α 0.01·w 5 ((b) 경계) | 확인 헤드 보정 파일 | 기본 미보정 | SCOPED S5 |
| 51 | STALE_MAX 1.5 s (E :487) | `m4.older_than:56` | 1.5·1.5+1e-10 유지, 1.5000001 폐기, 0.1+0.2+1.2 유지 | 일치 |
| 52–53 | C2 = VLM Stream, C0–C6 설정 (M4 :329-345) | `conditions.py`, `m4.py:220-226` | 시험 묶음; 파드 `--conditions C9` 거부 | 일치 |
| 54 | C5 = §4.2 전체, C5' = (b) 범주 뺌, 판정 3 (M4 :155, :232, :340-342, :361) | `core.b_line:199-205` | 파드 Isaac: C5 `last_step` {none 1, OK 32, LAG 8, DEVIATE 15}, C5' none 56/56, 요청 상태 마지막 줄 = 행 `last_step` 112/112 | 일치(§77) |
| 55 | H 1과 3 (정본 §2, M4 :188-189) | `m4.early_ask_steps:61` | 창 [t+d̂, t+lead]을 유리수로 따로 셈 5경우 일치(빈 창이면 d̂ 뒤 첫 스텝); 파드 `meta.m4_H` 3·`m4_lead_max` 1.0; H = 2는 받음(N1) | 일치 |
| 56–58 | n_LA 2·조기 호출 당겨 씀·FLIP_TH 끔 (M4 :275, :262, :287) | `m4.py`, `core.py:459-503` | 시험 묶음 | 일치 |
| 59 | 경계 직후 W 2·γ 1.0 등 | 없음 | §73 D5 | SCOPED S9 |
| 60 | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.select_rule:131` | 0.8999 부적격, 적격 없음 → None, 차 0.02 → plan, 0.0201 → short1 | 일치 |
| 61–62 | 폐루프 RD 재표집 = layout 짝, 주 RD = Score (EVAL :182-184) | `closed.py`, `rd.py` | 파드 rd `RD_DONE`(`drop.random` n 275) | 일치 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | §71 보충 | SCOPED S1 |
| 64–65 | M4b 2,000회, E-M4-lat 비례 STALE_MAX | `m4b/*` / 없음 | §72 예외 / §74 보충 | 일치 / SCOPED S11 |
| 66–67 | H = 1 창·`lead_max` 유한한 양수 (§75, §76 N4) | `m4.py:106-113`, `closed.py:390` | inf·−inf·NaN·0·−0.0·−1 거부, 1e-9·1.0·1.5 받음; 파드 `--m4-lead-max nan` rc 1 "refused before any worker" | 일치 |
| 68 | E0 판정 4 (E :183, :197) | `analysis/latency.py` | 시험 묶음 | 일치 |
| 69 | E-M4 판정 7 | 다스텝 DecCall 없음 | §75 보충 (2) | SCOPED S12 |
| 70 | FROZEN = 송신 시각 기준 (M4 :150) | `m4.py:228` | §77 N3 | 정본 기록 |
| 71, 93 | 카나리 표류 → J5 끔, 재보정 뒤 재사용 (E :139, :347, §79 D3) | `closed.j5_after_canary:169-185` | 시험 묶음(`test_r7c13_canary.py`); 파드 closed `meta.j5_alpha` None·`j5_canary_gate` 기록 | 일치 |
| 72–76 | 응답 모델 필드·재시도 기록, E0.5 정답, `fine_dir`, Astra 카나리 | `models`, `common` | §77 N4·N5, §67 보충 | 일치 / SCOPED S13·S6 |
| 77–79 | (b) 범주 줄·런타임 값·경계 틱 호출 = 방금 끝난 스텝 (M4 :232, §77 (ii)(iii), §79 N1) | `core.b_line`, `core.act:455-503` | 행 54의 파드 판; 시험 묶음(`test_r7c13_*`) — 코드 `2c4a30d..9cee78b` 불변 | 일치 |
| 80–84 | 학습 자료 값·학습 항목 상태·C5' none·ser-A-min-2·옛 체크포인트 거부 (§77) | `deccall_snap.py`, `stagea_data`, `serialize.py`, `stagea_train.serializer_of` | 시험 묶음 | 일치 |
| 85 | 카나리 세트 = 고정 `question_id@vN`, 판본 바뀌면 새 기준일 (§79 D2) | `canary.select_baseline:168-175` | 시험 묶음 | 일치 |
| 86–88 | 결정 호출 행 `probs`·blob·`last_step`, Astra 원응답, 결정 이미지는 해시만 (E :125, §28 A6, §77 D4) | `core.py`, `reqhash.request_body` | 행 6; 파드 blob 폴더 = 요청·응답 json + Astra jpg | 일치 / 정본 기록 |
| 90 | FLIP_TH = 성공 실행 flip_score의 1−α 분위(split conformal), 질문별 (M4 :287, §79 D1) | `e05.flip_th_conformal:271-281` | 행 36과 같은 18,006경우: 값·`finite`·`n_needed` = ⌈1/α − 1⌉ 모두 유리수 기대와 일치 | 일치 |
| 91–92 | 같은 시각 뒤집힘 성공·섭동, 층별 A0 대비 flip (§2A.4, §27) | `e05.py` | 시험 묶음 | 일치 |
| 94 | E0 판정 4 집계 (§77 N7) | `latency.step_votes:93`, `judgment4:108` | 시험 묶음 | 일치 |
| 95 | S-E2E 설정 (`prereg_se2e.md` §3) | 파드 실행 로그 | A·B `config.args`: lr·lr_heads 1e-4, batch 8, epochs 1, save_every 1000, eval_every 500, val 150/0, seed 0·1, KI stop, IMG, λ 1/1/0.1/0.1; 드라이버 시작 09:40:41Z·GPU 2·3·rc 모두 0 | 일치 |
| 96 | S-E2E 판정 (a)–(e) (`prereg_se2e.md` §4, §77 보충 2, §80 N1) | `tools/se2e/se2e_verdict.py` | 구성 로그 22건(행 119) + 실제 로그 재실행(행 105) | 일치 |
| 97 | S-E2E 재개·evalck | `stageb_train` | 파드 CPU `test_stageb_torch.py` 통과; 실제 로그 evalck 같음·재적재 차 0.0(행 105) | 일치(재개 키 빈틈 N2) |
| 98 | 라벨 복원 기준(계획 DC4 ≤ 1 mm → §78 (1) 비트 동일) | `sim/labeler.py:177-221,313` | `REPLAY_TOL` 0.0, 시험 묶음 | 일치(쓰는 쪽 틈 N10) |
| 99 | 에피소드마다 PhysX 장면 재생성, 모든 호출자 기본 (§78 결정) | `sim/scene.py`, `make_env(hard_reset=True)` | grep: `hard_reset=` 인자를 넘기는 호출자 0(모두 기본값); **파드 Isaac 한 워커 C5 → C5'(DEV 12, 모의 선택기)**: 행동 1,877개 비트 동일(첫 차이 없음), 호출 56개 시각·답 동일 | 일치(행렬은 S16) |
| **100** | **라벨 신뢰 = 재생 비트 동일, `replay_maxabs > 0`·필드 없음 행 제외, 뺀 수 기록 (§78 (1), §80 D1)** | `train/stagea_data.replay_bit_identical:49-53`, `eval/common.load_truth:378-411`, `stagea_data.OutcomeLabels:75-83`·`outcome_factory:204-219`, `stagea_train._items`·`cmd_train`(`label_trust`), `tools/labels_v2_eval.selfcheck_rows:135-150` | 로컬: 판정 함수 14경우(0.0·−0.0·0 참; 5e-324·1e-12·inf·NaN·True·False·"0"·None·[0]·−1e-300·필드 없음 거짓; + numpy 1건은 내 기대 오류, §5 머리); `load_truth` — 같은 (kind, seed, k, 질문)의 불신 행(0.2)과 다른 폴더의 신뢰 재라벨 → 재라벨 답만 정답, 필드 없음 빠짐, 원치 않는 시드·kind 행은 세지 않음, stats {3, 2}; 무작위 신뢰도 표(DEV 구성 폴더)로 `e05`·`rd`·`calib` `main` 실행 → `meta.truth_label_trust` = 독립 계산 {26, 19}·변형별·fit+held {40, 35}, 모두 불신이면 `e05` rc 0 `insufficient_data`·{0, 45}; labels_v2 정답이면 null; 단계 A `partial` — 완결 스냅샷 1행 불신 → 4항목, 잘린 스냅샷은 통계에 안 섞임, `.done` 없으면 건너뜀, 기본 `load_pool`(통계 없음)도 거름; `selfcheck_rows` 2남음·3뺌(파일 이름 규칙 밖 무시). **파드 실제 풀 라벨**: 6,627행 중 불신 886·29편·필드 없음 0; 불신 있는 2편 + 없는 1편(2002·2009·2000)에서 `load_truth` {133, 17} = 독립 계산, 불신 행이 정답에 든 경우 0; `e05 --split pool --seeds 2002,2009,2000 --truth outcome:plan` rc 0, `meta.truth_label_trust` 같음, git `9cee78b1`; 풀 전체 단계 A 5,195항목·`label_trust` {5,741, 886}(N3) | **일치(§80)** |
| 101 | R2_TRAIN은 하드 리셋 빌드, 옛 녹화 처리 보류 (§78 (2)(3)) | 파드 실행(읽기만) | 도는 `datagen.gen` 워커 5개(GPU 0·1) | 일치 / SCOPED S17 |
| 102 | 빈 입력 거부 (§79 N5) + **0편 선택 거부 (§80 N3)** | `eval/common.load_episodes:340-369` | 로컬: `seeds {7}`·빈 집합·P1만의 `{2}`, `e05 --seeds 7`, `rd --seeds 9` → SystemExit "no episode selected"; P0+P1에 `{2}` → P0 한 편만 받음 | 일치 |
| 103 | Isaac 워커 `OMP_WAIT_POLICY=PASSIVE` (§79) | `closed.worker_cmd:188-199` | 코드 불변(시험 묶음); 파드 `--isaac-gpu 3` → "0 or 1 only" rc 1 | 일치 |
| 104 | e05 qid 등록부 기본 = `<out>` (§79) | `e05.py:680` | 시험 묶음 | 일치 |
| 105 | S-E2E 판정 실행 = 결과 전 커밋 스크립트 (§77 보충 2, §80 N1) | `tools/se2e/se2e_verdict.py` | 파드: 9cee78b 스크립트(sha256 `6bfc674b…`)를 실제 로그에 읽기 전용 실행 → `verdict_v2.json`과 **바이트 동일**; 0b056b8 판 `verdict.json` 대비 바뀐·빠진 키 0, 더해진 키 6개(`expected_first_last3`·`steps_ok`·`window_ok` × 2); 끝 3점 [4000, 4500, 4686], 창 [2001, 2050] 50스텝, rc 6개 0, (d) 참, (e) tolerance·tolerance(중앙값 0.457 %·0.390 %, 최대 1.621 %·1.533 %) | 일치 |
| 106 | S-E2E 진단 사전 등록은 결과 전 (`prereg_se2e_diag.md` 머리) | 문서 | 파일 수정 11:48:08(14회차) < D1·D3 시작 11:52:17Z; 커밋은 뒤(N5) | 일치 |
| 107–108 | 판정 4 AUROC = 질문 평균, FLIP_TH 창 차이 (§79 [Claude 결정]) | `e05.py` | 코드 불변 | 정본 기록 |
| **109** | **진단 공통 설정: S-E2E와 같은 모델·손실·데이터·검증 300, 해시 보호 파일 불변 (`prereg_se2e_diag.md` §1)** | 파드 `code_se2e_diag`, `logs/se2e_diag/diag_run.sh` | D1·D2·D3 `CODE_HASHES.txt` `stageb_train.py` `2991f46c…`·시험 `3db6f476…` = **커밋 a4a6257 블롭**, `stageb_data.py` `be1e6214…`·`stageb_model.py` `5f3eba50…` = S-E2E `CODE_MANIFEST.txt`; D2 `val_keys_sha` `e22f6d8ef7fc` = S-E2E; GPU D1 = 2, D3 → D2 = 3 | 일치(위치 N6) |
| **110** | **D1: A `last/`에서 새 옵티마이저, lr 5e-5 상수(50스텝 워밍업), +1,200스텝, 300마다 평가; 전제 step 0 dec = A 4686; 규칙 dec(1200) ≤ 0.64388 → 계산 한계 (§2)** | `stageb_train --init-weights`, `--lr-schedule constant` | 파드 로그: 설정 인자 일치(`init_weights` = `se2e_A_s0/last`, `train_subset` 0), 학습 스텝 1–1200(1,200행), lr 스텝 1 = 2e-6(기록은 스케줄러 한 칸 뒤) → 스텝 49부터 5e-5; step 0 dec 0.6777731279791623 = A 4686 값(차 0.0), dec_acc 0.7222; step 1200 dec 0.7375 > 0.643884 → **"이 lr에서 계산 한계 아님"** = 문서 | 일치 |
| **111** | **D2: 기반 모델에서 새로(정규화·어휘 = 전체 train), RB1 500 + RB2 500 고정 무작위, lr 1e-4 상수 1,000스텝, 200마다 학습 부분집합·검증 평가; 규칙 ≥ 0.95 & 검증 ≤ 0.75 / < 0.85 / 그 밖 불확정 (§3)** | `--train-subset 500 --train-subset-seed 0 --eval-train-subset`, `train_subset = stratified_val`(키 정렬 → 시드 추출) | 파드 로그: `init_weights` "", `n_train_full` 37,484 → `n_train_used` 1,000(`train_keys_sha` `fb0b5036dcb9`), 코드에서 `new_model(…, tr 전체)` 뒤에 부분집합; `eval_train_subset` n 1,000 × 6점(0…1000), 검증 n 300; step 1000 학습 부분집합 dec_acc 0.88533·검증 0.56 → **"불확정"** = 문서; 표 6행의 평가 네 열 모두 일치(마지막 열 학습 이동 평균은 다시 세지 않음) | 일치 |
| **112** | **D3: A `last/` 항목별 예측 + `ee_delta`, 여백 정의·밴드(2 mm, 상대 0.10), 규칙 오답 중 밴드 ≥ 50 % → 모호성 한계, 기저율 ≥ 40 %면 "약함" (§4)** | `stageb_train predict`, 저장소 밖 분석 스크립트(N6) | 파드에서 독립 계산(`pred.jsonl` 900항목 + 행 파일에서 300키의 `ee_delta`, 모두 val): Δ로 다시 만든 라벨 = 정답 900/900, 예측 요약 dec 0.6777731·dec_acc 0.7222 = A 4686; 질문별 정확도 0.6767·0.8067·0.6833, 오답 97·58·95 = 250, 밴드 안 오답 35·14·37 = **86 → 0.344 < 0.50 → "라벨 모호성 한계 아님"**, 기저율 163/900 = 0.181(약함 아님), 밴드 안 오답률 0.528 대 밖 0.223, 질문별 밴드 비율 36.1 %·24.1 %·38.9 % — 문서 §5와 모두 같음 | 일치 |
| **113** | **종합 읽기 표 (§5)** | `se2e_diag.md` §6 | D1 아님 × D2 불확정 × D3 아님 → "판정 불가 → 스텝 2배 과적합 시험 또는 시간 맥락 시험을 다음 사전 등록으로" = 문서; 판정 밖 읽기는 판정 밖으로 표시 | 일치 |
| **114** | **§7 데이터 규모 곡선: 실행 전 등록, 설정 고정 (§7.1–7.4)** | 파드 `logs/se2e_scale/scale_run.sh`(커밋 밖 옵션, S18) | 파일 수정 12:33:46Z < 두 판 시작 12:36:17Z(드라이버) < 커밋 12:57:49Z < 결과(진행 중); 스크립트 설정 = §7.1(2,000스텝, 묶음 8, lr 1e-4·헤드 1e-4, 기본 코사인·워밍업 3 %, 시드 0, 500마다 평가, 검증 150/0, N 1,000 = `--train-subset 500` + 학습 평가, 9,371 = `--train-fraction 0.25` + `--eval-train-per-kind 500`, 18,742 = 0.5, 37,484 = 전체, GPU 2: 1,000 → 18,742, GPU 3: 9,371 → 37,484, 30 s GPU 기록) | 일치(구현 S18, 커밋 시각 N5) |
| **115** | **S-E2E 사전 등록 파일 = 실행 시 고정본 (`prereg_se2e.md` 머리, `se2e_train.md:3`)** | 파드 `ckpt/se2e/prereg_se2e.md` | 파드 사본(09:40:40) sha256 = 커밋 블롭 `29191168…d9930d3` = `se2e_train.md:3`의 값 | 일치(커밋 시각 N5) |
| **116** | **S-E2E 결과 문서 수 = 로그 (`se2e_train.md` §1·§2)** | 파드 `log.jsonl` | 표 88칸 중 83칸 일치, 5칸 셋째 자리 반올림 차(N4); (b) 비율 0.147·0.149·0.030·0.022·0.006 일치; 시간·드라이버 rc 일치 | 일치(반올림 N4) |
| **117** | **진단 옵션의 기본값 = S-E2E 동작 (`prereg_se2e_diag.md` §1 "기본값 동작은 비트 동일")** | `stageb_train.make_optimizer:132-147`, `train_loop`, `cmd_train` | 코드 읽기: 기본 코사인 식이 옛 식과 같은 람다, `train_subset(tr, 0)` = 원 목록 그대로(`stratified_val` n 0 → 입력 그대로), 추가 평가·`diag_config`는 옵션이 있을 때만; 파드 CPU `test_stageb_torch.py`(lr 비트 동일 시험 포함) 통과 | 일치(재개 키 N2) |
| **118** | **§80 [Claude 결정] (1) 필드 없음·null·NaN 불신, (2) 행 단위, (3) `partial` 완결 판정은 거르기 전** | 행 100과 같음 | 행 100의 해당 경우(필드 없음·None·NaN 거짓; 같은 스냅샷 다른 질문 남음; 잘린 스냅샷 4행은 통계 밖·완결 5행은 1행만 빠짐) | 정본 기록 / 일치 |
| **119** | **§80 N1 판정 스크립트 입력 검사: (b) 처음 = step 0·끝 3점 = 일정의 마지막 셋, (e) 창 = mid+1…mid+50, 드라이버 폴더 필수** | `tools/se2e/se2e_verdict.py:21-27,74-83,99-110` | 구성 로그(총 4686, mid 2000) 22건: 정상 → (d) 참·(e) tolerance, 비트 동일 → bit; 창 2002–2051·49스텝·2050 중복·순서 바뀜 → fail; 상대차 정확히 1 % → tolerance, 1.01 % → fail; 첫 eval 500·4500 빠짐([3500, 4000, 4686])·4686 두 번([4500, 4686, 4686]) → (b) 불합격; dec 끝 3점 = 0.70 × 처음 통과, 0.7000001 불합격, 끝 0.8000001 불합격; 드라이버 인자 없음·없는 폴더·파일 경로·인자 7개 → rc 1; `driver_B.out` 없음·`evalck rc=1`·`resume rc=` 줄 없음 → (a) 불합격 | 일치 |
| **120** | **§80 N3 `determinism`: 시드 검사 뒤 `--out` 생성** | `sim/determinism.py:194-201` | 로컬 9건(`fresh --seed 500`·`30`·`−1`·`1300`·없음, `history --seeds 3,500`·`3,1149`, `--first 549`, `--partial 2000`) → rc 1·폴더 없음, `compare` → 폴더 생성; 파드 `fresh --seed 1000`·`history --seeds 3,549` rc 1·폴더 없음 | 일치 |

### 5.1 14회차 표(`r7_cycle14.md` §5)와의 차이
- 행 100: 14회차 불일치(D1) → 모든 소비처에서 동작으로 일치(§80), 파드 실제 풀 라벨로도 확인.
- 행 96·105·119: 14회차 N1(입력 검사 빈틈 3가지) → 막힘 확인, 실제 판정 불변.
- 행 102·120: 14회차 N3(0편 선택·`determinism` 폴더) → 거부 확인.
- 행 99: 새 시드 DEV 12로 §78 재확인(1,877개 비트 동일).
- 행 36·90: 부동소수 순위(`conformal_qhat`)를 18,006경우 전수 대조로 넓힘.
- 새 행 109–120: S-E2E·진단 D1–D3·§7 추가 등록의 실행 절차와 판정, §80 결정.

## 6. 확인한 것 (근거)

### 6.1 14회차 수정(정본 §80)의 독립 확인 (과제 2)
- **라벨 신뢰(D1)**: 판독처 grep(`best_by_rule|replay_maxabs|labels/ep|_read_labels|outcome_factory|OutcomeLabels|load_truth|selfcheck`, `harvest`·`tools`·`tests`): 결과 라벨을 정답으로 읽는 곳은 `common.load_truth`(e05·rd·calib), `stagea_data.OutcomeLabels`(단계 A 학습, 기본 `load_pool`), `tools/labels_v2_eval.py` 자기 점검 셋뿐이고 모두 `replay_bit_identical`을 쓴다. 나머지(`cli_label.summarize`·`finalize`·`poolsum`)는 라벨러 자체 요약으로 정본 §80이 그대로 두기로 정했다. 단계 B(`stageb_data`)·`r3_bench`는 labels_v2만 읽는다. 정답이 빠진 질문은 세 평가 모두 건너뛴다(`calib.items_from:45-50`, `rd.items_from:122-127`, `e05.analyze:329-331,382-386` — 기본값을 채우지 않음). 행 100.
- **판정 스크립트(N1)**: 행 96·105·119.
- **0편 선택(N3)·`determinism`**: 행 102·120.
- **문서 D-1·D-2**: `r7c12_fixes.md:17`, `labeler.md:40`, `pool_replay_debug.md:17`·`:135`, `r2_datagen.md:147`에 [정정 R7 14회차 …] 표시 있음. 같은 사실의 빠진 곳은 이번 D-1.
- **정본 §80 수치**: `stagea_data.py` 블롭 `99b17048…`(9cee78b)·`bc052491…`(e6ab856·2c4a30d)·S-E2E 고정 사본 `a8c7f527…`(= 6b013ac 블롭, 파드 `code_se2e_run`·`code_se2e_diag` 둘 다) 일치; 풀 6,627·886·29편 일치; 자체 점검 4,970·597 일치, "13편"은 D-2.

### 6.2 S-E2E·진단 절차 대 파드 로그 (과제 1 일부)
- 파드 읽기 전용: `ckpt/se2e/{se2e_A_s0,se2e_B_s1}{,_resume}/log.jsonl`·`evalck.jsonl`·`CODE_MANIFEST.txt`·`prereg_se2e.md`, `logs/se2e/{driver_A,driver_B}.out`·`verdict*.json`, `ckpt/se2e_diag/{D1,D2,D3}`, `logs/se2e_diag/{diag_run.sh,driver_*.out}`, `logs/se2e_scale/{scale_run.sh,driver_*.out}`, `ckpt/se2e_scale/1000/CODE_HASHES.txt`, `data/se2e/conv/RB{1,2}.stageb.jsonl`. 행 95·105·109–116.
- 시각 순서: S-E2E 사전 등록 파일(09:39:32Z 머리, 파드 사본 09:40:40) < 학습 시작 09:40:41Z < 판정 스크립트 커밋 11:07:43 < 주 학습 끝(`main rc=0` 11:34:43·11:34:48Z) < `verdict.json` 11:57 < 커밋 bc1bd54 11:58:04. 진단 사전 등록 파일 11:48:08 < D1·D3 시작 11:52:17Z < 사전 등록 커밋 11:56:18 < D2 끝 12:29:44Z < 결과 커밋 a4a6257 12:32:15. §7 파일 12:33:46Z < 규모 곡선 시작 12:36:17Z < 커밋 12:57:49(결과 없음).

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st` + 코드 사본으로 R2 DEV `/data/harvest/r2/dev/*/*/P0` 전 편 `validate_episode`: **36/36 errors 없음**(standard·dr × mug_tray·mug_marker·bottle_tray 각 6). LeRobot 내보내기 시험 **6 passed**. (옛 물리 녹화지만 구조 검사는 물리와 무관; 재녹화는 S17.) |
| 2 모델 | 충족(CPU) | GPU 없음(0·1 = R2_TRAIN·내 Isaac, 2·3 = 규모 곡선) → CUDA 시험·GPU 재적재 건너뜀. 파드 CPU `stageb_train smoke --backbone tiny --device cpu --steps 40`(13:12–13:13 UTC): 손실 감소·`save_load` 차 0.0·KI 0.0(N12); CPU 묶음의 `test_stageb_torch.py`(재개 비트 재현·설정 변경 거부·진단 옵션 6개·기본 lr 비트 동일) 통과. 실제 GPU 학습은 S-E2E·진단 로그(재적재 차 0.0, evalck 같음, D1 전제 step 0 값 차 0.0 — 행 105·110). |
| 3 폐루프 | 충족 | Isaac 한 워커(`closed --model mock --split dev --seeds 12 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c15`, 13:16:09–13:20:21 UTC, `IR_INST` = `r7c15_standard`): `CLOSED_DONE` C5·C5' 성공 1.0, 18.76 s, 호출·Astra 행 필드·blob 확인(행 6), `meta.bootstrap` 10000, `meta.prereg` OK, git `9cee78b1`, `code_sha` `6c24decc1dd3a2cf`, 하드 리셋 빌드(행 99). (계획 밖 DEV 0 C5 판도 성공 14.78 s — 절차 사고.) |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 13:13–13:14 UTC): `e05 --data …/jsel_dev/P0,…/P2 --split dev --episodes 3` → `E05_DONE`, `rd --variants standard=…/jsel_dev,random=…/gen_dev/random/P0 --episodes 2` → `RD_DONE`(n 275), `calib --fit-data …/pool --fit-split pool --heldout …/jsel_dev/P1 --heldout-split dev --episodes 5` → `CALIB_DONE`, `e05 --split pool --truth outcome:plan`(행 100) → `E05_DONE`. 모두 rc 0, prereg OK. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·카나리·시드·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`j5_*`·`truth_label_trust`; 정리 뒤 흔적 없음(머리 규칙 줄). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`)
- `e05 --split cal|test|test_p5`, `calib --fit-split cal`, `calib --heldout-split test`, `rd --split test`, `closed --split test --seeds 1149`, `closed --split cal --seeds 500`, `closed --split test_p5 --seeds 1300` → "--split X refused: set HARVEST_ALLOW_SPLIT=X (main session only …)". `closed --split dev --seeds 29,30`·`--split pool --seeds 2120` → "not in split … (refused, never opened)". `--isaac-gpu 3` → "0 or 1 only"; `--conditions C9`·`--m4-lead-max nan` → "refused before any worker". `HARVEST_ALLOW_SPLIT=dev closed --split cal`, `HARVEST_ALLOW_SPLIT=test e05 --split cal` 거부. `gen gen --seeds 10007-10008`(확인 인자 없음), `determinism fresh --seed 1000`, `determinism history --seeds 3,549` 거부. **19건 모두 rc 1**, 거부된 명령의 출력 폴더 0개. (`--m4-h 2`는 가드가 아니었다 — N1.)

### 6.5 A. 테스트
- 로컬(`…\r7c15\repo` = 9cee78b archive, Git Bash, `python -m pytest -q -rs -p no:cacheprovider -o addopts="" --basetemp=…\r7c15\pt3`): EXIT 0, **987 passed · 13 skipped**(N11). (앞선 첫 두 번은 저장소 `pytest.ini`의 `-q`와 겹쳐 요약 줄이 안 나와 다시 돌림 — 내용 같음.)
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, TMPDIR·pyc·카나리·qid 등록부 = scratch, 13:11–13:12:53 UTC): **1041 passed, 4 skipped**(isaaclab·pyarrow·CUDA 없음·TODO(P3)), EXIT 0.

### 6.6 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외, §72–§80)
- §80 D1(라벨 신뢰): 코드 소비처 모두 적용(6.1). 문서 `labeler.md:40`·`pool_replay_debug.md:17`·`:139`(476 + 410 = 886 거부권 제외 권고)·논문 `6_prelim.tex:61` 맞음. §80 수치 D-2.
- §80 N1: `se2e_verdict.py` 머리 사용법 = 6인자 필수; 다른 문서의 사용 예 없음(`prereg_se2e.md:62`는 옛 경로 서술 — 13회차에 정리됨).
- §80 N3: "0편으로 rc 0" 서술 없음(정본 §79 N5·§80 N3만).
- §78 사실(고정 선행 실행으로 이력 의존 해소 안 됨): **`pool.md:32`·`:57`, `e_m4b_meas.md:19`, `D28:149`(D-1)**; `physx_hard_reset.md`·`pool_replay_debug.md`·`labeler.md`·`r2_datagen.md` 맞음; 코드 `cli_pool` prefix·warmup 설명은 절차 서술로 사실(§78 "제거 후보").
- §78 결정(`make_env(hard_reset=True)` 기본, 모든 호출자): `hard_reset=` 인자를 넘기는 호출 0.
- §77 보충 (2)·§80(S-E2E 고정 사본): `se2e_train.md:4`·`se2e_diag.md:16`·파드 해시 일치.
- 정본 범위: handoff `:3`·`:5`·`:83` = §80(맞음). 날짜 순서: 정본 §78 11:14·§79 11:50 UTC와 커밋 e8e1864·2c4a30d는 순서 맞음; §80·`r7c14_fixes.md`·handoff 머리의 "13:10 UTC"는 커밋 0790dd4(12:57:49 UTC)보다 늦다(N15).

### 6.7 F. 규칙·위생
- 저장소: 작업 트리는 읽지 않고(시작 `git status` = 시간 맥락 작업의 수정 17·미추적 5; 끝에는 다른 세션이 b283da2·0b853c2로 커밋해 깨끗함 — 범위 밖; 메타데이터 2건만 읽음) 이 보고서 한 파일만 추가. 로컬 C:: 이 검토의 산출물 없음(하네스 작업 출력 파일만). 파드: 시작 전 목록(`pod_baseline.txt`)과 대조해 내 항목만 삭제 — `tmp/r7c15`(398 MB), 내 두 Isaac 판이 만든 `tmp/{carb.nW31hS, carb.r9E3jA, tmpat6idxxg, tmpvq39w9u3}`·`cache/pyc_r6/data/harvest/tmp/{r7c15, tmpat6idxxg, tmpvq39w9u3}`·`ir/kitcache/cyclo-r7c15_standard`, LeRobot 시험이 만든 `cache/hf/datasets/parquet/default-4b720981789408e4`(+ 잠금, `dataset_info.json`에 r7c15 경로). 같은 시각대의 다른 새 항목(`tmp/se2e_t_smoke*` = 시간 맥락 작업, `tmp/hub-root.lock` = 시작 전부터 있음)과 공유 로그 `home/.nvidia-omniverse/logs/*`는 두었다. 끝에 내 프로세스 0, `/data` 밖 새 파일 0(`find / -xdev -newermt 13:00 UTC`, `/tmp` 포함).
- 규칙 쪽: 절차 사고 1건(머리 규칙 줄·N1). CLAUDE.md user-log 71 없음(N8).

## 7. 다음 순회 전에 할 일 (제안)
1. **D-1**: `pool.md:32`·`:57`에 [정정 R7 15회차 D-1, 정본 §78: 고정 선행 실행은 이력 의존을 없애지 못한다 — 다시 만든 풀에서도 886행·29편이 비트 동일이 아님(`pool_replay_debug.md`), 지금 기준은 하드 리셋] 표시; `e_m4b_meas.md:19`·`D28:149` "비트 동일"에도 같은 표시.
2. **D-2**: 정본 다음 절에 "§80 (1)의 `pool_selfcheck` '13편' → 13시드·20편" 정정 한 줄, `r7c14_fixes.md:24`에 정정 표시.
3. NOTE 처리 권함: N2(`RESUME_KEYS`에 진단 옵션), N3(뺀 수 기준 명시), N4(`se2e_train.md` 5칸), N5(사전 등록은 실행 전 커밋), N7(handoff 14회차 커밋·태그, §7 추가 등록 줄), N10(`cli_label` 쓰는 쪽 `or 0.0` → null), N15(§80·handoff 머리 시각 13:10 대 커밋 12:57:49), N9(논문 매시간 갱신 때).
