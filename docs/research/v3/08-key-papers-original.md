# 08. plan v3가 새로 기대는 논문 17편: 원문 대조 검증

작성: 2026-09-24, 조사 에이전트. 대상: `docs/plan.md` v3(2026-09-23 20:10 UTC).

## 1. 조사 방법과 한계
- arXiv `abs`(제목·저자·제출 이력·comments) 17편 + `html` 본문 17편 전부를 받아 방법 절과 주요 표·본문 문장을 grep으로 확인했다. 요청 간격은 2초 이상.
- 학회는 arXiv comments, 본문 머리말, OpenReview 검색(`api2.openreview.net/notes/search`, 9회)으로 확인했다.
- Harness VLA의 Astra 사용은 GitHub API가 아니라 `raw.githubusercontent.com/RLinf/RPent/main/README.md`(저장소 README 원문)와 프로젝트 페이지로 확인했다.
- **WebSearch는 쓰지 않았다(0회).** arXiv 검색 API, Semantic Scholar API, GitHub API도 쓰지 않았다.
- 한계
  - HTML 변환에서 수식 안 숫자와 `nicematrix` 표가 빠졌다. Show-Harness 표 2와 Harness VLA 표 3의 셀 값은 읽지 못했다. 초록과 본문 문장에 나온 숫자만 인용한다.
  - plan에 적힌 스타 수와 인용 수(451★, 962★, 인용 23, 2,481★, Evo-Memory 인용 130 등)는 **다시 재지 않았다**(API 금지).

## 2. 검증 표

표기: 맞음 / 정정 필요(원문: ...). 확인 수준은 README 규칙을 따른다. 모든 항목의 출처는 `https://arxiv.org/abs/<id>`와 `https://arxiv.org/html/<id>`이다.

### 2.1 Show-Harness (2609.10522) — M3에 가장 가까운 선행 연구
- **서지**
  - 제목: *Show-Harness: Just a VLM Agent Can Play Robots*
  - 첫 공개: 2026-09-09
  - 저자: Yanzhe Chen 외, 교신 Mike Zheng Shou(NUS Show Lab)
  - 학회: comments에 표시 없음. OpenReview에도 없다.
- **방법(3줄)**
  1. VLM에 이산 의미 행동 단위(MV_UP/DOWN/FWD…, GRASP 등)를 보기로 준다.
  2. 로봇별 interpreter가 이 단위를 로컬 행동으로 결정적으로 바꾼다(스텝당 이동량은 보정한 값).
  3. 단위마다 고유감각을 텍스트 피드백으로 돌려준다. 행동 청킹, 적응 스텝, 실패 복구 같은 플러그인이 붙는다.
- **핵심 수치와 조건**
  - 실물 Franka, 10개 작업(물체 5 × 용기 2), 작업당 10회, 최대 50스텝.
  - 기본 VLM은 Gemini-3.1 Pro, thinking effort medium.
  - 플러그인 절제
    - 적응 스텝: 96% 성공, 평균 30스텝
    - 청킹을 끄면: 96% 유지, 호출 수는 늘어남
    - 청킹을 항상 켜면: 74%
    - 복구를 빼면: 72%
    - 계획을 빼면: 60%
    - 손잡이 인식 파지: 40 → 85%
    - 숨은 물체 찾기: 35 → 85%
  - 유효한 행동 단위를 낸 응답은 98% 이상.
- **plan 문장 대조**
  - "스텝마다 VLM이 이산 행동 단위 선택, 단위마다 피드백": **맞음.** 원문은 "returns execution feedback after every unit"이다. 단 행동 청킹이 켜져 있어 목표가 멀면(손목 카메라에 목표가 안 보이면) 여러 단위를 한 번에 계획하고 개루프로 실행한다. **"매 스텝 호출"은 아니다.**
  - "적응 스텝 크기(멀면 크게, 가까우면 작게)": **정정 필요.** 원문: "a 2 cm fine step when the target is visible in the wrist view and a 4 cm coarse step otherwise." 거리가 아니라 손목 카메라에 목표가 보이는지로 2cm/4cm를 전환한다. 정밀 작업(쌓기·삽입)에서는 1cm로 줄였다.
  - "사고량을 늘려도 성공률은 그대로이고 시간만 늘었다": **정정 필요.** 원문: "increasing thinking effort mainly reduces redundant interaction steps with little gain in success and can incur higher wall-clock cost (e.g., for GPT-5.6-sol)." 성공률 이득은 작았고 **스텝 수는 줄었다.** 벽시계 비용 증가는 "그럴 수 있다"는 표현이고, 예로 든 것은 GPT-5.6-sol 하나다.
  - "오류는 세밀한 잡기·놓기에 몰렸다": **맞음.** 원문: "planning is also not the main bottleneck; errors concentrate on fine-grained grasping and placement." 목표 bounding box를 주면 더 좋아졌다.
- **가져올 것**
  - 의미 단위 + 결정적 interpreter
  - "목표가 보이면 fine" 같은 조건부 스텝 크기
  - 상호작용 근처에서만 촘촘히 묻는 선택적 청킹
  - 행동 이력 5개(진동 방지)
  - 빈 집기 감지 후 재시도
- **학습 여부**: ZS 모드는 학습 없음. FT 모드는 Qwen3.5-2B LoRA.
- **신뢰도: MED.** NUS Show Lab, 심사 전. 스타 수는 다시 재지 않았다.

### 2.2 Zetta (2608.16590)
- **서지**
  - 제목: *Zetta ζ: An Efficient Closed-Loop Embodied Harness for Self-Evolving Physical Intelligence*
  - 첫 공개: 2026-08-17
  - 소속: 칭화대 AIR 외(교신 Ting Cao)
  - 학회: 표시 없음
- **방법(3줄)**
  1. 동작 주기로 도는 코드 critic이 증거와 제안 모드를 내면, 고정된 Orchestrator Agent(멀티모달 추론 모델)가 그 제안을 승인할 때만 개입한다.
  2. 롤아웃 묶음의 실패를 군집화하고 medoid 시드로 원인을 진단한 뒤 critic과 복구 후보를 만든다.
  3. 검증 게이트("improve success rate and generalize across rollouts")를 통과한 후보만 스킬 메모리에 넣는다. 게이트는 진단 재생과 새 폐루프 롤아웃, 두 단계다.
- **핵심 수치와 조건**
  - LIBERO-Pro 34.5 → 90.8%(held-out 시드 1~20), RoboCasa(18작업) 73.6 → 93.6%(held-out 50시드). 모두 "under our current rollout budget"이다.
  - 11.1배 속도 향상은 RPent(Harness VLA) 대비 지연 감소(−91%)다. 인프라(Z-Infra, 모듈별 양자화) 효과가 섞여 있다.
- **plan 문장 대조**
  - "촘촘(코드 critic + 수락/거부 결정자)": **맞음.**
  - "Astra가 critic 코드를 만들고 Jev가 매 주기 수락/거부": **정정 필요.** 이것은 Zetta가 아니라 우리 접목안이다. 원문에서 critic 코드는 오프라인 Evolutionary Agent가 만든다. 매 주기 도는 것은 코드 critic뿐이다. Orchestrator는 critic이 제안을 올렸을 때만 판정한다. 원문: "reduces agent overhead by invoking agents only during offline Reflection & Evolve phases, while online rollouts execute pure VLA policy under lightweight runtime critics." 매 주기 LLM 수락/거부는 Zetta에 없다.
  - "Role1" 같은 역할 이름은 원문에 없다(grep 0건).
  - 스킬 갱신 게이트: **맞음.** 검증 게이트 이름은 "Validation-Gated Skill Update Loop"이다.
- **학습 여부**: 기반 VLA 가중치는 고정이다. 하네스 코드는 작업별 개발 시드 롤아웃으로 진화한다. 학습은 없지만 롤아웃 비용이 크다.
- **신뢰도: MED.** 칭화 AIR, 심사 전. **주의: MemCompiler와 같은 연구진이다**(Xin Ding, Liang Mi, Kun Li, Hao Wu, Yunxin Liu, Ting Cao). 두 논문을 독립된 근거로 세지 않는다.

### 2.3 Harness VLA / RPent (2607.08448)
- **서지**
  - 첫 공개: 2026-07-09(v4는 2026-09-02)
  - 소속: 칭화대, Striding AI, Purdue, HKUST 외
  - 학회: 표시 없음
- **방법(3줄)**
  1. 고정 VLA를 재시도 가능한 접촉 프리미티브 `vla_act`로 노출하고, 작은 고정 분석 프리미티브(접지·스테이징·운반·이동·놓기)와 조합한다.
  2. 작업별 기억(성공 프리미티브 조합 흔적)과 전역 기억(성공 규칙·실패 모델) 두 가지를 둔다.
  3. 원문: "Rather than adding more skills, the harness teaches the planner the operating range of each fixed primitive."
- **핵심 수치와 조건**
  - 가장 강한 기준 방법 대비 LIBERO-Pro +38.6%p(RATS 대비), RoboCasa365 +25.4%p. RoboTwin C2R 58.4%.
  - 계획기는 Codex, Claude Code.
  - **프로토콜**: 작업마다 seed 0에서 탐색해 작업별 기억을 만들고, seed 1~10에서 평가한다(few-shot 부트스트랩).
  - 작업별 기억을 끈 zero-shot 결과는 LIBERO-Pro Goal에서만 따로 보고했다(표 5).
- **plan 문장 대조**
  - "프리미티브 작동 범위를 기억으로", "스킬을 늘리지 않는다": **맞음.**
  - "9/17부터 Astra 계획기": **부분 확인.** RPent README 원문에는 "Codex / GPT-6 Astra / low / reasoning: 92.63% Overall (741/800) across all eight LIBERO-PRO suites"라고 적혀 있다. **Astra를 effort low로 썼다.** "9/17"이라는 날짜는 README 뉴스 목록에 없어 확인하지 못했다. 논문 본문에는 Astra가 없다.
- **학습 여부**: VLA 미세조정 없음. 단 작업별 탐색 시드가 필요하다.
- **신뢰도: MED.** 스타와 인용이 plan 수치대로면 HIGH 조건(유명 연구실 + 반응)에 해당하지만, 이번에 다시 재지 않았다.

### 2.4 PhyAgentOS (2607.16636)
- **서지**
  - 첫 공개: 2026-07-18
  - 소속: 중산대 HCP Lab(Liang Lin), X-Era Lab, Peng Cheng Lab
  - 학회: 표시 없음
- **방법**
  - 세션을 스케줄링·검증의 최소 단위로 삼는다.
  - 인지와 물리 사이 경계를 파일시스템(Markdown + YAML, "State-as-a-File")으로 둔다.
  - SessionVerifier가 성공 / 실패 / 재계획 판정을 내리고, 검증된 결과를 기억으로 통합한다.
- **수치**
  - LIBERO: 정책 4종에서 +0.4~+1.3점
  - CALVIN 전체 체인 성공: 예) X-VLA 74.3 → 75.7, 다른 백엔드 38.9 → 45.6, 85.3 → 89.4
  - 모두 검증기가 재시도를 촉발한 경우("Final")다. 저자도 이득이 "modest"하다고 썼다.
- **plan 문장 대조**
  - "거침(세션 단위)": **맞음.**
  - "학회 미확인": **맞음.**
- **학습 여부**: 학습 없음("without retraining").
- **신뢰도: MED.** 이득이 작아 결합 세밀도 참고로만 쓴다.

### 2.5 CheckVLA (2607.26789)
- **서지**
  - 첫 공개: 2026-07-29
  - 소속: 칭화대, 상해교대, 북경대, NTU, Xspark AI
  - 학회: 표시 없음
- **방법(3줄)**
  1. 따로 학습해 고정한 행동 조건 월드 모델(V-JEPA 2-AC 특징 공간)이 실행 중인 chunk의 결과를 예측한다.
  2. 학습된 risk head가 예측과 관측의 차이를 모으고, functional conformal 임계값(에피소드 FWER)을 넘으면 개입한다.
  3. 같은 VLA가 hard prefix 제약 아래 남은 suffix를 다시 쓴다. 재작성 뒤에는 일정 스텝 동안 트리거를 억제한다(suppression).
- **수치**
  - RoboCasa365 평균 36.1% 대 호출 수를 맞춘 주기 재계획 27.6%(**+8.5%p**). 호출 수는 10.2회 대 10.1회/에피소드.
  - 이 중 **검증 시점만의 기여가 +3.9%p**(고정 guidance 절제).
  - 오경보 5%에서 적시 재현율: 77.9% 대 관측만 48.6%, 행동 섞기 37.9%.
- **plan 문장 대조**
  - "호출 수를 맞춘 비교(CheckVLA 관행)": **맞음.**
  - "주기 간격은 검증 세트로 선택": **맞음.** 원문: "Validation selects the periodic interval."
  - v3/05의 "트리거 교체만으로 +3.9%p": **맞음.** 단 전체 차이는 +8.5%p이고, +3.9는 그 가운데 "verified timing"에 돌린 몫이다. 두 숫자를 함께 적는다.
- **학습 여부**: 전부 학습형이다(월드 모델, risk head, VLA 재학습). 가져올 수 있는 것은 평가 설계(호출 수 맞춤, FWER 고정 재현율)와 재작성 뒤 트리거 억제 규칙뿐이다.
- **신뢰도: MED.**

### 2.6 BRACE (2608.01428)
- **서지**
  - 제목: *When Replanning Becomes the Bottleneck: Budgeted Replanning for Embodied Agents*
  - 첫 공개: 2026-08-02
  - 소속: HKUST(광저우)
  - **ICML 2026 채택**(arXiv comments)
- **방법(3줄)**
  1. 트리거(주기 / 실패 / 위험)는 컨트롤러의 입력일 뿐이다. 컨트롤러는 먼저 안정성 게이트(cooldown: 직전 호출 뒤 최소 간격, commit: 새 계획의 최소 실행 길이)를 적용한다.
  2. 통과하면 재계획 모드(켤 모듈과 프롬프트 템플릿), 토큰 예산, 지연 SLO를 고른다. 실패가 이어지면 게이트를 풀고 예산을 늘린다.
  3. 선택 모듈 E-RECAP은 **학습된** 토큰 중요도 예측기로 트랜스포머 층 안에서 문맥을 가지친다.
- **수치**
  - 성공률이 이미 포화된 설정에서 재계획 토큰 −62~92%, SLO 위반 85.5~100% → 4.7~50.0%.
  - 어려운 RoboFactory 설정: 80.0% 성공, SLO 위반 4.6%.
  - 계획기는 7~14B 오픈 모델(Qwen2/2.5, LLaMA-3)이다.
- **plan 문장 대조**
  - "트리거 → 문지기(부를지, effort, 입력 토큰 예산) → 호출", "cooldown/commit 창으로 재계획 진동 억제": **대체로 맞음. 한 곳 정정.** BRACE의 문지기 출력은 (부를지, **모드**, 토큰 예산, 지연 SLO)다. **"effort"는 BRACE에 없다.** effort 선택은 우리가 모드 자리에 넣는 확장이다. 진동 억제는 원문의 "anti-churn property"에 해당한다.
- **학습 여부**: 컨트롤러와 게이트는 규칙이다. E-RECAP은 학습형이고 모델 내부 층에 접근해야 하므로 API(Astra)에는 쓸 수 없다.
- **신뢰도: HIGH.** ICML 2026.

### 2.7 Learning When to Plan (2509.03581)
- **서지**
  - 첫 공개: 2025-09-03(v3 2026-02-17)
  - 소속: UCL, Oxford, NYU, Princeton, Warsaw(Rocktäschel, Foerster 외)
  - **OpenReview: "Submitted to ICLR 2026"**(채택 표시 없음 = 채택 안 됨으로 판단)
- **방법**
  - 먼저 zero-shot으로 계획 빈도를 바꿔 본다(Llama-3.3-70B, Crafter/POGS, 각 100시드).
  - 그다음 SFT(70B 교사 궤적 1,024개) + PPO로 Llama-3.1-8B가 계획 시점을 스스로 고르게 학습한다.
- **수치와 결과**
  - 성공률은 계획 빈도의 중간값("Goldilocks")에서 가장 높았고, 항상 계획과 전혀 계획 안 함은 모두 더 나빴다(Gemini 2.5 Flash, TextWorld에서도 같은 경향).
  - 학습한 8B가 70B zero-shot을 이겼다(0.387 대 0.379, 토큰 85% 적게).
- **plan 문장 대조**
  - "항상 계획하면 더 나쁘다": **맞음.** 조건은 텍스트 게임, Llama-3.3-70B zero-shot이다.
  - "'필요할 때만 계획하라' 프롬프트가 작동하지 않았다": **맞음. 단 약하게 써야 한다.** 원문은 정량 실험이 아니라 "Our initial attempts … proved challenging and unreliable. Models struggled to consistently interpret abstract instructions such as 'plan only when necessary', often defaulting to fixed patterns"라는 서술이다. 그래서 zero-shot 비교에서 동적 계획 기준 방법을 뺐다. Llama-3.3-70B 기준이고, Astra 같은 추론 모델에서는 확인되지 않았다.
- **학습 여부**: 핵심 방법은 SFT + RL이다. zero-shot 빈도 분석만 학습이 없다.
- **신뢰도: MED.** 유명 연구실이지만 ICLR 2026에서 채택되지 않았다. plan은 학회를 적지 않아 충돌은 없다.

### 2.8 Evo-Memory (2511.20857)
- **서지**
  - 첫 공개: 2025-11-25
  - 소속: UIUC(1저자) + Google DeepMind 다수(Ed H. Chi, Fernando Pereira 외)
  - 학회: 표시 없음. OpenReview에는 CoRR로만 있다.
- **방법**
  - 과제를 흐름(stream)으로 순서대로 푸는 벤치마크다.
  - ExpRAG: (입력, 출력, 피드백) 경험 텍스트를 top-k로 검색해 붙인다.
  - ReMem: Think / Act / Refine-Memory 루프로 기억을 스스로 정리한다.
- **수치(표 1b, Claude 3.7 Sonnet, AlfWorld, S = 성공률)**
  - Baseline 0.18, History 0.50, ReAct 0.51, AWM 0.49, **ExpRAG 0.74, ReMem 0.92**
  - P(진행률)는 AWM 0.73 / ExpRAG 0.89 / ReMem 0.96
  - ReMem은 AlfWorld 평균 스텝을 22.6 → 11.5로 줄였다.
- **plan 문장 대조**
  - "ALFWorld Claude 3.7에서 AWM 0.49 / ExpRAG 0.74 / ReMem 0.92": **맞음**(성공률 S 열). 같은 표에서 ReAct 0.51이 AWM보다 높다는 점도 함께 적을 만하다.
  - "Google DeepMind": **맞음.** 단 1저자는 UIUC다.
  - "인용 130"은 다시 재지 않았다.
- **학습 여부**: 학습 없음.
- **주의**: ReMem은 Think·Refine 스텝을 더 쓴다. 예산을 맞춘 비교가 아니므로 2606.15017의 비판이 그대로 적용된다(v3/03과 같은 결론).
- **신뢰도: MED.** 인용 130이 확인되면 HIGH.

### 2.9 MemCompiler (2605.07594)
- **서지**
  - 첫 공개: 2026-05-08
  - 소속: USTC, HUST, **Microsoft Research**, 난징대, **칭화 AIR**
  - 학회: 표시 없음(OpenReview에 CoRR로만)
- **방법**
  - 학습된 Memory Compiler가 매 스텝 Brief State를 읽고, 관련 기억만 골라 지침으로 컴파일한다.
  - 지침은 텍스트 채널과 **Executor 임베딩에 직접 넣는 잠재 Soft-Mem 채널**, 두 가지로 전달된다.
  - 컴파일러는 SFT 후 GRPO로 학습한다.
- **plan 문장 대조**
  - "통째 주입이 작은 실행기를 18~62% 떨어뜨림": **정정 필요(조건 누락).** 이 범위는 부록 표 6(**진행률**, **Qwen-2.5-VL-32B**, **EB-ALFRED**)에서 AMMI 기준 방법들의 값이다.
    - 표 6 값: Mem0 −18.8, Langmem −21.4, MemGen −46.6, G-Mem −53.1, A-Mem −61.8
    - **같은 행 EB-Habitat에서는 Mem0 +7.8%, Langmem +6.4%로 올랐다.**
    - 본문 요약: "AMMI baselines yield negative gains in **over half** of all (executor, dataset) pairs, with extreme drops such as A-Mem at **−83.3%** on Qwen-2.5-VL-32B / EB-ALFRED."
    - 고친 문장 제안: "오픈소스 실행기(Qwen 4종) × 벤치마크 4종 조합의 절반 넘게에서 통째 주입이 무메모리보다 나빴다(최대 −83.3%)."
  - "MSR·칭화 AIR, MED": **맞음.**
- **학습 여부**: **학습형이다(SFT + GRPO).** 잠재 채널은 실행기 임베딩에 접근해야 하므로 Jev(API)에는 불가능하다. 우리가 가져올 수 있는 것은 "상태 조건 선택 + 텍스트 컴파일" 개념과 "통째 주입은 해롭다"는 증거뿐이다.
- **신뢰도: MED.** Zetta와 같은 연구진이다(2.2 참고).

### 2.10 ExpWeaver (2605.07164)
- **서지**
  - 제목: *Rethinking Experience Utilization in Self-Evolving Language Model Agents*
  - 첫 공개: 2026-05-08
  - 소속: 하얼빈공대(Bing Qin, Ting Liu = HIT-SCIR)
  - 학회: 표시 없음
- **방법**
  - 경험 구성은 그대로 두고, 경험을 "선택적 자원"으로 노출한다. **에이전트 자신이** 추론 중에 필요할 때 불러온다.
  - 비교 대상: 처음 한 번 주입(Init-only), 매 스텝 주입(Always-on).
  - 4개 프레임워크, 7개 백본, 3종 환경(ALFWorld, WebShop, QA)에서 실험했다.
- **결과**
  - 거의 모든 설정에서 ExpWeaver가 Init-only와 Always-on보다 좋았다.
  - RL(Qwen3-4B, GRPO)에서는 Always-on이 Init-only보다 낮았다(과다 노출은 간섭).
  - 엔트로피 분석: 경험 호출은 토큰 엔트로피가 높은 시점에 몰렸다(상관 분석).
- **plan 문장 대조**
  - "Jev 확률 차이가 작을 때만 힌트를 붙여 다시 묻기(ExpWeaver 개념, MED-LOW)": **대체로 맞음. 표현 정정.** ExpWeaver는 외부 불확실성 게이트가 아니라 모델이 스스로 부른다. "불확실할 때 부른다"는 사후 상관 분석 결과다. 우리 안(외부 확률 게이트)은 ExpWeaver의 **변형**이라고 적는다.
- **학습 여부**: 프롬프트판은 학습이 없다. RL은 선택 사항이다.
- **신뢰도: MED.** HIT-SCIR은 알려진 NLP 연구실이지만 심사 전이다. plan의 MED-LOW도 허용 범위다.

### 2.11 Speculative Actions (2510.04371)
- **서지**
  - 첫 공개: 2025-10-05
  - 소속: Columbia
  - **OpenReview: ICLR 2026 Oral**(제목이 "…for Faster AI Agents"로 조금 다름)
  - arXiv HTML 본문 머리에는 "NeurIPS 2025 Workshop on ML for Systems"라고 적혀 있다(초기판).
- **방법**
  - 빠른 모델(Speculator)이 다음 행동을 추측해 병렬로 미리 실행한다.
  - 느린 Actor의 결과와 일치하면 확정하고, 다르면 버리고 원래대로 진행한다(lossless).
  - 안전장치: semantic guard, 되돌릴 수 있는 부작용만 허용, rollback 또는 보상 행동으로 수리.
- **수치**: 다음 행동 예측 정확도 최대 55%, 지연 최대 20% 감소(체스, 전자상거래, 웹 검색). 둘 다 **"최대" 값**이다.
- **plan 문장 대조**
  - "ICLR 2026, 추측 → 검증 → 확정/수리 틀": **맞음.**
- **학습 여부**: 학습 없음.
- **신뢰도: HIGH.**

### 2.12 LocalAgreement / Whisper-Streaming (2307.14743)
- **서지**
  - 첫 공개: 2023-07-27
  - 소속: Charles Univ. 외
  - IJCNLP-AACL 2023 시스템 데모
  - **기간 밖, 기초 문헌.** LocalAgreement 자체는 Liu et al. 2020에서 나왔다.
- **방법**: 연속한 n개 업데이트 출력의 가장 긴 공통 접두사만 확정한다. n = 2를 썼다(IWSLT 2022에서 가장 효과적이었던 값).
- **수치**: 영어 평균 지연 3.3초(MinChunkSize 1초). 원문: "the average computationally unaware latency is approximately **twice the chunk size**."
- **plan 문장 대조**
  - "연속 호출이 일치하는 앞부분만 확정": **맞음.**
  - "확정 지연 약 2배": **맞음.** 정확한 기준은 "chunk 크기의 약 2배(n = 2일 때)"다. n을 올리면 더 늘어난다.
- **학습 여부**: 학습 없음.
- **신뢰도: HIGH.** ACL 계열, 기초 문헌.

### 2.13 Spec-VLA (2507.22424)
- **서지**
  - 첫 공개: 2025-07-30
  - 소속: 마카오대, 칭화대
  - **EMNLP 2025 main**
- **방법**
  - OpenVLA에 EAGLE식 draft 모델(학습형)을 붙인다.
  - 검증할 때 draft 토큰과 검증 토큰의 bin 거리가 임계값 이하면 수락한다(완화 수용).
- **수치**: 수락 길이 +44%, OpenVLA 대비 1.42배 속도, 성공률 유지(LIBERO 4종).
- **plan 문장 대조**
  - "순서형 보기는 ±1단계면 일치로(Spec-VLA, 완화 수용)": **정정 필요.**
    - 원문의 완화 임계값은 **256 bin 중 9**(Goal/Object/Spatial)와 **5**(Long)다.
    - Goal은 15까지 성공률이 안정적이었고, Long은 5를 넘으면 성공률이 크게 떨어졌다.
    - 원문: "the better a model performs in a scenario, the larger the relaxation threshold it can tolerate."
    - 따라서 ±1은 Spec-VLA 값이 아니라 우리 설정이다. 허용 폭은 **구간 수 대비 비율로 정하고 작업 난도에 따라 바꿔야 한다**는 것이 원문의 교훈이다.
- **학습 여부**: draft 모델은 학습형이다. 완화 수용 규칙 자체는 학습이 없다.
- **신뢰도: HIGH.**

### 2.14 KITE (2604.07034)
- **서지**
  - 첫 공개: 2026-04-08
  - 소속: 애들레이드대 AIML
  - **ICRA 2026**(arXiv comments, OpenReview 둘 다)
- **방법**
  - 조밀 광류 크기의 봉우리로 키프레임을 고른다. 부족하면 균일 프레임으로 채운다.
  - 검출 결과를 붙인 pseudo-BEV와 로봇·장면 토큰을 한 프롬프트로 만들어, 학습 없이 VLM에 넣는다.
- **수치(표 III, 실세계, Qwen2.5-VL, 실패 감지 FD)**: 전체 0.84, BEV 제거 0.81, **균일 키프레임 0.69**.
- **plan 문장 대조**
  - "균일 선택으로 바꾸면 실패 감지 0.84 → 0.69": **맞음.** 조건은 실세계 과제, Qwen2.5-VL, RoboFAC다.
  - v3/05의 주의(GPT-4o 단독이 실세계 FD 0.96)도 유지한다.
- **학습 여부**: 학습 없음(QLoRA판은 선택 사항).
- **신뢰도: HIGH.**

### 2.15 VLA-0 (2510.13054)
- **서지**
  - 첫 공개: 2025-10-15
  - 소속: NVIDIA(Ankit Goyal, Fabio Ramos 외)
  - 학회: 표시 없음
- **방법**: VLM이 행동을 정수 텍스트로 출력한다([0, 1000] 정규화). 학습 때 masked action augmentation, 추론 때 ACT식 앙상블을 쓴다.
- **수치**
  - LIBERO에서 해상도 1000이 94.7이다. 원문: "Decreasing the resolution to 250 … reducing the success rate by 1.5 points, while 4000 yields no additional" 이득.
  - 앙상블을 빼면 −2점, 마스킹을 빼면 −1.2점.
- **plan 문장 대조**
  - "해상도 250 대 1000 차이 1.5점(미세조정 모델)": **맞음.** 조건은 LIBERO 하나, 미세조정한 VLM이다.
- **학습 여부**: 미세조정 모델이다. 해상도에 대한 근거로만 쓴다.
- **신뢰도: MED~HIGH.** NVIDIA, 심사 전. plan의 인용 53과 스타 492는 다시 재지 않았다.

### 2.16 2503.03064 (Wang, Zhang, Choi)
- **서지**
  - 제목: *Improving LLM-as-a-Judge Inference with the Judgment Distribution*
  - 첫 공개: **2025-03-04 → 기간 밖**(기준일 03-23보다 19일 이르다)
  - 소속: UT Austin, NYU
  - **EMNLP 2025 Findings**
- **방법과 수치**
  - 판정 토큰 분포의 평균과 최빈값(greedy)을 비교했다.
  - 원문: "The mean outperforms the mode in 42 out of 48 cases"(RewardBench, MT-Bench; pointwise, pairwise, listwise).
  - CoT는 분포를 뾰족하게 만들어 자주 성능을 해쳤다. 평균을 쓸 때 no-CoT가 16개 중 14개에서 더 좋았다.
- **plan 문장 대조**
  - "분포 평균이 최빈값보다 나았다(48조건 중 42, 기간 밖)": **맞음.** 학회(EMNLP 2025 Findings, HIGH)를 plan에 함께 적자고 제안한다.
- **학습 여부**: 학습 없음.
- **신뢰도: HIGH.**

### 2.17 2510.05381 (Du 외)
- **서지**
  - 제목: *Context Length Alone Hurts LLM Performance Despite Perfect Retrieval*
  - 첫 공개: 2025-10-06
  - 소속: UIUC, Amazon 외
  - **EMNLP 2025 Findings**
- **방법과 수치**
  - LLM 5개, 수학·QA·코드 과제.
  - 관련 증거를 완벽히 찾아도 입력이 길어지면 13.9~85% 하락했다(길이 최대 약 30k 토큰, 모델 공칭 길이 이내).
  - 무관 토큰을 공백으로 바꾸거나 마스킹해도 하락했다.
  - 완화책(증거를 먼저 읊게 하기): GPT-4o RULER에서 최대 +4%.
- **plan 문장 대조**
  - "입력 길이만으로 13.9~85% 하락": **맞음.**
  - 조건 추가 제안: "수천~3만 토큰 범위"다. Jev 입력은 훨씬 짧을 가능성이 커서, 효과 크기는 우리 길이에서 직접 측정해야 한다.
- **학습 여부**: 분석 논문이다. 완화책은 학습이 없다.
- **신뢰도: HIGH.**

## 3. 새로 찾은 것과 모듈별 접목 (요약)
- **M8 effort**
  - Harness VLA 공식 리더보드의 Astra 결과는 **effort low**로 LIBERO-PRO 92.63%(741/800)다.
  - Show-Harness는 effort를 올리면 스텝 수가 줄고 성공률 이득은 작았다.
  - 두 결과 모두 "effort는 실험 축" 결정을 지지한다. 동시에 제3자는 이미 low로 높은 수치를 냈다는 점을 기준 방법 설정에 반영해야 한다.
- **M4 완화 수용**: Spec-VLA는 허용 폭(256 bin 중 5~9)이 작업 난도에 따라 달라야 한다고 보였다. 우리 ±1(255 보기)은 훨씬 엄격하다. 허용 폭을 실험 변수로 둔다. [제안]
- **M8 cooldown**: BRACE(cooldown / commit)와 CheckVLA(재작성 뒤 트리거 억제)가 같은 규칙을 쓴다. 둘 다 근거로 인용할 수 있다.
- **M10**: MemCompiler와 Zetta가 같은 연구진이다. "Astra 컴파일 규칙만 Jev에" 발상의 근거가 MemCompiler 하나에 몰려 있고, 그 논문의 컴파일러는 학습형이다. → "학습 없는 LLM 컴파일러"는 우리 쪽 가정이고, 원문의 근거는 "통째 주입은 해롭다"는 부분뿐이다.

## 4. 반대 증거와 위험
- Zetta의 "매 주기 LLM 없음" 설계와 RPent 지연 비판(에피소드당 392~513초, "LLM API calls at every decision point")은 **촘촘한 API 호출 자체가 느리다**는 반대 증거다. Jev(빠른 모델)가 이 비판을 피하는지는 한국 지연 측정으로 보여야 한다.
- Learning When to Plan의 "프롬프트 실패"는 정량 결과가 아니다. 강한 근거로 쓰면 안 된다.
- Evo-Memory의 ReMem 우위는 예산을 맞추지 않은 비교다.

## 5. plan.md 반영 제안 [제안]
1. §1 effort 반대 증거에서 Show-Harness 문장을 "성공률 이득은 작고 스텝 수는 줄며, 벽시계 비용은 늘 수 있다(GPT-5.6-sol)"로 고친다.
2. §1 선점 표와 §2 M6에 "Harness VLA의 Astra판은 effort low, LIBERO-PRO 92.63%(README)"를 적고, "9/17" 날짜는 미확인으로 둔다.
3. M3와 M5의 Show-Harness 적응 스텝: "손목 카메라에 목표가 보이면 2cm, 아니면 4cm(정밀 작업은 1cm)".
4. M4(a): "±1단계"를 우리 설정으로 명시한다. Spec-VLA 원값은 256 bin 중 5~9이고 난도에 따라 다르다.
5. M4 위험: LocalAgreement 지연은 "chunk 크기의 약 2배(n = 2)".
6. M6: Zetta 설명을 "코드 critic이 동작 주기로 돌고, 고정 Orchestrator가 critic 제안을 승인할 때만 개입한다. critic 코드는 오프라인 에이전트가 만들고 검증 게이트로 채택한다"로 고친다. "Astra 생성 + Jev 매 주기 수락"은 우리 접목안으로 표시한다.
7. M8: BRACE 문지기의 출력은 "모드 / 토큰 예산 / 지연 SLO"다. effort는 우리 확장으로 표시한다. BRACE는 ICML 2026(HIGH).
8. M8: CheckVLA는 "전체 +8.5%p, 그중 검증 시점 기여 +3.9%p(호출 10.1 대 10.2회)"로 적는다.
9. M10: MemCompiler 수치를 "Qwen 실행기 × 벤치마크 조합의 절반 넘게에서 통째 주입이 무메모리보다 나쁨(최대 −83.3%). −18~−62%는 표 6 EB-ALFRED 진행률(Qwen2.5-VL-32B) 한 행이고 EB-Habitat에서는 +6~8%"로 고친다. 컴파일러가 학습형(SFT + GRPO)임을 적고, Zetta와 같은 연구진임을 적는다.
10. M10: ExpWeaver는 "모델이 스스로 부르는 방식이다. 외부 확률 게이트는 우리 변형"으로 적는다.
11. M3: 2503.03064에 "EMNLP 2025 Findings"를 덧붙인다.
12. Learning When to Plan: "ICLR 2026 제출, 채택 안 됨, MED". "프롬프트 실패"는 정성 서술이라고 적는다.

## 6. 확인 못 한 것
- 스타와 인용 수 전부(Show-Harness 451, Harness VLA 962 / 23, PhyAgentOS 2,481, Zetta 1,252, Evo-Memory 130, VLA-0 53 / 492, 2510.05381 163). API 금지로 다시 재지 않았다.
- Show-Harness 표 2와 Harness VLA 표 3의 셀별 수치(HTML 변환에서 빠짐).
- Zetta Orchestrator Agent가 쓴 구체적 모델(참고문헌 72~74번으로만 표시).
- Harness VLA에 Astra가 들어간 날짜(9/17).
- Evo-Memory와 VLA-0의 학회 채택 여부(OpenReview에서는 CoRR로만 나옴).
