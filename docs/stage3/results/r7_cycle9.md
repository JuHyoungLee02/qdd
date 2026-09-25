# R7 객관 검증 순회 — 9회차 (cycle 9, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님, 8회차 결론·`r7c8_fixes.md` 대조표에 기대지 않고 사전 등록 원문에서 대조표를 새로 만들고 다시 돌림). 작성 2026-09-25 05:20 UTC(`date -u`; 시작 04:38:20 UTC, 파드 첫 명령 `Fri Sep 25 04:51:05 UTC 2026`, 파드 정리 끝 05:12:40 UTC).
- 대상: `D:\qdd` `dev` HEAD `a9b56e3` = `origin/dev`(`git ls-remote`), 태그 `stage3-r7fix8`, `main` = `origin/main` = `520b2be`. 작업 트리 깨끗(시작·끝 `git status` 출력 없음, 이 보고서만 새로). `aad30d6..a9b56e3` = 코드 10개(`analysis/replay.py`·`canary.py`·`eval/{calib,canary,closed,common,e05}.py`·`runtime/{calibration,core,m4}.py`) + 시험 3개(새 `tests/eval/test_r7c8_prereg.py`·`tests/runtime/test_m4_near.py`, `tests/test_replay.py`) + 문서(정본 §73, handoff·draft-log·direction-log, `r5_closed_loop.md:36`·`r6_eval.md:13`, 옛 계획서 2곳, `r7_cycle8.md`·`r7c8_fixes.md`). 파드 사본 = `git -c core.autocrlf=false archive HEAD`(+ JSON `CODE_VERSION`, tar sha256 `7eeee3fa…`), 모든 산출 `meta.git.commit` = `a9b56e3…`, `meta.code_sha` = `1777374fb2d896f7`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle2.md`–`r7_cycle8.md`, `r7_fixes.md`, `r7_sweep6.md`, `r7c7_fixes.md`, `r7c8_fixes.md`, 정본 `00-interfaces.md` §1–§73(뒤 절 우선; §67–§73 SCOPED는 근거만 확인, [사용자] 제목 절 본문은 §67 규칙, 논문 .tex vLLM 서빙 서술은 §70에 따라 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`M4-overlap-commit.md`(변수·기본값·조건 표).
- 분류 기준(8회차와 같음): **DEFECT** = 코드가 정본·사전 등록 규칙과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 지금도 참고되는 문서·주석의 현재 시제 서술이 HEAD와 다르고 정정·해결 표시가 없는 것, 그리고 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 정본에 적히지 않은 것.
- 규칙 준수: 코드·문서 수정·커밋·푸시 없음(이 보고서만 씀). git은 `-c safe.directory=D:/qdd`(전역 설정 안 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c9`(스크립트는 모두 Write 도구로 D:에 쓰고 경로로 실행; 로컬 파이썬은 `PYTHONDONTWRITEBYTECODE=1`, TMP·basetemp도 여기). 파드 파일은 `/data/harvest/tmp/r7c9`(코드 사본·체크포인트·산출·pytest, 1.2 GB)와 작업자가 만든 `ir/kitcache/cyclo-r7c9{,f}_standard`(각 208 MB)·`cache/pyc_r6/data/harvest/tmp/{r7c9,tmp91x5srxl,tmpv1kx3jhn}`·`tmp/{carb.NHMu8o,carb.tlTqJK,tmp91x5srxl,tmpv1kx3jhn}`뿐이고 **끝에 모두 지웠다**(05:12 UTC; 시작 전 목록 `pod_before.txt`와 대조해 새 이름만, 시각이 내 판 시작 04:57:56·05:05:11 UTC와 일치, 연 프로세스 없음 확인). GPU: 단계 B 학습·CUDA 시험 = GPU 2(렌더 없음), Isaac = GPU 1, GPU 0(라벨러 896 MiB)·GPU 3 건드리지 않음, 끝에 0–3 = 896/5/1/1 MiB(시작과 같음). 시드 DEV만(`HARVEST_ALLOW_SPLIT`은 가드 음성 시험 1건에서 `=dev`만). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. 남의 프로세스(라벨러 Isaac 2개) 건드리지 않음. **내 실수 2건은 §4 N11**(Git Bash 명령 한 줄에 `python -` 조각이 섞여 들어감 — 즉시 중지, 만든 파일 없음; MSYS 경로 변환으로 파드 루트에 빈 폴더 `/C:/Program Files/Git/data/harvest/tmp/r7c9`가 생김 — 1분 안에 지움).

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 2 |
| DOC | 1 |
| SCOPED | 10 |
| NOTE | 12 |

8회차 수정 다섯 가지(판정 2 Holm, E1 `ambiguous` 제외, 카나리 표류 규칙, C5 접촉 근처 τ, `meta.prereg`·`--m4-h`)는 독립 손 계산·무작위 대조로 **모두 맞다**(§6.1: 손 계산 29/29, 가짜 세계 폐루프 150판 × 7조건에서 C0·C1·C2·C4 = aad30d6 비트 동일, near를 끄면 7조건 모두 비트 동일). 완료 정의 1–5도 모두 다시 돈다(§6.3). 그러나 사전 등록 대조표를 원문(E-first §4.12, M4 §3·§4.4·§5, 정본 §20)에서 새로 채우자 8회차 대조표가 "일치"로 둔 행 하나와 표에 없던 행 하나에서 **런타임 M4가 사전 등록 조건 정의와 다르게 동작**하고 기록이 없었다: γ = 0.67이 "3표 중 2"를 확정하지 못함(D1), 기준 조건 C2(VLM Stream)가 원문 충실판 정의(5 s 타임아웃·상한 없음·매 틱 가장 새 응답)가 아님(D2). 문서는 카나리 도구 한계 목록의 해결된 "Holm 없음" 1건(D-1). 연속 무결은 **0회 그대로**.

---

## 1. DEFECT

### D1. 런타임 M4의 γ = 0.67이 "3표 중 2"를 확정하지 못한다 (E0.5 재생 규칙과도 다르다)
- 사전 등록·설계: `E-first-experiments.md:487`(§4.12 C5 설정 "γ=0.67"), `:240`(§2A.3 비교 규칙 "LA-2·γ=0.67(C3의 합의 부분…)"), `M4-overlap-commit.md:276`(§4.4 γ 행 "**0.67 (3표 중 2)**"), `:147`(§3 #2 "한 스텝에 표가 3개 이상 모이면 최빈 비율 ≥ γ로 확정(**3표면 2표 = 0.67**)"), 의사코드 `:221` `len(live)/len(s.votes) >= gamma`.
- 코드: `harvest/runtime/m4.py:46` `gamma: float = 0.67`, `:224` `len(live) / len(s.votes) >= self.p.gamma` — 2/3 = 0.6667 < 0.67이라 표 3개 중 2개 일치는 γ 규칙으로 확정되지 않는다(3개면 사실상 만장일치 = 절제 범위의 γ 1.0). 같은 저장소의 E0.5 재생은 같은 사전 등록 값을 "3표 중 2"로 구현한다: `harvest/eval/e05.py:61` `n / len(votes) >= 2 / 3 - 1e-3`, `harvest/analysis/replay.py:13-14` `la2(votes, gamma=2 / 3)` "canon γ=0.67 means 2 of 3". 즉 E0.5가 미리 재는 "C3의 합의 부분"과 E-M4 C3·C5·C6 런타임의 합의 규칙이 다르다. 런타임 시험 `tests/runtime/test_m4.py:79-84`는 3/4(0.75)만 확인한다. 정본(§1–§73)·`r5_closed_loop.md`·`r6_eval.md`에 이 차이를 정한 기록 없음(`grep "3표 중 2|2 of 3|2/3"` 정본 0건).
- 확인(`D:\tools\scratch_qdd\r7c9\gamma_check.py`, 원장 직접): 표 `a, b, a`(현 선택 a, 2/3 일치, LA-2 불성립) → 런타임 C5 원장 `('a', 'CONTESTED', 3)` 확정 없음, 재생 `la2` → a 확정. `n_la 9`(γ만)로도 `CONTESTED`, `gamma=2/3`을 주면 `COMMITTED`. `a, b, a, c` → `CONTESTED`(2/4). 8회차 대조표 행 30(`r7c8_fixes.md` §4 "γ 0.67, n_LA 2 … 일치")은 상수값만 보고 비교 연산의 경계를 보지 않았다.

### D2. 기준 조건 C2(VLM Stream)가 사전 등록 정의(원문 충실판)와 다르게 동작한다
- 사전 등록·정본: `E-first-experiments.md:495`(§4.12 D9 "**C2** = Slow Brain VLM Stream(T_c 고정 주기, **in-flight 상한 없음·실측 보고**, 요청 시각 기준 가장 새 유효 응답 하나 적용, 무효 무시, **5 s 타임아웃이면 기본 행동**)"), 정본 §20 `00-interfaces.md:179` 같은 문장, 정의 정본 `M4-overlap-commit.md:332`(§5 C2 "동시 요청 상한 없음(원문에 상한 없음, 실측 in-flight 수 보고), **매 틱** 요청(관측) 시각 기준 가장 새 유효 응답 하나의 보기를 그대로 적용, … 마지막 유효 응답이 5 s보다 오래되면 기본 행동(타임아웃)"). C2는 M4 판정 1·E-M4-gen(C5 − C2)·E-M4-lat 곡선의 비교 기준이다(`M4-overlap-commit.md:388`, E §4.12).
- 코드: `harvest/runtime/conditions.py:20`(C2 = `agree newest`·`feedback_b False`, 머리 `:7` "overlap + VLM Stream")는 M4 원장의 공통 규칙을 그대로 받는다 — (i) `m4.py:160-162` **STALE_MAX 1.5 s 폐기**가 C2에도 적용(사전 등록은 5 s 타임아웃), (ii) `m4.py:164-166` 이미 시작한(FROZEN) 스텝의 표는 `log_only` — 늦게 온 가장 새 응답을 적용하지 않음(원문은 매 틱 가장 새 유효 응답 적용), (iii) `core.py:409-410` 모든 조건의 in-flight를 `n_max()` = ⌈d̂/T_c⌉ + 1로 제한(`m4.py:127-129`; 원문·사전 등록은 상한 없음), (iv) 5 s 타임아웃 기본 행동 없음. 정본 §67–§73·`r6_eval.md:46`("C2 = 겹침 + newest")에 이 근사를 정한 기록 없음.
- 확인(가짜 세계 폐루프, `c2_stale.py`·`c2_check.py`): 고정 지연 **2.0 s**(E-M4-lat 격자 점)에서 C2 표 1,230개 중 **1,230개 `dropped_stale`**, 확정·적용 0, 판 끝 `approach`(원문 C2라면 5 s 안의 응답을 적용). 1.2 s에서는 C2 표 1,305 중 `log_only` 30. 지연이 0.25–0.35 s에 3% 확률로 1.4 s가 섞이면 C2 표 1,125 중 40개가 `log_only`로 버려진다. (M4 설계 C5가 STALE 1.5 s를 쓰는 것은 사전 등록 C5 설정대로이며 결함이 아니다 — 그 때문에 생기는 E-M4-lat 문제는 N4.)
- 판단: E-M4 기준선의 공정성 문제(기준선이 우리 설계의 시효·고정 구간 규칙을 물려받아 지연이 클수록 불리해짐)이고, 사전 등록 조건 정의와 다르며 기록이 없다. 고칠 길: C2 전용 경로(시효 5 s, 매 틱 가장 새 유효 응답, 상한 없음 + 실측 in-flight 기록)를 넣거나, 정본에 "런타임 C2 = 근사(무엇이 다른지)"를 결정으로 적고 E-M4 판정 해석에 반영.

## 2. DOC

### D-1. `docs/stage3/results/r7_fixes.md:45` 카나리 도구 한계 "한 모델·하루 한 검정이라 **Holm 없음**"
- `r7_fixes.md`는 카나리 도구(`harvest/eval/canary.py`)의 사용법·한계를 적은 유일한 결과 문서다(`:38-45`). a9b56e3이 표류 판정을 질문별 구간 + 질문 Holm으로 바꿔(`harvest/canary.py:31-54`, 정본 §73 D3) 이 한계 줄은 더 이상 사실이 아닌데 정정·해결 표시가 없다. 8회차 수정의 문구 grep은 영문 `no Holm`만 찾아 `eval/canary.py` 머리 설명만 고쳤다(`r7c8_fixes.md` §4). 같은 종류의 선례: 5회차 P2(해결된 '어댑터 없음' 한계 서술), 정본 §71(열린 문제 목록 전수 대조), §73 grep 목록 "카나리 규칙 문구".

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(정본 §71 보충) — 로컬·파드 모두 `tests/runtime/test_latency_ctrl.py:11` 1개 건너뜀. EVAL H1/H2 기준선 비교는 본 실험 단계.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66 "S-E2E 이후") — `gen gen --seeds 10005-10006` 확인 인자 없이 거부(§6.4).
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8 — `runtime/core.py` patch/replace = epoch만(무변경).
- S6. Astra 카나리 id "none" — 이번 모의·융합 판 `astra` 행 2/2·3/3에 `canary_id: "none"`.
- S7. S-E2E 체크포인트 런타임 tau 마스크 차이(`r7_fixes.md` §7).
- S8. CONTRADICT-soft(§68 K6·§69) — `measure.py` 무변경(`aad30d6..a9b56e3` diff에 없음).
- S9. §73 D5 M4 설계 확장(경계 직후 W 2·γ 1.0, 큐 임계 g 0.5, 장면 변화 조기 호출, 미확정 실행 (b) 엄격화) — 근거 확인: E §4.12(:487) C5 설정은 평탄한 "γ=0.67, W=1"이고 M4 §5 판정 6(:364)이 변수 절제를 C5 안에서 하나씩 하도록 둔다 → 사전 등록된 조건은 평탄 설정. `m4.py:24-29` "Not implemented"에 적힘.
- S10. §73 N5 E1 범위(`calib` = 판정 1·8, 판정 2–6·§3.5 일부·§3.3 2일 반복 없음, 등위 회귀 비교 안 함) — 완료 정의 4는 "보정(CAL 온도·J5)"라 막지 않음.

## 4. NOTE
- N1. **Holm은 양측이다**: `stats.holm_ci`(정본 §72가 "양측 구간"으로 기록)는 반대 방향으로 유의한 가설도 기각으로 세어 다음 단계의 수준을 푼다. 판정 2에서 C2'' 이득이 유의하게 음이면 LA-2가 95% 수준으로 검정되고(`hand_checks.py` A3 → `keep_a`), 카나리에서 불일치 0인 질문(바닥보다 유의하게 낮음 — 3편 세트면 구간이 한 점)이 4개면 남은 질문이 95%로 검정된다(C4: 4개 기각 후 dir_xy 수준 0.95 → 표류). 양측 Holm은 양측 영가설 가족의 FWER를 지키므로 규칙 위반은 아니나, 사전 등록 문장("유의하게 크면")을 한쪽 검정으로 읽으면 더 보수적이다 — 본 실험 전에 한쪽/양측을 정본에 한 줄 적기를 권한다.
- N2. 카나리 세트 `dev_v1` = **3편**(P0_ep0·ep1·ep2, 12 스냅샷). 편 군집 부트스트랩이 3군집이라 한 점 구간이 흔하다(파드 확인: mock 기준 대 zero-shot 답에 `canary_compare` → `mag_coarse` 불일치 0.333, 99% 하한 0.25로 기각, `n_clusters` 3). S-E2E 시작일 카나리를 새로 만들 때 편 수를 늘린 세트를 권한다. 이번 판 `meta.canary` = `cn20260924_mock_ae0d1a`(`stale: true`, §68대로).
- N3. D4(접촉 근처 τ = 0)의 범위: 무작위 가짜 세계 150판에서 near 틱 비율 평균 C3·C5 0.566, C6 0.558, C1·C2·C4 0.62–0.64. C3·C5는 150/150, C6은 113/150 판이 aad30d6과 원장 통계·슬롯이 달라졌지만 **행동 바이트는 7조건 모두 150/150 같다**(가짜 세계에서는 확정 상태만 바뀜). §73 보충과 맞다.
- N4. **E-M4-lat와 C5 STALE_MAX의 충돌(사전 등록 안의 긴장)**: C5 설정 STALE_MAX 1.5 s(E §4.12)로는 지연 2 s·5 s 격자 점(E §4.12 E-M4-lat, 판정 "C5 − C2' 2 s·5 s 하한 > 0")에서 모든 표가 폐기된다(`c2_stale.py`: 2.0 s C5 표 1,230/1,230 `dropped_stale`). E-M4-lat 설계 전에 지연 스윕에서의 STALE_MAX 처리를 정본에 정해야 한다(코드는 사전 등록 C5 설정대로라 결함 아님).
- N5. `docs/handoff.md:3` "마지막 갱신: 2026-09-25 04:18 UTC" — 같은 문서 `:100`에 04:27 UTC 수정·파드 시험(04:21–04:24) 결과가 있고 커밋은 04:37:35 UTC. 머리가 가리키는 §2.8 마지막 줄·정본 범위(§1~§73)는 맞다 — 6회차 N12·7회차 N1과 같은 판단으로 NOTE.
- N6. 논문 `paper/sec/3_method.tex:103`("경계 직후 $W=2,\gamma=1.0$, 경계에서 멀면 $W=1,\gamma=0.67$")·`SUMMARY.md:589`(설정 표 "1(경계 직후 2)")는 §73 D5 SCOPED인 경계 적응형을 방법으로 서술한다. 설계 서술(§73이 표시하지 않기로 함)이고 SUMMARY v3.10은 handoff가 옛 판본으로 지정 — E-M4 결과를 쓰기 전 논문 문장을 실제 조건(평탄 C5)에 맞출 것(§70의 논문 보류와 같은 처리).
- N7. 옛 계획서 `docs/superpowers/plans/2026-09-24-stage3-experiments.md:1453`·`:1457`·`:1461`(시험 초안의 `gain_la2_lo`·`gain_c2pp_lo` 입력) — 같은 과제의 `judge_e05` 초안(:1493)에는 정정 주석(:1492)이 있고 시험 초안에는 없다. 계획 초안 코드라 NOTE.
- N8. E §3.6(:333) "응답 확률이 소수 2자리로 반올림돼 오면 0.0 → 1e-3" [가정]은 로컬 모델 logprob(반올림 없음)에는 해당 없음 — `P_MIN = 1e-6`(`calibration.py:20`)만. API 모델을 쓸 때 다시 볼 것.
- N9. E0.5 요청 분당 400 이하 [가정](E §2A.8 :277)은 로컬 서버라 해당 없음(8회차 표 53과 같음).
- N10. 파드 공용 캐시: 이전 순회 잔여로 보이는 `cache/pyc_r6/data/harvest/tmp/r7c3`와 `tmp*` 폴더 약 28개(내 판 이전부터 있음, `pod_before.txt`)가 남아 있다 — 지우지 않았다(내 것 아님). 내 Isaac 판이 공용 `home/.nv/ComputeCache`·Isaac 하트비트 로그를 갱신했을 수 있다(/data 안, 공용이라 둠). 파드 `/data` 밖: `find / -xdev -newermt 04:38 UTC`(`/proc`·`/sys`·`/data` 제외) 결과 `/` 폴더 시각 하나뿐 — N11 (b)의 폴더를 만들고 지운 흔적.
- N11. **내 실수 2건**: (a) 로컬 Git Bash 명령 한 줄(pytest 출력 개수 세기)에 `python - 2>/dev/null </dev/null` 조각이 섞여 들어갔다(지시 위반 — 표준 입력은 `/dev/null`이었으나 명령이 멈춰 하네스가 배경으로 옮김). 즉시 `TaskStop`, 떠 있는 python 프로세스 0(`Get-Process`), 만든 파일 없음(하네스 배경 출력만 C:의 하네스 작업 폴더에). (b) 파드 `kubectl exec … mkdir -p /data/harvest/tmp/r7c9`를 `MSYS_NO_PATHCONV` 없이 Git Bash에서 보내 경로가 `C:/Program Files/Git/data/harvest/tmp/r7c9`로 바뀌어 파드 루트(`/`)에 빈 폴더 7단이 생겼다(04:51 UTC). `find`로 빈 폴더만임을 확인하고 04:52 UTC에 `rmdir`로 지웠다(`ls -la / | grep -c "C:"` = 0). 이후 모든 kubectl 호출은 `MSYS_NO_PATHCONV=1`.
- N12. 6–8회차 N 그대로: `handoff.md:27`·`:46`·`:55` 날짜 붙은 옛 절, `stageA_pipeline.md:53` 등 당시 기록, `CLAUDE.md` Jev 서술, `stageb_data.py:15`(§71 파일 해시 보호), 논문 vLLM 서빙(§70), `r7_sweep6.md` §3 열린 항목, 정본 §37 본문 102°(§47이 덮음), TEST2 1150–1299가 `splits.RANGES`에 없음, 기존 `calibration.json` 재생성(E1 전), RD 1차판 Score 기반 [가정](EVAL :179), 라벨러 정규화 상수, 자연/과표집 가중치 보고, S-E2E 사전 등록 항목(층화 검증·중간 체크포인트) — 모두 여전히 열림, 완료 정의 1–5를 막지 않음.

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦)

`prereg.json` 해시: 로컬 `python tools/prereg_hash.py --check` → **OK**(§2.7·§2A.6·§3.7·§4.8·§5.6), 파드 모든 산출 `meta.prereg.check` = "OK". 사전 등록 문서(`E-first`·`EVAL`·`M4`·`prereg_labeler`·`prereg.json`)는 `aad30d6..a9b56e3`에서 바뀌지 않았다. 코드 줄은 HEAD `a9b56e3`(`lines.py`로 찾음). "확인" 열: 로컬 = `D:\tools\scratch_qdd\r7c9\*.py`, 파드 = 이번 판 산출(§6.3).

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인 | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 / R2_TRAIN 10000–59999 (E :115-120, 정본 §66) | `eval/splits.py:13-15`, `datagen/gen.py:35,45-49` | 파드 가드 11건 모두 rc 1(§6.4) | 일치(TEST2 N12) |
| 2 | POOL 120 × 결정 10 = 1,200, 경계 30% 과표집 (E :121) | `sim/snapshot.py:30-31,119` | 코드 | 일치(가중치 N12) |
| 3 | `ambiguous` = 문턱 근처(히스테리시스 띠) 술어 (E :121) | `sim/snapshot.py:89`(near 5–6 cm), `cli_pool.py:470` | 파드 jsel_dev/P0 앞 4편 107줄 중 11줄 | 일치 |
| 4 | 분할·재표집 = 에피소드 (E :122, :130) | `calib.py:28-31`, `e05.py:541`, `rd`, `canary.py:25` | 파드 `meta.bootstrap.unit` 문구 4종 | 일치 |
| 5 | 성공 1 s·60 s·낙하 즉시 실패 (E :107) | `config.py:12-13` | 코드 | 일치 |
| 6 | 모든 호출 요청 원문 해시·이미지 해시·카나리 id (E :125-127, 정본 §28) | `core.py:267-268,370-371,595-596` | 파드 모의 `call` 39/39·융합 `call` 90/90·`chunk` 90/90 64자리 hex(모두 다름), 이미지 {cam_head, cam_wrist_right}, `astra` 2·3행 | 일치 |
| 7 | 95% 구간 = 군집 부트스트랩 10,000회 (E :130, EVAL :184) | `stats.py:4,7,14`, CLI `--n-boot` 기본 `N_BOOT` | 파드 e05·rd·calib·closed(모의·융합) `meta.bootstrap` n_boot 10000·level 0.95·percentile·seed 0 | 일치 |
| 8 | 짝 비교 = 같은 시드 짝 (E :130) | `stats.py:32-47`, `closed.py:112-133` | 코드(8회차 격자 확인, 무변경) | 일치 |
| 9 | Holm — 판정 2 "LA-2 또는 C2''" (E :131, :257) | `e05.py:199-206,403-404,432`, `replay.py:30-40` | `hand_checks.py` A1–A4(교과서 Holm = 코드, 단계 하강 97.5% → 95%) | 일치(양측 N1) |
| 10 | Holm — 판정 10 블록 쌍 (E :265) | `e05.py:209-218` | 8회차 손 계산 6예, 코드 무변경 | 일치 |
| 11 | Holm — 카나리 "하한 > 0, Holm" (E :139, 정본 :264) | `canary.py:31-54` | `hand_checks.py` C1–C4, 파드 dev_v1 `n_clusters` 3 | 일치(N1·N2) |
| 12 | 판정 절 해시·시각을 실행 기록 첫 줄에 (E :133) | `common.py:419-437` | 파드 5개 산출 `meta.prereg` = prereg.json(written 2026-09-24T08:32Z, 해시 5개 같음), check OK, `utc` 다음·`model` 앞 | 일치(§73) |
| 13 | 카나리 기준일 = 처음 돌린 날 (E :140) | `eval/canary.py:144-145`(파일명 정렬), `:211-218`(같은 지문·세트의 가장 이른 다른 파일) | 코드 | 일치 |
| 14 | "모델 식별 필드가 바뀌어도 같은 처리" (E :139) | `calibration.py:221-231` 지문 결속, 카나리 지문별 | 정본 §73 해석 | 정본 기록 |
| 15 | E0.5 표 = t_s − d_p95 − {0, .33, .66} (E :236) | `e05.py:43-55` | 코드(무변경) | 일치 |
| 16 | 같은 시각 K = 3 (E :238) | `e05.py:453` | 기본값 | 일치 |
| 17 | newest(요청 시각) / LA-2·γ 0.67(= 3표 중 2, 안 되면 첫 표) / C2'' 반감기 0.33 / C2' λ 3·τ 5 s·T_vlm 1·5 s / C2'-S λ 1 (E :240) | `replay.py:8-26`, `e05.py:35,58-62,134-146` | 코드 | 일치(재생 쪽) |
| 18 | `C_flip` 두 식, 직전 창 "예: 직전 1초" (E :242) | `e05.py:74-85`; 런타임 `m4.py:51,198-206` | 정본 §73 | 정본 기록 |
| 19 | A0–A4 판, 층 2지·Noul / 3–6 / 7–17, 바닥 층 × 시간 블록 (E :245-246) | `harvest/options.py:48-51`, `e05.py:225`, `:454-455` | 블록 정의 정본 §73 | 일치 |
| 20 | 성공 궤적(P0 무섭동)·섭동 궤적 따로 (E :250), 섭동 직후 창 | `e05.py:266-277`, 창 1 s `:159,466` | 정본 §73 | 일치 |
| 21 | 판정 1–3 문턱 5%·+2%p (E :256-258) | `replay.py:36-45` | 코드·`test_replay.py` | 일치 |
| 22 | 판정 4 ×2·AUROC 0.7·0.03 (E :259) | `replay.py:47-51` | 코드 | 일치 |
| 23 | 판정 5 재시험 빼기 (E :260) | `e05.py:424` | 코드 | 일치 |
| 24 | 판정 6 < 1% (E :261) | `replay.py:52-53` | 코드 | 일치 |
| 25 | 판정 7 C2' − LA-2 ≥ +2%p·하한 > 0 (E :262) | `e05.py:426` | 코드 | 일치 |
| 26 | 판정 8 치환 − 바닥 짝 하한 > 0, 층별 (E :263, :246) | `e05.py:429-430` | 코드 | 일치 |
| 27 | 판정 9 −2pt 하한·A3 > 바닥·A4 ≥ 5% (E :264) | `replay.py:54-63` | 코드 | 일치 |
| 28 | d_p95 = E0 값, 재실행 규칙 (E :236, :278) | `e05.py:456` 0.307(정본 §55), meta 주의 `:638-639` | 정본 기록 | 일치 |
| 29 | E0.5 분당 400 이하 [가정] (E :277) | 없음 | 로컬 서버 | N9 |
| 30 | E1 자료 1,200 스냅샷 적합/시험 반분 (E :296) → CAL 판 단위 반분 (정본 §52) | `calib.py:28-31,144-153`, 모집단 `:34-53` | 정본 §73 | 정본 기록 |
| 31 | ECE = 15개 동일 질량 구간, 판정 입력 (E :320, :339) | `calibration.py:71-83,193-194` | `hand_checks.py` B: 손 계산 0.264 = 코드 | 일치 |
| 32 | 오답 < 30 → AUROC 판정 불가, 게이트 끔 (E :320) | `calibration.py:191,195` | 코드 | 일치 |
| 33 | J5 α {.05,.1,.2}, 비순응 = 1 − 정답 보정 확률, q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.py:59-64`, `calib.py:66` | 코드 | 일치 |
| 34 | log p 1e-6 자름 (E :333), 반올림 시 1e-3 [가정] | `calibration.py:20,26` | 반올림 없음 | 일치(N8) |
| 35 | 질문별 온도 NLL 적합, 등위 회귀는 0.02 더 낮을 때만 (E :334) | `calibration.py:42`, 비교 없음 | 정본 §73 결정 | 정본 기록 |
| 36 | 원 확률: ECE ≤ .03 ∧ T ∈ [0.8, 1.25] (E :335) | `calibration.py:89-91`(애매 제외) | `hand_checks.py` B `fit_raw_ece` 0.264·`n_fit_ambiguous` 5 | 일치 |
| 37 | 판정 1 (i)–(iv), θ 0.6/0.7/0.8 (E :339) | `calibration.py:188-204`, `calib.py:67` | 코드 | 일치 |
| 38 | 판정 7 재보정 결속 (E :345-346) | `calibration.py:221-231` | 코드 | 일치 |
| 39 | 판정 8 J5 (E :347), 적합 400 미만 "보장 없음" | `calibration.py:197,205-209` | 코드 | 일치 |
| 40 | `ambiguous` 본 ECE 제외·따로 보고 (E :359) | `calib.py:52`, `calibration.py:89,122-149` | `hand_checks.py` B(애매 5개 ECE 0.96 따로, 포함했다면 0.363); 파드 `heldout.ambiguous.n` 11 = 독립 계수 11, `n_ece` 96 | 일치 |
| 41 | E1 판정 2–6, §3.5 일부, §3.3 2일 반복 | 없음 | 정본 §73 | SCOPED S10 |
| 42 | C5 d_p95·N_max = E0 값 (E :487), N_max = ⌈d̂/T_c⌉+1, d̂ = 최근 50회 p95 (M4 :258,:263) | `m4.py:52-53,104,118-129` | 코드 | 일치(§55) |
| **43** | **γ = 0.67 "3표 중 2" (E :487, M4 :276, :147)** | **`m4.py:46,224` (2/3 < 0.67)** | **`gamma_check.py`: `a,b,a` → CONTESTED, 재생 la2 → 확정** | **불일치 → D1** |
| 44 | W = 1, W = 0 즉시, W < 0 거부 (E :487, 정본 §72) | `m4.py:45,62-63,187-188` | 8회차 퍼즈, 코드 무변경 | 일치 |
| 45 | 비가역 W+1 (M4 :291, :306) | `m4.py:187` | 코드 | 일치 |
| 46 | τ = 1(접촉 근처 0) (E :487, M4 :277, :307; 정본 §7 :46) | `m4.py:48,148`, `core.py:39-54,435,441,503`, `m4.py:208,221-223` | `hand_checks.py` D(5.00 cm 참·5.01 거짓, carry 먼 곳 거짓, retreat의 o3–o5 참), 무작위 대조 150판(N3) | 일치(§73) |
| 47 | (b) conformal α 0.01·창 w 5 (E :487, M4 :285-286) | 정본 §61·§64 측정원 | 정본 기록 | 정본 기록 |
| 48 | STALE_MAX 1.5 s (E :487, M4 :288) | `m4.py:49,160-162` | 코드 | 일치(C5; N4) |
| **49** | **C2 = VLM Stream: 상한 없음·실측, 매 틱 가장 새 유효 응답, 5 s 타임아웃 (E :495, 정본 :179, M4 :332)** | **`conditions.py:20`, `m4.py:160-166`, `core.py:409-410`** | **`c2_stale.py` 2.0 s: 1,230/1,230 폐기; `c2_check.py` 늦은 응답 40/1,125 log_only** | **불일치 → D2** |
| 50 | C0·C1·C3·C4·C5·C6 정의 (M4 :329-346) | `conditions.py:18-24`, C5 TIDE 끔(정본 §6) | 코드, 무작위 대조 | 일치 |
| 51 | H 1과 3 비교 (E §4.12, M4 :273, :349) | `closed.py:151-160,283,396,424`, `m4.py:133` | 파드 `--m4-h 1`: spec·`meta.m4_H` 1, 호출당 슬롯 [1]; 융합 기본: `m4_H` 3·슬롯 [1,2,3]; `--m4-h 0` 거부 | 일치(§73) [정정 R7 10회차 D1: 인자 전달만 본 판정 — H = 1의 스텝당 표 수를 보면 불일치(스텝당 1표·확정 0), 정본 §75에서 수정] |
| 52 | n_LA 2 (M4 :275) | `m4.py:47,222-223` | 코드 | 일치 |
| 53 | 조기 호출은 주기 슬롯 하나를 당겨 씀 (M4 :262) | `core.py:408-416` | 코드 | 일치 |
| 54 | FLIP_TH·θ 게이트 끔(E0.5·E1 전) (정본 §6, M4 :282,:287) | `m4.py:50,214` | 코드 | 일치 |
| 55 | 경계 직후 W 2·γ 1.0, g 0.5, 장면 변화, 미확정 실행 엄격화 (M4 :150,:214,:221,:225,:259-261,:281,:289,:291) | 없음, `m4.py:24-29` | 정본 §73 | SCOPED S9 |
| 56 | P1 2 cm·near 5 cm, P2 0.5 s, h_lift 3 cm, tilt 30° (E :420-421, 정본 §7) | `perturb.py:26-27`, `config.py:8-11` | 코드 | 일치 |
| 57 | 라벨 규칙 적격 ≥ 0.90·판별력·0.02·단순 순서, D-short·D-time (prereg_labeler :7-13) | `sim/labeler.py:25,95-97,100-142` | 정본 §65 | 일치 |
| 58 | 폐루프 RD 재표집 = layout 짝, 10,000·95% 백분위 (EVAL :184) | `closed.py:56,112-133` | 파드 `meta.bootstrap.unit` "layout seed …" | 일치(§72) |
| 59 | 주 RD = Score 기반 (EVAL :182) | `closed.py:130` 성공률 | 1차판 [가정] | N12 |
| 60 | H1/H2 ΔRD·다중 비교 (EVAL :186-190) | 없음 | 기준선 | SCOPED S1 |
| 61 | M4b 자기 사전 등록 2,000회 (`e_m4b_meas.md:94`) | `m4b/*` | 정본 §72 예외 | 일치 |

### 5.1 8회차 수정 대조표(`r7c8_fixes.md` §4, 54행)와의 차이
- **행 30**("γ 0.67, n_LA 2 … `m4.py:46-47,221-224` 일치") → 이번 행 43 **불일치(D1)**: 상수는 같지만 비교 `>=`에서 2/3 < 0.67. 같은 표의 행 9는 재생(`replay.py`)만 봤고 거기서는 2/3로 맞다.
- **없던 행** → 이번 행 49 **C2 정의(D2)**: 8회차 표는 C5 설정 값만 대조하고 기준 조건 C0–C6의 정의(M4 §5·E §4.12 D9)는 대조하지 않았다.
- 행 44(카나리)·5b(판정 2): 결론 같음. 이번에는 양측 Holm의 결과(N1)와 3편 세트의 한 점 구간(N2)을 더했다.
- 행 17의 `options.py:48-51`은 `harvest/options.py`(경로 줄임) — 내용 같음. 나머지 행(1–16, 18–29, 31–42, 45–54)은 출처·코드 줄·결론이 이번 표와 같거나(줄 번호는 HEAD 기준으로 다시 찾음) 이번 표가 더 잘게 나눴다.

## 6. 확인한 것 (근거)

### 6.1 8회차 수정의 독립 확인 (과제 2)
- 손 계산 `D:\tools\scratch_qdd\r7c9\hand_checks.py` → **29/29 PASS**(`hand_checks.txt`). 부트스트랩 뽑기는 별도 구현(같은 rng 규약)으로 다시 만들고, Holm은 구간 역산 p 값(이분 탐색)의 교과서 단계 하강으로 따로 판정했다.
  - **판정 2 Holm**: A1 8회차 반례(30편) — 내 95% 하한 0.0099 > 0, 97.5% 하한 0.0 = 코드 `lo`, 교과서 Holm(p ≈ 0.030 > 0.025) 기각 없음 = 코드, `judge_e05` → `undecided`(keep_a 아님). A2 단계 하강 — C2'' 이득이 뚜렷하면(1단계 97.5%에서 기각) LA-2는 2단계 95%에서 기각(`level` 0.95, `lo` = 내 95% 하한 0.0099) = 교과서. A3 C2''가 유의하게 음이어도 같은 단계 하강(N1). A4 모든 편 이득 0.05 → 구간 [0.05, 0.05] 기각.
  - **ECE**: 깨끗한 15개(15 구간 = 1개씩) 손 계산 mean|정답 − p| = **0.264** = `ece_cal_mass`, 등폭 `ece_cal`도 깨끗한 항목만, 애매한 5개(p 0.96 모두 오답) `ambiguous` = {n 5, ECE 0.96, acc 0.0} 따로, 정확도는 20개 전부(0.65), `fit_question.fit_raw_ece` 0.264·`n_fit_ambiguous` 5. 애매 항목을 넣었다면 0.363.
  - **카나리**: 키는 `eval/canary.py:74` `f"{kind}_ep{seed}_k{k}"` + `|질문`(`:204`) — `episode_of_key("P0_ep12_k7|dir_xy")` = `P0_ep12`, `P0_ep1_k10`과 `P0_ep11_k0`는 다른 편, 밑줄·숫자가 든 kind도 끝의 `_k<n>`만 뗌. 파드 `dev_v1` 매니페스트 키 12개 → 편 {P0_ep0, P0_ep1, P0_ep2}. C1 3편 × 2스냅샷 × 2질문: dir_xy 편별 불일치 0.5/0.6/0.7 → 모든 뽑기 ≥ 0.4 → 하한 **0.4** 기각, phase 편 0에만 불일치 → 27개 순서 뽑기 중 8개가 편 0을 빼므로 하한 **−0.1** 기각 없음(손 계산과 같음), 표류 True. C2 phase만: 평균 0.333(> 바닥 2배)이어도 표류 아님(옛 규칙과 다름). C3 8편: 질문 1개면 95%에서 표류, 바닥 근처 무관 질문 4개를 더하면 1단계 99% 하한 −0.031로 표류 아님(내 편 부트스트랩 99% 하한 = 코드). C4는 N1.
  - **near_contact**(정본 §7 :46 "목표까지 ≤ 5 cm / 접촉 술어 참"): 정확히 5.00 cm 참(≤), 5.01 cm 거짓, carry(목표 o5)에서 o3를 쥔 채 멀면 거짓, retreat의 o3–o5 접촉 참, o3–탁자 접촉만이면 거짓. Isaac 관측 스키마(`snapshot.obs_to_json` :248-252, `oracle_state.py:52-65` "gripper"·물체 id)와 같은 키를 읽는다.
- **aad30d6 대 a9b56e3 무작위 대조**(`char_run.py`·`char_cmp.py`, `git archive aad30d6` 사본): 가짜 세계 폐루프 150판(지연 {0.15, 0.30, 0.45, 0.60, 0.90} s, W {1, 2}, 머그·트레이·TCP 시작 위치 무작위, 한 번의 P1 비슷한 물체 이동, 1,500–3,000틱) × C0–C6, 비교 = 행동 바이트 sha256·원장 counts·슬롯(incumbent, status) sha256·단계·epoch. **C0·C1·C2·C4 150/150 비트 동일**, C3 0/150·C5 0/150·C6 37/150 동일(차이는 원장·슬롯뿐, 행동 바이트는 7조건 모두 150/150 같음), a9b56e3에서 `near_contact`를 항상 거짓으로 바꾸면 **7조건 모두 150/150 비트 동일** → 차이는 접촉 근처 τ에서만 온다(`char_cmp.txt`).
- **`meta.prereg`**: 파드 e05·rd·calib·closed·closed(융합) 5개 모두 `prereg` = {written_utc 2026-09-24T08:32Z, hashes = `prereg.json`, check "OK"}, 키 순서 `command, argv, utc, prereg, …, model`.
- **`--m4-h`**: 파드 `closed --m4-h 1` → `spec_standard.json` `m4_H` 1, `meta.m4_H` 1, 결정 호출 행의 `slots` 길이 전부 1(H = 1이 런타임에 전달됨); 융합 판(기본) `m4_H` 3·`slots` [1, 2, 3]; `--m4-h 0` → "ValueError: M4 H = 0: decision steps per call must be >= 1", 작업자 없이 rc 1.
- **판정 2가 실제 출력에**: 파드 e05 모의 판 `judgments.j2_gain_holm.tests` = {la2: reject True, lo −0.1029, hi −0.0755, level 0.975; c2pp: reject False, level 0.95}, `judge_input`에 `gain_la2_lo` 없음, claim `a_as_stabilizer`.

### 6.2 8회차 이후 바뀐 기록
| 위치 | 주장 | 확인 |
|---|---|---|
| `handoff.md:100` | 8회차 FAIL 수치, 수정 내용, 로컬 813/11·파드 855/3, 연속 0회 → 9회차 | 이번 판 로컬 813 passed·11 skipped, 파드 855 passed·3 skipped — 같다 |
| `handoff.md:3`·`:5`·`:83` | 정본 §1~§73 | 맞음(머리 시각은 N5) |
| `draft-log.md:446`, `direction-log.md:56` | 8회차 판정·수정 요약 | 보고서·수정 문서와 같음 |
| 정본 §73 D1–D5·열린 값·N5·N8·해시 줄·보충 | 코드 줄 번호·동작 | 코드와 맞음(§5 행 9–12, 18–20, 30, 35, 46, 51, 55) |
| `r5_closed_loop.md:36`, `r6_eval.md:13`, 옛 계획서 :1291·:1492 | [정정 R7 8회차] 표시 | 표시 있음 |
| `r7c8_fixes.md` §2 "C3·C5·C6 행동 바이트 같음" | 무작위 대조 | 150판에서 같음(N3) |

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st`로 R2 DEV `/data/harvest/r2/dev/{standard,dr}/*/P0` 전 편 `validate_episode`(스탬프 안 함): **36/36 errors 없음**, 전부 DEV(seed < 30), 성공 mug_tray 12/12·mug_marker 12/12·bottle_tray 8/12. LeRobot 내보내기 시험(`venv_e3st` + `pylib_lerobot` + `pylib_pytest`, 데이터셋 캐시는 내 scratch) **6 passed**. |
| 2 모델 | 충족 | **단계 B S-E2E**(GPU 2): `stageb_train train --data se2e --run r7c9_se2e --out-root <scratch>/ckpt --max-train 40 --max-steps 6 --batch 2 --max-val 4 --eval-every 3 --reload-check --seed 43` → rc 0(04:57:16–04:57:56 UTC). 검증 dec 3.526 → 2.222 → 1.777, `save_load` `max_abs_action_diff` **0.0**, 재적재 전후 eval 같음. CUDA 시험(GPU 2, `tests/train` + `test_fused_action.py`) **102 passed**. 단계 A·단계 B 학습 코드는 `aad30d6..a9b56e3`에서 바뀌지 않았다. |
| 3 폐루프 | 충족 | (a) 모의 `closed --model mock --split dev --seeds 5 --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c9 --m4-h 1`(04:57:56–05:00:13) → `CLOSED_DONE`, 성공 1.0, `call` 39/39 64자리 hex `request_sha256`(모두 다름)·`image_sha256` {cam_head, cam_wrist_right}·`canary_id` `cn20260924_mock_ae0d1a`, `astra` 2행 hex + {cam_head} + "none", `meta.bootstrap` n_boot 10000, `meta.prereg` OK, `meta.m4_H` 1. (b) 바뀐 `core.py`의 융합 경로: `closed --model mock_fused --backend fused --split dev --seeds 6 --max-seconds 30 --isaac-gpu 1 --inst-prefix r7c9f`(05:05:11–05:07:48) → `CLOSED_DONE`(모의 청크가 자세 유지라 성공 0은 예상), `call` 90·`chunk` 90행 hex 해시·이미지 해시·카나리 id, `astra` 3행 "none", 오류 행 0. |
| 4 평가 | 충족(판정 절차는 D1·D2와 별개로 돈다) | 모의 모델 한 명령(`venv_vllm`, GPU 없음, `--n-boot` 안 줌): `e05 --data jsel_dev/P0,P1 --split dev --episodes 2` → `E05_DONE`, `rd --variants standard=jsel_dev,random=gen_dev/random --split dev --episodes 1` → `RD_DONE`, `calib --fit-data pool --fit-split pool --heldout jsel_dev/P0 --heldout-split dev --episodes 4` → `CALIB_DONE`. 모두 rc 0, `meta.bootstrap.n_boot` 10000, `meta.prereg` OK, calib `meta.ece` 문구에 애매 제외. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·카나리·시드·모델·부트스트랩·사전 등록 해시, 정리 뒤 흔적 없음(§4 N10). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`; 거부 뒤 출력 폴더 생기지 않음 — `ls ev/g*` 없음)
- `e05 --split cal`, `calib --fit-split cal`, `rd --split test`, `closed --split test --seeds 1000`, `closed --split cal --seeds 549` → "--split X refused: set HARVEST_ALLOW_SPLIT=X (main session only …)". `closed --split dev --seeds 30`·`--seeds 1149` → "not in split dev range(0, 30) (refused, never opened)". `--isaac-gpu 2` → "0 or 1 only (GPU 2 never renders)". `--m4-h 0` → ValueError. `HARVEST_ALLOW_SPLIT=dev closed --split test --seeds 1000` 거부. `gen gen --seeds 10005-10006` → "R2 generates DEV 0-29 only (R2_TRAIN 10000-59999 needs --confirm-train)". 모두 rc 1.

### 6.5 A. 테스트
- 로컬(Git Bash, `python -m pytest -q -rs -p no:cacheprovider --basetemp=D:/tools/scratch_qdd/r7c9/pt1`, TMP = `D:\tools\scratch_qdd\r7c9\tmp`, 04:38–04:39 UTC): EXIT 0, 진행 표시 **813 통과 · 건너뜀 11**(torch 없음 7, inspect_robots 2, pyarrow 1, TODO(P3) 1), F·E 0.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh` 4경로, `CUDA_VISIBLE_DEVICES=""`, TMPDIR·pyc·카나리 루트 = scratch): **855 passed, 3 skipped** 두 번(EXIT 0, 04:52:38–04:54:06 / 04:54:22–04:55:34, 70.7 s). 건너뜀 pyarrow 1·CUDA 없음 1·TODO(P3) 1, 경고 1(`test_stagea_loss_torch.py:42`, 전과 같음). 파드 CUDA 102 passed, LeRobot 6 passed.

### 6.6 같은 사실 grep (과제 3, `D:\tools\scratch_qdd\r7c9\sweep.py` — 추적 파일, `third_party/`·R7 보고서 제외, 정정 표시 유무 분리, `sweep.txt`)
- `n_boot 2000|2,000회`: 정본 §72 예외 줄, `e_m4b_meas.md:94,156`(D28 자기 사전 등록), 시험 인자 2곳, 인용 수 문구 — 현재 평가 기본값을 2,000으로 적은 곳 0.
- `Bonferroni`: 정본 §72·§72 grep 목록·시험 이름 — 0.
- 등폭 판정: `calib.py:9`("judgment 1 uses equal-mass")·정본 §72 — 0.
- `2×바닥|2배를 넘`: 정본 §73·draft-log·handoff(8회차 기록)·옛 계획서 :1291([정정] 표시)·시험 설명 — 0.
- `W=2 흡수 / 연속 2표`: 정본 §5 :35(§72가 덮음), M4·M5·SUMMARY [정정 R7 7회차] 표시, `D4-cross-field.md:118`(LocalAgreement 설명, 다른 뜻) — 0. `경계 직후`: N6.
- `τ = 1`: `D24-jev-replacement.md:195-207`(τ = 1 정답률 지표, 다른 뜻), `r5_closed_loop.md:36`([정정] 표시), 코드 머리 설명 — 0.
- `gain_la2_lo`: 옛 계획서 초안 N7, 정본 §73 — 현재 코드 0.
- `no Holm|Holm 없`: **`r7_fixes.md:45` (D-1)**(보고서 제외 규칙에 걸려 따로 grep), handoff(8회차 기록) — 그 밖 0.
- `ambiguous … ECE`: 코드·정본 §73·E-first 원문·시험 — 모두 제외 규칙과 맞음.
- 정본 범위 `§1~§N`/`지금 §N`: `handoff.md:3`·`:5`·`:83` = §73(맞음), `:27`(날짜 붙은 옛 절, N12), 단계 2 문서의 당시 범위 — 0.
- `vLLM` + 융합: 모두 모듈형 = vLLM, 융합 = HF 서버(`closed.py:18`, `eval/canary.py:9,257`, `r6_eval.md:14`) — 0.
- `one call|한 번 호출`: 정본 §58 [사용자] 절(:511, §67 C4), in-flight 1개 뜻(`conditions.py:5,11`), `jevl.py:8`, `models.py:1`, 연구 문서 — 0.
- `[제안]` + R2_TRAIN: 0. `500–699`: `tests/datagen/test_gen_guards.py:20`(거부 범위 주석) — 맞음.
- `GPU 2` + 금지: 모두 "렌더 금지" 뜻(`closed.py:165,363`, `ir_run.sh:56`, handoff :87, 계획 :29 취소선 + 대체) 또는 당시 기록 — 0.
- `102°`: 정본 :345(§37 결정 기록, §47이 덮음), `e3st.md:138`(머리 정정이 덮음) — 0.
- `20 Hz`: 모두 풀·라벨러 환경 스텝(20 Hz)·원문 인용·디바운스 환산 — 현재 시제 오류 0. `Jev (사용 가능)`: 0. `진행 중|미구현`: handoff :85("21:03 기준; R2·R6은 이후 완료") 등 표시 있음, 나머지는 설계 문장("진행 중 요청" 등 다른 뜻) — 0.
- UTC 날짜: 이번 변경 줄(정본 §73 04:16·04:37 UTC, handoff 04:18·04:27, draft-log 03:50·04:27, direction-log 03:50·04:27) = 커밋 04:37:35 UTC 이전·보고서 시각과 모순 없음(머리 시각 N5).
- 카메라(§47): 이번 변경 파일에 카메라 서술 없음; 모의·융합 판 이미지 키 {cam_head, cam_wrist_right} = §57 머리 + 활성 오른손목.
- 구현 이름 대조: `gamma`(D1), `stale_max`·`agree == "newest"`·`n_max`(D2), `near_contact`·`near=`(호출 3곳 모두 전달, `core.py:282,441,503`), `episode_of_key`·`holm_ci`, `prereg_meta`, `m4_config` — 코드 경로 끝까지 확인.

### 6.7 F. 규칙·위생
- `main` = `origin/main` = `520b2be`, `dev` = `a9b56e3` = `origin/dev`. 로컬 저장소: 04:38 UTC(13:38 KST) 뒤 바뀐 파일 0(`__pycache__` 최신 05:40 KST = 이전 세션), `git status` 깨끗.
- 로컬 C:: 시작 뒤 바뀐 것은 하네스(`.claude`·`.claude.json`, 큰 도구 출력 1건 `tool-results\*.txt`, 배경 작업 출력 `AppData\Local\Temp\claude\…\tasks`)와 이 저장소와 무관한 다른 세션의 파일(`AppData\Local\Temp\pop.py`·`killV.sh` = 다른 프로젝트 경로, `mat-debug-*.log`) — 이 저장소 산출물 0, `pytest-of-USER`·`.python_history` 없음.
- 파드: 머리 줄 정리 목록, `/data` 밖 새 파일 0(N10·N11), 내 프로세스 0(정리 뒤 `ps`), 라벨러(GPU 0)·공용 `canary`·`r2/dev`·`data/*`는 읽기만.

## 7. 다음 순회 전에 할 일 (제안)
1. **D1**: 런타임 γ를 "3표 중 2 = 확정"으로(예: `len(live) / len(s.votes) >= gamma - 1e-3` 또는 `gamma = 2/3`, 재생 `e05.py:61`·`replay.py:13`과 같은 규약), 2/3 경계 시험 추가. C3·C5·C6 동작이 바뀌므로 무작위 대조로 C0·C1·C2·C4 비트 동일을 다시 보일 것. 아니면 정본에 "런타임 γ는 초과 비교"를 결정으로(그러면 E0.5 재생과의 불일치도 적어야 함).
2. **D2**: C2를 사전 등록 정의대로(시효 5 s·타임아웃 기본 행동, 매 틱 가장 새 유효 응답, 상한 없음 + 실측 in-flight 기록) 별도 경로로 구현하거나, 런타임 C2 = 근사임을 정본 결정으로 적고 M4 판정 1·E-M4-gen·E-M4-lat 해석에 반영. 같은 기회에 N4(E-M4-lat의 C5 STALE_MAX)를 정한다.
3. **D-1**: `r7_fixes.md:45`의 "Holm 없음"에 [해결 R7 8회차, 정본 §73] 표시. 결과 문서의 "한계"·"열린" 목록을 §73 변경과 한 번에 대조(한국어 문구 포함: `Holm 없`, `2배`, `스냅샷×질문`).
4. 모두 코드·정본 변경이면 연속 무결은 0부터. 다음 순회의 대조표는 설정 **값**뿐 아니라 (a) 비교 연산의 경계(≥ 0.67 대 "3표 중 2"), (b) 조건 표의 **기준선 정의**(C0–C6·C2' 계열)까지 원문과 나란히 볼 것.
