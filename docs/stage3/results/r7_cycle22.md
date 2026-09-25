# R7 객관 검증 순회 — 22회차 (cycle 22, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle21.md` §5 표·결론을 근거로 쓰지 않고 사전 등록 원문에서 대조표를 다시 만들었다. 행마다 **21회차와 다른 새 경계값으로 구성한 입력 → 실제 함수·CLI 출력** 또는 **파드 원자료 재계산**으로 확인했다). 작성 2026-09-25 16:45 UTC 무렵(로컬 시작 약 16:10 UTC, 파드 첫 명령 약 16:20 UTC, 파드 정리 끝 16:38:59 UTC). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 `3a3d76c`(`3a3d76cf3a55…`, 커밋 시각 2026-09-25 16:09:49 UTC, "se2e_train.md: diagnostics status updated" — 31c517b 다음 커밋). `git diff --stat 874cb33 3a3d76c` = 36파일: **코드** `harvest/train/se2e_data.py`(`finite_velocity` 인과 후방 차분), `tools/se2e_convert.py`(`reconvert`, `merge_reconverted`), 새 `tools/se2e/motion_confirm_verdict.py`, 시험 3개(`tests/train/test_se2e_data.py` 수정, 새 `tests/train/test_se2e_reconvert.py`·`tests/test_se2e_motion_confirm_verdict.py`); **사전 등록** 새 `docs/stage3/prereg_se2e_motion_confirm.md`; 문서 `handoff.md`·`draft-log.md`·`direction-log.md`·`user-log.md`(82 보충)·`se2e_train.md`·`se2e_diag.md`·`se2e_temporal.md`·`hypothesis_short_window_2026-09-25.md`·`r7_cycle21.md`; 논문 .tex·그림. 정본 `00-interfaces.md` 변경 없음(끝 절 §83). 검토 시작 때 작업 트리에 다른 에이전트의 미커밋 코드(`harvest/astra_motion/`, `tests/astra_motion/`, 뒤에 `docs/stage3/prereg_astra_motion.md`) — **검토 대상 아님**. `git -c core.autocrlf=false archive 3a3d76c`를 Python tarfile로 `D:\tools\scratch_qdd\r7c22\repo`에 풀었다(**506파일**). 파드 사본 = 같은 archive(`/data/harvest/tmp/r7c22/code`, 507파일 = + JSON `CODE_VERSION` `3a3d76cf…`, dirty false); 파드 산출 `meta.git.commit` = `3a3d76cf3a55…`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle7.md`–`r7_cycle21.md`, `r7c7_fixes.md`–`r7c15_fixes.md`, 정본 `00-interfaces.md` §1–§83(뒤 절 우선; [사용자] 제목 절은 그대로; 논문 .tex는 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`(§7 포함)·`prereg_se2e_temporal.md`·**`prereg_se2e_motion_confirm.md`(새)**·`M4-overlap-commit.md`.
- 분류(21회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·같은 문서의 뒤 결과와 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 기록이 없는 것. 정본이 "나중에 할 일"로 적은 것(§82 구현, §83 런타임 적용, 확인 실험 결과)은 SCOPED. 연구 문서의 제안 목록·[결정 필요]는 지금의 결정·구조를 틀리게 말하지 않는 한 NOTE. 원문이 맞고 렌더에서만 빠지는 것은 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c22`(스크립트는 모두 Write 도구로 쓰고 경로로 실행; heredoc·`cat >` 없음). **절차 사고 1건(내 쪽)**: 로컬 해시 명령 줄 앞에 실수로 `python -`(표준 입력 대기)가 붙어 들어갔다 — 아무 코드도 받지 않은 채 대기하다 시간 초과로 배경 전환되었고 곧바로 중지했다(읽거나 쓴 것 없음, 결과 영향 없음). 규칙 위반이므로 기록한다. 파드 업로드 = `tar -cf - | kubectl exec -i … tar -xf -`(파드 스크립트 CR 바이트 0 확인), 정리 = `bash -s < clean22.sh`(경로를 하나씩 적음, 열린 파일 핸들 0 확인 뒤). 로컬 pytest basetemp = `…\r7c22\pt`, C: 쓰기 없음(하네스 작업 출력 파일만). 파드 = `/data/harvest/tmp/r7c22`. GPU: Isaac = GPU 1에 **내 프로세스 하나**(`--inst-prefix r7c22`, `IR_INST` `r7c22_standard`, `IR_ROOT=cyclo`, 기본 `r6` 안 씀; 같은 시각 GPU 0·1의 R2_TRAIN Isaac 워커 — 건드리지 않음), GPU 2·3(확인 실험 학습)에는 아무것도 올리지 않음(가드 12·13은 워커 전에 거부). CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`, 한 번에 한 묶음(CPU 시험 → 가드·평가 → se2e_c1 점검 → Isaac 순차). 시드 DEV·POOL만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 요청과 **다른** 값으로만). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. `ckpt/se2e*`·`logs/se2e*`·`data/se2e*`·`r2/dev`·`code_se2e_confirm`는 **읽기만**(확인 실험 예측 파일은 열지 않았다).

## 판정: **PASS**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 0 |
| SCOPED | 20 |
| NOTE | 30 |

새 코드(속도 누수 수정·재변환·확인 판정 스크립트)와 새 사전 등록을 행동으로 확인했고 어긋남이 없다. 로컬 **1014 passed / 15 skipped**, 파드 CPU **1130 passed / 4 skipped**, LeRobot 6 passed; 가드 **24건** 모두 rc 1(21회차와 다른 값); R2 DEV `validate_episode` **36/36** + 음성 대조(한 행 자른 사본 → 오류 검출); 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 모두 완료; 새 시드 **DEV 17**에서 같은 Isaac 워커 C5 → C5' 행동 **1,426개 비트 동일**; 로컬 구성 시험 `check22.py` **51/51**, `verdict22.py` **11/11**, `prereg_hash.py --check` OK.

**속도 누수 수정(정본 §83)**: `finite_velocity`는 이제 v[k] = (x[k] − x[k−1])·hz, v[0] = 0이고 프레임 k+1 이후를 무엇으로 바꿔도 0..k 행이 비트 단위로 같다(V1–V7). 파드 `se2e_c1` 전 42,813행을 **내 코드로 원본 parquet에서 다시 계산한 후방 차분과 최대 오차 0.0**으로 같고(RB1 25,433·RB2 17,380), 옛 `se2e` 행은 같은 parquet의 중앙 차분과 정확히 같다(누수 실재·수정 확인). 새 판은 옛 판과 `proprio.qd`·`grip[1]` 말고 모든 필드가 같고(42,813/42,813), 덧붙은 움직임 출처 필드는 E-TC `se2e_t`와 같다. **등록된 `reconvert`를 파드에서 10편(RB1 5·RB2 5)에 다시 돌린 출력이 `se2e_c1`의 같은 줄과 바이트 동일**(317·116줄). 로더 분할·키 sha(`cf0f400ee688`·`f03062db4b1d`·300개 `e22f6d8ef7fc`)는 두 판 같고 등록값과 같으며, 표본 차이는 이미지 뿌리 문자열(같은 실파일 81,672/81,672)을 빼면 `proprio.qd`·`proprio.grip`뿐이다. **확인 판정 스크립트**(`fa7299062cc5e1d1` = 커밋 = 파드 사본 = 판 폴더 `CODE_HASHES`)는 합동 효과 정확히 +0.015 → 통과·53/3600 → 불합격, 전이 층 정확히 −0.01 → 통과·−25/2400 → 불합격, 하한 정확히 0 → 불합격(엄격 >), 시드 짝 평균·교환 불변, 등록 부트스트랩을 내 코드로 재구현해 구간이 같았다. 등록 15:52:12Z < 판 시작 15:53:07Z < 커밋 15:53:42Z < 첫 학습 스텝 15:54:13Z.

21회차 DOC 1(handoff 정본 범위)은 고쳐졌다: `handoff.md:3`·`:5`·`:83`이 번호 없이 "마지막 절까지"를 가리키고(`grep "§1~§8|지금 §8"` 현재 판 줄 0), `:84` 핵심 결정에 §83·se2e_c1·44c907d 토막이 있다. 21회차 NOTE N12·N13·N20·N21·N22 정정도 실제로 들어갔다. **연속 무결 1회**(DEFECT 0·DOC 0). 단, 검토 중 HEAD가 문서만 바뀐 커밋 7개(00a0aad까지, 정본 §82 보충 2 포함)로 움직였다(N29).

---

## 1. DEFECT

없음.

(검토한 후보와 판단: ① 파드 확인 실험 코드 사본(`/data/harvest/code_se2e_confirm`)의 `.py` 258개 중 240개가 CRLF — 등록 §5의 "무수정" 해시(`stageb_data.py` `a61a7cf6…`, `stageb_model.py` `255c78cf…`, `se2e_temporal.py` `9fd650fc…`)는 CRLF 파일의 해시이고 저장소 LF 블롭(`038506ad…`·`5f3eba50…`·`d5babfb8…`)과 다르다. LF로 맞추면 `harvest/`·`tools/`·`tests/`의 모든 파일이 3a3d76c와 **내용 동일**(차이는 문서·논문뿐)이고, 파이썬은 줄 끝과 무관하게 같은 코드로 읽으므로 학습 동작은 같다. 등록된 해시는 그 사본과 정확히 같다(`CODE_HASHES` 6/6). 판정 규칙·데이터·지표에 영향 없음 → **NOTE N23**(체크포인트 `prompt_config.files_sha`도 CRLF 해시라 런타임 `check_prompt`의 `files_ok`는 거짓이 됨 — 확인 판은 런타임용이 아님). ② `merge_reconverted`는 새 행의 `images`·`img_rotate_cw`를 비교하지 않고 옛 값으로 덮는다(`se2e_convert.py:241`, 구성 R4) — 등록 §1 "이미지 경로 불변"은 옛 값을 그대로 쓰므로 성립 → NOTE N25. ③ `motion_confirm_verdict.py`는 입력이 검증 전체 1,799인지 보지 않고 300 판에도 `confirmed` 값을 낸다 — 등록 §4가 판정 집합을 문장으로 정했고 `run.sh verdict`가 `verdict_full.json`·`verdict_300.json`을 나눠 쓴다 → NOTE N3.)

## 2. DOC

없음.

(검토했지만 DOC로 올리지 않은 후보: `harvest/train/se2e_temporal.py:13` docstring "(the rows' proprio.qd is a central difference that reads frame k + 1 and is not used)" — 같은 docstring `:17` "Rows: … `se2e_t/conv`"이 가리키는 E-TC 판 행에는 지금도 사실(`se2e_t`는 옛 변환에서 만듦, 파드 재계산 42,813행 중앙 차분 확인)이고, 등록 §5가 이 파일을 해시로 묶어 둠 → N22. `se2e_data.md:62`·`:96` "중앙 차분" — 이 결과 문서가 기술하는 데이터 판 `se2e`(2026-09-24)에는 사실 → N21. `se2e_temporal.md:81` "여전히 그 값이 들어간다(메인 확인 필요)" — E-TC 판 기준으로 사실, 21회차 N23 그대로 → N19. `handoff.md:88` E-Astra-motion 탐침 정의(P-pc·P-plane·P-tri·예산 ≤ 3만 원)가 커밋 트리에 없음 → N12.)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드 GPU 0·1 R2_TRAIN Isaac 워커 진행 중(읽기만); 확인 인자 없는 `gen gen --seeds 10000` rc 1(가드 18).
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8(M9 복구·T_fail 뒤 하트비트 정지, A5′ 검사·계약 편집, 확인 헤드 보정 파일 기본 미보정).
- S6. Astra 카나리 "none"(§67 보충).
- S7. S-E2E 계열 체크포인트의 런타임 형식 차이(§77 보충 (2), §80).
- S8. CONTRADICT-soft(§68 K6).
- S9. §73 D5 M4 설계 확장.
- S10. §73 N5 E1 범위.
- S11. §74 보충 E-M4-lat 비례 STALE_MAX.
- S12. §75 보충 (2) E-M4 판정 7.
- S13. §77 N8 (13): 완료 정의 밖 사전 등록 실험.
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — 3a3d76c에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. **정본 §82 구현**(K5 모드·`harvest/astra/jobs.py`·`closed --upper`·T_nov·계약 캐시·J2 경로·`astra_slot.py`·Qwen3-VL-32B, 유료 실행은 사용자 승인 뒤) — "R7 관문 뒤 착수". 지금 코드: `CADENCES` = K0–K4, "K5"·"J5"·"k2" 거부, `RuntimeConfig()` = ("K2", 5.0)(`check22` C3·C5), 파드 판 `meta.hb_mode` K2·`hb_n` 5.
- S19. **정본 §83 런타임 적용**: 새 직렬화 판본(움직임 줄 위치), 런타임 속도 구간화, 보정 파일·카나리 기준 재생성, R2 학습 항목의 같은 줄 — "R7 관문 뒤 착수". 3a3d76c: `harvest/serialize` 원문에 움직임 줄 없음(`check22` D3), 파드 결정 호출 요청 86/86 `motion:` 없음.
- S20. **§83 확인 실험 결과**(`prereg_se2e_motion_confirm.md`): 파드에서 진행 중 — (single, none) 시드 1·2 학습 끝(16:30:56Z·16:31:03Z)·예측 진행, (single, motion) 두 판은 아직 시작 전. 판정 파일(`verdict_full.json`)·결과 문서(`se2e_motion_confirm.md`)는 없음. (21회차 S20 "속도 누수 수정"은 이번 커밋으로 **해소** — 행 142–145.)

## 4. NOTE
- N1. (그대로) `stageb_train predict`·`evalck`는 체크포인트 `prompt_config`를 자기 옵션과 대조하지 않는다.
- N2. (그대로) `cli_label.replay_max`의 NaN 순서 의존. 읽는 쪽 `replay_bit_identical`은 새 경우(정수 0·0.0 → 신뢰, "0"·nan·5e-324·필드 없음·−1e-300 → 불신)도 올바름.
- N3. (확장) `temporal_verdict.py`와 새 `motion_confirm_verdict.py`의 입력 검사가 `assert`·`KeyError`이고(내 구성: 다른 키 집합 → 전이 표지에서 `KeyError`, 요약 불일치 → `AssertionError`, 잘못된 판 이름 → SystemExit — 모두 rc ≠ 0), 등록 판정 집합(검증 전체 1,799)을 스크립트가 확인하지 않는다; 300 판 출력에도 `verdict.confirmed`가 들어간다(등록 §4는 보고만). `label`·`n_val_snapshots`가 출력에 남으므로 읽을 때 구분 가능.
- N4. (그대로) Astra 시간 초과 뒤 재송신 모양 — K5 구현 때 정본에 정하기를 권함.
- N5. (그대로) `se2e_diag.md:131` 6절 제안 (a) D2′는 8절로 사실상 수행.
- N6. (그대로) `se2e_diag.md:13` "0.72는 입력 + 데이터 규모 쪽" 읽기의 "약 9k까지만" 제한.
- N7. (그대로) `astra_role_2026-09-25.md:349`·`:517` "J6 effort high는 [결정 필요]", `:11` "정본 §1–§81"은 작성 시점 표기.
- N8. (그대로) `CLAUDE.md:32`(user-log 76 비용 한도 줄) 위치가 "## 논문 초안" 절 끝.
- N9. (그대로) `steering_representation_2026-09-25.md:33`·`:81`의 §82 표시가 표 머리보다 한 칸 많은 마지막 칸이라 GFM 렌더에서 사라짐(원문에는 있음).
- N10. (그대로) `e05`는 `--out` 폴더를 거부 전에 만든다 — 가드 24(`e05 --split pool --seeds 2000`, 데이터 jsel_dev/P1 → "no episode selected" rc 1)가 빈 `g24/`를 남김.
- N11. (그대로) 카나리 `--force` 같은 날 재실행이 그날 표류 파일을 덮는다.
- N12. (부분 해소) `handoff.md:88` 대기 항목이 user-log 79–82로 갱신됐다(21회차 권고 반영). 다만 그 줄의 E-Astra-motion 탐침 정의("P-pc·P-plane·P-tri 대 보고 조종 S, RGB만, 예산 ≤ 3만 원")는 3a3d76c 트리 어디에도 없다(작업 트리의 미커밋 `harvest/astra_motion/`·`prereg_astra_motion.md`). 커밋될 때 링크를 달면 좋다.
- N13. (그대로) `draft-log.md:462` "…`results/se2e_temporal.md`, 커밋 안 함" — f4f6a49에서 커밋됨(관용 표기).
- N14. (그대로) `prereg_se2e_temporal.md` §7 등록 해시 = 파드 `code_se2e_temporal` 사본; 저장소와 다른 두 파일은 §77·§81 N2 기록.
- N15. (그대로) `e_m4b_meas.md:36`·`:51`은 사전 등록 원문 복사.
- N16. (그대로) `2026-09-25-e2e-ready.md:12`·`:26`(완료 정의 3·R5의 "Astra 하트비트")은 지금 실행 계층 서술.
- N17. (그대로) `hypothesis_short_window_2026-09-25.md:49`·`:203` Astra 자리 제안 — 정본 결정 아님.
- N18. 논문(NOTE만): cd5210f에서 §83(움직임 줄 채택·V 불채택·속도 누수·확인 실험 진행 중)이 `3_method.tex`·`5_plan.tex`·`6_prelim.tex:57`·마인드맵에 반영됨(21회차 N19 해소). `main.tex:10`·마인드맵 `4_experiments.tex:99`의 "R7 16–19회차"는 작성 시점 표기.
- N19. (그대로, 21회차 N23) `se2e_temporal.md:81` "(메인 확인 필요)"에 "→ §83" 표시 없음; 이제 "여전히 그 값이 들어간다"도 E-TC 판 한정임을 적으면 좋다("→ 수정 44c907d, se2e_c1").
- N20. (그대로) `se2e_temporal.md` §5 표의 분 단위 반올림(15:22·14:44).
- N21. `se2e_data.md:62`("`qd`[7] rad/s(10 fps 상태의 중앙 차분)")·`:96`("보간·중앙 차분") — 데이터 판 `se2e`와 그때의 코드에 대한 기록으로는 사실. 지금 `se2e_data.py`는 인과 후방 차분(§83, se2e_c1)이므로 "→ §83: 44c907d부터 후방 차분, 새 판 se2e_c1" 한 토막 권함.
- N22. `harvest/train/se2e_temporal.py:13` docstring "the rows' proprio.qd is a central difference" — `se2e_t` 행에는 사실, `se2e_c1` 행(확인 실험이 `--se2e-t-root`로 읽음)에는 아님. 확인 실험 뒤 파일을 고칠 수 있을 때 "(se2e_t; se2e_c1 rows are causal, §83)" 권함(지금 고치면 등록 사본 해시와 저장소가 한 파일 더 갈라짐 — 사본은 별개라 실험 영향은 없음).
- N23. **파드 확인 실험 사본의 CRLF**(§1 후보 ①): `code_se2e_confirm`의 `.py` 240/258개 CRLF(바뀐 3개 파일·시험 등 18개만 LF) — `core.autocrlf` 없이 만든 사본으로 보인다. 등록 §5의 "무수정" 해시 3개는 CRLF 해시(LF 블롭은 `038506ad…`·`5f3eba50…`·`d5babfb8…` = 3a3d76c), 판 `prompt_config.files_sha`도 CRLF 해시(`stagea_data.py` `5bdb4de5…` 대 LF `99b17048…`, §80이 적은 기준). LF로 맞춘 내용은 `harvest/`·`tools/`·`tests/` 전부 3a3d76c와 같다(`conf22.py`). 결과 문서에 "무수정 해시 = CRLF 사본 해시, LF 블롭 = …"를 한 줄 적고, 다음 고정 사본은 `-c core.autocrlf=false archive`로 만들기를 권함(메모리 규칙 "MANIFEST는 LF 블롭 기준"과 같은 취지).
- N24. 등록 §3 "시드 간 변동: … (none) 칸끼리·(motion) 칸끼리의 시드 간 정확도 차"는 판정 스크립트 출력에 따로 없다(`runs` 칸별 정확도로 계산 가능; `seed_spread` = e_2 − e_1만 있음). 보고 항목이라 NOTE.
- N25. `reconvert` 설계 메모: `KEEP_FROM_OLD`(`images`·`img_rotate_cw`)는 비교 없이 옛 값을 쓴다(R4); `stats.json`은 옛 파일 + `reconverted_from`(수 세기만이라 속도와 무관); `--conv`가 `--src`의 부모 폴더 아래이면(형제 폴더 포함) 거부한다 — 내 첫 재현 시도(`recon/src`·`recon/conv`)가 이 규칙으로 rc 1이었다(의도된 안전 규칙, 판 폴더 `se2e_c1`은 해당 없음). 기본값끼리(`--src` = `--conv` = `se2e/conv`)도 거부(R6).
- N26. 등록 고정 시점: 등록 문서 머리 15:52:12Z, 판 드라이버 시작 15:53:07Z(`CODE_HASHES` 시각), 커밋 44c907d 15:53:42Z, 첫 학습 스텝 15:54:13Z. 파드 사본에는 등록 문서가 없으므로(문서가 사본 뒤에 작성됨) 원문 고정의 증거는 커밋이다 — 어느 모델 출력(첫 평가)보다 앞선다. 판정 스크립트 해시는 판 폴더 `CODE_HASHES`(15:53:07Z)에 고정.
- N27. 시험 수: 로컬 **1014 passed / 15 skipped**(145.5 s; 21회차 1006 + 새 시험 8), 파드 CPU **1130 passed / 4 skipped**(139.9 s, 16:26:56Z), LeRobot 6 passed(19.2 s). 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다.
- N28. 단계 B 소형 CPU 스모크(16:29 UTC): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21회차와 같은 값 — 결정적), eval fm 2.4379에서 시작, expert p50 0.038 s·전체 p50 0.098 s(CPU, 참고).
- N29. 검토 중 HEAD가 **00a0aad**로 움직였다(a8259df "user-log 83 + §82 supplement 2", ed2c67a·c6200c4·b697a57 user-log 83, 2cdef56·ac165ab·00a0aad `specs/2026-09-26-astra-vla-coupling-design.md`) — `git diff --stat 3a3d76c 00a0aad` = `00-interfaces.md` +2, 스펙 +139, `user-log.md` +9, **코드 변경 없음**. 이 보고서는 3a3d76c만 판정한다; 다음 순회는 정본 §82 보충 2를 포함한 HEAD를 본다.
- N30. (읽기 도움, 판정 아님) 등록 확인 스크립트를 E-TC 시드 0 예측(검증 300)에 "두 시드" 모두로 넣으면 합동 +0.0244·하한 −0.0033 → c_point 참·c_lower 거짓 → "확인 안 됨"이 나온다(`etc_confirm_sanity`) — 같은 입력이 규칙상 어떻게 읽히는지 보여 줄 뿐, 확인 실험은 검증 1,799·시드 1·2로 판정한다.

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**(`check22` H1), 파드 산출 `meta.prereg.check` = "OK"(closed). 코드 줄은 3a3d76c 기준. "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c22\check22.py`(A–H·V·R, 51/51), `verdict22.py`(M1–M8, 11/11), `ctrlscan22.py`; **파드** = §6(`pod_cpu22.sh`, `pod_eval22.sh`, `data22.py`, `c1rows22.py`, `c1keys22.py`·`c1keys22b.py`, `recon22.sh`, `conf22.py`, `pod_isaac22.sh`, `closed22.py`). "시험 묶음" = 해당 구현을 부르는 저장소 시험이 로컬 1014·파드 1130 묶음에서 통과. 모든 경계값은 21회차와 다르게 새로 골랐다.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149(TEST2 1150–1299) / TEST-P5 1300–1329 / POOL 2000–2119 / R2_TRAIN 10000–59999 (E :113-120, §66) | `eval/splits.py`, `datagen/gen.py` | 로컬 A1 새 경계 22값(0·13·29/31·499·501·549/551·1000·1149/1151·1250·1300·1329/1331·1999·2000·2119/2121·10050·60000·−1) 모두 기대 분할, A2 `cal` env 없음·`test` 거부/`cal` 통과, `test`에 `cal` 거부, A3 "DEV"·"pool2"·""·"eval" 거부, A4 [0, 31]·[2119, 2121] 통째 거부·문자열 시드 수용, A6 R2 가드 11경우(0·29 무확인 허용, 31·60000·2119·549·1149 거부, 10000·59999 확인 시만), A7 10000·10040·59980 eval, 10041·59999 fit; 파드 가드 24건 rc 1(§6.4) | 일치 |
| 2 | POOL 120 × 10, 경계 30 % 과표집 (E :121, §76 D-2) | `sim/snapshot.py:29-31` | 코드 무변경, 시험 묶음 | 일치(주석 S14) |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` | 시험 묶음 | 일치 |
| 4 | 분할 = 에피소드 (E :122) | `stagea_data.split_of`, `calib.halves` | 시험 묶음; 파드 `CALIB_DONE` | 일치 |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py`, `config.py` | 시험 묶음; 파드 Isaac DEV 17 C5·C5' 성공(14.26 s, `terminations` success 1) | 일치 |
| **6** | 호출 기록: 질문별 확률·요청/응답 원문(E :125), Astra A6(E :126, §28) | `core.py` | **파드 DEV 17 C5·C5' 결정 호출 86행**: `sha256(request_blob)` = `request_sha256` 86/86, 이미지 해시가 요청 본문에 86/86, 응답 blob 해시 86/86, `probs` 질문 = `answers` 질문·합 1·[0,1] 86/86, `canary_id` 86/86, `question_id@vN` 86/86; Astra 4행: 요청 해시·머리캠 JPEG 해시·effort low·600·`output_text` 4/4 | 일치 |
| **7** | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `analysis/stats.py` | 로컬 E3 일반 경로 = 군집 합 경로(새 37군집·seed 5), **E4 군집 안 행 2배 대 5배 → 구간 동일**; 파드 closed `meta.bootstrap` n_boot 10000·seed 0·percentile | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate`, `stats.cluster_diff_ci` | 파드 C5 대 C5' 같은 워커 | 일치 |
| **9–12** | 판정 2 Holm, 판정 10, 카나리 Holm, 판정 절 해시 (E :131, :265, :139, :133) | `stats.holm`, `canary.py`, `eval/common.py` | 로컬 E5 세 가설: (0.01, 0.02, 0.04) → 모두 기각(0.01 ≤ 0.0167, 0.02 ≤ 0.025, 0.04 ≤ 0.05), (0.01, 0.03, 0.04) → 둘째 0.03 > 0.025에서 멈춤(입력 순서 무관), 단일 0.0500001 → 유지; `meta.prereg` OK | 일치 |
| **13, 85** | 카나리 기준일 = 같은 세트 × 같은 `question_id@vN` 집합의 첫날 (E :136-140, §79 D2) | `eval/canary.py` | 로컬 G1: 두 질문 맵의 첫 실행 r1, 한 질문 맵(부분 집합) = 다른 사슬 r2, 다른 세트 → None | 일치(N11) |
| 14 | 모델 식별 필드가 바뀌어도 같은 처리 (E :139) | `Calibration.load`, `latest_canary` | 시험 묶음(코드 무변경) | 일치 |
| 15–17 | E0.5 표·재시험·같은 시각 K = 3 (E :236-238) | `e05.py` | 시험 묶음; 파드 `e05 --data jsel_dev/P2 --split dev --episodes 2` → `E05_DONE` | 일치 |
| **18** | γ 2/3 (E :240, M4 :276) | `m4.share_at_least:72-77` | 로컬 B1 새 비율(2/3·4/6·67/100·66/99 참, 1/2·13/20·665/1000 거짓) | 일치 |
| 19–20 | `C_flip` 두 식, A0–A4·층 (E :242, :246) | `e05.py` | 시험 묶음 | 정본 기록(§73) / 일치 |
| **21–28** | 판정 1–10 경계 (E :256-265) | `replay.judge_e05`, `stats.at_least/below` | 로컬 E1 CMP_EPS: `at_least(0.15+0.15, 0.3)` 참, `below(0.1*3, 0.3)` 거짓, `at_least(0.05−1e-8, 0.05)` 거짓; 파드 `E05_DONE` | 일치 |
| 29, 89 | FLIP_TH 후보 α 0.01·범위 (E :253, :487; M4 :285) | `e05.py` | 시험 묶음 | 일치 |
| 30 | 같은 시각 뒤집힘 성공·섭동 따로 (E :253, §27) | `e05.py` | 시험 묶음 | 일치 |
| 31–33 | d_p95 = E0 값, 분당 400 [가정], E1 반분 | `M4Params.d_p95_init`, `calib.halves` | 시험 묶음 | 정본 기록 |
| 34–35 | ECE 15 동일 질량, 오답 < 30 판정 불가 (E :320) | `calibration.ece_mass` | 로컬 E6(210예측·15구간 → 0.340 ∈ [0, 1]) | 일치 |
| **36** | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat` | 로컬 E2 새 n(유리수 기준값과 대조): 199·α 0.01 → 198, 98 → inf, 39·α 0.05 → 38, 18 → inf, 4·α 0.2 → 4, 3 → inf | 일치 |
| 37–43 | log p 자름·질문별 온도·원 확률·판정 1·7·8·`ambiguous` ECE 제외 (E :333-346) | `calibration.py`, `core.py` | 시험 묶음; 파드 `calib --heldout jsel_dev/P2 --episodes 2` → `CALIB_DONE` | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| **45** | N_max = ⌈d̂/T_c⌉+1 (M4 :258) | `m4.CommitLedger.n_max:178-182` | 로컬 B9: d̂ 0.99 → 4(정확히 3.0 경계), 0.9901 → 5; d̂ = ⌈0.95·40⌉ = 38번째(1..40 ms → 0.038) | 일치 |
| 46–49 | γ·W·비가역 W+1·τ | `m4.py` | 시험 묶음; B8 기본값 | 일치 |
| 50 | conformal α 0.01·w 5 ((b) 경계) | 확인 헤드 보정 파일 | 기본 미보정 | SCOPED S5 |
| **51** | STALE_MAX 1.5 s (E :487) | `m4.older_than:56-58` | 로컬 B3: **200 Hz** 틱 위치 800곳 모두에서 300틱 유지·301틱 버림, B4 +8e-10 유지·+1.5e-9 버림 | 일치 |
| 52–53 | C2 = VLM Stream, C0–C6 설정 (M4 :329-345) | `conditions.py`, `m4.py` | 파드 `--conditions "C5,C7"` → "refused before any worker"(가드 15) | 일치 |
| **54** | C5 = §4.2 전체, C5' = (b) 범주 뺌(줄은 none), 판정 3 (M4 :155, :232, :340-342, :361; §77 보충 (3)) | `core.b_line`, `core._boundary` | **파드 Isaac DEV 17**: C5 `last_step` {none 1, OK 33, LAG 5, DEVIATE 4}, C5' none 43/43, 요청 본문 마지막 `last_step:` 줄 = 행 값 86/86 | 일치 |
| 55 | H 1과 3 (정본 §2, M4 :188-189) | `m4.early_ask_steps`, `M4Params.H` | 로컬 B8 기본 H 3; 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 |
| **56–58** | n_LA 2·조기 호출 당겨 씀·FLIP_TH 끔; H = 1 = 같은 스텝 앞당겨 2~3회 (§75) | `m4.py:61-69`, `core.py` | 로컬 B5 네 창을 **정확한 유리수 창과 대조**: (0.99, 0.33, 0.33, 1.98) → [4..9](양 끝 포함), (0.1, 0.5, 0.33, 0.9) → [2, 3], (0.0, 0.66, 0.33, 0.66) → [2](한 점), (1.0, 0.05, 0.33, 0.2) → [4](창 빔 → d 뒤 첫 스텝); B8 n_LA 2·FLIP_TH None | 일치 |
| 59 | 경계 직후 W 2·γ 1.0 등 | 없음 | §73 D5 | SCOPED S9 |
| **60** | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.select_rule:131-142` | 로컬 E7: 차 정확히 0.02(0.50 대 0.52) → plan, 0.52001 → time0.33, 오라클 0.8999999 → None | 일치 |
| 61–62 | 폐루프 RD 재표집 = layout 짝, 주 RD = Score (EVAL :182-184) | `closed.py`, `rd.py` | 파드 `rd --variants standard=jsel_dev,random=gen_dev/random/P0 --episodes 2` → `RD_DONE` | 일치 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | §71 보충 | SCOPED S1 |
| 64–65 | M4b 2,000회, E-M4-lat 비례 STALE_MAX | `m4b/*` / 없음 | §72 예외 / §74 보충 | 일치 / SCOPED S11 |
| **66–67** | H = 1 창·`lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 파드 `--m4-lead-max -1` 거부(가드 14); 로컬 B8 기본 1.0 | 일치 |
| 68 | E0 판정 4 | `analysis/latency.py` | 시험 묶음 | 일치 |
| 69 | E-M4 판정 7 | 없음 | §75 보충 (2) | SCOPED S12 |
| 70 | FROZEN = 송신 시각 기준 (M4 :150) | `m4.py` | §77 N3 | 정본 기록 |
| 71, 93 | 카나리 표류 → J5 끔, 재보정 뒤 재사용 (E :139, :347, §77 N6, §79 D3) | `closed.j5_after_canary`, `canary.latest_canary` | 시험 묶음(코드 무변경) | 일치(N11) |
| 72–76 | 응답 모델 필드·재시도 기록, E0.5 정답, `fine_dir`, Astra 카나리 | `models`, `common` | §77 N4·N5, §67 보충; 파드 결정 호출 `canary_id` 86/86 | 일치 / SCOPED S13·S6 |
| 77–79 | (b) 범주 줄·런타임 값·경계 틱 호출 = 방금 끝난 스텝 (M4 :232, §77, §79 N1) | `core.b_line`, `core.act` | 행 54; 시험 묶음 | 일치 |
| **80–84** | 학습 자료 값·C5' none·ser-A-min-2·옛 체크포인트 거부 (§77 (iv), §77 보충 (1)) | `serialize.with_last_step` | 로컬 D2 `LAST_STEP_VALUES` 닫힌 집합, "Lag"·"none " 거부·"CONTRADICT" 수용 | 일치 |
| 86–88 | 결정 호출 행 `probs`·blob·`last_step`, Astra 원응답, 결정 이미지는 해시만 | `core.py`, `reqhash.request_body` | 행 6 | 일치 / 정본 기록 |
| 90 | FLIP_TH = 성공 실행 flip_score의 1−α 분위, 질문별 (M4 :287, §79 D1) | `e05.flip_th_conformal` | 시험 묶음(같은 순위 규칙 = 행 36) | 일치 |
| 91–92 | 같은 시각 뒤집힘 성공·섭동, 층별 A0 대비 flip | `e05.py` | 시험 묶음 | 일치 |
| 94 | E0 판정 4 집계 (§77 N7) | `latency.step_votes`, `judgment4` | 시험 묶음 | 일치 |
| 95–97, 105, 115–117, 119 | S-E2E 설정·판정 (a)–(e)·재개·evalck·판정 스크립트 입력 검사·고정본 (`prereg_se2e.md` §3·§4, §77 보충 2, §80 N1) | `tools/se2e/se2e_verdict.py` | 코드·로그 무변경(874cb33 대비 `se2e_verdict.py` 블롭 동일); 21회차 재현(잎 125 차이 0) 유지; 시험 묶음. 한계 줄 `se2e_train.md:56`(§83) 추가 | 일치 |
| **98** | 라벨 복원 기준(비트 동일, §78 (1)) | `stagea_data.replay_bit_identical` | 로컬 D1 새 7경우 | 일치(N2) |
| **99** | 에피소드마다 PhysX 장면 재생성, 모든 호출자 기본 (§78 결정) | `sim/scene.py` | **파드 Isaac 한 워커 C5 → C5'(DEV 17, 모의 선택기)**: 행동 **1,426개 비트 동일**(첫 차이 없음, 행동 시각열 동일), 호출 43개·Astra 2개 같은 수·같은 시각, `code_sha` `a2a7c8394ad45fd6` | 일치(행렬 S16) |
| 100, 118, 132 | 라벨 신뢰 = 재생 비트 동일, 뺀 수와 질문 범위 기록 (§78 (1), §80 D1, §81 N3) | `eval/common.load_truth` | 파드 `e05 --split pool --seeds 2010,2066,2115 --truth outcome:plan` → rc 0, `E05_DONE` | 일치 |
| 101 | R2_TRAIN은 하드 리셋 빌드, 옛 녹화 처리 보류 (§78 (2)(3)) | 파드 실행(읽기만) | GPU 0·1 R2_TRAIN Isaac 워커 진행 중 | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 선택 거부, `determinism` 시드 검사가 `--out` 앞 (§79 N5, §80 N3) | `eval/common.load_episodes`, `sim/determinism.py` | 가드 21(`fresh --seed 30`)·22(`history --seeds 500`) → "only DEV 0-29 and POOL" rc 1·폴더 없음, 가드 23(`canary build-set --seeds 1200-1201`)·24(`e05 --split pool --seeds 2000`) → "no episode selected" | 일치(e05 폴더 N10) |
| 103 | Isaac 워커 `OMP_WAIT_POLICY=PASSIVE` (§79) | `closed.worker_cmd` | 내 Isaac 워커가 이 명령으로 돌아 `CLOSED_DONE`; `--isaac-gpu 3`·`2` rc 1(가드 12·13) | 일치 |
| 104 | e05 qid 등록부 기본 = `<out>` (§79) | `e05.py` | 시험 묶음 | 일치 |
| 106–114, 133–136 | S-E2E 진단 D1–D3·§7 규모 곡선 (`prereg_se2e_diag.md`) | 파드 고정 사본, `se2e_diag.md` | 코드·로그 불변; `se2e_diag.md:174` 문구만 "판정 완료 → §83"로 정정(21회차 N20) | 일치(N5·N6) |
| 121–129 | E-TC(`prereg_se2e_temporal.md` §2–§8): 옵션 끔 = 기준, V 구성, M 구간·드롭아웃, 지표·층, 채택 규칙, 판정 재현 | `se2e_temporal.py`, `temporal_verdict.py` | 코드 블롭 874cb33과 동일(`temporal_verdict.py` `992d3e20…` = 등록, `check22` H2); 로컬 F1 k 1·3·9 → 0·0·6, F2a 등록 구간 경계(하한−1e-9 still·하한 slow·상한−1e-9 slow·상한 fast), F2b 그리퍼 1.0001배 opening/closing·0.9999배 still, F3 [1, 4, 4, 0, −2] → [0, 30, 0, −40, −20], F4 30,000표본 0.3025·(스텝, 시드) 난수·전역 불변; 21회차 판정 재현(잎 223 차이 0) 유지 | 일치(N14·N19·N20) |
| 130–131 | §81 N2 재개 검사 키, §81 N10 라벨 쓰기 null | `stageb_train.py`, `cli_label.replay_max` | 파드 시험 통과 | 일치(N2) |
| **137** | Astra 호출 주기 = 하트비트(응답 + N, N = 5 s) + 단계 경계 + 사건, in-flight 1, 15 s → 재송신, gpt-6-astra·low·600 (§45) | `runtime/astra_hb.py`, `core.py` | 로컬 C1 송신 2.0 뒤 4.0 없음(진행 중), 응답 6.5 뒤 11.4999 없음·11.5 hb, C2 송신 11.5 → 26.5 유지·26.5000001 초과, C4; **파드 판 Astra: hb 5.0 → 8.0, 경계 sub 8.01 → 11.01**(종료 14.26 전 다음 hb 없음) | 일치(N4) |
| 138 | LeRobot v2.1 내보내기 = ROBOTIS 형식(§63), 30 Hz·원본 해상도·관절 행동(§66) | `datagen/lerobot_export.py` | **파드 새 2편**(dr/mug_marker ep4, standard/mug_tray ep2) `export` → 2편·556프레임, `verify` 오류 0·PSNR 최소 35.05 dB·lerobot 0.3.3 적재 556프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참; LeRobot 시험 6 passed | 일치 |
| 139 | R2 DEV 구조 검사(§66, 완료 정의 1) | `datagen/validate.py` | 파드 `/data/harvest/r2/dev/*/*/P0` 전 편 **36/36 오류 없음**(6폴더 × 6), `valid_for_training` 메타 불일치 0; **음성 대조**(standard/mug_tray ep3): 무수정 사본 오류 0, `action` 끝 **1행** 자른 사본 → "npz action: length 260 (want 261) or non-finite" | 일치 |
| **140** | 정본 §82: 강등·J1–J6·K5 모드 등은 "구현(다음)·R7 관문 뒤" | 없음(현 구현 = §45 K0–K4) | 로컬 C3·C5 | SCOPED S18 |
| **141** | 정본 §83: 움직임 줄 채택·V 불채택 = E-TC 등록 판정; 누수 수정·확인 실험·런타임 적용은 다음 일 | 누수 수정·확인 등록 = 3a3d76c(행 142–150); 런타임 없음 | `check22` D3, 파드 요청 86/86 `motion:` 없음 | 일치 / SCOPED S19·S20 |
| **142** | **속도 누수 수정: v[k] = (x[k] − x[k−1]) × 10 Hz, v[0] = 0, 프레임 k+1 불사용, = `se2e_temporal.backward_velocity` (`prereg_se2e_motion_confirm.md:10`, §83 :738)** | `harvest/train/se2e_data.py:134-140`, `:185` | 로컬 V1 61×16 무작위 보행에서 손 계산과 **비트 동일**, V2 모든 k에서 `backward_velocity`와 비트 동일, V3 k = 0·1·7·30·59 뒤 모든 프레임을 바꿔도 0..k 행 불변, V4 1프레임 → 0, 0프레임 → 빈 배열, V5 옛 중앙 차분과 내부 다름, V6 hz 사용(30 Hz = 3배), V7 `episode_rows` 보폭 5 행마다 `qd`·`grip[1]` = 자기 팔의 후방 차분·k = 0 행 0; **파드 `c1rows22`: 원본 parquet에서 내 코드로 다시 계산한 후방 차분과 42,813/42,813행 일치(최대 오차 0.0)**, k = 0 행 1,574개(718 + 856) 0, 옛 `se2e` 행 = 같은 parquet 중앙 차분 42,813/42,813(최대 오차 0.0) | 일치 |
| **143** | **재변환: `proprio.qd`·`proprio.grip[1]` 외 모든 필드가 원 행과 같지 않으면 멈춤, 라벨·행동·분할·이미지 경로 불변, `hist_fields` 추가, 현재 프레임은 링크 (`:11`)** | `tools/se2e_convert.py:241-337` | 로컬 R1 속도만 바뀐 새 행 수용·나머지 = 옛 행, **R2 13종 변경 거부**(split, committed, `action_exec` +1e-15, valid, q +1e-12, tau, grip[0] ×1.0000001, t_src, arm, 새 키, 빠진 키, `ee_delta` +1e-15, `proprio_mask`), R3 옛 행에 이미 hist 필드 → 거부·프레임 순서/수 다름 → 거부, R5 `--hist` 행 `motion_src` = 행 속도·`k_prev` = max(0, k−3), R6 `--conv` = `--src`·`--src` 아래·`--src` 부모 아래·기본값 → rc 1, 기존 출력 → "exists" rc 1·파일 불변; **파드 `recon22`: 등록된 `reconvert --hist`를 10편(RB1 0·178·358·537·717, RB2 0·214·428·642·856)에 다시 돌린 출력이 `se2e_c1` 같은 줄과 바이트 동일(317·116줄)**; `c1rows22` 새 행 − {qd, grip[1]} − hist 키 = 옛 행 42,813/42,813, 순서·split 42,813, hist 필드 = `se2e_t` 42,813; `img` → `se2e/conv/img` | 일치(N25) |
| **144** | **판본 `se2e_c1` 표: RB1 25,433행·718편 `c4169181d556`, RB2 17,380·856 `45cd14ae3179`, 구간 `e164719a92d5`(학습 37,484), 전이 `7bcfc8f609c2`(val 1,921, 65.07 %); 바뀐 행 25,278·17,197, 변화 노름 중앙값 0.053·0.048 (`:12-23`)** | 파드 `/data/harvest/data/se2e_c1`(읽기만) | `SHA256SUMS.txt` 4파일 = 표, 판 폴더 `CODE_HASHES` 같은 값; 행·편 수, 바뀐 행 수 = `c1rows22`(25,278·17,197); `check_c1.json` 중앙값 0.053·0.048, p95 0.174·0.180, 그리퍼 p95 0.149·0.138; 구간 파일 = `se2e_t` 것과 sha 같음(0.21791767…·0.60703500…·0.17551597…, n 37,484, q 1/3·2/3·0.85); 전이 표지 `flags` = E-TC와 같음(1,921개, 0.6507) | 일치 |
| **145** | **분할·키 불변: train 37,484 / val 1,799, sha `cf0f400ee688`·`f03062db4b1d`·300개 `e22f6d8ef7fc`; 결정 프롬프트 입력 불변, 바뀐 것은 고유감각 속도 (`:22`, `:24`)** | `se2e_data.load_se2e`, `stageb_train.stratified_val:250-261` | **파드 `c1keys22`(3a3d76c 로더)**: 두 판 모두 표본 39,283·train 37,484·val 1,799·`stratified_val(0)` = 1,799, sha 셋 = 등록값, 300개 RB1 150·RB2 150; **`c1keys22b`: 이미지 뿌리 문자열을 맞추면 두 판 표본의 다른 필드는 `proprio.qd`(38,988)·`proprio.grip`(19,118)뿐**, 결정 항목·맥락 문장 동일, 맥락 이미지 경로 81,672개가 같은 실파일 | 일치 |
| **146** | **설계: (single, none)·(single, motion) × 시드 1·2, 2,000스텝·묶음 8·lr 1e-4/1e-4·워밍업 3 % + 코사인·검증 300(150/0)·500마다 평가, motion 칸 `--motion-line se2e-motion@v1 --motion-bins se2e_c1/motion_bins.json`·드롭아웃 0.3, 예측 300·전체 1,799, GPU 2 = none_s1 → motion_s1, 3 = none_s2 → motion_s2 (`:26-31`)** | 파드 `logs/se2e_confirm/run.sh`, 판 로그 `config` | **`conf22`: none_s1·none_s2 `config` = 묶음 8·`max_steps` 2000·lr 1e-4·`lr_heads` 1e-4·시드 1/2·`val_per_kind` 150·`val_seed` 0·`eval_every` 500·`motion_line` none·`se2e_root` = `se2e_c1/conv`·`lr_schedule` cosine·부분집합 없음·`init_weights`/`resume` 빈 값·KI stop·IMG, n_train 37,484·n_val 1,799**; lr: 스텝 1 3.33e-6, 60 = 1e-4, 이후 코사인(한 스텝 밀린 식과 최대 차 8.1e-4 × 1e-4); `run.sh`: 예측 `--val-per-kind 150` 과 `0`(= 전체, 행 145), motion 칸 `MO` 인자 = 등록, 드롭아웃 기본 0.3(`stageb_train.py:748`); 드라이버 GPU 2·3 15:53:07Z 시작, none 두 판 rc 0(16:31:03Z·16:30:56Z) | 일치 / motion 칸·예측 전체·판정은 SCOPED S20 |
| **147** | **지표·판정: 항목 = 스냅샷 × 3질문, e_s = acc(motion, s) − acc(none, s), 합동 = ½(e_1 + e_2), 스냅샷 군집 부트스트랩(네 판 같은 추출, 10,000, 시드 0, 95 % 백분위); 확인됨 ⇔ 합동 전체 ≥ +0.015 ∧ 하한 > 0(엄격) ∧ 합동 전이 ≥ −0.01, CMP_EPS 1e-12 (`:33-42`)** | `tools/se2e/motion_confirm_verdict.py:27-28,32-67,90-93` | **로컬 `verdict22` 11/11**(스냅샷 600 = 전이 400·정상 200, 1,800항목): M1 e 18/1800·36/1800 → 합동 정확히 +0.015 → c_point 참(손실 없는 이득 → 하한 +0.0111 → 확인됨), M1c 53/3600 = 0.014722 → 거짓; M2 전이 정확히 −0.01(시드마다 −12/1200) → c_transition 참, −25/2400 → 거짓(전체 +0.076이어도 확인 안 됨); M3 네 판 같음 → 하한 정확히 0.0 → c_lower 거짓; M4 시드 효과 0.05·0.01 → 합동 0.03·변동 −0.04, 시드 이름 교환 → 합동·부트스트랩 같고 변동 부호만 바뀜; **M5 내 코드로 재구현한 등록 부트스트랩(정렬 키 순서, 같은 추출, 10,000, 시드 0) = 스크립트 구간(오차 0)**; M6 1,799·300 입력 모두 `label`·`n_val_snapshots`·`rule` 기록; M7 잘못된 판 이름·다른 키·요약 불일치 → rc ≠ 0; M8 acc = 항목 평균·NLL = 보기 재정규화 | 일치(N3·N24) |
| **148** | **판정 스크립트 해시 `fa7299062cc5e1d1`·코드 해시(`se2e_data.py` `c6adc96f…`, `se2e_convert.py` `1438b8f7…`, 무수정 `stageb_data` `a61a7cf6…`·`stageb_model` `255c78cf…`·`se2e_temporal` `9fd650fc…`) (`:42`, `:47-48`)** | 파드 `code_se2e_confirm`, 판 `CODE_HASHES.txt` | 로컬 H2: 바뀐 3파일 sha 앞 16 = 3a3d76c 블롭; `conf22`: 두 판 `CODE_HASHES` 등록값 6/6 일치, 파드 사본 바뀐 3파일 = 커밋(LF), 무수정 3파일 = CRLF 사본 해시(LF 정규화 = 3a3d76c 블롭 `038506ad…`·`5f3eba50…`·`d5babfb8…`), `harvest/`·`tools/`·`tests/` 전 파일 LF 내용 = 3a3d76c | 일치(N23) |
| **149** | **등록은 어느 판도 학습하기 전; 결과 뒤 문턱·층·검증 집합·구간값 불변 (`:1-3`, `:5-7`)** | 커밋·로그 시각 | 등록 머리 15:52:12Z < 드라이버 시작 15:53:07Z < 커밋 44c907d 15:53:42Z < 첫 학습 스텝 15:54:13Z; 3a3d76c까지 등록 문서·판정 스크립트 변경 없음(`git log` 44c907d 한 번); 판정 파일 아직 없음 | 일치(N26) |
| 150 | 하지 않는 것: `se2e`·`se2e_t` 덮어쓰기, `PROMPT_FILES`·`stageb_data`·`stageb_model`·`harvest/runtime` 수정, GPU 0·1, 유료 API, CAL/TEST (`:52-53`) | 파드 실행 | `se2e/conv`·`se2e_t/conv` 행이 `c1rows22` 비교 기준으로 온전(옛 행 = 중앙 차분 42,813), 새 판은 별도 폴더·`reconvert`가 덮어쓰기 거부; 판 GPU 2·3; `harvest/runtime`·`PROMPT_FILES` 내용 = 3a3d76c | 일치 |

### 5.1 21회차 표와의 차이
- 새 행 142–150(`prereg_se2e_motion_confirm.md`). 행 141은 속도 누수 수정이 들어가 "일치 / SCOPED S19·S20"(21회차 S20 해소, S21 → S20 확인 실험 결과 대기). 판정 변화 없음(모두 일치 또는 SCOPED). 근거 교체: 행 1(새 경계 22값·R2 11경우·새 가드 24건), 6·54·99·137(새 시드 DEV 17, 86행, 행동 1,426개), 7(2배 대 5배), 9–12(세 가설 Holm), 13(부분 집합 맵), 36·45·51·56–58·60(새 경계값·유리수 기준), 121–129(새 구간 경계 입력), 138(다른 2편), 139(1행 자른 음성 대조).

## 6. 확인한 것 (근거)

### 6.1 21회차 정정·새 코드 확인 (과제 1·2)
- `git diff 874cb33 3a3d76c -- docs/handoff.md`: `:3` 머리 = "정본 범위는 적지 않는다: … 마지막 절까지가 현재 판", `:5` = "§1부터 마지막 절까지", `:83` = "§43부터 끝까지(지금 마지막 절)", `:84` 끝에 "결정 입력에 움직임 줄 채택·2프레임 비디오 불채택(§83, E-TC 사전 등록 판정), S-E2E 고유감각 속도 누수는 인과 후방 차분으로 수정(데이터 se2e_c1, 44c907d)" — **D-1 실제 반영**. `grep "§1~§8|§1–§8|지금 §8"` → 현재 판 줄 0(`:27` §1~§23은 옛 §2.x 기록). `:88` 대기 항목 user-log 79–82 반영(N12), `:116` 21회차 줄.
- NOTE 정정: N20 `se2e_diag.md:174` "(작성 당시 진행 중 → 판정 완료 …§83)", N22 `se2e_temporal.md:82` "300 중 201개(67 %; 전체 1,921행 기준 65.1 %)", N21 `hypothesis_short_window:166`·`:255` "→ 갱신: … 판정 완료", N13 `draft-log.md:463-464`·`direction-log.md:67-68`에 20·21회차와 §83 줄 — 모두 실제 반영. N23(`se2e_temporal.md:81` "→ §83")은 그대로(N19).
- `se2e_train.md:56` §83 한계 줄(16:09 UTC, 31c517b) — 서술("중앙 차분 … action expert 고유감각 입력에 섞여", "44c907d, se2e_c1")은 행 142와 파드 재계산에 맞다; `:40` 진단 상태 갱신(3a3d76c)은 `se2e_diag.md` 결과와 같음.
- **제어 문자·줄 끝 전수**(`ctrlscan22.py`, archive 텍스트 457파일): `\r\r\n` 0, 외톨이 `\r` 0, CRLF 0, `\t`(모든 파일) **0**, 기타 C0·C1·영폭 문자 0, BOM 0, UTF-8 아님 0. 끝 줄바꿈 없음 1(`prereg.json` — 해시가 고정한 원문).

### 6.2 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외)
- 정본 범위 줄: 현재 판 줄은 handoff의 번호 없는 세 줄뿐; 번호 붙은 것은 날짜 붙은 옛 기록·수정 보고서·연구 문서 머리(`astra_role:11` §1–§81, N7).
- 속도 출처(`np.gradient|중앙 차분|후방 차분|se2e_c1`): 정본 §83 `:736`·`:738`(결정 당시 서술, 수정은 "다음 일"로 적힌 그대로 수행됨), `prereg_se2e_temporal.md:29`(E-TC 등록 원문), `prereg_se2e_motion_confirm.md:10-23`, `se2e_train.md:56`, `se2e_temporal.md:81`·`:85`(N19), `se2e_data.md:62`·`:96`(N21), 코드 `se2e_data.py:15-16`·`:135-136`(수정 반영), `se2e_temporal.py:13`(N22), 논문(`3_method.tex`, 마인드맵 — 수정·확인 진행 중으로 적음, N18). **S-E2E 새 판(se2e_c1)을 중앙 차분이라고 적은 줄 0, 옛 판(se2e)을 인과적이라고 적은 줄 0.**
- E-TC·움직임 줄·video2: "V 채택" 또는 "M 불채택"을 말하는 줄 0. user-log 79–82 대 문서: 정본 결정 없음(브레인스토밍) — handoff 대기 항목에 반영.
- §72–§82 사실: 874cb33 이후 바뀐 문서는 위 목록뿐이고 하트비트·라벨 신뢰·재개 키·하드 리셋 어휘의 새 줄은 논문 갱신(N18)·`r7_cycle21.md` 인용뿐 — 어긋나는 현재 서술 0.

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st` + 코드 사본으로 R2 DEV 전 편 `validate_episode` **36/36** + 음성 대조 검출; LeRobot 시험 6 passed; 새 2편 내보내기·검증·lerobot 적재(행 138). S-E2E 새 판 `se2e_c1` 전 행 검증(행 142–145). |
| 2 모델 | 충족(CPU) | GPU 학습 없음 → CUDA 시험·GPU 재적재 건너뜀. 파드 CPU 스모크(N28), CPU 묶음의 `test_stageb_torch.py`·`test_r7c15_resume_keys.py`·`test_se2e_temporal_qwen.py`·새 `test_se2e_reconvert.py`·`test_se2e_motion_confirm_verdict.py` 통과. |
| 3 폐루프 | 충족 | Isaac 한 워커(`closed --model mock --split dev --seeds 17 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c22`, 16:33:43–16:38:07 UTC, `IR_INST` `r7c22_standard`): `CLOSED_DONE` C5·C5' 성공 1.0, 14.26 s, 호출 43·오류 0, 확정 비율 0.9045, 결정 3.018/s, 행 필드·blob(행 6), `meta.bootstrap` 10000, `prereg` OK, git `3a3d76cf`, `code_sha` `a2a7c8394ad45fd6`, 하드 리셋 빌드 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 16:27:36–16:28:13 UTC): `e05`(P2) → `E05_DONE`, `rd` → `RD_DONE`, `calib`(P2) → `CALIB_DONE`, `e05 --split pool --truth outcome:plan` → `E05_DONE`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.6). 새 데이터 판은 새 폴더·SHA256SUMS·덮어쓰기 거부(행 143·144). CRLF 사본 해시는 N23. |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`, 16:27:29–16:27:36 UTC, 21회차와 다른 값)
- 1 `e05 --data P0 --split test_p5`, 2 `e05 --data P1 --split cal --seeds 500`, 3 `calib --fit-split test`, 4 `calib --heldout-split cal`, 5 `rd --split test`, 6–8 `closed --split test --seeds 1149`·`cal 500`·`test_p5 1300` → "refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 0,31`, 10 `pool --seeds 2120`, 11 `dev --seeds 1300` → "not in split … never opened"; 12–13 `--isaac-gpu 3`·`2` → "GPU 2 never renders"; 14 `--m4-lead-max -1`, 15 `--conditions "C5,C7"` → "refused before any worker"; 16 `HARVEST_ALLOW_SPLIT=test` + `closed --split cal --seeds 500`, 17 `=cal` + `e05 --split test_p5` → 거부; 18 `gen --seeds 10000`(확인 없음), 19 `--seeds 60000 --confirm-train`, 20 `--seeds 1000 --confirm-train` → 거부; 21 `determinism fresh --seed 30`, 22 `history --seeds 500` → "only DEV 0-29 and POOL"; 23 `canary build-set --seeds 1200-1201` → "no episode selected"; 24 `e05 --split pool --seeds 2000`(P1) → "no episode selected". **24건 모두 rc 1**; 출력 폴더는 24번(e05)의 빈 폴더 하나(N10), 나머지 0.

### 6.5 A. 테스트
- 로컬(`…\r7c22\repo` = 3a3d76c archive, `python -m pytest -rs -o addopts="-p no:cacheprovider -q" --basetemp=D:/tools/scratch_qdd/r7c22/pt`): EXIT 0, **1014 passed · 15 skipped**.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, TMPDIR·pyc·카나리·qid 등록부 = scratch): **1130 passed, 4 skipped**, EXIT 0(16:26:56Z).
- 파드 LeRobot(`venv_e3st` + `r2/pylib_lerobot`·`pylib_pytest`): **6 passed**.

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가. 검토 시작 때 HEAD = 3a3d76c(작업 트리에 다른 에이전트의 미커밋 코드); 끝날 때 HEAD = 00a0aad(N29)와 미커밋 `prereg_astra_motion.md` 등 — 내가 만든 것 아님, 건드리지 않음. 로컬 C:에 이 검토의 산출물 없음(하네스 작업 출력 파일만). 로컬 `reconvert` 거부 시험의 기본값 경로(`D:\data\harvest\…`)는 거부가 폴더 생성보다 앞서 만들어지지 않았다(확인).
- 파드 정리(`clean22.sh`, 경로를 하나씩 적은 스크립트, 열린 핸들 0 확인 뒤, 16:38:59 UTC): `tmp/r7c22`(재현 폴더·가드·평가 산출 포함), 내 Isaac 판이 만든 `tmp/carb.v1HYHw`(16:33:44Z)·`tmp/tmptx2srnn1`(16:34:02Z)·`cache/pyc_r6/data/harvest/tmp/tmptx2srnn1`·`cache/pyc_r6/data/harvest/tmp/r7c22`, `ir/kitcache/cyclo-r7c22_standard`(208 MB). 판별: Isaac 앞뒤 목록 차이, 생성 시각이 내 Isaac 창 안. 끝에 `tmp`·`kitcache`의 r7c22 항목 0, 내 프로세스 0. 확인 실험 폴더(`ckpt/se2e_confirm`, `logs/se2e_confirm`, `data/se2e_c1`, `code_se2e_confirm`)는 읽기만 했다.
- 로컬 임시(`D:\tools\scratch_qdd\r7c22`: `src.tar`, `repo/`, `pt/`, `tmp/`, `tv/`, `pod/`, `podout/`, 스크립트)는 다음 순회 대조용으로 남김(C: 아님).
- 절차 사고(내 쪽, 결과 영향 없음): (1) 위 머리의 `python -` 1건. (2) 첫 `recon22.sh`는 재현 폴더를 `recon/src`·`recon/conv`로 두어 `reconvert`의 "부모 폴더 아래 거부" 규칙에 걸려 rc 1(행동 확인이 된 셈, N25) — `recon/a/src`·`recon/b/conv`로 바꿔 다시 돌려 위 바이트 동일 결과를 얻었다. (3) 첫 `conf22.py`는 파드 사본에 없는 등록 문서를 열다 멈춤 — 없는 파일은 건너뛰게 고쳐 다시 돌렸다. (4) 첫 `c1keys22.py`는 이미지 뿌리 문자열 차이까지 세어 `context`·`items`가 모두 다르게 나옴 — 뿌리를 맞춘 `c1keys22b.py`로 행 145 결과.

## 7. 다음 순회 전에 할 일 (제안)
1. (선택, NOTE) N23 확인 실험 결과 문서에 "무수정 해시 = CRLF 사본 해시(LF 블롭 …)" 한 줄, 다음 고정 사본은 `-c core.autocrlf=false archive`. N19·N21·N22 "→ §83, se2e_c1" 표시(`se2e_temporal.py`는 확인 실험 뒤). N12 E-Astra-motion 정의 문서가 커밋되면 handoff 링크. N3·N24 판정 스크립트 출력은 결과 문서에서 1,799 판만 판정으로 인용.
2. 23회차 대상은 00a0aad 이후 HEAD(정본 §82 보충 2·Astra-VLA 결합 스펙, 문서만) — 연속 무결 1에서. 확인할 것: §82 보충 2가 §82·§83과 어긋나는 현재 서술을 만들지 않는지, 스펙이 정본 결정인지 제안인지의 표시, 확인 실험이 끝났다면 판정 파일이 등록 규칙·스크립트 해시대로 나왔는지(검증 1,799, 네 판 같은 키).
