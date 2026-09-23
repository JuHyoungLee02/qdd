# D4-cross-field 원문 검증 (00-interfaces §14가 기대는 출처)

작성: 2026-09-24, 독립 검증 에이전트. 대상: `docs/design/D4-cross-field.md`와, 그 문서를 반영한 `00-interfaces.md` §14·`plan.md` §7 마지막 항목.
판정: **맞음** / **정정 필요**(사실이 틀림) / **조건 보완**(사실은 맞지만 조건·범위가 빠짐) / **학회 미확인**.
다른 파일은 고치지 않았다.

## 0. 확인 방법
- arXiv abs 17편, arXiv html 본문 11편(2602.21702, 2603.20356, 2608.03091, 2601.08444, 2602.09902, 2604.23577, 2509.22984, 2602.14849, 2503.11951, 2511.02603, 2305.11860). 요청 간격 2초 이상.
- 공식 학회·출판 페이지: PVLDB 18권 목록(vldb.org), PLDI 2025 논문 페이지, ACL Anthology(2024.naacl-long, 2023.emnlp-main, 2026.acl-industry 권 목록), PMLR 267권 목록, ICML 2025·2026 / ICLR 2026 공식 virtual 목록 JSON, RecSys 2026 accepted contributions, NeurIPS 2025 ER 워크숍 페이지 + OpenReview 노트 검색 2회, GDC Vault 1025331, SIGGRAPH history의 Bollo 2017 Talk PDF 원문, IJCAI 1995 목차 + Smyth·Keane PDF 원문, doi.org 해석 2회.
- Semantic Scholar batch 1회(17편): 인용 수는 D4 기재값과 모두 일치(76, 25, 0, 60, 10, 0, 55, 156, 4, 2, 2, 1, 5, 0, 3, 47, 1).
- ACM DL 페이지는 403으로 막혀 PLDI 쪽수(601–626)는 확인 못 함.
- arXiv 검색 API, GitHub API, WebSearch는 쓰지 않았다.

## 1. 출처별 판정 표

| # | 출처 | 제목·첫 공개(기간) | 학회(공식 페이지) | D4 주장 대비 원문 (위치) | 판정 |
|---|---|---|---|---|---|
| 1 | SagaLLM 2503.11951 | 제목 일치. v1 2025-03-15 → **기간 밖(8일)**, D4 표기 맞음 | **PVLDB 18권 12호, pp. 4874–4886** (vldb.org 18권 목록), DOI 10.14778/3750601.3750611 (doi.org → ACM로 연결). 12호의 앞뒤 논문(SiriusBI, Azure Cosmos DB 등)으로 보아 산업 트랙일 가능성이 있음(추정, 트랙 미확인) | "사가 패턴 + 지속 메모리 + 자동 보상 + 독립 검증 에이전트" = 초록 그대로. 수치 미확인이라는 D4 표기도 맞음 | **맞음** (S2만 보고 적은 학회 표기가 이제 공식 목록으로 확인됨) |
| 2 | Atomix 2602.14849 | 제목 일치. 2026-02-16(v2 2026-05-29), 기간 안 | 학회 표기 없음(무학회 맞음). 코드는 mpi-dsg | 효과 분류(본문 §2): Reversible(즉시 실행, 중단 시 **역방향 의존 순서로 보상**), Bufferable(커밋 때 적용), **Irreversible-gated(이메일·송금·"physical actions", 커밋 때만 방출)**. 초록 인용문 일치. 본문: "Saga compensation helps only when every externalized effect is reversible… cannot prevent an irreversible send" | **맞음**. 오히려 원문이 "물리 행동"을 비가역 게이트 대상으로 직접 꼽아 §14-3을 더 강하게 뒷받침한다 |
| 3 | Half Pound Filter 2602.21702 | 제목 일치. 2026-02-25, 기간 안, 12쪽 | 무학회 | **Table 1** 원문: XFade 0.0259 / DeadMan 0.0054 / Bollo 0.0017 / HPF 0.0032 / XFade Auto 0.0215 / Bollo Auto **0.0005** / HPF Auto 0.0006. NPSS 0.0409~0.0464. 표에 없는 D4 생략값: Raw 0.0000/0.0445, GB-HPF 0.0019, DeadMan Auto 0.0035, GB-HPF Auto 0.0014. "LaFAN1 예시 1개" 맞음. 자동 트리거: 도함수(저크까지) 경계를 어길 때만 켜고, 목표와 속도 차가 크면 유지(§5) | **맞음**. 덧붙일 반대 근거: 같은 논문 §1이 관성화가 "빠른 고주파 움직임에서 과도한 평활화, 빠르게 바뀌는 움직임에서 overshoot"를 낼 수 있다고 적음 |
| 4 | 관성화 원출처 (Bollo) | 기간 밖, 기초 문헌 | **SIGGRAPH 2017 Talks** "High Performance Animation in Gears of War 4", DOI 10.1145/3084363.3085069 (SIGGRAPH history PDF 원문 확인). **GDC 2018** "Inertialization: High-Performance Animation Transitions in 'Gears of War'", David Bollo (GDC Vault 1025331 확인) | 기전: 전환 시작 때 원본 속도와 원본·목표 자세 차를 기록 → **5차 다항식**이 그 차·속도에서 시작해 0으로 수렴, 목표 애니메이션에 더함, 초기 가속도 조절로 overshoot 방지(Talk §2) → D4 설명 맞음. **"약 60% 절감"은 GDC 소개문에 없다.** GDC 소개문은 "significant performance boost"뿐이다. 60%는 **SIGGRAPH 2017 Talk §2**: 12 µs 대 30 µs(원본 시퀀스 20 µs + 블렌드 10 µs), **원본 애니메이션이 하나뿐인 가장 단순한 경우**, Xbox One | **정정 필요** (수치의 출처 위치와 조건) |
| 5 | Type-Constrained Code Generation 2504.09246 | 제목 일치. 2025-04-12, 기간 안 | **PLDI 2025 Research Papers** (pldi25.sigplan.org 논문 페이지: Mündler, He, Wang, Sen, Song, Vechev), DOI 10.1145/3729274 (S2: Proc. ACM Program. Lang.). 쪽수 601–626은 ACM 403으로 미확인 | 초록: HumanEval·MBPP, TypeScript, 컴파일 오류 절반 이상 감소, 합성·번역·**수리** 과제 기능 정확도 향상, 30B 넘는 오픈 가중치 모델 포함. 기전 = 접두부 오토마타 + 거주 가능 타입 탐색 → 디코딩 중 제약 | **맞음** (쪽수만 미확인) |
| 6 | Agentproof 2603.20356 | 제목 일치. 2026-03-20, 기간 안 | 무학회 | 18개 작성자 제작 워크플로, 27% 구조 결함, 55% 사람 승인 정책 위반, 15개 정책이 모두 7형식 DSL 안, 5,000 노드까지 1초 미만, "유병률 연구 아님" = 초록 일치. DFA 컴파일, 그래프×DFA 곱(정적) + 사건열(실행 중) 맞음. **다만 7형식은 본문 DSL 절에 모두 나온다**: (1) Forbidden `G !a` (2) Implication-future `a -> F b`(a가 다시 오기 전에 b) (3) Until (4) Bounded response `a -> F[<=k] b` (5) Response chain (6) **Conjunction** (7) **Disjunction**. 부록 B는 BNF 전체다. 저자: 1저자 Luleå 공대, 나머지 3명 독립 연구자 | **정정 필요** (경미: "6·7번은 부록 B, 안 읽음" → 본문에 AND/OR로 있음. "독립 연구자" → 대학 1명 + 독립 3명) |
| 7 | RecSys 2026 2608.03091 | arXiv 제목 "Position Bias Undermines Preference Consistency in Listwise LLM-Based Reranking", 2026-08-04, 기간 안 | RecSys 2026 공식 목록에는 **Short paper**로, 제목은 **"Position Bias Induces Inconsistent Rankings in Listwise LLM-based Recommendation"** (Bito, Ren, He). arXiv 본문 메타데이터에 DOI 10.1145/3773078.3831801 있음 | 초록·결론 원문은 **"does not necessarily restore"**. D4의 "복원되지 않는다"는 단정이 너무 강하다. 결정적 채점: 후보 표지 토큰 logprob으로 순위를 뽑아 결정적 → 변동은 순열 때문뿐(§실험 설정). 모델 Llama-3.2-3B / Mistral-7B / Qwen2.5-7B, MovieLens-32M·Amazon Books. **Table 1: Bootstrapping(무작위 순서 3회 + Borda 집계, Hou 외 2024)이 zero-shot보다 PPI·GPI를 낮춘다**(예: Llama-3B MovieLens PPI 0.4775→0.2992, GPI 0.1149→0.0827). 가장 좋은 것은 SGS(한 개씩 뽑고 다시 섞기, 순차 호출 25회) | **정정 필요**: (a) 학회 등급 "본 학회 HIGH" → **Short paper**, 공식 제목 다름 (b) 단정 표현 (c) D4 §13의 "순열 집계가 복원한다는 수치는 기간 밖 NAACL 2024뿐"은 틀림. **기간 안 근거가 바로 이 논문 Table 1에 있다**(줄어들지만 없어지지는 않음) |
| 8 | Permutation Self-Consistency 2310.07712 | 제목 일치. 2023-10-11, 기간 밖 | **NAACL 2024 long** (ACL Anthology 2024.naacl-long.129) | 순서를 여러 번 섞음 → 중심 순위(Kendall 거리) 집계, GPT-3.5 기준 7–18%, LLaMA-2-70B 8–16% 향상(최대치, 초록) | **맞음** |
| 9 | Adaptive-Consistency 2305.11860 | 제목 일치. 2023-05-19, 기간 밖 | **EMNLP 2023 main** (2023.emnlp-main.761) | §3 원문 확인: Dirichlet 기준 = P(현재 최다 답이 최다로 남음 \| 표 수) > C_thresh. **실험 기본값은 Beta 근사**: 1위·2위 표 수만 쓰는 Beta(v1+1, v2+1), **C_thresh = 0.95**(§4 Hyperparameters). 초록: 표본 예산 최대 7.9배 감소, 정확도 평균 하락 0.1% 미만, 17개 데이터셋 | **맞음** (단, §2의 설계 조건 보완 참고) |
| 10 | CGES 2511.02603 | 제목 일치. 2025-11-04(v2 2026-06-09), 기간 안 | **NeurIPS 2025 Efficient Reasoning(ER) Workshop Spotlight** (OpenReview 노트 pNuj4yTsRb, venue 필드). arXiv판은 확장판 | 5개 벤치 평균 호출 16.0→6.7(−58%), 자기 일관성 대비 0.4%p 이내, 보정 가정 + 잡음 신뢰도 가정("directional drift" 조건 아래) 보장 = 초록 일치 | **맞음** |
| 11 | RouteNLP 2604.23577 | 제목 일치. 2026-04-26, 기간 안 | arXiv 주석과 **OpenReview venue "ACL 2026 Industry Track Poster"**(노트 H9KBJXHoA8)로 확인. **ACL Anthology 2026.acl-industry 권 목록(155편)에는 이 제목이 없다**(확인 시점 2026-09-24) | §3.2 원문: conformal risk control로 임계값 **초기화**, "보장은 질의별이 아니라 주변(marginal), 교환 가능성 필요, 분포 이동에서 깨짐" = D4 맞음. 빠진 조건: **작업·단계당 보정 500개**. 부록 D: 위반율 n=100에서 7.2%(CI 3.4–14.4%), n=250 5.8%, n=500 4.2%(CI 상한 6.6%로 5% 목표 초과 가능). 도메인 이동 때 위반 8.1%(§5). 8주 파일럿은 **A/B 없는 그림자 배치**이고 고객 상담 한 분야뿐(Limitations) | **조건 보완** |
| 12 | Routing, Cascades, and User Choice 2602.09902 | 제목 일치. 2026-02-10, 기간 안 | **ICLR 2026** (ICLR 2026 공식 virtual 목록에 있음) | 원문 문장(초록): "in nearly all cases, the **optimal routing policy** involves a **static policy with no cascading** that depends on the expected utility of the models to the user." 여기서 "최적"은 **공급자 최적**(서비스 비용 + 사용자 이탈 벌점 최소)이다. 모형은 **모델 2개(표준·추론) + 다시 묻거나 포기하는 사용자**의 슈탱켈베르크 게임이다. 가정: 성공 i.i.d., 사용자가 공급자 정책을 관찰, 정상(stationary) 이탈 정책(§결론). "정적" = **실패 뒤 더 강한 모델로 올리지 않는(no escalation)** 1회 라우팅. 캐스케이드는 두 모델의 사용자 순가치가 갈리는 좁은 구간에서만 최적(서론 기여 항목, Thm 4–5) | **정정 필요**: §14의 "정적 규칙이 대개 최적"은 원문 뜻과 다르다(§3 참고) |
| 13 | Inter-Cascade 2509.22984 | 제목 "From Deferral to Learning: Online In-Context Knowledge Distillation for LLM Cascades". 2025-09-26, 기간 안 | 심사 중(arXiv 주석) | 초록 수치 +33.06% / +6.35% / −48.05%(모두 최대치) 맞음. 임계값: **§2, Algorithm 1**(Jung 외 2025의 **fixed-sequence testing**, 위험 허용 α와 오류 δ). §3.2는 실험 설정에서 그 적용일 뿐이다. 신뢰도 점수 = **정규화 토큰 확률**(logprob 필요). 효과는 구조 변형이 많은 GSM 계열에서 크고, 변형이 없는 NASA-History에서는 작다(정확도 +0.76%, 강한 모델 호출 −15.5%, §3.3) | **조건 보완** (절 위치, logprob 전제, "conformal"이 아니라 고정 순서 검정) |
| 14 | TabGR 2601.08444 | 제목 "Beyond Linearization: Attributed Table Graphs for Table Reasoning". 2026-01-13(v2 2026-08-27), 기간 안 | 무학회 | Table 3(순서 무관 질문만 섞음, 시드 3): **TabGR 0.1~0.7%, TabGR† 0.5~1.3%** 하락. 기준 방법 중 Table-Critic은 9.7~18.7%로 크게 떨어지지만, **RoT는 WikiTQ 4.1~6.2%, TabFact 0.9~1.1%**로 크지 않다. Table 5 절제: QG-PPR 제거 80.1→79.5(WikiTQ, 전체 표). 더 직접적인 근거는 부록 **Table 12**: QG-PPR을 빼고 섞으면 WikiTQ 하락이 5.8~7.1%(뺀 판) 대 0.1~1.3%(넣은 판). TabFact에서는 1.0~1.5% 대 0.5~0.7%로 차이가 작다 | **조건 보완** ("0.1~0.7%"는 TabGR 전체 판만 해당, "기준 방법 크게 하락"은 Table-Critic만. E3 조건 근거로는 Table 12를 인용해야 함) |
| 15 | 2511.10876 | 제목 일치. 2025-11-14, 기간 안 | **Information and Software Technology** (DOI 10.1016/j.infsof.2026.108133 → doi.org가 Elsevier linkinghub S0950584926001229로 연결). S2만 보던 것이 확인됨 | 최대 82.849% 포괄, 최대 F1 95.957%, AUC 93.669%, ERTMS/ETCS 사례 1건 = 초록 일치 | **맞음** |
| 16 | 조건부 CTM 2602.13848 | 제목 "Testing For Distribution Shifts with Conditional Conformal Test Martingales". 2026-02-14, 기간 안 | 무학회 | 고정 기준 집합, anytime-valid 1종 오류, 점근 검정력 1, 탐지 지연 한계, 기존 CTM의 오염 문제 = 초록 일치 | **맞음** |
| 17 | TLM 2505.20633 | "Test-Time Learning for Large Language Models", 2025-05-27, 기간 안 | **ICML 2025, PMLR 267:24823–24849** (PMLR 목록) | 입력 perplexity 최소화 + LoRA, 가중치 갱신 → API 불가 판단 맞음 | **맞음** |
| 18 | MemoPilot 2606.08656 | "From Player to Master: …", 2026-06-07, 기간 안 | **ICML 2026** (ICML 2026 공식 virtual 목록에 있음) | multi-turn GRPO로 메모리 갱신기 학습, Elo LHE 1762 / RPS 1590 = 초록 일치 | **맞음** |
| 19 | Smyth·Keane 1995 | "Remembering To Forget: A Competence-Preserving Case Deletion Policy for Case-Based Reasoning Systems", 기간 밖 | **IJCAI 1995**, 1권 p.377 (ijcai.org 목차, PDF Papers/050) | 원문: coverage(사례가 풀 수 있는 문제 집합)·reachability(문제를 풀 수 있는 사례 집합). 사례 4분류 pivotal / spanning / support / auxiliary. pivotal을 지우면 역량이 되돌릴 수 없게 줄어든다. 다른 사례가 덮는 auxiliary부터 지운다 | **맞음** |

**맞음 12 / 정정 필요 4 (4·6·7·12) / 조건 보완 3 (11·13·14) / 학회 미확인 0.** RouteNLP는 OpenReview에서 채택이 확인되지만 Anthology 목록에는 아직 없다.

## 2. 00-interfaces §14가 출처를 잘못 쓰거나 조건이 빠진 곳

1. **§14 "실험 조건 추가"의 E-M8a: "ICLR 2026 2602.09902 '정적 규칙이 대개 최적' 반대 근거"는 틀린 인용이다.**
   - 원문의 "static"은 **실패해도 더 강한 모델로 올리지 않는(no cascading) 1회 라우팅**이다. "최적"은 사용자 포기 벌점이 있는 2모델 게임에서의 **공급자 비용** 기준이다.
   - 우리 E-M8a의 "정적 규칙(트리거별 고정 부름/안 부름)"과 BRACE식 동적 문지기의 대비는 원문이 다루지 않는다.
   - 굳이 옮기면 이 결론은 우리 불변식인 "실패하면 항상 Astra"(= 실패 시 상향 캐스케이드)에 반대하는 쪽이다. 다만 가정(공급자 비용, 사용자 이탈, i.i.d. 성공)이 우리와 맞지 않아 그 방향 근거로도 약하다.
   - 권장 문구: "2모델 라우팅 게임에서 공급자 최적 정책은 대개 캐스케이드 없는 정적 라우팅(ICLR 2026). 가정이 달라 방향만 참고." E-M8a의 정적 규칙 조건 자체는 합리적인 절제 조건이므로 유지해도 된다. 바꿀 것은 근거 표기다.
2. **§14-1 M3 순서 돌리기 근거 "NAACL 2024 기간 밖 + RecSys 2026"**:
   - RecSys 2026은 **Short paper**이고 공식 제목이 다르다.
   - RecSys는 순열 자기 일관성을 제안하지 않았다(진단 논문). 대신 Table 1에서 **무작위 순서 3회 + Borda 집계(Bootstrapping)가 PPI·GPI를 줄이지만 없애지는 못함**을 보였다. 이것이 C3''에 대한 **기간 안 직접 근거**다. D4 §13의 "NAACL뿐"은 정정해야 한다.
   - 또 원문은 logprob으로 결정적 순위를 뽑았다. 결정적 Jev와 조건이 비슷해 C3''를 설계할 때 참고가 된다.
3. **§14 E-M4 C3'(Adaptive-Consistency식 베이즈 정지)**: 원문 기본값(Beta 기준, C_thresh 0.95)을 그대로 쓰면 **만장일치 표가 최소 4개** 있어야 확정된다.
   - 계산(원문 식에서 우리가 직접 계산, 원문 수치 아님): v2=0이면 P = 1 − 0.5^(v1+1). v1=3이면 0.9375, v1=4이면 0.969.
   - T_c 0.33 s라면 약 1.3 s이고, LocalAgreement-2보다 늦다. D4 §13이 걱정한 "스텝당 표 약 3개"에서는 **한 번도 확정되지 않는다.**
   - 따라서 C3'는 C_thresh를 명시하거나(예: 0.9면 표 3개), "Beta 대 Dirichlet"를 명시해야 한다.
4. **§14 M6 "PLDI 2025 타입 제약 생성의 API판"**: 원문은 **디코딩 중 제약**만 평가했다. 사후 타입 검사 + 오류 되먹임의 효과는 원문에 없다(D4 §13이 이미 인정). §14 문장만 읽으면 원문이 사후 검사판을 보인 것처럼 읽히므로 "(접목안, 원문 미평가)"를 붙여야 한다.
5. **§14 M8 T3b "conformal risk control(RouteNLP)"**: 원문 보장이 성립하는 조건은 교환 가능성과 **작업·단계당 보정 약 500개**다. n=100에서는 위반 7.2%, 도메인 이동에서는 8.1%다. E-M8b의 기록 사건 수가 이보다 작으면 원문 조건 밖이다. 또 원문은 "초기화 + 운영 감시"로 쓰라고 권한다.
6. **§14-5 M5 관성화**: 기전 설명은 원문과 맞는다. 다만 반대 근거가 두 가지 빠졌다.
   - (a) HPF 논문 §1이 관성화의 과평활·overshoot 한계를 명시한다.
   - (b) 60% 성능 수치는 연산 비용이지 궤적 품질이 아니다. 조건은 Xbox One, 원본 1개.
   - 우리에게 의미 있는 품질 근거는 HPF Table 1 예시 1개뿐이다(D4 표기 LOW 유지).
7. **§14-3 M9 사가·Atomix**: 인용이 원문과 맞는다. Atomix가 "physical actions"을 비가역 게이트로 직접 분류하므로 오히려 근거를 올려 적어도 된다. SagaLLM 학회는 PVLDB 18(12)로 확정됐다.

## 3. 정정 목록 (한 줄씩)
- 관성화 "약 60% 절감(GDC 소개문)" → 출처는 **SIGGRAPH 2017 Talk §2**(12 µs 대 30 µs, 원본 애니메이션 1개일 때). GDC 소개문에는 수치가 없다.
- Agentproof "6·7번 형식은 부록 B, 안 읽음" → 본문에 **Conjunction·Disjunction**으로 나온다. "독립 연구자" → 1저자 Luleå 공대 + 독립 연구자 3명.
- RecSys 2026 2608.03091 → **Short paper**, 공식 제목 "Position Bias Induces Inconsistent Rankings in Listwise LLM-based Recommendation". "복원되지 않는다" → "반드시 복원되지는 않는다(does not necessarily restore)".
- D4 §13 "순열 집계 근거는 기간 밖 NAACL 2024뿐" → RecSys 2026 Table 1의 Bootstrapping(3회 섞기 + Borda)이 PPI·GPI를 줄인다(예: 0.4775→0.2992). 기간 안 근거다.
- 00-interfaces §14 E-M8a "정적 규칙이 대개 최적(ICLR 2026)" → 원문은 "2모델·사용자 이탈 게임에서 **공급자 최적** 라우팅은 거의 항상 **캐스케이드 없는** 정적 정책". 트리거별 고정 규칙 대 동적 문지기 비교의 근거가 아니다.
- RouteNLP → 채택은 OpenReview venue로 확인되지만 ACL Anthology 2026 Industry 목록에는 없다. 보장 조건 추가: 보정 n≈500/작업·단계, 도메인 이동 때 위반 8.1%, 파일럿은 그림자 배치.
- Inter-Cascade 임계값 "§3.2" → **§2 Algorithm 1**(Jung 외 2025, fixed-sequence testing). 신뢰도는 토큰 확률이라 logprob이 필요하다.
- TabGR "하락 0.1~0.7%" → TabGR 전체 판만 해당(TabGR†는 0.5~1.3%). "기준 방법 크게 하락"은 Table-Critic만 해당(RoT의 TabFact 하락은 0.9~1.1%). 순서 강건성의 직접 근거는 부록 Table 12(QG-PPR 제거 시 WikiTQ 5.8~7.1%).
- (설계 조건) E-M4 C3' Adaptive-Consistency → 원문 기본 C_thresh 0.95에서는 만장일치 4표가 필요해 스텝당 3표로는 확정이 불가능하다. 임계값을 명시해야 한다.
- (표기) M6 "PLDI 2025 API판" → 사후 검사 + 되먹임은 접목안이고 원문은 평가하지 않았다.

## 4. 확인 못 한 것
- PLDI 논문 쪽수 601–626(ACM DL 403).
- SagaLLM의 VLDB 트랙(연구/산업). 권·호·쪽만 확인했다.
- RouteNLP가 Anthology에 없는 이유(게재 지연인지 철회인지).
- ESC(ICLR 2024), Flexible Paxos, Sagas 1987, Aamodt·Plaza 1994, Dwyer 1999, Adriansyah 2011: 이번 우선순위 밖이라 원문을 보지 않았다.
