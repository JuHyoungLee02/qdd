# R7 객관 검증 순회 — 10회차 (cycle 10, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님, `r7c9_fixes.md` 대조표에 기대지 않고 사전 등록 원문에서 대조표를 새로 만들고 경계값을 실제 함수로 다시 돌림). 작성 2026-09-25 07:00 UTC 무렵(`date -u`; 로컬 시작 06:20 UTC, 파드 첫 명령 06:26:18 UTC, 파드 정리 끝 06:51:23 UTC).
- 대상: `D:\qdd` `dev` 커밋 `6522fda`(= 태그 `stage3-r7fix9`, 커밋 시각 2026-09-25 06:20:20 UTC). 다른 에이전트가 같은 작업 트리에서 재생 결정성 조사를 하고 있어 **작업 트리는 쓰지 않고** `git -c safe.directory=D:/qdd -c core.autocrlf=false archive 6522fda`를 `D:\tools\scratch_qdd\r7c10\repo`에 풀어 검토했다(비교용 `a9b56e3` 사본 `…\r7c10\a9b`). `a9b56e3..6522fda` = 코드 15개(`analysis/{replay,stats}.py`, `canary.py`, `cli_pool.py`, `datagen/gen.py`, `eval/e05.py`, `predicates.py`, `runtime/{calibration,conditions,core,m4,skills}.py`, `sim/{labeler,planner,snapshot}.py`, `stereo/pipeline.py`) + 시험 5개 + 문서(정본 §74, handoff·draft-log·direction-log, `labeler.md`(b68fbf7), `r5_closed_loop.md`·`r6_eval.md`·`r7_fixes.md`·`SUMMARY.md` 표시, `r7_cycle9.md`·`r7c9_fixes.md`). 파드 사본 = 같은 archive + `CODE_VERSION`(tgz sha256 `71414d23…`), 모든 산출 `meta.git.commit` = `6522fda9…`, `meta.code_sha` = `b58c94b29d82347a`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle2.md`–`r7_cycle9.md`, `r7c7_fixes.md`·`r7c8_fixes.md`·`r7c9_fixes.md`, 정본 `00-interfaces.md` §1–§74(§74 메인 보충 포함, 뒤 절 우선; [사용자] 제목 절은 §67 규칙, 논문 .tex는 §70·§74 논문 갱신 항목에 따라 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`M4-overlap-commit.md`(조건·변수 표).
- 분류(9회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋과 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 정본에 없는 것.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(이 보고서 파일만 새로 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c10`(스크립트는 Write 도구로 쓰고 경로로 실행). 파드 = `/data/harvest/tmp/r7c10`(코드 사본·pytest·산출, 1.1 GB)와 작업이 만든 `ir/kitcache/cyclo-r7c10_standard`(208 MB)·`cache/pyc_r6/data/harvest/tmp/{r7c10,tmpewtc0ci3}`·`tmp/{carb.PXR5Lp,tmpewtc0ci3}` — 시작 전 목록(`pod_before.txt`)과 생성 시각(06:30:39–06:30:54 UTC = 내 Isaac 판 시작)으로 가려 **모두 지웠다**(06:51 UTC). 같은 시간대의 다른 새 항목(`kitcache/cyclo-replaydbg_*`, `tmp/carb.*`·`tmp/tmp*` 06:32–06:43 UTC)은 재생 조사 에이전트 것이라 두었다. GPU: 단계 B 학습·CUDA 시험 = GPU 2(렌더 없음), Isaac = GPU 1, GPU 0(재생 조사 Isaac)·GPU 3 건드리지 않음, 끝에 0–3 = 456/1/1/1 MiB. 시드 DEV만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 1건에서 `=dev`만). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. 남의 프로세스 건드리지 않음. **내 실수는 §4 N9**.

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 1 |
| DOC | 1 |
| SCOPED | 11 |
| NOTE | 10 |

9회차 수정(γ = 정확히 2/3 공유, C2 = VLM Stream, 방향 Holm, 반올림 없는 판정 + `CMP_EPS`, near ≤ 5 cm)은 손 계산 98/98과 무작위 대조로 **모두 문서대로 동작한다**(§6.1: 가짜 세계 폐루프 300판 × C0–C6에서 C0·C1·C4 = a9b56e3 **300/300 비트 동일**, HEAD에 γ = 소수 0.67을 주면 C3·C5·C6도 300/300 비트 동일 → 차이는 γ 경계에서만). 완료 정의 1–5도 모두 다시 돈다(§6.3). 그러나 대조표를 원문에서 다시 만들면서 H 행을 조건 문장 전체와 나란히 보니, **E-M4의 H = 1 칸이 사전 등록 정의("같은 스텝을 시각을 당겨 2~3회 묻기")를 구현하지 않아 스텝마다 표가 1개뿐이고 (a) 합의가 구조적으로 일어나지 않는다**(D1). 문서는 §74 메인 보충(06:20 UTC)으로 닫힌 N4 척도 규칙을 handoff가 아직 "[결정 필요]"로 적은 1건(D-1). 연속 무결은 **0회 그대로**.

---

## 1. DEFECT

### D1. E-M4 H = 1 조건이 사전 등록 정의("같은 스텝을 호출 시각을 앞당겨 2~3회 묻기")를 구현하지 않는다 — H = 1이면 스텝당 표 1개, (a) 합의 불가
- 사전 등록·정본: 정본 §2 `00-interfaces.md:18`("H는 1과 3을 비교한다(E-M4). … **H=1일 때 M4 (a)의 여러 표는 '같은 스텝을 시각을 당겨 여러 번 묻기'로 얻는다**"), `M4-overlap-commit.md:188`(§4.1 "H=1은 M3 원안 …, 이때 같은 스텝의 여러 표는 **호출 시각을 스텝 시작보다 앞당겨 같은 스텝을 2~3회 묻기**(질문 문구 동일)로 얻는다"), `:189`("H=1이면 앞당김 횟수만큼"), `:194`(J3, H=1의 앞당긴 표는 합의 표), `:273`(§4.4 H 행 "H=1은 호출 시각 앞당기기로 표 수 확보"), `:349`·`:365`(판정 7 "C5(H=3)가 C5(H=1)보다 …"), E-first `:236`(§2A.3 재생 = "H=1 '같은 스텝을 시각을 당겨 2~3회 묻기'(M4 §4.1)를 흉내"), `:183`·`:197`(§2.6·§2.7 판정 4: "`lead_max` ∈ {1.0, 1.5} s부터 `d_p95` 전까지 T_c 간격으로 같은 스텝을 묻는 H=1 방식 … 스텝당 표 수 중앙값 ≥ 2이면 LA-2 확정이 성립 가능"), E §4.12 `:487`.
- 코드: `harvest/eval/closed.py:151-160` `m4_config(cond, H)`와 `--m4-h`(:283)는 `M4Params.H`만 바꾼다. 스케줄러(`runtime/core.py:413-421`)는 T_c마다 호출하고 각 호출의 대상은 `CommitLedger.target_slots`(`runtime/m4.py:152-154`) = "시작이 `t_send + d̂` 이후인 첫 스텝부터 H개"뿐이라, H = 1이면 연속 호출이 연속 스텝을 하나씩 맡는다 — 같은 스텝을 앞당겨 다시 묻는 경로(`lead_max`)가 없다(`lead_max`는 오프라인 `analysis/latency.votes_per_step`에만 있음). E0.5 재생(`eval/e05.vote_steps`)은 사전 등록대로 스텝마다 앞선 스냅샷 3개를 표로 쓰므로, **재생이 미리 재는 H=1 "C3의 합의 부분"과 런타임 H=1이 다르다**(9회차 D1과 같은 모양).
- 확인(원장 직접):
  - `D:\tools\scratch_qdd\r7c10\h1_check.py`(가짜 세계, 모의 선택기, 2,000틱): C5·C3 **H = 1 → 스텝당 표 {1: 60}(지연 0.15·0.3 s)·{0: 2, 1: 57}(0.6 s), 확정 0, 확정 실행 0 / 가확정 실행 57–60**; H = 3 → 스텝당 표 대부분 2–3, 확정 288–299(`h1_check.txt`).
  - 무작위 대조 300판(§6.1)의 H = 1 판 145개 중 113개가 C3·C5에서 확정 0(나머지 32개는 흔들림·d̂ 변화로 가끔 두 호출이 같은 스텝에 걸린 경우).
  - **파드 Isaac 폐루프**(`closed --conditions C5,C2 --m4-h 1`, GPU 1): C5 결정 호출 42회, 표 결과 `tentative` 190 · `dropped_epoch` 20, **`commits` 0**, 호출당 슬롯 1.
- 영향: 사전 등록 판정 7(H 선택)·H = 1 칸의 C3·C5·C6·E-M4 판정 2((a) 기여)가 "(a)가 구조적으로 꺼진 H = 1"을 재게 된다. W 유예 창도 두 번째 표가 없어 작동하지 않는다. 정본 §73 N8은 "`--m4-h {3|1}` … 사전 등록 'H 1과 3 비교'"로 인자만 기록했고, H = 1의 표 수 확보 방식(앞당김, `lead_max` — E0이 정할 열린 값)이나 "런타임 H = 1은 앞당김 없음"을 정한 정본 결정은 없다(정본 `grep "앞당|lead_max"` → §45 하트비트 앞당김 등 다른 뜻뿐). 9회차 대조표 행 51("H 1과 3 비교 … 호출당 슬롯 [1] … 일치(§73)")은 H 값이 전달되는지만 보고 스텝당 표 수를 보지 않았다.
- 고칠 길(제안): H = 1이면 스텝 시작 `lead_max` 전부터 고정 구간 경계(`t_start − d̂`) 전까지 T_c마다 **같은 스텝**을 묻는 스케줄(M4 §4.1, E §2.6의 `votes_per_step`와 같은 규칙)을 넣고 `lead_max`(사전 등록 후보 {1.0, 1.5} s, E0 뒤 확정)를 정본에 적는다; 또는 "런타임 H = 1 = 앞당김 없음(스텝당 1표)"을 정본 결정으로 적고 판정 7·2의 해석에 반영. 어느 쪽이든 C0–C6 H = 3 동작 불변을 무작위 대조로 보일 것.

## 2. DOC

### D-1. `docs/handoff.md:101` — N4 척도 규칙을 "**[결정 필요: 메인 세션]**(코드 없음)"으로 적음(정본 §74 보충이 이미 결정)
- 정본 §74 보충(`00-interfaces.md:643`, "2026-09-25 06:20 UTC, 메인 결정")이 "**N4 → (가) 비례 규칙 채택**: STALE_MAX = 1.5 s × d*_p95 / d_p95(E0)"로 닫았는데, 새 세션이 가장 먼저 읽는 handoff의 9회차 줄(`:101`, "→ 수정(06:16 UTC …): … N4 E-M4-lat 지연 점의 STALE_MAX = 지연에 맞춰 다시 잡되 척도 규칙은 **[결정 필요: 메인 세션]**(코드 없음)")은 그대로이고 해결 표시가 없다. 머리 `마지막 갱신: 2026-09-25 06:17 UTC`(`:3`)도 보충(06:20)·커밋(06:20:20) 이전이다. 같은 사실: `r7c9_fixes.md:15`(N4 행 "척도 규칙 … **열림 → [결정 필요: 메인 세션]**", 현재 상태 표) — 해결 표시 없음. (`direction-log.md:57`·`draft-log.md:447`의 "메인 결정 대기"는 05:20 시점 기록 줄이라 NOTE 범주, `r7c9_fixes.md:88`은 "적었다" 과거 서술이라 사실.)
- 선례: 5회차 P1(handoff 머리 상태가 뒤 정본 절을 반영 안 함 → DOC), 정본 §71 grep 목록 "`[결정 필요]`를 후속 정본 절과 대조".

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(정본 §71 보충) — 로컬·파드 모두 `tests/runtime/test_latency_ctrl.py:11` 1개 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66) — `gen gen --seeds 10005-10006` 확인 인자 없이 거부(§6.4).
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4(이번에 `e05 --split test`도 더함).
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8 — `core.py` Astra patch/replace = epoch만(`core.py:376`, 무변경).
- S6. Astra 카나리 id "none" — 파드 C5·C2 판 `astra` 행 2/2 `canary_id: "none"`.
- S7. S-E2E 체크포인트 런타임 tau 마스크 차이(`r7_fixes.md` §7).
- S8. CONTRADICT-soft(§68 K6·§69) — `measure.py` 무변경.
- S9. §73 D5 M4 설계 확장(경계 직후 W 2·γ 1.0, 큐 임계 g, 장면 변화 조기 호출, 미확정 실행 (b) 엄격화) — `m4.py:26-31` "Not implemented".
- S10. §73 N5 E1 범위(`calib` = 판정 1·8).
- S11. (새) §74 보충 N4 (가) 비례 STALE_MAX는 "구현은 지연 큐와 함께 E-M4-lat 준비 때" — 지연 큐가 없어 E-M4-lat 경로 자체가 없고 주 지연 동작은 1.5 s 그대로(`m4.py:63`). 또한 런타임에 없는 조건 C2'·C2'-S·C2-match·C3'·C3''·C5-A3·C-FIX·C5'(`conditions.py:14-15`, `closed.json` `meta.not_in_runtime`, `r6_eval.md:46`) — E-M4 본 실험 전 구현 대상, 완료 정의 1–5와 무관.

## 4. NOTE
- N1. **나이 비교의 부동소수 경계**: `m4.on_vote`(`:181`)·`decision`(`:266`)의 `now − t_state > stale_max`는 원시 비교다. 100 Hz 틱 시각(소수 6자리)에서 정확히 5.00 s인 나이가 5.0보다 크게 계산되는 틱 위치가 6,000개 중 **372개**, 1.50 s는 **174개**(`hand_checks.txt` INFO). 즉 C2의 5 s 타임아웃이 약 6%의 위치에서 한 틱(10 ms) 일찍 걸리고, 지연이 정확히 1.5 s인 모의 판에서는 C5 표 일부가 버려진다. 연속 지연에서는 측도 0이고 효과 ≤ 10 ms라 결함으로 보지 않으나, `r7c9_fixes.md` §4 행 48 "나이 1.5는 유지"는 틱 위치에 따라서만 참이다. E-M4-lat에서 비례 STALE_MAX(§74 보충)를 구현할 때 정수 틱 또는 `CMP_EPS` 식 허용으로 맞출 것을 권한다.
- N2. `share_at_least(n, v, 0.67)`(소수)은 이진 값 0.67000000000000004로 비교해 2/3뿐 아니라 **67/100도 불성립**이다(`hand_checks` "share 67/100 float 0.67" = False). 정본 §74 "명시적 소수 0.67을 주면 문자 그대로(> 2/3)"는 방향은 맞지만 "문자 그대로(= 67/100)"로 읽히면 부정확 — 절제 γ는 반드시 "2/3"(또는 `Fraction`)으로 줄 것. 코드 안에서 γ를 소수로 주는 곳은 시험 `tests/runtime/test_m4.py:80`(3/4 경우라 무관)뿐.
- N3. 9회차 N4의 뒤처리: 정본 §74 보충이 (가)를 채택 — 코드 영향 없음(S11).
- N4. near "< 5 cm" 옛 서술: `docs/stage3/results/e3st.md:66`("들어가기 < 5 cm … (정본 §7)" — 정본 §7은 원래 ≤ 5 cm), `planner_dev.md:102`(P1 구현 "< 5 cm"), 옛 계획서 `2026-09-24-stage3-experiments.md:314`·`:400`, `tests/test_predicates.py:22` 주석(0.049 m라 참인 서술). 모두 2026-09-24 실행 기록·계획 초안이고 §74 변경은 정확히 5.000 cm에서만 달라져 NOTE — 다음 문서 정리 때 [정정 R7 9회차, §74] 표시 권장(§69 절차).
- N5. 단계 B S-E2E 스모크(6스텝, 검증 4개): dec 3.526 → 2.927 → 2.440은 줄지만 fm 2.494 → 2.784 → 3.118은 늘었다(§6.3). 재적재 차 0.0. 소규모 확인이라 판정 없음(§56) — S-E2E 사전 등록 때 "손실 감소" 기준에 어느 손실을 볼지 적을 것.
- N6. 카나리 세트 `dev_v1` = 3편(9회차 N2 그대로), 이번 판 `meta.canary` = `cn20260924_mock_ae0d1a`(`stale: true`, §68대로).
- N7. 논문 `paper/sec/3_method.tex:103` 경계 적응형 서술·γ 0.67 — §74 논문 갱신 항목(§70 보류와 같음). D1 수정 시 H = 1 서술도 같은 목록에 넣을 것.
- N8. 9회차 N7–N12 그대로: 옛 계획서 초안 코드(`:1430` `la2(votes, gamma=0.67)`, `:1480` `>= gamma - 1e-3`), E §3.6 반올림 [가정]·E0.5 분당 400 [가정](로컬 서버라 해당 없음), `handoff.md:27`·`:46`·`:55` 날짜 붙은 옛 절, `CLAUDE.md` Jev 서술, `stageb_data.py`(§71 해시 보호), 논문 vLLM 서빙(§70), `r7_sweep6.md` §3 열린 항목, 정본 §37 102°(§47이 덮음), TEST2 1150–1299가 `splits.RANGES`에 없음, RD 1차판 Score [가정], 자연/과표집 가중치 보고, S-E2E 사전 등록 항목 — 모두 열림, 완료 정의 1–5를 막지 않음.
- N9. **내 실수 2건**: (a) 06:37 UTC 무렵 로컬 Git Bash에서 빈 heredoc을 `python -`에 넣는 명령(`python - <<'EOF'` … `EOF`, 내용 없음)을 실행했다 — 지시 위반. 명령이 멈춰 하네스가 배경으로 옮겼고 즉시 `TaskStop`으로 멈췄다. 만든 파일 없음(출력은 하네스 작업 폴더에만). 이후 모든 스크립트는 Write 도구로 쓴 파일을 경로로 실행. (b) 첫 로컬 archive를 `core.autocrlf=false` 없이 풀어(전역 `autocrlf=true`) `test_challenge_cameras.py`의 해시 시험 2개가 CRLF 변환 때문에 실패했다 — 사본을 지우고 `-c core.autocrlf=false`로 다시 풀어 재실행(§6.5, 실패 0). 그 첫 실행이 공용 `D:\tools\scratch_qdd\pytest_tmp\p34800`(conftest의 프로세스별 폴더)을 만들어 끝에 지웠다.
- N10. 파드 공용 캐시: `/data/harvest/tmp`의 다른 에이전트 항목(재생 조사 `replaydbg`, vLLM `vllm_dist_*` 등)은 건드리지 않았다. `/data` 밖: `find / -xdev -newermt "06:25 UTC"`(`/proc`·`/sys`·`/dev`·`/run`·`/data` 제외) → 마운트 지점 `/data`뿐, 루트에 "C:" 폴더 0.

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦)

`prereg.json` 해시: 파드 모든 산출 `meta.prereg.check` = "OK"(e05·rd·calib·closed, 해시 5개 = `prereg.json`, `utc` 다음·`model` 앞). 사전 등록 문서(`E-first`·`EVAL`·`M4`·`prereg_labeler`·`prereg.json`)는 `a9b56e3..6522fda`에서 바뀌지 않았다. 코드 줄은 `6522fda` 기준. "확인" 열: 로컬 = `D:\tools\scratch_qdd\r7c10\hand_checks.py`(98/98 PASS), `h1_check.py`, `char_run.py`·`char_cmp.py`; 파드 = §6.3.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인 | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 / R2_TRAIN 10000–59999 (E :115-120, 정본 §66) | `eval/splits.py:13-15`, `datagen/gen.py` | `RANGES` 끝값 손 확인, 파드 가드 13건 rc 1 | 일치(TEST2 N8) |
| 2 | POOL 120 × 10 = 1,200, 경계 30% 과표집 (E :121) | `sim/snapshot.py` | 코드(무변경) | 일치(가중치 N8) |
| 3 | `ambiguous` = 히스테리시스 띠 술어 (E :121; M1 :140 "≤ 5 cm 들어가기 / 6 cm 나가기") | `sim/snapshot.py:97` (5, 6] cm, `predicates.py:59` | 0.05 아님·0.055·0.06 참·0.0600001 아님; 파드 calib `heldout.ambiguous.n` 11 | 일치(§74) |
| 4 | 분할·재표집 = 에피소드 (E :122, :130) | `calib.py`, `e05.py`, `rd`, `canary.py:25-28` | 파드 `meta.bootstrap.unit` 4종 | 일치 |
| 5 | 성공 1 s 연속·60 s·낙하 (E :107) | `config.py:12-13`, `sim/planner.py:34`(`≥ 1.0 − 1e-9`) | 코드 | 일치 |
| 6 | 모든 호출 요청 해시·이미지 해시·카나리 id (E :125-127, 정본 §28) | `core.py:214-217,271`, 워커 행 | 파드 C5 `call` 42/42·C2 39/39 64자리 hex·이미지 {cam_head, cam_wrist_right}·`cn20260924_mock_ae0d1a`, `astra` 2+2행 {cam_head}·"none" | 일치 |
| 7 | 95% 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `stats.py:4,32-72` | 파드 4개 `meta.bootstrap` n_boot 10000·0.95·percentile·seed 0 | 일치 |
| 8 | 짝 비교 = 같은 시드 짝 (E :130) | `stats.cluster_diff_ci`, `closed.aggregate` | 코드(무변경) | 일치 |
| 9 | Holm 판정 2 "LA-2 또는 C2''"(하한 > 0) (E :131, :257) | `e05.py:216-224` `direction="greater"`, `stats.py:87-110`, `replay.py:33-50` | 음의 가설은 기각 아님·다음 수준 안 풂(표본 자료: la2 음, c2pp 97.5%에서 판정), 양측과 대조 | 일치(§74 N1) |
| 10 | Holm 판정 10 블록 쌍(방향 없음) (E :265) | `e05.py:200-236` 양측 | 블록 1 < 0 쌍도 기각 | 일치(§74) |
| 11 | Holm 카나리 "하한 > 0, Holm" (E :139, 정본 :264) | `canary.py:31-55` `direction="greater"` | 바닥 아래 질문 4개 기각 없음, dir_xy는 1단계 0.99에서 판정 | 일치 |
| 12 | 판정 절 해시·시각을 실행 기록 첫 줄에 (E :133) | `common.py` `prereg_meta` | 파드 5개 산출 check OK | 일치(§73) |
| 13 | 카나리 기준일 = 처음 돌린 날 (E :140) | `eval/canary.py` | 코드(무변경) | 일치 |
| 14 | "모델 식별 필드가 바뀌어도 같은 처리" (E :139) | `calibration.py` 지문 결속 | 정본 §73 | 정본 기록 |
| 15 | E0.5 표 = t_s − d_p95 − {0, .33, .66} (E :236) | `e05.py:44-56`(t ≤ t_s − d_p95 + 1e-9) | 코드 | 일치 |
| 16 | 같은 시각 K = 3 (E :238) | `e05` 기본 | 코드 | 일치 |
| 17 | newest / LA-2·γ 0.67 = 3표 중 2(아니면 첫 표) / C2'' / C2' (E :240) | `replay.py:10-26`, `e05.py:59-63` → `m4.share_at_least` | `a,b,a` → a·확정, `a,b,c` → 첫 표 a·미확정, 같은 함수 객체 | 일치(§74 D1) |
| 18 | `C_flip` 두 식, 직전 창 (E :242) | `e05.py`, `m4._update_flip` | 정본 §73 | 정본 기록 |
| 19 | A0–A4, 층, 바닥 층 × 시간 블록 (E :245-246) | `options.py`, `e05` | 정본 §73 | 일치 |
| 20 | 성공·섭동 궤적 따로, 섭동 창 (E :250) | `e05` 창 1 s | 정본 §73 | 일치 |
| 21 | 판정 1–3 문턱 5%·+2%p (E :256-258) | `replay.py:39-50` `below`·`at_least`, 입력 `_mean_x` `e05.py:419-422` | flip 500/10001 → 판정 1, 1/20 → 판정 3, 이득 1/50은 "< 2%p" 아님, lo 0.0 → 판정 2 아님 | 일치(§74) |
| 22 | 판정 4 ×2·AUROC 0.7·0.03 (E :259) | `replay.py:51-56` | 정확히 2배·0.7 참, 0.83−0.80 → 그 식, 0.8299−0.80 → tv | 일치 |
| 23 | 판정 5 재시험 빼기 (E :260) | `e05` | 코드 | 일치 |
| 24 | 판정 6 < 1% (E :261) | `replay.py:57-58` | 0.01 단서 없음, 0.0099 단서 | 일치 |
| 25 | 판정 7 +2%p·하한 > 0 (E :262) | `e05.py:448-449` | 코드(`at_least`·`above`) | 일치 |
| 26 | 판정 8 하한 > 0, 층별 (E :263) | `e05.py:451-457` | 코드 | 일치 |
| 27 | 판정 9 −2pt 하한·A3 > 바닥·A4 ≥ 5% (E :264) | `replay.py:59-68` | 0.08−0.1 → neutral, A3 lo 0 → 아님, A4 0.05 → C3'' 필수 | 일치 |
| 28 | d_p95 = E0 값, 재실행 규칙 (E :236, :278) | `e05 --d-p95` 0.307(정본 §55) | 정본 기록 | 일치 |
| 29 | E0.5 분당 400 [가정] (E :277) | 없음 | 로컬 서버 | N8 |
| 30 | E1 자료 반분 (E :296 → 정본 §52) | `calib.py` | 정본 §73 | 정본 기록 |
| 31 | ECE = 15 동일 질량 (E :320) | `calibration.ece_mass` | 코드(무변경) | 일치 |
| 32 | 오답 < 30 → 판정 불가 (E :320) | `calibration.py:215` | 30 가능·29 불가 | 일치 |
| 33 | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.py:59-64` | n 1–5000 × α 3개 정확값과 부동소수 순위 불일치 0 | 일치 |
| 34 | log p 1e-6 자름 (E :333) | `calibration.py:20` | 코드 | 일치(N8) |
| 35 | 질문별 온도, 등위 회귀 비교 없음 (E :334) | `calibration.py:42` | 정본 §73 | 정본 기록 |
| 36 | 원 확률: ECE ≤ .03 ∧ T ∈ [0.8, 1.25] (E :335) | `calibration.py:92` | T 0.8·1.25·ECE |0.78−0.75| 참, T 1.2500001·0.7999999·ECE 0.0300001 거짓 | 일치 |
| 37 | 판정 1 (i)–(iv) (E :339) | `calibration.py:210-234`, 값 `judge_values` :140-206 | 모든 문턱 정확히 경계에서 켬, ECE 0.0500001·AUROC 0.749971·적용률 0.1999 끔; 파드 `heldout.judge_values` 있음 | 일치(§74) |
| 38 | 판정 7 재보정 결속 (E :345-346) | `calibration.py` | 코드 | 일치 |
| 39 | 판정 8 J5, 적합 400 미만 "보장 없음" (E :347) | `calibration.py:230-233` | 경계 켬, 단일 정확도 0.9499 끔, n 400 보장·399 없음 | 일치 |
| 40 | `ambiguous` ECE 제외·따로 (E :359) | `calibration.evaluate` | 파드 `n_ece` 96 + 애매 11 = n 107 | 일치 |
| 41 | E1 판정 2–6 등 | 없음 | 정본 §73 | SCOPED S10 |
| 42 | N_max = ⌈d̂/T_c⌉+1 (M4 :258,:263) — C5; C2는 상한 없음 | `m4.py:146-150` | C5 d̂ 0.307 → 2, C2 ∞; 파드 `dec_inflight` C5 max 2·C2 max 1 | 일치 |
| 43 | γ = 0.67 = 3표 중 2 (E :487, M4 :276, :147) | `m4.py:44-52`, `:252` | 런타임 `a,b,a` 확정, `a,b,c,a` 미확정, γ 1.0 미확정, 소수 0.67 미확정(N2), 무작위 대조 | 일치(§74 D1) |
| 44 | W = 1, W = 0 즉시, W < 0 거부 (정본 §72) | `m4.py:80-81,215-217` | 대조 W ∈ {0,1,2}에서 a9b 동일(C0·C1·C4) | 일치 |
| 45 | 비가역 W+1 (M4 :291) | `m4.py:207,215` | 코드 | 일치 |
| 46 | τ = 1(접촉 근처 0), near ≤ 5 cm (E :487, 정본 §7 :45) | `core.py:42-56`, `m4.py:163-172` | 5.00 cm 참·5.01 거짓 | 일치 |
| 47 | conformal α 0.01·w 5 (E :487) | 정본 §61·§64 | 정본 기록 | 정본 기록 |
| 48 | STALE_MAX 1.5 s (E :487, M4 :288) — C0·C1·C3–C6 | `m4.py:63,181` | 나이 1.5(1.0→2.5) 유지·1.5+1e-6 폐기; 틱 위치에 따라 부동소수(N1) | 일치(N1; E-M4-lat = S11) |
| 49 | C2 = VLM Stream: 상한 없음·실측, 매 틱 가장 새 유효 응답, 늦은 응답도 적용, 5 s 타임아웃 → 기본 행동 (E :495, 정본 :179, M4 :332) | `conditions.py:22`, `m4.py:184-190,260-268`, `core.py:413-415,451-456`, `skills.py:115-121` | 5.0 s 유지·5.0+1e-6 EMPTY/폐기, 시작한 스텝 대상 응답 `newest`(log_only 0), 옛 요청 `older`, 확정 없음; 대조 300판 C2 `dropped_stale`·`log_only` 0, in-flight 최대 8; 파드 Isaac C2 표 195개 모두 `newest` | 일치(§74 D2) |
| 50 | C0·C1·C3·C4·C5·C6 정의 (M4 :329-346) | `conditions.py:20-26` | 무작위 대조 C0·C1·C4 300/300 a9b 동일 | 일치 |
| **51** | **H 1과 3 비교, H=1은 같은 스텝을 호출 시각을 앞당겨 2~3회 묻기 (정본 §2 :18, M4 :188-189, :273, E :236, :183, :197)** | **`closed.py:151-160,283` H만, `m4.py:152-154` `target_slots`, `core.py:413-421`** | **H=1 스텝당 표 1개·확정 0(가짜 세계, 파드 Isaac C5 `commits` 0)** | **불일치 → D1** |
| 52 | n_LA 2 (M4 :275) | `m4.py:249-251` | `a,b,c,a,a` LA-2 확정 | 일치 |
| 53 | 조기 호출은 주기 슬롯을 당겨 씀 (M4 :262) | `core.py:414-421` | 코드 | 일치 |
| 54 | FLIP_TH·θ 게이트 끔 (정본 §6) | `m4.py:64,242` | 코드 | 일치 |
| 55 | 경계 직후 W 2·γ 1.0 등 (M4 §3 #5, §4.3) | 없음 | 정본 §73 | SCOPED S9 |
| 56 | P1 2 cm·near 5 cm, P2 0.5 s, h_lift 3 cm, tilt 30° (E :420-421, 정본 §7) | `config.py:8-11`, `sim/planner.py:272` 등 `≤` | 코드 | 일치 |
| 57 | 라벨 규칙 적격 ≥ 0.90·0.02 (prereg_labeler :11-12) | `sim/labeler.py:131-142` | 코드(무변경) | 일치 |
| 58 | 폐루프 RD 재표집 = layout 짝 (EVAL :184) | `closed.aggregate` | 파드 `meta.bootstrap.unit` "layout seed …" | 일치 |
| 59 | 주 RD = Score 기반 (EVAL :182) | 성공률 | 1차판 [가정] | N8 |
| 60 | H1/H2/H3 판정 (EVAL :186-190) | 없음 | 기준선 | SCOPED S1 |
| 61 | M4b 자기 사전 등록 2,000회 | `m4b/*` | 정본 §72 예외 | 일치 |
| 62 | E-M4-lat STALE_MAX = 지연에 맞춘 비례 (M4 :378, 정본 §74 보충) | 없음(지연 큐 없음) | 정본 기록 | SCOPED S11 |

### 5.1 9회차 수정 대조표(`r7c9_fixes.md` §4)·9회차 표(`r7_cycle9.md` §5)와의 차이
- **9회차 행 51**("H 1과 3 비교 … 호출당 슬롯 [1] … 일치(§73)") → 이번 행 51 **불일치(D1)**: H 값 전달만 확인하고 사전 등록이 정한 H = 1의 표 수 확보 방식(앞당김)과 스텝당 표 수를 보지 않았다. `r7c9_fixes.md` §4는 이 행을 다루지 않았다.
- 행 48: `r7c9_fixes.md` "나이 1.5는 유지"는 틱 위치에 따라서만 참(N1, 결함 아님).
- 행 43: 소수 0.67의 뜻(N2).
- 새 행 62(§74 보충). 나머지 행은 `r7c9_fixes.md` §4의 21개 행과 결론이 같다(줄 번호는 6522fda로 다시 찾음).

## 6. 확인한 것 (근거)

### 6.1 9회차 수정의 독립 확인 (과제 2)
- 손 계산 `hand_checks.py` → **98/98 PASS**(`hand_checks.txt`): γ(정수 교차 곱, 2/3·4/6·66/99 참, 3/5·2/4·66/100 거짓, 소수·문자열 "0.67" 거짓, `GAMMA` JSON "2/3"), 런타임·재생·`e05.apply_rules`가 **같은 함수 객체**, C2 원장(5 s 경계·늦은 응답·옛 요청·확정 없음·n_max ∞), 조건 표(C2만 stream·5 s, 나머지 1.5 s), 방향 Holm(합성 구간·실제 `gain_holm`·`canary_compare`), 판정 10 양측, `judge_e05`·`judge_question`·`fit_question` 문턱 경계, J5 순위, near·띠·`near_contact`.
- **무작위 대조**(`char_run.py`, 9회차 수정 에이전트의 스크립트와 따로 씀: 다른 난수 씨앗 1010, 지연 {0.2, 0.33, 0.5, 0.75, 1.0, 1.4, 1.6, 2.5} s + 흔들림(0.2–0.4 s, 5% 1.3–1.8 s), **H ∈ {1, 3}**, W ∈ {0, 1, 2}, 답을 15%·30% 확률로 다른 보기로 바꾸는 잡음 선택기(합의 경계를 자주 만듦), 머그·트레이·TCP 무작위, P1 비슷한 이동, 1,200–2,600틱) **300판 × C0–C6**, 비교 = 행동 바이트 sha256·원장 counts·슬롯·실행 계정·호출 수·단계·epoch(`char_cmp.py`):
  - HEAD 대 a9b56e3: **C0·C1·C4 300/300 비트 동일**; C2 0/300(의도); C3·C5 203/300 동일(다른 97판은 모두 H = 3, 행동 바이트는 4판만 다름), C6 256/300(행동 바이트 2판).
  - HEAD + γ = 소수 0.67 대 a9b56e3: **C3·C5·C6 300/300 비트 동일** → HEAD의 C3·C5·C6 차이는 γ 경계에서만 온다(§74 D1 주장과 같음).
  - C2(HEAD): `dropped_stale` 0·`log_only` 0, 실측 in-flight 최대 8(상한 없음). 지연 1.6 s에서 끝까지 간 판 a9b 0/45 → HEAD 10/45, 2.5 s는 둘 다 0/24.
- **Isaac에서 새 C2 경로**: 파드 `closed --conditions C5,C2 --m4-h 1 --seeds 7`(GPU 1) → 두 칸 모두 성공 1.0, C2 표 195개 모두 `newest`, `dropped_stale`·`log_only` 0, `summary.dec_inflight` {max 1, mean 1.0, n_sends 40}; C5 `dec_inflight` {max 2, mean 1.093, n_sends 43}(모든 조건에 기록, §74 (iv)).

### 6.2 9회차 이후 바뀐 기록
| 위치 | 주장 | 확인 |
|---|---|---|
| `handoff.md:101` | 9회차 수치, 수정, 로컬 841/11·파드 883/3, 연속 0 → 10회차 | 수치 모두 이번 판과 같음; N4 "[결정 필요]"는 D-1 |
| `handoff.md:3`·`:5`·`:83` | 정본 §1~§74 | 맞음(머리 시각 06:17 < 보충 06:20 → D-1) |
| `direction-log.md:57`, `draft-log.md:447` | 9회차 판정·수정 | 보고서와 같음(05:20 시점 줄) |
| 정본 §74 D1·D2·N1·경계·보충 | 코드 줄·동작 | 코드와 맞음(§5 행 3, 9–11, 17, 21–27, 36–37, 43, 46, 48–49) |
| `r5_closed_loop.md:33`·`:36`, `r6_eval.md:46-47`, `r7_fixes.md:45`, `SUMMARY.md:287`·`:589` | [정정·해결·SCOPED R7 9회차] 표시 | 표시 있음 |
| `labeler.md`(b68fbf7) | 풀 결과 라벨 120편 확정, 재생 > 1 mm 행 무효(조사 중) | 기록 문서 추가, 코드 무변경 — 판정 영향 없음 |

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st`로 R2 DEV `/data/harvest/r2/dev/*/*/P0` 전 편 `validate_episode`: **36/36 errors 없음**, 모두 DEV, 성공 mug_tray 12/12·mug_marker 12/12·bottle_tray 8/12. LeRobot 내보내기 시험 **6 passed**(06:37 UTC). |
| 2 모델 | 충족 | **단계 B S-E2E**(GPU 2): `stageb_train train --data se2e --run r7c10_se2e --max-train 40 --max-steps 6 --batch 2 --max-val 4 --eval-every 3 --reload-check --seed 44` → rc 0(06:29:59–06:30:38 UTC), 검증 dec 3.526 → 2.927 → 2.440(fm은 N5), `save_load` `max_abs_action_diff` **0.0**, 재적재 전후 eval 같음. CUDA 시험(GPU 2, `tests/train` + `test_fused_action.py`) **102 passed**. |
| 3 폐루프 | 충족 | 모의 `closed --model mock --split dev --seeds 7 --conditions C5,C2 --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c10 --m4-h 1`(06:30:38–06:33:14) → `CLOSED_DONE`, C5·C2 성공 1.0. 로그 행: `call` 42 + 39행 전부 64자리 hex `request_sha256`·`image_sha256` {cam_head, cam_wrist_right}·`canary_id` `cn20260924_mock_ae0d1a`, `astra` 2 + 2행 hex·{cam_head}·"none". `meta.bootstrap` n_boot 10000, `meta.prereg` OK, `meta.m4_H` 1(스펙도 1, 호출당 슬롯 1). (H = 1 칸의 합의 부재는 D1.) |
| 4 평가 | 충족 | 모의 한 명령(`venv_vllm`, GPU 없음): `e05 --data jsel_dev/P0,P1 --split dev --episodes 2` → `E05_DONE`(claim `a_as_stabilizer`, `j2_gain_holm` la2 기각 없음 lo −0.1029·level 0.975, `judge_input` 반올림 없는 값), `rd … --episodes 1` → `RD_DONE`, `calib --fit-data pool --fit-split pool --heldout jsel_dev/P0 --heldout-split dev --episodes 4` → `CALIB_DONE`(질문별 `heldout.judge_values` 있음, `meta.ece` 애매 제외 문구). 모두 rc 0, n_boot 10000, prereg OK. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·카나리·시드·모델·부트스트랩·사전 등록 해시·`m4_H`, 정리 뒤 흔적 없음(N10). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`; 거부 뒤 출력 폴더 없음 — "no guard output dirs")
- `e05 --split cal`, `calib --fit-split cal`, `rd --split test`, `e05 --split test`, `closed --split test --seeds 1000`, `closed --split cal --seeds 549` → "--split X refused: set HARVEST_ALLOW_SPLIT=X (main session only …)". `closed --split dev --seeds 30`·`--seeds 1149` → "not in split dev range(0, 30) (refused, never opened)". `--isaac-gpu 2` → "0 or 1 only (GPU 2 never renders)". `--m4-h 0` → ValueError. `--conditions C2p` → "runtime has [C0…C6]". `HARVEST_ALLOW_SPLIT=dev closed --split test --seeds 1000` 거부. `gen gen --seeds 10005-10006` → "R2 generates DEV 0-29 only (… --confirm-train)". **13건 모두 rc 1.**

### 6.5 A. 테스트
- 로컬(`D:\tools\scratch_qdd\r7c10\repo`, `python -m pytest -q -rs -p no:cacheprovider --basetemp=…\r7c10\pt1`, `PYTHONDONTWRITEBYTECODE=1`): EXIT 0, **841 passed · 11 skipped**(진행 표시 841, 건너뜀 요약 11 = torch 없음 7, inspect_robots 2, pyarrow 1, TODO(P3) 1), F·E 0.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, TMPDIR·pyc·카나리 루트 = scratch, 06:28:02–06:29:25 UTC): **883 passed, 3 skipped**, EXIT 0(건너뜀 CUDA 없음·pyarrow·TODO(P3), 경고 1). 파드 CUDA 102 passed, LeRobot 6 passed.

### 6.6 같은 사실 grep (과제 3, `D:\tools\scratch_qdd\r7c10\sweep.py` → `sweep.txt`, 추적 파일, `third_party/` 제외, 정정 표시 유무 분리)
- `C2 = newest` 계열: `r6_eval.md:46`([정정 R7 9회차] 표시)뿐 — 0.
- C2 + 1.5 s/N_max/STALE: 정본 §74·handoff·draft-log(9회차 기록), `STAGE2-CLOSE.md:178`(다른 뜻) — 0.
- `>= 0.67`·`gamma - 1e-3`·`gamma=0.67`: 옛 계획서 초안(N8), `m4.py:27` 머리 설명("E §4.12 … gamma=0.67" 사전 등록 인용), `tests/runtime/test_m4.py:80`(N2), `paper/…:103`(N7) — 현재 코드 경로 0.
- Holm 양측 + 판정 2/카나리: 기록 줄뿐 — 0.
- 반올림 뒤 문턱 비교(`round(...) >= 0.x`): 0.
- near `< 5 cm`: N4.
- 띠 `5–6 cm`: 정본 §73(옛 절, §74가 (5, 6]로 덮음), `pool.md:17`, `snapshot.py:90` 머리 설명(띠 이름) — 결함 아님.
- H = 1 앞당김·`lead_max`·`--m4-h`: 사전 등록 문장 9곳과 오프라인 `analysis/latency.py:85`뿐, 런타임 구현 0 → **D1**.
- `[결정 필요]`·"결정 대기" + N4: **D-1**(`handoff.md:101`, `r7c9_fixes.md:15`), 기록 줄 2개(NOTE).
- `dec_inflight`·`CMP_EPS`: 코드·정본 §74·시험만, 서술 일치.
- 정본 범위 `§1~§N`: `handoff.md:3`·`:5`·`:83` = §74(맞음).
- `마지막 갱신`: `handoff.md:3` 06:17 UTC(D-1).
- `GPU 2` + 금지: 모두 "렌더 금지" 뜻 — 0.
- 카메라(§47): 이번 변경 파일에 카메라 서술 없음; 폐루프 이미지 키 {cam_head, cam_wrist_right}(§57).
- 구현 이름 대조: `share_at_least`(런타임 `:252`·재생 `:20`·`apply_rules :62` 모두), `agree == "stream"`(원장 `:184,:240,:264`, `core.py:451`), `n_max_cap`, `inflight_at_send`, `redecide`·`moved`, `direction="greater"`(`gain_holm`·`canary_compare`만, `block_diff_holm` 기본), `at_least/at_most/below/above`(판정 입력), `target_slots`(D1).

### 6.7 F. 규칙·위생
- 저장소: 작업 트리는 읽지 않고 쓰지 않음(archive만), 이 보고서 한 파일만 추가. 로컬 C:: 시작 뒤 바뀐 것은 하네스(`.claude`, `.claude.json`, `AppData\Local\Temp\claude\…`)와 이 저장소와 무관한 파일(`Temp\wstest.py` = 다른 프로젝트, 이전부터 있던 앱 `.tmp` 캐시) — 이 저장소 산출물 0.
- 파드: §4 N10, 내 프로세스 0(끝에 `ps`), 재생 조사 Isaac(GPU 0)·`/data/harvest/data`·`r2/dev`·`canary`는 읽기만.

## 7. 다음 순회 전에 할 일 (제안)
1. **D1**: H = 1의 표 수 확보(스텝 시작 `lead_max` 전부터 T_c마다 같은 스텝을 묻기, M4 §4.1·E §2.6)를 구현하고 `lead_max`(사전 등록 후보 {1.0, 1.5} s, E0 뒤 확정 — 그 전 기본값)를 정본에 적거나, "런타임 H = 1 = 앞당김 없음"을 정본 결정으로 적고 판정 7·2 해석에 반영. H = 1 스텝당 표 수 ≥ 2 시험과 H = 3 동작 불변 대조를 함께.
2. **D-1**: `handoff.md:101`·`r7c9_fixes.md:15`에 [해결: 정본 §74 보충 06:20 UTC, (가) 비례] 표시, handoff 머리 시각 갱신.
3. N1·N2는 E-M4-lat·γ 절제 구현 때 함께(정수 틱 또는 허용 오차, γ는 "2/3"로).
4. 대조표 점검 방식: 조건 **변수 행**(H·W·γ·τ)도 값 전달뿐 아니라 그 변수가 사전 등록에서 만들어야 하는 **결과**(스텝당 표 수, 확정 가능성)를 원장에서 세어 볼 것.
