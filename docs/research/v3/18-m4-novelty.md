# 18. M4 새로움 문장 정밀화 (가장 가까운 선행 대조 + 추가 부재 검색)

작성: 2026-09-24 UTC. 대상: plan.md v4.1 §4 후보 1(M4), §0 "비어 있는 자리 (1)", §2.5 마지막 줄, v3/17 B1·B2.
**모든 부재 판정은 "2026-09-24 기준 arXiv 제목·초록 검색 + 아래 GitHub 저장소 원문"이다.**

---

## 0. 결론 먼저

- **plan의 현재 문구 "비정지 로봇에서 빠른 typed 모델을 계단식으로 겹쳐 부르는 구조 — 선점 없음"은 그대로 쓰면 틀린다.** 세 조각이 이미 있다.
  1. **비정지**: Jev를 제어 루프에 넣은 공개 프로젝트는 거의 모두 "Jev가 생각하는 동안 직전 행동 유지"다. jev-realtime-sdk DESIGN.md가 7개 프로젝트를 조사해 "The action in flight is held while Jev thinks"를 공통 구조로 적었다. Jev-as-Policy 코드도 비정지다(`physics and continuous Cartesian servo overlap inference`, 아래 2.3).
  2. **여러 요청을 겹쳐 보내기(streaming, multiple in-flight)**: Slow Brain, Fast Planner(2606.20458, UCLA Bolei Zhou)가 **블랙박스 API VLM(Gemini, GPT-5, Qwen)에 후보 번호 선택(typed choice)을 1Hz로 기다리지 않고 보내 여러 요청을 동시에 띄우고, 비정지 실물 로봇**에서 돌렸다. 다만 도착한 것 중 **가장 새것만** 쓰고 시간 감쇠로 섞는다.
  3. **추측 → 검증 → 확정**: Speculative Actions(ICLR 2026), SMC, AOSpec(모두 비로봇, 되돌릴 수 있는 sandbox 전제).
- **남는 빈칸 (방어 가능)**: 겹쳐 띄운 호출들이 **같은 미래 결정 스텝**에 낸 typed 답끼리의 합의(a)와, 확정해 실행한 스텝에 대해 **코드가 계산한 예상 상태 대 측정 상태 비교**(b)를 **확정 기준**으로 삼고, 결과로 commit / keep / replace / repair를 고르는 구조. 이것을 비정지 로봇에서 블랙박스 typed 결정 모델로 한 사례는 arXiv 검색 53개(v3/07의 27 + 이번 26), Jev 로봇 저장소 8곳에서 찾지 못했다. 확신 **MED**(이유는 §6).
- 가장 가까운 5편(한 줄 차이)은 §5 끝에 있다.

---

## 1. 조사 방법과 한계

- WebSearch **2회**(한도 6). arXiv API 검색 **26개**(N01~N26, 간격 6초, 전부 HTTP 200, 429 없음). Semantic Scholar·GitHub API 사용 안 함.
- **본문(HTML)을 받아 해당 절을 읽은 논문 10편**: 2510.04371 Speculative Actions(2절 알고리즘, 4절 lossy OS), 2608.00881 AOSpec(4.3 JASV), 2609.03236 SMC(초록, 3.3 commit rule 주변), 2604.25050 DiscreteRTC(초록·RTC 정의), 2603.21142 AlphaAdj(초록·IV-C·지연 처리), 2606.13355(서론 4단계, 부록 A.4 multi-trajectory), 2512.17250(초록), 2606.20458 Slow Brain(3.3, 부록 스케줄링, 4.2 결과), 2609.22587 Event-triggered(초록, IV-B), 2607.05482 TypeGo(6절 S1·S0).
- 이번 검색에서 초록만 읽은 것: 2607.01804 VLA-Corrector, 2604.02965 SV-VLA, 2607.29169 ActFovea, 2605.08168, 2606.15285, 2604.24086 AsyncShield, 2607.16806 SPARK-VLN, 2608.09516 HarnessWAM, 2609.25845 Visual Jev, 2510.02851 ADAHI, 2505.20783 FM-Planner.
- **GitHub 원문**(raw.githubusercontent.com): YuanKJing/Jev-as-Policy README + `app.py`·`jev_policy.py`(코드로 비정지 여부 확인), chy4pro/jev-realtime-sdk README + DESIGN.md, RomanSlack/jev-drone README + `tactics.py`·`run.py`, Dimweaker/jev-libero README, Frank-ZY-Dou/awesome-jev, AbdelStark/awesome-typesafe-jev(로봇·게임 절), kxzk/typesafe-jev-drone-demo, openroboto-ai/jev-robot-control README(grep). 외부 페이지: systemonemodels.org 실시간 제어 페이지.
- 제출일·comment는 `export.arxiv.org/abs/<id>`에서 확인.
- 한계: 제목·초록 검색이다. arXiv 구 검색은 하이픈·어간을 느슨하게 처리한다(N06 `"in-flight"` 732건, N12 `"pipelined"` 339건은 "flight", "pipeline" 일치로 전부 무관한 소음이었다). 그래서 Slow Brain의 "multiple in-flight requests"처럼 **부록에만 있는 스케줄링 방식은 검색으로 못 잡는다**(실제로 이번에 본문을 읽고서야 찾았다). 같은 사정으로 다른 VLM 내비게이션 논문 부록에 비슷한 스트리밍이 있을 수 있다.

---

## 2. 가장 가까운 선행 연구 정밀 대조

표기: (a) = 호출 사이 합의(같은 미래 스텝의 답 비교), (b) = 확정 실행 스텝의 예상 대 측정 상태 비교. "비정지" = 모델 응답을 기다리는 동안 로봇이 계속 움직임. "블랙박스" = 학습·logit 접근 없이 API로 부르는 모델.

### 2.1 차별화 표

| 연구 (id, 첫 제출일, 신뢰도) | 무엇을 하나 (원문) | 하지 않는 것 | (a)와 겹침 | (b)와 겹침 | 로봇? | 비정지? | 블랙박스 API? | 동시 여러 호출? |
|---|---|---|---|---|---|---|---|---|
| **Slow Brain, Fast Planner** (2606.20458, 2026-06-18, MED: UCLA Bolei Zhou, 학회 미확인) | VLM이 플래너 후보 중 **번호 하나를 고른다**(typed choice). 1–3초 지연. 스트리밍 모드: "submit queries at a fixed cadence (1 Hz by default) without waiting for previous responses, keep multiple requests in flight, and on each tick fuse with the newest-by-timestamp response". 오래된 선택은 기하 유사도 + 지수 감쇠로 현재 후보 점수에 섞는다. 실험에서 VLM Hold(단일 요청)는 지연 2초 넘으면 무너지고, 스트리밍도 5초에서 20% 미만, Fusion은 80% 유지 | 도착한 답끼리 비교하지 않는다(가장 새것만). 선택의 실제 반영 확인 없음. 확정·수리 개념 없음 | **없음** (newest-wins) | **없음** (감쇠는 시간 기반, 측정 비교 아님) | 예 (실물 인도 주행) | **예** | **예** (Gemini, GPT-5, Qwen 무학습) | **예** |
| **Jev-as-Policy** (YuanKJing, GitHub 2026-09-21, 37★, LOW) | 업데이트마다 Jev 순차 2회(intent Choice → x/y/z/fingers Choice). 코드 확인: `step()`은 `busy` 플래그로 **한 번에 한 업데이트만**. 실행 중에는 `wait_ticks=0`이라 직전 방향을 **3초 만료**로 래치해 20ms 서보가 계속 움직인다. 리포트 문자열: "two sequential Jev calls per update; physics and continuous Cartesian servo overlap inference" | 호출 겹침 없음(단일 in-flight). 합의 없음. `after_observation`을 로그에 적기만 하고 비교·갱신에 쓰지 않음 | 없음 | 없음(기록만) | 시뮬(MuJoCo Panda) | **예** (finish만 1초 정지) | 예 (Jev) | 아니오 |
| **jev-realtime-sdk** (chy4pro, v0.1.0, LOW) | 코드 inner tick + Jev decision tick(2–10Hz). "at most one decision is in flight at a time; a trigger that fires while one is outstanding is skipped". 늦은 답·대체된 답은 버림. DESIGN.md: 7개 Jev 제어 프로젝트 공통 구조 = "action in flight is held while Jev thinks", "Latency is absorbed … not predicted". 결과 판단은 "fingerprint diff"(상태 지문이 바뀌었나) | 동시 여러 호출 금지(설계상). 호출 사이 합의 없음. 예측 상태 없음(지문 변화 유무만) | 없음 | **약함**: 지문 무변화 5회면 교착 판정 — "움직였나"만 보고 "예상대로 움직였나"는 안 봄 | 커서·모의 구동기(실물 없음) | **예** | 예 | 아니오 |
| **jev-drone** (RomanSlack, LOW) | Jev 약 2.5Hz, 작업자 스레드 1개, 비행 코드는 캐시된 판단을 읽기만(비차단). `stale_after_s: 1.5`, 장면 지문 같으면 재호출 안 함. 저자: 더 단순한 경기장 3시드 비교에서 이점 없음 | 합의·반영 확인 없음, 단일 in-flight | 없음 | 없음 | 시뮬 드론 | **예** (sim 시간을 벽시계에 맞춤) | 예 | 아니오 |
| **jev-libero** (Dimweaker, 63★, LOW) | 층별 Jev 선택 + 되돌릴 수 있는 시뮬 분기로 후보를 최대 8스텝 미리 실행. "Videos follow simulation time, with decision and physics-preview waiting omitted" | 비정지 아님 | 없음 | 미리보기(실행 **전** 시뮬 특권) — 실행 **후** 측정 비교 아님 | 시뮬 | **아니오 (정지 대기)** | 예 | 아니오 |
| **Speculative Actions** (2510.04371, 2025-10-05, HIGH: ICLR 2026 포스터(v3/06 확인), Columbia) | 빠른 모델이 다음 API 호출을 추측해 병렬로 미리 실행, 권위 모델 답과 **일치할 때만 확정**. 무손실 조건: 되돌릴 수 있는 추측만. 4절 lossy 확장(OS 튜닝): Speculator가 1초마다 임시 조정, Actor(10–15초)가 도착하면 **last-write-wins**로 덮어씀. 최대 55% 예측 정확도, 최대 20% 지연 감소 | 로봇 아님. 합의 대상이 "같은 스텝에 대한 다른 모델(추측 대 권위)"이지 "같은 모델의 시간차 호출"이 아님. lossy 판은 반영 확인 없이 덮어쓰기 | **부분**: "일치하면 확정" 뼈대 | 없음 | 아니오 | lossy 판만 비정지(OS) | 예 | 예(추측 분기) |
| **SMC** (2609.03236, 2026-09-03, LOW~MED: MLSP 2026) | 작은 drafter가 격리 스냅샷에서 행동 사슬을 미리 실행, 큰 actor의 다음 호출이 draft 첫 행동과 맞으면 나머지 확정. 되돌릴 수 없는 호출은 규칙으로 거부, forkable 변경은 live-state replay 일치 필요 | 로봇 아님, 물리 되돌리기 불가 문제 없음 | 부분(첫 행동 일치 → 확정) | 약함(replay 일치는 실행 **전** 검사) | 아니오 | 해당 없음 | 예 (Qwen 로컬이지만 무학습) | 예 |
| **AOSpec** (2608.00881, 2026-08-01, LOW: 미심사, Imperial) | 격리 fork에서 추측 행동 실행, JASV = "accepts the fork only if both actions and pre-execution environments match" | 로봇 아님. 검사 대상이 **실행 전 출발 상태 동일성**(sandbox 필요) | 부분(행동 동일성) | **발상 유사, 방향 반대**: 실행 전 상태 대조 / 우리는 실행 후 예상 대 측정 | 아니오 | 해당 없음 | 예 | 예 |
| **2512.17250** Input Prediction and Mishit Correction (2025-12-19, LOW: "UIUC 25 Fall CS 498" 수업 과제) | TD-MPC2가 행동 큐 + 예측 잠재 상태 생성, 새 관측의 실제 잠재와 차이를 재서 작으면 학습된 보정기로 잔차 수정, 크면 큐 비우고 재계획. 추론 500→282회, 보상 935→869(−7.1%). "speculative execution without correction is unreliable in longer horizons" | LLM 아님(제목의 "LLM"과 달리 방법은 TD-MPC2). 호출 겹침·합의 없음 | 없음 | **가장 가까운 개념**(예측 대 측정 → 유지/수정/재계획) | 시뮬 제어(DMC) | 예 | 아니오(학습) | 아니오 |
| **DiscreteRTC** (2604.25050, 2026-04-27, MED: Tomizuka·Driggs-Campbell, 미심사) | 이산 확산 정책에서 확정 행동 고정 + 나머지 unmasking = RTC. 실물 하키 방어 +65% | 학습 정책 내부 연산. 호출 사이 비교 없음(이전 청크 접두 고정만) | 약함(고정 접두 = "이미 확정된 구간 유지") | 없음 | 예 | 예 | 아니오 | 아니오(1 in-flight) |
| **2606.13355** Real-Time Execution with AR Policies (2026-06-11, LOW-MED: KIST·SNU·Google Research) | 토큰 AR VLA를 실시간 실행: 호라이즌 조정 + 실행 중 청크 접두 조건화 + 지연 상한 제약 디코딩 + multi-trajectory 중 누적 log-likelihood 최대 선택 | logit·미세조정 필요(블랙박스 불가). 호출 사이 합의·측정 비교 없음 | 약함(접두 조건) | 없음 | 예 (LIBERO, DROID 실물) | 예 | **아니오** | 아니오 |
| **AlphaAdj** (2603.21142, 2026-03-22, LOW: UVA, 미심사) | VLM 위험 점수 → CBF 파라미터. 30스텝마다 비동기 질의, "detects stale or anomalous VLM updates and triggers fallback", 기하 상한으로 과감한 값 제한 | 합의·반영 확인 없음 | 없음 | 없음(신선도·상한만) | 예 | 예 | 예(VLM) | 아니오 |
| **Event-triggered** (2609.22587, 2026-09-18, MED: TUM Knoll) | VLA 청크 추론 간격을 장면 변화 점수(P90 임계)로 조절 | 호출 시점만 다룸 | 없음 | 약함(장면 변화 ≠ 예상 대 측정) | 예 | 예 | 아니오(π0.5 LoRA) | 아니오 |
| **TypeGo** (2607.05482, 2026-07-06, MED-LOW: Yale Lin Zhong, 예비 결과) | S1 streamer가 LLM 호출마다 몇 스텝을 크기 3 bounded queue에 넣고, 하나 꺼낼 때 하나 채움(생성·실행 겹침). 각 스텝은 (조건 → 스킬) 분기, 실행 시점에 조건 재평가 | 같은 스텝을 두 번 생성하지 않음(연속 구간을 이어 붙임). 실행 후 확인 없음 | 없음 | 약함(실행 **전** 조건 재평가) | 예(Go2) | 예 | 예(LLM) | 부분(생성·실행 겹침, 호출끼리는 순차) |
| VLA-Corrector (2607.01804) / SV-VLA (2604.02965) (2026, 미심사, LOW~MED) | 청크 VLA 실행 중 **예측 대 실제 시각 특징 편차**(학습된 모니터) 또는 경량 검증기로 남은 행동 폐기·재추론 | 학습된 VLA 층. 블랙박스 결정 모델·겹침 호출 없음 | 없음 | **발상 유사(학습형)** | 예 | 예 | 아니오 | 아니오 |

### 2.2 조각별로 보면

| 우리 구성 요소 | 이미 있는 곳 | 우리만의 부분 |
|---|---|---|
| 비정지(응답 기다리는 동안 행동 유지) | Jev 제어 프로젝트 7종(jev-realtime-sdk 조사), Jev-as-Policy, jev-drone, Slow Brain, RTC 계열 전부 | **없음** — 새로움으로 주장 금지 |
| 블랙박스 typed 선택을 로봇 루프에 | Slow Brain(후보 번호), Jev-as-Policy, jev-drone | 없음 |
| 여러 호출 동시 in-flight(계단식) | Slow Brain streaming(1Hz, newest-wins), Speculative Actions·SMC·AOSpec(비로봇) | 호출 수·간격을 지연 p95에 맞춘 계단식은 설계 세부일 뿐 |
| (a) 같은 미래 스텝에 대한 시간차 호출끼리 합의 → 확정 | LocalAgreement(동시통역, 기간 밖), Speculative Actions·SMC("권위 모델과 일치하면 확정", 다른 모델끼리) | **로봇에서, 같은 모델의 시간차 호출끼리, typed 보기 ID 합의를 확정 기준으로** — 찾지 못함 |
| (b) 확정 실행 스텝의 예상 대 측정 상태 비교 → 유지/수정/재계획 | 2512.17250(TD-MPC2, LOW), VLA-Corrector·SV-VLA(학습 모니터), AOSpec JASV(실행 전), jev-realtime-sdk 지문 변화(유무만), jev-plays-pokemon-red(예측을 RAM 상태로 Brier 채점 — 평가용) | **블랙박스 typed 결정 모델의 확정에 코드 예상 상태를 되먹이는 것** — 찾지 못함 |
| (a)+(b)를 함께 써서 commit / keep / replace / repair | 없음 | **핵심 새로움** |

### 2.3 Jev-as-Policy는 로봇을 멈추나? (v3/17 B2, 확인 요청 항목)
- `app.py` `step(apply=True)`: 새 응답을 `self.command`로 래치(`'expires': time.monotonic()+3.0`), `wait_ticks = 100 if intent=='finish' else (0 if self.running else 100)`. 실행 중에는 대기 0 → 바로 다음 쌍의 호출로 넘어가고, 별도 `physics_loop` 스레드가 4ms마다 래치된 방향으로 서보한다. 주석: "Other motions overlap the next pair of API requests", "A delayed direction may reach its endpoint while an API call is in flight. Clamp there; never infer the next intent."
- **결론: 비정지다(finish 판정 때만 약 1초 정지). 호출은 `busy` 플래그로 한 번에 하나.** 겹침 호출·합의·반영 확인은 없다. README의 "Astra + JEV 평가 결과 후속 공개"는 2026-09-24 현재도 README에 예고로만 있다.
- 따라서 plan §2.5 "빠른 typed 모델이 비정지 루프 가까이 도는 구조는 스킬 상위 6편에 없다"는 **범위 밖에서는 틀린 문장**이다. 공개 Jev 데모들이 이미 그렇게 한다.

---

## 3. 추가 arXiv 부재 검색 (v3/07에 없던 것)

적중 수 = API `totalResults`. 날짜 = 첫 제출일.

| # | 검색어 | 적중 | 관련 적중 | 판정 |
|---|---|---|---|---|
| N01 | `abs:"receding horizon" AND abs:"language model" AND abs:robot AND abs:asynchronous` | 0 | — | 없음 |
| N02 | `abs:"action chunk" AND abs:"LLM" AND abs:"consistency"` | 3 | 2607.06564, 2512.03444, 2409.03166 | 전부 학습 정책·데이터 합성. 무관 |
| N03 | `abs:"streaming" AND abs:"decision" AND abs:"LLM" AND abs:"control"` | 34 | 2605.29262 RACE-Sched(v3/07에서 이미 봄) | 로봇 겹침 호출 없음 |
| N04 | `abs:"look-ahead" AND abs:"verification" AND abs:"language model" AND abs:robot` | 0 | — | 없음 |
| N05 | `abs:"lookahead" AND abs:"verif" AND abs:"language model" AND abs:robot` | 0 | — | 없음 |
| N06 | `abs:"in-flight" AND abs:robot` | 732 | 없음 | 하이픈 분리로 "flight" 일치(항공 로봇). 소음 |
| N07 | `abs:"temporal consistency" AND abs:"language model" AND abs:robot AND abs:latency` | 1 | 2603.18988 MERGE | HRI 사건 추론. 무관 |
| N08 | `abs:"consensus" AND abs:"consecutive" AND abs:"language model" AND abs:robot` | 0 | — | 없음 |
| N09 | `abs:"rolling" AND abs:"LLM" AND abs:robot AND abs:latency` | 2 | 2606.20537, 2605.28097 | 서빙 체크포인트·배포. 무관 |
| N10 | `abs:"stale" AND abs:"vision-language" AND abs:robot` | 25 | 2606.20458 Slow Brain, 2603.21142 AlphaAdj, 2607.01804 VLA-Corrector, 2605.08168, 2606.15285, 2604.24086 AsyncShield, 2607.16806 SPARK-VLN, 2607.29169 ActFovea, 2608.03483 BCP | 모두 "오래된 VLM/VLA 출력 처리"(감쇠·재투영·학습 보정·폐기). 호출 사이 합의 + 블랙박스 typed 결정 확정 없음 |
| N11 | `abs:"expected state" AND abs:"language model" AND abs:robot` | 0 | — | 없음 |
| N12 | `abs:"pipelined" AND abs:"language model" AND abs:robot` | 339 | 없음 | 어간 일치("pipeline") 소음 |
| N13 | `abs:"self-consistency" AND abs:robot AND abs:"real-time"` | 2 | 2606.09390 | 자세 인식 신뢰도. 무관 |
| N14 | `abs:"thinking while acting"` | 2 | 2604.25050 DiscreteRTC, 2512.09928 HiF-VLA | 학습 정책 |
| N15 | `abs:"latency" AND abs:"stale" AND abs:"LLM" AND abs:"agent" AND abs:"real-time"` | 2 | 2607.18267, 2604.03888 | 보험·트레이딩. 무관 |
| N16 | `abs:"predicted" AND abs:"observed" AND abs:"language model" AND abs:robot AND abs:"mismatch"` | 2 | 2608.09516 HarnessWAM, 2608.05215 | HarnessWAM: VLM 작업 관리자 + 진행 추정기로 실행 검증(스킬 경계 단위). 겹침 호출 없음 |
| N17 | `abs:"asynchronous" AND abs:"language model" AND abs:"non-blocking" AND abs:robot` | 0 | — | 없음 |
| N18 | `abs:"real-time" AND abs:"typed" AND abs:"language model" AND abs:"control loop"` | 1 | 2608.21049 | 6G RAN. 무관 |
| N19 | `abs:"multiple" AND abs:"in flight" AND abs:"vision-language" AND abs:robot` | 1 | 2505.20783 FM-Planner | 드론 경로 계획 벤치. 겹침 호출 아님 |
| N20 | `abs:"out-of-order" AND abs:"language model" AND abs:robot` | 0 | — | 없음(Slow Brain의 out-of-order 처리는 부록에만) |
| N21 | `abs:"cadence" AND abs:"language model" AND abs:robot` | 0 | — | 없음 |
| N22 | `abs:"agreement" AND abs:"language model" AND abs:robot AND abs:asynchronous` | 0 | — | 없음 |
| N23 | `all:Jev` | 14 | 2609.25845 Visual Jev 등 12편(2026-09-19~22) | **로봇 0편** 재확인(v3/07과 같은 14건). Visual Jev는 이미지 공유 배치 질문(비로봇) |
| N24 | `abs:"commit" AND abs:"verify" AND abs:robot AND abs:"language model"` | 1 | 2606.13861 | 비디오 추론. 무관 |
| N25 | `abs:"staggered" AND abs:"language model"` | 32 | 2512.16134(서빙 배치) | 로봇 없음 |
| N26 | `abs:"speculative" AND abs:"embodied"` | 35 | 2604.02965 SV-VLA, 2608.15636 SpecVLA, 2510.02851 ADAHI, 2605.13778, 2603.01581 KERV, 2607.05482 TypeGo | 전부 VLA 추론 가속(추측 디코딩·학습 검증기) 또는 TypeGo. 블랙박스 결정 모델의 시간차 합의 없음 |

WebSearch 2회: (1) "Jev TypeSafe robot pipelined overlapping requests in flight github" → 겹침 호출 로봇 사례 없음(pi-jev의 "sibling calls share one in-flight request"는 코딩 에이전트의 요청 합치기). (2) "LLM robot control "multiple requests in flight" agreement consecutive responses commit action" → 관련 없음.

**합계: v3/07 M4 검색어 27개 + 이번 26개 = 53개.** 부록에만 있던 Slow Brain streaming을 검색이 못 잡았다는 점이 이 부재 판정의 가장 큰 약점이다.

---

## 4. 새로움 문장 (최종 제안) [제안]

### 4.1 쓰면 안 되는 문장
- "비정지 로봇에서 빠른 모델을 부르는 첫 구조" — Jev 데모 7종 이상, Slow Brain, RTC 계열.
- "LLM/VLM 호출을 겹쳐 보내는 첫 로봇 시스템" — Slow Brain(streaming, multiple in-flight).
- "추측-검증-확정의 첫 적용" — Speculative Actions, SMC, AOSpec(비로봇이지만 틀 자체는 선행).
- "예측 대 측정 불일치로 재계획하는 첫 방법" — 2512.17250, VLA-Corrector, SV-VLA(학습형).

### 4.2 방어 가능한 문장 (영문, 논문용 2–3문장)
> Prior real-time systems that place a black-box language or decision model in a non-stopping robot loop either keep a single request in flight and hold the last action, or stream overlapping requests and simply adopt the newest answer (e.g., Slow Brain, Fast Planner); none checks whether the overlapping answers, and the motion already executed under them, are mutually consistent. We treat staggered, overlapping calls to a fast typed decision model as repeated votes on the same future decision steps and commit a step only when (a) successive calls agree on its typed choice and (b) the state measured after executing previously committed steps matches the state the code predicted for them; disagreement or mismatch triggers keep, replace, or repair instead of blind overwrite. To our knowledge this agreement-plus-outcome commit rule has not been applied to a training-free, API-served typed decision model on a moving robot (arXiv title/abstract search, 53 queries, and eight public Jev robot repositories, as of 2026-09-24).

### 4.3 한국어 요약 문장 (plan §4용)
> "비정지 로봇에서 빠른 typed 결정 모델(Jev)을 계단식으로 겹쳐 부를 때, 겹친 호출이 같은 미래 스텝에 낸 선택의 합의(a)와 이미 실행한 확정 스텝의 코드 예상 대 측정 상태 일치(b)를 **확정 규칙**으로 삼아 commit / keep / replace / repair를 고른다. 비정지 실행, 겹침 요청(Slow Brain: 가장 새 답 채택), 추측-확정(Speculative Actions, 비로봇)은 각각 선행이 있고, 새로움은 두 검사를 합친 확정 규칙과 그 효과 측정에 있다(확신 MED)."

### 4.4 문장에 붙여야 할 조건
- **M3 의존(v3/17 B1)**: 목표 지정형이면 "미래 스텝" 대신 **결정 지점 열**(다음 스킬, 전이 시점, critic 수락, 목표 선택)에 같은 규칙을 적용한다. 문장은 "future decision steps"로 써서 두 경우를 다 덮는다(위 영문이 그렇게 되어 있다).
- **"확률 기반"은 빼거나 조건부(v3/17 B9)**: (a)는 보기 ID 합의(최빈값·연속 일치)로 정의하고, 확률 가중은 E1 보정 결과가 좋을 때만 선택 사항으로 둔다.
- **(b)의 예상 상태는 코드가 만든다.** Jev는 수치·산술이 약하다(공식 jaggedness). Jev에게 예상 상태를 묻지 않는다. 이러면 "모델 자기 검증"이 아니라 "외부 기준 검증"이 되어 Too Consistent to Detect(EMNLP 2025, 같은 모델의 반복 오답) 반론을 피한다.
- 사용자 표현 "스스로 확인"은 **시스템이 스스로**(코드 + 합의)라는 뜻으로 쓴다.

---

## 5. 반드시 인용할 문헌 (must-cite)

| 순위 | 문헌 | 왜 | 신뢰도 |
|---|---|---|---|
| 1 | **Slow Brain, Fast Planner** 2606.20458 | 가장 가까운 선행: 비정지 + 블랙박스 VLM + typed 선택 + 여러 요청 in-flight. 우리 기준 방법(newest-wins + 감쇠)으로 그대로 재현해야 한다 | MED |
| 2 | **Speculative Actions** 2510.04371 | 추측-검증-확정 틀, lossy last-write-wins | HIGH (ICLR 2026) |
| 3 | **RTC**(2506.07339) 계열 + **DiscreteRTC** 2604.25050 | 고정 구간(확정 접두) 개념의 출처 | RTC 기간 안(2025-06), DiscreteRTC MED |
| 4 | **jev-realtime-sdk**(+DESIGN.md 7개 프로젝트 조사), **Jev-as-Policy** | 비정지·단일 in-flight·hold가 Jev 커뮤니티 표준임을 보여 주는 기준 방법 | LOW (근거 아닌 "기존 관행" 기술용) |
| 5 | **2606.13355** | 비동기 실시간 실행의 AR/토큰 정책판(학습형) | LOW-MED |
| 6 | SMC 2609.03236, AOSpec 2608.00881 | 비로봇 추측 확정의 최신판, 실행 전 상태 대조(JASV) | LOW~MED |
| 7 | 2512.17250, VLA-Corrector 2607.01804, SV-VLA 2604.02965 | (b)의 학습형·비LLM 선례. 2512.17250은 LOW라 "같은 발상"으로만 | LOW~MED |
| 8 | TypeGo 2607.05482 | 생성·실행 겹침(bounded queue) + 조건 분기 | MED-LOW |
| 9 | AlphaAdj 2603.21142, Event-triggered 2609.22587 | 오래된 VLM 출력 처리, 호출 시점 | LOW / MED |
| 10 | LocalAgreement(Whisper-Streaming, **기간 밖, 기초 문헌**) | (a) 합의 확정 규칙의 출처 | 기초 문헌 예외 |

### 가장 가까운 5편, 한 줄 차이
1. **Slow Brain, Fast Planner (2606.20458)**: 여러 VLM 요청을 겹쳐 띄우지만 가장 새 답만 시간 감쇠로 섞는다 → 호출 사이 합의(a)도 실행 결과 확인(b)도 없다.
2. **Jev-as-Policy / jev-realtime-sdk**: Jev로 비정지 로봇을 돌리지만 in-flight는 항상 하나이고 직전 행동을 유지할 뿐 → 겹침·합의·예상 대 측정 없음.
3. **Speculative Actions (ICLR 2026)**: "일치하면 확정"이지만 추측 모델 대 권위 모델의 일치이고, 되돌릴 수 있는 비로봇 API가 전제 → 물리 실행 후 확인(b) 없음.
4. **2512.17250 (TD-MPC2, LOW)**: 예측 잠재 대 실제 잠재 차이로 유지/수정/재계획 → 학습된 세계 모델, LLM·겹침 호출·합의 없음.
5. **DiscreteRTC / 2606.13355**: 확정 접두를 고정한 비동기 실행 → 학습 정책 내부 연산이고, 호출 사이 비교나 측정 확인이 없으며 블랙박스 API에 못 옮긴다.

---

## 6. 반대 증거와 위험

- **(a)의 실익이 작을 수 있다.** Jev 공식 약점 #8(질문 사이 확률 항등식 불성립)과 같은 모델 반복 오답 때문에, 합의는 "흔들림(flip-flop) 억제"는 해도 "틀린 결정 차단"은 약하다. 새로움의 무게를 (b)에 두고, (a)는 흔들림·jerk 지표로 정당화한다.
- **(b)는 코드 예측만 있으면 모델 없이도 된다.** 리뷰어가 "(b)는 그냥 MPC 잔차 감시 아니냐"고 할 수 있다. 대답: (b)의 결과가 **다음 Jev 호출의 입력 범주**와 **확정 규칙**으로 들어가 결정 모델의 커밋을 바꾸는 점이 새롭다. 실험으로 "(b) 결과를 Jev에 안 넣고 코드 재계획만" 조건과 비교해야 한다.
- **Slow Brain 결과**: VLM Stream(겹침 요청만)은 지연 5초에서 20% 미만, Fusion이 80%. "겹침만으로는 부족하다"는 우리 주장을 지지하지만, 동시에 "간단한 감쇠 융합으로 충분하다"는 반론 근거도 된다. 이 방법을 반드시 기준으로 둔다.
- **Jev 지연이 짧으면 겹침이 필요 없을 수 있다.** jev-drone 중앙값 0.11초, jev-realtime-sdk "110 ms median … 21 decisions/s pipelined". p95가 결정 간격보다 짧으면 단일 in-flight로도 된다 → E0에서 한국 p95를 먼저 잰다(v3/17 5.4). 겹침의 가치는 "지연 흡수"보다 "같은 스텝을 여러 번 보는 것"(a)에서 나와야 한다.
- **E2 전제(v3/17 A1)**: Jev 결정이 룰보다 낫지 않으면 M4의 대상이 사라진다.
- **부재 판정 확신 MED**: 부록 속 스케줄링(Slow Brain 사례)은 검색으로 못 찾는다. VLM 내비게이션·자율주행 쪽에 비슷한 스트리밍 + 투표가 부록에 있을 수 있다.

---

## 7. 기여를 보이는 실험 [제안]

같은 텍스트 상태, 같은 스킬·서보, 같은 Jev 버전(`jev-1.13.0` 고정), 같은 호출 예산(초당 호출 수 맞춤). 섭동 과제(실행 중 물체 이동, 서보 추종 오차 주입, 가림) 포함.

| 조건 | 설명 | 선행 대응 |
|---|---|---|
| C0 정지 대기 | 응답 올 때까지 로봇 정지 후 실행 | jev-libero |
| C1 단일 in-flight + hold | 한 번에 한 호출, 직전 행동 유지, 늦은 답 폐기 | Jev-as-Policy, jev-realtime-sdk |
| C2 겹침 + newest-wins | 계단식 3개 in-flight, 가장 새 답 채택 | Slow Brain VLM Stream |
| C2' 겹침 + 감쇠 융합 | 가장 새 답 + 지수 감쇠(가능한 범위에서) | Slow Brain Fusion |
| C3 겹침 + (a)만 | 합의된 스텝만 확정 | LocalAgreement식 |
| C4 겹침 + (b)만 | 예상 대 측정 불일치 시 keep/replace/repair, 합의 없음 | 2512.17250식 |
| **C5 겹침 + (a) + (b)** | 전체 | 제안 |
| C5' (a)+(b), (b) 결과를 Jev 입력에 안 넣음 | 코드 재계획만 | (b)가 "그냥 MPC"인지 분리 |
| C6 (a)+(b), 겹침 끔 | 단일 in-flight에서 연속 호출 사이 합의 + (b) | 겹침 자체의 기여 분리 |

- 지표: 성공률, 완료 시간, **정지 시간**, 잘못 확정된 스텝 비율(사후 라벨: 예상 대 측정 기준), 결정 번복(flip) 수, jerk, 섭동 후 반응 시간(섭동 → 새 결정이 실행에 반영될 때까지), 호출 수·비용, Jev 지연 p50/p95.
- 핵심 비교: C5 대 C2(=가장 가까운 선행), C5 대 C3·C4(두 검사의 기여), C5 대 C6(겹침의 기여), C5 대 C0·C1(비정지·겹침 전체의 이득). 3시드 이상 평균 ± 표준편차(jev-drone이 1회 실행으로 과장한 전례).
- 판정 기준(실행 전에 고정): C5가 C2 대비 섭동 과제 성공률 또는 잘못 확정 비율에서 3시드 모두 우위이고, C3·C4 각각보다 나아야 "(a)+(b) 결합"을 주장한다. C4 ≈ C5면 주장을 (b) 중심으로 좁힌다.

---

## 8. plan.md에 반영할 제안 [제안]

1. §0 "비어 있는 자리 (1)"과 §4 후보 1 문구를 §4.3 문장으로 바꾼다. "비정지"와 "겹쳐 부르기"는 새로움이 아니라 전제로 내린다.
2. §4 관련 조각 목록에 **Slow Brain, Fast Planner(가장 가까움)**, Jev-as-Policy·jev-realtime-sdk(관행), VLA-Corrector·SV-VLA((b) 학습형)를 추가한다. 근거 보고서 번호 v3/07 + v3/18.
3. §2.5 마지막 줄 "비정지 루프 가까이 도는 구조는 스킬 상위 6편에 없다"를 지우거나 "Jev 공개 데모(Jev-as-Policy 등)는 비정지 단일 in-flight이고, 겹침 요청은 Slow Brain이 있다"로 고친다.
4. §3 기준 방법에 **C1(Jev 커뮤니티 표준)과 C2/C2'(Slow Brain)**를 추가한다.
5. 선점 감시 표: Jev-as-Policy "Jev 응답 중 로봇 정지 여부 확인 필요" → "확인됨: 비정지, 단일 in-flight, 겹침·검증 없음(코드 확인 2026-09-24)".
6. M4 (b)의 예상 상태 생성 주체 = 코드(서보·기구학 전진 모델)로 명시.

## 9. 확인 못 한 것

- Slow Brain, Fast Planner의 학회 채택 여부(arXiv comment 없음), 스트리밍 모드에서 동시 in-flight 평균 개수.
- jev-realtime-sdk가 조사한 7개 프로젝트 중 kxzk·openroboto·FazalAAli·Icohen007·fhshaik·lukaske 저장소의 코드(README grep만 일부). "21 decisions/s pipelined"가 어느 프로젝트의 어떤 구성인지.
- openroboto-ai/jev-robot-control의 "concurrent paired execution"은 두 모델(Jev·Astra)의 병렬 비교 실행으로 보이나 코드는 읽지 않았다.
- Speculative Actions ICLR 2026 채택은 v3/06 기록에 의존(이번에 OpenReview 재확인 안 함).
- 이번 논문들의 인용 수·스타(API 미사용).
- 2026-09-23 이후 제출분(색인 전일 수 있음).

## 출처
- https://arxiv.org/abs/2606.20458 , https://arxiv.org/html/2606.20458
- https://arxiv.org/abs/2510.04371 , https://arxiv.org/abs/2609.03236 , https://arxiv.org/abs/2608.00881
- https://arxiv.org/abs/2512.17250 , https://arxiv.org/abs/2604.25050 , https://arxiv.org/abs/2606.13355
- https://arxiv.org/abs/2603.21142 , https://arxiv.org/abs/2609.22587 , https://arxiv.org/abs/2607.05482
- https://arxiv.org/abs/2607.01804 , https://arxiv.org/abs/2604.02965
- https://github.com/YuanKJing/Jev-as-Policy (README, app.py) , https://github.com/chy4pro/jev-realtime-sdk (README, DESIGN.md)
- https://github.com/RomanSlack/jev-drone (README, tactics.py, run.py) , https://github.com/Dimweaker/jev-libero
- https://github.com/Frank-ZY-Dou/awesome-jev , https://github.com/AbdelStark/awesome-typesafe-jev , https://github.com/kxzk/typesafe-jev-drone-demo
- https://systemonemodels.org/use-cases/real-time-and-agents/real-time-control/
