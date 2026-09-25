# R7 객관 검증 순회 — 26회차 (cycle 26, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle25.md`의 표·결론을 근거로 쓰지 않고 사전 등록·정본 원문에서 대조표를 다시 만들었다. 행마다 **21–25회차와 다른 새 경계값으로 구성한 입력 → 실제 함수·CLI 출력**, **기준선 파일 수정 전·후 코드의 같은 입력 실행 비교**, 또는 **파드 원자료 재계산**으로 확인했다). 작성 2026-09-25 19:45 UTC 무렵(로컬 사본 풀기 19:07:30Z, 파드 첫 명령 19:12:49Z, 파드 정리 끝 19:40:40Z). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`6483397`**(`6483397c35d1d70a1cdfa134e498bd8b2ce3e7d1`, 커밋 시각 2026-09-25 18:59:57 UTC, "book 06-updates: log the README TOC change"). `c767c3a..6483397` = 커밋 14개(ded38d7 E-MA1b 사전 등록 + 코드 — **기준선 파일 `harvest/train/stageb_train.py` +62/−7**, bb1f5f7·7bb9035 결합 구현 계획, 13f3495 user-log 88, 745af38 논문, 35029e5·8063733 탐침 등록 개정·정정, 36dd6cd 25회차 보고서·정본 §85·정정, 9815725 user-log 89, 3ad960b `ma1.md` 정정, e15270a·4117851·641547e·6483397 기록책 `docs/book/`), `git diff --stat` 56파일 +5,737/−110.
- **범위 나눔(메인 결정, 25회차와 같음)**: **기준선 판정**(연속 무결 카운트에 들어감) = `harvest/`(런타임·평가·시뮬·분석·학습 파이프라인), `tools/`(새 실험 도구 제외), 시험, 정본, 25회차 목록의 사전 등록, handoff·기록·결과 문서, 그리고 이번부터 **기록책 `docs/book/`(살아 있는 문서)**. 이번 기준선에는 **ded38d7이 고친 `stageb_train.py`의 기본 경로**가 들어간다. **실험 코드 절**(따로 판정, 카운트와 별개) = E-MA1b(`prereg_ma1b.md`, `harvest/train/se2e_a3d.py`, `se2e_trace_model.py` 변경, `tools/ma1/build_a3d.py`·`ma1b_verdict.py`, 시험 5개). 미커밋 탐침 파일(`harvest/astra_motion/`, `results/astra_motion*`)은 범위 밖. **E-MA1b 예측·평가·판정 파일은 열지 않았다**(학습 로그는 첫 줄 `config` 사건만 파싱해 인자·시각·`prompt_config`만 출력, 나머지는 이름·시각).
- 사본: `git -c core.autocrlf=false archive 6483397`(해시 고정, tar 주석 = `6483397c35d1…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c26\repo`에 풀었다(**542파일** = 25회차 525 + 17; 텍스트 파일 CR 0 — CR은 글꼴 두 개의 이진 바이트뿐). 파드 사본 = 같은 archive를 `kubectl exec -i … tar -xf -`로 흘려 `/data/harvest/tmp/r7c26/code`(543파일 = + JSON `CODE_VERSION`), 비교용 **수정 전 사본 `c767c3a`**(`code_before`, 525파일); 두 사본 텍스트 CR 0, 올린 스크립트 CR 0(매번 확인). 파드 산출 `meta.git.commit` = `6483397c35d1…`, dirty false.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle25.md`, 정본 `00-interfaces.md` §1–§85(뒤 절 우선), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`·`prereg_se2e_temporal.md`·`prereg_se2e_motion_confirm.md`·`M4-overlap-commit.md`·`prereg_astra_motion.md`(개정 확인)(실험 절: `prereg_ma1b.md`).
- 분류(25회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·결과 문서·같은 문서의 뒤 결과와 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 기록이 없는 것. 정본이 "나중에 할 일"로 적은 것은 SCOPED. 뒤 절이 이미 덮는 정본 문장, 출처 표기만 어긋난 요약 수치(값은 맞음), 추정 표시(≈)가 있는 파생 수치는 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c26`(C: 쓰기 없음; 하네스 작업 출력 파일만). 스크립트는 Write 도구로 쓰고 경로로 실행(내 스크립트 몇 개는 `sed`·Edit로 고친 뒤 재실행). **절차상 어긋남(내 쪽) 1건**: 19:2x UTC 무렵 로컬에서 설치된 pytest의 `tmp_path` 보존 정책 소스를 읽으려고 인라인 `python -c`를 한 번 썼다(읽기만, 저장소·파드 영향 없음; N62). 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c26`, `source /data/harvest/env.sh`, **모든 kubectl에 `MSYS_NO_PATHCONV=1`**(끝에 `/C:` 없음 확인). GPU: Isaac = GPU 1에 **내 프로세스 하나**(`--inst-prefix r7c26`, `IR_INST` `r7c26_standard`, `IR_ROOT=cyclo`; 같은 GPU의 R2_TRAIN Isaac 워커는 건드리지 않음), GPU 2(E-MA1b)·3에는 아무것도 올리지 않음(가드 12·13은 워커 전에 거부). CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`, 한 번에 한 묶음(수정 전·후 비교 → CPU 시험 → 가드·평가·데이터·E-MA1b 확인 → Isaac → 정리). 시드 DEV·POOL만. 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. 탐침 비용 장부는 시각·모델·effort·비용·토큰 수 필드만 읽었다(프롬프트·답 안 읽음).

## 판정 (기준선): **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 1 |
| SCOPED | 22 |
| NOTE | 54 |

## 판정 (실험 코드 절, 카운트와 별개): **PASS — 코드 결함 0, DOC 0**

**기준선 파일 `stageb_train.py`의 기본 경로는 수정 전(c767c3a)과 행동·바이트가 같다**(§6.1): 같은 파드 CPU에서 수정 전·후 사본으로 실제 `cmd_train`(백본 로더만 작은 무작위 Qwen3-VL로 바꿈, 실제 `se2e_c1` 행)을 시드 5·4스텝·2스텝마다 저장으로 돌린 두 판(기본 D27v1, 움직임 줄 켬 = E-MA1b 기준 칸 경로)에서 **학습 손실·로그 기록 전부 동일**, `heads.pt` 191텐서·어댑터 바이트·`stageb.json`·`train_state.pt`(순서·난수·옵티마이저 206매개변수) **비트 동일**, `prompt_config` sha(`b491cf1b71f2`·`c1b0798217f5`)와 `files_sha`(11·14파일) 동일·`aux_extra` 없음, `predict` 항목 기록·`evalck` 동일, **교차 재개**(새 코드가 옛 체크포인트를, 옛 코드가 새 체크포인트를 step 2에서 재개) 3–4스텝이 원래 판과 동일; CLI 기본값은 **기존 키 전부 같고 새 키 4개만**(`aux_extra` none, `a3d_root`, `aux_view` trained, `extra_out` "") 추가; `PROMPT_FILES`·`PROMPT_FILES_B`·`TEMPORAL_FILES`·`stageb_expert`·`prefix_share`·`se2e_trace` 블롭 c767c3a = 6483397, `harvest/runtime` 변경 0. 회귀: 로컬 **1056 passed / 17 skipped**(Git Bash, 183.4 s), 파드 CPU **1188 passed / 4 skipped**(118.4 s), LeRobot 6 passed; 가드 **28건** 모두 rc ≠ 0(21–25회차와 다른 값, `--m4-lead-max=1e400`·`=-7`, `--conditions "C5,C10"` 등) + E-MA1b 옵트인 가드 4건; R2 DEV `validate_episode` **36/36** + 21–25회차와 **다른 종류**의 음성 대조 5종(행 `valid` 가운데 패딩, 행 `action_exec` 한 스텝 짧음, 모르는 aux 이름, 메타 `success` 거짓, 프레임 하나 덧붙임 — 모두 검출, 무수정 사본 오류 0); 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 모두 완료; 새 시드 **DEV 3**에서 같은 Isaac 워커 C5 → C5' 행동 **1,427개 비트 동일**; 로컬 `check26.py` 41항목(내 기대 설계 오류 2건 재설계 뒤 전부 일치, N62); `prereg_hash.py --check` OK; 제어 문자 전수 0(텍스트 489파일)·변경 md 19개 표 칸 수 불일치 0. **25회차 정정 주장은 실제 diff와 모두 맞다**(§6.2).

**DOC 1건(기준선)**: 기록책 `docs/book/01-experiments.md:38`이 R7 이력을 "16·20·22회차 PASS, 나머지 FAIL"로 적는데, 같은 대상 트리의 handoff `:100`("**R7 6회차(2026-09-25 02:20 UTC) PASS**: DEFECT 0, DOC 0 … 연속 무결 1회")과 결과 `r7_cycle6.md:9`("## 판정: **PASS**")은 6회차도 PASS다(D-1). 책은 "숫자는 커밋된 결과 문서에 있는 값만 옮긴다"(README `:8`)를 스스로 규칙으로 두고 이번 회차부터 기준선 범위다. **연속 무결 0 유지.**

---

## 1. DEFECT

없음.

(검토한 후보와 판단: ① `RESUME_KEYS`에 `a3d_root`가 들어가 `--aux-extra none` 판도 `--a3d-root` 값을 바꿔 재개하면 거부된다 — 쓰이지 않는 값에 대한 과한 엄격함일 뿐 기본 경로의 결과는 바뀌지 않고, 옛 체크포인트(키 없음)는 기본값으로 읽혀 재개가 통과한다(교차 재개 확인) → NOTE N46. ② `predict --extra-out`은 파일을 닫지 않고 `json.dump(…, open(…))` — CPython에서 즉시 닫히고 옵트인 경로 → 실험 절 NOTE.)

## 2. DOC

- **D-1. `docs/book/01-experiments.md:38` — R7 PASS 회차에서 6회차가 빠졌다.** 대상 트리에서 handoff §2.8 `:100` "**R7 6회차(2026-09-25 02:20 UTC) PASS**: DEFECT 0, DOC 0, SCOPED 8, NOTE 14 … 연속 무결 1회", `docs/stage3/results/r7_cycle6.md:9` "## 판정: **PASS**". 책의 줄은 "16·20·22회차 PASS, 나머지 FAIL(8회차 DEFECT 5 등)"이라 적어, 기준점 이력(연속 무결이 몇 번 1까지 갔는지)을 틀리게 전한다. 책 README `:8`의 규칙("숫자는 커밋된 결과 문서에 있는 값만 옮긴다")과도 어긋나고 정정 표시가 없다. **고칠 것**: "6·16·20·22회차 PASS(각각 연속 무결 1에서 다음 회차 FAIL), 나머지 FAIL"로 고치고 `06-updates.md`에 같은 커밋으로 한 줄. 재발 방지: 책 줄을 쓸 때 회차 목록은 handoff §2.8을 `grep -n "PASS"`로 뽑아 옮긴다.

(검토했지만 DOC로 올리지 않은 후보: ① 정본 `:729`(§82 E-Astra-necessity "유료 실행은 … 사용자 승인 후")·`:730`(§82 "남은 [결정 필요]: falsify …")에 표시가 없다 — 뒤 절 §85(`:762`, 유료·GPU 실험은 자체 검사로 실행, 일반 문장)와 §84(`:746`, "§82 [결정 필요] 해소")가 덮고 handoff `:5`가 "뒤 절이 앞 절을 덮는다"를 명시 → N47. ② 책 `05-costs.md:13`의 토큰 수(입력 507/657/811, 출력 73, 추론 약 19)는 인용한 user-log 87·등록 수정 2에 없지만 **값은 맞다**(파드 장부 17:40:44–17:41:35Z 유료 13행의 `usage`: 입력 507/657/811, 출력 평균 949/13 = 73.0, 추론 평균 253/13 = 19.5; 비용 합 203.99원·평균 15.69원·지연 중앙값 4.201 s) → 출처 표기 N50. ③ 책 `01:50`·`05:30` "≈ 2.9 GPU-h(15:53–17:21 × 2)"는 원문(`se2e_motion_confirm.md:64–67`: 15:53–16:31, 16:37–17:15)에 없는 끝 시각이지만 ≈ 추정 표시가 있다 → N51. ④ 책의 절 귀속·출처 표기 어긋남(ECE 15구간 §73 대 실제 §72 등) → N53–N55.)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드 R2_TRAIN Isaac 워커 5개 진행 중(19:13Z, `gen gen --kinds P1 --seeds 10600-10799 --confirm-train`, standard·dr, GPU 0·1; 읽기만); 확인 인자 없는 `gen gen --seeds 10123` rc 1(가드 19).
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8.
- S6. Astra 카나리 "none"(§67 보충).
- S7. S-E2E 계열 체크포인트의 런타임 형식 차이(§77 보충 (2), §80).
- S8. CONTRADICT-soft(§68 K6).
- S9. §73 D5 M4 설계 확장.
- S10. §73 N5 E1 범위.
- S11. §74 보충 E-M4-lat 비례 STALE_MAX.
- S12. §75 보충 (2) E-M4 판정 7.
- S13. §77 N8 (13): 완료 정의 밖 사전 등록 실험.
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — 6483397에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. **정본 §82 구현 및 §84 결합 설계 구현**(직렬 흐름 호출, 두 층 M4, 카메라 3대·덧그림, falsify 먼저 평가) — §84 "R7 E2E 준비 기준점 뒤". 지금 코드: 파드 `closed --hb-mode K7`·`k1` → 워커 전 거부(가드 26·27, "from ('K0', … 'K4')"), Astra 요청 이미지 1장·effort low·600(파드 Astra 4행), DEV 3 Astra 겹침 0(hb 5.0 → 8.0, sub 8.01 → 11.01). 결합 구현 계획(bb1f5f7·7bb9035)은 문서뿐, 코드 0.
- S19. **정본 §83 런타임 적용**(새 직렬화 판본·런타임 속도 구간화) — 파드 결정 호출 요청 86/86 `motion:` 없음.
- S20. **대상 뒤 커밋**: 검토 중 HEAD가 **3500f54**(19:09:37Z, "E-Astra-motion results (6,933 KRW) … canon §86, spec §17, handoff, book 01/02/03/05/06; probe code + 62 tests")로 움직였다. 내가 처음 `D:\qdd` 작업 트리에서 책을 읽었을 때 이 판이 섞여 있어(§86·P57–P62·탐침 수치) 모든 대조를 **6483397 사본에서 다시** 했다(N63). 27회차 대상.
- S21. **탐침 E-Astra-motion 실행·결과**: 대상 트리에는 등록·개정만 있고 코드·결과 문서는 미추적 — 범위 밖(책 `01:61`도 "결과 문서는 작성 중(미커밋) … `[진행 중]`", `05:14` "`[미검증 — 결과 문서 커밋 뒤 확정]`"으로 맞게 표시).
- S22. **E-MA1b 결과**: 진행 중(a3d_s1 끝, a3d_s2 학습·예측 중 — GPU 2). 등록 §3 (2) 기준 재사용 비트 동일 검사와 §4 (c) 실제 체크포인트 보기 검사는 예측 파일을 열어야 해서 이번에 확인하지 않았다 → 결과 커밋 뒤 순회(실험 절 X7).

## 4. NOTE
- N1. (그대로) `stageb_train predict`·`evalck`는 체크포인트 `prompt_config`를 자기 옵션과 대조하지 않는다(새 `--aux-view`도 같음).
- N2. (그대로) `cli_label.replay_max`의 NaN 순서 의존.
- N3. (그대로) `temporal_verdict.py`·`motion_confirm_verdict.py`·`ma1_verdict.py` 입력 검사는 assert·argparse 수준(책 P25).
- N4. (그대로) Astra 시간 초과 뒤 늦게 온 답 처리 — 구현 때 정본 한 줄 권함(탐침 결과 커밋 3500f54의 §86이 다룸 — 27회차).
- N5–N6. (그대로) `se2e_diag.md:131`·`:13`.
- N7. (그대로) 연구 문서 `astra_role_2026-09-25.md:239`·`:515`·`:517` 표시 권함.
- N8. (그대로) `CLAUDE.md:32` 위치; 하위 VLM 계단식 호출 문구.
- N9. (그대로) `steering_representation_2026-09-25.md:33`·`:81` 표시 렌더 누락.
- N10. (그대로, 재현) `e05`는 `--out` 폴더를 거부 전에 만든다 — 가드 25(`e05 --data jsel_dev/P1 --split pool --seeds 2083` → "no episode selected" rc 1)가 빈 `g25/`를 남김.
- N11. (그대로) 카나리 `--force` 같은 날 재실행.
- N12. (해소 기록) **25회차 정정이 실제 diff와 맞다**(§6.2): 정본 §85(`:760`–`:764`, 제목 "[사용자 결정 + Claude 결정]", 첫 항목 "**[사용자 결정] 유료·GPU 실험은 Claude 자체 검사로 실행**"), `:732` 끝 "[→ 대체 2026-09-25 18:28 UTC, R7 25회차 D-1: '실행은 사용자 승인'은 §85(user-log 87 자체 검사)로 대체]", N42 `:683` "[→ 정정 … 절대 허용치 1e-12 …]", N43 `se2e_diag.md:7` 한계 줄, N41 handoff `:86` "[→ … N41: E-MA1b는 §84가 아니라 §85]", handoff §2.8 `:123`, draft-log `:472`–`:474`, direction-log `:72` — 모두 보고서와 **같은 커밋** 36dd6cd(`git show --stat`: 보고서 + 정본 + draft-log + handoff + direction-log + se2e_diag). 탐침 등록 개정 35029e5(18:27:27Z)·정정 8063733(18:29:52Z)은 덧붙이기만(diff에 `-` 줄 0). `results/ma1.md` 정정 3ad960b(`:30` 21·30·28·30, 25회차 재현값과 같음).
- N13. (그대로) `draft-log.md:462` "커밋 안 함" 관용 표기.
- N14–N16. (그대로).
- N17. (그대로) 스펙 `:5`·`:7` 표시.
- N18. (그대로) §82 `:726` 강등 줄과 흐름 호출의 관계.
- N19–N21. (그대로).
- N23. (그대로) 등록 §5 "무수정" 해시 3개 = CRLF 형태.
- N26. (그대로) 확인 실험 등록 고정 시점.
- N28–N29. (그대로).
- N30. (그대로) 로컬 시험은 Git Bash에서(책 P33).
- N34. (그대로) 가드 12·13 거부 문구 "(GPU 2 never renders)"는 GPU 3을 이름으로 들지 않는다(`--isaac-gpu 3`도 같은 문구).
- N36. (그대로) 스펙 §15 비용 추정 산술.
- N38. (그대로) direction-log `:69`–`:72` 행 형식.
- N39. (그대로) MolmoAct 연구 문서의 코드 서술 맞음.
- N42. (해소) 정본 `:683` 표시.
- N43. (해소) `se2e_diag.md:7`.
- N44. (해소) 25회차 절차 기록.
- N45. (그대로) 파드 상태 목록은 `TZ=UTC`로 찍는다.
- N46. `RESUME_KEYS`의 `a3d_root`(D 후보 ①): `--aux-extra none`에서도 재개 비교 대상 — 기본 경로 결과에는 영향 없음. `aux_extra`가 none일 때 `a3d_root`를 건너뛰는 한 줄 권함(선택).
- N47. 정본 `:729`·`:730`(§82 본문)에 뒤 절 표시 권함: `:729` 끝 "[→ §85: 사용자 승인 대신 자체 검사]", `:730` 끝 "[→ §84 해소: falsify 먼저 평가]". §85가 이름으로 대체한다고 적은 것은 `:732`(보충)뿐이라, 정본만 읽는 사람이 `:729`를 따로 볼 여지가 있다(25회차 D-1과 같은 계열이지만 이번엔 뒤 절이 있음).
- N48. 정본 §85 `:762` "유료 한도 약 10만 원·실험별 상한·80 % 정지는 그대로(저장소 CLAUDE.md 규칙과 같음)" — 80 % 정지는 `CLAUDE.md`에 없고 스펙 §15(`2026-09-26-astra-vla-coupling-design.md:183`, §84로 승인)에 있다. 괄호의 출처를 "(스펙 §15, CLAUDE.md 자체 검사 규칙)"으로.
- N49. 25회차 시각: handoff `:123`·draft-log `:473`·direction-log `:72`가 "18:15 UTC 무렵"이라 적는데 25회차 보고서 머리는 "작성 18:25 UTC 무렵, 파드 정리 끝 18:20:16 UTC"다(책 P11 — 시각은 `date -u` 값으로).
- N50. 책 `05-costs.md:13` 옛 설계 G1 줄의 토큰 수 출처(D 후보 ②): 값은 장부와 같다. 출처 칸에 `H/logs/astra_motion/cost.jsonl`(17:40:44–17:41:35Z 13행 `usage`)을 더하기를 권함.
- N51. 책 `01-experiments.md:50`·`05-costs.md:30` "≈ 2.9 GPU-h(15:53–17:21 × 2)" — 원문 끝 시각은 17:15(`se2e_motion_confirm.md:66`–`:67`), 학습 시간 합은 2,172 + 2,166 + 2,222 + 2,226 s ≈ 2.45 GPU-h, 벽시계로는 2 × (15:53–17:15) ≈ 2.7 GPU-h. 17:21은 원문에 없다.
- N52. 책 `05-costs.md:28` "S-E2E 진단·규모 곡선 `[미기록]`" — `se2e_diag.md:138`(D1 GPU 2 27분, D3 GPU 3 1분, D2 GPU 3 36분)과 `:183`(규모 곡선 12:36–14:00Z GPU 2·3)에 있다.
- N53. 책 `03-decisions.md:47`이 "등질량 15구간 ECE"를 §73에 두지만 정본은 §72 N4(`:606`); `03:4` "§56–§62 제목의 '2026-09-25'"는 §59(`:514`)·§61(`:525`)이 이미 09-24; `03:62` "목표 문구는 §84 보충 2 표시"는 정본 `:741` 표시가 16:33 '일반 조종법만'(user-log 83) 결정을 가리킨다.
- N54. 책 `02-pitfalls.md:71` P48 "Qwen 12/14"의 출처 칸 `P/prereg_astra_motion.md §12`는 옛 스냅샷 12장 "오탐 6/7(pre 4/4)"을 적는다; 12/14는 user-log 87(`user-log.md:377`)의 수. `02:12` P04 "이번 세션 ulog94"는 스크래치 스크립트 이름인데 user-log 94처럼 읽힌다(user-log는 89까지). `02:15` P07 "세 번 낡음"과 발생 칸 5회(3·8·18·19·21).
- N55. 책 `01:12` "Qwen3-VL-4B(§44)"(정본 §44는 8B 1순위, 4B는 §50 `:440`), `01:20` "판별력 0.025"(출처는 정본 §65 `:555`·DL 433, `labeler.md`에 없음), `04:61` "R2_TRAIN 10000–10999(계획)"이 **시드 분할** 줄에 있다(정본 §66·코드 가드 = 10000–59999; 10000–10999는 생성 계획), `01:67` "작업자 5, P0 10000–10599"(17:3x 기록 — 19:13Z 파드는 P1 10600–10799 워커 5개, 25회차 보고서 `:42`는 4개).
- N56. 책 갱신 기록 규칙(4117851부터): 641547e(README 목차)는 **같은 커밋에** `06-updates.md` 줄이 없었고, 다음 커밋 6483397이 "앞 커밋에서 갱신 기록 줄을 빠뜨려 여기서 보충"으로 채웠다 — 대상 시점에는 모든 책 변경에 줄이 있다(e15270a는 규칙 전 첫 작성이고 06의 첫 줄이 그것을 적음). `git log e15270a^..6483397 -- docs/book`: e15270a(01–05·README), 4117851(06·README + 06 줄), 641547e(README, 06 없음), 6483397(06 줄).
- N57. 탐침 등록 E-D1 정정은 13절(`prereg_astra_motion.md` 끝)에 덧붙였고 0절 `:6`–`:11` 원문 줄에는 13절을 가리키는 표시가 없다(등록 원문 불변 원칙과 양립하는 "[→ 13절 정정]" 짧은 꼬리표 권함).
- N58. 탐침 수정 1(17:41:05Z, 하드 정지 30,000·S3 삭제)도 커밋(35029e5, 18:27:27Z) 전에 유료 호출을 다스렸다(장부 17:41:05–17:41:35Z 7행, 모두 분석 제외된 옛 설계 G1). 12절 이탈 줄은 수정 2의 재개만 적는다.
- N59. 시험 수: 로컬 **1056 passed / 17 skipped**(183.4 s, 19:21:50–19:24:55Z; 25회차 1046/16 대비 E-MA1b 시험 +10 통과, `test_se2e_a3d_cli.py`는 torch 없어 건너뜀 +1; D: 여유 부족으로 `-o tmp_path_retention_policy=failed`, `PYTHONDONTWRITEBYTECODE=1`), 파드 CPU **1188 passed / 4 skipped**(118.4 s, EXIT 19:28:55Z; +20), 경고 1개(`test_stagea_loss_torch.py:42` 기존), LeRobot 6 passed(35.3 s). 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다.
- N60. 단계 B 소형 CPU 스모크(19:31Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–25회차와 같은 값 — 결정적), expert p50 0.041 s·전체 p50 0.111 s(CPU, 참고), 맥락 토큰 454.
- N61. DEV 3 판: 행동 1,427·14.27 s·호출 43, `last_step` {none 1, OK 34, DEVIATE 4, LAG 4}, 확정 비율 0.90, 결정 3.015/s, rtf 0.367, Astra 2(hb 5.0 → 8.0, sub 8.01 → 11.01), `code_sha` `ff1523d3083b88d9`. 파일명 `dev3-P0-standard-e0`.
- N62. (절차, 내 쪽) ① 인라인 `python -c` 1회(19:2xZ, pytest 소스 읽기만, 로컬). ② 자체 점검으로 다시 설계한 항목 4개(user-log 87·CLAUDE.md 규칙): `check26` H2(시험 파일 `test_se2e_trace_model.py` 수정을 기대 목록에 빠뜨림 → `harvest/`·`tools/` 수정 = 정확히 두 파일로), H7(새 모듈 자신을 import 목록에 넣음 → 가져오는 기준선 모듈은 `stageb_train.py`뿐이고 함수 안 지연 import), `neg26` 보기 검사(요약 줄의 `aux` 손실까지 비교해 "다름" → 등록 §4 (c)대로 항목 기록만 비교하면 **12항목 비트 동일**, 요약 차이는 `aux` 0.787 대 0.0 하나), R2+aux 가드(R2 DEV 행이 먼저 POOL 분할 검사에 걸려 aux 검사에 닿지 않음 → `--dev-val-seeds 0-1`로 다시: "--aux-extra: --data se2e only", 폴더 없음). 모두 내 입력·기대의 잘못이고 코드는 등록·설계대로였다. ③ 로컬 D: 여유가 시작 때 140 MB에서 29 MB로 줄었다(내 몫 27 MB — 사본 25 MB; 나머지는 다른 작업). **D: 가득 참 위험**(메모리의 09-12 C: 사고와 같은 유형) — 메인 확인 권함.
- N63. 작업 트리 대 대상: 처음 몇 분 `D:\qdd` 작업 트리의 책 파일을 읽었는데 HEAD가 이미 3500f54(대상 뒤)였다(§86·P57–P62·탐침 수치가 섞여 있음). 그 읽기는 버리고 모든 대조를 6483397 사본·`git show 6483397:`로 다시 했다. 다음 순회도 작업 트리가 아니라 archive 사본에서 읽을 것.
- N64. 파드 GPU(19:13Z): 0 = R2_TRAIN 워커 2, 1 = R2_TRAIN 워커 3(+ 내 Isaac 19:35–19:39Z), 2 = E-MA1b(a3d_s2 학습 PID 596013 → 예측 PID 604331), 3 = 1 MiB(탐침 Qwen 서버 없음 — 탐침 끝, 3500f54).
- N65. 파드 정리 대상 판별: 내 Isaac 창(19:35:11–19:39:13Z)에 생긴 `tmp/carb.zxmdYY`(19:35:13Z, Kit 임시)·`tmp/tmpnoqpzjh4`(19:35:42Z, `.pyc`가 `cache/pyc_r6` 아래 = 내 워커의 `PYTHONPYCACHEPREFIX`, `closed.py:192–194`)는 내 것. 같은 시각 `TMPDIR=/data/harvest/tmp`인 다른 프로세스는 E-MA1b 예측(PID 604331, `.pyc`는 `cache/pyc`)뿐이라 구분된다.

---

## 5. 사전 등록 대조표 (원문에서 새로 만듦, 행마다 이번 회차의 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**(`check26` H9), 파드 산출 `meta.prereg.check` = "OK". 25회차 표의 행 번호를 그대로 쓴다. 코드 줄은 6483397 기준. 기존 사전 등록 블롭은 c767c3a = 6483397(바뀐 등록은 `prereg_astra_motion.md` 덧붙임과 새 `prereg_ma1b.md`뿐, `check26` H5·H6). "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c26\check26.py`(H·A·V·B·C), **파드** = §6(`ab26.py`·`cmp26.py`, `pod_cpu26.sh`, `pod_eval26.sh`, `data26.py`, `neg26.py`·`neg26b.py`·`view26.py`, `exp26.py`·`usage26.py`, `pod_isaac26.sh`·`closed26.py`, `who26.sh`, `clean26.sh`). "시험 묶음" = 해당 구현을 부르는 저장소 시험이 로컬 1056·파드 1188 묶음에서 통과. 코드 무변경 행(이번 diff 밖)은 새 가드 값·새 판으로 다시 확인했다.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 분할 DEV/CAL/TEST/TEST-P5/POOL/R2_TRAIN (E :113-120, §66) | `eval/splits.py`, `datagen/gen.py` | 파드 가드 28건 rc ≠ 0(§6.4): test 1071·1093, cal 511·517, test_p5 1317, dev 3,31·2061, pool 1987, gen 10123(확인 없음)·60123·1322(확인 있음), determinism 2133·1011 | 일치 |
| 2–4 | POOL 120 × 10·경계 과표집, `ambiguous` 띠, 분할 = 에피소드 (E :121-122) | `sim/snapshot.py`, `stagea_data.split_of`, `calib.halves` | 코드 무변경; 파드 `calib --heldout jsel_dev/P2 --episodes 3` → `CALIB_DONE`; `split_of`가 DEV 행을 POOL 밖으로 거부(N62 R2+aux 첫 시도) | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | 파드 Isaac **DEV 3** C5·C5' 성공(14.27 s, `terminations` success 1) | 일치 |
| **6** | 호출 기록·Astra A6 (E :125-126, §28) | `core.py` | **DEV 3 결정 호출 86행**: 요청 blob 해시 = `request_sha256` 86/86, 이미지 해시가 요청 본문에 86/86, 응답 blob 해시 86/86, `probs` 86/86, `canary_id`·`question_id@vN` 86/86; Astra 4행 요청·머리 JPEG 해시·effort low·600·`output_text` 4/4 | 일치 |
| 7–8 | 군집 부트스트랩 10,000, 같은 시드 짝 (E :130) | `analysis/stats.py`, `closed.aggregate` | 파드 `meta.bootstrap` 10000·seed 0·percentile; C5 대 C5' 같은 워커 | 일치 |
| 9–12 | 판정 2 Holm, 카나리 Holm, 판정 절 해시 | `stats.holm`, `eval/common.py` | 코드 무변경·시험 묶음; `meta.prereg` OK | 일치 |
| 13–17 | 카나리 기준일, 모델 식별 필드, E0.5 (E :136-140, :236-238) | `eval/canary.py`, `e05.py` | 파드 `e05 --data jsel_dev/P1 --split dev --episodes 3` → `E05_DONE`; 가드 24(`canary build-set --seeds 3001-3002`) 거부 | 일치(N11) |
| 18–35 | γ 2/3, `C_flip`, 판정 1–10 경계, FLIP_TH, d_p95·ECE (E :240-320) | `m4`, `stats`, `e05`, `calibration` | 코드 무변경(블롭 동일)·시험 묶음 | 일치 |
| 36–50 | J5 q̂, log p·온도, N_max·d̂, γ·W·τ | `calibration.py`, `m4.py` | 코드 무변경·시험 묶음; 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 / SCOPED S5 |
| **51–58** | STALE_MAX, C0–C6, C5·C5', H 1과 3, n_LA 2 (M4 :155-345, §75, §77) | `m4`, `conditions`, `core.b_line` | 가드 16 `--conditions "C5,C10"` → "condition 'C10': runtime has [C0 … C6]"; **DEV 3 C5 `last_step` {none 1, OK 34, DEVIATE 4, LAG 4}, C5' none 43/43, 요청 본문 마지막 `last_step:` 줄 = 행 값 86/86** | 일치 |
| 59 | 경계 직후 W 2 등 | 없음 | §73 D5 | SCOPED S9 |
| 60 | 라벨 규칙 (labeler :11-12) | `sim/labeler.select_rule` | 코드 무변경·시험 묶음 | 일치 |
| 61–62 | RD 재표집 (EVAL :182-184) | `rd.py` | 파드 `rd --variants standard,random/P1 --episodes 2` → `RD_DONE`; 가드 5 `rd --variants dr=… --split test_p5` 거부 | 일치 |
| 63–65 | H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §71 보충 / §72 / §74 보충 | SCOPED S1·S11 / 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 가드 14 `--m4-lead-max=1e400`(float 넘침 → inf) → "M4 lead_max = inf … finite > 0" 워커 전 거부, 가드 15 `=-7` → 거부 | 일치 |
| 68–94 | E0 판정 4, E-M4 판정 7, 카나리 표류, 응답 기록, (b) 범주 줄, `last_step` 값 | `latency`, `canary`, `core`, `serialize` | 행 6·54; 코드 무변경·시험 묶음 | 일치 / SCOPED S12·S13·S6 |
| 95–97, 105, 115–117, 119 | S-E2E 설정·판정 (`prereg_se2e.md`) | `tools/se2e/se2e_verdict.py` | 코드 무변경; 시험 묶음 | 일치 |
| **98, 100, 118, 132** | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1) | `stagea_data.replay_bit_identical`, `eval/common.load_truth` | 파드 `e05 --split pool --seeds 2031,2066,2110 --truth outcome:plan` → `E05_DONE` | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **파드 Isaac 한 워커 C5 → C5'(DEV 3, 19:35:11–19:39:13Z)**: 행동 **1,427개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 43·Astra 2 같은 수·같은 시각 | 일치(S16) |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | R2_TRAIN 워커 5개 진행 중 | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, 시드 검사가 `--out` 앞 (§79 N5, §80 N3) | `common.load_episodes`, `sim/determinism.py` | 가드 22·23 → "only DEV 0-29 and POOL" rc 1·폴더 없음; 24·25 → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 기본 (§79) | `closed.worker_cmd` | 내 워커가 이 명령으로 `CLOSED_DONE`; `--isaac-gpu 2`·`3` rc 1 | 일치(N34) |
| 106–114, 121–131, 133–136 | S-E2E 진단·E-TC | `se2e_temporal*.py`, `temporal_verdict.py` | 블롭 c767c3a = 6483397(`check26` H3); **수정 전·후 `mot` 판(움직임 줄 켬) 비트 동일**(§6.1) | 일치 |
| 137 | Astra 주기·in-flight 1·low·600 (§45, §82 보충 2) | `runtime/astra_hb.py`, `core.py` | 파드 DEV 3 hb 5.0 → 8.0, sub 8.01 → 11.01, 겹침 0 | 일치(N4) |
| 138 | LeRobot v2.1 내보내기 | `datagen/lerobot_export.py` | **파드 새 2편**(dr/bottle_tray ep2 = `valid_for_training` 거짓 → 건너뜀, dr/mug_tray ep4 참): 1편·277프레임, `verify` 오류 0·PSNR 최소 36.28 dB·lerobot 0.3.3 적재 277프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참; LeRobot 시험 6 passed | 일치 |
| **139** | R2 DEV 구조 검사 (§66, 완료 정의 1) | `datagen/validate.py` | 파드 전 편 **36/36 오류 없음**, 검증기 대 메타 `valid_for_training` 불일치 0; **새 종류 음성 대조 5종**(standard/mug_marker ep1, 288프레임·행 286): 무수정 사본 오류 0·학습 가능; 행 k143 `valid` [1, 0, 1, 1] → "valid: padding only at the end"; 행 k71 `action_exec` 14스텝 → "shape (14, 8), expected (15, 8)"; 행 k57 aux `g2tgt_dw` → "unknown aux names"; 메타 `success` 거짓 → 구조 OK·`valid_for_training` 거짓; 프레임 k287 덧붙임 → 시각 격자·행 수·npz 길이 오류 | 일치 |
| **140–141, 152** | 정본 §82·§84 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 가드 26·27, 요청 86/86 `motion:` 없음, Astra 이미지 1장 | SCOPED S18·S19 |
| 142–146 | 속도 누수 수정, 재변환, `se2e_c1` 판본·분할 (`prereg_se2e_motion_confirm.md:10-31`) | `se2e_data.py`, `tools/se2e_convert.py` | `se2e_data.py` 블롭 불변(H3); 파드 `sha256sum -c` **5/5 OK**(19:40Z); A/B 판 `val_keys_sha` `c2aae0252454`(작은 판) 양쪽 같음 | 일치 |
| 147–150 | 확인 실험 판정·해시·결과 수치·하지 않는 것 | `motion_confirm_verdict.py` | 코드·결과 문서 무변경(25회차 값 재현 유지); `PROMPT_FILES_B` 블롭 불변 | 일치 |
| 151 | §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT`, `core.py` | 파드 Astra 4행 effort low | 일치 |
| **153** | 정본 §85: 유료·GPU 실험 = 자체 검사(사용자 승인 대체) (`:760`–`:764`) | — | 문서 대조: `:732` 대체 표시, handoff `:86`·`:90`, `CLAUDE.md:33`, 계획 `:25`·`:39` 같은 뜻; `:729`·`:730` 표시 없음(N47) | 일치(N47·N48) |
| **154** | **기준선 파일 `stageb_train.py` 옵트인 옵션(ded38d7) — 끔일 때 동작 불변** (`prereg_ma1b.md` §3 (3), §4 (a)) | `stageb_train.py:85-130`, `:305`, `:553-556`, `:615`, `:630-633`, `:664-665`, `:696`, `:720`, `:729-732`, `:805-814`, `:840-843` | **§6.1: 수정 전·후 같은 입력 → 로그·가중치·옵티마이저 상태·`prompt_config`·예측·evalck 비트 동일, 교차 재개 동일, CLI 기존 기본값 동일** | 일치 |
| **155** | 책 `docs/book/` 현재 서술·수치 = 출처 | — | 부분 대조(§6.3): 링크 89개 끊김 0, 정본 절 시각 §26–§85 일치, 사전 등록 시각 8개 일치, DL 줄 번호 22개 일치 | **DOC D-1** / NOTE N50–N56 |

### 5.1 25회차 표와의 차이
- 행 154(기준선 파일 행동 동일)·155(책)를 더했다. 행 153은 D-1 해소(§85) 확인으로 바꿨다. 근거 교체: 행 1(새 가드 28건), 5·6·51–58·99·137(DEV 3, 86행, 행동 1,427개), 61–62(random/P1), 66–67(`1e400`·`-7`), 138·139(다른 편·새 음성 대조 5종).

## 6. 확인한 것 (근거)

### 6.1 기준선 파일 `stageb_train.py` — 수정 전(c767c3a) 대 후(6483397) 행동 비교 (`ab26.py`·`cmp26.py`, 19:15:31–19:22:11Z, 파드 CPU)
- 방법: 같은 파드·같은 파이썬(`venv_train`)·`OMP_NUM_THREADS=2`에서 두 사본을 각자 `PYTHONPATH`로 올려 **실제 `stageb_train.main`**을 부름. 바꾼 것은 백본 로더 하나(`load_backbone` → `kind="tiny"`: 실제 Qwen3-VL-4B 설정·프로세서의 2층 무작위 모델, fp32 — 4B 가중치를 CPU에 올리지 않으려고). 데이터 = 실제 `se2e_c1/conv` 전 행(표본 42,813 → `--max-train 10`, `--max-val 4`), `--seed 5 --batch 2 --max-steps 4 --eval-every 2 --save-every 2`. 판 `def`(옵션 없음, D27v1)·`mot`(`--motion-line se2e-motion@v1 --motion-bins se2e_c1/motion_bins.json --se2e-t-root se2e_c1/conv` = E-MA1b 기준 칸의 경로).
- 결과(`cmp26` **BAD 0**): CLI — `smoke` 키 변화 0, `train` +`a3d_root`·`aux_extra`, `evalck` +`aux_view`, `predict` +`aux_view`·`extra_out`, 기존 키 값 변화 0; `RESUME_KEYS` + `aux_extra`·`a3d_root`, `RESUME_FREE` 같음. 두 판 모두 `config` 기록(출력 경로 밖) 동일·새 인자는 기본값뿐, `prompt_config` sha `b491cf1b71f2`(def, `files_sha` 11파일)·`c1b0798217f5`(mot, 14파일) 동일, 학습 4스텝 총손실(def 3.28337·13.77616·7.47954·6.2747, mot 3.94893·15.17658·6.54156·4.5558)과 평가·저장 기록 동일; `last`·step 2·step 4의 `heads.pt` 191텐서 `torch.equal`, 어댑터 세 파일 바이트 동일, `stageb.json` 동일·`aux_extra` 없음, `train_state.pt` 순서·파이썬/토치 난수·매개변수 이름·옵티마이저 상태 206개 동일; `predict`(last·step 2) 13기록(항목 12) 동일, `evalck --against … --step 2` 동일; **교차 재개**: 새 코드가 옛 코드의 step 2를, 옛 코드가 새 코드의 step 2를 `--stop-at 4`로 재개 → 3–4스텝 기록이 원래 판과 동일.
- 옵트인 쪽 대조(`neg26.py`, 같은 작은 설정, 음성 대조): `--aux-extra a3d@v1`을 켜면 `prompt_config` sha `c1b0798217f5` → `02b5022305a3`(`aux` 키 + `AUX_FILES` 3개, 공유 파일 해시 같음), `stageb.json` `aux_extra` a3d@v1·aux `n_reg` 23, 학습 aux 손실 1.141/0.595/0.733/1.637(기본 0.0), 같은 배치 순서, **step 0 평가 dec·fm 동일**(백본·LoRA·expert 초기값 같은 난수 흐름 — 등록 §3); 가드 `--aux-extra` + R2 데이터 → "--data se2e only", 움직임 줄 없음 → "with the motion line (prereg_ma1b cells)", 기본 `mot` 체크포인트를 `--aux-extra`로 재개 → "settings differ … {'aux_extra': ('none', 'a3d@v1')}", `--aux-extra trace9` → argparse 거부(가드 28). 즉 비교 도구가 차이를 잡을 수 있고, 기본 경로에서는 차이가 없다.

### 6.2 변경분·25회차 정정 확인
- `git diff c767c3a 6483397`: 기준선 문서 = `CLAUDE.md` +2(user-log 88·89 규칙), 정본 +8/−2(`:683` N42 표시, `:732` §85 대체 표시, §85 `:760`–`:765`), draft-log +3(`:472`–`:474`), handoff +5/−2(`:3`, `:7` 기록책, `:86` §85·N41, `:123`), direction-log +1(`:72`), user-log +9(88·89), `se2e_diag.md` +3(N43), `ma1.md` +3/−1(E-N1 머리 표시·E-D3), `r7_cycle25.md` +245, 기록책 7파일 +369, 계획 +4,001, `paper/` 27파일. 코드 = 새 5파일 + 수정 2(`stageb_train.py`·`se2e_trace_model.py`) + 시험 새 4 수정 1(`check26` H2, N62). `harvest/runtime`·`PROMPT_FILES*`·`TEMPORAL_FILES` 변경 0.
- 25회차 권고(§8) 반영: D-1 → §85 + `:732` 표시(**같은 커밋 36dd6cd**), E-D1 → 13절, E-D2 → 35029e5 + 12절 이탈 줄, E-D3 → 3ad960b, N41·N42·N43·E-N1 해소. 남은 것 N17·N38·E-N2·E-N3(범위 밖 탐침).
- **제어 문자·줄 끝 전수**(`check26` C1, 텍스트 489파일): `\r\r\n`·외톨이 `\r`·CRLF·C0·C1·영폭·BOM·비 UTF-8 모두 0. 변경된 md 19개의 표 행 칸 수 = 머리 칸 수(C2 불일치 0).

### 6.3 기록책 `docs/book/` (6483397 사본에서; 독립 읽기 전용 하위 점검 + 내가 핵심 항목 재확인)
- 링크 89개(53개 대상) 끊김 0(미커밋 `harvest/astra_motion/`은 책이 `[미커밋]`으로 표시). `03-decisions`의 정본 절 시각 §26·§27–§85·보충 시각 모두 제목과 같고 §85 뒤 절 주장 없음; 대체 표시(§35→§58, §37→§43, §45→§82, §82 보충→§85, 설계 §3→§84 보충 2) 맞음. `01`의 사전 등록 머리 시각 8개(09:39:32, 11:47:14, 12:33:21, 13:05:07, 15:52:12, 17:32:31, 17:38:25, 17:54:05) 일치, 결과 수치 약 130개 일치(예외 D-1·N51). `02`의 DL 줄 번호 22개·R7 인용 27개 일치(예외 N54). `04`의 경로 75개 존재, GPU 역할·`val_keys_sha e22f6d8ef7fc`·`CMP_EPS` 절대 1e-12 일치(예외 N55). `05`의 한도·상한·가격·계획 예산 일치, 옛 G1 토큰 수는 장부로 확인(N50), 본 단계 약 7천 원은 `[미검증]` 표시(맞음).
- 갱신 기록 규칙: N56. 현재 시제 상태(대기 항목 없음, 연속 무결 0 → 26회차, E-MA1b `[진행 중]`, 탐침 결과 미커밋, R2_TRAIN 진행 중, `se2e_c1` 현재 판)는 handoff·정본과 같다.
- 같은 사실 grep(추적 파일, 6483397): 유료 실행 승인(`승인` × `유료|실행`) — 정본 `:729`(N47)·`:732`(대체 표시)·`:530`·`:549`(옛 E-M4b-meas 과거 서술), handoff `:86`·`:90`(자체 검사), 계획 `:25`·`:39`(자체 검사), `:3932`·`:4000`(계획 안의 '승인' = 사전 등록 초안 — `:39`가 뜻을 바꿈), 탐침 등록 `:3`(user-log 79 인용).

### 6.4 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 19:29:41–19:29:54Z, 21–25회차와 다른 값)
1 `e05 --data P1 --split test --seeds 1071`, 2 `e05 --data P0 --split cal --seeds 511`, 3 `calib --fit-split test --heldout P2 --heldout-split pool`, 4 `calib --fit-split pool --heldout P1 --heldout-split test`, 5 `rd --variants dr=gen_dev/dr/P1 --split test_p5`, 6–8 `closed --split test --seeds 1093`·`cal 517`·`test_p5 1317` → "refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 3,31`, 10 `pool --seeds 1987`, 11 `dev --seeds 2061` → "not in split … never opened"; 12–13 `--isaac-gpu 2`·`3` → "(GPU 2 never renders)"; 14 `--m4-lead-max=1e400`, 15 `--m4-lead-max=-7` → "finite > 0 … refused before any worker"; 16 `--conditions "C5,C10"` → "condition 'C10': runtime has […]"; 17 `HARVEST_ALLOW_SPLIT=test` + `closed --split cal --seeds 526`, 18 `=test_p5` + `e05 --data P1 --split test` → 거부; 19 `gen --seeds 10123`(확인 없음), 20 `--seeds 60123 --confirm-train`, 21 `--seeds 1322 --confirm-train` → 거부; 22 `determinism fresh --seed 2133`, 23 `history --seeds 1011` → "only DEV 0-29 and POOL"; 24 `canary build-set --data P1 --seeds 3001-3002`, 25 `e05 --data P1 --split pool --seeds 2083` → "no episode selected"; 26 `--hb-mode K7`, 27 `--hb-mode k1` → "from ('K0', …, 'K4')"; **28 `stageb_train train --aux-extra trace9` → argparse "invalid choice … ('none', 'a3d@v1')" rc 2**. **28건 모두 rc ≠ 0**; 출력 폴더는 25번(e05)의 빈 폴더 하나(N10). + E-MA1b 옵트인 가드 3건(§6.1)과 재설계한 R2+aux 가드 1건(N62).

### 6.5 A. 테스트
- 로컬(`…\r7c26\repo` = 6483397 archive, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider -q" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/r7c26/pt tests`, `PYTHONDONTWRITEBYTECODE=1`): EXIT 0, **1056 passed · 17 skipped**.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, TMPDIR·pyc·카나리·qid·HF = scratch): **1188 passed, 4 skipped**, EXIT 0.
- 파드 LeRobot(`venv_e3st` + `r2/pylib_lerobot`·`pylib_pytest`): **6 passed**.

### 6.6 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV `validate_episode` **36/36** + 새 음성 대조 5종 검출; LeRobot 시험 6 passed; 새 편 내보내기·검증·적재(행 138); `se2e_c1` 5/5 해시. |
| 2 모델 | 충족(CPU) | CPU 스모크(N60), 수정 전·후 학습 비트 동일(§6.1, 저장·재적재·재개 포함), CPU 묶음의 `test_stageb_torch.py`·`test_se2e_a3d_cli.py`·`test_se2e_trace_model.py` 통과. GPU 학습 없음. |
| 3 폐루프 | 충족 | Isaac 한 워커(`closed --model mock --split dev --seeds 3 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c26`, 19:35:11–19:39:13Z): `CLOSED_DONE` C5·C5' 성공 1.0, 14.27 s, 호출 43·오류 0, 확정 비율 0.90, 행 필드·blob(행 6), `meta.bootstrap` 10000, `prereg` OK, git `6483397c`, 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 19:29:54–19:30:30Z): `e05`(P1, 3편) → `E05_DONE`, `rd`(standard + random/P1) → `RD_DONE`, `calib`(P2, 3편) → `CALIB_DONE`, `e05 --split pool --seeds 2031,2066,2110 --truth outcome:plan` → `E05_DONE`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.7). |

### 6.7 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함). 검토 시작 때 HEAD = 6483397, 끝날 때 HEAD = 3500f54(S20·N63) — 내가 만든 것 아님. 작업 트리의 다른 에이전트 미커밋 파일은 건드리지 않았다.
- 파드 정리(`clean26.sh`, 경로를 하나씩 적은 스크립트를 `bash -s`로 보냄, 열린 핸들 0 확인 뒤, 19:40:40Z): `tmp/r7c26`(13 GB — 작은 판 체크포인트 포함), 내 Isaac 판의 `tmp/carb.zxmdYY`·`tmp/tmpnoqpzjh4`·`cache/pyc_r6/data/harvest/tmp/tmpnoqpzjh4`·`cache/pyc_r6/data/harvest/tmp/r7c26`, `ir/kitcache/cyclo-r7c26_standard`(208 MB). 판별 근거 N65. 끝에 `tmp`·`kitcache`·`pyc_r6`·`pyc`의 r7c26 항목 0, 파드 루트 `/C:` 없음, 명령줄에 r7c26이 든 프로세스 0, 열린 핸들 0. `code_ma1b`·`code_se2e_confirm`·`data/ma1b`·`data/se2e_c1`·`logs/astra_motion/cost.jsonl`은 읽기만, `ckpt/ma1b/*/log.jsonl`은 첫 줄만, 나머지 `*/ma1b`는 이름·시각만.
- 로컬 임시(`D:\tools\scratch_qdd\r7c26`: `repo/`, `pod/`(스크립트·`out/` 파드 출력 사본), `check26.py`·`check26_out.txt`, `extract26.py`, `local_pytest26.sh`·`local_pytest.txt`, `up26.sh`)는 다음 순회 대조용으로 남김(D: 여유 부족 — N62 ③).

## 7. 실험 코드 절 (E-MA1b — 별도 판정: PASS, 코드 결함 0, DOC 0)

### 7.1 행동 확인 (모두 통과)
| # | 등록 값 (`prereg_ma1b.md` file:line) | 구현 | 확인 | 판정 |
|---|---|---|---|---|
| X1 | 고정 코드 해시 5개(§6 표, `:46`) | `se2e_a3d.py` `82353d67…`, `se2e_trace_model.py` `67f7eab5…`, `stageb_train.py` `98ff930c…`, `build_a3d.py` `8597de82…`, `ma1b_verdict.py` `6bc198bf…` | 로컬 H1: LF 블롭 sha16이 ded38d7 = 6483397 = 등록 = 내 사본; 파드 `code_ma1b` 다섯 파일 = 등록; `ckpt/ma1b/a3d_s1`·`a3d_s2`의 `CODE_HASHES.txt`에 등록 해시 5/5 | 일치 |
| X2 | 등록 시각 < 첫 A3d 실행(머리 `:1` 17:54:05Z, "어느 A3d 판도 학습하기 전에") | 커밋·파일 시각 | 등록 커밋 ded38d7 **17:54:06Z** < `code_ma1b` 풀기 17:54:23Z < `run_ma1b.sh` 17:54:45Z < A3d 데이터 17:54:51–56Z < **사전 실행(스모크 20스텝) `config` 17:55:24Z** < 기준 예측 18:01–18:06Z < **a3d_s1 `config` 18:06:56Z** < a3d_s2 `config` 18:56:49Z. 등록 앞의 `ma1b` 산출물 없음 | 일치 |
| X3 | 기준 재사용 조건 (1): 인자가 `run`·`out_root`·`aux_extra`·`a3d_root` 밖에서 전부 같음(`:25`) | 학습 로그 첫 줄 | 파드: a3d_s1·a3d_s2 대 motion_s1·motion_s2 `config.args` 차이 **없음**; `n_train` 37,484, `total_steps` 2,000, `val_keys_sha` `e22f6d8ef7fc` 같음; `prompt_config` sha `02b5022305a3`(aux 표시) 대 `7d1cf93de7b5` — 섞이지 않음(§4) | 일치 |
| X4 | 기준 재사용 조건 (3): 학습 경로 코드가 줄 끝 밖에서 같음, `stageb_train.py` 새 옵션 끔 = 동작 불변(`:25`, §4 (a) `:32`) | `code_se2e_confirm`(CRLF) 대 `code_ma1b` | 파드: `harvest/**/*.py` 110개 CR 제거 뒤 동일, 다른 것 `stageb_train.py`뿐(→ 기준선 §6.1에서 기본 경로 비트 동일), `code_ma1b`에만 새 3파일 | 일치 |
| X5 | 목표 정의: 5점 = k + i(e − k)/4 선형 보간, e = 그리퍼 상태(> 0.5 닫힘)가 바뀌는 첫 프레임 또는 끝·상한 30프레임, 목표 = p₂…p₅ − p₁(12값), e = k면 마스크 0(`:18`–`:19`) | `se2e_a3d.a3d_target` | 로컬 A1(0.5는 열림·0.5000001 닫힘 → e = k+14, 7프레임 구간의 1.75·3.5·5.25 분수 점, 비선형 궤적에서 내 보간과 오차 ≤ 1e-15), A2(k+30에서 변화 → e = k+30·3.0 s), A3(k+31 → 상한 k+30), A4(마지막 프레임 → 마스크 0·영), A5(끝 앞 프레임 → e = T−1), A6(k+1에서 바뀜); **파드 X4: 원본 parquet에서 내 독립 구현(자체 끝 규칙·`np.interp`)으로 8편(RB1 44·485·551·457, RB2 495·700·717·614) 312행 다시 계산 → 저장된 목표와 불일치 0, 최대 차 1.1e-16, 마스크 행 2** | 일치 |
| X6 | 손실 단위 m / 0.05, 마스크 smooth-L1, λ_aux 0.1, S-E2E 원래 aux 목표 마스크 0(`:20`) | `a3d_aux_vecs`, `se2e_trace_model.StageBTrace` | 로컬 A7(11 + 12, [0.0125, −0.05, 0.1] → [0.25, −1, 2], 마스크 점 0, 기본 마스크 0), A9; 파드 작은 판: aux 손실 > 0·기본 0(§6.1), 시험 묶음 `test_a3d_head_and_loss` | 일치 |
| X7 | 데이터 확인: FK(k + label_steps) − FK(k) = `ee_delta` ± 2e-5 m, 어기면 멈춤(`:21`) | `build_a3d.LABEL_TOL` | `a3d_stats.json` `label_check_max_m` RB1 5.0e-6·RB2 5.0e-6(≤ 2e-5), 행 25,433·17,380(= 42,813), 마스크 행 147·182; A8 목표 없는 표본 → KeyError | 일치 |
| X8 | 실행 경로 동일성 §4 (b)(c): 학습 보기 대 기본 보기 결정 항목 기록 비트 동일 | `base_view`, `--aux-view` | 파드 작은 a3d 판: `predict --aux-view trained` 대 `base` **항목 12개 비트 동일**, 요약은 `aux` 손실만 다름(0.787 대 0.0 — 기본 보기는 추가 출력 없음), `--extra-out` a3d_cm 점별 4개(학습 보기)·None(기본 보기), 청크 오차 같음; 시험 `test_base_view_decides_identically` 통과(파드) | 일치(실제 체크포인트는 S22) |
| X9 | 판정: 합동 ≥ +0.02 ∧ 부트스트랩 2.5 % > 0(엄격) ∧ 전이 ≥ −0.01, 상대 CMP_EPS 1e-12, 부트스트랩 10,000·시드 0·네 판 같은 추출(`:36`–`:39`) | `ma1b_verdict.py` | 로컬 V1(1,000스냅샷: 합동 **정확히 +0.02**·전이 **정확히 −0.01** → 채택), V2(+0.0198333 → c_point 거짓), V3(전이 −0.01333 → 거짓), **V4(효과가 80스냅샷 중 2개에만 → 합동 0.025인데 2.5 % 하한 정확히 0.0 → c_lower 거짓·불채택)**, V5(`_ge` 0.02−0.9e-12 참·−1.1e-12 거짓, −0.01 경계 같음), V6 상수, V7 모르는 판 이름 거부, V8 한 판에서 스냅샷 하나 빠짐 → 거부, **V9 내 독립 군집 부트스트랩 = 스크립트 값(세 층)**, V10 원천별 효과 보고 | 일치 |
| X10 | 도중 관문 (3): 판 하나 ≤ 75분(`:11`) | 파일 시각 | a3d_s1 18:06:56Z → `last/` 18:47:25Z = 40.5분 | 일치 |
| X11 | 하지 않는 것: `harvest/runtime`·프롬프트 해시 파일 무수정, GPU 2만(`:12`, `:51`) | diff, 파드 | H3·H4(블롭 불변), 19:13Z GPU 2에 E-MA1b 하나(PID 596013) | 일치 |

### 7.2 DOC (실험 절)
없음.

### 7.3 NOTE (실험 절)
- E-N1. `ma1b_verdict.py`는 등록 §5 "검증 전체 1,799에서만 판정"을 강제하지 않는다(`n_val_snapshots`를 출력만; 네 판 키 일치는 강제 — V8). 책 P25와 같은 성격 — 스냅샷 수 1,799·`val_keys_summary_sha` 확인 한 줄 권함.
- E-N2. `cmd_predict`의 `json.dump(…, open(a.extra_out, "w"))`는 파일 객체를 닫지 않는다(CPython 참조 계수로 즉시 닫힘, 옵트인).
- E-N3. 등록 §3 (2) 기준 재사용 비트 동일 검사(예측 `predfull_none_s*` 18:01·18:06Z)와 §4 (c) 실제 체크포인트 보기 검사는 예측 파일이라 열지 않았다 — 결과 문서가 커밋되면 파일 해시와 함께 다음 순회(S22).
- E-N4. `se2e_trace_model.extra_metrics`의 a3d 오차는 cm, 점 4개(p₂…p₅) — 등록 §5 "점별 평균·중앙값"과 맞음(작은 판에서 per_point_mean 4개 확인).

## 8. 다음 순회 전에 할 일 (제안)
1. **D-1(기준선)**: 책 `01-experiments.md:38`을 "6·16·20·22회차 PASS …"로 고치고 같은 커밋에 `06-updates.md` 한 줄. 책의 R7 이력 줄은 handoff §2.8에서 `grep`으로 뽑아 옮긴다.
2. (선택, NOTE) N47(정본 `:729`·`:730` 뒤 절 표시), N48(§85의 80 % 출처), N49(25회차 시각), N50–N55(책 출처·수치 정리 — `01:50`/`05:30` GPU 시간, `05:28` 미기록, `03:47` §72, `02:71` P48 출처, `02:12` ulog94 표기, `04:61` 분할 줄), N57(탐침 0절 꼬리표), E-N1.
3. **D: 여유 29 MB**(N62 ③) — 다른 작업이 D:를 채우는 중이면 먼저 정리할 것.
4. 27회차 대상은 3500f54 이후 HEAD, **연속 무결 0에서**: 탐침 결과·정본 §86·스펙 §17·탐침 코드 62시험(범위 나눔 다시 정할 것), E-MA1b 결과가 커밋되면 등록 §3 (2)·§4 (c) 파일 해시와 판정 재계산, 책 갱신 기록 규칙(갱신마다 같은 커밋). Git Bash kubectl은 `MSYS_NO_PATHCONV=1`, 책·문서는 작업 트리가 아니라 archive 사본에서 읽는다(N63).
