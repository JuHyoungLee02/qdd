# v2 감사 보고서 01: M1 상태 표현(이미지 → 텍스트) + M2 Astra → Jev 인수인계

- 작성일: 2026-09-23
- 대상: `docs/plan.md`의 M1, M2 절과 그 근거 문헌
- 방법: WebSearch 검색 요약(snippet)끼리 교차 확인. arxiv.org 직접 접근은 막혀 있음(WebFetch 1회 시도, EGRESS_BLOCKED).
- **중요한 한계**: 이 세션은 약 30회 검색 뒤 공유 검색 예산(200회)이 다 떨어졌다. 그래서 인용 항목 10개와 인식 앞단 핵심 후보는 확인했지만, 장면 그래프 계열(ConceptGraphs, HOV-SG, SayPlan), Set-of-Mark, 코드 기반 하위 목표 명세(Code as Policies, VoxPoser, MOKA, OmniManip 등)는 **이번 세션에서 검증하지 못했다**. 이 항목들은 5절에 "검증 필요"로만 적었고 추천 순위의 근거로 쓰지 않았다.
- 신뢰도 등급(사용자 규칙): HIGH = 주요 학회(ICLR/NeurIPS/ICML/CVPR/ICCV/CoRL/RSS/ICRA, ACL 계열)와 유명 연구실 / MEDIUM = 2급 학회(IROS 등)나 유명 기관의 arXiv / LOW = 알려지지 않은 그룹의 arXiv 전용 논문이나 하위 학회, 반응 없음 → 추천하지 않음.

---

## 1) 검증 표

| 항목 | 확인 수준 | 정정/비고 (신뢰도) | 출처 URL |
|---|---|---|---|
| **From Text to Space** (arXiv 2502.16690) | 논문 존재와 결론: CONFIRMED-MULTI / plan의 표현: 일부 부정확 | 정확한 제목: "From Text to Space: Mapping Abstract Spatial Models in LLMs during a Grid-World Navigation Task". 저자 Nicolas Martorell(단독). 2025-02-23. *Explainable Artificial Intelligence* 2025(Springer 학회 논문집)에 실림. 비교한 형식은 **Cartesian(좌표) / Topographic(격자 배치, ASCII에 가까움) / Textual(산문)** 세 가지이고, "좌표가 성공률과 경로 효율에서 일관되게 높았으며 모델이 클수록 효과가 컸다"는 부분은 확인했다. **다만 2D 격자 길찾기 결과다.** 3D 조작이나 JSON에 그대로 옮길 수 있다는 근거는 아니다. 1.5년 기준(2025-03-23)보다 1개월 이르다. 신뢰도: **LOW~MEDIUM**(단독 저자, 2급 venue). 보조 근거로만 쓴다. | https://arxiv.org/abs/2502.16690 , https://link.springer.com/chapter/10.1007/978-3-032-08330-2_13 , https://www.themoonlight.io/en/review/from-text-to-space-mapping-abstract-spatial-models-in-llms-during-a-grid-world-navigation-task |
| **RoboPrompt** (arXiv 2410.12782) | CONFIRMED-MULTI | 제목 "In-Context Learning Enables Robot Action Prediction in LLMs". Yida Yin, Zekai Wang, Yuvan Sharma, Dantong Niu, Trevor Darrell, Roei Herzig(UC Berkeley). **ICRA 2025**. "RLBench 16개 작업 평균 51.8%"는 확인했다. 주의할 점: 입력은 **초기 물체 자세 추정값 + 키프레임 엔드이펙터 행동**을 텍스트로 바꾼 in-context 예시다. 매 스텝 닫힌 루프 결정이 아니라 키프레임 행동 예측이다. 2024-10 논문이라 1.5년 기준을 벗어난다. 신뢰도: **HIGH**. | https://arxiv.org/abs/2410.12782 , https://davidyyd.github.io/roboprompt/ , https://ieeexplore.ieee.org/document/11128807/ |
| **Read More, Think More** (arXiv 2604.01535) | **WRONG (plan이 내용을 잘못 옮김)** | 정확한 제목: "Read More, Think More: Revisiting Observation Reduction for Web Agents". Enomoto, Obara, Zhang, Oyamada(NEC). 2026-04-02. 로봇이 아니라 **웹 에이전트(HTML과 접근성 트리 비교)** 연구다. 결론: 성능이 낮은 모델은 짧은 관측(접근성 트리)이 낫고, **성능이 높은 모델은 자세한 관측(HTML)이 낫다. thinking 토큰을 늘리면 HTML의 이점이 더 커진다.** **"변화분(diff)만 주는 방식이 토큰 효율적"이라는 내용은 이 논문에 없다.** plan에 적힌 두 번째 절반은 근거가 없으므로 지워야 한다. 오히려 강한 모델에게 입력을 지나치게 압축하면 손해일 수 있다는 **반대 근거**다. 신뢰도: **MEDIUM**(NEC, arXiv 전용). | https://arxiv.org/abs/2604.01535 , https://arxiv.org/html/2604.01535 |
| **Domain-Conditioned Scene Graphs** (arXiv 2504.06661) | CONFIRMED-MULTI | "Domain-Conditioned Scene Graphs for State-Grounded Task Planning". Jonas Herzog, Jiangpin Liu, Yue Wang. **IROS 2025**. 장면 그래프의 노드를 도메인 물체로, 관계를 도메인 술어로 제한해서 PDDL 기호 상태로 바로 옮긴다. LMM(GPT-4o)이 그래프를 만든다. "상태 접지를 개선했다"는 방향은 초록과 맞다. 구체적 수치는 미확인. 이 논문은 **상위 작업 계획(PDDL)**용이지, 빠른 저수준 결정용이 아니다. 신뢰도: **MEDIUM**. | https://arxiv.org/abs/2504.06661 , https://awesomepapers.io/robotics/papers/2504.06661 |
| **REFLECT** (arXiv 2306.15724) | CONFIRMED-MULTI(내용) / 학회: SINGLE-SOURCE(기억, 이번 검색으로는 미확인) | "REFLECT: Summarizing Robot Experiences for Failure Explanation and Correction". 다중 감각 관측(RGB-D, 소리, 로봇 상태)을 작업 맥락 장면 그래프, 이벤트 캡션, 계층 요약으로 바꾸고, LLM이 실패를 설명한다. RoboFail 데이터셋. 2023년 논문이라 기간을 벗어난다. M1보다 **M8(실패 설명)**에 더 맞는 근거다. 신뢰도: 학회(CoRL 2023으로 알려짐)를 확인하면 HIGH. | https://arxiv.org/abs/2306.15724 , https://robot-reflect.github.io/ , https://huggingface.co/papers/2306.15724 |
| **ReKep** (arXiv 2409.01652) | CONFIRMED-MULTI | "ReKep: Spatio-Temporal Reasoning of Relational Keypoint Constraints for Robotic Manipulation". Wenlong Huang, Chen Wang, Yunzhu Li, Ruohan Zhang, Li Fei-Fei. **CoRL 2024**. **정정**: ReKep 제약은 "텍스트 관계 제약"이 아니다. **3D 키포인트 → 수치 비용으로 가는 Python 함수**이고, 계층 최적화기가 실시간으로 풀어서 행동을 만든다. 따라서 Jev의 객관식 출력과 바로 이어지지 않는다(최적화기가 필요하다). 기간을 벗어난다. 신뢰도: **HIGH**. | https://arxiv.org/abs/2409.01652 , https://rekep-robot.github.io/ , https://dblp.org/rec/journals/corr/abs-2409-01652.html |
| **GSU** (arXiv 2603.17333) | CONFIRMED-MULTI(검색 2건이 같은 내용) | "Grid Spatial Understanding: A Dataset for Textual Spatial Reasoning over Grids, Embodied Settings, and Coordinate Structures". Risham Sidhu, Julia Hockenmaier(UIUC). 2026-03-18, cs.CL. "에이전트 기준 좌표계에 약하다"는 plan의 주장은 맞다. 좌표 목록으로 3D 모양을 알아보는 것도 약하다. 덧붙일 사실 두 가지: (1) 최신 프론티어 모델은 이 과제를 푼다. (2) 작은 LM을 미세조정하면 프론티어 수준에 다가갈 수 있다. 신뢰도: **MEDIUM**(유명 NLP 연구실, arXiv 전용). | https://arxiv.org/pdf/2603.17333 , https://arxiv.org/abs/2603.17333 |
| **B2FF** (arXiv 2606.09258) | CONFIRMED-MULTI | "Back to the Familiar Future: Failure Recovery for VLA Policies via Pre-Imagined Milestone Selection". 서울대, 연세대, 숭실대. 2026-06-08. 실패를 주입한 LIBERO에서 56.3% → 74.0%, VLA 동결(미세조정 없음). 모두 확인했다. **정정**: 이정표는 **foresight VLA가 생성한 미래 "이미지(시각 목표)"**이고, 복구 때 그 이미지를 고정 시각 목표로 조건화한다. 텍스트 전용 Jev에는 이 방식을 그대로 쓸 수 없다. 이정표를 M1 텍스트 상태로 표현하는 것은 우리가 새로 하는 일이고, B2FF가 검증한 것이 아니다. 신뢰도: **MEDIUM-LOW**(arXiv 전용, 3개월 전 논문, 반응 미확인). 개념 참고용으로만 쓴다. | https://arxiv.org/abs/2606.09258 , https://arxiv.org/html/2606.09258 , https://awesomepapers.io/robotics/papers/2606.09258 |
| **2507.12391** | CONFIRMED-MULTI | "Assessing the Value of Visual Input: A Benchmark of Multimodal Large Language Models for Robotic Path Planning". Jacinto Colan, Ana Davila, Yasuhisa Hasegawa. 2025-07-16. SICE FES 2025. MLLM 15개로 2D 격자 경로 계획을 평가했다. 결과: "잘 구조화된 텍스트보다 시각 입력이 항상 우세하지는 않았다". 큰 격자에서는 성능이 크게 떨어졌다. 신뢰도: **LOW~MEDIUM**(하위 학회). 핵심 근거로 쓰지 않는다. | https://arxiv.org/abs/2507.12391 , https://awesomepapers.io/robotics/papers/2507.12391 |
| **Socratic Models** (arXiv 2204.00598) | CONFIRMED-MULTI | "Socratic Models: Composing Zero-Shot Multimodal Reasoning with Language". Andy Zeng 외(Google). **ICLR 2023**(top 25%, oral 페이지 있음). 언어를 중간 표현으로 삼아 VLM과 LM을 zero-shot으로 조합한다. 우리 구조("이미지 → 텍스트 → 텍스트 LLM")의 원조 격이다. 기간을 벗어나지만 기초 문헌으로는 적절하다. 신뢰도: **HIGH**. | https://arxiv.org/abs/2204.00598 , https://openreview.net/forum?id=G2Q2Mh3avow , https://iclr.cc/virtual/2023/oral/12574 |
| plan 문장 "조작 작업에서 표현 형식 비교는 찾지 못했다" | **부분적으로 WRONG** | SiT-Bench(ACL 2026 Findings)는 장면을 **좌표를 담은 텍스트 설명**으로 바꿔서 LLM의 공간 지능을 평가한다. 17개 하위 과제에 **정밀 로봇 조작**이 들어 있다. 2507.12391도 텍스트와 시각을 비교한다. "조작용 표현 형식을 정확도, 토큰, 지연으로 함께 비교한 연구"로 범위를 좁혀야 컨트리뷰션 주장이 안전하다. | https://aclanthology.org/2026.findings-acl.90/ , https://arxiv.org/abs/2601.03590 |

---

## 2) 더 나은 대안 / 최신 SOTA (이번 세션에서 확인한 것만)

### 2.1 "이미지 대신 텍스트로 결정하는 것"을 뒷받침하는 강한 근거 (LLM/VLM 분야)
- **BALROG** (ICLR 2025, arXiv 2411.13543): 게임 에이전트 벤치마크. **환경 이미지를 함께 주면 여러 모델의 성능이 오히려 떨어졌다**("severe deficiencies in vision-based decision-making"). 텍스트 상태로 결정하게 하는 설계를 뒷받침하는 근거 중 **신뢰도가 가장 높다(HIGH)**. 로봇이 아닌 분야의 근거다.
  - https://openreview.net/forum?id=fp6t3F669F , https://proceedings.iclr.cc/paper_files/paper/2025/file/f0b1515be276f6ba82b4f2b25e50bef0-Paper-Conference.pdf
- **SiT-Bench** (ACL 2026 Findings, arXiv 2601.03590): 좌표를 담은 텍스트 장면 설명만으로 LLM을 평가했다. 국소 의미 과제는 잘하지만 **전역 일관성에서 "spatial gap"이 남는다**. 조작 하위 과제가 들어 있다. 신뢰도 **HIGH~MEDIUM**(Findings).
  - https://aclanthology.org/2026.findings-acl.90/
- 웹 에이전트 분야의 대응 관계(2604.01535): "접근성 트리(구조화 요약)냐 원본 HTML이냐"는 우리 문제("객체 JSON이냐 풍부한 장면 기술이냐")와 같은 구조다. **최적 표현은 모델 능력에 따라 달라진다.** Jev의 능력 수준에 맞춰 실험으로 정해야 한다.

### 2.2 형식 민감도: "가장 좋은 단일 형식"은 없다
- **Does Prompt Formatting Have Any Impact on LLM Performance?** (arXiv 2411.10541, Microsoft 계열로 알려짐, arXiv 전용 → MEDIUM): plain text, Markdown, JSON, YAML에 따라 GPT-3.5는 최대 40%까지 차이가 났다. GPT-4는 더 강건했다. **보편적으로 가장 좋은 형식은 없다.**
  - https://arxiv.org/abs/2411.10541
- **Do LLMs Build Spatial World Models?** (arXiv 2604.10690, OpenReview 제출본 있음, 학회 채택 미확인 → MEDIUM-LOW): 같은 미로라도 형식에 따라 정확도가 2~5배 달랐다(Gemini-2.5-Flash CoT: 토큰화한 인접 목록 86%, 시각 격자 텍스트 34%). CoT 없이는 대부분 실패했다. 순차 질의 사이에 공간 지식을 쌓지 못했다. → **Jev처럼 CoT 없이 바로 답하는 모델이면 사전 계산(상대 벡터, 술어)이 더 중요해진다**는 간접 근거다.
  - https://arxiv.org/abs/2604.10690

**시사점**: plan의 방향(좌표 JSON + 미리 계산한 상대 벡터 + 술어)은 여러 근거와 맞는다. 하지만 "좌표 JSON이 최고"는 **확정된 사실이 아니다.** Jev 자체로 형식 비교를 해야 한다. 이 비교는 M1 절제 실험으로 이미 계획되어 있으므로 그대로 둔다.

### 2.3 인식 앞단 (이미지 → 물체 목록 + 3D 위치/자세), 2026-09 기준

| 모듈 | 무엇 | 확인한 속도/정확도 | 신뢰도 | 출처 |
|---|---|---|---|---|
| **SAM 3** (Meta, ICLR 2026, arXiv 2511.16719) | 텍스트 명사구나 예시 이미지로 **모든 인스턴스를 검출, 분할, 추적**(Promptable Concept Segmentation) | 이미지 1장에 물체 100개 이상일 때 **H200에서 30 ms**. 비디오는 물체 수에 비례해서 느려진다. **H200 1장으로 약 5개 물체까지 준실시간(30 FPS)**. 기존 시스템 대비 PCS 정확도 약 2배 | **HIGH** | https://openreview.net/forum?id=r35clVtGzw , https://ai.meta.com/research/publications/sam-3-segment-anything-with-concepts/ , https://docs.ultralytics.com/models/sam-3 |
| **SAM 3.1** (Meta, 2026-03-27) | SAM 3 체크포인트에 Object Multiplex(여러 물체를 묶어서 공동 처리) 추가 | **H100에서 물체 128개 기준 약 7배 빨라짐**(Meta 발표) | HIGH(Meta 공식 블로그, 논문 심사 여부 미확인) | https://ai.meta.com/blog/segment-anything-model-3/ |
| EfficientSAM3 / SAM3-LiteText | SAM3 지식 증류 경량판 | 수치 미확인. LiteText는 ICMR 2026 채택 | MEDIUM-LOW(개인 저장소) | https://github.com/SimonZeng7108/efficientsam3 (검색 스니펫만 봄) |
| **YOLOE** (Tsinghua THU-MIG, ICCV 2025) | 텍스트, 시각, 프롬프트 없음 방식을 모두 지원하는 실시간 개방어휘 검출 + 분할 | "closed-set YOLO 대비 추론 오버헤드 0". 구체적 FPS/AP는 **이번 세션에서 미확인** | HIGH(ICCV) | https://openaccess.thecvf.com/content/ICCV2025/html/Wang_YOLOE_Real-Time_Seeing_Anything_ICCV_2025_paper.html |
| Grounding DINO 1.5 Edge (IDEA) | 개방어휘 검출 경량판 | TensorRT **75.2 FPS**(A100), LVIS-minival zero-shot 36.2 AP, Orin NX에서 10 FPS 이상 | MEDIUM(arXiv 기술 보고서). **1.5 Pro는 API 전용이고 가중치 공개 계획 없음.** Edge 가중치 공개 여부는 미확인 | https://arxiv.org/abs/2405.10300v2 , https://github.com/IDEA-Research/Grounding-DINO-1.5-API/issues/24 |
| DINO-X Edge (IDEA) | 개방세계 검출 | Orin NX에서 20.1 FPS(Grounding DINO 1.6 Edge의 15.1 FPS 대비) | MEDIUM(API 중심) | https://arxiv.org/pdf/2411.14347 |
| **FoundationPose** (NVIDIA, CVPR 2024 Highlight) | 처음 보는 물체의 6D 자세 추정과 추적(CAD나 참조 이미지 몇 장 필요) | 추정은 물체당 약 1.3 s, **추적은 약 32 Hz**(RTX 3090). 공식 문서: 추적은 **20~50 Hz로 돌려야 하고 약 5 Hz에서는 크게 나빠진다**. 2024-03 BOP 1위 | **HIGH** | https://arxiv.org/html/2312.08344v2 , https://github.com/NVlabs/FoundationPose |
| **Any6D** (KAIST + NVIDIA, CVPR 2025) | **RGB-D 앵커 이미지 1장**으로 처음 보는 물체의 6D 자세와 크기 추정 | 속도는 미확인 | HIGH | https://openaccess.thecvf.com/content/CVPR2025/html/Lee_Any6D_Model-free_6D_Pose_Estimation_of_Novel_Objects_CVPR_2025_paper.html |
| BOP 2024 결과 | 처음 보는 물체 6D 로컬라이제이션 | FreeZeV2.1이 가장 정확하다. Co-op은 **이미지당 0.8 s**. 보고서 결론은 "실시간 응용에는 더 빨라져야 한다". BOP 2025 상세 결과는 미확인 | HIGH(공식 챌린지 보고서) | https://arxiv.org/abs/2504.02812 |

**시사점**
- 개방어휘 **검출과 분할 + 깊이 역투영(3D 중심점)**은 SAM 3/3.1 수준이면 Jev 호출 주기(수 Hz)보다 충분히 빠르다(데이터센터 GPU 기준). 우리 GPU에서의 지연은 미확인이다.
- **6D 자세 추정(초기화)은 여전히 초 단위다.** "초기화 1회 + 고속 추적"으로 나눠야 한다. FoundationPose 추적은 5 Hz 수준에서 나빠지므로, Jev 주기와 따로 **독립된 고속 루프**로 돌려야 한다.
- 매 프레임 전체 자세 추정을 가정한 설계는 위험하다.

---

## 3) 반대 증거와 위험

1. **"변화분만 주면 효율적"의 근거가 사라졌다**(2604.01535를 잘못 인용). 비슷한 연구인 2604.10690은 "LLM이 순차 질의 사이에 공간 지식을 누적하지 못한다"고 보고했다. 그렇다면 diff만 주고 누적 상태를 Jev가 머릿속에서 재구성하길 기대하는 것은 **위험할 수 있다**(추론이며 직접 검증되지 않았다). diff는 "전체 상태 + 변화 요약"을 함께 주는 방식과 비교하는 실험 변수로 두는 것이 안전하다.
2. **강한 모델에게 과도한 압축은 손해**다(2604.01535). Astra 쪽에는 풍부한 입력을 주고, Jev의 능력에 맞는 압축 수준은 실험으로 정해야 한다.
3. **형식 민감도가 크다**(2411.10541, 2604.10690). 한 형식에서 얻은 결과가 다른 모델(Jev)로 옮겨간다는 보장이 없다.
4. **텍스트 전용 LLM은 전역 공간 일관성과 에이전트 기준 좌표계에 약하다**(GSU, SiT-Bench). 상대 벡터와 술어를 미리 계산하는 plan의 방향이 이 약점을 피하는 설계다. 이 방향은 근거와 맞는다.
5. **plan의 좌표 형식 근거(2502.16690)는 약하다.** 2D 격자, 단독 저자, 2급 venue다. 더 강한 근거(BALROG, SiT-Bench)로 바꾸거나 보강해야 한다.
6. **B2FF 이정표는 시각적이다.** 텍스트 이정표로 옮겨도 효과가 유지된다는 근거는 없다.
7. **ReKep은 코드 비용 함수 + 최적화기다.** Jev의 객관식 출력으로는 바로 쓸 수 없다. M2에서 "ReKep식 관계 제약"을 쓰려면 제약을 **평가 가능한 술어(참/거짓)**로 바꾸거나, 별도 최적화기를 두어야 한다.
8. **기간 규칙**: RoboPrompt, ReKep, REFLECT, Socratic Models, FoundationPose는 1.5년 기준을 벗어난다. 기초 문헌이나 도구로는 괜찮다. 하지만 "최신 근거"로 내세우면 안 된다.
9. **인식 오류의 전파**: 텍스트 상태는 인식기가 놓친 물체나 잘못 잰 자세를 그대로 Jev에 넘긴다. RoboPrompt는 자세 추정 오류에 강건하다고 보고했다. 하지만 그 결과는 키프레임 방식에서 나온 것이다.

---

## 4) 이 모듈에 장착할 모듈 후보 순위

### 4.1 M1 인식 앞단 (이미지 → 물체 JSON)
1. **SAM 3 / SAM 3.1** (HIGH: ICLR 2026, Meta). 텍스트 프롬프트 하나로 검출, 분할, 추적이 끝나고 물체 ID가 유지된다. 깊이와 결합하면 3D 중심점과 크기를 얻는다. 개방어휘라 새 물체와 새 환경에 대응할 수 있어서 일반화 메시지와 맞는다. 위험: 비디오 지연이 물체 수에 비례한다. 수치는 H200/H100 기준이다.
2. **FoundationPose** (HIGH: CVPR 2024 Highlight, NVIDIA). 자세(회전)가 필요한 작업(끼우기, 방향 맞추기)용이다. 초기화는 약 1.3 s이고 추적은 약 32 Hz다. 반드시 고속 추적 루프로 따로 돌린다. CAD나 참조 이미지가 없으면 **Any6D**(HIGH: CVPR 2025, RGB-D 앵커 1장)를 대안으로 쓴다.
3. **YOLOE** (HIGH: ICCV 2025). SAM 3가 우리 하드웨어에서 너무 느리면 쓰는 실시간 대안이다. 속도와 정확도 수치는 다음 조사에서 확인해야 한다.
4. Grounding DINO 1.5/1.6 Edge, DINO-X (MEDIUM). 수치는 좋다. 하지만 Pro는 API 전용이고, 로컬에서 쓸 수 있는지(가중치 공개)가 불확실하다. 실시간 루프에는 추천하지 않는다.
- 추천하지 않음: EfficientSAM3(개인 저장소, 수치 미확인). 신뢰도가 LOW~MEDIUM이다.

### 4.2 M1 상태 표현 형식
1. **객체 중심 JSON(좌표) + 미리 계산한 상대 벡터 + 참/거짓 술어.** 근거: BALROG(HIGH, 텍스트 결정 > 이미지 결정), SiT-Bench(HIGH~MEDIUM, 좌표를 담은 텍스트로 조작 과제 평가), RoboPrompt(HIGH, 자세 텍스트만으로 행동 예측), GSU(MEDIUM, 에이전트 기준 좌표계 약점 → 미리 계산할 필요), 2504.06661(MEDIUM, 술어 장면 그래프). 형식 자체(JSON, YAML, 표)는 **Jev로 실험해서 정한다.**
2. **도메인 술어로 제한한 장면 그래프**(2504.06661). 물체 간 관계가 많은 장면이나 Astra 계획 단계에 쓴다.
3. **diff 전용**: 근거 없음. 순위에서 빼고 절제 실험 변수로만 둔다.

### 4.3 M2 하위 목표 명세 형식 (Astra → Jev)
1. **술어 집합(완료 조건) + 대상 물체 ID.** 가장 단순하고, Jev의 예/아니오 판정과 바로 이어진다. 2504.06661의 "도메인 술어 → PDDL" 매핑이 뒷받침한다.
2. **키포인트 관계 제약**(ReKep, HIGH). 표현력이 높지만 코드 비용 함수 + 최적화기가 필요하다. Jev에 넘길 때는 "제약 만족 여부" 술어로 바꿔서 쓰는 방식을 검토한다.
3. **이정표 상태**(B2FF 개념, MEDIUM-LOW). 개념만 빌린다. 텍스트 이정표의 효과는 검증되지 않았다.
- 코드 기반 명세(Code as Policies 등)와 기타 계층 구조 사례는 이번 세션에서 검증하지 못해 순위에 넣지 않았다(5절).

---

## 5) 확인 못 한 것

검색 예산이 떨어져서 **이번 세션에서 전혀 검증하지 못한** 항목들이다. 다음 조사에서 우선 확인해야 한다. 이름만 적고 수치나 주장은 적지 않는다.
- 3D 장면 그래프: ConceptGraphs, HOV-SG, SayPlan, MomaGraph(arXiv 2512.16909, 존재만 검색 결과에서 봄), "LLM Meets Scene Graph"(ACL 2025, 존재만 봄)
- Set-of-Mark 시각 프롬프팅과 그것을 조작에 쓴 방법들(MOKA 등)
- 하위 목표를 코드나 제약으로 명세하는 계층 방법: Code as Policies, VoxPoser, OmniManip, Code-as-Monitor, Gemini Robotics-ER 계열의 점/JSON 출력
- 점유 격자(occupancy grid) 텍스트 표현이 조작에서 어떤 효과를 내는지
- 토큰 효율 형식 비교(JSON 대 압축 표기) 가운데 신뢰도 높은 연구
- SAM 2 지연, YOLOE와 YOLO-World의 구체적 FPS와 AP, SAM 3D Objects, 깊이 추정기(FoundationStereo 등), BOP 2025 결과
- REFLECT의 학회(CoRL 2023으로 알려짐), 2504.06661의 구체적 수치
- 각 항목의 인용 수, HF 업보트, GitHub 스타(신뢰도 규칙의 보조 지표)
- jev-drone의 15 Hz 비전 → 장면 변환 구성(plan 1절). 출처 미확인
