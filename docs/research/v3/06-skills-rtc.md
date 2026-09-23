# v3-06: M6 스킬 결합 상위 5개 확정 + M4/M5 LLM 쪽 보강

작성: 2026-09-23 20:0x UTC (v3 초안 조사, 에이전트 06). 스타 측정 시각: **2026-09-23 19:55–20:01 UTC** (GitHub API `stargazers_count`, 일부는 검색 API 결과의 같은 필드).

---

## 1. 조사 방법과 한계

- WebSearch **6회** 사용(한도 15). 나머지는 arXiv 원문(abs/html) curl, GitHub REST API(비인증 60회, 소진함), GitHub 검색 API, raw README, Semantic Scholar batch API로 했다.
- 원문 본문(HTML)을 직접 읽고 해당 절을 뽑아 확인한 논문: 11편(PhyAgentOS, Zetta, Harness VLA, CaP-X, ROSClaw, Show-Harness, TypeGo, Event-triggered, Speculative Actions, Whisper-Streaming, Spec-VLA). 초록만 확인: 약 30편.
- 후보 수집 경로: (a) arXiv API 검색 9개 질의(code-as-policies, skill library, agentic robot framework, MCP robot, coding agent robot, tool calling manipulation, skill composition 등, 2025-09-23~2026-09-30), (b) GitHub 검색 API 13개 질의(created>2025-09, 스타순), (c) 큐레이션 목록 4개(visitworld123/Awesome-Robot-Use-Agent, kkakkkka/awesome-code-as-x, showlab/Awesome-Multimodal-Embodied-Agent, lysandre001/awesome-code-as-policy)에서 저장소-논문 짝 추출.
- 한계
  - arXiv API가 조사 후반에 429(요청 과다)로 막혀 "OpenClaw", "harness robot" 질의는 arXiv에서 못 돌렸다. 대신 GitHub 검색과 큐레이션 목록으로 메웠다.
  - GitHub REST 한도가 끝나 TypeGo 등 일부 저장소 스타는 못 쟀다.
  - GitHub 검색은 저장소 설명에 검색어가 있어야 걸린다. 설명이 엉뚱한 고스타 저장소를 놓쳤을 수 있다.
  - 스타는 하루에도 바뀐다. 위 측정 시각 기준이다.

---

## 2. 검증 표

### 2.1 M6 후보: 기간(arXiv 첫 공개 ≥ 2025-09-23) 안, 공식 저장소가 있는 것 (스타순)

| 항목 | 확인 수준 | 스타 / 저장소 생성일 / arXiv 첫 공개 / 학회 / 인용(S2) · 비고 | 출처 |
|---|---|---|---|
| **PhyAgentOS** (2607.16636) | ORIGINAL-CONFIRMED | **2,481★**, 포크 119 / 저장소 2026-03-12 / arXiv 2026-07-18 / 학회 미확인(tech report v0.1.6) / 인용 4. 소속: X-Era Lab, 중산대 HCP Lab, Peng Cheng Lab. 논문의 링크 `github.com/PhyAgentOS/PhyAgentOS`는 `PhyAgentOS-core`로 301 리다이렉트된다(공식 확인). **저장소가 논문보다 4개월 먼저 생겨서 스타가 논문만의 반응은 아니다.** | https://arxiv.org/abs/2607.16636 , https://github.com/PhyAgentOS/PhyAgentOS-core |
| **Zetta** (2608.16590) | ORIGINAL-CONFIRMED | **1,252★** (검색 API, 20:00 UTC) / 저장소 2026-08-18 / arXiv 2026-08-17 / 학회 미확인 / 인용 미조회. 칭화대 AIR(Yunxin Liu, Ting Cao), Z-Trans AI. README에 arXiv 인용. LIBERO-Pro 90.8%, RoboCasa 93.6%("현재 rollout 예산 기준" 단서 있음), 추론 11.1배 가속. **기반 정책은 고정(frozen) VLA다.** | https://arxiv.org/abs/2608.16590 , https://github.com/air-embodied-brain/Zetta-Embodiment |
| **Harness VLA** (2607.08448), 저장소 RPent | ORIGINAL-CONFIRMED | **962★**, 포크 100 / 저장소 2026-07-07 / arXiv 2026-07-09 / 학회 미확인 / 인용 23. 칭화대, Infinigence AI, Purdue 등(RLinf 팀). 초록에 코드 링크. **저장소 이름이 "RPent: Agentic Infrastructure for the Physical World"라서 논문보다 넓은 인프라다. 스타 일부는 RLinf 조직의 영향으로 보인다(추정).** LIBERO-Pro +38.6%p, RoboCasa365 +25.4%p(가장 강한 관련 기준 방법 대비), RoboTwin C2R 58.4%. 역시 frozen VLA를 기본 도구로 쓴다. | https://arxiv.org/abs/2607.08448 , https://github.com/RLinf/RPent |
| **CaP-X** (2603.22435) | ORIGINAL-CONFIRMED | **819★**, 포크 123 / 저장소 2026-03-25 / arXiv 2026-03-23 / **ICML 2026** (저장소 제목, v2 보고서에서 ICML 포스터 페이지 확인) / 인용 52. v2의 "약 800★(단일 출처)"를 **실측 819★로 정정**한다. | https://arxiv.org/abs/2603.22435 , https://github.com/capgym/cap-x |
| **ROSClaw** (2603.26997) | CONFIRMED(논문) / **저장소 연결은 추정** | **625★**, 포크 66 / 저장소 2026-02-15 / arXiv 2026-03-27 / 학회 미확인 / 인용 4. 논문 저자 소속에 PlaiPin Inc가 있고 저장소도 PlaiPin 소유다. 그러나 **논문 본문에서 이 저장소 링크를 찾지 못했고, README에도 논문 언급이 없다.** README는 "대규모 재구성 중"이라고 적혀 있다. 저장소는 메신저로 로봇을 부리는 해커톤 제품에서 시작했다. v2의 "168★"은 **틀렸다(실측 625★)**. | https://arxiv.org/abs/2603.26997 , https://github.com/PlaiPin/rosclaw |
| Show-Harness (2609.10522) | ORIGINAL-CONFIRMED | 451★ / 저장소 2026-09-07 / arXiv 2026-09-09 / 학회 미확인 / 인용 4. NUS Show Lab(Mike Shou). **6위지만 사용자 요구(잘게 엮기)에 가장 가깝다(3절).** | https://arxiv.org/abs/2609.10522 , https://github.com/showlab/Show-Harness |
| HoloAgent-0 (2606.23565) | ORIGINAL-CONFIRMED(초록) | 389★ / 저장소 2025-11-07 / arXiv 2026-06-22 / 인용 2. Horizon Robotics. 언어를 실행 가능한 스킬 그래프로 바꾸고 실행 감시 후 재계획. | https://arxiv.org/abs/2606.23565 , https://github.com/HorizonRobotics/HoloAgent |
| GPT-Policy (2609.19138) | CONFIRMED(초록) | 270★ / 2026-09-10 / arXiv 2026-09-16 / 인용 0. GPT-6 Astra가 로봇 도구 행동을 제안하고, 제약 제어기가 행동마다 검증, 실행, 결과 보고. **Astra 사용 기존 논문(비교 대상)** 후보. | https://arxiv.org/abs/2609.19138 , https://github.com/cheng-haha/GPT-Policy |
| EMERGE-Policy (2608.29896) | CONFIRMED(존재) | 231★ / 2026-08-28 / arXiv 2026-08-30 / 인용 0 | https://github.com/EMERGE-Policy/EMERGE-Policy |
| ENPIRE (2606.19980) | CONFIRMED | 221★ / 2026-07-22 / arXiv 2026-06-18 / **CoRL 2026**(arXiv 코멘트) / 인용 17. NVIDIA. 코딩 에이전트가 실제 로봇 정책을 개선(정책 학습 쪽, 스킬 결합과는 거리 있음). | https://arxiv.org/abs/2606.19980 , https://github.com/NVlabs/ENPIRE |
| ABot-Claw (2604.10096) | CONFIRMED | 213★ / 2026-03-27 / arXiv 2026-04-11 / 인용 6. 논문 본문에 저장소 링크 있음. | https://github.com/amap-cvlab/ABot-Claw |
| ASPIRE (2607.00272) | CONFIRMED | 208★ / 2026-07-08 / arXiv 2026-06-30 / 인용 21. v2의 "스타 미확인"을 채운다. | https://github.com/NVlabs/ASPIRE |
| ros-claw/rosclaw | UNCONFIRMED(어느 논문인지) | 205★ / 2026-03-16. 이름이 같은 2604.04664(통지대 쪽) 것인지 확인 못 했다. README에 arXiv 링크 없음. | https://github.com/ros-claw/rosclaw |
| Agent as Policy (2609.12541) | CONFIRMED | 14★ / 2026-09-15. 반응 매우 적음. | https://github.com/agent-as-policy-2026/agent-as-policy |
| VLCP, 2609.20822, 2609.26499, BLAZER(2510.08572), Guava(2606.18363), Maestro(2511.00917) | CONFIRMED(존재, 날짜) | 논문 본문/초록에서 공식 코드 저장소를 찾지 못했다(프로젝트 페이지만 있는 것 포함). 스타 순위에서 뺀다. Maestro는 arXiv 코멘트에 "대폭 수정 후 재제출 예정"이라고 적혀 있다. | 각 arXiv abs |

### 2.2 기간 밖이거나 논문이 없는 고스타 저장소 (순위에서 제외, 근거 기록)

| 항목 | 확인 수준 | 비고 | 출처 |
|---|---|---|---|
| dimensionalOS/dimos | CONFIRMED | 4,560★, 저장소 2024-10-19. README에 arXiv 논문 없음. **논문이 아니고 기간도 밖**이라 제외. | https://github.com/dimensionalOS/dimos |
| robotmcp/ros-mcp-server | CONFIRMED | 1,474★, 저장소 2025-04-11. 논문 없음, 기간 밖. v2의 "생성일 미확인"을 채운다. | https://github.com/robotmcp/ros-mcp-server |
| FlagOpen/RoboOS, RobotecAI/rai | v2에서 확인 | 2025-05 논문, 기간 밖. | v2 03-skills.md |
| Jev 로봇 제어 저장소들(STEERIX-home/robo-jev 3★, openroboto-ai/jev-robot-control 44★ 등) | CONFIRMED(존재) | 논문 아님, 반응 적음(LOW). **다만 "Jev로 로봇을 스텝마다 typed 결정으로 제어"하는 공개 시도가 이미 있다는 경쟁 상황 정보다.** jev-robot-control은 seed 하나로 Jev 1.13과 GPT-6 Astra(low)를 비교했다(성공률 아님). | https://github.com/openroboto-ai/jev-robot-control , https://github.com/STEERIX-home/robo-jev |

### 2.3 M4/M5 관련 항목

| 항목 | 확인 수준 | 정정/비고(신뢰도 근거) | 출처 |
|---|---|---|---|
| **πR²** (2607.26055) | ORIGINAL-CONFIRMED(초록) | "πR²: Reactive Real-time Flow Policies", Sungjae Park, Shubham Tulsiani(CMU), 2026-07-28. 코멘트는 "Preprint, Under Review". 빠른 채널(고유수용 감각, 매 tick 새로 들어옴)과 비동기로 갱신되는 느린 채널(비전-언어 특징)로 조건을 나눈다. GR00T-N1.7을 미세조정해 약 25Hz(A5000), 40ms마다 새 관측. **"최대" +23%(시뮬), +30%(실제), 가장 강한 기준 방법 대비.** 학습형이므로 Jev에는 발상만 가져온다. 인용 1. 신뢰도 MED(알려진 연구실, 심사 전). | https://arxiv.org/abs/2607.26055 |
| **Event-triggered** (2609.22587) | ORIGINAL-CONFIRMED(본문 해당 절) | TUM(Alois Knoll), MBZUAI, 2026-09-18. v2 내용이 맞다. 본문으로 추가 확인: 사건 추정기는 **LoRA로 미세조정한 π0.5의 시각 인코더 특징**으로 기준 장면(마지막 추론 때)과 현재 장면의 차이 점수를 낸다. 임계값은 정지 시연 점수 분포의 **90번째 백분위수(P90)**이고, **두 번 연속** 넘을 때만 사건으로 본다(순간 흔들림 억제). 사건이 없으면 가능한 가장 긴 간격을 유지한다. 평균 성공률 95%, 가장 강한 기준 방법보다 +55%p. 코드는 채택 후 공개. 인용 0. 신뢰도 MED. | https://arxiv.org/abs/2609.22587 , https://arxiv.org/html/2609.22587 |
| **Speculative Actions** (2510.04371) | ORIGINAL-CONFIRMED | Columbia(Kaffes, Peng 등), 2025-10-05, **ICLR 2026 포스터**(검색 결과의 iclr.cc 페이지). 빠른 모델이 다음 행동을 추측해 미리 병렬 실행하고, 느린 권위 모델(actor)의 답과 **일치할 때만 확정(commit)**, 불일치면 평소대로 진행. 손실 없음을 지키는 세 장치: (a) 의미 가드(상태 전이 동치 확인 후 확정), (b) 되돌릴 수 있는 추측만 허용, (c) 불일치 시 되돌림/보상 경로. **"최대" 55% 다음 행동 예측 정확도, "최대" 20% 지연 감소**(게임, 전자상거래, 웹 검색). 인용 17. 신뢰도 HIGH. | https://arxiv.org/abs/2510.04371 , https://iclr.cc/virtual/2026/poster/10009726 |
| **Spec-VLA** (2507.22424) | ORIGINAL-CONFIRMED | EMNLP 2025 main. VLA 행동 토큰에 speculative decoding을 적용할 때, 초안 토큰과 검증 토큰의 **행동 거리가 가까우면 수용(relaxed acceptance)**. 수용 길이 26–44% 증가, OpenVLA 대비 1.22–1.42배 가속, 성공률 유지. 신뢰도 HIGH(학회). | https://arxiv.org/abs/2507.22424 |
| **LocalAgreement / Whisper-Streaming** (2307.14743) | ORIGINAL-CONFIRMED | **기간 밖, 기초 문헌.** IJCNLP-AACL 2023 시스템 데모, 인용 68. "LocalAgreement-2 = 연속된 두 갱신 출력의 **가장 긴 공통 접두부(longest common prefix)**를 확정"하고, 이미 확정된 부분에 대한 뒤 갱신은 무시한다. IWSLT 2022 동시통역 과제 우승 시스템(CUNI-KIT)이 쓴 정책이다. 전체-시퀀스 모델이면 무엇이든 스트리밍으로 바꾸는 **학습 없는** 정책이다. 평균 지연은 청크 크기의 약 2배(두 번 합의를 기다리므로). | https://arxiv.org/abs/2307.14743 |
| TypeGo (2607.05482) | ORIGINAL-CONFIRMED | Yale(Lin Zhong), 2026-07-06, 학회 미확인, 인용 0, 저장소 스타 미확인(API 한도). **speculative skill streaming**: S1 streamer가 LLM 호출 한 번에 몇 스텝씩 크기 3짜리 bounded queue에 넣고, executor가 가장 오래된 것을 꺼낼 때마다 하나를 새로 채운다(생성과 실행이 겹침). 각 스텝은 **조건-스킬 분기 여러 개**(조건 = 관측 술어 또는 짧은 자연어)로 되어 있고, 실행 시점에 맞는 분기를 고른다. S0 반사층 100Hz(LLM이 오프라인으로 컴파일한 Python 조건/행동 함수, 반응 경로에 LLM 없음), S2/S3 0.5Hz, S1은 사건 구동. Go2 사족 로봇에서 스텝별 계획 대비 스텝당 지연 50%↓, 통짜 계획 대비 첫 행동까지 시간 73%↓. **예비 결과(prototype)**다. 신뢰도 MED-LOW(알려진 연구실이지만 반응 0, 작은 과제 모음). | https://arxiv.org/abs/2607.05482 |
| TimelyLLM (2412.18695) | SINGLE-SOURCE(검색 요약) | 로봇 계획 생성과 실행 사이 시간 여유를 이용한 분할 생성 스케줄링. **2024-12라 1.5년 기간 밖**이고 서빙 시스템 논문이다. 참고만. | https://arxiv.org/abs/2412.18695 |
| CISC (2502.06233) | SINGLE-SOURCE(검색 요약 + 공식 저장소 설명) | 모델 자신의 신뢰도로 가중한 다수결. ACL 2025 Findings. 필요한 추론 경로 수를 평균 40% 넘게 줄였다. **2025-02라 1.5년 기간 밖(한 달 차이).** 발상만 쓴다. | https://arxiv.org/abs/2502.06233 , https://github.com/taubenfeld/CISC |
| DeepConf (2508.15260) | ORIGINAL-CONFIRMED(초록) | Meta(Yuandong Tian 등), 2025-08-21, 인용 164. 모델 내부 신뢰도로 낮은 품질의 추론 경로를 걸러내는 학습 없는 방법. AIME 2025에서 "최대" 99.9%(DeepConf@512), 생성 토큰 "최대" 84.7% 절감. 신뢰도 HIGH(유명 연구실 + 높은 인용). | https://arxiv.org/abs/2508.15260 |
| Too Consistent to Detect (2505.17656) | ORIGINAL-CONFIRMED(초록) | EMNLP 2025 main. **반대 증거**: 같은 오답을 여러 샘플에서 반복하는 "자기 일관 오류"는 모델이 커져도 줄지 않거나 늘고, 기존 검출법 4종 모두 잘 못 잡는다. 다른 모델과 교차 검증하면 나아진다. | https://arxiv.org/abs/2505.17656 |
| Slow Brain, Fast Planner (2606.20458) | ORIGINAL-CONFIRMED(초록) | v2 내용 맞음. **저자에 Bolei Zhou(UCLA)가 있어 신뢰도를 MED로 유지하되 "알려진 연구실"로 근거를 보탠다.** VLM 1–3초/질의, 5–20Hz 제어, 학습 없는 융합층, ADE 30%↓(약 2,000개 실제 시나리오). | https://arxiv.org/abs/2606.20458 |

---

## 3. 새로 찾은 것과 모듈별 최고 후보

### 3.1 M6: 스타 기준 상위 5개 (확정안)

규칙 [사용자]: LLM+스킬 논문, arXiv 첫 공개 ≥ 2025-09-23, GitHub 스타순. 측정 2026-09-23 19:55–20:01 UTC.

| 순위 | 이름 (arXiv) | 스타 | 저장소 생성 | arXiv 첫 공개 | 학회 | 신뢰도 |
|---|---|---|---|---|---|---|
| 1 | PhyAgentOS (2607.16636) | 2,481 | 2026-03-12 | 2026-07-18 | 미확인 | MED (중산대 HCP Lab, 높은 스타, 인용 4) |
| 2 | Zetta (2608.16590) | 1,252 | 2026-08-18 | 2026-08-17 | 미확인 | MED (칭화 AIR, 높은 스타) |
| 3 | Harness VLA / RPent (2607.08448) | 962 | 2026-07-07 | 2026-07-09 | 미확인 | MED-HIGH (칭화, 인용 23, 스타) |
| 4 | CaP-X (2603.22435) | 819 | 2026-03-25 | 2026-03-23 | ICML 2026 | HIGH |
| 5 | ROSClaw (2603.26997) | 625 | 2026-02-15 | 2026-03-27 | 미확인 | LOW-MED (저장소 연결이 추정, 인용 4) |
| (6) | Show-Harness (2609.10522) | 451 | 2026-09-07 | 2026-09-09 | 미확인 | MED (NUS Show Lab, 공개 2주에 451★) |

주의
- 5위 ROSClaw는 "논문 공식 저장소"가 추정이다. **엄격하게 논문 링크로 확인된 것만 세면 5위는 Show-Harness(451★)다.** [결정 필요]
- 1위와 3위는 저장소가 논문보다 넓은 인프라다. 스타가 "논문 방법"에 대한 반응만은 아니다.
- 2위와 3위는 기반 실행기로 frozen VLA를 쓴다. "VLA는 일반화가 안 된다"는 핵심 메시지와 부딪힌다. **하네스 방법만 가져오고 VLA 부분은 우리 스킬로 바꾼다.**

### 3.2 다섯 개(+Show-Harness)의 결합 세밀도와 Jev typed 질문을 꽂을 자리

세밀도: 거침(스킬을 부르고 끝) → 중간(스킬 호출마다 결과 보고 후 다음 결정) → 촘촘함(제어 스텝마다 LLM 결정, 또는 LLM이 만든 코드가 제어 주기로 개입).

| 후보 | 결합 방식 (원문 확인) | 세밀도 | Jev typed 질문을 꽂을 자리 [제안] |
|---|---|---|---|
| PhyAgentOS | 스케줄링 단위가 행동이 아니라 **세션**이다. 계층 사이 상태를 Markdown+YAML 파일로 주고받는다(State-as-a-File). SessionVerifier가 증거 묶음으로 {성공, 실패, 재계획} 판정을 내린다. 검증된 결과를 교훈으로 저장해 재학습 없이 시행착오 고리를 닫는다. | 거침~중간 | (1) SessionVerifier의 3지선다 판정을 Jev Choice로 둔다. (2) 실행 전 preflight 호환성 확인을 yes/no 질문으로 둔다. (3) State-as-a-File은 텍스트라서 Jev 입력 형식과 잘 맞는다. 다만 카메라→텍스트 변환 방법은 사용자가 정한다. |
| Zetta | 시간 척도가 다른 세 고리. (a) **행동 주기 통제**: LLM이 만든 코드형 critic이 높은 주기로 감시하고 이탈 전조를 보면 복구를 제안한다(반응 경로에 LLM 없음). (b) 에피소드 단위 critic-복구 후보 제안. (c) 검증을 통과해야 스킬을 갱신(같은 seed 짝 비교 게이트, held-out seed). 실행 중에는 "Role1"이 critic 제안을 수락/거부하는 유일한 상위 결정자다. | **촘촘함(코드로)** | Role1의 "이 복구 제안을 받아들일까?"를 Jev yes/no로 둔다. Jev는 빠르니 행동 주기에 가깝게 부를 수 있다. critic 코드는 Astra가 만들고 Jev가 매 주기 판정하는 구조가 된다. **M8(복구)와 M9(경험)에도 바로 쓰인다.** |
| Harness VLA | 계획기가 고정된 기본 도구 목록(move_to, rotate, set_gripper, vla_act)에서 구조화된 호출을 고른다. vla_act는 "재시도 가능한 국소 시도"다: 자세 잡기 → 실행 → 접촉 결과 확인 → 필요하면 다시 자세 잡기. 과제 기억(성공 호출 기록)과 전역 기억(성공 규칙, 실패 모델)으로 **각 기본 도구의 작동 범위를 배운다**. 도구 수를 늘리지 않는다. | 중간 | (1) "다음 호출은 어느 기본 도구인가", "다시 자세를 잡을까" 질문. (2) 전역 기억의 성공 규칙과 실패 모델을 Jev 입력의 짧은 텍스트 규칙으로 준다. **"스킬을 늘리지 말고 기존 스킬의 작동 범위를 기억으로 배운다"는 발상이 "기존 스킬 위에 Jev" 구조와 가장 잘 맞는다.** |
| CaP-X | 추상화 수준별 API 위에서 코드를 생성하고 여러 턴 실행 피드백을 받는다. VDM이 장면 변화를 텍스트로 설명한다. 스킬 자동 합성. (v2에서 확인) | 중간 | 생성 코드 안에 `jev_choice(질문, 보기)` 함수를 넣어 분기점마다 부른다(v2 제안 유지). |
| ROSClaw | OpenClaw 도구 호출 런타임과 ROS 2를 잇는다. 능력 자동 발견, 관측 정규화, **실행 전 행동 검증(안전 범위)**, 감사 기록. 모델마다 정책 밖 행동 제안률이 최대 4.8배 달랐다. | 거침(부르고 끝) | 실행 전 검증 자리의 yes/no 질문 하나. 사용자가 원하는 "잘게 엮기"의 참고로는 약하다. |
| (6) Show-Harness | 로봇 제어를 **이산 의미 행동 단위**(한 방향으로 한 스텝 이동, 또는 그리퍼 행동)로 바꾼다. 로봇별 해석기가 각 단위를 작고 제한된 동작으로 결정론적으로 바꾸고, **단위마다 실행 피드백**을 돌려준다. 멀리 있을 땐 여러 단위를 한 번에 내 열린 고리로 실행하고, 가까우면 스텝을 작게(Adaptive Step). 기본 VLM은 Gemini-3.1 Pro(medium effort). 모델들이 98% 넘게 유효한 행동 단위를 냈다. 오류는 계획이 아니라 **세밀한 잡기와 놓기**에 몰렸다. 사고량을 늘리면 성공률은 거의 그대로이고 벽시계 시간만 늘었다(GPT-5.6-sol에서 3.4배). | **가장 촘촘함(스텝마다 LLM)** | 우리 M3(촘촘한 객관식 행동)와 사실상 같은 설계다. **가장 가까운 선행 연구로 반드시 인용**해야 한다. 차이는 Jev의 확률 출력, 계단식 겹침 호출(M4), 스킬과의 결합(M6)에서 찾는다. |

**최고 후보 판단 [제안]**
- 스타 1위는 PhyAgentOS지만 결합이 가장 거칠다. **사용자 기준(잘게 엮기)으로는 Zetta(코드 critic의 행동 주기 통제 + 수락/거부 결정자)와 Show-Harness(스텝마다 이산 결정)가 가장 가깝다.**
- 가져올 것: Zetta의 "세 시간 척도 + 검증 게이트를 통과한 스킬만 갱신", Harness VLA의 "기존 스킬 작동 범위를 기억으로 배우기", CaP-X의 "코드 안의 typed 선택 함수", Show-Harness의 "단위마다 피드백과 적응 스텝 크기".

### 3.3 M4: LLM 쪽에서 가져올 학습 없는 "겹침 구간 자기 확인 후 갱신" 장치

사용자 요구 [사용자]: 1초에 여러 번 계단식으로 겹쳐 호출하고, **겹치는 구간의 움직임이 제대로 반영됐는지 스스로 확인하고 업데이트**한다.

아래 장치는 모두 학습 없이 블랙박스 LLM 호출에 붙일 수 있다.

1. **LocalAgreement식 확정** (Whisper-Streaming, 기간 밖 기초 문헌, 동시통역 분야의 표준 정책)
   - 연속된 두(또는 n) 호출이 같은 미래 구간에 대해 낸 선택 가운데 **앞에서부터 일치하는 부분만 확정**한다. 이미 확정된 스텝은 뒤 호출이 바꾸려 해도 무시한다(RTC의 "고정"과 같은 역할).
   - Jev에 옮기기: 약 333ms마다 부르고 각 호출이 k스텝 보기를 낸다 → 겹치는 스텝에서 호출 i와 i+1이 일치하면 확정한다.
2. **완화 수용(Spec-VLA, EMNLP 2025)**: 순서형 보기(크기 단계)는 "±1단계 이내면 일치"로 본다. 정확히 같아야만 확정하면 확정이 너무 늦어진다.
3. **추측-검증-확정-수리(Speculative Actions, ICLR 2026)**
   - 초안: 이전 호출의 꼬리 스텝(또는 코드 외삽). 검증자: 새 Jev 호출. 일치하면 확정, 어긋나면 수리 경로.
   - 규칙 두 개를 그대로 가져온다. 되돌릴 수 있는 작은 동작만 추측 실행한다. 어긋났을 때 되돌림/보상 동작이 미리 정해져 있어야 한다.
4. **신뢰도 가중 합의(CISC, DeepConf)**: 겹침 구간에서 여러 호출의 선택을 Jev 확률로 가중해 합의한다. 단, CLAUDE.md 제약대로 **Jev 확률 보정은 우리 데이터로 먼저 측정**해야 한다.
5. **조건부 분기 스텝(TypeGo)**: Jev가 "스텝 = (조건 → 스킬)" 분기를 내면, 실행 시점에 코드가 조건을 다시 평가한다. 응답이 늦게 와도 "그때의 상태"에 맞는 분기가 골라진다. 크기 3짜리 bounded queue와 "하나 꺼내면 하나 채우기" 규칙은 M4 스케줄러 기본값 후보다.
6. **사건 트리거 조기 호출(Event-triggered)**: M1 상태 diff가 정지 상태 분포의 P90을 **두 번 연속** 넘으면 정해진 주기를 기다리지 않고 바로 호출한다. 백분위수 임계값과 연속 2회 규칙은 학습 없이 옮겨진다(원문의 특징 추출기는 미세조정했으므로 그 부분은 옮기지 않는다).

**"제대로 반영됐는지"에는 두 가지 확인이 따로 필요하다 [제안]**
- (a) **호출 사이 합의**(위 1–4): 새 호출이 이전 호출과 같은 말을 하는가.
- (b) **실제 반영 확인**: 확정해서 실행한 스텝이 실제로 예상대로 움직였는가. VLASH식으로 예측한 상태와 측정 상태를 코드로 비교하고, 결과를 범주(예: 맞음 / 조금 모자람 / 어긋남)로 바꿔 다음 Jev 입력에 넣는다.
- (a)만으로는 부족하다. 같은 모델은 같은 오답을 반복할 수 있다(4절, Too Consistent to Detect). 그래서 (b)의 외부 기준(센서, 기하)이 반드시 필요하다.
- 갱신 규칙 초안
  - 합의하고 실제 반영도 맞음 → 확정 유지.
  - 불합의인데 새 호출의 확신이 낮음 → 이전 선택 유지(히스테리시스).
  - 불합의이고 새 호출의 확신이 높거나 실제 반영이 어긋남 → 미확정 구간 교체. 필요하면 수리 동작.
  - 불일치 크기 → M7/M8 이상 신호(v2 제안 유지).

### 3.4 M5
- LLM 쪽에서 새 스무딩 방법은 찾지 못했다(검색어: speculative decoding, streaming LLM, simultaneous translation, self-consistency).
- M5는 v2 결론(LiPo식 후처리, B-스플라인 제어점)을 유지한다.
- Show-Harness의 "Adaptive Step"(멀면 큰 스텝, 가까우면 작은 스텝)은 M3/M5 사이의 스텝 크기 규칙으로 참고할 수 있다.

---

## 4. 반대 증거와 위험

- **스타 순위와 사용자 기준이 어긋난다.** 스타 1위(PhyAgentOS)는 세션 단위의 거친 결합이다. 잘게 엮는 쪽(Show-Harness)은 6위다. "스타 상위"만 따르면 사용자가 원하는 결합 방식의 근거가 약해진다.
- **상위 2, 3위는 frozen VLA 위의 하네스다.** 인용할 때 "VLA 실행기"를 빼고 하네스 방법만 가져온다고 명시해야 한다.
- **스타가 논문 반응을 과대평가할 수 있다.** PhyAgentOS는 저장소가 논문보다 4개월 먼저 생겼다. RPent는 논문보다 넓은 인프라 저장소다. ROSClaw는 해커톤 제품 저장소다.
- **Show-Harness와 공개 Jev 로봇 저장소들이 우리 M3/M6 설계와 겹친다.** "스텝마다 LLM이 이산 행동을 고른다"는 것 자체는 새롭지 않다. 새로움은 Jev 확률 + 계단식 겹침 + 자기 검증 갱신, 그리고 스킬과의 결합에서 찾아야 한다.
- **Show-Harness 자체 결과에서도** 오류는 세밀한 잡기와 놓기에 몰렸다. 스텝 단위 LLM 결정의 약점이 접촉 구간이라는 뜻이고, 이 구간은 스킬에 맡기는 편이 낫다는 근거도 된다(Harness VLA가 접촉 구간만 vla_act에 맡긴 것과 같은 논리).
- **자기 일관 오류**(EMNLP 2025): 호출 사이 합의가 정답을 보장하지 않는다. 모델이 커질수록 이 오류가 줄지 않았다.
- **LocalAgreement는 지연을 늘린다.** 두 번 합의를 기다리므로 평균 지연이 청크 크기의 약 2배였다. 1초 3회 호출이면 확정까지 약 0.67초가 걸릴 수 있다(추정, 미측정). 완화 수용과 조건부 분기로 줄여야 한다.
- **Speculative Actions의 이득은 "최대" 20%**이고 다음 행동 예측 정확도도 "최대" 55%다. 물리 행동은 되돌리기 어려워서, 원문이 요구하는 "되돌릴 수 있는 추측만" 조건을 지키기 어렵다.
- TypeGo, Event-triggered, πR²는 모두 심사 전이고 인용 0–1이다.

---

## 5. plan.md에 반영할 제안

[사용자] (다시 적음)
- M6: 잘게 엮는다. 1년 이내, 스타 상위 논문을 참고한다.
- M4: 계단식 겹침 호출과 겹침 구간 자기 확인·갱신이 반드시 있어야 한다.

[제안]
1. M6 "스타 상위 5개"를 3.1절 표로 확정한다(측정 2026-09-23 20:00 UTC). ROSClaw 대신 Show-Harness를 넣을지는 [결정 필요].
2. M6 참고 우선순위는 스타순이 아니라 결합 세밀도로 둔다: Zetta(critic 수락/거부 결정자), Show-Harness(스텝 단위), Harness VLA(작동 범위 기억), CaP-X(코드 안 typed 선택 함수).
3. v2 수치를 정정한다: CaP-X 805→819★, ROSClaw 168→625★(저장소 연결은 추정), ASPIRE 미확인→208★.
4. M4에 "겹침 확인 = (a) 호출 사이 합의(LocalAgreement + 완화 수용) + (b) 실제 반영 확인(예측 상태 대 측정 상태)" 두 줄을 넣는다. 갱신 규칙은 3.3절 초안으로 한다.
5. M4 스케줄러 기본값 후보: TypeGo식 bounded queue(크기 3, 하나 꺼내면 하나 채우기) + Event-triggered식 조기 호출(P90, 연속 2회).
6. Show-Harness와 GPT-Policy를 비교 대상 목록("LLM+스킬 기존 논문", "Astra를 쓰는 기존 논문")에 추가하는 것을 검토한다.
7. 컨트리뷰션 문구: "스텝 단위 LLM 이산 행동 선택"은 선행 연구가 있다(Show-Harness). "Jev 확률 기반 계단식 겹침 호출 + 외부 기준을 쓰는 겹침 자기 확인 갱신"으로 좁힌다.

---

## 6. 확인 못 한 것

- TypeGo 저장소와 스타(GitHub API 한도 소진).
- ros-claw/rosclaw(205★)가 어느 ROSClaw 논문의 저장소인지.
- PlaiPin/rosclaw가 2603.26997의 공식 저장소인지(논문 본문에서 링크를 못 찾음).
- 상위 5개의 학회 채택 여부(CaP-X 제외). Semantic Scholar에는 모두 arXiv로만 나온다.
- arXiv API 429 때문에 "OpenClaw", "harness robot" 질의를 arXiv에서 못 돌렸다. GitHub 검색과 큐레이션 목록으로 대신했으므로 설명이 특이한 고스타 저장소를 놓쳤을 수 있다.
- 부재 주장: "LLM 호출을 실시간 제어 고리에서 겹쳐 보내고 겹침 구간을 자기 검증하는 2025–26 연구"로는 TypeGo(겹침 생성, 조건 분기)와 Slow Brain Fast Planner(stale 선택 융합) 말고 찾지 못했다. 사용한 검색어: "LLM real-time control loop overlapping requests speculative decoding streaming decisions robot", "self-consistency overlapping LLM outputs streaming incremental decision revision", "Speculative Actions", "TimelyLLM", "LLM simultaneous translation local agreement stable prefix". **없다고 단정하지 않는다.**
- Show-Harness 표 2의 수치별 성공률은 읽지 않았다(정성 결론과 98% 유효 단위만 확인).
- Zetta 수치(90.8%, 93.6%)의 비교 기준 방법과 "현재 rollout 예산"의 크기.
