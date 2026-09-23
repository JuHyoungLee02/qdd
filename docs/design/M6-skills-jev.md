# M6. 스킬과 Jev 결합 — 모듈 설계 (단계 2)

> **정본 우선**: 모듈 사이 인터페이스·정지·확정 규칙·확률 게이트·시간 값은 `00-interfaces.md`가 우선한다(2026-09-23 22:00 UTC). 이 문서와 다르면 그쪽을 따른다.
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
| **Harness VLA** 프리미티브 호출 △ | 로봇 | 고정 어휘 JSON 호출, `vla_act{prompt, max_chunks, stop 술어}`, post-condition까지 실행, "planner cannot invent new primitives". LIBERO-Pro +38.6%p 등(v3/06, 가장 강한 관련 기준 대비) | MED-HIGH(칭화, 962★, 인용 23) | 2026-07 | 예 | 예(시뮬만) |
| **PhyAgentOS** 세션 계약 + SKILLRUNTIME.md ◎△ | 로봇 | 세션 계약 = 목표, 런타임·타깃, **사전조건, 실행 한계, 수용 기준**(§3.3). SKILLRUNTIME.md = "required observations, produced action forms, orchestration mode, configurable parameters, and adapter requirements". 판정 {success, failure, replan} | MED(2,481★, 인용 4, 저장소가 논문보다 4개월 먼저) | 2026-07 | 예 | 예 |
| **Zetta** 재진입 계약·critic 제안 △ | 로봇 | critic 제안 = (증거, 제안 모드), Orchestrator가 승인할 때만 개입(§2.1.3). 재진입 = "실패 증거 해소 AND 접촉 안정"(§2.5.1). LIBERO-Pro 90.8%, RoboCasa 93.6%(현재 rollout 예산 기준 단서) | MED(칭화 AIR, 1,252★) | 2026-08 | 예(오프라인 진화는 롤아웃 필요) | 예 |
| **BATON** 전이 인지 계약 ◎ | 로봇 | "VLA primitive carries an **exit** condition but no **entry** condition" 을 지적. 세 전이: invocation(손목 카메라로 준비 확인 뒤에만 VLA 호출), handoff(앞 단계 잔여물이 흐트린 진입 상태 복구), **lookahead**(뒤 단계가 요구하는 조건이 지금 단계의 실행 방식을 정함). RoboMemArena 과제 성공 +11.6, 누적 +14.9(SoTA 대비, 초록 "%", 본문 "points" → %p) | LOW-MED(USC, 심사 전, 2026-08-17, 인용 1). **보조 참고**: 계약 필드를 좌우하는 근거로 쓰지 않는다(00-interfaces §11.3, D2 C5). 필드는 HIGH 근거나 우리 실험으로 정한다(§3) | 2026-08 | 예(파라미터 갱신 없음) | 예 |
| **GPSFSM** (2607.15674) ○ | 로봇 | LLM이 부분 명세 FSM(상태, **사건 촉발 전이**, Sequential/Recovery/Parallel-Any/All)을 생성, 엔진이 파싱·검증·실행, ROS 2 Capabilities2에 **실행 시 파라미터 주입**·비동기 사건. **정정(D2 A1)**: BTGenBot보다 나은 것은 **GPT 모델에서만**(성공 90%·부분 10% 대 BTGenBot 54/11/34%). **로컬 모델에서는 BTGenBot이 더 나음**(13/35/52 대 10/22/68). 5개 항법 과제, 사람 평가자 3명(Table I) | MED-HIGH(**IROS 2026 채택**, arXiv 코멘트) | 2026-07 | 예 | 예 |
| MoA 대화형 계획 → BT (2603.01113) ○ | 로봇 | 전문 에이전트가 **자기 전제 설명에 해당하는 질문만** 답하고 나머지는 넘김(기권 기반 위임), BT로 재시도·정책 전환. 사람 응답 약 27% 감소. "**적용 한계는 계획기가 아니라 가장 약한 행동 노드의 신뢰도**"(초록) | LOW-MED(와세다 Ogata 연구실, 심사 미표기) | 2026-03 | 예 | 예(실물) |
| VLM 행동 트리 조건 노드 (Wake, 2501.03968) ○ | 로봇 | VLM이 조건을 **자유 텍스트 조건 노드**로 BT에 넣고, 실행 때 다른 VLM이 이미지로 참/거짓 판정 | MED(Microsoft) | **기간 밖(2025-01), 기초 문헌** | 예 | 예 |
| 행동 트리 reactive sequence / PA-BT (Colledanchise·Ögren) | 로봇 | 매 틱 조건 재확인, 사전조건 거짓이면 그 조건을 만드는 하위 트리로 확장 | 기초 | **기간 밖, 기초 문헌**(M9 문서와 같음, 원문 재확인 안 함) | 예 | 예 |
| SkillWrapper (2511.18203) ○ | 로봇 TAMP | 기반 모델로 **블랙박스 스킬의 사전조건·효과 술어를 생성·학습**, "provably sound and complete planning", 실물 장기 과제 | MED(Brown, Tellex. 학회 미확인, v7까지 개정) | 2025-11 | 데이터 수집 필요(학습 없음이지만 능동 수집) | 예 |
| CaP-X 코드 턴 △ | 로봇 | 턴 = 프로그램 한 편 끝까지 실행, 성공 롤아웃에서 스킬 9개 추출(CaP-Agent0) | HIGH(ICML 2026, 819★) | 2026-03 | 예 | 예 |
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
| CaP-X | 코드 턴, 성공 롤아웃에서 스킬 추출 | "기존 스킬 = 생성(b)"일 때: 생성 코드 안에 `jev_choice(dp_id)` 호출만 허용하는 API(v2부터 우리 제안, 원문 아님) |

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
  "outputSchema": { "result": "enum[ok, stopped_early, budget_exceeded, precondition_false, error]",
                    "exit_predicates": "map<predicate,bool>" }
}
```
- 파라미터 범위: **enum(보기 ID)만**. 순서형은 M3의 보기 수 실험(E-M3-1) 결과 N을 따른다. 코드 표가 enum 값을 수치로 바꾼다(Jev 수치 약함, plan §1).
- 술어: 모두 M1 술어 등록부 이름(수치 인자 없음). `reachable`·`aligned_*`·`at_pregrasp`·`contact_stable`은 T2라 M7 하드 채널(즉시 FAIL)에 쓰이지 않고 소프트 채널로만 간다(00-interfaces §11.2). `holding`·`gripper_open`·`lifted`는 T1.
- Astra 권한: 계약에 있는 스킬·보기·**결정 지점 id**만 고른다(Harness VLA "cannot invent"). 결정 지점 id는 이 스킬 계약에 고정된 것이 정본이고, M2 세션 계약은 그 id를 골라 쓰고 인자(예: `target`)만 채운다. M10 Jev 규칙 키도 같은 id를 쓴다(00-interfaces §11.1). 새 스킬·새 결정 지점 제안은 오프라인 경로(M10 검증 게이트)로만.

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
| lift/transport | `dp.critic_accept` (**M9가 복구 제안 목록을 냈을 때만**: M7 FAIL 뒤 또는 WARN의 모드 제안) | "Which recovery proposal should run for {phase}? Evidence: {evidence}." | **M9 복구 제안 목록**(코드가 채움, 예: `retry_grasp_once`, `regrasp`, `restage`) + `NONE_ESCALATE`(M8로 올림). "거절하고 계속" 보기는 없다 | 제안 중 선택만. **M7 FAIL 판정을 뒤집을 수 없다**(00-interfaces §11.2, D2 B10). Zetta 승인자 자리(접목) |
| transport | `dp.transport_mode` (경로 막힘 술어) | "Choose how to continue transport." | `continue`, `slow`, `detour_up`, `regrasp`, `place_safe_now` | 스킬 인자 |
| place | `dp.release` (놓을 자리 위 도달) | "Release now?" | `release_now`, `lower_more`, `adjust_small`, `hold`, `NONE_ESCALATE` | **irreversible**: M4 확정 + 코드 안전 술어(접촉·높이) 둘 다 필요 |
| (재진입) | `dp.reentry` (복구 동작 끝) | "Resume the skill from which phase?" | 코드가 계산한 재개 가능 단계만(M9 §4.2) | M9 L2와 공유 |

- 한 요청에 여러 질문 묶기(Jev 질문 수 상한 없음, plan §1): 진입 시 `dp.approach_dir` + `dp.next_skill` 확인을 한 요청에.
- M10 규칙은 결정 지점 키가 정확히 맞을 때만 1~2줄 `hint:`로 붙는다(M10 문서).

#### 4.1.3 스킬 실행 쪽 (코드)
단계 FSM(GPSFSM식): 상태 = phase, 전이 = 코드 술어 사건(stop 참, budget 초과, `invariants` 위반, M7 FAIL 뒤 M9 복구 제안). 전이 순간에 해당 결정 지점의 **확정된** Jev 답(M4 출력)을 파라미터로 주입. 확정 답이 없으면 계약의 `default_on_timeout` = **"직전 확정 행동 유지 + 감속"**(`hold_last_committed_slow`). 정지가 아니다. 완전 정지가 필요하면 M7 FAIL을 거친다(00-interfaces §4·§11.2, D2 B8·C6). 이 필드는 §4.1.1 `contract.json`에 있다.

### 4.2 대안 A: 경계만(Harness VLA식; BATON은 보조 참고)
결정 지점을 스킬 사이(진입·출구·재스테이징)에만 둔다. 스킬 내부는 블랙박스. 장점: 기존 스킬을 고치지 않는다. 단점: 사용자 "잘게"보다 거침. → E-M6-1의 G1 조건.

### 4.3 대안 B: 행동 트리(BT)로 조건 노드
스킬 단계를 BT reactive sequence로. 조건 노드는 코드 술어, 코드로 못 쓰는 것만 Jev Noul(Wake 방식의 텍스트 판정자 자리를 Jev로). FSM보다 재개 규칙(M9)이 자연스럽다(매 틱 왼쪽부터 재확인). → E-M6-2.

### 4.4 "기존 스킬"의 정의 [결정 필요] — 세 안이 설계에 주는 영향

[사용자] 문제 설정: "물체를 보고 스킬을 생성해서 잡는 기존 방법". plan M6: (a) 보유 라이브러리 / (b) 코드 에이전트 생성 / (c) 새 라이브러리.

| 안 | 뜻 | 결정 지점을 어디까지 둘 수 있나 | 계약 필드는 누가 쓰나 | 위험 | 근거 |
|---|---|---|---|---|---|
| (a) 보유 라이브러리 | 벤치마크·로봇에 이미 있는 스킬(예: RoboDojo·LIBERO 제공 프리미티브, 모션 플래너 pick/place) | 스킬이 단계 훅을 안 주면 **경계만**(대안 A). 훅을 주려면 스킬을 단계로 나누는 래퍼 필요 | 사람(또는 SkillWrapper식 오프라인 발명) | 스킬 내부 실패를 못 봄. "가장 약한 노드"(2603.01113)가 그대로 | Harness VLA |
| **(b) 생성 스킬** (본 조건, 구현 먼저) | Astra/코드 에이전트가 과제마다 스킬 코드를 생성(CaP-X식) | 코드 어디든 `jev_choice(dp_id)` 삽입 가능 → **가장 잘게**. `dp_id`는 스킬 계약에 고정된 id 목록 안에서만(생성 코드가 계약도 함께 내고 검증기가 확인) | Astra가 생성, 계약 검증기(코드)가 형식·술어·결정 지점 id 검사 | **SkillsBench(2602.12670 v4): 스스로 만든 스킬이 스킬 없음보다 −8.1~−11.5pp**. 조건: 에이전트가 skill-creator로 스킬 팩을 먼저 만들고 그 팩만으로 풀이(부록 D.6) — 실행 중 실패를 보고 고치는 우리 루프와 조건이 다르다. 생성 코드의 오류가 로봇 동작으로 | CaP-X, SkillsBench(v3/03) |
| **(a') 래퍼 라이브러리** (본 조건, 동등) | (a)를 단계 래퍼로 감싸 계약을 붙인 것. 스킬 몸체는 그대로, 단계 경계에 훅 | 단계 경계 + 인자 | 사람 작성, Astra는 `lookahead_req`만 계획 시점에 채움 | 래퍼가 안 되는 스킬(학습 정책 한 덩어리)은 대안 A로. 사용자 문장("생성해서")과 거리가 있다 | Harness VLA. **SkillsBench 같은 설정에서 사람이 다듬은 스킬은 +18.2~+24.8pp**(D2 A1) — (a')·(c) 쪽 근거 |
| (c) 새 라이브러리 | 우리가 단계 FSM·계약을 갖춘 스킬을 새로 작성 | 설계대로 전부 | 사람 | "기존 스킬"이라는 사용자 표현과 멀어짐, 작성 비용, 비교 공정성(우리만 좋은 스킬) | SkillsBench 사람이 다듬은 스킬 +18.2~+24.8pp(같은 근거) |

**사용자 표현("물체를 보고 스킬을 생성해서 잡는 기존 방법들을 기본으로 사용")은 (b)에 가깝다.** 그래서 이 문서는 (a')를 1순위로 두지 않는다(00-interfaces §11.3, D2 C1). **(b)와 (a')를 동등한 조건**으로 둔다: 같은 계약 형식(4.1.1), 같은 결정 지점 id 목록, 같은 실험 조건(§5 E-M6-1·E-M6-2를 두 본 조건 각각에서 실행). 구현 순서를 정해야 하면 사용자 문장에 가까운 **(b)를 먼저** 만든다. (b)면 Astra가 스킬 코드와 계약을 생성하고 코드가 검증한다. **최종 선택은 [결정 필요, 사용자]**.

---

## 5. 비교 실험 (판정 기준은 실행 전 고정)

공통: 같은 M1 술어 등록부·같은 Astra 계획(고정 계약 파일 재사용)·Jev 버전 고정. **스킬 몸체는 두 본 조건 (b) 생성 / (a') 래퍼 각각에서 고정**하고, E-M6-1·E-M6-2를 두 본 조건에서 모두 돌린다(동등 조건, D2 C1). 하나만 먼저 돌려야 하면 (b) 먼저. 과제 = 단일 pick-and-place + 2단계 연쇄(pick→narrow place) + 섭동 4종(물체 이동, 방해물 삽입, 미끄러짐 주입, 놓을 자리 좁힘). 시드 ≥ 3(시드 = 장면 배치 + 섭동 시각), **평균 ± 표준편차**. 시뮬(RoboDojo-Sim 또는 LIBERO 계열, plan [결정 필요] 3 따름).

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
2. G2가 R보다 낫지 않으면(차이의 평균 − 표준편차 ≤ 0) E2(plan 마차 시험)와 함께 방향 재검토 보고.
3. G3이 G2보다 +3%p 이상이거나 복구 성공률 +10%p 이상이면 critic 승인 질문을 기본에 넣음.
4. SH가 G2보다 grasp·place 단계 실패가 많으면(Show-Harness 원문 관찰과 같은 방향) "접촉 구간은 스킬" 원칙 확정.

### E-M6-2 인터페이스 절제
G2에서 하나씩 뺀다: −예상 결과 술어 / −`entry` / −`lookahead_req` / −`stop` 술어(budget만) / −`NONE_ESCALATE` / FSM 대신 BT(대안 B). 판정: 빼서 성공률이 **3%p 이상** 떨어지는 필드만 필수로 남긴다. `lookahead_req`는 "narrow place" 과제에서만 판정. BATON(보조)에서 온 필드(`lookahead_req`, `next_entry_ok`)는 이 절제 결과로만 필수 여부를 정한다(00-interfaces §11.3).

### E-M6-3 "기존 스킬" 정의
(b)(Astra 생성 + `jev_choice` 삽입) 대 (a')(래퍼 + 같은 결정 지점) 대 (b) 원형(생성 코드만, Jev 없음 = CaP-X식 기준) 대 (a') 원형(래퍼 없이 부르고 끝). 지표에 **생성 코드 형식 오류율, 계약 검증 거부율, 래퍼 작성 시간(사람)** 추가. 판정(대칭, 사전): (b)가 (a')보다 3%p 이상 낮으면 SkillsBench 자기 생성 경고가 우리에게도 해당된다고 보고. (a')가 (b)보다 3%p 이상 낮으면 SkillsBench "사람이 다듬은 스킬" 이득이 우리 래퍼에는 나오지 않는다고 보고. 부트스트랩 95% 구간이 겹치면 "차이 없음". 어느 쪽이든 본 조건 선택은 사용자에게 올린다.

### E-M6-4 Astra 스킬 카드 점진 공개
Astra 계획에 (i) 카드만(메타 ~100토큰/스킬) 대 (ii) 본문 전부. 지표: 계획 성공률(계약 검증 통과율), 입력 토큰, 첫 계획 지연. 판정: (i)가 계획 통과율 −2%p 이내면 (i).

---

## 6. 반대 증거와 위험
- **스타 순위와 사용자 기준 불일치**(v3/06): 스타 1위 PhyAgentOS는 거친 결합. 잘게 엮는 근거(Zetta 승인자, Show-Harness)는 원문이 LLM 승인자·스텝 VLM이고, **Jev를 그 자리에 넣는 것은 우리 접목**이다.
- **SkillsBench(v3/03, v4)**: 사전 생성 스킬이 스킬 없음보다 나쁨(−8.1~−11.5pp, skill-creator로 팩을 먼저 만들고 그것만 쓰는 조건). (b)안의 위험. 반대로 같은 설정에서 사람이 다듬은 스킬은 +18.2~+24.8pp — (a')·(c)가 이 이득을 얻는다는 보장은 없다(래퍼 품질 의존).
- **2603.01113**: 한계는 계획기가 아니라 가장 약한 행동 노드. Jev 결정이 좋아도 스킬 몸체가 약하면 이득이 안 보일 수 있다 → 단계별 실패 분해를 필수 지표로 둔 이유.
- **결정 지점이 많을수록 Jev 호출·M4 확정 지연이 쌓인다.** Show-Harness 선택적 청킹(96%) 대 청킹 끔(96%, 호출 증가) — 더 잘게가 항상 이득은 아니다.
- **MCP annotations는 힌트다**(명세: untrusted). `irreversible` 선언을 믿고 안전을 넘기면 안 된다. 코드 안전 술어가 최종.
- BATON은 심사 전·인용 1이라 보조 참고로만 둔다(D2 A1이 초록·본문 문장은 확인). GPSFSM의 BTGenBot 대비 우위는 GPT 모델에서만이고 로컬 모델에서는 BTGenBot이 낫다(Table I) — FSM 선택의 근거로 과장하지 않는다.
- **MCP idempotent ≠ 로봇 재시도 안전**: 뜻이 바뀌므로 `retry_safe`는 우리 정의로 둔다(§3).
- Zetta 원문 불일치(온라인 LLM 승인자 대 인프라 절 "온라인 에이전트 없음", v3/16 #23).

## 7. 열린 질문, [결정 필요]
1. [결정 필요, 사용자] "기존 스킬"의 정의: (b) 생성과 (a') 래퍼를 동등 조건으로 둘 다 실험(구현은 (b) 먼저) 뒤 선택, 또는 처음부터 한쪽(4.4).
2. [결정 필요] 5위: ROSClaw(저장소 연결 추정) 대 Show-Harness(논문 링크 확인).
3. 스킬 단계 구조: FSM(1순위) 대 BT(대안 B) — E-M6-2로.
4. 양팔 벤치마크면 `arms` 필드와 "어느 팔" 결정 지점이 추가된다(plan M6).
5. `lookahead_req`를 Astra가 계획 때 채울지, 스킬 작성자가 표로 둘지(필드 존속은 E-M6-2 결과가 먼저).
6. `dp.grasp_result`처럼 코드 술어가 애매한 곳의 경계(그리퍼 폭 임계)는 M7 보정과 같이 정한다.
7. [결정 필요] 되돌릴 수 없음을 누가 정하나: `annotations.irreversible_phases`(스킬 작성자) / M2 계약 단계 수준 `irreversible`(Astra) / 사용자 목록. M2 §7-4와 **한 [결정 필요]**로 묶는다(D2 B7). 어느 안이든 코드 안전 규칙이 최종.

## 8. 확인 못 한 것
- Agent Skills 공개 표준화 날짜(2025-12-18)는 2차 출처(firecrawl 블로그)만 봤다.
- BATON 표 수치, SkillWrapper 학회. (GPSFSM의 BTGenBot 대비 수치는 D2 검증 Table I 값으로 채웠다.)
- 스타 수 재측정(API 금지). 2025-09-23 이후 스킬 논문 중 v3/06 이후(9/23 이후) 새로 뜬 고스타 저장소.
- 로봇에서 Agent Skills(SKILL.md) 형식을 스킬 계약으로 쓴 선행: PhyAgentOS가 SKILL.md를 절차 기억으로 씀(원문 문장 확인). 그 밖은 찾지 않았다(부재 주장 안 함).
- "스킬 내부 단계마다 typed 결정 모델 질문"의 로봇 선행: v3/07 결론(로봇 선점 없음, 비로봇 선례 있음)을 따르고 이번에 새로 검색하지 않았다.
