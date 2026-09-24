# D19 학습 실행기(action expert, 사용자 결정 B안) 조사 (user-log 33·34)

저장 2026-09-24 06:30 UTC. 조사 에이전트 보고 전문(신뢰도 기준 user-log 14 적용). 메인 원문 재확인(D:/tools/audit_d19): RoboTwin 2.0 46.4·16.3·30.1%·"data without domain randomization" / InternData-A1 "18 skills"·"70 tasks"·"matches the official" / VIRAL "fails to correct its own mistakes" / π0.5 "GPT-4 ablation attains the worst" / LIBERO-Plus 95%·"below 30%"·"ignore language" / HiVLA 8.8%·"object-centric crops" — 모두 일치.


작성 2026-09-24. D:\qdd는 읽기만 했고, 받은 자료는 모두 `D:\tools\audit_d19\`에 있다(abs_*.html, hf_*.html, gh_*.html, html_*.txt 원문 텍스트, fly.html, rpent_readme.md). 날짜는 arXiv abs의 [v1]로 확인했고, 요청 사이 간격은 2초 이상이었다. HF 업보트와 GitHub 스타는 2026-09-24에 잰 값이다. 표기는 [접목]·[가정]·[제안]을 쓴다. 인용문에는 원문 조건을 함께 적었다.

## 0. 결론 요약
- **B안이 맞다.** 가장 강하게 받치는 근거는 두 개다.
  - RoboTwin 2.0(ICML 2026, 2,909★)이 C안(E2E) 위험을 수치로 보여준다. 깨끗한 시연으로만 학습한 정책은 무작위화 장면에서 크게 떨어진다. π0 성공률이 46.4%에서 16.3%로 떨어졌다(Easy → Hard, 단일 과제, 과제당 깨끗한 시연 50개).
  - 계층형·물체 중심 연구가 B안을 받친다. HiVLA는 물체 crop과 스킬 문장을 조건으로 받는 DiT 액션 익스퍼트를 쓰고, SlotFlow(CoRL 2026)는 물체 중심 조건으로 방해물에 강했다.
- **B안에서 학습하는 부분**: 조건부 flow-matching 행동 헤드 하나가 **모든 스킬의 모든 phase 실행**을 맡는다.
  - 입력: skill_id·phase_id, Jev `option_key`, 코드 목표 자세, **공유 M1 앞단이 만든 물체 crop·마스크**(손목 카메라 + 머리 카메라), 고유수용 상태.
  - 출력: 행동 청크, 그리고 보조 머리 셋(진행도, phase 끝 술어 예측, 샘플 분산).
- **흡수하는 모듈**
  - M5 L2 → RTC 인페인팅. RTC는 원래 학습형 flow 정책을 위한 방법이다.
  - M1의 "접촉 근처 세밀 기하" 일부.
- **코드로 남기는 모듈**: M1 술어 등록부(Jev 입력, M7 T1 하드 술어), M3 `expected_after`(실행기와 무관한 목표 술어), M4 규칙 전부, M5 L1·L3, M6 FSM·계약(entry/exit/`effect`/진단 필드), M7 FAIL 판정, Astra·Jev.
- **C2 위험이 가장 크다.** 학습 실행기는 standard → random에서 무너질 수 있다(RoboTwin 2.0, LIBERO-Plus). 공정성은 다음 네 가지로 지킨다.
  - 결정 층 비교 표 안에서는 실행기를 모든 조건에 똑같이 둔다.
  - 사전 등록한 주 표는 **스크립트 실행기 S**로 유지한다.
  - B 실행기 표는 병기한다.
  - **실행기 단독 낙폭**(오라클 결정 + 실행기)을 따로 잰다.
- **확인하지 못한 것**: "증류 정책이 원래 스크립트 스킬을 넘었다"는 강한 근거는 이번 조사에서 찾지 못했다. MimicGen은 "comparable"이고, 비교 대상은 사람 시연이다. 따라서 B의 이득은 "세밀 시각 보정 + 연속성 + 지연 흡수"에 거는 가설([가정])이다.

## 1. 근거와 신뢰도

| 출처 | 첫 공개(v1) | 학회·소속 | ★ / HF 업보트 | 등급 |
|---|---|---|---|---|
| π0.5 2504.16054 | 2025-04-22 | abs에 학회 표기 없음, Physical Intelligence | openpi 13,976 / 5 | HIGH |
| Knowledge Insulating 2505.23705 | 2025-05-29 | abs에 학회 표기 없음, PI | openpi 공유 / 1 | MED-HIGH |
| SmolVLA 2506.01844 | 2025-06-02 | Hugging Face | lerobot 27,741 / 166 | HIGH |
| RTC 2506.07339 | 2025-06-09 | NeurIPS 2025 (comments), PI | – / 0 | HIGH |
| RoboTwin 2.0 2506.18088 | 2025-06-22 | ICML 2026 (저장소 제목) | 2,909 / 19 | HIGH |
| InternData-A1 2511.16651 | 2025-11-20 | abs에 학회 표기 없음, Shanghai AI Lab 계열 | – / 5 | MED |
| Sim-and-Real Co-Training 2503.24361 | 2025-03-31 | abs에 학회 표기 없음, NVIDIA 등 | HF 미등재 | MED |
| Real2Render2Real 2505.09601 | 2025-05-14 | CoRL 2025 (저장소 제목) | 375 / 6 | MED-HIGH |
| VIRAL 2511.15200 | 2025-11-19 | NVIDIA·CMU·UC Berkeley·CUHK | HF 미등재 | MED |
| HiVLA 2604.14125 | 2026-04-15 | HKU·Shanghai AI Lab·CUHK | – / 20 | MED |
| SlotFlow 2609.24155 | 2026-09-21 | CoRL 2026 채택 (comments) | HF 미등재 | MED |
| 3D HAMSTER 2606.31329 | 2026-06-30 | IROS 2026 (comments) | 33 / 7 | MED |
| LIBERO-Plus 2510.13626 | 2025-10-15 | – | 459 / 48 | MED-HIGH |
| Gemini Robotics 1.5 2510.03342 | 2025-10-02 | Google DeepMind 기술 보고서 | HF 미등재 | MED-HIGH (초록만) |
| RPent Flywheel 문서 | – | Harness VLA 2607.08448의 저장소 | 983 | MED (문서, 수치 없음) |
| PEEK 2509.18282 | 2025-09-22 | UW·NVIDIA·USC·AI2 | 13 / 2 | MED-LOW, 보조만 |
| Latent Policy Barrier 2508.05941 | 2025-08-08 | Shuran Song 그룹 | – / 0 | MED-LOW, 보조만 |
| ASPIRE 2607.00272 / RATs 2606.19419 | 2026-06-30 / 2026-06-17 | – | –·25 / 129·49 | MED, 참고 |

기간 밖 기초 문헌(모두 HIGH):
- π0 2410.24164(2024-10-31)
- π0-FAST 2501.09747(2025-01-16)
- Hi Robot 2502.19417(2025-02-26, ICML 2025)
- **GR00T N1 2503.14734(2025-03-18로 기준일보다 5일 이르다, Isaac-GR00T 8,121★)**
- MimicGen 2310.17596(CoRL 2023, 647★)
- DexMimicGen 2410.24185(ICRA 2025)

## 2. 조사 결과

### Q1. 액션 익스퍼트 설계, 지연, 데이터 규모
- **π0.5**
  - "action expert with 300M parameters" 설정이다.
  - "At inference-time, the model first produces a high-level subtask ... and then, conditioned on this subtask, predicts the low-level actions via the action expert."
  - 이동 조작 데이터는 "about 400 hours"다. 첫 학습 단계 예시의 97.6%는 다른 출처에서 왔다.
- **Knowledge Insulating**: "naively including such experts significantly harms both training speed and knowledge transfer". 해법은 stop-gradient로 백본을 격리하는 것이다. → [접목] 사전학습 시각 인코더는 동결하거나 격리한다.
- **SmolVLA**
  - 전체 0.45B다. 전체 파라미터를 기준으로 "fewer than 30k episodes"로 학습했다.
  - 비동기 추론은 과제 완료 9.7 s 대 13.75 s("∼30% faster")였고, 60 s 안에 19회 대 9회를 해냈다. 조건은 실물 Pick-Place, 10회 × 큐브 위치 5곳이다.
  - 절제는 "VLM backbone is frozen, and only the action expert is trained".
- **GR00T N1(기간 밖)**
  - System 2 VLM은 10 Hz, System 1 DiT는 flow-matching이고 "120Hz"다.
  - "The inference time for sampling a chunk of 16 actions is 63.9ms on an L40 GPU using bf16."
- **RTC**: "applicable to any diffusion- or flow-based VLA out of the box with no re-training ... 'freezing' actions guaranteed to execute and 'inpainting' the rest." 학습형 flow 실행기를 쓰면 M5 L2를 원문 그대로 적용할 수 있다.
- **HiVLA**
  - DiT 액션 익스퍼트가 "global context, high-resolution object-centric crops and skill semantics"를 순서대로 cross-attention한다. 평균 83.3%였고, 시뮬에서 "37.7% over π0"였다.
  - "Ours (w/o Skill)"는 Hard 과제에서 "8.8% performance drop"이었다. 하위 과제 조건을 빼면 손해라는 뜻이다.

### Q2. 스크립트·계획기가 만든 GT로 학습하기
- **InternData-A1** (우리 안과 가장 비슷한 선례)
  - "composing scripted skill policies that compute and interpolate trajectories ... into complete behaviors"
  - "CuRobo ... validates them through physics simulation, and renders only successful trajectories"
  - 규모는 630k 궤적, 7,433시간, **18 skills, 70 tasks**다. π0와 같은 구조로 학습한 모델이 "matches the official π0 across 49 simulation tasks, 5 real-world tasks"였다.
  - "ten selected simulated tasks achieve direct sim-to-real transfer with an average success rate exceeding 50%."
- **GR00T N1(DexMimicGen)**: "Only successful demonstrations are retained ... 780,000 simulation trajectories ... in just 11 hours."
- **MimicGen(기간 밖)**: 사람 시연 "∼200"개로 "over 50K demonstrations across 18 tasks"를 만들었다. "agent performance on MimicGen data can be comparable to performance on an equal number of human demos."
- **RoboTwin 2.0**: 스크립트 전문가 코드로 만든 데이터다. 과제당 깨끗한 시연 50개로 단일 과제 학습 결과는 다음과 같다.

  | 정책 | Easy | Hard |
  |---|---|---|
  | Pi0 | 46.4 | 16.3 |
  | RDT | 34.5 | 13.7 |

  - "success rates drop by 20.8% (RDT) and 30.1% (Pi0) from clean to randomized settings"
  - "models fine-tuned with clean data show negligible improvements ... data without domain randomization does not help"
  - 실물에서는 "1,000 domain-randomized synthetic trajectories ... with just 10 real-world demonstrations"가 평균 +24.4%였고, 합성만 쓰면 보지 못한 배경에서 +21.0 / +20.5%였다.
- **VIRAL(실패 양상의 핵심)**: 특권 교사에서 RGB 학생으로 증류했다. "BC (α=1) yields fast loss reduction but produces a brittle policy that fails to correct its own mistakes ... Introducing student rollouts (α=0.5) ... substantially improves deployment success rate."
  - → [접목] 스크립트 스킬을 **DAgger 라벨러**로 쓰면 복구 데이터가 공짜로 생긴다. 단, 스킬이 임의 상태에서 다시 풀 수 있는 폐루프여야 한다.
- **Sim-and-Real Co-Training**: "simulation data can enhance real-world task performance by an average of 38%". **R2R2R**: "a single human demonstration can match ... 150 human teleoperation demonstrations".
- **RPent Flywheel(문서)**
  - "exporter includes all executed actions ... including scripted and VLA actions", "Failed episodes ... are not included in this supervised-training export"
  - 기록 필드에 "primitive IDs"가 들어간다. 도구 선례로만 쓰고, 성능 수치는 없다.

### Q3. 계층: 이산 의도 + 학습 실행기
- **Hi Robot(기간 밖)**: "The hierarchical approach outperforms the flat variant trained on the same data". **π0.5 절제**: "while there is a benefit to explicitly infer high-level subtasks, a significant portion of that benefit is already obtained simply by including subtask prediction data in the training mixture."
- **반대 증거(우리에게 중요)**
  - π0.5: "the zero-shot GPT-4 ablation attains the worst performance". 조건은 GPT-4에 과제 설명과 자주 쓰는 라벨 목록을 주고 상위 정책으로 쓴 것, 새 집 환경이다.
  - Hi Robot: "averages over 40% higher instruction accuracy than GPT-4o".
  - 즉, 학습 실행기 위에 학습하지 않은 API 상위 층을 올리면 약했다는 선례가 있다. 우리 typed 인터페이스(보기 목록 + 코드 목표)가 이 차이를 줄이는지는 실험으로 확인해야 한다.
- **3D HAMSTER**: 계층형이 "largest gains under appearance-altering shifts and unseen language, spatial, and visual conditions"였다. **SlotFlow**: "improved robustness under visual distractors and severe spatial perturbations".
- **"이산 선택 + 학습 연속 실행 > 순수 스크립트"를 같은 결정 층에서 잰 수치는 찾지 못했다.** E-AE가 이것을 잰다.

### Q4. 우리 주장에 대한 위험
- **LIBERO-Plus**
  - "performance dropping from 95% to below 30% under modest perturbations"
  - "models tend to ignore language instructions completely"
  - → 학습 실행기가 Jev 보기 조건을 **무시할 위험**이 있다. 보기 준수 시험이 필요하다(§4 E-AE-1).
- 스킬 GT로 학습한 익스퍼트는 스킬의 체계적 편향을 물려받는다. 성공한 것만 걸러도 편향은 남는다. RoboTwin 2.0 수치는 이것이 무작위화 낙폭으로 드러난다는 것을 보인다. 그러면 사용자 빨간 줄("VLA는 다른 환경에 가면 일반화가 안 된다")이 **우리 실행기에도** 적용될 수 있다.
- random은 시험 전용이다(EVAL §3.2-2). 그러므로 익스퍼트 학습 데이터도 standard 장면에서만 만든다. 일반적인 도메인 무작위화를 넣는다면 B3c 등 모든 학습 조건에 **같은 데이터**를 준다.

## 3. A/B/C 비교 (기록용)

| 안 | 장점 | 약점 | 판정 |
|---|---|---|---|
| A: 실행만, 상태·목표 조건(이미지 없음) | 인식 변화는 M1이 흡수, C2와 충돌 적음 | M1 상태 오차보다 작은 세밀 보정 불가 ("too coarse" 문제가 남음) | 비교 조건 |
| **B: 물체 중심 시각 + 조건부 실행, 결정 층은 밖** | HiVLA·SlotFlow·3D HAMSTER·Hi Robot 방향, RTC를 그대로 적용, (b)·M7용 머리 가능 | 시각 입력 때문에 random 낙폭 위험 → crop·마스크만 넣어 줄임 | **채택(사용자 결정)** |
| C: 전체 E2E(VLA) | π0.5식 대규모 공동학습 | 400시간급 데이터, LIBERO-Plus·RoboTwin 낙폭, 실행기가 곧 "과제 데이터로 미세조정한 학습 정책"이 되어 C2 비교가 성립하지 않음 | 참고 기준선만 |

## 4. B안 설계 [제안]

### 위치
M6 스킬 FSM의 "phase 실행" 자리에 들어간다. FSM 전이는 여전히 코드 술어 사건으로 일어난다. 익스퍼트는 전이를 결정하지 않는다.

### 입력
- `skill_id`·`phase_id` 임베딩
- 확정된 Jev `option_key` 임베딩(`dp.approach_dir`, `Q_fine_dir` 등)
- M3 코드 `target`(목표 자세 수치)
- 공유 M1 앞단이 만든 대상·관련 물체의 **crop + 마스크**(손목 카메라, 머리 카메라). 전체 장면 원본 이미지는 넣지 않는다([가정], PEEK·HiVLA 방향).
- 고유수용 상태(관절, 그리퍼 폭)
- 짧은 행동 이력

### 출력
- 행동 청크: 0.5 s 분량, 100 Hz로 보간 실행, 청크 생성은 약 10 Hz([가정]).
- 보조 머리 세 개:
  - (i) phase 진행도(0~1) → M7 `C_stag` 보조 소프트 채널
  - (ii) phase 끝 등록부 술어 예측 확률 → **보조 채널만**
  - (iii) flow 샘플 K개의 분산 → OOD 신호(E1식 conformal 보정)

### 다른 모듈과의 관계
- **M4 (b)**
  - `expected_after`는 지금처럼 코드 목표 술어로 둔다. 실행기와 무관하므로 S와 B 조건이 같다.
  - `ref(t)`는 확정된 행동 청크 자체로 둔다. 연속 잔차 = 측정값 − 청크.
- **M5**: L2 블렌딩을 RTC 인페인팅으로 바꾼다(E-M5 조건 S4-RTC). L1 시간 정렬과 L3 Ruckig 한계는 유지한다. 접촉 구간 규칙은 E-M5로 다시 확인한다.
- **M6 계약**: entry/exit/`effect`/진단 필드(최고 들어올림 높이, 최소 그리퍼 간격)는 **센서 측정으로 코드가 계산**하므로 그대로 유지된다.
- **M7**: T1 하드 술어와 FAIL은 코드만 낸다. 익스퍼트 머리는 소프트 채널로만 들어가고 FIPER식으로 보정한다.
- **폴백**: 다음 경우 해당 phase를 스크립트 스킬로 넘긴다.
  - 조건: 샘플 분산이 보정 문턱을 넘음, 또는 M4 (b)가 DEVIATE 2회 연속([가정]).
  - 넘기는 방식: 청크 경계에서 M5 관성화 2b로 이어 붙인다.
  - 폴백은 FAIL이 아니다. Astra 호출 규칙은 바뀌지 않는다. 폴백 비율은 모든 표에 기록한다.
- **Astra·M9**: 복구 보기(`reset_skill`, `resume_ckpt_k`)를 익스퍼트의 skill/phase 조건으로 그대로 실행한다. 재진입 상태는 DAgger 데이터가 덮는다.

### 데이터 파이프라인 (스킬 × phase × 보기마다)
1. standard 장면에서 스크립트 스킬을 실행하고, 성공 에피소드만 남긴다(GR00T, InternData, RPent 방식). phase 경계, skill/phase id, `option_key`, 코드 target을 함께 기록한다.
2. 섭동 주입: 물체 자세, 시작 자세, 실행 중 밀기.
3. **DAgger**: 익스퍼트 롤아웃 상태에서 스크립트 스킬이 라벨을 준다. α는 0.5에서 시작한다(VIRAL 값, [가정]).
4. 복구 구간은 섞어서만 쓴다. 복구 데이터만 따로 미세조정하면 망각 보고가 있다(RECALL, LOW라 참고만).

**커버리지 지표 [제안]**: (skill, phase, option_key) 칸 중에서 다음 두 조건을 모두 채운 칸의 비율이다.
- 성공 에피소드 ≥ N
- 오프라인 칸별 폐루프 성공률이 스크립트 대비 −2%p 이내

**크기·지연 [가정]**
- 동결 소형 시각 인코더 + 약 50~100M 규모 flow DiT, 청크당 ≤ 30 ms 목표.
- 참고치: π0.5 익스퍼트 300M, SmolVLA 전체 0.45B, GR00T 16스텝 63.9 ms(L40).

### 실험 [제안]
- **E-AE-0 (오프라인)**: 칸별 모방 오차와 커버리지. 데이터 규모 곡선은 스킬당 {100, 300, 1k, 3k} 에피소드([가정])이고, BC만 / +DAgger / +섭동 을 비교한다.
- **E-AE-1 보기 준수**: 같은 상태에서 `option_key`만 바꿨을 때 실행 궤적이 코드 기대 방향으로 바뀌는 비율이다. LIBERO-Plus "ignore language" 위험을 재는 시험이다.
- **E-AE-2 (주 실험)**: 결정 층을 우리 것(Jev+Astra)으로 고정하고, 실행기 {S 스크립트, A, B, B−폴백}을 standard와 random에서 비교한다. 지표는 성공률, 세밀 보정 오차(mm), 섭동 복구율, 폴백 비율, jerk다.
- **E-AE-3 실행기 단독 낙폭**: 오라클(특권) 결정 + 실행기 {S, A, B}로 standard → random 낙폭을 잰다.
- **E-AE-4 C2 불변성**: 결정 층 {LLM, 규칙, B3c} × 실행기 {S, B}에서 결정 층 순위·낙폭 차이의 부호가 실행기에 따라 바뀌는지 본다(상호작용 CI). 주 표는 S로 유지하고, B 표는 부호가 같을 때만 "실행기와 무관"이라고 쓴다.
- **E-AE-5**: M5 조건 S4(L2) 대 S4-RTC. B 실행기일 때만 비교한다.

### 새 [결정 필요]
- D9 해소 확인: 로컬 학습 모델 허용. 이번 사용자 결정이 사실상 허용이다.
- 도메인 무작위화 허용 여부: 허용하면 B3c 등 학습 조건 모두에 같은 데이터를 준다.
- 주 표 실행기를 S로 둘지 B로 둘지. 제안은 S다.

## 5. 제외 (LOW, 근거로 쓰지 않음)
- SkipVLA 2609.20648: 무학회, HF 미등재
- GR00T N1.7 Drifting 2609.18108: 단독 저자 기술 보고서
- DR-LfD 2607.25397: 무학회, HF·★ 없음. 스킬당 시연 20개라는 주장이 있다.
- ARCHITECT 2607.23784: 업보트 0
- BLAZER 2510.08572
- RECALL 2606.23617
- Scene2Demo, MinInter, RESample

## 6. 확인하지 못한 것
- 원문(abs·HTML)에서 확인하지 못한 학회 표기:
  - π0.5·KI·Sim-and-Real Co-Training·PEEK·LPB: abs에 학회 표기가 없다.
  - HAMSTER(ICLR 2025로 알고 있음): 기간 밖이라 쓰지 않았다.
- Gemini Robotics 1.5와 GraspVLA는 초록만 읽었다.
- 증류 정책 대 원래 스크립트 전문가의 직접 비교 수치는 찾지 못했다.
- HiVLA 83.3%가 어느 벤치마크의 평균인지, 코드 공개 여부는 HTML에서 확정하지 못했다.
