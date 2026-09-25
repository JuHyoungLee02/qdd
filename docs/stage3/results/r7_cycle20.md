# R7 객관 검증 순회 — 20회차 (cycle 20, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle19.md` §5 표·결론을 근거로 쓰지 않고 사전 등록 원문에서 대조표를 다시 만들었다. 행마다 **19회차와 다른 새 경계값으로 구성한 입력 → 실제 함수·CLI 출력** 또는 **파드 원자료 재계산**으로 확인했다). 작성 2026-09-25 15:50 UTC 무렵(로컬 시작 약 15:28 UTC, 파드 첫 명령 15:32:42 UTC, 파드 정리 끝 15:44:30 UTC). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 `7e0aeba`(`7e0aeba9412b…`, 커밋 시각 2026-09-25 15:27:51 UTC). 검토 시작 때 HEAD = 7e0aeba·작업 트리 깨끗. **검토 중에 다른 에이전트가 커밋을 더했다**(5ce4ac1·31f538a·ab90ee9·cd518a9 user-log 79, f4f6a49 E-TC 판정, f00cb59 정본 §83; 15:28–15:40 UTC)와 작업 트리 변경(`harvest/train/se2e_data.py` 등, `harvest/astra_motion/`) — **이번 검토 대상 아님**(모든 확인은 7e0aeba archive 사본에서 했다). `git diff --name-only f91ad52 7e0aeba`에 `harvest/`·`tools/`·`tests/`·`pytest.ini`·`third_party/`·사전 등록(`E-first`·`EVAL`·`M4`·`prereg*.md`·`prereg.json`)은 **없음**(파일별 블롭 해시 비교로 직접 확인 — 코드·시험·사전 등록 바이트 동일). 정본 `00-interfaces.md` 블롭은 25370d5와 같음(`178bc04f`, 끝 = §82). `git -c safe.directory=D:/qdd -c core.autocrlf=false archive 7e0aeba`를 Python tarfile로 `D:\tools\scratch_qdd\r7c20\repo`에 풀었다(**499파일** = 19회차 497 + `hypothesis_short_window_2026-09-25.md`·`r7_cycle19.md`). 파드 사본 = 같은 archive(`/data/harvest/tmp/r7c20/code`, 500파일 = + JSON `CODE_VERSION` `7e0aeba9…`, dirty false); 파드 산출 `meta.git.commit` = `7e0aeba9412b…`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle7.md`–`r7_cycle19.md`, `r7c7_fixes.md`–`r7c15_fixes.md`, 정본 `00-interfaces.md` §1–§82(뒤 절 우선; [사용자] 제목 절은 그대로; 논문 .tex는 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`(§7 포함)·`prereg_se2e_temporal.md`·`M4-overlap-commit.md`.
- 분류(19회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·같은 문서의 뒤 결과와 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 기록이 없는 것. 정본이 "나중에 할 일"로 적은 것(§82 구현 포함)은 SCOPED. 연구 문서의 제안 목록·[결정 필요]는 지금의 결정·구조를 틀리게 말하지 않는 한 NOTE. 원문이 맞고 렌더에서만 빠지는 표 칸은 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c20`(스크립트는 모두 Write 도구로 쓰고 경로로 실행; 로컬·파드 어디서도 heredoc·`cat >`·`python -` 없음). 파드 업로드 = `kubectl exec … mkdir -p` 뒤 `tar -cf - | kubectl exec -i … tar -xf -`(archive `src.tar` + 스크립트, 파드 스크립트 CR 바이트 0 확인), 정리 = `bash -s < clean20.sh`. 로컬 pytest basetemp·TMP = `…\r7c20\pt`·`…\r7c20\tmp`, C: 쓰기 없음(하네스 작업 출력 파일만). 파드 = `/data/harvest/tmp/r7c20`. GPU: Isaac = GPU 1에 **내 프로세스 하나**(`--inst-prefix r7c20`, `IR_INST` `r7c20_standard`, `IR_ROOT=cyclo`, 기본 `r6` 안 씀; 그 시각 GPU 0·1에 R2_TRAIN Isaac 워커들 — 건드리지 않음), GPU 2·3에는 아무것도 올리지 않음(가드 12·13은 워커 전에 거부), GPU 학습 없음. CPU: 시작 전 파드 cgroup 5 s = 약 17코어·스로틀 증가 0(쿼터 32) → `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`, 한 번에 한 묶음(CPU 시험 → 가드·평가 → Isaac 순차). 시드 DEV·POOL만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 `=test`·`=cal`만, 다른 분할에 대해). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. `ckpt/se2e*`·`logs/se2e*`·`data/se2e_t`·`r2/train`·`r2/dev`·`code_se2e_temporal`는 **읽기만**.

## 판정: **PASS**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 0 |
| SCOPED | 19 |
| NOTE | 23 |

코드·시험·사전 등록은 f91ad52와 바이트가 같고 모든 행동 확인이 통과했다: 로컬 **1006 passed / 15 skipped**, 파드 CPU **1122 passed / 4 skipped**, LeRobot 6 passed; 가드 **24건** 모두 rc 1(19회차와 다른 값); R2 DEV `validate_episode` **36/36**; 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 모두 완료·`prereg` OK; 새 시드 **DEV 22**에서 같은 Isaac 워커 C5 → C5' 행동 **1,691개 비트 동일**; 로컬 구성 시험 `check20.py` **36/36**, `verdict20.py` 7/7, `canary20.py` 7/7, `succ20.py` 5/5, `prereg_hash.py --check` OK. 저장소 499파일 전체에서 `\r\r\n`·외톨이 `\r`·기타 C0 제어 문자·CRLF·BOM·UTF-8 아닌 텍스트 모두 **0**(탭 1개는 N14).

**19회차 정정 두 건은 모두 실제로 들어갔다**: `handoff.md:5`·`:83`이 §82로 바뀌었고(`git diff -U0 25370d5 7e0aeba`의 변경 hunk = `:3`·`:5`·`:83`·`:88`·`:113`), `:3` 갱신 시각 = 커밋 시각 15:27 UTC, `grep`으로 handoff의 정본 범위 줄 셋(`:3`·`:5`·`:83`)이 모두 §1~§82·지금 §82. `steering_representation_2026-09-25.md:33`·`:81`·`:168` 세 곳에 §82 표시(Astra = J1–J6, 경계 확인·하트비트 강등, 지금 코드는 K2)가 원문에 있다. 19회차 NOTE 중 N9(D25 절 단위 표시, `:146`)·N12(18–19회차 기록 줄)·N13(handoff 사용자 대기 항목)도 반영됐다. 남은 것은 모두 NOTE(렌더에서 빠지는 표 칸, 정정 표시 문구의 부정확, 옛 기록 줄의 탭 한 개 등)라 판정에 영향이 없다. **연속 무결 1회.**

---

## 1. DEFECT

없음.

(검토한 후보와 판단: ① 런타임 기본 호출 주기는 여전히 K2·N = 5 s(`RuntimeConfig()` → ("K2", 5.0), 내 파드 판 `meta.hb_mode` K2·`hb_n` 5, Astra = hb t 5.0 → 8.0, 경계 sub 8.92 → 11.92, 다음 hb 16.92 > 종료 16.91)이고 `HeartbeatScheduler(mode="K5"|"J5"|"k2")`는 거부 — 정본 §82 "구현(다음) … R7 관문 확인 뒤 착수"가 다음 일로 적었으므로 **SCOPED S19**. ② `m4.share_at_least(0, 0)`는 참을 돌려주지만 모든 호출처가 `n >= 2`(`e05.py:64`, `replay.py:20`) 또는 `len(votes) >= 3`(`m4.py:288`)으로 먼저 거른다 — 도달 불가라 해당 없음. ③ 소수 float γ(0.666)는 정확한 이진 값으로 비교된다(666/1000 거짓) — `m4.py:73-75` docstring이 밝힌 동작이고 런타임 `GAMMA` = 문자열 "2/3"이라 해당 없음. ④ `determinism history`는 POOL 시드도 거부("DEV seeds 0-29 only", 가드 22) — 사전 등록보다 좁은 쪽이라 해당 없음. ⑤ `prereg_se2e_temporal.md` §7의 `stageb_data.py` `be1e6214…`·`stageb_train.py` `a79ed547…` ≠ 저장소 블롭(`038506ad…`·`1f56bb6d…`) — 등록은 파드 고정 사본 `code_se2e_temporal`의 해시이고 그 사본과 10/10 같음(`hash20.sh`), 저장소 차이는 §77·§81 N2로 기록됨 → N20.)

## 2. DOC

없음.

(검토한 후보: `handoff.md:113`의 18회차 줄 정정 표시 문구(N12), `:88`의 정의 안 된 실험 이름(N13), `steering_representation`의 표 밖 칸 표시(N9), `hypothesis_short_window`의 Astra 자리 제안(N16), `draft-log.md:422` 탭(N14) — 모두 현재 결정·구조를 틀리게 말하지 않거나, 원문이 맞거나, 날짜 붙은 옛 기록이라 NOTE.)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드 GPU 0·1에서 `gen gen --confirm-train --seeds 10000-10599` Isaac 워커 진행 중(읽기만); 확인 인자 없는 `gen gen --seeds 10000` rc 1(가드 18).
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
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — 7e0aeba에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. **E-TC 판정**(`prereg_se2e_temporal.md` §7): 7e0aeba 시점에는 판정 없음. 파드 읽기(15:38Z): `logs/se2e_temporal/verdict.json`이 15:37:34 UTC에 생겼고 f4f6a49(15:39 UTC)로 커밋됨 — 대상 커밋 뒤라 **이번 검토 대상 아님**(다음 순회에서 등록 판정 스크립트 재실행으로 확인 권함).
- S19. **정본 §82 구현**(K5 모드·`harvest/astra/jobs.py`·`closed --upper`·T_nov·계약 캐시·J2 경로·`astra_slot.py`·Qwen3-VL-32B, E-Astra-necessity 사전 등록·유료 실행은 사용자 승인 뒤, 한도 약 10만 원) — §82 "R7 관문(연속 무결 2회) 확인 뒤 착수". 지금 코드: 기본 K2·N 5 s, `CADENCES` = K0–K4, K5·J5 거부(`check20` C3·C5).

## 4. NOTE
- N1. (그대로) `stageb_train predict`·`evalck`는 체크포인트 `prompt_config`를 자기 옵션과 대조하지 않는다 — E-TC 결과 문서에 칸별 `prompt_config` 일치를 적기를 권함.
- N2. (그대로) `cli_label.replay_max`의 NaN 순서 의존. 읽는 쪽 `replay_bit_identical`은 새 경우(0.0·0 → 신뢰, 1e-300·nan·False·"0"·−1e-12·없음 → 불신)도 올바름.
- N3. (그대로) `temporal_verdict.py` 입력 검사가 `assert`이고 등록 검증 집합(300·900항목)을 보지 않는다(내 구성 입력 300키 = 전이 200·정상 100으로 돌아감).
- N4. (그대로) Astra 시간 초과 뒤 재송신 모양 — K5 구현 때 정본에 정하기를 권함.
- N5. (그대로) `se2e_diag.md:131` 6절 제안 (a) D2′는 8절로 사실상 수행 — "→ 8절로 수행" 한 줄 권함.
- N6. (그대로) `se2e_diag.md:13` "0.72는 입력 + 데이터 규모 쪽" 읽기에는 "약 9k까지만" 제한이 붙는다(`:12`에 적힘).
- N7. (그대로) `astra_role_2026-09-25.md:349`·`:517` "J6 effort high는 [결정 필요]" — §82 "low·high 두 조건 모두 측정"으로 사실상 답이 남. 제안 목록이라 NOTE. 같은 문서 `:11` "정본 §1–§81"은 작성 시점 표기.
- N8. (그대로) `CLAUDE.md:32`(user-log 76 비용 한도 줄) 위치가 "## 논문 초안" 절 끝.
- N9. **`steering_representation_2026-09-25.md:33`·`:81`의 §82 표시가 렌더에서 사라짐**: 두 표시는 표 머리(`:33`은 7칸, `:81`은 6칸)보다 한 칸 많은 **마지막 칸**에 붙었다. markdown-it(GFM 표)로 렌더하면 원문 §82 6개 중 2개만 남는다(`gfm20b.py`: 빠지는 줄 = `:33`·`:81`; `:168` 문단 표시는 남음). 원문(에이전트가 읽는 형태)에는 있고, 권고 5의 본문 설명 `:168`에는 렌더 뒤에도 표시가 있어 NOTE — 표 아래에 한 줄 표시를 두거나 마지막 칸 안으로 옮기기를 권함. D25 `:155`·`:156`도 같은 모양이지만 7e0aeba의 §6 절 단위 표시(`:146`)가 덮는다. D28·handoff는 원문 = 렌더(§82 8·9개).
- N10. (그대로) `e05`는 `--out` 폴더를 거부 전에 만든다 — 가드 24(`e05 --split pool --seeds 1999` → "no episode selected" rc 1)가 빈 `g24/`를 남김.
- N11. (그대로) 카나리 `--force` 같은 날 재실행이 그날 표류 파일을 덮는다.
- N12. **`handoff.md:113` 정정 표시 문구가 사실보다 좁다**: "[정정 … R7 19회차 D-1: 이 커밋에서 실제로 바뀐 것은 머리 줄(:3)뿐이었다 — :5·:83은 19회차 정정에서 §82로 갱신]". `git diff -U0 7fe42c6 25370d5 -- docs/handoff.md`의 hunk는 `:3`·`:84`·`:112`·`:113`이고, D-2가 말한 "핵심 결정 줄"(`:84`)은 25370d5에서 실제로 §82 표시를 받았다(19회차가 "맞음"으로 확인). 뜻은 "정본 범위 세 줄 중 바뀐 것은 :3뿐"이라 현재 상태를 틀리게 말하지는 않는다(과거 커밋에 대한 기록) — "정본 범위 줄 중에서는"을 넣기를 권함.
- N13. `handoff.md:88` 사용자 대기 (2)의 "**E-Astra-motion** 탐침"은 7e0aeba 트리 어디에도 정의가 없다(전체 grep 1건 = 이 줄). 7e0aeba 뒤 커밋 5ce4ac1(user-log 79)에서 이름이 나온다 — 정의 문서가 생기면 경로를 붙이기를 권함.
- N14. **`draft-log.md:422`에 실제 탭 문자 1개**: "미확정 수치는 `<TAB>`entative 표시" — LaTeX `\tentative`의 `\t`가 셸에서 탭으로 바뀐 것(8aaa241부터, 18회차 D-1과 같은 종류). 저장소 모든 .md 중 탭은 이 한 곳뿐. 날짜 붙은 옛 기록이고 뜻이 드러나 NOTE — `` `\tentative` ``로 복원 권함(18·19회차 제어 문자 검사는 탭을 허용해 걸리지 않았다).
- N15. 위생: `handoff.md`가 7e0aeba에서 **끝 줄바꿈을 잃었고**(25370d5 블롭은 `\n`으로 끝남) `:114` 빈 줄이 §2.8 목록을 둘로 나눈다(렌더는 정상). `prereg.json`의 끝 줄바꿈 없음은 해시가 고정한 원문이라 그대로.
- N16. `research/hypothesis_short_window_2026-09-25.md:49`·`:203`("Astra의 자리는 실행 중 매 단계 흐름을 불러 주는 계획기가 아니다", 7.3 "제안, 결정은 메인 세션")는 §82 J1·J6과 맞는 제안이다. 뒤에 온 user-log 78(15:16 UTC, "아스트라가 움직임에도 개입")과 방향이 다르지만 정본 결정이 아니고 handoff `:88` (3)에 "설계 브레인스토밍 진행 중"으로 올라 있어 NOTE.
- N17. 시험 수: 로컬 **1006 passed / 15 skipped**(190.6 s; torch 없음 10·inspect_robots 2·pyarrow 1·isaaclab 1·TODO(P3) 1), 파드 CPU **1122 passed / 4 skipped**(119.67 s, 15:37:05Z), LeRobot 6 passed(19.45 s). 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다.
- N18. 단계 B 소형 CPU 스모크(15:39 UTC): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(19회차와 같은 값 — 결정적), eval fm 2.4379에서 시작, 지연 expert p50 0.043 s·전체 p50 0.118 s(CPU, 참고).
- N19. 논문(NOTE만): 18·19회차 N14·N16 그대로(`paper/sec/0_abstract.tex:2`·`1_intro.tex:12`·`3_method.tex:10` 등 Astra 하트비트를 방법 수단으로 적음, §82 미반영).
- N20. `prereg_se2e_temporal.md` §7 등록 해시 10개 = 파드 고정 사본 `code_se2e_temporal` **10/10 같음**; 저장소 7e0aeba는 `stageb_data.py`(§77)·`stageb_train.py`(§81 N2)만 다름 — 등록은 사본을 적은 것이고 차이는 정본에 기록됨(16·19회차와 같은 판단).
- N21. (그대로) `e_m4b_meas.md:36`·`:51`은 `<!-- END verbatim D28 §4 -->` 사전 등록 원문 복사 — 표시 불필요.
- N22. (그대로) `2026-09-25-e2e-ready.md:12`·`:26`(완료 정의 3·R5의 "Astra 하트비트")은 지금 실행 계층 서술이라 해당 없음(§82 구현 뒤 계획 개정 때 같이 권함). `D25-planner-cadence.md:142`(§5, "지금 설계(T0 + 실패·사건 트리거)에 빠진 것은 … 하트비트와 단계 경계 확인")는 작성 시점(2026-09-24) 공백 분석이고 §6 절 표시 밖이다 — 날짜 붙은 분석이라 NOTE.
- N23. 검토 중 HEAD가 f00cb59로 움직였다(§머리). 이 보고서는 7e0aeba만 판정한다 — 그 뒤 커밋(정본 §83, E-TC 판정, user-log 79)과 작업 트리의 코드 변경(`harvest/train/se2e_data.py`, `harvest/astra_motion/`)은 **다음 순회 대상**이고, 코드가 바뀌면 연속 무결은 다시 0부터 센다.

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**, 파드 산출 `meta.prereg.check` = "OK"(e05·e05o·rd·calib·closed). 사전 등록·코드는 `f91ad52..7e0aeba`에서 바뀌지 않았다. 코드 줄은 7e0aeba 기준. "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c20\check20.py`(A–G), `verdict20.py`, `canary20.py`, `succ20.py`; **파드** = §6(`pod_cpu20.sh`, `pod_eval20.sh`, `data20.py`, `meta20.py`, `hash20.sh`, `se2ev20.py`, `pod_isaac20.sh`, `closed20.py`). "시험 묶음" = 해당 구현을 부르는 저장소 시험이 로컬 1006·파드 1122 묶음에서 통과. 모든 경계값은 19회차와 다르게 새로 골랐다.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149(TEST2 1150–1299 연장 시) / TEST-P5 1300–1329 / POOL 2000–2119 / R2_TRAIN 10000–59999 (E :113-120, §66) | `eval/splits.py:13-43`, `datagen/gen.py:43-57` | 로컬 A1 새 경계 27값(0·15·29/31·499·520·549/551·999·1000·1075·1149/1151·1250·1298·1300·1315·1329/1331·1999·2000·2060·2119/2121·9999·30000·−1) 모두 기대 분할(TEST2 = 미배정), A2 env 없음·다른 값 거부/같은 값 통과, dev·pool은 env 불필요, A3 `r2_train`·`test2`·`DEV`·"" 거부, A4 [2000, 2119, 2120]·[29, 1300] 통째 거부·문자열 시드 수용, A5 `test` env로 1000·1149 통과·1300 거부, A6 R2 가드 12경우(0 무확인 허용, 29 허용, 31·9999·60000·2119·1149·520 거부, 10000·59999·35000은 확인 있을 때만), A7 eval 분할 = seed % 20(10040·59980 eval, 10041·59999 fit); 파드 가드 24건 rc 1(§6.4) | 일치 |
| 2 | POOL 120 × 10, 경계 30 % 과표집 (E :121, §76 D-2) | `sim/snapshot.py:29-31` | 상수 `N_DECISION` 10·`OVERSAMPLE_FRAC` 0.30·`SNAP_DT` 0.33(33 부단계) | 일치(주석 S14) |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` | 시험 묶음 | 일치 |
| 4 | 분할 = 에피소드 (E :122) | `stagea_data.split_of`, `calib.halves` | 시험 묶음; 파드 `CALIB_DONE`(단위 = 보류 집합 에피소드) | 일치 |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py:24-37`, `config.py:12-13` | 로컬 `succ20.py` 5/5: 100 Hz에서 1.00 s 유지 → 성공, 0.99 s → 아님, 중간 None 한 번 → 끊김, 끊긴 뒤 다시 1.0 s → 성공, `success_hold_s` 1.0·`episode_limit_s` 60.0; 파드 Isaac DEV 22 C5·C5' 성공(16.91 s) | 일치 |
| **6** | 호출 기록: 질문별 확률·요청/응답 원문(E :125), Astra A6(E :126, §28) | `core.py:279-322,395-426` | **파드 DEV 22 C5·C5' 결정 호출 102행**: `sha256(request_blob)` = `request_sha256` 102/102, 이미지 해시가 요청 본문에 102/102, 응답 blob 해시 102/102, `probs` 질문 = `answers` 질문·합 1·[0,1] 102/102, `canary_id` 102/102, `question_id@vN` 102/102; Astra 4행: 요청 해시·머리캠 JPEG 해시·effort low·600·`output_text` 4/4 | 일치 |
| **7** | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `analysis/stats.py:4,31-54` | 로컬 E1 `N_BOOT` 10000, E3 일반 경로 = 군집 합 경로(새 35군집·seed 4), **E4 군집 안 행을 2배 대 5배로 늘려도 구간 동일**; 파드 closed·e05·e05o·rd·calib `meta.bootstrap` n_boot 10000·seed 0·percentile·단위 기록 | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate`, `stats.cluster_diff_ci` | 파드 C5 대 C5' 같은 워커(행 99) | 일치 |
| **9–12** | 판정 2 Holm, 판정 10, 카나리 Holm, 판정 절 해시 (E :131, :265, :139, :133) | `stats.holm:75`, `canary.py`, `eval/common.py` | 로컬 E5 Holm 단계 하강: (0.0166, 0.03, 0.2) → 첫째만 기각(0.03 > 0.05/2에서 멈춤), (0.0167, 0.001) → 둘 다 기각(순서 무관); `meta.prereg` OK | 일치 |
| **13, 85** | 카나리 기준일 = 같은 세트 × 같은 `question_id@vN` 집합의 첫날 (E :136-140, §79 D2) | `eval/canary.py:168-190` | 로컬 G1: 질문 하나가 더 있는 상위 집합 맵 → 다른 사슬(y1), 같은 맵의 첫 실행(y3), 다른 세트 무시, 세트 S에 상위 맵 없음 → None | 일치(N11) |
| 14 | 모델 식별 필드가 바뀌어도 같은 처리 (E :139) | `Calibration.load`, `latest_canary` | 로컬 canary20: 다른 지문(fpB)의 표류가 fpA에 섞이지 않음, 모르는 지문 → none | 일치 |
| 15–17 | E0.5 표·재시험·같은 시각 K = 3 (E :236-238) | `e05.vote_steps`, `e05.py` | 시험 묶음; 파드 `e05 --data jsel_dev/P2 --split dev --episodes 3` → `E05_DONE` | 일치 |
| **18** | γ 2/3 (E :240, M4 :276) | `m4.share_at_least:72-77`, `GAMMA` `:46` = "2/3" | 로컬 B1 새 비율(2/3·4/6·10/15·67/100 참, 1/2·9/14·66/100 거짓), B2 float 0.666은 정확한 이진 값(> 0.666)이라 666/1000 거짓·문자열 "0.666" 참·665/1000 거짓(docstring대로) | 일치 |
| 19–20 | `C_flip` 두 식, A0–A4·층 (E :242, :246) | `e05.py` | 시험 묶음 | 정본 기록(§73) / 일치 |
| **21–28** | 판정 1–10 경계 (E :256-265) | `replay.judge_e05`, `stats.at_least/below` | 로컬 E1 CMP_EPS: `at_least(0.3−0.1, 0.2)` 참, `below(0.3−0.1, 0.2)` 거짓; 파드 `E05_DONE` | 일치 |
| 29, 89 | FLIP_TH 후보 α 0.01·범위 (E :253, :487; M4 :285) | `e05.py:437-446` | 시험 묶음 | 일치 |
| 30 | 같은 시각 뒤집힘 성공·섭동 따로 (E :253, §27) | `e05.py:352-383` | 시험 묶음 | 일치 |
| 31–33 | d_p95 = E0 값, 분당 400 [가정], E1 반분 | `M4Params.d_p95_init`, `calib.halves` | 로컬 B8 `d_p95_init` 0.307 | 정본 기록 |
| 34–35 | ECE 15 동일 질량, 오답 < 30 판정 불가 (E :320) | `calibration.ece_mass:71` | 로컬 E6(450예측·15구간 실행); 시험 묶음 | 일치 |
| **36** | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat:59-64` | 로컬 E2 새 n: 299·α 0.01 → 297, 300 → 298, 98 → inf, 199·α 0.05 → 190, 58 → 57, 18 → inf, 1·α 0.5 → 1 (식으로 따로 계산한 값과 같음) | 일치 |
| 37–43 | log p 자름·질문별 온도·원 확률·판정 1·7·8·`ambiguous` ECE 제외 (E :333-346) | `calibration.py`, `core.py:362-393` | 시험 묶음; 파드 `calib --heldout jsel_dev/P0 --episodes 3` → `CALIB_DONE` | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| **45** | N_max = ⌈d̂/T_c⌉+1 (M4 :258) | `m4.CommitLedger.n_max:178-182`, `d_hat:165-173` | 로컬 B9: d̂ 0.33 → 2(정확히 1.0 경계), 0.3301 → 3; d̂ = ⌈0.95·40⌉ = 38번째(1..40 ms → 0.038) | 일치 |
| 46–49 | γ·W·비가역 W+1·τ | `m4.py` | 로컬 B7 W −2 거부, B8 기본 W 1·τ 1 | 일치 |
| 50 | conformal α 0.01·w 5 ((b) 경계) | 확인 헤드 보정 파일 | 기본 미보정 | SCOPED S5 |
| **51** | STALE_MAX 1.5 s (E :487) | `m4.older_than:56-58` | 로컬 B3: 50 Hz 틱 위치 300곳 모두에서 75틱 유지·76틱 버림, B4 +9e-10 유지·+1.1e-9 버림 | 일치 |
| 52–53 | C2 = VLM Stream, C0–C6 설정 (M4 :329-345) | `conditions.py`, `m4.py:220-226` | 파드 `--conditions "C5,C99"` → "refused before any worker"(가드 15) | 일치 |
| **54** | C5 = §4.2 전체, C5' = (b) 범주 뺌(줄은 none), 판정 3 (M4 :155, :232, :340-342, :361; §77 보충 (3)) | `core.b_line`, `core._boundary:527-578` | **파드 Isaac DEV 22**: C5 `last_step` {none 1, OK 34, DEVIATE 10, LAG 4, CONTRADICT 2}, C5' none 51/51, 요청 본문 마지막 `last_step:` 줄 = 행 값 102/102 | 일치 |
| 55 | H 1과 3 (정본 §2, M4 :188-189) | `m4.early_ask_steps:61`, `M4Params.H` | 로컬 B8 기본 H 3; 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 |
| **56–58** | n_LA 2·조기 호출 당겨 씀·FLIP_TH 끔; H = 1 = 같은 스텝 앞당겨 2~3회 (§75) | `m4.py:61-69`, `core.py:455-503` | 로컬 B5b t_send 0·d̂ 0.33·T_c 0.33·lead 0.99 → [1, 2, 3](양 끝 정확히 포함), B6 d̂ 0.3301 → [2, 3], B5 (0.1, 0.25, 0.9) → [2, 3]; B8 n_LA 2·FLIP_TH None | 일치 |
| 59 | 경계 직후 W 2·γ 1.0 등 | 없음 | §73 D5 | SCOPED S9 |
| **60** | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.select_rule:131-142` | 로컬 E7: (0.95, 0.30) 대 (0.95, 0.32) → plan, 0.3201 → time0.33, 0.8999 부적격 → time0.66 | 일치 |
| 61–62 | 폐루프 RD 재표집 = layout 짝, 주 RD = Score (EVAL :182-184) | `closed.py`, `rd.py` | 파드 `rd --variants standard=jsel_dev,random=gen_dev/random/P0 --episodes 3` → `RD_DONE`, 단위 "(kind, layout seed) … paired" | 일치 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | §71 보충 | SCOPED S1 |
| 64–65 | M4b 2,000회, E-M4-lat 비례 STALE_MAX | `m4b/*` / 없음 | §72 예외 / §74 보충 | 일치 / SCOPED S11 |
| **66–67** | H = 1 창·`lead_max` 유한 양수 (§75, §76 N4) | `m4.py:108-113`, `closed.py:160-166` | 로컬 B7 lead_max −1·−inf 거부, 0.001 수용; 파드 `--m4-lead-max -0.5` 거부(가드 14) | 일치 |
| 68 | E0 판정 4 | `analysis/latency.py` | 시험 묶음 | 일치 |
| 69 | E-M4 판정 7 | 없음 | §75 보충 (2) | SCOPED S12 |
| 70 | FROZEN = 송신 시각 기준 (M4 :150) | `m4.py:228` | §77 N3 | 정본 기록 |
| **71, 93** | 카나리 표류 → J5 끔, 재보정 뒤 재사용, 다음 날 깨끗한 카나리로는 안 켜짐 (E :139, :347, §77 N6, §79 D3) | `closed.j5_after_canary:169-185`, `canary.latest_canary:149-165` | 로컬 canary20 7/7: 표류 9/10 + 깨끗한 9/11 → `last_drift` 9/10, 보정 9/09 23:59:59.9 → 끔, 9/10 00:00:00·23:59:59 → 켬(날짜 단위, §79 D3), 새 표류 9/12 뒤 9/11 보정 → 다시 끔 | 일치(N11) |
| 72–76 | 응답 모델 필드·재시도 기록, E0.5 정답, `fine_dir`, Astra 카나리 | `models`, `common` | §77 N4·N5, §67 보충; 파드 결정 호출 `canary_id` 102/102 | 일치 / SCOPED S13·S6 |
| 77–79 | (b) 범주 줄·런타임 값·경계 틱 호출 = 방금 끝난 스텝 (M4 :232, §77, §79 N1) | `core.b_line`, `core.act:429-515` | 행 54; 시험 묶음 | 일치 |
| **80–84** | 학습 자료 값·C5' none·ser-A-min-2·옛 체크포인트 거부 (§77 (iv), §77 보충 (1)) | `serialize.with_last_step:12-15` | 로컬 D2 `LAST_STEP_VALUES` 닫힌 집합, "Ok"·"NONE" 거부·"LAG" 수용; 시험 묶음 | 일치 |
| 86–88 | 결정 호출 행 `probs`·blob·`last_step`, Astra 원응답, 결정 이미지는 해시만 | `core.py`, `reqhash.request_body` | 행 6 | 일치 / 정본 기록 |
| 90 | FLIP_TH = 성공 실행 flip_score의 1−α 분위, 질문별 (M4 :287, §79 D1) | `e05.flip_th_conformal:271-281` | 시험 묶음(같은 순위 규칙 = 행 36) | 일치 |
| 91–92 | 같은 시각 뒤집힘 성공·섭동, 층별 A0 대비 flip | `e05.py` | 시험 묶음 | 일치 |
| 94 | E0 판정 4 집계 (§77 N7) | `latency.step_votes:93`, `judgment4:108` | 시험 묶음 | 일치 |
| **95–97, 105, 115–117, 119** | S-E2E 설정·판정 (a)–(e)·재개·evalck·판정 스크립트 입력 검사·고정본 (`prereg_se2e.md` §3·§4, §77 보충 2, §80 N1) | `tools/se2e/se2e_verdict.py` | **파드 `se2ev20.py`: 7e0aeba 사본의 판정 스크립트를 실제 로그(읽기 전용)에 다시 돌림** → rc 0, 잎 125개가 기록 `verdict_v2.json`과 **차이 0**, 두 시드 (a)(b)(c)(e) pass; `ckpt/se2e/prereg_se2e.md` sha256 `29191168e48d2a13` = 사본 블롭 | 일치 |
| **98** | 라벨 복원 기준(비트 동일, §78 (1)) | `stagea_data.replay_bit_identical:49-53` | 로컬 D1 새 8경우(0.0·0 참; 1e-300·nan·False·"0"·−1e-12·없음 거짓) | 일치(N2) |
| **99** | 에피소드마다 PhysX 장면 재생성, 모든 호출자 기본 (§78 결정) | `sim/scene.py:418-425,529-532,621-633` | **파드 Isaac 한 워커 C5 → C5'(DEV 22, 모의 선택기)**: 행동 **1,691개 비트 동일**(첫 차이 없음), 호출 51개·Astra 2개 같은 수·같은 시각, `code_sha` `9242f67e59a09ee4` | 일치(행렬 S16) |
| **100, 118, 132** | 라벨 신뢰 = 재생 비트 동일, 필드 없음·null·NaN 행 제외, 뺀 수와 질문 범위 기록 (§78 (1), §80 D1, §81 N3) | `eval/common.load_truth:378-412` | **파드 `e05 --split pool --seeds 2011,2048,2090 --truth outcome:plan`** → rc 0, `meta.truth_label_trust` = {plan, kept **100**, excluded **50**, questions 5개}; 독립 재계수(`meta20.py`): 결정 스냅샷 30개 × 5질문에서 `replay_maxabs`가 실수 0인 행 100·아님 50·라벨 없음 0(라벨 파일 165행 = 5질문 150 + `fine_dir` 15, 중복 키 0) = meta | 일치 |
| 101 | R2_TRAIN은 하드 리셋 빌드, 옛 녹화 처리 보류 (§78 (2)(3)) | 파드 실행(읽기만) | GPU 0·1 R2_TRAIN Isaac 워커 진행 중 | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 선택 거부, `determinism` 시드 검사가 `--out` 앞 (§79 N5, §80 N3) | `eval/common.load_episodes:340-369`, `sim/determinism.py:48-53,197-203` | 가드 21(`fresh --seed 1000` → "only DEV 0-29 and POOL")·22(`history --seeds 2000,500` → "DEV seeds 0-29 only") rc 1·폴더 없음, 가드 23(`canary build-set --seeds 500-501`)·24(`e05 --seeds 1999`) → "no episode selected" | 일치(e05 폴더 N10) |
| 103 | Isaac 워커 `OMP_WAIT_POLICY=PASSIVE` (§79) | `closed.worker_cmd:188-199` | 내 Isaac 워커가 이 명령으로 돌아 `CLOSED_DONE`; `--isaac-gpu 2`·`3` rc 1(가드 12·13) | 일치 |
| 104 | e05 qid 등록부 기본 = `<out>` (§79) | `e05.py:680` | 시험 묶음 | 일치 |
| 106–113 | S-E2E 진단 D1–D3 (`prereg_se2e_diag.md` §1–§4) | 파드 고정 사본 | 로그·문서 불변(`se2e_diag.md`는 25370d5 뒤 무변경) | 일치 |
| 114 | §7.1 설정 | 파드 판 로그 `config` | 로그 불변(읽기만) | 일치 |
| **133** | §7.2 주 지표·적합·확인/포화 규칙·외삽 | 문서 `se2e_diag.md:148-165` | **파드 `se2ev20.py` 독립 계산**: acc@2000 = 0.552222 / 0.682222 / 0.685556 / 0.683333, NLL 5.34203 / 0.79566 / 0.76804 / 0.77350; 적합 a 0.2944·b 0.0901; Δ25 +0.00111, Δ50 −0.00222 → 확인 거짓·포화 참; N\* 134,460 = 문서 | 일치 |
| 134–136 | §7.3 D2 해소, §7.4 처리량, §5 종합 읽기 표 | `se2e_diag.md:12`, `:125`, `:166-180` | 무변경 | 일치(N5·N6) |
| 121 | E-TC 옵션 끔 = 기준 표본, 기본 경로·프롬프트 해시 파일 무수정 (`prereg_se2e_temporal.md` §7, §8) | `se2e_temporal.load_se2e_t`, `stageb_train._load_data` | **파드 `hash20.sh`: 등록 해시 10/10 = 고정 사본**(N20); 시험 `test_stageb_train_defaults_unchanged_and_variant_config` 통과 | 일치 |
| **122** | V = video2: [t−0.3 s, t], 10 Hz에서 k−3(0으로 자름) (§2) | `se2e_temporal.prev_index:46-47` | 로컬 F1 k 1·3·4·100 → 0·0·1·97 | 일치 |
| **123** | M = 움직임 줄: 인과 후방 차분, 팔 = 7관절 노름 3분위 0.2179·0.6070, 그리퍼 0.1755 초과 (§3 :29-31) | `se2e_temporal.backward_velocity:50-53`·`motion_values`·`motion_line:86-92` | 로컬 F3 후방 차분 [1, 1.5, 1.5, 0.5] → [0, 5, 0, −10](k+1 안 읽음); F2 한 관절 −0.2179 → slow(≥ 하한), 0.1 × 7관절 → 노름 0.2646 slow, 0.6069 slow, −0.6070 fast; 그리퍼 |g| = 문턱 정확히 같으면 still(엄격한 >, 양·음 모두), 넘으면 opening/closing | 일치 |
| **124** | 드롭아웃 p = 0.3, 난수 (시드, 스텝) 따로 (§3) | `se2e_temporal.motion_dropout:95-109` | 로컬 F4 30,000표본 비율 0.304, 같은 (3, 17) 결과 같음·스텝 18 다름, 전역 `random` 상태 불변, 입력 무변경 | 일치 |
| 125 | 새 판 표지·`prompt_config` → 기본 체크포인트와 섞이지 않음 (§7) | `stageb_train.prompt_config_t`, `fused_model.check_prompt` | 시험 묶음 | 일치(N1) |
| 126 | 지표·층: 검증 300 × 3질문 = 900항목, 전이 층 (§4) | `temporal_verdict.metrics:48-60` | 로컬 verdict20이 전이 층(600항목)·정상 층(300)을 따로 셈 | 일치 |
| **127** | 채택 규칙: 주효과 = 두 칸 평균 ≥ +0.02 ∧ 전이 주효과 ≥ −0.01 ∧ FULL p95 증가 ≤ 10 %, 상대 CMP_EPS 1e-12 (§6 :45-47) | `tools/se2e/temporal_verdict.py:24-34,63-68,119-128` | 로컬 `verdict20.py` 7/7(새 배치: 전이 200·정상 100 스냅샷, 19회차는 V 쪽을 봤고 이번에는 **M 쪽**): M 단순 효과 +27/900·+9/900 → 주효과 정확히 +0.02 채택 / +26 거짓; M 전이 두 칸 평균 (−3, −9)/600 = −0.01 채택 / (−3, −10) 거짓; V 지연 0.44/0.40 = 정확히 +10 % 채택 / 0.4400001 거짓; M 판정이 (video2, motion) 지연 9 s를 보지 않음 | 일치(N3) |
| 128–129 | 판정 스크립트·등록 코드 해시, 등록은 학습 전, 실행 순서, 지연 측정 (§5–§7) | 파드 E-TC 판 | 해시 행 121; 판정은 7e0aeba 뒤(S18) | 일치 / SCOPED S18 |
| 130–131 | §81 N2 재개 검사 키, §81 N10 라벨 쓰기 null | `stageb_train.py:264-292`, `cli_label.replay_max:37-43` | 파드 시험 `test_r7c15_resume_keys.py`·`test_r7c15_label_write.py` 통과 | 일치(N2) |
| **137** | Astra 호출 주기 = 하트비트(응답 + N, N = 5 s) + 단계 경계 + 사건, in-flight 1, 15 s → 재송신, gpt-6-astra·low·600 (§45) | `runtime/astra_hb.py:33-34,82-140`, `core.py:242-276` | 로컬 C1 진행 중이면 없음(6.0), 응답 7.3 뒤 12.2999 없음·12.3 hb, C2 송신 12.3 → 27.3 유지·27.30001 초과, C4 모델·effort·600; **파드 판 Astra: hb 5.0 → 8.0, 경계 sub 8.92 → 11.92, 다음 hb 16.92 > 종료 16.91(0.01 s 경계에서 안 나감)** | 일치(N4) |
| **140** | 정본 §82: 강등(5 s 하트비트·단계 경계 ack·K3), J1–J6, K5 모드 등은 "구현(다음)·R7 관문 뒤" | 없음(현 구현 = §45 K0–K4) | 로컬 C3 `CADENCES` = K0–K4, "K5"·"J5"·"k2" 거부, C5 `RuntimeConfig()` = ("K2", 5.0) | SCOPED S19 |
| **138** | LeRobot v2.1 내보내기 = ROBOTIS 형식(§63), 30 Hz·원본 해상도·관절 행동(§66) | `datagen/lerobot_export.py` | **파드 새 2편**(dr/mug_tray ep3, standard/mug_marker ep4) `export` → 2편·556프레임, `verify` 오류 0·PSNR 최소 39.68 dB·lerobot 0.3.3 적재 556프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참; LeRobot 시험 6 passed | 일치 |
| 139 | R2 DEV 구조 검사(§66, 완료 정의 1) | `datagen/validate.py` | 파드 `/data/harvest/r2/dev/*/*/P0` 전 편 **36/36 오류 없음**, `valid_for_training` 메타 불일치 0 | 일치 |

### 5.1 19회차 표와의 차이
- 표 판정 변화 없음(모두 일치 또는 SCOPED). 근거 교체: 행 1(새 경계 27값·R2 12경우·새 가드 24건), 5(성공 1 s 경계 새로 구성), 6·54·99·137(새 시드 DEV 22, 102행, Astra 0.01 s 경계), 7(2배 대 5배), 9–12(Holm 멈춤 경계), 13(상위 집합 맵), 18(float γ 문서 동작), 36·45·51·56–58·60(새 경계값), 71(새 날짜열·재표류), 100(새 시드 조합 100/50), 122–124(새 값, 노름·엄격한 문턱), 127(M 쪽 경계), 138(새 2편).

## 6. 확인한 것 (근거)

### 6.1 19회차 정정 확인 (과제 2)
- `git diff -U0 25370d5 7e0aeba`: `handoff.md` hunk `:3`·`:5`·`:83`·`:88`·`:113`(+2줄), `steering_representation` `:33`·`:81`·`:168`, `D25` `:146`(+2줄), `draft-log.md` +2줄, `direction-log.md` +2행, `user-log.md` +6줄(78), 새 파일 `hypothesis_short_window_2026-09-25.md`(a8d4242)·`r7_cycle19.md`.
- **D-1(handoff 정본 범위)**: `:5` "§1~§82", `:83` "지금 §82", `:3` "마지막 갱신: 2026-09-25 15:27 UTC … 정본 §1~§82" — 맞음. 저장소 전체 정본 범위 줄 grep: 현재 시제로 §81 이하를 말하는 줄 없음(`astra_role:11`은 작성 시점 표기, 옛 절·결과 문서는 날짜 붙은 기록). `:113` 정정 표시는 문구가 좁음(N12).
- **D-2(steering §82 표시)**: `:33`·`:81`·`:168` 원문에 표시 — 맞음. 렌더에서 `:33`·`:81`은 빠짐(N9).
- **19회차 N9·N12·N13**: D25 §6 절 단위 표시(`:146`, "이 절(6.1–6.3과 표)의 T_hb 5 s·T_sub 기본값은 §82로 대체") — §82 원문과 맞음. `draft-log.md`·`direction-log.md`에 18·19회차 줄(표 4칸 일치). handoff `:88`에 사용자 대기 3항목(§82 falsify [결정 필요] = 정본 §82 "남은 [결정 필요]"와 같음, 유료 실행 승인·한도 10만 원 = §82 보충, 움직임 인터페이스 = user-log 78) — 맞음(이름 N13).
- **제어 문자·줄 끝 전수**(`ctrlscan20.py`, archive 499파일 중 텍스트 450): `\r\r\n` 0, 외톨이 `\r` 0, `\t`·`\n`·`\r` 외 C0 0, CRLF 0, 섞임 0, BOM 0, UTF-8 아님 0. 끝 줄바꿈 없음 2(`handoff.md` — N15, `prereg.json` — 원문). 탭은 .md 전체에 `draft-log.md:422` 하나(N14).

### 6.2 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외)
- 하트비트 어휘(`하트비트|heartbeat|T_hb|T_sub|K2-N|H-cadence`) 53개 파일: 정본 §45·§46은 §82가 덮음(뒤 절 우선), 코드·시험·구현 결과 문서(`r5_closed_loop`, `r6_eval`, `pre_r7_fixes`, `r7_cycle*`)는 지금 있는 구현(K2) 서술 또는 날짜 붙은 기록, `astra_role`는 §82의 근거 문서(현 구현 K2를 사실대로 적고 K5를 제안), D25·D28·steering·handoff는 §82 표시 있음, 계획 `:12`·`:26`은 N22, 논문은 N19. **§82와 어긋나는 현재 시제·표시 없음 = 0.**
- 새 문서 `hypothesis_short_window_2026-09-25.md`: Astra 자리 = T0 닫힌 단계 어휘(J1)·오프라인 라벨 교사(J6) — §82와 맞음, 제안 표시("결정은 메인 세션")(N16). 지금 구조에 대한 서술(`:167` "우리 결정 모델은 지금 단계 정보 없이 배운다", `:195` 인식·코드가 좌표를 맡음)은 `se2e_data.md`·정본 §58과 맞음.
- user-log 78 대 문서: 정본 결정 없음(브레인스토밍) — handoff `:88` (3)에 대기 항목으로만 적힘, 맞음. `CLAUDE.md`는 25370d5 뒤 무변경.

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st` + 코드 사본으로 R2 DEV 전 편 `validate_episode` **36/36**; LeRobot 시험 6 passed; 새 2편 내보내기·검증·lerobot 적재(행 138). |
| 2 모델 | 충족(CPU) | GPU 없음 → CUDA 시험·GPU 재적재 건너뜀. 파드 CPU 스모크(N18), CPU 묶음의 `test_stageb_torch.py`·`test_r7c15_resume_keys.py`·`test_se2e_temporal_qwen.py` 통과. |
| 3 폐루프 | 충족 | Isaac 한 워커(`closed --model mock --split dev --seeds 22 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c20`, 15:39:47–15:43:55 UTC, `IR_INST` `r7c20_standard`): `CLOSED_DONE` C5·C5' 성공 1.0, 16.91 s, 호출 51·오류 0, 확정 비율 0.854, 결정 3.02/s, 행 필드·blob(행 6), `meta.bootstrap` 10000, `prereg` OK, git `7e0aeba9`, `code_sha` `9242f67e59a09ee4`, 하드 리셋 빌드 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 15:37:30–15:38:06 UTC): `e05` → `E05_DONE`, `rd` → `RD_DONE`, `calib` → `CALIB_DONE`, `e05 --split pool --truth outcome:plan`(행 100) → `E05_DONE`. 모두 prereg OK·git `7e0aeba9`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·카나리·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`·`truth_label_trust`(+ `questions`); 정리 뒤 흔적 없음(§6.6). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`, 15:37:22–15:37:30 UTC, 19회차와 다른 값)
- 1 `e05 --data P2 --split test`, 2 `e05 --split cal --seeds 520`, 3 `calib --fit-split cal`, 4 `calib --heldout-split test`, 5 `rd --split test_p5`, 6–8 `closed --split test --seeds 1149`·`cal 500`·`test_p5 1300` → "refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 0,31`, 10 `pool --seeds 2120`, 11 `dev --seeds 1299` → "not in split … never opened"; 12–13 `--isaac-gpu 2`·`3` → "GPU 2 never renders"; 14 `--m4-lead-max -0.5`, 15 `--conditions "C5,C99"` → "refused before any worker"; 16 `HARVEST_ALLOW_SPLIT=test` + `closed --split cal --seeds 520`, 17 `=cal` + `e05 --split test_p5` → 거부; 18 `gen --seeds 10000`(확인 없음), 19 `--seeds 60000 --confirm-train`, 20 `--seeds 1300 --confirm-train` → 거부; 21 `determinism fresh --seed 1000` → "only DEV 0-29 and POOL"; 22 `history --seeds 2000,500` → "DEV seeds 0-29 only"; 23 `canary build-set --seeds 500-501` → "no episode selected"; 24 `e05 --split pool --seeds 1999` → "no episode selected". **24건 모두 rc 1**; 출력 폴더는 24번(e05)의 빈 폴더 하나(N10), 나머지 0.

### 6.5 A. 테스트
- 로컬(`…\r7c20\repo` = 7e0aeba archive, `python -m pytest -q -rs -p no:cacheprovider -o addopts="" --basetemp=D:/tools/scratch_qdd/r7c20/pt`): EXIT 0, **1006 passed · 15 skipped**.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, TMPDIR·pyc·카나리·qid 등록부 = scratch): **1122 passed, 4 skipped**, EXIT 0(15:37:05Z).
- 파드 LeRobot(`venv_e3st` + `r2/pylib_lerobot`·`pylib_pytest`): **6 passed**.

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가. 검토 시작 때 HEAD = 7e0aeba·작업 트리 깨끗; 끝날 때 HEAD = f00cb59와 다른 에이전트의 작업 트리 변경이 있음(N23, 내가 만든 것 아님, 건드리지 않음). 로컬 C:에 이 검토의 산출물 없음(하네스 작업 출력 파일만).
- 파드 정리(`clean20.sh`, 경로를 하나씩 적은 스크립트, 15:44:30 UTC): `tmp/r7c20`, 내 Isaac 판이 만든 `tmp/carb.h4dne5`(15:39:48Z)·`tmp/tmp29cozvkk`(15:40:06Z)·`cache/pyc_r6/data/harvest/tmp/tmp29cozvkk`·`cache/pyc_r6/data/harvest/tmp/r7c20`, `ir/kitcache/cyclo-r7c20_standard`(208 MB). 판별: Isaac 앞뒤 `tmp`·`pyc_r6`·`kitcache` 목록 차이(새 항목은 이것뿐), 생성 시각이 내 Isaac 창(15:39:47–15:43:55Z) 안, `/proc/*/fd` 전수에서 여는 프로세스 없음. 끝에 `tmp`·`kitcache`의 r7c20 항목 0, 내 프로세스 0.
- 로컬 임시(`D:\tools\scratch_qdd\r7c20`: `src.tar`, `repo/`, `pt/`, `tmp/`, `tv/`, `pod/`, 스크립트)는 다음 순회 대조용으로 남김(C: 아님). `canary20.py`의 `canroot/`는 스크립트가 지움.
- 절차 사고: 없음.

## 7. 다음 순회 전에 할 일 (제안)
1. (선택, NOTE) N9: `steering_representation:33`·`:81` 표시를 표 칸 안으로 옮기거나 표 아래 한 줄 표시. N12: `handoff.md:113` 문구에 "정본 범위 줄 중에서는". N13: E-Astra-motion 정의 문서 경로. N14: `draft-log.md:422` 탭 → `` `\tentative` ``. N15: `handoff.md` 끝 줄바꿈.
2. 다음(21회차) 대상은 7e0aeba 뒤 커밋(f4f6a49 E-TC 판정, f00cb59 정본 §83)과 그 뒤 코드 변경이다. **코드가 바뀌면(작업 트리의 `se2e_data.py`·`astra_motion/` 등이 커밋되면) 연속 무결은 0부터 다시 센다**; 문서·결과만 더해지면 이 PASS가 연속 무결 1회로 남는다.
3. 21회차에서 확인할 것: E-TC 판정(S18)을 등록 판정 스크립트(`992d3e20…`)로 파드 예측 파일에 다시 돌려 `verdict.json`과 대조, 정본 §83이 사전 등록 §6 규칙·§7 표지와 맞는지, 채택된 움직임 줄의 런타임 경로(§83 "runtime follow-up")가 SCOPED로 기록됐는지.
