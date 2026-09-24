# M6. 스킬과 Jev 결합 — 모듈 설계 (단계 2)

> **정본 우선**: 모듈 사이 인터페이스·정지·확정 규칙·확률 게이트·시간 값은 `00-interfaces.md`가 우선한다(2026-09-23 22:00 UTC). 이 문서와 다르면 그쪽을 따른다.
> 개정 2026-09-24 (정본 §24, D12 반영): §4.1.2 원칙 아래에 결정 지점 보기 이름의 편향(Type-Safe 2609.26758)과 중립 식별자 규칙을 [결정 필요] D32로(M3와 한 항목, 지금 설계는 바꾸지 않음), §6에 Type-Safe·C²Nav(2609.15142, [초록만]) 줄, §7-9 D32.
> 개정 2026-09-24 (D11 일관성 점검 반영, `D11-final-consistency.md` I-9): §4.4 [사용자] 문제 설정 인용을 user-log 3 원문으로(첫 판의 "기존 방법"은 원문에 없음, 00 §16).
> 개정 2026-09-24 (정본 §22, D10a 반영): 스킬 출력에 원자료 진단 필드 필수(§4.1.1), typed 결정 지점 후보 5개(§4.1.2a), §2.1 Harness VLA·CaP-X 행 정정(공개 코드 `pi0_pick`/`pi0_doubled` 수치 임계 인자, CaP-X 9개는 대부분 기하 유틸·스크립트에 자동 검증 없음), (b) 생성 스킬 = 추출 + 계약 + typed hole + 실행 기반 검증(§4.4a), E-M6-3에 "생성 기반 API 단계" 축, Harness VLA는 (a)/(a') 근거이지 (b) 근거 아님, 차별 문장(§6a). 근거 `D10a-harness-capx.md` §1.2·§2.2·§3-3·§3-4.
> 개정: 2026-09-23 D5 반영 (`D5-consistency.md` 1-9·1-10·1-12·1-15·1-17·4-1, 00-interfaces §11.2·§13·§16): `dp.critic_accept`는 M7 FAIL 뒤 M9 제안 목록이 있을 때만(WARN 발동 삭제), 보기를 M9 §4.1 L2 목록과 같게. E-M6-1 판정 2를 00 §13 방향 재검토 규칙(95% 상한 < +5%p)으로, 통계를 부트스트랩 95% 구간으로. 실험 환경을 단일 팔 자작 장면으로. `effect`(사가)를 잠정 기본([결정 필요] 4)으로 표시. §4.4의 사용자 문장 인용을 user-log 3 원문으로 고침(00 §16).
> 개정: 2026-09-23 정본 §14–§15 반영 (`00-interfaces.md` §14-3·§14 M6 항·§15, `D4-cross-field.md` §7·§10, `D4-cross-field-verification.md` #1·#2·#5·§2-4). 핵심: (1) 스킬 계약 phase마다 **`effect` 필드**를 둔다. 값은 `reversible` + 보상 스킬 id, 또는 `irreversible`이다(§4.1.1). M9는 보상을 역순으로 실행하고 비가역 경계를 넘어 되돌리지 않으며, M4는 비가역 보기 확정에 W+1을 쓴다. 근거는 사가(1987, 기초 문헌), SagaLLM(PVLDB 18(12), 2025-03-15 공개로 기간 8일 밖), Atomix 2602.14849다(§2.3). (2) 생성 스킬 (b)에 **typed hole 사후 검사 게이트**를 둔다(§4.5 신설). 이것은 **[접목] 우리 접목안**이다. PLDI 2025 원문은 디코딩 중 제약만 평가했다(§2.4). E-M6-2 절제에 −`effect` 추가, E-M6-5(typed hole 게이트) 신설, §7-8 해소.
> 개정: 2026-09-23 D2 검증·00-interfaces §11 반영 (`D2-verification.md` Part A 정정, Part B·C 해소안. 핵심: 결정 지점 id는 이 문서의 스킬 고정 id가 정본(M2는 골라 쓰고 인자만, M10 키도 이 id), `default_on_timeout` = 직전 확정 행동 유지 + 감속, 확률 게이트는 E1 뒤에만, `dp.critic_accept`는 M9 복구 제안 중 선택만(M7 FAIL을 뒤집지 못함), `dp.grasp_result` 보기 = M7 S5 공유 목록, "기존 스킬" (b)·(a') 동등 조건, BATON은 보조 참고로 내림, GPSFSM 수치 정정.)


작성: 2026-09-23 21:49 UTC 시작(`date -u`), 단계 2 모듈 설계 에이전트(M6·M10 담당). 규칙: `docs/design/README.md`.
읽은 것: `plan.md` v4.3(§1, M6, M10, §2.5), `user-log.md` 11(스킬·경험 축적), `research/v3/06`, `v3/15`, `v3/16`, `v3/03`, `v3/07`(Kintsugi 부분), `design/M3`(DecisionStep·예상 결과 술어), `design/M4`(원장·확정기), `design/M7`(술어 S1~S6), `design/M9`(복구 사다리·체크포인트).

표기: **[원문]** = 원문(본문·명세)에서 직접 읽음 / **[접목]** = 우리 접목안(원문이 아님) / [사용자] / [제안] / [결정 필요].
전제: M1 변환 방법은 [결정 필요, 사용자]다. 이 문서는 특정 M1 후보(A/B/C)를 가정하지 않고 **M1 술어 등록부 인터페이스(M1 §4.0)에만 의존**한다(00-interfaces §11.3). 스킬 계약의 모든 술어는 등록부 이름이고 등급(T1/T2/T3)은 등록부가 정한다.

---

## 0. 조사 방법과 한계
- WebSearch: 이 문서(M6)용 3회(Agent Skills 명세 1, LLM+행동 트리 2). M10과 합쳐 5회(한도 10).
- 이번에 원문을 직접 읽은 것: Agent Skills 명세(agentskills.io/specification 전문), MCP 명세 2025-06-18 Tools 절 전문 + `schema.ts`(raw.githubusercontent, annotations 필드), PhyAgentOS 2607.16636 HTML(SKILL.md·SKILLRUNTIME.md·세션 계약·교훈 주입 문장), BATON 2608.16889 HTML(진입·출구·lookahead 전이 문장), arXiv abs: 2509.16611, 2603.01113, 2607.15674, 2606.10808, 2511.18203, 2602.12430, 2501.03968.
- 스킬 상위 6편(PhyAgentOS, Zetta, Harness VLA, CaP-X, ROSClaw, Show-Harness)의 루프 구조는 `v3/15`(원문 절 확인)와 `v3/16`(49항목 재확인)을 그대로 쓴다. 다시 읽지 않았다.
- 스타·인용은 다시 재지 않았다(GitHub·Semantic Scholar API 금지). 스타는 v3/06(2026-09-23 19:55–20:01 UTC 측정) 값.
- 한계: 행동 트리+LLM 쪽 2025-26 논문은 초록만 읽었다(수치는 초록 문장 그대로). Anthropic 원 발표 블로그는 읽지 않고 공개 명세(agentskills.io)만 읽었다.

---

## 1. 역할과 입출력

[사용자] (user-log 11 스킬) "기존 스킬도 Jev와 엄청 연관될수록 좋다. 1년 이내에 나온 GitHub 스타 상위 5개 중에서, LLM이 스킬을 불러오고 끝이 아니라 잘게 엮어 놓은 논문을 참고해 파이프라인을 대충 짜 본다."
[사용자] (user-log 3) "물체를 보고 스킬을 생성해서 잡는 방법들이 많지만 실패할 때가 있다. 실패할 때마다 Astra가 개입."

| 항목 | 내용 |
|---|---|
| 위치 | Astra(계획 시점, 세션 계약) → **M6 스킬 계약** → Jev(~3Hz 겹침, M3 질문) → M4 확정기 → 스킬/제어기 100Hz+ → M5 |
| 입력 | 스킬 라이브러리(스킬 카드), Astra 세션 계약(단계 원장, 단계별 스킬 바인딩), M1 술어 표, M7 critic 제안, M10 컴파일 규칙(0~2개) |
| 출력 | (1) 스킬 인스턴스(인자 = 보기 ID로 고른 범주형 파라미터), (2) 단계(phase)별 **결정 지점** 질문 묶음(M3 형식), (3) 스킬 결과(출구 술어·오류 코드) → M7·M4(b)·M10 |
| M6가 정하는 것 | 스킬 인터페이스 형식, 결정 지점을 어디에 두는지, 기존 스킬을 어떻게 감싸는지 |
| M6가 정하지 않는 것 | 질문 문구·보기 수(M3), 확정 규칙(M4), 실패 판정(M7), 복구 선택(M9), 규칙 컴파일(M10) |

"잘게 엮기"의 뜻 [제안]: 스킬 **안의 단계 경계와 결정 지점마다** Jev가 typed 선택을 하고, 스킬은 그 선택을 인자로 받아 짧게 실행한 뒤 **결과 술어를 돌려준다**. "스킬 하나 부르고 끝날 때까지 기다리기"(거침)와 "스텝마다 증분 이동"(Show-Harness, 스킬이 없음)의 사이다.

---

## 2. 분야 전체 최고 후보 표

기간: 첫 공개 ≥ 2025-03-23(LLM+스킬 논문은 ≥ 2025-09-23). 신뢰도는 v3/README 기준. ◎ 이번에 원문, △ v3 원문 확인에 기댐, ○ 초록만.

### 2.1 하위 부분 (1) 스킬 인터페이스 명세

| 이름 | 분야 | 어디서 최고였나 (조건) | 신뢰도 | 기간 | 학습 없이 | 로봇 |
|---|---|---|---|---|---|---|
| **Agent Skills 명세** (SKILL.md, agentskills.io) ◎ | LLM 에이전트 표준 | 성능 수치가 아니라 **사실상 표준**: Anthropic이 만들어 2025-12-18 공개 표준으로 냄(2차 출처 firecrawl 블로그, 날짜는 원문 미확인). 명세: 필수 `name`(≤64자, 소문자·숫자·하이픈), `description`(≤1024자, "무엇을·언제"), 선택 `license`, `compatibility`(≤500자), `metadata`(문자열→문자열 맵), `allowed-tools`(실험). **점진 공개 3단**: 메타데이터 ~100토큰은 시작 때 전부, 본문 <5000토큰 권장은 활성화 때, `scripts/`·`references/`·`assets/`는 필요할 때. 본문 500줄 이하 | HIGH(표준, 다수 제품 채택) — 논문 아님 | 2025-12 | 예 | 아니오(PhyAgentOS가 SKILL.md를 절차 기억으로 씀 ◎) |
| **MCP Tools 명세 2025-06-18** ◎ | LLM 도구 표준 | `inputSchema`(JSON Schema), 선택 `outputSchema`(있으면 서버는 반드시(MUST) 준수, **클라이언트 검증은 SHOULD(권장)** — D2 A1 정정), `structuredContent`, 오류 두 층(프로토콜 오류 대 `isError: true` 실행 오류), `annotations`: `readOnlyHint`, `destructiveHint`(기본 true), `idempotentHint`(기본 false; 둘 다 `readOnlyHint==false`일 때만 의미), `openWorldHint`(schema.ts). "clients MUST consider tool annotations to be **untrusted** unless they come from trusted servers" | HIGH(표준) | 2025-06 | 예 | ROSClaw 등 로봇 MCP 서버 있음(v3/06) |
| **Harness VLA** 프리미티브 호출 △◎ | 로봇 | 고정 어휘 JSON 호출, `vla_act{prompt, max_chunks, stop 술어}`, post-condition까지 실행, "planner cannot invent new primitives". LIBERO-Pro +38.6%p 등(v3/06, 가장 강한 관련 기준 대비). **추가(D10a §3-3)**: 논문 어휘는 위와 맞다. 공개 LIBERO 코드(`robots/libero/tools.py`)에서는 `vla_act`가 `pi0_pick`과 `pi0_doubled` 둘로 나뉘고, stop은 수치 임계 인자다(`pi0_pick(prompt, max_chunks=24, lift_thresh=0.05 m, gripper_closed_thresh=0.06, gripper_open_thresh=0.0, descent_thresh=0.10 m)`). `pi0_pick` 반환 = success, chunks_used, peak_lift_m, min/final_gripper_opening, diagnostics. `pi0_doubled`는 "success=false does not necessarily mean the contact interaction failed" | MED-HIGH(칭화, 962★, 인용 23) | 2026-07 | 예 | 예(시뮬만) |
| **PhyAgentOS** 세션 계약 + SKILLRUNTIME.md ◎△ | 로봇 | 세션 계약 = 목표, 런타임·타깃, **사전조건, 실행 한계, 수용 기준**(§3.3). SKILLRUNTIME.md = "required observations, produced action forms, orchestration mode, configurable parameters, and adapter requirements". 판정 {success, failure, replan} | MED(2,481★, 인용 4, 저장소가 논문보다 4개월 먼저) | 2026-07 | 예 | 예 |
| **Zetta** 재진입 계약·critic 제안 △ | 로봇 | critic 제안 = (증거, 제안 모드), Orchestrator가 승인할 때만 개입(§2.1.3). 재진입 = "실패 증거 해소 AND 접촉 안정"(§2.5.1). LIBERO-Pro 90.8%, RoboCasa 93.6%(현재 rollout 예산 기준 단서) | MED(칭화 AIR, 1,252★) | 2026-08 | 예(오프라인 진화는 롤아웃 필요) | 예 |
| **BATON** 전이 인지 계약 ◎ | 로봇 | "VLA primitive carries an **exit** condition but no **entry** condition" 을 지적. 세 전이: invocation(손목 카메라로 준비 확인 뒤에만 VLA 호출), handoff(앞 단계 잔여물이 흐트린 진입 상태 복구), **lookahead**(뒤 단계가 요구하는 조건이 지금 단계의 실행 방식을 정함). RoboMemArena 과제 성공 +11.6, 누적 +14.9(SoTA 대비, 초록 "%", 본문 "points" → %p) | LOW-MED(USC, 심사 전, 2026-08-17, 인용 1). **보조 참고**: 계약 필드를 좌우하는 근거로 쓰지 않는다(00-interfaces §11.3, D2 C5). 필드는 HIGH 근거나 우리 실험으로 정한다(§3) | 2026-08 | 예(파라미터 갱신 없음) | 예 |
| **GPSFSM** (2607.15674) ○ | 로봇 | LLM이 부분 명세 FSM(상태, **사건 촉발 전이**, Sequential/Recovery/Parallel-Any/All)을 생성, 엔진이 파싱·검증·실행, ROS 2 Capabilities2에 **실행 시 파라미터 주입**·비동기 사건. **정정(D2 A1)**: BTGenBot보다 나은 것은 **GPT 모델에서만**(성공 90%·부분 10% 대 BTGenBot 54/11/34%). **로컬 모델에서는 BTGenBot이 더 나음**(13/35/52 대 10/22/68). 5개 항법 과제, 사람 평가자 3명(Table I) | MED-HIGH(**IROS 2026 채택**, arXiv 코멘트) | 2026-07 | 예 | 예 |
| MoA 대화형 계획 → BT (2603.01113) ○ | 로봇 | 전문 에이전트가 **자기 전제 설명에 해당하는 질문만** 답하고 나머지는 넘김(기권 기반 위임), BT로 재시도·정책 전환. 사람 응답 약 27% 감소. "**적용 한계는 계획기가 아니라 가장 약한 행동 노드의 신뢰도**"(초록) | LOW-MED(와세다 Ogata 연구실, 심사 미표기) | 2026-03 | 예 | 예(실물) |
| VLM 행동 트리 조건 노드 (Wake, 2501.03968) ○ | 로봇 | VLM이 조건을 **자유 텍스트 조건 노드**로 BT에 넣고, 실행 때 다른 VLM이 이미지로 참/거짓 판정 | MED(Microsoft) | **기간 밖(2025-01), 기초 문헌** | 예 | 예 |
| 행동 트리 reactive sequence / PA-BT (Colledanchise·Ögren) | 로봇 | 매 틱 조건 재확인, 사전조건 거짓이면 그 조건을 만드는 하위 트리로 확장 | 기초 | **기간 밖, 기초 문헌**(M9 문서와 같음, 원문 재확인 안 함) | 예 | 예 |
| SkillWrapper (2511.18203) ○ | 로봇 TAMP | 기반 모델로 **블랙박스 스킬의 사전조건·효과 술어를 생성·학습**, "provably sound and complete planning", 실물 장기 과제 | MED(Brown, Tellex. 학회 미확인, v7까지 개정) | 2025-11 | 데이터 수집 필요(학습 없음이지만 능동 수집) | 예 |
| CaP-X 코드 턴 △◎ | 로봇 | 턴 = 프로그램 한 편 끝까지 실행, 성공 롤아웃에서 스킬 9개 추출(CaP-Agent0). **추가(D10a §3-4)**: 9개는 대부분 좌표·기하 유틸리티이고(조작 스킬은 `select_top_down_grasp` 하나 정도), 사전·사후조건 필드가 없으며, 컴파일 스크립트(`compile_skill_library.py`)에 자동 테스트·실행 검증 단계가 없다. 논문의 "9 verified"의 뜻은 원문에서 확인 못 함 | HIGH(ICML 2026, 819★) | 2026-03 | 예 | 예 |
| Show-Harness 의미 행동 단위 △ | 로봇 | 결정론 interpreter가 단위당 한계 강제, 위반은 실행 전 차단, 선택적 청킹 96% 대 항상 청킹 74% | MED(NUS Show Lab, 451★) | 2026-09 | 예 | 예 |
| Agent Skills 서베이 (2602.12430) ○ | LLM | 커뮤니티 스킬의 26.1%에 취약점, 4단 게이트 권한 모델 제안 | LOW-MED(ACM CAIS 2026 **워크숍**) | 2026-02 | – | 아니오 |

### 2.2 하위 부분 (2) Jev 질문을 꽂을 자리 (결합 세밀도)

| 이름 | 원문 결합 방식 | 세밀도 | 근거 |
|---|---|---|---|
| Zetta △ | 코드 critic 고주기(청크마다) → 제안 → 모델 승인 | 촘촘(코드) + 사건 단위 승인 | v3/16 #21–23 |
| Show-Harness △ | 스텝마다 VLM이 단위 선택 | 가장 촘촘(스킬 없음) | v3/15 §2.6 |
| Harness VLA △ | 프리미티브 종료마다 동기식 선택, 스테이징→시도→관찰→재스테이징 | 중간 | v3/16 #36, #39 |
| BATON ◎(보조) | 전이(invocation/handoff/lookahead)마다 검증 에이전트 | 중간(경계) | 본문 |
| PhyAgentOS △ | 세션 계약 후 루프 밖(정책 모드) | 거침 | v3/16 #29 |
| CaP-X / ROSClaw △ | 턴(프로그램)마다 / 도구 호출마다 + 사전 검증 | 중간 / 거침 | v3/16 #26, #48 |

**스타 상위 5(+1)** (v3/06, 측정 2026-09-23 20:00 UTC, 다시 재지 않음): PhyAgentOS 2,481 / Zetta 1,252 / Harness VLA 962 / CaP-X 819 / ROSClaw 625(저장소 연결 추정) 또는 Show-Harness 451. [결정 필요: 5위] — 그대로 유지.

### 2.3 하위 부분 (3) 효과 분류·보상 (사가, 00-interfaces §14-3)

| 이름 | 분야 | 어디서 최고였나 (조건) | 신뢰도 | 기간 | 학습 없이 | 로봇 |
|---|---|---|---|---|---|---|
| Sagas (Garcia-Molina·Salem, SIGMOD 1987) | 데이터베이스 | 긴 트랜잭션을 하위 트랜잭션 열 T_i로 나누고 각각에 보상 C_i를 짝짓는다. 실패하면 역순 보상(backward) 또는 저장점부터 재시도(forward) | 기초 문헌(원문은 이번 라운드와 D4 검증 모두 읽지 않음) | **기간 밖, 기초 문헌** | 예 | – |
| **SagaLLM** (2503.11951) | LLM 다중 에이전트 계획 | 사가 패턴 + 지속 메모리 + 자동 보상 + 독립 검증 에이전트(초록. 수치 미확인) | HIGH (**PVLDB 18권 12호, pp. 4874–4886**, DOI 10.14778/3750601.3750611, vldb.org 목록 확인. 트랙(연구/산업)은 미확인. 인용 76) | **2025-03-15 → 기간 밖(8일)** | 예 | 아니오 |
| **Atomix** (2602.14849) | LLM 에이전트 도구 사용 트랜잭션 | 효과 3분류(본문 §2): Reversible(즉시 실행, 중단 시 **역방향 의존 순서로 보상**) / Bufferable(커밋 때 적용) / **Irreversible-gated**(이메일·송금·"**physical actions**", 커밋 때만 방출). 본문: "Saga compensation helps only when every externalized effect is reversible… cannot prevent an irreversible send" | MED-LOW (무학회, 인용 25) | 2026-02-16, 기간 안 | 예 | 아니오(원문이 물리 행동을 비가역 게이트 대상으로 직접 꼽음) |

### 2.4 하위 부분 (4) 생성 스킬 검사 (타입 제약 생성, 00-interfaces §14·§15)

| 이름 | 분야 | 어디서 최고였나 (조건) | 신뢰도 | 기간 | 학습 없이 | 로봇 |
|---|---|---|---|---|---|---|
| **Type-Constrained Code Generation with Language Models** (2504.09246) | PL / LLM 코드 생성 | 기전: 접두부 오토마타 + 거주 가능 타입 탐색으로 **디코딩 중** 타입이 맞지 않는 토큰을 막는다. HumanEval·MBPP(TypeScript)에서 컴파일 오류 절반 이상 감소, 합성·번역·수리 과제 기능 정확도 향상, 30B 넘는 오픈 가중치 모델 포함(초록). **원문이 평가한 것은 디코딩 중 제약뿐이다.** 사후 타입 검사 + 오류 되먹임은 평가하지 않았다(D4 검증 #5·§2-4) | HIGH (**PLDI 2025** Research Papers, DOI 10.1145/3729274, 인용 60. 쪽수 601–626은 ACM 403으로 미확인) | 2025-04-12, 기간 안 | 예(단 로짓 접근 필요 → **Astra API에는 직접 못 씀**) | 아니오 |
| Statically Contextualizing LLMs with Typed Holes (Hazel, OOPSLA 2024) | PL | 구멍의 기대 타입과 관련 타입 정의를 LLM 문맥에 넣음 | 원문 안 읽음 | 기간 밖(2024-09) | 예 | 아니오 |

---

## 3. 가져올 것과 접목 방법 (원문 칸과 접목 칸 분리)

| 출처 | 원문에 있는 것 | 우리 접목안 [접목] |
|---|---|---|
| Agent Skills | 점진 공개 3단(메타 ~100토큰 / 본문 <5000 / 자원은 필요 시). `description`은 "무엇을·언제" | **Astra용 스킬 카드**: 계획 시점에 Astra에게는 카드(이름·설명·진입/출구 술어 이름·파라미터 이름)만 전부 준다. 본문(단계·결정 지점 전문)은 **바인딩된 스킬만** 세션 계약에 붙인다. Jev에게는 카드도 주지 않고 **지금 단계의 결정 지점 질문만**(Jev "관련 없는 내용 늘면 정확도 하락" 약점, plan §1) |
| MCP Tools | `inputSchema`/`outputSchema`, `isError`(실행 오류) 대 프로토콜 오류, annotations 4종은 "힌트이며 신뢰 전 untrusted" | 스킬 계약을 JSON Schema로: 입력 = **범주형 파라미터 enum**(보기 ID), 출력 = 결과 술어 + 오류 코드(`isError` 대응). 출력 검증은 MCP에서는 클라이언트 SHOULD지만 **우리는 설계 선택으로 필수**로 둔다. annotations를 로봇 의미로 옮김: `destructiveHint` → `irreversible`(놓기·삽입 시작: M4 확정 전 실행 금지, M9 잠금 대상), `idempotentHint` → `retry_safe`(M9 L1 재시도 허용), `readOnlyHint` → 인식·관찰 스킬. 주의(D2, 우리 판단): MCP idempotent는 "같은 인자로 반복 호출해도 추가 효과 없음"인데 로봇 접근·정렬은 대개 그렇지 않다 → `retry_safe`는 뜻이 다른 **우리 필드**로 정의한다(재시도해도 안전, 효과 없음이 아님). **"힌트는 untrusted"를 그대로**: 되돌릴 수 없음 여부는 스킬 작성자 선언이 아니라 코드 안전 규칙이 최종 |
| Harness VLA | `stop 술어`와 `max_chunks`를 호출 인자로, post-condition까지 실행, 고정 어휘 | 모든 스킬 단계에 `stop`(조기 종료 술어)과 `budget`(시간·청크 상한)을 인자로. Astra는 **새 스킬을 발명하지 않는다**(원문 규칙 그대로), 결정 지점의 보기도 계약에 나열된 것만 |
| PhyAgentOS | 세션 계약: 사전조건·실행 한계·수용 기준. SKILLRUNTIME.md: 필요한 관측·행동 형식·파라미터. 교훈은 "provenance and scope"와 함께, 사전조건이 맞을 때만 전이 | 스킬 계약 필드 `entry`(사전조건), `exit`(수용 기준), `budget`(실행 한계). 교훈 주입 조건은 M10의 정확 일치 키와 같은 원리 |
| `entry`의 근거(HIGH·기초) | 행동 트리 PA-BT(사전조건 거짓이면 그 조건을 만드는 하위 트리로 확장, 기초 문헌), PhyAgentOS 세션 계약의 사전조건, MCP `inputSchema`(호출 전 형식 조건) | **스킬마다 `entry`와 `exit`를 둘 다** 둔다. 계획 시점에 코드가 `exit_k ⇒ entry_{k+1}` 검사, 성립하지 않으면 Astra에 되돌림. 필드 유지 여부는 E-M6-2 절제(우리 실험)로 확정 |
| BATON(보조 참고, 인용 1·심사 전) | 출구만 있고 진입이 없는 문제, handoff·lookahead 전이 | 착상 출처로만 적는다. **`lookahead_req`**(다음 스킬 `entry`가 요구하는 것 중 지금 스킬 실행 방식에 걸리는 것, 예: 놓을 자리가 좁으면 옆잡기)는 HIGH 근거가 없으므로 **E-M6-2에서 3%p 이상 기여할 때만** 필수 필드로 남긴다. Jev 접근 방향 보기의 `next_entry_ok` 예상 결과 술어도 같은 판정 |
| Zetta | critic 제안 (증거, 모드), 승인자만 개입 허용, 재진입 = 증거 해소 AND 접촉 안정 | `dp.critic_accept`: **M9가 낸 복구 제안 목록 중 하나를 고르는 질문**으로만 쓴다(00-interfaces §11.2, D2 B10). M7 FAIL을 뒤집는 "거절-계속" 보기는 두지 않는다(FAIL은 M7만). 재진입 조건을 스킬 계약 `reentry` 필드로(코드 술어). 원문 승인자는 LLM(Claude/GPT, v3/16 #23)이고 **Jev로 바꾸는 것은 접목** |
| GPSFSM | 사건 촉발 전이, Recovery 구조, 실행 시 파라미터 주입(BTGenBot 대비 우위는 GPT 모델에서만) | 스킬 **내부 단계 = 작은 FSM**(approach→align→grasp→lift/transport→place→retreat), 전이는 코드 술어 사건으로, 파라미터는 전이 순간 Jev 답으로 주입. BT 대신 FSM을 기본으로 둘지는 E-M6-2에서 |
| MoA→BT | 자기 전제에 해당하는 질문만 답하고 넘김, "가장 약한 행동 노드"가 한계 | 모든 Jev 질문에 `NONE_ESCALATE`(M3와 같음). 실험에서 **단계별 실패 분해**(어느 단계 노드가 약한가)를 필수 지표로 |
| Wake(기간 밖) | 자유 텍스트 조건 노드를 실행 때 VLM이 판정 | 코드로 못 쓰는 조건만(예: "천이 펴졌다") Jev Noul 조건 노드로. **코드 술어가 있으면 코드가 정답**(M7 규칙과 같음) |
| SkillWrapper | 블랙박스 스킬의 사전조건·효과를 기반 모델로 발명·학습 | "기존 스킬 = 라이브러리(a)"일 때 `entry`/`exit` 술어가 없는 스킬에 **오프라인으로 술어를 붙이는 방법** 후보(대안). 기본은 사람이 쓰고 Astra가 제안 |
| Show-Harness | interpreter가 단위 한계 강제, 위반 실행 전 차단 | 스킬 파라미터 enum의 각 값은 코드가 한계 안의 수치로 바꾼다(Jev는 수치를 쓰지 않음). 스킬 밖 자유 이동 구간만 Show-Harness식 단위(M3 D안) |
| CaP-X | 코드 턴, 성공 롤아웃에서 스킬 추출(정규식 추출 → 2회 이상 + 이름 필터 → LLM 큐레이션, 결과는 기하 유틸 9개, 사전·사후조건 없음, 스크립트에 자동 검증 없음. D10a §2.1). 사람이 만든 높은 단계 API일수록 성공률↑(단조, Takeaway 2) | "기존 스킬 = 생성(b)"일 때: 생성 코드 안에 `jev_choice(dp_id)` 호출만 허용하는 API(v2부터 우리 제안, 원문 아님). 추출 절차는 같게 쓰고 계약·typed hole·실행 기반 검증을 더한다(§4.4a) |
| 사가(기초) · SagaLLM · Atomix (§2.3) | [원문] 하위 단계마다 보상 짝(사가). 효과를 가역 / 버퍼 가능 / 비가역 게이트로 나누고, 비가역은 커밋 게이트 전에 방출하지 않는다(Atomix §2). 가역 효과는 중단 시 역방향 의존 순서로 보상한다 | [접목] 스킬 계약 phase마다 `effect`: `{kind: reversible, compensate: <스킬 id>}` 또는 `{kind: irreversible}`(§4.1.1). M9 재개 = 재개 지점까지 가역 phase의 보상 스킬을 **역순**으로 실행하고, 비가역 경계를 넘어 되돌리지 않는다(그 너머는 forward 재시도만). M4 = 비가역 보기의 유예 창 W+1(00-interfaces §14-3). 물리 보상은 원상 복구가 아니므로 보상 뒤 `entry`를 다시 확인한다 |
| PLDI 2025 타입 제약 생성 (§2.4) | [원문] 디코딩 중 타입 제약(로짓 필요). 사후 검사는 평가하지 않음 | [접목] **원문 미평가 접목안**: 생성 스킬 (b)의 결정 자리를 typed hole `jev_choice(dp_id, Enum)`으로만 허용하고, 생성 뒤 코드가 타입·철저성·id·술어·`effect`를 검사해 오류 문장을 되먹인다(§4.5). 원문의 "타입을 생성의 합격 조건으로 쓴다"는 발상만 옮긴다 |

---

## 4. 설계안

### 4.1 1순위: 스킬 계약(HarvestSkill) + 단계 FSM + 단계별 결정 지점

#### 4.1.1 스킬 계약 형식 [제안]
Agent Skills 폴더 형식을 그대로 쓰고(점진 공개), 계약은 `SKILL.md` 앞머리 + `contract.json`(JSON Schema)로 둔다.

```yaml
# SKILL.md frontmatter (Agent Skills 명세 필드 + metadata에 우리 필드)
name: pick-side-grasp
description: Grasp a rigid object from the side and lift it. Use when top access is blocked or the place target needs a side-held object.
metadata:
  harvest.version: "1"
  harvest.arms: "right"          # 양팔 벤치마크면 left|right|both
```
```jsonc
// contract.json (MCP inputSchema/outputSchema 형식을 빌림)
{
  "inputSchema":  { "target_id": "enum<scene objects>", "approach": "enum[side_front, side_left, side_right]",
                    "grip_force": "enum[light, normal, firm]" },        // 수치 없음. 값→수치는 코드 표
  "entry":  ["reachable(target)", "gripper_open", "not holding(any)"],   // 진입 술어 (PA-BT 사전조건·PhyAgentOS)
  "exit":   ["holding(target)", "lifted(target)"],                       // 출구 = 수용 기준 (PhyAgentOS). lifted 문턱 h_lift=3cm는 설정 표
  "invariants": { "lift": ["holding(target)"] },                         // phase별. M7 invariants_k로 넘어감
  "phases": ["approach", "align", "grasp", "lift"],
  "decision_points": ["dp.approach_dir", "dp.align_commit", "dp.grasp_commit", "dp.grasp_result"],  // 스킬 고정 id (정본)
  "stop":   { "approach": "at_pregrasp(target)", "align": "aligned_xy(gripper,target) and aligned_yaw(gripper,target)" },
  "budget": { "approach": "4s", "align": "3s", "grasp": "2s", "lift": "2s" },
  "default_on_timeout": "hold_last_committed_slow",                     // 직전 확정 행동 유지 + 감속 (정지 아님)
  "reentry": ["failure_evidence_cleared", "contact_stable"],             // Zetta
  "lookahead_req": { "if next_skill=place-narrow": "approach=side_*" },  // 착상 BATON(보조), 유지 여부는 E-M6-2
  "annotations": { "irreversible_phases": [], "retry_safe_phases": ["approach", "align"] },
  "effect": {                                                           // phase별 효과 (00-interfaces §14-3, 사가·Atomix 접목)
    "approach": { "kind": "reversible", "compensate": "retreat-to-pregrasp" },
    "align":    { "kind": "reversible", "compensate": "retreat-to-pregrasp" },
    "grasp":    { "kind": "reversible", "compensate": "open-and-retreat" },
    "lift":     { "kind": "reversible", "compensate": "lower-and-release-in-place" } },
  "outputSchema": { "result": "enum[ok, stopped_early, budget_exceeded, precondition_false, error]",
                    "exit_predicates": "map<predicate,bool>",
                    "diagnostics": "map<name,raw value>" }                // 필수 원자료 진단 필드 (00 §22, RPent pi0_pick 반환 dict)
}
```
- **원자료 진단 필드 필수** (00-interfaces §22, D10a §1.2) [접목]: 스킬 출력은 출구 술어 + 오류 코드에 더해 `diagnostics`에 원자료 값을 반드시 담는다. 예: 최고 들어올림 높이, 최소 그리퍼 간격, 사용 청크 수, 종료 신호(RPent `pi0_pick` 반환의 `peak_lift_m`, `min_gripper_opening`, `chunks_used`, `terminated`에 대응). 근거: RPent 전역 메모리가 "`pi0_pick.success`=false여도 영상상 들고 있으면 계속"을 교훈으로 가질 만큼 스킬 불리언 하나는 틀린다. 이것은 M7 "코드 술어가 정답, 스킬 자기 보고는 보조" 규칙의 원문 사례다. `result`·`exit_predicates`는 보조이고 M7은 등록부 술어와 이 원자료로 판정한다.
- 파라미터 범위: **enum(보기 ID)만**. 순서형은 M3의 보기 수 실험(E-M3-1) 결과 N을 따른다. 코드 표가 enum 값을 수치로 바꾼다(Jev 수치 약함, plan §1).
- 술어: 모두 M1 술어 등록부 이름(수치 인자 없음). `reachable`·`aligned_*`·`at_pregrasp`·`contact_stable`은 T2라 M7 하드 채널(즉시 FAIL)에 쓰이지 않고 소프트 채널로만 간다(00-interfaces §11.2). `holding`·`gripper_open`·`lifted`는 T1.
- Astra 권한: 계약에 있는 스킬·보기·**결정 지점 id**만 고른다(Harness VLA "cannot invent"). 결정 지점 id는 이 스킬 계약에 고정된 것이 정본이고, M2 세션 계약은 그 id를 골라 쓰고 인자(예: `target`)만 채운다. M10 Jev 규칙 키도 같은 id를 쓴다(00-interfaces §11.1). 새 스킬·새 결정 지점 제안은 오프라인 경로(M10 검증 게이트)로만.
- **`effect` 필드** (00-interfaces §14-3 채택) [접목]:
  - 값: phase마다 `{kind: "reversible", compensate: <스킬 id>}` 또는 `{kind: "irreversible"}`. 보상 스킬 id는 라이브러리에 있는 스킬이어야 하고, 그 스킬도 `entry`/`exit`를 갖는다(검사기가 확인). 예: `place-on` 스킬의 `release` phase는 `irreversible`(놓기), `lower` phase는 `reversible`(보상 = 다시 들어 올리기).
  - 읽는 곳: **M9**는 재개 지점("사전조건이 참인 가장 늦은 지점", 00 §12)까지 가역 phase의 보상을 **역순**으로 실행한다. 경로에 비가역 phase가 있으면 그 너머로는 되돌리지 않고 forward 재시도만 한다. **M4**는 비가역 phase의 보기 확정에 유예 창 W+1을 쓴다(M4 §4.6). **M2** 단계 수준 `irreversible`은 "그 단계 phase 중 하나라도 `irreversible`"과 같게 두는 것을 제안한다([제안], §7-7 [결정 필요]와 묶음).
  - `annotations.irreversible_phases`와의 관계: `effect`가 정본이고 `irreversible_phases`는 `effect`에서 계산되는 파생 값으로 둔다([제안]). 두 값이 다르면 검사기가 거부한다.
  - **잠정 기본**: `effect`와 보상 역순 재개는 사가(1987)·SagaLLM(기간 8일 밖)에 기대므로 [결정 필요] 4 사용자 승인 전까지 잠정 기본이다(00 §16). 불허하면 기간 안 근거는 Atomix(무학회)만 남는다.
  - `effect`는 **표지(힌트)**다. MCP annotations와 같은 이유로 안전을 넘기지 않는다. 코드 안전 술어가 최종이다. 물리 보상은 원상 복구가 아니므로(물체 자세 변화) 보상 뒤 재개 phase의 `entry`를 반드시 다시 확인한다.

#### 4.1.2 Jev 질문을 꽂는 자리: 단계별 템플릿 [제안]
원칙: (1) 코드 술어로 답이 나오는 것은 묻지 않는다. (2) 질문은 **단계 전이 사건** 때와 M4의 겹침 확인 때만. (3) 모든 보기에 예상 결과 술어(M3), 모든 질문에 `NONE_ESCALATE`. (4) 같은 문구 고정(Jev #8). (5) **확률 게이트는 E1(보정 측정) 뒤에만 켠다. E1 전에는 확률 게이트를 끄고 최빈 선택만 쓴다**(00-interfaces §6, D2 B9). (6) 아래 표의 id가 정본 결정 지점 id다(M2·M10이 그대로 참조).

| 단계 | 결정 지점 (촉발 사건) | 질문 템플릿(영어, 고정 문구) | 보기 집합 (예상 결과 술어 붙음) | 누가 답을 쓰나 |
|---|---|---|---|---|
| (스킬 사이) | `dp.next_skill` (앞 스킬 exit 참 / 실패 사건) | "Which skill should run next for stage {k}?" | 계약이 허락한 스킬 후보(+ 같은 스킬 다른 파라미터), `RESTAGE`, `NONE_ESCALATE` | 스킬 선택기 |
| approach | `dp.approach_dir` (스킬 진입 시, 장애물 술어 변화 시) | "Choose the approach for {target}." | **바인딩된 스킬 inputSchema의 `approach` enum에서 가져온다**(D2 B12: 예 `pick-side-grasp`는 `side_front`, `side_left`, `side_right` 3개, `pick-top-grasp`는 `top`, 둘 다 후보인 단계면 합집합). 각각 `after: reachable=?, collision_risk=?, next_entry_ok=?`(lookahead). M10 `prefer`/`avoid` 규칙의 대상 집합도 이 enum | 스킬 인자 |
| approach | (M4 겹침 확인) | 같은 질문 반복 | 같음 | M4 합의 |
| align | `dp.align_commit` (stop 술어 근접 또는 정체) | "Is the gripper ready to descend, or adjust?" | `descend`, `adjust_+x/-x/+y/-y`(≈단계), `rotate_+/-`, `restage`, `NONE_ESCALATE` | 스킬 인자 / M3 D안 미세 이동 |
| grasp | `dp.grasp_commit` (정렬 stop 참) | "Close the gripper now?" | `close_now`, `lower_more`, `adjust_small`, `restage`, `NONE_ESCALATE` | 되돌릴 수 있음(retry_safe 아님이면 M4 확정 뒤 실행) |
| grasp | `dp.grasp_result` (**코드 술어가 애매할 때만**: 그리퍼 폭이 "빈 집기"와 "얇은 물체" 경계) | "What is the grasp progress?" | **M7 S5와 한 목록을 공유**(00-interfaces §11.2, D2 B11): `valid_progress`(after: `holding(target)`), `allowed_change`(after: 파지 유지·자세 조금 변함), `failure`(after: `not holding(target)` — 빈 집기·미끄러짐), `recovering`, + `NONE_ESCALATE`(불확실) | M7 입력(S5), 확정은 코드(T1 `holding`) 우선 |
| lift/transport | `dp.critic_accept` (**M7 FAIL 뒤 M9가 복구 제안 목록을 냈을 때만**) | "Which recovery proposal should run for {phase}? Evidence: {evidence}." | **M9 복구 제안 목록**(코드가 채움, M9 §4.1 L2와 같은 목록: `continue_lower_layer`(FAIL 채널 해소가 코드로 확인됐을 때만), `resume_ckpt_<k>`, `reset_skill`, `safe_wait`) + `NONE_ESCALATE`(M8로 올림). "거절하고 계속" 보기는 없다 | 제안 중 선택만. **M7 FAIL 판정을 뒤집을 수 없다**(00-interfaces §11.2, D2 B10). Zetta 승인자 자리(접목) |
| transport | `dp.transport_mode` (경로 막힘 술어) | "Choose how to continue transport." | `continue`, `slow`, `detour_up`, `regrasp`, `place_safe_now` | 스킬 인자 |
| place | `dp.release` (놓을 자리 위 도달) | "Release now?" | `release_now`, `lower_more`, `adjust_small`, `hold`, `NONE_ESCALATE` | **irreversible**(`effect`): M4 확정 + 코드 안전 술어(접촉·높이) 둘 다 필요. M4 유예 창은 W+1(00-interfaces §14-3, M4 §4.6) |
| (재진입) | `dp.reentry` (복구 동작 끝) | "Resume the skill from which phase?" | 코드가 계산한 재개 가능 단계만(M9 §4.2) | M9 L2와 공유 |

- 한 요청에 여러 질문 묶기(Jev 질문 수 상한 없음, plan §1): 진입 시 `dp.approach_dir` + `dp.next_skill` 확인을 한 요청에.
- M10 규칙은 결정 지점 키가 정확히 맞을 때만 1~2줄 `hint:`로 붙는다(M10 문서).
- **(00 §24, D12) 보기 이름 규칙 — [결정 필요] D32**: 위 표의 보기(`close_now`, `release_now`, `side_front` 등)는 뜻을 이름에 싣는다. Type-Safe Is Not Error-Free(2609.26758, 09-22, D12 메인 재확인): "renaming the two options from 0/1 to no/yes changes 70.4 more answers per hundred ... shifts AUC from .94 to .23", "The hosted model exhibits the same behavior: the swap changes AUC from .8146 to .5806 and produces 24x as many answer flips as its test-retest floor", "the type-error rate remains 0%". 권고: "Use neutral option identifiers and carry the meaning in the rubric". 결정 지점 보기를 중립 식별자로 바꾸고 뜻은 루브릭(질문 템플릿)에 적을지는 M3와 한 항목으로 사용자가 정한다(SUMMARY §5.1 D32). 결정 지점 id(`dp.*`)는 스킬 고정 id 규칙 그대로이고, 바뀔 수 있는 것은 보기 이름뿐이다. 결정 전까지 위 표는 바꾸지 않는다. 자료는 E0.5 (i)·(ii)(E 문서 §2A).

#### 4.1.2a typed 결정 지점 후보 (Harness 탐색 레버에서 도출, 00-interfaces §22) [접목]
Harness VLA §2.2 원문 탐색 레버("staging orders, pre-contact poses, invocation timings for vla_act, and early-return termination thresholds")와 RPent 메모리 교훈의 레버에서 뽑은 후보다. **원문은 typed 보기 없이 자유 JSON 수치 인자를 플래너가 준다.** 우리는 이를 enum(보기 ID)으로 바꾼다. 결정 지점 id 등록은 §4.1.2 표 규칙 그대로(스킬 고정 id, 00-interfaces §11.1). 모두 [접목]이다.

| id 후보 | 보기 | 출처 레버 |
|---|---|---|
| `dp.stage_pose` | 사전 자세: `default_home` / `over_target` / `offset_rim` | pre-contact poses |
| `dp.invoke_now` | 지금 스킬 호출 / 한 번 더 staging | invocation timings for vla_act |
| `dp.chunk_budget` | `short(≤8)`, `mid(12–16)`, `long(24)` — 값은 RPent 교훈 수치에서 가져온 [가정] | early-return termination thresholds, `max_chunks` |
| `dp.retry_prompt` | `grasp-only` / `full-task` | 교훈 "missed pick 뒤 full task 문장 금지" |
| `dp.grasp_verify` | 스킬 불리언 / 영상 증거 | 교훈 "`pi0_pick.success`=false여도 영상상 들고 있으면 계속" |

#### 4.1.3 스킬 실행 쪽 (코드)
단계 FSM(GPSFSM식): 상태 = phase, 전이 = 코드 술어 사건(stop 참, budget 초과, `invariants` 위반, M7 FAIL 뒤 M9 복구 제안). 전이 순간에 해당 결정 지점의 **확정된** Jev 답(M4 출력)을 파라미터로 주입. 확정 답이 없으면 계약의 `default_on_timeout` = **"직전 확정 행동 유지 + 감속"**(`hold_last_committed_slow`). 정지가 아니다. 완전 정지가 필요하면 M7 FAIL을 거친다(00-interfaces §4·§11.2, D2 B8·C6). 이 필드는 §4.1.1 `contract.json`에 있다.

### 4.2 대안 A: 경계만(Harness VLA식; BATON은 보조 참고)
결정 지점을 스킬 사이(진입·출구·재스테이징)에만 둔다. 스킬 내부는 블랙박스. 장점: 기존 스킬을 고치지 않는다. 단점: 사용자 "잘게"보다 거침. → E-M6-1의 G1 조건.

### 4.3 대안 B: 행동 트리(BT)로 조건 노드
스킬 단계를 BT reactive sequence로. 조건 노드는 코드 술어, 코드로 못 쓰는 것만 Jev Noul(Wake 방식의 텍스트 판정자 자리를 Jev로). FSM보다 재개 규칙(M9)이 자연스럽다(매 틱 왼쪽부터 재확인). → E-M6-2.

### 4.4 "기존 스킬"의 정의 [결정 필요] — 세 안이 설계에 주는 영향

[사용자] 문제 설정(user-log 3): "물체를 보고 스킬을 생성해서 잡는 방법들이 많지만 실패할 때가 있다." plan M6: (a) 보유 라이브러리 / (b) 코드 에이전트 생성 / (c) 새 라이브러리.

| 안 | 뜻 | 결정 지점을 어디까지 둘 수 있나 | 계약 필드는 누가 쓰나 | 위험 | 근거 |
|---|---|---|---|---|---|
| (a) 보유 라이브러리 | 벤치마크·로봇에 이미 있는 스킬(예: RoboDojo·LIBERO 제공 프리미티브, 모션 플래너 pick/place) | 스킬이 단계 훅을 안 주면 **경계만**(대안 A). 훅을 주려면 스킬을 단계로 나누는 래퍼 필요 | 사람(또는 SkillWrapper식 오프라인 발명) | 스킬 내부 실패를 못 봄. "가장 약한 노드"(2603.01113)가 그대로 | Harness VLA |
| **(b) 생성 스킬** (본 조건, 구현 먼저) | Astra/코드 에이전트가 과제마다 스킬 코드를 생성(CaP-X식) | 코드 어디든 `jev_choice(dp_id)` 삽입 가능 → **가장 잘게**. `dp_id`는 스킬 계약에 고정된 id 목록 안에서만(생성 코드가 계약도 함께 내고 검증기가 확인) | Astra가 생성, 계약 검증기(코드)가 형식·술어·결정 지점 id 검사 | **SkillsBench(2602.12670 v4): 스스로 만든 스킬이 스킬 없음보다 −8.1~−11.5pp**. 조건: 에이전트가 skill-creator로 스킬 팩을 먼저 만들고 그 팩만으로 풀이(부록 D.6) — 실행 중 실패를 보고 고치는 우리 루프와 조건이 다르다. 생성 코드의 오류가 로봇 동작으로 | CaP-X, SkillsBench(v3/03) |
| **(a') 래퍼 라이브러리** (본 조건, 동등) | (a)를 단계 래퍼로 감싸 계약을 붙인 것. 스킬 몸체는 그대로, 단계 경계에 훅 | 단계 경계 + 인자 | 사람 작성, Astra는 `lookahead_req`만 계획 시점에 채움 | 래퍼가 안 되는 스킬(학습 정책 한 덩어리)은 대안 A로. 사용자 문장("생성해서")과 거리가 있다 | Harness VLA. **SkillsBench 같은 설정에서 사람이 다듬은 스킬은 +18.2~+24.8pp**(D2 A1) — (a')·(c) 쪽 근거 |
| (c) 새 라이브러리 | 우리가 단계 FSM·계약을 갖춘 스킬을 새로 작성 | 설계대로 전부 | 사람 | "기존 스킬"이라는 사용자 표현과 멀어짐, 작성 비용, 비교 공정성(우리만 좋은 스킬) | SkillsBench 사람이 다듬은 스킬 +18.2~+24.8pp(같은 근거) |

**user-log 3 원문은 "물체를 보고 스킬을 생성해서 잡는 방법들이 많지만 실패할 때가 있다. 실패할 때마다 Astra가 개입해서 진행하는 방식을 원한다"이다("기존 방법들을 기본으로 사용"은 첫 세션 초안의 풀어 쓰기, 00 §16). 문제 설정이 생성형을 예로 들므로 (b)를 먼저 한다는 것은 Claude의 해석이다([제안]).** 그래서 이 문서는 (a')를 1순위로 두지 않는다(00-interfaces §11.3, D2 C1). **(b)와 (a')를 동등한 조건**으로 둔다: 같은 계약 형식(4.1.1), 같은 결정 지점 id 목록, 같은 실험 조건(§5 E-M6-1·E-M6-2를 두 본 조건 각각에서 실행). 구현 순서를 정해야 하면 사용자 문장에 가까운 **(b)를 먼저** 만든다. (b)면 Astra가 스킬 코드와 계약을 생성하고 코드가 검증한다. **최종 선택은 [결정 필요, 사용자]**.

#### 4.4a (b) 생성 스킬 경로와 근거 위치 (00-interfaces §22, D10a §1.2·§2.2)
- **Harness VLA는 (a)/(a') 근거이지 (b) 근거가 아니다.** 원문은 코드를 생성하지 않고 고정 어휘만 쓴다(§2.3 "the planner cannot invent new primitives at deployment time", §4 "our agentic planner does not synthesize executable code or new control programs"). 저자도 향후 과제로 ASPIRE식 "propose, validate, and admit a new reusable skill"을 적었다 → (b) + 검증 게이트(§4.5)가 이 빈칸에 들어간다.
- **CaP-X 원문 추출 절차** [원문]: 성공 롤아웃 코드 → 정규식으로 함수 추출 → 2회 이상 등장(`min_occurrences=2`) + 이름 필터(과제 특화 패턴 제외) → LLM 큐레이션. 결과는 **기하 유틸 9개, 사전·사후조건 없음, 스크립트에 자동 검증 없음**.
- **우리 (b)** [접목]: 같은 추출 + 계약(`entry`/`exit`/`effect`, §4.1.1) + typed hole(`jev_choice(dp_id, Enum)`, §4.5) + **실행 기반 검증**(재생 + 새 seed 비열화, M10 게이트와 같은 장치). 원문 "verified"의 뜻이 불분명하므로 검증을 실행 기반으로 정의한다.
- **무엇 위에서 생성하나**: CaP-X의 가장 강한 결과는 "사람이 만든 높은 단계 API일수록 성공률↑, 빼면↓(단조)"와 "저수준은 다회 + VDM으로 높은 단계 다회(M3)와 동등까지"다. 그래서 E-M6-3에 "생성 기반 API 단계" 축을 둔다(§5). 원문 권고("primitive-level performance로 평가")와 우리 설계("접촉 구간은 스킬")가 방향이 달라 이 비교가 필요하다.

### 4.5 생성 스킬 (b)의 typed hole 사후 검사 게이트 [접목, 원문 미평가] (00-interfaces §14·§15)

[원문] PLDI 2025(2504.09246)는 접두부 오토마타와 거주 가능 타입 탐색으로 **디코딩 중**에 타입이 맞지 않는 토큰을 막는다. 원문의 "수리" 과제 이득도 제약 디코딩으로 얻은 것이다. **사후 타입 검사 + 오류 되먹임의 효과는 원문에 없다**(D4 검증 #5·§2-4). 디코딩 제약은 로짓 접근이 필요해 Astra(API, logprob 불가)에는 직접 못 쓴다.

[접목] 아래는 **우리 접목안**이다. 효과 근거는 없고 E-M6-5로 잰다.
- **typed hole**: 생성 스킬 코드의 결정 자리는 `jev_choice(dp_id: DecisionPointId, options: Enum[...]) -> 그 Enum` 형태로만 허용한다(§3 CaP-X 행과 같은 API).
- **게이트 검사**(생성 직후, 실행 전): (i) 타입 검사(mypy/pyright 수준) (ii) `dp_id`가 스킬 계약의 고정 id 목록 안인지(00-interfaces §11.1) (iii) **철저성**: 반환 Enum의 모든 값에 분기가 있는지(`NONE_ESCALATE` 포함) (iv) 모든 술어가 M1 등록부에 있는지 (v) phase마다 `effect`가 있고 `compensate` 스킬 id가 라이브러리에 있는지(§4.1.1).
- **오류 되먹임**: 실패하면 검사기 오류 문장(파일·줄·어느 검사·왜)을 Astra에 되돌려 수리하게 한다. 시점 규칙은 M2 계약 검사와 같다(00-interfaces §14-4). **T0(첫 계획)에서는 수리 왕복 1~2회**를 허용한다. **실행 중 재계획으로 새로 생성된 스킬은 검사만** 하고, 실패하면 그 스킬을 거부하고 M7에 신호를 보낸다. 로봇은 직전 확정 행동을 유지하며 멈추지 않는다(M2 §4.2 R7과 같은 규칙).
- **대칭 조건**: (a') 래퍼 라이브러리에도 같은 게이트를 적용한다(검사 (ii)~(v)). (b)·(a') 동등 비교(00-interfaces §11.3)의 공정 조건이다.
- Hazel식 문맥 넣기(보조, 원문 안 읽음): Astra가 스킬을 쓸 때 각 구멍에 필요한 타입 정의(술어 시그니처, 스킬 계약 스키마)만 골라 문맥에 넣는다. 게이트와 따로 켜고 끌 수 있게 둔다.

---

## 5. 비교 실험 (판정 기준은 실행 전 고정)

공통: 같은 M1 술어 등록부·같은 Astra 계획(고정 계약 파일 재사용)·Jev 버전 고정. **스킬 몸체는 두 본 조건 (b) 생성 / (a') 래퍼 각각에서 고정**하고, E-M6-1·E-M6-2를 두 본 조건에서 모두 돌린다(동등 조건, D2 C1). 하나만 먼저 돌려야 하면 (b) 먼저. 과제 = 단일 pick-and-place + 2단계 연쇄(pick→narrow place) + 섭동 4종(물체 이동, 방해물 삽입, 미끄러짐 주입, 놓을 자리 좁힘). 시드 ≥ 3(시드 = 장면 배치 + 섭동 시각), 평균과 **부트스트랩 95% 구간**(M3·M4·M7·E와 같게). 환경은 **단일 팔 자작 장면**(00 §13, E0~E3와 같음). 양팔 스킬은 본 평가(RoboDojo) 이식 때 다룬다.

### E-M6-1 결합 세밀도 (핵심)
| 조건 | 내용 |
|---|---|
| R | 같은 술어 위 규칙(결정 지점마다 손으로 쓴 if-then) |
| G0 | 부르고 끝: 스킬을 기본 파라미터로 끝까지 실행, 끝나면 Jev가 다음 스킬 선택 |
| G1 | 경계만(대안 A): 진입 시 파라미터 선택 + 출구 뒤 선택 |
| **G2** | 1순위: 단계별 결정 지점(4.1.2) |
| G3 | G2 + `dp.critic_accept`(M9 복구 제안 중 선택, Zetta 자리) |
| SH | Show-Harness식: 스킬 없이 의미 단위 증분(M3 SH 조건과 공유) |
지표: 성공률, 섭동별 성공률, **단계별 실패 분해**(approach/align/grasp/transport/place 중 어디서), 결정 수, Jev 호출 수, 로봇 정지 시간, 완료 시간, 복구 성공률.
판정(사전):
1. G2가 G0보다 섭동 조건 평균 성공률 **+5%p 이상**이고 비섭동에서 −2%p보다 나빠지지 않으면 "잘게 엮기" 채택.
2. G2 − R 차이의 부트스트랩 95% 상한 < +5%p이면 E2a 판정 2와 함께 방향 재검토 보고. 구간이 +5%p를 걸치면 "결론 유보"(00 §13).
3. G3이 G2보다 +3%p 이상이거나 복구 성공률 +10%p 이상이면 critic 승인 질문을 기본에 넣음.
4. SH가 G2보다 grasp·place 단계 실패가 많으면(Show-Harness 원문 관찰과 같은 방향) "접촉 구간은 스킬" 원칙 확정.

### E-M6-2 인터페이스 절제
G2에서 하나씩 뺀다: −예상 결과 술어 / −`entry` / −`lookahead_req` / −`stop` 술어(budget만) / −`NONE_ESCALATE` / FSM 대신 BT(대안 B) / −`effect`(M9 보상 역순 재개와 M4 W+1을 끔. 복구 성공률과 비가역 단계 오확정 수로 판정하며 E-M9와 함께 돌린다). 판정: 빼서 성공률이 **3%p 이상** 떨어지는 필드만 필수로 남긴다. `lookahead_req`는 "narrow place" 과제에서만 판정. BATON(보조)에서 온 필드(`lookahead_req`, `next_entry_ok`)는 이 절제 결과로만 필수 여부를 정한다(00-interfaces §11.3).

### E-M6-3 "기존 스킬" 정의
(b)(Astra 생성 + `jev_choice` 삽입) 대 (a')(래퍼 + 같은 결정 지점) 대 (b) 원형(생성 코드만, Jev 없음 = CaP-X식 기준) 대 (a') 원형(래퍼 없이 부르고 끝). 지표에 **생성 코드 형식 오류율, 계약 검증 거부율, 래퍼 작성 시간(사람)** 추가. 판정(대칭, 사전): (b)가 (a')보다 3%p 이상 낮으면 SkillsBench 자기 생성 경고가 우리에게도 해당된다고 보고. (a')가 (b)보다 3%p 이상 낮으면 SkillsBench "사람이 다듬은 스킬" 이득이 우리 래퍼에는 나오지 않는다고 보고. 부트스트랩 95% 구간이 겹치면 "차이 없음". 어느 쪽이든 본 조건 선택은 사용자에게 올린다.
- **축 추가: 생성 기반 API 단계** (00-interfaces §22, D10a §2.2) [제안]: (b)를 두 판으로 나눈다. **높은 단계** = 우리 스킬 다발 위에서 생성(CaP-X S2/M3 대응) / **저수준** = M1 술어 + IK만 위에서 생성(CaP-X S3/M4 대응). 같은 지표로 보고한다.

### E-M6-4 Astra 스킬 카드 점진 공개
Astra 계획에 (i) 카드만(메타 ~100토큰/스킬) 대 (ii) 본문 전부. 지표: 계획 성공률(계약 검증 통과율), 입력 토큰, 첫 계획 지연. 판정: (i)가 계획 통과율 −2%p 이내면 (i).

### E-M6-5 typed hole 게이트 (§4.5, 우리 접목안 검증)
(b) 생성 조건에서 게이트 켬 대 게이트 끔(코드 안전 규칙만 남김) 대 게이트 켬 + Hazel식 문맥. 지표: **첫 생성 합격률**, T0 수리 왕복 횟수와 왕복 뒤 합격률, 실행 중 재생성 스킬 거부율, 거부 유형(타입 / id / 철저성 / 술어 / `effect`), 실행 중 오류(런타임 예외·정의되지 않은 분기)로 인한 실패 수, 과제 성공률. 판정(사전, [제안]): 게이트 켬이 끔보다 실행 중 오류 실패를 절반 이하로 줄이고 성공률이 −2%p보다 나빠지지 않으면 게이트를 기본으로 둔다. 첫 생성 합격률이 50% 미만이면 T0 지연을 따로 보고하고, 카드·예시 계약을 프롬프트에 넣는 조건을 더한다.

---

## 6. 반대 증거와 위험
- **스타 순위와 사용자 기준 불일치**(v3/06): 스타 1위 PhyAgentOS는 거친 결합. 잘게 엮는 근거(Zetta 승인자, Show-Harness)는 원문이 LLM 승인자·스텝 VLM이고, **Jev를 그 자리에 넣는 것은 우리 접목**이다.
- **SkillsBench(v3/03, v4)**: 사전 생성 스킬이 스킬 없음보다 나쁨(−8.1~−11.5pp, skill-creator로 팩을 먼저 만들고 그것만 쓰는 조건). (b)안의 위험. 반대로 같은 설정에서 사람이 다듬은 스킬은 +18.2~+24.8pp — (a')·(c)가 이 이득을 얻는다는 보장은 없다(래퍼 품질 의존).
- **2603.01113**: 한계는 계획기가 아니라 가장 약한 행동 노드. Jev 결정이 좋아도 스킬 몸체가 약하면 이득이 안 보일 수 있다 → 단계별 실패 분해를 필수 지표로 둔 이유.
- **결정 지점이 많을수록 Jev 호출·M4 확정 지연이 쌓인다.** Show-Harness 선택적 청킹(96%) 대 청킹 끔(96%, 호출 증가) — 더 잘게가 항상 이득은 아니다.
- **MCP annotations는 힌트다**(명세: untrusted). `irreversible` 선언을 믿고 안전을 넘기면 안 된다. 코드 안전 술어가 최종.
- BATON은 심사 전·인용 1이라 보조 참고로만 둔다(D2 A1이 초록·본문 문장은 확인). GPSFSM의 BTGenBot 대비 우위는 GPT 모델에서만이고 로컬 모델에서는 BTGenBot이 낫다(Table I) — FSM 선택의 근거로 과장하지 않는다.
- **MCP idempotent ≠ 로봇 재시도 안전**: 뜻이 바뀌므로 `retry_safe`는 우리 정의로 둔다(§3).
- **보기 이름 편향(00 §24, D12)**: Type-Safe(2609.26758)는 typed 모델의 보기 이름 편향이 type-error 0%인 채로 생긴다는 것을 보였다(0/1 → no/yes, 100개당 70.4개 답 변경). M4 반복 합의로는 안 걸러진다 → [결정 필요] D32.
- **질문 형태(00 §24, D12, [초록만])**: C²Nav(2609.15142)는 VLM이 제어기가 만든 대안을 비교하게 하고 기하·문턱·행동 크기는 물리 쪽에 두었다. 비교형 질문을 절댓값형으로 바꾸면 SR이 12~28%로 떨어진다. "코드 술어로 답이 나오는 것은 묻지 않고, 코드가 만든 보기 중 고르게 한다"는 §4.1.2 원칙의 근거 후보로 인용한다. 초록만 읽었다.
- Zetta 원문 불일치(온라인 LLM 승인자 대 인프라 절 "온라인 에이전트 없음", v3/16 #23).
- **typed hole 게이트는 원문이 평가하지 않은 접목안이다**(00-interfaces §15): PLDI 2025 결과는 디코딩 중 제약이다. 사후 검사 + 수리로 바꾸면 같은 효과가 난다는 근거가 없다. 수리 왕복은 T0 지연을 늘린다.
- **`effect`의 근거와 한계**: 사가(1987)는 기초 문헌이고 원문을 읽지 않았다. SagaLLM은 PVLDB 18(12)로 확정됐지만 2025-03-15 공개라 기간 8일 밖이고 수치는 확인하지 못했다. Atomix는 무학회다. 모두 소프트웨어 효과가 대상이다. 로봇의 보상 스킬은 원상 복구를 보장하지 못한다(물체가 움직임). 그래서 보상 뒤 `entry` 재확인이 필수다. 가역/비가역 표지를 잘못 붙이면 M9가 되돌릴 수 없는 것을 되돌리려 할 수 있다 → 코드 안전 술어가 최종이다.

### 6a. 차별 문장 후보 (D10a §1.2·§2.2 초안, 00-interfaces §22)
- "Harness VLA는 프리미티브 하나가 끝날 때마다 플래너가 결과 파일을 기다렸다가 다음 JSON 호출을 고르는 동기 REPL이며(부록 A 'The planner waits for these files before selecting the next primitive'), 저자 스스로 플래너와 하위 VLA 사이가 열린 고리라고 적었다(§5). VLA 실행 중에는 플래너가 정한 stop 술어와 청크 예산만 작동한다. 우리는 스킬 안 단계 경계마다 typed 결정 지점을 두고 Jev가 로봇을 멈추지 않은 채 겹쳐 답하며, Astra는 실패 신호가 날 때만 비동기로 부른다."
- "CaP-X의 한 턴은 생성한 프로그램 한 편을 끝까지 실행한 뒤, stdout/stderr와 VLM 시각 차분 텍스트를 보고 프로그램 전체를 다시 생성할지(REGENERATE) 끝낼지(FINISH)를 정한다(§2, §3.2). 성공 롤아웃에서 뽑은 스킬 라이브러리는 사전·사후조건이 없는 기하 유틸리티 9개다(부록 H.1). 우리는 생성 스킬에 진입·출구·효과 계약과 typed 결정 지점을 붙여 실행 중 결정 지점 단위로 고르고, 실패하면 전체 재생성이 아니라 사전조건이 참인 가장 늦은 체크포인트에서 재개한다."
- "CaP-X는 접촉이 많은 과제(삽입·붓기)에서 코드 제어가 약하다고 적고 코딩 에이전트 + VLA 혼합을 향후 과제로 남겼다(부록 A). Harness VLA가 그 혼합을 동기 루프로 구현했다. 우리는 같은 분업을 비동기 typed 결정으로 한다."

## 7. 열린 질문, [결정 필요]
1. [결정 필요, 사용자] "기존 스킬"의 정의: (b) 생성과 (a') 래퍼를 동등 조건으로 둘 다 실험(구현은 (b) 먼저) 뒤 선택, 또는 처음부터 한쪽(4.4).
2. [결정 필요] 5위: ROSClaw(저장소 연결 추정) 대 Show-Harness(논문 링크 확인).
3. 스킬 단계 구조: FSM(1순위) 대 BT(대안 B) — E-M6-2로.
4. 양팔 벤치마크면 `arms` 필드와 "어느 팔" 결정 지점이 추가된다(plan M6).
5. `lookahead_req`를 Astra가 계획 때 채울지, 스킬 작성자가 표로 둘지(필드 존속은 E-M6-2 결과가 먼저).
6. `dp.grasp_result`처럼 코드 술어가 애매한 곳의 경계(그리퍼 폭 임계)는 M7 보정과 같이 정한다.
7. [결정 필요] 되돌릴 수 없음을 누가 정하나: `annotations.irreversible_phases`(스킬 작성자) / M2 계약 단계 수준 `irreversible`(Astra) / 사용자 목록. M2 §7-4와 **한 [결정 필요]**로 묶는다(D2 B7). 어느 안이든 코드 안전 규칙이 최종.
8. 해소(00-interfaces §14-3, D4 §14-3): 스킬 계약 phase별 `effect`(가역 + 보상 스킬 id / 비가역)를 **채택**한다. M9는 보상 역순, 비가역 경계 너머 되돌리기 금지, M4는 비가역 보기 W+1. 메인 세션 잠정 결정이며 E-M6-2(−`effect` 절제)와 E-M9로 검증한다. 누가 표지를 붙이느냐는 7번 [결정 필요]에 그대로 남는다. 생성 스킬 (b)의 typed hole 게이트(§4.5)도 00-interfaces §14에 따라 넣었고, 원문 미평가 접목안이라 E-M6-5로 검증한다.
9. [결정 필요] D32(00 §24, SUMMARY §5.1, M3 §7-9와 한 항목): 결정 지점 보기를 중립 식별자로 바꾸고 뜻은 루브릭에 적는 규칙을 (i) E0.5 (i) 결과 전에 기본으로 둘지 / (ii) E0.5 (i) 결과를 본 뒤 정할지 / (iii) 지금 이름을 유지할지. 결정 전까지 §4.1.2 표는 바꾸지 않는다.

## 8. 확인 못 한 것
- Agent Skills 공개 표준화 날짜(2025-12-18)는 2차 출처(firecrawl 블로그)만 봤다.
- BATON 표 수치, SkillWrapper 학회. (GPSFSM의 BTGenBot 대비 수치는 D2 검증 Table I 값으로 채웠다.)
- 스타 수 재측정(API 금지). 2025-09-23 이후 스킬 논문 중 v3/06 이후(9/23 이후) 새로 뜬 고스타 저장소.
- 로봇에서 Agent Skills(SKILL.md) 형식을 스킬 계약으로 쓴 선행: PhyAgentOS가 SKILL.md를 절차 기억으로 씀(원문 문장 확인). 그 밖은 찾지 않았다(부재 주장 안 함).
- "스킬 내부 단계마다 typed 결정 모델 질문"의 로봇 선행: v3/07 결론(로봇 선점 없음, 비로봇 선례 있음)을 따르고 이번에 새로 검색하지 않았다.
- Sagas 1987 원문, SagaLLM의 VLDB 트랙(연구/산업)과 본문 수치, PLDI 논문 쪽수(601–626, ACM 403), Hazel OOPSLA 2024 원문. SagaLLM 권·호·쪽, Atomix §2 효과 분류, PLDI 채택은 D4 검증 #1·#2·#5에 기댄다. 이번에 다시 읽지 않았다.
- 로봇 스킬에 가역/비가역 효과 표지와 보상 스킬을 붙인 선행: 따로 검색하지 않았다. 부재 주장 안 함.
