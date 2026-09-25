# R7 9회차 지적 수정 (DEFECT D1·D2, DOC D-1, NOTE N1·N4·N5·N6, 사전 등록 수치 경계 대조)

- 작성 2026-09-25 06:16 UTC(`date -u`). 대상 `D:\qdd` `dev` HEAD `a9b56e3` + 작업 트리(커밋·푸시 안 함 — 메인 세션). 입력 보고서 `docs/stage3/results/r7_cycle9.md`(판정 FAIL, DEFECT 2, DOC 1).
- 원칙: 사전 등록(`E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`, 조건 정의 `M4-overlap-commit.md`)과 정본은 구속한다. 결정 D1·D2·N1은 메인 세션 결정을 구현했고, N4·경계 대조의 해석과 열린 값은 정본 **§74**에 적었다. 사전 등록 문서는 바꾸지 않았다(`python tools/prereg_hash.py --check` OK).
- 건드리지 않은 파일: `stagea_train.PROMPT_FILES` 9개, `train/stageb_data.py`·`stageb_model.py`(§71) — `git diff --name-only`에 없음. `[사용자]` 줄·사용자 인용 줄: 바뀐 문서 줄 중 '사용자' 포함 0. 정본은 끝에 §74만 덧붙였다. `paper/`는 고치지 않았다(§74 논문 갱신 항목).
- 로컬 임시 = `D:\tools\scratch_qdd\r7c9fix`(a9b56e3 사본 `a9b/` = `git archive`, 대조·경계 스크립트, `bound/` 경계 감사). 파드 `/data/harvest/tmp/r7c9fix`(코드 사본·pytest, 266 MB)는 시험 뒤 지웠다.

## 1. 무엇을 바꿨나

| 항목 | 사전 등록·정본 | 코드 |
|---|---|---|
| **D1** γ 0.67 = 2/3 | E §4.12 :487 "γ=0.67", §2A.3 :240, M4 §4.4 :276 "0.67 (3표 중 2)", §3 #2 :147 "3표면 2표 = 0.67" | `runtime/m4.py:42-52` `GAMMA = "2/3"`, `share_at_least(n, v, γ)` = `n·den ≥ num·v`(정수, 엡실론 없음); 런타임 `try_commit_prefix` `:252`, 재생 `analysis/replay.la2` `:16-22`, `eval/e05.apply_rules` `:62` — 같은 함수. `M4Params.gamma` 기본 "2/3"(`:60`) |
| **D2** C2 = VLM Stream | E §4.12 D9 :495, 정본 §20 :179, M4 §5 :332 (아래 인용) | `conditions.py:22` C2 = `agree "stream"`, `stale_max 5.0`, `n_max_cap False`, `feedback_b False`; `m4.py:146-148` `n_max()` = ∞, `:184-190` 슬롯 없이 질문별 가장 새(요청 시각) 유효 응답, `:260-268` `decision(q, ds, now)` = 그 응답, 5 s 넘으면 EMPTY; `core.py:413-415` 보낼 때 in-flight 수 기록, `:451-456` 매 틱 달라진 결정을 실행 중 스텝에 적용, `:659-661` `summary.dec_inflight`; `skills.py:115-121` `redecide`(스텝 예산 = 새 보기 크기 − 이미 움직인 양), `:101,113,206` `moved` |
| **N1** Holm 방향 | E §2A.6-2 :257 "(하한 > 0)", E §1.8 :139·정본 §28 :264 "(하한 > 0, Holm)", 판정 10 :265 "블록 사이 차이" | `analysis/stats.holm_ci(..., direction="greater")`(`:87-101`): 하한 > 0만 기각, 음의 방향 유의는 다음 단계 수준을 풀지 않음; `e05.gain_holm`(`:216-224`)·`harvest/canary.canary_compare`(`:47-48`) 사용; 판정 10 `block_diff_holm`은 양측 그대로 |
| **N4** E-M4-lat STALE_MAX | E §4.12 :487·M4 :288 STALE 1.5 s 대 E :490·M4 §5.1 :375-385 지연 2·5 s | 코드 없음(지연 큐 미구현). 정본 §74: 사전 등록 문장(목적 :375, 판정 11 :381, 11e :385, "d̂·N_max는 목표 분포의 값으로 다시", "척도만 바꿔" :378)이 "STALE_MAX도 지연 점에 맞춰 다시 잡는다"까지 정함; 척도 규칙 (가) 배율 × d*_p95/d_p95(E0) / (나) 1.5 s + (d*_p95 − d_p95(E0))는 **열림 → [결정 필요: 메인 세션]** |
| **경계** 사전 등록 수치 문턱 | 아래 §4 | `stats.CMP_EPS`·`at_least`·`at_most`·`below`·`above`(`:6-29`); E0.5 `judge_e05`(`replay.py:33-71`)·`e05` 판정 입력 반올림 제거(`:184-196`, `:419-433`, `:448-457`), `gain_holm` lo·hi 반올림 제거; E1 `calibration.evaluate` → `judge_values`(`:140-206`), `judge_question`(`:210-234`)·`_display_values`(`:237-`), `fit_question` `:92`; M1 near 들어가기 `≤ 5 cm`(`predicates.py:59`, `stereo/pipeline.py:104-108`, `sim/planner.py:272`, `cli_pool.py:100`, `datagen/gen.py:81`, `sim/labeler.py:200`), 애매 띠 (5, 6] cm(`sim/snapshot.py:97`) |
| **DOC D-1** | — | `r7_fixes.md:45` "Holm 없음"에 [해결 R7 8회차, 정본 §73 D3; 9회차 §74 방향] 표시 |
| **N5** | — | `handoff.md:3`(머리 시각, 횟수 없음)·`:5`·`:83` → §74, §2.8 9회차 줄; `direction-log.md` 행; `draft-log.md` 줄(교훈) |
| **N6** | — | `SUMMARY.md:287`·`:589` "경계 직후 W 2·γ 1.0"에 [SCOPED R7 9회차, §73 D5·§74]; 논문 `paper/sec/3_method.tex:103`은 §74 논문 갱신 항목 |
| 관련 문서 표시 | — | `r5_closed_loop.md:33`(N_max — C2 상한 없음)·`:36`(γ 0.67 = 2/3, STALE·FROZEN은 합의 원장만), `r6_eval.md:46-47`(C2 = newest → stream), 코드 머리 설명 `m4.py:17-25`·`conditions.py:7-9`·`core.py:3-9` |

D2 사전 등록 원문(구현의 근거):
- E §4.12 D9(:495): "**C2** = Slow Brain VLM Stream(T_c 고정 주기, in-flight 상한 없음·실측 보고, 요청 시각 기준 가장 새 유효 응답 하나 적용, 무효 무시, 5 s 타임아웃이면 기본 행동)".
- 정본 §20(:179): "C2 = Slow Brain 'VLM Stream'(요청 시각 기준 가장 새 유효 응답 하나 적용, in-flight 상한 없음·실측 보고, 5 s 타임아웃)".
- M4 §5(:332): "겹침 + **VLM Stream**(원문 충실판, 00 §20): T_c 고정 주기, 동시 요청 상한 없음(원문에 상한 없음, 실측 in-flight 수 보고), 매 틱 **요청(관측) 시각 기준 가장 새 유효 응답** 하나의 보기를 그대로 적용, 무효 응답 무시, 마지막 유효 응답이 5 s보다 오래되면 기본 행동(타임아웃)".
- 대응: 상한 없음 = `n_max()` ∞; 실측 보고 = `dec_inflight`; 매 틱 = `act()` 100 Hz 틱마다 가장 새 응답으로 실행 중 스텝 결정 교체(늦은 응답도 적용, FROZEN `log_only` 없음); 요청(관측) 시각 기준 = `t_state`; 무효 무시 = 오류 응답·전제 epoch 낮은 응답 폐기(공통), 더 오래된 요청 시각 "older"; 5 s = 나이(지금 − 요청 시각) > 5 s면 결정 없음 = 기본 행동(빈 스텝과 같은 스킬 동작). STALE_MAX 1.5 s 폐기는 C2에 적용하지 않는다. 열린 값 (i)–(vii)은 정본 §74.

## 2. 시험 (RED → GREEN)

새 파일 `tests/runtime/test_r7c9_prereg.py`(12), `tests/eval/test_r7c9_prereg.py`(6), `tests/eval/test_r7c9_bounds.py`(10). 옛 뜻을 적은 기존 시험 3곳을 결정에 맞춰 고쳤다: `tests/eval/test_runtime_r6.py:45`(C2 조건 표), `tests/eval/test_r7c8_prereg.py:47-49`(음의 이득은 이제 Holm 기각 아님), `:141`(카나리 참조 Holm = `direction="greater"`).

- RED(구현 전, `D:\tools\scratch_qdd\r7c9fix\red.txt`): D1·D2·N1 18개 중 **14 실패** — `share_at_least` 없음(ImportError), 런타임 `a, b, a` CONTESTED(확정 없음), 재생이 같은 함수가 아님, C2 조건 표·`n_max` 8(상한), 2 s 나이 표 `dropped_stale`, 늦은 응답 `log_only`, 2.0 s 폐루프 `dropped_stale` > 0, 매 틱 적용 불일치, `redecide` 없음, `holm_ci` `direction` 없음(TypeError), 판정 2 A3 예(음의 C2''가 LA-2를 95%로 풀어 `keep_a`), 카나리 C4 예(바닥 아래 질문 4개가 dir_xy를 95%로 풀어 표류). 처음부터 통과(회귀 보호): `a,b,c,a` 2/4 미확정, γ 1.0 만장일치, 양측 Holm 예, 판정 10 음의 차.
- RED(경계, `red_bounds.txt`, a9b56e3 사본에서도 같은 결과): 10개 중 **9 실패** — AUROC 0.83 − 0.80, 판정 9 하한 −0.02, E0.5 flip 1/9가 0.1111로 판정, `gain_holm` 하한 1e-5 → 0.0, θ 0.8 하한 0.72, ECE |78/100 − 0.75|, AUROC 0.749971 → 0.75, near 5 cm 정확히, 애매 띠 5 cm. 통과(회귀 보호): J5 경계 1 − α − 0.03·1 − α.
- GREEN: 새 28개 모두 통과(`green.txt`). 전체 — **로컬**(Git Bash `python -m pytest`, basetemp·TMP = scratch): **841 passed, 11 skipped**, 실패 0(이전 813/11 + 새 28). 건너뜀 11 = torch 없음 7, inspect_robots 2, pyarrow 1, TODO(P3) 1(전과 같음). **파드 CPU**(`venv_train`, 작업 트리 사본 + third_party, `CUDA_VISIBLE_DEVICES=""`, 05:59–06:00 UTC): **883 passed, 3 skipped**, EXIT 0(이전 855/3 + 28), 건너뜀 = CUDA 없음·pyarrow·TODO(P3), 경고 1(전과 같음).

## 3. 무작위 대조 (a9b56e3 대 이 수정)

`D:\tools\scratch_qdd\r7c9fix\char_run.py`(검증자 `r7c9/char_run.py`를 넓힘): 가짜 세계 폐루프 **200판 × C0–C6**, 지연 {0.15, 0.30, 0.45, 0.60, 0.90, 1.2, 2.0} s 고정 또는 흔들림(호출마다 0.25–0.35 s, 3%는 1.4 s; 요청 시각의 해시로 정해 스레드 순서와 무관), W {1, 2}, 머그·트레이·TCP 무작위, 한 번의 P1 비슷한 이동, 1,500–3,000틱. 비교 = 행동 바이트 sha256·원장 counts·슬롯 sha256·실행 계정(확정/가확정/빈)·호출 수·단계·epoch(`char_cmp.py`, `char_cmp.txt`).

| 조건 | a9b56e3과 같음 | 다른 것 | 원인 |
|---|---|---|---|
| C0·C1·C4 | **200/200 비트 동일** | — | — |
| C2 | 0/200 | 전부(의도) | D2 |
| C3·C5 | 23/200 | 177판: counts·슬롯·실행 계정(행동 바이트는 1판) | D1 |
| C6 | 118/200 | 82판: counts·슬롯·실행 계정(행동 바이트 동일) | D1 |

- **D1 분리**: HEAD에 γ = 0.67(옛 문자 값)을 주면 C3·C5·C6 **200/200 비트 동일**(`c_g067.json`). 계수 도구(`share_at_least` 감싸기, `c_c23.json`·`n23_match.txt`): γ 규칙이 **정확히 2/3** 공유를 본 판 = C3·C5 177판(평가 309회)·C6 82판(133회)이고, a9b56e3과 달라진 판의 집합과 **정확히 같다** → 바뀐 칸은 2/3 경계에 걸린 경우뿐(지시의 예상과 같음). 100표 미만에서는 [2/3, 0.67) 사이 다른 분수가 없다.
- **D2 지연별 C2**(`c2_detail.txt`): 2.0 s에서 a9b56e3 표 15,825/15,825 `dropped_stale`·끝까지 간 판 0/18 → 수정 뒤 폐기 0·8/18; `log_only` 0.45 s 310·0.6 s 170·0.9 s 600·1.2 s 540·흔들림 1,005 → 모두 0; 호출 수는 1.2 s(1,138 → 1,152)·2.0 s(1,163 → 1,219)에서만 늘어남(상한이 묶던 곳), 0.15–0.9 s·흔들림은 같음.
- **경계 수정 뒤 최종 코드**(`c_final.json` 대 D1+D2만 넣은 `c_head.json`): §5 참조.

## 4. 사전 등록 대조표 — 이번 변경이 닿은 행(원문에서 다시 만듦, 9회차 표 번호)

| # | 사전 등록 값·절차 (출처) | 구현 (file:line, 수정 뒤) | 확인 | 판정 |
|---|---|---|---|---|
| 3 | `ambiguous` = 히스테리시스 띠 술어 (E :121; M1 :140 "≤ 5 cm 들어가기 / 6 cm 나가기") | `sim/snapshot.py:89-99`(띠 (5, 6] cm), `predicates.py:59` | `test_ambiguous_band_is_the_history_dependent_part` | 일치(수정) |
| 9 | Holm — 판정 2 "LA-2 또는 C2''"(하한 > 0) (E :131, :257) | `e05.py:216-224` `direction="greater"`, `replay.py:41` | `test_judgment2_negative_c2pp_does_not_release_la2` | 일치(N1, §74) |
| 10 | Holm — 판정 10 블록 쌍 (E :265) | `e05.py:200-236`(양측) | `test_judgment10_stays_two_sided` | 일치(양측 근거 §74) |
| 11 | Holm — 카나리 "하한 > 0, Holm" (E :139, 정본 :264) | `harvest/canary.py:31-55` `direction="greater"` | `test_canary_below_floor_questions_do_not_release_level` | 일치(N1) |
| 17 | 재생 규칙 LA-2·γ 0.67 = 3표 중 2 (E :240) | `replay.py:16-22`, `e05.py:59-63` → `m4.share_at_least` | `test_replay_uses_the_same_rule` | 일치(D1) |
| 21 | 판정 1–3 문턱 5%·+2%p (E :256-258) | `replay.py:39-50`(`below`·`at_least`), 입력 반올림 없음 `e05.py:419-422` | `test_e05_judge_input_is_not_rounded`, 경계 감사 | 일치(수정) |
| 22 | 판정 4 ×2·AUROC 0.7·0.03 (E :259) | `replay.py:51-56` | `test_j4_auroc_margin_exactly_003_counts` | 일치(수정) |
| 24 | 판정 6 < 1% (E :261) | `replay.py:57-58` | 경계 감사 | 일치 |
| 25 | 판정 7 +2%p·하한 > 0 (E :262) | `e05.py:447-449`(반올림 없음) | 경계 감사 | 일치(수정) |
| 26 | 판정 8 하한 > 0 (E :263) | `e05.py:452-457` | 코드 | 일치(수정) |
| 27 | 판정 9 −2pt 하한·A3 > 바닥·A4 ≥ 5% (E :264) | `replay.py:59-68`, 입력 `e05.py:424-433` | `test_j9_neutral_bound_exactly_minus_002` | 일치(수정) |
| 36 | 원 확률 ECE ≤ .03 ∧ T ∈ [0.8, 1.25] (E :335) | `calibration.py:92` | `test_raw_ece_exactly_003_uses_raw` | 일치(수정) |
| 37 | 판정 1 (i)–(iv): ECE ≤ .05·상한 ≤ .08, AUROC ≥ .75·하한 ≥ .70, θ − .03·하한 θ − .08, 20% (E :339) | `calibration.py:210-229`, 값 `evaluate` `judge_values` `:140-206` | `test_theta_gate_at_theta_minus_008`, `test_auroc_judged_unrounded` | 일치(수정) |
| 39 | 판정 8 J5: 1 − α − .03, 50%, 1 − α (E :347) | `calibration.py:230-233` | `test_j5_bounds_exact` | 일치 |
| 42 | N_max = ⌈d̂/T_c⌉+1 (M4 :258, :263) — C5 | `m4.py:146-151`(C2는 ∞) | 경계 감사(0.33→2, 0.66→3, 0.81→4) | 일치 |
| **43** | **γ = 0.67 "3표 중 2" (E :487, M4 :276, :147)** | **`m4.py:42-52`, `:252`** | `test_runtime_two_of_three_commits_at_default_gamma`, `…two_of_four…`, `…gamma_one…`, 무작위 대조 | **일치(D1 수정)** |
| 46 | τ = 1(접촉 근처 0), near ≤ 5 cm (E :487, 정본 §7 :45) | `core.py:42-56`, `m4.py:163-172` | 경계 감사(0.05 참) | 일치 |
| 48 | STALE_MAX 1.5 s (E :487, M4 :288) — C5·C1·C3·C4·C6 | `m4.py:63`, `:181` | 경계 감사(나이 1.5는 유지 — "폐기 나이" 초과부터 폐기) | 일치; E-M4-lat 지연 점은 N4(§74, 열림) |
| **49** | **C2 = VLM Stream (E :495, 정본 :179, M4 :332)** | **`conditions.py:22`, `m4.py:146-148,184-190,260-268`, `core.py:413-415,451-456`, `skills.py:115-121`** | **`test_c2_*` 6개, 무작위 대조(2.0 s 폐기 0)** | **일치(D2 수정)** |
| 50 | C0·C1·C3·C4·C5·C6 정의 (M4 :329-346) | `conditions.py:18-26` | 무작위 대조 C0·C1·C4 200/200 동일, C3·C5·C6은 D1 경계만 | 일치 |
| 56 | P1 2 cm·near 5 cm (E :420, 정본 §7) | `sim/planner.py:272`·`datagen/gen.py:81`·`cli_pool.py:100`·`sim/labeler.py:200` P1 발동 `≤ 5 cm` | 경계 감사 | 일치(수정) |
| 57 | 라벨 규칙 적격 ≥ 0.90·판별력 0.02 (prereg_labeler :11-12) | `sim/labeler.py:135,139` | 경계 감사(810/900 적격, 0.02 동점) | 일치 |

### 4.1 모든 수치 문턱의 경계값 대조(9회차 지시, 하위 에이전트 감사 + 이 수정)
스크립트 `D:\tools\scratch_qdd\r7c9fix\bound\bound_checks.py`(출력 `bound_checks.log`·`.out.json`): 문턱 약 45개를 정확히 문턱 값과 바로 위·아래(`nextafter` 포함)로 실제 함수에 넣었다. 불일치 6건은 모두 이 수정으로 고쳤다(시험 §2): M1 E0.5 판정 입력 4자리 반올림, M2 판정 4 AUROC 차 0.03, M3 E1 θ − 0.08, M4 E1 원 확률 ECE 0.03, M5 E1 반올림 뒤 비교(AUROC·ECE·단일 집합 비율·적용률), M6 near 들어가기 `<`. 이외에 판정 9 하한 −0.02(부동소수 0.08 − 0.1 = −0.020000000000000004)와 `gain_holm` 하한 반올림을 같은 규칙으로 고쳤다.
- 일치 확인(요약): 판정 1–3·6·7·8·9·10의 방향(≥·<·>), γ 2/3, Holm 방향, E0.5 표 자르기 t ≤ t_s − d_p95, E1 판정 1 (i)·(ii)·(iv), 오답 30, J5 적합 400, q̂ = ⌈(n+1)(1−α)⌉(n 1–5000 × α 3개 정확값과 같음), N_max, 첫 슬롯 t_start ≥ t_send + d̂, W·W_irrev, τ, near/contact ≤ 5 cm(`core.near_contact`), lifted ≥ 3 cm, upright ≤ 30°, 성공 1 s 연속, P1 2 cm·P2 +0.5 s, 라벨러 0.90·0.02·D-time, 시드 범위 끝값, E0 사례 a–e·실패율 2%·2 s 검열, 판정 절 해시 5개.
- 기록만(코드 무변경, 정본 §74): E-M4b-meas PC3 "+0.05"·V1q "+0.03"(`m4b/analyze.py:465,:443`)의 부동소수 덧셈(정확히 +0.05인 개수 쌍 탈락) — §64로 끝난 판정, 여유 커서 결과 불변; D28 :176 "지연 증가 ≤ 50 ms" 조건 코드 없음; `e05 --d-p95` 기본 0.307 = 정본 §55 판정 값(본 실행은 E0 측정값을 넘김, §2A.8 재실행 비교는 수동); 섭동 창 (t_e, t_e + 1]·STALE "초과부터 폐기"·60 s 시간 제한 포함 여부는 사전 등록이 경계를 적지 않음.
- 시험하지 못한 문턱(코드 없음): E2a §4.8 판정 1–9(+5%p·Holm(3)·상한 < +5%p·연장·+10%p·R0 − R-lag·D-줌 15%p), "R0 DEV > 90%면 P1 4 cm"(E :482), "429 > 5%면 재실행"(E :484), EVAL §4.2 H1–H3(RD ≤ 35%·B3c 80%·차 < 15%p면 시드 추가), E1 묶음 확인(≥ 98%, |Δp| ≤ 0.02)·등위 회귀 −0.02·판정 2–5(§73 SCOPED), M4 §4.3 조기 호출 g·P90(§73 D5 SCOPED), 정본 §7의 M7/M8 값(grasp/release 1.0 s, 정체 10/20틱, cooldown 2 s, C_assume·C_pred) — 해당 코드가 생길 때 같은 `at_least`/`at_most` 규칙으로.

## 5. 경계 수정 뒤 최종 대조
- 같은 200판을 최종 작업 트리(D1 + D2 + N1 + 경계 수정)로 다시 돌렸다(`c_final.json`, `char_final.txt`): D1 + D2만 넣은 코드와 **7조건 모두 200/200 비트 동일** — 경계 수정(E0.5·E1 판정, near `≤`)은 폐루프 동작을 바꾸지 않는다(가짜 세계에서 거리가 정확히 5 cm인 틱 없음). 따라서 a9b56e3 대 최종 = §3 표 그대로(C0·C1·C4 200/200 동일, C2 전부 다름, C3·C5 177·C6 82판은 정확히 2/3 경계 판).

## 6. 판단이 갈릴 수 있는 곳
1. **N4(가장 중요)**: 사전 등록 문장(E-M4-lat 목적·판정 11·11e·"목표 분포의 값으로 다시")은 STALE_MAX 1.5 s를 지연 2·5 s 점에 그대로 쓰는 읽기(모든 표 폐기 → C1·C5가 모델 없이 도는 칸)를 배제한다고 읽었다. 그러나 **어떤 규칙으로 다시 잡는지**(배율 대 초 여유)는 문장이 정하지 않는다 → 고르지 않고 [결정 필요: 메인 세션]으로 정본 §74에 두 읽기를 적었다. 지금은 지연 큐가 없어 코드 영향 없음.
2. **C2 "매 틱"과 스텝 예산**: 사전 등록 "매 틱 … 보기를 그대로 적용"을 `act()` 100 Hz 틱마다 실행 중 스텝의 결정 교체로 구현했다. 보기의 크기(`mag_coarse`)는 스텝당 이동량이라, 스텝 안에서 바뀌면 "새 보기 크기 − 이미 움직인 양"을 남은 예산으로 두었다(스텝당 한 보기 크기를 넘지 않음). 새 보기 크기를 통째로 다시 주는 읽기(스텝당 최대 2배 이동)도 가능하나 C2에 유리하게 기울어 택하지 않았다.
3. **C2 "기본 행동"**: 결정 없는 스텝과 같은 스킬 동작(제자리)으로 읽었다. Slow Brain 원문의 기본 행동은 빠른 층 플래너 자체이고, 우리 스킬 S의 결정 없는 동작이 그 대응이다.
4. **C2의 premise epoch**: 공통 유효성 규칙으로 남겼다(Astra 결정이 epoch를 올리면 옛 전제 응답을 버림). E-M4 주 조건은 Astra를 끄므로 영향 없음.
5. **판정 10 양측 유지**: 메인 지시는 판정 10도 Holm 호출 목록에 넣었지만, 원문이 "블록 사이 차이"(방향 없음)이고 쌍 순서가 임의라 양측이 맞다고 판단했다.
6. **near `≤`로 바꾼 곳이 데이터 생성 코드**: 풀·R2 생성(`planner`·`gen`·`cli_pool`·`labeler`·`predicates`)의 near 들어가기가 5 cm 정확히에서만 달라진다 — 연속 물리량이라 사실상 일어나지 않아 기존 자료는 그대로 유효하다고 보고 재생성하지 않았다.
7. **E1 `judge_values`**: `calib.json`의 질문별 `heldout`에 반올림 없는 판정 값이 새 키로 함께 나간다(표시 값은 그대로 4–5자리).

## 7. 변경 파일 검사
- 탭·폼피드·NUL: 바뀐 파일·새 파일 모두 0(`draft-log.md`의 탭 1개는 전부터 있던 것, 이번 추가 줄에는 없음). 줄 끝(작업 트리): `m4.py`·`SUMMARY.md`·`sim/labeler.py`·`sim/snapshot.py` CRLF 유지, 나머지 LF 유지, `draft-log.md` 섞임 유지(1–284 CRLF, 그 뒤 LF). `git diff --name-only`에 PROMPT_FILES·`stageb_data.py`·`stageb_model.py` 없음.
- 파드: 만든 것은 `/data/harvest/tmp/r7c9fix`(266 MB)뿐, 시험 뒤 지움(`ls /data/harvest/tmp | grep -c r7c9fix` = 0). 그 시간대 `/data/harvest` 아래 새 파일은 다른 세션의 `tmp/replaydbg`뿐(건드리지 않음). GPU 사용 없음(CPU 시험), 남의 프로세스 건드리지 않음.

## 8. 사고(내 실수) 1건
- 지시(Git Bash heredoc 금지)를 어기고 내용 없는 heredoc 한 번(`cat > /dev/null <<'X'` … `X`)을 실행했다. 파일을 만들지 않았고(출력 대상 `/dev/null`) 결과에 영향 없음. 그 뒤 모든 파일은 Write 도구 또는 경로로 실행한 스크립트로만 만들었다.
