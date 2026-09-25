# R7 객관 검증 순회 — 21회차 (cycle 21, 연속 무결 카운트 1에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle20.md` §5 표·결론을 근거로 쓰지 않고 사전 등록 원문에서 대조표를 다시 만들었다. 행마다 **20회차와 다른 새 경계값으로 구성한 입력 → 실제 함수·CLI 출력** 또는 **파드 원자료 재계산**으로 확인했다). 작성 2026-09-25 16:10 UTC 무렵(로컬 시작 약 15:49 UTC, 파드 첫 명령 15:50:41 UTC, 파드 정리 끝 16:03:47 UTC). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 `874cb33`(`874cb3381b5c…`, 커밋 시각 2026-09-25 15:49:01 UTC). `git diff --stat 7e0aeba 874cb33 -- harvest tests tools` = **비어 있음**(직접 확인); 바뀐 파일 6개 = `00-interfaces.md`(§83 +7줄), `draft-log.md`, `handoff.md`, `user-log.md`(79–82), 새 `results/se2e_temporal.md`·`r7_cycle20.md`. 사전 등록 파일(`E-first`·`EVAL`·`M4`·`prereg*.md`·`prereg.json`) 변경 없음. 검토 시작 때 작업 트리에 다른 에이전트의 미커밋 코드(`harvest/astra_motion/`, `tools/se2e_convert.py`, `harvest/train/se2e_data.py`, 시험) — **검토 대상 아님**. `git -c core.autocrlf=false archive 874cb33`를 Python tarfile로 `D:\tools\scratch_qdd\r7c21\repo`에 풀었다(**501파일** = 20회차 499 + `se2e_temporal.md`·`r7_cycle20.md`). 파드 사본 = 같은 archive(`/data/harvest/tmp/r7c21/code`, 502파일 = + JSON `CODE_VERSION` `874cb338…`, dirty false); 파드 산출 `meta.git.commit` = `874cb3381b5c…`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle7.md`–`r7_cycle20.md`, `r7c7_fixes.md`–`r7c15_fixes.md`, 정본 `00-interfaces.md` §1–§83(뒤 절 우선; [사용자] 제목 절은 그대로; 논문 .tex는 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`(§7 포함)·`prereg_se2e_temporal.md`·`M4-overlap-commit.md`.
- 분류(20회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·같은 문서의 뒤 결과와 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 기록이 없는 것. 정본이 "나중에 할 일"로 적은 것(§82·§83 구현, 속도 누수 수정)은 SCOPED. 연구 문서의 제안 목록·[결정 필요]는 지금의 결정·구조를 틀리게 말하지 않는 한 NOTE. 원문이 맞고 렌더에서만 빠지는 것은 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c21`(스크립트는 모두 Write 도구로 쓰고 경로로 실행; 로컬·파드 어디서도 heredoc·`cat >`·`python -` 없음). 파드 업로드 = `kubectl exec … mkdir -p` 뒤 `tar -cf - | kubectl exec -i … tar -xf -`(파드 스크립트 CR 바이트 0 확인), 정리 = `bash -s < clean21.sh`. 로컬 pytest basetemp·TMP = `…\r7c21\pt`·`…\r7c21\tmp`, C: 쓰기 없음(하네스 작업 출력 파일만). 파드 = `/data/harvest/tmp/r7c21`. GPU: Isaac = GPU 1에 **내 프로세스 하나**(`--inst-prefix r7c21`, `IR_INST` `r7c21_standard`, `IR_ROOT=cyclo`, 기본 `r6` 안 씀; 같은 시각 GPU 0·1에 R2_TRAIN Isaac 워커들 — 건드리지 않음), GPU 2·3에는 아무것도 올리지 않음(가드 12·13은 워커 전에 거부), GPU 학습 없음. CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`, 한 번에 한 묶음(CPU 시험 → 가드·평가 → Isaac 순차; 판독 스크립트만 Isaac 중에 짧게). 시드 DEV·POOL만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 요청과 **다른** 값으로만). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. `ckpt/se2e*`·`logs/se2e*`·`data/se2e*`·`r2/dev`·`code_se2e_temporal`는 **읽기만**.

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 1 |
| SCOPED | 21 |
| NOTE | 27 |

코드·시험·사전 등록은 7e0aeba(=f91ad52)와 바이트가 같고 모든 행동 확인이 통과했다: 로컬 **1006 passed / 15 skipped**, 파드 CPU **1122 passed / 4 skipped**, LeRobot 6 passed; 가드 **24건** 모두 rc 1(20회차와 다른 값); R2 DEV `validate_episode` **36/36** + 음성 대조(자른 사본 → 오류 검출); 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 모두 완료; 새 시드 **DEV 26**에서 같은 Isaac 워커 C5 → C5' 행동 **1,877개 비트 동일**; 로컬 구성 시험 `check21.py` **42/42**, `verdict21.py` 8/8, `prereg_hash.py --check` OK. **E-TC 판정은 파드 원자료에서 재현됐다**: 등록 판정 스크립트(`992d3e20198ca317`, 저장소 = 파드 고정 사본 = 등록 해시)를 예측 4개·전이 표지·지연 파일에 다시 돌린 결과가 기록 `verdict.json`과 잎 **223/223 차이 0**, 내 독립 재계산(스크립트를 쓰지 않은 코드)도 M 채택·V 불채택으로 같고, 정본 §83의 수치(+0.025 [+0.003, +0.047], 전이 +0.027, p95 −3.8 %, V +0.013·+20.4 %)가 모두 맞다. 20회차 NOTE 정정(N12 문구, N14 탭, N15 끝 줄바꿈·빈 줄)은 실제로 들어갔다(탭 0, `\r\r\n`·외톨이 CR·기타 제어 문자 0).

**그러나 DOC 1건**: `handoff.md`가 정본 범위를 여전히 "§1~§82"로 적는다(`:3`·`:5`·`:83`) — 874cb33의 정본은 §83까지이고, 같은 문서 `:115`(이 커밋에서 더한 줄)는 "정본 §83만 추가된 HEAD"라고 적는다. 18회차 D-2·19회차 D-1과 같은 종류(인계 문서의 현재 판본 줄이 새 정본 절을 반영하지 않음)라 같은 분류를 적용했다. 코드 영향은 없고 고치기는 세 줄(+ 핵심 결정 줄 §83 한 토막)이다. **연속 무결 0회로 돌아감.** 또한 검토 중 HEAD가 44c907d로 움직였고 그 커밋은 코드(`se2e_data.py` 속도 누수 수정 등)를 바꾸므로, 다음 순회는 어차피 코드가 바뀐 HEAD에서 0부터 센다(N27).

---

## 1. DEFECT

없음.

(검토한 후보와 판단: ① S-E2E 변환 행 `proprio.qd`·그리퍼 속도 = 중앙 차분 — 874cb33 `harvest/train/se2e_data.py:133-137` `finite_velocity` = `np.gradient(x, axis=0) * hz`(직접 확인), 이 값이 `:182`·`:193-194`로 `proprio.qd`·`grip[1]`에 들어간다. 정본 §83 "발견된 누수 … 변환기를 인과 후방 차분으로 고치고(새 데이터 판본)"가 다음 일로 적었으므로 **SCOPED S20**. 런타임 쪽은 이미 인과적이다(`runtime/fused_model.proprio23:43-49` = (jp − jp_prev)/dt), R2 시뮬 데이터는 측정 `joint_vel`(`datagen/gen.py:164`)이라 누수 없음. ② §83 채택된 움직임 줄이 런타임 직렬화에 없음 — `check21` D3(직렬화 원문에 `motion` 없음), 파드 판 결정 호출 요청 본문 56/56에 `motion:` 줄 없음 — 정본 §83 "런타임 적용(다음 작업) … R7 관문 뒤 착수" → **SCOPED S19**. ③ 런타임 기본 호출 주기 K2·N 5 s(§82 미구현) → SCOPED S18(20회차와 같음).)

## 2. DOC

- **D-1. `docs/handoff.md:3`·`:5`·`:83`의 정본 범위가 §82에 머묾(§83 미반영)**: `:5` "현재 판본: 정본 `00-interfaces.md` **§1~§82**(뒤 절이 앞 절을 덮는다)", `:83` "`00-interfaces.md` §43부터 끝까지(지금 §82)", `:3` "마지막 갱신: 2026-09-25 15:27 UTC (… 정본 §1~§82 …)". 874cb33의 정본 끝 절은 **§83**(`00-interfaces.md:734-739`, f00cb59 15:40 UTC, [사용자 결정] 움직임 줄 채택 + S-E2E 속도 누수 + 런타임 후속)이고, 같은 파일 `:115`(874cb33에서 추가)는 "21회차는 … 정본 §83만 추가된 HEAD에서"라고 적는다 — 한 문서 안에서 현재 판본이 둘로 갈린다. 정정 표시 없음. 인계 문서를 따라 읽는 에이전트는 §83(결정 입력 변경·데이터 누수)을 놓친다. `:84` 핵심 결정 줄에도 §83 토막이 없다. 머리 줄 `:3`의 "마지막 갱신 15:27 UTC"도 874cb33(15:49 UTC)에서 이 파일을 고친 뒤 그대로다. → 권고: `:3`·`:5`·`:83`을 §83으로, `:84`에 "[→ 정본 §83(user-log 80): 결정 입력에 움직임 줄 채택, V 불채택, S-E2E `proprio.qd` 중앙 차분 누수 → 변환기 수정·런타임 적용은 R7 관문 뒤]" 한 토막, `:3` 갱신 시각. 고친 뒤 `grep -n "§1~§8\|지금 §8" docs/handoff.md`로 세 줄이 모두 바뀌었는지 확인(19회차 교훈).

(검토했지만 DOC로 올리지 않은 후보: `se2e_diag.md:174` "E-TC(메인 세션 진행 중)"(N20 — 다른 실험 상태에 대한 작성 시점 괄호), `se2e_temporal.md:82` "65 %(201/300 스냅샷)"(N22 — 두 분모를 붙여 쓴 것, 각 수치는 맞음), `hypothesis_short_window:166`·`:255` "판정 전"(N21 — 연구 문서, 시각 표기), `se2e_train.md`에 §83 누수 한계 줄 없음(S20의 일부 — §83이 "적는다"로 적은 후속 일).)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드 GPU 0·1 R2_TRAIN Isaac 워커 진행 중(읽기만); 확인 인자 없는 `gen gen --seeds 59999` rc 1(가드 18).
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
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — 874cb33에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. **정본 §82 구현**(K5 모드·`harvest/astra/jobs.py`·`closed --upper`·T_nov·계약 캐시·J2 경로·`astra_slot.py`·Qwen3-VL-32B, 유료 실행은 사용자 승인 뒤) — "R7 관문 뒤 착수". 지금 코드: `CADENCES` = K0–K4, "K5"·"J1"·"K2 " 거부, `RuntimeConfig()` = ("K2", 5.0)(`check21` C3·C5), 파드 판 `meta.hb_mode` K2·`hb_n` 5.
- S19. **정본 §83 런타임 적용**: 새 직렬화 판본(움직임 줄 위치), 런타임 속도 구간화(같은 경계·인과 차분), 보정 파일·카나리 기준 재생성, R2 학습 항목의 같은 줄 — "R7 관문 뒤 착수". 874cb33: `harvest/serialize` 원문에 움직임 줄 없음(`check21` D3), 파드 결정 호출 요청 56/56 `motion:` 없음.
- S20. **정본 §83 속도 누수 수정**: 변환기 인과 후방 차분·새 데이터 판본·이후 S-E2E 학습은 고친 판, "이 한계를 결과 문서에 적는다" — 874cb33 `se2e_data.py:137` = `np.gradient`(중앙), `se2e_train.md`에 한계 줄 없음(grep `qd|속도|누수` 0건; `se2e_data.md:62`는 "중앙 차분"을 사실대로 적음). 검토 중 44c907d가 수정 커밋으로 들어옴(다음 순회 대상).
- S21. **정본 §83 확인 실험(권고)**: 속도 누수를 고친 데이터로 두 번째 시드 또는 검증 1,799 전체, 새 사전 등록 — 검토 중 44c907d에 사전 등록(15:52Z)으로 들어옴(다음 순회 대상).

## 4. NOTE
- N1. (그대로) `stageb_train predict`·`evalck`는 체크포인트 `prompt_config`를 자기 옵션과 대조하지 않는다. E-TC 결과 문서 §5 표가 칸별 `prompt_config` sha를 적었고 파드 체크포인트와 4/4 같음(`dce3869037c1`·`687f31904d2a`·`a42824df52e6`·`277134b6b39b`).
- N2. (그대로) `cli_label.replay_max`의 NaN 순서 의존. 읽는 쪽 `replay_bit_identical`은 새 경우(−0.0·np 0.0 → 신뢰, True·None·inf·1e-320·[0] → 불신)도 올바름.
- N3. (그대로) `temporal_verdict.py` 입력 검사가 `assert`이고 등록 검증 집합(300·900항목)을 보지 않는다(내 구성 입력 300키 = 전이 250·정상 50으로 돌아감). 실제 판은 300스냅샷·900항목·네 칸 같은 키(파드 `etc21`).
- N4. (그대로) Astra 시간 초과 뒤 재송신 모양 — K5 구현 때 정본에 정하기를 권함.
- N5. (그대로) `se2e_diag.md:131` 6절 제안 (a) D2′는 8절로 사실상 수행.
- N6. (그대로) `se2e_diag.md:13` "0.72는 입력 + 데이터 규모 쪽" 읽기의 "약 9k까지만" 제한.
- N7. (그대로) `astra_role_2026-09-25.md:349`·`:517` "J6 effort high는 [결정 필요]", `:11` "정본 §1–§81"은 작성 시점 표기.
- N8. (그대로) `CLAUDE.md:32`(user-log 76 비용 한도 줄) 위치가 "## 논문 초안" 절 끝.
- N9. (그대로) `steering_representation_2026-09-25.md:33`·`:81`의 §82 표시가 표 머리보다 한 칸 많은 마지막 칸이라 GFM 렌더에서 사라짐(원문에는 있음, `:168` 문단 표시는 남음).
- N10. (그대로) `e05`는 `--out` 폴더를 거부 전에 만든다 — 가드 24(`e05 --split dev --seeds 30` → "no episode selected" rc 1)가 빈 `g24/`를 남김.
- N11. (그대로) 카나리 `--force` 같은 날 재실행이 그날 표류 파일을 덮는다.
- N12. (부분 해소) `handoff.md:88` 사용자 대기 (2)의 "E-Astra-motion 탐침" — 이제 user-log 79(`user-log.md:333`)에 뜻("3D 경로 그리기 대 보고 조종하기", "해보자")이 있으나 정의 문서는 874cb33 트리에 없음(작업 트리의 미커밋 `harvest/astra_motion/`). 대기 항목 (2)·(3)은 user-log 79–82(탐침 진행 지시, "VLA를 순간 엔드포인트 보정기로")를 반영하지 않았다 — D-1 고칠 때 함께 갱신 권함.
- N13. `draft-log.md`·`stage3/direction-log.md`에 **20회차 줄과 §83 채택 줄이 없다**(handoff `:115`에는 20회차 줄 있음; draft-log 마지막 = `:462` E-TC 결과 15:40 UTC, direction-log 마지막 = `:66` 19회차). 기록 누락이라 NOTE.
- N14. `draft-log.md:462` "…`results/se2e_temporal.md`, 커밋 안 함" — 결과 문서는 같은 줄과 함께 f4f6a49에서 커밋됐다. `:454`·`:456`과 같은 관용("작업 에이전트는 커밋하지 않음, 메인이 커밋")이라 NOTE.
- N15. (그대로, 16·19·20회차와 같은 판단) `prereg_se2e_temporal.md` §7 등록 해시 = 파드 고정 사본·세 칸 `CODE_HASHES.txt` **12/12 같음**(`stageb_train` `a79ed547…`, `stageb_data` `be1e6214…` 포함); 저장소 874cb33은 이 둘만 다름(`1f56bb6d…`·`038506ad…`, §77·§81 N2 기록). 나머지 8개 파일 해시는 저장소 = 등록(`check21` 해시 줄).
- N16. (그대로) `e_m4b_meas.md:36`·`:51`은 사전 등록 원문 복사 — 표시 불필요.
- N17. (그대로) `2026-09-25-e2e-ready.md:12`·`:26`(완료 정의 3·R5의 "Astra 하트비트")은 지금 실행 계층 서술; `D25-planner-cadence.md:142`는 날짜 붙은 분석.
- N18. (그대로) `hypothesis_short_window_2026-09-25.md:49`·`:203` Astra 자리 제안 — 정본 결정 아님.
- N19. 논문(NOTE만): `paper/sec/3_method.tex:26` "시간 맥락: 과거 프레임 (계획, 검증 중)", `5_plan.tex:159`·`:181`·`:185` E-TC "계획"·`\todoexp` — §83(V 불채택, M 채택)이 아직 반영 안 됨; 18–20회차 N19(Astra 하트비트를 방법 수단으로 적음)도 그대로. (검토 끝 시점 작업 트리에서 논문이 수정 중 — 대상 밖.)
- N20. `se2e_diag.md:174` "E-TC(메인 세션 진행 중)가 그 가설을 직접 잰다" — 874cb33에서는 판정이 났다(`se2e_temporal.md`, §83). 8.4 "읽기(판정 밖)" 절의 다른 실험 상태 괄호(14:05 UTC 무렵 작성)이고 결정·구조를 말하지 않아 NOTE — "→ 판정 §83, `se2e_temporal.md`" 한 토막 권함. (17회차 D-1은 같은 문서 안의 요약-본문 불일치였고, 이 건은 다른 문서의 뒤 결과라 구분했다.)
- N21. `hypothesis_short_window_2026-09-25.md:166`(E-TC 중간값 "15:06 UTC 읽음, **판정 전**")·`:255`("판정이 나오면 6절을 갱신해야 한다") — 판정 뒤 갱신 안 됨. 연구 문서·시각 표기가 붙어 NOTE. 중간값 숫자는 최종과 같은 칸 값이다(단순 효과 표).
- N22. `se2e_temporal.md:82` "전이 층이 검증의 65 %(201/300 스냅샷)로 크다" — 201/300 = **67 %**. 65.1 %는 검증 전체 1,921행의 비율(`transition_val.json` meta 0.6507, 사전 등록 §4). 두 수치 모두 맞지만 붙여 써서 한 수치처럼 읽힌다 → "검증 행 1,921개의 65 %(평가 300개 중 201 = 67 %)" 권함.
- N23. `se2e_temporal.md:81` "(메인 확인 필요)" — 정본 §83 "발견된 누수"가 답했다. 결과 문서에 "→ §83" 표시가 있으면 좋음.
- N24. `se2e_temporal.md` §5 표 `single + motion` 끝 "15:22"는 학습 마지막 평가 15:21:38Z(+ 저장), `video2 + none` "14:44"는 마지막 평가 14:43:37Z — 분 단위 반올림 차이.
- N25. 시험 수: 로컬 **1006 passed / 15 skipped**(149.7 s; torch 없음 10·inspect_robots 2·pyarrow 1·isaaclab 1·TODO(P3) 1), 파드 CPU **1122 passed / 4 skipped**(114.5 s, 15:55:08Z), LeRobot 6 passed(18.3 s). 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다.
- N26. 단계 B 소형 CPU 스모크(15:57 UTC): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(20회차와 같은 값 — 결정적), eval fm 2.4379에서 시작, 지연 expert p50 0.042 s·전체 p50 0.103 s(CPU, 참고).
- N27. 검토 중 HEAD가 **44c907d**로 움직였다(4f7243c user-log 82 보충, 44c907d "S-E2E proprio velocity leak fixed … + motion-line confirmation pre-registration") — **코드 변경**이 들어갔으므로 다음 순회(22회차)는 그 HEAD에서 연속 무결 0부터 센다. 이 보고서는 874cb33만 판정한다.

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**(`check21` H1), 파드 산출 `meta.prereg.check` = "OK"(closed). 사전 등록·코드는 `f91ad52..874cb33`에서 바뀌지 않았다. 코드 줄은 874cb33 기준(7e0aeba와 바이트 동일). "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c21\check21.py`(A–H, 42/42), `verdict21.py`(8/8), `ctrlscan21.py`; **파드** = §6(`pod_cpu21.sh`, `pod_eval21.sh`, `pod_fix21.sh`, `data21.py`·`data21b.py`, `etc21.py`·`etc21b.py`, `se2ev21.py`, `pod_isaac21.sh`, `closed21.py`). "시험 묶음" = 해당 구현을 부르는 저장소 시험이 로컬 1006·파드 1122 묶음에서 통과. 모든 경계값은 20회차와 다르게 새로 골랐다.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149(TEST2 연장 시 1150–1299) / TEST-P5 1300–1329 / POOL 2000–2119 / R2_TRAIN 10000–59999 (E :113-120, §66) | `eval/splits.py:13-43`, `datagen/gen.py:43-57` | 로컬 A1 새 경계 23값(1·14·28/30·498·500·525·548/550·1001·1148/1150·1200·1299·1301·1328/1330·2001·2118/2120·10000·59999·−5) 모두 기대 분할, A2 `test_p5` env 없음·다른 값 거부/같은 값 통과, A3 `train`·`Test`·"cal "·`p5` 거부, A4 [1, 30]·[500, 499] 통째 거부·문자열 시드 수용, A5 `test_p5` env로 1301·1328 통과·1149 거부, A6 R2 가드 11경우(1·28 무확인 허용, 30·60001·2000·500·1000 거부, 10001·45000 확인 시만, 59998·9999 무확인 거부), A7 10000·10020·59960 eval, 10019·59961 fit; 파드 가드 24건 rc 1(§6.4) | 일치 |
| 2 | POOL 120 × 10, 경계 30 % 과표집 (E :121, §76 D-2) | `sim/snapshot.py:29-31` | 코드 무변경(블롭 동일), 시험 묶음 | 일치(주석 S14) |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` | 시험 묶음 | 일치 |
| 4 | 분할 = 에피소드 (E :122) | `stagea_data.split_of`, `calib.halves` | 시험 묶음; 파드 `CALIB_DONE` | 일치 |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py:24-37`, `config.py:12-13` | 시험 묶음; 파드 Isaac DEV 26 C5·C5' 성공(18.77 s, `terminations` success 1) | 일치 |
| **6** | 호출 기록: 질문별 확률·요청/응답 원문(E :125), Astra A6(E :126, §28) | `core.py:279-322,395-426` | **파드 DEV 26 C5·C5' 결정 호출 112행**: `sha256(request_blob)` = `request_sha256` 112/112, 이미지 해시가 요청 본문에 112/112, 응답 blob 해시 112/112, `probs` 질문 = `answers` 질문·합 1·[0,1] 112/112, `canary_id` 112/112, `question_id@vN` 112/112; Astra 4행: 요청 해시·머리캠 JPEG 해시·effort low·600·`output_text` 4/4 | 일치 |
| **7** | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `analysis/stats.py:4,31-54` | 로컬 E3 일반 경로 = 군집 합 경로(새 41군집·seed 7), **E4 군집 안 행 3배 대 4배 → 구간 동일**; 파드 closed `meta.bootstrap` n_boot 10000·seed 0·percentile·단위 기록 | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate`, `stats.cluster_diff_ci` | 파드 C5 대 C5' 같은 워커(행 99) | 일치 |
| **9–12** | 판정 2 Holm, 판정 10, 카나리 Holm, 판정 절 해시 (E :131, :265, :139, :133) | `stats.holm:75-84`, `canary.py`, `eval/common.py` | 로컬 E5: (0.024, 0.026) → 둘 다 기각(0.024 ≤ 0.05/2, 0.026 ≤ 0.05), (0.026, 0.03) → 첫 단계 0.026 > 0.025에서 멈춤·둘 다 유지(입력 순서 무관), 단일 0.05 → 기각(≤); `meta.prereg` OK | 일치 |
| **13, 85** | 카나리 기준일 = 같은 세트 × 같은 `question_id@vN` 집합의 첫날 (E :136-140, §79 D2) | `eval/canary.py:168-190` | 로컬 G1: 같은 질문 판본 올림(`z@v3` → `z@v4`) = 다른 사슬(r1), 같은 맵의 첫 실행 r2(r3 아님), 세트 V 따로(r4), V에 v4 맵 없음 → None | 일치(N11) |
| 14 | 모델 식별 필드가 바뀌어도 같은 처리 (E :139) | `Calibration.load`, `latest_canary` | 시험 묶음(코드 무변경; 20회차 구성 확인 뒤 블롭 동일) | 일치 |
| 15–17 | E0.5 표·재시험·같은 시각 K = 3 (E :236-238) | `e05.vote_steps`, `e05.py` | 시험 묶음; 파드 `e05 --data jsel_dev/P1 --split dev --episodes 2` → `E05_DONE` | 일치 |
| **18** | γ 2/3 (E :240, M4 :276) | `m4.share_at_least:72-77`, `GAMMA` `:46` | 로컬 B1 새 비율(6/9·20/30·200/300·3/4 참, 5/8·19/29·199/300 거짓) | 일치 |
| 19–20 | `C_flip` 두 식, A0–A4·층 (E :242, :246) | `e05.py` | 시험 묶음 | 정본 기록(§73) / 일치 |
| **21–28** | 판정 1–10 경계 (E :256-265) | `replay.judge_e05`, `stats.at_least/below` | 로컬 E1 CMP_EPS: `at_least(0.1+0.2, 0.3)` 참, `below(0.1+0.2, 0.3)` 거짓, `at_least(0.3−1e-9, 0.3)` 거짓; 파드 `E05_DONE` | 일치 |
| 29, 89 | FLIP_TH 후보 α 0.01·범위 (E :253, :487; M4 :285) | `e05.py:437-446` | 시험 묶음 | 일치 |
| 30 | 같은 시각 뒤집힘 성공·섭동 따로 (E :253, §27) | `e05.py:352-383` | 시험 묶음 | 일치 |
| 31–33 | d_p95 = E0 값, 분당 400 [가정], E1 반분 | `M4Params.d_p95_init`, `calib.halves` | 시험 묶음 | 정본 기록 |
| 34–35 | ECE 15 동일 질량, 오답 < 30 판정 불가 (E :320) | `calibration.ece_mass:71` | 로컬 E6(330예측·15구간 → 0.276 ∈ [0, 1]); 시험 묶음 | 일치 |
| **36** | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat:59-64` | 로컬 E2 새 n(유리수 기준값과 대조): 100·α 0.01 → 100, 99 → 99, 49·α 0.02 → 49, 48 → inf, 19·α 0.1 → 18, 9 → 9, 8 → inf | 일치 |
| 37–43 | log p 자름·질문별 온도·원 확률·판정 1·7·8·`ambiguous` ECE 제외 (E :333-346) | `calibration.py`, `core.py:362-393` | 시험 묶음; 파드 `calib --heldout jsel_dev/P1 --episodes 2` → `CALIB_DONE` | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| **45** | N_max = ⌈d̂/T_c⌉+1 (M4 :258) | `m4.CommitLedger.n_max:178-182`, `d_hat:165-173` | 로컬 B9: d̂ 0.66 → 3(정확히 2.0 경계), 0.6601 → 4; d̂ = ⌈0.95·20⌉ = 19번째(1..20 ms → 0.019) | 일치 |
| 46–49 | γ·W·비가역 W+1·τ | `m4.py` | 로컬 B7 W −1 거부·W 0 수용 | 일치 |
| 50 | conformal α 0.01·w 5 ((b) 경계) | 확인 헤드 보정 파일 | 기본 미보정 | SCOPED S5 |
| **51** | STALE_MAX 1.5 s (E :487) | `m4.older_than:56-58` | 로컬 B3: **100 Hz** 틱 위치 500곳 모두에서 150틱 유지·151틱 버림, B4 +5e-10 유지·+2e-9 버림 | 일치 |
| 52–53 | C2 = VLM Stream, C0–C6 설정 (M4 :329-345) | `conditions.py`, `m4.py:220-226` | 파드 `--conditions "C3,CX"` → "refused before any worker"(가드 15) | 일치 |
| **54** | C5 = §4.2 전체, C5' = (b) 범주 뺌(줄은 none), 판정 3 (M4 :155, :232, :340-342, :361; §77 보충 (3)) | `core.b_line`, `core._boundary:527-578` | **파드 Isaac DEV 26**: C5 `last_step` {none 1, OK 29, LAG 12, DEVIATE 14}, C5' none 56/56, 요청 본문 마지막 `last_step:` 줄 = 행 값 112/112 | 일치 |
| 55 | H 1과 3 (정본 §2, M4 :188-189) | `m4.early_ask_steps:61`, `M4Params.H` | 로컬 B8 기본 H 3; 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 |
| **56–58** | n_LA 2·조기 호출 당겨 씀·FLIP_TH 끔; H = 1 = 같은 스텝 앞당겨 2~3회 (§75) | `m4.py:61-69`, `core.py:455-503` | 로컬 B5 네 창을 **정확한 유리수 창과 대조**: (0.33, 0.33, 0.33, 1.32) → [2, 3, 4, 5](양 끝 포함), d 0.3300001 → [3, 4, 5], 창 빔 (0, 0.1, 0.33, 0.2) → [1](d 뒤 첫 스텝), (0.66, 0.2, 0.33, 1.0) → [3, 4, 5]; B8 n_LA 2·FLIP_TH None | 일치 |
| 59 | 경계 직후 W 2·γ 1.0 등 | 없음 | §73 D5 | SCOPED S9 |
| **60** | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.select_rule:131-142` | 로컬 E7: 오라클 정확히 0.90 적격, (0.40 대 0.42) 차 정확히 0.02 → plan, 0.4201 → time0.33, 모두 0.90 미만 → None | 일치 |
| 61–62 | 폐루프 RD 재표집 = layout 짝, 주 RD = Score (EVAL :182-184) | `closed.py`, `rd.py` | 파드 `rd --variants standard=jsel_dev,random=gen_dev/random/P0 --episodes 2` → `RD_DONE` | 일치 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | §71 보충 | SCOPED S1 |
| 64–65 | M4b 2,000회, E-M4-lat 비례 STALE_MAX | `m4b/*` / 없음 | §72 예외 / §74 보충 | 일치 / SCOPED S11 |
| **66–67** | H = 1 창·`lead_max` 유한 양수 (§75, §76 N4) | `m4.py:104-113`, `closed.py:151-166` | 로컬 B7 lead_max 0·nan·inf 거부, 1e-6 수용; 파드 `--m4-lead-max 0` 거부(가드 14) | 일치 |
| 68 | E0 판정 4 | `analysis/latency.py` | 시험 묶음 | 일치 |
| 69 | E-M4 판정 7 | 없음 | §75 보충 (2) | SCOPED S12 |
| 70 | FROZEN = 송신 시각 기준 (M4 :150) | `m4.py:228` | §77 N3 | 정본 기록 |
| 71, 93 | 카나리 표류 → J5 끔, 재보정 뒤 재사용 (E :139, :347, §77 N6, §79 D3) | `closed.j5_after_canary:169-185`, `canary.latest_canary:149-165` | 시험 묶음(코드 무변경) | 일치(N11) |
| 72–76 | 응답 모델 필드·재시도 기록, E0.5 정답, `fine_dir`, Astra 카나리 | `models`, `common` | §77 N4·N5, §67 보충; 파드 결정 호출 `canary_id` 112/112 | 일치 / SCOPED S13·S6 |
| 77–79 | (b) 범주 줄·런타임 값·경계 틱 호출 = 방금 끝난 스텝 (M4 :232, §77, §79 N1) | `core.b_line`, `core.act:429-515` | 행 54; 시험 묶음 | 일치 |
| **80–84** | 학습 자료 값·C5' none·ser-A-min-2·옛 체크포인트 거부 (§77 (iv), §77 보충 (1)) | `serialize.with_last_step:12-15` | 로컬 D2 `LAST_STEP_VALUES` 닫힌 집합, "ok"·"" 거부·"DEVIATE" 수용 | 일치 |
| 86–88 | 결정 호출 행 `probs`·blob·`last_step`, Astra 원응답, 결정 이미지는 해시만 | `core.py`, `reqhash.request_body` | 행 6 | 일치 / 정본 기록 |
| 90 | FLIP_TH = 성공 실행 flip_score의 1−α 분위, 질문별 (M4 :287, §79 D1) | `e05.flip_th_conformal:271-281` | 시험 묶음(같은 순위 규칙 = 행 36) | 일치 |
| 91–92 | 같은 시각 뒤집힘 성공·섭동, 층별 A0 대비 flip | `e05.py` | 시험 묶음 | 일치 |
| 94 | E0 판정 4 집계 (§77 N7) | `latency.step_votes:93`, `judgment4:108` | 시험 묶음 | 일치 |
| **95–97, 105, 115–117, 119** | S-E2E 설정·판정 (a)–(e)·재개·evalck·판정 스크립트 입력 검사·고정본 (`prereg_se2e.md` §3·§4, §77 보충 2, §80 N1) | `tools/se2e/se2e_verdict.py` | **파드 `se2ev21.py`: 874cb33 사본의 판정 스크립트를 실제 로그(읽기 전용)에 다시 돌림** → rc 0, 잎 125개가 기록 `verdict_v2.json`과 **차이 0**, 두 시드 (a)(b)(c)(e) pass; `ckpt/se2e/prereg_se2e.md` sha256 `29191168e48d2a13` = 사본 블롭 | 일치 |
| **98** | 라벨 복원 기준(비트 동일, §78 (1)) | `stagea_data.replay_bit_identical:49-53` | 로컬 D1 새 7경우(−0.0·np 0.0 참; True·None·inf·1e-320·[0] 거짓) | 일치(N2) |
| **99** | 에피소드마다 PhysX 장면 재생성, 모든 호출자 기본 (§78 결정) | `sim/scene.py:418-425,529-532,621-633` | **파드 Isaac 한 워커 C5 → C5'(DEV 26, 모의 선택기)**: 행동 **1,877개 비트 동일**(첫 차이 없음, 행동 시각열 동일), 호출 56개·Astra 2개 같은 수·같은 시각, `code_sha` `9242f67e59a09ee4` | 일치(행렬 S16) |
| **100, 118, 132** | 라벨 신뢰 = 재생 비트 동일, 필드 없음·null·NaN 행 제외, 뺀 수와 질문 범위 기록 (§78 (1), §80 D1, §81 N3) | `eval/common.load_truth:378-412` | 파드 `e05 --split pool --seeds 2003,2057,2101 --truth outcome:plan` → rc 0, `E05_DONE`(claim `a_as_stabilizer`) | 일치 |
| 101 | R2_TRAIN은 하드 리셋 빌드, 옛 녹화 처리 보류 (§78 (2)(3)) | 파드 실행(읽기만) | GPU 0·1 R2_TRAIN Isaac 워커 진행 중 | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 선택 거부, `determinism` 시드 검사가 `--out` 앞 (§79 N5, §80 N3) | `eval/common.load_episodes:340-369`, `sim/determinism.py:48-53,197-203` | 가드 21(`fresh --seed 549` → "only DEV 0-29 and POOL")·22(`history --seeds 2119` → "only (got 2119)") rc 1·폴더 없음, 가드 23(`canary build-set --seeds 1150-1151`)·24(`e05 --seeds 30`) → "no episode selected" | 일치(e05 폴더 N10) |
| 103 | Isaac 워커 `OMP_WAIT_POLICY=PASSIVE` (§79) | `closed.worker_cmd:188-199` | 내 Isaac 워커가 이 명령으로 돌아 `CLOSED_DONE`; `--isaac-gpu 2`·`3` rc 1(가드 12·13) | 일치 |
| 104 | e05 qid 등록부 기본 = `<out>` (§79) | `e05.py:680` | 시험 묶음 | 일치 |
| 106–113 | S-E2E 진단 D1–D3 (`prereg_se2e_diag.md` §1–§4) | 파드 고정 사본 | 로그·문서 불변 | 일치 |
| 114 | §7.1 설정 | 파드 판 로그 `config` | `etc21b`: 37484 판 args(묶음 8·2,000스텝·lr 1e-4/1e-4·시드 0·val 150/0·부분집합 없음·코사인) | 일치 |
| **133** | §7.2 주 지표·적합·확인/포화 규칙 | 문서 `se2e_diag.md:148-165` | **파드 `se2ev21.py` 독립 계산(`np.polyfit`)**: acc@2000 = 0.552222 / 0.682222 / 0.685556 / 0.683333, a 0.2944·b 0.0901, Δ25 +0.00111, Δ50 −0.00222 → 확인 거짓·포화 참 | 일치 |
| 134–136 | §7.3 D2 해소, §7.4 처리량, §5 종합 읽기 표 | `se2e_diag.md:12`, `:125`, `:166-180` | 무변경 | 일치(N5·N6·N20) |
| 121 | E-TC 옵션 끔 = 기준 표본, 기본 경로·프롬프트 해시 파일 무수정 (`prereg_se2e_temporal.md` §7, §8) | `se2e_temporal.load_se2e_t`, `stageb_train._load_data` | **파드 `etc21b`: 세 칸 `CODE_HASHES.txt` 12개 = 등록 해시**(N15); 칸 `prompt_config` sha 기본 `dce3869037c1` 대 옵션 판 3개 모두 다름; 시험 `test_stageb_train_defaults_unchanged_and_variant_config` 통과 | 일치 |
| **122** | V = video2: [t−0.3 s, t], 10 Hz에서 k−3(0으로 자름) (§2) | `se2e_temporal.prev_index:46-47` | 로컬 F1 k 0·2·5 → 0·0·2 | 일치 |
| **123** | M = 움직임 줄: 인과 후방 차분, 팔 = 7관절 노름 3분위, 그리퍼 0.85 분위 초과 (§3 :29-31) | `se2e_temporal.backward_velocity:50-53`·`motion_values:67-71`·`motion_line:86-92` | 로컬 **파드 실제 구간값**(0.21791767…·0.60703500…·0.17551597…)으로 F2a: 하한 바로 아래 still, 하한 = slow, 상한 바로 아래 slow, 상한 = fast; F2b 0.2 → opening/closing, 0.17 → still; F3 [2, 2, 2.3, 1.9, 5] → [0, 0, 3, −4, 31], F3b x[k+1]을 99로 바꿔도 v[k] 불변; 파드 `motion_bins.json` sha `e164719a92d5`·n 37,484·arm_q 1/3·2/3·grip_q 0.85 = 등록 | 일치 |
| **124** | 드롭아웃 p = 0.3, 난수 (시드, 스텝) 따로 (§3) | `se2e_temporal.motion_dropout:95-109` | 로컬 F4 20,000표본 비율 0.3003, 같은 (5, 11) 같음·(5, 12) 다름, 전역 `random` 상태 불변, 입력 무변경, `MOTION_DROPOUT` 0.3 | 일치 |
| 125 | 새 판 표지·`prompt_config` → 기본 체크포인트와 섞이지 않음 (§7) | `stageb_train.prompt_config_t`, `fused_model.check_prompt` | 행 121; 파드 칸 `stageb.json` layout `D27v2-video2`/`D27v1`, motion `se2e-motion@v1`(구간 포함) | 일치(N1) |
| **126** | 지표·층: 검증 300 × 3질문 = 900항목, 전이 층 (§4) | `temporal_verdict.metrics:48-60` | **파드 `etc21`**: 네 칸 모두 900항목·300스냅샷·같은 키, 전이 201스냅샷(603항목)·정상 99(297), `transition_val.json` sha `ee7b4fdb7962`; 항목 기록이 `evaluate()` 요약 dec_acc·dec 재현, argmax = `correct` 900/900 × 4 | 일치(N22) |
| **127** | 채택 규칙: 주효과 ≥ +0.02 ∧ 전이 주효과 ≥ −0.01 ∧ FULL p95 증가 ≤ 10 %, 상대 CMP_EPS 1e-12 (§6 :46-48) | `tools/se2e/temporal_verdict.py:24-34,63-68,119-128` | 로컬 `verdict21.py` 8/8(새 배치: 전이 250·정상 50, 이번에는 **V의 이득·전이 경계와 M의 지연 경계**): V 단순 효과 +30/900·+6/900 → 정확히 +0.02 채택 / +35/2/900 거짓; V 전이 (−5, −10)/750 = −0.01 채택 / (−5, −11) 거짓; M 지연 0.33/0.30 = +10 % 채택 / 0.3300001 거짓; M −3.8 % 지연·+0.0256 이득 채택; V가 (video2, motion) 지연 9 s를 보지 않음 | 일치(N3) |
| **128–129** | 판정 스크립트·등록 코드 해시, 등록은 학습 전, 실행 순서, 지연 측정, 판정 (§5–§7) | 파드 E-TC 판, `se2e_temporal.md`, 정본 §83 | **파드 `etc21`: 등록 스크립트(sha `992d3e20198ca317` = 저장소 = 파드 사본)를 실제 예측 4개에 다시 돌림 → rc 0, 기록 `verdict.json`(sha `7f557ac3c0eb2115` = 결과 문서)과 잎 223/223 차이 0.** 독립 재계산: V 주효과 +0.012778(문턱 −0.0072)·전이 +0.018242·FULL p95 +20.38 % → c1 거짓·c3 거짓 → **불채택**; M 주효과 +0.025000(여유 +0.005)·전이 +0.026534·p95 −3.80 % → **채택**; 부트스트랩 M 전체 [+0.0028, +0.0467]·전이 [+0.0008, +0.0531]. 등록 13:05:07Z(커밋 0b853c2 13:07 UTC) < 첫 학습 13:23:48Z(`etc21b` 로그), 재사용 조건 = step 2000 평가와 `predict` 요약 6필드 모두 같음(dec `0.7734998467661596`), 실행 순서·GPU(2: 14:02–14:43, 3: 14:01–14:44 → 14:45–15:21), 지연 50표본 × 4회 형식별 200·워밍업 30. **§83 수치 대조: +0.025 [+0.003, +0.047], 전이 +0.027, p95 −3.8 %, V +0.013·+20.4 % 모두 일치; 구간 경계 0.218/0.607/0.176 = 등록값 반올림.** 결과 문서 칸 표(acc·NLL·층·질문별·항목 전이 116/66/134)·곡선·지연 표·NLL 주효과·GPU 사용률(60.5 %·76.2 %) 모두 원자료와 같음 | 일치(N22–N24) |
| 130–131 | §81 N2 재개 검사 키, §81 N10 라벨 쓰기 null | `stageb_train.py:264-292`, `cli_label.replay_max:37-43` | 파드 시험 `test_r7c15_resume_keys.py`·`test_r7c15_label_write.py` 통과 | 일치(N2) |
| **137** | Astra 호출 주기 = 하트비트(응답 + N, N = 5 s) + 단계 경계 + 사건, in-flight 1, 15 s → 재송신, gpt-6-astra·low·600 (§45) | `runtime/astra_hb.py:33-34,82-140`, `core.py:242-276` | 로컬 C1 송신 1.0 뒤 2.0 없음(진행 중), 응답 3.14 뒤 8.1399 없음·8.14 hb, C2 송신 8.14 → 23.14 유지·23.1400001 초과, C4 모델·effort·600; **파드 판 Astra: hb 5.0 → 8.0, 경계 sub 8.01 → 11.01, 다음 hb 16.01 송신 → 응답 19.01 > 종료 18.77(전달 안 됨, `astra_by_kind` hb 2·전달 2)** | 일치(N4) |
| **140** | 정본 §82: 강등·J1–J6·K5 모드 등은 "구현(다음)·R7 관문 뒤" | 없음(현 구현 = §45 K0–K4) | 로컬 C3·C5 | SCOPED S18 |
| **141** | 정본 §83: 움직임 줄 채택·V 불채택 = E-TC 등록 판정대로; 런타임 적용·누수 수정·확인 실험은 다음 일 | 없음(런타임 직렬화에 움직임 줄 없음; `se2e_data.py:137` 중앙 차분) | 행 128–129(판정 재현), `check21` D3, 파드 요청 112/112 `motion:` 없음 | 일치 / SCOPED S19–S21 |
| **138** | LeRobot v2.1 내보내기 = ROBOTIS 형식(§63), 30 Hz·원본 해상도·관절 행동(§66) | `datagen/lerobot_export.py` | **파드 새 2편**(dr/bottle_tray ep1 = `valid_for_training` false, standard/bottle_tray ep5 = true) `export` → **무효 편은 건너뛰고** 1편·273프레임, `verify` 오류 0·PSNR 최소 40.1 dB·lerobot 0.3.3 적재 273프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참; LeRobot 시험 6 passed | 일치 |
| 139 | R2 DEV 구조 검사(§66, 완료 정의 1) | `datagen/validate.py` | 파드 `/data/harvest/r2/dev/*/*/P0` 전 편 **36/36 오류 없음**(6폴더 × 6), `valid_for_training` 메타 불일치 0; **음성 대조**(`data21b`): 같은 편의 무수정 사본 오류 0, `action` 끝 3행 자른 사본 → "npz action: length 370 (want 373)" | 일치 |

### 5.1 20회차 표와의 차이
- 새 행 141(정본 §83). 행 128–129는 20회차 SCOPED S18(판정이 대상 커밋 뒤)에서 **일치**로 바뀜(판정 재현). 판정 변화 없음(모두 일치 또는 SCOPED). 근거 교체: 행 1(새 경계 23값·R2 11경우·새 가드 24건), 6·54·99·137(새 시드 DEV 26, 112행, 행동 1,877개, Astra 경계), 7(3배 대 4배), 9–12(Holm 멈춤 경계 0.026 > 0.025), 13(질문 판본 올림), 36·45·51·56–58·60(새 경계값·유리수 기준), 122–124(실제 등록 구간값), 127(V 이득·전이, M 지연 쪽), 138(무효 편 건너뜀 포함), 139(음성 대조 추가).

## 6. 확인한 것 (근거)

### 6.1 20회차 정정·E-TC·§83 확인 (과제 1·2)
- `git diff 7e0aeba 874cb33`: `handoff.md` hunk = `:113` 문구(N12 → "정본 범위 줄 가운데 바뀐 것은 머리 줄(:3)뿐이었다(핵심 결정 줄 :84의 §82 표시는 들어갔음)"), 옛 `:114` 빈 줄 삭제·끝 줄바꿈 복원(N15), `:115` 20회차 줄 추가; `draft-log.md:422` 탭 → `\tentative`(N14) + `:462` E-TC 줄; `user-log.md` 79–82; 정본 §83; 새 `se2e_temporal.md`·`r7_cycle20.md`. **N12·N14·N15 실제 반영 확인.** N9(steering 렌더)·N13(E-Astra-motion 정의)은 그대로(N9·N12).
- **E-TC 판정 재현**: 행 128–129. 결과 문서의 모든 표 수치를 파드 원자료(`pred_*.jsonl`, `verdict.json`, `latency.json`, 학습 로그 4개, `gpumon.csv`, 체크포인트 `stageb.json`·`CODE_HASHES.txt`)와 대조 — 차이는 N22(65 % 분모)·N24(분 반올림)뿐.
- **§83 대 사전 등록**: 결정 = 등록 §6 규칙의 결과 그대로(결과 뒤 문턱 변경 없음, 스크립트 해시 불변), V의 "직전 프레임 재사용 판은 새 사전 등록으로만" = 등록 §0·§8("결과를 본 뒤 … 바꾸지 않는다")과 맞음, 움직임 줄 정의·드롭아웃 = 등록 §3, [사용자 결정] = user-log 80(15:40 UTC 경 "일단 움직임 줄 채택할게", f00cb59 15:40:42 UTC). 누수 서술 = 코드 사실(`se2e_data.py:137`), 런타임은 인과(`fused_model.py:47`).
- **제어 문자·줄 끝 전수**(`ctrlscan21.py`, archive 501파일 중 텍스트 452): `\r\r\n` 0, 외톨이 `\r` 0, CRLF 0, `\t`(모든 파일) **0**, 기타 C0·C1·영폭 문자 0, BOM 0, UTF-8 아님 0. 끝 줄바꿈 없음 1(`prereg.json` — 해시가 고정한 원문). `handoff.md`는 끝 줄바꿈 있음.

### 6.2 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외)
- 정본 범위 줄(`§1~§8x|§1–§8x|지금 §8x`): `handoff.md:3`·`:5`·`:83` = §82(**D-1**), `astra_role:11` = §1–§81(작성 시점, N7). 다른 현재 판본 줄 없음(CLAUDE.md·README·SUMMARY·계획 문서에 정본 범위 없음).
- E-TC·시간 맥락·움직임 줄·video2 어휘: 정본 §81 N2(`:717`)·§83, `draft-log:462`(N14), handoff 옛 회차 줄(날짜 붙은 기록), `hypothesis_short_window:47`·`:166`·`:255`(N21), `steering_representation:199`(병행 주의, 무해), `se2e_diag.md:12`·`:125`·`:131`·`:174`(N5·N20), `prereg_se2e_diag.md:52`·`:54`(등록 원문), `r7c15_fixes.md:34-35`(날짜 기록), 논문(N19). **"V 채택" 또는 "M 불채택"을 말하는 줄 0**, §83과 어긋나는 현재 결정 서술 0.
- 속도 출처(`np.gradient|중앙 차분|후방 차분`): `se2e_data.md:62`·`:96`("중앙 차분" — 사실대로), `prereg_se2e_temporal.md:29`, `se2e_temporal.md:81`·`:85`, 정본 §83, 논문 `3_method.tex:30`, 코드 `se2e_data.py:137`·`se2e_temporal.py:13`. **S-E2E 속도를 인과적이라고 적은 줄 0.**
- user-log 79–82 대 문서: 정본 결정 없음(브레인스토밍) — handoff 대기 항목이 77·78까지만 가리킴(N12). §72–§82 사실은 20회차 grep 뒤 바뀐 파일이 위 6개뿐이라 그 결과가 유지된다(하트비트 어휘 새 줄 = `draft-log:422` 옛 기록의 탭 복원·`r7_cycle20.md` 인용뿐).

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st` + 코드 사본으로 R2 DEV 전 편 `validate_episode` **36/36** + 음성 대조 검출; LeRobot 시험 6 passed; 새 2편 내보내기(무효 편 건너뜀)·검증·lerobot 적재(행 138). §83 움직임 줄·누수 수정은 다음 일(S19·S20). |
| 2 모델 | 충족(CPU) | GPU 학습 없음 → CUDA 시험·GPU 재적재 건너뜀. 파드 CPU 스모크(N26), CPU 묶음의 `test_stageb_torch.py`·`test_r7c15_resume_keys.py`·`test_se2e_temporal_qwen.py` 통과. |
| 3 폐루프 | 충족 | Isaac 한 워커(`closed --model mock --split dev --seeds 26 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c21`, 15:58:49–16:03:07 UTC, `IR_INST` `r7c21_standard`): `CLOSED_DONE` C5·C5' 성공 1.0, 18.77 s, 호출 56·오류 0, 확정 비율 0.772, 결정 2.985/s, 행 필드·blob(행 6), `meta.bootstrap` 10000, `prereg` OK, git `874cb338`, `code_sha` `9242f67e59a09ee4`, 하드 리셋 빌드 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 15:55:49–15:56:25 UTC): `e05` → `E05_DONE`, `rd` → `RD_DONE`, `calib` → `CALIB_DONE`, `e05 --split pool --truth outcome:plan` → `E05_DONE`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.6). 문서 쪽은 D-1(인계 문서 현재 판본 줄). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`, 15:55:42–15:55:49 UTC, 20회차와 다른 값)
- 1 `e05 --data P1 --split test`, 2 `e05 --split cal --seeds 549`, 3 `calib --fit-split cal`, 4 `calib --heldout-split test_p5`, 5 `rd --split cal`, 6–8 `closed --split test --seeds 1000`·`cal 549`·`test_p5 1329` → "refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 29,30`, 10 `pool --seeds 1999`, 11 `dev --seeds 2000` → "not in split … never opened"; 12–13 `--isaac-gpu 2`·`3` → "GPU 2 never renders"; 14 `--m4-lead-max 0`, 15 `--conditions "C3,CX"` → "refused before any worker"; 16 `HARVEST_ALLOW_SPLIT=cal` + `closed --split test --seeds 1000`, 17 `=test_p5` + `e05 --split test` → 거부; 18 `gen --seeds 59999`(확인 없음), 19 `--seeds 9999 --confirm-train`, 20 `--seeds 2119 --confirm-train` → 거부; 21 `determinism fresh --seed 549` → "only DEV 0-29 and POOL"; 22 `history --seeds 2119` → "only (got 2119)"; 23 `canary build-set --seeds 1150-1151` → "no episode selected"; 24 `e05 --split dev --seeds 30` → "no episode selected". **24건 모두 rc 1**; 출력 폴더는 24번(e05)의 빈 폴더 하나(N10), 나머지 0.

### 6.5 A. 테스트
- 로컬(`…\r7c21\repo` = 874cb33 archive, `python -m pytest -q -rs -p no:cacheprovider -o addopts="" --basetemp=D:/tools/scratch_qdd/r7c21/pt`): EXIT 0, **1006 passed · 15 skipped**.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, TMPDIR·pyc·카나리·qid 등록부 = scratch): **1122 passed, 4 skipped**, EXIT 0(15:55:08Z).
- 파드 LeRobot(`venv_e3st` + `r2/pylib_lerobot`·`pylib_pytest`): **6 passed**.

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가. 검토 시작 때 HEAD = 874cb33(작업 트리에 다른 에이전트의 미커밋 코드); 끝날 때 HEAD = 44c907d(N27)와 논문 등 작업 트리 변경 — 내가 만든 것 아님, 건드리지 않음. 로컬 C:에 이 검토의 산출물 없음(하네스 작업 출력 파일만).
- 파드 정리(`clean21.sh`, 경로를 하나씩 적은 스크립트, 16:03:47 UTC): `tmp/r7c21`, 내 Isaac 판이 만든 `tmp/carb.FMR1rR`(15:58:50Z)·`tmp/tmpf5yr1400`(15:59:07Z)·`cache/pyc_r6/data/harvest/tmp/tmpf5yr1400`·`cache/pyc_r6/data/harvest/tmp/r7c21`, `ir/kitcache/cyclo-r7c21_standard`(208 MB). 판별: Isaac 앞뒤 목록 차이, 생성 시각이 내 Isaac 창(15:58:49–16:03:07Z) 안, `/proc/*/fd`에서 여는 프로세스 0. 같은 차이에 나온 `ir/kitcache/cyclo-astram_sanity`(16:02:47Z 생성)는 **다른 에이전트의 것이라 남겼다**. 끝에 `tmp`·`kitcache`의 r7c21 항목 0, 내 프로세스 0.
- 로컬 임시(`D:\tools\scratch_qdd\r7c21`: `src.tar`, `repo/`, `pt/`, `tmp/`, `tv/`, `pod/`, 스크립트)는 다음 순회 대조용으로 남김(C: 아님).
- 절차 사고(내 쪽, 결과 영향 없음): `pod_eval21.sh`의 LeRobot 왕복에서 r2/dev에 없는 `random` 변형을 골라 export rc 1, 음성 대조 사본에 `rows/`를 빠뜨려 예외 — 둘 다 `pod_fix21.sh`·`data21b.py`로 올바른 입력으로 다시 돌려 위 결과를 얻었다(첫 실행의 잘못 만든 링크 폴더는 재실행 전에 지움). 36/36 본 검사는 첫 실행에서 끝났다.

## 7. 다음 순회 전에 할 일 (제안)
1. **D-1**: `handoff.md:3`·`:5`·`:83` 정본 범위 → §83, `:84` 핵심 결정에 §83 토막, `:3` 갱신 시각; 같은 기회에 `:88` 대기 항목을 user-log 79–82로 갱신(N12). 고친 뒤 `grep`으로 세 줄 확인.
2. (선택, NOTE) N13 draft-log·direction-log에 20·21회차와 §83 줄, N20 `se2e_diag.md:174` "→ §83", N22 `se2e_temporal.md:82` 분모, N23 `:81` "→ §83", S20의 `se2e_train.md` 한계 한 줄, N9 steering 표 칸.
3. 22회차 대상은 44c907d 이후 HEAD(코드 변경: 속도 누수 수정·새 데이터 `se2e_c1`·확인 실험 사전 등록과 판정 스크립트) — 연속 무결 0부터. 확인할 것: 변환기 후방 차분이 모든 속도 필드(`qd`·`grip[1]`)에 적용됐는지(미래 프레임을 읽지 않는 행동 시험), 새 사전 등록이 학습 전에 고정됐는지(커밋·로그 시각), §83 확인 실험 판정 스크립트의 문턱이 등록 원문과 같은지, 옛 `se2e` 데이터·체크포인트와 새 판이 `prompt_config`·데이터 판본으로 섞이지 않는지.
