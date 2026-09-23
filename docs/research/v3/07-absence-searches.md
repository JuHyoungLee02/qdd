# 07. 컨트리뷰션 후보의 "선행 연구 없음" 판정 보강 (arXiv API 부재 검색)

작성: 2026-09-23 20:30 UTC. 대상: plan.md v3 §4 컨트리뷰션 후보 2번(M4), 3번(M8), 4번(M6), 5번(M10).
**모든 판정은 "2026-09-23 기준 arXiv 검색"이다.** 검색 결과에 잡힌 가장 최근 논문은 2026-09-22 제출분이다(그 뒤 제출분은 색인 전일 수 있다).

---

## 1. 조사 방법과 한계

- **arXiv 검색 API**(`https://export.arxiv.org/api/query`, `max_results=50`, `sortBy=submittedDate` 내림차순)로 검색어 **72개**를 돌렸다. 요청 간격 5초 이상. 429는 한 번도 나지 않았다.
  - 첫 시도는 파이썬 urllib로 보냈다가 406을 받았다(요청 머리글 문제). curl + https로 바꾼 뒤 전부 200. 406 요청은 결과가 없으므로 계산에서 뺐다.
- **읽은 원문**
  - 관련 후보 약 35편은 API가 돌려준 **초록 원문**(Atom `summary`)을 전부 읽었다. 제출일도 API의 `published` 값(첫 버전 제출일)으로 확인했다.
  - 판정에 결정적인 3편은 arXiv HTML 본문에서 해당 절을 읽었다: Critic in the Loop(2603.05185, 알고리즘 1), Kintsugi(2605.09487, 소속·6.4절), AutoRefine(2601.22758, 벤치마크 절).
- **WebSearch 0회**. Semantic Scholar, GitHub API는 쓰지 않았다(지시 사항). 그래서 이 보고서에서 새로 찾은 논문의 인용 수·스타는 **확인하지 못했다**. 신뢰도는 학회 표기(arXiv comment)와 소속만으로 매겼다.
- **한계**
  1. arXiv API의 따옴표 구 검색은 불용어를 무시한다. `"when to query"`는 사실상 `query` 근처 일치로 동작해 77건 대부분이 무관했다(Q19). `"when to replan"`, `"when to call"`도 같은 문제가 있을 수 있다.
  2. 제목·초록 검색만 했다. 본문에만 있는 방법(예: 본문 속 타임아웃 규칙)은 놓칠 수 있다. Critic in the Loop의 "stagnation timeout"도 초록에는 "stagnation"만 있어서, 본문을 열어 보고서야 확인했다.
  3. arXiv 밖(학회 전용 논문, 블로그, GitHub 데모)은 이번 검색 범위가 아니다. Jev 관련 GitHub 데모는 v3/01의 목록 전수 조사 결과를 그대로 쓴다.
  4. 검색어는 영어 구 조합이다. 같은 발상을 다른 용어("choice point", "gating", "arbitration")로 쓴 논문은 놓쳤을 수 있다.

---

## 2. 검색 기록 (전체)

표기: 적중 수 = API `totalResults`. "관련 적중"은 초록을 읽고 우리 후보와 조금이라도 닿는 것만 적었다. 날짜는 arXiv 첫 제출일.

### 2.1 M4 (후보 2번): 계단식 겹침 호출 + 겹침 반영 자기 검증

| # | 검색어 | 적중 | 관련 적중 (id, 제목, 날짜) | 한 줄 판정 |
|---|---|---|---|---|
| Q01 | `abs:"overlapping" AND abs:"language model" AND abs:robot` | 21 | 2609.22335 KerColle(2026-09-16), 2608.16978 VLCP(2026-08-17) | KerColle은 GPU 커널 겹침(하드웨어), VLCP는 K스텝마다 VLM이 제어 코드를 다시 씀(겹침·합의 없음). 선점 아님 |
| Q02 | `abs:"asynchronous" AND abs:"LLM" AND abs:"control loop"` | 3 | 2605.29262 RACE-Sched(2026-05-28) | 공장 일정. 느린 LLM이 규칙을 만들고 빠른 규칙 실행기가 돈다. 겹침 호출 아님(M10 쪽 참고) |
| Q03 | `abs:"speculative" AND abs:"robot" AND abs:"language model"` | 4 | 없음 | 전부 추측 디코딩(토큰 가속). 무관 |
| Q04 | `all:Jev` | 14 | 12편 모두 2026-09-19~22 Jev 논문. 로봇 논문 **0편** | **Jev를 로봇에 쓴 arXiv 논문 없음** 재확인 |
| Q05 | `abs:"multiple-choice" AND abs:"robot" AND abs:"real-time"` | 0 | — | 없음 |
| Q06 | `abs:"draft" AND abs:"verify" AND abs:"robot" AND abs:"language model"` | 1 | 2410.01440(2024, 기간 밖) | 계획 반복 정제. 겹침 호출 아님 |
| Q07 | `abs:"System One model"` | 7 | 2609.24052, 2609.24395 (Jev, 비로봇) | 로봇 없음 |
| Q08 | `abs:"decision model" AND abs:robot AND abs:"language model"` | 0 | — | 없음 |
| Q09 | `abs:"speculative actions"` | 5 | 2510.04371 Speculative Actions(2025-10-05), 2609.03236 SMC(2026-09-03, MLSP 2026), 2608.00881 AOSpec(2026-08-01), 2512.17250(2025-12-19) | 추측 → 검증 → 확정 틀의 에이전트판. 로봇·결정 모델 겹침 호출은 없음. 2512.17250만 제어(아래 3절) |
| Q10 | `abs:"real-time chunking" AND abs:"language model"` | 2 | 없음 | 무관(RAG, 음성 번역) |
| Q11 | `abs:"local agreement" AND abs:robot` | 0 | — | LocalAgreement를 로봇에 쓴 논문 없음 |
| Q12 | `abs:"asynchronous" AND abs:"language model" AND abs:robot AND abs:"overlap"` | 1 | 2609.22335 KerColle | 하드웨어 겹침. 선점 아님 |
| Q13 | `abs:"multiple-choice" AND abs:robot AND abs:"action"` | 3 | 2609.16864 TEMPO(CoRL 2026) | 객관식은 평가용 벤치 형식일 뿐. 무관 |
| Q14 | `all:TypeSafe` | 5 | 없음(2011~2022 프로그래밍 논문) | 무관 |
| Q15 | `abs:"asynchronous" AND abs:"LLM" AND abs:robot AND abs:"consistency"` | 1 | 2607.15674 GPSFSM(IROS 2026) | LLM이 FSM 계획 생성. 겹침 호출 아님 |
| Q41 | `abs:"asynchronous inference" AND abs:"language model" AND abs:robot` | 2 | 2603.21142 AlphaAdj(2026-03-22), 2506.01844 SmolVLA | AlphaAdj: 비동기 VLM 위험 점수를 "staleness-gated fusion"으로 제어에 섞음(아래 3절). 호출 사이 합의·실제 반영 확인 없음 |
| Q42 | `abs:"action chunk" AND abs:"LLM" AND abs:"overlap"` | 0 | — | 없음 |
| Q43 | `abs:"inference-time" AND abs:"real-time chunking"` | 4 | 2604.25050 DiscreteRTC(2026-04-27), 2605.25537, 2512.05964, 2506.07339 RTC | 모두 학습된 연속/이산 확산 정책의 RTC. LLM·결정 모델 아님 |
| Q44 | `abs:"hysteresis" AND abs:"language model" AND abs:robot` | 1 | 2606.13878 AnyGoal | 탐사 목표 전환. 무관 |
| Q45 | `abs:"speculative execution" AND abs:robot` | 0 | — | 없음 |
| Q46 | `abs:"predicted state" AND abs:"measured state" AND abs:"language model"` | 0 | — | 없음 |
| Q47 | `abs:"stale" AND abs:"LLM" AND abs:"robot" AND abs:"latency"` | 0 | — | 없음 |
| Q61 | `abs:"decision model" AND abs:"robot"` | 17 | 2607.17213 Retriever(2026-07-19) | "asynchronous decision model"은 수학적 형식화 뜻. Jev류 아님 |
| Q63 | `abs:"language model" AND abs:"action chunk" AND abs:"asynchronous"` | 2 | 2512.20188 DuoCore-FS(2025-12-23), 2506.01953 Fast-in-Slow | 종단 학습 VLA의 빠름/느림 비동기. 겹침 검증 없음 |
| Q64 | `abs:"agreement" AND abs:"consecutive" AND abs:"language model" AND abs:"action"` | 0 | — | 없음 |
| Q65 | `abs:"committed" AND abs:"language model" AND abs:robot AND abs:"latency"` | 0 | — | 없음 |
| Q71 | `abs:"System 1" AND abs:"System 2" AND abs:"LLM" AND abs:"multiple-choice"` | 0 | — | 없음 |

### 2.2 M8 (후보 3번): 호출 시점(주기 / 정한 순간 / 시간 초과 / 이벤트) × effort

v3/05 §4.3에서 429로 못 돌린 다섯 개는 Q16~Q20.

| # | 검색어 | 적중 | 관련 적중 | 한 줄 판정 |
|---|---|---|---|---|
| Q16 | `abs:"when to replan"` | 7 | 2608.09492 TempoWAM(2026-08-10), 2608.03483 BCP(2026-08-04) | 둘 다 청크 VLA/WAM의 "언제 다시 추론하나"를 **학습된** 진행 감시·연속/재계획 헤드로 푼다. LLM 계획기·effort·시간 초과 없음 |
| Q17 | `abs:replanning AND abs:frequency AND abs:LLM AND abs:robot` | 0 | — | 없음 |
| Q18 | `abs:"event-triggered" AND abs:"language model"` | 37 | 2607.13048(2026-06-27, ECML PKDD 2026), 2608.14991(2026-08-15), 2608.07637 Agent-MD(2026-08-07), 2606.25629 EAMP(2026-06-24, IROS 2026), 2607.15674 | 대부분 사건 추출(NLP). 관련 4편은 아래 3절. 주기 대 이벤트 비교는 2608.14991만(자율주행) |
| Q19 | `abs:"when to query" AND abs:"language model"` | 77 | 없음 | 불용어 무시로 사실상 `query` 검색. 무관 결과뿐 |
| Q20 | `abs:periodic AND abs:"event-triggered" AND abs:replanning` | 0 | — | 없음 |
| Q21 | `abs:timeout AND abs:"language model" AND abs:robot` | 2 | 2510.05547 ARRC(2025-10-07) | 타임아웃은 실행 안전 게이트(재시도 한도). LLM 재호출 트리거로 비교하지 않음 |
| Q22 | `abs:"expected duration" AND abs:robot AND abs:"language model"` | 0 | — | 없음 |
| Q23 | `abs:"time budget" AND abs:replanning AND abs:"language model"` | 0 | — | 없음 |
| Q24 | `abs:"reasoning effort" AND abs:robot` | 4 | 2609.23841 WORLDS(2026-09-20, Pavone, ICRA 2027 투고), 2609.03611 FailBench, 2607.15524 RHI, 2604.09338 Spatial-Gym | WORLDS: 추론 강도를 낮춰도 기준보다 +18.8점(항공 탐색). 호출 시점과 effort의 요인 비교는 아님 |
| Q25 | `abs:"thinking budget" AND abs:robot` | 0 | — | 없음 |
| Q26 | `abs:"self-triggered" AND abs:"language model"` | 1 | 2401.07301(무관, 자기 교정) | self-triggered 제어 개념을 LLM 호출에 적용한 논문 없음 |
| Q27 | `abs:"when to call" AND abs:"language model"` | 8 | 2412.07017 AsyncLM(2024, 기간 밖) | 도구 호출 비동기화. 로봇·재계획 아님 |
| Q28 | `abs:"invocation" AND abs:"planner" AND abs:robot AND abs:"language model"` | 1 | 2602.21161 ActionReasoning | 벽돌 쌓기 LLM 추론. 호출 시점 비교 없음 |
| Q48 | `abs:"replanning" AND abs:"trigger" AND abs:"language model" AND abs:robot` | 15 | 2603.05185 Critic in the Loop(2026-03-05), 2605.13119 VLAs-as-Tools(2026-05-13) | **Critic in the Loop이 "정체 시간 초과" 트리거를 쓴다**(아래 3절). VLAs-as-Tools는 진행 피드백 기반 이벤트 재계획(연속 폴링 없음) |
| Q49 | `abs:"periodic" AND abs:"replanning" AND abs:"language model" AND abs:robot` | 0 | — | 없음 |
| Q50 | `abs:"invocation frequency" AND abs:"language model"` | 0 | — | 없음 |
| Q51 | `abs:"reasoning effort" AND abs:"embodied"` | 1 | 2607.15439(ARC-AGI-3 코딩 에이전트) | 로봇 아님 |
| Q52 | `abs:"reasoning effort" AND abs:"latency" AND abs:"agent" AND abs:"real-time"` | 0 | — | 없음 |
| Q53 | `abs:"elapsed time" AND abs:"language model" AND abs:robot AND abs:failure` | 1 | 2605.08774 ProcVLM | 학습된 진행 보상. 호출 트리거 아님 |
| Q54 | `abs:"slow" AND abs:"planner" AND abs:"non-blocking" AND abs:robot` | 0 | — | 없음 |
| Q66 | `abs:"deadline" AND abs:"LLM" AND abs:robot AND abs:"replan"` | 0 | — | 없음 |
| Q67 | `abs:"stagnation" AND abs:"vision-language" AND abs:robot` | 5 | 2603.05185 Critic in the Loop | Q48과 같은 논문 재확인 |
| Q68 | `abs:"expected completion time" AND abs:robot` | 0 | — | 없음 |

### 2.3 M10 (후보 5번): Astra가 컴파일한 typed 규칙만 빠른 실행기(Jev)에

| # | 검색어 | 적중 | 관련 적중 | 한 줄 판정 |
|---|---|---|---|---|
| Q29 | `abs:"memory compilation"` | 11 | 2605.07594 MemCompiler(2026-05-08), 2608.00962 PMMC(2026-08-02), 2605.07068 WiCER | MemCompiler는 이미 인용 중(학습된 컴파일러). PMMC는 질문 예측 기반 메모리 프로그램(LVLM 대화). 로봇·결정 모델 아님 |
| Q30 | `abs:"compiled" AND abs:"memory" AND abs:"small model"` | 2 | 없음 | 무관 |
| Q31 | `abs:"state-conditioned" AND abs:"hints"` | 7 | 없음 | 무관 |
| Q32 | `abs:robot AND abs:experience AND abs:"small model" AND abs:"language model"` | 2 | 없음(2024, 무관) | 없음 |
| Q33 | `abs:"typed" AND abs:"rules" AND abs:"memory" AND abs:"language model"` | 20 | 2606.08151 Decision-Aware Memory Cards(ICONIP 2026), 2605.09487 Kintsugi(2026-05-10) | 메모리 카드는 코딩 에이전트의 typed 문맥 압축. Kintsugi는 아래 3절 |
| Q34 | `ti:MemCompiler` | 1 | 2605.07594 | 이미 인용 중 |
| Q35 | `abs:"executor" AND abs:"memory" AND abs:"rules" AND abs:"language model" AND abs:"small"` | 0 | — | 없음 |
| Q36 | `abs:"memory" AND abs:"distill" AND abs:"rules" AND abs:robot AND abs:"language model"` | 3 | 2605.25832 Auto-Robotist(2026-05-25) | 로봇 **설계** 탐색의 규칙 라이브러리. 실행기 주입 아님 |
| Q55 | `abs:"memory" AND abs:"small language model" AND abs:"rules" AND abs:"agent" AND abs:"experience"` | 0 | — | 없음 |
| Q56 | `abs:"lessons" AND abs:"compile" AND abs:"agent"` | 7 | 2601.22758 AutoRefine(2026-01-30), 2608.15071 Evo-Harness(2026-08-15, EMNLP 2026 Main) | **"경험 → typed 산출물 컴파일"은 이미 있다**(아래 3절). 둘 다 비로봇, 같은 모델이 소비 |
| Q57 | `abs:"teacher" AND abs:"student" AND abs:"memory" AND abs:"rules" AND abs:"embodied"` | 0 | — | 없음 |
| Q62 | `abs:"typed decision"` | 20 | Jev 논문들, 2608.11241 RecSys Factory | Jev 관련은 비로봇. RecSys Factory는 3절 |
| Q72 | `abs:"rules" AND abs:"small model" AND abs:"large model" AND abs:"memory" AND abs:"agent"` | 0 | — | 없음 |
| (Q02) | 위 M4 표 | 3 | 2605.29262 RACE-Sched | 느린 LLM이 규칙을 합성·검증 → 빠른 규칙 실행기가 원자적 교체로 받음(공장 일정). 구조 유사, 비로봇·비LLM 실행기 |
| (Q04) | 위 M4 표 | 14 | 2609.23986 Jev-Mem(2026-09-21) | Jev가 **메모리 조작을 제어**(분류·검색 예산·중단). 방향이 반대(Jev가 규칙을 받는 게 아님). 비로봇 |

### 2.4 M6 (후보 4번): 스킬 내부 결정 지점을 typed 질문으로

| # | 검색어 | 적중 | 관련 적중 | 한 줄 판정 |
|---|---|---|---|---|
| Q37 | `abs:skill AND abs:"decision point" AND abs:LLM` | 2 | 2608.11241 RecSys Factory(2026-07-31), 2602.17902 El Agente Gráfico(2026-02-19) | **"LLM 판단을 명시된 결정 지점에 가둔다"는 비로봇 분야에 이미 있다**(3절) |
| Q38 | `abs:skill AND abs:"decision points" AND abs:"language model"` | 2 | 2602.17902 (재확인) | 같은 논문 |
| Q39 | `abs:skill AND abs:"decision point" AND abs:robot` | 0 | — | 로봇에서는 없음 |
| Q40 | `abs:skill AND abs:"typed" AND abs:robot AND abs:"language model"` | 9 | 2607.06256 Semantic Handoff(2026-07-07), 2609.01215 REFACTOR-VLA(2026-09-01), 2604.14399 SpaceMind | Handoff: 스킬에 typed 인자·스텝 예산, VLM이 진행/재시도/재계획 판정(스킬 **경계**에서). REFACTOR-VLA: typed 모터 프로그램 학습. 스킬 **내부** 결정 지점 개방은 없음 |
| Q58 | `abs:"skill" AND abs:"multiple-choice" AND abs:"language model" AND abs:robot` | 1 | 없음(LEGO-Puzzles 벤치) | 없음 |
| Q59 | `abs:"behavior tree" AND abs:"language model" AND abs:"decision" AND abs:"condition node"` | 0 | — | 없음 |
| Q60 | `abs:"skill" AND abs:"branch" AND abs:"LLM" AND abs:"robot" AND abs:"query"` | 0 | — | 없음 |
| Q69 | `abs:"parameterized skill" AND abs:"language model" AND abs:"decision"` | 0 | — | 없음 |
| Q70 | `abs:"skill" AND abs:"typed" AND abs:"decision" AND abs:"LLM"` | 24 | RecSys Factory, El Agente Gráfico(재확인) | 나머지는 에이전트 스킬 보안·지식베이스 등 무관 |

---

## 3. 검증 표 (초록 또는 본문을 읽은 관련 논문)

신뢰도: README 기준. 인용 수·스타는 이번에 조회하지 않았다(1절 한계).

| 항목 | 확인 수준 | 우리 후보와의 겹침 / 신뢰도 근거 | 출처 URL |
|---|---|---|---|
| **2512.17250** Input Prediction and Mishit Correction (2025-12-19) | ORIGINAL-CONFIRMED (초록) | **M4(b)와 개념이 가장 가깝다.** TD-MPC2가 행동 큐 + 예측 잠재 상태를 만들고, 새 관측이 오면 실제 잠재 상태와 예측의 차이를 잰다. 작으면 학습된 보정기가 잔차 수정, 크면 큐를 비우고 재계획. 추론 500 → 282회, 보상 −7.1%. **LLM·결정 모델 아님, 호출끼리 겹침 합의 없음.** comment "UIUC 25 Fall CS 498"(수업 과제) → **LOW** | https://arxiv.org/abs/2512.17250 |
| **2608.00881** AOSpec (2026-08-01) | ORIGINAL-CONFIRMED (초록) | 에이전트 서빙. 행동·관측을 함께 추측하고 JASV가 "행동과 그 출발 상태"를 확정된 실행과 대조해 재사용 여부 결정. M4(b)의 "확정 전 상태 대조" 발상과 닮았지만 도구 호출 지연 문제이고 로봇이 아니다. 미심사 → LOW | https://arxiv.org/abs/2608.00881 |
| **2609.03236** Speculative Macro Commit (2026-09-03) | ORIGINAL-CONFIRMED (초록) | 큰 모델 = 권위, 작은 모델 = 초안. 초안 첫 행동이 맞으면 나머지 미리 실행분 확정. "합의되면 확정"은 LocalAgreement와 같은 뼈대. 비로봇. MLSP 2026 채택(주요 학회 아님) → LOW~MED | https://arxiv.org/abs/2609.03236 |
| **2603.21142** AlphaAdj (2026-03-22) | ORIGINAL-CONFIRMED (초록) | 비동기 VLM 위험 점수를 제어(CBF 파라미터)에 넣을 때 **staleness-gated fusion**과 속도 기반 상한을 둔다. M4 스케줄러의 "늦게 온 응답 처리" 참고거리. 겹침 합의·실제 반영 확인 없음. 미심사 → LOW | https://arxiv.org/abs/2603.21142 |
| **2604.25050** DiscreteRTC (2026-04-27) | ORIGINAL-CONFIRMED (초록) | 이산 확산 정책은 가려진 토큰 채우기가 곧 RTC(확정 행동 고정 + 나머지 생성). "이산 선택 + 고정 구간"이라는 점에서 우리 텍스트판 RTC와 비유가 된다. 학습된 정책 → 결정 모델 API에는 못 옮긴다. Tomizuka·Driggs-Campbell 공저, 미심사 → MED | https://arxiv.org/abs/2604.25050 |
| **2603.05185** Critic in the Loop (2026-03-05) | ORIGINAL-CONFIRMED (본문 알고리즘 1) | **M8 시간 초과 트리거의 가장 가까운 선례.** 학습된 시각 Critic의 가치가 N_stag = 180스텝(제어 약 20Hz → 약 9초) 동안 최고값을 넘지 못하면 "stagnation timeout" → 로봇 상태 초기화 + VLM(Brain) 재호출. 다른 트리거는 하위 작업 완료, 물리적 실패. **다만 (1) 예상 소요 시간이 아니라 "진행 정체" 기준, (2) 트리거 방식끼리 비교 실험이 없다(절제는 프롬프트 형식 등), (3) effort 축 없음, (4) 로봇이 VLM을 기다리는지 여부는 본문에서 확인 못 함.** 중국과학원 자동화연구소, 미심사 → MED | https://arxiv.org/abs/2603.05185 , https://arxiv.org/html/2603.05185 |
| **2608.14991** Risk-Adaptive Edge-Cloud (2026-08-15) | ORIGINAL-CONFIRMED (초록) | 자율주행(CARLA). 온보드 위험 평가가 클라우드 VLM 호출 시점을 정한다. **주기 호출과 성공률 같음 + 요청 54.1% 감소.** 지연 도로공사 절제에서 이벤트가 다음 정기 점검보다 먼저 호출. 주기 대 이벤트 비교 선행 연구 목록에 추가. 시간 초과·effort 없음. 미심사 → LOW | https://arxiv.org/abs/2608.14991 |
| **2607.13048** Event-Triggered LLM Invocation in Streaming Systems (2026-06-27) | ORIGINAL-CONFIRMED (초록) | ECML PKDD 2026 채택(comment). "빠른 모델 + 비싼 LLM, 언제 부르나"를 위험 기반 순차 정지 문제로 정식화. 채터링 방지 최소 사건 간격, 임계값 정책 최적성, regret 보장. 이벤트·SPRT·CUSUM·베이즈 트리거를 특수 경우로 포함. 터보팬 데이터 + 실제 LLM 호출. **로봇 아님, 시간 초과·effort 없음.** 단일 저자 → MED(학회 채택) | https://arxiv.org/abs/2607.13048 |
| **2608.09492** TempoWAM / **2608.03483** BCP (2026-08) | ORIGINAL-CONFIRMED (초록) | 청크 정책의 "고정 실행 지평 대 적응형 재계획". 둘 다 학습(진행 감시기 보정, RL 헤드). 실물 로봇에서 추론 −26.9%(TempoWAM, 쉬운 작업), 성공 74 → 92%, 44 → 84%(BCP). 호출 대상이 VLA/WAM이라 우리 Astra 호출과 층이 다르다. 미심사 → LOW~MED | https://arxiv.org/abs/2608.09492 , https://arxiv.org/abs/2608.03483 |
| **2605.13119** VLAs-as-Tools (2026-05-13) | ORIGINAL-CONFIRMED (초록) | VLM 에이전트가 VLA 도구를 고르고, 도구가 실행 중 진행 피드백을 내보내 **연속 폴링 없이 이벤트로 재계획**. 호출 시점 비교는 초록에 없음. 미심사 → LOW~MED | https://arxiv.org/abs/2605.13119 |
| **2609.23841** WORLDS (2026-09-20) | ORIGINAL-CONFIRMED (초록) | Pavone 연구실. 추론 강도를 낮춰도 GeoNav 기준보다 +18.8점, 토큰은 적음. "effort를 낮춰도 된다" 쪽 증거 하나 추가(로봇 탐색). ICRA 2027 투고(미심사) → MED | https://arxiv.org/abs/2609.23841 |
| **2601.22758** AutoRefine (2026-01-30) | ORIGINAL-CONFIRMED (초록 + 벤치마크 절) | **M10의 "경험을 typed 산출물로 컴파일"은 여기서 이미 한다.** 실패/성공 궤적을 대조해 Rule / Skill / Subagent 중 하나로 컴파일, 타입별 계약 검사 + 재생 검사 통과 시에만 채택. GPT-5.6-terra 공통 백본, TravelPlanner 80.56% 대 최강 기준 50.0%. ALFWorld 등 텍스트 환경, 로봇 없음. **규칙을 소비하는 쪽이 같은 큰 모델**이고, 작은/빠른 결정 모델에 정확 일치로 붙이는 구조는 아니다. 미심사, 7쪽 → LOW~MED | https://arxiv.org/abs/2601.22758 |
| **2605.09487** Kintsugi (2026-05-10) | ORIGINAL-CONFIRMED (초록 + 소속·6.4절 제목) | TU Darmstadt Kersting 연구실. 정책 지식을 typed 실행 KB(술어·연산자·모니터·복구 규칙·경험 기록)로 두고, 롤아웃 증거로 국소 typed 편집, 결정론 검증 게이트. **실행 시 LLM 호출 0회**(기호 실행기). SquareNut 등 물체 중심 조작 설정 포함. M10과 "typed 규칙 + 검증 게이트"는 겹치고, 빠른 결정 모델이 없다는 점이 다르다. 미심사 → MED | https://arxiv.org/abs/2605.09487 |
| **2608.15071** Evo-Harness (2026-08-15) | ORIGINAL-CONFIRMED (초록) | EMNLP 2026 Main(comment). 한 번의 잡음 섞인 실행을 재사용 가능한 스킬 하네스로 컴파일(동결 에이전트). 비로봇, 소비자는 같은 에이전트. M10 관련 연구 → HIGH(학회 채택 표기 기준, 반응 미확인) | https://arxiv.org/abs/2608.15071 |
| **2605.29262** RACE-Sched (2026-05-28) | ORIGINAL-CONFIRMED (초록) | 느린 LLM 흐름이 규칙을 합성·샌드박스 검증 → 빠른 반응 흐름(기호 휴리스틱)에 원자적 교체로 배포, 제어 루프를 막지 않는다. **"느린 상위가 규칙을 컴파일하고 빠른 하위는 규칙만 실행"의 비로봇 선례.** 하위가 결정 모델이 아니라 규칙 엔진. 미심사 → LOW | https://arxiv.org/abs/2605.29262 |
| **2609.23986** Jev-Mem (2026-09-21) | ORIGINAL-CONFIRMED (초록) | Jev가 메모리 구성·검색을 제어(System One 제어 평면). **Jev가 메모리를 "받는" 우리 M10과 방향이 반대.** LoCoMo 0.777. 비로봇, 미심사 → LOW | https://arxiv.org/abs/2609.23986 |
| **2608.11241** RecSys Factory (2026-07-31) | ORIGINAL-CONFIRMED (초록) | Tencent 추천 운영, 78일 배포. "파이프라인이 아니라 **결정 지점에서의 자율**". 스킬 파일의 함정 표가 400항목 PitfallStore로 기계적으로 컴파일되어 자율을 "bounded typed decision surfaces"로 가둔다. **M6 발상과 M10의 "컴파일된 함정 규칙"이 둘 다 비로봇 분야에 있다.** 미심사 → LOW~MED | https://arxiv.org/abs/2608.11241 |
| **2602.17902** El Agente Gráfico (2026-02-19) | ORIGINAL-CONFIRMED (초록) | 과학 에이전트. typed 실행 그래프로 상태 전이를 강제하고 **모델 판단을 명시적 결정 지점으로 제한**. 비용 약 −80%, 벽시계 4배 이상 단축(이전 다중 에이전트 대비). 비로봇, 미심사, 소속은 이번에 확인 못 함 → LOW~MED(반응 미확인) | https://arxiv.org/abs/2602.17902 |
| **2607.06256** Semantic Handoff Failures (2026-07-07) | ORIGINAL-CONFIRMED (초록) | BEHAVIOR-1K. π0.5 스킬에 typed 인자와 스텝 예산을 주고, 다중 시점 VLM이 진행/재시도/재계획 판정. 결정은 **스킬 경계**에서. 스킬 내부 결정 지점은 아님. 미심사 → LOW~MED | https://arxiv.org/abs/2607.06256 |

---

## 4. 후보별 결론 (2026-09-23 기준 arXiv 검색)

### 후보 2번 (M4) — **선점 없음**, 확신도 중간(MED)
- 27개 검색어(Q01~Q15, Q41~Q47, Q61, Q63~Q65, Q71)에서 "LLM 또는 결정 모델을 1초에 여러 번 겹쳐 부르고, 호출 사이 합의 + 측정 상태로 반영을 확인해 갱신"하는 로봇 논문은 없었다.
- `all:Jev` 14건 중 로봇 0건. Jev 로봇 논문 없음 재확인(2026-09-22 제출분까지).
- 부분적으로 닮은 조각(모두 조각 하나씩만):
  - 추측 → 검증 → 확정: Speculative Actions(ICLR 2026, 이미 인용), SMC, AOSpec(에이전트 서빙, 비로봇).
  - 예측 상태 대 실제 상태 차이로 보정/재계획: 2512.17250(TD-MPC2, 수업 과제, LOW). **관련 연구 절에 "비-LLM 제어에서의 같은 발상"으로 적되 근거로 쓰지는 않는다.**
  - 늦은 비동기 VLM 출력 처리: AlphaAdj staleness gating(LOW).
  - 이산 행동 RTC: DiscreteRTC(학습 정책).
- 확신도를 HIGH로 못 올리는 이유: 제목·초록 검색만 했고, "겹침/합의"를 다른 말(예: "rolling", "receding", "consensus")로 쓴 논문은 놓쳤을 수 있다.

### 후보 3번 (M8) — **부분 겹침**, 확신도 중간(MED)
- v3/05 §4.3에서 429로 막힌 다섯 검색어(Q16~Q20)를 돌렸다. 새로 겹치는 것:
  - **Critic in the Loop(2603.05185)**: 진행 정체가 약 9초(180스텝) 이어지면 "stagnation timeout"으로 VLM 재호출. **"시간 초과 트리거를 쓴 로봇 LLM/VLM 논문은 없다"는 문장은 쓰면 안 된다.** 쓸 수 있는 문장: "시간 초과류 트리거를 다른 호출 방식과 같은 호출 수로 비교한 연구는 찾지 못했다", "M2의 예상 소요 시간에서 코드가 마감을 계산하는 방식은 찾지 못했다".
  - 주기 대 이벤트 비교 선행 연구 추가: 2608.14991(자율주행, 주기와 성공률 같고 요청 −54.1%).
  - 이론 쪽: 2607.13048(ECML PKDD 2026)이 이벤트 트리거 LLM 호출을 순차 정지 문제로 정식화했다(비로봇). 관련 연구로 인용할 만하다.
  - 학습된 "언제 재추론" 헤드: TempoWAM, BCP(VLA/WAM 층).
- 빈칸 (a) 예상 시간 기반 시간 초과를 **독립 조건**으로 둔 비교, (b) 학습 없는 API effort 단계 × 호출 방식, (c) 비정지 실행, (d) 호출 수 맞춘 요인 설계: 이 조합은 **찾지 못했다**. v3/05의 "평가·분석 컨트리뷰션, 새로움 중간~낮음" 판정을 유지한다.
- 검색어 `"expected duration"`, `"time budget"`, `"deadline"`, `"expected completion time"`, `"self-triggered"`, `"thinking budget"`, `"invocation frequency"` 조합은 모두 0건이었다.

### 후보 4번 (M6) — **로봇에서는 선점 없음, 발상은 비로봇 분야에 있음(부분 겹침)**, 확신도 낮음~중간(LOW~MED)
- `abs:skill AND abs:"decision point" AND abs:robot` 0건(Q39). 로봇에서 스킬 **내부** 결정 지점을 typed 질문으로 여는 논문은 못 찾았다.
- 비로봇 선례 두 편: **El Agente Gráfico**(모델 판단을 typed 실행 그래프의 명시적 결정 지점으로 제한), **RecSys Factory**("결정 지점에서의 자율", bounded typed decision surfaces). 둘 다 관련 연구로 인용해야 한다. 여기에 v3/01의 Jev_SO101 데모(발상 수준)가 더해진다.
- 로봇 쪽 가장 가까운 것: Semantic Handoff(2607.06256, 스킬 경계에서 typed 인자 + VLM 판정).
- 확신도가 낮은 이유: "decision point"는 표준 용어가 아니다. behavior tree의 조건 노드, "choice point", "branching" 같은 동의어 조합(Q59, Q60)은 0건이었지만 검색어가 좁았다.
- 차별점 문장 제안 [제안]: "비로봇 에이전트에서 제안된 '결정 지점에 판단을 가두는' 설계를 로봇 스킬 내부로 옮기고, 결정 지점마다 확률을 내는 결정 모델을 붙여 정량 평가한다."

### 후보 5번 (M10) — **부분 겹침**, 확신도 중간(MED)
- **"경험 → typed 규칙/산출물 컴파일"은 이미 여러 편 있다**: AutoRefine(Rule/Skill/Subagent 컴파일 + 검증 게이트), Kintsugi(typed 실행 KB + 결정론 검증, 조작 설정 포함), Evo-Harness(EMNLP 2026), RecSys Factory(PitfallStore 컴파일), MemCompiler(상태 조건 컴파일, 이미 인용). 느린 상위가 규칙을 만들고 빠른 하위가 실행하는 구조도 RACE-Sched(비로봇)가 있다.
- 찾지 못한 조합: **API 계획기(Astra)가 컴파일한 typed 규칙을, 코드가 (스킬, 결정 지점, 술어) 정확 일치로 0~2개만 골라, 확률을 내는 빠른 결정 모델(Jev)에 넣는 로봇 시스템.** Jev-Mem은 Jev가 메모리를 "제어"하는 반대 방향이다.
- 따라서 plan §4의 "선행 사례 못 찾음"은 **"컴파일 자체"에 대해서는 틀렸다.** 새로움은 "주입 대상이 확률 결정 모델이고, 정확 일치로 붙이고, 로봇에서 센서 술어로 라벨한다"는 좁은 부분에만 있다.

---

## 5. 반대 증거와 위험

- M8: Critic in the Loop이 정체 시간 초과를 이미 쓰므로, 리뷰어가 "시간 초과 트리거는 새롭지 않다"고 할 수 있다. 차별점은 "진행 정체" 대 "계획기가 말한 예상 시간 초과"의 구분과, 그것을 비교 조건으로 둔 것뿐이다. 두 가지를 모두 실험 조건으로 두면 오히려 비교가 풍부해진다(제안).
- M8: WORLDS·AGP·Show-Harness에 이어 effort를 낮춰도 성능이 유지된 로봇 결과가 하나 더 있다(WORLDS). effort 축의 효과가 작게 나올 가능성이 커졌다.
- M10: AutoRefine, Kintsugi가 검증 게이트까지 갖췄으므로, 우리 M10에 "검증 게이트"가 없으면 약해 보인다. 반대로 Kintsugi는 LLM 0회 실행이라 "규칙만으로 충분하면 결정 모델이 왜 필요한가"라는 반론이 가능하다 → 기준 방법에 "규칙만(결정 모델 없음)" 조건을 넣을 근거.
- M4: 2512.17250이 "보정 없는 추측 실행은 긴 지평에서 믿을 수 없다"를 보였다(비LLM). 우리 M4(b) 실제 반영 확인의 필요성을 뒷받침하지만, LOW라 근거로 쓰지 않는다.

---

## 6. plan.md에 반영할 제안

- [제안] §4 후보 2번(M4): "선점 없음(2026-09-23 기준 arXiv 검색 27개 검색어, v3/07)"로 근거를 바꾼다. 관련 연구에 Speculative Actions 계열(SMC, AOSpec), AlphaAdj, DiscreteRTC를 "조각별 유사"로 적는다.
- [제안] §4 후보 3번(M8): 빈칸 (a)를 "시간 초과 트리거"에서 **"계획기가 준 예상 소요 시간으로 코드가 계산한 마감 트리거를, 진행 정체 트리거(Critic in the Loop)와 구분해 같은 호출 수로 비교"**로 고친다. 관련 연구에 Critic in the Loop, 2608.14991, 2607.13048 추가. M8 실험 조건에 "정체 시간 초과"를 넣는 것을 검토.
- [제안] §4 후보 4번(M6): "로봇에서 선점 없음, 비로봇 선례 El Agente Gráfico·RecSys Factory"로 적는다.
- [제안] §4 후보 5번(M10): "선행 사례 못 찾음"을 **"경험의 typed 컴파일은 선행 연구 있음(AutoRefine, Kintsugi, Evo-Harness, MemCompiler). 새로움은 확률 결정 모델에 정확 일치로 붙이는 부분뿐"**으로 고친다. 기준 방법에 "규칙만 실행(결정 모델 없음, Kintsugi식)" 조건 추가 검토. 채택 전 검증 게이트(AutoRefine식 재생 검사) 추가 검토.
- [제안] §0 "아직 선점되지 않은 자리" 문단에서 M10 문구를 좁힌다.

## 7. 확인 못 한 것

- 새로 찾은 논문의 인용 수와 GitHub 스타(Semantic Scholar·GitHub API를 쓰지 않았다).
- Critic in the Loop에서 로봇이 VLM 응답을 기다리는지(비정지 여부)와 트리거별 호출 횟수.
- El Agente Gráfico, AutoRefine의 소속(초록·일부 본문만 읽음).
- arXiv 밖(학회 전용, OpenReview 전용 투고, GitHub 데모)의 부재 여부. Jev 관련 GitHub 데모는 v3/01 결과에 기댄다.
- 2026-09-23 제출분(색인 전일 수 있음).
