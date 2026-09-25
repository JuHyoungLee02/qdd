# R7 객관 검증 순회 — 18회차 (cycle 18, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle17.md` §5 표·결론에 기대지 않고 사전 등록 원문에서 대조표를 다시 만들고, 행마다 **구성한 입력 → 실제 함수·런타임 출력** 또는 **파드 원자료 재계산**으로 확인함). 작성 2026-09-25 15:05 UTC 무렵(로컬 시작 약 14:46 UTC, 파드 첫 명령 14:49:27 UTC, 파드 정리 끝 15:01:48 UTC). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 `7fe42c6`(`7fe42c63ac06…`, 커밋 시각 2026-09-25 14:46:13 UTC). `f91ad52..7fe42c6` = 문서만: `CLAUDE.md`(user-log 76 비용 한도 줄), `docs/design/00-interfaces.md` §82·보충, `docs/research/astra_role_2026-09-25.md`(새), `docs/user-log.md` 75–76, `docs/stage3/results/se2e_diag.md`(8절 + 17회차 D-1 정정), `r7_cycle16.md`·`r7_cycle17.md`, `handoff.md`·`draft-log.md`·`direction-log.md` 줄. `harvest/`·`tools/`·`tests/`·사전 등록(`prereg*.md`, `prereg.json`, `E-first`, `EVAL`, `M4`)은 `git diff --stat f91ad52 7fe42c6`에 **없음**(직접 확인; 코드·시험·사전 등록 바이트 동일). 검토 중 다른 세션이 `a13ad17`·`906c97d`·`e0d0816`(user-log 77)·`1079716`(`docs/research/steering_representation_2026-09-25.md`)을 커밋했다 — 범위 밖(`git diff --stat 7fe42c6 HEAD` = 그 두 파일뿐, D-1·D-2·D-3 위치는 건드리지 않음). `git -c safe.directory=D:/qdd -c core.autocrlf=false archive 7fe42c6`를 Python tarfile로 `D:\tools\scratch_qdd\r7c18\repo`에 풀어 검토했다(495파일). 파드 사본 = 같은 archive(`/data/harvest/tmp/r7c18/code`, 496파일 = + JSON `CODE_VERSION` `7fe42c63…`, dirty false); 파드 산출 `meta.git.commit` = `7fe42c63ac06…`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle7.md`–`r7_cycle17.md`, `r7c7_fixes.md`–`r7c15_fixes.md`, 정본 `00-interfaces.md` §1–§82(뒤 절 우선; [사용자] 제목 절은 그대로; 논문 .tex는 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`(§7 포함)·`prereg_se2e_temporal.md`·`M4-overlap-commit.md`.
- 분류(17회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·같은 문서의 뒤 결과와 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 기록이 없는 것. 정본이 "나중에 할 일"로 적은 것(§82 구현 포함)은 SCOPED. 이번 순회 지시에 따라 **§82와 어긋나는 설계·계획 서술(표시 없음)은 DOC**, 지금 있는 구현을 설명하는 서술은 해당 없음.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 시작 `git status` 깨끗). 로컬 임시 = `D:\tools\scratch_qdd\r7c18`(스크립트는 모두 Write 도구로 쓰고 경로로 실행; heredoc·`cat >`·`python -` 없음; 파드로는 `tar -cf - | kubectl exec -i … tar -xf -`, archive는 `tar -xf - < src.tar`, 정리 스크립트는 `bash -s < clean18.sh`). 로컬 pytest basetemp·TMP = `…\r7c18\pt`·`…\r7c18\tmp`, C: 쓰기 없음(하네스 작업 출력 파일만). 파드 = `/data/harvest/tmp/r7c18`(정리 전 399 MB). GPU: Isaac = GPU 1에 **내 프로세스 하나**(`--inst-prefix r7c18`, `IR_INST` `r7c18_standard`, `IR_ROOT=cyclo`, 기본 `r6` 접두사 안 씀; 그 시각 GPU 0·1에 R2_TRAIN `datagen.gen` Isaac 워커들, GPU 3에 E-TC 학습 — 건드리지 않음), GPU 학습 없음. CPU: 시작 전 파드 cgroup 5 s = 약 19코어 사용·스로틀 증가 0(쿼터 32) → `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`, 한 번에 한 묶음. 시드 DEV·POOL만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 `=dev`·`=test`만). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. `ckpt/se2e*`·`logs/se2e*`·`data/se2e_t`·`r2/train`·`r2/dev`는 **읽기만**.

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 3 |
| SCOPED | 19 |
| NOTE | 16 |

코드·시험·사전 등록은 16회차 대상(f91ad52)과 바이트가 같고, 모든 행동 확인이 통과했다: 로컬 **1006 passed / 15 skipped**, 파드 CPU **1122 passed / 4 skipped**, LeRobot 6 passed; 가드 **24건** rc 1; R2 DEV `validate_episode` **36/36**; 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 모두 완료·`prereg` OK; 새 시드 **DEV 7**에서 같은 Isaac 워커 C5 → C5' 행동 **1,592개 비트 동일**; 단계 B CPU 스모크. **17회차 D-1 정정은 맞다**: `se2e_diag.md` 요약(`:12`)·6절(`:125`)의 갱신 표시가 사전 등록 5절 표(`prereg_se2e_diag.md:49`)의 칸과 같고, 파드 로그에서 다시 계산한 8절 수치·판정(행 133–136)과 모순이 없다. **user-log.md 복원도 맞다**(925b0b0·9a0ae52의 바이트가 그대로 접두, 덧붙은 것은 75·76뿐, 줄 끝 LF 318줄·CR 0).

그러나 (1) **같은 정정 커밋이 `\r\r\n`을 다른 두 기록 파일에 새로 넣었다** — `draft-log.md:459-462`·`handoff.md:112-113`의 새 줄에서 `\n`·`\r\n`·`\r\r\n`을 가리키던 글자가 실제 제어 문자로 바뀌어 문장이 끊기고 사실이 빠졌으며, 그 외톨이 CR 때문에 git이 `draft-log.md`의 기존 284줄을 CRLF 그대로 블롭에 넣었다(`git diff` 288+/284−) → **DOC D-1**. (2) **정본 §82(14:38 UTC, a1bb055)가 `handoff.md`에 반영되지 않았다**: `:3`·`:5`·`:83`이 정본 범위를 "§1~§81"로 적고, `:84` "핵심 결정"이 여전히 "Astra = 위층 계획기 + 하트비트 5 s·단계 경계·사건(§45)" → **DOC D-2**(8·12회차 D-1과 같은 모양). (3) **설계 문서 `D25-planner-cadence.md`·`D28-m4-critic-measurement.md`가 5 s 하트비트·단계 경계 확인을 설계 기본으로 적고 §82 표시가 없다** → **DOC D-3**. 셋 다 문서만 고치면 되는 항목이다.

---

## 1. DEFECT

없음.

(검토한 후보와 판단: ① 런타임 기본 호출 주기는 여전히 K2·N = 5 s(`RuntimeConfig()` → `hb_mode` "K2"·`hb_N_s` 5.0, 내 파드 판 `meta.hb_mode` K2·`hb_n` 5)이고 `HeartbeatScheduler(mode="K5")`는 "cadence 'K5': ('K0', …, 'K4')"로 거부된다 — 정본 §82 "구현(다음): `astra_hb.py` K5 모드 … R7 관문 확인 뒤 착수"가 다음 일로 적었으므로 **SCOPED S19**(코드가 지금 있는 것을 하고 있고, §82가 구현 전 상태를 허용). ② Astra 시간 초과 뒤 재송신 모양(17회차 N4)은 코드 불변 — N4 유지, §82와의 관계는 N4에 적음.)

## 2. DOC

### D-1. 정정 커밋 7fe42c6이 `draft-log.md`·`handoff.md`에 `\r\r\n`을 새로 넣어 새 기록 줄이 깨지고, `draft-log.md` 블롭 284줄의 줄 끝이 바뀜
- 위치(7fe42c6 블롭, git 줄 번호): `docs/draft-log.md:459-462`, `docs/handoff.md:112-113`.
- 바이트(`crcheck.py`·`eolmap.py`): `draft-log.md` 새 줄 = "…이미 CRLF인 내용에 `\n`→`\r\n`을 또 적용해 user-log.md가 `\r\r\n`이 됐다." — 글자 `\n`·`\r\n`·`\r\r\n`이 **실제 제어 문자**로 들어가 한 줄이 4줄(459 LF / 460 "→" CRLF / 461 CRCRLF / 462 "이 됐다.")로 쪼개졌다. `handoff.md:112` "…docs/user-log.md 줄 끝이 `\r\r\n`이 됐다(내용 불변) — 복원."도 같은 모양으로 112(CRCRLF)·113으로 쪼개졌다. CommonMark에서 `\r`은 줄 끝이라 `\r\r\n`은 빈 줄 = 문단 끊김 → 렌더에서 "줄 끝이"로 목록 항목이 끝나고 "이 됐다(내용 불변) — 복원."이 목록 밖 문단이 된다. 즉 **사고 기록 문장이 무엇이 어떻게 바뀌었는지(줄 끝 값)를 더 이상 담지 않는다**.
- 부수 효과: 외톨이 CR이 있으면 git은 CRLF→LF 정규화를 하지 않으므로, 작업 트리에서 오래 CRLF였던 `draft-log.md` 1–284행이 이번에 **CRLF 그대로 블롭에 들어갔다**(9a0ae52·4eb988d 블롭 = LF 458줄·CR 0 → 7fe42c6 블롭 = CRLF 285줄·LF 176줄·CRCRLF 1줄). `git diff 9a0ae52 7fe42c6 -- docs/draft-log.md` = 288+/284−(공백 무시 비교로는 +4뿐) → 이 기록 파일 284행의 `blame`이 7fe42c6으로 바뀐다. 내용(LF로 풀어 비교)은 f91ad52·9a0ae52 블롭이 그대로 접두다.
- 어긋남: 이번 순회 확인 항목 "저장소 어디에도 `\r\r\n` 없음"이 **2파일에서 거짓**이고, 7fe42c6 커밋 메시지·`draft-log.md` 교훈 (2)·`handoff.md:112`가 "user-log.md 줄 끝 복원"을 적으면서 같은 커밋에서 같은 종류의 손상을 두 파일에 만들었다. 두 줄 모두 새로 추가된 현재 기록이며 정정 표시가 없다.
- 확인한 반대 사실(정상): `docs/user-log.md` 7fe42c6 블롭 = LF 318줄·CR 0; 925b0b0·9a0ae52 블롭 바이트가 그대로 접두(내용 변화 없음), 덧붙은 것은 75(9a0ae52 뒤)·76(925b0b0 뒤)뿐이고 LF로 푼 4eb988d와 같음. 저장소 전체(495파일)에서 CRCRLF·외톨이 CR이 있는 파일은 이 두 개뿐, CRLF·LF 섞인 파일은 `draft-log.md`뿐.
- 고칠 것(제안): 두 줄의 제어 문자를 글자(`` `\r\n` ``·`` `\r\r\n` `` 백틱 안 문자열)로 되돌리고, `draft-log.md` 블롭을 LF로(작업 트리 1–284행 CRLF 관행이 블롭에 들어가지 않게 — 외톨이 CR 0 확인) 되돌린다. 덧붙이기 스크립트는 쓰기 전에 문자열 안의 이스케이프를 해석하지 않는지, 쓴 뒤 `\r\r`·외톨이 `\r` 0인지 검사한다.

### D-2. `handoff.md`가 정본 §82를 반영하지 않음 — 정본 범위 "§1~§81"과 "핵심 결정: 하트비트 5 s·단계 경계"
- 위치: `docs/handoff.md:3` "(… 정본 §1~§81 …)", `:5` "> 현재 판본: 정본 `00-interfaces.md` **§1~§81**(뒤 절이 앞 절을 덮는다)", `:83` "`00-interfaces.md` §43부터 끝까지(지금 §81)", `:84` "**핵심 결정**: … / **Astra = 위층 계획기 + 하트비트 5 s·단계 경계·사건(§45)** / …".
- 정본: `00-interfaces.md:723` §82(2026-09-25 14:38 UTC, a1bb055 14:38:35 UTC, user-log 74·76 [사용자 결정 + Claude 설계]) "**강등(작은 모델·코드로)**: 5 s 하트비트(→ J5 저빈도 감사로 대체 …), 단계 경계 ack, K3 성공 판정·단계 전환 …", Astra 전용 일 J1–J6, `:732` 비용 한도 보충. 7fe42c6(14:46 UTC)은 handoff에 17회차 줄(`:112`)만 더했고 `grep "82\|astra_role\|E-Astra"` = handoff에 0건.
- 어긋남: `:5`·`:83`은 현재 시제("현재 판본", "지금")로 정본 끝을 §81로, `:84`는 새 세션이 가장 먼저 읽는 "핵심 결정"에 §82가 강등한 호출(5 s 하트비트·단계 경계)을 Astra의 역할로 적고 표시가 없다. 선례: 8회차 D-1·12회차 D-1(handoff 정본 범위 줄이 같은 커밋의 새 절을 빠뜨림 → DOC).
- 구분: 지금 코드의 기본이 K2·5 s라는 **구현 서술**(예: `r5_closed_loop.md:37`, `astra_role_2026-09-25.md:50` "K2(런타임 기본) 구현됨", `2026-09-25-e2e-ready.md:12`·`:26` 완료 정의 3의 실행 계층 설명)은 지금 있는 것을 말하므로 해당 없음. `:84`는 "결정" 목록이라 설계 서술이다.
- 고칠 것(제안): `:3`·`:5`·`:83`을 §82로, `:84`의 Astra 항목에 "→ **[갱신 §82]** Astra는 전용 일 J1–J6만, 5 s 하트비트·단계 경계 ack는 강등(J5 저빈도 감사), 구현은 R7 관문 뒤" 표시, §2.8 또는 §2.7에 §82·user-log 74–76 줄.

### D-3. 설계 문서 D25·D28이 5 s 하트비트·단계 경계 확인을 설계 기본으로 적고 §82 표시가 없음
- 위치: `docs/design/D25-planner-cadence.md:153` "| **T_hb 하트비트** (새 기본) | … 기본 **N = 5 s** …", `:154` "| **T_sub 단계 경계** (새 기본) | … `ack`/`patch`/`replace` …", `:142` "→ 지금 설계에 빠진 것은 Gemini의 (a) 주기 하트비트와 (b) 단계 경계 확인이다", `:188-189`(하트비트 채택·N 선택 규칙). `docs/design/D28-m4-critic-measurement.md:15` "(iv) Astra 성공 판정은 … **단계 경계(T_sub)·하트비트의 느린 감사**로만 둔다", `:75` "Astra는 단계 경계 확인(§45 T_sub)에만", `:137` "**Astra 성공 판정**: 정본 §45 T_sub(단계 경계)에서 '이 단계가 끝났나 + 다음 계약이 맞나'를 비동기로 묻는 데만".
- 정본 §82(`00-interfaces.md:726`): 5 s 하트비트·단계 경계 ack·K3 성공 판정·단계 전환을 작은 모델·코드로 강등, 주기 호출은 J5 저빈도 감사로. 두 문서는 단계 3 설계 문서(D25 = §45의 근거, D28 = §61·§64의 근거)로, handoff `:5`의 "단계 3 이전 판본은 옛 기록" 범위 밖이다. `grep "§82"` = 두 파일 0건.
- 어긋남: 설계 서술("새 기본", "…에만 둔다")이 §82와 어긋나고 표시가 없다. 정본의 앞 절(§45·§61·§64)은 "뒤 절이 앞 절을 덮는다" 규칙으로 해당 없음 — 설계 문서에는 그 규칙이 없어 선례(sweep6·15회차 D-1의 D28 표시)대로 표시가 필요하다. D28의 요지("Astra를 M4 (b) 측정에 쓰지 않는다")는 §82와 같은 방향이므로 표시는 "Astra가 단계 경계 확인을 한다"는 부분에만 필요하다.
- 고칠 것(제안): D25 `:153`·`:154`(표 셀 뒤)와 `:142`, D28 `:15`·`:75`·`:137`에 "→ **[갱신 정본 §82]** 5 s 하트비트·단계 경계 ack·성공 판정은 강등(작은 모델·코드), Astra 주기 호출은 J5 저빈도 감사; 구현은 다음 일" 표시.

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드에서 진행 중(읽기만: `datagen.gen … --seeds 10000-10599 --confirm-train`, standard·dr 워커, GPU 0·1); 확인 인자 없는 `gen gen --seeds 10007-10008` rc 1(가드 17).
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8(M9 복구·T_fail 뒤 하트비트 정지 — `pause_until`은 있으나 `core`가 부르지 않음, A5′ 검사·계약 편집, 확인 헤드 보정 파일 기본 미보정).
- S6. Astra 카나리 "none"(§67 보충).
- S7. S-E2E 계열 체크포인트의 런타임 형식 차이(§77 보충 (2), §80).
- S8. CONTRADICT-soft(§68 K6).
- S9. §73 D5 M4 설계 확장.
- S10. §73 N5 E1 범위.
- S11. §74 보충 E-M4-lat 비례 STALE_MAX.
- S12. §75 보충 (2) E-M4 판정 7.
- S13. §77 N8 (13): 완료 정의 밖 사전 등록 실험(E-M8 계열 포함) 등.
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — 7fe42c6에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. **E-TC 판정 아직 없음**(`prereg_se2e_temporal.md` §7; 이번 검토 대상 아님): 파드 읽기(14:58Z) — `video2_none`·`video2_motion` step 2000 평가 기록 있음, `single_motion` 학습 step 약 650, 판정 파일 없음.
- S19. **정본 §82 구현**(K5 모드·`harvest/astra/jobs.py`·`closed --upper`·T_nov·계약 캐시·J2 경로·`astra_slot.py`·Qwen3-VL-32B, E-Astra-necessity 사전 등록·유료 실행은 사용자 승인 뒤, 비용 한도 약 10만 원) — §82 "구현(다음) … R7 관문(연속 무결 2회) 확인 뒤 착수". 지금 코드: 기본 K2·N 5 s, K5 거부(etc18), 파드 판 Astra 2회/15.9 s(hb 1·sub 1).

## 4. NOTE
- N1. (17회차 N1 그대로) `stageb_train predict`·`evalck`는 체크포인트 `prompt_config`를 자기 옵션과 대조하지 않는다 — E-TC 결과 문서에 칸별 `prompt_config` 일치를 적기를 권함.
- N2. (17회차 N2 그대로) `cli_label.replay_max`의 NaN 순서 의존. 읽는 쪽 `replay_bit_identical`은 NaN·`-0.0`·문자열 "0"을 올바로 처리(내 D7 9경우).
- N3. (17회차 N3 그대로) `temporal_verdict.py` 입력 검사가 `assert`이고 등록 검증 집합(300·900항목)을 보지 않는다.
- N4. (17회차 N4 그대로 + §82와의 관계) Astra 시간 초과 뒤 재송신 모양(K1에서 하트비트 문구가 나감, K2에서 시간 초과된 경계 질문이 하트비트로 바뀜). §82는 하트비트·경계 ack를 강등하고 주기 호출을 J5 저빈도 감사(K5, 미구현)로 바꾸므로, 이 모양은 이제 E-M8c 기준선(K1·K2)과 **K5 설계** 둘 다에 걸린다 — K5 구현 때 "시간 초과된 호출은 같은 종류로 재송신"을 정해 정본에 적기를 권함.
- N5. `se2e_diag.md:131` 6절 "다음 사전 등록 제안 (a) D2′ — 같은 1,000개로 2,000스텝 … D2 불확정 해소"는 8절(N = 1,000 판, 2,000스텝)로 사실상 수행·해소됐고, `:49` 4절 읽기 "(3) 0.95까지 가는지는 스텝 2배 판이어야 알 수 있다"도 8.3(1.000)으로 답이 났다. `:12`·`:125` 갱신 표시가 D2 해소를 말하므로 독자가 오해할 여지는 작다(제안 목록·판정 밖 읽기라 NOTE). (a)에 "→ 8절로 수행" 한 줄 권함.
- N6. `se2e_diag.md:13` 판정 밖 읽기 "0.72는 입력 + 데이터 규모 쪽으로 기운다"는 8.2 뒤 "데이터 규모는 약 9k까지만" 제한이 붙는다(`:12`에 적힘). 모순은 아님.
- N7. `docs/research/astra_role_2026-09-25.md:349`·`:517` "J6 effort high(오프라인)는 [결정 필요]", `:39` "effort 높게" — user-log 76·정본 §82 "effort: low·high를 모두 가져가 비교 … 오프라인 일(J1 첫 컴파일, J6)과 E-Astra-necessity는 low·high 두 조건을 모두 측정"으로 사실상 답이 났다(오프라인 기본값 자체는 §82가 정하지 않음). 연구 문서의 제안 목록이라 NOTE; "→ §82: 두 조건 측정" 표시 권함. 같은 문서 `:11` "정본 §1–§81이 우선"은 작성 시점 서술(맞음).
- N8. `CLAUDE.md:32`(user-log 76 비용 한도 줄)가 "## 논문 초안" 절 끝(임시 파일 규칙 뒤)에 들어가 있다 — 원문·내용은 user-log 76과 같음(원문 "지금 10만원 정도는 비용 한도 책정이 가능해" 일치). 위치만 어색함.
- N9. 정본 §82 대 user-log 원문: J1·J2·J3·J4·J6 = user-log 76 질문의 "과제 컴파일·실패 진단/복구·검사 술어 합성·새 물체 이름·경험 증류", J5 = "주기 호출은 저빈도 진행 감사로", 선택 "바꾸기"; effort·유료 실행 시점·비용 한도 문장도 원문과 같다. §82의 근거 수치(V1h 0.949·0.44 ms = `e_m4b_meas.md:150`·`:198`/정본 §64, R5 `zs_hw` Astra 7회 전부 ack = `r5_closed_loop.md:12`, 첫 토큰 2.975 s·K3 스모크 1.88 s)는 출처와 같다.
- N10. (17회차 N10 그대로) `e05`는 `--out` 폴더를 가드 거부 전에 만든다 — 가드 21이 rc 1 "not in split dev … never opened"로 거부했지만 빈 `g21/` 폴더가 남음(열린 파일 없음).
- N11. (17회차 N11 그대로) 카나리 `--force` 같은 날 재실행이 그날 표류 파일을 덮는다.
- N12. 시험 수: 로컬 **1006 passed / 15 skipped**(134.7 s; torch 없음 10·inspect_robots 2·pyarrow 1·isaaclab 1·TODO(P3) 1), 파드 CPU **1122 passed / 4 skipped**(116.5 s, 14:52:13Z), LeRobot 6 passed(18.9 s). 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다. 내 구성 시험: `check18.py` 42/42, `verdict18.py` 7/7, `etc18.py` 8/8, 파드 `lr18.py` 30/30. `verdict18.py`의 새 경우 "V·M 동시 경계"는 처음 내 기대값을 잘못 만들었다(주효과를 한 칸 차이로 셈) — 사전 등록 `prereg_se2e_temporal.md:47`의 주효과 = 두 칸 평균으로 입력을 고치자 V·M 모두 채택(0.020000000000000018, p95 +10 %); 코드는 처음부터 등록식대로였다.
- N13. 단계 B 소형 CPU 스모크(14:56 UTC): 총손실 처음 5 평균 3.055 → 끝 5 2.903, eval fm 2.438 → 2.132·dec 0.787 → 0.655, `save_load` `max_abs_action_diff` 0.0·eval·정규화 같음.
- N14. 논문(NOTE만): `paper/sec/6_prelim.tex:56` "진단 D1--D3 판정 불가", `paper/mindmap/sec/4_experiments.tex:74` "종합 = 판정 불가"(17회차 D-1의 갱신 문장 미반영), `paper/sec/0_abstract.tex:2`·`1_intro.tex:12`·`:18`·`3_method.tex:10`·`:154` 등이 Astra 하트비트를 방법의 수단으로 적음(§82 미반영). 마지막 논문 커밋 ad4f7b0(13:47Z) 뒤 4시간 주기(user-log 73) 안이라 늦은 것은 아님 — 반영 때 두 가지를 같이.
- N15. 정본 범위 서술 중 연구 문서의 작성 시점 표기(`astra_role_2026-09-25.md:11` §1–§81, `:497` "새 절 제안, 예: §82")는 날짜 붙은 기록이라 해당 없음.
- N16. E-TC 참고(범위 밖, 읽기만): `ckpt/se2e_temporal/{video2_none,video2_motion}` step 2000 검증 dec_acc 0.6956·0.7211(dec 0.7273·0.7225), `single_motion` 진행 중 — 판정은 네 칸·지연 측정 뒤(S18). N1·N3를 결과 문서에 적기를 다시 권함.

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**, 파드 산출 `meta.prereg.check` = "OK"(e05·e05o·rd·calib·closed). 사전 등록·정본(§1–§81)·코드는 `f91ad52..7fe42c6`에서 바뀌지 않았다(`git diff --stat`에 없음; 정본은 §82 덧붙임만). 코드 줄은 `7fe42c6` 기준(= 9a0ae52와 같은 줄). "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c18\check18.py`(42/42), `verdict18.py`(7/7), `etc18.py`(8/8); **파드** = §6(`pod_cpu18.sh`, `pod_eval18.sh`, `data18.py`, `lr18.py`, `canary18.py`, `stagea18.py`, `scale18.py`, `se2ev18.py`, `trust18.py`, `pod_isaac18.sh`, `closed18.py`, `meta18.py`·`meta18b.py`). "시험 묶음" = 해당 구현을 부르는 저장소 시험이 로컬 1006·파드 1122 묶음에서 통과. 굵게 = 이번에 처음 대조하거나 근거가 바뀐 행.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 (E :113-120, §66), R2_TRAIN 10000–59999 (§66) | `eval/splits.py:13-14,19-42`, `datagen/gen.py:35-50` | 로컬 경계 20값(−1·0·29/30·499/500·549/550·999/1000·1149/1150·1299/1300·1329/1330·1999/2000·2119/2120) → 기대 분할(A1), 보호 분할 변수 없음·다른 값 거부·같은 값 통과(A2–A4·A7), DEV 29,30·POOL 2120 거부(A5·A6), **R2 시드 가드 9경우**(0·29 확인 없이 허용, 10000·59999 확인 있어야 허용, 9999·60000·500·1149 거부, A8); 파드 가드 24건 rc 1(§6.4) | 일치 |
| 2 | POOL 120 × 10, 경계 30 % 과표집 (E :121, §76 D-2) | `sim/snapshot.py:102-136` | 시험 묶음; 파드 실제 풀 결정 스냅샷 1,200개·시드 2000–2119 120개(`stagea18`) | 일치(주석 S14) |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` | 시험 묶음 | 일치 |
| 4 | 분할 = 에피소드 (E :122) | `stagea_data.split_of:151-157`, `calib.halves` | 파드 실제 풀 단계 A 항목 train 3,000·val 3,000; calib `CALIB_DONE` | 일치 |
| 5 | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py:26-38` | 시험 묶음; 파드 Isaac DEV 7 C5·C5' 성공 1.0, 15.92 s | 일치 |
| 6 | 호출 기록: 질문별 확률·요청/응답 원문(E :125), Astra A6(E :126, §28) | `core.py:279-322,395-426` | **파드 DEV 7 C5·C5' 결정 호출 96행**: `sha256(request_blob)` = `request_sha256` 96/96, 이미지 해시가 요청 본문에 96/96, 응답 blob 해시 96/96, `probs` 질문 = `answers` 질문·합 1 96/96; Astra 4행: 요청 해시·머리캠 JPEG 해시·effort low·600·`output_text` 4/4 | 일치 |
| 7 | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `analysis/stats.py:4,32` | 로컬 `N_BOOT` 10000(E1); 파드 closed·e05·e05o·rd `meta.bootstrap` n_boot 10000·seed 0·percentile·단위 기록 | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate` | 파드 C5 대 C5' 같은 워커(행 99) | 일치 |
| 9–12 | 판정 2 Holm, 판정 10, 카나리 Holm, 판정 절 해시 (E :131, :265, :139, :133) | `e05`, `canary.py`, `eval/common.py` | 시험 묶음; 파드 `meta.prereg` 해시 5절 OK | 일치 |
| 13, 85 | 카나리 기준일 = 같은 세트 × 같은 `question_id@vN` 집합의 첫날 (E :136-140, §79 D2) | `eval/canary.py:168-175,188-252` | 로컬 F1; **파드 카나리 끝까지(모의)**: 세트 재생성 rc 1, 같은 날 재실행 rc 1·`--force` rc 0, 전날 같은 세트·qid → `baseline` = 전날·`drift_suspect` false, qid 바뀜 → `baseline` null, 9/23·9/24 → 이른 9/23 | 일치(N11) |
| 14 | 모델 식별 필드가 바뀌어도 같은 처리 (E :139) | `Calibration.load` | 시험 묶음 | 일치 |
| 15–17 | E0.5 표·재시험·같은 시각 K = 3 (E :236-238) | `e05.vote_steps`, `e05.py` | 시험 묶음; 파드 `e05 --data jsel_dev/P0,P2 --split dev --episodes 3` → `E05_DONE` | 일치 |
| 18 | γ 2/3 (E :240, M4 :276) | `m4.share_at_least:72-77`, `GAMMA` `:46` | 로컬 B1·B2·B4(0.67 소수 = 정확값 → (2,3) 거짓) | 일치 |
| 19–20 | `C_flip` 두 식, A0–A4·층 (E :242, :246) | `e05.py` | 시험 묶음 | 정본 기록(§73) / 일치 |
| 21–28 | 판정 1–10 경계 (E :256-265) | `replay.judge_e05`, `e05.py` | 시험 묶음; 파드 `E05_DONE` | 일치 |
| 29, 89 | FLIP_TH 후보 α 0.01·범위 (E :253, :487; M4 :285) | `e05.py:437-446` | 시험 묶음 | 일치 |
| 30 | 같은 시각 뒤집힘 성공·섭동 따로 (E :253, §27) | `e05.py:352-383` | 시험 묶음 | 일치 |
| 31–33 | d_p95 = E0 값, 분당 400 [가정], E1 반분 | `e05 --d-p95`, `calib.halves` | — | 정본 기록 |
| 34–35 | ECE 15 동일 질량, 오답 < 30 판정 불가 (E :320) | `calibration.py` | 시험 묶음 | 일치 |
| 36 | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat:59-64` | 로컬 n 99·α 0.01 → 99, n 98 → inf, n 19·α 0.05 → 19, **n 20·α 0.05 → 20**(E2) | 일치 |
| 37–43 | log p 자름·질문별 온도·원 확률·판정 1·7·8·`ambiguous` ECE 제외 (E :333-346) | `calibration.py`, `core.py:362-393` | 시험 묶음; 파드 `CALIB_DONE` | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| 45 | N_max = ⌈d̂/T_c⌉+1 (M4 :258) | `m4.py:178-182` | 시험 묶음 | 일치 |
| 46–49 | γ·W·비가역 W+1·τ | `m4.py` | 시험 묶음 | 일치 |
| 50 | conformal α 0.01·w 5 ((b) 경계) | 확인 헤드 보정 파일 | 기본 미보정 | SCOPED S5 |
| 51 | STALE_MAX 1.5 s (E :487) | `m4.older_than:56-58`, `M4Params.stale_max:88` | 로컬 B3·B5 | 일치 |
| 52–53 | C2 = VLM Stream, C0–C6 설정 (M4 :329-345) | `conditions.py`, `m4.py:220-226` | 파드 `--conditions C9` "refused before any worker"(가드 13) | 일치 |
| 54 | C5 = §4.2 전체, C5' = (b) 범주 뺌(줄은 none), 판정 3 (M4 :155, :232, :340-342, :361; §77 보충 (3)) | `core.b_line`, `core._boundary:527-578` | **파드 Isaac DEV 7**: C5 `last_step` {none 1, OK 31, DEVIATE 13, LAG 3}, C5' none 48/48, 요청 마지막 `last_step:` 줄 = 행 값 96/96 | 일치 |
| 55 | H 1과 3 (정본 §2, M4 :188-189) | `m4.early_ask_steps:61` | 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 |
| 56–58 | n_LA 2·조기 호출 당겨 씀·FLIP_TH 끔 | `m4.py`, `core.py:455-503` | 시험 묶음 | 일치 |
| 59 | 경계 직후 W 2·γ 1.0 등 | 없음 | §73 D5 | SCOPED S9 |
| 60 | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.select_rule:131-142` | 로컬 E3 | 일치 |
| 61–62 | 폐루프 RD 재표집 = layout 짝, 주 RD = Score (EVAL :182-184) | `closed.py`, `rd.py` | 파드 `rd --variants standard=jsel_dev,random=gen_dev/random/P0 --episodes 2` → `RD_DONE`, 단위 "(kind, layout seed) … paired" | 일치 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | §71 보충 | SCOPED S1 |
| 64–65 | M4b 2,000회, E-M4-lat 비례 STALE_MAX | `m4b/*` / 없음 | §72 예외 / §74 보충 | 일치 / SCOPED S11 |
| 66–67 | H = 1 창·`lead_max` 유한 양수 (§75, §76 N4) | `m4.py:106-113`, `closed.py:160-166` | 파드 `--m4-lead-max nan` 거부(가드 14) | 일치 |
| 68 | E0 판정 4 | `analysis/latency.py` | 시험 묶음 | 일치 |
| 69 | E-M4 판정 7 | 없음 | §75 보충 (2) | SCOPED S12 |
| 70 | FROZEN = 송신 시각 기준 (M4 :150) | `m4.py:228` | §77 N3 | 정본 기록 |
| 71, 93 | 카나리 표류 → J5 끔, 재보정 뒤 재사용, 다음 날 깨끗한 카나리로는 안 켜짐 (E :139, :347, §77 N6, §79 D3) | `closed.j5_after_canary:169-185`, `canary.latest_canary:149-165` | **파드(실제 CLI + 실제 함수)**: 전날 답을 모두 바꿈 → 오늘 `drift_suspect` true; 보정 오늘 → (0.1, None), 전날 → (None, "J5 off: … drift suspect … before it"); 표류를 9/24로 옮기고 오늘 깨끗한 카나리 → `last_drift` 9/24 유지, 보정 9/23 → 꺼짐, 9/25 → 켜짐; α None → (None, None) | 일치(N11) |
| 72–76 | 응답 모델 필드·재시도 기록, E0.5 정답, `fine_dir`, Astra 카나리 | `models`, `common` | §77 N4·N5, §67 보충; 파드 폐루프 결정 호출 `canary_id` = 최신 모의 카나리 `cn20260925_mock_c203fb` 96/96 | 일치 / SCOPED S13·S6 |
| 77–79 | (b) 범주 줄·런타임 값·경계 틱 호출 = 방금 끝난 스텝 (M4 :232, §77, §79 N1) | `core.b_line`, `core.act:429-515` | 행 54; 시험 묶음 | 일치 |
| 80–84 | 학습 자료 값·학습 항목 상태·C5' none·ser-A-min-2·옛 체크포인트 거부 (§77 (iv), §77 보충 (1)) | `deccall_snap.py:31-75,78-105`, `stagea_data.build_items:160-190`, `serialize.with_last_step:12-15` | 로컬 D1–D6; **파드 실제 풀**: `load_pool(labels_v2)` 6,000항목(5질문 × 1,200), 목표 1개씩(0건 예외), `last_step` {OK 5,775, none 220, CONTRADICT 5}; §77 보충 수치: R2 DEV 결정 스냅샷 **1,081** 중 DEVIATE **21**·CONTRADICT **0**, POOL 1,200 중 CONTRADICT **1** = 정본 그대로 | 일치 |
| 86–88 | 결정 호출 행 `probs`·blob·`last_step`, Astra 원응답, 결정 이미지는 해시만 | `core.py`, `reqhash.request_body` | 행 6 | 일치 / 정본 기록 |
| 90 | FLIP_TH = 성공 실행 flip_score의 1−α 분위, 질문별 (M4 :287, §79 D1) | `e05.flip_th_conformal:271-281` | 시험 묶음 | 일치 |
| 91–92 | 같은 시각 뒤집힘 성공·섭동, 층별 A0 대비 flip | `e05.py` | 시험 묶음 | 일치 |
| 94 | E0 판정 4 집계 (§77 N7) | `latency.step_votes:93`, `judgment4:108` | 시험 묶음 | 일치 |
| 95–97, 105, 115–117, 119 | S-E2E 설정·판정 (a)–(e)·재개·evalck·판정 스크립트 입력 검사·고정본 (`prereg_se2e.md` §3·§4, §77 보충 2, §80 N1) | `tools/se2e/se2e_verdict.py` | **파드: 7fe42c6 사본의 판정 스크립트를 실제 S-E2E 로그(읽기 전용)에 다시 돌림**(`se2ev18.py`) → rc 0, 키 125개가 기록 `verdict_v2.json`과 **차이 0**, 두 시드 (a)(b)(c)(e) pass; `ckpt/se2e/prereg_se2e.md` sha256 `29191168e48d2a13` = 사본 블롭 | 일치 |
| 98 | 라벨 복원 기준(비트 동일, §78 (1)) | `stagea_data.replay_bit_identical:49-53` | 로컬 9경우(0·0.0·−0.0 참; 1e-12·None·없음·NaN·False·"0" 거짓, D7) | 일치(N2) |
| 99 | 에피소드마다 PhysX 장면 재생성, 모든 호출자 기본 (§78 결정) | `sim/scene.py:418-425,529-532,621-633` | **파드 Isaac 한 워커 C5 → C5'(DEV 7, 모의 선택기)**: 행동 **1,592개 비트 동일**(첫 차이 없음), 호출 48개·Astra 2개 같은 수, `code_sha` `9242f67e59a09ee4` | 일치(행렬 S16) |
| 100, 118, 132 | 라벨 신뢰 = 재생 비트 동일, 필드 없음·null·NaN 행 제외, 뺀 수와 질문 범위 기록 (§78 (1), §80 D1, §81 N3) | `eval/common.load_truth:378-412` | **파드 `e05 --split pool --seeds 2003,2011,2001 --truth outcome:plan`** → rc 0, `meta.truth_label_trust` = {plan, kept **150**, excluded **0**, questions 5개}; 독립 계수(`trust18.py`): 이 세 시드 라벨 행 `replay_maxabs` 모두 0(57·56·56), 17회차 시드 2002는 비0 17행(= 17회차 제외 17) → 제외 수가 원자료와 맞음 | 일치 |
| 101 | R2_TRAIN은 하드 리셋 빌드, 옛 녹화 처리 보류 (§78 (2)(3)) | 파드 실행(읽기만) | 도는 `datagen.gen gen --out r2/train --seeds 10000-10599 --confirm-train`(standard·dr, GPU 0·1) | 일치 / SCOPED S17 |
| 102, 120 | 빈 입력·0편 선택 거부, `determinism` 시드 검사가 `--out` 앞 (§79 N5, §80 N3) | `eval/common.load_episodes:340-369`, `sim/determinism.py:194-201` | 가드 19·20 rc 1·폴더 없음, `canary build-set --seeds 500-502` → "no episode selected" rc 1(가드 22) | 일치(e05 폴더 N10) |
| 103 | Isaac 워커 `OMP_WAIT_POLICY=PASSIVE` (§79) | `closed.worker_cmd:188-199` | 내 Isaac 워커가 이 명령으로 돌아 `CLOSED_DONE`; `--isaac-gpu 3`·**`--isaac-gpu 2`** rc 1(가드 12·23) | 일치 |
| 104 | e05 qid 등록부 기본 = `<out>` (§79) | `e05.py:680` | 시험 묶음 | 일치 |
| 106–113 | S-E2E 진단 D1–D3 (`prereg_se2e_diag.md` §1–§4) | 파드 고정 사본 | **파드 로그 재적용(`scale18.py`)**: D1 step 0 `dec` 0.6777731279791623(A 4686과 차 2.8e-8 < 1e-3), step 1200 `dec` 0.73753 > 0.643884 → "이 lr에서 계산 한계 아님"; D2 step 1000 학습 0.88533·검증 0.5600 → "불확정" = 문서 `:8-9`; D3는 15회차 재계산(0.344) 그대로 | 일치 |
| 114 | §7.1 설정: 네 판 2,000스텝·묶음 8·lr 1e-4/1e-4·코사인·시드 0, 같은 검증 300, 500마다 평가, 부분집합 1,000·25 %·50 %·100 %, 학습 부분집합 평가, GPU 배정 | 파드 판 로그 `config` | 네 판 `max_steps` 2000·batch 8·lr·lr_heads 1e-4·`lr_schedule` cosine·seed 0·`val_per_kind` 150·`val_seed` 0·`eval_every` 500; N 1,000 = `train_subset` 500·`eval_train` 1,000개, 9,371 = `train_fraction` 0.25·`eval_train_per_kind` 500, 18,742 = 0.5, 37,484 = 없음; 스텝 시간 중앙값 네 판 1.00 s; 첫/끝 학습 기록 12:39–13:20Z(1,000·9,371), 13:24–13:59Z(18,742·37,484) | 일치 |
| 133 | §7.2 주 지표·적합·확인/포화 규칙·외삽 | 문서 `se2e_diag.md:148-165` | **파드 로그 독립 계산**: acc@2000 = 0.552222 / 0.682222 / 0.685556 / 0.683333, dec = 5.34203 / 0.79566 / 0.76804 / 0.77350; 적합 a 0.2944·b 0.0901(NLL 14.276·−3.124); Δ25 +0.00111, Δ50 −0.00222 → 확인 거짓·포화 참 → "약함 + 포화" = 문서; N\* 134,460(문서 ≈ 134,000); **8.1 표 20칸 모두 일치**(37,484 NLL 0.773 정정 확인), 학습 부분집합 곡선 10값 일치 | 일치 |
| 134 | §7.3 D2 해소(3절 규칙, 스케줄 다름 적기) | 문서 `se2e_diag.md:166-169` | N = 1,000 step 2000 학습 1.000(NLL 3.5e-5)·검증 0.5522 → "학습 가능·간극" = 문서; 스케줄 차이 문장 `:168` | 일치 |
| 135 | §7.4 처리량 보고 | 문서 `:176-180` | 스텝 시간 중앙값 1.00 s = 문서; GPU 창 표시(`:179` "실제 표본 창 시작은 약 12:37–12:38Z")가 17회차 N7 정정으로 붙음 | 일치 |
| **136** | **§5 종합 읽기 표: 칸은 D1·D2·D3 판정으로 정함 (`prereg_se2e_diag.md:45-54`), §7 목적 "D2를 원래 규칙으로 해소" (`:62`)** | 문서 `se2e_diag.md:12`, `:125` | 17회차 D-1 정정 확인: 두 곳 모두 "[갱신 … R7 17회차 D-1]" 표시로 칸 = "D1 아님 × D2 일반화 간극 × D3 아님 → 데이터 규모 한계 → 데이터 늘리기" = `:49`, 8.2(약함 + 포화)와의 관계("1k→9k +0.13만 듣고 9k→37k +0.001") = 로그 재계산(0.130·0.00111); 요약 `:14`·8.3 `:167-169`와 모순 없음 | **일치**(남은 제안 목록 N5·N6) |
| 121 | E-TC 옵션 끔 = 기준 표본, 기본 경로·프롬프트 해시 파일 무수정 (`prereg_se2e_temporal.md` §7, §8) | `se2e_temporal.load_se2e_t:123-130`, `stageb_train._load_data` | 코드 불변; 파드 시험 `test_stageb_train_defaults_unchanged_and_variant_config` 통과 | 일치 |
| 122 | V = video2: [t−0.3 s, t], 10 Hz에서 k−3(0으로 자름) (§2) | `se2e_temporal.prev_index:46-47` | 로컬 k 0·1·2·3·4·100 → 0·0·0·0·1·97, `DELTA_S` 0.3 | 일치 |
| 123 | M = 움직임 줄: 인과 후방 차분, 팔 3분위 0.2179·0.6070, 그리퍼 0.1755 (§3) | `se2e_temporal.backward_velocity:50-53`·`motion_line:86-92` | 로컬 후방 차분 [0, 10, 20, 30], 경계 8경우(0.2178999 still·0.2179 slow·0.6069999 slow·0.6070 fast, ±0.1755 still, ±0.17550001 opening/closing) | 일치 |
| 124 | 드롭아웃 p = 0.3, 난수 (시드, 스텝) 따로 (§3) | `se2e_temporal.motion_dropout:95-109` | 로컬 12,000표본 비율 0.29992, 전역 `random` 상태 불변, 결정적, p = 0 항등 | 일치 |
| 125 | 새 판 표지·`prompt_config` → 기본 체크포인트와 섞이지 않음 (§7) | `stageb_train.prompt_config_t:83-96`, `fused_model.check_prompt:319-344` | 시험 묶음 | 일치(N1) |
| 126 | 지표·층: 검증 300 × 3질문 = 900항목, 전이 층 (§4) | `temporal_verdict.metrics:48-60` | 로컬 구성 판정이 전이 층·전체를 따로 셈(행 127) | 일치 |
| 127 | 채택 규칙: 주효과(두 칸 평균, `:47`) ≥ +0.02 ∧ 전이 ≥ −0.01 ∧ FULL p95 증가 ≤ 10 %, CMP_EPS 1e-12 (§6) | `tools/se2e/temporal_verdict.py:24-34,119-128` | 로컬 `verdict18.py` 7/7: +18/900·−6/600·p95 +10 % → V 채택, +17/900 거짓, 전이 −7/600 거짓, p95 0.3300001/0.30 거짓, M 경계 채택(V 지연 50 s 무관), (s, motion) 0.331 거짓, **V·M 동시 경계(두 칸 평균 +18/900, 전이 0, p95 +10 %) → 둘 다 채택** | 일치(N3, N12) |
| 128–129 | 판정 스크립트·등록 코드 해시, 등록은 학습 전, 실행 순서, 지연 측정 (§5–§7) | 파드 E-TC 판 | 코드 불변(16·17회차 확인), 판정 전 | 일치 / SCOPED S18 |
| 130–131 | §81 N2 재개 검사 키, §81 N10 라벨 쓰기 null | `stageb_train.py:267-293`, `cli_label.replay_max:37-43` | 파드 시험 `test_r7c15_resume_keys.py`·`test_r7c15_label_write.py` 통과 | 일치(N2) |
| 137 | Astra 호출 주기 = 하트비트(응답 + N, N = 5 s) + 단계 경계 + 사건, in-flight 1, 15 s → 재송신, ack epoch 불변·patch/replace +1, gpt-6-astra·low (§45) | `runtime/astra_hb.py:33,81-140`, `core.py:242-276,395-426,461-477` | 로컬 C0–C16(스케줄러 경계·가짜 세계 런타임: 간격 = 직전 응답 + 2.0 s, epoch [ack None, patch 1, replace 2, …]); 파드 판 Astra 2회/15.9 s(hb 1·sub 1) | 일치(N4) |
| **140** | **정본 §82: 강등(5 s 하트비트·단계 경계 ack·K3), J1–J6, K5 모드 등은 "구현(다음)·R7 관문 뒤"** | 없음(현 구현 = §45 K0–K4) | 로컬 `RuntimeConfig()` 기본 K2·5.0(C0), `HeartbeatScheduler(mode="K5"|"J5")` 거부·K0–K4 수락(etc18) → 코드는 §82 이전 상태 그대로이고 §82가 그것을 다음 일로 둠 | SCOPED S19 |
| 138 | LeRobot v2.1 내보내기 = ROBOTIS 형식(§63), 30 Hz·원본 해상도·관절 행동(§66) | `datagen/lerobot_export.py:28-80,134-185,192-251` | **파드 끝까지(새 3편)**: standard/mug_marker ep3, dr/bottle_tray ep4, standard/mug_tray ep2 `export` → 3편·915프레임, `verify` 오류 0·PSNR 최소 35.06 dB·lerobot 0.3.3 `LeRobotDataset` 915프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·action0 같음; `lr18.py` 30/30(ROBOTIS `Task_0001…/meta/info.json`과 `codebase_version` v2.1·경로 틀·표준 열 같음, state = [q, 폭]·action = npz 비트 같음, timestamp = k/30·sim_time 차 ≤ 3.33 ms, decision 깃발 = 원본, `next.done` 마지막 한 칸) | 일치 |
| 139 | R2 DEV 구조 검사(§66, 완료 정의 1) | `datagen/validate.py:38-` | 파드 `/data/harvest/r2/dev/*/*/P0` 전 편 **36/36 오류 없음**(6폴더 × 6), `valid_for_training` 메타 불일치 0 | 일치 |

### 5.1 17회차 표와의 차이
- 행 136: 17회차 DOC D-1 → 정정 확인으로 "일치".
- 새 행 140: 정본 §82(SCOPED S19).
- 행 1(가드 A7·A8·가드 23·24), 6·54·99(새 시드 DEV 7), 100(새 시드 3개 + 원자료 독립 계수), 127(V·M 동시 경계), 138(새 3편)으로 근거 교체·추가.

## 6. 확인한 것 (근거)

### 6.1 17회차 D-1 정정과 user-log 복원 (과제 2)
- `git diff 9a0ae52 7fe42c6 -- docs/stage3/results/se2e_diag.md`: `:12`·`:125`에 "[갱신 2026-09-25 14:46 UTC, R7 17회차 D-1]" 문장 추가, `:155` 0.774 → 0.773, `:179` 창 시각 표시, `:182` N5·N6 정정 줄. 문장 내용은 파드 재계산(행 133–136)과 같다. 요약(`:12`·`:14`), 6절(`:125`), 8절(`:159-169`) 사이 모순 없음(N5·N6은 남은 제안·판정 밖 읽기).
- `docs/user-log.md`: 925b0b0 블롭(28,358바이트)·9a0ae52 블롭(27,433바이트)이 7fe42c6 블롭(29,112바이트)의 바이트 접두, 덧붙은 텍스트 = 75(9a0ae52 뒤)·76(925b0b0 뒤), 4eb988d(`\r\r\n` 316줄)를 LF로 풀면 7fe42c6과 같음 → 내용 변화 없음, 줄 끝 LF 318·CR 0. **다만 `\r\r\n`은 `draft-log.md`·`handoff.md`로 옮겨 감 → D-1.**

### 6.2 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외)
- §82 대상 어휘(`하트비트|heartbeat|T_hb|T_sub|K2-N|H-cadence|5 s 주기|주기 호출|단계 경계 확인|성공 판정`) 전수: 정본 앞 절(§45 `:408-416`, §46 `:421-422`, §61·§64 `:528`·`:530`, §67 `:569`)은 뒤 절 우선 규칙으로 해당 없음. 구현·결과 서술(`r5_closed_loop.md`, `r6_eval.md`, `pre_r7_fixes.md`, `e3st.md:255`, 코드·시험, `astra_role:50`, 계획서 완료 정의 `:12`·`:26`)은 지금 있는 것을 말함. **설계·결정 서술로 §82와 어긋나고 표시 없는 곳 = `handoff.md:84`(D-2), `D25:142,153-154,188-189`·`D28:15,75,137`(D-3)**. 단계 2 이전 문서(`SUMMARY.md`, `STAGE2-CLOSE.md`, `M8`, `D10b`, `plan.md`, 연구 v2·v3)의 "T1 주기" 등은 handoff `:5`가 "옛 기록"으로 둔 범위이거나 비교 조건 서술. `CLAUDE.md:52`는 [사용자] 줄(그대로). 논문 = N14.
- 정본 범위: `handoff.md:3`·`:5`·`:83` = §81(**D-2**); 정본 끝 = §82(`:723`).
- se2e_diag "판정 불가"를 현재 상태로 쓰는 곳: 문서 안은 갱신 표시가 붙음; 논문 `6_prelim.tex:56`·마인드맵 `4_experiments.tex:74`(N14); `draft-log.md:454`는 시각 붙은 기록.
- §72–§81 사실: `f91ad52..7fe42c6`에서 바뀐 파일(위 목록)에 새로 어긋나는 서술 없음; §82·`astra_role` 문서의 인용 수치는 출처와 같음(N9).

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st` + 코드 사본으로 R2 DEV 전 편 `validate_episode` **36/36**; LeRobot 시험 6 passed; 내보내기·되읽기·lerobot 적재 끝까지(행 138). |
| 2 모델 | 충족(CPU) | GPU 없음 → CUDA 시험·GPU 재적재 건너뜀. 파드 CPU 스모크(N13), CPU 묶음의 `test_stageb_torch.py`·`test_r7c15_resume_keys.py`·`test_se2e_temporal_qwen.py` 통과. |
| 3 폐루프 | 충족 | Isaac 한 워커(`closed --model mock --split dev --seeds 7 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c18`, 14:57:11–15:01:09 UTC, `IR_INST` `r7c18_standard`): `CLOSED_DONE` C5·C5' 성공 1.0, 15.92 s, 호출 48·오류 0, 행 필드·blob 확인(행 6), `meta.bootstrap` 10000, `prereg` OK, git `7fe42c63`, `code_sha` `9242f67e59a09ee4`, 하드 리셋 빌드 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 14:54 UTC): `e05` → `E05_DONE`, `rd` → `RD_DONE`, `calib` → `CALIB_DONE`, `e05 --split pool --truth outcome:plan`(행 100) → `E05_DONE`. 모두 prereg OK·git `7fe42c63`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·카나리·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`truth_label_trust`(+ `questions`); 정리 뒤 흔적 없음(§6.6). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`, 14:53:57–14:54:04 UTC)
- 1–22: 17회차와 같은 명령(e05·calib·rd·closed의 cal/test/test_p5 → "refused: set HARVEST_ALLOW_SPLIT=X (main session only …)", DEV 29,30·POOL 2120 → "not in split … never opened", `--isaac-gpu 3` → "GPU 2 never renders" 계열, `--conditions C9`·`--m4-lead-max nan` → "refused before any worker", 다른 값의 `HARVEST_ALLOW_SPLIT` 2건, `gen` 확인 인자 없음·`--seeds 500 --confirm-train`, `determinism` 2건, `e05 --data pool --split dev`, `canary build-set --seeds 500-502` → "no episode selected"). 새로 23 `closed --isaac-gpu 2` → 거부, 24 `gen gen --seeds 60000 --confirm-train` → 거부. **24건 모두 rc 1**; 출력 폴더는 21번(e05)의 빈 폴더 하나(N10), 나머지 0.

### 6.5 A. 테스트
- 로컬(`…\r7c18\repo` = 7fe42c6 archive, `python -m pytest -q -rs -p no:cacheprovider -o addopts="" --basetemp=D:/tools/scratch_qdd/r7c18/pt`): EXIT 0, **1006 passed · 15 skipped**.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, TMPDIR·pyc·카나리·qid 등록부 = scratch): **1122 passed, 4 skipped**, EXIT 0(14:52:13Z).
- 파드 LeRobot(`venv_e3st` + `r2/pylib_lerobot`·`pylib_pytest`): **6 passed**.

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(시작 `git status` 깨끗). 로컬 C:에 이 검토의 산출물 없음(하네스 작업 출력 파일만).
- 파드 정리(`clean18.sh`, 경로를 하나씩 적은 스크립트, 15:01:48 UTC): `tmp/r7c18`(399 MB), 내 Isaac 판이 만든 `tmp/carb.zJmu6c`(14:57:12Z)·`tmp/tmpy5ixrlvp`(14:57:30Z)·`cache/pyc_r6/data/harvest/tmp/tmpy5ixrlvp`·`cache/pyc_r6/data/harvest/tmp/r7c18`, `ir/kitcache/cyclo-r7c18_standard`(208 MB). 판별: Isaac 앞뒤 `tmp`·`pyc_r6`·`kitcache` 목록 차이(새 항목은 이것뿐), 생성 시각이 내 Isaac 창(14:57:11–15:01:09Z) 안, `/proc/*/fd` 전수에서 여는 프로세스 없음. 끝에 `tmp`·`kitcache`의 r7c18 항목 0, 내 프로세스 0(확인 명령의 grep 1건은 자기 매칭).
- 절차 사고 없음. 첫 `verdict18.py` 새 경우의 기대값 오류는 내 시험 구성의 잘못(N12).

## 7. 다음 순회 전에 할 일 (제안)
1. **D-1**: `draft-log.md:459-462`·`handoff.md:112-113`의 제어 문자를 글자로 되돌리고 `draft-log.md` 블롭을 LF로; 덧붙이기 스크립트에 "쓴 뒤 `\r\r`·외톨이 `\r` 0" 검사.
2. **D-2**: `handoff.md:3`·`:5`·`:83` 정본 범위 §82, `:84` Astra 핵심 결정에 §82 갱신 표시, §2.7/§2.8에 §82·user-log 74–76 줄.
3. **D-3**: `D25-planner-cadence.md:142,153-154,188-189`, `D28-m4-critic-measurement.md:15,75,137`에 §82 갱신 표시.
4. N4: K5(J5 저빈도 감사) 구현 때 시간 초과 재송신 규칙을 정본에 정하기. N5·N7: `se2e_diag.md:131` (a)와 `astra_role` effort [결정 필요]에 해소 표시(선택). N14: 논문 갱신 때 D2 해소 문장과 §82.
5. (문서만 고치면 코드 무변경 — 다음 순회는 연속 무결 0에서 다시 셈.)
