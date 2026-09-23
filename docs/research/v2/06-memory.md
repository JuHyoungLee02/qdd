# M10 경험 축적 (고정 API 모델) 검증 보고서 (v2, 2026-09-23)

대상: `docs/plan.md`의 M10 항목과 작업 지시에 들어 있던 인용 항목.
기준 기간: 1.5년 이내(2025-03-23 이후). LLM+스킬 논문은 1년 이내(2025-09-23 이후).

## 0. 조사 한계 (먼저 읽을 것)
- 이 세션에서 WebSearch 호출 한도(세션 전체 200회)가 이 모듈 조사 중간에 바닥났다. 그래서 **IOM (2607.23702), H2-EMV (2604.11306), 예산 제약 연구 (2606.15017), ExpWeaver (2605.07164)는 한 번도 검색하지 못했다.** 이 네 개는 존재 여부도 확인되지 않았다(UNCONFIRMED).
- arxiv.org, export.arxiv.org, huggingface.co 직접 접근은 프록시에서 막혔다(직접 시도해서 확인).
- 그래서 "2026년 최신 방법 조사"와 "메모리 방법 비교 벤치마크 조사"는 거의 하지 못했다. 다른 검색 결과에 제목만 잠깐 나온 논문들은 5절에 "확인 필요"로만 적었다. 추천 순위에는 넣지 않았다.
- 수치는 모두 검색 결과 요약(초록, 학회 페이지, 2차 글)에서 가져왔다. 원문 표로 확인한 것은 없다.

---

## 1. 검증 표

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| **ACE**: Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models, arXiv 2510.04618 (v1 2025-10-06) | CONFIRMED-MULTI | 기간 안. **ICLR 2026 채택** (Stanford, SambaNova, UC Berkeley). "+10.6% (agents), +8.6% (finance)" 확인. playbook을 generation, reflection, curation 세 단계로 키우고, delta를 덧붙이며, embedding으로 중복을 지우는 grow-and-refine 방식이다. 이 설명은 plan과 맞다. AppWorld에서 DeepSeek-V3.1 + ReAct + ACE가 59.4%로, GPT-4.1 기반 IBM CUGA(60.3%)와 비슷했다. | https://arxiv.org/abs/2510.04618 , https://proceedings.iclr.cc/paper_files/paper/2026/file/8a94ff6f922d995d7d3f4ebf4143e442-Paper-Conference.pdf , https://mlanthology.org/iclr/2026/zhang2026iclr-agentic/ , https://sambanova.ai/blog/ace-open-sourced-on-github |
| ACE "86.9% 지연 감소" | CONFIRMED-MULTI, **해석 정정 필요** | 줄어드는 것은 **적응(adaptation) 지연**이고, 추론 지연이 아니다. offline에서 GEPA 대비 82.3%, online에서 Dynamic Cheatsheet 대비 91.5%이고, 86.9%는 평균이다. 추론할 때 Astra 호출이 빨라진다는 근거로 쓰면 틀린다. | https://machinelearningatscale.substack.com/p/agent-context-engineering , https://www.marktechpost.com/2025/10/10/agentic-context-engineering-ace-self-improving-llms-via-evolving-contexts-not-fine-tuning/ |
| ACE는 검색(retrieval)을 하나, playbook 전체를 넣나 | CONFIRMED-MULTI | **playbook 전체를 문맥에 넣는 방식**이다. 유사도로 top-k를 꺼내는 방식이 아니다. embedding은 중복 제거에만 쓴다. 저자들은 평가 때 입력 토큰이 더 많을 수 있다고 인정한다. 대신 KV cache 재사용으로 실제 비용이 선형으로 늘지는 않는다고 주장한다. 따라서 Jev처럼 호출마다 지연에 민감한 모델에 그대로 붙이는 방식은 맞지 않는다. | https://arxiv.org/pdf/2510.04618 , https://www.tinyfish.ai/blog/agentic-context-engineering |
| **ReasoningBank**: Scaling Agent Self-Evolving with Reasoning Memory, arXiv 2509.25140 (2025-09-29) | CONFIRMED-MULTI | 기간 안. **ICLR 2026 poster**, Google Cloud AI Research (Siru Ouyang, Jun Yan 외). 공식 코드: google-research/reasoning-bank. 정정: plan은 "WebArena +8.3%"라고 썼지만 정확히는 "**최대(up to) 8.3%p**"다. 성공과 실패 모두에서 교훈을 뽑는다는 설명은 맞다. 다만 성공/실패 라벨은 **self-judged**(LLM이 스스로 판정)다. plan이 제안한 "센서/술어로 판정"은 원 논문과 다른 설정이다. MaTTS(memory-aware test-time scaling) 확인. 벤치마크는 WebArena, Mind2Web, SWE-Bench-Verified. | https://arxiv.org/abs/2509.25140 , https://iclr.cc/virtual/2026/poster/10007887 , https://mlanthology.org/iclr/2026/ouyang2026iclr-reasoningbank/ , https://www.marktechpost.com/2026/04/23/google-cloud-ai-research-introduces-reasoningbank-a-memory-framework-that-distills-reasoning-strategies-from-agent-successes-and-failures/ |
| **Memento**: Fine-tuning LLM Agents without Fine-tuning LLMs, arXiv 2508.16153 | CONFIRMED-MULTI (수치), 학회 UNCONFIRMED | 기간 안. GAIA validation 87.88%는 **Pass@3** 기준이다(인용할 때 반드시 Pass@3라고 밝혀야 한다). GAIA test 79.40%, DeepResearcher 66.6% F1 / 80.4% PM, OOD에서 case memory가 +4.7~9.6%p 올렸다. M-MDP와 신경망 case-selection policy를 쓰고, LLM은 고정한다는 plan 설명도 맞다. HF 페이지에는 이름이 **AgentFly**로 바뀌어 있다. 학회 채택과 저자 소속은 확인하지 못했다. | https://arxiv.org/abs/2508.16153 , https://huggingface.co/papers/2508.16153 , https://www.emergentmind.com/papers/2508.16153 |
| **Dynamic Cheatsheet**: Test-Time Learning with Adaptive Memory, arXiv 2504.07952 (2025-04-10) | CONFIRMED-MULTI | 기간 안(간신히). **EACL 2026 long** (Suzgun, Yuksekgonul, Bianchi, Jurafsky, Zou; Stanford). GPT-4o의 Game of 24가 10%에서 99%로, Claude 3.5 Sonnet의 AIME 정확도가 2배 이상으로 올랐다. ACE 논문의 online 비교 대상이기도 하다. | https://aclanthology.org/2026.eacl-long.333/ , https://arxiv.org/abs/2504.07952 |
| **Mem0**: Building Production-Ready AI Agents with Scalable Long-Term Memory, arXiv 2504.19413 | CONFIRMED-MULTI (수치), 신뢰도 논쟁 있음 | 기간 안. Mem0.ai 회사 논문이고 arXiv에만 있다(학회 확인 못 함). LOCOMO에서 OpenAI memory 대비 상대 26%(LLM-as-judge), p95 지연 91% 감소, 토큰 90% 이상 절감이라고 주장한다. **Zep이 공개 반박했고 LOCOMO 설정을 두고 공급사끼리 분쟁이 있다.** 대화형 개인화 메모리라서 로봇 절차 경험과 맞지 않는다. | https://arxiv.org/pdf/2504.19413 , https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/ , https://www.developersdigest.tech/blog/best-ai-agent-memory-providers-2026 |
| **A-MEM**: Agentic Memory for LLM Agents, arXiv 2502.12110 | CONFIRMED-MULTI, **기간 밖** | NeurIPS 2025 (Xu, Liang, Mei, Gao, Tan, Yongfeng Zhang; Rutgers 계열 agiresearch). arXiv가 2025-02라서 **1.5년 기준(2025-03-23)을 벗어난다.** 역시 대화형 메모리(Zettelkasten 방식)다. | https://proceedings.neurips.cc/paper_files/paper/2025/hash/19909c36f51abc4856b4560aff3d36d6-Abstract-Conference.html , https://arxiv.org/abs/2502.12110 |
| **ViReSkill**: Vision-Grounded Replanning with Skill Memory for LLM-Based Planning in Lifelong Robot Learning, arXiv 2509.24219 (2025-09) | 수치 CONFIRMED-MULTI (초록과 그 사본들), 학회 UNCONFIRMED | LIBERO 45→78%, RLBench 47→82%, 실제 로봇 30→75% 확인. 비교 대상은 초록에 "a baseline"이라고만 되어 있어서 무엇인지 확인하지 못했다. 성공한 계획을 skill로 저장하고 다음에는 LLM/VLM 호출 없이 재생한다는 설명도 확인했다. Panasonic Connect와 Panasonic R&D Singapore(Kagaya 외)가 썼다. ICRA/IROS/RA-L 채택은 확인하지 못했다. 공식 GitHub(PanasonicConnect/vireskill)가 있지만 스타 수는 확인하지 못했다. 1년 기준 경계: 2025-09 말에 올라왔으므로 LLM+스킬 1년 기준(2025-09-23)에 걸치는지 날짜를 확인해야 한다. | https://arxiv.org/abs/2509.24219 , https://www.alphaxiv.org/overview/2509.24219v1 , https://github.com/PanasonicConnect/vireskill |
| **MTP**: Memory Transfer Planning: LLM-driven Context-Aware Code Adaptation for Robot Manipulation, arXiv 2509.24160 | CONFIRMED-MULTI (존재, 방법), 학회 UNCONFIRMED | ViReSkill과 같은 그룹(Kagaya 외, Panasonic + NUS Yang You). plan은 "실패하면 비슷한 성공 코드를 꺼내 고친다"고 썼는데, 정확히는 "초기 계획 → code memory에서 비슷한 성공 예시 검색 → 대상 환경에 맞게 고쳐서 재계획"이다. 큰 틀은 맞다. RLBench 평균 64.4% (VoxPoser 39.3%), CALVIN 52.0→67.3%. 날짜가 1년 기준 경계에 있다. | https://arxiv.org/abs/2509.24160 , https://www.themoonlight.io/en/review/memory-transfer-planning-llm-driven-context-aware-code-adaptation-for-robot-manipulation |
| IOM, arXiv 2607.23702 | **UNCONFIRMED** | 검색 한도가 바닥나서 한 번도 확인하지 못했다. 존재, 제목, 내용 모두 모른다. 인용 금지. | 없음 |
| H2-EMV, arXiv 2604.11306 | **UNCONFIRMED** | 위와 같다. 인용 금지. | 없음 |
| 예산 제약 연구, arXiv 2606.15017 ("같은 토큰 예산이면 메모리 없는 기본 에이전트가 비슷하거나 더 낫다") | **UNCONFIRMED** | 위와 같다. **plan과 `paper/main.tex` 157행에 이미 인용되어 있으니, 확인 전까지는 빼거나 "미확인"으로 표시해야 한다.** 다만 "같은 예산의 no-memory baseline을 넣는다"는 실험 설계 자체는 이 논문과 상관없이 타당한 통제 조건이다. | 없음 |
| ExpWeaver, arXiv 2605.07164 ("매 스텝 주입보다 필요할 때만 꺼내는 게 낫다") | **UNCONFIRMED** | 위와 같다. 인용 금지. | 없음 |

---

## 2. 더 나은 대안 / 최신 SOTA
확인된 범위에서만 적는다.

- **신뢰도가 높은 LLM 쪽 방법 세 개**: ACE (ICLR 2026), ReasoningBank (ICLR 2026), Dynamic Cheatsheet (EACL 2026). 셋 다 고정 LLM의 문맥이나 메모리만 바꾸는 방식이라 API 모델(Astra)에 바로 쓸 수 있다. 셋의 관계는 이렇다.
  - ACE는 Dynamic Cheatsheet와 GEPA를 비교 대상으로 두고 이긴다고 보고했다. [ACE 논문, 위 출처]
  - ReasoningBank는 "원시 궤적 저장"이나 "성공 루틴만 저장"하는 방식(즉 AWM류)보다 낫다고 보고했다. [https://arxiv.org/abs/2509.25140]
  - **ACE와 ReasoningBank를 같은 벤치마크에서 직접 비교한 결과는 찾지 못했다.** 둘 중 무엇이 "최고"인지는 확인되지 않았다.
- **Memento**: GAIA 수치가 가장 강하다. 하지만 Pass@3 기준이고 학회 채택은 확인하지 못했다. 작은 case-selection policy를 따로 학습해야 한다.
- **로봇 분야**: ViReSkill과 MTP가 구조적으로 가장 가깝다. 둘 다 같은 Panasonic 그룹이고 학회 채택은 확인하지 못했다.
- **2026년 최신 방법과 메모리 비교 벤치마크**: 검색 한도 때문에 조사하지 못했다(5절 참고).

### 이득 대비 토큰/지연 (Astra는 느리고 Jev는 싸다)
- **Astra 호출 자체를 없애는 방식**(ViReSkill: 성공한 계획을 저장했다가 LLM 없이 재생)이 지연을 가장 많이 줄이는 것은 구조상 당연하다. 다만 지연을 정량으로 측정한 결과는 확인하지 못했다.
- **ACE의 효율 수치는 적응 쪽이다.** 추론할 때는 playbook 전체가 들어가서 입력 토큰이 오히려 늘 수 있다. 저자들은 KV cache 재사용으로 이를 상쇄한다고 주장한다. [https://arxiv.org/pdf/2510.04618] 따라서 Astra에는 prompt caching이 되는 경우에만 유리하고, Jev에 호출마다 넣으면 지연이 늘어난다(추론).
- **Mem0의 91% 지연 감소**는 대화 QA에서 전체 대화를 넣는 방식과 비교한 수치라서 이 문제에 옮겨 쓸 수 없다.

### Jev(텍스트 전용, typed 출력)가 메모리를 쓸 수 있나
- **직접 다룬 논문은 찾지 못했다.**
- 위 방법들은 모두 "텍스트를 문맥에 넣는" 방식이라 원리상 텍스트 입력 모델이면 붙일 수 있다(추론, 사실 아님).
- 제약은 호출당 지연이다. 그래서 ACE처럼 전부 넣는 것보다 ReasoningBank처럼 top-k 검색으로 짧게 넣는 방식이 맞을 것으로 본다(추론).
- Jev의 선택지 확률이 메모리 유무에 따라 어떻게 바뀌는지는 실험으로 확인해야 한다.

---

## 3. 반대 증거와 위험
- **plan의 핵심 반론(2606.15017)과 ExpWeaver는 확인하지 못했다.** 확인되지 않은 반론에 기대는 설계 결정은 보류해야 한다.
- **자기 판정 라벨**: ReasoningBank는 self-judged 라벨을 쓴다. plan이 제안한 "센서/술어 라벨"은 논문이 검증한 설정이 아니다. 효과가 같을지는 실험해 봐야 안다.
- **벤치마크 신뢰성**: 메모리 분야는 공급사가 각자 자기가 이기는 벤치마크를 내는 문제가 공개적으로 지적되었다(Mem0 대 Zep의 LOCOMO 분쟁). [https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/ , https://www.developersdigest.tech/blog/best-ai-agent-memory-providers-2026]
- **ACE의 긴 문맥 비용**: 저자들도 평가 때 입력 토큰이 늘 수 있다고 인정했다. [https://arxiv.org/pdf/2510.04618]
- **ViReSkill 재생의 위험**: 저장한 계획을 LLM 없이 재생하므로, 환경이 조금만 달라도 틀린 계획을 그대로 실행할 수 있다. 이 방식은 "LLM이라 일반화된다"는 핵심 메시지와 부딪칠 수 있다. 재생 조건을 어떻게 판정하는지는 원문에서 확인하지 못했다.
- **Memento 87.88%**: Pass@3 기준이라 Pass@1과 비교하면 안 된다.

---

## 4. 이 모듈에 장착할 모듈 후보 순위 (신뢰도 포함)

| 순위 | 모듈 | 역할 | 신뢰도 근거 | 판단 |
|---|---|---|---|---|
| 1 | **ReasoningBank** (성공과 실패에서 뽑은 전략 메모리 + 임베딩 top-k 검색) | Astra 재계획과 복구 때 교훈 주입. top-k로 짧게 넣으므로 Jev 입력에도 붙일 수 있는 후보 | HIGH: ICLR 2026, Google Cloud AI Research, 공식 코드 공개 | 추천. 라벨 방식(self-judge 대 센서)은 ablation으로 비교 |
| 2 | **ACE** (delta 덧붙이기, 중복 제거, reflector/curator) | 메모리를 정리하는 방법. 1번 은행이 커질 때 중복 병합과 반복 실패 통합 | HIGH: ICLR 2026, Stanford/SambaNova/Berkeley, 오픈소스 | 추천. 단, playbook 전체 주입은 Astra에만, 그것도 prompt caching이 될 때만 |
| 3 | **Dynamic Cheatsheet** | 가장 단순한 비교 기준(baseline) 메모리 | HIGH: EACL 2026, Stanford (Jurafsky, Zou) | 비교 기준으로 추천 |
| 4 | **성공 계획 재생 (ViReSkill 방식)** | 같은 작업이면 Astra 호출을 건너뜀. 지연 이득이 가장 큼 | MEDIUM-LOW: 산업 연구소, 학회 채택 미확인, 스타 수 미확인 | 개념만 조건부로 사용. 주요 근거로 인용하는 것은 채택 여부를 확인한 뒤에 |
| 5 | **Memento / AgentFly** (case bank + 학습된 선택 정책) | 사례 선택 정책 | MEDIUM: 수치는 강하지만 학회 미확인, 정책 학습이 필요 | 보류 |
| 제외 | Mem0 | | 회사 논문, 벤치마크 분쟁, 대화형 메모리 | 제외 |
| 제외 | A-MEM | | 기간 밖(2025-02), 대화형 메모리 | 제외 |
| 제외 | MTP | | 코드 생성 방식이라 우리 스킬+Jev 구조와 거리가 멂, 학회 미확인 | 제외 |
| 제외 | IOM, H2-EMV, 2606.15017, ExpWeaver | | 미확인 | 제외 |

---

## 5. 확인 못 한 것
- IOM (2607.23702), H2-EMV (2604.11306), 2606.15017, ExpWeaver (2605.07164): 존재, 제목, 저자, 수치 전부.
- 2026년 최신 메모리 방법과, 메모리 방법을 서로 비교한 벤치마크.
- ViReSkill과 MTP의 학회 채택 여부, GitHub 스타 수, 첫 버전 날짜(1년 기준 2025-09-23과 비교해야 함). ViReSkill 비교 대상 "baseline"이 무엇인지.
- Memento의 학회 채택 여부와 저자 소속.
- ACE와 ReasoningBank의 직접 비교 결과.
- 저자 블로그, 발표, X 글: SambaNova 블로그(ACE 공개)와 MarkTechPost 기사(ReasoningBank) 말고는 조사하지 못했다.
- **다른 검색 결과에 제목만 나온 논문들**(내용과 신뢰도 모두 미확인이라 추천하지 않음. 다음 조사 때 우선 확인할 목록):
  - MemCompiler: Compile, Don't Inject — State-Conditioned Memory for Embodied Agents (arXiv 2605.07594). 제목상 Jev처럼 상태를 조건으로 삼는 메모리와 관련이 있어 보인다. https://arxiv.org/pdf/2605.07594
  - Functional Cache Grafting: Robust and Rapid Code-Policy Synthesis for Embodied Agents (arXiv 2606.13097). https://arxiv.org/pdf/2606.13097
  - Learning and Transferring Closed-Loop Robot Software (arXiv 2609.19906). https://arxiv.org/html/2609.19906
  - Skills in Weights, Memory in Code: Hybrid Learning for Memory-Dependent Robot Manipulation (arXiv 2608.09410). https://arxiv.org/pdf/2608.09410
  - Memory as Action: Autonomous Context Curation for Long-Horizon Agentic Tasks (arXiv 2510.12635). https://arxiv.org/pdf/2510.12635
