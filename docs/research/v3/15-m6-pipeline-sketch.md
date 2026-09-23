# v3-15: M6 스타 상위 5(+1)개의 루프 구조와 Harvest 파이프라인 대략안

작성: 2026-09-24, 조사 에이전트. 사용자 지시(user-log 11, 스킬 항목): "1년 이내에 나온 GitHub 스타 상위 5개 중에서, LLM이 스킬을 불러오고 끝이 아니라 잘게 엮어 놓은 논문을 참고해 파이프라인을 대충 짜 본다." [사용자]
같은 사용자 지시: 상세 설계 단계는 모듈에 집중하고 파이프라인은 깊게 들어가지 않는다 [사용자] → 3절은 **한 쪽짜리 대략안**이다. 확정이 아니다.

표기: **[원문]** = arXiv 본문에서 직접 읽은 것(절 번호 표시) / **[해석]** = 우리 해석·접목안 / [제안] = 이 보고서의 제안.

## 1. 조사 방법과 한계
- 6편의 arXiv HTML 본문을 받아 방법 절을 읽었다(요청 간격 3초): PhyAgentOS 2607.16636 §3.2–4.3, Zetta 2608.16590 §2.1, §2.5–2.6, Harness VLA 2607.08448 §2, §3.3 Key Finding 2, §5, 부록 A, CaP-X 2603.22435 §2–4, ROSClaw 2603.26997 §III, Show-Harness 2609.10522 §3, §5.4.3.
- WebSearch 0회. arXiv 검색 API, Semantic Scholar API, GitHub API 쓰지 않음. 스타·인용·신뢰도는 다시 재지 않고 v3/06, v3/08 값을 따른다(PhyAgentOS 2,481★, Zetta 1,252★, Harness VLA 962★, CaP-X 819★ ICML 2026, ROSClaw 625★ 저장소 연결 추정, Show-Harness 451★).
- 한계: HTML 변환에서 수식이 빠져 식 (1)–(14)의 기호는 읽지 못했다. Zetta의 critic 주기, Show-Harness의 스텝당 벽시계 시간은 **원문에 숫자가 없다**(찾은 검색어: Hz, latency, per step, wall-clock).

## 2. 논문별 루프 구조 (원문)

### 2.1 PhyAgentOS (1위) — 세션 단위, LLM은 루프 밖
- [원문 §3.2] 흐름: Goal Planner → Goal Graph/Session Compiler → SkillRuntime-Target Selector가 **세션 계약**을 만든다 → WatchdogSupervisor가 preflight 후 SessionRunner 생성 → 종료 시 증거를 적고 SessionVerifier가 판정.
- [원문 §3.3] 세션 계약 = 목표, 선택된 런타임·타깃, 사전조건, 실행 한계, **수용 기준**. 판정은 success / failure / replan.
- [원문 §3.5.1] PolicySkillRuntime: "The Agent remains outside the low-level loop after compiling the session." 제어 주기 루프는 런타임이 돈다.
- [원문 §3.5.2] BuiltinSkillRuntime: Agent가 "observe, decide, invoke a tool, and observe again" 온라인 도구 루프에 들어간다(도구 호출 단위).
- [원문 §3.6, §4.1] 계층 사이 상태는 Markdown 파일(SESSIONS, SKILLRUNTIME, TARGETS, ENVIRONMENT, LESSONS). ENVIRONMENT.md = 인식 결과를 "entities, attributes, relations, and state changes"로 줄인 것. "does not move latency-sensitive perception or control into the protocol layer."
- [원문 §4.2] 검증기 입력 = 초기·종료 관측, 과제 정의, ENVIRONMENT 스냅샷, 행동-관측 이력. replan이면 원 시도는 그대로 두고 자식 세션을 만든다.
- [원문 §4.3] Execute → Verify → Diagnose → Revise → Re-verify → Consolidate. "only after the outcome is verified is the resulting knowledge committed." KNOWLEDGE.md(성공 패턴)와 LESSONS.md(검증된 실패 교정) 분리.
- [해석] 결합은 거칠다. 가져올 것은 **계약 형식과 검증 후에만 기억에 넣는 순서**다.

### 2.2 Zetta (2위) — 세 시간 척도, 실행 중 LLM은 "제안이 올라올 때만"
- [원문 §2.1.1] 고정 요소 둘: Action Policy(고정 VLA)와 Orchestrator Agent("fixed multimodal reasoning operator … auditing real-time evidence and approving mode transitions").
- [원문 §2.1.2] 진화 대상 Harness = Runtime Critic("high-frequency monitoring functions" → 제안 = (증거, 제안 모드)) + Recovery Playbook(실패 메커니즘 → 전략) + 도구 모음.
- [원문 §2.1.3] "although [the critic] operates at a high frequency, an intervention is only permitted if the evidence is validated and accepted by [the Orchestrator]." 모드는 VLA 또는 특화 도구. 판정 입력에 마일스톤·성공 기준·환경 제약.
- [원문 §2.5.1] **재진입 계약**: 복구 후 VLA에 제어를 돌려주는 조건 = 실패 증거가 해소됨 AND 접촉이 안정됨(토크 진동·파지력 임계값).
- [원문 §2.3, §2.5.2] First Missing Milestone(처음으로 관측되지 않은 마일스톤)으로 실패 단계를 찾는다. 패치는 진단 재생 + 새 폐루프 롤아웃 두 단계로 검증.
- [원문, v3/08 인용] 에이전트는 오프라인 Reflection & Evolve 단계에서만 부르고, 온라인은 "pure VLA policy under lightweight runtime critics".
- 시간 척도: critic = 고주기(숫자 없음), Orchestrator = 제안 사건마다, Evolutionary Agents = 롤아웃 묶음마다(오프라인).
- [해석] **"코드 critic이 빠르게 돌고, 모델은 제안 승인만"** 구조가 Jev 자리와 가장 잘 맞는다. 원문의 Orchestrator는 느린 추론 모델이고, Jev로 바꾸는 것은 우리 접목안이다(v3/08 정정 유지).

### 2.3 Harness VLA / RPent (3위) — 프리미티브 단위 턴제, 로봇은 계획기를 기다린다
- [원문 §2.1] 턴마다 계획기가 관측(RGB, 깊이, 고유감각) + 과제 + 두 기억을 읽고 JSON 프리미티브 호출 하나를 낸다. 프리미티브는 "until the primitive's internal post-condition is met" 실행 후 새 관측을 돌려준다.
- [원문 부록 A] "synchronous file-mediated REPL": command.json에 쓰고, 워커가 실행하고, "The planner waits for these files before selecting the next primitive." → **실행 중 로봇이 계획기를 기다리는 동기식**이다.
- [원문 §2.3] 고정 어휘(move_to, move_pose, rotate_wrist, rotate_pitch, set_gripper, release, vla_act, 이동형 2개). "the planner cannot invent new primitives at deployment time." vla_act 인자 = prompt, max_chunks, **stop 술어**(조기 반환).
- [원문 §3.3 Key Finding 2] 스테이징(분석 프리미티브로 접촉 전 자세) → vla_act → 접촉 결과 관찰 → 계속 또는 재스테이징 후 재시도. "repeated VLA calls are not continuous control; they are sparse, planner-selected attempts."
- [원문 §2.2] 기억: 성공 호출 순서를 좌표 대신 "symbolic perception queries"로 바꾼 JSONL(작업별), 성공 규칙·실패 모델(전역, 예: 빈 집기, 거짓 성공).
- [원문 §5] 한계: "an open feedback loop between the high-level planner and low-level VLA."
- [해석] 가져올 것: **스킬 호출에 stop 술어를 인자로 붙이는 인터페이스**, 스테이징-시도-관찰-재시도 단위, 좌표를 술어 질의로 바꾼 기억 흔적.

### 2.4 CaP-X (4위, ICML 2026) — 턴 = 프로그램 한 편
- [원문 §2] "a code environment 'turn' corresponds to one interaction …: the agent receives observations, generates a Python program, and the environment executes it to completion." 프로그램 안에서 인식·제어 프리미티브 여러 개, 각각이 여러 내부 갱신.
- [원문 §3.2] 턴 피드백: stdout/stderr(M1), 원시 RGB(M2), VDM(M3: 첫 턴 장면 설명, 이후 "differences between the previous and current image observations and whether the coding agent has completed the task").
- [원문 §3.3] RGB를 매 턴 끼우면 텍스트만보다 나빴고, VDM 텍스트가 M1·M2보다 좋았다(그림 5, 모델 전반).
- [원문 §4] CaP-Agent0 = VDM + 성공 롤아웃에서 뽑은 9개 스킬 라이브러리 + 병렬 추론(턴마다 9개 후보 합성).
- [해석] 결합 세밀도는 중간(턴 단위). 가져올 것은 **VDM식 "변화 텍스트"**(M1)와 **성공 실행에서 스킬을 뽑는 방식**(M10). "코드 안 jev_choice()"는 원문이 아니라 v2의 우리 제안이다.

### 2.5 ROSClaw (5위, 저장소 연결 추정) — 도구 호출 단위, 호출 전 검증
- [원문 §III-A] 스텝마다 에이전트가 관측 → 도구 호출 제안 → 검증기가 허용/차단(+근거) → 차단되면 "return to force replanning". 모든 결정은 append-only 감사 기록.
- [원문 §III-D] "LLM inference (1–3 s) dominates latency." 과제는 6–15턴.
- [원문 §III-G] 텍스트 전용 모델용 "bridged grounding": VLM이 프레임을 "canonical fixed-schema JSON scene description"으로 바꾼다.
- [해석] 결합은 거칠다(부르고 끝 + 사전 검증). 가져올 것은 **거부가 구조화된 사유로 돌아와 재선택을 부르는 형식** 하나. 5위 자리는 여전히 [결정 필요](v3/06).

### 2.6 Show-Harness (6위, 엄격 기준이면 5위) — 의미 행동 단위마다
- [원문 §3.1] 스텝마다: 관측 + 짧은 이력 → 추론 플러그인이 문맥 정제 → VLM이 의미 행동 단위 하나 선택 → 결정론 interpreter가 제어로 바꿈 → 새 관측.
- [원문 §3.2] 단위: MV_FWD/BACK/LEFT/RIGHT/UP/DOWN, ROTATE_CW/CCW(축), GRASP, RELEASE, DONE. interpreter가 작업공간·스텝당 한계를 강제하고 위반은 실행 전 차단.
- [원문 §3.3] Subtask Planning: 처음에 VLM이 완료 기준이 있는 하위 작업 목록을 만들고, "at every step it checks the completion criterion against the current images." Situated Planning: 불확실한 분기는 증거가 보일 때까지 미룬다. Action Chunking: 목표가 멀면 짧은 단위 열을 개루프 실행. Action History: 최근 행동으로 진동 방지. Failure Recovery: 빈 집기 감지 → 그리퍼 리셋 → 잡기 하위 작업으로 되돌림.
- [원문 §5.4.3] 청킹 항상 켬 74%, 끔 96%(호출 증가), 선택적 청킹이 기본. 적응 스텝 96%, 평균 30스텝.
- [해석] 원문에 비동기 실행 서술이 없어 **스텝 사이 로봇이 모델을 기다리는 구조로 보인다**(확인 못 함). 가장 촘촘하지만 스킬이 아니라 증분 이동이다.

## 3. 비교 표

| 논문 | 상위 모델 위치 | 모델 호출 단위 / 시간 척도 | 스킬 인터페이스 | 상태 → 모델 | 피드백 | 실행 중 정지? | Jev가 앉을 자리 [해석] |
|---|---|---|---|---|---|---|---|
| PhyAgentOS | 세션 컴파일러 + 종료 후 검증기 | 세션마다(정책 모드) / 도구 호출마다(내장 모드) | 세션 계약(수용 기준 포함), 런타임·타깃 선택 | ENVIRONMENT.md(개체·속성·관계) | 증거 묶음 → success/failure/replan | 정책 모드는 비정지 | 검증기 3지선다, preflight yes/no |
| Zetta | 고정 Orchestrator(제안 승인만) + 오프라인 진화 에이전트 | critic 고주기(숫자 없음) / 승인은 사건마다 / 진화는 오프라인 | 모드 전환(VLA ↔ 도구), 재진입 계약 | 증거(충돌, 정체), 마일스톤 | critic 제안 | 비정지(승인 대기 방식은 원문 불명) | **critic 제안 수락/거부, 모드 선택** |
| Harness VLA | 턴마다 프리미티브 1개 선택 | 프리미티브 종료마다, 동기식 | 고정 어휘 JSON + stop 술어 + post-condition | RGB-D + 고유감각 + 두 기억 | 새 관측 | **정지(동기)** | 다음 프리미티브, 재스테이징 여부 |
| CaP-X | 턴마다 프로그램 생성 | 프로그램 한 편마다 | 인식·제어 API(고/저수준), 자동 합성 스킬 9개 | 코드 print + VDM 변화 텍스트 | stdout/stderr, VDM | 턴 사이 정지 | (v2 제안) 코드 안 분기점 |
| ROSClaw | 스텝마다 도구 호출 | 1–3 s 추론, 6–15턴 | ROS 2 도구 8개 | 고정 스키마 JSON(텍스트 모델용) | 허용/차단 + 사유 | 도구 단위 | 차단 후 재선택 |
| Show-Harness | 스텝마다 의미 단위 | 단위(또는 짧은 청크)마다, 평균 30스텝 | 증분 단위 + 결정론 interpreter | 다중 시점 이미지 + 고유감각 텍스트 + 이력 | 단위마다 새 관측 | 스텝 사이 대기로 보임 | 행동 단위 Choice(M3와 거의 같음) |

요약 [해석]
- 여섯 편 모두 **상위 모델이 결정할 때 로봇이 기다리거나(Harness VLA, CaP-X, Show-Harness, ROSClaw), 모델이 실행 루프 밖에 있다(PhyAgentOS 정책 모드, Zetta 온라인)**. 비정지 로봇에서 빠른 typed 모델이 제어 루프 가까이 도는 구조는 여섯 편 중 없다 → M4의 빈칸과 같다.
- 가장 잘게 엮은 두 방식은 다르다: Show-Harness는 "모델이 매 스텝 결정", Zetta는 "코드가 매 주기 감시, 모델은 사건 때만". 우리에게는 둘을 합친 형태(스킬 안 결정 지점은 매 단계 Jev, 이탈 감지는 코드 critic)가 맞아 보인다.

## 4. Harvest 파이프라인 대략안 [제안, 한 쪽]

```
 ── 계획 시점 (로봇 정지 허용) ────────────────────────────────────────────
 [Astra, 수 초~수십 초]  M2 · M8          ← 기억 규칙 M10
   입력: 다중 프레임 + M1 장면 텍스트 + 검증된 교훈
   출력: "세션 계약" (PhyAgentOS §3.3)
     - 단계 원장: 단계별 마일스톤 완료 술어 + 예상 시간     (Zetta 마일스톤, M7)
     - 단계별 스킬 바인딩 + stop 술어                       (Harness VLA vla_act)
     - 결정 지점 목록: typed 질문 + 보기 (Jev용)            (M6 · M3)
     - critic 규칙(코드 술어) + 복구 playbook 항목          (Zetta §2.1.2)
          │ 계약 파일(텍스트)
 ── 실행 (비정지) ─────────────────────────────────────────────────────────
 카메라 10–30 Hz → 인식 앞단 → 코드 기하 → 술어·범주 텍스트 M1
                   (PhyAgentOS ENVIRONMENT, CaP-X VDM 변화 텍스트)
          │
          ▼
 [Jev, 약 3 Hz 계단식 겹침]  M4 · M3 · M6
   질문 = 지금 단계의 결정 지점만:
     · 다음 스킬/재스테이징?            (Harness VLA)
     · 의미 행동 단위·스텝 크기          (Show-Harness, 스킬 밖 이동 구간만)
     · critic 제안 수락/거부            (Zetta의 Orchestrator 자리, 우리 접목)
   → 선택 큐(bounded) → 겹침 합의·실제 반영 확인 후 확정 (M4)
          │
          ▼
 [스킬 / 제어기, 100 Hz+]  기존 스킬 + M5 스무딩
   스킬은 stop 술어·post-condition으로 종료, 결과 술어 반환 (Harness VLA)
   접촉 구간은 스킬에 맡김 (Show-Harness 오류 분포)
          │                            ▲
          ▼                            │ 모드 전환 · 재진입 조건 (Zetta §2.5.1)
 [코드 critic, 제어 주기]  M7        ──┘
   마일스톤 술어, 진행 정체 규칙, 마감 초과 → 제안(증거, 모드)
          │ 실패 제안
          ▼
 [복구 사다리]  M9
   스킬 재시도·재스테이징 → Jev 재선택 → 리셋 스킬 → Astra 재계획
   Astra에는 증거 묶음(시작·마지막 정상·키프레임·현재 + 이력) (PhyAgentOS §4.2, M8)
 ── 에피소드 후 ───────────────────────────────────────────────────────────
 [검증 게이트 → 기억]  M10
   센서 술어로 검증된 것만 KNOWLEDGE/LESSONS → Astra가 typed 규칙으로 컴파일
   (PhyAgentOS §4.3 순서, Zetta 검증 게이트, Harness VLA 전역 기억)
```

시간 척도 정리 [제안]: Astra = 초 단위, 계획 시점과 복구 때만 / Jev = 약 3 Hz, 겹쳐서 / 코드 critic·인식 술어 = 카메라 주기 / 스킬·제어기 = 100 Hz 이상. Jev 지연 실측 전이라 "3 Hz"는 사용자 예시값이다 [사용자].

## 5. 열린 질문
1. Zetta의 Orchestrator는 제안이 올 때 로봇을 멈추고 기다리는가? 원문에서 확인 못 했다. Jev 수락/거부가 제어 주기에 맞출 만큼 빠른지는 한국 지연 측정이 먼저다.
2. Show-Harness식 증분 단위를 스킬 밖(이동 구간)에서만 쓸지, 아예 쓰지 않고 스킬 인자(목표 술어)만 Jev가 고를지. 결정 수 대 정밀도 실험 변수.
3. 결정 지점 목록을 Astra가 매번 만들지, 스킬마다 미리 코드로 박아 둘지(M6 컨트리뷰션 4의 핵심).
4. critic 규칙을 Astra가 계획 때 만드는 것은 Zetta(오프라인 진화 + 검증 게이트)와 다르다. 검증 없이 쓰는 critic의 오경보를 어떻게 막을지.
5. PhyAgentOS식 "replan이면 자식 세션" 기록과 M9 체크포인트 복귀를 합칠지.
6. ROSClaw 대 Show-Harness 5위 문제는 그대로 [결정 필요].

## 6. 확인 못 한 것
- Zetta critic 주기와 Orchestrator 모델(참고문헌 72–74로만 표시), Show-Harness 스텝당 시간, Show-Harness의 동기/비동기 여부.
- ROSClaw bridged grounding의 프레임당 초(HTML에서 숫자 빠짐).
- 스타 수 재측정(API 금지).
