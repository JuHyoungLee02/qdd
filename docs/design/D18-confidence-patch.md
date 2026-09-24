# D18 신뢰도 측정·보장 방법과 patch 재계획 조사 (user-log 31)

저장 2026-09-24 05:03 UTC. 조사 에이전트 보고 전문(신뢰도 기준 user-log 14 적용). 메인 원문 재확인(abs): CoFineLLM "prediction sets that contain the correct action", JRA "false discovery rate", 2512.02304 "across model families", SWE-Edit "12.5", Plan-and-Act ICML, 2505.14489 "33 out of the 36"·NeurIPS, Trust-or-Escalate "80% human agreement", RoboMonkey "25% absolute" — 일치. **학회 표기 미확인(abs에 없음)**: JRA COLM 2026, Trust-or-Escalate ICLR 2025, RoboMonkey CoRL 2025 → 인용 시 "학회 미확인" 또는 다른 출처로 확인 필요.


D:\qdd는 읽기만 했고, 내려받은 자료는 D:\tools\audit_d18\에만 두었습니다.
- 폴더 구성: `abs/`(arXiv abs 원본 51편), `hf/`(HF 추천 수 페이지), `gh/`(GitHub 페이지), `html/`(arXiv 본문 HTML 24편)
- 요약 파일: `abs_summary.txt`, `hf_summary.txt`, `abstracts.txt`

## 0. 결론 먼저

1. **"같은 모델 3번 병렬 다수결"은 2025~2026 문헌에서 기준선(baseline)입니다.**
   - 핵심 방법으로 쓰는 강한 논문은 없었습니다. 최신 흐름은 세 갈래입니다.
     - (가) 확신 가중 투표 또는 저확신 경로 걸러내기. logprob가 필요합니다(CISC, DeepConf).
     - (나) 별도 검증기로 고르기(RoboMonkey, ThinkPRM, 교차 계열 검증).
     - (다) 보정 집합으로 문턱을 맞춘 conformal 집합·기권·에스컬레이션. 커버리지나 위험 상한을 보장합니다.
   - 사용자 직감("오리지널 예전 방식")은 문헌과 맞습니다.
   - 다만 투표가 사라진 것은 아닙니다. RoboMonkey(CoRL 2025)는 그리퍼 열림·닫힘을 샘플 최빈값으로 정하는 부품으로 씁니다.
2. **통계적 보장이 붙는 방법은 모두 점수(확률·logprob·내부 특징)와 보정 집합이 필요합니다.**
   - 그래서 **Jev에는 맞고**(보기 확률, E1 뒤), **Astra에는 거의 안 맞습니다**(logprob 없음, 느림).
   - Astra에 쓸 수 있는 최신 방식은 두 가지입니다.
     - 실행 기반 외부 검사 + 다른 계열 검증기
     - 검사 실패 때만 순차로 수리 재호출
   - 둘 다 보장은 없지만, 외부 신호가 자기 검증보다 낫다는 근거가 있습니다.
3. **patch 재계획은 로봇·에이전트 계획에서는 표준이 아닙니다.**
   - 강한 논문들은 매 호출 다음 하위 목표나 남은 계획 전체를 다시 생성합니다. 이전 계획은 입력으로만 넣습니다(Plan-and-Act ICML 2025, π0.5, DeepMind Hi-VLA 연구).
   - 코드 편집 에이전트에서는 diff(찾아 바꾸기)가 지배적입니다. 최신판은 "작은 변경은 diff, 큰 변경은 전체 재작성"으로 **적응형으로 고릅니다**.
   - 권고: A4를 "patch 전용"이 아니라 **`patch | replace` 적응형 기본**으로 고치고, E-M2에서 전체 재생성과 비교합니다.

## 1. 조사 방법과 한계

- **검증한 것**
  - arXiv abs 페이지에서 v1 날짜·Comments·journal-ref를 직접 읽었습니다.
  - HF 추천 수는 페이지의 `upvotes` 필드로 확인했습니다. 크기 52,953 B 응답은 "페이지 없음"으로 봤습니다.
  - GitHub 스타는 저장소 HTML의 star counter에서 오늘 읽었습니다.
  - 소속은 arXiv HTML의 affiliation 필드에서 읽었습니다.
- **로봇 논문은 HF 추천 수가 전반적으로 낮습니다**(π0.5도 5). 그래서 로봇 쪽은 학회·소속·스타의 무게를 더 두었습니다.
- **인용 수**: 이번에는 조회하지 못했습니다(미확인).
- **인용문 출처 표시**
  - (abs): abs 원문에서 그대로 옮긴 것입니다.
  - (요약): WebFetch 요약 도구를 거친 것이라 본문 반영 전 원문 대조가 필요합니다.

## 2. Part 1: 출력이 완벽하지 않을 때 신뢰도를 재고 보장하는 방법

표기: 적합 = Astra / Jev에 맞는지. 등급 = HIGH / MED / LOW.

### 2.1 Conformal 집합·기권·에스컬레이션 (보장 있음)

**CoFineLLM, 2511.06575** [MED]
- 서지: v1 2025-11-09, WashU(Kantaros), 학회 표기 없음, HF 페이지 없음
- 방법: 보기별 LLM 확신 점수 → 계획 단계별 예측 집합을 만듭니다. 원소가 하나면 실행하고, 아니면 도움을 요청합니다.
- 보장: 계획 전체 커버리지
  - (abs) "wrapping LLM outputs into prediction sets that contain the correct action with a user-defined confidence. When the prediction set is a singleton, the planner executes that action; otherwise, it requests help"
  - 계획 전체 보장은 단계별 집합의 곱으로 만듭니다. (요약) "P(τ_test ∈ 𝒞̄) ≥ 1−α … 𝒞̄=𝒞(1)×⋯×𝒞(H_test)"
- 필요한 것: 보기 확률 + 보정 시나리오 400개(요약)
- 약점: (abs) "they tend to produce unnecessarily large sets, particularly at higher confidence levels, resulting in frequent human interventions"
- 적합: **Jev ○**(보기 확률), Astra ✕

**KnowNo, 2307.01928** [HIGH, 기간 밖 기초 문헌]
- 서지: CoRL 2023 Oral, HF 10
- 위 방법의 원조입니다. 객관식 계획을 conformal 집합으로 다룹니다.

**Introspective Planning, 2402.06529** [HIGH, 기간 밖 기초 문헌]
- 서지: NeurIPS 2024

**ConformalNL2LTL, 2504.21022** [MED]
- 서지: v1 2025-04-22, 학회 없음
- 방법: 주 모델이 확신하지 못하면 보조 모델, 그다음 사용자로 넘깁니다. (abs) "when it is insufficiently certain … it requests assistance from the auxiliary model and, if necessary, from the user"
- 적합: 계단식 에스컬레이션 구조 = **Jev → Astra**와 같은 모양입니다.

**Trust or Escalate, 2407.18370** [HIGH, 기간 밖 기초 문헌]
- 서지: ICLR 2025, 30★
- (abs) "use cheaper models as initial judges and escalate to stronger models only when necessary … guarantees over 80% human agreement with almost 80% test coverage"
- 적합: 계단식 구조가 **Jev(싸고 빠름) → Astra(비쌈)**와 같습니다.

**Judge, Retrieve, or Abstain, 2608.17994** [MED-HIGH]
- 서지: v1 2026-08-18, COLM 2026, Dalhousie·NYUAD·Emory
- 방법: 보류 집합으로 문턱을 맞춰 FDR ≤ α를 보장합니다.
  - (abs) "calibrates uncertainty thresholds on a held-out set so that the false discovery rate among accepted verdicts remains below a user-specified level α with high probability, using finite-sample Clopper–Pearson intervals"
  - 두 문턱 라우팅에도 보장이 유지됩니다: (abs) "The finite-sample guarantee carries over to this two-threshold routing"
- 필요한 것: verdict 위치의 토큰 logprob 엔트로피, 보정 1,000개(요약)
- 수치: NQ-Open, Qwen3-8B, α = 0.20에서 커버리지 7% → 82%(요약)
- 적합: **Jev ○**(보기 확률이 곧 verdict 확률), Astra ✕

**API Is Enough, 2403.01216** [MED, 기간 밖 기초 문헌]
- 서지: Findings EMNLP 2024
- 방법: logprob 없이 샘플 빈도로 conformal 집합을 만듭니다.

**2508.05544** [LOW-MED, 보조로만]
- 서지: Jinan, under review
- (abs) "sampling frequency can serve as a viable substitute for logit-based probabilities in black-box scenarios"
- 적합: 이론상 Astra에도 되지만 **입력당 여러 번 샘플해야 합니다**.
- [우리 계산] K = 3이면 일치도는 {1/3, 2/3, 1} 세 값뿐이라 문턱을 세밀하게 잡을 수 없습니다. 효용이 낮습니다.

**FIPER, 2510.09459** [HIGH]
- 서지: NeurIPS 2025, TUM, 55★
- 보장: 성공 롤아웃의 오경보 확률 ≤ δ(요약: "P(∃t … F(𝝉:t)=1)≤δ")
- 필요한 것: 성공 롤아웃 M = 50(시뮬) 또는 10(실물)(요약). 실패 데이터는 필요 없지만 **정책 내부 임베딩이 필요**합니다.

**SAFE, 2506.09937** [HIGH]
- 서지: NeurIPS 2025, U Toronto·Vector, HF 10, 109★
- VLA 내부 특징으로 실패를 예측하고, conformal로 문턱을 정합니다.
  - (abs) "the best trade-off between accuracy and detection time using conformal prediction"
- 적합(FIPER·SAFE 공통): Jev·Astra에는 직접 적용 못 합니다. 대신 **M7 critic 소프트 채널 문턱을 성공 에피소드로 conformal 보정**하는 틀로 가져옵니다([접목]). 오경보 상한은 "정지 최소화" 원칙과 맞습니다.

**PCE, 2602.04326** [MED-HIGH]
- 서지: ICLR 2026, Korea Univ.
- 방법: LLM 추론 흔적 속 가정을 결정 트리로 바꿉니다. (abs) "converts the fragmented assumptions latent in LLM reasoning traces into a structured decision tree. Internal nodes encode environment assumptions and leaves map to actions"
- 보장: 없음
- 적합: **Astra ○**. 우리 계약의 "가정 술어 + `C_assume`"와 같은 방향입니다.

- **공통 주의(기초 사실)**: conformal 보장은 보정·시험의 교환 가능성(exchangeability)을 전제합니다. 판본·모델이 바뀌면 깨집니다. 우리 §28 E1(`question_id@vN` × 모델 ID에 보정값 묶기)과 매일 카나리가 바로 이 조건을 지킵니다.

### 2.2 투표·확신 가중·검증기로 고르기 (보장 없음)

**CISC, 2502.06233** [HIGH, 기간 밖(2025-02-10)]
- 서지: ACL Findings 2025, Google Research
- 방법: 확신 점수로 가중한 다수결입니다. (abs) "CISC outperforms self-consistency in nearly all configurations, reducing the required number of reasoning paths by over 40% on average"
- 필요한 것: 가장 좋은 방법은 P(True)이고 **토큰 확률이 필요**합니다(요약).
- 추가 발견: (abs) "the most calibrated confidence method proved to be the least effective for CISC"
- 적합: Astra ✕

**DeepConf, 2508.15260** [HIGH]
- 서지: Meta, HF 92, 414★
- (abs) "self-consistency with majority voting … often leads to diminishing returns"
- 적합: 내부 확신이 필요해 Astra ✕

**RoboMonkey, 2506.17811** [HIGH]
- 서지: CoRL 2025, Stanford·Berkeley·NVIDIA, HF 1, 스타 미확인
- 방법: 샘플 + 가우시안 섭동 + 다수결로 후보를 만든 뒤 **VLM 검증기가 고릅니다**.
- 수치: (abs) "25% absolute improvement on out-of-distribution tasks and 9% on in-distribution tasks"
- 비용: 16후보에 약 650 ms, H100(요약)
- 다수결의 역할: 그리퍼 최빈값에만 씁니다(요약).

**MG-Select, 2510.05681** [MED-HIGH]
- 서지: ICLR 2026, KAIST·SNU
- 검증기 없이 VLA 토큰 분포의 KL로 고릅니다. 내부 분포가 필요해 해당 없음.

**ThinkPRM, 2504.16828** [HIGH]
- 서지: HF 19, 92★
- 생성형 단계 검증기입니다. (abs) "outperforms LLM-as-a-Judge and discriminative verifiers -- using only 1% of the process labels in PRM800K"

**When Does Verification Pay Off?, 2512.02304** [MED]
- 서지: NYU(Mengye Ren), ICLR 2026 워크숍
- (abs) "verification across model families is more effective than either self-verification or verification within the same family … reasoning post-training weakens self-improvement abilities but strengthens cross-family improvement"
- 적합: **Astra 계획은 다른 계열 모델이나 외부 검사로 검증하는 편이 낫다**는 근거입니다.

- **다수결의 현재 위치**: CISC·DeepConf·RLCR 모두 majority vote를 **비교 기준선**으로 둡니다. RoboMonkey는 부품으로만 씁니다.
  - "다수결이 해가 된다"는 2608.11403은 LOW라 근거로 쓰지 않습니다.

### 2.3 말로 한 확신(verbalized confidence)과 자기 검증

**Reasoning Models Better Express Their Confidence, 2505.14489** [HIGH]
- 서지: NeurIPS 2025, KAIST·LG AI, HF 20, 23★
- (abs) "achieve strictly better confidence calibration than their non-reasoning counterparts in 33 out of the 36 settings"
- 적합: Astra(추론 모델)의 말로 한 확신은 **기록할 가치가 있는 특징**입니다. 다만 보장은 없습니다.

**RLCR, 2507.16806** [MED-HIGH]
- 서지: MIT(Yoon Kim), HF 7
- (abs) "While ordinary RL hurts calibration, RLCR improves it"
- 훈련 기법이라 우리가 쓸 수는 없습니다. RL로 훈련된 API 모델의 말로 한 확신은 보정되어 있다고 가정하면 안 된다는 방향 근거입니다.

**UQ for LLM Agents, 2609.07395** [MED-LOW, 보조로만]
- 서지: TCD, 학회 없음
- (abs) "confidence estimates from the agent's own responses do not consistently outperform a simple baseline … step-level … does not imply [trajectory-level]"

**Self-Verification Limitations, 2402.08115** [기간 밖 기초 문헌, 학회 표기는 abs에서 미확인]
- LLM 자기 검증의 한계를 다룬 기초 문헌입니다.

**UQLM, 2504.19254** [HIGH]
- 서지: TMLR 2025, CVS Health, 1,202★
- 블랙박스(샘플 일치), 화이트박스, LLM-judge 점수를 앙상블하는 실무 도구입니다.
- Astra에 적용하려면 샘플 여러 개 = 호출 여러 번이 필요합니다.

**추세 서베이, 2601.15690** [MED]
- 서지: ACL 2026, Salesforce·Vanderbilt, HF 4
- (abs) "the evolution of uncertainty from a passive diagnostic metric to an active control signal"
- 이것이 2025~26년의 흐름입니다. 우리 M7 게이트·M8 트리거와 같은 방향입니다.

### 2.4 실행 기반 검증과 체화 계획 검증

**Plan Verification for LLM-Based Embodied Agents, 2509.02761** [MED]
- 서지: UIUC(Hakkani-Tür·Tur), 학회 없음
- 방법: Judge LLM이 비평하고 Planner LLM이 고치는 반복 수리입니다.
- 수치: (abs) "up to 90% recall and 100% precision … 96.5% of sequences requiring at most three iterations"
- 조건: TEACh 오프라인 데이터 정제 설정입니다.

**VerifyLLM, 2507.05118** [MED]
- 서지: IROS 2025, MIPT·AIRI
- 방법: 실행 전 LTL로 바꿔 계획의 빠진 전제 조건을 검사합니다.

**Hi-VLA 연구, 2606.10267** [HIGH-소속, 학회 미표기]
- 서지: Google DeepMind(Shah·Xie 외)
- (요약) "success detector consistently achieves good performance" — 성공 감지를 VLM 호출 전환 조건으로 쓴 결과입니다.
- 적합: M7 = 코드 critic으로 두는 현재 설계와 같은 방향입니다.

### 2.5 무엇이 어디에 맞나

| 방법 | 보장 | 필요한 것 | Astra | Jev |
|---|---|---|---|---|
| conformal 집합(KnowNo·CoFineLLM) | 커버리지 ≥ 1−α | 보기 확률 + 보정 집합 | ✕ | **○ (E1 뒤)** |
| 위험 통제 기권·에스컬레이션(JRA·T-or-E) | FDR ≤ α | 확률 + 보정 약 1,000개 | ✕ | **○ → 모르면 Astra로** |
| 빈도 기반 conformal | 커버리지 | 입력당 여러 샘플 | △ (T0만, 비쌈) | 불필요 |
| 확신 가중 투표(CISC·DeepConf) | 없음 | logprob | ✕ | △ |
| 외부 검증기·교차 계열 | 없음 | 두 번째 모델 | **○** | — |
| 실행 기반 검사(전제·효과) | 없음(결정적 검사) | 술어·시뮬 | **○** | ○ |
| 말로 한 확신 | 없음 | 없음 | 기록만 | — |
| 성공 롤아웃 보정 감시기(FIPER식) | 오경보 ≤ δ | 성공 에피소드 | — | M7 문턱 |

## 3. Part 2: patch/diff 재계획은 요즘 표준인가

### 3.1 패치 방식이 아닌 쪽 (강한 논문)

- **Plan-and-Act, 2503.09572** [HIGH, 기간 밖(2025-03-12), 기초 문헌]
  - 서지: ICML 2025, UC Berkeley, 46★
  - 매 스텝 계획을 새로 생성합니다. (요약) "After each iteration, the Planner takes in the current state as well as the previous plans and actions and generates a new plan."
  - 수치: 정적 29.63% → 동적 재계획 53.94%, WebArena-Lite(요약)
- **π0.5, 2504.16054** [HIGH]
  - 서지: Physical Intelligence, openpi 13,975★
  - 매 스텝 하위 과제를 다시 추론합니다. (요약) "during each step of inference, the model first predicts the semantic subtask"
- **Hi-VLA 연구(DeepMind)**
  - 플래너는 "a single command that should be executed immediately"를 냅니다(요약).
  - "in-episode summarization generally has a neutral to negative effect"(요약)
- **BRACE, 2608.01428** [MED-HIGH]
  - 서지: ICML 2026, HKUST-GZ
  - 계획을 고정하면 실패합니다. 비교 설정은 RoboFactory 한 과제(Pass-Shoe)입니다. (abs) "where open-loop, frozen-plan, and No BRACE all fail, BRACE + E-RECAP reaches 80.0% success"
  - 핵심 문제는 재계획 지연의 긴 꼬리(heavy tail)입니다. patch와 전체 재계획을 직접 비교하지는 않았습니다(요약).

### 3.2 패치·재사용 쪽

- **AgenticCache** [HIGH]: MLSys 2026. "plan locality"
- **APC** [HIGH]: NeurIPS 2025. 계획 템플릿 재사용.
- 둘은 재사용·캐시이지 patch 형식 자체의 근거는 아닙니다.
- **Replan, Repair, or Edit?, 2609.19654** [MED-LOW, 보조로만]
  - 서지: UNSW·USyd 외, 여행 계획 도메인
  - 편집 수·보존율: 전체 재계획 LLM-Z3는 편집 6.628·보존 65.35%, 계층 수리 IPyHOPPER는 1.000·92.67%(단일 교란)
  - 성공률: 복합 교란에서 LLM-Z3 93.0 > IPyHOPPER 89.0 > **LLM 국소 편집 iTIMO 67.0**, 그리고 iTIMO는 토큰이 더 많았습니다(요약).
  - 저자 단서: "repair scope is confounded with feedback … budgets"(요약)

### 3.3 코드 편집 에이전트

- **SWE-Edit, 2604.26102** [MED-HIGH]
  - 서지: Microsoft, 14★
  - 찾아 바꾸기가 기본이지만, 적응형 선택이 더 낫습니다: "adaptive find-replace/whole-file-rewrite policy improves edit success by 12.5 pp"(abs)
- **AdaEdit, 2604.27296** [MED-HIGH]
  - 서지: Findings ACL 2026, NJU·Alibaba
  - (abs) "consistently matches the accuracy of full-code generation, while reducing both latency and cost by over 30%"
  - 조건: 긴 코드 편집 과제입니다.
- **Cascaded Code Editing, 2604.19201** [MED-HIGH]: FSE 2026, CUHK·Tencent

### 3.4 판정

- "이전 계획을 입력에 넣고 다시 생성"이 체화·에이전트 계획의 주류입니다.
- **patch 전용은 표준이 아닙니다.**
- patch(diff)가 이기는 조건은 **변경이 국소적일 때**입니다. 이득은 지연·토큰 감소와 약속 보존입니다.
  - 코드 쪽 "task locality"는 2609.05779(LOW)에만 있는 표현이라 방향 참고로만 둡니다.
  - 국소 편집의 성공률 손해는 MED-LOW 한 편(여행 도메인)의 결과입니다.
- 최신판은 **형식을 적응형으로 고릅니다**.

## 4. 대체안 제안

### 4.1 A5 대체: "K = 3 병렬 다수결" 삭제

**Astra — A5′ "검사 → 수리" 순차 루프** [제안]
- T0(정지 허용)
  1. effort low로 1회 호출합니다.
  2. 검사기 1–6에 **실행 기반 전제·효과 검사**를 더합니다([접목]). 단계 i의 전제 술어를 현재 측정 상태 또는 앞 단계의 `expected_after`로 코드 평가하고, 연쇄 일관성·금지 술어를 검사합니다.
  3. 실패하면 위반 목록을 붙여 **수리 재호출**합니다. 최대 N회([가정] N = 2, 근거 2509.02761의 "≤3 iterations 96.5%"는 오프라인 조건)
  4. 선택: Jev typed 질문이나 다른 계열 모델로 교차 검증합니다.
     - 근거: 2512.02304 "cross-family" (MED)
     - [가정] Jev와 Astra가 다른 계열인지는 미확인입니다.
- 비정지 호출(T_fail·T3)
  - 1회 호출 + 같은 검사를 합니다.
  - 실패하면 **이전 유효 계약을 유지**하고 백그라운드로 수리 재호출합니다(JEV-Star식 "previous valid plan available").
  - 로봇은 멈추지 않으므로 사용자 원칙과 충돌하지 않습니다.
- 계약에 결정 지점별 말로 한 확신(`astra_conf`)을 **기록만** 합니다. E-M8에서 결과와 맞춰 보정 곡선을 그립니다. 게이트로는 쓰지 않습니다.
  - 근거: 2505.14489는 개선 쪽(HIGH), 2609.07395는 에이전트 수준에서 이득이 없다는 쪽(MED-LOW)입니다.
- 같은 입력 반복 일치도는 **E0 측정 지표로만** 남깁니다(A5 판정 E0 유지).

**Jev — J5 conformal 게이트** [제안, E1 뒤에만 켬]
- `question_id@vN`마다 보정 집합으로 문턱 q̂를 잡습니다(KnowNo·CoFineLLM식).
  - 예측 집합이 원소 하나 → M4 확정 후보
  - 집합 크기 > 1이거나 `NONE_ESCALATE`를 포함 → 확정 보류(직전 확정 행동 유지 + 감속, §4)하고, 반복되면 Astra로 에스컬레이션합니다(Trust-or-Escalate·JRA 두 문턱 라우팅식).
- 질문별 보정이라 "질문 사이 확률 비교 금지"(J4)를 자연스럽게 지킵니다([접목]).
- 보장은 **단계별 주변(marginal) 커버리지**입니다. 에피소드 수준 보장이 아닙니다.
- 보정 집합 크기는 [가정]입니다. 참고로 논문들의 크기는 CoFineLLM 400, JRA 1,000, FIPER 성공 롤아웃 50입니다.
- E1 전에는 §6(게이트 끔, 최빈 선택)을 유지합니다.

**M7 — 성공 에피소드로 소프트 채널 문턱 보정** [접목]
- FIPER식으로 성공 에피소드에서 소프트 채널 문턱을 conformal 보정해, 에피소드당 오경보 ≤ δ를 겨냥합니다.

### 4.2 A4: 잠정 기본 유지, 적응형으로 수정 [제안]

- 출력 `mode ∈ {patch, replace}`
  - `patch`: 지금 규칙 그대로입니다(`change_reason`, 실행한 단계 불변, 편집 거리 기록).
  - `replace`로 강제하는 경우([가정] 규칙):
    - (i) 실패 판정이 깨뜨린 전제 술어에 기대는 미실행 단계가 절반을 넘을 때
    - (ii) 목표나 물체 역할이 바뀔 때
    - (iii) patch가 검사기를 통과하지 못할 때
- `replace`도 이전 계약을 입력에 넣습니다(Plan-and-Act식). 이미 실행한 단계는 바꾸지 않습니다.
- **E-M2 비교 조건 추가**: {patch 전용, 이전 계약 넣고 전체 재생성, 적응형}
  - 지표: 성공률, Astra 출력 토큰·첫 토큰~완료 지연, 약속 보존율, 편집 거리
- 사용자 원칙은 바뀌지 않습니다. 실패할 때마다 Astra를 부르고, 형식만 바뀝니다.

## 5. 제외 (LOW, 권고 근거로 쓰지 않음)

- 2608.11403(다수결 역효과): 단독 소속(Scaler), 워크숍, v2는 비심사
- 2606.29054(CRC 불가능성): Independent Researcher
- 2606.11211(추론이 길수록 과신): 문항 47개, Llama만, 학회 없음
- 2605.28726(VLA 감시): 비보존 워크숍, 2★
- 2510.08044(CURE): 학회 없음
- 2606.05976(자기 교정 착시): 학회 없음
- 2609.17499(ENCP): 학회 없음
- 2604.27914(conformal 기권): 학회 없음
- 2607.24343: 학회 없음
- 2609.05779(diff 대 전체 파일): 2★
- 2508.05544와 2609.19654·2609.07395는 보조로만 씁니다.

## 6. 사용자에게 알릴 것

- **보장을 원하면 확률과 보정 집합이 필수입니다.** 그래서 보장은 Jev 쪽(E1 뒤)에서만 얻을 수 있고, Astra 쪽은 외부 검사로 "틀린 것을 잡는" 구조가 한계입니다.
- **[결정 필요]**
  - (가) A5를 삭제하고 A5′(검사 → 수리)로 바꿀지
  - (나) A4를 적응형 `patch | replace`로 바꿀지
  - (다) J5를 E1 뒤에 켤 후보로 정본 §6 설정 표에 넣을지
