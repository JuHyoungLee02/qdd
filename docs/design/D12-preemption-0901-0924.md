# D12 선점 재검사 (2026-09-01~09-24 게시분)

작성: 2026-09-24 01:41 UTC(처음 01:50으로 잘못 적음 — 짐작 시각). 조사 에이전트 보고 전문을 메인 세션이 저장(줄이지 않음). 메인 원문 재확인(abs·HTML curl): JEV-Star 2609.27331(23 Sep 2026) 인용 5개 일치 / Type-Safe Is Not Error-Free 2609.26758(22 Sep 2026) 70.4·.94→.23·.8146·type-error 0%·neutral option identifiers 일치 / World-Coherent Decoding 2609.02159(2 Sep 2026) "realized observation audits" 일치. 나머지 [초록만] 표시 항목은 메인이 재확인하지 않았다.


## 결론
- **C1(M4 확정 규칙)을 강하게 선점하는 논문은 없었다.** 시간차로 겹쳐 부른 블랙박스 typed 호출 사이의 합의, 실행 뒤 코드 예상 상태 대 측정 상태 비교, 전제 epoch 무효화, keep/replace/repair 선택을 한 규칙으로 묶은 선행은 이번 창에서도 찾지 못했다. 부분 겹침은 4편 있다(아래 표).
- **C2(같은 인식 앞단 위에서 결정 층만 바꾸고 standard→random 낙폭을 짝지어 재는 평가)의 선점도 없었다.** GTA-2, 2609.05985, RoboFind가 π0.5나 Astra 단독과 비교하지만, 모두 같은 인식 비교가 아니고 짝지은 낙폭도 재지 않는다.
- **Astra/Jev 계층 자체는 강한 선행이 새로 나왔다.** JEV-Star(2609.27331, 09-23)가 "빠른 JEV 선택 + GPT-6 Astra 비동기 계획"을 StarCraft II에서 먼저 했다. 로봇이 아니고 실패 시 호출도 아니지만, 이 구조를 새로움으로 주장하면 안 된다. 이 구조는 원래 SUMMARY §0의 기여 목록에 없으므로 기여 두 개는 그대로 선다. 다만 인용은 반드시 해야 한다.
- **반대 증거 2편이 중요하다.** Type-Safe Is Not Error-Free(2609.26758)는 typed 모델의 체계적 편향을 보였다. 이 편향은 반복 호출끼리 합의해도 잡히지 않는다. PACT(2609.01662)는 "같은 관측에 대한 반복 추론의 합의는 증거가 아니다"라고 말한다. 둘 다 M4 (a)가 (b) 없이 서면 안 된다는 근거라서, 우리 서술에는 오히려 도움이 된다.

## 방법과 색인 범위
- **cs.RO 9월 월간 목록:** 1,378편 제목 전수(cs.RO로 교차 게시된 것 포함). 여기서 키워드로 약 230편을 거른 뒤 약 40편은 초록을 읽었다.
- **arXiv API 검색:** 검색어 약 76개, 모두 `submittedDate:[202609010000 TO 202609242359]` 조건, 호출 간격 2.5~3.5초. 전 분야에서 고유 결과 약 280편이 나왔다.
- **정독:** abs 페이지로 날짜를 확인한 것 20편, HTML 본문을 키워드로 정독한 것 14편.
- **색인 한계:** 2609.277xx(9/23 제출, 9/24 게시)까지 들어 있다. 9/24 제출분은 아직 없다. D7(9/22 17:59 UTC까지)보다 약 하루 반이 늘었다.

## 후보별 판정
날짜는 모두 abs 페이지의 "Submitted on"으로 확인했다.

### 계층 (Astra/Jev)
**2609.27331 JEV-Star: Fast, Low-Cost StarCraft II Control with Language-Model Planning (09-23)** — 계층 겹침 **강함**, C1·C2 없음.
- 원문: "combining fast JEV action selection with persistent GPT-6 planning".
- 본문 §3.3: "Full-game control is asynchronous: the game continues while requests are in flight. JEV requests are rate-limited to at most one per wall-clock second. The planner is checked on a nominal 60-game-second interval and at relevant events".
- 본문 §3.2: "A failed or delayed planning request leaves the previous valid plan available."
- 사용 모델은 "JEV 1.13, GPT-6 Astra with medium reasoning effort"이고, JEV는 "selects among structured alternatives"로 동작한다.
- 우리와 다른 점:
  - 게임 영역이고, 로봇·인식 앞단이 없다.
  - 계획기를 실패 때 부르지 않고 주기 호출과 사건 호출을 쓴다.
  - JEV 요청은 초당 1개로 제한돼 겹침 호출이 없다.
  - 호출 사이 합의나 예상 대 측정 비교가 없다.
  - 저자도 "planning's contribution is not isolated by a controlled ablation"이라고 적었다.
- **해야 할 일:**
  - 반드시 인용한다.
  - "빠른 typed 선택 + 느린 Astra 비동기 계획"을 새로움으로 쓰지 않는다.
  - 우리 차이는 "로봇 실행 중 **실패 판정이 불러내는** Astra 호출, 겹침 호출 합의 + 실행 뒤 확인(M4)"으로 좁혀 쓴다.
  - 부수 후보 M8(호출 방식 × effort)은 JEV-Star의 주기+사건 호출을 비교 조건 하나로 명시하면 좋다.

**2609.26532 REFLEX with Jev for Efficient Selective Control in LLM Agents (09-22)** — 계층 **부분**.
- 원문: "uses Jev as a fast, typed decision layer and calls a strong LLM when confidence is low, or generation is required".
- 본문에서 확인한 것: robot 언급 0회, 비동기 없음. 도구 사용 에이전트다.
- 강한 모델 호출 조건이 실패가 아니라 낮은 확신이다.
- 한계를 직접 적었다: "reliability depends on action-set size and near-valid alternatives near authorization boundaries".
- **해야 할 일:** 인용한다. M8에 확신 기반으로 올려 보내는 조건(escalation)을 비교 기준선 후보로 넣을지 [결정 필요]로 올린다.

**2609.18451 VLM-MPPI (09-16)** — 계층·비정지 **부분**.
- 원문: "A pretrained vision–language model (VLM) asynchronously selects the candidate index ... while MPPI replans at 20 Hz".
- 본문: "the parallel MPPI planner ensures flight safety during these asynchronous updates". 사용 모델은 Gemini 2.5 Flash.
- 차이: 드론이고, 객관식 한 번 호출이며, 합의·실행 뒤 확인·실패 트리거가 없다.
- **해야 할 일:** "비동기 VLM이 후보 번호를 고르는 동안 빠른 계층은 멈추지 않는다"의 선례로 인용한다.

**2609.26084 VLMs as copilots for Autonomous UAV Navigation (제출 08-10, 게시는 9월 말)** [초록만] — 계층 **부분(약함)**.
- 원문: "deterministic Finite State Machine ... with an asynchronous VLM copilot".
- **해야 할 일:** 관련 연구에서 한 줄 언급하면 된다.

그 밖에 한 줄씩 언급할 만한 것:
- **2609.26550 JEV-as-a-Judge [초록만]:** "accepts confident verdicts and escalates uncertain ones".
- **2609.23986 Jev-Mem [초록만]:** System-One/Two 분업.
- **2609.22753 [초록만]:** Jev로 엣지 서비스 조율, 지연 15.9~26.5% 감소.

### C1 (M4 확정 규칙)
**2609.02159 World-Coherent Decoding (09-02)** — C1 **부분**. 이번 창에서 가장 가깝다.
- 원문: "samples multiple candidates from a frozen WAM ... After execution, the realized observation audits the selected imagination, yielding an imagination–reality mismatch that trains a lightweight online predictor for future candidate selection".
- 본문 확인: consensus·agree·invalid·replan 모두 0회.
- 차이:
  - 같은 시각에 학습 WAM에서 뽑은 샘플이다(시간차 블랙박스 typed 호출이 아니다).
  - 샘플 사이 합의가 아니라 내부 신호로 순위를 매긴다.
  - 예상 대 실제 불일치는 다음 선택을 위한 예측기 **학습 신호**로만 쓴다. 전제 무효화나 keep/replace/repair 판정에는 쓰지 않는다.
- **해야 할 일:** A3와 함께 인용한다. 차별화 문장에 "실행 뒤 예측-실제 불일치를 **다음 후보 선택 학습**에 쓰는 WCD와 달리, 우리는 그것을 합의 원장의 **전제 무효화·확정 판정**에 쓴다"를 추가한다.

**2609.03236 Speculative Macro Commit for Faster Tool-Using Agents (09-03)** — C1 (a) **부분**. 비로봇이다.
- 원문: "a faster speculative drafter model continuously predicts and executes future action chains ... When the actor's next tool call matches the first drafted action, SMC commits the remaining pre-executed draft steps".
- 본문: robot·embodied 0회.
- 두 모델의 일치로 확정한다는 점은 겹친다. 그러나 격리된 스냅샷 위의 추측 실행이고, 물리 측정 확인이나 전제 무효화가 없다.
- **해야 할 일:** "합의로 확정"의 비로봇 선례로 A3 옆에 인용한다.

**2609.27612 RegenHarness (09-23)** — epoch 무효화 **부분(약함)**.
- 본문: "identity- and version-bound commit gate", 판정은 "satisfied, violated, ambiguous, stale, or unsafe"이고 "stale means it is no longer valid for the decision".
- 본문: "A transition residual is a discrepancy between an expected and observed effect".
- 차이: 과제 진행 상태를 확정하는 게이트다. 결정 표의 합의나 비정지 겹침 호출은 없다. 사족 로봇 사례 보고 수준이다.
- **해야 할 일:** 전제 epoch 설명에서 "버전에 묶인 증거와 낡은(stale) 판정의 선례"로 인용한다.

**2609.01281 EmbodiedSkills (09-01)** — C1 (b) **부분(약함)**.
- 원문: "treats each skill decision as an execution proposal: the runtime checks its prerequisites before execution and verifies the outcome afterward".
- 본문: asynchronous·agree·expected 모두 0회.
- **해야 할 일:** "실행 뒤 확인 자체"의 선례 목록(Show-Harness, RoboDawn)에 추가한다.

같은 범주, LOW, [초록만] 3편:
- **2609.21908 CommitFlow (09-18):** "holds back dependent actions when a required condition is unmet". 이 유보는 학습 정책 π0.5 위에서 한다.
- **2609.19315 GAVEL (09-16):** "predict the consequences of LLM-generated actions before execution, detect violations, and repair".
- **2609.16368 UDAV (09-14):** "draws multiple stochastic trajectory predictions, selects their medoid as a self-consistent nominal route". 같은 시각 샘플이다.

typed 인터페이스 쪽, [초록만]:
- **2609.15142 C²Nav (09-14):** 부분. 원문 "the VLM compares controller-constructed alternatives, while geometry, thresholds, action magnitude, and execution remain on the physical side". 같은 VLM에서 비교형 질문을 절댓값형으로 바꾸면 SR이 12~28%로 떨어진다. M3/M6 typed 질문 설계의 근거로 인용하면 된다.

### C2 (평가)
C2를 선점하는 논문은 없다.

**2609.09808 GTA-2 (09-09)** [초록만] — C2 약하게 부분. 다중 VLM 무학습 스킬을 π0.5, CaP와 실로봇 14과제에서 비교해 73.9%. 같은 인식 비교도 아니고 환경 변화 낙폭도 없다.

**2609.05985 Brain-inspired Hierarchical Framework (09-05)** [초록만] — "higher success rates than ReKep, Dream2Flow, and π0.5". 배치 조건은 flat/irregular 두 가지다. 같은 앞단 비교가 아니다.

**2609.20330 RoboFind (09-17)** [초록만] — "10/12 trials, against 5/12 for ... GPT-6 Astra-only". 다중 에이전트 검증이 Astra 단독보다 낫다는 결과라서, 계층과 검증의 가치를 보여 주는 지지 증거다.

**2609.26292 RoboTwin-Phys (09-22)** [초록만] — 지지 증거. "models that remain effective under existing visual and layout randomization can degrade markedly under changes in physical conditions". 반대로 읽으면 우리 random 조건(시각 요소)만으로는 부족할 수 있다는 뜻도 된다.

**2609.13606 From Vision to Harvest (09-11)** — 참고. 제목만 같은 영역이고 C2와는 겹치지 않는다. VLM 계획 파이프라인을 전통적 인식-계획 파이프라인과 비교하지만, 과수원 이미지로 계획만 평가한다.

### 반대 증거와 설계 입력
**2609.26758 Type-Safe Is Not Error-Free (09-22)** — 중요.
- 원문: "renaming the two options from 0/1 to no/yes changes 70.4 more answers per hundred ... shifts AUC from .94 to .23".
- 원문: "The hosted model exhibits the same behavior: the swap changes AUC from .8146 to .5806 and produces 24x as many answer flips as its test-retest floor".
- 원문: "the type-error rate remains 0%".
- 본문의 권고: "Use neutral option identifiers and carry the meaning in the rubric".
- 우리에게 주는 뜻 세 가지:
  1. 옵션 이름에서 오는 체계적 오류는 반복 호출끼리 합의해도 걸러지지 않는다. (a)만으로는 부족하고 (b)가 필요하다는 근거이므로 M4 서술에 인용한다.
  2. hosted 모델이 결정적이지 않다(test-retest floor가 있다). W2/E0.5에서 flip이 0이 아닐 근거다.
  3. M3/M6 옵션 이름을 중립 식별자로 바꾸는 규칙을 [결정 필요]로 올리고, E0.5에 옵션 이름 치환 대조를 추가한다.

**2609.01662 PACT (08-31 제출, 09-16 v2)** — 창 밖이지만 방금 수정됐다. 원문: "Repeated inference over one observation can improve predictions without adding an evidential origin."
- A3식 같은 관측 반복 샘플 합의를 반박하는 논거로 쓸 수 있다. 우리 쪽은 시간차 관측과 실행 뒤 측정이므로 "증거 출처가 늘어나는 합의"라고 차별화할 수 있다. 인용을 권장한다.

**2609.03221 (09-02)** [초록만] — 참고. 같은 조건을 10회 반복했을 때 행동이 8.7% 바뀌었고, 5회 다수결이 그 흔들림의 39%만 없앤다. LLM 반복 호출의 흔들림 수치로 E0.5 해석에 참고하면 된다.

## 집계
- 훑은 양: cs.RO 제목 1,378편, API 검색어 약 76개(고유 결과 약 280편), 초록 약 75편, abs 날짜 확인 20편, 본문 정독 14편.
- **강한 겹침: 1편.** JEV-Star 2609.27331, 계층 한정. C1·C2와는 겹치지 않는다.
- **부분 겹침:**
  - C1: 2609.02159 WCD, 2609.03236 SMC, 2609.27612 RegenHarness, 2609.01281 EmbodiedSkills. 약하게 CommitFlow, GAVEL, UDAV.
  - typed 인터페이스: 2609.15142 C²Nav.
  - 계층: 2609.26532 REFLEX, 2609.18451 VLM-MPPI, 2609.26084.
  - C2: GTA-2, 2609.05985 (둘 다 약함).
- **반대 증거:** 2609.26758 Type-Safe, 2609.01662 PACT, 2609.03221.

## 권고 변경 (SUMMARY §0 / 정본)
1. **계층 문구:** "빠른 typed 모델 + 느린 Astra 비동기 계획" 자체는 새롭지 않다(JEV-Star). 차이는 "로봇 실행, 실패 판정이 불러내는 Astra 호출, 겹침 호출 합의 + 실행 뒤 확인"으로만 적는다. M8 비교 조건에 JEV-Star식 주기+사건 호출과 REFLEX식 확신 기반 올려 보내기를 넣을지 [결정 필요]로 올린다.
2. **M4 차별화 문장:** A3 옆에 WCD(실행 뒤 불일치를 선택 학습에 씀)와 SMC(두 모델 일치로 확정, 비로봇)를 추가 인용한다. "(b)가 합의 원장의 전제 무효화·확정 판정에 쓰인다"는 차별점은 그대로 유지할 수 있다. 전제 epoch 설명에는 RegenHarness의 stale/version-bound를 인용한다.
3. **반대 증거를 동기로 쓴다:** Type-Safe와 PACT를 "(a) 반복 합의만으로는 체계적 오류를 못 거른다 → (b)가 필요하다"의 근거로 쓴다.
4. **설계:** Jev 옵션을 중립 식별자로 바꾸는 규칙을 [결정 필요]로 올린다. E0.5에 옵션 이름 치환 대조와 test-retest floor 측정을 추가한다.
5. **C2 문구:** 현재의 "같은 인식·같은 실행기 위에서 결정 층만 바꾼 짝지은 낙폭 연구는 없다"는 9/23 제출분까지 유지된다. 색인 날짜를 "2026-09-23 제출분"으로 갱신한다. RoboTwin-Phys는 "시각 랜덤화만으로는 부족할 수 있다"는 한계 문장과 함께 인용한다.
6. **Jev 비교 기준선:** this-that-model-1.0(2609.23886, 09-20, 2B 오픈 typed 결정 모델)이 있다. 제3자 문항 68개에서 0.941로, 같은 문항의 hosted Jev 0.765보다 높았다고 주장한다. Jev 대체·로컬 기준선 후보로 [결정 필요]에 올린다. [초록만]

작업 파일은 스크래치패드 `C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER\1a853580-8a79-4164-a03a-eeb77b9f612f\scratchpad\`(titles.tsv, seen.json, out2~4.txt, html\)에 있다. D:\qdd는 수정하지 않았다.
