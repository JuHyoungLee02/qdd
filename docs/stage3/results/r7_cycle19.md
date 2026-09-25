# R7 객관 검증 순회 — 19회차 (cycle 19, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle18.md` §5 표·결론을 근거로 쓰지 않고 사전 등록 원문에서 대조표를 다시 만들었다. 행마다 **새 경계값으로 구성한 입력 → 실제 함수·CLI 출력** 또는 **파드 원자료 재계산**으로 확인했다). 작성 2026-09-25 15:30 UTC 무렵(로컬 시작 약 15:08 UTC, 파드 첫 명령 15:10:07 UTC, 파드 정리 끝 15:23 UTC). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 `25370d5`(`25370d5fede1…`, 커밋 시각 2026-09-25 15:07:13 UTC) = 검토 시작·끝의 HEAD(작업 트리 깨끗). `f91ad52..25370d5` = 문서만: `CLAUDE.md`, `docs/design/00-interfaces.md`(§82·보충), `D25-planner-cadence.md`, `D28-m4-critic-measurement.md`, `docs/research/astra_role_2026-09-25.md`·`steering_representation_2026-09-25.md`(새), `docs/user-log.md` 72–77, `draft-log.md`·`handoff.md`·`direction-log.md`, `se2e_diag.md`, `r7_cycle16.md`–`r7_cycle18.md`. `harvest/`·`tools/`·`tests/`·사전 등록(`prereg*.md`, `prereg.json`, `E-first`, `EVAL`, `M4`)은 `git diff --name-only f91ad52 25370d5`에 **없음**(직접 확인; 코드·시험·사전 등록 바이트 동일). `git -c safe.directory=D:/qdd -c core.autocrlf=false archive 25370d5`를 Python tarfile로 `D:\tools\scratch_qdd\r7c19\repo`에 풀었다(497파일). 파드 사본 = 같은 archive(`/data/harvest/tmp/r7c19/code`, 498파일 = + JSON `CODE_VERSION` `25370d5f…`, dirty false); 파드 산출 `meta.git.commit` = `25370d5fede1…`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle7.md`–`r7_cycle18.md`, `r7c7_fixes.md`–`r7c15_fixes.md`, 정본 `00-interfaces.md` §1–§82(뒤 절 우선; [사용자] 제목 절은 그대로; 논문 .tex는 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`(§7 포함)·`prereg_se2e_temporal.md`·`M4-overlap-commit.md`.
- 분류(18회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·같은 문서의 뒤 결과와 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 기록이 없는 것. 정본이 "나중에 할 일"로 적은 것(§82 구현 포함)은 SCOPED. §82와 어긋나는 설계·계획 서술(표시 없음)은 DOC, 지금 있는 구현을 설명하는 서술은 해당 없음. 연구 문서의 제안 목록·[결정 필요]가 §82로 답이 난 것은 NOTE, **단 지금의 결정·구조를 틀리게 말하면 DOC**.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c19`(스크립트는 모두 Write 도구로 쓰고 경로로 실행; 로컬 Git Bash heredoc·`cat >`·`python -` 없음. **절차 주의 1건**: 첫 파드 스크립트 `setup19.sh`만 `kubectl exec -i … bash -c 'cat > …/setup19.sh' < setup19.sh`로 올렸다 — 파드 쪽 `cat >`가 stdin을 받은 것이라 규칙 문구에 걸린다. 내용은 Write 도구로 쓴 파일의 바이트 그대로이고(CR 0 확인) 그 뒤 업로드는 모두 `tar -cf - | kubectl exec -i … tar -xf -`, archive는 `tar -xf -`, 정리는 `bash -s < clean19.sh`). 로컬 pytest basetemp·TMP = `…\r7c19\pt`·`…\r7c19\tmp`, C: 쓰기 없음(하네스 작업 출력 파일만). 파드 = `/data/harvest/tmp/r7c19`(정리 전 384 MB). GPU: Isaac = GPU 1에 **내 프로세스 하나**(`--inst-prefix r7c19`, `IR_INST` `r7c19_standard`, `IR_ROOT=cyclo`, 기본 `r6` 접두사 안 씀; 그 시각 GPU 0·1에 R2_TRAIN Isaac 워커들, GPU 3에 E-TC 학습 — 건드리지 않음), GPU 2·3에는 아무것도 올리지 않음, GPU 학습 없음. CPU: 시작 전 파드 cgroup 5 s = 약 19코어 사용·스로틀 증가 0(쿼터 32) → `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`, 한 번에 한 묶음. 시드 DEV·POOL만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 `=cal`·`=test_p5`만, 다른 분할에 대해). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. `ckpt/se2e*`·`logs/se2e*`·`data/se2e_t`·`r2/train`·`r2/dev`는 **읽기만**.

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 2 |
| SCOPED | 19 |
| NOTE | 20 |

코드·시험·사전 등록은 16회차 대상(f91ad52)과 바이트가 같고 모든 행동 확인이 통과했다: 로컬 **1006 passed / 15 skipped**, 파드 CPU **1122 passed / 4 skipped**, LeRobot 6 passed; 가드 **24건** rc 1(새 경계값); R2 DEV `validate_episode` **36/36**; 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 모두 완료·`prereg` OK; 새 시드 **DEV 13**에서 같은 Isaac 워커 C5 → C5' 행동 **1,413개 비트 동일**; 로컬 구성 시험 `check19.py` 37/38(나머지 1은 사전 등록이 파드 고정 사본 해시를 적은 것 — 파드에서 일치 확인, N17), `verdict19.py` 7/7, `canary19.py` 9/9. **18회차 D-1 정정은 맞다**: 저장소 497파일 전체에서 `\r\r\n`·외톨이 `\r`·기타 C0 제어 문자·CRLF 모두 **0**, `draft-log.md` 블롭은 4eb988d(마지막 깨끗한 LF 블롭) 대비 +1줄뿐. **18회차 D-3 정정도 D28은 맞다.**

그러나 (1) **18회차 D-2 정정이 반만 됐다**: `handoff.md:3`만 §82로 바꾸고 D-2가 짚은 `:5`("현재 판본: 정본 §1~§81")·`:83`("§43부터 끝까지(지금 §81)")은 그대로인데, 같은 커밋이 `:113`에 "D-2 handoff가 §82 미반영(정본 범위·핵심 결정 줄 갱신)"이라고 적었다 → **DOC D-1**. (2) **새 연구 문서 `steering_representation_2026-09-25.md`(1079716, 14:55 UTC — §82 14:38 UTC 뒤)가 Astra의 지금 구조를 "경계·사건에만(지금 구조와 같음)"이라고 적는다** — §82는 단계 경계 확인을 작은 모델·코드로 강등했고(Astra = T0·T_fail·T_nov·T_audit), 지금 코드는 K2(5 s 하트비트 + 경계 + 사건)라 어느 쪽과도 맞지 않으며 §82 표시가 없다 → **DOC D-2**. 둘 다 문서만 고치면 되는 항목이다.

---

## 1. DEFECT

없음.

(검토한 후보와 판단: ① 런타임 기본 호출 주기는 K2·N = 5 s(`RuntimeConfig()` → ("K2", 5.0), 내 파드 판 `meta.hb_mode` K2·`hb_n` 5, Astra 호출 = hb t 5.0 → 응답 8.0, 경계 sub t 8.01 → 11.01)이고 `HeartbeatScheduler(mode="K5"|"J5")`는 거부된다 — 정본 §82 "구현(다음) … R7 관문 확인 뒤 착수"가 다음 일로 적었으므로 **SCOPED S19**. ② 카나리 표류 뒤 J5 재사용은 보정 파일의 **날짜** 단위로 비교(같은 날 00:00 적합이면 켬, `canary19.py`) — 정본 §79 D3 "날짜 단위(같은 날 경계) … §77 N6 그대로"가 정했으므로 해당 없음. ③ `prereg_se2e_temporal.md` §7의 `stageb_data.py` `be1e6214…`·`stageb_train.py` `a79ed547…` ≠ 저장소 25370d5 블롭(`038506ad…`·`1f56bb6d…`) — 등록 문장은 파드 고정 사본(`code_se2e_temporal`)의 해시이고 그 사본과 **모두 같음**(`hash19.sh`), 저장소 차이는 §77 `annotate_last_step`·§81 N2 `RESUME_KEYS`로 기록됨 → N17.)

## 2. DOC

### D-1. `handoff.md`의 정본 범위가 여전히 §81 — 18회차 D-2 정정이 `:3`에만 적용되고, 같은 커밋이 "정본 범위 갱신"이라고 기록
- 위치(25370d5 블롭): `docs/handoff.md:5` "> 현재 판본: 정본 `00-interfaces.md` **§1~§81**(뒤 절이 앞 절을 덮는다).", `:83` "`docs/design/00-interfaces.md` §43부터 끝까지(지금 §81)". 대조: `:3`은 이번 커밋에서 "정본 §1~§82"로 바뀜(`git diff 7fe42c6 25370d5 -- docs/handoff.md`의 변경 줄 = `:3`·`:84`·`:112`·`:113`뿐).
- 정본 끝 = §82(`00-interfaces.md:723`, 2026-09-25 14:38 UTC). 18회차 D-2가 `:3`·`:5`·`:83` 세 곳을 명시했고 "고칠 것"에도 세 줄을 적었다.
- 어긋남: `:5`는 "현재 판본", `:83`은 "지금"이라는 현재 시제로 정본 끝을 §81로 적고, 새 세션이 가장 먼저 읽는 줄이다. 게다가 같은 커밋이 `:113` "D-2 handoff가 §82 미반영(정본 범위·핵심 결정 줄 갱신)"으로 정정을 마친 것처럼 기록했다 — 기록 자체가 사실과 다르다. 선례: 3회차 L4·8회차 D-1·12회차 DOC(handoff 정본 범위 줄) — 같은 문서 안 같은 사실을 적은 줄을 다 찾지 않은 모양.
- 덧붙임(같은 줄 무리): `:3` "마지막 갱신: 2026-09-25 13:42 UTC"는 이번 커밋(15:07 UTC)에서 같은 줄의 정본 범위를 고치면서 시각은 그대로 두었다(내용은 15:06 UTC 정정까지 반영).
- 고칠 것(제안): `:5`·`:83`을 §82로, `:3` 갱신 시각을 실제 커밋 시각으로; `:113`은 그대로 두되 "(19회차 D-1: `:5`·`:83`은 이때 빠짐)" 정정 표시. 정정 뒤 `grep -n "§81\b\|§1~§8" docs/handoff.md`로 같은 사실 전수 확인.

### D-2. `steering_representation_2026-09-25.md`가 Astra의 지금 구조를 "경계·사건에만(지금 구조와 같음)"으로 적음 — §82 뒤 작성, 표시 없음
- 위치: `docs/research/steering_representation_2026-09-25.md:33`(권고 표 순위 5) "…상위 추론은 Astra·경계 시점에만 | **유지(지금 구조와 같음)**", `:168` "상위 추론은 **지금처럼** Astra를 경계·사건에만(OneTwoVLA +24 pt 대 이중 시스템…)", `:81` "우리 Astra(경계·사건 호출, §45)와 같은 문제·같은 처방 방향".
- 정본 §82(`00-interfaces.md:726`, 14:38 UTC): "강등(작은 모델·코드로): 5 s 하트비트, **단계 경계 ack**, K3 성공 판정·단계 전환 …", 호출 정책 "트리거 T0 / T_fail / T_nov / T_audit(저빈도)". 이 문서는 커밋 1079716(14:55:34 UTC)으로 §82 **뒤에** 들어왔다. 지금 코드는 K2(하트비트 5 s + 경계 + 사건, 내 파드 판: hb 1·sub 1)라 "경계·사건에만"은 구현 서술로도 맞지 않는다.
- 어긋남: "지금 구조와 같음"·"지금처럼"은 지금의 결정·구조를 말하는 현재 시제인데, 정본 결정(§82: 경계 확인은 Astra가 하지 않음)과도, 현 구현(K2: 주기 하트비트 포함)과도 다르고 §82 표시가 없다. 이 문서는 사용자 질문(user-log 75)에 대한 답의 근거 문서라 독자가 Astra 호출 지점을 이 줄로 잘못 알 수 있다. 권고 5의 요지(실행 때 CoT 생성 금지)는 §82와 충돌하지 않으므로 표시는 Astra 부분에만 필요하다.
- 고칠 것(제안): `:33`·`:168`·`:81`에 "→ **[갱신 정본 §82]** Astra는 J1–J6(T0 과제 컴파일·T_fail 진단/복구·T_nov·저빈도 감사 J5 등)만, 단계 경계 확인·하트비트는 작은 모델·코드로 강등(구현은 R7 관문 뒤; 지금 코드는 K2)" 표시.

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드 GPU 0·1에서 Isaac 워커 진행 중(읽기만); 확인 인자 없는 `gen gen --seeds 59999` rc 1(가드 18).
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8(M9 복구·T_fail 뒤 하트비트 정지 — `pause_until`은 있으나 `core`가 부르지 않음, A5′ 검사·계약 편집, 확인 헤드 보정 파일 기본 미보정).
- S6. Astra 카나리 "none"(§67 보충).
- S7. S-E2E 계열 체크포인트의 런타임 형식 차이(§77 보충 (2), §80) — 저장소 `stageb_data.py`는 §77 뒤 블롭(`038506ad…`), S-E2E·E-TC 고정 사본은 `be1e6214…`.
- S8. CONTRADICT-soft(§68 K6).
- S9. §73 D5 M4 설계 확장.
- S10. §73 N5 E1 범위.
- S11. §74 보충 E-M4-lat 비례 STALE_MAX.
- S12. §75 보충 (2) E-M4 판정 7.
- S13. §77 N8 (13): 완료 정의 밖 사전 등록 실험(E-M8 계열 포함) 등.
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — 25370d5에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. **E-TC 판정 아직 없음**(`prereg_se2e_temporal.md` §7; 이번 검토 대상 아님): 파드 읽기(15:21Z) — `video2_none`·`video2_motion` step 2000 평가 기록(dec_acc 0.6956·0.7211), `single_motion` 학습 step 2000 도달, `logs/se2e_temporal/pred_{single_none,video2_none,video2_motion}.jsonl` 있음, 판정 파일 없음.
- S19. **정본 §82 구현**(K5 모드·`harvest/astra/jobs.py`·`closed --upper`·T_nov·계약 캐시·J2 경로·`astra_slot.py`·Qwen3-VL-32B, E-Astra-necessity 사전 등록·유료 실행은 사용자 승인 뒤, 비용 한도 약 10만 원) — §82 "R7 관문(연속 무결 2회) 확인 뒤 착수". 지금 코드: 기본 K2·N 5 s, `CADENCES` = K0–K4, K5·J5 거부(`check19` C3·C5).

## 4. NOTE
- N1. (18회차 N1 그대로) `stageb_train predict`·`evalck`는 체크포인트 `prompt_config`를 자기 옵션과 대조하지 않는다 — E-TC 결과 문서에 칸별 `prompt_config` 일치를 적기를 권함.
- N2. (그대로) `cli_label.replay_max`의 NaN 순서 의존. 읽는 쪽 `replay_bit_identical`은 이번 새 경우(5e-324·inf·True·[0]·None·없음 → 불신, 0·−0.0 → 신뢰)도 올바름.
- N3. (그대로) `temporal_verdict.py` 입력 검사가 `assert`이고 등록 검증 집합(300·900항목)을 보지 않는다(내 구성 입력 300키로 돌아감).
- N4. (그대로) Astra 시간 초과 뒤 재송신 모양 — K5(J5 저빈도 감사) 구현 때 "시간 초과된 호출은 같은 종류로 재송신"을 정본에 정하기를 권함.
- N5. (그대로) `se2e_diag.md:131` 6절 제안 (a) D2′는 8절로 사실상 수행·해소 — "→ 8절로 수행" 한 줄 권함.
- N6. (그대로) `se2e_diag.md:13` "0.72는 입력 + 데이터 규모 쪽" 읽기는 8.2 뒤 "약 9k까지만" 제한이 붙는다(`:12`에 적힘).
- N7. (그대로) `astra_role_2026-09-25.md:349`·`:517` "J6 effort high는 [결정 필요]", `:478` — §82 "low·high 두 조건 모두 측정"으로 사실상 답이 남. 제안 목록이라 NOTE.
- N8. (그대로) `CLAUDE.md:32`(user-log 76 비용 한도 줄) 위치가 "## 논문 초안" 절 끝.
- N9. **D25 §82 표시가 렌더에서 사라짐**: `D25-planner-cadence.md:153`·`:154`의 표시는 5칸 표(`:150` 머리 5칸) 뒤 **6번째 칸**으로 붙었다. GFM/CommonMark 표 규칙은 머리보다 많은 칸을 버리므로 렌더된 표에는 "(새 기본)"만 남는다(`gfm19.py`: markdown-it 표 확장으로 렌더한 HTML에 "§82" 없음). 원문(에이전트가 읽는 형태)에는 표시가 있어 DOC로 세지 않았다 — 표시를 5번째 칸 안으로 옮기기를 권함. 같은 문서 `:142`(작성 시점 설계의 공백 분석, 괄호로 "T0 + 실패·사건 트리거" 시점을 밝힘)와 §6.1–§6.3의 뒷받침 줄(`:158`·`:159`·`:167`·`:173`)은 표시가 없다 — §6 제목(`:144`, "[우리 접목안, 정본 반영은 메인 세션·사용자 결정]")에 절 단위 §82 표시 한 줄을 권함. D28 표시(`:15`·`:75`·`:137`·`:181`)는 문단·목록 안이라 렌더에도 남음.
- N10. (그대로) `e05`는 `--out` 폴더를 거부 전에 만든다 — 가드 24(`e05 --split dev --seeds 30` → "no episode selected" rc 1)가 빈 `g24/`를 남김(열린 파일 없음).
- N11. (그대로) 카나리 `--force` 같은 날 재실행이 그날 표류 파일을 덮는다.
- N12. 18회차 기록이 `handoff.md:113`에만 있고 `direction-log.md`(마지막 행 14:46 17회차)·`draft-log.md`(마지막 항목 17회차 줄 + 18회차 정정 표시)에는 18회차 행·항목이 없다. 틀린 서술은 아니라 NOTE.
- N13. `handoff.md:88`(§2.7, "2026-09-24 21:03 UTC" 절) "사용자 대기 항목: 없음" — §82 뒤로는 사용자 확인 대기가 있다(`falsify` 반복 진단 [결정 필요], E-Astra-necessity 유료 실행 승인). 날짜 붙은 절이라 NOTE; §2.8에 한 줄 권함.
- N14. 시험 수: 로컬 **1006 passed / 15 skipped**(159.5 s; torch 없음 10·inspect_robots 2·pyarrow 1·isaaclab 1·TODO(P3) 1), 파드 CPU **1122 passed / 4 skipped**(114.96 s, 15:12:51Z), LeRobot 6 passed(23.4 s). 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다. 내 구성 시험: `check19.py` 37/38(H1 = N17), `verdict19.py` 7/7, `canary19.py` 9/9, `prereg_hash.py --check` OK.
- N15. 단계 B 소형 CPU 스모크(15:18 UTC): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(18회차와 같은 값 — 결정적), eval fm 2.4379에서 감소, 지연 expert p50 0.041 s·전체 p50 0.116 s(CPU, 참고).
- N16. 논문(NOTE만): 마지막 논문 커밋 이후 변경 없음 — 18회차 N14(D2 해소 문장, §82 미반영: `paper/sec/0_abstract.tex:2`·`1_intro.tex:12`·`3_method.tex:10` 등 Astra 하트비트를 방법 수단으로 적음) 그대로. 4시간 주기(user-log 73) 반영 때 같이.
- N17. `prereg_se2e_temporal.md:56` §7 등록 해시 10개를 파드 고정 사본 `code_se2e_temporal`과 비교 → **10/10 같음**(`temporal_verdict.py` `992d3e20…`, `se2e_temporal.py` `d5babfb8…`, `se2e_temporal_model.py` `28265152…`, `stageb_train.py` `a79ed547…`, `tools/se2e_temporal.py` `285a7320…`, `temporal_latency.py` `a0dcafcf…`, `stageb_data.py` `be1e6214…`, `stageb_model.py` `5f3eba50…`, `prefix_share.py` `c231a0de…`, `se2e_data.py` `a08f7127…`). 저장소 25370d5는 `stageb_data.py`(+`annotate_last_step` 2줄, §77)·`stageb_train.py`(§81 N2 `RESUME_KEYS`)만 다름 — 등록은 사본을 적은 것이고 차이는 정본에 기록됨(16회차 N4와 같은 판단).
- N18. `e_m4b_meas.md:36`(선택 조건 A "Astra 단계 경계 성공 판정")·`:51`(PC6 "Astra T_sub로 옮긴 판")은 `<!-- END verbatim D28 §4 -->`로 표시된 사전 등록 원문 복사이고 PC6은 발동 안 함(`:212`) — 표시 불필요.
- N19. `docs/superpowers/plans/2026-09-25-e2e-ready.md:12`·`:26`(완료 정의 3·R5 행의 "Astra 하트비트")은 완료 정의가 가리키는 지금 실행 계층 서술이라 해당 없음(§82 구현 뒤 계획 개정 때 같이 권함).
- N20. 절차: 머리 "규칙 준수"의 파드 쪽 `cat >` 1회(내용 영향 없음). 다른 에이전트 파일·프로세스는 건드리지 않았다.

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**, 파드 산출 `meta.prereg.check` = "OK"(e05·e05o·rd·calib·closed). 사전 등록·코드는 `f91ad52..25370d5`에서 바뀌지 않았다(정본은 §82 덧붙임만). 코드 줄은 `25370d5` 기준. "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c19\check19.py`(A–H), `verdict19.py`, `canary19.py`; **파드** = §6(`pod_cpu19.sh`, `pod_eval19.sh`, `data19.py`, `meta19.py`, `trust19.py`, `hash19.sh`, `se2ev19.py`, `scale19.py`, `pod_isaac19.sh`, `closed19.py`). "시험 묶음" = 해당 구현을 부르는 저장소 시험이 로컬 1006·파드 1122 묶음에서 통과. 굵게 = 이번에 근거를 새로 만든 행.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| **1** | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149(TEST2 1150–1299는 연장 시) / TEST-P5 1300–1329 / POOL 2000–2119 (E :113-120), R2_TRAIN 10000–59999 (§66, E :120) | `eval/splits.py:13-43`, `datagen/gen.py:43-57` | 로컬 A1 경계 28값(1·28·29/30·498·500·501·548·549/550·1000·1001·1148·1149/1150·1200·1299/1300·1328·1329/1330·2000·2001·2118·2119/2120·10000·−5) 모두 기대 분할(TEST2 = 미배정 → 어떤 분할로도 안 열림), A2 빈 문자열·다른 값 거부/같은 값 통과, A3 모르는 분할 거부, A4 섞인 목록 [0,1,500] 통째 거부, A5 `cal`+env에서 1000 거부, A6 R2 가드 12경우(1·28 허용, 30 확인 유무 모두 거부, 10001·59998 확인 있어야, 59999 확인 없으면 거부, 60001·2000·1300·549 거부), A7 R2 eval 분할 = seed % 20; 파드 가드 24건 rc 1(§6.4) | 일치 |
| 2 | POOL 120 × 10, 경계 30 % 과표집 (E :121, §76 D-2) | `sim/snapshot.py:29-31,102-136` | 상수 `N_DECISION` 10·`OVERSAMPLE_FRAC` 0.30; 파드 라벨 3시드 168행 중 `oversampled` 51(30 %) | 일치(주석 S14) |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` | 시험 묶음 | 일치 |
| 4 | 분할 = 에피소드 (E :122) | `stagea_data.split_of:151-157`, `calib.halves` | 시험 묶음; 파드 `CALIB_DONE`(보류 = 에피소드 단위 `unit`) | 일치 |
| 5 | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py:26-38` | 시험 묶음; **파드 Isaac DEV 13 C5·C5' 성공 1.0, 14.13 s** | 일치 |
| **6** | 호출 기록: 질문별 확률·요청/응답 원문(E :125), Astra A6(E :126, §28) | `core.py:279-322,395-426` | **파드 DEV 13 C5·C5' 결정 호출 84행**: `sha256(request_blob)` = `request_sha256` 84/84, 이미지 해시가 요청 본문에 84/84, 응답 blob 해시 84/84, `probs` 질문 = `answers` 질문·합 1·[0,1] 84/84, `canary_id` 84/84; Astra 4행: 요청 해시·머리캠 JPEG 해시·effort low·600·`output_text` 4/4 | 일치 |
| **7** | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `analysis/stats.py:4,31-54` | 로컬 E1 `N_BOOT` 10000, E3 합 경로 = 일반 경로(같은 표집), **E4 군집 안 행을 3배로 늘려도 구간 불변 = 행이 아니라 군집 재표집**; 파드 closed·e05·e05o·rd·calib `meta.bootstrap` n_boot 10000·seed 0·percentile·단위 기록 | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate`, `stats.cluster_diff_ci` | 파드 C5 대 C5' 같은 워커(행 99) | 일치 |
| 9–12 | 판정 2 Holm, 판정 10, 카나리 Holm, 판정 절 해시 (E :131, :265, :139, :133) | `e05`, `canary.py`, `eval/common.py`, `stats.holm` | 로컬 E5 Holm 단계 하강(0.01·0.02·0.04 모두 기각); 시험 묶음; `meta.prereg` OK | 일치 |
| **13, 85** | 카나리 기준일 = 같은 세트 × 같은 `question_id@vN` 집합의 첫날 (E :136-140, §79 D2) | `eval/canary.py:168-190` | 로컬 G1: 두 질문 중 하나만 판본이 다른 기록 → 다른 사슬(각자 첫날), 부분 qid 맵 → None | 일치(N11) |
| 14 | 모델 식별 필드가 바뀌어도 같은 처리 (E :139) | `Calibration.load` | 시험 묶음; 로컬 canary19 "다른 지문 → none" | 일치 |
| 15–17 | E0.5 표·재시험·같은 시각 K = 3 (E :236-238) | `e05.vote_steps`, `e05.py` | 시험 묶음; 파드 `e05 --data jsel_dev/P1 --split dev --episodes 2` → `E05_DONE` | 일치 |
| **18** | γ 2/3 (E :240, M4 :276) | `m4.share_at_least:72-77`, `GAMMA` `:46` | 로컬 B1 새 비율(6/9·7/10·14/21 참, 5/8·13/20·0/1 거짓), B2 0.6667 소수 = 정확값(> 2/3) → 2/3 거짓, Fraction(2,3) 참 | 일치 |
| 19–20 | `C_flip` 두 식, A0–A4·층 (E :242, :246) | `e05.py` | 시험 묶음 | 정본 기록(§73) / 일치 |
| 21–28 | 판정 1–10 경계 (E :256-265) | `replay.judge_e05`, `e05.py`, `stats.at_least/below` | 로컬 E1 CMP_EPS: `at_least(0.83−0.80, 0.03)` 참, `below(0.8−0.08, 0.72)` 거짓; 시험 묶음; 파드 `E05_DONE` | 일치 |
| 29, 89 | FLIP_TH 후보 α 0.01·범위 (E :253, :487; M4 :285) | `e05.py:437-446` | 시험 묶음 | 일치 |
| 30 | 같은 시각 뒤집힘 성공·섭동 따로 (E :253, §27) | `e05.py:352-383` | 시험 묶음 | 일치 |
| 31–33 | d_p95 = E0 값, 분당 400 [가정], E1 반분 | `e05 --d-p95`, `calib.halves` | 로컬 B9 `CommitLedger().d_hat` 초기 0.307(stageA_sft p95) | 정본 기록 |
| 34–35 | ECE 15 동일 질량, 오답 < 30 판정 불가 (E :320) | `calibration.ece_mass:71` | 로컬 E6(15구간 실행); 시험 묶음 | 일치 |
| **36** | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat:59-64` | 로컬 E2 새 n: 199·α 0.01 → 198, 200 → 199, 98 → inf, 99 → 99, 39·α 0.05 → 38, 18 → inf, 19 → 19 | 일치 |
| 37–43 | log p 자름·질문별 온도·원 확률·판정 1·7·8·`ambiguous` ECE 제외 (E :333-346) | `calibration.py`, `core.py:362-393` | 시험 묶음; 파드 `calib --heldout jsel_dev/P2` → `CALIB_DONE` | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| **45** | N_max = ⌈d̂/T_c⌉+1 (M4 :258) | `m4.CommitLedger.n_max:178-182`, `d_hat:165-173` | 로컬 B9: d̂ 0.66 → 3(정확히 2.0 경계), 0.67 → 4; d̂ = ⌈0.95 n⌉번째(1..20 → 0.19) | 일치 |
| 46–49 | γ·W·비가역 W+1·τ | `m4.py` | 로컬 B7 W < 0 거부, B8 기본 W 1·τ 1; 시험 묶음 | 일치 |
| 50 | conformal α 0.01·w 5 ((b) 경계) | 확인 헤드 보정 파일 | 기본 미보정 | SCOPED S5 |
| **51** | STALE_MAX 1.5 s (E :487) | `m4.older_than:56-58`, `M4Params.stale_max` | 로컬 B3: 100 Hz 틱 위치 600곳 모두에서 150틱 유지·151틱 버림, B4 +5e-10 유지·+2e-9 버림 | 일치 |
| 52–53 | C2 = VLM Stream, C0–C6 설정 (M4 :329-345) | `conditions.py`, `m4.py:220-226` | 파드 `--conditions "C5,C10"` → "refused before any worker"(가드 15) | 일치 |
| **54** | C5 = §4.2 전체, C5' = (b) 범주 뺌(줄은 none), 판정 3 (M4 :155, :232, :340-342, :361; §77 보충 (3)) | `core.b_line`, `core._boundary:527-578` | **파드 Isaac DEV 13**: C5 `last_step` {none 1, OK 30, LAG 6, DEVIATE 5}, C5' none 42/42, 요청 본문 마지막 `last_step:` 줄 = 행 값 84/84 | 일치 |
| 55 | H 1과 3 (정본 §2, M4 :188-189) | `m4.early_ask_steps:61`, `M4Params.H` | 로컬 B8 기본 H 3; 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 |
| **56–58** | n_LA 2·조기 호출 당겨 씀·FLIP_TH 끔; H = 1 = 같은 스텝 앞당겨 2~3회 (§75) | `m4.py:61-69`, `core.py:455-503` | 로컬 B5 t_send 0.023·d̂ 0.307·T_c 0.33·lead 1.0 → [1, 2, 3](양 끝 포함), B6 lead < d̂ → [2]; B8 n_LA 2·FLIP_TH None | 일치 |
| 59 | 경계 직후 W 2·γ 1.0 등 | 없음 | §73 D5 | SCOPED S9 |
| **60** | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.select_rule:131-142` | 로컬 E7: (0.90, 0.50) 대 (0.91, 0.52) → plan, 0.5201 → time0.33, 0.8999999 부적격 → time0.33, 같은 가족 안 긴 τ(time0.66) | 일치 |
| 61–62 | 폐루프 RD 재표집 = layout 짝, 주 RD = Score (EVAL :182-184) | `closed.py`, `rd.py` | 파드 `rd --variants standard=jsel_dev,random=gen_dev/random/P0 --episodes 2` → `RD_DONE`, 단위 "(kind, layout seed) … paired" | 일치 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | §71 보충 | SCOPED S1 |
| 64–65 | M4b 2,000회, E-M4-lat 비례 STALE_MAX | `m4b/*` / 없음 | §72 예외 / §74 보충 | 일치 / SCOPED S11 |
| **66–67** | H = 1 창·`lead_max` 유한 양수 (§75, §76 N4) | `m4.py:108-113`, `closed.py:160-166` | 로컬 B7 lead_max 0·inf·nan 거부; 파드 `--m4-lead-max 0` 거부(가드 14) | 일치 |
| 68 | E0 판정 4 | `analysis/latency.py` | 시험 묶음 | 일치 |
| 69 | E-M4 판정 7 | 없음 | §75 보충 (2) | SCOPED S12 |
| 70 | FROZEN = 송신 시각 기준 (M4 :150) | `m4.py:228` | §77 N3 | 정본 기록 |
| **71, 93** | 카나리 표류 → J5 끔, 재보정 뒤 재사용, 다음 날 깨끗한 카나리로는 안 켜짐 (E :139, :347, §77 N6, §79 D3) | `closed.j5_after_canary:169-185`, `canary.latest_canary:149-165` | 로컬 canary19 9/9: 표류 9/21·9/23 + 깨끗한 9/24 → `last_drift` = 9/23(최신 표류), 보정 9/22 23:59:59 → 끔, 9/23 00:00 → 켬(날짜 단위, §79 D3), 9/24 → 켬, α None → (None, None), `last_drift` 없는 표류 카나리 → 끔, 다른 지문 → none, 표류 없음 → 켬 | 일치(N11) |
| 72–76 | 응답 모델 필드·재시도 기록, E0.5 정답, `fine_dir`, Astra 카나리 | `models`, `common` | §77 N4·N5, §67 보충; 파드 폐루프 결정 호출 `canary_id` 84/84 | 일치 / SCOPED S13·S6 |
| 77–79 | (b) 범주 줄·런타임 값·경계 틱 호출 = 방금 끝난 스텝 (M4 :232, §77, §79 N1) | `core.b_line`, `core.act:429-515` | 행 54; 시험 묶음 | 일치 |
| 80–84 | 학습 자료 값·학습 항목 상태·C5' none·ser-A-min-2·옛 체크포인트 거부 (§77 (iv), §77 보충 (1)) | `deccall_snap.py`, `stagea_data.build_items`, `serialize.with_last_step:12-15` | 로컬 D2 `LAST_STEP_VALUES` 닫힌 집합, 소문자 "ok" 거부; 시험 묶음(`test_r7c12_last_step.py` 등) | 일치 |
| 86–88 | 결정 호출 행 `probs`·blob·`last_step`, Astra 원응답, 결정 이미지는 해시만 | `core.py`, `reqhash.request_body` | 행 6 | 일치 / 정본 기록 |
| 90 | FLIP_TH = 성공 실행 flip_score의 1−α 분위, 질문별 (M4 :287, §79 D1) | `e05.flip_th_conformal:271-281` | 시험 묶음(같은 순위 규칙 = 행 36) | 일치 |
| 91–92 | 같은 시각 뒤집힘 성공·섭동, 층별 A0 대비 flip | `e05.py` | 시험 묶음 | 일치 |
| 94 | E0 판정 4 집계 (§77 N7) | `latency.step_votes:93`, `judgment4:108` | 시험 묶음 | 일치 |
| **95–97, 105, 115–117, 119** | S-E2E 설정·판정 (a)–(e)·재개·evalck·판정 스크립트 입력 검사·고정본 (`prereg_se2e.md` §3·§4, §77 보충 2, §80 N1) | `tools/se2e/se2e_verdict.py` | **파드 `se2ev19.py`: 25370d5 사본의 판정 스크립트를 실제 로그(읽기 전용)에 다시 돌림** → rc 0, 잎 125개가 기록 `verdict_v2.json`과 **차이 0**, 두 시드 (a)(b)(c)(e) pass; `ckpt/se2e/prereg_se2e.md` sha256 `29191168e48d2a13` = 사본 블롭 | 일치 |
| **98** | 라벨 복원 기준(비트 동일, §78 (1)) | `stagea_data.replay_bit_identical:49-53` | 로컬 D1 새 8경우(0·−0.0 참; 5e-324·inf·True·[0]·None·없음 거짓) | 일치(N2) |
| **99** | 에피소드마다 PhysX 장면 재생성, 모든 호출자 기본 (§78 결정) | `sim/scene.py:418-425,529-532,621-633` | **파드 Isaac 한 워커 C5 → C5'(DEV 13, 모의 선택기)**: 행동 **1,413개 비트 동일**(첫 차이 없음), 호출 42개·Astra 2개 같은 수, `code_sha` `9242f67e59a09ee4` | 일치(행렬 S16) |
| **100, 118, 132** | 라벨 신뢰 = 재생 비트 동일, 필드 없음·null·NaN 행 제외, 뺀 수와 질문 범위 기록 (§78 (1), §80 D1, §81 N3) | `eval/common.load_truth:378-412` | **파드 `e05 --split pool --seeds 2005,2017,2002 --truth outcome:plan`** → rc 0, `meta.truth_label_trust` = {plan, kept **135**, excluded **15**, questions 5개}; 독립 재계수(`trust19.py`): 쓰인 결정 스냅샷 30개 × 5질문에서 `replay_maxabs == 0` 135·아님 15·라벨 없음 0(시드 2002의 비0 17행 중 5질문 몫이 15, 나머지 2는 다른 질문) = meta | 일치 |
| 101 | R2_TRAIN은 하드 리셋 빌드, 옛 녹화 처리 보류 (§78 (2)(3)) | 파드 실행(읽기만) | GPU 0·1 R2_TRAIN Isaac 워커 진행 중 | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 선택 거부, `determinism` 시드 검사가 `--out` 앞 (§79 N5, §80 N3) | `eval/common.load_episodes:340-369`, `sim/determinism.py:194-201` | 가드 21(`fresh --seed 549`)·22(`history --seeds 1,1300`) rc 1·폴더 없음, `canary build-set --seeds 1000-1001` → "no episode selected" rc 1(가드 23), `e05 --seeds 30` → "no episode selected"(가드 24) | 일치(e05 폴더 N10) |
| 103 | Isaac 워커 `OMP_WAIT_POLICY=PASSIVE` (§79) | `closed.worker_cmd:188-199` | 내 Isaac 워커가 이 명령으로 돌아 `CLOSED_DONE`; `--isaac-gpu 3`·`2` rc 1(가드 12·13) | 일치 |
| 104 | e05 qid 등록부 기본 = `<out>` (§79) | `e05.py:680` | 시험 묶음 | 일치 |
| 106–113 | S-E2E 진단 D1–D3 (`prereg_se2e_diag.md` §1–§4) | 파드 고정 사본 | 로그·문서 불변(7fe42c6 뒤 `se2e_diag.md` 무변경); 18회차 재계산 값과 문서 일치 | 일치 |
| 114 | §7.1 설정 | 파드 판 로그 `config` | 로그 불변(읽기만) | 일치 |
| **133** | §7.2 주 지표·적합·확인/포화 규칙·외삽 | 문서 `se2e_diag.md:148-165` | **파드 `scale19.py` 독립 계산**: acc@2000 = 0.552222 / 0.682222 / 0.685556 / 0.683333, NLL 5.34203 / 0.79566 / 0.76804 / 0.77350; 적합 a 0.2944·b 0.0901; Δ25 +0.00111, Δ50 −0.00222 → 확인 거짓·포화 참; N\* 134,460 = 문서 | 일치 |
| 134–136 | §7.3 D2 해소, §7.4 처리량, §5 종합 읽기 표 | 문서 `se2e_diag.md:12`, `:125`, `:166-180` | 7fe42c6 뒤 무변경(18회차 확인 그대로) | 일치(N5·N6) |
| 121 | E-TC 옵션 끔 = 기준 표본, 기본 경로·프롬프트 해시 파일 무수정 (`prereg_se2e_temporal.md` §7, §8) | `se2e_temporal.load_se2e_t`, `stageb_train._load_data` | **파드 `hash19.sh`: 등록 해시 10/10 = 고정 사본 `code_se2e_temporal`**(N17); 시험 `test_stageb_train_defaults_unchanged_and_variant_config` 통과 | 일치 |
| **122** | V = video2: [t−0.3 s, t], 10 Hz에서 k−3(0으로 자름) (§2) | `se2e_temporal.prev_index:46-47` | 로컬 F1 k 0·2·3·7·400 → 0·0·0·4·397, `DELTA_S` 0.3 | 일치 |
| **123** | M = 움직임 줄: 인과 후방 차분, 팔 3분위 0.2179·0.6070, 그리퍼 0.1755 (§3) | `se2e_temporal.backward_velocity:50-53`·`motion_line:86-92` | 로컬 F3 후방 차분 [0, 10, 20, 30]; F2 경계 8경우(0.21789 still·0.2179 slow·0.60699 slow·0.6070 fast, 열림 속도 ±0.1756 opening/closing·±0.1754 still, 실제 `GRIP_CAL["sim_width_m"]`로 환산) | 일치 |
| **124** | 드롭아웃 p = 0.3, 난수 (시드, 스텝) 따로 (§3) | `se2e_temporal.motion_dropout:95-109` | 로컬 F4 20,000표본 비율 0.303, 같은 (시드, 스텝) 결과 같음·다른 스텝 다름, 전역 `random` 상태 불변, 입력 표본 무변경; F5 p = 0 항등 | 일치 |
| 125 | 새 판 표지·`prompt_config` → 기본 체크포인트와 섞이지 않음 (§7) | `stageb_train.prompt_config_t`, `fused_model.check_prompt` | 시험 묶음 | 일치(N1) |
| 126 | 지표·층: 검증 300 × 3질문 = 900항목, 전이 층 (§4) | `temporal_verdict.metrics:48-60` | 로컬 verdict19가 전이 층(750항목)·정상 층(150)을 따로 셈 | 일치 |
| **127** | 채택 규칙: 주효과 = 두 칸 평균(§6 :47) ≥ +0.02 ∧ 전이 주효과 ≥ −0.01 ∧ FULL p95 증가 ≤ 10 %, 상대 CMP_EPS 1e-12 | `tools/se2e/temporal_verdict.py:24-34,63-68,119-128` | 로컬 `verdict19.py` 7/7(새 배치: 전이 250·정상 50 스냅샷): **비대칭 단순 효과**(+36/900, 0) → V 주효과 정확히 0.02 채택 / +35 거짓; **전이 두 칸 평균** (−8, −7)/750 = −0.01 채택 / (−8, −8) 거짓; M 지연 0.33/0.30 = 정확히 +10 % 채택 / 0.33000001 거짓; V 판정이 (video2, motion) 지연 7.0 s를 보지 않음 | 일치(N3) |
| 128–129 | 판정 스크립트·등록 코드 해시, 등록은 학습 전, 실행 순서, 지연 측정 (§5–§7) | 파드 E-TC 판 | 해시 행 121; 판정 전 | 일치 / SCOPED S18 |
| 130–131 | §81 N2 재개 검사 키, §81 N10 라벨 쓰기 null | `stageb_train.py:264-292`, `cli_label.replay_max:37-43` | 파드 시험 `test_r7c15_resume_keys.py`·`test_r7c15_label_write.py` 통과 | 일치(N2) |
| **137** | Astra 호출 주기 = 하트비트(응답 + N, N = 5 s) + 단계 경계 + 사건, in-flight 1, 15 s → 재송신, gpt-6-astra·low·600 (§45) | `runtime/astra_hb.py:33-34,82-140`, `core.py:242-276` | 로컬 C1 N = 5 경계(4.999999 없음·5.0 hb, 응답 9.5 뒤 14.49 없음·14.5 hb), C2 15 s 정확히 유지·+0.0001 초과, C4 모델·effort·600; **파드 판 Astra: hb t 5.0 → 응답 8.0, 경계 sub는 진행 중 1개 규칙으로 응답 뒤 8.01 송신 → 11.01, 다음 hb 16.01 > 종료 14.13** | 일치(N4) |
| **140** | 정본 §82: 강등(5 s 하트비트·단계 경계 ack·K3), J1–J6, K5 모드 등은 "구현(다음)·R7 관문 뒤" | 없음(현 구현 = §45 K0–K4) | 로컬 C3 `CADENCES` = K0–K4, K5·J5 거부, C5 `RuntimeConfig()` = ("K2", 5.0) | SCOPED S19 |
| **138** | LeRobot v2.1 내보내기 = ROBOTIS 형식(§63), 30 Hz·원본 해상도·관절 행동(§66) | `datagen/lerobot_export.py` | **파드 새 2편**(dr/mug_marker ep5, standard/bottle_tray ep1) `export` → 2편·628프레임, `verify` 오류 0·PSNR 최소 38.02 dB·lerobot 0.3.3 적재 628프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참; LeRobot 시험 6 passed | 일치 |
| 139 | R2 DEV 구조 검사(§66, 완료 정의 1) | `datagen/validate.py` | 파드 `/data/harvest/r2/dev/*/*/P0` 전 편 **36/36 오류 없음**(6폴더 × 6), `valid_for_training` 메타 불일치 0 | 일치 |

### 5.1 18회차 표와의 차이
- 표 판정 변화 없음(모두 일치 또는 SCOPED). 근거 교체: 행 1(경계 28값·R2 12경우·새 가드 24건), 6·54·99·137(새 시드 DEV 13, Astra 시각열), 7(군집 재표집 불변성), 13·71(날짜 경계·최신 표류 선택), 18·36·45·51·56–58·60(새 경계값), 100(새 시드 조합, 제외 15의 독립 재계수), 121(고정 사본 해시 10/10), 122–124·127(새 경계·두 칸 평균 경계), 133(독립 재계산), 138(새 2편).

## 6. 확인한 것 (근거)

### 6.1 18회차 정정 확인 (과제 2)
- **D-1(제어 문자)**: `ctrlscan.py`로 25370d5 archive 497파일 전수 — `\r\r\n` 0, 외톨이 `\r` 0, `\t`·`\n`·`\r` 외 C0 제어 문자 0, CRLF 0, CRLF·LF 섞임 0, BOM 0, UTF-8 아닌 텍스트 0. 블롭 줄 끝: `git diff 4eb988d 25370d5 -- docs/draft-log.md` = +1줄(17회차 줄)뿐 → 7fe42c6의 284줄 CRLF 블롭 문제 해소. `draft-log.md:460`·`handoff.md:112`는 `\n`·`\r\n`·`\r\r\n`을 역슬래시 글자로 담고 정정 표시가 붙음.
- **D-2(handoff §82)**: `:84` 핵심 결정에 §82 표시(J1–J6·강등·effort·한도·구현 시점) — 맞음. `:3` §1~§82 — 맞음. **`:5`·`:83` 미정정 → 이번 D-1.**
- **D-3(D25·D28)**: D28 `:15`·`:75`·`:137`·`:181`(PC6) 표시 — 맞음. D25 `:153`·`:154`·`:182` 표시 — 원문에는 있으나 `:153`·`:154`는 렌더에서 빠짐, `:142` 등 미표시(N9).

### 6.2 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외)
- §82 대상 어휘(`하트비트|heartbeat|T_hb|T_sub|K2-N|H-cadence|단계 경계|성공 판정`) 41개 파일 전수: 정본 앞 절은 뒤 절 우선 규칙으로 해당 없음. 구현·결과 서술(`r5_closed_loop.md`, `r6_eval.md`, `pre_r7_fixes.md`, `planner_dev.md`, `r2_datagen.md:148`, 코드·시험, 계획 완료 정의 `:12`·`:26`)은 지금 있는 것 또는 다른 뜻("단계 경계" = 스킬 단계, "성공 판정" = T1 술어)이다. `M6`·`SUMMARY`·`STAGE2-CLOSE`의 "단계 경계"는 Jev 결정 지점 뜻, `D10a`·`D23`·`research/v2`는 다른 주제·옛 기록. `e_m4b_meas.md`는 원문 복사(N18). **§82와 어긋나는 현재 시제·표시 없음 = `steering_representation:33`·`:81`·`:168`(D-2)**; D25는 N9. 정본 범위: `handoff.md:5`·`:83` = §81(**D-1**), `astra_role:11`·`:497`은 작성 시점 표기(해당 없음). `CLAUDE.md:52`는 [사용자] 줄(그대로).
- 연구 문서 [결정 필요]: `astra_role` `:349`·`:478`·`:517`(N7), `:515`(falsify — §82 "남은 [결정 필요]"와 같음, 맞음). `steering_representation`의 "정본 결정 필요"(`:31` M4의 연속·2D 목표 확정)는 §82와 무관, 열린 제안으로 맞음.
- 새 문서의 인용 수치: `steering_representation:6` "0.72·부호 반대 8/155·상한 약 0.93·9k 이상 포화", `:172` "오답 34 %만 경계 밴드·인접 0.1 s 라벨 9–20 %" = `se2e_diag.md:13`·`:60`·`:119`·`:129`, `se2e_data.md:76`(1 cm 데드밴드·MAG 경계).
- user-log 72–77 대 `CLAUDE.md`: 72(보고 KST·기록 UTC)·73(4시간)·76(10만 원) 원문 인용 일치. 77(브레인스토밍)은 정본 결정 없음 — 반영할 결정 없음.

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st` + 코드 사본으로 R2 DEV 전 편 `validate_episode` **36/36**; LeRobot 시험 6 passed; 새 2편 내보내기·검증·lerobot 적재(행 138). |
| 2 모델 | 충족(CPU) | GPU 없음 → CUDA 시험·GPU 재적재 건너뜀. 파드 CPU 스모크(N15), CPU 묶음의 `test_stageb_torch.py`·`test_r7c15_resume_keys.py`·`test_se2e_temporal_qwen.py` 통과. |
| 3 폐루프 | 충족 | Isaac 한 워커(`closed --model mock --split dev --seeds 13 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c19`, 15:18:27–15:22:24 UTC, `IR_INST` `r7c19_standard`): `CLOSED_DONE` C5·C5' 성공 1.0, 14.13 s, 호출 42·오류 0, 행 필드·blob(행 6), `meta.bootstrap` 10000, `prereg` OK, git `25370d5f`, `code_sha` `9242f67e59a09ee4`, 하드 리셋 빌드 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 15:15:47–15:16:23 UTC): `e05` → `E05_DONE`, `rd` → `RD_DONE`, `calib` → `CALIB_DONE`, `e05 --split pool --truth outcome:plan`(행 100) → `E05_DONE`. 모두 prereg OK·git `25370d5f`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·카나리·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`truth_label_trust`(+ `questions`); 정리 뒤 흔적 없음(§6.6). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`, 15:15:40–15:15:47 UTC, 18회차와 다른 값)
- 1–2 `e05 --split cal|test_p5`, 3–4 `calib --fit-split test`·`--heldout-split test_p5`, 5 `rd --split cal`, 6–8 `closed --split test --seeds 1000`·`cal 549`·`test_p5 1329` → "refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 28,29,30`, 10 `pool --seeds 1999`, 11 `dev --seeds 1150` → "not in split … never opened"; 12–13 `--isaac-gpu 3`·`2` → "GPU 2 never renders"; 14 `--m4-lead-max 0`, 15 `--conditions "C5,C10"` → "refused before any worker"; 16 `HARVEST_ALLOW_SPLIT=cal` + `--split test`, 17 `=test_p5` + `e05 --split test` → 거부; 18 `gen --seeds 59999`(확인 없음), 19 `--seeds 9999 --confirm-train`, 20 `--seeds 0,2000 --confirm-train` → 거부; 21 `determinism fresh --seed 549`, 22 `history --seeds 1,1300` → "only DEV 0-29 and POOL"; 23 `canary build-set --seeds 1000-1001` → "no episode selected"; 24 `e05 --split dev --seeds 30` → "no episode selected". **24건 모두 rc 1**; 출력 폴더는 24번(e05)의 빈 폴더 하나(N10), 나머지 0.

### 6.5 A. 테스트
- 로컬(`…\r7c19\repo` = 25370d5 archive, `python -m pytest -q -rs -p no:cacheprovider -o addopts="" --basetemp=D:/tools/scratch_qdd/r7c19/pt`): EXIT 0, **1006 passed · 15 skipped**.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, TMPDIR·pyc·카나리·qid 등록부 = scratch): **1122 passed, 4 skipped**, EXIT 0(15:12:51Z).
- 파드 LeRobot(`venv_e3st` + `r2/pylib_lerobot`·`pylib_pytest`): **6 passed**.

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(시작·끝 `git status` 깨끗, HEAD = 25370d5). 로컬 C:에 이 검토의 산출물 없음(하네스 작업 출력 파일만).
- 파드 정리(`clean19.sh`, 경로를 하나씩 적은 스크립트, 15:23 UTC): `tmp/r7c19`(384 MB), 내 Isaac 판이 만든 `tmp/carb.Uz9nXo`(15:18:28Z)·`tmp/tmpn69w2dbr`(15:18:46Z)·`cache/pyc_r6/data/harvest/tmp/tmpn69w2dbr`·`cache/pyc_r6/data/harvest/tmp/r7c19`, `ir/kitcache/cyclo-r7c19_standard`(208 MB). 판별: Isaac 앞뒤 `tmp`·`pyc_r6`·`kitcache` 목록 차이(새 항목은 이것뿐), 생성 시각이 내 Isaac 창(15:18:27–15:22:24Z) 안, `/proc/*/fd` 전수에서 여는 프로세스 없음. 끝에 `tmp`·`kitcache`의 r7c19 항목 0, 내 프로세스 0.
- 로컬 임시(`D:\tools\scratch_qdd\r7c19`: `src.tar`, `repo/`, `pt/`, `tmp/`, `tv/`, 스크립트)는 다음 순회 대조용으로 남김(C: 아님). `canary19.py`의 `canroot/`는 스크립트가 지움.
- 절차 사고: 파드 쪽 `cat >` 1회(머리 "규칙 준수", N20). 그 밖에 없음.

## 7. 다음 순회 전에 할 일 (제안)
1. **D-1**: `handoff.md:5`·`:83`을 §82로, `:3` 갱신 시각 정정, `:113`에 "`:5`·`:83`은 19회차에 정정" 표시; `grep -n "§8[0-9]" docs/handoff.md`로 같은 사실 전수.
2. **D-2**: `steering_representation_2026-09-25.md:33`·`:81`·`:168`에 §82 갱신 표시(Astra = J1–J6, 경계 확인·하트비트는 강등, 구현 전 코드는 K2).
3. N9: D25 `:153`·`:154` 표시를 5번째 칸 안으로 옮기고 §6 제목에 절 단위 §82 표시. N12·N13: direction-log·draft-log 18회차 줄, handoff §2.8에 §82의 사용자 대기 항목. N5·N7: 해소 표시(선택). N16: 논문 갱신 때 D2 해소 문장과 §82.
4. 정정 커밋 전 검사: 바뀐 모든 파일에 대해 `ctrlscan`류 검사(제어 문자·CRLF 0)와 "고친다고 적은 줄 = 실제 바뀐 줄" 대조(`git diff`의 변경 줄 번호와 수정 기록 비교).
5. (문서만 고치면 코드 무변경 — 다음 순회는 연속 무결 0에서 다시 셈.)
