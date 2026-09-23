# 07. 평가 계획과 핵심 주장 검증 ("VLA는 새 환경에 일반화 못 하고, LLM 기반은 한다")

작성일: 2026-09-23 · 감사 대상: `docs/plan.md` §3 평가 계획, §0 핵심 메시지

## 조사 한계 (먼저 읽을 것)
- 이 세션에서 쓸 수 있는 네트워크는 WebSearch뿐이었다. arxiv.org, huggingface.co 직접 접근은 막혀 있었다(WebFetch 시도 결과 `EGRESS_BLOCKED`).
- **세션 전체의 WebSearch 한도(200회)를 다른 모듈이 거의 다 써서, 이 모듈에서 실제로 돌린 검색은 약 15회뿐이다.** 그래서 아래 내용은 두 종류로 나뉜다.
  - **[검색 확인]**: 이번 세션 검색 결과(snippet)로 확인한 것. 출처 URL을 붙였다.
  - **[사전 지식·미확인]**: 모델의 사전 지식(2026-06 이전)에 기반한 것. 이번 세션에서는 검색으로 확인하지 못했다. 논문에 넣기 전에 반드시 원문으로 다시 확인해야 한다. 수치는 일부러 거의 적지 않았다.
- 권장 검색 목표(40회 이상)를 채우지 못했다. §5의 확인 못 한 목록을 다음 세션에서 우선 확인해야 한다.

---

## 1) 검증 표

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| AGNOSTOS / X-ICM 존재, 제목, arXiv 2505.15660, NeurIPS 2025 | CONFIRMED-MULTI | 정식 제목은 "Exploring the Limits of Vision-Language-Action Manipulation**s** in Cross-task Generalization" (v1/v2), NeurIPS 판은 "Manipulation" (s 없음). 제1저자 Jiaming Zhou. 2025-05 첫 공개 → 1.5년 창 안. NeurIPS 2025 poster. 공식 코드 저장소 `jiaming-zhou/X-ICM` 존재(검색 결과 제목으로만 확인, 저장소는 열어보지 않음). | https://arxiv.org/abs/2505.15660 · https://proceedings.neurips.cc/paper_files/paper/2025/hash/cc92809cd8dfbd035801966ab4896741-Abstract-Conference.html · https://neurips.cc/virtual/2025/poster/116674 · https://openreview.net/forum?id=h6xQClTm4W · https://github.com/jiaming-zhou/X-ICM |
| "처음 보는 23개 작업" | CONFIRMED-MULTI | 맞다. 학습(seen) 18개, 테스트(unseen) 23개. Level-1 13개(물체나 동작이 seen과 일부 겹침), Level-2 10개(완전히 새 장면). RLBench 기반 시뮬레이션. | https://arxiv.org/html/2505.15660v3 · https://jiaming-zhou.github.io/AGNOSTOS/ |
| "VLA는 23개 작업에 일반화하지 못했다" | CONFIRMED-MULTI (단, 표현 정정 필요) | 논문 표현은 "struggle to generalize effectively". 즉 **0이 아니라 낮다**. π0 평균 17.5%, VoxPoser 15.6%; 후속 논문 기준 OpenVLA 13.6%, RDT 12.1%. "다른 모델들은 23개 중 최소 8개 작업에서 완전히 실패"했다. | https://arxiv.org/pdf/2505.15660 · https://arxiv.org/pdf/2605.01448 |
| "LLM in-context 방법이 크게 앞섰다" | **WRONG (과장)** | X-ICM(7B) 23.5%, X-ICM(72B) 30.1%. 초록의 "π0 대비 +6.0%, VoxPoser 대비 +7.9%"는 **7B 기준**이다(17.5+6.0=23.5, 15.6+7.9=23.5로 일치). 72B도 π0 대비 +12.6%p. **LLM 방법도 절대 성공률은 30% 수준**이다. "LLM은 일반화된다"의 근거로 쓰기엔 약하다. 정확한 표현: "LLM in-context 방법이 VLA보다 덜 무너졌지만, 둘 다 낮다". | https://arxiv.org/pdf/2505.15660 · https://jiaming-zhou.github.io/AGNOSTOS/ |
| AGNOSTOS가 "새 환경" 일반화를 재는가 | **WRONG (주제 불일치)** | AGNOSTOS는 **새 작업(cross-task)** 일반화 벤치마크다. 사용자 주장은 **새 환경**이다. 같은 RLBench 시뮬레이터 안에서의 새 작업이라, 조명·카메라·배경·물체 외형 같은 환경 변화는 따로 측정하지 않는다(검색 snippet 기준). 환경 변화 축은 다른 벤치마크로 보충해야 한다(§4). | https://arxiv.org/html/2505.15660v3 |
| X-ICM이 "LLM+스킬"인가 | 비고 (SINGLE-SOURCE) | X-ICM은 seen 작업 시연을 in-context 예시로 넣어 LLM(Qwen2.5-Instruct 7B/72B)이 **행동 시퀀스를 직접 예측**하게 한다. 스킬 라이브러리 호출 방식이 아니다. 또한 seen 작업 시연을 쓰므로 "완전 zero-shot"은 아니다. 우리 시스템과 가장 가까운 기존 LLM 기준 방법이지만 같은 계열은 아니다. | https://arxiv.org/pdf/2505.15660 |
| AGNOSTOS에서 VLA를 어떻게 학습시켰는가 (seen 18개 미세조정 여부) | UNCONFIRMED | 공정 비교에 핵심이다. VLA를 seen 18개 작업으로 미세조정한 뒤 unseen에 돌렸다면, 이는 "소량 데이터 미세조정 VLA"의 한계이지 대규모 사전학습 VLA(π0.5, Gemini Robotics) 전체의 한계는 아니다. 원문 확인 필요. | — |
| SAFE (arXiv 2506.09937)의 서술 "VLA는 새 작업에 바로 배포하면 성공률이 제한적" | CONFIRMED-MULTI | 초록 문장: VLA는 "achieve limited success rates when deployed on novel tasks out of the box". NeurIPS 2025 (공식 저장소 제목과 OpenReview로 확인). 단, 이것은 **실패 감지 논문의 동기 문장**이지 일반화 실험 결과가 아니다. 주장의 근거로는 보조 인용만 가능하다. | https://arxiv.org/abs/2506.09937 · https://github.com/vla-safe/SAFE · https://openreview.net/forum?id=XPyAukgsFf |
| 2510.09607 snippet | 비고 (CONFIRMED-MULTI로 논문 정체 확인) | 2510.09607은 **VITA-VLA** (Dong, Fu 외, action expert distillation). snippet의 "VLA 방법은 일반화가 향상됐다"는 서론의 일반론 문장이며 **오히려 반대 방향**이다. 결과는 LIBERO 97.3% 등 **분포 내(in-distribution)** 벤치마크다. arXiv 전용, 학회 채택 미확인. **우리 주장의 근거로도 반론으로도 쓰지 않는다.** | https://arxiv.org/abs/2510.09607 · https://papers.cool/arxiv/2510.09607 |
| Goal-VLA (arXiv 2506.23919) | CONFIRMED-MULTI (채택 학회는 SINGLE-SOURCE) | 제목 "Goal-VLA: Image-Generative VLMs as Object-Centric World Models Empowering Zero-shot Robot Manipulation". 저자 Haonan Chen 외, Lin Shao(NUS LinS Lab). 2025-06-30 첫 공개(창 안). ICRA 2026 채택(검색 요약 한 곳). 주장: "VLA의 zero-shot 능력은 기반 VLM보다 크게 뒤처진다. 명령-영상-행동 데이터가 너무 적기 때문". **우리 주장을 지지**하는 서술이지만 이것도 동기 문장이다. 이름에 VLA가 들어가지만 실제로는 학습 없는 모듈형(VLM + 물체 자세 인터페이스) 방법이다. | https://arxiv.org/abs/2506.23919 · https://nus-lins-lab.github.io/goalvlaweb/ · https://chenhn02.github.io/ |
| BLAZER (arXiv 2510.08572) | CONFIRMED-MULTI (존재·내용), 학회 UNCONFIRMED | "BLAZER: Bootstrapping LLM-based Manipulation Agents with Zero-Shot Data Generation". Rocktim Jyoti Das 외, MBZUAI, Ivan Laptev. 2025-10-09 공개 → LLM+스킬 1년 창(2025-09-23 이후) **안**. LLM이 계획 생성 → 시뮬레이터에서 성공한 것만 모아 작은 LLM을 미세조정. 학습 풀 밖 작업에서도 향상. 단, 학습에 시뮬레이터 상태 접근이 필요. 코드 공개 여부 미확인. | https://arxiv.org/abs/2510.08572 · https://rocktimjyotidas.github.io/ |
| plan.md §5 "시뮬레이터(LIBERO, RLBench, ManiSkill)" | 비고 | AGNOSTOS를 쓰려면 RLBench(CoppeliaSim/PyRep)가 강제된다. LIBERO 계열은 VLA 쪽 표준이라 VLA 기준 방법 재현은 쉽지만, LLM 기준 방법(X-ICM)은 없다. | https://jiaming-zhou.github.io/AGNOSTOS/ |

---

## 2) 더 나은 대안 / 최신 SOTA

### 2-1. AGNOSTOS 위의 더 새로운 LLM 방법
- **Decompose and Recompose** (arXiv 2605.01448, 2026-05-02) [검색 확인]: 시연을 원자 스킬-행동 쌍으로 분해하고, unseen 작업에서 다시 조합한다. AGNOSTOS 전체 26.4%로 X-ICM(7B) 23.5%를 넘었다고 보고. 실제 로봇은 xArm6.
  - 신뢰도: arXiv 전용, 학회 채택·인용·스타 미확인 → **LOW~MEDIUM. 추천하지 않는다.** 다만 "AGNOSTOS가 이 분야의 비교 기준이 되고 있다"는 방증이다.
  - https://arxiv.org/abs/2605.01448
- **Zero-WAM** (arXiv 2608.26103) [검색 결과 제목만 확인]: "In-Context World-Action Modeling from Human Videos for Open-Ended Task Generalization". 내용·신뢰도 미확인.

### 2-2. 대규모 VLA / World Action Model 쪽 (반대 증거가 되는 최신 모델) → §3 참고

### 2-3. LLM/VLM 쪽에서 가져올 평가 관행 [사전 지식·미확인]
- LLM 에이전트 평가는 성공률 외에 **비용·호출 수·지연을 같은 표에 넣고, 같은 예산의 단순 기준 방법과 비교**하는 것이 표준이 되었다. plan.md M10의 "같은 토큰 예산 기준 방법" 제안과 맞는다.
- 체화 에이전트 LLM 벤치마크: **EmbodiedBench** (ICML 2025로 알고 있음, EB-Manipulation 포함), **Embodied Agent Interface** (NeurIPS 2024 D&B로 알고 있음). 둘 다 "LLM이 상위 계획/하위 조작을 얼마나 잘 하나"를 여러 LLM으로 잰다. Astra-only / Jev-only 조건 설계에 참고할 만하다. 이번 세션 검색 미확인.

---

## 3) 반대 증거와 위험

### 3-1. "VLA는 새 환경으로 일반화가 안 된다" — 2026-09 기준으로는 **그대로 쓰면 틀린 주장이 될 위험이 크다**
- **π0.5** (arXiv 2504.16054, Physical Intelligence) [검색 확인]: 학습에 없던 **실제 집 3곳과 모의 가정 환경**에서 부엌·침실 정리 같은 긴 작업을 수행. 제목 자체가 "Open-World Generalization". 저자들도 "항상 한 번에 성공하지는 않는다"고 한계를 인정.
  - https://arxiv.org/abs/2504.16054 · https://www.pi.website/blog/pi05
- **Gemini Robotics 2** (Google DeepMind, 2026-07-30 발표) [검색 확인, 요약 수준]: "학습 때 보지 못한 작업도 수행하고 낯선 상황에 즉석에서 적응한다", 한 체크포인트로 여러 로봇 몸체를 구동한다고 주장. Bloomberg 기사 제목은 "dexterity에서 고전"이라고 한계도 언급. 수치·기술 보고서 미확인.
  - https://deepmind.google/blog/gemini-robotics-2-brings-whole-body-intelligence-to-robots/ · https://www.bloomberg.com/news/articles/2026-07-30/google-unveils-gemini-ai-for-robots-struggling-with-dexterity · https://deepmind.google/models/gemini-robotics/
- **GR00T N2 / DreamZero World Action Model** (NVIDIA, 2026 GTC 발표, 연말 출시 예정) [검색 확인, 2차 출처만]: "기존 VLA 대비 새 환경의 새 작업 성공률을 두 배 이상" 올린다고 주장. MolmoSpaces·RoboArena 1위라고 보도됨. 1차 논문 미확인. 흥미롭게도 이 주장 자체가 "**기존 VLA는 새 환경·새 작업에 약하다**"는 것을 업계 1위 회사도 인정한다는 의미다. 동시에 그 약점이 빠르게 줄어들고 있다는 의미이기도 하다.
  - https://www.trendforce.com/news/2026/03/19/insights-nvidia-expands-robotics-ecosystem-at-gtc-as-physical-ai-moves-toward-large-scale-deployment/ · https://developer.nvidia.com/isaac/gr00t
- 결론: 2026-09 기준 사실관계는 이렇다.
  1. **소량 데이터로 미세조정한 공개 VLA**(OpenVLA, π0, RDT 등)는 새 작업·새 환경에서 크게 무너진다 → 증거 충분(AGNOSTOS, SAFE·Goal-VLA의 서술).
  2. **초대규모 데이터 frontier VLA/WAM**(π0.5 이후, Gemini Robotics 2, GR00T N2)은 새 환경 일반화를 실제 데모로 보이고 있다 → "VLA는 일반화 안 된다"는 **전칭 명제는 반박 가능**하다.
  3. LLM 기반 방법도 AGNOSTOS에서 절대 성공률 30% 수준 → "LLM 기반은 일반화된다"도 **전칭으로는 과장**이다.
- **권장 표현(사용자 결정 필요)**: "대규모 로봇 데이터 없이, 학습 없이, VLA보다 새 작업·새 환경에서 덜 무너지는 구조" 또는 "같은 로봇 데이터 예산에서 VLA 대비 일반화 우위". 이렇게 좁혀야 리뷰어가 π0.5·Gemini Robotics 2를 들고 와도 버틸 수 있다.

### 3-2. 비교 공정성 위험
- frontier VLA(Gemini Robotics 2, GR00T N2)는 비공개이거나 아직 미출시라 **재현 비교가 불가능**하다. 공개 가중치 VLA만 비교하면 "약한 VLA만 골랐다"는 비판을 받는다. 이 한계를 논문에 명시해야 한다.
- 우리 시스템은 GPT-6 Astra(최신 frontier API)를 쓰는데, AGNOSTOS의 X-ICM은 Qwen2.5 7B/72B다. 백본 차이 때문에 이긴 것인지, 구조 때문에 이긴 것인지 분리해야 한다 → **"같은 백본으로 기존 LLM 방법 재실행"** 조건이 필요하다(§4 범주 6).
- 우리 시스템은 인식 앞단(카메라 → 물체 JSON)이 필요하다. 시뮬레이터에서 물체 자세 정답(ground-truth)을 쓰면 VLA(이미지 입력)보다 유리해진다. X-ICM도 텍스트 입력 LLM이므로 같은 조건에서 비교 가능한지 원문 확인 필요. Jev 입력 변환 방법은 CLAUDE.md 규칙상 **사용자가 정하기 전까지 정하지 않는다**. 평가 설계에서는 "정답 상태 조건"과 "인식 추정 상태 조건"을 둘 다 두는 틀만 제안한다.

### 3-3. 인용 위험
- 2510.09607(VITA-VLA)은 우리 주장과 무관하거나 반대 방향이다. 근거로 인용하면 안 된다.
- SAFE·Goal-VLA의 문장은 동기 서술이지 실험 결과가 아니다. 핵심 근거는 AGNOSTOS의 수치여야 한다.

---

## 4) 이 모듈에 장착할 모듈 후보 순위

### 4-1. 벤치마크 / 시뮬레이터

| 순위 | 후보 | 근거 | 신뢰도 근거 |
|---|---|---|---|
| 1 | **AGNOSTOS (RLBench 기반)** | 새 작업 23개, 난이도 2단계. VLA(π0, OpenVLA, RDT 등)와 LLM(X-ICM), 모듈형(VoxPoser) 기준 수치가 이미 논문에 있다. 텍스트 입력 LLM 기준 방법이 있어 Jev(텍스트 전용)와 구조가 맞다. 후속 논문(2605.01448)도 이 벤치마크를 쓰기 시작 → 비교 기준으로 자리 잡는 중. 코드 공개. | NeurIPS 2025 채택(CONFIRMED-MULTI). 저장소 스타 수·인용 수는 미확인. |
| 2 | **환경 변화 축 보충용: RLBench 기반 섭동 벤치마크 (예: COLOSSEUM)** 또는 LIBERO 기반 섭동 벤치마크 (LIBERO-Plus, LIBERO-PRO) | AGNOSTOS가 재지 않는 "새 환경"(조명, 카메라 시점, 배경, 물체 외형·배치) 축을 잰다. RLBench 쪽을 쓰면 AGNOSTOS와 같은 시뮬레이터라 구현이 한 번으로 끝난다. | [사전 지식·미확인] COLOSSEUM은 RSS 2024로 알고 있으나(1.5년 창 밖, 벤치마크라 기준 방법 용도로는 무방) 이번 세션 확인 못 함. LIBERO-Plus/LIBERO-PRO는 2025-10 arXiv로 알고 있고, 공개 VLA가 섭동에 취약하다는 결과로 알고 있으나 **이번 세션 미확인, 학회 채택 미확인** → 확인 전에는 추천 보류. |
| 3 | 실제 로봇 소규모 검증 | 시뮬레이션만으로는 "새 환경" 주장이 약하다. AGNOSTOS·X-ICM, Decompose & Recompose 모두 실제 로봇 실험을 덧붙였다. | 관행 (위 논문들) |
| 보류 | RoboArena, MolmoSpaces | GR00T N2가 1위라고 보도된 일반 정책 평가. RoboArena는 DROID 플랫폼 실물 분산 평가로 알고 있다. 우리 시스템(Astra+Jev+스킬)을 올릴 수 있는지 미확인. | 이번 세션 검색은 NVIDIA 관련 2차 출처 한 번뿐. |
| 보류 | GenManip, VLABench | LLM 기반 모듈형과 end-to-end를 같이 재는 일반화 벤치마크로 알고 있다. | [사전 지식·미확인] 이번 세션 확인 못 함. |

**권장**: 주 벤치마크는 AGNOSTOS 하나로 확정하고, 환경 변화는 같은 RLBench 위에서 섭동 조건을 추가하는 방향. LIBERO를 주 벤치마크로 쓰면 VLA 재현은 쉽지만 LLM 기준 수치가 없고, LIBERO 원본은 분포 내 성능 포화(예: VITA-VLA 97.3%) 상태라 일반화 주장에 맞지 않다.

### 4-2. 비교 범주별 기준 방법 (plan.md §3의 6개 범주)

| 범주 | 추천 기준 방법 | 코드 | 신뢰도 / 비고 |
|---|---|---|---|
| 1. Astra만 | 우리 시스템에서 Jev 제거. Astra가 같은 스킬을 직접 호출하고 같은 상태 JSON을 받음 | 자체 구현 | 절제 조건. 느린 응답 때문에 지연 비용이 드러난다(CLAUDE.md 제약). |
| 2. Jev만 | 우리 시스템에서 Astra 제거. Jev가 작업 문장 + 텍스트 상태만으로 매 단계 선택 | 자체 구현 | 절제 조건. |
| 3. VLA | **π0**, **OpenVLA**, **RDT**: AGNOSTOS 논문에 수치가 있어 재사용 가능(π0 17.5%, OpenVLA 13.6%, RDT 12.1%). 가능하면 **π0.5 공개 가중치**를 seen 18개로 미세조정해 추가 | X-ICM 저장소(AGNOSTOS 평가 코드) 확인됨. π0/π0.5는 openpi 공개로 알고 있음 [사전 지식·미확인] | π0·π0.5: Physical Intelligence, 널리 인용. OpenVLA: CoRL 2024 [사전 지식]. π0.5를 넣지 않으면 "약한 VLA만 비교" 비판을 받는다. |
| 4. 룰베이스 | 같은 스킬 라이브러리 + 작업별 고정 스크립트(또는 키워드 매칭으로 스킬 순서 결정), LLM 없음 | 자체 구현 | unseen 작업에서는 스크립트가 없으므로 "사람이 unseen 작업마다 스크립트를 짜는 비용"을 함께 보고하는 게 공정하다. |
| 5. LLM+스킬 기존 논문 | **X-ICM** (필수, 같은 벤치마크, 코드 있음), **VoxPoser** (AGNOSTOS에 수치 있음), **BLAZER** (1년 창 안의 LLM+스킬 방법) | X-ICM: 확인. VoxPoser: 공개로 알고 있음 [사전 지식]. BLAZER: 미확인 | X-ICM: NeurIPS 2025 → HIGH. VoxPoser: CoRL 2023, 창 밖이지만 AGNOSTOS 공식 기준 방법이라 유지. BLAZER: MBZUAI + Ivan Laptev(저명 연구자), arXiv 전용, 채택·코드 미확인 → MEDIUM, 코드가 없으면 제외. Decompose & Recompose(2605.01448): LOW~MEDIUM → 제외, 관련 연구로만 언급. |
| 6. Astra를 쓰는 기존 논문 | GPT-6 Astra를 쓴 출판 논문은 **확인하지 못했다**(Astra 자체가 최근 모델). 대안: **범주 5의 방법(X-ICM, VoxPoser)을 백본만 Astra로 바꿔 재실행** ("같은 백본" 조건) | 범주 5와 동일 | 백본 효과와 구조 효과를 분리하는 역할. 사용자가 원래 의도한 "Astra 기반 기존 논문"이 따로 있다면 알려주어야 한다. |
| 추가 | 같은 토큰·호출 예산의 메모리 없는 기준 방법 (plan.md M10 제안 유지) | 자체 구현 | LLM 에이전트 문헌의 표준 관행 [사전 지식]. |

### 4-3. 지표
- **주 지표 (AGNOSTOS 관행)**: 작업별 성공률, Level-1 / Level-2 / 전체 평균, 완전 실패(0%) 작업 수 — X-ICM 논문이 "0% 작업 수"를 강조했으므로 같은 형식으로 보고하면 직접 비교가 쉽다. [검색 확인: 평균 성공률, 0% 작업 수]
  - 작업당 에피소드 수와 시드 수는 AGNOSTOS 원문 설정을 따라야 한다(미확인). 신뢰구간(예: 부트스트랩 95%)을 함께 보고할 것을 권장.
- **일반화 지표**: seen 대비 unseen 성능 하락폭(절대·상대). "VLA보다 덜 무너진다"는 주장을 가장 직접적으로 보여 준다.
- **효율 지표** (plan.md 제안 유지): 작업 완료 시간, 로봇 정지 시간, Astra 호출 수, API 비용, Jev 호출 수와 지연.
- 실패 감지 정확도, 복구 성공률, jerk는 절제 실험용 부 지표로 둔다.

---

## 5) 확인 못 한 것 (다음 세션 우선 확인 목록)
1. AGNOSTOS에서 VLA 학습 방식(seen 18개 미세조정 여부), 작업당 에피소드 수, 입력 조건(X-ICM이 정답 물체 자세를 텍스트로 받는지). → 공정 비교의 핵심.
2. X-ICM 저장소의 스타 수, 인용 수, 평가 코드 상태.
3. π0.5의 새 집 실험 정확 수치, π0.6 / π*0.6 이후 PI 모델의 일반화 주장.
4. Gemini Robotics 1.5 기술 보고서와 Gemini Robotics 2의 정량 일반화 결과.
5. GR00T N2 / DreamZero 1차 논문과 "두 배" 수치의 기준.
6. LIBERO-Plus, LIBERO-PRO, COLOSSEUM, GenManip, VLABench, RoboArena, MolmoSpaces, EmbodiedBench, Embodied Agent Interface의 서지(ID, 학회)와 핵심 결과. 모두 이번 세션에서 검색하지 못했다.
7. BLAZER의 학회 채택 여부와 코드 공개 여부.
8. Goal-VLA의 ICRA 2026 채택을 두 번째 출처로 교차 확인.
9. "Astra 기반 기존 논문"이 실제로 존재하는지.
10. Zero-WAM(2608.26103)의 내용과 신뢰도.

원인: 세션 공용 WebSearch 한도(200회) 소진. 한도를 올리면(`CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`) 위 항목을 이어서 확인할 수 있다.
