# 03. M10 경험 축적 (고정 API 모델용 메모리), v3 초안 조사

작성: 2026-09-24, v3 조사 에이전트. 대상: `docs/plan.md` M10, `docs/research/v2/06-memory.md`의 미확인 항목 9개, 2025-03-23 이후 LLM/VLM/로봇 메모리 방법.

---

## 1. 조사 방법과 한계

- WebSearch 5회 사용(한도 15회).
- **원문 본문(HTML)을 직접 읽은 논문 6편**: 2606.15017(예산 제약 연구), 2605.07164(ExpWeaver), 2605.07594(MemCompiler), 2511.20857(Evo-Memory), 2509.25140(ReasoningBank, 판정 관련 절), 2602.12670(SkillsBench, v4). 수치는 이 6편의 표나 본문 문장에서 가져왔다.
- **arXiv 원문 초록(abs 페이지나 API)만 읽은 논문 16편**: 2607.23702, 2604.11306, 2606.13097, 2609.19906, 2608.09410, 2510.12635, 2602.16313, 2605.18421, 2609.22538, 2509.24219, 2604.18791, 2609.08444, 2510.20328, 2605.21463, 2605.19576, 2601.16690. 소속은 HTML 첫 부분에서 확인했다.
- 인용 수는 Semantic Scholar batch API에서, 스타 수는 GitHub API에서 2026-09-24에 가져왔다.
- 한계
  - arXiv 검색 API는 몇 번 쓴 뒤 429(요청 한도)로 막혔다. 다른 에이전트와 한도를 같이 쓰는 것으로 보인다. 그래서 절차 메모리와 스킬 라이브러리 검색 일부는 WebSearch로 대신했다. 검색 폭은 계획보다 좁다.
  - ExpWeaver의 주 결과는 그림(Figure 2, 3)에만 있어서 숫자를 뽑지 못했다. 본문 문장과 표 1, 표 2의 서술만 인용한다.
  - 학회 채택은 arXiv Comments 칸과 Semantic Scholar venue로만 확인했다. 학회 프로그램 페이지까지는 보지 않았다.

---

## 2. 검증 표

### 2.1 v2에서 미확인이던 9개

| 항목 | 확인 수준 | 정정/비고 (신뢰도 근거 포함) | 출처 URL |
|---|---|---|---|
| **2606.15017** "Are Online Skill and Memory Modules Always Worth Their Tokens? A Budget-Constrained Study of Web Agents" | ORIGINAL-CONFIRMED | **존재한다.** v1은 2026-06-12, v2는 2026-08-30. **EMNLP 2026 채택**(arXiv Comments). ServiceNow AI Research, ÉTS Montréal, UBC, McGill. 인용 1회. **신뢰도 HIGH**(주요 학회 채택). 방법: AWM, ASI, ReasoningBank를 "온라인 보강"(매 작업마다 모듈 비용을 냄)으로 돌리고, 모듈 없이 행동 스텝을 10에서 15로 늘리고 접근성 트리 규칙 가지치기를 넣은 Vanilla-IB와 비교했다. 3회 실행 평균이다. **WebArena 4개 도메인 평균 성공률(%)과 작업당 토큰(K)**: Gemini 3 Flash는 Vanilla-IB 44.78/73.6, AWM 39.34/99.3, ASI 41.02/107.3, RBank 39.33/82.6. GPT-5.4-mini는 Vanilla-IB 32.67/90.2, AWM 27.02, ASI 29.00, RBank 24.58. Qwen 3.6-27B는 Vanilla-IB 42.14/95.5, AWM 38.01, ASI 40.15, RBank 37.00 (표 1). **WorkArena-L1**(Qwen만)에서는 Vanilla-IB 55.56과 RBank 55.56이 같았고 AWM 53.53, ASI 48.49였다 (표 2). 부록 F.3, 표 10: ReasoningBank의 **LLM 판정기가 "성공"이라고 붙인 항목 가운데 52.9%(Gemini, Shopping), 59.5%(GPT, Shopping)가 실제로는 실패한 궤적**이었다. **한계(저자 본인이 씀)**: WebArena와 WorkArena는 작업이 서로 독립적이라 장기 메모리가 별로 필요 없다. 메모리가 중요한 환경에서는 결과가 달라질 수 있다. 결론은 온라인 보강에만 적용되고, 오프라인 방법(SkillWeaver 등)은 계산 방식이 달라야 한다. **plan의 요약 "같은 예산이면 메모리 없는 기본 에이전트가 비슷하거나 더 낫다"는 웹 에이전트, 온라인 설정이라는 조건을 붙이면 맞다.** main.tex는 현재 arXiv 번호를 인용하지 않고 "같은 토큰 예산의 메모리 없는 방법"만 쓰고 있다(172행). | https://arxiv.org/abs/2606.15017 , https://arxiv.org/html/2606.15017 , https://sinahmr.github.io/budget-constrained-web-agents |
| **2605.07164 ExpWeaver** "Rethinking Experience Utilization in Self-Evolving Language Model Agents" | ORIGINAL-CONFIRMED | 존재한다. 2026-05-08. 하얼빈공대(HIT, Ting Liu와 Bing Qin 그룹)와 Huawei. 학회 표시가 없고 인용 1회. **신뢰도 MED-LOW**(알려진 NLP 연구실, 심사 전, 반응 거의 없음). 방법: 경험을 만드는 방식은 그대로 두고, 경험을 추론 중에 **필요할 때만 꺼내는 선택 자원**으로 바꿨다(reasoning → (선택적 경험 사용) → action). 4개 프레임워크(ReasoningBank, AWM, SkillRL, G-Memory), 7개 백본, ALFWorld, WebShop, QA에서 Init-only(처음에 한 번)나 Always-on(매 스텝)보다 "거의 모든 설정에서" 낫다고 한다(수치는 그림에만 있어서 확인 못 함). 표 1(샘플당 경험 호출 횟수): **강한 모델일수록 거의 안 꺼낸다.** ReasoningBank 틀에서 GPT-5.2는 ALFWorld, WebShop, HotpotQA 모두 0.00회, Qwen3-32B는 ALFWorld 2.17회. 표 2: 호출 위치에서 경험을 빼거나(Empty) 무작위 위치에서 꺼내면(Random) 성능이 떨어진다(Qwen3-32B, DeepSeek-V4-Pro). 5.3절: 경험 호출은 **토큰 엔트로피가 높은 스텝**에 몰린다. plan의 요약 "매 스텝 주입보다 필요할 때만"은 맞다. | https://arxiv.org/abs/2605.07164 , https://arxiv.org/html/2605.07164 |
| **2607.23702 IOM** "Try Once, Then Optimal: De-Redundified Procedure Memory for Cross-Episode Exploration Amortization" | ORIGINAL-CONFIRMED (초록) | 존재한다. 2026-07-26. 칭화대(Guyue Zhou, Ruqi Huang 외). 학회 표시 없음, 인용 0, 코드는 채택 후 공개 예정. **신뢰도 LOW.** 방법: 숨은 상태가 있는 물체(걸쇠 달린 전자레인지 등)를 한 번 만나면, 성공 여부와 상관없이 짧은 절차를 기록한다. 이 절차를 **물체의 식별 특징을 키로** 저장하고, 절차 조건부 정책에 soft bias로 넣는다. 기성 VLM이 경험을 절차로 파싱한다. 오라클 메모리는 재탐색보다 조작 횟수를 16~30% 줄였고, VLM 버전은 그 절감의 69~88%를 얻었다. 문 과제에서 약 12%는 틀린 절차를 꺼냈지만 성공률은 떨어지지 않았다(soft bias라서). 이득은 효율뿐이고 성공률 향상은 아니다(실제 로봇에서는 개선). | https://arxiv.org/abs/2607.23702 |
| **2604.11306 H²-EMV** "Learning to Forget: Hierarchical Episodic Memory for Lifelong Robot Deployment" | ORIGINAL-CONFIRMED (초록) | 존재한다. 2026-04-13, v2 2026-05-05. KIT(Bärmann, Plewnia, Waibel, **Asfour**, ARMAR-7). 학회 표시 없음, 인용 0. **신뢰도 MED-LOW**(유명 연구실, 심사 전, 반응 없음). **주제가 다르다.** 사용자 질문("열쇠 어디 뒀어?")에 답하는 일화 기억 QA이고, 행동 개선용 경험 축적이 아니다. 계층형 일화 기억에 LM 기반 관련도로 선택적 망각을 한다. 메모리 크기 45%, 질의 계산 35%를 줄였고, 두 번째 질의 라운드에서 정확도가 70% 올랐다. M10에는 "망각 규칙" 개념만 참고한다. | https://arxiv.org/abs/2604.11306 |
| **2605.07594 MemCompiler** "Compile, Don't Inject: State-Conditioned Memory for Embodied Agents" | ORIGINAL-CONFIRMED | 존재한다. 2026-05-08. USTC, **Microsoft Research**, 칭화대 AIR(Ting Cao, Yunxin Liu). 학회 표시 없음, 인용 5, 코드와 데이터 공개 페이지 있음. **신뢰도 MED**(유명 연구실, 심사 전). 방법: 에피소드 시작에 메모리를 통째로 넣는 방식(AMMI)을 비판한다. 학습된 Memory Compiler(Qwen2.5-VL-7B LoRA, SFT 뒤 GRPO)가 **구조화된 Brief State(과제 진행 상태 + 환경 믿음)**를 읽고, 스텝마다 관련 메모리만 골라 실행 가능한 지침으로 바꾼다. 출력은 {지침, 상태 갱신, 둘 다, 아무것도 안 함} 넷 중 하나다. 텍스트 채널과 잠재 채널(Soft-Mem)이 있다. 실행기 백본은 고정한다. **핵심 수치**: (a) 통째 주입은 **작은 실행기를 메모리 없는 경우보다 나쁘게 만든다.** EB-ALFRED 진행률(표 6), Qwen2.5-VL-32B에서 No Mem 28.86, G-Mem −53.1%, A-Mem −61.8%, Mem0 −18.8%, MemCompiler +54.3%. 반면 GPT-5와 Gemini 같은 큰 모델은 통째 주입으로도 +31~46%(표 1). (b) AlfWorld 효율(표 5): 성공률 AMMI 35.03% 대 SCMC 82.16%, 실행기 입력 토큰 2481에서 1003, 실행기 지연 0.30초에서 0.12초. (c) AMMI에서는 메모리 토큰에 주는 attention이 29스텝째에 86.7% 떨어진다. 저자들은 규칙 기반 공개(rule-based disclosure)가 부족하다고 주장한다. 다만 규칙 기반과의 직접 수치 비교는 확인하지 못했다. | https://arxiv.org/abs/2605.07594 , https://arxiv.org/html/2605.07594 , https://air-embodied-brain.github.io/MemCompiler/ |
| **2606.13097 FCGraft** "Functional Cache Grafting: Robust and Rapid Code-Policy Synthesis for Embodied Agents" | ORIGINAL-CONFIRMED (초록) | 존재한다. 2026-06-11. 성균관대(Honguk Woo). **ICML 2026 채택**(Comments). 인용 0. **신뢰도 MED-HIGH**(주요 학회, 반응 없음). 검증된 함수 단위 코드 뼈대와 그 **KV cache**를 저장해 두고 이어 붙인다(stitching, patching). RAGCache 대비 성공률 +18.31%, 생성 속도 2.3배. **KV cache를 직접 다뤄야 하므로 API 모델인 Astra와 Jev에는 쓸 수 없다.** "검증된 뼈대 재사용" 개념만 해당된다. | https://arxiv.org/abs/2606.13097 |
| **2609.19906** "Learning and Transferring Closed-Loop Robot Software" | ORIGINAL-CONFIRMED (초록) | 존재한다. 2026-09-17. **Sakana AI**(Kuroki, Yujin Tang). 학회 표시 없음, 인용 0. **신뢰도 LOW-MED.** 코딩 에이전트가 시연과 시뮬 피드백으로 폐루프 정책 코드를 만들고 개선해서 아카이브에 넣는다. 새 작업에서는 이 아카이브를 참고한다. RoboCasa 원천 4개 작업: 28.3%에서 64.2%. 목표 9개 작업, 3회 실행: 참고 없음 45.2%, 초기 코드 참고 41.5%, **최적화된 코드 참고 57.0%**. 초기 코드 참고가 오히려 떨어뜨린 점, 2개 작업에서는 초기 참고가 더 나았다는 점도 저자가 보고했다. 최종 정책은 모델 호출 없이 실행된다. | https://arxiv.org/abs/2609.19906 |
| **2608.09410 HyMeS** "Skills in Weights, Memory in Code: Hybrid Learning for Memory-Dependent Robot Manipulation" | ORIGINAL-CONFIRMED (초록) | 존재한다. 2026-08-10. Northwestern(Qi Zhu), Minnesota, Stanford(Ruohan Zhang). 학회 표시 없음, 인용 0. **신뢰도 LOW-MED.** 저수준 스킬은 모방학습 VLA(π0.5)가 맡고, 코딩 에이전트가 **메모리 관리 휴리스틱을 실행 가능한 코드로** 롤아웃 피드백을 받아 고친다. 단계 완료는 **고유수용 신호와 다중 프레임 VLM 판정**으로 확인한다. RoboMemArena에서 π0.5 대비 평균 누적 성공 52.5%→66.2%, 과제 성공 41.3%→60.1%, PrediMem 대비 +4.5, +14.5점. 에피소드 안의 작업 기억이지 에피소드 사이의 경험 축적은 아니다. "메모리는 코드로, 판정은 센서 + VLM으로"라는 분업이 우리 구조와 닮았다. | https://arxiv.org/abs/2608.09410 |
| **2510.12635 MemAct** "Memory as Action: Autonomous Context Curation for Long-Horizon Agentic Tasks" | ORIGINAL-CONFIRMED (초록), 학회 SINGLE-SOURCE | 존재한다. 2025-10-14, v2 2026-05-07. 베이징교통대(Jitao Sang) 외. Semantic Scholar venue가 **ACL**(연도는 표시 없음, 2026으로 추정되지만 미확인), 인용 48. **신뢰도 MED.** 문맥 편집(삭제, 삽입)을 정책의 행동으로 두고 **RL로 학습**한다. 14B가 16배 큰 모델과 정확도가 같고 문맥 길이는 51% 줄었다. **가중치를 학습해야 하므로 고정 API 모델에는 쓸 수 없다.** | https://arxiv.org/abs/2510.12635 |

### 2.2 v2 항목 재확인과 추가 정보

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| ReasoningBank의 라벨 | ORIGINAL-CONFIRMED | 본문: "judged by the agent itself without ground-truth labels", LLM-as-a-judge. WebArena-Shopping에서 판정기(Gemini-2.5-flash) 정확도는 **72.7%**였다. 저자들은 판정 정확도를 50~100%로 바꿔 시뮬레이션해도 성능이 크게 바뀌지 않았다고 주장한다(그림 8). **반대 증거**: 2606.15017 표 10의 성공 라벨 오염률 52.9~60.0%. 스타 594, 인용 199, ICLR 2026. | https://arxiv.org/html/2509.25140 |
| ACE | 인용과 스타 갱신 | 인용 321, GitHub ace-agent/ace 스타 1,331. 다른 내용은 v2와 같다. | https://github.com/ace-agent/ace |
| Dynamic Cheatsheet | 갱신 | 인용 125, 스타 276. EACL 2026. | https://github.com/suzgunmirac/dynamic-cheatsheet |
| ViReSkill (2509.24219) | **신뢰도 하향** | 첫 공개 2025-09-29. LLM+스킬 1년 기준(2025-09-23) 안에 든다. 그러나 **인용 2, GitHub 스타 0, 학회 표시 없음** → **LOW.** plan의 "MED-LOW"를 LOW로 내린다. | https://arxiv.org/abs/2509.24219 , https://github.com/PanasonicConnect/vireskill |
| AWM (2409.07429) | 기간 밖, 기초 문헌 | ICML 2025(Semantic Scholar), 인용 285, 스타 474. 2606.15017과 Evo-Memory의 비교 대상으로 계속 쓰인다. | https://github.com/zorazrw/agent-workflow-memory |

### 2.3 새로 확인한 벤치마크와 방법

| 항목 | 확인 수준 | 정정/비고 (신뢰도) | 출처 URL |
|---|---|---|---|
| **Evo-Memory**, ExpRAG / ReMem (2511.20857) | ORIGINAL-CONFIRMED | 2025-11-25, v2 2026-05-18. **Google DeepMind(Ed Chi, Fernando Pereira 외)와 UIUC.** 학회 표시 없음, 인용 130. **신뢰도 HIGH**(유명 연구실 + 반응). 스트리밍 작업열 벤치마크다. 10개가 넘는 메모리 모듈을 같은 search→predict→evolve 루프로 구현해 비교했다. **다중 턴 체화 과제(표 1b) 성공률**: Claude 3.7 Sonnet, ALFWorld에서 No-memory 0.18, AWM 0.49, DC-RS 0.50, Mem0 0.51, A-Mem 0.48, **ExpRAG 0.74, ReMem 0.92**. 4개 환경 평균 성공률은 AWM 0.49, ExpRAG 0.63, ReMem 0.78. Gemini 2.5 Flash의 ALFWorld는 Baseline 0.12, AWM 0.26, ExpRAG 0.59, ReMem 0.66. **ExpRAG는 "작업 입력, 출력, 피드백"을 템플릿으로 저장하고 top-k로 꺼내는 단순한 방식이다.** 그런데도 AWM, DC, Mem0, A-Mem을 모두 이겼다. ReMem은 매 스텝 {Think, Act, Refine-memory} 중 하나를 고른다. **표 3: 실패 경험까지 거르지 않고 저장하면 기준 방법들이 뚜렷하게 나빠진다.** 주 실험의 메모리는 피드백(정답 신호) f를 함께 저장한다. **비교에 ReasoningBank와 ACE는 없다.** 같은 예산으로 맞춘 비교도 아니다. | https://arxiv.org/abs/2511.20857 , https://arxiv.org/html/2511.20857 |
| **MemoryArena** (2602.16313) | ORIGINAL-CONFIRMED (초록) | 2026-02-18, **ICML 2026**, 인용 67. 저자에 UCSD(McAuley), ReasoningBank의 Siru Ouyang 포함. **HIGH.** 결과: LoCoMo 같은 대화 메모리 벤치마크를 거의 포화한 에이전트도 서로 의존하는 다중 세션 과제에서는 성능이 낮다. 대화형 메모리(Mem0 계열)를 로봇 절차 경험에 옮기면 안 된다는 v2 판단을 뒷받침한다. | https://arxiv.org/abs/2602.16313 , https://memoryarena.github.io/ |
| EvoMemBench (2605.18421) | ORIGINAL-CONFIRMED (초록) | 2026-05-18, 인용 9, 학회 표시 없음. **LOW-MED.** 메모리 방법 15개를 비교했다. 긴 문맥 기준 방법이 여전히 강하다. 메모리는 현재 문맥이 부족하거나 과제가 어려울 때 가장 도움이 되고, 한 가지 형태가 모든 설정에서 이기지는 않는다. 절차 메모리는 **저장된 경험이 과제 구조와 맞을 때** 실행 과제에서 효과적이다. | https://arxiv.org/abs/2605.18421 |
| **SkillsBench** (2602.12670) | ORIGINAL-CONFIRMED (v4 본문) | 2026-02-13, v4 2026-06-14. 인용 253, GitHub benchflow-ai/skillsbench 스타 1,812. 학회 표시 없음. **HIGH**(반응이 큼). 87개 과제, 결정적 검증기 사용. 큐레이션한 스킬은 평균 통과율을 33.9%에서 50.5%로 올렸다(+16.6pp, v4). 모듈이 3개 이하인 짧은 스킬이 큰 묶음보다 낫다. **스스로 만든 스킬은 3개 구성 모두에서 스킬 없음보다 나빴다(−8.1, −11.3, −11.5pp).** 이유는 만든 스킬을 해결기가 발견하지 못하거나, 만드는 작업이 실제 작업 시간을 빼앗거나, 내용이 자신 있게 틀려서다. **주의**: 여기서 "스스로 만든 스킬"은 **과제를 풀기 전에 경험 없이 만든 것**이다. 경험에서 뽑은 메모리를 시험한 것이 아니다. 2차 문헌(2605.19576)이 인용한 "+0.0pp"는 v1 수치이고, v4에서는 음수로 바뀌었다. | https://arxiv.org/abs/2602.12670 , https://arxiv.org/html/2602.12670 , https://github.com/benchflow-ai/skillsbench |
| Mem-π (2605.21463) | ORIGINAL-CONFIRMED (초록) | 2026-05-20, ServiceNow와 Mila(Chris Pal 외), "Work in progress". **LOW-MED.** 따로 학습한 모델이 **언제** 지침을 낼지(내지 않기 포함)와 **무엇을** 낼지 함께 결정한다(RL). 웹 과제에서 상대 30% 넘게 개선. 학습이 필요하다. | https://arxiv.org/abs/2605.21463 |
| Library Drift (2605.19576) | ORIGINAL-CONFIRMED (초록) | ICML 2026 **워크숍**. **LOW-MED.** 스킬 라이브러리가 관리 없이 커지면 검색이 나빠지고 잘못된 주입이 늘어난다. 결과 기반 퇴출과 활성 스킬 개수 상한으로 고쳤다(MBPP+ 과제라 로봇과는 거리가 멂). | https://arxiv.org/abs/2605.19576 |
| FRAMES (2609.22538) | ORIGINAL-CONFIRMED (초록) | 2026-09-18, IROS 2026 **워크숍** 포스터. **LOW.** Planner, VLM Monitor, Recovery와 Memory Module로 이뤄져 우리와 구조가 거의 같다. 평가한 것은 모니터(94%)뿐이고 메모리는 평가하지 않았다. | https://arxiv.org/abs/2609.22538 |
| MemER (2510.20328) | ORIGINAL-CONFIRMED (초록) | Stanford(Chelsea Finn). 에피소드 **안** 키프레임 기억이고, 학습된 VLM이 필요하다. M10(에피소드 사이 경험)과는 다른 문제다. 참고만 한다. | https://arxiv.org/abs/2510.20328 |

---

## 3. 새로 찾은 것과 모듈별 최고 후보

### 3.1 2026년 현재 분야 판도 (확인된 범위)
1. **"무엇을 저장하나"에서 "언제, 어떻게 넣나"로 초점이 옮겨 갔다.** ExpWeaver(필요할 때만), MemCompiler(상태 조건부 컴파일), Mem-π(언제와 무엇을 함께)가 2026년 5월에 연달아 나왔다. 셋 다 "매 스텝, 통째 주입"을 비판한다.
2. **작은 실행기에는 통째 주입이 해롭다.** MemCompiler 표 6에서 32B 오픈 모델은 −18%에서 −62%, 큰 폐쇄 모델은 +31%에서 +46%였다. ExpWeaver 표 1에서도 강한 모델은 경험을 거의 꺼내지 않는다. **Jev(작고 빠르며, 관련 없는 상태가 들어가면 정확도가 떨어짐)에 대한 가장 직접적인 경고다.**
3. **단순한 방법이 강하다.** Evo-Memory에서 ExpRAG(경험 + 피드백 top-k)가 AWM, DC, Mem0, A-Mem을 이겼다. EvoMemBench에서도 긴 문맥 기준 방법이 경쟁력 있었다.
4. **예산을 맞추면 이득이 사라질 수 있다.** 2606.15017(EMNLP 2026)은 웹, 온라인 설정에서 AWM, ASI, ReasoningBank 모두 예산을 맞춘 기본 방법을 넘지 못했다.
5. **자기 판정 라벨은 오염된다.** 2606.15017 표 10에서 판정기가 성공이라 붙인 것의 최대 60%가 실제로는 실패였다. Evo-Memory 표 3에서는 거르지 않은 실패 경험이 기준 방법들을 망가뜨렸다.

### 3.2 모듈별 최고 후보

| 역할 | 최고 후보 | 어디서 최고였나 | 가져올 것 | 우리 구조에 접목 | 신뢰도 |
|---|---|---|---|---|---|
| 경험 저장과 검색 (Astra) | **ExpRAG에서 ReMem으로** (Evo-Memory) | 공통 벤치마크(ALFWorld, BabyAI, PDDL, ScienceWorld)에서 10여 개 메모리 모듈 중 1, 2위 (Claude 3.7 평균 성공 0.78, 0.63 대 AWM 0.49) | 경험 단위를 (입력, 출력, **검증된 피드백**)으로 저장하고 top-k로 꺼낸다. ReMem의 Refine(메모리 정리)은 실행 중이 아니라 에피소드 사이에 한다. | Astra 재계획과 복구 호출에 top-k(예: 3개)를 넣는다. 키는 (작업, 스킬, 실패 유형 술어, 물체 범주)로 한다. | HIGH (GDM, 인용 130). 로봇 미적용(텍스트 체화 시뮬만) |
| 교훈 추출 (Astra) | **ReasoningBank** 형식의 교훈 항목(제목, 설명, 내용), 성공과 실패 모두 | WebArena, SWE-Bench에서 AWM, Synapse보다 높음(자체 비교) | 실패에서 "예방 교훈"을 뽑는 프롬프트와 항목 형식 | Astra가 에피소드 뒤에 추출한다. **라벨은 센서 술어로 바꾼다**(3.4절). | HIGH (ICLR 2026, 스타 594). 로봇 미적용 |
| 메모리 정리 | **ACE** delta와 중복 제거 + Library Drift의 결과 기반 퇴출과 개수 상한 | ACE: AppWorld 등(ICLR 2026) | 중복 병합, 항목별 성공/실패 카운터, 기여가 없는 항목 퇴출 | 오프라인(에피소드 사이)에서만 돌린다. 실행 루프에는 넣지 않는다. | ACE HIGH, Drift LOW-MED(개념만) |
| **Jev 입력용 경험 전달** | **상태 조건부 컴파일** (MemCompiler 개념) + **필요할 때만** (ExpWeaver 개념) | MemCompiler: EB-ALFRED와 AlfWorld에서 작은 실행기로 유일하게 모든 칸에서 개선. ExpWeaver: 4개 틀, 7개 백본에서 Init-only와 Always-on보다 나음 | "Brief State(진행 단계 + 환경 믿음)로 관련 항목만 고른다"와 "출력에 '없음'을 허용한다" | 3.3절 참고. 학습된 컴파일러 대신 **Astra가 계획 시점에 컴파일하거나 코드 규칙으로** 한다. | MED (MSR + 칭화 AIR, 심사 전) / MED-LOW. **로봇 미적용**(MemCompiler는 체화 시뮬뿐, ExpWeaver는 텍스트 환경) |
| 물체별 절차 메모리 | **IOM** 개념: 물체 식별 특징을 키로 한 절차 + soft bias | 관절 물체 4개 과제에서 조작 16~30% 감소(오라클) | "물체 인스턴스를 키로", "틀려도 따르지 않고 참고만(soft)" | 같은 물체를 다시 만나면 Astra 계획에 절차 힌트를 넣는다. Jev에는 기본 선택지 순서나 사전 편향으로만 준다. | LOW (인용 0). 개념만 |
| 성공 계획 재사용 | ViReSkill 재생 / 2609.19906 소프트웨어 아카이브 | 각 논문의 자체 비교 | 검증된 계획을 저장한다 | Astra 첫 계획의 **초안**으로 쓴다(그대로 재생하지 않는다). 첫 계획 때의 정지 시간을 줄이는 데 쓴다. | 둘 다 LOW. 개념만 |
| 비교 기준 | **Vanilla-IB 방식의 예산 맞춘 기본 방법** (2606.15017) | EMNLP 2026 | 메모리 모듈에 쓴 토큰과 시간을 Astra 추가 호출이나 effort 상향에 대신 쓰는 기준 방법. 3회 이상 실행한 평균 ± 표준편차 | M10 비교 실험의 필수 기준 방법 | HIGH |

### 3.3 Astra 호출과 Jev 호출에 들어갈 메모리 (질문 3 답)

**Astra (느림, 이미지 + 텍스트, 재계획과 복구)** [제안]
- 넣는 것
  1. top-k(3개 안팎) 교훈 항목. ReasoningBank 형식이고, 라벨은 센서가 검증했다.
  2. 같은 물체 인스턴스나 범주의 절차 메모리(IOM 개념).
  3. 비슷한 과거 실패 1~2건의 요약: 실패 술어, 복구 행동, 결과.
- 넣는 방식
  - 매 호출 top-k 검색을 기본으로 한다.
  - playbook 전체 주입(ACE 방식)은 prompt caching이 확인될 때만 쓴다(v2와 같음).
- 이유
  - 큰 모델은 통째 주입으로도 이득을 봤다(MemCompiler 표 1, GPT-5와 Gemini +31~46%).
  - 하지만 ExpWeaver에 따르면 큰 모델은 스스로 거의 꺼내지 않는다.
  - 그래서 Astra에는 필요할 때 꺼내는 방식(도구 호출로 경험 조회)과 top-k 기본 주입을 **비교 실험**한다. [결정 필요]
- Astra는 **Jev용 메모리의 컴파일러 역할**도 맡는다. 계획할 때 관련 교훈을 "스킬 k의 결정 지점 j에서, 술어 P가 참이면 선택지 X를 우선한다" 같은 짧은 typed 규칙으로 바꿔 Jev 프롬프트 조각으로 내려보낸다.
  - MemCompiler의 학습된 컴파일러를 Astra로 대신하는 셈이다. 호출은 계획이나 재계획 때 한 번뿐이라 지연을 늘리지 않는다.
  - **로봇 미적용, 선행 사례를 찾지 못했다.** 검색어: "memory compiler", "state-conditioned memory", "compile memory into guidance robot", "hierarchical memory distillation planner executor". 부재를 주장하지는 않는다.

**Jev (빠름, 텍스트 전용, typed 선택지, 수치에 약함, 관련 없는 상태에 민감)** [제안]
- 원칙: **원시 경험, 교훈 문장 목록, 수치를 넣지 않는다.** 근거는 MemCompiler 표 6(작은 실행기에 통째 주입하면 −18~−62%)과 CLAUDE.md의 Jev 제약이다.
- 넣는 것: 지금 결정 지점에 해당하는 **컴파일된 규칙 0~2개**뿐이다. 형식은 범주형 술어와 선택지 이름으로만 한다. 예: `hint: if grasp_contact=false after close -> prefer REGRASP_SIDE`.
- 고르는 방법(코드, LLM 호출 없음)
  - 조건: (현재 스킬 ID, 결정 지점 ID, 현재 술어 값)이 규칙의 조건과 **정확히 일치**하는 것만 넣는다.
  - 일치하는 게 없으면 넣지 않는다. MemCompiler의 NOACTION, ExpWeaver의 "선택적"과 같은 취지다.
  - MemCompiler 저자는 규칙 기반 공개가 부족하다고 주장한다. 다만 그 근거는 원시 관측열에서 조건을 알 수 없다는 점이다. 우리는 술어를 코드로 계산하므로 이 약점이 줄어든다(추론). 규칙 기반과 학습 기반의 수치 비교는 확인하지 못했다.
- 필요할 때만(ExpWeaver 방식)의 Jev 버전: Jev의 선택지 확률 여유(1위와 2위 차이)가 작을 때만 힌트를 붙여 다시 묻는다. ExpWeaver 5.3절(엔트로피가 높은 곳에서 경험을 호출할 때 효과)을 옮긴 것이다.
  - **전제**: Jev 확률 보정을 먼저 우리 데이터로 측정해야 한다(CLAUDE.md).
  - 비용: 다시 묻는 호출 1회가 든다. M4의 계단식 호출과 겹치는지 확인해야 한다.
  - **로봇 미적용.**
- 길이 예산: 힌트 줄 수에 상한을 둔다(예: 2줄). SkillsBench의 "모듈 3개 이하가 낫다"와 Library Drift의 "활성 개수 상한"이 근거다.

### 3.4 성공/실패 라벨 (질문 3 답)
- **기본은 센서 술어(프로그램 검증기)로 한다. 자기 판정(LLM-as-judge)은 보조로만 쓴다.** [제안]
  - 근거 1: 2606.15017 표 10. ReasoningBank 판정기가 성공이라 붙인 것 가운데 실제 실패가 30.2~60.0%(도메인과 모델에 따라 다름)였다.
  - 근거 2: ReasoningBank 자체 측정에서도 판정 정확도는 72.7%였다.
  - 근거 3: Evo-Memory 표 3. 거르지 않은 실패 경험이 기준 방법들을 떨어뜨렸다.
  - 근거 4: SkillsBench와 Evo-Memory 모두 결정적 검증기나 피드백을 쓴다.
  - HyMeS는 로봇에서 "고유수용 신호 + 다중 프레임 VLM 판정"으로 단계 완료를 확인했다(초록).
- **반대 증거**: ReasoningBank 그림 8은 판정 정확도를 50%까지 낮춰도 성능이 크게 변하지 않았다고 주장한다. 판정 품질이 결정적이지 않을 수 있다. 그래도 우리는 술어를 싸게 얻을 수 있으므로 술어를 쓰지 않을 이유가 없다(판단).
- 라벨 세 등급
  - (a) 술어로 확정한 성공이나 실패
  - (b) 술어가 다루지 못해 Astra가 다중 프레임으로 판정한 것: "미검증" 태그를 단다.
  - (c) 판정 불가
- **Jev용 규칙으로 컴파일하는 것은 (a)에서 나온 것만** 쓴다. (b)는 Astra 참고용으로만 쓴다.
- 이 설정(센서 라벨 + LLM 교훈 추출)은 ReasoningBank 원 논문이 검증한 설정이 아니다(v2와 같음). ablation으로 비교한다.

### 3.5 결론: 가져올 방법 (순위)
1. **Evo-Memory의 ExpRAG를 기본 골격으로, ReasoningBank 형식의 교훈 추출과 센서 라벨을 더하고, 오프라인에서 ACE 정리를 한다.** Astra 쪽이다. 공통 벤치마크에서 확인된 가장 강한 단순 방법에, ICLR 2026 방법 둘을 붙이는 조합이다.
2. **Astra를 컴파일러로 쓰는 상태 조건부 Jev 힌트.** MemCompiler와 ExpWeaver의 개념이고, **로봇 미적용이며 선행 사례를 찾지 못했다.** 컨트리뷰션 후보가 될 수 있다. 다만 근거 논문 둘 다 심사 전이다.
3. 예산을 맞춘 기본 방법(2606.15017)을 비교 기준으로 반드시 넣는다.

---

## 4. 반대 증거와 위험
- **메모리 자체가 이득이 없을 수 있다.**
  - 2606.15017(EMNLP 2026): 웹에서 예산을 맞추면 AWM, ASI, ReasoningBank 모두 기본 방법보다 낫지 않았다.
  - EvoMemBench: 긴 문맥 기준 방법이 강했다.
  - 다만 두 논문 모두 "작업끼리 독립적인 환경"에서의 결과이고, 저자들도 메모리가 중요한 환경은 다를 수 있다고 적었다. 로봇에서 같은 물체와 같은 스킬을 반복하는 구조는 메모리에 유리한 쪽일 가능성이 있다(추론, 미검증).
- **큰 모델은 메모리를 무시한다**(ExpWeaver 표 1, GPT-5.2의 호출 0회). Astra도 넣어 준 교훈을 덜 쓸 수 있다.
- **ReasoningBank 과잉 적용**(2606.15017 F.3): 검색한 항목은 몇 개뿐이어도 작업당 8~12번 언급되었다. 교훈이 행동을 과하게 지배할 위험이 있다.
- **스스로 만든 스킬은 해로웠다**(SkillsBench, −8~−11pp). 경험에서 뽑은 것은 아니지만, "LLM이 쓴 절차 지식은 자신 있게 틀릴 수 있다"는 점은 우리 교훈 추출에도 해당된다. Jev 규칙은 센서 검증을 거친 것만 쓰는 이유다.
- **초기 참고가 해로울 수 있다**(2609.19906: 초기 소스 코드 참고 41.5% < 참고 없음 45.2%). 검증되지 않은 계획 재사용의 위험이다.
- **MemCompiler와 ExpWeaver는 학습을 전제로 한 부분이 있다.** MemCompiler의 컴파일러는 LoRA SFT와 GRPO로 학습하고, Soft-Mem은 실행기 내부에 접근해야 한다(Jev에는 불가). ExpWeaver의 RL 버전도 학습이 필요하다. 우리가 가져올 수 있는 것은 **프롬프트 수준 개념뿐**이고, 그 효과는 원 논문 수치로 보장되지 않는다.
- **벤치마크 사이 비교가 없다.** Evo-Memory에는 ReasoningBank와 ACE가 없고, ReasoningBank 논문에는 ExpRAG가 없다. "최고"는 벤치마크 안에서만 말할 수 있다.
- Evo-Memory의 ReMem은 추가 Think와 Refine 스텝을 쓴다. 예산을 맞춘 비교가 아니라서 2606.15017의 비판이 그대로 해당될 수 있다.

---

## 5. plan.md에 반영할 제안

**[사용자] (변경 없음)**: API 모델 기반의 경험 축적을 제대로 한다.

**[제안]**
1. 2606.15017을 "미확인"에서 **"확인됨(EMNLP 2026, ServiceNow). 웹, 온라인 설정에서 AWM, ASI, ReasoningBank가 예산을 맞춘 기본 방법을 넘지 못함"**으로 바꾼다. main.tex 172행의 "같은 토큰 예산의 메모리 없는 방법"에 이 논문을 인용 근거로 달 수 있다. 조건(웹 에이전트, 온라인 보강, 작업끼리 독립)을 함께 적는다.
2. M10 후보 순서를 바꾼다.
   1. Evo-Memory의 **ExpRAG**(HIGH, GDM)를 기본 골격과 강한 기준 방법으로 둔다.
   2. ReasoningBank 형식의 교훈 추출. 라벨은 센서 술어로 한다.
   3. ACE 정리는 오프라인에서만 하고, 항목 퇴출과 개수 상한을 더한다.
   4. Dynamic Cheatsheet는 비교 기준으로 유지한다.
3. **Jev 메모리 규칙을 새로 둔다**: 원시 경험과 교훈 목록은 넣지 않는다. Astra가 계획할 때 컴파일한 typed 규칙 가운데 (스킬, 결정 지점, 술어)가 정확히 일치하는 0~2개만 넣는다. 근거는 MemCompiler(MED)와 ExpWeaver(MED-LOW)이고, **로봇 미적용**이다.
4. **라벨 규칙**: 센서 술어로 확정한 것만 Jev 규칙의 재료로 쓴다. Astra 판정은 "미검증" 태그를 달고 Astra 참고용으로만 쓴다. 근거는 2606.15017 표 10과 Evo-Memory 표 3.
5. ViReSkill을 LOW로 내린다(인용 2, 스타 0). "성공 계획 재생"은 Astra 첫 계획의 초안 용도로만 남긴다.
6. 평가
   - 메모리 on/off, 예산을 맞춘 기본 방법(아낀 토큰과 시간을 Astra effort나 호출에 쓰기), 라벨 방식(센서 대 자기 판정), Jev 힌트 방식(없음, 통째, 컴파일 규칙, 필요할 때만)을 ablation으로 비교한다.
   - **3회 이상 실행한 평균 ± 표준편차**를 보고한다(2606.15017의 권고).
7. [결정 필요] Astra 메모리 전달: top-k 기본 주입과 도구 호출로 필요할 때 조회하는 방식 중 어느 것을 쓸지, 아니면 둘 다 비교할지.
8. [결정 필요] Jev "필요할 때만" 재질의를 M4의 계단식 호출과 합칠지.

---

## 6. 확인 못 한 것
- ExpWeaver 주 결과의 수치(그림에만 있음). Init-only와 Always-on 대비 이득의 크기.
- MemAct의 학회: Semantic Scholar에만 ACL로 나오고 연도와 본문 채택 표기는 확인하지 못했다.
- 2606.15017 부록 C(가지치기가 보강 방법들에 미치는 효과)와 부록 D(더 큰 예산)의 수치.
- MemCompiler의 규칙 기반 공개와 학습 컴파일러의 직접 수치 비교가 있는지.
- ASI(2504.06821)와 SkillWeaver(2504.07079)의 학회 채택. Semantic Scholar venue는 arXiv로만 나오고, 인용은 각각 94, 142였다.
- Evo-Memory와 MemoryArena의 코드 저장소 스타 수(MemoryArena 저장소 이름을 찾지 못했다).
- ACE, ReasoningBank, ExpRAG를 같은 벤치마크에서 직접 비교한 결과(찾지 못함).
- "고정 API 모델 계층(느린 상위 + 빠른 하위)에서 상위가 하위용 메모리를 컴파일하는" 선행 연구: 3.3절의 검색어로는 찾지 못했다. arXiv API가 막혀서 검색 폭이 좁다. 부재를 주장하지 않는다.
- Jev에 텍스트 힌트를 넣었을 때 선택지 확률이 어떻게 바뀌는지: 문헌이 없고, 실험해야 한다.
