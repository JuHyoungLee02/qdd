# M10. 경험 축적 — 모듈 설계 (단계 2)

> **정본 우선**: 모듈 사이 인터페이스·정지·확정 규칙·확률 게이트·시간 값은 `00-interfaces.md`가 우선한다(2026-09-23 22:00 UTC). 이 문서와 다르면 그쪽을 따른다.
> 개정: 2026-09-23 D5 반영 (00-interfaces §16): effort 표기를 "잠정 기본 high(다른 작업 발언 근거) — [결정 필요] 5"로.
> 개정: 2026-09-23 정본 §14–§15 반영 (`00-interfaces.md` §14·§15, `D4-cross-field.md` §11, `D4-cross-field-verification.md` #17·#18·#19): CBR 4R의 Revise(적용·검증 뒤에만 Retain, Aamodt·Plaza 1994)를 센서 라벨 규칙의 **기초 문헌 근거**로 추가(새 기전 아님), **역량 보존 사례 삭제**(Smyth·Keane, IJCAI 1995)를 E-M10 조건 B10으로 추가, TLM(ICML 2025)·MemoPilot(ICML 2026)은 가중치 갱신·갱신기 학습이 필요해 **쓸 수 없음**으로 기록.
> 개정: 2026-09-23 D2 검증·00-interfaces §11 반영 (`D2-verification.md` Part A 정정, Part B·C 해소안. 핵심: Jev 규칙 키 = M6 스킬 고정 결정 지점 id, 술어는 M1 등록부 이름, L1 LAG는 `ref(t)` 기준, 삭제 규칙 "최소 n회 꺼낸 뒤", GEPA Pareto 뜻 정정(우리 게이트는 "비열화 게이트"), PragmaBot·Proactive Memory Agent 수치·조건 정정, SkillsBench 사람이 다듬은 스킬 +18.2~+24.8pp 추가, BATON 보조로 내림.)


작성: 2026-09-23 22:05 UTC 전후(`date -u` 기준 시작 21:49), 단계 2 모듈 설계 에이전트(M6·M10 담당). 규칙: `docs/design/README.md`.
읽은 것: `plan.md` v4.3(§1, M10, §2.5, §3), `user-log.md` 11(경험 축적), `research/v3/03`(메모리 원문 확인 22편), `v3/07`(Kintsugi 등 선행), `design/M7`(술어·라벨), `design/M9`(체크포인트·"메모리 없는 재시도" 기준), `design/M6`(결정 지점 키).

표기: **[원문]** / **[접목]** = 우리 접목안 / [사용자] / [제안] / [결정 필요]. 전제: 특정 M1 후보를 가정하지 않고 **M1 술어 등록부 인터페이스(M1 §4.0)에만 의존**한다(00-interfaces §11.3). 결정 지점 id는 **M6 스킬 계약에 고정된 id**가 정본이다(00-interfaces §11.1).

---

## 0. 조사 방법과 한계
- WebSearch: M10용 2회(메모리 해악 증거 1, 로봇 경험 메모리 1). M6과 합쳐 5회(한도 10). arXiv 검색 API·S2·GitHub API 쓰지 않음.
- 이번에 원문 HTML 본문을 읽은 것: 2505.16067(표 1·2, §3.4, §4), 2604.27003(§3.2, §3.4, 설정), 2607.08716(소속, 표 2 설정, 절제 문장), 2507.16713 PragmaBot(§IV-D, 표), 2608.16889 BATON(전이·메모리 키 문장), 2607.16636 PhyAgentOS(교훈 주입 문장).
- arXiv abs만: 2604.14004, 2606.29774, 2605.31075, 2511.21730, 2608.22767, 2510.08191, 2508.16153, 2507.19457, 2510.04618, 2604.18791, 2607.01111.
- v3/03의 원문 확인 수치(2606.15017, Evo-Memory, MemCompiler, ExpWeaver, SkillsBench, ReasoningBank)는 다시 읽지 않고 인용한다.
- 인용 수·스타 미측정(API 금지). 신뢰도는 학회 표기·소속·v3/19 값으로만.

---

## 1. 역할과 입출력

[사용자] (user-log 11 (9)) "경험 축적이 제대로 되어야 한다. API로 불러오는 모델의 경험 축적을 어떻게 하는지, 어떻게 해야 효율적인지 논문을 찾는다. 1년 반 이내."

| 항목 | 내용 |
|---|---|
| 입력 | 에피소드 기록: 세션 계약, 결정 스텝 기록(M3 `DecisionStep`: 질문·보기·확률·예상 결과 술어), M4(b) 범주(OK/LAG/DEVIATE/CONTRADICT, M4가 낸 값 그대로), M7 사건(FAIL/WARN, 발동 채널, 단계 원장 `exit_k`/`invariants_k`), M9 복구 시도와 결과, 스킬 결과 술어(M6 `exit`), 측정 술어 시계열, Astra 판단문 |
| 출력 A (Astra용) | 계획·재계획·복구 호출에 붙는 경험 묶음(교훈 항목 top-k + 비슷한 사례 1~2건) |
| 출력 B (Jev용) | 결정 지점 키가 정확히 맞는 **컴파일 규칙 0~2줄** |
| 출력 C (M6용) | 스킬 계약 수정 제안(`entry`/`lookahead_req` 추가, 파라미터 기본값) — 검증 게이트 통과한 것만 |
| 하지 않는 것 | 실행 중(에피소드 안) 메모리 정리·재작성. 가중치 학습(Astra·Jev 모두 API, 학습 불가). LLM 판정만으로 "성공" 라벨 |

---

## 2. 분야 전체 최고 후보 표

기간 ≥ 2025-03-23. ◎ 이번 원문, △ v3/03 원문 확인, ○ 초록만.

### 2.1 (1) 메모리 구조: 무엇을 저장하고 어떻게 넣나

| 이름 | 분야 | 어디서 최고였나 (조건) | 신뢰도 | 기간 | 학습 없이 | 로봇 |
|---|---|---|---|---|---|---|
| **Evo-Memory: ExpRAG / ReMem** (2511.20857) △ | LLM 에이전트 | 10여 개 메모리 모듈을 같은 루프로 비교. Claude 3.7 Sonnet ALFWorld 성공 No-mem 0.18, AWM 0.49, **ExpRAG 0.74, ReMem 0.92**(표 1b). 4환경 평균 AWM 0.49 / ExpRAG 0.63 / ReMem 0.78. 표 3: **거르지 않은 실패 경험 저장 시 기준 방법들이 뚜렷이 나빠짐**. 예산 맞춘 비교 아님, ReasoningBank·ACE 없음 | HIGH(GDM+UIUC, 인용 130) | 2025-11 | 예 | 아니오(텍스트 체화 시뮬) |
| **ReasoningBank** (2509.25140) △ | LLM 에이전트 | 교훈 항목(제목·설명·내용), 성공·실패 모두에서 추출. 판정기 정확도 72.7%(Shopping) | HIGH(ICLR 2026) | 2025-09 | 예 | 아니오 |
| **ACE** (2510.04618) ○△ | LLM 문맥 공학 | "evolving playbook", 생성·반성·**큐레이션** 분리, **구조화된 증분(delta) 갱신으로 context collapse 방지**. 에이전트 +10.6%, 금융 +8.6%(초록), AppWorld 상위 에이전트와 평균 동률 | HIGH(ICLR 2026) | 2025-10 | 예 | 아니오 |
| **GEPA** (2507.19457) ○ | LLM 프롬프트 최적화 | 궤적을 자연어로 반성해 **프롬프트 규칙을 진화**. Pareto는 **"문제 인스턴스별 최고 후보들을 남겨 거기서 다음 후보를 뽑는" 다양성 장치**(§3.1, D2 A1 정정)이고, 그 후보들의 보완 교훈을 합침. GRPO보다 평균 +6%, 최대 +20%, 롤아웃 최대 35배 적음. MIPROv2보다 10% 넘게(초록) | **HIGH(ICLR 2026 Oral, 인용 391)** | 2025-07 | 예 | 확인 못 함 |
| Training-Free GRPO (2510.08191) ○ | LLM 에이전트 | 롤아웃 그룹의 "의미적 상대 이점"으로 경험 지식을 증류해 **API 호출 때 token prior로** 넣음. DeepSeek-V3.1-Terminus, 수십 개 학습 샘플로 미세조정 소형 모델보다 나음(초록) | MED-LOW(Tencent Youtu, 학회 미확인) | 2025-10 | 예 | 아니오 |
| **Proactive Memory Agent** (2607.08716) ◎ | LLM 에이전트 | **별도 메모리 에이전트**가 구조화 메모리를 갱신하고 **"알림을 넣을지, 침묵할지"** 결정. 실행 주기: **첫 스텝과 이후 매 스텝**(§4.1, D2 정정 — "고정 주기" 아님). Terminal-Bench 2.0 +8.3pp, τ²-Bench +6.8pp(pass@1, τ²는 과제 가중)는 **약한 행동 에이전트 Sonnet 4.5일 때**. **Opus 4.6 행동 에이전트는 +2.4 / +2.5**(Table 1). 절제(τ², 행동 에이전트 Sonnet 4.5, 메모리 에이전트 Opus 4.6): 선택적 개입이 수동 노출·항상 주입·조언자형·일반 검색보다 나은 것은 **macro 평균에서만**. micro에서는 Always inject가 0.3p 앞섬(저자: 실행 분산 이내, §4.3 Table 2). **범위: 한 과제 안(실행 중) 메모리**이고 에피소드 사이 경험 축적이 아니다 | MED(Meta AI, 심사 전, 인용 3) | 2026-07 | 예(주 결과는 API 모델) | 아니오 |
| **MemCompiler** (2605.07594) △ | 체화 LLM | 상태 조건 컴파일. 통째 주입이 32B 실행기에 −18.8~−61.8%(표 6), 큰 폐쇄 모델엔 +31~46%(표 1) | MED(MSR+칭화 AIR, 심사 전) | 2026-05 | 컴파일러는 학습 | 체화 시뮬 |
| ExpWeaver (2605.07164) △ | LLM 에이전트 | 필요할 때만 꺼냄, 강한 모델은 거의 안 꺼냄(GPT-5.2 0.00회), 엔트로피 높은 스텝에 몰림 | MED-LOW | 2026-05 | 일부 | 아니오 |
| **PhyAgentOS** 교훈 (2607.16636) ◎ | 로봇 | "only after the outcome is verified is the resulting knowledge committed"(§4.3), KNOWLEDGE/LESSONS 분리. **"Retrieved knowledge is injected with provenance and scope: a lesson learned on one embodiment is not assumed to transfer unless its preconditions match the new target and scene."** | MED(2,481★) | 2026-07 | 예 | 예 |
| **BATON** 전이 인지 메모리 (2608.16889) ◎ | 로봇 | **"Edges are keyed by transition type rather than by task"**("좁은 입구 용기에 놓기"가 바구니→통으로 전이), 계약 위반을 되써서 해당 전략을 그 전이에서 배제. RoboMemArena 과제 +11.6, 누적 +14.9(%p, 초록) | LOW-MED(USC, 심사 전, 인용 1). **보조 참고**: 검색 키 1순위를 좌우하는 근거로 쓰지 않는다(00-interfaces §11.3, D2 C5) | 2026-08 | 예 | 예 |
| **PragmaBot** (2507.16713) ◎ | 로봇(실물) | VLM이 결과를 시각 판정·반성 → STM(과제 중) → 과제 뒤 LTM 요약 → RAG. STM 35→84%. **LTM 12개 실물 시나리오(8개 처음 봄) 단일 시도 80%, 비교값 22%는 다른 방법(COME, LTM 없음)**이지 같은 시스템의 LTM 끔이 아니다(D2 정정). **LTM 100항목 중 96개는 단순 과제의 교시용(instructional) 경험**이고 과제에서 얻은 것은 4개(§V-C). RAG 대 전체 LTM 통째 프롬프트는 **첫 행동 정확도** 89% 대 74%(실행 없음, Fig. 7) | MED-HIGH(**RA-L 채택**, ETH Hutter, 인용 3) | 2025-07 | 예 | 예 |
| Analytic Concept-Centric Memory (2606.29774) ○ | 로봇 | 물체 부분·템플릿·자세·어포던스·조작 상태 + 전이 메모리 + 스킬 메모리, **거친→세밀 구조 검색**이 비구조·임베딩 메모리보다 나음(초록) | MED(SJTU Cewu Lu, 심사 전) | 2026-06 | 확인 못 함 | 예 |
| Kintsugi (2605.09487) △ | 로봇(기호) | typed 실행 KB(술어·연산자·모니터·복구 규칙) + 결정론 검증 게이트, **실행 시 LLM 0회** | MED-LOW(TU Darmstadt, 인용 2) | 2026-05 | 예 | 예 |
| Dynamic Cheatsheet △ | LLM | 비교 기준 | MED(EACL 2026) | 2025-04 | 예 | 아니오 |
| TLM (2505.20633) / MemoPilot (2606.08656) | 동결 LLM 테스트 시점 학습 | TLM: 입력 perplexity 최소화 + LoRA 갱신. MemoPilot: 메모리 갱신기를 multi-turn GRPO로 학습해 동결 LLM 플레이어 개선, Elo LHE 1762 / RPS 1590(초록) | HIGH (TLM ICML 2025, PMLR 267:24823–24849 / MemoPilot ICML 2026 공식 목록) | 2025-05-27 / 2026-06-07 | **아니오**(가중치 갱신 / 갱신기 학습) → Astra·Jev(API)에 **쓸 수 없음** | 아니오 |

### 2.2 (2) 라벨: 무엇을 "성공 경험"으로 저장하나

| 이름 | 어디서 최고였나 (조건) | 신뢰도 |
|---|---|---|
| **Experience-following** (2505.16067) ◎ | 입력이 비슷한 기억을 꺼내면 출력도 비슷해진다(experience-following) → **오류 전파**, **어긋난 경험 재생**. 표 1(4개 에이전트, 열 순서 RegAgent / EHRAgent / AgentDriver / CIC-IoT): 고정 메모리 67.53 / 16.75 / 40.11 / 71.50, **전부 추가 55.48 / 13.05 / 32.32 / 59.90(고정보다 나쁨)**, 엄격 선별 추가(사람 판정) **70.95 / 38.50 / 51.00 / 85.40**, 자동 판정 C1~C3은 그 사이. 표 2: **이력 기반 삭제**가 엄격 판정과 짝지을 때 대개 최고, 결합 삭제가 메모리를 가장 줄임. 원문 삭제 규칙: **"최소 n회 꺼낸 뒤" 평균 효용 ≤ β이면 삭제**(§4.1, D2 조건 보완). "future task evaluations can serve as free quality labels". 지표: RegAgent SR, EHRAgent ACC, AgentDriver SR, CIC-IoT ACC | **HIGH(ACL 2026 long, aclanthology 2026.acl-long.27 — D2가 페이지를 열어 제목 확인, 인용 97)**, Harvard·MSU |
| 2606.15017 표 10 △ | ReasoningBank LLM 판정이 "성공"이라 한 것 중 52.9%(Gemini)·59.5%(GPT) Shopping이 실제 실패 | HIGH(EMNLP 2026) |
| PragmaBot ◎ | VLM 자기 판정 라벨을 쓰는 시스템이 실물 단일 시도 80%(비교값 22%는 다른 방법 COME). **정정(D2)**: LTM 100항목 중 96개가 교시용 경험이라 **이득의 대부분을 VLM 자기 판정 라벨로 돌릴 수 없다**. "LLM 판정이 쓸모없지 않다"의 약한 근거로만 | MED-HIGH(RA-L) |
| Zetta 검증 게이트 △ | 패치는 진단 재생 + 새 폐루프 롤아웃 두 단계 통과해야 채택 | MED |
| **CBR 4R 순환** (Aamodt·Plaza, AI Communications 1994) | Retrieve → Reuse → **Revise(재사용한 해를 실제로 적용·검증)** → Retain. 검증된 해만 저장 | 기간 밖, 기초 문헌(원문 이번에 안 읽음) |
| **역량 보존 사례 삭제** (Smyth·Keane, "Remembering To Forget", IJCAI 1995, 1권 p.377) | 사례마다 coverage(그 사례가 풀 수 있는 문제 집합)·reachability(그 문제를 풀 수 있는 사례 집합)를 보고 pivotal / spanning / support / auxiliary로 4분류. pivotal을 지우면 역량이 되돌릴 수 없게 줄어들므로, 다른 사례가 덮는 auxiliary부터 지운다(D4 검증이 ijcai.org 목차와 PDF 원문으로 확인) | 기간 밖, 기초 문헌 |

### 2.3 (4) 메모리가 도움이 될 때와 해가 될 때 (2026 증거)

| 이름 | 결과 (조건) | 신뢰도 |
|---|---|---|
| **2606.15017** △ | 웹(WebArena 4도메인, 작업 독립, 온라인 보강, 3회 평균): 예산 맞춘 메모리 없음(Vanilla-IB) 44.78% 대 AWM 39.34, ASI 41.02, RBank 39.33(Gemini 3 Flash). 저자 한계: 작업이 독립이라 장기 메모리 불필요 | HIGH(EMNLP 2026) |
| **2604.27003** ◎ | ALFWorld·BabyAI 순차 과제, ReMe 메모리 모듈, 고정 백본: **추상 절차 교훈(Insight)은 양의 전이, 원시 궤적(Raw)은 A→B에서 음의 전이**. 음의 전이는 **"hard cases"(메모리 없음 기준 실패 부분집합)에 집중**. 조건: B→A ALF에서는 Insight도 −2.5 → "Insight는 양의 전이"는 방향·환경 의존. 더 세밀한 단위·더 잦은 검색이 항상 좋지 않음, 새 과제 적응이 좋은 설계가 이전 과제 망각(BWT<0)을 일으킴. 오염 원인 3종: retrieval pollution, context competition, memory dilution | LOW-MED("Working in progress") |
| 2604.14004 ○ | 코딩 6벤치, 교차 도메인 메모리 평균 +3.7%, **추상 통찰은 전이, 저수준 궤적은 음의 전이** | MED-LOW(KAIST Hwang, NYU Ren, 프리프린트) |
| MemoryArena (2602.16313) △ | 대화 메모리 벤치 포화 에이전트도 서로 의존하는 다중 세션 과제에선 낮음 | HIGH(ICML 2026) |
| MemCompiler 표 6 △ | 작은 실행기에 통째 주입은 해로움 | MED |
| SkillsBench v4 △ | 사전 자기 생성 스킬 −8.1~−11.5pp(skill-creator로 팩을 먼저 만들고 그 팩만으로 풀이, 부록 D.6). **같은 설정에서 사람이 다듬은 스킬은 +18.2~+24.8pp**(D2 A1) — "검증·큐레이션된 절차 지식은 돕고, 검증 없는 자기 생성은 해롭다"는 쪽. 우리 게이트·센서 라벨의 근거 방향 | HIGH(반응) |
| 2511.21730 ○ | 절차 검색에서 **임베딩은 처음 보는 어휘에서 급락**, LLM이 만든 절차 추상은 전이 | LOW(반응 미측정) |
| PragmaBot ◎ | 실물 반복 과제에서 LTM 시스템이 크게 도움(단 비교 기준은 다른 방법 COME, LTM 대부분은 교시용 경험). 실패 사례: 꺼낸 기억(가림 치우기)을 VLM이 무시해 실패 | MED-HIGH |

요약 [해석]: 도움이 되는 조건 = (i) 같은 구조의 과제가 반복됨, (ii) 기억이 **추상 절차·교훈** 수준, (iii) 저장 전 **검증된 라벨**, (iv) 주입이 **선택적**(침묵 가능). 해가 되는 조건 = 원시 궤적, 거르지 않은 실패, 통째 주입(특히 작은 실행기), 예산을 맞추면 사라지는 작은 이득, 새 과제의 어려운 사례.

---

## 3. 가져올 것과 접목 방법

| 출처 | 원문에 있는 것 | 우리 접목안 [접목] |
|---|---|---|
| ExpRAG | (입력, 출력, 피드백) 템플릿, top-k | Astra 사례 단위 = (과제, 단계 k, 스킬 id, 결정 지점 id(M6 고정 id), 술어 스냅샷(M1 등록부), 물체 범주) → (Astra 계획/복구 행동) → (**센서 라벨** + 결과 술어) |
| ReMem | 매 스텝 {Think, Act, Refine-memory} | Refine을 **에피소드 사이로 옮긴다**(Astra 지연 때문, 원문과 다름). 실행 중에는 읽기만 |
| ReasoningBank | 교훈 항목 형식(제목·설명·내용), 실패에서 예방 교훈 | 형식 그대로 + 필드 추가: `scope`(스킬·전이 유형·물체 범주), `provenance`(에피소드 id, 라벨 등급), `counters`(도움/해 횟수) |
| ACE | 생성·반성·큐레이션 분리, delta 갱신, 중복 병합 | 큐레이션은 오프라인 배치(에피소드 N개마다). 교훈 전체 재작성 금지(context collapse 방지) — 항목 추가·병합·퇴출만 |
| 2505.16067 | 엄격 선별 추가 > 자동 판정 > 전부 추가, 이력 기반 삭제("최소 n회 꺼낸 뒤 평균 효용 ≤ β", §4.1) | 추가 = 센서 라벨 (a)등급만(엄격 판정의 대리). 삭제 = **최소 n회(초기값 n=3 [제안]) 꺼낸 뒤**, 꺼낸 뒤 해당 결정 지점·단계의 센서 성공 비율(`then_success / retrieved`)이 β(초기값 0.5 [제안]) 이하이면 퇴출(이력 기반 삭제의 로봇판). n 미만일 때는 삭제하지 않는다(적은 표본의 우연한 실패로 지우지 않기) |
| PhyAgentOS | provenance·scope 붙여 주입, 사전조건 맞을 때만 전이 | Jev 규칙의 **정확 일치 키**와 같은 원리. Astra 교훈도 scope 불일치면 넣지 않음 |
| BATON(보조 참고) | 메모리 키 = 과제가 아니라 **전이 유형**, 위반 시 그 전략 배제 | 착상 출처로만. 검색 키 1순위 = (스킬 id, **M6 고정 결정 지점 id**) — 근거는 PhyAgentOS의 provenance·scope(사전조건이 맞을 때만 전이)와 M6 계약 id 정본 규칙이다. 전이 유형(`handoff:pick->place_narrow`)은 **보조 키**로 두고, 1순위로 올릴지는 E-M10-1 부수 비교(키 방식별 규칙 발동률·결정 변경 비율)로 정한다. 위반 기록은 "avoid option" 규칙으로 컴파일 |
| Proactive Memory Agent | 메모리 에이전트가 알림 넣을지·침묵할지 결정, 선택적 개입이 macro 평균에서 최선(약한 행동 에이전트일 때 이득이 큼, 한 과제 안 메모리) | 범위 차이를 명시: 원문은 **과제 안** 메모리이고 우리 출력 A는 **에피소드 사이** 경험이다. 옮기는 것은 "침묵할 수 있는 선택적 주입" 원리뿐. Astra 호출 때는 **Astra 스스로**(또는 코드 조건) 넣을지 결정 — 별도 에이전트는 호출 비용이 커서 안 쓴다. Jev에는 "키 일치 없으면 침묵"이 같은 원리 |
| MemCompiler / ExpWeaver | 작은 실행기엔 상태 조건 공개, 필요 시만 | Jev에는 교훈 문장 금지, 컴파일 규칙 0~2줄만(plan M10 유지) |
| GEPA | 반성으로 규칙 진화. Pareto = 인스턴스별 최고 후보를 남겨 거기서 뽑는 **다양성 장치**(§3.1) | (1) 후보 **생성**: 반성으로 규칙 후보를 만든다(GEPA식). 후보 풀을 여럿 유지할 때는 원문대로 "시드별 최고 후보를 남기는" Pareto 풀을 쓸 수 있다. (2) **채택**은 GEPA와 다른 우리 장치인 **비열화 게이트**: 후보 규칙은 개발 시드들에서 "켠 것 대 끈 것"을 재생 비교, 어느 시드에서도 성공률을 떨어뜨리지 않는 것만 채택. 이 게이트는 GEPA의 Pareto와 뜻이 다르다(이름을 빌리지 않는다, D2 A1). 원문은 프롬프트 최적화용, 로봇 적용 확인 못 함 |
| Zetta | 진단 재생 + 새 롤아웃 두 단계 검증 | 게이트 두 단계: (1) 원 실패 에피소드 재생에서 규칙이 해당 결정을 바꾸는지, (2) 새 시드 롤아웃에서 성공률 비감소 |
| Kintsugi | 실행 시 LLM 0회 규칙 실행 | 기준 방법 "rules-only": 컴파일 규칙 + M6 R 조건 규칙을 코드가 실행, Jev·Astra 없음 |
| 2604.27003 | 추상 > 원시, 음의 전이는 어려운 사례에 | 원시 궤적은 저장만(디버깅·재생용), 주입 금지. 결과는 **쉬운/어려운 부분집합으로 나눠 보고** |
| CBR 4R (기초) | Revise = 재사용한 해를 실제로 적용·검증한 뒤에만 Retain | 새 기전이 아니다. 센서 라벨 규칙("센서 술어로 확정한 (a)등급만 교훈·규칙 재료", §4.2)이 이미 Revise다 → **기초 문헌 근거 상향**으로만 표기(00 §14) |
| Smyth·Keane 1995 (기초) | coverage·reachability로 4분류, 다른 사례가 덮는 것부터 삭제, 유일하게 덮는 사례(pivotal)는 보존 | Jev 규칙의 coverage = 정확 일치 키(skill_id, dp_id, 조건 술어). **같은 키를 다른 규칙이 이미 덮으면 먼저 삭제 후보, 그 키를 유일하게 덮는 규칙은 보존**(삭제 대신 재게이트). 2505.16067식 이력 기반 삭제의 **비교 조건**(E-M10 B10)으로만 둔다. Astra 교훈은 scope로 coverage를 근사해야 해 정의가 느슨하다 → Jev 규칙표에만 적용 |
| TLM, MemoPilot | 가중치 갱신 / 갱신기 학습 | 쓰지 않는다. MemoPilot의 "메모리 갱신을 다단계 결정으로 보고 뒤 결과로 평가"는 발상만: E-M10에서 규칙 추가·삭제마다 뒤 N 사건의 성공 변화를 기록(측정만, 학습 없음) |

---

## 4. 설계안

### 4.1 1순위: 두 갈래 메모리 (Astra 교훈 저장소 / Jev 컴파일 규칙표)

```
 에피소드 실행 (읽기만)
   Astra 호출(계획·재계획·복구) ← 검색: 키 정확 → 범주 → (선택) 임베딩, top-k=3 교훈 + 사례 ≤2
   Jev 결정 지점              ← 규칙표 조회: (skill, dp, 술어값) 정확 일치 0~2줄, 없으면 침묵
 에피소드 뒤 (오프라인)
   ① 라벨링(코드, 4.2) → ② 추출(Astra, ReasoningBank 형식) → ③ 큐레이션(ACE delta, 코드+Astra)
   → ④ 컴파일(Astra: 교훈 → typed 규칙 후보) → ⑤ 게이트(재생 + 새 시드, 비열화) → ⑥ 규칙표 반영
   → ⑦ 이력 기반 삭제(counters, 최소 n회 꺼낸 뒤)
```

**Astra 교훈 항목** [제안]
```json
{"id":"L-0042","title":"Side grasp before narrow place",
 "description":"When the place target opening is narrow, top grasps collide at release.",
 "content":"Choose side approach at dp.approach_dir if next skill is place-narrow; verify clearance before release.",
 "scope":{"skill":"pick-*","transition":"handoff:pick->place_narrow","object_cat":"rigid_small"},
 "provenance":{"episodes":["e17","e23"],"label":"sensor_confirmed"},
 "counters":{"retrieved":5,"then_success":4,"then_fail":1}}
```
**Jev 규칙** [제안] (영어, 범주형만, 보기 ID로)
```
hint: at dp.approach_dir if next_skill=place-narrow and top_clear(o3)=yes -> prefer side_front
hint: at dp.release if contact_under(o3)=no -> avoid release_now
```
- 키 = (skill_id, dp_id, 조건 술어). **dp_id는 M6 스킬 계약에 고정된 id**(`dp.approach_dir`, `dp.release` 등)이고 M2 계약은 이 id를 골라 쓸 뿐이다(00-interfaces §11.1, D2 B1) → 에피소드마다 이름이 달라져 규칙이 안 맞는 일이 없다. 조건 술어는 M1 등록부 이름(`top_clear` T2, `contact_under` T1, `next_skill`은 문맥 변수), 보기(`side_front`, `release_now`)는 그 스킬 inputSchema enum 안에서만.
- 규칙은 **보기 순서를 바꾸지 않는다**(M3 순서 편향 규칙). `prefer`/`avoid` 한 줄로만.
- Jev 규칙 최대 2줄/결정 지점(SkillsBench "짧은 것이 낫다", Library Drift 상한, v3/03).

### 4.2 센서 술어 라벨링 파이프라인 [제안]
| 단계 | 내용 | 출처 |
|---|---|---|
| L1 결정 스텝 라벨 | 각 확정 스텝의 **M4(b) 범주를 그대로 기록**한다(M10이 다시 계산하지 않음). M4(b)는 두 가지를 따로 계산한다: (1) M5 계획 궤적 **`ref(t)` 대비 연속 잔차** → OK / **LAG**(LAG는 `ref(t)` 기준에서만 나옴) / DEVIATE, (2) 선택 보기의 `expected_after` 술어 대 측정 → 일치 / CONTRADICT. 두 값을 함께 저장 | M4 문서, 00-interfaces §3·§11.2(D2 B14) |
| L2 단계 라벨 | 스킬 단계별 `stop`·`exit` 술어 참/거짓, budget 초과, `invariants` 위반(T1이면 M7 하드 FAIL, T2면 소프트 `C_pred`), M7 발동 채널 목록 | M6 계약, M7 |
| L3 에피소드 라벨 | 과제 수용 기준(단계 원장 마지막 `exit_k`)을 **센서 술어로** | PhyAgentOS 수용 기준 |
| L4 책임 단계 | First Missing Milestone(Zetta §2.3)으로 첫 누락 단계 → 그 단계의 결정 지점들에 실패 귀속. "진입 상태가 틀렸나(앞 단계 책임) / 스킬이 약했나"를 M6 `entry` 술어로 구분(착상 BATON, 보조) | Zetta |
| 등급 | (a) 술어로 확정(T1·T2 술어, T3는 (b)) → 교훈·규칙 재료 / (b) 술어가 못 다뤄 Astra 다중 프레임 판정 → "미검증", Astra 참고만 / (c) 판정 불가 → 저장 안 함 | v3/03 §3.4 |
| 효용 라벨 | 꺼낸 항목마다 이후 해당 단계의 L2 결과를 counters에 누적(2505.16067 "future task evaluations as free labels") | 2505.16067 |
실패 경험: (a)등급 실패 + L4로 책임 단계가 특정된 것만 "예방 교훈"으로(Evo-Memory 표 3의 거르지 않은 실패 경고).
근거 표기(00 §14): (a)등급만 교훈·규칙 재료로 쓰는 규칙은 CBR 4R의 Revise(Aamodt·Plaza 1994, **기간 밖, 기초 문헌**)와 같은 원리다. 새 기전이 아니라 근거 상향이다.

### 4.3 검색 키와 예산
- Astra 키 계층: ① (skill_id, dp_id(M6 고정 id), 실패 유형 술어) 정확 — 전이 유형은 보조 키(§3 BATON 행) → ② + object_cat → ③ (선택) 임베딩(2511.21730: 처음 보는 어휘에서 임베딩 급락이라 마지막 수단). 최대 top-3 교훈 + 사례 2건, 상한 토큰 T_mem(예: 1,500) [제안 값].
- Jev 키: (skill_id, dp_id, 규칙 조건 술어 전부) 정확 일치만. 부분 일치 없음. 술어 등록부 버전·스킬 계약 버전이 바뀌면 해당 규칙은 재게이트 전까지 끈다.
- [결정 필요] Astra 주입 방식: (i) top-k 기본 주입 / (ii) 도구로 필요할 때 조회(ExpWeaver: 강한 모델은 거의 안 꺼냄 → Astra도 안 꺼낼 위험) / (iii) 코드가 "키 ① 일치 있을 때만" 주입(Proactive Memory Agent의 "침묵" 원리를 코드로. 원문은 과제 안 메모리·macro 평균 우세라 근거 강도는 약함). 1순위 제안 (iii), 비교는 E-M10-2.

### 4.4 대안
- **대안 A (GEPA식 템플릿 진화)**: 규칙을 따로 붙이지 않고, Jev 질문 템플릿 문구·보기 이름 자체를 오프라인으로 진화(후보 풀은 GEPA식 인스턴스별 Pareto, 채택은 비열화 게이트). Jev #8(문구 바뀌면 확률 비교 불가) 때문에 **템플릿 교체는 버전 단위로만**.
- **대안 B (rules-only, Kintsugi식)**: 컴파일 규칙이 충분히 쌓인 결정 지점은 Jev 없이 코드가 실행. 기준 방법이자, 호출 절감 수단.

---

## 5. 비교 실험 (판정 기준 사전 고정)

### 설정
- 반복 과제 열: 단계 A(같은 물체 범주·장면 배치 변화, 에피소드 40) → 단계 B(새 물체 범주 또는 새 장면, 에피소드 40) → A 재평가 20(망각 측정). 시드 = 과제 순서·장면 배치, **≥ 3개(가능하면 5개), 평균 ± 표준편차**(2606.15017 권고).
- 같은 M1·M6 계약·Jev 버전·Astra effort(고정, 잠정 기본 high(다른 작업 발언 근거) — 이 프로젝트 적용은 [결정 필요] 5, 00 §16).

### 조건 (E-M10-1 주 비교)
| id | 조건 |
|---|---|
| B0 | 메모리 없음 |
| **B1** | **예산 맞춘 메모리 없음**(2606.15017 Vanilla-IB의 로봇판): 메모리에 쓸 토큰·호출을 Astra 추가 호출(예: 복구 때 재질의 1회 더)과 상태 가지치기에 쓴다. 비용은 에피소드당 Astra 입력 토큰과 벽시계로 맞춘다 |
| B2 | ExpRAG(사례 top-k, LLM 판정 라벨) |
| B3 | ReasoningBank 형식 + LLM 판정 라벨(Astra 판정) |
| **B4** | 1순위: B3 형식 + **센서 라벨** + ACE 큐레이션 + 이력 기반 삭제 + Jev 컴파일 규칙 |
| B5 | B4에서 Jev 규칙만 뺌(Astra 쪽 메모리만) |
| B6 | B4에서 Jev에 규칙 대신 교훈 top-k 문장 통째 주입(MemCompiler AMMI의 대응) |
| B7 | **rules-only**(Kintsugi식): B4 규칙표 + M6 R 규칙을 코드가 실행, Jev·Astra 결정 없음(Astra는 계획만) |
| B8 | Dynamic Cheatsheet |
| B9 | B4에서 게이트(⑤) 끔 |
| B10 | [제안] B4에서 삭제 정책만 **역량 보존 삭제**(Smyth·Keane IJCAI 1995식)로 교체: 규칙표를 키 coverage로 분류해, 효용 조건(최소 n회 꺼낸 뒤 `then_success / retrieved` ≤ β)에 걸린 규칙 중 **같은 키를 다른 규칙이 덮는 것은 삭제**, 그 키를 유일하게 덮는 규칙은 삭제 대신 재게이트(⑤)로 보냄. 결정 지점당 2줄 상한을 넘을 때도 덮이는 규칙부터 뺀다. n·β는 B4와 같게 |

### 지표
성공률(A, B, A 재평가), **전방 전이**(B의 학습 곡선 기울기·B 첫 10편 성공률), **BWT**(A 재평가 − A 끝), **쉬운/어려운 부분집합**(B0 기준 성공/실패 시드별로 나눠 음의 전이 위치, 2604.27003), 에피소드당 Astra 토큰·호출·벽시계, Jev 입력 토큰·지연 p50/p95, 메모리 크기, 규칙 수, 규칙 발동률, 규칙 발동 시 결정이 바뀐 비율, 라벨 오염률(B3의 LLM 라벨 대 센서 라벨 불일치).

### 판정 (사전)
1. **메모리 채택**: B4 − B1 ≥ +5%p(단계 A 끝 20편 평균)이고 평균 차 − 두 조건 표준편차 합 > 0. 아니면 "메모리 이득 없음"을 결과로 보고(2606.15017과 같은 결론).
2. **망각 허용**: B4의 BWT ≥ −3%p.
3. **음의 전이 점검**: 어려운 부분집합에서 B4가 B0보다 낮으면 해당 단계의 규칙·교훈을 원인별로 보고(발동 로그로).
4. **Jev 규칙 방식**: B4 − B5 ≥ +3%p이면 Jev 규칙 유지. B6 < B5이면 "Jev에 교훈 통째 주입 금지" 확정(MemCompiler 방향 재현).
5. **라벨**: B4(센서) − B3(LLM 판정) ≥ +3%p이거나 라벨 오염률 ≥ 20%이면 센서 라벨 원칙 확정. 차이 없으면 PragmaBot 쪽 증거와 함께 "판정 품질이 결정적이지 않을 수 있음" 보고.
6. **rules-only**: B7이 B4와 −2%p 이내면 "규칙이 쌓인 결정 지점은 Jev 불필요"를 인정하고 호출 절감으로 보고(프로젝트 주장 약화 위험 명시).
7. **게이트**: B9가 B4보다 낮으면(1%p 이상) 게이트 유지. 비용(게이트 롤아웃 수)도 함께 보고.
8. **삭제 정책**: B10이 B4보다 성공률 +2%p 이상이거나, −1%p 이내이면서 BWT가 B4 이상이고 규칙 수가 적으면 역량 보존 삭제를 채택 후보로. B10의 BWT가 B4보다 나쁘면(역량 보존의 원래 목적과 반대) 채택하지 않는다.

### E-M10-2 Astra 주입 방식
(i) top-k 항상 / (ii) 도구 조회 / (iii) 키 ① 일치 때만. 지표: 복구 성공률, Astra 토큰, 조회 횟수(ii), 교훈 "과잉 적용"(한 교훈이 응답에서 언급된 횟수, 2606.15017 F.3 관찰). 판정: 성공률 차 2%p 이내면 토큰이 가장 적은 안.

---

## 6. 반대 증거와 위험
- **예산을 맞추면 이득이 사라질 수 있다**(2606.15017, EMNLP 2026). 다만 작업 독립 웹 환경이고, 우리 반복 조작은 메모리에 유리한 쪽일 수 있다(추론, 미검증) → B1 필수.
- **음의 전이는 어려운 사례에 몰린다**(2604.27003, LOW-MED). 평균만 보면 숨는다 → 부분집합 보고.
- **Experience-following**(2505.16067, ACL 2026): 비슷한 입력의 기억을 따라 한다 → 틀린 기억 하나가 반복 전파. 이력 기반 삭제로 막지만 "최소 n회 꺼낸 뒤"라는 조건 때문에 삭제가 늦게 작동하고, 그 사이 초기 에피소드가 오염된다(n과 β는 E-M10-1 부수 측정으로 조정).
- **LLM 판정 라벨을 쓰는 시스템도 실물에서 통했다**(PragmaBot RA-L, 단일 시도 80%, 비교 기준은 다른 방법 COME 22%). 단 LTM 100항목 중 96개가 교시용 경험이라 자기 판정 라벨의 몫은 작다(D2). 센서 라벨 원칙의 절대 근거도, 반대 근거도 아니다. 센서 술어가 못 다루는 과제(변형 물체)에선 (b)등급이 늘어 메모리 재료가 줄어든다.
- **큰 모델은 메모리를 덜 쓴다**(ExpWeaver) / **Astra가 꺼낸 기억을 무시할 수 있다**(PragmaBot 실패 사례).
- **Kintsugi식 rules-only가 충분하면** "빠른 결정 모델이 왜 필요한가" 반론(v3/07) → B7로 정면 측정.
- 선행: 경험 → typed 규칙 컴파일(Kintsugi, AutoRefine, MemCompiler 등, v3/07). 새로움은 **확률 결정 모델(Jev)의 결정 지점에 정확 일치로 붙이고 비열화 게이트로 채택**하는 부분뿐(좁음, plan §4-5).
- GEPA·Training-Free GRPO·Proactive Memory Agent는 로봇 미적용(확인한 범위). Proactive Memory Agent 이득은 약한 행동 에이전트(Sonnet 4.5)에서 컸고 강한 쪽(Opus 4.6)은 +2.4/+2.5 — Astra가 강한 모델이면 이득이 작을 수 있다. BATON·2604.27003은 심사 전.
- **SkillsBench 양면**: 자기 생성 스킬 −8.1~−11.5pp, 사람이 다듬은 스킬 +18.2~+24.8pp. Astra가 만든 교훈·규칙은 "자기 생성" 쪽에 가깝다 → 게이트 없이 넣으면 해로울 수 있다(B9 조건).
- **역량 보존 삭제의 옮김 한계**: 원문은 1995년 CBR(사례가 문제를 "푼다"는 정의가 명확한 설정)이다. 우리 규칙의 coverage를 키 일치로 근사한 것은 접목안이고, 해로운 유일 규칙을 오래 남길 위험이 있다(B10에서 삭제 대신 재게이트로 막음).

## 7. 열린 질문, [결정 필요]
1. [결정 필요] Astra 메모리 주입 방식(4.3 (i)/(ii)/(iii)), 기본 제안 (iii).
2. [결정 필요] 로컬 학습 모델(예: Robo-Dopamine 8B) 허용 여부(plan [결정 필요] 9) — 허용하면 MemCompiler식 학습 컴파일러가 비교 조건에 들어온다.
3. Jev "필요할 때만" 재질의(1·2위 확률 차가 작을 때 규칙 붙여 다시 묻기)를 M4 겹침 호출과 합칠지(v3/03 제안 8). Jev 보정 E1 전에는 끔.
4. 게이트 비용: 규칙 하나당 재생 + 새 시드 롤아웃 몇 편이 필요한가(Zetta는 과제당 개발 시드 50).
5. 교훈 항목 언어: 영어(Jev·Astra 공통 규칙, plan §1).

## 8. 확인 못 한 것
- 2505.16067: D2 검증이 ACL Anthology 페이지를 열어 확인했고, 열별 지표(RegAgent SR, EHRAgent ACC, AgentDriver SR, CIC-IoT ACC)도 확인됐다.
- 2607.08716 표 1·2: D2 검증 값(Opus 4.6 +2.4/+2.5, micro Always inject +0.3p)만 옮겼다. 나머지 셀은 옮기지 않았다.
- GEPA, ACE, Training-Free GRPO, Memento의 본문 수치(초록만). Memento(2508.16153, GAIA 검증 87.88% Pass@3, 사례 메모리 OOD +4.7~9.6pp)는 표에 넣지 않았다(학회 미확인, 신경망 사례 선택기 학습 포함).
- 2606.29774(개념 중심 로봇 메모리)의 수치와 학습 여부.
- "메모리가 로봇 반복 조작에서 예산 맞춘 기준보다 나은가"를 잰 연구: 찾지 못했다. 검색어: "agent memory hurts performance repeated embodied tasks experience retrieval negative transfer", "robot manipulation LLM planner experience memory lessons from failures across episodes training-free". 부재를 주장하지 않는다.
- 스타·인용 수(API 금지).
- Aamodt·Plaza 1994 원문은 읽지 않았다(D4 검증 §4). Smyth·Keane 1995는 D4 검증이 원문 PDF로 확인했다. TLM·MemoPilot은 D4 검증의 학회 목록 확인 범위만.
