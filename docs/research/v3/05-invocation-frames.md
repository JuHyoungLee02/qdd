# 05. M8 호출 시점 선행 연구 + 다중 프레임 입력 + M7/M9의 LLM/VLM 쪽 보강 (v3 초안 조사)

작성: 2026-09-24, v3 조사 에이전트 05. 대상: `docs/plan.md`의 M8(★ 컨트리뷰션 3번), M7, M9.

---

## 1. 조사 방법과 한계

- **WebSearch 13회** 사용(한도 15). 나머지는 arXiv 원문 HTML(`arxiv.org/html/<id>`)과 초록 페이지를 curl로 받아 필요한 절을 직접 읽었다.
- **원문(본문 해당 절 또는 표)을 읽은 논문 20편**: 2608.28075(전문), 2609.22587, 2607.01804, 2609.21908, 2609.20648, 2607.26789, 2606.25509, 2601.08665, 2509.03581, 2603.16673, 2608.01428, 2511.04898, 2601.07812, 2604.09687, 2604.07034, 2511.22354, 2505.11917(일부), 그 밖에 초록 메타데이터만 읽은 것 약 15편.
- 인용 수는 Semantic Scholar batch API(2026-09-24 조회)로 확인했다. venue는 arXiv comments, OpenReview API, 학회 페이지로 확인했다.
- 한계
  - arXiv 검색 API(export.arxiv.org)와 Semantic Scholar 검색 API가 **429(요청 과다)** 로 막혀서, 키워드 검색은 WebSearch에 기댔다. 그래서 검색 범위가 평소보다 좁다. 부재 주장(4.3절)은 이 한계 안에서의 결론이다.
  - GitHub 스타는 조회하지 않았다(이번 주제의 핵심 문헌 대부분이 코드 미공개이거나 스타가 판단에 결정적이지 않음).
  - HTML 변환에서 수식이 빠져서 일부 수치(격자 크기, 호출 간격 값)는 본문 문장이나 표에서만 확인했다. 확인 못 한 값은 적지 않았다.

---

## 2. 검증 표

신뢰도: HIGH / MED / LOW (README 기준). 인용 수는 Semantic Scholar 2026-09-24.

### 2.1 M8 호출 시점

| 항목 | 확인 수준 | 정정/비고 (신뢰도 근거) | 출처 URL |
|---|---|---|---|
| **Plan Along the Way / Robust TAMP** (2608.28075): "주기 대 이벤트 비교를 했을 수 있다"(v2의 추측) | ORIGINAL-CONFIRMED (전문 읽음) → v2 추측은 **WRONG** | 2026-08-28 제출. IIIT Hyderabad. **주기 호출과 비교하지 않았다. 시간 초과 호출도 없다.** 호출은 (1) 처음 계획, (2) 숨은 물체 발견(discovery event), (3) 실행기 내부 재시도로 못 고친 실패(failure event) 세 가지뿐이다. 비교 축은 모델 크기(Qwen3 4B/8B/32B), 모달리티(LLM 대 VLM), zero-shot 대 ICL이다. 재계획 한도 10회, 조건당 10회 시행, RLBench/CoppeliaSim 6개 변형. 핵심 수치(표 II, Mean TSR): 32B LLM zero-shot 95.0%, 32B VLM zero-shot 90.0%, 8B LLM zero-shot 86.7%, 8B VLM zero-shot 91.7%, 4B LLM zero-shot 26.7%. 저자 결론: "관계형 상태를 명시적으로 주면 8B·32B에서 VLM이 LLM보다 나은 점이 없고 지연만 크다." 우리에게 쓸 것: **실패를 층으로 나눠 실행기 안에서 먼저 처리하고, 못 고친 것만 FM에 구조화된 사건 문맥으로 올리는 구조**(표 I의 L1/L2 분류). 인용 1. **LOW** (arXiv만, 덜 알려진 그룹, 반응 없음) | https://arxiv.org/abs/2608.28075 , https://arxiv.org/html/2608.28075 |
| **React When You Need To** (2609.22587): 이벤트 트리거 비동기 VLA 추론 | ORIGINAL-CONFIRMED | 2026-09-18, TUM(Alois Knoll) + MBZUAI. **고정 간격 4종과 이벤트 트리거를 직접 비교했다.** 대상은 느린 계획기가 아니라 VLA 청크 추론이다. 정적 장애물에서는 간격이 길수록 잡기 성공이 올랐고(짧은 간격은 청크 합치기가 잦아 잡기를 망침), 움직이는 장애물·목표에서는 반대였다. 움직이는 목표에 놓기(과제 2): 동기 실행 5%, 긴 고정 간격 15%, 가장 좋은 고정 간격 60%, 짧은 고정 간격 30%, **이벤트 트리거 85%** (RTC보다 +45%p, 최고 고정 간격보다 +25%p). 세 설정 평균 95%, 최강 기준보다 +55%p(초록). 실물 Franka 한 대, 과제 2개. 인용 0. **LOW~MED** (TUM Knoll 연구실이지만 심사 전·반응 없음) | https://arxiv.org/abs/2609.22587 |
| **VLA-Corrector** (2607.01804) | ORIGINAL-CONFIRMED | 2026-07-02, 저장대 + Alibaba DAMO. 고정 행동 지평을 여러 값으로 바꿔 보는 실험(그림 2)과, 잠재 공간 편차가 지속되면 청크를 끊는 이벤트 방식을 비교했다. 예: π0.5 지평 50에서 성공 48.7→58.7%, 호출 수 5.15→4.98. SmolVLA 지평 10에서 61.90→73.00%, 호출 19.27→15.64. "좋은 고정 지평을 고르는 것이 아니라 언제 청크를 믿지 않을지를 정하는 것이 핵심"이라는 문장이 우리 논지와 같다. VLA 내부 잠재가 필요하다. 인용 6, 코드 공개. **MED-LOW** | https://arxiv.org/abs/2607.01804 |
| **CommitFlow** (2609.21908) | ORIGINAL-CONFIRMED (초록·관련연구·절제) | 2026-09-18, 국방과기대. 느린 모델 호출 시점 비교가 아니다. 단계 전이 전에 "물리 조건(commitment)"을 확인하고 의존 행동을 붙잡아 두는 감시기다. RoboTwin 2.0 10개 과제 평균 75.9%(기본 정책 +22.7). 우리에게는 "**정해진 순간**(단계 전이 직전)에 확인한다"의 근거 사례. 인용 0. **LOW** | https://arxiv.org/abs/2609.21908 |
| **SkipVLA** (2609.20648) | ORIGINAL-CONFIRMED (초록) | Purdue(Kingston). 자유 공간 이동은 고전 플래너, 접촉 구간만 VLA 호출. **호출 시점 방식 비교가 아니다.** "최대 2.5배 빠름"은 최대값. 인용 0. M8 근거로는 쓰지 않는다. **LOW~MED** | https://arxiv.org/abs/2609.20648 |
| **CheckVLA** (2607.26789) ★ 새로 찾음 | ORIGINAL-CONFIRMED (초록, 표 3) | 2026-07-29, 칭화대·상해교대·북경대·NTU. **호출 수를 맞춘(invocation-matched) 주기 재계획과 검증 트리거를 비교했다.** 주기 간격은 검증 세트로 골라 에피소드당 10.1회, CheckVLA 10.2회. RoboCasa365 평균 성공: 주기 재계획 27.6%, 검증 트리거(나머지 동일) 31.5%(+3.9), 전체 36.1%(+8.5). 같은 5% 오경보에서 적시 재현율 77.9%. 학습된 행동 조건 월드 모델 필요. 시뮬레이션만. 인용 2. **MED-LOW**. 우리 실험 설계(호출 수 맞추기, 오경보율 맞춘 재현율)에 그대로 가져올 **평가 방법**이 핵심 가치 | https://arxiv.org/abs/2607.26789 |
| **ASSCG** (2606.25509) ★ 새로 찾음 | ORIGINAL-CONFIRMED (초록, 표 3) | 2026-06-24, 칭화 AIR + Lenovo. 자율주행 fast–slow LLM 계획기에서 **항상 호출 / 5프레임 고정 간격 / 난이도 휴리스틱 / 학습된 Query·Cache·Drop 게이트**를 비교. nuPlan Hard20: 항상 호출 65.00점 0.80s/프레임, 5프레임 고정 64.27점 0.32s, ASSCG 67.28점 0.32s. 14개 시나리오 유형별 고정 간격 격자 탐색에서 최적 간격이 3.1~29.3프레임으로 달랐다. 게이트는 SFT+GRPO로 학습. 인용 1. **MED-LOW** | https://arxiv.org/abs/2606.25509 |
| **VLingNav** (2601.08665) ★ | ORIGINAL-CONFIRMED (표 6) | 2026-01-13, ByteDance Seed. 네비게이션 VLA에서 추론(CoT) 빈도 비교. ObjNav SR: CoT 없음 36.2, 매 스텝 25.3, 고정 간격(추론 빈도 20%) 42.5, 고정 간격(5%) 39.7, **적응형 50.1(빈도 2.1%)**. 매 스텝 추론이 오히려 가장 나빴다. 학습형. 인용 15. **MED** (대형 연구소, 심사 미확인) | https://arxiv.org/abs/2601.08665 |
| **Learning When to Plan** (2509.03581) ★ LLM 에이전트 | ORIGINAL-CONFIRMED (초록, 5.1절) | 2025-09-03, UCL·Oxford(Rocktäschel, Foerster, Grefenstette). Llama-3.3-70B zero-shot으로 **계획 빈도를 "안 함"부터 고정 간격까지 바꿔** POGS·Crafter 100 시드에서 측정. 결과: 성능이 계산량에 따라 단조 증가하지 않고 **중간 빈도에서 최고("Goldilocks")**, 항상 계획하면 오히려 떨어짐(되돌아가기 증가). Gemini 2.5 Flash, TextWorld에서도 같은 경향. 그리고 **"필요할 때만 계획하라"는 프롬프트로는 적응형 계획을 끌어내지 못했다**(항상/전혀로 쏠림) → SFT+RL로 학습. OpenReview에 "Submitted to ICLR 2026"으로 표시(채택 표시 없음). 인용 19. **MED** (유명 연구실, 심사 통과 미확인) | https://arxiv.org/abs/2509.03581 , https://openreview.net/forum?id=mBxFCTlFmW |
| **RARRL: When Should a Robot Think?** (2603.16673) ★ | ORIGINAL-CONFIRMED (초록, 기준 방법 목록, 표 I) | 2026-03-17, Northeastern·CMU·Harvard. 체현 에이전트에서 **추론 안 함 / 매번 / 고정 간격(검증으로 조정) / 불확실성 임계값 휴리스틱 / 제약 PPO / 학습 오케스트레이터**를 비교. 오케스트레이터는 호출 여부, 추론 역할, **계산 예산**까지 정한다(= effort 축과 가까움). ALFRED 실제 LLM 추론 50 에피소드: 매번 추론 대비 LLM 시간 60% 이상 감소, 성공률 비슷(예: 네비게이션 84.0 대 82.7). 인용 3. **LOW~MED** | https://arxiv.org/abs/2603.16673 |
| **BRACE** (2608.01428) ★ | ORIGINAL-CONFIRMED (초록, 방법 절) | 2026-08-02, **ICML 2026 채택**(arXiv comments). 체현 에이전트 재계획을 예산 제어 루프로: 트리거가 오면 (1) 재계획할지, (2) 어떤 모드로, (3) 토큰 예산과 지연 목표(SLO)를 정한다. cooldown/commit 창으로 재계획 진동을 막는다. Habitat·RoboFactory·AirSim에서 호출 토큰 62~92% 감소, SLO 위반 85.5~100% → 4.7~50.0%. **트리거 방식끼리(주기/이벤트/시간 초과) 비교는 하지 않았다.** 인용 0(신규). **HIGH**(ICML) | https://arxiv.org/abs/2608.01428 |
| **Real-Time Reasoning Agents** (2511.04898) | ORIGINAL-CONFIRMED (초록, 일부 절) | 2025-11-07, Diyi Yang·Hao Zhu(Stanford). **ICLR 2026 채택**(proceedings PDF 확인). 짧은 추론(reactive) 대 긴 추론(planning) 에이전트를 시간 압박 아래 비교하고 둘을 동시에 돌리는 AgileThinker 제안. effort 축의 LLM 쪽 선행 연구. 로봇 아님. 인용 9. **HIGH** | https://arxiv.org/abs/2511.04898 , https://proceedings.iclr.cc/paper_files/paper/2026/file/ccbe16043125599293b01dd467c260f3-Paper-Conference.pdf |
| **OneTwoVLA** (2505.11917) | 메타데이터 ORIGINAL-CONFIRMED, 본문 일부 | **ICLR 2026 포스터**(OpenReview). 하나의 VLA가 추론/행동 모드를 스스로 전환, 주로 하위 작업 경계와 오류 때 추론. 추론 모드 진입 시 2~3초 멈춤(타 논문 서술, 원문 미확인). 고정 간격 기준과의 비교는 원문에서 찾지 못했다. 인용 123. **HIGH**. 학습형이라 "정해진 순간 = 하위 작업 경계" 근거로만 쓴다 | https://arxiv.org/abs/2505.11917 |
| PACE (2608.03034) | 초록만 | 추론 토큰 예산을 실행 시간 창에 맞춰 배분, 생각을 실행 중에 숨김(66.8%). Robotouille, 성공률 10%(절대값 낮음). 인용 0. **LOW** → 개념만("실행 중에 Astra를 돌려 멈춤을 숨긴다"는 사용자 의도와 같은 방향) | https://arxiv.org/abs/2608.03034 |
| CoMuRoS (2511.22354) | ORIGINAL-CONFIRMED | v2 미확인 항목. IIT Gandhinagar. 다중 로봇 LLM 계획, 물체 떨어짐·사람 의도 변화로 이벤트 재계획. **비교 실험 없음.** **LOW** | https://arxiv.org/abs/2511.22354 |
| 고전: Åström & Bernhardsson, "Comparison of Riemann and Lebesgue sampling for first order stochastic systems", CDC 2002 | CONFIRMED-MULTI (Lund 포털, ResearchGate) | **기간 밖, 기초 문헌.** 주기 샘플링(Riemann) 대 사건 기반 샘플링(Lebesgue)을 같은 평균 샘플 수에서 비교한 원조. 일부 단순계에서 사건 기반이 낫다. **"같은 호출 수에서 비교"라는 실험 틀의 원형** | https://portal.research.lu.se/en/publications/comparison-of-riemann-and-lebesgue-sampling-for-first-order-stoch/ |
| 고전: Heemels, Johansson, Tabuada, "An introduction to event-triggered and self-triggered control", CDC 2012 | CONFIRMED-MULTI (TU/e 포털, dblp, KTH 튜토리얼) | **기간 밖, 기초 문헌.** 약 2,000회 인용(scispace 표기). event-triggered = 상태가 임계값을 넘으면 샘플, **self-triggered = 지금 정보로 "다음에 언제 확인해야 하는지"를 미리 계산**. 사용자의 "이때쯤 결과가 나왔어야 한다"는 시간 초과 방식은 self-triggered(예측 기반 다음 확인 시각)와 구조가 같다. 논문에서 이 용어로 연결하면 좋다 | https://research.tue.nl/en/publications/an-introduction-to-event-triggered-and-self-triggered-control , https://people.kth.se/~kallej/papers/cdc12_tutorial_tabuada.pdf |

### 2.2 다중 프레임 입력

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| **More Images, More Problems? (MIMIC)** (2601.07812) | ORIGINAL-CONFIRMED (초록, 부록 A.1 표 6) | 2026-01-12, Samsung AI Cambridge + MPI(Schiele). Semantic Scholar venue: ACL. 결과: 정보가 여러 이미지에 흩어지면 성능이 일관되게 떨어지고, 이미지 수가 늘수록 떨어진다. **격자 이어붙이기(stitching) 대 개별 이미지**(시각 토큰 수를 맞춤): "전반적으로 비슷하거나 일부 약간 오름". 모델·과제별로 방향이 엇갈린다. 예: LLaVA-OV-7B Common 72.4→68.2(하락), Odd-one 58.0→67.1(상승). **대상은 오픈 모델(0.5B~7B)이고, 과제는 COCO 이미지 모음이지 시간 순 영상이 아니다.** 인용 6. **MED~HIGH**(ACL 표기, 유명 그룹; 채택 연도는 미확인) | https://arxiv.org/abs/2601.07812 |
| **Grid2Matrix** (2604.09687) | ORIGINAL-CONFIRMED (초록, 결과 일부) | 2026-04, UC Santa Cruz + BAIR. 색 격자를 행렬로 옮겨 적는 과제. GPT-5.2, Gemini-3 Pro/Flash 등 최신 독점 모델도 **생각보다 작은 격자에서 급격히 무너진다.** 오류는 격자 칸이 비전 인코더의 패치 경계와 어떻게 겹치는지에 크게 좌우된다. 프레임 격자 실험이 아니다. 우리에게 주는 뜻: **한 장에 여러 프레임을 넣으면 프레임마다 해상도가 줄고, 작은 세부(그리퍼 틈, 물체 미끄러짐)가 패치 경계에서 사라질 수 있다.** 인용 0. **LOW~MED** | https://arxiv.org/abs/2604.09687 |
| **KITE** (2604.07034) | ORIGINAL-CONFIRMED (초록, 표 I, 표 III) | v2의 "LOW~MED"를 정정: **ICRA 2026 채택**(arXiv comments). 학습 없이 광류 크기 봉우리로 키프레임을 고르고(부족하면 균일 프레임으로 채움), 검출 결과·타임스탬프 덧그림·BEV 배치도·로봇 프로필 텍스트를 붙인다. RoboFAC 실세계 MCQ: 전체 KITE FD 0.84 / FI 0.43 / FL 0.74, **균일 키프레임으로 바꾸면 0.69 / 0.33 / 0.56**, BEV 빼면 0.81/0.37/0.70. 즉 **키프레임 선택이 BEV보다 더 중요**했다. 참고로 GPT-4o(KITE 없이) 실세계 FD 0.96, FI 0.43, FL 0.52. 백본은 Qwen2.5-VL-7B. 인용 2. **MED~HIGH**(ICRA, 반응 적음) | https://arxiv.org/abs/2604.07034 , https://m80hz.github.io/kite/ |
| AKS: Adaptive Keyframe Sampling (2502.21271) | 메타데이터 ORIGINAL-CONFIRMED | CVPR 2025, 인용 198. 질문 관련도 + 시간 커버리지를 함께 최대화하는 학습 없는 키프레임 선택. arXiv 2025-02-28이라 **기간 밖**(15일 이르다). 개념만. | https://arxiv.org/abs/2502.21271 |
| BOLT (2503.21483) | 초록 ORIGINAL-CONFIRMED | CVPR 2025, 인용 89, 2025-03-27(기간 안). 학습 없이 질문-프레임 유사도로 프레임 선택(역변환 샘플링). "노이즈가 많은 문맥에서 균일 샘플링이 나쁘다". **HIGH**. 실패 설명 질의("그리퍼가 물체를 놓친 순간")로 프레임을 고르는 데 쓸 수 있다 | https://arxiv.org/abs/2503.21483 |
| IG-VLM "An Image Grid Can Be Worth a Video" (2403.18406) | 메타데이터 확인 | 2024-03, IEEE Access, 인용 122. 영상을 격자 한 장으로 바꿔 zero-shot VQA. **기간 밖, 기초 문헌**(격자 방식의 원조 격). 최신 모델로의 전이는 미확인 | https://arxiv.org/abs/2403.18406 |
| **Astra 이미지 토큰 계산** (OpenAI 공식 문서) | ORIGINAL-CONFIRMED (developers.openai.com) | `gpt-6-astra`는 32px 패치 기반, 배수 1.2. detail `low` = 512×512 안에 맞춤, `high` = 최대 2,500 패치, `original` = 최대 30,000 패치. 문서 예시: 2048×2048 → 1600×1600 → 2,500 패치 → 3,000 토큰. **내 계산(문서 규칙 적용)**: low 한 장 ≤ 16×16=256 패치 → 약 308 토큰. 따라서 **low 개별 10장 ≈ 3,080 토큰 ≈ high 격자 1장(최대 3,000 토큰)**. 입력 $10/1M이면 호출당 약 $0.03. 토큰 수가 TTFT에 주는 영향은 측정하지 못했다 | https://developers.openai.com/api/docs/guides/images-vision |
| STAR (2503.06060) 격자 근거 | v2 결론 유지 | 2025-03-08, **기간 밖**, GPT-4V, LOW. 핵심 근거로 쓰지 않는다 | https://arxiv.org/abs/2503.06060 |

### 2.3 M7 진행 판별, M9 복구 (LLM/VLM 쪽)

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| **GVL** "Vision Language Models are In-Context Value Learners" (2411.04549) | CONFIRMED-MULTI | v2 미확인 항목 해결. Ma, Hejna, … (Google DeepMind, UPenn Jayaraman). **ICLR 2025 포스터**, 인용 118. arXiv 2024-11-07이라 **기간 밖, 기초 문헌**(학습 없는 VLM 진행도 추정의 기준점). 방법: 섞은 프레임을 주고 프레임별 진행 %를 매기게 해서 시간 순서 편향을 없앤다. 300개 이상 실세계 과제 zero-shot/few-shot | https://iclr.cc/virtual/2025/poster/28853 , https://arxiv.org/abs/2411.04549 |
| OpenGVL (2509.17321) | 초록 ORIGINAL-CONFIRMED | CoRL 2025 워크숍. 오픈 모델이 독점 모델 성능의 약 70%. → Astra 같은 독점 API에서 GVL이 맞다는 v2 판단을 뒷받침. **MED** | https://arxiv.org/abs/2509.17321 |
| TOPReward (2602.19313) | v2 유지 + 인용 27 | logit 필요. Astra가 logprob을 주는지는 여전히 미확인 | https://arxiv.org/abs/2602.19313 |
| **AgentRewardBench** (2504.08942) | 초록 ORIGINAL-CONFIRMED | McGill/Mila(Siva Reddy 그룹으로 추정, 저자 목록 일부만 확인). 웹 에이전트 궤적 1,302개, LLM 판정기 12개. **어떤 판정기도 모든 벤치마크에서 우세하지 않다. 규칙 기반 평가는 성공을 과소 보고한다.** 인용 90. venue 미확인 → **MED**. M7에 주는 뜻: 판정기 하나를 믿지 말고, 규칙(술어)과 모델 판정을 함께 쓴다 | https://arxiv.org/abs/2504.08942 |
| **ReflAct** (2505.15182) | 초록 ORIGINAL-CONFIRMED | **EMNLP 2025 main**, 인용 40. 매 스텝 "다음 행동" 대신 "현재 상태가 목표에 비해 어디인가"를 먼저 쓰게 하는 골격. ALFWorld 93.3%, ReAct 대비 평균 +27.7%, Reflexion을 붙인 ReAct보다도 나음. 학습 없음. **HIGH**. 로봇 적용은 찾지 못했다 | https://arxiv.org/abs/2505.15182 |
| **WebRollback** (2504.11788) | 초록 ORIGINAL-CONFIRMED | **EACL 2026**, Tencent AI Lab 저자진(Zhisong Zhang, Wenhao Yu, Haitao Mi 등), 인용 13. 행동 공간에 "이전 상태로 되돌리기"를 명시적으로 넣는다. zero-shot과 미세조정 모두에서 효과. **MED~HIGH** | https://arxiv.org/abs/2504.11788 |
| AgentRewind (2608.14380) | 초록 | 에이전트 문맥과 환경을 함께 체크포인트, 되돌린 뒤 이전 시도 정보를 들고 재개. 인용 5. **LOW** → 개념만 | https://arxiv.org/abs/2608.14380 |
| REVISE (2609.00643) | 초록 | 수정이 오면 의존성으로 영향받은 부분만 다시 계산하고 유효한 진행은 보존. **LOW** → 개념만 | https://arxiv.org/abs/2609.00643 |

---

## 3. 새로 찾은 것과 모듈별 최고 후보

### 3.1 M8 호출 시점: 무엇을 가져오나

"최고"를 한 방법으로 정할 수 없다. 모든 비교가 서로 다른 조건(VLA 청크, 자율주행, 텍스트 게임)이다. 대신 **실험 틀과 부품**을 가져온다.

| 순위 | 가져올 것 | 어디서 최고/강했나 | 우리 구조에 접목 |
|---|---|---|---|
| 1 | **호출 수를 맞춘 비교(invocation-matched) + 오경보율을 맞춘 적시 재현율** | CheckVLA: 같은 10회/에피소드에서 트리거 교체만으로 +3.9%p. 고전 Åström(2002)도 같은 평균 샘플 수에서 비교 | 주기 / 정한 순간 / 시간 초과 / 실패 이벤트를 **같은 Astra 호출 수**에서 비교한다. 주기 간격은 검증 세트로 고른다(CheckVLA, RARRL과 같은 관행) |
| 2 | **트리거를 받은 뒤 "진짜 부를지 + 예산"을 정하는 문지기, cooldown/commit 창** | BRACE(ICML 2026): SLO 위반 크게 감소, 재계획 진동 억제. ASSCG의 "chattering" 억제도 같은 목적 | Astra 호출을 (트리거) → (문지기: 부를지, effort low/high, 입력 토큰 예산) 두 단계로 나눈다. 복구 직후 일정 시간은 다시 부르지 않는다. **effort를 호출 목적별로 나누자는 v2 제안에 ICML 근거가 생겼다** |
| 3 | **실패를 층으로 나눠 아래에서 먼저 처리, 못 고친 것만 구조화된 사건 문맥으로 상위 모델에** | Robust TAMP 표 I(LOW, 구조 참고용). BRACE의 failure-aware override(HIGH) | 스킬 내부 재시도 → Jev 재선택 → Astra. Astra 입력에 "사건 종류, 단계, 관련 행동, 증거"와 완료된 행동 이력을 넣는다 |
| 4 | **시간 초과 = self-triggered 개념** | Heemels 외(2012, 기간 밖 기초 문헌) | M2의 예상 소요 시간(코드가 계산)에서 "다음 확인 시각"을 정한다. **LLM 자기 판단으로 두지 않는다**: Learning When to Plan에서 "필요할 때만 계획하라" 프롬프트가 작동하지 않았다. Jev도 수치·시간 비교에 약하다 |
| 5 | **정한 순간 = 단계 전이 직전** | CommitFlow(LOW), OneTwoVLA(HIGH, 학습형)는 하위 작업 경계에서 추론 | 사용자가 정한 순간의 기본값 후보로 "스킬 전이 직전 확인"을 둔다 |
| 6 | effort 축의 선행 근거 | Real-Time Reasoning Agents(ICLR 2026): 짧은/긴 추론을 동시에 돌리는 쪽이 시간 압박에서 우세 | Astra low를 빠른 확인용, high를 멈춤 허용 재계획용으로. "low와 high를 동시에 발사해서 low로 먼저 움직이고 high로 고친다"는 변형도 실험 후보 |

### 3.2 다중 프레임: "실패 순간 → Astra" 증거 묶음 권고 [제안]

근거를 모으면 이렇다.
- 격자 대 개별: **일관된 승자가 없다.** MIMIC은 토큰을 맞추면 비슷하거나 약간 오른다고 했고, 과제에 따라 오르내린다. Grid2Matrix는 한 장에 촘촘히 넣을수록 세부가 패치 경계에서 사라진다고 보였다. 시간 순 실패 영상에서 최신 API 모델로 두 방식을 비교한 연구는 찾지 못했다.
- 프레임 선택: **어떤 프레임을 넣느냐가 격자냐 개별이냐보다 크다.** KITE 절제에서 균일 선택으로 바꾸면 FD 0.84→0.69로, BEV를 뺄 때(0.81)보다 더 떨어졌다. BOLT(CVPR 2025)도 균일 샘플링이 나쁘다고 했다.
- 이미지 수: MIMIC은 이미지가 많을수록, 정보가 흩어질수록 떨어진다고 했다. 10장이 많을수록 좋다는 근거는 없다.
- Astra 비용: low 개별 10장과 high 격자 1장이 입력 토큰이 거의 같다(약 3,000). 비용으로는 둘 중 하나를 고를 이유가 없다.
- 텍스트 상태: Robust TAMP에서 관계형 상태를 명시적으로 주면 VLM이 LLM보다 나은 점이 없었다. 이미지는 **텍스트 상태가 설명하지 못하는 부분**을 위해 넣는다.

권고(기본값, 실험으로 확인):
1. **개별 이미지를 기본으로, 격자 한 장은 비교 조건으로 둔다.** 이유: 프레임마다 고유 패치 예산이 있고, 순서 경계가 명확하며, 중요한 프레임만 `high`로 올리는 혼합이 가능하다. 격자는 한 장에 2,500 패치 상한이 걸려 프레임당 해상도가 줄어든다(Grid2Matrix 위험).
2. **프레임 구성(약 6~10장)**: (a) 현재 하위 작업 시작 프레임 1장, (b) 마지막으로 "정상"이라 판정된 프레임 1장, (c) 그 사이 광류 봉우리(KITE 방식) 3~5장, (d) 실패 감지 순간과 현재 프레임 각 1장. 감지 순간과 현재 프레임은 `high`, 나머지는 `low`.
3. **각 이미지 앞에 텍스트 꼬리표**: "t=-1.8s, 스킬=grasp, 단계=close, 그리퍼 폭=…". 타임스탬프 덧그림(KITE)도 넣는다.
4. **이미지와 함께 구조화된 텍스트**: 센서 술어(파지 여부, 힘), 완료된 행동 이력, 실패 사건 종류(Robust TAMP 방식), Jev의 최근 선택과 확률.
5. 손목 카메라와 외부 카메라는 **시점별로 나눠** 넣는다(v2의 Guardian 결과는 시점 축에서 개별 입력이 나았다: 0.74→0.83).
6. 실험 조건: {개별 low×10, 개별 혼합(2 high + 6 low), 격자 high×1, KITE식 키프레임 대 균일} × {effort low, high}.

### 3.3 M7 진행 판별 (LLM/VLM 쪽 보강)

- 1순위 유지: **센서·술어 판정**(v2). AgentRewardBench가 "판정기 하나로 모든 경우를 이길 수 없다"를 LLM 쪽에서 보였다.
- 가끔 Astra로 **GVL 방식 확인**(ICLR 2025, 기간 밖 기초 문헌): 섞은 프레임으로 진행 % 추정. 주기 호출 조건에서 Astra가 할 일의 기본 형태로 쓴다.
- **ReflAct식 "상태 대 목표" 먼저 쓰기**(EMNLP 2025, 학습 없음, 로봇 미적용): Astra 프롬프트 첫 단계로 "지금 상태가 목표에 비해 어디인가"를 적게 한다. Jev에는 긴 자유 서술이 맞지 않으므로 "목표 술어 중 참인 것" 같은 Choice 질문으로 바꿔 쓴다.

### 3.4 M9 복구 (LLM 쪽에서 가져올 것, 로봇 미적용)

- **명시적 되돌리기 행동**(WebRollback, EACL 2026): 웹과 달리 물리 세계는 되돌릴 수 없다. 그래서 "되돌리기"를 (a) **계획 상태의 체크포인트 복귀**와 (b) **리셋 스킬 호출**(FLARE의 reset 갈래)로 나눈다. Astra 출력 스키마에 `rollback_to=<체크포인트 id>`를 선택지로 둔다.
- **유효한 진행 보존**(REVISE 개념, LOW; Robust TAMP의 완료 행동 이력, CommitFlow의 "영향 없는 진행 보존"도 같은 방향): 재계획할 때 이미 성립한 술어는 다시 하지 않는다. 이것은 코드로 검사한다.
- ReflAct의 목표-상태 반성은 Reflexion 계열 후속 중 학회 근거가 있고 학습이 필요 없는 가장 쉬운 선택이다.

---

## 4. 반대 증거와 위험

### 4.1 호출 시점
1. **자주 부르면 나빠질 수 있다.** Learning When to Plan: 항상 계획하면 중간 빈도보다 나빴다. VLingNav: 매 스텝 추론(25.3)이 추론 없음(36.2)보다 나빴다. React When You Need To: 짧은 간격이 잡기를 망쳤다. → 주기 호출의 "Hz를 높이면 좋다"는 가정은 틀릴 수 있다. Astra 계획이 도착할 때마다 진행 중 스킬을 흔들 위험이 있으니 commit 창이 필요하다.
2. **"스스로 판단하는 시간 초과"를 LLM에게 맡기면 안 될 수 있다.** Learning When to Plan에서 프롬프트로 적응형 계획이 안 됐다. 코드가 계산하는 시간 초과로 정의하는 것이 안전하다.
3. **이벤트 트리거는 감지기 품질에 묶인다.** CheckVLA의 이득은 학습된 월드 모델 감지기에서 나왔다. 우리 감지기(술어 + Jev + FailBench 수준의 VLM 판정)는 그보다 약할 수 있다. 그러면 주기 호출이 이벤트 호출보다 나을 수도 있다. 이 결과도 보고할 가치가 있다.
4. 대부분의 비교 논문이 **학습된 게이트**로 이겼다(ASSCG, RARRL, VLingNav, Learning When to Plan). 학습 없는 규칙 트리거가 이길 것이라는 보장은 없다. "학습 없이"라는 우리 조건에서 규칙 트리거가 학습 게이트에 얼마나 못 미치는지가 드러날 수 있다.

### 4.2 다중 프레임
5. Robust TAMP에서 VLM이 LLM보다 나은 점이 없었다. 텍스트 상태가 좋으면 이미지 10장의 가치가 작을 수 있다. "이미지 없는 Astra(텍스트 상태만)" 조건을 기준으로 반드시 넣는다.
6. KITE 표에서 GPT-4o 단독이 실세계 FD 0.96으로 KITE+Qwen 0.84보다 높았다. 구조화 증거의 이득은 약한 오픈 모델에서 크고, Astra 같은 강한 모델에서는 작을 수 있다.
7. 격자 대 개별의 증거는 모두 오픈 모델 또는 비시간 과제다. Astra에서 결과가 뒤집힐 수 있다.

### 4.3 컨트리뷰션 3번의 새로움 (정직한 판정)

**결론: "주기 대 이벤트 호출의 정량 비교"는 새롭지 않다. "effort(추론 예산)를 함께 조절"하는 것도 부분적으로 선행 연구가 있다. 남은 빈칸은 좁다.**

이미 한 것:
- 주기(고정 간격) 대 이벤트/적응형, 같은 조건 비교: React When You Need To(VLA), CheckVLA(호출 수 맞춤), ASSCG(자율주행 LLM), VLingNav(추론 빈도), RARRL(체현 LLM, 고정 간격·휴리스틱 임계값·학습), Learning When to Plan(LLM 에이전트, 빈도 스윕), VLA-Corrector(고정 지평 대 이벤트).
- 추론 예산을 호출 결정과 함께: RARRL(호출 여부 + 역할 + 예산), BRACE(ICML 2026, 호출 여부 + 모드 + 토큰 예산 + 지연 목표), Real-Time Reasoning Agents(ICLR 2026, 짧은 대 긴 추론).

찾지 못한 것(아래 검색어 기준):
- (a) **"예상 시간 초과" 트리거를 독립 조건으로 둔 비교.** Robust TAMP, CheckVLA, ASSCG, RARRL 어디에도 없다. 고전 제어의 self-triggered와 같은 구조지만, LLM/VLM 호출에 적용해 비교한 연구는 찾지 못했다.
- (b) **학습 없는 최신 API 모델을 effort 단계(TTFT 2.8초 대 45초)별로, 로봇이 멈추지 않고 실행하는 동안 부르는 조건**에서의 비교. 기존 비교는 로컬 모델(수십~수백 ms)이거나 텍스트 게임이다.
- (c) 네 방식(주기 / 정한 순간 / 시간 초과 / 실패 이벤트)을 **호출 수를 맞춰** effort와 요인 설계로 비교한 연구.

권고 [제안]: 3번을 "호출 시점 비교"라는 방법 컨트리뷰션으로 쓰지 않는다. **"느린 API 계획기를 비정지 로봇에 붙일 때의 호출 시점 × effort 체계적 평가(시간 초과 트리거 포함)"라는 평가·분석 컨트리뷰션**으로 범위를 좁힌다. 관련 연구 절에 위 7편을 반드시 인용한다. 새로움 정도: 중간~낮음.

사용한 검색어(WebSearch 13회 중 이 판정에 쓴 것):
1. `arXiv 2026 when to invoke LLM planner robot periodic vs event-triggered replanning comparison latency`
2. `LLM agent "when to reflect" OR "when to replan" adaptive triggering 2025 arXiv`
3. `"fast and slow" dual-system LLM agent switching when to think System 1 System 2 2025 arXiv router`
4. `autonomous driving slow VLM invocation frequency trigger uncertainty fast-slow system comparison fixed interval vs adaptive 2025`
5. `OneTwoVLA adaptive reasoning when to think VLA ablation reasoning frequency fixed interval`
6. `robot LLM failure detection "expected duration" OR "time budget" OR "timeout" stall detection triggers VLM replanning subtask 2025 2026 arXiv`
7. `"when to call" OR "when to query" VLM supervisor robot manipulation invocation strategy periodic event-driven ablation cost latency 2026`
8. `"reasoning effort" OR "thinking budget" latency trade-off embodied agent robot real-time LLM planner evaluation 2026 arXiv`
9. 고전 제어 확인 1회
- arXiv API 검색(`"when to replan"`, `replanning AND frequency AND LLM AND robot`, `"event-triggered" AND "language model"`, `"when to query" AND "language model"`, `periodic AND "event-triggered" AND replanning`)은 **429로 결과를 받지 못했다.** 다음 세션에서 이 검색을 다시 돌려야 부재 판정이 단단해진다.

---

## 5. plan.md에 반영할 제안

- [사용자] (변경 없음) 최소한 실패 판정 시 호출, 연속 프레임 입력, 세 방식 비교, 처음 계획만 정지.
- [제안] **§4 컨트리뷰션 3번 문구 정정**: "선행 비교가 없는지 미확인" → "주기 대 이벤트 비교와 추론 예산 조절은 선행 연구가 있다(CheckVLA, RARRL, BRACE(ICML 2026), ASSCG, VLingNav, Learning When to Plan, 2609.22587). 새로움은 (a) 시간 초과 트리거, (b) 학습 없는 API 모델의 effort 단계, (c) 비정지 실행, (d) 호출 수를 맞춘 요인 설계에 있다. 평가 컨트리뷰션으로 쓴다."
- [제안] **M8 실험 설계**: 호출 수를 맞춘 비교(CheckVLA 방식), 주기 간격은 검증으로 선택, 지표에 적시 재현율(오경보율 고정), 호출당 지연 분포 꼬리(p95)와 마감 초과율(BRACE), 정지 시간 추가. 조건에 "Astra 없음"과 "이미지 없는 Astra"를 넣는다.
- [제안] **M8 호출 구조**: 트리거 → 문지기(부를지, effort, 토큰 예산) → 호출, 복구 후 cooldown. 근거 BRACE(HIGH).
- [제안] **시간 초과의 정의**: M2 예상 소요 시간에서 코드가 계산(self-triggered 개념). LLM 자기 판단으로 두지 않는다. 근거: Learning When to Plan(MED), Jev 수치 약점.
- [제안] **M8 다중 프레임 기본값**: 개별 이미지 6~10장, KITE식 움직임 키프레임 + 감지 순간·현재 프레임은 high, 나머지 low, 텍스트 꼬리표와 센서 술어 동반. 격자 한 장은 비교 조건. 근거: KITE(ICRA 2026), MIMIC, Grid2Matrix, Astra 토큰 규칙.
- [제안] **M7**: GVL 인용을 "ICLR 2025, 기간 밖 기초 문헌"으로 확정. ReflAct식 "상태 대 목표" 단계를 Astra 프롬프트에 추가.
- [제안] **M9**: Astra 출력 스키마에 `rollback_to` 선택지(계획 체크포인트 복귀)와 리셋 스킬을 분리해 둔다(WebRollback 개념 + FLARE reset). 재계획 때 이미 성립한 술어는 보존.
- [제안] KITE 신뢰도를 LOW~MED → MED~HIGH(ICRA 2026)로 올린다.
- [결정 필요] 시간 초과 트리거를 "M2 예상 시간 × 계수"로 할지, SAFE식 conformal 시간 임계값으로 할지.

---

## 6. 확인 못 한 것

- arXiv/Semantic Scholar 키워드 검색 API가 429로 막혀 **arXiv 전체 키워드 검색을 하지 못했다.** 부재 판정(4.3)은 WebSearch 결과와 읽은 논문의 관련 연구 절에 기댄 것이다.
- Learning When to Plan의 ICLR 2026 최종 결과(OpenReview "Submitted" 표시만 확인, 채택 표시 없음).
- MIMIC(2601.07812)의 ACL 채택 연도(Semantic Scholar venue 표기만 확인).
- AgentRewardBench의 venue.
- OneTwoVLA가 고정 간격 기준과 비교했는지(본문에서 찾지 못함), 추론 진입 시 2~3초 멈춤의 원문 출처.
- AsyncDriver(ECCV 2024)의 호출 간격 스윕 수치(ASSCG를 통해서만 확인).
- Astra 이미지 토큰 수가 TTFT에 주는 영향, 개별 이미지 여러 장과 격자 한 장의 실제 지연 차이. 우리 측정이 필요하다.
- Astra API의 logprob 제공 여부(TOPReward 적용 가능성).
- 시간 순 로봇 실패 영상에서 최신 독점 모델로 격자 대 개별 이미지를 비교한 연구(찾지 못함).
- React When You Need To의 고정 간격 실제 값(수식이 HTML 변환에서 빠짐).
