# M6 검증 보고서: 스킬과 LLM(Jev)을 잘게 엮기 (v2 감사)

작성일: 2026-09-23. 대상: `docs/plan.md`의 M6 절.

**조사 한계 (먼저 읽을 것)**
- arXiv, GitHub, 프로젝트 페이지는 직접 열지 못했다. 모든 확인은 WebSearch 검색 요약(snippet)만으로 했다.
- 이 모듈은 WebSearch를 26회 썼다. 그 뒤 세션 전체 검색 한도(200회)가 끝나 더 검색하지 못했다. 목표였던 40회 이상에 못 미친다. 그래서 **LLM/VLM 분야 조사(CREDIBILITY/“로봇에 답이 있다고 가정하지 말 것” 규칙)는 거의 하지 못했다.** 5절에 후속 검색 목록으로 남겼다.
- GitHub 스타 수는 검색엔진이 요약한 값이다. 측정 날짜를 알 수 없는 경우가 대부분이다. 모든 스타 수는 "근사치, 재확인 필요"로 본다.
- "1년 이내" 기준일은 2025-09-23이다.

---

## 1) 검증 표

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| **CaP-X** 존재, 제목, ID 2603.22435 | CONFIRMED-MULTI | 정확한 제목: "CaP-X: A Framework for Benchmarking and Improving Coding Agents for Robot Manipulation". arXiv 제출일 2026-03-23. 1년 창 안에 있다. 저자: Letian Fu, Justin Yu, Karim El-Refai, Ethan Kou, Haoru Xue, Huang Huang, Wenli Xiao, Li Fei-Fei, Guanya Shi, Jiajun Wu, S. Sastry, Yuke Zhu, Ken Goldberg, Jim Fan. MIT 라이선스. | https://arxiv.org/abs/2603.22435 , https://github.com/capgym/cap-x |
| CaP-X ICML 2026 채택 | CONFIRMED-MULTI | ICML 2026 가상 사이트에 포스터 페이지가 있다. GitHub 제목에도 "[ICML 2026]"이 붙어 있다. | https://icml.cc/virtual/2026/poster/66369 , https://github.com/capgym/cap-x |
| CaP-X 약 800★ | SINGLE-SOURCE | 검색 요약에 575, 660, 805 세 값이 나왔다. 805는 2026-09-17 날짜의 페이지에서 나왔다고 요약되어 있다. 세 값 모두 같은 검색엔진 요약 한 곳에서 나와 독립 출처가 아니다. "약 800★(2026-09 중순 기준 검색 요약)"으로 고쳐 쓴다. | https://github.com/capgym/cap-x (검색 요약) |
| CaP-X 기능: 여러 추상화 수준의 API, 여러 번의 실행 피드백, 실행 전후 이미지 비교, 새 스킬 자동 합성 | CONFIRMED-MULTI | 맞다. 세부 정정: CaP-Bench는 8단계(S1–S4 단일 턴, M1–M4 다중 턴)다. 12개 모델을 평가했다. CaP-Agent0는 학습 없이 쓰는 프레임워크로 세 요소가 있다: 다중 턴 visual differencing, 자동 합성 스킬 라이브러리, 병렬 앙상블 추론. **"실행 전후 이미지 비교"는 이미지 자체를 비교하는 것이 아니다.** VDM(visual differencing model)이 첫 장면과 매 턴의 변화를 **텍스트로 설명**한다. 이 외에 CaP-RL(GRPO로 코딩 에이전트를 강화학습)도 있고, sim2real 차이가 작다고 보고했다. | https://arxiv.org/html/2603.22435v1 , https://github.com/capgym/cap-x |
| **ASPIRE** 존재, ID 2607.00272, NVIDIA | CONFIRMED-MULTI | 제목: "ASPIRE: Agentic /Skills Discovery for Robotics". 풀네임: Agentic Skill Programming through Iterative Robot Exploration. NVIDIA GEAR, UMich, UIUC, UC Berkeley, CMU의 공동 연구다. arXiv 2026-06-30. 코드는 NVlabs/ASPIRE(Apache 2.0). **학회 채택은 확인되지 않았다(preprint).** | https://arxiv.org/abs/2607.00272 , https://research.nvidia.com/labs/gear/aspire/ , https://github.com/NVlabs/ASPIRE |
| ASPIRE "실행 추적으로 진단→수리→검증된 수리를 스킬로 저장" | CONFIRMED-MULTI | 맞다. 구성은 세 가지다: (1) 세밀한 멀티모달 추적을 내는 폐루프 실행 엔진, (2) 계속 커지는 스킬 라이브러리(18개 범주), (3) 진화적 탐색. 저장한 스킬은 이후 작업에 **in-context 지침으로 검색되어** 쓰인다. | https://arxiv.org/html/2607.00272v1 , https://www.marktechpost.com/2026/07/03/nvidia-ai-introduces-aspire-a-self-improving-robotics-framework-reaching-31-zero-shot-on-libero-pro-long-tasks/ |
| ASPIRE "처음 보는 긴 작업에서 31% 대 4%" | CONFIRMED-MULTI | 맞다. 벤치마크는 LIBERO-Pro Long zero-shot이다. 4%는 "test-time reasoning과 재시도를 허용한 기존 방법"의 값이다(AI Weekly 요약). 다른 수치: LIBERO-Pro 섭동에서 최대 +77%, Robosuite 양팔 전달에서 +72%, BEHAVIOR-1K에서 +32%. 이 값들은 "기존 방법 대비 최대 향상폭"이다. 절대 성공률이 아니다. | https://aiweekly.co/alerts/aspire-agent-writes-robot-code-hits-31-zero-shot-vs-4 , https://x.com/Marktechpost/status/2073297157684379706 |
| ASPIRE 스타 수 | UNCONFIRMED | 검색에서 스타 수를 찾지 못했다. | — |
| **VLCP** 존재, ID 2608.16978 | SINGLE-SOURCE (초록 하나를 여러 사이트가 옮김) | 제목: "VLCP: Vision Language Control Policy Closed-Loop Code Replanning for Robot Manipulation". arXiv 2026-08-17. 저자: Dhia Naouali, Minghan Wu, Claudia Wong, Abhinav Puthran, Omar G. Younis 등. 소속, 학회, 코드 저장소, 스타는 확인되지 않았다. | https://arxiv.org/abs/2608.16978 , https://pith.science/paper/2608.16978 |
| VLCP "K스텝마다 다시 관측해 제어 코드를 에피소드 안에서 고쳐 씀, 3.5%→35.1%" | SINGLE-SOURCE | 맞다. 세부: VLM은 고정(frozen)이다. 짧은 Python 제어 함수를 쓴다. K스텝마다 다시 보는 입력은 여러 시점 RGB, 고유수용(proprioceptive) 상태, 상태 변화량(delta)이다. 57개 작업 시뮬레이션 기준이다. 실패한 잡기의 복구율은 27.3%다. **35.1%는 향상 후에도 절대 성공률이 낮다.** | https://arxiv.org/html/2608.16978 , https://awesomepapers.io/robotics/papers/2608.16978 |
| **RoboOS** 2505.03673, 약 600★, 1년보다 오래됨 | CONFIRMED-MULTI | 제목: "RoboOS: A Hierarchical Embodied Framework for Cross-Embodiment and Multi-Agent Collaboration". BAAI/FlagOpen. 스타 608, 포크 91(검색 요약, 날짜 모름). 2025년 5월 논문이라 1년 창 밖이다. plan에 "1년보다 오래됨"이라고 적은 것은 맞다. 구성: Embodied Cloud Model(MLLM), Cerebellum Skill Library, Real-Time Shared Memory. RoboOS 2.0은 stand-alone 브랜치로 나왔다. | https://huggingface.co/papers/2505.03673 , https://github.com/FlagOpen/RoboOS , https://oosmetrics.com/repo/FlagOpen/RoboOS |
| **RAI** 2505.07532 (창 밖) | CONFIRMED-MULTI | 제목: "RAI: Flexible Agent Framework for Embodied AI". Robotec.AI(바르샤바). arXiv 2025-05-12라 창 밖이다. 스타 약 520, 포크 69(검색 요약, 날짜 모름). ROS 2 기반이다. Agents/Connectors/Tools 세 가지 추상화로 이루어진다. | https://arxiv.org/abs/2505.07532 , https://github.com/RobotecAI/rai |
| **Agent as Policy** 2609.12541 | CONFIRMED-MULTI (존재) / SINGLE-SOURCE (수치) | 제목: "Agent as Policy for Robotic Manipulation"(AGP). arXiv 2026-09-11이고 v2가 있다. 저자: Mengzhao Jia, Yang Lin, Xixin Zhang, Zhihan Zhang, Xiaobai Liu, Meng Jiang. 실제 양팔 YAM 로봇에서 LLM 에이전트가 직접 정책 역할을 한다. 도구로 카메라를 읽고 Cartesian/관절 명령을 내리며 완료를 스스로 판정한다. 블록 쌓기 세 구성에서 100/100/80%. 소속 기관, 스타, 학회는 확인되지 않았다. | https://arxiv.org/abs/2609.12541 , https://github.com/agent-as-policy-2026/agent-as-policy |
| **Agentic Robot** 2505.23450 | CONFIRMED-MULTI (존재) / **WRONG (기간)** | 2025년 5월 논문이다. **plan은 "1년 이내" 목록에 넣었지만 1년 창 밖이다.** 구성: GPT-4o 계획기, OpenVLA 실행기, 미세조정한 Qwen2.5-VL-3B 검증기. SAP(Standardized Action Procedure)로 셋을 조율한다. LIBERO 평균 79.6%. OpenReview에 PDF가 있지만 채택 여부는 확인되지 않았다. **실행기가 VLA라서 "VLA는 일반화가 안 된다"는 핵심 메시지와 부딪힌다.** | https://arxiv.org/abs/2505.23450 , https://openreview.net/pdf?id=IwSvhHAQcL , https://agentic-robot.github.io/ |
| **ROSClaw** 2603.26997 | CONFIRMED-MULTI | 제목: "ROSClaw: An OpenClaw ROS 2 Framework for Agentic Robot Control and Interaction". Kent State Univ., OpenDive, PlaiPin. arXiv 2026-03-27. OpenClaw 런타임을 ROS 2에 붙이는 모델 무관(model-agnostic) 실행 계층이다. **실행 전 행동 검증(안전 범위, safety envelope)** 을 한다. 로봇 3종, 모델 백엔드 4종에서 정책 밖 행동 제안 비율이 모델마다 최대 4.8배 달랐다. 코드는 PlaiPin/rosclaw이고 **168★**(검색 요약, 날짜 모름). 해커톤 프로젝트에서 시작했다. | https://arxiv.org/abs/2603.26997 , https://github.com/PlaiPin/rosclaw , https://cerebralvalley.ai/e/open-claw-hackathon-41d0b52d/hackathon/gallery/2.md |
| **ROSClaw** 2604.04664 | CONFIRMED-MULTI (존재) | **이름만 같은 다른 논문이다.** 제목: "ROSClaw: A Hierarchical Semantic-Physical Framework for Heterogeneous Multi-Agent Collaboration". 통지대(Tongji) 쪽 상하이 연구소. 프로젝트 페이지는 rosclaw.io다. GitHub 저장소와 스타는 찾지 못했다. 인용할 때 두 ROSClaw를 섞지 않도록 주의한다. | https://arxiv.org/abs/2604.04664 |

---

## 2) 더 나은 대안 / 최신 SOTA (이번 검색에서 새로 찾은 것)

| 후보 | 날짜 | 스타/신뢰도 근거 | 메모 | 출처 |
|---|---|---|---|---|
| ros-mcp-server (robotmcp) | 저장소 생성일 미확인(2025년 초로 보이나 미확인). 논문 없음 | 약 1.1K★, 포크 161, 기여자 17(검색 요약) | 스타는 CaP-X보다 많다. 하지만 "LLM이 ROS 명령을 부르고 끝나는" 거친 결합이다. 사용자 요구(잘게 엮기)에 맞지 않고, 논문도 아니다. | https://github.com/robotmcp/ros-mcp-server |
| OpenClaw (범용 에이전트 런타임) | — | 247K★(2026-03-02 기준, 검색 요약) | 로봇 전용이 아니다. ROSClaw와 ABot-Claw의 바탕이다. | https://en.wikipedia.org/wiki/OpenClaw , https://github.com/openclaw/openclaw |
| ABot-Claw (2604.10096) | 2026-04-11 | 스타 미확인, 학회 미확인 | OpenClaw를 로봇용으로 확장했다. 능력 기반 스케줄링, 여러 로봇이 공유하는 멀티모달 메모리, critic 기반 폐루프 피드백이 있다. | https://arxiv.org/abs/2604.10096 |
| dimensionalOS/dimos | 미확인 | 스타 미확인(검색 한도 때문에 확인 못 함) | 자연어로 여러 로봇을 제어하는 에이전트 OS다. 스킬을 MCP로 부른다. | https://github.com/dimensionalOS/dimos |
| Coding Agents with an Obstacle-Aware Harness (2609.20822) | 2026-09 | 미확인 | 제목만 확인했다(Agent as Policy 검색 결과에 함께 나옴). | https://arxiv.org/html/2609.20822 |
| Generalizing Manipulation Skills with a Local Coding Agent (2609.26499) | 2026-09 | 미확인 | 제목만 확인했다. | https://arxiv.org/html/2609.26499 |
| EMERGE-Policy (2608.29896) | 2026-08 | 미확인 | 제목만 확인했다. | https://arxiv.org/pdf/2608.29896 |
| ROSBag MCP Server (2511.03497) | 2025-11-05 | 미확인 | 로그 분석용이다. 제어용이 아니어서 M6와는 관련이 적다. | https://arxiv.org/abs/2511.03497 |

**1년 창 안 논문을 스타 순으로 정리 (확인된 범위 안에서)**
1. CaP-X: 약 805★. ICML 2026. **스타 수와 학회가 모두 확인된 유일한 항목이다.**
2. ROSClaw (2603.26997): 168★. 저장소가 논문보다 먼저 해커톤 프로젝트로 시작했을 수 있다.
3. ASPIRE: 스타 미확인. NVIDIA 공식 저장소다.
4. Agent as Policy: 스타 미확인.
5. VLCP: 코드 저장소 자체를 확인하지 못했다.

결론: **"스타 기준 상위 5개"는 지금 자료로 순위를 정할 수 없다.** 스타 수가 확인된 것은 CaP-X와 ROSClaw 둘뿐이다. 1년 창 안에서 CaP-X를 넘는 로봇 LLM+스킬 논문 저장소는 이번 검색에서 찾지 못했다. ros-mcp-server와 OpenClaw는 스타가 더 많지만 논문이 아니거나 로봇 전용이 아니다.

---

## 3) 반대 증거와 위험

- **추상화에 의존한다 (CaP-X 자체 결과)**: 사람이 만든 고수준 스킬이 있으면 성능이 좋다. 그 스킬을 빼면 성능이 떨어진다. 다중 턴, 실행 피드백, visual differencing, 스킬 합성으로 상당 부분 되찾는다. 우리 계획은 "기존 스킬 위에 LLM"이므로 이 결과와 맞는 방향이다. 다만 스킬 품질이 성능을 좌우한다. https://arxiv.org/html/2603.22435v1
- **code-as-policy의 절대 성공률이 낮다**: VLCP는 향상 후에도 35.1%다. ASPIRE의 zero-shot도 31%다. "LLM 기반이 일반화된다"는 메시지를 세울 때 이 절대값이 반론 근거가 될 수 있다. https://arxiv.org/abs/2608.16978 , https://aiweekly.co/alerts/aspire-agent-writes-robot-code-hits-31-zero-shot-vs-4
- **ASPIRE는 동료 심사 전이다**: AI Weekly는 "preprint이며, 벤치마크 향상이 가정이나 창고에서의 지속적 신뢰성과 같지 않다"고 적었다. https://aiweekly.co/alerts/aspire-agent-writes-robot-code-hits-31-zero-shot-vs-4
- **모델에 따라 안전 행동이 크게 다르다**: ROSClaw에서는 같은 기반 위에서도 모델마다 정책 밖 행동 제안 비율이 최대 4.8배 달랐다. LLM을 스킬 결정 지점에 넣을 때는 실행 전 검증 계층이 필요하다는 근거다. https://arxiv.org/abs/2603.26997
- **VLA 실행기에 의존하는 항목이 있다**: Agentic Robot의 실행기는 OpenVLA다. 핵심 메시지("VLA는 일반화가 안 된다")와 충돌한다. 그대로 인용하면 논지가 약해진다. https://arxiv.org/abs/2505.23450
- **같은 이름, 다른 논문**: ROSClaw 두 편은 서로 무관하다. 잘못 인용할 위험이 있다.
- **기간 규칙 위반**: Agentic Robot, RoboOS, RAI는 모두 2025년 5월 논문이다. 사용자가 정한 1년 규칙에 어긋난다. RoboOS는 plan에 "1년보다 오래됨"이라고 표시되어 있다. Agentic Robot은 표시 없이 1년 이내 목록에 들어가 있다.

---

## 4) 이 모듈에 장착할 모듈 후보 순위 (신뢰도 규칙 적용)

신뢰도 등급: HIGH = 학회 채택, 유명 연구실, 확인된 스타. MEDIUM = 유명 연구실이지만 preprint. LOW = 무명 그룹, arXiv만 있음, 반응 확인 안 됨. LOW는 추천에서 뺀다.

| 순위 | 후보 | 신뢰도 | 근거 | Jev를 스킬 결정 지점에 둘 수 있나 (구조 분석, Claude 의견) |
|---|---|---|---|---|
| 1 | **CaP-X / CaP-Agent0** | HIGH (ICML 2026, Berkeley, Stanford, NVIDIA, UT 등 저자: Goldberg, Fei-Fei, Yuke Zhu, Jim Fan; 약 805★) | 1년 창 안에서 학회와 스타가 모두 확인된 유일한 틀이다. 추상화 수준별 스킬 API와 다중 턴 피드백이 있다. VDM이 장면 변화를 **텍스트로** 설명한다. 텍스트만 받는 Jev 입력과 성격이 맞다. 단, 변환 방법은 사용자가 정할 사항이라 여기서 정하지 않는다. | 가능하다. 생성된 Python 코드가 부르는 기본 함수 가운데 하나로 "typed 선택 함수"를 넣을 수 있다. 다중 턴 루프에서 턴마다 판단을 넣을 수 있다. |
| 2 | **ASPIRE** | MEDIUM (NVIDIA GEAR, UMich, UIUC, Berkeley, CMU; preprint; 스타 미확인) | 실패 진단→수리→검증→스킬 저장 순환이 plan의 "Astra 복구 결과를 스킬로 저장"과 정확히 맞는다. 31% 대 4%는 여러 출처에서 확인했다. | 가능하다. 스킬이 코드이므로 코드 안의 분기점을 typed 질문으로 바꿀 수 있다. 저장된 스킬은 in-context로 불러 쓴다. |
| 3 | **RoboOS** (참고용, 창 밖) | MEDIUM-HIGH (BAAI, 608★) 그러나 1년 규칙 위반 | 뇌-소뇌 구조와 공유 메모리가 있다. 사용자의 1년 규칙 때문에 주 참고로 쓰지 않는다. | 가능하다. Cerebellum Skill Library의 스킬 선택/전환 지점. |
| 4 | **ROSClaw (2603.26997)** | LOW-MEDIUM (Kent State와 스타트업, 168★, 학회 미확인) | 실행 전 검증 계층이라는 발상은 유용하다. 신뢰도가 경계선이라 주 참고로는 추천하지 않는다. | 가능하다. 실행 전 행동 검증(yes/no) 자리에 둘 수 있다. |
| 제외 | VLCP | LOW (arXiv만, 소속/코드/반응 미확인) | 신뢰도 규칙에 따라 추천에서 뺀다. 수치만 참고한다. | — |
| 제외 | Agent as Policy | LOW-MEDIUM (2주 전 공개, 학회/스타 미확인) | 너무 새롭고 반응 증거가 없다. 2~3개월 뒤 다시 확인한다. | — |
| 제외 | Agentic Robot, RAI | 창 밖. Agentic Robot은 VLA 실행기라 핵심 메시지와 충돌 | — | — |

**plan 수정 제안(사용자 확정 필요)**
- M6 참고 목록에서 Agentic Robot의 "1년 이내" 분류를 고친다.
- VLCP를 참고에서 빼거나 "LOW 신뢰도"로 표시한다.
- CaP-X의 "실행 전후 이미지 비교"를 "변화를 텍스트로 설명하는 VDM"으로 정정한다.

---

## 5) 확인 못 한 것

- ASPIRE, Agent as Policy, VLCP, ROSClaw(2604.04664), ABot-Claw, dimos의 GitHub 스타 수.
- 스타 수의 측정 날짜(CaP-X 805만 2026-09-17로 요약됨).
- ros-mcp-server의 생성일(1년 창 안인지).
- ASPIRE의 "4% 기존 방법"이 정확히 어떤 기준 방법인지(CaP-Agent0인지 등).
- Agent as Policy 저자 소속(Notre Dame로 추정되나 검색으로 확인 못 함).
- Agentic Robot의 학회 채택 여부.
- **LLM/VLM 분야 조사를 하지 못했다(검색 한도 소진).** 다음 후보들은 Claude가 기억하는 것일 뿐 이번 세션에서 확인하지 않았다. 사실로 인용하면 안 되고, 후속 검색 대상으로만 둔다: 경험을 전략 메모리로 쌓는 LLM 에이전트 연구(예: "ReasoningBank", "Agentic Context Engineering(ACE)"), 에이전트용 스킬 패키징 방식("Agent Skills"), LLM+behavior tree 결합 연구, 구조화 출력/제약 디코딩 기반 결정 연구. 각 항목의 ID, 날짜, 학회, 반응을 확인한 뒤에만 추천 여부를 정한다.
- 1년 창 안에서 CaP-X보다 스타가 많은 LLM+로봇 스킬 논문 저장소가 있는지 추가로 검색하지 못했다. 이번 검색 범위 안에서는 찾지 못했다.
