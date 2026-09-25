# R7 객관 검증 순회 — 12회차 (cycle 12, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님; `r7_cycle11.md` §5 표나 수정 에이전트 시험에 기대지 않고 사전 등록 원문에서 대조표를 새로 만들고, 행마다 **구성한 입력 → 실제 함수·런타임 출력**으로 확인함). 작성 2026-09-25 09:10 UTC 무렵(`date -u`; 로컬 시작 08:33 UTC, 파드 첫 명령 08:52:47 UTC, 파드 정리 끝 09:04:23 UTC).
- 대상: `D:\qdd` `dev` 커밋 `6b013ac`(커밋 시각 2026-09-25 08:32:33 UTC). 재생 결정성 조사 에이전트의 커밋 안 된 변경(`harvest/sim/labeler.py`, `tests/sim/test_labeler_logic.py`, `docs/stage3/results/pool_replay_debug.md`)이 작업 트리에 있어 **작업 트리는 읽지도 쓰지도 않고** `git -c safe.directory=D:/qdd -c core.autocrlf=false archive 6b013ac`를 `D:\tools\scratch_qdd\r7c12\repo`에 풀어 검토했다(비교용 `6522fda`의 `harvest/`·`fakeworld.py`는 `…\r7c12\base`). `43cd1ff..6b013ac` = 코드 1곳(`runtime/m4.py` `lead_max` 유한 검사) + 시험 4개(`test_lead_max_must_be_finite_and_positive` 매개 4) + 문서(정본 §76, handoff·draft-log·direction-log, `r7c10_fixes.md` 표시, `r7_cycle11.md`). 파드 사본 = 같은 archive(sha256 `a4a7d4a6…`) + `CODE_VERSION`, 모든 산출 `meta.git.commit` = `6b013ac9…`, `meta.code_sha` = `1041eed78b4935f6`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle2.md`–`r7_cycle11.md`, `r7c7_fixes.md`–`r7c10_fixes.md`, 정본 `00-interfaces.md` §1–§76(뒤 절 우선; [사용자] 제목 절은 §67 규칙, 논문 .tex는 §70·§74·§75 논문 갱신 항목에 따라 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`M4-overlap-commit.md`(조건 정의 §4·§5).
- 분류(11회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋과 다르고 정정 표시가 없는 것(후속 정본이 이미 정한 "[결정 필요]" 포함), 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 정본에 없는 것.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(이 보고서 한 파일만 새로 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c12`(스크립트는 모두 Write 도구로 쓰고 경로로 실행; heredoc·`cat >`·`python -` 0 — 파드 스크립트 초안에 heredoc 한 줄을 썼다가 실행 전에 지우고 `pod_r2.py`로 바꿈). 파드 = `/data/harvest/tmp/r7c12`(코드 사본·pytest·산출·가짜 날짜 카나리 루트, 905 MB)와 내 Isaac 판(08:58:01 UTC 시작)이 만든 `ir/kitcache/cyclo-r7c12_standard`(208 MB)·`cache/pyc_r6/data/harvest/tmp/{r7c12,tmp4ai76ufo}`·`tmp/{carb.0SWwVb,tmp4ai76ufo}` — 시작 전 목록(`pod_before.txt`, 08:52:57 UTC)과 대조하고 생성 시각(08:58:03–08:58:33 UTC)·pyc 접두(`pyc_r6` = `closed` 워커 전용, 재생 조사 판은 `pyc_replaydbg`)로 가려 **모두 지웠다**(09:04 UTC). GPU: 단계 B 학습·CUDA 시험 = GPU 2(렌더 없음), Isaac = GPU 1(`closed --isaac-gpu 1` → `IR_ROOT=cyclo`, 고유 `IR_INST` = `r7c12_standard`, `CUDA_VISIBLE_DEVICES=1`), GPU 0(재생 조사 판)·GPU 3 건드리지 않음, 끝에 0–3 = 893/2/1/1 MiB. 시드 DEV만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 `=dev`·`=cal`만). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. 남의 프로세스 건드리지 않음.

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 4 |
| DOC | 3 |
| SCOPED | 12 |
| NOTE | 12 |

11회차 수정(정본 §76)은 **동작으로 확인했다**: `M4Params`는 `lead_max` ∈ {inf, −inf, NaN, 0, −0.0, −1}을 모두 거부하고 1e-9·1.0·1.5·1e6은 받는다(1e6에서도 `target_slots`가 넘침 없이 계산), `closed --m4-h 1 --m4-lead-max inf|nan|0|-1`(H = 3의 inf 포함)은 워커·출력 폴더 전에 rc 1; §76 D-2의 경계 사례 정의는 `boundary_flags`(앞 방향만)·`select_decision`(3 + 7, `w_natural` 합 10)·섭동 배정(40/40/40)·분할(60/60, 섭동별 20/20)과 같고, 파드 풀 120편을 다시 계산하면 저장된 `boundary_case`·결정 선택 불일치 0, 과표집 29.67 %·자연 22.85 %·앞뒤 두 방향 35.38 %(pool.md §1 그대로). 9·10회차 동작(정확히 2/3, C2 스트림, H = 1 스텝당 표, H = 3 불변)도 다시 확인했다(§6.2). 완료 정의 1–5도 모두 다시 돈다(§6.3). 그러나 사전 등록 원문에서 **지금까지 표에 없던 절차**를 찾아 대조하자 코드 결함 4건이 나왔다: E0.5 출력의 FLIP_TH 후보 분위가 사전 등록 α = 0.01이 아님(D1), E0.5 지표 두 가지 미보고(D2), **C5·C4의 (b) 범주가 결정 모델 입력으로 되먹임되지 않아 런타임 C5 = 사전 등록 C5'**(D3), 호출 재현 기록에 사전 등록·정본 §28 A6 필드(질문별 확률·요청/응답 원문·Astra 원응답)가 없음(D4). 문서 3건: handoff 정본 범위 §75(D-1), `r7c9_fixes.md:88`의 해결된 "[결정 필요]"(D-2), `snapshot.py`의 "boundary (ambiguous)" 주석(D-3). 연속 무결은 **0회 그대로**.

---

## 1. DEFECT

### D1. E0.5 FLIP_TH 후보 분위가 사전 등록 α(0.01)가 아니다 — `harvest/eval/e05.py:406-409`
- 사전 등록: E §2A.5(`E-first-experiments.md:253`) 지표 "두 식의 성공 궤적 **1−α 분위(FLIP_TH 초기값 후보)**". α는 같은 사전 등록 체계에서 정해져 있다 — E §4.12 C5 설정(`:487`) "**α=0.01**", M4 §4.4(`M4-overlap-commit.md:285`) α "conformal 오경보율 | **0.01** | {0.001, 0.01, 0.05}", 같은 표 FLIP_TH 행(`:287`) "성공 실행 flip_score의 **1−α 분위**(split conformal) … E0.5 재생 자료로 먼저 잡는다", E §4.12(`:487`) "CAL 시드 conformal·FLIP_TH 적합(… **E0.5 초기값에서 시작**)".
- 코드: `c_flip.flip_th_candidates` = `{f"q{1 - al:.2f}" … for al in (0.05, 0.1)}` → 키 **q0.95·q0.90**만. 사전 등록 값 q0.99가 없고, α = 0.1은 M4 α 범위 밖.
- 행동 확인: 로컬 `hand12.py` 구성 재생(12편 × 20스냅샷)의 `analyze()` 출력 키 `['q0.90', 'q0.95']`; 파드 `e05 --model mock … --split dev --episodes 2` 산출 `flip_th_candidates` = `{'q0.95': …, 'q0.90': …}`.
- 정본 기록: 없음(`grep "flip_th_candidates|FLIP_TH 후보|1−α 분위"` → 사전 등록·설계 문서와 코드뿐; 정본 §73 E0.5 열린 값 목록(섭동 창·시간 블록·C_flip 직전 창)에 없다).
- 영향: 판정 1–10은 이 값을 쓰지 않는다. E-M4의 FLIP_TH 시작값(= E0.5 초기값)이 사전 등록과 다른 분위에서 나온다.

### D2. E0.5 사전 등록 지표 두 가지를 내지 않는다 — `harvest/eval/e05.py:346-348,393`, `:370-376`
- 사전 등록: E §2A.5(`:253`) "**같은 시각 반복 호출 뒤집힘 비율(K=3, 성공·섭동 궤적 따로)**" (굵은 글씨 원문), 같은 줄 "(정본 §27) (i) 확장판 층별 지표: **A0 대비 flip(`option_key` 기준)**, 결과 기반 라벨 정답률, A3 이름 추종률, 첫 자리 선택률 대 정답이 첫 자리에 있는 비율", 정본 §27(`00-interfaces.md:243`) "지표: `option_key` 기준 flip, …"(판 A1–A4 모두).
- 코드: 같은 시각 뒤집힘은 편 군집 하나로 합친 값(`same[c]`, `out["same_time_flip"] = mean_ci(same)`)뿐 — 성공/섭동 궤적 분리 없음. 층별 flip은 A1(`subst`)·A4(`a4flip`)만 있고 **A2·A3의 A0 대비 flip이 없다**(A3은 이름 추종률 `follow`만, A2는 정답률만).
- 행동 확인: `hand12.py` 구성 재생 출력 `same_time_flip` 키 `['ci', 'mean', 'n']`, 층 키 `['a0', 'a0_minus_a1', 'a1', 'a1_minus_a0', 'a2', 'a3', 'a4', 'a4flip', 'first_pick', 'first_true', 'floor', 'follow', …, 'subst', …]` — A2·A3 flip 키 없음.
- 정본 기록: 없음(정본 §73은 "성공/섭동 스텝 분리"를 연속 flip과 판정 4의 섭동 창 1 s로 정했을 뿐 같은 시각 뒤집힘·A2/A3 flip은 다루지 않는다).

### D3. C5·C4의 "(b) 범주를 결정 모델 입력에" 되먹임이 없다 — 런타임 C5가 사전 등록 C5'와 같다 — `harvest/runtime/core.py:191-207`, `conditions.py:11-12`
- 사전 등록(조건 정의 = M4 §4·§5, 정본 §74 원칙 목록): M4 §4.2 의사코드(`M4-overlap-commit.md:232`) `next_jev_input.add_line(f"last_step: {s.outcome}")  # (b) → Jev 입력 (C5'와 대조)`, §3 #10(`:155`) "Jev에 넘길 때는 범주 한 줄만", 조건 표 `:341` "**C5** | 겹침 + (a) + (b) + TIDE 경고 (**§4.2 전체**)", `:342` "**C5'** | C5에서 (b) 범주를 Jev 입력에서 뺌(코드 재계획만)", `:340` "C4 | 겹침 + (b)만(**범주** + epoch 무효화, 가장 새 표)", 판정 3(`:361`) "C5가 C5'보다 섭동 성공률 +5%p 이상이면 '(b) 범주를 결정 모델에 되먹임'을 주장. 아니면 '(b)는 코드 감시'로 쓰고 새로움 문장에서 되먹임을 뺀다". 정본 §17(`:163`) "M4 주장을 … '(b) 되먹임 + 전제 epoch'로 좁힌다"도 같은 되먹임을 가리킨다.
- 코드: 결정 호출 입력은 `_decision_ctx`의 `text_state`(S0 → S1/IMG) + 이미지뿐이고, (b) 결과(`skill.step_outcome`·T1/T2 확인 → `ledger.on_step_executed`)는 원장 epoch·재개방·hold와 Astra 하트비트 요약(`core.py:236` "last step checks")에만 들어간다. `conditions.py` C5 설명 "overlap + (a) + (b) (the M4 design; runtime default)", C5'는 `meta.not_in_runtime` 목록에 있다.
- 행동 확인: `b_feedback.py`(가짜 세계, C5와 C4, 요청을 모두 기록하는 모의 선택기, 400틱째 실행한 스텝에 DEVIATE를 넣어 epoch 1로 올림) → **요청 46개 중 (b) 결과("DEVIATE"·"CONTRADICT"·"LAG"·"last_step"·"outcome")를 담은 요청 0개**, 상태 텍스트는 `t_state … contract … robot … objects … facts …`뿐. 즉 런타임 C5 = 사전 등록 C5'(되먹임 없음), C4도 같은 요소가 빠짐 — 판정 3(C5 대 C5')은 이 런타임에서 성립하지 않는다.
- 정본 기록: 없음(`grep "되먹임|Jev 입력|last_step|C5'"` 정본 → 설계 요약 줄뿐, 결정·SCOPED 없음). 9회차 D2(C2가 조건 문장과 다름)·10회차 D1(H = 1 정의)과 같은 부류 — 설정 값이 아니라 조건 문장 전체와 대조해야 드러난다. 되먹임 줄을 넣으면 단계 A DecCall 프롬프트 형식이 바뀌므로(§71 학습 파일 보호) §75 보충 (2)(판정 7)처럼 정본에서 판정 3의 범위를 정하거나 형식을 바꾸는 결정이 필요하다.

### D4. 호출 재현 기록에 사전 등록 E §1.6·정본 §28 A6 필드가 없다 — `harvest/runtime/core.py:266-271`, `:367-374`
- 사전 등록·정본: E §1.6(`:125`) 모든 결정 호출 기록 "… 질문별 {choice, **probabilities**, confidence | noul | score, legend} … **요청·응답 원문 JSON을 그대로 저장(재분석용)**", `:126`(정본 §28) "Astra(**모든 호출**, A1·A6): **요청 원문(이미지 바이트 해시 + 원본)**, `astra_prompt_id`, 모델 ID, 응답의 모델 식별 필드, effort, **최대 토큰**, 사용량, 첫 토큰·완료 시각, **원응답**, 검사기 결과, 계획 서명, patch 편집 거리", `:127`(정본 §42) 트라이얼 부가 JSONL = "(M4 표·option_key·epoch·요청 해시·카나리 id, **위 호출 기록 필드**)", 정본 §28 A6(`00-interfaces.md:255`) 같은 목록.
- 코드·행동(파드 Isaac 폐루프 사이드카 `dev7-P0-standard-e0.jsonl`, C5·C2): 결정 `call` 행 필드 = `answers, call_id, call_no, canary_id, epoch_sent, error, image_sha256, latency_s, meta, phase, request_sha256, slots, t_deliver, t_state, votes` — `answers`는 질문마다 `[choice, p_chosen]` 두 값뿐(250/250, 195/195)이고 **질문별 확률 분포·요청/응답 원문이 없다**(요청은 해시만; `JevLSelector`가 받은 `probs`는 행에 옮기지 않음). `astra` 행 필드 = `cadence, canary_id, decision, error, first_token_s, hb_no, http, image_sha256, kind, latency_s, model, note, prompt_id, request_sha256, t_deliver, t_send, usage` — **원응답(`output_text`)·요청 원문(요약 텍스트)·최대 토큰이 없다**(파싱한 `decision`·`note`만). 정본 §42의 좁은 목록(설정 dataclass·M4 표·option_key·epoch·요청 해시·카나리 id)과 `policy_config`(astra_prompt_id·question_ids·model_id·astra_effort·T_c·clock·m4)는 모두 있다.
- 정본 기록: 없음(§67 보충은 1회차 수정으로 "요청 해시·카나리 id"를 더했다고만 적음; 검사기 결과·계획 서명·patch 편집 거리는 §67 C8 SCOPED(A5′ 검사·계약 편집 미구현)라 이 결함에서 뺀다). 영향: 유료 Astra API나 실모델로 돌린 판은 원응답·확률 분포를 다시 볼 수 없다(E1식 재분석·재현 불가).

## 2. DOC

### D-1. `docs/handoff.md:3`·`:5`·`:83` — 정본 범위를 "§1~§75"·"지금 §75"로 적음(같은 커밋에서 §76 추가)
- `:3` "마지막 갱신: 2026-09-25 08:30 UTC (… 정본 §1~§75)", `:5` "현재 판본: 정본 `00-interfaces.md` **§1~§75**", `:83` "`00-interfaces.md` §43부터 끝까지(**지금 §75**)" — 6b013ac가 §76을 더하고 `:3`의 시각만 고쳤다. 선례: 8회차 D-1(handoff 정본 범위 줄), 3회차 L4.

### D-2. `docs/stage3/results/r7c9_fixes.md:88` — N4를 "[결정 필요: 메인 세션]"으로 적은 §6 항목 1에 해결 표시 없음
- `:88`(§6 "판단이 갈릴 수 있는 곳" 1) "… 고르지 않고 **[결정 필요: 메인 세션]**으로 정본 §74에 두 읽기를 적었다." — 정본 §74 보충(06:20 UTC, (가) 비례 규칙 채택)이 결정했고 같은 파일 `:15`에는 [해결 R7 10회차 D-1] 표시가 있지만 `:88`에는 없다. 11회차 D-1이 `r7c10_fixes.md` §5 항목 1–3(같은 모양)을 DOC로 잡아 §76에서 표시했으므로 같은 기준. 10·11회차 모두 놓쳤다.

### D-3. `harvest/sim/snapshot.py:31`·`:119-121` — 과표집 층을 "boundary (ambiguous)"로 적음(정본 §76 D-2와 다름)
- `:31` `OVERSAMPLE_FRAC = 0.30  # boundary (ambiguous) share of the decision snapshots (E §1.5)`, `:119` `select_decision(ambiguous, …)`, `:120-121` "round(n * frac) from the boundary stratum (**ambiguous**)". 정본 §76 D-2는 경계 사례 = `ambiguous` **또는** 다음 연속 스냅샷까지 등록부 술어 변화로 정했고(`cli_pool.choose_from`은 `boundary_flags`를 넘김), 파드 풀에서 경계 층 22.85 % 대 `ambiguous` 4.65 % — 주석·인자 이름이 좁은 옛 정의를 말한다. 정본 §69·§70 정정 절차("코드 주석 포함", "구현 이름 검색"). 같은 부류 옛 계획서 `2026-09-24-stage3-experiments.md:1394`("히스테리시스 띠 안 술어가 있는 결정 시점을 우선")는 옛 계획서라 NOTE(N11).

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(정본 §71 보충) — 로컬·파드 모두 `tests/runtime/test_latency_ctrl.py:11` 1개 건너뜀. EVAL H1–H3(기준선 비교)도 같은 보충 "기준선 비교는 본 실험 단계에서".
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66) — `gen gen --seeds 10005-10006` 확인 인자 없이 rc 1(§6.4).
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8 — Astra patch/replace = epoch만(검사기·계획 서명·편집 거리 없음), 확인 헤드 보정 파일(`verify_cal` 기본 미보정 — (b) conformal α 0.01 적용 전), M9 복구.
- S6. Astra 카나리 id "none" — 파드 C5·C2 판 `astra` 행 2 + 2 모두 `canary_id: "none"`.
- S7. S-E2E 체크포인트 런타임 tau 마스크 차이(`r7_fixes.md` §7).
- S8. CONTRADICT-soft(§68 K6·§69).
- S9. §73 D5 M4 설계 확장(경계 직후 W 2·γ 1.0, 큐 임계 g, 장면 변화 조기 호출, 미확정 실행 (b) 엄격화) — `m4.py:28-32` "Not implemented".
- S10. §73 N5 E1 범위(`calib` = 판정 1·8).
- S11. §74 보충 N4 (가) 비례 STALE_MAX와 런타임에 없는 조건 C2'·C2'-S·C2-match·C3'·C3''·C5-A3·C-FIX·C5'(`closed.json` `meta.not_in_runtime`) — 단, C5' "없음"의 뜻은 D3(런타임 C5 자체가 C5'와 같음).
- S12. §75 보충 (2) E-M4 판정 7(H = 3 대 H = 1).

## 4. NOTE
- N1. `r7c10_fixes.md:72` 행 51의 [해결 R7 11회차 D-1] 표시는 4칸 표에 **다섯째 칸**으로 붙어 있어 GFM 렌더링에서 버려진다(원문에는 있음) — 판정 칸 안으로 옮길 것.
- N2. `closed.py:165` "# validation (lead_max > 0, W >= 0)", `:370` "lead_max <= 0 -> refused" — 틀리지 않지만 §76 N4의 "유한" 조건이 빠진 설명.
- N3. **FROZEN 읽기**: 런타임은 이미 시작한 슬롯만 불변(`m4.py:228` `t_start <= now`)이고 표의 대상은 송신 시각 기준 `t_start ≥ t_send + d̂`(`target_slots`). M4 §3 #5(`:150`) "고정 구간 = 시작 시각이 now + d̂_p95 이전"을 **도착 시각** 기준으로 읽으면 H = 3에서 스텝당 표가 약 2개가 되어 M4 §4.1 `:189`("약 3표")·E §2A.3 재생(t_s − d_p95 표 포함)·E §2.6 계수와 어긋나므로, 코드의 송신 기준 읽기가 사전 등록 수치와 맞는다(행동: `hand12.py` C20 — 시작 0.02 s 전 도착 표가 `tentative`). 한 줄 정본 기록을 권함.
- N4. **E0.5·E1 채점 정답 기본 = labels_v2**(§54 "결정 질문 정답 v2 채택"·§65 "결과 기반 라벨은 거부권 용도로만"). 사전 등록 E §2A.3(`:241`)은 결과 기반 라벨, `prereg_labeler.md` 규칙으로 plan이 적격(§65) — E0.5 본 실행 전에 "E0.5 판정 정답 = labels_v2"를 명시하고, labels_v2와 C2'의 S1이 같은 코드 규칙이라 판정 7(C2' − LA-2)이 순환임(`e05` meta 주석, `r6_eval.md:56`)을 결과 문서에 적을 것.
- N5. **E0.5·E1 질문 집합 = DecCall 5질문**(dir_xy·dir_z·mag_coarse·target·phase). 사전 등록 E0.5 표현(`:239`)의 `fine_dir`(접촉 근처), E1 질문군 표(`:299-309`)의 QC-progress·QS-dist·QN-*·QC-accept는 묻지 않는다 — §54(정답 v2 질문)·§71(progress 제외)·§73 N5(결정 질문에 Noul 없음)가 암묵적으로 덮지만 fine_dir은 정본에 언급이 없다(`stagea_data.py:18` 주석뿐).
- N6. **카나리 "표류 의심" → 게이트 끔**(E §1.8 `:139`, §3.7-8 `:347`)은 런타임이 강제하지 않는다(보정 파일이 주어지면 그날 카나리와 무관하게 J5 적용). 평가 `meta.canary`에 `drift_suspect`·`stale`이 실려 분리 보고는 가능 — 운영 절차로 두려면 정본 한 줄, 아니면 `closed`/`calib`에서 경고·거부.
- N7. **E0(Jev-L) 도구 없음**: `cli_e0`은 Jev API 판(user-log 46으로 사용 불가), `judge_e0`은 판정 4(스텝당 표 수 **중앙값**)·6·7·8을 모으지 않고 `votes_per_step`은 지연 하나만 받는다. §75 보충·§76 N3의 "E0 오프라인 수로 lead_max 재결정" 전에 필요. 완료 정의 4(E0.5·RD·보정)의 범위 밖.
- N8. 완료 정의 밖이라 구현되지 않은 사전 등록 실험(E2a·E3·E-M3·E-M7 소프트 채널 AND·`C_flip` 채널·E-M8·E-AE·E-R·E-link)은 계획 완료 정의 4가 범위를 정하지만, 한 곳에 모은 정본 SCOPED 줄은 없다 — 한 줄 권함.
- N9. 시험 수: 로컬 사본 **860 passed / 11 skipped**(= 11회차 856 + 새 매개 시험 4; 지시문의 기대 861과 1 차이 — 6b013ac 문서 어디에도 수치 주장 없음), 파드 CPU 902/3, 파드 CUDA 110 passed(`tests/train` + `test_fused_action.py` + `test_fused_model.py` — 11회차 102는 `test_fused_model` 제외), LeRobot 6 passed.
- N10. 단계 B S-E2E 스모크(6스텝, 검증 4개): dec 3.526 → 2.895 → 2.303은 줄지만 fm 3.382 → 3.132 → 3.376은 단조가 아니다(10·11회차와 같은 모양). 재적재 차 0.0. S-E2E 사전 등록 때 "손실 감소"의 손실을 적을 것.
- N11. 11회차 N2(H = 1 앞당긴 묻기의 질문 문구), N5(판정 5 반올림 재시험 값), N6(지문 없는 보정 파일은 결속 검사 생략), N7(라벨러 동점·오라클 조기 종료), N9 목록(옛 계획서 γ 소수·`:1394` 경계 사례 정의, 카나리 `dev_v1` 3편·`stale: true`, 논문 .tex §74·§75 갱신 항목 — D3·D4 수정이 논문 방법 서술(되먹임 주장)에도 닿음, TEST2가 `splits.RANGES`에 없음, 1차판 RD Score [가정], 자연/과표집 가중치 보고, E0.5 분당 400 [가정]) 그대로.
- N12. 위생·절차: 첫 로컬 pytest를 PowerShell에서 띄워 `date` 명령이 없어 2건 실패(FileNotFound) — Git Bash에서 TMP·basetemp를 D:로 두고 다시 돌린 판이 위 N9 수치(08:35:56–08:38:02 UTC). 로컬 C:에서 이 검토 시작(17:33 KST) 뒤 새로 생긴 것은 `AppData\Local\Temp`의 앱 캐시(GUID `.tmp`, Inno Setup `is-*.tmp`, `2026-09-25_mservice.txt`)와 `.claude` 하네스 파일뿐 — 이 저장소 산출물 0. 파드 `/data` 밖: `find / -xdev -newermt "08:52 UTC"`(`/proc`·`/sys`·`/dev`·`/run`·`/data` 제외) 0건, 루트에 "C:" 폴더 0. 첫 `git -C D:/qdd` 명령은 safe.directory 오류(읽기 전용, 전역 설정 안 씀 — 이후 `-c safe.directory=D:/qdd`).

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` OK, 파드 산출 `meta.prereg.check` = "OK"(e05·rd·calib·closed, 해시 5개, `utc` 바로 다음). 사전 등록 문서는 `43cd1ff..6b013ac`에서 바뀌지 않았다. 코드 줄은 `6b013ac` 기준. "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c12\hand12.py`(113/116 — 실패 3개는 모두 D1·D2 증거, `hand12.txt`), `hand12b.py`(4/4), `fw_run.py`·`cmp_fw.py`(무작위 대조, `cmp_fw.txt`), `b_feedback.py`(D3), 오프그리드 H = 1(`og.txt`); **파드** = §6.3·§6.4(`pod_cpu.log`, `pod_gpu.log`, `pod_logs.txt`, `pod_pod_checks.json`). 굵게 = 이번에 처음 대조한 행.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 / R2_TRAIN 10000–59999 (E :113-120, 정본 §66) | `eval/splits.py:13-14,27-42`, `datagen/gen.py` | `RANGES` 같음; 보호 분할 무변수·다른 값 거부, 범위 밖 시드 거부; 파드 가드 23건 rc ≠ 0·출력 폴더 0 | 일치(TEST2 N11) |
| 2 | POOL 120 × 10, 경계 사례 30 % 과표집, 자연·과표집 가중치 (E :121, 정본 §76 D-2) | `sim/snapshot.py:28-52,102-136`, `cli_pool.py:400-436` | 앞 방향만·띠 단독·다음에 없는 키 무시; 20/100 → 3 + 7·가중치 합 10·역포함확률; 부족 층 채움 2 + 8, 5 + 5; 짧은 판 전부; 파드 120편: 결정 1,200·편당 10·과표집 29.67 %·자연 22.85 %·양방향 35.38 %·저장 표시/재선택 불일치 0 | 일치(§76), 주석 **D-3** |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` (5, 6] cm | 0.05 아님·0.0500001 참·0.06 참·0.0600001 아님 | 일치(§74) |
| 4 | 분할 = 에피소드 (E :122) | `pool_split`, `calib.halves:28-31`, `calib.py:123-125` | 섭동 40/40/40, fit/eval 60/60·섭동별 20/20, 결정적; 파드 판 안 혼합 0 | 일치(§76) |
| 5 | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py:26-38`, `aiworker.py` | 20 Hz 곱 시각 정확히 1.0 s → 성공, 0.95 s 아님, 중간 None → 끊김 | 일치 |
| **6** | 호출 기록 필드: 질문별 확률·요청/응답 원문(E :125), Astra A6 요청 원문·최대 토큰·원응답(E :126, 정본 §28 :255), 부가 JSONL = 위 필드(E :127) | `core.py:266-271,367-374`, `ir_policy.py` | 파드 C5 `call` 50행·C2 39행: 요청 해시 64자리 hex 전부·이미지 {cam_head, cam_wrist_right}·카나리 id 있음, `answers` = [choice, p] 뿐; `astra` 행에 원응답·요청 원문·최대 토큰 없음 | **불일치 → D4** (정본 §42 목록은 일치) |
| 7 | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `stats.py:4` | 파드 e05·rd·calib·closed `meta.bootstrap.n_boot` 10000 | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `stats.cluster_diff_ci`, `closed.aggregate` | 구성 폐루프 12짝: RD 0.5·`n_seeds` 6·재표집 단위 "layout seed" | 일치 |
| 9 | 판정 2 Holm "LA-2 또는 C2''"(하한 > 0) (E :131, :257) | `e05.gain_holm:218-226`, `stats.holm_ci(direction="greater")` | 완전히 음인 구간 기각 아님·다음 수준 안 풂(1단계 수준 0.975); 이득 정확히 1/50 + 기각 + lo > 0 → `keep_a`, 0.0199 → 아님, lo = 0 → 아님 | 일치(§74 N1) |
| 10 | 판정 10 (E :265) | `e05.block_diff_lo`·`block_diff_holm` 양측 | lo = 0 → 효과 없음, 1e-9 → 있음 | 일치(§74) |
| 11 | 카나리 "하한 > 0, Holm" (E :139) | `harvest/canary.py:31-55` | 한 질문만 바닥 위 → 표류 의심(그 질문만 기각), 모두 바닥 아래 → 아님, 군집 = 편(10) | 일치 |
| 12 | 판정 절 해시·시각을 실행 기록 첫 줄에 (E :133) | `eval/common.py:419-437` | 로컬 `run_meta` 키 순서 `utc` → `prereg`, check OK; 파드 4개 OK | 일치(§73) |
| 13 | 카나리 기준일 = 세트를 처음 돌린 날 (E :140) | `eval/canary.py:210-218` | 파드 가짜 날짜(scratch 루트, 모의): 세트 t_a 09-20 기준 없음 → 09-22·**09-25 기준 09-20**; t_b 09-23 없음 → 09-26 기준 09-23 | 일치 |
| 14 | "모델 식별 필드가 바뀌어도 같은 처리" (E :139) | `calibration.Calibration.load:255-267` | 다른 지문 → 거부 | 일치(§73 D3) |
| 15 | E0.5 표 = t_s − d_p95 − {0, .33, .66} (E :236) | `e05.vote_steps:44-58` | 스텝 6 = (−0.33, −0.66, −0.99); 파드 Isaac C5 H = 1 3표 스텝 오프셋 (−0.32, −0.65, −0.98) 등(한 틱 밀린 송신) | 일치 |
| 16 | 재시험 1회 (E :237) | `e05.py:349-353` | 첫 블록 첫 답 대 표(코드) | 일치 |
| 17 | 같은 시각 K = 3 동시 (E :238) | `e05.py:535-541`(`asyncio.gather`) | 파드 `meta.same_k` 3 | 일치 |
| 18 | newest / LA-2·γ 2/3 / C2'' / C2' (E :240) | `analysis/replay.py:11-30`, `e05.py:61-65,137-149` | la2(a,b,a) = a, la2(b,a,c) = 첫 표 b; 런타임·재생·e05가 같은 `share_at_least` 객체 | 일치(§74) |
| 19 | `C_flip` 두 식 (E :242) | `e05.py:77-87` | 코드 | 정본 기록(§73) |
| 20 | A0–A4, 층 (E :246) | `options.variant`, `e05.analyze` | 구성 재생에서 층별 a0–a4 정답률·follow·first_pick 있음 | 일치(flip은 D2) |
| 21 | 판정 1–3 (E :256-258) | `replay.judge_e05:33-50` | flip 0.0499 → narrow, 정확히 5/100 → 판정 1 아님(→ 3) | 일치(§74) |
| 22 | 판정 4 (E :259) | `replay.py:51-56` | 0.83 − 0.80 → one_flip; 섭동 flip 정확히 2배 → 유지; AUROC 0.6999 → 아님 | 일치 |
| 23 | 판정 5 재시험 빼기 (E :260) | `e05.py:447-448` | 코드(보고 값) | 일치(N11) |
| 24 | 판정 6 < 1 % (E :261) | `replay.py:57-58` | 0.01 → 단서 없음, 0.0099 → 단서 | 일치 |
| 25 | 판정 7 (E :262) | `e05.py:449-453` | `at_least(0.02)` ∧ `above(lo, 0)`, 보고 3값(코드) | 일치 |
| 26 | 판정 8 (E :263) | `e05.py:454-459` | `above(lo, 0)` 층별(코드) | 일치 |
| 27 | 판정 9 (E :264) | `replay.py:59-68` | A1 − A0 하한 정확히 −0.02(부동소수) + follow 하한 > 0 → neutral; A4 flip 0.05 → C3'' 필수 | 일치 |
| 28 | 판정 10 시간 블록 (E :265) | 행 10 | 행 10 | 일치 |
| **29** | FLIP_TH 초기값 후보 = 성공 궤적 1−α 분위, α 0.01 (E :253, :487; M4 :285, :287) | `e05.py:406-409` | 구성 재생·파드 산출 키 q0.95·q0.90 | **불일치 → D1** |
| **30** | 같은 시각 뒤집힘 성공·섭동 따로, A1–A4 각각 A0 대비 flip (E :253, 정본 §27 :243) | `e05.py:346-348,393,370-376` | 같은 시각 = 한 값, 층별 flip = A1·A4만 | **불일치 → D2** |
| 31 | d_p95 = E0 값, 재실행 규칙 (E :236, :278) | `e05 --d-p95` 0.307 | 정본 §55·§74 | 정본 기록 |
| 32 | E0.5 분당 400 [가정] (E :277) | 없음 | 로컬 서버 | N11 |
| 33 | E1 자료 반분 (정본 §52) | `calib.halves:28-31` | 정본 §73 | 정본 기록 |
| 34 | ECE = 15 동일 질량 (E :320) | `calibration.ece_mass:71-83` | 독립 구현과 n ∈ {1, 7, 15, 16, 17, 29, 31, 100, 437} × 10(동점 포함) 차 > 1e-12 0건 | 일치 |
| 35 | 오답 < 30 → 판정 불가 (E :320) | `calibration.py:215` | 30 → 켬, 29 → 끔 | 일치 |
| 36 | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.py:59-64` | n 10·α .1 → 10, n 5 → inf, n 19 → 18; 부동소수 올림 오차 n ≤ 5,000 × α 3개 0건 | 일치 |
| 37 | log p 1e-6 자름 (E :333) | `calibration.py:20,23-30` | p = 0, T 2 → 1e-3/1.001 | 일치 |
| 38 | 질문별 온도 (E :334) | `calibration.fit_temperature` | 정본 §73 N5 | 정본 기록 |
| 39 | 원 확률: ECE ≤ .03 ∧ T ∈ [0.8, 1.25] (E :335) | `calibration.py:92` | 150항목 15묶음 각 |0.8 − 0.77| = 0.03000000000000003 → 원 확률 사용(T 0.872) | 일치(§74) |
| 40 | 판정 1 (i)–(iv) (E :339) | `calibration.py:210-228` | 모든 문턱 정확히 경계에서 켬, ECE .0501·상한 .0801·AUROC .7499·하한 .6999·정확도 .7699·하한 .7199·적용률 .1999 각각 끔 | 일치(§74) |
| 41 | 판정 7 재보정 결속 (E :345-346) | `calibration.py:255-267`, `core.py:124-127` | 같은 지문·같은 해시 → 읽음, 다른 지문·다른 question_id 해시 → 거부 | 일치(N11) |
| 42 | 판정 8 J5, 적합 400 미만 "보장 없음" (E :347) | `calibration.py:229-233` | 경계 켬, 하한 .8699·단일 .4999·정확도 .8999 각각 끔, 400 보장·399 없음 | 일치 |
| 43 | `ambiguous` ECE 제외 (E :359) | `calibration.evaluate:131-163` | 40항목 중 애매 10 → `n_ece` 30, 따로 보고 10; 파드 calib `n_ece` 96 | 일치(§73) |
| 44 | E1 판정 2–6·2일 반복 등 | 없음 | 정본 §73 N5 | SCOPED S10 |
| 45 | N_max = ⌈d̂/T_c⌉+1, C2 상한 없음 (M4 :258, :332) | `m4.py:178-182` | d̂ 0.307 → 2, 0.33 → 2, 0.34 → 3, 0.9 → 4; C0·C1·C6 → 1; C2 → inf; 무작위 대조 in-flight 최대 C5 6·C6 1 | 일치 |
| 46 | γ = 0.67 = 3표 중 2 (E :487, M4 :276) | `m4.py:46,72-77,288` | 2/3·4/6·66/99 참, 66/100·3/5·1/2 거짓, 소수 0.67은 문자 그대로; 원장 a,b,a → 세 번째 표에서 확정, a,b,c 없음 | 일치(§74) |
| 47 | W 정의, W = 0 즉시, W < 0 거부 (정본 §72) | `m4.py:109-110,246-255` | W 0/1/2 → 도전 표 1/2/3번째에서 교체, −1 거부 | 일치 |
| 48 | 비가역 W+1 (M4 :291) | `m4.py:243,251` | W 1 비가역 → challenger, defer, replaced(3표) | 일치 |
| 49 | τ = 1(접촉 근처 0), near ≤ 5 cm (E :487, 정본 §7) | `core.py:44-56`, `m4.py:199-208` | 5.00 cm near·5.01 아님·접촉 near; 옆 칸 멀리서 agree, near에서 challenger | 일치(§73·§74) |
| 50 | conformal α 0.01·w 5 ((b) 경계) (E :487) | `measure.py`(확인 헤드 보정 파일) | 기본 미보정 | SCOPED S5 |
| 51 | STALE_MAX 1.5 s (E :487, M4 :288) | `m4.py:53-58,217` | C5 나이 정확히 1.5 → 유지, 1.51 → 폐기; 누적 합 부동소수 1.5 유지 | 일치(§75 N1) |
| 52 | C2 = VLM Stream, 5 s 타임아웃 (E :495, M4 :332) | `conditions.py:22`, `m4.py:220-226,300-304`, `core.py:451-456` | 2 s 나이 적용(1.5 폐기 없음), 시작한 스텝 대상 늦은 답 `newest`, 옛 요청 `older`, 5.00 s 적용·5.01 s 기본 행동, 확정 0; 파드 Isaac C2 표 117개 모두 `newest`·`log_only` 0·확정 0 | 일치(§74 D2) |
| 53 | C0·C1·C3·C4·C5·C6 설정 (M4 :329-345) | `conditions.py:19-27` | 무작위 대조 H = 3 315판(45판 × 7조건): 6522fda와 다른 판은 지연 정확히 1.5 s(C0 1·C1 1·C3 3·C4 2·C5 3)·5.0 s(C2 4)뿐, C6 0 | 일치(§75 N1·§76 N1), 되먹임은 행 54 |
| **54** | C5 = §4.2 전체 — (b) 범주를 결정 모델 입력에(`last_step`), C4 "범주", C5' = 그것을 뺌, 판정 3 (M4 :155, :232, :340-342, :361) | `core.py:191-207`(입력), `:504-512`((b) → 원장만) | DEVIATE 뒤 요청 46개 중 결과를 담은 것 0(C5·C4) | **불일치 → D3** |
| 55 | H 1과 3, H = 1 = 같은 스텝 앞당겨 2~3회 (정본 §2 :18, M4 :188-189, :273, E :183, :197, :236) | `m4.py:61-69,184-190`, `closed.py:151-166,291-292` | 가짜 세계 격자 위 0.307 s: 묻기 3·받아들인 표 2·확정 203–219(C3·C5·C6); 격자 밖 시작(1.00–1.30 s): 0.307 s 묻기 2, 0.45 s는 위상에 따라 1·2, 0.6 s 대부분 1(§76 N3 그대로); 파드 Isaac C5 H = 1 묻기 중앙값 3·받아들인 표 중앙값 2·`commits` 187·호출당 슬롯 3 | 일치(§75·§76) |
| 56 | n_LA 2 (M4 :275) | `m4.py:286-288` | a,a 확정, a,b 아님 | 일치 |
| 57 | 조기 호출은 주기 슬롯을 당겨 씀 (M4 :262) | `core.py:414-421` | 로컬 시험 `test_early_call_pulls…` 통과(860 중) | 일치 |
| 58 | FLIP_TH 끔 (M4 :287, 정본 §6) | `m4.py:89,279` | 기본 None; 0.5로 두면 flip_score 1.0에서 확정 없음 | 일치 |
| 59 | 경계 직후 W 2·γ 1.0, 큐 임계 g, 장면 변화 (M4 §3 #5, §4.3) | 없음 | 정본 §73 D5 | SCOPED S9 |
| 60 | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.py:131-142` | 27/30 적격·0.8999 아님; 차 0.02 → plan, 0.0201 → short1 | 일치 |
| 61 | 폐루프 RD 재표집 = layout 짝 (EVAL :184) | `closed.py:56,101-133` | 행 8 | 일치 |
| 62 | 주 RD = Score (EVAL :182) | 성공률 | 1차판 [가정] | N11 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | 정본 §71 보충(기준선 비교는 본 실험) | SCOPED S1 |
| 64 | M4b 2,000회 | `m4b/*` | 정본 §72 예외 | 일치 |
| 65 | E-M4-lat STALE_MAX 비례 (정본 §74 보충) | 없음 | 지연 큐 없음 | SCOPED S11 |
| 66 | H = 1 창이 비면 d̂ 뒤 첫 스텝 (정본 §75 (ii), 보충 (3)) | `m4.py:67-69` | lead 0.2 → [1] | 정본 기록 |
| 67 | `lead_max` 유한한 양수, 기본 1.0 (정본 §75 보충 (1), §76 N4) | `m4.py:106,111-113`, `closed.py:163-165,370` | inf·−inf·NaN·0·−0.0·−1 거부, 1e-9·1.5·1e6 받음; 파드 `--m4-lead-max 0|-1|nan|inf`(H 1)·`inf`(H 3) rc 1, `-inf`는 argparse rc 2; 파드 `meta.m4_lead_max` 1.0 | 일치(§76) |
| 68 | E0 판정 4 오프라인 스텝당 표 수 (E :183, :197) | `analysis/latency.py:85-88` | 0.307·lead 1.0 = 3, lead 1.5 = 4 = 런타임 묻기 수 | 일치(중앙값 집계·E0 도구는 N7) |
| 69 | E-M4 판정 7 H = 3 대 H = 1 (M4 :365) | 다스텝 DecCall 없음 | 정본 §75 보충 (2) | SCOPED S12 |
| **70** | 고정 구간(FROZEN) = "now + d̂ 이전" (M4 :150, :205) | `m4.py:228` 시작한 슬롯만 | 시작 0.02 s 전 도착 표 `tentative` | 해석 N3 |
| **71** | 카나리 표류 의심 → 그날 분리 보고, E1 재보정 뒤 게이트 재사용 (E :139, :347) | `common.run_meta`(`meta.canary`), 런타임 강제 없음 | 파드 산출 `meta.canary` = {id, stale True, drift_suspect} | 운영 절차 N6 |
| **72** | 응답 모델 필드 매 호출 기록 (E :51) | `models.JevLSelector` `meta.model`·`model_ok`, `common.Asker` `model` | 코드(모의 판은 `{"mock": true}`) | 일치 |
| **73** | 재시도는 우리 코드, 횟수 기록 (E :54) | `common.Asker.ask:272-285` `tries` | 코드 | 일치 |
| **74** | E0.5 채점 = 결과 기반 라벨 (E :241, prereg_labeler) | `e05 --truth` 기본 labels_v2 | 정본 §54·§65 | N4 |
| **75** | E0.5 표현 D-줌 + H안(`fine_dir`), E1 질문군 9종 (E :239, :299-309) | `common.QUESTIONS` 5 | 정본 §54·§71·§73 N5(fine_dir 언급 없음) | N5 |
| **76** | Astra 카나리 (E :138) | "none" | 정본 §67 보충 | SCOPED S6 |

### 5.1 11회차 표(`r7_cycle11.md` §5)와의 차이
- 행 6: 11회차 "일치"(요청 해시·이미지 해시·카나리 id만 봄) → 이번에 E §1.6·§28 A6의 전체 필드 목록과 대조해 **불일치(D4)**.
- 행 50(11회차 행 50 "C0·C1·C3·C4·C5·C6 정의")에서 C5 문장의 "§4.2 전체"를 의사코드 끝까지 따라가 (b) → 결정 모델 입력 줄을 찾음 → 새 행 54 **불일치(D3)**.
- 새 행 29·30(E §2A.5 지표): 1–11회차 표는 E0.5 **판정** 1–10만 대조했고 §2A.5 **지표**는 표에 없었다 → D1·D2.
- 새 행 70–76: FROZEN 읽기, 카나리 표류 뒤 처리, 모델 필드·재시도, 채점 정답, 질문 집합, Astra 카나리(모두 NOTE·SCOPED).
- 행 2·4: §76 D-2가 정본에 들어가 "값 일치, 정의 미기록(11회차 D-2)" → 일치, 대신 코드 주석 **D-3**.
- 행 67: 11회차 "inf는 통과 후 첫 호출에서 실패(N4)" → 거부(§76 N4).

## 6. 확인한 것 (근거)

### 6.1 11회차 수정(정본 §76)의 독립 확인 (과제 2)
- **N4 `lead_max`**: 로컬 `M4Params` 거부 6값·수락 5값(행 67), `closed.m4_config("C5", 1|3, inf)` ValueError, `closed.main([... "--m4-lead-max", "inf"])` → ValueError이고 출력 폴더 없음. 파드 가드(§6.4). 시험 `test_lead_max_must_be_finite_and_positive` 4개가 로컬·파드 수치에 들어 있음.
- **D-2 경계 사례**: 정본 §76 문장("그 스냅샷이 `ambiguous`이거나, 그 스냅샷에서 시작하는 결정 스텝(다음 연속 스냅샷, 0.33 s) 동안 등록부 술어 값이 하나라도 바뀌는 경우", "섭동 배정 = 시드로 정한 고정 순열, P0·P1·P2 각 40편, 분할 fit/eval 60/60(섭동별 20/20)", "E0.5·E1 기본 판정에 쓰이지 않고 … `calib --decision-only`에서 쓰인다")을 행동으로: `boundary_flags([{a:1,b:0},{a:1,b:0},{a:0,…},{a:0,…},{…,b:1}], F×5)` = [F, T, F, T, F](앞 방향만), 파드 풀 재계산이 저장값과 같음, `e05.py`는 `decision`·`oversampled`·`boundary_case`를 읽지 않음, `calib.items_from(decision_only=True)`는 결정 스냅샷만. pool.md 수치(29.67 %, 22.8 %, 35 %, 4.6 %)와 파드 재계산(29.67 %, 22.85 %, 35.38 %, 4.65 %)이 같다(자연 비율의 0.03 %p 차는 분모 차로 보이며 판단에 영향 없음). 주석 불일치는 D-3.
- **D-1 표시**: handoff `:102`, `r7c10_fixes.md:72`·`:85`–`:87`에 [해결 R7 11회차 D-1] 있음(행 51 표시의 렌더링 문제는 N1). 11회차가 놓친 `r7c9_fixes.md:88`은 D-2.
- **N1 문구**: 정본 §76 "지연이 정확히 1.5 s(C2는 5.0 s)인 경계 판을 뺀 표본에서 참" — 내 무작위 대조(행 53)와 같다.
- **N3**: 격자 밖 시작에서 H = 1 표 수가 1로 떨어지는 지연·위상(행 55) — §76 N3 서술 그대로.

### 6.2 9·10회차 동작 재확인
- 정확히 2/3(행 46), C2 스트림(행 52, 로컬 원장 + 파드 Isaac), H = 1 스텝당 표(행 55, 가짜 세계 + 파드 Isaac `commits` 187 = 11회차와 같은 값), H = 3 불변(행 53: `fw_run.py`로 6b013ac와 6522fda를 같은 315판 — 7조건 × 45판, W ∈ {0, 1, 2} 무작위, 잡음 선택기 0/15/30 %, 지연 {0.2, 0.307, 0.33, 0.5, 0.75, 1.0, 1.4, 1.5, 1.6, 2.5, 5.0} s 고정 또는 흔들림(0.15–0.45 s, 7 % 1.3–1.8 s), 시작 오프셋 0–8 s — 행동 바이트 해시·원장 counts·epoch·실행 계정·호출 수·호출당 슬롯 비교): 다른 판 14개는 모두 지연 정확히 1.5 s(C0·C1·C3·C4·C5) 또는 5.0 s(C2) — §75 N1의 의도된 변경. 나이 경계 `older_than`(행 51).

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st`로 R2 DEV `/data/harvest/r2/dev/*/*/P0` 전 편 `validate_episode`: **36/36 errors 없음**, 모두 DEV, 성공 mug_tray 12·mug_marker 12·bottle_tray 8, 변형 {standard, dr}(08:58:30 UTC). LeRobot 내보내기 시험 **6 passed**. |
| 2 모델 | 충족 | **단계 B S-E2E**(GPU 2): `stageb_train train --data se2e --run r7c12_se2e --out-root <scratch> --max-train 40 --max-steps 6 --batch 2 --max-val 4 --eval-every 3 --reload-check --seed 44` → rc 0(08:55:43–08:56:44 UTC), 검증 dec 3.526 → 2.895 → 2.303(fm은 N10), `save_load` `max_abs_action_diff` **0.0**, 재적재 전후 eval 같음. CUDA 시험(GPU 2, `tests/train` + `test_fused_action.py` + `test_fused_model.py`, 서빙 포함) **110 passed**(08:56:44–08:58:01). |
| 3 폐루프 | 충족 | 모의 `closed --model mock --split dev --seeds 7 --conditions C5,C2 --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c12 --m4-h 1`(08:58:01–09:01:33) → `CLOSED_DONE`, C5·C2 성공 1.0(16.58 s·12.92 s). 로그 행: `call` 50 + 39행 모두 64자리 hex `request_sha256`·`image_sha256` {cam_head, cam_wrist_right}·`canary_id` `cn20260924_mock_ae0d1a`, `astra` 2 + 2행 hex·{cam_head}·"none"; `policy_config`에 정본 §42 목록(astra_prompt_id·question_ids·model_id·astra_effort·T_c·clock·m4) + `trial_metadata.ours_sidecar`. `meta.bootstrap` n_boot 10000(= `result.bootstrap`), `meta.prereg` OK, `meta.m4_H` 1, `meta.m4_lead_max` 1.0, C5 호출당 슬롯 3·받아들인 표 스텝당 중앙값 2·`commits` 187·`dropped_stale` 0, C2 `newest` 117·확정 0. (호출 기록 필드 부족은 D4 — 완료 정의 3의 "한 판 끝까지"는 충족.) |
| 4 평가 | 충족 | 모의 한 명령(`venv_vllm`, GPU 없음): `e05 --data jsel_dev/P0,P1 --split dev --episodes 2` → `E05_DONE`(claim `a_as_stabilizer`, 판정 키 j2·j5·j7·j8·j10 모두, `same_k` 3), `rd --variants standard=jsel_dev/P0,random=gen_dev/random/P0 --episodes 1` → `RD_DONE`, `calib --fit-data pool --fit-split pool --heldout jsel_dev/P0 --heldout-split dev --episodes 4` → `CALIB_DONE`(질문별 `n_ece` 96). 모두 rc 0, n_boot 10000, prereg OK. (E0.5 지표 결함은 D1·D2.) |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git `6b013ac9…`·`code_sha`·카나리·시드·모델·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`; 정리 뒤 흔적 없음(N12). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`; 거부 뒤 출력 폴더 0개)
- `e05 --split cal|test|test_p5`, `calib --fit-split cal`, `rd --split test`, `closed --split test --seeds 1000`, `closed --split cal --seeds 549` → "--split X refused: set HARVEST_ALLOW_SPLIT=X (main session only …)". `closed --split dev --seeds 30`·`1149`, `--split pool --seeds 5` → "not in split … (refused, never opened)". `--isaac-gpu 2` → "0 or 1 only (GPU 2 never renders)". `--m4-h 0` → ValueError. `--conditions C2p` → "runtime has [C0…C6]". **`--m4-lead-max 0`·`-1`·`nan`·`inf`(H 1)·`inf`(H 3) → ValueError "must be a finite > 0 s (canon §75, §76)"**, `-inf` → argparse rc 2. `HARVEST_ALLOW_SPLIT=dev closed --split test`, `HARVEST_ALLOW_SPLIT=cal e05 --split test` 거부. `gen gen --seeds 10005-10006` → "R2 generates DEV 0-29 only (… --confirm-train)". 카나리 `build-set --seeds 1000-1001`(DEV 폴더) → 결정 스냅샷 0개로 멈춤(폴더에 그 시드 파일이 없음 — CAL 폴더를 주면 `check_seeds`가 거부). **23건 모두 rc ≠ 0.**

### 6.5 A. 테스트
- 로컬(`D:\tools\scratch_qdd\r7c12\repo` = 6b013ac archive, Git Bash, `python -m pytest -q -rs -p no:cacheprovider --basetemp=…\r7c12\pt1 -o addopts=""`, TMP·TEMP·TMPDIR = scratch, 08:35:56–08:38:02 UTC): EXIT 0, **860 passed · 11 skipped**(건너뜀 = torch 없음 7, inspect_robots 2, pyarrow 1, TODO(P3) 1). 860 = 856(43cd1ff) + 4(새 매개 시험); 재생 조사 에이전트의 커밋 안 된 시험 4개는 사본에 없음.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, TMPDIR·pyc·카나리 루트 = scratch, 08:55:44–08:57:38 UTC): **902 passed, 3 skipped**, EXIT 0(건너뜀 pyarrow·CUDA 없음·TODO(P3)). 파드 CUDA 110 passed, LeRobot 6 passed.

### 6.6 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외, 정정 표시 유무 분리)
- 정본 범위 `§1~§N`·"지금 §N": `handoff.md:3`·`:5`·`:83` = §75(**D-1**); 나머지는 R7 보고서의 당시 기록.
- `[결정 필요]`·"메인 확인"(현재 상태 문서 — handoff, `docs/stage3/**`, 계획, draft-log, README, CLAUDE.md, 코드·시험): `r7c9_fixes.md:88`(**D-2**); `r7c9_fixes.md:15`·`r7c10_fixes.md:72`·`:85`–`:87`·handoff `:101`·`:102` 해결 표시 있음; `se2e_data.md:107` 제목 "[결정 필요, R4·S-E2E 설계]"은 바로 아래 갱신 줄(1–3 해결, 4–6 S-E2E 사전 등록)이 있음; `e_m4b_meas.md:50`·`:211`은 사전 등록 조건 문장과 미실행 기록; handoff `:13`·`:46`·`:58`·`:75`, CLAUDE.md, draft-log 앞 절은 단계 1–2 규칙·기록.
- `lead_max`: 코드·정본 §75–§76·E 문서·시험 — 서술 일치("유한"이 빠진 주석 2곳 N2).
- 경계 사례·`boundary`·`ambiguous`: 정본 §76·`pool.md:25`·`snapshot.boundary_flags` 설명·`cli_pool.choose_from` 설명 일치, `snapshot.py:31`·`:119-121`(**D-3**), 옛 계획서 `:1394`(N11).
- "H = 3 비트 동일"·155/155: 정본 §75 D1(§76 N1이 덮음), `r7c10_fixes.md:65`·`:88`, handoff `:102`는 수정 에이전트 표본의 기록 줄(참).
- 되먹임·`last_step`·C5' (D3): 코드 `conditions.py:11-12`(C4 "(b) categories", C5 "(a) + (b)"), 정본 §17 `:163`·§20 `:180`(되먹임 주장), 논문은 N11.
- 호출 기록 필드 (D4): `r5_closed_loop.md`·`r6_eval.md`의 로그 서술은 정본 §42 목록 수준이라 거짓 서술 없음; 확률·원응답 부재를 적은 곳도 없음.
- 옛 사실 재확인(9–11회차 목록): γ 소수 0.67, "C2 = newest", 부트스트랩 2,000, "W=2 흡수", near "< 5 cm", `older_than`·원시 나이 비교(`M4:203` 사전 등록 인용뿐) — 새 누락 0.
- 카메라(§47): 폐루프 이미지 키 {cam_head, cam_wrist_right}(§57), 6b013ac 변경 파일에 카메라 서술 없음. GPU: "GPU 2 = 렌더 금지" 서술·가드 일치(`--isaac-gpu 2` 거부). 시드: 정본 §66 표 = `splits.RANGES`. 날짜: 정본 §76 08:30 UTC·handoff 머리 08:30·draft-log 08:30·direction-log 08:30·커밋 08:32:33 UTC 서로 맞음.

### 6.7 F. 규칙·위생
- 저장소: 작업 트리는 읽지 않고 쓰지 않음(archive만; `git status`는 재생 조사 에이전트의 3개 항목 그대로), 이 보고서 한 파일만 추가. 로컬 C:: N12(이 저장소 산출물 0). 파드: 시작 전·후 목록 대조로 내 항목만 삭제(머리 규칙 준수 줄), 끝에 내 프로세스 0, 재생 조사 Isaac(GPU 0)·`/data/harvest/data`·`r2/dev`·`canary`는 읽기만(카나리 시험은 scratch 루트 `HARVEST_CANARY_ROOT`).

## 7. 다음 순회 전에 할 일 (제안)
1. **D1**: `e05`의 FLIP_TH 후보에 사전 등록 α 0.01(q0.99)을 넣는다(M4 α 범위 {0.001, 0.01, 0.05}도 같이 낼지, 0.1을 뺄지 정본에 한 줄).
2. **D2**: 같은 시각 뒤집힘을 성공 궤적·섭동 궤적으로 나눠 보고, 층별 A2·A3의 A0 대비 flip(`option_key`) 추가 — 또는 정본에서 범위를 정한다.
3. **D3**: 결정 메인 세션 — (가) DecCall 입력에 직전 스텝 (b) 범주 한 줄을 넣는 형식 변경(단계 A·B 학습 형식과 함께), 또는 (나) 정본에 "런타임 C5·C4 = (b) 범주 되먹임 없음(= C5'), M4 판정 3은 형식 변경 전까지 SCOPED, 논문 새로움 문장에서 '되먹임' 보류"를 적고 `conditions.py` 설명을 고친다(§75 보충 (2)와 같은 처리).
4. **D4**: 결정 호출 행에 질문별 확률 분포(이미 받은 `probs`)와 요청 원문(텍스트 상태·질문; 이미지는 해시), Astra 행에 요청 원문·원응답(`output_text`)·최대 토큰을 싣는다 — 또는 정본에 런타임 기록 범위를 결정으로 적는다.
5. **D-1·D-2·D-3**: handoff `:3`·`:5`·`:83` → §76; `r7c9_fixes.md:88`에 [해결: 정본 §74 보충 (가) 비례 규칙] 표시; `snapshot.py:31`·`:119-121` 주석·인자 이름을 "boundary stratum (`boundary_flags`: ambiguous or a predicate change to the next snapshot, canon §76)"으로.
6. NOTE N3–N8은 정본 한 줄씩(FROZEN 읽기, E0.5 채점 정답, 질문 집합, 카나리 표류 뒤 게이트, E0 도구, 범위 밖 실험 목록)으로 닫을 것을 권함. N1·N2는 다음 문서·코드 정리 때.
