# 10. 평가 벤치마크와 핵심 주장 검증 ("VLA는 새 환경에 일반화 못 하고, LLM 기반은 한다")

작성: 2026-09-24, v3 조사 에이전트. 대상: `plan.md` §0 핵심 메시지, §3 평가, §4-6. v2/07 §5 "확인 못 한 것" 1~10번의 후속.

---

## 1. 조사 방법과 한계
- 원문 본문(arXiv HTML)을 직접 내려받아 표와 본문 문장을 뽑아 확인: **14편** (RoboDojo 평가 2609.24170, RoboDojo 벤치마크 2607.04434, LIBERO-Plus, LIBERO-PRO, COLOSSEUM, GenManip, VLABench, MolmoSpaces, LIBERO-RECOVER, EmbodiedBench, π0.5, DreamZero, Gemini Robotics 1.5, CaP-X).
- 초록·메타데이터만: RoboArena, Embodied Agent Interface, AGNOSTOS(v2/v3에서 본문 확인됨), Maestro 2511.00917, Decompose & Recompose 2605.01448, 2512.02902, 2607.26148.
- arXiv 검색 API(export.arxiv.org): id_list 1회(14편 제출일 일괄 확인) + 검색어 11개, 호출 간 6초. 429 없음.
- WebSearch **6회** (한도 12). WebFetch 2회(NVIDIA 뉴스룸, DeepMind GR2 블로그).
- 학회 확인: OpenReview 검색 API(검색은 됨, 개별 노트 조회는 403 챌린지로 막힘), CVF 오픈액세스 URL, arXiv comment 필드.
- GitHub 스타는 API가 아니라 저장소 HTML 페이지에서 읽었다(2026-09-24).
- 한계
  - π0.5 새 집 결과, MolmoSpaces 결과, Gemini Robotics 1.5 일반화 결과, LIBERO-PRO 주 결과는 **그림에만 있고 본문·표에 숫자가 없다**. 그림 수치를 읽어 적지 않았다.
  - RoboDojo 평가 논문은 Astra의 Gen 축을 standard/random으로 **나누어 보고하지 않는다**(두 조건의 평균만).
  - Gemini Robotics 2는 기술 보고서가 "안전 보고서"뿐이고 일반화 정량 결과를 찾지 못했다.

---

## 2. 검증 표

### 2-1. 벤치마크 10종

| 항목 | 확인 수준 | 정정/비고 (신뢰도 근거 포함) | 출처 URL |
|---|---|---|---|
| **LIBERO-Plus** 2510.13626 | ORIGINAL-CONFIRMED | v1 **2025-10-15**(창 안). NUS·푸단·통지대(Xipeng Qiu). **CVPR 2026 채택**(CVF 오픈액세스 논문 페이지 존재) → **HIGH**. 코드 459★. **섭동 축 7개**: 물체 배치, 카메라 시점, 로봇 초기 상태, 언어, 조명, 배경 텍스처, 센서 노이즈 → **환경 축이 중심**(조명·배경·카메라·노이즈). 평가 대상은 **VLA만**(OpenVLA, OpenVLA-OFT 3종, π0, π0-FAST, NORA, WorldVLA, UniVLA, RIPT-VLA). LLM 기반 방법은 없다. 표 1(원본 → 섭동): π0 94.2 → 카메라 15.8 / 로봇 6.6 / 조명 79.6 / 배경 78.5; OpenVLA 76.5 → 카메라 1.1 / 조명 4.4; OpenVLA-OFT 97.1 → 카메라 59.7 / 로봇 37.2 / 배경 92.4. 초록의 "95% → 30% 미만"은 **카메라·로봇 초기 상태 축의 최악 사례**이지 평균이 아니다. 조명·배경에서는 π0·OFT가 80~90%대를 유지한다. "언어 지시를 거의 무시한다"는 발견도 있다. | https://arxiv.org/abs/2510.13626 · https://openaccess.thecvf.com/content/CVPR2026/html/Fei_LIBERO-Plus_A_Progressive_Robustness_Benchmark_for_Visual-Language-Action_Models_CVPR_2026_paper.html · https://github.com/sylvestf/LIBERO-plus |
| **LIBERO-PRO** 2510.03827 | ORIGINAL-CONFIRMED (결과 수치는 그림에만) | v1 **2025-10-04**, v2 2026-05-25. 화중과기대·칭화대 등. 학회 **미확인**(OpenReview 검색에 노트는 있으나 조회 403). 코드 325★ → **MED**. 섭동 축 4개: 물체, 초기 위치, 지시(의미·구조), **환경(배경·조명·텍스처)**. 평가 대상 **OpenVLA, π0, π0.5만**. "0.0%로 붕괴"는 **위치·작업(task) 섭동**에서다. 환경 섭동은 본문 표현상 "모델마다 다르다(model-specific)"이고 붕괴가 아니다. 즉 **LIBERO-PRO의 0%는 환경 일반화 근거가 아니다.** | https://arxiv.org/abs/2510.03827 · https://github.com/Zxy-MLlab/LIBERO-PRO |
| **COLOSSEUM** 2402.08191 | ORIGINAL-CONFIRMED | 2024-02-13, **RSS 2024**(arXiv comment) → HIGH, 단 **기간 밖(기초 문헌)**. 155★. RLBench 20작업, **환경 섭동 14축**(물체·받침 물체 색/텍스처/크기, 테이블, 배경, 조명, 방해물, 물리 속성, 카메라). 평가: R3M-MLP, MVP-MLP, PerAct, RVT(각 100시연 학습) + **VoxPoser(LLM 코드, 학습 없음) zero-shot**. 성공률 30~50% 하락, 섭동 결합 시 ≥75% 하락. 실물 상관 R̄²=0.614. **최신 VLA·LLM 수치가 없다**(2024 기준 방법). | https://arxiv.org/abs/2402.08191 |
| **GenManip** 2506.10966 | ORIGINAL-CONFIRMED | 2025-06-12, **CVPR 2025**(OpenReview 검색 결과 venue 필드) → HIGH. 상해 AI Lab 계열. 200 시나리오, 10K 에셋. 축은 **공간·외형·상식·장기 계획 = 주로 작업/지시 축**. 모듈형(CoPA, MOKA × GPT-4o/4.5/Claude-3.7/Gemini-2.0-Flash/Qwen2.5-VL-72B) 최고 **CoPA+GPT-4.5 23.0%**(전체 SR). 종단형은 **GR-1, ACT뿐**이고 같은 200 시나리오가 아니라 따로 데이터 규모·분포 이동 절제 실험(그림)만 했다. 초록의 "모듈형이 더 잘 일반화"는 **같은 조건 정면 비교가 아니다**. | https://arxiv.org/abs/2506.10966 |
| **VLABench** 2412.18194 | ORIGINAL-CONFIRMED (학회 UNCONFIRMED) | 2024-12-24 → **기간 밖**. 푸단. 학회 미확인(OpenReview는 CoRR만). 100 작업 범주, 2,000+ 물체. 축은 **새 물체 범주·새 작업·상식·장기 추론 = 작업/의미 축**. VLA(OpenVLA, Octo, RDT-1B, 미세조정) 모두 매우 낮음(표 4, seen 물체 기본 작업 PS: RDT-1B 15.37, OpenVLA 11.74, Octo 1.34). 워크플로(VoxPoser, CoPA)는 기본 작업 PS 30~40, 복잡 작업에서 약함. 저자 결론: **"둘 다 어렵다"**. | https://arxiv.org/abs/2412.18194 |
| **RoboArena** 2506.18123 | CONFIRMED-MULTI (본문 미확인) | 2025-06-22, **CoRL 2025 Oral**(OpenReview venue) → HIGH. PI·스탠퍼드·버클리 등 32명. DROID Franka 실물, 7개 기관이 과제·환경을 자유 선택해 **쌍 비교 선호**로 순위. 7개 정책, 600+ 에피소드. **환경 축을 통제하지 않고 섞는다.** DROID 하드웨어가 있어야 참여 가능 → 우리 시스템 올리기는 비현실적. | https://arxiv.org/abs/2506.18123 |
| **MolmoSpaces** 2602.11337 | ORIGINAL-CONFIRMED (수치는 그림에만) | 2026-02-11. AI2(26명). 학회 미확인. 코드 allenai/molmospaces 477★ → **MED**. 실내 환경 **23만 개**, 물체 13만 개, MuJoCo/Isaac/ManiSkill 지원. 8작업 벤치. 평가: **π0, π0-FAST, π0.5(DROID 미세조정판, zero-shot, real-to-sim)**, CAP(Gemini-Robotics-ER-1.5가 접촉점 제공), 내비 정책. 심-실 상관 R=0.96. 발견: 조명은 거의 영향 없음, **손목 카메라 가림 시 π0.5 2%**, 3인칭 가림 20%, 초기 관절 자세·프롬프트 문구에 민감. **LLM 에이전트 기준은 없다.** GR00T N2가 1위라는 것은 NVIDIA 발표(아래). | https://arxiv.org/abs/2602.11337 · https://github.com/allenai/molmospaces |
| **EmbodiedBench** 2502.09560 | ORIGINAL-CONFIRMED | 2025-02-13(1.5년 창 **밖**, 2025-03-23 이전), **ICML 2025**(comment) → HIGH. MLLM 에이전트 24종만(VLA 없음). **EB-Manipulation은 VLMBench(RLBench 기반)** 확장이고 행동을 **위치 100칸·자세 120칸으로 이산화**하고 YOLO 박스·물체 자세를 추가 정보로 준다 → Jev 객관식 구조와 가장 비슷한 LLM 조작 벤치. 최고 GPT-4o **28.9%**. 환경 섭동 축은 없다. | https://arxiv.org/abs/2502.09560 |
| **Embodied Agent Interface** 2410.07166 | SINGLE-SOURCE (arXiv comment만) | 2024-10-09 → 기간 밖. **NeurIPS 2024 D&B Oral**(comment). BEHAVIOR·VirtualHome에서 LLM의 목표 해석·하위 목표 분해·행동 순서·전이 모델링을 **기호 수준**으로 잰다. VLA 없음, 환경 섭동 없음. 본문 미확인. 우리 평가에는 Astra 상위 계획의 오류 분류 틀로만 참고. | https://arxiv.org/abs/2410.07166 |
| **LIBERO-RECOVER** 2609.05178 | ORIGINAL-CONFIRMED | v1 **2026-09-04**. 대련이공대·Beta Infinity·NTU. 학회 없음, 공개 3주 → **LOW~MED**(추천은 보류, M9 참고용). 축은 환경이 아니라 **실패 후 복구** 4단계(L1 재시도, L2 행동 적응, L3 물체 상태 복구, L4 환경 복구), 1,000+ 시나리오(실제 실패 궤적에서 추출, Qwen3.5-27B로 실패 구간 지정). 평가: π0, π0-FAST, GR00T N1.5, OpenVLA-OFT, Wan2-Policy, Cosmos-Predict2-Policy — **VLA/WAM만, LLM 없음**. L4는 거의 0(LIBERO-100 L4 전원 0.0). 복구 데이터 학습은 표준 LIBERO 성공률로 전이 안 됨. 초기 프레임을 시간 맥락으로 주면 OFT 평균 20.8 → 26.8%. | https://arxiv.org/abs/2609.05178 |

### 2-2. 핵심 주장의 찬반 근거

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| **RoboDojo 평가(Astra)** 2609.24170 | ORIGINAL-CONFIRMED | 2026-09-21, 미심사. 42작업 전체, Astra·GPT-5.5는 작업당 50회(총 2,100), DeepSeek-Flash 10회. **effort medium, 에피소드당 호출 100회**. 도구는 `move_eef`/`give_up`만(집기 프리미티브 없음), **깊이·물체 자세 특권 정보 없음**. 단 LLM에게는 **RoboDojo wiki에서 뽑은 과제 레시피 문장**을 주었고 공개 정책은 이 문장 없이 돌렸다(저자 명시). 축별(Score/SR%, 표 1): **Astra 평균 28.97/22.48 · Gen 33.36/30.50 · Prec 12.65/4.00 · Long 21.45/8.25 · Memory 43.04/38.67 · Open 34.36/31.00.** 공개 1위 DM0.5: 24.90/19.34 · Gen 15.77/10.95 · Prec 24.82/16.75 · Long 33.70/19.50 · Mem 47.74/47.44 · Open 2.43/2.08. π0.5(표기 Pi-05, 9위): 11.41/6.91 · Gen 13.38/8.17 · Prec 12.40/5.50 · Long 23.54/14.67 · Mem 5.78/4.56 · Open 1.98/1.67. GPT-5.5 1.13/0.88. **Astra의 1위는 Gen·Open 두 축 덕이고 정밀·장기·기억은 DM0.5보다 낮다.** Gen 셀은 standard와 random 평균이며 Astra의 분리 수치는 **보고되지 않았다**. 실물 공식 프로토콜은 끝내지 못했다(안전 정지). | https://arxiv.org/abs/2609.24170 |
| **RoboDojo 벤치마크** 2607.04434 | ORIGINAL-CONFIRMED | 2026-07-05, 미심사, 44명(Tianxing Chen 외, RoboTwin 계열). 코드 **RoboDojo-Benchmark/RoboDojo 617★, MIT**. Isaac Sim, 양팔(ARX X5) 42 시뮬 + 18 실물 작업. **Gen 축 12작업 = 환경 축**: 에피소드 절반은 standard(학습과 같은 장면), 절반은 random(**배경·방해물 최대 25개·과제 물체·조명 변경**). **Open 축 8작업 = 작업 축**(학습에 없는 작업 지정, 스킬 재조합). VLA는 35작업 3,500궤적(20.66시간)으로 미세조정, Gen 작업 학습 데이터는 standard 장면에서만 모았고 무작위화된 보조 궤적 100개(과제 무관)만 추가. **표 3(Score, standard → random, 상대 하락)**: π0.5 20.92 → 5.82(**−72.2%**), Spatial Forcing 21.25 → 6.98(−67.2%, 최고 random), Hy-Embodied-0.5 21.98 → 1.57(−92.9%), X-VLA 17.92 → 3.04(−83.0%), π0 7.18 → 0.71(−90.1%), GR00T N1.7 3.97 → 0.35(−91.2%). 저자: "대부분의 정책이 standard 성능의 **대부분을 잃는다**". | https://arxiv.org/abs/2607.04434 · https://github.com/RoboDojo-Benchmark/RoboDojo |
| **π0.5 새 집 수치** 2504.16054 | ORIGINAL-CONFIRMED (정확 수치는 그림에만) | 2025-04-22(창 안). PI. **실제 집 3곳(부엌 3·침실 3), 두 종류 로봇, 과제당 10회**, 지표는 성공률이 아니라 **과제 진행률(rubric)**. 본문에는 "각 집에서 꾸준히 성공했다"는 서술뿐이고 **숫자는 그림 7 막대에만** 있다. 모의 집에서: 학습 장소를 3 → 104곳으로 늘리면 성능이 오르고, **104곳 모델이 테스트 집 데이터로 학습한 대조군과 비슷**하다(그림 8). **반대 방향 핵심 증거**: 상위 계획을 **zero-shot GPT-4로 바꾸면 모든 변형 중 최하위**(그림 13, "adapting VLMs with robot data의 중요성"). → "LLM이 일반화된다"는 주장에 대한 가장 직접적인 반례. 다만 GPT-4(2023)이고 보기 목록에서 고르는 방식. | https://arxiv.org/abs/2504.16054 |
| **Gemini Robotics 1.5** 2510.03342 | ORIGINAL-CONFIRMED (일반화 수치는 그림에만) | 2025-10-02. Google DeepMind. 일반화 4축: **Visual(배경·조명·방해물·텍스처) = 환경**, Instruction, Action, **Task(새 환경의 새 작업)**. GR 1.5가 이전 GR·GRoD보다 모든 축에서 높다(그림 3). **중요한 뉘앙스**: 최상위 시스템 자체가 **VLM 계획기(GR-ER 1.5) + VLA** 계층이다. 장기 과제 실패율: 계획기 Gemini 2.5 Flash **44.5%** 대 GR-ER 1.5 **22%**(표 1, 계획 실패 25.5% 대 9%). "기성 VLM을 VLA와 붙이는 것만으로는 부족하다". → **"VLA 대 LLM"이라는 이분법 자체가 최전선에서는 무너졌다.** | https://arxiv.org/abs/2510.03342 |
| **Gemini Robotics 2** (2026-07-30) | SINGLE-SOURCE (공식 블로그) | 기술 보고서는 **안전 보고서만** 확인. 블로그 수치는 과제별 성공률(예: Franka Duo 일반 집고 놓기 74.2%, 정밀 삽입 89.6%; Apollo 바닥 집기 45.7%)이고 **새 환경 대 학습 환경 비교는 없다**. 새 몸체 적응 "200개 미만 예시, 수 시간". 일반화 근거로는 약하다. | https://deepmind.google/blog/gemini-robotics-2-brings-whole-body-intelligence-to-robots/ |
| **GR00T N2 = DreamZero 기반** | CONFIRMED-MULTI | NVIDIA 뉴스룸(2026-03-16) 원문: "GR00T N2, a next-generation robot foundation model based on DreamZero research", "새 환경의 새 작업에서 선도 VLA보다 **두 배 이상** 자주 성공", "MolmoSpaces와 RoboArena 1위", 연말 출시. 1차 수치는 DreamZero 논문. | https://nvidianews.nvidia.com/news/nvidia-and-global-robotics-leaders-take-physical-ai-to-the-real-world |
| **DreamZero** 2602.15922 | ORIGINAL-CONFIRMED | 2026-02-17, NVIDIA(Jim Fan, Yuke Zhu 교신). "두 배"의 조건: AgiBot G1, **학습에 있던 작업을 처음 보는 환경·처음 보는 물체**에서(평가 장소가 데이터 수집지와 지리적으로 다름), 평균 **과제 진행률 62.2% 대 최고 사전학습 VLA 27.4%**(π0.5 / GR00T N1.6을 같은 데이터로 추가 학습). 초록 첫 문장: **"SOTA VLA는 의미 일반화는 뛰어나지만 새 환경에서 처음 보는 물리 동작으로 일반화하는 데 어려움을 겪는다"** → 사용자 주장을 업계 1위 회사가 문장으로 지지. 동시에 **해법이 WAM(학습 모델)이지 LLM이 아니다**. | https://arxiv.org/abs/2602.15922 |
| **CaP-X LIBERO-PRO 비교** 2603.22435 | ORIGINAL-CONFIRMED | ICML 2026(v3/02 확인). LIBERO-PRO 30작업, **위치(Pos)·작업(Task) 섭동만**(환경 섭동은 안 씀). 표 2: OpenVLA·π0 전부 0.00; **π0.5 Pos 0.17/0.38/0.20, Task 0.01/0.00/0.01**; **CaP-Agent0(학습 없음) Pos 0.22/0.26/0.12, Task 0.18/0.17/0.14**(object/goal/spatial). → 작업 섭동에서는 코드 에이전트가 확실히 덜 무너지지만 **절대 성공률 12~26%**, 위치 섭동에서는 π0.5와 비슷(goal·spatial은 π0.5가 더 높다). | https://arxiv.org/abs/2603.22435 |
| **Decompose & Recompose** 2605.01448 | ORIGINAL-CONFIRMED (comment) | v2/07은 LOW~MED로 제외했으나 **arXiv comment "Accepted by ICML 2026"** → **HIGH로 정정**. AGNOSTOS 전체 26.4%(v2 기록, 이번엔 본문 미재확인). AGNOSTOS의 LLM 기준 방법 2번째. | https://arxiv.org/abs/2605.01448 |
| VLA 일반화 반론: "VLA Models Are More Generalizable Than You Think" 2512.02902 | SINGLE-SOURCE (초록 + CVF 링크) | 2025-12-02, **CVPR 2026**(CVF 오픈액세스 PDF 존재). 시점 변화 붕괴는 공간 모델링 정렬 문제이고, **4K 파라미터 1-shot 적응으로 LIBERO 시점 정확도 48.5 → 87.1%**. → "VLA는 환경 변화에 근본적으로 약하다"가 아니라 **적은 적응으로 회복된다**는 반론. 우리 표에 "적응 예산"을 같이 적어야 하는 이유. | https://arxiv.org/abs/2512.02902 |
| 찬성 쪽(비조작): 2607.26148 | SINGLE-SOURCE (초록) | 2026-07, 미심사. VLN에서 범용 에이전트(opus-5, fable-5)가 RGB + 이산 행동만으로 zero-shot 70.7±3.5%~78%, "산업 규모 정책에 필적". 조작이 아니라 **내비게이션**이다. 참고용. | https://arxiv.org/abs/2607.26148 |

---

## 3. 새로 찾은 것과 벤치마크 추천

### 3-1. 각 벤치마크가 어느 축을 재나 (환경 대 작업)

| 벤치마크 | 환경 축 | 작업 축 | 최신 VLA 수치 | LLM/Astra 수치 | 시뮬·코드 | 신뢰도 |
|---|---|---|---|---|---|---|
| **RoboDojo-Sim** | **Gen(standard/random 분리)** | Open | 40개(π0.5 포함), 축별 공개 리더보드 | **Astra-as-policy(2609.24170)** | Isaac Sim, MIT, 617★ | MED(미심사, 대형 컨소시엄) |
| **LIBERO-Plus** | **조명·배경·카메라·노이즈·배치** | 언어만 | 10개 | TGL(Astra) 92.4%(v3/01) | MuJoCo(robosuite), 459★ | **HIGH(CVPR 2026)** |
| LIBERO-PRO | 환경(수치 그림) | 위치·작업 | OpenVLA·π0·π0.5 | CaP-X, Harness VLA/RPent(Astra low 92.63%), Zetta, ASPIRE | MuJoCo, 325★ | MED |
| AGNOSTOS | 없음 | **새 작업 23개** | π0, OpenVLA, RDT 등 | X-ICM, VoxPoser, D&R(ICML 2026) | RLBench(CoppeliaSim), X-ICM 70★ | HIGH(NeurIPS 2025) |
| COLOSSEUM | **14축** | 없음 | 없음(2024 모델) | VoxPoser | RLBench, 155★ | HIGH, 기간 밖 |
| MolmoSpaces | **새 집 23만 개** | 8작업 | π0/π0.5-DROID zero-shot | 없음 | MuJoCo/Isaac/ManiSkill, 477★ | MED |
| GenManip / VLABench | 약함 | 주 축 | 약한 VLA | CoPA·MOKA·VoxPoser | 공개 | HIGH / 미확인, VLABench는 기간 밖 |
| RoboArena | 섞임(통제 안 됨) | 섞임 | 7개 | 없음 | 실물 DROID만 | HIGH, 우리 사용 불가 |
| LIBERO-RECOVER | 없음(복구 축) | 없음 | 6개 | 없음 | LIBERO | LOW~MED |

### 3-2. "AGNOSTOS + RLBench 섭동"이 여전히 최선인가 → **아니다** [제안]
- AGNOSTOS는 **작업 축**만 잰다(v2에서도 지적). 사용자 주장은 **환경 축**이다.
- RLBench 섭동(COLOSSEUM)은 환경 축은 맞지만 **최신 VLA와 Astra 계열 수치가 전혀 없다**. 우리가 π0.5·Astra 기준 방법을 전부 새로 돌려야 하고, RLBench용 π0.5 미세조정도 직접 해야 한다.
- 2026-09 현재 더 나은 조합이 있다.
  1. **RoboDojo-Sim의 Gen 축(주 벤치마크)**: 환경 변화 전후(standard → random)를 **같은 작업 안에서** 분리해 재고, π0.5 등 40개 정책의 분리 수치가 이미 논문 표 3에 있으며, **Astra-as-policy 기준 결과까지 있다.** Open 축으로 새 작업도 함께 잰다. 코드 MIT.
  2. **LIBERO-Plus(보조, 심사된 벤치마크)**: CVPR 2026이라 신뢰도가 가장 높고, 환경 축이 세분되어 있으며 가볍다(MuJoCo). LLM+스킬·Astra 논문(TGL, CaP-X, Harness VLA, Zetta)이 모두 LIBERO 계열에 수치를 내서 **범주 5·6 기준 방법의 공개 수치가 가장 많은 곳**이다.
  3. **AGNOSTOS(선택)**: 새 작업 축과 X-ICM·D&R 비교가 필요할 때만. 환경 주장의 근거로는 쓰지 않는다.
  4. **MolmoSpaces(선택, "진짜 새 집")**: VLA도 zero-shot(π0.5-DROID, 미세조정 없음)이라 **양쪽 모두 해당 환경 데이터 0**인 가장 공정한 조건이다. 단 Franka 스킬 라이브러리를 새로 붙여야 하고 수치가 그림에만 있다.

### 3-3. 6개 기준 방법 범주 지원 여부

| 범주 [사용자] | RoboDojo Gen/Open | LIBERO-Plus/PRO | AGNOSTOS |
|---|---|---|---|
| 1. Astra만 | **공개 결과 있음**(2609.24170, medium, 100호출) + 우리 인터페이스로 재실행 | TGL·RPent Astra 결과(인터페이스가 다름) | 직접 구현 |
| 2. Jev만 | 직접 구현 | 직접 구현 | 직접 구현 |
| 3. VLA | **π0.5 포함 40개, Gen 분리 수치 공개** | 10개(Plus), π0.5(PRO) | π0, OpenVLA, RDT |
| 4. 룰베이스 | 직접 구현(양팔 스킬 필요) | 직접 구현 | 직접 구현 |
| 5. LLM+스킬 기존 논문 | **없음**(재실행 필요) | **CaP-X(ICML 2026), Harness VLA, Zetta** 수치 존재 | X-ICM, D&R(ICML 2026), VoxPoser |
| 6. Astra 쓰는 기존 논문 | **RoboDojo Astra 평가 자체** | TGL, RPent Astra판 | 없음 |

→ **한 벤치마크로 6범주를 다 채우는 곳은 없다.** RoboDojo(1·3·6)와 LIBERO-Plus/PRO(3·5·6)를 합치면 공개 수치로 1·3·5·6을 채우고 2·4는 자체 구현.

### 3-4. 우리 구조(Astra 상위 + Jev 텍스트 하위 + 스킬)에 붙일 때의 핵심 설계 조건 [제안]
- **정답 상태를 주면 환경 섭동이 무의미해진다.** 조명·배경·텍스처 섭동은 대부분 **인식**을 때린다. 시뮬레이터 정답 물체 자세를 텍스트로 넣으면 우리 쪽은 섭동에 자동 면역이 되고, 비교가 성립하지 않는다(X-ICM이 정답 좌표를 받는 문제와 같음). → 환경 축 평가는 **인식 추정 상태 조건에서만** 주장한다. 정답 상태 조건은 상한선 참고로만. (인식 앞단 방법은 사용자가 정한다.)
- RoboDojo는 **양팔** 작업이다. 스킬 라이브러리를 양팔용으로 만들어야 한다. 정밀(Prec) 축은 Astra 단독이 4.00%로 약하므로 스킬이 맡는 부분에서 이득을 보일 수 있는 자리다.
- RoboDojo의 Astra 결과는 **wiki 레시피 문장**을 받았다. 우리도 같은 문장을 쓰면 Astra 결과와 직접 비교 가능하지만, VLA와의 비교에는 "입력 정보가 다르다"는 단서를 똑같이 달아야 한다.
- Jev는 수치에 약하다(plan §1). EB-Manipulation처럼 **위치를 칸으로 이산화**하는 방식은 Jev 객관식과 맞지만, 칸 번호 비교는 Jev가 약한 수치 비교다 → 칸 선택은 코드, Jev는 "어느 물체/어느 스킬/진행 중인가" 판단에 한정하는 쪽이 안전하다.

---

## 4. 반대 증거와 위험
1. **"VLA는 새 환경 일반화가 안 된다"는 전칭으로는 틀렸다.**
   - π0.5는 처음 보는 실제 집 3곳에서 긴 작업을 수행했고, 104곳 학습 모델이 테스트 집 데이터로 학습한 모델과 비슷했다.
   - DreamZero/GR00T N2는 새 환경에서 기존 VLA의 두 배(62.2 대 27.4% 진행률).
   - 2512.02902(CVPR 2026): 시점 변화 붕괴는 4K 파라미터 1-shot 적응으로 48.5 → 87.1% 회복.
   - LIBERO-Plus 원문: 조명·배경 섭동에서는 π0·OFT가 80~90%대 유지. 붕괴는 카메라·로봇 초기 상태에서.
   - 다만 **"같은 과제 데이터로 미세조정한 공개 VLA는 장면 무작위화에서 성능 대부분을 잃는다"는 강하게 지지된다**(RoboDojo 표 3: 30개 정책 거의 전부 −65~−100%).
2. **"LLM 기반은 일반화된다"도 전칭으로는 틀렸다.**
   - π0.5 논문: zero-shot GPT-4 상위 계획이 **최하위**.
   - GR 1.5: 기성 Gemini 2.5 Flash 계획기 실패율 44.5%, 로봇 데이터로 맞춘 GR-ER 1.5는 22%.
   - LLM 쪽 절대 성공률은 낮다: RoboDojo Astra 22.48%, AGNOSTOS X-ICM 30.1%, GenManip CoPA 23.0%, CaP-X LIBERO-PRO 12~26%, EmbodiedBench EB-Manip 28.9%.
   - RoboDojo: 같은 LLM-as-policy 틀에서 GPT-5.5 0.88%. **"LLM"이 아니라 "Astra"가 된 것**이다. 모델 의존성이 매우 크다(2607.26148 VLN에서도 "모델 선택이 성능 변동을 지배").
3. **이분법 붕괴**: 최전선 VLA 시스템(π0.5 고수준 추론, GR 1.5 에이전트)은 이미 VLM 계획기 + VLA 계층이다. "VLA 대 LLM"보다 "로봇 데이터로 학습한 정책 대 학습 없는 API 모델 + 스킬"이 정확한 대립 구도다.
4. **비교 공정성**
   - RoboDojo의 VLA는 standard 장면 in-domain 데모로 학습됐다. random은 "학습 분포 밖"이지만 Astra에게는 standard도 random도 모두 처음이다. → **상대 하락폭 비교**가 공정하고, 절대 비교는 wiki 레시피 단서를 달아야 한다.
   - Astra의 Gen standard/random 분리 수치가 공개되지 않았다. 우리가 직접 돌려야 "LLM 쪽이 덜 무너진다"를 보일 수 있다(현재는 **증거 없음**).
   - frontier VLA(GR 2, GR00T N2)는 재현 불가. GR00T N2는 연말 출시 예정.
5. **벤치마크 자체 위험**: RoboDojo는 미심사(2개월). LIBERO 계열은 원본이 포화(LIBERO-RECOVER 서론: SOTA ≈100%)되어 Plus/PRO만 의미가 있다. LIBERO-PRO의 0% 붕괴는 위치·작업 섭동 결과라 환경 근거로 인용하면 틀린 인용이 된다.

---

## 5. plan.md에 반영할 제안

### [사용자] (변경 없음)
- 핵심 메시지: VLA는 일반화가 약하고 LLM 기반은 일반화된다.
- 비교 범주 6개: Astra만 / Jev만 / VLA / 룰베이스 / LLM+스킬 기존 논문 / Astra를 쓰는 기존 논문.

### [제안]
1. **주장 문구(권장안, 사용자 결정 필요)**
   > "같은 과제의 로봇 데이터로 미세조정한 VLA는 배경·조명·방해물·물체가 바뀌면 성능 대부분을 잃는다(RoboDojo: π0.5 −72%, 30개 정책 대부분 −65% 이상). 학습 없이 API 모델과 스킬로 짠 우리 시스템은 같은 변화에서 **상대 하락폭이 작다**."
   - "LLM은 일반화된다" 대신 **"하락폭(retention)"**으로 주장한다. 절대 성공률 우위는 주장하지 않는다(Astra도 20~30%대).
   - "VLA 전반"이 아니라 **"대상 과제 데이터로 미세조정한 공개 VLA"**로 범위를 좁힌다. π0.5 새 집, DreamZero, GR 1.5는 관련 연구에서 정면으로 인정한다.
2. **벤치마크 세트(plan §3 교체안)**
   - 주: **RoboDojo-Sim Gen 12작업(standard/random 분리 보고) + Open 8작업**. π0.5 수치는 논문 표 3 재사용, Astra-as-policy는 공개 결과 + 우리 인터페이스 재실행.
   - 보조: **LIBERO-Plus**(조명·배경·카메라 축, CVPR 2026) + **LIBERO-PRO**(CaP-X·Harness VLA·RPent Astra 수치와 비교).
   - AGNOSTOS는 "새 작업" 보조 결과로 강등(선택). COLOSSEUM(RLBench 섭동)은 최신 기준 수치가 없어 제외.
   - 선택: MolmoSpaces(양쪽 모두 zero-shot인 새 집 조건).
3. **조건**: 환경 축은 **인식 추정 상태 조건**에서만 주장. 정답 상태 조건은 상한선.
4. **지표 추가**: standard → random **상대 하락폭**(RoboDojo 표 3과 같은 식), **적응 예산**(데모 수, 개발 시드 수, 2512.02902의 1-shot 적응과 비교), 입력 정보 차이(wiki 레시피 여부) 표기.
5. **정정**: v2/07의 Decompose & Recompose "LOW~MED, 제외" → **ICML 2026 채택, AGNOSTOS LLM 기준 방법으로 포함 가능**. v2/07의 "LIBERO-Plus/PRO 채택 미확인" → **LIBERO-Plus는 CVPR 2026 확인**, LIBERO-PRO는 여전히 미확인.
6. M9(복구) 평가용으로 LIBERO-RECOVER 레벨 정의(L1~L4)를 참고하되 신뢰도가 낮으니 핵심 근거로는 쓰지 않는다.

---

## 6. 확인 못 한 것
1. **Astra의 RoboDojo Gen standard/random 분리 수치**(논문 미보고). 리더보드 사이트(robodojo-benchmark.com)는 JS라 읽지 않았다.
2. π0.5 새 집 과제별 진행률 숫자(그림 7), 모의 집 GPT-4 상위 계획 수치(그림 13). 블로그에도 숫자가 있는지 미확인.
3. Gemini Robotics 1.5 축별 수치(그림 3), Gemini Robotics 2의 일반화 정량 결과(찾지 못함).
4. LIBERO-PRO·VLABench·MolmoSpaces의 학회 채택(OpenReview 개별 조회가 403 챌린지로 막힘).
5. LIBERO-PRO 환경 섭동에서의 π0.5 수치(그림 7에만), TGL·Harness VLA·RPent 결과가 LIBERO-PRO/Plus의 **어느 섭동 축**인지(환경 축 포함 여부).
6. RoboDojo 벤치마크 논문의 소속 기관 전체(v3/01의 "HKU·칭화·버클리·프린스턴·MIT·PKU"는 Astra 평가 논문 기준).
7. Embodied Agent Interface 본문(comment만 확인).
8. "환경 변화에서 VLA 대 LLM 에이전트를 같은 조건으로 정면 비교한 2026 벤치마크"의 부재: 사용한 검색어 — arXiv `abs:"code-as-policy" AND VLA AND generalization`, `abs:"LLM as policy" OR "VLM as policy"`, `abs:benchmark AND modular AND end-to-end AND manipulation AND "unseen environments"`, `abs:AGNOSTOS`, `abs:"coding agents" AND manipulation AND VLA`, WebSearch 1회("2026 benchmark compare VLA policies versus VLM agent code-as-policy zero-shot unseen scenes..."). 찾은 가장 가까운 것은 RoboDojo+Astra 평가(Gen 축, 단 분리 수치 없음)와 CaP-X(LIBERO-PRO, 위치·작업 축만). **환경 축에서 둘을 같은 조건으로 분리 비교한 결과는 찾지 못했다(확신 MED)** → 이것이 우리 평가가 채울 빈칸이다.
