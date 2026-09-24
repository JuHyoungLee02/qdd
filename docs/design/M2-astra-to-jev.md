# M2. Astra → Jev 전달 (세션 계약) — 모듈 설계

> **정본 우선**: 모듈 사이 인터페이스·정지·확정 규칙·확률 게이트·시간 값은 `00-interfaces.md`가 우선한다. 이 문서의 계약 교체 규칙(§4.2)은 정지를 만들지 않는다(교체 대기 중에도 직전 확정 행동 유지, `00-interfaces.md` §4). E-M2-2의 W(기다림) 조건은 비교용이며 기본안이 아니다.
> 개정 2026-09-24 (정본 §28, D17 반영, `D17-api-consistency.md`): §2.4 신설 — API 일관성·재계획 고정 근거 행(HIGH/MED만. D17 §2의 LOW 12편은 근거로 쓰지 않음, MED-LOW 보조 4편도 넣지 않음). §4.5 신설 — **Astra 일관성 규약 A1~A6**: A1 템플릿 해시 `astra_prompt_id`, A2 입력 정규화, A3 출력 = 계약 JSON + 검사기 1–6 유지(2턴 변환은 첫 시도 통과율 < 80%일 때만 비교), A4 재계획 고정 = **잠정 기본**(R6 승격: 기본 출력 `patch`, 단계마다 `change_reason`, 이미 실행한 단계 변경 금지, 편집 거리 기록), A5 T0 전용 K = 3 투표 = **잠정 기본**(비정지 호출 K = 1, effort high에서는 투표 안 함), A6 재현 기록. §4.2 R6 승격 표시, E-M2-3 지표·조건 추가, §6-10, §7-5 갱신. A4·A5는 Claude 설계 선택이고 사용자 원칙("실패할 때마다 Astra 개입", T0 뒤 웬만하면 안 멈춤, effort 기본 low + low·high 비교)은 그대로다.
> 개정 2026-09-24 (정본 §26, 사용자 결정 user-log 25): M1 변환 방법 줄 갱신 — "변환 방법은 사용자가 정한다"는 사용자가 한 말이 아니라 폐기, M1 기본 = 후보 A(Claude 결정, B·C는 E3 비교). §0 전제 줄과 §7-1. 이 문서는 여전히 등록부 인터페이스에만 의존한다. E-M2-2의 Astra 지연 분포는 low·high 둘 다에서 뽑는다(effort 기본 low).
> 개정 2026-09-24 (정본 §25, D13 반영, `D13-m1-m2-m5-deepread.md` §3~§5·§8): COPE 근거 정정 — 큰 → 작은 이득(Llama-3B 42.8 → 53.0)은 **절차형(guideline)** 계획이었고 목표형 우위(30.2 대 23.2)는 1B 자기 계획뿐, 본 방법 Stage 2도 큰 모델 절차형이다 → COPE를 v1(목표 중심 조각)의 근거에서 뺀다. v1 기본값은 **설계 선택**으로 유지(M4·M7·M9가 술어를 읽음, AgentSpec 모양). E-M2-1에 **B-COPE** 조건 추가. AgentSpec 지표 정정(집행률 95.56%, "recall" 70.96%는 정의 모호, 과차단 포함) + E-M2-3 `forbidden` 과차단률. AgileThinker 등급 HIGH → MED(학회 [미확인]), Table 10 네 열, 16k 역전, E-M2-2 지연 구간별 보고. WAM 등급 LOW-MED로 통일. 근거 약화는 사용자에게 알림(SUMMARY).
> 개정: 2026-09-23 D5 반영 (`D5-consistency.md` 1-2·1-17·2-1, 00-interfaces §7·§15·§16): `contract_patch_rejected`는 M7 `C_assume`로 보낸다(00 §15 확정, R7 (ii)·§7-8). DFA 형식 검증(§4.4)을 기간 밖 기초 문헌에 기댄 **잠정 기본**([결정 필요] 4)으로 표시. R3 교체 시점을 M8 commit 창·M9 적용 시점의 단일 기준으로 명시(비가역 판단은 M6 `effect`). `C_assume` 0.5 s·`tilt_max`·`h_lift`는 00 §7 설정 표.
> 개정: 2026-09-23 정본 §14–§15 반영 (`00-interfaces.md` §14-4·§15, `D4-cross-field.md` §3, `D4-cross-field-verification.md` #6). 핵심: 계약 수리 왕복(검사기 오류를 Astra에 되돌림)은 **T0(첫 계획)에서만**(§4.1 검사기). 실행 중 재계획 patch는 **검사만** 하고, 실패하면 거부 + M7 신호를 보낸다. 로봇은 멈추지 않는다(§4.2 R7). `forbidden`·순서 제약은 명세 패턴 부분집합으로만 쓰고 DFA로 컴파일해 H5와 `C_assume` 감시를 한 감시기로 통일한다(§4.4 신설). 근거로 Agentproof(LOW, 저자 구성·7형식 위치 정정)와 형식 검증 기초 문헌(기간 밖)을 더했다(§2.3). E-M2-3 지표 추가, §7-8 해소.
> 개정: 2026-09-23 D2 검증·00-interfaces §11 반영 (`D2-verification.md` Part A 정정, Part B·C 해소안. 핵심: 단계 필드 `pre/done/inv/substeps` → `entry/exit/invariants/phases`, 결정 지점 id는 M6 스킬 고정 id를 **골라 쓰고 인자만 채움**, 가정 술어 거짓 → M7 소프트 채널 `C_assume` + M8 재호출 신호, 계약 버전 교체 → M4 `premise_epoch` +1, PlanAhead는 보조 참고로 내림.)

- 작성: 2026-09-23 UTC, 단계 2 라운드 D2 설계 에이전트(M1·M2, 이번 라운드 arXiv 검색 API 전담)
- **[사용자]** M1과 거의 같은 문제로 본다. Astra는 이미지를 보고 명령하지만 Jev는 이미지를 못 보므로, Astra가 본 것과 원하는 것을 Jev에게 효율적으로 전달하는 방법이 필요하다.
- [사용자] Astra가 처음 계획할 때는 로봇이 멈춰도 되고, 그 뒤에는 웬만하면 멈추지 않는다(실패로 다시 생각할 때만 예외). 실패 판정이 나면 Astra를 부른다(M8).
- 이 문서는 M1과 짝이다. M1이 "카메라 → 텍스트"라면 M2는 "Astra의 판단 → Jev가 읽을 수 있는 typed 계약". **계약 안 술어 이름은 M1 술어 등록부(M1 §4.0)의 이름만 쓴다.** M1 변환 방법은 기본 = 후보 A(Claude 결정, 정본 §26 — B·C는 E3 비교 조건, M1 §7-1). 이 문서는 특정 후보가 아니라 등록부 인터페이스에만 의존한다(후보 A·B·C 모두 등록부 술어를 낸다, 00-interfaces §11.3).
- 조사 방법·검색어·한계는 M1 문서 0절과 같다(같은 에이전트, 같은 라운드). M2용으로 추가로 읽은 것: PlanAhead(2605.29927) 본문 표, Magentic-One(2411.04468) §3 원장, AgileThinker Tab.10, AgentSpec 초록, 2608.02645·2606.15285·2606.20978 초록.

---

## 1. 역할과 입출력

| 항목 | 내용 |
|---|---|
| 위치 | Astra(느림, 이미지 입력: Set-of-Mark 번호 이미지 + M1 텍스트 상태) → **계약 검사기(코드)** → 계약 저장소(버전) → Jev 요청 조립기(M3)·M4 원장·M7 critic·M8 호출기·M9 복구 |
| 입력(Astra에게) | 과제 지시, SoM 이미지(M1이 붙인 ID와 같은 번호), M1 상태 텍스트(같은 `t_state`), 스킬 카드(이름·`entry`/`exit` 술어·결정 지점 id·파라미터 이름, M6), 술어 어휘(M1), 이전 계약·실패 사건 문맥(재계획일 때, M8·M9), M10 규칙 |
| 출력 | **세션 계약(Session Contract)** JSON 한 개. 코드가 검사해 통과하면 새 버전으로 게시 |
| Jev가 보는 것 | 계약 전체가 아니라 **현재 단계에 필요한 조각**(현재 단계의 목표·완료 술어·금지 술어·결정 지점 질문·관련 ID). M1 원칙(관련 없는 내용 넣지 않기)과 같다 |
| 코드가 보는 것 | 계약 전체(원장, 술어 정의, 마감, 체크포인트, 예상 실패 목록) |

---

## 2. 분야 전체 최고 후보 표

### 2.1 계획기 → 실행기 전달 형식

| 이름 | 분야 | 어디서 최고였나 (조건) | 신뢰도 | 기간 | 학습 없이 | 로봇 |
|---|---|---|---|---|---|---|
| **COPE** (2506.11578) | LLM 협업 | 계획 = 한두 문장. 큰 계획기 → 작은 실행기 도움(Llama-3B 42.8→53.0%, GPT-4o-mini 계획) — (§25 D13 정정) 이 이득은 **절차형(guideline, "strategy and key ideas" 1~2문장) 계획**에서 나왔다(Observation 3 "rather than a guideline … as before"). **목표형 30.2 / 절차형 23.2 / 없음 25.2**는 Llama-1B **자기 계획** 조건뿐(Table 2, MATH-500). 본 방법 Stage 2도 작은 모델 자신의 목표 + 큰 모델의 "guideline-type plan". 큰 모델 계획만 준 Plan-only는 56.8로 계획 없는 cascade 71.2보다 낮다(Table 8). 작은 계획기 → 큰 실행기는 해로움(v3/14 원문 확인) | HIGH(TMLR 2026) | 안 | 예 | 아니오 |
| **PlanAhead** (2605.29927) | 웹 에이전트 | 계획 형식 4종(순차 하위목표 / 서사 / 의사코드 / 체크리스트), 계획기·실행기 3모델 조합, WebArena Hard 158과제 × 5회. **가장 좋은 형식이 실행기 모델마다 다르다**(GPT-4.1-mini는 서사, Qwen-2.5-VL은 체크리스트·순차, Gemini 계획+실행은 의사코드). 정적 계획이 동적 단일 에이전트보다 자주 낫다. **정정(D2 A1)**: "32.5~84.0"(4.1-mini 체크리스트)은 **Table 5(STC, 해결 과제 일관성)**의 부트스트랩 구간이다. **Table 4(AR)**의 같은 칸은 **1.20~4.79**이고 저자는 AR 추정이 "highly stable"하다고 쓴다 → "구간이 넓다"는 STC에만 해당. Hard 과제 AR 절대값이 약 1~11%로 매우 낮다 | MED-LOW(Mila 등, EMNLP 투고 중, 인용 0). **보조 참고**: 설계 선택 근거로 쓰지 않는다(00-interfaces §11.3) | 안 | 예 | 아니오 |
| **Magentic-One 원장** (2411.04468) | 다중 에이전트 | 바깥 고리 **과제 원장**(확인된 사실, 찾을 사실, 유도할 사실, 추측, 계획), 안쪽 고리 **진행 원장** 다섯 질문(완료됐나 / 반복 중인가 / 전진 중인가 / 다음 누구 / 무슨 지시). 정체 카운터 ≤2 넘으면 바깥 고리 재계획(§3 본문) | HIGH(Microsoft, 반응 큼 — 수치 미측정) | **기간 밖(2024-11), 기초 문헌** | 예 | 아니오 |
| **AgentSpec** (2503.18666) | LLM 에이전트 안전 | 규칙 = **트리거 + 술어 + 집행**의 DSL. 코드 에이전트 90% 이상 위험 실행 차단, 체화 에이전트 위험 행동 전부 제거(초록) — **사람이 쓴 규칙 기준**(안전 과제 수행 58.62 → 54.26%, Table 4). **LLM(o1)이 생성한 규칙은 체화에서 처음 보는 위험 사례 집행률(원문 "precision") 95.56%, 안전 짝 사례로 낸 "recall" 70.96%**(Table 6·§5.3). (§25 D13 정정) "recall"은 원문 정의가 모호하고 본문이 놓침과 과차단을 함께 설명한다. Astra가 규칙을 쓰는 M2에는 이 값이 더 가까운 근거 | HIGH(ICSE 2026, 인용 221) | 안(2025-03-24) | 예 | 체화 시뮬 |
| **Code-as-Monitor** (2412.04455) | 로봇 | VLM이 제약 요소를 정의하고 만족 여부 **코드**를 생성, 실시간 감시. 심한 방해 +28.7%p(v3/04) | HIGH(CVPR 2025) | **기간 밖, 기초 문헌(개념)** | 예 | 예 |
| MAST (2503.13657) | 다중 에이전트 실패 분석 | 실패 유형 중 "과제 명세 불이행", "종료 조건 모름"(v3/14) | MED | 기간 밖(6일), 기초 | — | — |
| Anthropic 다중 에이전트 블로그 | 업체 | 하위 에이전트 지시 네 요소: 목표, 출력 형식, 도구·출처, 과제 경계(v3/14) | MED | 안 | 예 | 아니오 |
| Plan-then-Execute 입장 (2605.14290) | 웹 | WebArena 80%가 실행 중 LLM 없는 프로그램 계획으로 가능, 전제는 효과를 미리 아는 typed 행동(v3/14) | MED-LOW | 안 | 예 | 아니오 |
| 계층 시연 구조 (2606.20978) | 웹 | 같은 행동 열을 **이름 붙은 계층 하위목표로 묶으면** 모호한 지시 과제에서 76.7→90.7%(p=0.034), 정확한 지시에서는 효과 없음(초록) | LOW-MED(ICML 2026 DL4C 워크숍) | 안 | 예 | 아니오 |
| 검증된 도구 호출 (2608.02645) | 에이전트 | 도구 호출에 **사후조건 검증 + 재시도 전 검증 + 멱등 키** → 중복 행동 크게 감소, 성공률 비슷(초록, 시뮬 주입 실패) | LOW(소속·학회 미확인) | 안 | 예 | 아니오 |

### 2.2 낡은 계획 처리 (계획기가 느릴 때)

| 이름 | 분야 | 무엇 | 신뢰도 | 기간 | 로봇 |
|---|---|---|---|---|---|
| **AgileThinker** (2511.04898) | 실시간 LLM | 반응 스레드가 계획 스레드의 부분 추론을 참조. 추론 흔적 비공개 모델(Gemini-2.5-Flash)에서는 **계획의 최종 출력만 참조**하는 축소판(Tab. 10, Freeway 중간): 8k 토큰/스텝 0.31 대 반응 단독 0.09·계획 단독 0.25, 4k 0.26 대 0.00·0.05, 16k·32k는 차이 없음. (§25 D13 정정) Table 10 네 열(반응 생각 끔 / 반응 생각 켬+예산 / 계획 / 반응+계획): 32k 0.12 / 0.93 / 0.93 / 0.92, 16k 0.12 / 0.76 / 0.70 / 0.70, 8k 0.12 / 0.09 / 0.25 / 0.31, 4k 0.12 / 0.00 / 0.05 / 0.26. **16k에서는 결합 0.70 < 반응(생각 켬) 0.76** → 압박이 약하면 결합이 손해일 수 있다. Table 10 표본 수는 원문에 없다 | MED(학회 [미확인], abs 코멘트 "30 pages"만. 첫 판 "HIGH(ICLR 2026)"는 확인 안 됨, §25 D13) | 안 | 아니오 |
| **Slow Brain, Fast Planner** (2606.20458) | 로봇 | 블랙박스 VLM에 1Hz로 기다리지 않고 여러 요청, **가장 새 답 + 지수 감쇠 융합**, 로봇 무정지(plan v4.2, 메인 세션 원문 확인) | LOW(인정해야 할 선행) | 안 | 예 |
| 비동기 의미-행동 분리 (2606.15285) | VLA | 저주파 이해 모듈이 의미 조건을 비동기 갱신, 고주파 행동 모듈이 **낡은 의미 조건** 아래 계속 동작. 낡음 대책 = 최근 행동 이력 조건화 + 시간 어긋남 학습(초록) | LOW(학회 미확인) | 안 | 예(학습형) |
| WAM 실시간 연구 (2608.01880) | 로봇 | 관측·예측·실행 **시간 정렬이 먼저**(v3/14) | LOW-MED(arXiv만, 저자 "Motubrain Team", 학회 표기 없음. M5와 통일, §25 D13) | 안 | 예 |
| Raft term / 낙관적 동시성 제어 | 분산 시스템 | 버전(term) 낮은 명령 거부 | 기초(비유) | 기간 밖 | — |

### 2.3 계획 정적 검증 (D4 교차 분야, 00-interfaces §14-4·§15)
| 이름 | 분야 | 어디서 최고였나 (조건, 위치) | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| **Agentproof** (2603.20356) | LLM 에이전트 워크플로 정적 검증 | 워크플로 그래프를 공통 추상 그래프로 뽑아 구조 검사(막다른 노드, 도달 불가 출구 등) + **7형식 시간 정책 DSL**을 DFA로 컴파일. 7형식은 모두 **본문 DSL 절**에 있다: (1) Forbidden `G !a` (2) Implication-future `a -> F b`(a가 다시 오기 전에 b) (3) Until `a U b` (4) Bounded response `a -> F[<=k] b` (5) Response chain (6) Conjunction (7) Disjunction. 부록 B는 BNF 전체다. 정적 검사는 그래프 × DFA 곱, 실행 중 검사는 사건열 위에서 같은 DFA로. 작성자가 만든 워크플로 18개 중 27%에 구조 결함, 55%에 사람 승인 정책 위반. 정책 15개가 모두 7형식 안에 들어갔고, 5,000 노드까지 1초 미만(초록). 원문 스스로 "유병률 연구가 아니다"라고 한정한다 | LOW (무학회, 인용 10. 저자는 1저자 Luleå 공대 + 독립 연구자 3명 — D4 첫 판의 "독립 연구자"와 "6·7번 형식은 부록 B"는 D4 검증 #6에서 정정) | 2026-03-20, 기간 안 | 예(검증기, 학습 없음) | 아니오 |
| 명세 패턴 + 런타임 검증 (Dwyer 외 ICSE 1999; LTL → 오토마타 감시, Bauer·Leucker·Schallhart TOSEM 2011) | 형식 검증 | 시간 논리 명세를 소수 패턴으로 제한하고 오토마타로 감시하는 기초 이론 | 기초 문헌(이번 라운드와 D4 검증 모두 원문은 읽지 않음) | **기간 밖, 기초 문헌** | 예 | 로봇 LTL 계획에는 있음. 우리 Jev 계약 검사로 쓴 사례는 확인 못 함 |

### 2.4 API 일관성·재계획 고정 (정본 §28, `D17-api-consistency.md`)
등급은 D17 조사 기준(user-log 14)을 그대로 옮겼다. 메인이 원문을 다시 확인한 것은 이 표의 2506.09501·2604.24039·2506.14852(그 밖에 2512.03816·2509.01790)뿐이고, 나머지 인용문은 조사 에이전트가 요약 도구로 뽑은 것이라 본문 반영 전 원문 대조가 필요하다(D17 머리). D17 §2의 LOW 12편은 근거로 쓰지 않는다. MED-LOW 보조(2603.19022·2602.04297·2609.19654·2511.02603)도 이 표에 넣지 않았다.

| 이름 | 분야 | 어디서 최고였나 (조건) | 신뢰도 | 기간 | 학습 없이 | 로봇 |
|---|---|---|---|---|---|---|
| **Yuan 외** (2506.09501) | LLM 추론 재현성 | "under bfloat16 precision with greedy decoding, a reasoning model like DeepSeek-R1-Distill-Qwen-7B can exhibit up to 9% variation in accuracy and 9,000 tokens difference in response length due to differences in GPU count, type, and evaluation batch size." 추론 모델일수록 심하고 초기 토큰의 반올림 차이가 번져 나간다. 서버 쪽 해결(LayerCast)은 우리가 쓸 수 없다 | HIGH(NeurIPS 2025 Oral — 저자 저장소 README에서 확인, abs에는 표기 없음. HF 20, 코드 118★) | 안(v1 2025-06-11) | — | 아니오 |
| Atil 외 (2408.04667) | LLM 반복성 | "accuracy variations up to 15% across naturally occurring runs", "none of the LLMs consistently delivers repeatable accuracy across all tasks." 결정적 설정의 반복 불일치 지표 TARr@N/TARa@N | MED(S2 인용 126) | **기간 밖(2024-08-06), 기초 문헌** | — | 아니오 |
| Messina·Scotta (2604.22411) | LLM 반복성 측정 | T=0의 "background temperature" 추정: 프롬프트마다 T=0으로 M ≥ 50회, exact-match 비율과 K-S 거리. 시범값 gpt-4.1-nano 0.075, gemini-2.0-flash 0.065, claude-sonnet-4 0("identical") | MED(journal-ref TMLR 2026-02, RAI CRITS) | 안(v1 2026-04-24) | — | 아니오 |
| Bjarnason·Silva·Monperrus (2602.07150) | LLM 에이전트 평가 | "single-run pass@1 estimates vary by 2.2 to 6.0 percentage points". T=0에서도 표준편차 > 1.5pp. 2%p 차이 검출에 약 9회, 1%p면 36회 | MED(KTH, ICLR 2026 Workshop Agents in the Wild, HF 2, 9★) | 안(v1 2026-02-06) | — | 아니오 |
| ReasonBENCH (2512.07795) | LLM 추론 분산 | "the inter-quartile range at T=0 is comparable to—and in several cells wider than—the range at T=0.7", "Spending more on test-time reasoning reliably increases cost, but buys neither higher quality nor lower variance." 권장 반복 n = 30(최소 n ≥ 9) | MED(Aarhus·EPFL·IIT Delhi, 학회 없음, HF 1) | 안(v1 2025-12-08) | — | 아니오 |
| Chen·Zaharia·Zou (2307.09009) | 호스트 모델 표류 | "GPT-4 (March 2023) … 84% accuracy … GPT-4 (June 2023) … 51%", "highlighting the need for continuous monitoring of LLMs." | HIGH-기초 | **기간 밖(2023-07-18), 기초 문헌** | — | 아니오 |
| FormatSpread (Sclar 외, 2310.11324) | 프롬프트 형식 민감도 | "performance differences of up to 76 accuracy points when evaluated using LLaMA-2-13B". 형식 하나가 아니라 여러 형식에 걸친 범위를 보고하라고 권함 | HIGH-기초(ICLR 2024) | **기간 밖, 기초 문헌** | — | 아니오 |
| Mind the Gap (2509.15020) | 객관식 라벨 토큰화 | 라벨 문자 앞 공백을 어떻게 토큰화하느냐만으로 정답률 최대 11%, 보기 순서를 바꾼 효과보다 큼 | HIGH(EMNLP 2025 Main, HF 4) | 안 | — | 아니오 |
| Rosenfeld·Glazer·Fetaya (2511.11206) | VQA 안정성 | GPT-4o는 패딩·크롭만으로 인스턴스의 0.08이 답을 바꿨고 섭동 전체로는 0.14. 모든 섭동에 안정한 표본의 정답률 0.91 대 기준 0.78 | MED(Bar-Ilan, 학회 없음, HF 1) | 안(v1 2025-11-14) | — | 아니오 |
| **The Format Tax** (Lee·D'Antoni·Berg-Kirkpatrick, 2604.03616) | 구조화 출력 | "format-requesting instructions alone cause most of the accuracy loss, before any decoder constraint is applied". 오픈 가중치 평균 −3.9pp, GCD 추가 −1.6pp. 자유 서술 후 2턴째 형식 변환이 72개 비교 중 42개에서 유의하게 나음(평균 +6.8pp), extended thinking 평균 +9.2pp. "most recent closed-weight models show little to no format tax" | MED(UCSD, 학회 없음, HF 0) | 안(v1 2026-04-04) | — | 아니오 |
| **AgenticCache** (2604.24039) | 체화 에이전트 계획 캐시 | "embodied tasks exhibit strong plan locality, where the next plan is largely predictable from the current one". 예: "go grasp target" 다음이 "put into container"인 경우 59.7%. 성공률 +22%, 지연 −65%, 토큰 −50%. 백그라운드 LLM이 k스텝 뒤 실제 실행 궤적과 비교해 캐시를 검증 | HIGH(MLSys 2026, SNU·Stanford) | 안(v1 2026-04-27) | — | 체화 과제 |
| **Agentic Plan Caching** (2506.14852) | LLM 에이전트 | 구조화된 계획 템플릿을 저장·적응·재사용해 비용 −50.31%, 지연 −27.28% | HIGH(NeurIPS 2025) | 안(v1 2025-06-17) | — | 아니오 |
| From Plan to Action (Liu 외, 2604.12147) | LLM 에이전트 궤적 분석 | 궤적 21,120개. "periodic plan reminders can mitigate plan violations". 초반에 모델 전략과 맞지 않는 단계를 넣으면 성능이 떨어짐 | MED-HIGH(UIUC·IBM, ACM DOI 10.1145/3832783.3834400, 학회 이름 미확인) | 안(v1 2026-04-13) | — | 아니오 |

---

## 3. 가져올 것과 접목 방법 (원문 / 우리 접목안 분리)

| # | 원문 | 우리 접목안 [제안] | 옮길 때 주의 |
|---|---|---|---|
| 1 | COPE: 작은 실행기에는 목표형 > 절차형(1B 자기 계획 조건)뿐. 큰 → 작은 이득은 절차형(§25 D13 정정) | Jev에 가는 계약 조각의 중심 = **완료 술어(무엇이 참이 되어야 하나)**. (§25 D13 정정) 이 기본값의 근거는 COPE가 아니라 **설계 선택**이다(M4·M7·M9가 술어를 읽어야 하는 구조, AgentSpec 술어 모양). COPE는 오히려 큰 계획기의 짧은 절차가 작은 실행기를 돕는다는 반대 방향이라 E-M2-1 B-COPE로 잰다. 절차 서술은 스킬 이름으로만. Astra 자유 서술 `rationale`은 코드·로그용이고 Jev에는 기본으로 보내지 않는다(E-M2 조건으로 시험) | 큰 계획기가 목표형을 준 조건은 원문에 없고, 그 조건의 이득은 절차형에서 나왔다(§25 D13) |
| 2 | PlanAhead(보조): 최적 계획 형식이 실행기 모델마다 다름(STC 구간은 넓고 AR은 안정적) | "어느 형식이 최고"를 문헌에서 옮기지 않고 **Jev로 잰다**(E-M2 형식 축). 기본을 typed 술어 목록으로 두는 이유는 PlanAhead가 아니라 M4·M7·M9가 술어를 읽어야 하는 우리 구조와 AgentSpec(HIGH)의 술어 DSL이다 | 인용 0, 투고 중 → 보조 참고로만(00-interfaces §11.3), 웹 과제 |
| 3 | Magentic-One: 과제 원장(사실·추측·계획) / 진행 원장(완료? 반복? 전진? 다음? 지시?) | 계약 = **과제 원장**(Astra가 씀). 진행 원장의 다섯 질문은 우리 구조에서 **코드 critic(M7)과 Jev typed 질문으로 나뉜다**: 완료 = `exit_k` 코드 판정, 반복·전진 = M7 정체 규칙, 다음 행동 = Jev M3 질문. Astra의 "추측"은 `assumptions`(가정 술어)로 분리해 코드가 매 틱 검사(거짓 → M7 `C_assume`) | 기간 밖 기초 문헌. 원문은 한 LLM이 다섯 질문에 답한다. 우리는 느린 Astra를 루프에서 뺀다 |
| 4 | AgentSpec: 트리거 + 술어 + 집행 | 계약의 `forbidden`·`monitors` 칸을 이 모양으로: `{when: <트리거>, check: <술어>, enforce: fail / skip / escalate}`. 집행은 코드. `fail`은 직접 정지가 아니라 M7 하드 채널 신호다(`00-interfaces.md` §4: FAIL은 M7만). Jev에는 금지 술어의 **현재 값**만 보인다 | 원문 주 수치는 사람이 쓴 규칙(그것도 안전 과제 수행을 58.62 → 54.26%로 깎음). (§25 D13 정정) LLM(o1) 생성 규칙은 처음 보는 위험 사례 집행률(원문 "precision") 95.56%, 안전 짝 사례로 낸 "recall" 70.96%(원문 정의 모호, 놓침과 과차단(pour 전면 금지)을 함께 설명. "약 3할 놓침"은 원문에서 바로 나오지 않음) → Astra `forbidden`만 믿지 않고 M7 하드 층(스킬 오류·T1 불변)과 코드 안전 규칙을 독립으로 둔다. 이유는 놓침에 더해 **과차단**(정상 행동을 막아 오경보 FAIL·재호출로 이어짐). `enforce: fail`은 T1 술어에만 허용(검사기 2c) |
| 5 | Code-as-Monitor: VLM이 제약을 코드로, 실시간 평가 | 어휘에 없는 술어가 필요하면 Astra가 `custom_predicates`에 **작은 코드 식**(허용된 기하 함수만 쓰는 DSL)을 적고, 코드가 평가해 참/거짓만 Jev에 넣는다 | 임의 코드 실행 금지 — 허용 함수 목록(거리, 각도, 포함, 접촉, 속도)만 |
| 6 | Anthropic 네 요소, MAST "종료 조건 모름" | 계약 필수 칸 검사: 목표(`exit`), 출력 형식(Jev 질문의 보기 집합), 도구(스킬), **경계**(`forbidden`, `scope`). 완료 술어 없는 단계는 검사기가 거부 | — |
| 7 | 계층 시연(워크숍): 이름 붙은 계층 하위목표가 모호한 지시에서 도움 | 원장은 **단계(stage) → phase 2층**, 각각 짧은 영어 이름. phase 목록은 바인딩된 M6 스킬 계약의 `phases`(스킬 고정). M9 "거친→세밀 재개점"(RIR)과 같은 2층 | LOW-MED |
| 8 | 검증된 도구 호출: 사후조건 검증, 재시도 전 검증, 멱등 키 | 각 단계의 `exit`(= `exit_k`)는 **스킬이 "끝났다"고 돌려줘도 코드가 측정 술어로 다시 확인**. 재시도 전 `exit`가 이미 참이면 재시도하지 않는다(중복 잡기 방지). 단계 ID = 멱등 키 | LOW — 발상만 |
| 9 | AgileThinker 축소판: 계획의 **최종 출력만** 참조, 반응 쪽은 계속 결정. 압박이 셀 때(4k·8k)만 이득 | Astra 응답을 기다리지 않는다. Jev는 **항상 가장 최근에 게시된 계약 버전**으로 결정하고, 새 버전이 오면 다음 결정 스텝부터 교체. Jev 입력에 `contract: c7 (based_on f1100, age 6.2s)`를 적어 낡음을 드러낸다 | Astra 추론 흔적은 볼 수 없다(OpenAI 추론 모델). 이득이 압박 조건에서만 나왔다는 점을 과장하지 않는다 |
| 10 | Slow Brain: 가장 새 답 + 감쇠 융합 | 계약은 **융합하지 않는다**(계약은 구조물이라 평균이 없다). 대신 "가장 새 **유효** 계약" 규칙: 새 계약이 기준 상태(`based_on`) 이후 바뀐 사실과 충돌하면(가정 술어 거짓) 게시하지 않고 M8에 재호출 신호(실행 중 가정이 거짓이 되면 M7 `C_assume`) | 비교 조건 C2로 남긴다(M4 문서) |
| 11 | WAM: 시간 정렬 먼저 / Raft term | 계약에 `based_on_t_state` 필수, 게시 시 `contract_version` 증가 → **M4 `premise_epoch`도 증가**(00-interfaces §11.2로 확정, D2 B6) | — |
| 12 | 2606.15285: 낡은 의미 조건 아래 최근 행동 이력으로 버팀(학습형) | 학습은 못 옮긴다. 옮길 수 있는 것: 낡은 계약 아래에서는 Jev 질문에 **최근 확정 행동 2~3개**를 함께 보인다(M4 원장에서) | LOW, 학습형 |
| 13 | **Agentproof**(LOW, §2.3): 추상 그래프 구조 검사 + 7형식 DSL → DFA. 정적으로는 그래프 × DFA 곱, 실행 중에는 사건열 위 같은 DFA | **우리 접목안** (1) 계약 게시 전 구조 검사: 모든 단계가 `goal`까지 도달 가능한지, 막다른 단계가 없는지(§4.1 검사기 5). (2) `forbidden`·순서 제약을 7형식 부분집합으로만 쓰게 하고 DFA로 컴파일한다. 실행 중에는 **같은 DFA**가 H5와 `C_assume`를 함께 감시한다(§4.4). (3) 검사 실패 문장을 Astra에 되돌리는 수리 왕복은 **T0에서만** 한다(00-interfaces §14-4) | 원문 대상은 사람이 만든 에이전트 워크플로다. LLM이 쓴 계약도, 로봇 시간 제약도 대상이 아니다. 수치는 18개 표본이고 원문도 유병률 연구가 아니라고 적었다 → **설계 근거의 주축은 기초 문헌이고 Agentproof는 보조**다 |
| 14 | 명세 패턴·런타임 검증(기간 밖, 기초 문헌): 명세를 패턴으로 제한 → 오토마타 감시 | 제약 표기를 패턴으로 제한하는 이유(표현력보다 검사 가능성 우선)의 근거. M7 하드 채널 H5(T1 술어만)의 `enforce: fail` 감시를 DFA 진행으로 구현 | 원문 미확인(§8). 패턴 밖 제약이 얼마나 나오는지는 E-M2-3에서 잰다 |

---

## 4. 설계안

### 4.1 1순위: 세션 계약 v1 (목표 중심 + 가정 술어 + 버전)

필드(모두 영어 값, 술어 이름은 M1 어휘):

| 필드 | 뜻 | 누가 쓰나 / 누가 읽나 |
|---|---|---|
| `contract_id`, `version`, `parent_version` | 버전 사슬 | 코드 / 전 모듈 |
| `based_on_t_state` | Astra가 본 프레임·시각 (SoM 이미지와 M1 텍스트의 `t_state`) | Astra / M4(epoch)·Jev(나이 표시) |
| `goal` | 과제 전체 완료 술어 집합 | Astra / M7 |
| `relevant_ids`, `relevant_predicates` | M1 관련도 필터 입력 | Astra / M1 |
| `objects` | ID별 역할 한 단어(`target`, `container`, `obstacle`)와 Astra가 본 속성(T3 술어 초깃값, 측정 시각 붙음) | Astra / M1(T3 캐시), Jev |
| `assumptions` | 계획이 기대는 가정 술어(물체 존재, 경로 비어 있음, 뚜껑 닫힘 등). **거짓이 되면 계약이 낡은 것** | Astra / 코드가 매 틱 검사 → 거짓(0.5초 연속)이면 **M7 소프트 채널 `C_assume`** + 동시에 **M8 재호출 요청 신호**(00-interfaces §11.2, D2 B5). FAIL은 M7만 낸다 |
| `stages[]` | 단계 원장 = **스킬 인스턴스**. 각 단계: `id`, `name`, `skill`, `entry`, `exit`, `invariants`, `stop`, `T_exp_s`, `phases[]`, `decision_points[]`, `checkpoint`(true면 M9 재개점), `irreversible`(true면 M8 T2 순간). 필드 이름은 M6 스킬 계약과 같다(00-interfaces §11.1: 옛 `pre/done/inv/substeps`). `phases`는 스킬 계약에서 복사(읽기 전용), `entry`/`exit`/`invariants`는 스킬 계약 술어에 인자를 채운 것 + Astra가 더한 단계 술어. `T_exp_s`는 단계 전체 예상 시간(M7 마감 대체값)이고 M6 `budget`은 phase별 상한이다(다른 양) | Astra / M3·M4·M6·M7·M8·M9 |
| `decision_points[]` | **바인딩된 스킬 계약(M6)에 고정된 결정 지점 id를 골라 쓰고 인자만 채운다**: `{dp, args, when?}`. `dp`는 스킬 계약 `decision_points` 안의 id(예: `dp.approach_dir`)만, `args`는 질문 자리표시자(예: `target: o3`), `when`은 스킬 기본 트리거를 좁힐 때만. Astra는 **새 id·새 보기를 만들지 않는다**(보기는 스킬 inputSchema enum + M3 `NONE_ESCALATE`). M10 Jev 규칙 키도 이 id(00-interfaces §11.1, D2 B1) | Astra 선택 + 코드가 보기·예상 결과 술어 채움 / Jev(M3) |
| `forbidden[]` | `{when, check, enforce}`(AgentSpec 모양) | Astra / 코드 집행, Jev는 현재 값만 |
| `expected_failures[]` | 예상 실패 목록(`slip_during_transport`, `grasp_miss` 등)과 권장 아래 층 대응 | Astra / M9(ID 판정) |
| `custom_predicates[]` | 어휘 밖 술어를 허용 DSL로(`dist(o3.rim, o9.spout) < 0.02`) | Astra / 코드 평가 → M1 facts |
| `rationale` | Astra 자유 서술(2~3문장) | Astra / 로그·M10. **Jev 기본 입력에서 제외**(E-M2에서 시험) |

예(단순 배치 과제, 계약 전체 — 코드가 보는 것):
```json
{
  "contract_id": "ep42", "version": 7, "parent_version": 6,
  "based_on_t_state": "f1100",
  "goal": ["on(o3,o5)"],
  "relevant_ids": ["o3", "o5", "o8"],
  "relevant_predicates": ["holding", "above", "near", "aligned_xy", "in_contact", "on", "touch"],
  "objects": {"o3": {"role": "target", "attrs": {"contents": "empty@f1100"}},
              "o5": {"role": "container"}, "o8": {"role": "obstacle"}},
  "assumptions": ["exists(o3)", "exists(o5)", "path_clear(gripper->o3)", "clear(o5)"],
  "stages": [
    {"id": "S1", "name": "grasp mug", "skill": "pick-top-grasp", "entry": ["not holding(any)"],
     "exit": ["holding(o3)", "lifted(o3)"], "invariants": [], "stop": ["holding(o3)"], "T_exp_s": 6,
     "checkpoint": true, "irreversible": false,
     "phases": ["approach", "align", "grasp", "lift"],
     "decision_points": [{"dp": "dp.approach_dir", "args": {"target": "o3"}},
                         {"dp": "dp.grasp_commit", "args": {"target": "o3"}}]},
    {"id": "S2", "name": "place mug on tray", "skill": "place-on", "entry": ["holding(o3)"],
     "exit": ["on(o3,o5)", "not holding(o3)"], "invariants": ["holding(o3)"], "stop": ["in_contact(o3,o5)"],
     "T_exp_s": 8, "checkpoint": true, "irreversible": true,
     "phases": ["approach", "align", "lower", "release"],
     "decision_points": [{"dp": "dp.align_commit", "args": {"target": "o5"}, "when": "near(o3,o5)"},
                         {"dp": "dp.release", "args": {"target": "o5"}}]}
  ],
  "forbidden": [{"when": "always", "check": "touch(o8)", "enforce": "fail"},
                {"when": "stage==S2", "check": "not tilt_ok(o3)", "enforce": "escalate"}],
  "expected_failures": [{"event": "grasp_miss", "lower_layer": "retry_grasp_once"},
                        {"event": "slip_during_transport", "lower_layer": "stop_and_regrasp"}],
  "custom_predicates": [],
  "rationale": "Handle faces away; top grasp is safer. Tray rim on far side, approach from near side."
}
```
(`tilt_ok(o3)`는 M1 등록부 T1 술어이고 문턱(30°)은 설정 표에 있다. 숫자 비교는 **코드**가 하고 Jev는 `tilt_ok(o3)=yes/no`만 본다. 스킬 이름 `pick-top-grasp`·`place-on`과 `phases`는 M6 스킬 계약의 것이고, 결정 지점은 그 스킬의 고정 id 중에서 고른 것이다. 옛 판의 `S1.target_part`처럼 Astra가 만든 id는 더 쓰지 않는다 — 부품 선택이 필요하면 M6에 스킬 고정 id를 추가하는 오프라인 경로로.)

Jev가 실제로 받는 조각(M1 상태 앞에 붙음, 현재 단계 S2 기준):
```
contract: ep42 v7 (based_on f1100, age 6.2s)  assumptions: all_true
goal: on(o3,o5)
stage S2 "place mug on tray" [phase: align]  exit_when: on(o3,o5) and not holding(o3)
forbidden now: touch(o8)=no  tilt_ok(o3)=yes
recent committed: approach, approach, align(+x)
```

계약 검사기(코드, 게시 전)
1. JSON 스키마·필수 칸(각 단계 `exit` 비지 않음) 검사. 실패하면 **T0(첫 계획, 정지 허용 구간)에서만** Astra에 검사기 오류 문장을 되돌려 고치게 한다(수리 왕복, 00-interfaces §14-4). 실행 중 재계획(patch·전체 계약 모두)은 왕복하지 않고 검사만 한다(§4.2 R7). 참고: MCP 명세에서 `outputSchema` 준수는 서버 MUST이지만 **클라이언트 검증은 SHOULD(권장)**다(D2 A1). 우리가 검사를 필수로 두는 것은 우리 설계 선택이지 MCP가 요구해서가 아니다.
2. 모든 술어 이름이 M1 술어 등록부(M1 §4.0) 또는 `custom_predicates` 안에 있는지. 수치 인자가 이름에 붙은 술어(`>=3cm`)는 거부(문턱은 설정 표).
   - 2b. 모든 `decision_points[].dp`가 그 단계 `skill`의 스킬 계약 `decision_points` 안에 있는지(새 id 거부).
   - 2c. `forbidden[].enforce == fail`의 `check` 술어가 등록부 **T1**인지. T2·T3이면 `escalate`로 바꾸라고 되돌림(M7 하드 채널은 T1만, 00-interfaces §11.2).
3. `based_on_t_state` 이후 바뀐 사실(M1 변화 기록) 중 `assumptions`와 충돌하는 것이 있는지 → 있으면 게시 보류 + M8 재호출(낡은 계약).
4. 첫 단계 `entry`가 지금 측정 상태에서 참인지(거짓이면 M9 재개점 계산으로 넘김).
5. 구조 검사 [우리 접목안, Agentproof 구조 검사를 옮김]: 단계 그래프에서 모든 단계가 `goal`(마지막 단계 `exit`)까지 도달 가능한지, 나가는 전이가 없는 비종료 단계(막다른 단계)가 없는지, 인접 단계에서 `exit_k ⇒ entry_{k+1}`이 성립하는지(M6 §3 `entry` 행과 같은 검사).
6. `forbidden[]`·순서 제약이 §4.4의 허용 패턴으로만 쓰였고 DFA로 컴파일되는지. 컴파일이 안 되면 검사 실패다. 정적으로는 단계 그래프 × DFA 곱에서 "모든 경로가 제약을 어기는" 단계가 있으면 거부한다.

수리 왕복 규칙 (00-interfaces §14-4)
- **T0**: 검사 1~6 중 실패가 있으면 오류 문장(어느 필드, 어느 술어·id, 어느 패턴이 왜 틀렸나)을 Astra에 되돌린다. 왕복 상한은 시작값 2회다([제안], E-M2-3으로 조정). 상한을 넘으면 같은 T0 안에서 새 계획 요청으로 바꾼다. T0는 정지가 허용된 구간이라 사용자 원칙과 충돌하지 않는다.
- **실행 중(T0 뒤)**: 왕복하지 않는다. 검사만 하고 결과는 §4.2 R7을 따른다.

### 4.2 낡은 계약 처리 규칙 (AgileThinker 축소판 + 버전)
- **R1 기다리지 않는다**: 첫 계약 전만 정지 허용([사용자]). 이후 Astra 요청 중에도 Jev는 현재 계약으로 계속 결정한다.
- **R2 가장 새 유효 버전만**: 계약 저장소는 버전 하나만 활성. 새 버전 게시 = 활성 교체 + **M4 `premise_epoch` +1**(이전 epoch의 미확정 표 폐기, M4 §4.2). 이 규칙은 00-interfaces §11.2("세션 계약 버전이 바뀌면 M4 `premise_epoch`를 올린다", D2 B6)로 확정됐다. 이미 확정·실행된 것은 되돌리지 않는다.
- **R3 교체 시점**: 결정 스텝 경계에서만 교체(M4 FROZEN 구간 안 스텝은 건드리지 않음). `irreversible` 단계 진행 중이면 그 phase 끝까지 기다린다(추론, 안전 쪽). phase가 비가역인지는 M6 `effect`로 읽는다(00 §14-3). **M8 commit 창과 M9의 Astra 계획 적용 시점도 이 R3 하나를 따른다**(D5 2-1). M6 `effect`에서 grasp·lift는 가역(보상 스킬 있음)이므로 "잡기 닫힘~들어올림 시작"을 따로 기다리지 않는다. 그리퍼가 닫히는 순간 자체는 설정 표의 grasp/release 전환 보류(1.0 s)와 결정 스텝 경계 규칙이 보호한다. 기다리는 동안에도 직전 확정 행동 유지 + 감속이며 정지가 아니다. 단계 수준 `irreversible`(Astra)과 M6 phase 수준 `annotations.irreversible_phases`(스킬 작성자)가 두 곳이다 → §7-4 [결정 필요]로 묶음(D2 B7).
- **R4 낡음 표시**: Jev 조각에 `age`와 `assumptions: all_true` 또는 `<거짓 목록>`을 항상 적는다. 거짓 가정이 있으면 모든 Jev 질문의 `NONE_ESCALATE`가 자연스러운 선택이 되도록 보인다. Jev가 무시해도 코드가 **M7 소프트 채널 `C_assume`**을 올리고 동시에 M8에 재호출 요청 신호를 보낸다(00-interfaces §11.2). FAIL 판정은 M7만 한다(다른 소프트 채널과 겹치면 FAIL, 혼자면 WARN).
- **R5 순서 뒤바뀜**: 늦게 보낸 요청의 답이 먼저 오면 `based_on_t_state`가 더 새 것만 받는다(Raft term 비유). 같은 기준 시각이면 나중 도착 것.
- **R6 부분 갱신**: 재계획 때 Astra가 전체 계약 대신 `patch`(바꿀 단계만, `parent_version` 명시)를 낼 수 있다. 검사기는 patch 적용 결과를 전체 검사. 목적: Astra 출력 토큰·지연 감소(추론, 측정 필요). (정본 §28 A4) 실행 중 재계획의 **잠정 기본** 출력으로 승격했다 — 입력·`change_reason`·실행한 단계 변경 금지·편집 거리 기록은 §4.5 A4. 전체 계약 재요청은 예외·비교 조건으로 남는다(E-M2-3 추가 판정 (2)).
- **R7 실행 중 patch는 검사만** (00-interfaces §14-4): 실행 중 재계획으로 온 patch(또는 전체 계약)는 적용 결과에 검사기 1~6을 돌린다. 하나라도 실패하면 (i) patch를 **거부**한다. 활성 계약과 M4 `premise_epoch`는 그대로다. (ii) M7에 `contract_patch_rejected` 사건 신호를 보낸다. 이 사건은 M7 소프트 채널 **`C_assume`**로 센다(00 §15, 확정. 새 채널을 만들지 않는다). (iii) 로봇은 멈추지 않는다. 직전 확정 행동을 유지하며 현재 계약으로 계속 간다. 오류 문장은 로그와, M8이 정한 다음 Astra 호출의 입력에 싣는다. 이 patch를 고치려고 따로 왕복하지는 않는다.

### 4.3 대안
- **대안 B (절차 포함형)**: 각 단계에 Astra의 절차 서술(`how`: "approach from the near side, lower slowly")을 Jev 조각에도 넣는다. (§25 D13 정정) COPE는 큰 → 작은 방향에서 오히려 절차형이 도왔으므로, 이 조건은 "COPE 결과의 반대 방향"이 아니라 COPE 쪽 방향을 우리 데이터로 확인하는 조건이다.
- **B-COPE (COPE 원문 모양)**(§25 D13): v1 조각 + Astra 절차 1~2문장("strategy and key ideas", COPE 원문 절차형 프롬프트 모양). 대안 B보다 짧고, 목표(v1 술어)와 절차를 함께 주는 COPE Stage 2 모양에 가깝다.
- **대안 C (체크리스트만)**: `stages[].exit`만 체크리스트로(스킬·결정 지점 없음), Jev가 다음 단계를 스스로 고른다. PlanAhead 체크리스트형(보조 참고)·Magentic-One 진행 원장에 가까움. 스킬 결합(M6)을 느슨하게 할 때의 비교 조건.
- **대안 D (서사형)**: Astra 자연어 계획 문단 하나(PlanAhead 서사형, GPT-4.1-mini에서 최선이었던 것 — 보조 참고, Hard AR 절대값 1~11%로 낮음). typed 칸이 없어 M4·M7·M9가 쓸 술어가 없으므로 **Jev 판단 정확도 비교에만**.

### 4.4 제약 표기와 DFA 감시: H5와 `C_assume` 통일 (00-interfaces §14-4)

원문 (Agentproof §DSL, D4 검증 #6 확인)
- 7형식 DSL(§2.3 표)의 정책을 DFA로 컴파일한다. 정적으로는 그래프 × DFA 곱으로, 실행 중에는 사건열 위에서 **같은 DFA**로 검사한다.
- 기초 문헌(기간 밖): 명세 패턴(Dwyer 외 1999)과 LTL → 오토마타 런타임 검증(Bauer 외 2011). 원문 미확인.

우리 접목안 (잠정 기본: 근거의 주축이 기간 밖 기초 문헌이라 [결정 필요] 4 사용자 승인 전까지 잠정, 00 §16. 불허하면 `forbidden`은 술어별 감시로 두고 H5·`C_assume` 통일만 뺀다)
- **허용 패턴**: `forbidden[].check`와 순서 제약은 Agentproof 7형식으로만 쓴다. Forbidden `G !p`, Implication-future `a -> F b`, Until `a U b`, Bounded response `a -> F[<=k] b`, Response chain, 그리고 이들의 Conjunction·Disjunction이다. 원자 명제는 M1 등록부 술어(인자 채움)와 단계 사건(`enter(S2)`, `exit(S1)`)뿐이다. `when`은 앞에 붙는 조건(`G(when -> ...)`)으로 컴파일한다. AgentSpec 모양 `{when, check, enforce}`는 그대로 둔다.
  - 예: `{"when": "always", "check": "G !touch(o8)", "enforce": "fail"}`, `{"when": "stage==S2", "check": "enter(release) -> F[<=2s] not holding(o3)", "enforce": "escalate"}`.
- **컴파일**: 코드가 제약마다 DFA를 만든다. 게시 전에는 §4.1 검사기 6의 정적 곱 검사를 하고, 실행 중에는 10 Hz 틱마다 술어 전이 사건으로 DFA를 한 칸씩 진행한다.
- **감시 통일**: `assumptions[]`도 같은 감시기에 넣는다. 가정 `p`는 `G p`로 둔다. 감시기 하나가 모든 DFA를 돌리고, 거부 상태에 들어간 DFA만 채널에 배정한다.
  - `enforce: fail`이고 원자 술어가 **모두 T1** → M7 하드 채널 H5(00-interfaces §11.2).
  - `enforce: fail`인데 T2·`unknown` 원자가 섞였거나 `enforce: escalate` → 소프트 채널. 검사기 2c가 게시 전에 막으므로 실행 중에는 `unknown` 전이만 해당한다.
  - `assumptions` DFA의 거부(0.5초 연속) → `C_assume` + M8 재호출 요청 신호. 지금 규칙과 같다.
  - 감시기는 **신호만** 낸다. FAIL은 M7만 내고 정지는 M7 FAIL을 거친다(00-interfaces §4).
- 한정 응답 `a -> F[<=k] b`는 M8 T3a "예상 시간 마감"과 모양이 같다. **표기만 공유**하고 마감 판정의 소유(M7 마감 채널, M8 T3a)는 바꾸지 않는다.
- 옮길 때 깨지는 가정: 원문은 사람이 쓴 워크플로의 이산 사건이다. 우리 사건은 술어 전이라 인식 잡음이 섞이므로, T2 술어에는 지금 규칙대로 지속 시간 조건을 둔다. 7형식이 Astra가 쓰고 싶은 제약을 다 담는지는 모른다 → E-M2-3에서 "패턴 밖 제약 비율"을 잰다.

### 4.5 Astra 일관성 규약 A1~A6 (정본 §28, D17)
전제(정본 §28): API 모델은 temperature 0·seed로 결정성을 얻을 수 없다(추론 모델은 greedy에서도 정확도 최대 9% 변동 — 2506.09501, NeurIPS 2025 Oral). 효과 크기가 작은 비교는 반복 실행이 필요하다(2%p 차이 검출에 약 9회 — 2602.07150, MED). effort를 올려도 분산이 준다는 보장은 없다(2512.07795, MED) → 사용자 결정 "effort 기본 low, low·high 비교"는 그대로 두고 비교 때 분산도 보고한다.
- **A1 템플릿 고정**: `astra_prompt_id` = 해시(시스템 문장 + 계약 스키마 + 스킬 카드 + 술어 어휘 + 예시 계약 + 격자 렌더러 판본). 실험 도중 불변, 판본은 실험 사이에만 올린다. 매 호출 기록. 모델은 날짜 박힌 스냅샷 ID(가능하면, 별칭 대신), 응답의 모델 식별 필드를 기록한다([가정]: 필드 유무 미확인).
- **A2 입력 정규화**: 물체 id 순, 술어는 등록부 순, 숫자 고정 자릿수, 시각은 상대 범주. 격자 이미지(M8 §4.3)는 배치·해상도·패딩·덧그림 글꼴을 바이트 단위로 고정하고 프레임은 시간순. 정적 부분(시스템·스키마·카드)을 앞, 동적 부분(상태·프레임·실패 문맥)을 뒤에 둔다. 근거: 형식 민감도 FormatSpread(기간 밖 기초 문헌), 라벨 앞 공백만으로 최대 11%(2509.15020, EMNLP 2025), 패딩·크롭만으로 답이 바뀜(2511.11206, MED). §1 입력 표의 M1 상태 텍스트는 M1 직렬화기 정규화(정본 §28 J2)를 그대로 쓴다.
- **A3 출력**: 계약 JSON(§4.1) + 검사기 1–6 유지. "자유 계획 → 2턴 스키마 변환"은 E-M2-3 첫 시도 통과율 < 80%일 때만 비교 조건으로 넣는다(Format Tax 2604.03616, MED: 최근 폐쇄 모델은 형식 손실이 거의 없음).
- **A4 재계획 고정(잠정 기본, R6 승격)**: T0 이후 재계획은 활성 계약 + `based_on` 이후 변한 사실 목록 + 이미 VERIFIED·EXECUTING 단계를 입력으로 받고, 기본 출력은 `patch`다. 바꾸는 단계마다 근거 변화 사실 id(`change_reason`)를 붙이고, 이미 실행한 단계는 변경 금지, 편집 거리(바뀐 단계 수)를 기록한다. patch 적용 결과의 검사·거부는 R7 그대로. 근거: 체화 과제의 계획 지역성(AgenticCache 2604.24039, MLSys 2026), 계획 템플릿 재사용(2506.14852, NeurIPS 2025). 계약 요약을 Jev 조각에 계속 싣는 지금 설계(§4.1 조각)는 "periodic plan reminders"(2604.12147, MED-HIGH)와 같은 방향이다. 사용자 원칙("실패할 때마다 Astra 개입")은 그대로 — 부르는 방식이 아니라 받는 형식의 규칙이다.
- **A5 투표(잠정 기본)**: T0(정지 허용)에서만 effort low로 K = 3 병렬 호출하고, 계획 서명(단계 스킬 열 + 결정 지점 id + 물체 역할) 다수결로 고른다. 셋 다 다르면 검사기 통과 첫 번째 + `plan_unstable` 기록(추가 호출 없음). 비정지 호출(T_fail·T3)은 K = 1(지연을 늘리지 않음, 오류는 검사기·M4 (b)가 잡음). effort high 조건에서는 투표 안 함. K = 3은 설계 선택([가정])이고 E0 Astra 반복 결과로 확정한다(E 문서 §2). 같은 관측 반복은 분산만 줄이고 증거를 늘리지 않는다(PACT, 정본 §24). 호출 쪽 규칙은 M8 §4.2.
- **A6 재현 기록**: 요청 원문(이미지 바이트 해시 + 원본), `astra_prompt_id`, 모델 ID, effort, 최대 토큰, 사용량, 첫 토큰·완료 시각, 원응답, 검사기 결과, 계획 서명, patch 편집 거리.

---

## 5. 비교 실험 (판정 기준 사전 등록)

### E-M2-1 전달 형식 (오프라인, M1 E3와 같은 스냅샷 재사용)
- 조건: 1순위 v1 조각 / v1 + `rationale` / 대안 B(절차 포함) / **B-COPE(v1 + Astra 절차 1~2문장, §25 D13)** / 대안 C(체크리스트만) / 대안 D(서사형). 모두 같은 Astra 계약에서 기계적으로 만든다(Astra 호출 1회, 형식만 바꿈).
- 질문: M1 E3의 Q1~Q4 + Q5 "지금 단계가 끝났나"(`exit` 술어가 참/거짓/모름), Q6 "다음 단계로 넘어가도 되나".
- 지표: 정답률, `NONE_ESCALATE` 비율, 입력 토큰, Jev 지연.
- 판정(실행 전 고정):
  1. v1 + `rationale`이 v1보다 2%p 이상 높지 않으면 `rationale`은 Jev 입력에서 뺀다(관련 없는 내용 원칙).
  2. 대안 B 또는 **B-COPE**가 v1보다 3%p 이상 높으면 [결정 필요]로 올린다(절차 서술이 Jev에도 도움. COPE 원문의 큰 → 작은 절차형 이득과 같은 방향, §25 D13).
  3. 대안 C가 Q6에서 v1보다 5%p 이상 낮으면 "단계 전이는 코드가 `exit`로" 규칙 유지.
  4. 대안 D가 v1보다 높아도 typed 칸이 없으므로 채택하지 않고, 차이를 "typed화 비용"으로 보고한다.
  5. 부트스트랩 95% 구간이 겹치면 "차이 없음".

### E-M2-2 낡은 계약 처리 (시뮬 폐루프)
- 조건: W 기다림(Astra 응답까지 정지) / L 가장 새 계약 즉시 교체(R2, 가정 검사 없음) / L+A R1~R5 전부(1순위) / F Slow Brain식(여러 요청, 가장 새 답, 가정 검사 없음).
- 섭동: 계획 도중 물체 밀기(가정 `path_clear` 깨짐), 목표 물체 이동, Astra 지연 인위 증가(low/high effort 실측 분포에서 뽑음 — 기본은 low, high는 비교 조건, 정본 §26).
- 지표: 성공률, 완료 시간, 정지 시간, 낡은 계약으로 실행한 결정 스텝 수(가정 거짓인데 실행), 계약 교체 뒤 epoch 폐기 표 수, `C_assume` 발동 수와 그중 M7 FAIL로 이어진 수, Astra 호출 수.
- 판정(실행 전 고정):
  1. L+A가 W보다 성공률이 3%p 이상 낮지 않고 정지 시간이 50% 이상 짧으면 1순위 유지.
  2. L+A가 L보다 "가정 거짓 상태 실행 스텝"을 절반 이하로 줄이지 못하면 `assumptions` 검사를 단순화(존재·경로만).
  3. F가 L+A보다 성공률 3%p 이상 높으면 [결정 필요](융합 방식 채택 여부).
  4. 각 조건 에피소드 ≥ 50, 3개 시드, 평균 ± 표준편차.
  5. (§25 D13) L+A 대 L의 차이를 **Astra 지연 구간별**(낮은 지연·높은 지연)로 따로 보고한다. AgileThinker Table 10에서 압박이 약한 16k에서는 결합이 반응 단독보다 낮았다(0.70 대 0.76). 낮은 지연 구간에서 L+A가 L보다 낮으면 기본값을 바꾸지 않고 그 사실을 보고한다.

### E-M2-3 계약 품질 (Astra 쪽, 부수)
- 측정: 검사기 통과율(첫 시도 / 재요청 후), 등록부 밖 술어 비율, 스킬 밖 결정 지점 id 거부 수(검사기 2b), `enforce: fail`에 T2·T3 술어를 쓴 비율(2c), `T_exp_s` 대 실측 단계 시간 비율(M7 `D_k` 대체값 1.5×T_exp의 근거), 가정 술어 누락으로 인한 실패 수.
- 판정: 첫 시도 통과율 < 80%면 계약 스키마를 줄이거나(필수 칸만) 예시 계약을 프롬프트에 넣는 조건을 추가 시험.
- (§25 D13) **`forbidden` 과차단률**: 정상 성공 에피소드 중 `forbidden` DFA가 거부 상태에 들어간 에피소드의 비율(에피소드 단위). AgentSpec 원문의 과차단 사례(pour 전면 금지)가 근거. 판정 후보([제안]): 과차단률 > 5%이면 `enforce: fail` 규칙을 `escalate`로 낮추는 규칙을 검토한다.
- 추가 측정(00-interfaces §14-4): T0 수리 왕복 횟수와 왕복 뒤 통과율, 구조 검사(검사기 5) 실패 유형, **패턴 밖 제약 비율**(검사기 6 거부 중 7형식으로 못 쓴 것), 실행 중 patch 거부율(R7)과 거부 뒤 M7 FAIL로 이어진 수. 오프라인 재생에서는 DFA 감시기와 기존 술어별 감시의 경보가 얼마나 일치하는지도 본다.
- 추가 판정([제안], 실행 전 고정): (1) 패턴 밖 제약 비율이 10%를 넘으면 허용 패턴 확장을 [결정 필요: 메인 세션]으로 올린다. (2) 실행 중 patch 거부율이 10%를 넘으면 E-M2-2에 "patch 대신 전체 계약 재요청" 조건을 더한다. (3) 오프라인 재생에서 DFA 감시와 기존 감시의 경보 불일치가 1%를 넘으면 원인을 나눠 보고한다(컴파일 오류 대 표기 차이).
- (정본 §28) 추가 측정: patch 편집 거리 분포, `change_reason` 없는 변경 수, 이미 실행한 단계를 바꾸려 한 patch 수, T0 투표의 계획 서명 일치율과 `plan_unstable` 비율, `astra_prompt_id`·모델 ID별로 나눈 통과율. 추가 조건: 첫 시도 통과율 < 80%일 때만 "자유 계획 → 2턴 스키마 변환"을 비교 조건으로 넣는다(A3). Astra 조건 사이 비교는 반복 실행 수와 검정력 계산을 사전 등록한다(2%p 검출에 약 9회 기준, 정본 §28). 단일 실행 비교로 결론 내지 않는다.

---

## 6. 반대 증거와 위험
1. **COPE 근거의 조건**: 1B 자기 계획, 수학 문제. 큰 계획기가 작은 실행기에게 목표형을 준 조건은 없다. Jev의 규모·능력은 공개되지 않았다. (§25 D13 정정) 한 단계 더: 큰 → 작은 조건의 이득은 **절차형**에서 나왔고 본 방법 Stage 2도 큰 모델 절차형이다. 그래서 COPE는 v1의 근거가 아니라 **반대 증거**다. v1은 설계 선택으로 유지하고 E-M2-1 B-COPE로 확인한다. `rationale`/`how`를 Jev 기본 입력에서 빼는 현재 기본값의 근거도 약해졌다(사용자에게 알림).
2. **PlanAhead(보조, 인용 0)**: 최적 형식이 모델마다 달랐다 → 우리가 고른 "체크리스트형 typed 계약"이 Jev에게 최적이라는 문헌 근거는 없다. E-M2-1이 필요. PlanAhead 자체도 Hard AR 절대값이 1~11%이고 넓은 구간은 STC(Table 5) 쪽이라 강한 근거가 아니다.
3. **계약이 길어지면** M1과 같은 길이 손실(2510.05381). Jev 조각을 현재 단계로 자르는 이유. 전체 계약은 코드만 읽는다.
4. **Astra가 typed 계약을 틀리게 쓸 위험**: 술어 오기, 가정 누락, 현실과 안 맞는 `T_exp`. 검사기는 문법만 잡고 의미 오류(잘못된 완료 조건)는 못 잡는다. MAST의 "명세 불이행" 실패가 우리 쪽에서도 날 수 있다.
5. **낡은 계약**: AgileThinker의 축소판 이득은 시간 압박이 셀 때만(4k·8k) 나왔고 16k·32k에서는 없었다. (§25 D13 정정) 16k에서는 오히려 결합 0.70이 반응(생각 켬) 0.76보다 낮다 → 압박이 약할 때 "가장 새 계약 참조"가 손해일 수 있다(E-M2-2 판정 5). 등급도 MED(학회 [미확인])로 내렸다. "항상 가장 새 계약"이 늘 이득이라고 말할 근거는 없다.
6. **가정 술어 검사가 과민하면** 재호출이 잦아진다(M8 호출 수 증가). M7 conformal 임계와 같은 문제 — 가정 술어에도 히스테리시스·지속 시간 조건(예: 0.5초 연속 거짓)을 둔다(추론).
7. **Slow Brain식 융합(F)이 더 단순하고 더 나을 수 있다**. 선행이므로 반드시 비교 조건으로 둔다.
8. 계약·사전·사후조건 문헌 다수가 LOW(2608.02645, 2602.22302 등). "계약 형식이 실행기를 좋게 한다"를 HIGH 근거로 말할 수 없다(v3/14 결론 유지). HIGH 근거는 AgentSpec(집행 쪽)과 Code-as-Monitor(감시 쪽, 기간 밖)뿐이다. 그 AgentSpec도 LLM(o1)이 규칙을 쓰면 체화 "recall" 70.96%다. (§25 D13 정정) 이 값은 안전 짝 사례로 낸 것이고 원문 정의가 모호하며 놓침과 과차단을 함께 설명한다(처음 보는 위험 사례 집행률은 95.56%). "위험의 약 3할을 놓친다"로 읽지 않는다. Astra가 쓴 `forbidden`은 놓침과 **과차단**을 둘 다 낼 수 있다고 보고 설계한다(E-M2-3 과차단률).
9. **DFA 감시·수리 왕복의 근거 등급** (00-interfaces §14-4·§15): 기간 안 사례 Agentproof는 LOW다(무학회, 작성자 제작 워크플로 18개, 유병률 연구 아님). 설계의 주축은 기간 밖 기초 문헌(명세 패턴, 런타임 검증)이고 이번에 원문을 읽지 않았다. LLM 계획기에 검사 오류를 되먹이면 통과율이 오른다는 기간 안 로봇 수치는 없다. 패턴을 7형식으로 제한하면 Astra가 쓸 수 있는 제약의 표현력이 줄어든다. 실행 중 patch를 거부하면 낡은 계약으로 계속 가게 되는데, 이 위험은 R4(`C_assume`)와 M7이 막는다.
10. **A4·A5 근거의 한계** (정본 §28): AgenticCache·APC는 계획 캐시·템플릿 재사용 연구라 "patch 고정이 계획 품질을 올린다"는 직접 근거가 아니다 [우리 판단]. patch 고정은 첫 계획의 잘못을 끌고 갈 수 있다(바꾸려면 `change_reason`이 필요하므로, [우리 추론]) → E-M2-2·E-M2-3에서 편집 거리와 성공률을 함께 본다. K = 3, 계획 서명 정의는 논문 값이 아니라 설계 선택([가정])이고 E0 Astra 반복으로 확정한다. Astra에 seed·응답 식별 필드·prompt caching이 있는지는 확인하지 못했다(D17 §6) — 어느 경우든 temperature 0이나 seed로 결정성을 얻을 수 없다는 전제는 유지한다.

## 7. 열린 질문, [결정 필요]
1. 해소(정본 §26, user-log 25): M1 기본 = 후보 A가 M2 술어 칸을 정한다(E3 결과로 B·C로 바뀔 수 있음, M1 §7-1).
2. [결정 필요] `rationale`(Astra 자유 서술)을 Jev에 줄지 — E-M2-1 판정 1로 정하자는 제안.
3. 해소(00-interfaces §11.1, D2 B1): 결정 지점 id는 M6 스킬 계약에 고정된 id가 정본이다. Astra는 골라 쓰고 인자만 채운다. M10 규칙 키도 이 id.
4. [결정 필요] 되돌릴 수 없음을 누가 정하나: 계약의 단계 수준 `irreversible`(Astra) / M6 phase 수준 `annotations.irreversible_phases`(스킬 작성자) / 사용자 목록(M8 T2 순간, M8 §7과 같은 질문). D2 B7에 따라 M6 §7의 같은 질문과 **한 [결정 필요]로 묶는다**. 어느 안이든 코드 안전 규칙이 최종이다.
5. 잠정 기본(정본 §28 A4, Claude 설계 선택): 재계획 때 기본 출력 = `patch`(R6 승격, §4.5). 전체 계약 재요청은 예외·비교 조건으로 남고(E-M2-3 추가 판정 (2)), Astra 출력 지연·편집 거리 측정 뒤 다시 본다. 사용자 원칙은 바뀌지 않는다.
6. 해소(00-interfaces §11.2, D2 B6): 계약 버전 교체 = M4 `premise_epoch` +1.
7. 열린 질문: `custom_predicates` 허용 DSL의 범위(거리·각도·포함·접촉·속도). 너무 넓으면 검사·안전 문제, 너무 좁으면 Code-as-Monitor 이득을 잃는다.
8. 해소(00-interfaces §14-4, D4 §14-4): 계약 정적 검사 실패 시 수리 왕복은 **T0에서만** 허용한다. 실행 중 재계획 patch는 검사만 하고, 실패하면 거부 + M7 신호를 보내며 로봇은 멈추지 않는다(R7). `forbidden`·순서 제약은 DFA로 컴파일해 H5·`C_assume` 감시를 통일한다(§4.4). 메인 세션의 잠정 결정(기술 선택)이며 E-M2-3으로 검증한다. `contract_patch_rejected`는 `C_assume`로 센다(00 §15). DFA 형식 검증은 기간 밖 기초 문헌(명세 패턴·런타임 검증)에 기대므로 [결정 필요] 4 승인 전까지 잠정 기본이다(00 §16).

## 8. 확인 못 한 것
- AgentSpec 본문 중 체화 과제 설정·규칙 예의 세부. 초록·§1·§3.2는 D2 검증이 대조(LLM 생성 규칙 정밀도 95.56%·재현율 70.96%). (§25 D13) Table 4·6·§5.3은 원문 확인. "precision 95.56 / recall 70.96"의 정확한 계산식은 본문 정의가 모호하고 코드 저장소는 읽지 않았다.
- AgileThinker ICLR 2026 채택 여부 [미확인](abs 코멘트 "30 pages"뿐), Table 10 표본 수(원문에 없음).
- PlanAhead Table 1의 형식별 AR 점수와 학회 채택. D2 검증으로 Table 4(AR) 구간 1.20~4.79, Table 5(STC) 32.5~84.0, Hard AR 절대값 약 1~11%는 확인됐다.
- Magentic-One 원장 효과를 따로 뗀 절제 수치(본문 §3 설명만 읽음).
- 2606.15285·2606.20978·2608.02645 본문(초록만).
- 큰 계획기 → 작은 실행기에 목표형 대 절차형을 준 조건의 연구(찾지 못함. 검색: `abs:planner AND abs:executor AND abs:"small language model" AND abs:plan`, WebSearch "planner executor plan format structured vs natural language small executor"). 부재 주장 안 함.
- Astra가 이 스키마로 구조화 출력을 낼 때의 지연·통과율(미측정, E-M2-3).
- 명세 패턴(Dwyer 외 ICSE 1999)·런타임 검증(Bauer·Leucker·Schallhart TOSEM 2011) 원문: 이번 라운드와 D4 검증 모두 읽지 않았다. Agentproof 7형식·저자 구성은 D4 검증 #6의 본문 확인에 기댄다. 이번에 다시 읽지 않았다.
- LLM 계획기에 형식 검증 오류를 되먹이는 수리 왕복의 로봇 사례(기간 안): 이번에 따로 검색하지 않았다. 부재 주장 안 함.
- (정본 §28, D17) §2.4 인용문 중 메인이 원문을 다시 확인한 것은 2506.09501·2604.24039·2506.14852뿐이다. 나머지는 요약 도구 추출이라 원문 PDF 대조가 남았다. 인용 수는 Atil(126) 말고는 미확인(Semantic Scholar 429). Astra API의 seed·응답 식별 필드·prompt caching 유무 미확인.
