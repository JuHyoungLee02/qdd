# R7 객관 검증 순회 — 8회차 (cycle 8, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님, 7회차 결론·수정 기록에 기대지 않고 다시 돌림). 작성 2026-09-25 03:50 UTC(`date -u`; 시작 03:17:29 UTC, 파드 첫 명령 `Fri Sep 25 03:29:44 UTC 2026`, 파드 정리 끝 `03:44:37 UTC`).
- 대상: `D:\qdd` `dev` HEAD `aad30d6` = `origin/dev`(`git ls-remote`), 태그 `stage3-r7fix7`, `main` = `origin/main` = `520b2be`. 작업 트리 깨끗(시작·끝 `git status` 출력 없음). `3ed2e49..aad30d6` = 코드 12개(`analysis/stats.py`·`canary.py`·`eval/{calib,closed,common,e05,rd}.py`·`runtime/{calibration,m4}.py`·시험 3개) + 문서(정본 §72, M4·M5·SUMMARY 정정 표시, handoff·direction-log·draft-log·`r6_eval.md`, `r7_cycle7.md`·`r7c7_fixes.md`). 파드 사본 = `git -c core.autocrlf=false archive HEAD`(+ JSON `CODE_VERSION`), 모든 산출 `meta.git` = `aad30d6…`, `meta.code_sha` = `6eacb1d83de799b6`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle2.md`–`r7_cycle7.md`, `r7_fixes.md`, `r7_sweep6.md`, `r7c7_fixes.md`, 정본 `00-interfaces.md` §1–§72(뒤 절 우선; §67–§72 SCOPED는 근거만 확인, [사용자] 제목 절 본문은 §67 규칙, 논문 .tex vLLM 서빙 서술은 §70에 따라 NOTE, `r7_sweep6.md` §3 열린 항목은 완료 정의 1–5를 막지 않으면 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`M4-overlap-commit.md`(변수·기본값).
- 분류 기준(7회차와 같음 + 이번 과제의 대조 규칙): **DEFECT** = 코드가 정본·사전 등록 규칙과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것(사전 등록 대조표에서 어긋나고 정본 기록이 없는 것 포함). **DOC** = 지금도 참고되는 문서·주석의 현재 시제 서술이 HEAD와 다르고 정정·해결 표시가 없는 것, 그리고 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 정본에 적히지 않은 것.
- 규칙 준수: 코드·문서 수정·커밋·푸시 없음(이 보고서만 씀). git은 `-c safe.directory=D:/qdd`(전역 설정 안 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c8`(스크립트는 모두 Write 도구로 D:에 쓰고 경로로 실행, Git Bash heredoc·`python -` 표준 입력 안 씀 — 파드 스크립트 초안에 들어갔던 herestring 한 줄은 전송 전에 지웠고 `grep -c "python -\|<<"` = 0 확인). 파드 파일은 `/data/harvest/tmp/r7c8`(코드 사본·체크포인트·산출·pytest, 1.8 GB)와 작업자가 만든 `ir/kitcache/cyclo-r7c8{,f}_standard`(각 208 MB)·`cache/pyc_r6/data/harvest/tmp/{r7c8,tmp5w_uwcgp,tmpl_y5_b1u}`·`tmp/{carb.FFjIYL,carb.ROFDQR,hub-root.lock,tmp5w_uwcgp,tmpl_y5_b1u}`·`tmp/fused_frames/2999780`·LeRobot 시험의 `cache/hf/datasets/parquet/default-4a96bd006ebccff9`(+잠금)뿐이고 **끝에 모두 지웠다**(03:44:37 UTC; 시작 전 목록과 대조해 새로 생긴 이름만). GPU: 단계 B 학습·CUDA 시험·융합 서버 = GPU 2(렌더 없음), Isaac = GPU 1, GPU 0(라벨러 896 MiB)·GPU 3 건드리지 않음, 끝에 0–3 = 896/5/1/1 MiB(시작과 같음). 시드 DEV만, `HARVEST_ALLOW_SPLIT`은 가드 음성 시험 1건에서 `=dev`만. 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. 남의 프로세스(라벨러 2개, 12 h 경과) 건드리지 않음.

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 5 |
| DOC | 2 |
| SCOPED | 8 |
| NOTE | 14 |

7회차 수정 다섯 가지는 독립 계산으로 모두 맞다(§6.1: Holm 손 계산 6예 일치, 등질량 ECE 손 계산 일치, RD 시드 격자 일치, M4 W ≥ 1 옛/새 코드 무작위 대조 3,600판 전부 비트 동일, 융합 `meta.prompt_config` = 체크포인트 구성). 완료 정의 1–5도 모두 다시 돌아간다(§6.3). 그러나 이번 판의 필수 과제인 **사전 등록 대조표**(§5, 47행)를 끝까지 채우자 7회차가 보지 않은 줄에서 코드와 사전 등록·정본이 어긋나고 기록이 없는 곳 다섯 군데가 나왔다: E0.5 판정 2의 Holm 누락(D1), E1 본 ECE에서 `ambiguous` 항목 미제외(D2), 매일 카나리 표류 규칙의 추가 조건·재표집 단위(D3), C5 설정 "접촉 근처 τ = 0" 미적용(D4), M4 경계 직후 엄격화(W 2·γ 1.0)와 큐 임계 조기 호출 미구현(D5). 문서는 handoff 머리의 정본 범위 "§1~§71"(D-1)과 사전 등록이 열어 둔 값의 정본 미기록(D-2) 두 건. 연속 무결은 **0회 그대로**.

---

## 1. DEFECT

### D1. E0.5 판정 2("LA-2 **또는** C2''")에 Holm 보정이 없다
- 사전 등록: `E-first-experiments.md:131`(§1.7 통계 공통, "네 실험 모두") "다중 비교: 한 판정에 여러 조건을 걸면 Holm 보정". 판정 2(`:257`, 해시 절 §2A.6) "flip rate ≥ 5%이고 **LA-2 또는 C2''**가 newest보다 +2%p 이상(하한 > 0)" — 두 조건(규칙) 중 하나라도 유의하면 참인 판정이다(같은 문서의 E2a 판정 1 `:445` "Holm 보정(3개)"과 같은 모양).
- 코드: `harvest/analysis/replay.py:32-33` `sig_gain = any(g >= 0.02 and lo > 0 ...)` — `gain_la2_lo`·`gain_c2pp_lo`는 각각 보정 없는 95% 하한(`harvest/eval/e05.py:357-358,391-392`, `mean_ci` 기본 수준 0.95). Holm이면 첫 단계 수준 1 − 0.05/2(97.5% 구간 하한 > 0)가 필요하다. 정본 §72는 판정 10만 Holm으로 고쳤고 판정 2는 기록이 없다.
- 확인(로컬, `D:\tools\scratch_qdd\r7c8\j2_holm.py`, 10,000회): LA-2 이득 평균 0.0633, 95% 구간 [0.0099, 0.1167](하한 > 0), 97.5% 하한 0.0, C2'' 이득 0 → `judge_e05` = **`keep_a`**(판정 2), 같은 뽑기의 `stats.holm_ci` = 두 규칙 모두 기각 못 함 → 사전 등록대로면 판정 2 불성립(`a_as_stabilizer`). 즉 사전 등록보다 느슨한 절차로 "(a) 주장 유지"가 나올 수 있다.

### D2. E1 본 ECE에서 `ambiguous` 항목을 빼지 않는다
- 사전 등록: `E-first-experiments.md:359`(§3.10) "`ambiguous` 항목은 **본 ECE에서 빼고 따로 보고**." 이 ECE가 판정 1(`:339`)·원 확률 규칙(§3.6 `:335`)의 입력이다(정본 §72가 §3.4의 구간 정의를 같은 방식으로 구속력 있게 읽었다).
- 코드: `harvest/eval/calib.py:34-51` `items_from`은 `ambiguous`를 보지 않고 모든 줄을 넣고, `runtime/calibration.py:106-138` `evaluate`·`:178-191` `judge_question`은 그 전체로 ECE·구간을 낸다. 따로 보고하는 값도 없다.
- 자료에 표시가 있다(파드 확인): POOL 연속 스냅샷 3,361줄 중 `ambiguous` 225줄(6.7%), `jsel_dev/P0` 앞 4편 109줄 중 12줄 — 모의 `calib` 판의 보류 편 `n`(dir_xy 107)에 그대로 들어간다.
- 기록 없음: 정본(§52·§54·§72)·`r6_eval.md`에 `ambiguous`/애매 처리 결정 0건(`grep`). 정답이 labels_v2(§54)로 바뀌어 "애매함"의 정의(near 띠 대 labels_v2 데드밴드·구간 경계)를 다시 정할 여지는 있지만, 그 결정도 기록이 없다.

### D3. 매일 카나리 표류 판정 = 정본 규칙 + 기록 없는 추가 조건, 재표집 단위도 다르다
- 정본·사전 등록: `00-interfaces.md:264`(§28) "기준 대비 불일치가 그날 바닥보다 유의하게 크면(**하한 > 0, Holm**) '표류 의심' → 그날 결과 분리 보고, E1 보정 재실행", `E-first-experiments.md:139`(§1.8) 같은 문장, 구간은 §1.7(`:130`) "에피소드(또는 스냅샷의 에피소드) 군집 부트스트랩".
- 코드: `harvest/canary.py:20-29` `drift_suspect = mean > 2 * floor and lo > 0` — "평균 불일치 > 바닥의 2배"가 덧붙어 있고 이 조건은 어느 설계 문서·정본에도 없다(`grep "2×바닥|2 × 바닥|2×floor"` 코드 외 0건). 재표집 단위는 `"<snapshot>|<question>"` 키(`:23-28`, 결과의 `boot_unit` "snapshot|question key")인데 파드 세트 `dev_v1`은 12 스냅샷 = DEV 시드 0–2 **3편**이다(매니페스트 확인) — 사전 등록 단위(에피소드 3개) 대신 60개 군집으로 구간을 낸다.
- 확인(`D:\tools\scratch_qdd\r7c8\canary_rule.py`): 바닥 0.10, 불일치 0.18, (불일치 − 바닥) 하한 +0.063 > 0 → 정본 규칙은 "표류 의심", 코드는 `drift_suspect: False`. 정본 §72는 카나리 결과에 `n_boot`·`boot_unit`을 싣는다고만 적었고 규칙·단위 차이는 기록하지 않았다. 표류 판정은 E1 재보정·결과 분리 보고를 부르는 운영 규칙이다.

### D4. C5 설정 "τ = 1(접촉 근처 0)"의 접촉 근처 τ = 0이 런타임에 적용되지 않는다
- 사전 등록: `E-first-experiments.md:487`(§4.12) "C5 설정(… γ=0.67, W=1, **τ=1(접촉 근처 0)**, α=0.01, STALE_MAX=1.5 s)". 같은 값 `M4-overlap-commit.md:277`(§4.4 τ 행 "1 (접촉 근처 0)"), `:307`(§4.6 "정밀 접촉 구간 τ=0").
- 코드: 원장은 `near` 인자를 지원하지만(`runtime/m4.py:137-146`, `:148`) 유일한 호출 `runtime/core.py:265` `self.ledger.on_vote(v, now, irreversible=irr)`는 `near`를 넘기지 않고, 확정 경로 `m4.py:215-217` `try_commit_prefix`는 `near` 인자 자체가 없다 → 순서형 질문(`mag_coarse`)의 τ는 어디서나 1.
- 확인(`D:\tools\scratch_qdd\r7c8\tau_near.py`): `small, tiny, tiny` 표에서 런타임 경로(near 없음)는 둘째 표가 `agree`로 들어가 LA-2 확정, `near=True`로 불러도 도전 표가 된 뒤 `try_commit_prefix`가 τ = 1로 확정한다. 정본에 접촉 근처 τ를 뺀다는 기록 없음(`grep "접촉 근처|τ=0"` 정본·단계 3 문서 0건). m4.py 머리의 "Not implemented" 목록에도 없다.

### D5. M4 경계 직후 엄격화(W 2·γ 1.0)와 큐 임계 조기 호출(g 0.5)·장면 변화 조기 호출이 구현되지 않았고 기록도 없다
- 설계 기본값(과제의 대조 범위 "M4 변수·기본값"): `M4-overlap-commit.md:150`(§3 #5 RTC 3구간 접목) "경계 직후 스텝은 W=2·γ=1.0, 멀수록 W=1·γ=0.67", `:214`·`:221`(§4.2 의사코드 `W(s.zone_dist)`·`gamma(s.zone_dist)`), `:281`(§4.4 W "1 (경계 직후 2)"), `:291`(W_irrev "경계 직후 2 → 3"), `:259`·`:289`(§4.3 조기 호출 "committed_ahead / needed < g (0.5)", "장면 변화 점수 > P90 두 번 연속"). 정본 §72(`00-interfaces.md:608`)는 "M4 기본값(§4.4 '**1, 경계 직후 2**')… 의 뜻이 그대로"라고 이 기본값을 인용한다.
- 코드: `runtime/m4.py:40-41` `W = 1`, `gamma = 0.67` 상수, `:182` `w = self.p.W + irr`(구간 거리 없음), `:218` 확정 비율 γ 상수. 조기 호출은 (b) DEVIATE/CONTRADICT(`m4.py:274-278`, `core.py:302,357,482`)만 있고 큐 임계·장면 변화 트리거는 없다(`grep committed_ahead|P90` 0건). `m4.py:22-25` "Not implemented" 목록·정본·`r7_sweep6.md` §3 어디에도 없다.
- 판단: 사전 등록 C5 설정(E §4.12 "γ=0.67, W=1")의 평탄한 값과는 맞으므로 동작이 사전 등록과 어긋나는 것은 아니다. 그러나 M4 설계 기본값·정본 §72가 인용한 기본값과 코드가 다르고 그 차이를 정한 기록이 없어 대조 규칙상 결함이다. 고칠 길은 둘 중 하나: 정본에 "E-M4 C5 = E §4.12 평탄 설정, 경계 직후 엄격화·g 트리거는 쓰지 않음(또는 절제)"을 적거나 코드에 넣는다.

## 2. DOC

### D-1. `docs/handoff.md:5`·`:83` 정본 범위 "§1~§71"(현재 §72까지)
- `:5` "> 현재 판본: 정본 `00-interfaces.md` **§1~§71**(뒤 절이 앞 절을 덮는다)", `:83` "`00-interfaces.md` §43부터 끝까지(**지금 §71**)". aad30d6이 §72를 더하고 같은 머리의 `:3`은 "정본 §1~§72"로 고쳤는데 두 줄 아래 `:5`와 §2.7의 "지금" 줄은 그대로다. 둘 다 현재 시제("현재 판본", "지금")이고 정정 표시가 없다. 정본 §71이 정본 범위를 정정 grep 목록에 넣었다(6회차 이전 `:5`는 sweep6에서 §71로 맞춤, `r7_sweep6.md:27`).

### D-2. 사전 등록이 열어 둔 평가 값을 코드가 정해 쓰는데 정본(§72 원칙)에 적히지 않았다
정본 §72 첫 줄은 "사전 등록이 정하지 않은 값은 이 절에 적는다"고 하고 seed·백분위·등질량 구간 세부·epoch 처리·W '연속'의 뜻을 적었다. 다음은 판정 입력에 들어가는데 빠졌다(코드 머리 설명·`r6_eval.md`에만 있거나 아무 데도 없음):
- E0.5 섭동 창 **1 s**(`harvest/eval/e05.py:159-161` `[가정: window 1 s after the perturbation]`, `:451` `--perturb-window 1.0`) — 판정 4(`:259`, 섭동 창 flip ≥ 성공 창 2배·AUROC)와 성공/섭동 궤적 분리의 입력. 사전 등록은 "섭동 직후 창"(`:232`)만 적었다.
- E0.5 시간 블록 = **한 실행 안에서 바닥 부분집합을 차례로 두 번씩 묻는 통과 B개**(`e05.py:12-13`, `:439-440` `--blocks 2`, `--floor-n 0`) — 사전 등록은 "블록 구분은 E0 시간대 슬롯과 같게 [가정]", 반복 횟수 "[가정]"(`:244-245`). 판정 10의 입력.
- E1 스냅샷 모집단 = 보류·적합 편의 **연속 스냅샷 전부**(`calib.py:39`, `--decision-only` 기본 끔) — 사전 등록 §3.3은 결정 스냅샷 풀(1,200)이었고 정본 §52는 CAL 편 반분만 정했다. 반분 방법(편 id sha256 정렬 뒤 교대, `calib.py:28-31`)과 AUROC 부트스트랩에서 한 부류가 빠진 뽑기를 0.5로 두는 관례(`runtime/calibration.py:142-144`)도 기록 없음.

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(정본 §71 보충) — 로컬·파드 모두 `tests/runtime/test_latency_ctrl.py:11` 1개 건너뜀. 기준선 비교(EVAL H1/H2)는 본 실험 단계.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66 "S-E2E 이후") — `gen --seeds 10005-10006` 확인 인자 없이 거부(§6.4).
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8 — `runtime/core.py:355`(patch/replace = epoch만) 그대로.
- S6. Astra 카나리 id "none" — 이번 두 폐루프 판 `astra` 행 2/2·5/5에 `canary_id: "none"`.
- S7. S-E2E 체크포인트 런타임 tau 마스크 차이(`r7_fixes.md` §7).
- S8. CONTRADICT-soft(§68 K6·§69) — `measure.py` 무변경(3ed2e49..aad30d6 diff에 없음).

## 4. NOTE
- N1. **융합 폐루프 결정 지연 p50 1.24 s**(이번 R2 소형 체크포인트 판, DEV 시드 7; 호출 75·청크 56·오류 0, RTF 0.760). 파드 load average 24 → 60(라벨러 Isaac 2개가 주) — 7회차 N6과 같은 양상. 지연 수치를 옮길 때 파드 CPU 부하를 함께 적을 것.
- N2. 카나리: 모의 판 `meta.canary` = `cn20260924_mock_ae0d1a`(전날, stale), 융합 판 `{"id": "none", "reason": "no canary for model fingerprint 2b7ebc70241c2cd8"}` — §68대로 S-E2E 시작일에 새로 만든다(D3을 고친 뒤).
- N3. §69 S-E2E 사전 등록 항목(층화 검증 부분집합·중간 체크포인트·평가 간격) 코드 선택지 없음 — 이번 판도 `n_val 1799` 중 `--max-val 4` = 앞 4개.
- N4. TEST2 1150–1299는 `splits.RANGES`에 없다(`check_layout_seed(1150)`·`(1299)` 거부). 연장을 쓸 때 넣을 것.
- N5. E1 범위: `calib`는 §3.7 판정 1·8만(판정 2–7, §3.5의 AURC·부류별 ECE·위치 편향·신뢰도 도표·`confidence` 필드 AUROC, §3.3 2일 반복은 없음). 완료 정의 4는 "보정(CAL 온도·J5)"이라 막지 않는다. §3.6의 "등위 회귀는 시험 ECE가 0.02 이상 낮을 때만" 비교는 정본 §52(질문별 온도)가 보정기를 정해 덮는다고 읽었다 — E1 실행 전 정본에 범위를 한 줄로 적기를 권한다.
- N6. 이미 만들어진 `calibration.json`의 `use_raw`·θ 판정은 옛 등폭 규칙으로 정해졌다(`r7c7_fixes.md` §4-3) — E1 전 재생성.
- N7. RD: 오프라인 `rd`는 절대 낙폭(A_std − A_var)에만 구간이 있고 상대 RD(1 − A_var/A_std)는 점추정만, `--compare` dRD도 절대 낙폭 차다. EVAL H1/H2의 ΔRD(상대 RD, 시스템 짝 재표집)는 없다(S1). 폐루프 RD는 성공률 기반(`closed.py:130`)인데 EVAL §4.2 주 지표는 Score 기반 — 1차판 규칙은 "P4 뒤 확정 [가정]"(`EVAL:179`)이므로 확정 때 적을 것. 폐루프 RD 부트스트랩은 표준 성공 0인 뽑기를 버린다(`closed.py:122`, 조건부 구간).
- N8. H: `M4Params.H = 3` 고정, `closed`에 H 인자 없음 — E-M4는 H = 1·3 모두(E §4.12, M4 §5 판정 7).
- N9. 라벨러: D-plan 정규화 0.30 m(`sim/labeler.py:27`)는 `labeler.md:6`에 적혀 있고 사전 등록 전 값, D-short 최소 시작 거리 5 mm(`:97`)는 코드에만. 결과 라벨은 거부권 용도(§65)라 영향 작음.
- N10. 자연/과표집 가중치(E §1.5 "둘 다 보고"): E0.5·E1은 연속 스냅샷 전부를 쓰므로 자연 분포 그대로이고 `--decision-only`일 때만 과표집 모집단이 된다(가중치 보고 없음).
- N11. 정본 §37 본문(`00-interfaces.md:345`) "ZED Mini(102°×57°…)"는 뒤 절 §47이 덮는 결정 기록 — DOC 아님.
- N12. 6·7회차 N 그대로: `handoff.md:46`·`:55` 날짜 붙은 옛 절, `stageA_pipeline.md:53` 등 당시 기록, `CLAUDE.md` Jev 서술, `stageb_data.py:15`(§71 파일 해시 보호), 논문 vLLM 서빙(§70), `r7_sweep6.md` §3 열린 항목(`fused_model.py:126` 잔차 체크포인트 거부, θ 게이트 런타임 없음, `core.py:355`, aiworker P1/P2, `jevcall.PROGRESS`) — 모두 여전히 열림, 완료 정의 1–5를 막지 않음.
- N13. 파드 공용 캐시: 내 Isaac 판이 `home/.nv/ComputeCache`(새 파일 23개)·`home/.nvidia-omniverse/logs`를 갱신했다 — 공용 캐시라 두었다(/data 안). `/dev/shm` 폴더 시각이 03:43 UTC로 바뀌었으나 새 파일 0(남은 것은 09-20 파일 3개뿐). 파드 `/data` 밖 새 파일 0(`find -xdev -newermt 03:29 UTC`: `/`·`/tmp`·`/root`·`/home1`·`/var/tmp`·`/isaac-sim`·`/opt`·`/usr/local`·`/etc` 각각 0).
- N14. 로컬 C: 위생: 시작(12:17 KST) 뒤 C:에서 바뀐 것은 `.claude`·`.claude.json`(하네스 — 큰 도구 출력 두 번이 하네스에 의해 `.claude\projects\…\tool-results\*.txt`로, 배경 작업 출력이 `AppData\Local\Temp\claude\…\tasks`로 저장됨), `AppData\Local\Temp\2026-09-25_mservice.txt`(12:34 KST, 다른 앱), `AppData\Local\Temp\8f92a052-ab64-4e27-8f22-0a0d0b93ec45.tmp`(12:41 KST, 출처 모름, 이 저장소 산출물 아님, 지우지 않음). `pytest-of-USER`·`torchinductor_USER`·`.python_history` 없음. 로컬 파이썬은 모두 `PYTHONDONTWRITEBYTECODE=1`, TMP·basetemp = `D:\tools\scratch_qdd\r7c8`.

---

## 5. 사전 등록 대조표 (과제 1)

`prereg.json` 해시 대조: `python tools/prereg_hash.py --check` → **OK**(§2.7·§2A.6·§3.7·§4.8·§5.6). 사전 등록 뒤 E-first 편집은 `6e2889f`(§1.5 표에 R2_TRAIN 줄, 정본 §66·§67)와 `ac7095a`(머리 안내·§1.4 카메라 정정 표시)뿐 — 판정 절 무변경.
"확인" 열의 파드 = 모의 모델 한 명령 산출(`meta`)·폐루프 판 행, 로컬 = `D:\tools\scratch_qdd\r7c8\*.py`.

| # | 사전 등록 값·절차 (출처) | 구현 (file:line) | 확인 | 판정 |
|---|---|---|---|---|
| 1 | 군집 부트스트랩 10,000회 (E :130, EVAL :184) | `analysis/stats.py:4` `N_BOOT`; CLI `e05.py:452`·`rd.py:155`·`calib.py:76`·`closed.py:294`; `canary.py:19` | 파드 e05·rd·calib·closed(모의·융합) `meta.bootstrap.n_boot` 10000(`--n-boot` 안 줌), `closed.json` `result.bootstrap` = `meta.bootstrap` | 일치 |
| 2 | 95% 백분위 구간 (EVAL :184) | `stats.py:14-15,28,46`; seed 0 | `meta.bootstrap` level 0.95·percentile·seed 0 | 일치(seed = 정본 §72) |
| 3 | 재표집 단위 = 에피소드 군집 (E :130) | e05 `(kind, seed)` `e05.py:526`; calib `calib.py:49`; rd `rd.py:130` | `meta.bootstrap.unit` 문구 | 일치 |
| 3b | 같은 단위 — 카나리 | `canary.py:23-28` 스냅샷×질문 키 | 세트 `dev_v1` = 3편·60키 | **불일치 → D3** |
| 4 | 짝 비교 = 같은 시드 짝 (E :130) | `stats.py:32-47` 공유 군집; `closed.py:90-100` | 코드 읽기·시험 | 일치 |
| 5 | Holm — 판정 10 (E :265, :131) | `stats.py:62-81`, `e05.py:199-210` | 손 계산 6예 = `holm_ci` = `stats.holm`(§6.1) | 일치 |
| 5b | Holm — 판정 2 "LA-2 또는 C2''" (E :131, :257) | `replay.py:32-33` 보정 없음 | `j2_holm.py` 반례 | **불일치 → D1** |
| 6 | 폐루프 RD 재표집 = layout 짝 (EVAL :184) | `closed.py:112-123` | 2시드×3epoch 격자 [0, 0.6667] = 손 계산 | 일치(epoch = §72) |
| 7 | E0.5 표 = t_s − d_p95 − {0, .33, .66} (E :236) | `e05.py:43-55` 최근 3 스냅샷 | 코드·시험 | 일치 |
| 8 | 같은 시각 K = 3 (E :238) | `e05.py:438` | 기본값 | 일치 |
| 9 | LA-2 γ 0.67 / C2'' 반감기 0.33 / C2' λ 3·τ 5 s·T_vlm 1·5 s / C2'-S λ 1 (E :240) | `replay.py:13,21`; `e05.py:35` | 상수 | 일치 |
| 10 | 판정 1–3 문턱 5%·+2%p (E :256-258) | `replay.py:33-40` | 코드 | 일치(판정 2 보정은 D1) |
| 11 | 판정 4 ×2·AUROC 0.7·0.03 (E :259) | `replay.py:46-48` | 코드 | 일치 |
| 11b | 판정 4 "섭동 직후 창" 길이 (열림) | `e05.py:159-161,451` 1 s | 정본 기록 없음 | **DOC D-2** |
| 12 | 판정 5 재시험 빼기 (E :260) | `e05.py:412-413` | 코드 | 일치 |
| 13 | 판정 6 < 1% (E :261) | `replay.py:50` | 코드 | 일치 |
| 14 | 판정 7 C2' − LA-2 ≥ +2%p·하한 > 0 (E :262) | `e05.py:415` | 코드 | 일치 |
| 15 | 판정 8 치환 − 바닥 짝 하한 > 0, 층별 (E :263) | `e05.py:386-387,418` | 코드 | 일치 |
| 16 | 판정 9 −2pt·A3 > 바닥·A4 ≥ 5% (E :264) | `replay.py:54-60` | 코드 | 일치 |
| 17 | 층 2지·Noul / 3–6 / 7–17 (E :245) | `options.py:48-51` | 코드 | 일치 |
| 18 | 판정 10 시간 블록 정의·반복 수 (열림 [가정]) | `e05.py:12-13,439-440` 한 실행 안 통과 2개 × 2회 | 정본 기록 없음 | **DOC D-2** |
| 19 | d_p95 = E0 값, 재실행 규칙 (E :236, :278) | `e05.py:441` 0.307 (= 정본 §55 `00-interfaces.md:487`), `:624` meta 주의 | 기록 있음 | 일치 |
| 20 | E1 ECE = 15개 동일 질량 (E :320) | `calibration.py:71-83`, 판정 `:180-181`, §3.6 `:89` | 손 계산 0.125·0.272941 일치, 판정은 등질량만 읽음(§6.1) | 일치 |
| 21 | 판정 1: ECE ≤ .05·상한 ≤ .08, AUROC ≥ .75·하한 ≥ .70, 오답 < 30 불가, θ − .03·하한 θ − .08·적용률 20%, θ 0.6/0.7/0.8 (E :320,:339) | `calibration.py:178-191`, `calib.py:65` | 코드·`test_calib_pure` | 일치 |
| 22 | 판정 8 J5: α {.05,.1,.2}, 커버리지 하한 ≥ 1−α−.03, 원소 하나 ≥ 50%, 정확도 ≥ 1−α, 적합 400 (E :330,:347) | `calibration.py:184,192-196`, `calib.py:64` | 코드 | 일치 |
| 23 | split conformal q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.py:59-64` | 코드 | 일치 |
| 24 | 원 확률: ECE ≤ .03 ∧ T ∈ [0.8, 1.25], log p 1e-6 (E :333-335) | `calibration.py:20,89-90` | `fit_raw_ece` = 등질량(§6.1) | 일치 |
| 25 | 온도 대 등위 회귀 비교 (E :334) | 없음 | 정본 §52 "질문별 온도" | 정본 기록(N5) |
| 26 | `ambiguous` 본 ECE 제외 (E :359) | `calib.py:34-51` 필터 없음 | POOL 6.7% 표시 | **불일치 → D2** |
| 27 | 적합/시험 에피소드 분할 (E :296 → 정본 §52 CAL 반분) | `calib.py:28-31,111-121` | 편 겹침 거부 | 일치(방법 세부 D-2) |
| 28 | E1 스냅샷 모집단 (E :296 결정 스냅샷 → §52) | `calib.py:39` 연속 전부 | 정본 기록 없음 | **DOC D-2** |
| 29 | T_c 0.33 / H 1·3 비교 (E :487, M4 :272-273) | `m4.py:38-39` H = 3, CLI 없음 | 코드 | T_c 일치, H는 N8 |
| 30 | γ 0.67, n_LA 2 (E :487, M4 :275-276) | `m4.py:41-42,215-218` | 퍼즈 | 일치 |
| 30b | 경계 직후 γ 1.0·W 2 (M4 :150,:214,:221,:281,:291; 정본 :608 인용) | 없음 | `grep` | **불일치 → D5** |
| 31 | W 1, W = 첫 도전 뒤 더 필요한 표 수, W = 0 즉시, W < 0 거부 (정본 §72) | `m4.py:40,56-58,177-186` | 옛/새 퍼즈·시험(§6.1) | 일치 |
| 32 | 비가역 W+1 (M4 :291, :306) | `m4.py:174,182` | 퍼즈 irr 켬 150/150 동일 | 일치 |
| 33 | τ 1(접촉 근처 0) (E :487, M4 :277) | `m4.py:43,137-146` 지원, `core.py:265`·`m4.py:215-217` near 없음 | `tau_near.py` | **불일치 → D4** |
| 34 | STALE 1.5 s, d̂ = 최근 50회 p95, N_max = ⌈d̂/T_c⌉ + 1 (E :487, :220, M4 :258,:263) | `m4.py:44,48,112-124` | 코드 | 일치 |
| 35 | FLIP_TH·θ 게이트 끔(E0.5·E1 전) (정본 §6, M4 :282,:287) | `m4.py:45`, J5만 `core.py`(보정 파일 있을 때) | 코드 | 일치 |
| 36 | 조기 호출: (b) ≠ OK / 큐 임계 g 0.5 / 장면 변화 P90 (M4 :259-261, :289) | (b)만 `m4.py:274-278`, `core.py:302,482` | `grep` | **불일치 → D5** |
| 37 | (b) conformal α 0.01·창 w 5 (E :487, M4 :285-286) | 정본 §61·§64 측정원(proprio T1 + V1h T2)으로 대체 | 7회차 §5.2 확인 | 정본 기록 |
| 38 | 시드: DEV 0–29, CAL 500–549, TEST 1000–1149, TEST-P5 1300–1329, POOL 2000–2119, R2_TRAIN 10000–59999 (E :115-120, 정본 §66) | `eval/splits.py:13-15`, `datagen/gen.py:34-35` | 파드 가드 실행(§6.4) | 일치(TEST2는 N4) |
| 39 | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `config.py:12`, `closed.py:274`, `aiworker.py:14-15` | 코드 | 일치 |
| 40 | P1 2 cm·near 5 cm, P2 0.5 s, h_lift 3 cm, tilt 30° (E :420-421, 정본 §7) | `perturb.py:26-28`, `config.py:8-11` | 코드 | 일치 |
| 41 | POOL 120 × 10, 경계 30% (E :121) | `sim/snapshot.py:31`, `pool.md:17,25` | 기록 | 일치(가중치 보고는 N10) |
| 42 | 라벨 규칙: 적격 ≥ 0.90, 판별력, 0.02, 단순 순서 (prereg_labeler :11-13) | `sim/labeler.py:95-96,131-142` | 7회차 재계산 = 정본 §65 | 일치 |
| 43 | D-short = 단계 + (1 − 남은/시작), 10 s 실패 0, D-time τ {.33,.66} (prereg_labeler :7-9) | `labeler.py:25,100-111,114-128` | 코드 | 일치(정규화 상수 N9) |
| 44 | 카나리 표류 = 하한 > 0 (Holm) (정본 :264, E :139) | `canary.py:29` + "> 2×바닥" | `canary_rule.py` | **불일치 → D3** |
| 45 | EVAL H1/H2 ΔRD·다중 비교 H1·H2만 확인적 (EVAL :186-190) | 없음(기준선 S1) | — | SCOPED S1 |
| 46 | 주 RD = Score 기반 (EVAL :182) | `closed.py:130` 성공률 기반 | 1차판 [가정] | N7 |
| 47 | M4b(D28) 자기 사전 등록 2,000회 (`e_m4b_meas.md:94`) | `m4b/metrics.py:87,97`, `m4b/analyze.py:161,243,360` | 정본 §72 예외 | 일치 |

## 6. 확인한 것 (근거)

### 6.1 7회차 수정의 독립 확인 (과제 2)
- **Holm**(`D:\tools\scratch_qdd\r7c8\hand_checks.py`): 정규 근사 구간 오라클로 p 값을 정확히 맞춘 6예 — {0.001, 0.02, 0.5} → {a, b}(Bonferroni는 a만), {0.01, 0.03, 0.04} → {a}, {0.02 ×3} → 없음, {0.012, 0.02, 0.04} → 전부, {0.2, 0.001} → {b}, {0.04} → {a}. `holm_ci` = 교과서 Holm 손 계산 = `stats.holm` 6/6. 부트스트랩판 `block_diff_holm`(블록 3개, 4,000회): 0-2(수준 0.9833)·1-2(0.975) 기각, 0-1 유지, `any` = `block_diff_lo` 0.12 > 0 — 정본 §72 "판정 10의 참·거짓은 Bonferroni 첫 단계와 같다"와 맞다.
- **등질량 ECE**: p = (.1,.2,.3,.4,.9,.95), 정답 (0,0,1,0,1,1), 3구간 → 손 계산 0.125 = 코드. n = 17·15구간(앞 2구간 2개, 나머지 1개) → 손 계산 0.272941 = 코드 = 독립 구현, 등폭은 0.135294. `judge_question`에 등폭 0.2·등질량 0.03(상한 0.07)을 주면 합격 — 등폭을 읽지 않는다. `fit_question.fit_raw_ece` = `ece_mass`. 파드 `calib` 모의 판 `calib.json`에 `ece_cal_mass_ci` 있고 `ece_cal_ci` 없음, `meta.ece` "judged ECE = 15 equal-mass bins".
- **폐루프 RD 재표집**: 시드 0(표준 3/3, 무작위 1/3)·시드 1(2/3, 2/3) × epoch 3 → 가능한 뽑기 값 {0, 0.4, 0.4, 0.6667}, `aggregate(n_boot=10000)` `rd_ci` = [0.0, 0.6667], `n_seeds` 2·`n_pairs` 6 — 시드 격자와 같다.
- **M4 W**(`m4_diff.py`·`m4_diff2.py`·`m4_diff3.py`): 무작위 표·(b) 결과·실행 400사건 × 150 시드 × W ∈ {1, 2, 3} × agree {consensus, newest} × feedback_b {켬, 끔} × 비가역 {켬, 끔} = 3,600판에서 aad30d6과 3ed2e49의 반환값 열·통계·슬롯 상태가 **전부 같다**(C0–C6 = `conditions.py` 덮어쓰기 {max_inflight, agree, feedback_b}뿐, W 없음 확인). W = 0: 옛 코드는 가역일 때 W = 1과 행동 150/150 같음(7회차 N2 사실), 새 코드는 150/150 다름(즉시 교체). W = −1: 새 코드 거부, 옛 코드 허용. `test_m4_window.py`를 3ed2e49 사본에서 돌리면 W0·음수 2개 실패·3개 통과, `test_m4.py` 15개 양쪽 통과; HEAD는 20/20.
- **융합 `meta.prompt_config`**: 파드 융합 판 `meta.prompt_config` = {sha `61ef1e6bc090`, layout D27v1, camera `D27v1:head camera:|right wrist camera (active arm):`, state IMG, source "checkpoint stageb.json (fused server check_prompt enforces runtime equality)"} = 체크포인트 `stageb.json`의 `prompt_config`와 같다. 모의 판은 모듈형 H·S1(`sha afc047c2ab9d`).

### 6.2 7회차 이후 바뀐 기록
| 위치 | 주장 | 확인 |
|---|---|---|
| `handoff.md:99` | 7회차 FAIL 수치, 수정 내용, 로컬 800/11·파드 842/3, 연속 0회 | 이번 판 로컬 800 passed·11 skipped, 파드 842 passed·3 skipped(2회) — 같다 |
| `handoff.md:3` | 마지막 갱신 03:11 UTC, 정본 §1~§72 | 커밋 03:16:44 UTC, 맞음. 같은 머리 `:5`는 D-1 |
| `draft-log.md:445`, `direction-log.md:55` | 7회차 판정·수정 요약 | 보고서·수정 문서와 같음 |
| `r7c7_fixes.md:21` | 파드 1회차 잔여 삭제 | `code_r7c1*`·`cache/pyc_r7c1*`·`ir/kitcache/cyclo-r7c1*`·`tmp/r7c7*` 없음(`ls`) |
| M4 §4.4·M5 L1·SUMMARY 2곳 | [정정 R7 7회차, 정본 §72: W=1] 표시 | 표시 있음; 정본 §5 원문은 규칙대로 둠 |

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV `validate_episode`만(스탬프 안 함): **36/36 구조 이상 없음**, 전부 DEV, 성공 mug_tray 12/12·mug_marker 12/12·bottle_tray 8/12. LeRobot 내보내기 시험(`venv_e3st` + `pylib_lerobot`) **6 passed**. |
| 2 모델 | 충족 | **단계 B S-E2E**(GPU 2): `stageb_train train --data se2e --run r7c8_se2e --out-root <scratch>/ckpt --max-train 40 --max-steps 6 --batch 2 --max-val 4 --eval-every 3 --reload-check --seed 31` → EXIT 0(03:33:16–03:33:57 UTC). `config` data se2e·hz 10·H 5·n_val 1799·`grip_space open01@v1`·`grip_src [RB1, RB2]`·`proprio_masked 40`; 검증 dec 3.526 → 2.954 → 1.825; `save_load` `max_abs_action_diff` **0.0**, `eval_equal`·`norm_equal` true. **단계 B R2**(GPU 2, `--data r2 --pool …/standard/mug_tray/P0,…/dr/mug_marker/P0 --dev-val-seeds 5 … --seed 37`) → EXIT 0(hz 30·H 15), 재적재 차 **0.0**. **서빙**: 이 R2 체크포인트로 정의 3 (b). CUDA 시험(GPU 2, `tests/train` + `test_fused_action.py`) **102 passed**. 단계 A 코드는 3ed2e49..aad30d6에서 바뀌지 않아 학습 스모크는 다시 돌리지 않았다(파드 CPU·CUDA 시험에 포함). |
| 3 폐루프 | 충족 | (a) `closed --model mock --split dev --seeds 4 --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c8`(03:36:14–03:38:38) → `CLOSED_DONE`, 성공, 호출 48·오류 0, RTF 0.890, M4 epoch 5, Astra 2. 부가 JSONL: `call` 48/48 64자리 hex `request_sha256`(48개 모두 다름), `image_sha256` {cam_head, cam_wrist_right} 48/48 hex, `canary_id` `cn20260924_mock_ae0d1a` 48/48; `astra` 2/2 hex 요청 해시 + `image_sha256` {cam_head} + `canary_id` "none". `meta.bootstrap` n_boot 10000, `meta.git` aad30d6, split dev, seeds [4]. (b) **융합 실체크포인트** `closed --backend fused --model <scratch>/ckpt/r7c8_r2/last --split dev --seeds 7 --max-seconds 20 --astra mock --isaac-gpu 1 --gpu 2 --inst-prefix r7c8f`(03:38:41–03:41:27) → `CLOSED_DONE`, 끝까지 돎(6스텝 모델이라 성공 요구 아님), `call` 75/75·`chunk` 56/56 hex 요청 해시(모두 다름)·이미지 해시·`canary_id` "none"(이유 명시), `astra` 5, `measure` 48행, 오류 0, M4 epoch 92. `meta.prompt_config`는 §6.1. 지연 N1. |
| 4 평가 | 충족(판정 절차 D1·D2) | 모의 모델 한 명령(`venv_vllm`, GPU 없음, `--n-boot` 안 줌): `e05 --split dev --episodes 2` → `E05_DONE`(a_as_stabilizer), `rd --variants standard=jsel_dev,random=gen_dev/random --split dev --episodes 1` → `RD_DONE`, `calib --fit-data pool --fit-split pool --heldout jsel_dev/P0 --heldout-split dev --episodes 4` → `CALIB_DONE`. 모두 EXIT 0, `meta.bootstrap.n_boot` 10000, 단위 문구 정본 §72와 같음, e05 `judgments`에 `j10_block_pairs_holm`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·카나리·시드·모델 지문·부트스트랩, 체크포인트 `prompt_config.files_sha` 대조(융합 서버 거부 없음). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`; 거부 뒤 출력 폴더 생기지 않음)
- 평가: `e05 --split cal`·`--split test_p5`, `rd --split test`, `calib --fit-split cal`·`--heldout-split test`, `closed --split test --seeds 1000`·`--split cal --seeds 549` → "--split X refused: set HARVEST_ALLOW_SPLIT=X (main session only …)". `closed --split dev --seeds 30|499|1149|1329|2119|3100|59999` → "not in split dev range(0, 30) (refused, never opened)". `HARVEST_ALLOW_SPLIT=dev closed --split test --seeds 1000` 거부. `--isaac-gpu 2` → "0 or 1 only (GPU 2 never renders)". 모두 rc 1.
- 생성: `gen gen --seeds 10005-10006`(확인 인자 없음) → "R2 generates DEV 0-29 only (R2_TRAIN 10000-59999 needs --confirm-train)", `--variant random` → "TEST pool … use 'dr'". `check_r2_seed`: (0,F)(29,T)(10000,T)(59999,T) 허용, (30,F)(10000,F)(60000,T)(549,T)(3000,T)(2000,T)(1329,T) 거부. `aiworker.check_layout_seed`: 0·29 허용, 30·499·500·549·999·1000·1149·1150·1299·1300·1329·2000·2119·3000·3199·10000·59999 거부. `splits.RANGES`·`PROTECTED` = §5 행 38.

### 6.5 A. 테스트
- 로컬(Git Bash, `python -m pytest -q -rs -p no:cacheprovider --basetemp=D:/tools/scratch_qdd/r7c8/pt{1,2}`, TMP = `D:\tools\scratch_qdd\r7c8\tmp`): 2회(03:18:18–03:19:34 / 03:47:45–03:49:01) 모두 EXIT 0, 진행 표시 **800 통과 · 건너뜀 11**(torch 없음 7, inspect_robots 2, pyarrow 1, TODO(P3) 1), F·E 0. 실행 뒤 `git status`에는 이 보고서 파일만.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh` 4경로, `CUDA_VISIBLE_DEVICES=""`): **842 passed, 3 skipped** 두 번(EXIT 0, 83 s / 70 s). 건너뜀 pyarrow 1·CUDA 없음 1·TODO(P3) 1, 경고 1(`test_stagea_loss_torch.py:42` requires_grad 스칼라 변환, 무해). 파드 CUDA(GPU 2) 102 passed, LeRobot 6 passed.

### 6.6 같은 사실 grep (과제 3, `D:\tools\scratch_qdd\r7c8\sweep.py` — 추적 파일, `paper/`·`third_party/`·R7 보고서 제외, 표시 유무 분리)
- `n_boot 2000|2,000회`: 표시 없는 것은 정본 §72 예외 줄(m4b, 맞음), `e_m4b_meas.md:94,156`(D28 자기 사전 등록), `m4b/*`(같음), `tests/test_stats.py:5`·`tests/eval/test_r7c7_prereg.py:135`(시험 인자), 옛 계획 코드 조각 — 현재 평가 기본값을 2,000으로 적은 곳 0.
- `Bonferroni|stand-in for Holm`: 정본 §72·`r7c7_fixes.md`·시험 이름 — 모두 대조 설명. 현재 규칙으로 적은 곳 0.
- `등폭 판정|ece_cal_ci`: `r7c7_fixes.md`(변경 기록)·`calib.py:9`(보고만) — 0.
- `W=2 흡수 / 연속 2표`: 정본 §5 `:35`(원문, §72가 덮음), M4 `:281`·M5 `:86`·SUMMARY `:325,534` 모두 [정정 R7 7회차] 표시, `D1-verification.md:77`(당시 검증 표). 표시 없는 현재 오류 0. `경계 직후`는 D5.
- `vLLM` + 융합/단계 B: 모두 모듈형 = vLLM, 융합 = HF 서버로 구분(`closed.py:18`, `fused_model.py:15`, `canary.py:9,257`, `pre_r7_fixes.md:24`, `r6_eval.md:14`, `r7_fixes.md:40`).
- `one call|한 번 호출`: 정본 §58 [사용자] 절(`:511`, §67 C4), in-flight·DecCall 뜻(`jevl.py:8`, `conditions.py:5,11`, `models.py:1`, `jevl_mmbench.py:3`), 정본 `:412`(하트비트 in-flight 1개) — 0.
- `[제안]|[proposal]`: E-first·EVAL·정본의 표기 규칙·당시 제안, `e3st.md:104,149` — R2_TRAIN을 제안으로 적은 곳 0.
- `500–699`: `tests/datagen/test_gen_guards.py:20`(거부 범위 주석) — 맞음.
- `GPU 2` + 금지: 렌더 금지 뜻(`closed.py:11,153,353`, 계획 `:40`)·당시 기록(`pool.md:4`) — 현재 시제 "GPU 2 금지" 0.
- `102°`: 정본 `:345`(§37 결정 기록, N11), `e3st.md:54`([대체됨] 표시)·`:138`(머리 정정이 덮음), `cli_e3st.py:19`·`test_stereo_metrics.py:36`(옛 값 재현) — 0.
- 정본 범위 `§1~§N`: **`handoff.md:5`·`:83` (D-1)**, `:3` §72(맞음), `:27`(날짜 붙은 옛 절, N12), 단계 2 문서의 당시 범위.
- `\bJev\b`·`20 Hz`·`진행 중|미구현`: 이번 변경 파일(정본 §72, handoff, direction-log, `r6_eval.md`, eval·runtime 코드, M4 문서)에서 새 현재 시제 오류 0; 나머지는 6·7회차 판단과 같음(N12).
- 카메라(§47): 이번 변경 파일에 카메라 서술 없음; 모의·융합 판 이미지 키 {cam_head, cam_wrist_right}, 융합 prompt_config D27v1 머리 + 오른손목 = §57.

### 6.7 F. 규칙
- `main` = `origin/main` = `520b2be`, `dev` = `aad30d6` = `origin/dev`.
- 파드: §4 N13, 머리 줄 정리 목록. 내 프로세스 0(정리 뒤 `ps`), 라벨러(GPU 0)·공용 `canary`·`r2/dev`·`data/*`는 읽기만.
- 로컬 C:: N14.

## 7. 다음 순회 전에 할 일 (제안)
1. **D1**: 판정 2를 LA-2·C2'' 두 비교의 Holm으로(`stats.holm_ci`, "하나라도 기각"이면 첫 단계 수준 1 − 0.05/2), `judgments`에 쌍별 결과. 판정 1·3의 점추정 문턱은 그대로.
2. **D2**: `calib`에서 `ambiguous` 항목을 본 ECE·판정 입력에서 빼고 따로 보고(또는 labels_v2 기준 애매함 정의를 정본에 적고 그 정의로). 둘 중 무엇이든 정본에 한 줄.
3. **D3**: 카나리 표류 = 정본 §28 규칙(하한 > 0, Holm)만, 재표집 단위 = 스냅샷의 에피소드(또는 세트를 편마다 1 스냅샷으로 다시 만들고 그 사실을 기록). "> 2×바닥"을 남기려면 정본 결정으로.
4. **D4**: `core.py`가 슬롯의 near/contact 여부(정본 §7 "목표까지 ≤ 5 cm / 접촉 술어 참")를 `on_vote`와 `try_commit_prefix`에 넘기게(또는 정본에 "τ 평탄"을 결정으로).
5. **D5**: 경계 직후 W 2·γ 1.0, 큐 임계 g 0.5·장면 변화 조기 호출 — 구현하거나 정본에 "E-M4 C5 = E §4.12 평탄 설정, 이 항목들은 쓰지 않음/절제"를 적고 `m4.py` "Not implemented" 목록에 더함.
6. **D-1**: `handoff.md:5`·`:83`의 정본 범위를 §72(또는 범위를 쓰지 않는 문구)로.
7. **D-2**: 정본 §72에 섭동 창 1 s, 시간 블록 정의·반복 수, E1 스냅샷 모집단·반분 방법·AUROC 부트스트랩 관례를 "사전 등록이 정하지 않은 값"으로 추가.
8. 모두 코드·정본 변경이므로 연속 무결은 0부터. 다음 순회도 §5 대조표를 처음부터 다시 채우기를 권한다(이번 판의 D1·D4는 한 파일만 보면 맞아 보이고 호출 경로·다른 절의 문장을 함께 봐야 드러났다).
