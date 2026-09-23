# D4. 아직 캐지 않은 분야에서 모듈별 최고 기전 1개씩 (교차 분야 조사)

작성: 2026-09-24 (단계 2, 조사 에이전트 D4). 규칙: `docs/design/README.md`, 정본 `00-interfaces.md`, `plan.md` §6.
[사용자] "LLM이나 VLM 자체에서도 거기에서의 방법론이 아직 로봇에 적용되지 않은 것들"까지 모듈 단위로 최고를 찾는다. 이 문서는 **기존 M1~M10 문서가 아직 보지 않은 분야**만 다룬다(겹침 확인: 설계 폴더·v3 보고서에서 LLMCompiler, rerank/listwise, saga/compensat, case-based, cascade/routing, table serial, typed hole, process mining/conformance, inertialization, martingale 검색 → 기존 언급 없음. 예외: Memento는 M10 §8에 "표 밖", TOON은 M1에 이미 있음).

표기: **원문** = 논문이 한 것. **접목안** = 우리 제안(원문 아님). 기간 = arXiv 첫 공개 2025-03-23 이후면 "기간 안". 인용 수는 Semantic Scholar batch 1회(2026-09-24 측정). 신뢰도 HIGH/MED/LOW는 v3 README 규칙.

---

## 0. 한 줄 결론 (모듈별)

| 모듈 | 새로 본 분야 | 가져올 기전 1개 | 근거 신뢰도 | 설계 변경 |
|---|---|---|---|---|
| M1 | 표 QA 직렬화 | 질문 기준 정렬(질문 앵커에서 개인화 PageRank로 줄 순서 정함) + 삼중항 표기 | LOW (TabGR, 무학회, 인용 5) / 형식 비교는 TABVERSE(심사 중) | 작음: 후보 A에 "줄 순서 규칙"을 E3 조건으로 추가 |
| M2 | 에이전트 워크플로 정적 검증 / 컴파일러 IR | 계획(단계 그래프)을 7가지 시간 논리 패턴 DSL → DFA로 컴파일해 **넘기기 전 정적 검사 + 실행 중 같은 DFA로 감시** | 기전은 기초 문헌(명세 패턴 ICSE 1999, 런타임 검증), 기간 안 사례 Agentproof LOW(인용 10) | 예: 세션 계약 수신 검사 게이트 + H5를 DFA 감시로 통일 |
| M3 | 추천·재순위 LLM 목록 순위 | 보기 **순서 섞기(순열) 후 집계** — 겹친 호출마다 순서를 바꿔 위치 편향을 상쇄 | HIGH(RecSys 2026 진단) + 기초 문헌(NAACL 2024, 기간 밖, 인용 55) | 예, 단 [결정 필요]: "같은 질문끼리만" 규칙과 충돌 |
| M4 | 자기 일관성 조기 종료 / 분산 합의 | 표 수 기반 **베이즈 안정성 정지 규칙**(Dirichlet-다항: "지금 1위가 끝까지 1위일 확률 ≥ 기준"이면 확정) | 기초 문헌 Adaptive-Consistency(EMNLP 2023, 인용 156) + 기간 안 CGES(NeurIPS 2025 워크숍, 인용 4) | 예: C3 합의 규칙의 대안 조건 추가(확률 게이트 아님 — 표 수만 씀) |
| M5 | 게임 캐릭터 애니메이션 전환 | **관성화(inertialization)**: 전환 순간 옛·새 궤적을 섞지 않고, 위치·속도 차이(오프셋)만 감쇠시켜 새 궤적에 더함 | 기초 문헌(Bollo SIGGRAPH 2017 Talk, GDC 2018) + 기간 안 비교표(Half Pound Filter, LOW, 인용 0) | 예: "모드가 다르면 평균하지 않는다" 경우의 전환 처리를 관성화로 명시(L2·L3 사이) |
| M6 | 프로그램 합성·타입 제약 생성 | **타입이 있는 구멍(typed hole)**: 생성 스킬 코드의 `jev_choice` 자리를 열거형 타입으로 두고 타입 검사 통과만 실행 | HIGH(PLDI 2025, 인용 60) — 단 디코딩 제약 자체는 API 모델에 못 씀 | 예: 생성형 (b)에 타입 검사 게이트 + 오류 되먹임 수리 |
| M7 | 프로세스 마이닝 적합성 검사 | **정렬(alignment) 기반 적합성 검사**: 관측 사건열 대 계획 모델을 맞춰 "모델만 이동(건너뜀)/로그만 이동(계획 밖 사건)" 편차를 셈 | 기초 문헌(van der Aalst 계열) + 기간 안 LLM 결합 사례(Information and Software Technology 2025, 인용 0) | 예: M7에 순서 편차 채널, M9 재개 지점 계산과 공유 |
| M8 | LLM 캐스케이드·라우팅 | **보정된 위임 임계값(conformal risk control) + 위임 결과를 약한 모델의 문맥 전략으로 저장(Inter-Cascade)** | RouteNLP ACL 2026 Industry(인용 2), Inter-Cascade 심사 중(인용 1), 반대 이론 ICLR 2026(인용 2) | 부분: E1 뒤 T3b 게이트 임계값 설정법만. 실패 트리거는 그대로 무조건 호출 |
| M9 | 데이터베이스 사가·에이전트 트랜잭션 | **보상 행동(compensation) + 되돌릴 수 없는 효과는 확정 전 방출 금지(Atomix)** | 기초 문헌 Saga(1987) + SagaLLM(VLDB 2025, 인용 76, 2025-03-15 → 기간 밖 8일) + Atomix(무학회, 인용 25) | 예: 스킬 단계에 가역/비가역 표지, M4 확정 규칙을 비가역 스텝에서 강화 |
| M10 | 사례 기반 추론(CBR) / 동결 LLM 테스트 시점 학습 | **CBR 4R의 Revise(검증 뒤에만 Retain) + 사례 집합 유지(역량 보존 삭제)** | 기초 문헌(Aamodt·Plaza 1994, Smyth·Keane 1995) + 기간 안 리뷰(인용 22, LOW) | 작음: 삭제 규칙에 "역량 보존" 조건을 비교 조건으로 |

---

## 1. 조사 방법과 한계
- arXiv 검색 API 응답 성공 50회(5.5초 이상 간격). 이와 별도로 python urllib 요청 28회가 HTTP 406으로 거절돼 curl로 다시 보냈다(간격은 지킴). 검색어는 §12 목록.
- WebSearch 2회(Type-Constrained PLDI 2025 확인, inertialization 원출처 확인). Semantic Scholar batch 1회(21편). GitHub API 0회.
- 초록(arxiv abs) 20편, 본문(arxiv html) 해당 절 grep 9편: 2608.03091, 2511.02603, 2603.20356, 2606.09578, 2601.08444, 2602.21702, 2604.23577, 2509.22984 (+ PLDI 쪽은 초록·학회 페이지만).
- 약 60분 제한 → **모듈당 기전 1개**만 깊이 보고, 나머지 후보는 "대안"으로만 적는다. 수치는 본문에서 확인한 것만 적고 조건을 붙였다.
- 기초 문헌(기간 밖)은 원문을 이번에 다시 읽지 않았다. 서지 정보는 기억과 이번 검색 결과(인용한 논문의 참고문헌 목록)로만 확인 → §11에 표시.

---

## 2. M1 상태 → 텍스트 : 표 QA 직렬화

### 후보 표
| 이름 | 분야 | 어디서 최고였나 (조건) | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| TabGR — Attributed Table Graph + QG-PPR (2601.08444) | LLM 표 추론 | 초록: 여러 표 추론 벤치에서 "최대 9.7%" 향상(최대치). 본문 Table 3: 행·열을 섞었을 때(순서 무관 질문만, 시드 3) 기준 방법은 크게 떨어지고 TabGR 하락은 0.1~0.7%. Table 5 절제: ATG 제거가 가장 큰 하락, QG-PPR 제거는 "작은 하락" | LOW (arXiv만, 인용 5, v2 2026-08 개정, 학회 표기 없음) | 2026-01-13, 기간 안 | 예 | 아니오 |
| TABVERSE (2606.09578) | LLM/VLM 표 형식 | 같은 내용을 HTML/Markdown/LaTeX/이미지로 맞춘 700문항: 구조 텍스트 > 이미지, "HTML is often the most robust text format"(초록·서론 문장, 모델·과제별 차이 큼) | LOW-MED (ARR 2026-05 제출, 인용 0) | 2026-06-08, 기간 안 | 예 | 아니오 |

### 원문 (TabGR)
- 표를 선형화하지 않고 (행, 열, 값) 속성 삼중항 그래프로 둔다. 질문에서 정확히 일치하는 셀을 앵커로 잡고, **질문 기준 개인화 PageRank(QG-PPR)로 삼중항을 재순위**해 관련 높은 것을 앞에 둔다 → "lost-in-the-middle" 완화. 본문: "our QG-PPR mechanism prioritizes the question-relevant triples regardless of their initial positions".

### 우리 접목안
- 후보 A(객체 ID 목록 + 관계 + 술어)의 **줄 순서**를 고정 순서가 아니라 "질문 앵커(목표 물체 ID, 그리퍼, 결정 지점이 참조하는 술어)에서 장면 관계 그래프 위 개인화 PageRank 점수 순"으로 정한다. 계산은 코드(수십 노드, 1ms 이하 예상 — 미측정).
- 제약: 한 `JevCall`은 여러 질문이 **한 상태를 공유**한다(00-interfaces §2). 질문마다 순서를 바꿀 수 없으니 앵커 = 결정 질문 H개 + 감시 질문이 참조하는 ID의 합집합.
- 형식(HTML/JSON/줄 표)은 M1 기존 결론(형식 효과 작음, FloorplanQA ±3%p)과 TABVERSE "HTML이 자주 가장 견고"가 약간 어긋난다. TABVERSE는 표 QA(행·열 격자)이고 우리 상태는 격자가 아니므로 형식 결론은 옮기지 않는다.

### 설계 변경: 작음
- E3에 조건 1개 추가 제안: A-고정순서 대 A-QG-PPR순서(같은 내용). 근거가 LOW라 기본값으로 올리지 않는다. 변환 방법 선택은 사용자 몫(00-interfaces §11.3) — 이 조건은 비교 자료일 뿐.

---

## 3. M2 Astra → Jev 넘기기 : 컴파일러 IR·계획 DSL·정적 검증

### 후보 표
| 이름 | 분야 | 어디서 최고였나 | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| Agentproof (2603.20356) | LLM 에이전트 워크플로 검증 | 작성자가 만든 18개 워크플로에서 27% 구조 결함(막다른 노드, 도달 불가 출구), 55% 사람 승인 정책 위반. 15개 시간 정책 모두 7형식 DSL 안에 들어감, 5,000 노드까지 1초 미만(초록). 원문 스스로 "유병률 연구가 아니다"라고 한정 | LOW (독립 연구자, 무학회, 인용 10) | 2026-03-20, 기간 안 | 예(검증기, 학습 없음) | 아니오 |
| 명세 패턴 + 런타임 검증 (Dwyer 외 ICSE 1999; LTL→오토마타 감시, Bauer·Leucker·Schallhart TOSEM 2011) | 형식 검증 | 기초 이론 | 기간 밖, 기초 문헌 | 기간 밖 | 예 | 로봇 LTL 계획에는 있음(우리 Jev 계약 검사로는 미확인) |
| LLMCompiler (2312.04511) | LLM 병렬 함수 호출 | ReAct 대비 지연 최대 3.7배↓, 비용 최대 6.7배↓, 정확도 최대 약 9%↑(모두 최대치) | HIGH (ICML 2024, 인용 217) | 기간 밖(2023-12) | 예 | 로봇 적용 있음 여부 미확인 |
| MermaidFlow (2505.22967) | 워크플로 생성 | Mermaid 그래프를 "검증 가능한 IR"로 두고 진화 연산자가 의미 정확성을 보존 | LOW (무학회, 인용 미측정) | 기간 안 | 예 | 아니오 |

### 원문 (Agentproof §DSL, 본문 확인)
- 워크플로 그래프를 공통 추상 그래프로 뽑고 6가지 구조 검사(막다른 노드, 도달 불가 출구 등) + **7형식 시간 정책 DSL**: (1) Forbidden `G !a` (2) `a -> F b` (3) Until `a U b` (4) 한정 응답 `a -> F[<=k] b` (5) 응답 사슬 … (나머지 2형식은 부록 B, 이번에 안 읽음). 정책을 **DFA로 컴파일**해 정적으로는 그래프 × DFA 곱으로, 실행 중에는 사건열 위에서 같은 DFA로 검사.

### 우리 접목안
- 세션 계약(M2, 필드는 `phases/entry/exit/invariants` — 00-interfaces §11.1)을 Jev에 넘기기 **전에** 코드가 정적 검사한다: (i) 모든 단계가 `exit`로 도달 가능한가 (ii) 막다른 단계 없음 (iii) 모든 술어가 M1 등록부에 있음 (iv) 결정 지점 id가 M6 고정 id 목록 안. 실패하면 Astra에 **검사기 오류 문장**을 되돌려 고치게 한다(컴파일 오류 되먹임 — 첫 계획(T0)에는 정지가 허용되므로 여기서 1회 수리 왕복은 사용자 원칙과 충돌 없음).
- `forbidden`과 순서 제약을 위 5~7형식 중 하나로만 쓰게 제한 → DFA로 컴파일 → M7 하드 채널 H5(T1 술어만)와 `C_assume`의 실행 중 감시를 **같은 DFA**로 한다. 한정 응답 `a -> F[<=k] b`는 M8 T3a "예상 시간 마감"과 같은 모양이라 한 표기로 합칠 수 있다.
- LLMCompiler식 "단계 사이 의존 DAG + 변수 참조($1)"는 우리 단계 원장이 거의 순차라 이득이 작다고 보아 가져오지 않는다(판단, 미실험).

### 설계 변경: 예
- M2: 계약 수신 검사 게이트(정적 검사 + 오류 되먹임) 추가. M2·M7: `forbidden`/순서 제약 표기를 명세 패턴 부분집합으로 제한. 근거는 기초 문헌(형식 검증) — Agentproof는 보조로만(LOW).

---

## 4. M3 이산 선택 : LLM 목록 순위·재순위

### 후보 표
| 이름 | 분야 | 어디서 최고였나 | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| Position Bias Undermines Preference Consistency in Listwise LLM-Based Reranking (2608.03091) | 추천 재순위 | 진단 논문: 동등한 후보 순열에서 나온 순위를 "유도된 선호 체계"의 관측으로 보고 쌍 불안정(PPI)·전역 비일관(GPI)·출력 일관(LOC) 측정. **"relevance를 높이거나 위치별 노출을 평평하게 해도 안정된 쌍 선호가 복원되지 않는다"**(초록·결론). Figure 2: Llama-3.2-3B, MovieLens-32M에서 목록 길이별 PPI·GPI | HIGH(RecSys 2026 본 학회, DOI 10.1145/3773078.3831801; RMIT; 인용 0 — 공개 직후) | 2026-08-04, 기간 안 | 예 | 아니오 |
| Permutation Self-Consistency (2310.07712) | LLM 목록 순위 | 순서를 여러 번 섞어 순위를 받고 중심 순위(Kemeny)로 집계 | HIGH(NAACL 2024, 인용 55) | 기간 밖, 기초 문헌 | 예 | 아니오(우리 확인 범위) |
| Whole-Pool Setwise / DualEnd (2606.01782) | 문단 재순위 | 긴 문맥 모델이 전체 후보를 한 번에 보고 최선·최악을 동시에 고름: 100개를 직렬 50회(대비 99회) | LOW-MED(4쪽 본문, 인용 0) | 기간 안 | 예 | 아니오 |

### 원문
- RecSys 2026: 순서만 다른 같은 후보 집합에서 LLM의 쌍 선호가 뒤집힌다. 위치 편향을 "노출 평탄화"로 고쳐도 선호 일관성은 안 돌아온다 → **순서 불변성 자체를 따로 재야 한다**.
- NAACL 2024(기간 밖): 순서 섞기 여러 번 + 집계가 위치 편향을 상쇄.

### 우리 접목안
- M4가 이미 같은 결정 스텝을 1초에 여러 번(T_c 0.33s) 묻는다. **호출마다 보기 순서를 순환(예: 3가지 고정 순열)** 시키면 추가 호출 없이 순열 자기 일관성을 얻는다. 표 원장은 보기 id(순서 아닌 이름)로 쌓으므로 집계는 그대로 된다.
- Jev Choice는 한 번에 전체 보기 분포를 주므로 DualEnd류 "여러 번 나눠 부르기" 이득은 없다(가져오지 않음).
- E-M3-1(오프라인)에 "순서 고정 대 순서 순환" 조건과 RecSys식 PPI 측정(순열 사이 1위 뒤집힘률)을 넣는다.

### 설계 변경: 예, 단 [결정 필요]
- 충돌: 00-interfaces·plan §1 "확률 비교는 **같은 문구·같은 보기**끼리만", M4 "같은 질문끼리만 합의". 순서가 바뀌면 엄밀히 같은 질문이 아니다. 두 안: (가) 순서 순환을 표 합의에 포함(편향 상쇄 우선) (나) 순서 고정 유지, 순환은 E-M3-1에서 순서 민감도가 크게 나올 때만. E1 전에는 최빈 선택만 쓰므로 (가)도 확률 비교 규칙은 어기지 않는다(표 수만 셈) — 그래도 M4 `flip_score`(분포 거리)가 순서 효과로 부풀 수 있다.

---

## 5. M4 겹침 확정 : LocalAgreement 너머

### 후보 표
| 이름 | 분야 | 어디서 최고였나 | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| Adaptive-Consistency (2305.11860) | LLM 자기 일관성 | 표본마다 Beta/Dirichlet 사후로 "현재 다수가 안정적일 확률"을 계산해 넘으면 정지(CGES 본문의 요약 문장으로 확인) | HIGH(EMNLP 2023, 인용 156) | 기간 밖, 기초 문헌 | 예 | 아니오 |
| CGES (2511.02603) | LLM 자기 일관성 | 신뢰도 점수를 증거로 답 사후를 만들고 사후 질량이 기준을 넘으면 정지. 5개 벤치 평균 호출 16.0→6.7(−58%), 정확도는 자기 일관성과 0.4%p 이내(초록) | MED-LOW(NeurIPS 2025 Efficient Reasoning **워크숍**, 확장판 arXiv, 인용 4) | 2025-11-04, 기간 안 | 예 | 아니오 |
| ESC (Li 외, ICLR 2024) | 동상 | "마지막 w개 예측이 일치하면 정지"(CGES 본문 요약) = LocalAgreement와 같은 모양 | HIGH | 기간 밖 | 예 | 아니오 |
| Flexible Paxos (Howard 외, 2016) | 분산 합의 | 1단계(리더 선출)와 2단계(커밋) 정족수는 **서로만** 교차하면 됨 → 커밋 정족수를 작게, 교체 정족수를 크게 둘 수 있음 | 기간 밖, 기초 문헌(OPODIS 2016, 원문 이번에 안 읽음) | 기간 밖 | – | – |
| 스트리밍 동시통역 2025–26 신규 정책 | 동시통역 | 검색 A10·B07·C06에서 LLM 정책 신규 논문(2607.13158 prefix-to-prefix 데이터 방식 등)은 모두 **학습형**이라 제외. LocalAgreement/AlignAtt를 넘는 학습 없는 안정화 정책은 **못 찾음** | – | – | – | – |

### 원문 (Adaptive-Consistency·CGES 공통 골격)
- 표본을 하나씩 받으며 답 분포에 대한 사후(Dirichlet-다항)를 갱신하고, "현재 최다 답이 계속 최다일 사후 확률"이 기준을 넘으면 멈추고 그 답을 고른다. CGES는 여기에 표본별 신뢰도를 증거 가중으로 넣는다(보정 가정 + 잡음 가정 둘 다에서 보장 증명).

### 우리 접목안
- M4 (a)의 확정 규칙 대안: LocalAgreement-2("연속 2표 일치")는 ESC와 같은 모양이다. **Adaptive-Consistency식 규칙** = 한 스텝에 쌓인 표 수(보기별 개수)만으로 Dirichlet 사후 안정 확률을 계산해 기준 이상이면 확정. **Jev 확률을 쓰지 않으므로 E1 전 확률 게이트 금지(00-interfaces §6)와 충돌하지 않는다.** CGES식 신뢰도 가중은 E1 뒤 후보.
- 이 규칙은 "마감(d_p95 고정 구간 진입)까지 기준 미달이면 → 직전 확정 유지 + 감속"과 자연스럽게 맞는다(표본 예산 = 그 스텝이 고정 구간에 들어가기 전 도착한 표 수).
- Flexible Paxos 비유(접목안, 비유만): **유지(현 확정 행동 계속)는 작은 정족수, 교체(도전 선택 수용)는 큰 정족수**로 비대칭을 두는 것은 M4 유예 창 W와 같은 방향 — 새 근거라기보다 현재 설계의 이름 붙이기.

### 설계 변경: 예 (비교 조건 추가)
- E-M4에 C3' = "(a)를 Adaptive-Consistency 정지 규칙으로" 추가(C3 LocalAgreement-2와 같은 호출 예산). 판정: 확정 지연 중앙값과 오확정률(뒤에 CONTRADICT로 뒤집힌 확정 비율)을 함께 보고, 오확정률이 C3 이하이면서 지연이 짧으면 채택 후보.
- H=1일 때 한 스텝의 표는 최대 3개 안팎이라 Dirichlet 사후의 이득이 작을 수 있다(위험, §13).

---

## 6. M5 스무딩 : 캐릭터 애니메이션 전환

### 후보 표
| 이름 | 분야 | 어디서 최고였나 | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| Inertialization (Bollo, "High Performance Animation in Gears of War 4", SIGGRAPH 2017 Talks; GDC 2018) | 게임 애니메이션 | 두 상태를 동시에 평가하는 블렌드 전환을 없애고 후처리로 전환 → 전환 비용 약 60% 절감(GDC 소개문, 성능 수치) | 기간 밖, 기초 문헌(업계 발표, 동료 심사 논문 아님 → MED) | 기간 밖 | 예 | 확인 못 함 |
| Half Pound Filter 비교표 (2602.21702) | 애니메이션 필터 | **Table 1**(LaFAN1 한 예시, 클립 전환 불연속 숨기기): MSE — XFade(교차 블렌드) 0.0259 / DeadMan 0.0054 / **Bollo(관성화) 0.0017** / HPF 0.0032 / 자동 트리거 판: XFade Auto 0.0215 / **Bollo Auto 0.0005** / HPF Auto 0.0006. NPSS는 모두 0.041~0.046으로 비슷 | LOW(arXiv, 12쪽, 인용 0, 예시 1개) | 2026-02-25, 기간 안 | 예 | 아니오 |
| 1€ 필터 (Casiez 외, CHI 2012) | HCI 입력 필터 | 속도 적응 저역 통과 | 기간 밖, 기초 문헌 | – | 예 | 로봇 쓰임 있음 |

### 원문
- 관성화: 전환 순간 **옛 궤적과 새 궤적의 위치·속도 차이(오프셋)를 한 번 계산**하고, 이후에는 새 궤적만 평가하면서 그 오프셋을 다항식(원문 5차)으로 0까지 감쇠시켜 더한다. 옛 궤적을 계속 평가·평균하지 않는다.
- Half Pound Filter 논문 Table 1: 같은 전환 예시에서 교차 블렌드(XFade)가 관성화(Bollo)보다 MSE 약 15배 큼. "자동" 판 = 운동 도함수 경계 검사로 필터를 **필요할 때만 켬**(속도 차가 기준보다 크면 유지).

### 우리 접목안
- M5 L2는 "같은 보기끼리만 RTC식 감쇠 블렌딩"이고, **보기가 다를 때(모드 전환)** 는 평균하지 않는다(RTC + BID, D3). 그 경우 현재 설계는 L3 Ruckig에 연속성을 맡긴다. 관성화는 정확히 이 빈칸용이다: 모드 전환 시 새 `ref(t)`에 "옛 계획 대비 위치·속도 오프셋 × 감쇠"를 더해 시작하고, 옛 보기 궤적은 버린다. → "섞지 않고 잇는다"를 기전으로 명시.
- 자동 트리거: 오프셋(속도 차)이 작으면 관성화를 끄고 Ruckig만 — "아주 작은 움직임만 부드럽게"(사용자)와 맞음.
- M4 (b) 연동: 관성화 오프셋은 `ref(t)`에 포함해서 공개해야 한다(00-interfaces §3: 예상 상태는 `ref(t)` 한 곳). 아니면 전환 직후 가짜 LAG.

### 설계 변경: 예 (L2 모드 전환 가지)
- E-M5-1에 조건 추가: "모드 전환 = Ruckig만" 대 "모드 전환 = 관성화 + Ruckig". 지표: 전환 구간 저크 최대값, 목표 오차, M4 가짜 LAG 수. 기본값(L2 RTC식 블렌딩)은 바꾸지 않는다(00-interfaces C3).

---

## 7. M6 스킬 : 타입 구멍 프로그램 합성

### 후보 표
| 이름 | 분야 | 어디서 최고였나 | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| Type-Constrained Code Generation (2504.09246) | PL / LLM 코드 생성 | HumanEval·MBPP(TypeScript)에서 컴파일 오류 절반 이상 감소, 합성·번역·수리 기능 정확도 향상, 30B 넘는 오픈 모델 포함(초록) | HIGH (PLDI 2025 = PACMPL 9 PLDI: 601–626, ETH SRI + Berkeley, 인용 60) | 2025-04-12, 기간 안 | 예(디코딩 제약) | 아니오 |
| Statically Contextualizing LLMs with Typed Holes (Hazel, OOPSLA 2024) | PL | 구멍의 기대 타입과 관련 타입 정의를 LLM 문맥에 넣음 | 기간 밖(2024-09), 이번에 원문 안 읽음 | 기간 밖 | 예 | 아니오 |
| MetaAgent (2507.22606) | 다중 에이전트 FSM 자동 구성 | – (초록만) | HIGH(ICML 2025, 인용 17) | 기간 안 | 예 | 아니오 |

### 원문 (PLDI 2025)
- 접두부 오토마타 + "거주 가능한 타입 탐색"으로 디코딩 중 **타입이 맞지 않는 토큰을 막는다**. 문법 제약을 넘어 타입 수준까지 건전하게 강제.

### 우리 접목안
- 한계부터: 디코딩 제약은 로짓 접근이 필요 → **Astra(API)에는 직접 못 쓴다**(plan §1: logprob 불가). 옮길 수 있는 것은 "타입을 생성의 합격 조건으로 쓰기"다.
- 생성형 스킬 (b)(CaP-X식, 00-interfaces §11.3)에서 Astra가 쓴 스킬 코드의 결정 자리는 **`jev_choice(dp_id: DecisionPointId, options: Enum[...]) -> 그 Enum`** 형태의 typed hole로만 허용. 코드가 (i) 타입 검사(mypy/pyright 수준) (ii) `dp_id`가 M6 고정 id인지 (iii) 모든 Enum 값에 분기가 있는지(철저성) (iv) 술어가 M1 등록부에 있는지 검사 → 실패 시 오류 문장을 Astra에 되먹여 수리(PLDI의 "수리(repair)" 과제와 같은 쓰임, 단 우리는 사후 검사).
- Hazel식: Astra가 스킬을 쓸 때 각 구멍 자리에 필요한 타입 정의(술어 시그니처, 스킬 카드 스키마)만 골라 문맥에 넣는다.
- 보유 라이브러리 (a')에도 같은 검사를 적용하면 (a')·(b) 대칭 비교(00-interfaces §11.3)의 공정 조건이 된다.

### 설계 변경: 예
- M6: 생성 스킬 합격 게이트(타입·철저성·id·술어 검사) + 오류 되먹임 수리 1~2회. E-M6 지표에 "첫 생성 합격률", "수리 횟수" 추가.

---

## 8. M7 진행·실패 : 프로세스 마이닝 적합성 검사

### 후보 표
| 이름 | 분야 | 어디서 최고였나 | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| 정렬 기반 적합성 검사 (Adriansyah·van Dongen·van der Aalst 2011 계열; van der Aalst "Process Mining" 교과서) | 프로세스 마이닝 | 기초 이론: 관측 사건열과 모델(페트리넷) 사이 최소 비용 정렬 → fitness, 편차 위치·종류 | 기간 밖, 기초 문헌(이번에 원문 안 읽음) | 기간 밖 | 예 | 확인 못 함 |
| LLM + 적합성 검사 모니터 (2511.10876) | 소프트웨어 감시(철도 ERTMS/ETCS) | 사례 연구 1건: LLM 코드 계측이 설계 모델 제어 흐름의 최대 82.849% 포괄, 적합성 검사 이상 탐지 **최대** F1 95.957%, AUC 93.669%(초록, 최대치) | MED(Information and Software Technology 저널(S2 표기), 인용 0) | 2025-11-14, 기간 안 | 예 | 아니오 |
| 조건부 conformal test martingale (2602.13848) | 통계적 변화 탐지 | 고정 기준 집합과 비교해 오염 없이 anytime-valid 1종 오류 + 탐지 지연 한계(초록, 이론) | LOW-MED(무학회, 인용 3) | 2026-02-14, 기간 안 | 예 | 아니오 |
| LLM 시계열 이상 탐지(AnomSeer ICML 2026 등) | 시계열 | 대부분 학습형(RL·미세조정) → 제외 | – | 기간 안 | 아니오 | – |

### 원문
- 적합성 검사: 계획 모델(허용 순서)과 실제 사건 로그를 정렬하면 각 사건이 "동기 이동(일치)", "로그만 이동(모델에 없는 사건)", "모델만 이동(건너뛴 단계)" 중 하나로 분류된다. 2511.10876은 이것을 설명 가능한 제어 흐름 이상 탐지기로 썼다(LLM은 계측 코드 생성만).
- 조건부 CTM: 성공 실행 같은 **고정 기준 집합**과 매 표본을 비교해 베팅 마팅게일을 키우고, 1/α를 넘으면 경보. 기존 CTM은 변화 뒤 표본이 기준에 섞여 탐지가 늦어짐.

### 우리 접목안
- M2 단계 원장(`phases` + `entry/exit`)을 작은 순서 모델(선형 + 허용 분기)로, M1 술어 전이(예: `grasped` 참이 됨)를 사건으로 보고 매 틱 증분 정렬. 편차를 셋으로:
  - "모델만 이동" = 단계 `exit` 없이 다음 단계 사건 발생(건너뜀) → 새 소프트 채널 `C_order` 후보.
  - "로그만 이동" = 계획에 없는 술어 전이(예: 물체 떨어짐) → T1 술어면 하드, 아니면 소프트(00-interfaces §11.2 규칙 그대로).
  - 정렬의 **마지막 동기 이동 위치 = 사전조건이 참인 가장 늦은 지점** 후보 → M9 재개 지점 계산(PLANEX 삼각표, D3)과 같은 값을 한 계산으로 공유.
- CTM은 M7의 conformal 마감·C_flip 임계값(D3: 성공 실행으로 conformal 보정)을 **고정 기준 집합 순차 검정**으로 바꾸는 대안. 이득은 anytime-valid(매 틱 반복 검사에도 오경보율 보장). 근거 LOW라 대안 조건으로만.

### 설계 변경: 예
- M7 채널에 `C_order`(순서 편차) 추가 제안 — 정본 채널 목록(00-interfaces §11.2) 변경이므로 [결정 필요: 메인 세션]. M9와 재개 지점 계산 공유.

---

## 9. M8 호출 시점 : 캐스케이드·라우팅

### 후보 표
| 이름 | 분야 | 어디서 최고였나 | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| RouteNLP (2604.23577) | LLM 서빙 | 8주 실사용(하루 약 5K 질의): 추론 비용 −58%, 응답 수용 91%, p99 지연 1,847→387ms. 6과제 벤치 비용 −40~85%(초록). §3.2: **conformal risk control로 위임 임계값 초기화**, 원문 스스로 "보장은 질의별이 아니라 주변(marginal), 분포 이동에 깨짐" | MED(ACL 2026 **Industry** Track, 인용 2) | 2026-04-26, 기간 안 | 라우터는 학습, 임계값 설정은 학습 없음 | 아니오 |
| Inter-Cascade (2509.22984) | LLM 캐스케이드 | 강한 모델이 위임받은 문제를 풀 때 **재사용 가능한 전략**을 만들어 저장, 약한 모델이 비슷한 질의에서 검색해 문맥에 넣음. 약한 모델 정확도 최대 +33.06%, 전체 +6.35%, 강한 모델 호출 최대 −48.05%(모두 최대치, 초록). 임계값 λ는 보정 집합에서 위험 허용 α·오류 δ로 도출(§3.2, Jung 외 방식) | LOW-MED(심사 중, 인용 1) | 2025-09-26, 기간 안 | 예 | 아니오 |
| Routing, Cascades, and User Choice (2602.09902) | 이론(슈타켈베르크 게임) | "거의 모든 경우 최적 라우팅은 **캐스케이드 없는 정적 정책**", 단순 임계값 규칙 도출(초록) | HIGH(ICLR 2026, 인용 2) | 2026-02-10, 기간 안 | – | 아니오 |

### 원문 → 우리 접목안
- 사용자 원칙: 실패 판정이면 **항상** Astra(문지기 건너뜀). 따라서 캐스케이드 기전은 실패 아닌 트리거(T1 주기, T2 정한 순간, T3b 모델 자체 판단)의 "부를지"에만 해당한다.
- 접목안 1(RouteNLP·Inter-Cascade 공통 골격): E1 뒤 T3b(Jev가 "이상하다" Noul 또는 진행 범주 확률)로 Astra를 부를지의 임계값을, 기록된 사건 묶음(E-M8b)에서 **conformal risk control로 "Jev 단독 수용 결정의 오류율 ≤ α"가 되도록** 정한다. E1 전에는 게이트 끔(00-interfaces §6).
- 접목안 2(Inter-Cascade): Astra가 실패를 풀 때마다 "전략"을 만든다 → 이것은 M10의 "Astra가 typed 규칙으로 컴파일해 Jev에 0~2개"와 같은 모양이다. **새 근거가 아니라 M10 설계의 비로봇 선행**으로 인용한다(강한 모델 호출 감소를 M10 효과 지표로 쓰는 근거).
- ICLR 2026 이론은 "복잡한 동적 캐스케이드보다 정적 임계값"이라는 반대 방향 근거 → M8 문지기(BRACE)를 두되 비교 조건에 "정적 규칙(트리거별 고정 부름/안 부름)"을 넣는다. 가정(사용자 재질의·포기 게임)이 우리와 달라 직접 옮기지는 않는다.

### 설계 변경: 부분
- E1 뒤 T3b 임계값 설정법(conformal risk control) 명시. E-M8a에 "정적 규칙" 조건 추가. M10 효과 지표에 "Astra 호출 수 감소" 추가.

---

## 10. M9 복구 : 사가·트랜잭션

### 후보 표
| 이름 | 분야 | 어디서 최고였나 | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| Sagas (Garcia-Molina·Salem, SIGMOD 1987) | 데이터베이스 | 긴 트랜잭션을 하위 트랜잭션 열로 나누고 각 T_i에 보상 C_i를 짝지음. 실패 시 역순 보상(backward) 또는 저장점부터 재시도(forward) | 기간 밖, 기초 문헌(이번에 원문 안 읽음) | 기간 밖 | 예 | – |
| SagaLLM (2503.11951) | LLM 다중 에이전트 계획 | 사가 패턴 + 지속 메모리 + 자동 보상 + 독립 검증 에이전트(초록, 수치 미확인) | HIGH(VLDB 2025(S2 표기), 인용 76) | **2025-03-15 → 기간 밖(8일 차)** | 예 | 아니오 |
| Atomix (2602.14849) | LLM 에이전트 도구 사용 | 진행 인지 트랜잭션: 읽기·효과 기록 → 발자국 완성 시 봉인 → **이전 충돌 작업이 더 올 수 없을 때만 커밋**. 효과 3분류: 버퍼 가능 / 가역 외부 / 비가역. 중단 시 방출 전 효과는 억제, 방출된 가역 효과는 보상. 비가역은 커밋 게이트 전 방출 금지(초록) | MED-LOW(무학회, 인용 25 — 공개 7개월에 비해 반응 있음) | 2026-02-16, 기간 안 | 예 | 아니오 |
| Cordon (2606.17573), Agentic Transaction ACID (2608.13900) | 동상 | 그림자 상태 + 효과 발신함 / ACID 재해석 | LOW(무학회) | 기간 안 | 예 | 아니오 |

### 원문 (Atomix 핵심 문장, 초록)
- "Correct settlement needs two facts that retries, checkpoint replay, locks, and compensation each conflate: which effects must settle together, and when earlier conflicting work is exhausted." 추측(speculation)·경합 작업에서 진 가지의 잔여 효과를 막는다.

### 우리 접목안
- 로봇 행동은 되돌릴 수 없는 게 많다(물리). 그래서 가져올 것은 **효과 분류**다. M6 스킬 카드 단계마다 `effect: reversible(보상 스킬 id) | irreversible` 표지(접목안):
  - 가역 예: 들어올림 → 보상 = 원위치 내려놓기, 접근 → 보상 = 후퇴.
  - 비가역 예: 놓기(release), 밀어 떨어뜨리기, 끼우기 완료.
- M9 복구: "재개 지점 = 사전조건 참인 가장 늦은 지점"(D3)에 **거기까지 가는 경로 = 가역 단계들의 보상을 역순 실행**(사가 backward recovery)을 붙인다. 경로에 비가역 단계가 있으면 그 너머로는 되돌릴 수 없으므로 재개 후보에서 제외 → forward recovery(재시도)만.
- M4 연동(Atomix의 "비가역은 커밋 게이트 전 방출 금지"): M4의 추측 스텝(미확정 표)이 **비가역 효과를 내는 보기**(예: `release`)이면 LocalAgreement 등 기본 확정 규칙보다 강한 조건(합의 (a) + 실행 확인 (b) 모두 + grasp/release 전환 보류 1.0s — 설정 표 기존값)을 요구. 이는 기존 "전환 보류 1.0s"를 효과 분류로 일반화한 것.

### 설계 변경: 예
- M6 스킬 카드에 `effect` 필드(가역/비가역 + 보상 스킬 id). M9 재개 경로 = 보상 역순 실행, 비가역 경계 넘어 되돌리기 금지. M4 비가역 보기의 확정 강화. 00-interfaces 필드 추가라 [결정 필요: 메인 세션].

---

## 11. M10 경험 : 사례 기반 추론 + 동결 LLM 테스트 시점 학습

### 후보 표
| 이름 | 분야 | 어디서 최고였나 | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| CBR 4R 순환 (Aamodt·Plaza, AI Communications 1994) | 고전 AI | Retrieve → Reuse → **Revise(실세계·검사로 검증)** → Retain | 기간 밖, 기초 문헌 | 기간 밖 | 예 | CBR 로봇 적용은 오래 있음 |
| 역량 보존 사례 삭제 (Smyth·Keane, IJCAI 1995 "Remembering to Forget") | CBR 유지 | 사례의 coverage/reachability로 분류해 다른 사례가 대신 덮는 사례부터 지움 | 기간 밖, 기초 문헌(원문 이번에 안 읽음) | 기간 밖 | 예 | – |
| Review of CBR for LLM Agents (2504.06943) | LLM 에이전트 | 검색·적응·학습 수식화, CoT·RAG와 비교(리뷰) | LOW(무학회, 인용 22) | 2025-04-09, 기간 안 | 예 | 아니오 |
| MemoPilot (2606.08656) | 동결 LLM 테스트 시점 학습 | 메모리 갱신기를 multi-turn GRPO로 학습해 동결 LLM 플레이어 개선, Elo 1위(LHE 1762, RPS 1590)(초록) | HIGH(ICML 2026, 인용 1) | 기간 안 | **아니오(갱신기 학습)** | 아니오 |
| TLM (2505.20633) | 테스트 시점 학습 | 입력 perplexity 최소화 LoRA 갱신 | HIGH(ICML 2025) | 기간 안 | 아니오(가중치 갱신) → **API 모델에 불가** | – |

### 원문 → 우리 접목안
- CBR의 Revise는 "재사용한 해를 **실제로 적용·검증한 뒤에만** 저장"이다. M10의 "센서 술어로 확정한 것만 Jev 규칙 재료"(plan §2 M10)는 이미 Revise다 → **새 기전은 아니고 기초 문헌 근거 상향**.
- 새로 가져올 것 = 사례 집합 **유지 정책**: 현재 M10 삭제 규칙은 2505.16067(ACL 2026) "최소 n회 꺼낸 뒤 해가 크면 삭제". 여기에 Smyth·Keane식 **역량 보존**(같은 (스킬, 결정 지점, 술어) 키를 다른 규칙이 이미 덮으면 먼저 삭제, 유일하게 덮는 규칙은 보존)을 비교 조건으로. Jev 키 정확 일치 0~2개 설계와 잘 맞는다(키 = coverage 정의가 명확).
- 테스트 시점 학습 계열(TLM, MemoPilot)은 가중치 갱신이나 갱신기 학습이 필요해 Astra·Jev(API)에 직접 못 쓴다. MemoPilot의 "메모리 갱신을 다단계 결정으로 보고 차례별 보상으로 평가"는 발상만 — E-M10에서 규칙 추가·삭제마다 뒤 N 사건의 성공 변화로 기록(학습 없이 측정만).

### 설계 변경: 작음
- E-M10에 삭제 정책 두 조건(2505.16067식 대 역량 보존) 추가. 4R은 근거 표기만.

---

## 12. 검색어 기록 (arXiv API, 날짜 ≥2025-03-20 결과만 검토)
- M1: `all:"table serialization" AND all:LLM` / `abs:table AND abs:serialization AND abs:"large language models" AND abs:format` / `all:"structured data" AND all:serialization AND all:LLM AND all:agent`(0건) / `ti:table AND ti:format AND ti:LLM` / `ti:serialization AND abs:LLM AND abs:table`(0) / `ti:tables AND abs:markdown AND abs:JSON AND abs:LLM`(0) / `ti:"structured data" AND ti:LLM AND ti:format`(0)
- M2: `all:"LLM compiler" AND all:plan AND all:agent` / `abs:"intermediate representation" AND abs:"LLM agent" AND abs:plan` / `abs:plan AND abs:DSL AND abs:"type checking" ...`(0) / `ti:"LLM compiler"` / `ti:plan AND ti:verification AND ti:agent AND ti:typed`(0) / `ti:LLMCompiler`(0) / `abs:"intermediate representation" AND ti:agent AND abs:planning` / `ti:"workflow" AND ti:verification AND ti:agentic AND abs:"static"` / `ti:plan AND ti:language AND abs:agent AND abs:"domain-specific language" AND abs:verif`(0)
- M3: `abs:listwise AND abs:reranking AND abs:LLM AND abs:"position bias"` / `abs:"setwise" AND abs:ranking AND abs:LLM` / `abs:"multiple choice" AND abs:"many options" ...`(0) / `ti:"permutation self-consistency"`(0) / `ti:reranking AND ti:tournament AND abs:LLM`(0) / `ti:"multiple-choice" AND abs:"option order" AND abs:"large language models"`
- M4: `abs:"simultaneous" AND abs:"speech translation" AND abs:policy AND abs:LLM AND abs:stability`(0) / `abs:streaming AND abs:"speech recognition" AND abs:"partial hypotheses" AND abs:stability`(0) / `ti:simultaneous AND ti:translation AND ti:LLM AND ti:policy`(0) / `ti:"adaptive consistency"` / `ti:self-consistency AND ti:"early stopping"` / `ti:simultaneous AND ti:LLM AND abs:"read/write"` / `ti:"streaming" AND ti:"stable" AND abs:ASR`(0)
- M5: `abs:"motion matching" AND abs:blending` / `abs:"inertialization"`(무관 결과만) / `abs:"motion in-betweening" AND abs:transition` / `ti:"motion matching"` / `ti:"motion blending"` / `ti:"frame interpolation" AND abs:"scene cut"`(0) + WebSearch 1회(inertialization 원출처)
- M6: `ti:"type-constrained"` / `ti:"typed holes"`(0) / `ti:holes AND abs:"language model" AND abs:program`(0) / `ti:"behavior tree" AND abs:LLM AND abs:game`(0) / `ti:"finite state machine" AND abs:LLM AND abs:agent` + WebSearch 1회(PLDI 확인)
- M7: `ti:"conformal test martingales"` / `ti:"conformance checking" AND abs:LLM` / `ti:"time series" AND ti:anomaly AND ti:LLM`
- M8: `ti:cascade AND ti:LLM AND ti:deferral` / `ti:routing AND ti:LLM AND ti:cascading`
- M9: `ti:saga AND abs:LLM`(사가 패턴 무관 SAGA 약어만) / `ti:transactional AND ti:agents` / `ti:SagaLLM`(0 — abs 페이지 2503.11951로 직접 확인)
- M10: `ti:"case-based reasoning" AND abs:LLM AND abs:agent` / `ti:"test-time learning" AND abs:LLM`

## 13. 반대 증거와 위험
- M3 순서 순환: RecSys 2026은 "노출 평탄화로 선호 일관성이 안 돌아온다"고 했다. 순열 집계가 이를 복원한다는 수치는 **기간 밖 NAACL 2024 근거뿐**이고, Jev(typed 분류 모델)가 생성형 LLM만큼 위치 편향이 있는지는 모른다 → E-M3-1에서 먼저 잰다.
- M4 Adaptive-Consistency: 표가 스텝당 몇 개뿐(T_c 0.33s, d_p95 미측정)이면 사후 안정 확률이 기준에 거의 못 닿아 LocalAgreement-2와 같아질 수 있다. 또 같은 모델 반복 표는 독립이 아니다(M4 문서의 "같은 오답 반복") — Dirichlet 모형의 교환 가능성 가정이 깨진다.
- M5 관성화: 기간 안 수치 근거는 LOW 논문의 예시 1개(LaFAN1) Table 1뿐. 캐릭터 애니메이션은 접촉·물체 동역학이 없다 → 접촉 구간(near/contact)에서는 관성화 오프셋이 목표 오차를 만들 수 있다. 접촉 구간은 끄는 조건 필요.
- M6 타입 제약: PLDI 결과는 디코딩 제약이다. 사후 검사 + 수리로 바꾸면 같은 효과가 난다는 근거는 없다(원문은 수리 **과제**에서도 이득이지만 그것도 제약 디코딩으로 한 것).
- M7 적합성 검사: 로봇 사건 추출(술어 전이)의 잡음이 크면 "로그만 이동" 오경보가 많아진다. 기간 안 근거는 철도 사례 1건(최대치 수치).
- M8: ICLR 2026 이론은 동적 캐스케이드에 불리. RouteNLP 보장은 주변(marginal)이고 분포 이동에 깨진다(원문 명시) — 새 환경 일반화가 핵심인 우리 과제에서 약점.
- M9: SagaLLM은 기간 밖(8일). Atomix·Cordon은 무학회. 물리 로봇에서 "보상 스킬"이 정확히 원상 복구하지 못한다(물체 자세 변화) → 보상 뒤 사전조건 재확인 필수.
- 전반: 이번 조사는 모듈당 1개만 깊이 봤다. "분야 최고"라는 말은 "이번에 찾은 것 중 우리에게 옮기기 가장 좋은 것"으로 읽어야 한다.

## 14. 열린 질문, [결정 필요]
1. [결정 필요] M3 보기 순서 순환을 M4 표 합의에 넣을지(“같은 질문끼리만” 규칙과의 충돌) — (가) 넣음 (나) E-M3-1 결과 보고 결정.
2. [결정 필요: 메인 세션] M7 새 소프트 채널 `C_order` 추가(정본 채널 목록 변경).
3. [결정 필요: 메인 세션] M6 스킬 카드 `effect`(가역/비가역 + 보상 스킬) 필드와 M4 비가역 보기 확정 강화.
4. M2 계약 정적 검사 실패 시 수리 왕복을 T0에서만 허용할지, 실패 뒤 재계획에도 허용할지(재계획은 정지 예외 범위 — 00-interfaces §4).
5. M5 관성화를 접촉 구간에서 끌지(near/contact 정의는 설정 표 기존값).

## 15. 확인 못 한 것
- 기초 문헌 원문 재확인 안 함: Bollo SIGGRAPH 2017 Talk/GDC 2018(수학식·5차 다항 감쇠는 기억), Sagas 1987, Aamodt·Plaza 1994, Smyth·Keane 1995, Dwyer 외 1999, Adriansyah 외 2011, Flexible Paxos 2016, ESC(ICLR 2024)·Adaptive-Consistency(EMNLP 2023)의 정지 규칙 세부(CGES 본문의 요약 문장으로만 확인), Hazel OOPSLA 2024.
- Agentproof DSL 7형식 중 6·7번(부록 B), RecSys 2026 본문 수치표(PPI·GPI 실제 값), CGES 사후 계산식·기준값, RouteNLP §3.2 conformal 절차 세부, Inter-Cascade 실험 표 수치(초록 최대치만).
- SagaLLM의 VLDB 2025 채택은 S2 표기뿐(학회 페이지 미확인). 2511.10876의 Information and Software Technology 게재도 S2 표기뿐.
- LocalAgreement/AlignAtt를 넘는 **학습 없는** 2025–26 스트리밍 안정화 정책: 검색 7개로 못 찾음(부재 단정 아님).
- LLM + 행동 트리/상태 기계 합성의 로봇 밖 사례(게임 AI 등): 검색 2개로 못 찾음. MetaAgent(ICML 2025)는 초록만.
- 인용 수는 Semantic Scholar 2026-09-24 1회 측정. 공개 직후 논문(RecSys 2026 등)은 0이 정상.

## 출처
- https://arxiv.org/abs/2601.08444 (TabGR) · https://arxiv.org/abs/2606.09578 (TABVERSE)
- https://arxiv.org/abs/2603.20356 (Agentproof) · https://arxiv.org/abs/2312.04511 (LLMCompiler, ICML 2024) · https://arxiv.org/abs/2505.22967 (MermaidFlow)
- https://arxiv.org/abs/2608.03091 (RecSys 2026) · https://arxiv.org/abs/2310.07712 (NAACL 2024) · https://arxiv.org/abs/2606.01782
- https://arxiv.org/abs/2511.02603 (CGES) · https://arxiv.org/abs/2305.11860 (Adaptive-Consistency)
- https://arxiv.org/abs/2602.21702 (Half Pound Filter) · https://www.gdcvault.com/play/1025331/Inertialization-High-Performance-Animation-Transitions · https://history.siggraph.org/wp-content/uploads/2022/09/2017-Talks-Bollo_High-Performance-Animation-in-Gears-of-War-4.pdf
- https://arxiv.org/abs/2504.09246 · https://pldi25.sigplan.org/details/pldi-2025-papers/25/Type-Constrained-Code-Generation-with-Language-Models · https://dl.acm.org/doi/10.1145/3729274
- https://arxiv.org/abs/2511.10876 · https://arxiv.org/abs/2602.13848
- https://arxiv.org/abs/2604.23577 (RouteNLP) · https://arxiv.org/abs/2509.22984 (Inter-Cascade) · https://arxiv.org/abs/2602.09902 (ICLR 2026)
- https://arxiv.org/abs/2503.11951 (SagaLLM) · https://arxiv.org/abs/2602.14849 (Atomix) · https://arxiv.org/abs/2606.17573 · https://arxiv.org/abs/2608.13900
- https://arxiv.org/abs/2504.06943 · https://arxiv.org/abs/2606.08656 (MemoPilot) · https://arxiv.org/abs/2505.20633 (TLM)
