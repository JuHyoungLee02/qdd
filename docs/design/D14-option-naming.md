# D14 Jev 보기 이름·식별자 일반 관행 조사 (D32, user-log 25)

저장: 2026-09-24 03:24 UTC(`date -u`). 조사 에이전트 보고 전문. 메인 원문 재확인: Type-Safe HTML "neutral renaming alone costs 52.42% of answers"·표 as shipped .5637 / neutral A, B, C .2782·"directional support for the binary result rather than as a second headline"·호스트 "32.50% … 2.08% and 1.67%"·"at most 1.33%"·"Opaque names land on the neutral class"·"positional rather than semantic" / Pydantic TypeSafe 문서 "name Literal and Enum options for what they mean"·"reordering them can move the answer. If a classification matters, test it with the options in more than one order." 모두 일치.

## 조사 보고: Jev 보기 이름·식별자의 일반 관행과 D32 적용안 (2026-09-24)

D:\qdd는 읽기만 했습니다. 먼저 D12의 Type-Safe 절, M3 §4.1(101~102행)·§4.6, M6 §4.1.2(191행), E-first-experiments §2A(E0.5)·§3.2(H1-c), 00-interfaces 232행을 읽었습니다. 00-interfaces 232행에는 "조사 결과의 일반 관행을 기본 규칙으로 적용하고 E0.5 (i)는 확인 실험으로 유지"라고 되어 있습니다.

### 핵심 발견
Type-Safe 논문을 본문까지 다시 읽으니 **권고 범위가 D12 요약보다 좁았습니다.**
- 중립 식별자 권고의 근거는 **2지선다**에 한정됩니다.
- **3지선다 이상**에서는 같은 논문 §4.5가 반대 방향을 보입니다. 중립 문자로 바꾸면 정답률이 절반으로 떨어지고, 설명이 거의 무시되며, 답이 위치를 따라갑니다.
- 따라서 "모든 보기를 중립 식별자로"는 이 논문 자체로도 뒷받침되지 않습니다.

---

## 1. 보기 이름·기호 편향 문헌

**[A] 2609.26758 Type-Safe Is Not Error-Free** (v1 2026-09-22, abs와 HTML 본문을 curl로 원문 확인)
- 실험 설계: 보기 이름과 루브릭의 대응만 바꿉니다. aligned 판은 제품 그대로이고, swapped 판은 두 이름 사이에서 루브릭을 맞바꿉니다. 대상은 워크플로 결정 1,200개입니다.
- 이름 종류별 결과(marker 헤드):

| 이름 | aligned BA | swapped BA | AUROC(aligned → swapped) | flip |
|---|---|---|---|---|
| no/yes | .8719 | .2839 | .9376 → .2315 | 76.92% |
| false/true | .9012 | .4861 | — | 49.67% |
| 0/1 (대조) | .8368 | — | .9420 → .9243 | 6.50% |
| A/B (대조) | — | — | — | 6.00% |

- aligned 판만 보면 의미 있는 이름(no/yes)이 0/1보다 약간 높습니다. 대신 이름과 루브릭이 어긋나면 결과가 뒤집힙니다.
- **호스트 Jev** 원문: "Exchanging the rubrics behind no and yes changes 32.50% of its answers against 2.08% and 1.67% for the two neutral controls … balanced accuracy moves .7127 → .5163".
  - test-retest 바닥: "the answer changes at most 1.33% of the time when nothing changes. The swap is 24× that floor, and the two neutral controls sit on it."
- **무작위 문자열 이름**(xg6a6/e97ce 등 15쌍): 원문 "Opaque names land on the neutral class in all three families".
  - 호스트에서 0/1·A/B와의 차이는 0.14pt입니다(95% CI [−0.38, 0.67]).
- **3지선다 이상(§4.5, 표 4, n=683, k∈{3,4,5,6,16})** 원문: "renaming the members to neutral letters — without touching a single description — changes 52.42% of answers and drops accuracy from .5637 to .2782".
  - numbered 이름: .2592. 설명과 어긋나게 돌린 이름: .1552, 답 79.65% 변경.
  - 원문: "at higher cardinality the descriptions are close to ignored. Neutral renaming at k=16 lands at .141, which is exactly the share of those items whose gold member happens to sit first (.1406), i.e. positional rather than semantic."
  - 단서 1: 저자들은 이 결과를 "directional support … rather than as a second headline"으로만 둡니다.
  - 단서 2: 이 표가 어느 모델로 잰 것인지 본문에서 명시 문장을 찾지 못했습니다. 문맥상 로컬 헤드이고 **호스트 Jev는 아닌 것으로 봅니다.**
- 권고 원문: "Use neutral option identifiers and carry the meaning in the rubric, which on our data costs 6.50% instability instead of 76.92%".
- 보고 권고 원문: "The flip rate against neutral option names is a practical candidate: it requires no labels, costs two extra forward passes per item."

**[B] 2603.21016 PA-GRPO** (2026-03-22) [초록만]
- 원문: "often exhibit selection bias due to non-semantic factors like option positions and label symbols".
- 해법은 학습 쪽입니다(순열 그룹과 일관성 보상). Jev에는 가중치를 건드릴 수 없어 쓸 수 없고, "순열 사이 일관성 = 목표"라는 관점만 가져옵니다.

**[C] 2509.02452 Do LLMs Adhere to Label Definitions?** (2025-09-02) [초록만]
- 원문: "their integration into an LLM's task-solving processes is neither guaranteed nor consistent … Models often default to their internal representations".
- 이름의 사전 의미가 정의를 이기는 경향을 보여 [A]를 지지합니다.

**[D] 2602.02219 루브릭 기반 LLM 판정의 위치 편향** (2026-02-02, 초록과 HTML 일부)
- 원문: "rubric-based evaluation implicitly resembles a multiple-choice setting and therefore exhibits position bias … Its direction, however, is model-specific".
- 순열 효과: "roughly two-thirds of the K=1→10 improvement is reached by K=3 and about 85% by K=5". 균형 순열과 무작위 순열의 차이는 CI가 0을 포함한 칸이 12칸 중 11칸입니다.
- 집계는 K번 읽은 점수의 평균입니다.
- Jev Score에 관련됩니다. 다만 Jev API 문서는 Score 수준의 순서가 숫자 자체로 정해져 선언 순서가 무관하다고 적습니다(검색 요약으로 확인).

**[E] 2604.16790 Bias in the Loop** (2026-04-18) [초록만]
- 원문: "several biases systematically shift preferences toward the option favored by the prompt, improving accuracy when that option aligns with the gold answer but substantially reducing it otherwise".
- "이름이 맞으면 이득, 어긋나면 손해"라는 [A]와 같은 구조입니다.

**기초 문헌 (기간 밖)**
- 2309.03882 PriDe (2023-09-07, ICLR 2024, PDF 원문 확인)
  - 원문: "replace the default ID symbols A/B/C/D with … a/b/c/d, 1/2/3/4, and (A)/(B)/(C)/(D), but observe no remarkable reduction in RStd".
  - 표 2(gpt-3.5): IDs 제거 시 RStd 5.5 → 1.0입니다.
  - Cyclic Permutation 원문: "reduces the computational cost … from n! to n and ensures one pairing between each option ID and option content".
- 2308.11483 (2023-08-22): 순서만 바꿔도 "approximately 13% to 75%" 성능 차가 납니다. 원인은 상위 2~3개 보기 사이의 불확실성입니다.
- 2210.12353 MCSB (2022-10-22): 기호와 보기 내용을 묶는 능력("symbol binding")은 모델마다 크게 다릅니다.
- 2406.07791 Judging the Judges (2024-06-12): 위치 편향은 "not due to random chance"이고, 후보 사이 품질 차가 작을수록 커집니다.

## 2. 업체 공식 지침

**TypeSafe/Pydantic AI 통합 문서** (https://pydantic.dev/docs/ai/models/typesafe/, jev-1.13.0 기준) — 사실상 공식 지침입니다.
- 원문: "Unless the schema describes an option, Jev sees it by its name alone, so name `Literal` and `Enum` options for what they mean."
  - 보기 설명은 `UseEnumMemberDocstrings` docstring이나 Choices 매핑으로 붙입니다.
- 원문: "The order of a `Literal`'s options or an `Enum`'s members is part of what Jev sees, and reordering them can move the answer. If a classification matters, test it with the options in more than one order."
- Score는 수준마다 설명이 필수입니다. 설명 없는 bare `Literal[0,1,2]`는 UserError입니다.

**Jev 1.13 jaggedness 문서** (docs.typesafe.ai/model-jaggedness/jev-1.13)
- 보기 이름에 대한 항목은 없습니다.
- 관련 항목은 두 가지입니다. 복잡한 부정과 간접 참조가 정확도를 깎는다는 것, 그리고 Noul과 그 부정이 합쳐 1이 된다고 가정하지 말라는 것입니다.

**OpenAI Structured Outputs 가이드**
- "Name keys clearly and intuitively" / "Create clear titles and descriptions for important keys" / "Create and use evals to determine the structure that works best".

Anthropic 분류(ticket routing) 가이드는 검색 요약만 봤습니다. "잘 정의된 범주 목록"을 강조하지만 원문 인용은 확인하지 않아 근거로 쓰지 않습니다.

## 3. 로봇·에이전트의 후보 행동 선택

**2506.12374 AntiGrounding** (v1 2025-06-14, v4 2026-09-18, HTML 확인)
- 후보 궤적에 **중립 ID T1–T8**을 붙입니다. 원문: "Each candidate carries a consistent identifier and a distinct color across rendered views."
- 뜻은 그림(궤적 렌더)이 담고, VLM은 후보마다 1–10점을 매깁니다. 하나를 고르게 하지 않고 후보별 점수를 매기는 방식입니다.

**2605.12620 VeGAS** (2026-05-12) [초록만]
- 후보 행동을 여러 개 샘플하고 검증기가 고릅니다.
- 원문: "using an MLLM off-the-shelf as a verifier yields no improvement".

**기간 밖 계열**
- PIVOT/SoM 계열은 이미지 위 번호를 쓰고, SayCan·Code-as-Policies 계열은 의미 있는 스킬·함수 이름을 씁니다.
- 로봇 쪽에서 "의미 있는 이름 대 중립 ID"를 직접 비교한 논문은 찾지 못했습니다.

---

## (a) 일반 관행: 합의된 점과 갈리는 점

**합의된 점 (근거 여러 개)**
1. 이름·기호·위치 모두 답을 움직입니다. 기호만 바꿔서는 편향이 안 없어집니다(PriDe, Pydantic, [A], [D]).
2. 보기마다 뜻을 적은 설명을 붙입니다(업체 공통).
3. 이름이 설명과 어긋나거나 평가를 암시하면 최악입니다. [A]의 swap과 rotated, [E]가 보여 줍니다.
4. 순서를 두 가지 이상 바꿔 검사합니다. 운영에서는 소수 순열(K=3)로 집계하는 것이 표준 완화책입니다(PriDe cyclic, [D], 업체 문서).
5. 이름·순서 불변성 수치를 정확도와 함께 보고합니다([A], [E]).

**갈리는 점**
- **중립 ID 대 의미 있는 이름.**
  - 업체(TypeSafe/Pydantic, OpenAI)는 "뜻대로 이름 붙여라"라고 합니다.
  - [A]는 2지선다에 대해 중립을 권하지만, 같은 논문의 3지선다 이상 자료는 중립 문자가 설명을 무력화한다고 보입니다.
  - 정리: 2지선다·극성 보기에는 중립 ID, 3지선다 이상에는 내용을 그대로 적은 이름이 현재 근거에 가장 맞습니다.
- 중립 ID와 무작위 문자열은 호스트 Jev에서 구별되지 않습니다(0.14pt). 문자열 모양은 문제가 아닙니다.

## (b) 우리 Jev 질문에 적용할 규칙 (D32 적용안)

**R1. 모든 질문에 지금 바로 적용** (근거가 합의된 부분, 호출 추가 없음)
- 모든 보기에 설명을 붙입니다(Choices 매핑이나 docstring). 이름만 있는 보기는 금지합니다.
- 이름은 설명의 앞머리를 줄인 형태여야 하고, 설명에 없는 뜻을 담으면 안 됩니다.
- 이름 금지어:
  - 극성·판정어: yes/no/true/false/ok/fail/accept/reject/good/bad/safe/correct 등.
  - 조건을 품은 이름: 예를 들어 `descend_if_aligned`처럼 조건을 담지 말고, 조건은 설명에만 적습니다.
- 내부 키와 표시 이름을 분리합니다. 원장·M4 합의·결과 라벨은 고정된 `option_key`(보기 id)로 쌓습니다. 표시 이름, 표시 순서, `perm_id`는 호출마다 요청 기록에 남깁니다.

**R2. 2지선다와 극성 질문**
- Choice 2개로 묻는 결정 지점은 중립 ID(`A`/`B`, 또는 5자 무작위 문자열)를 쓰고 뜻은 설명에만 적습니다. 호스트 Jev에서 이름 효과가 바닥 수준(1.67~2.08% 대 1.33%)으로 떨어지는 직접 근거가 있습니다.
- Noul은 true/false 채널이 고정이라 이름을 바꿀 수 없습니다. 기준 문장을 부정 없이 긍정형으로 씁니다(jaggedness 문서).
- 비용: 이름 뜻 때문에 aligned 정확도가 조금 빠질 수 있습니다(marker 헤드에서 .8719 → .8368, 3.5pt).

**R3. 3지선다 이상의 행동 보기** (방향, 목표 객체, 크기, 최대 17개)
- 지금처럼 내용을 그대로 적은 이름(`+x`, `cup_red`, `≈2cm` 등)에 설명을 더해 유지합니다. 중립 문자로 바꾸지 않습니다([A] §4.5의 역방향 증거, 업체 지침, E1 H1-c와도 같은 방향).
- `side_front`나 `close_now`처럼 행위를 담은 이름도 R1 금지어에 걸리지 않으면 유지합니다.
- 이 규칙은 **E0.5 (i) 결과로 확정**합니다. [A]의 3지선다 이상 결과가 호스트 Jev에서 잰 것이 아니기 때문입니다.

**R4. 순서**
- 기본은 `question_id`마다 고정된 표준 순서입니다(M3 §3). `NONE_ESCALATE`는 항상 마지막에 둡니다.
- 순서 순환(C3'')은 지금처럼 E-M4 조건으로 둡니다.
- 켜는 경우 M4 시간차 호출 2~3회에 순열 3개를 돌려 붙이므로 **추가 호출은 0**입니다. 대가는 두 가지입니다.
  - 합의가 "같은 입력"이 아니게 되어, 불일치가 상태 변화에서 왔는지 순서 효과에서 왔는지 섞입니다.
  - `flip_score`가 부풀 수 있어 FLIP_TH를 C3'' 조건에서 따로 보정해야 합니다(M3 §4.6 위험 목록과 같음).
- 같은 시각 순열 평균(K=3번 동시 호출)은 호출이 3배라 운영 기본으로 권하지 않습니다.

**R5. M4 합의와의 관계**
- 합의와 최빈 계산은 반드시 `option_key`로 되돌려 셉니다.
- 2지선다 중립 ID에서 ID와 내용의 짝을 순열마다 바꾸는 경우(PriDe cyclic처럼 A↔B를 교대로 배정), 호출마다 `display_id → option_key` 대응표를 기록해야 합니다.
- 확률 평균은 쓰지 않고 최빈 보기만 셉니다. Jev #8과 M3 §4.6 방침 그대로입니다.

**R6. 일관성 검사**
- 이름 불변성 flip([A]가 권한 수치, 보기당 호출 +1~2회)은 **오프라인 E0.5·E1에서만** 잽니다. 운영 중에는 켜지 않습니다.

## (c) E0.5 (i) 시험 설계

지금 설계(의미 있는 이름 대 중립, 순서 고정)를 다음처럼 늘릴 것을 제안합니다.

**판 구성** (같은 스냅샷, 같은 문구, 같은 설명)
- A0: 지금 이름
- A1: 중립 문자
- A2: 무작위 5자 문자열
- A3: 이름을 설명과 한 칸 어긋나게 돌린 판. 이름과 설명 중 무엇을 따르는지 재는 진단용이며, [A]의 rotated·swapped에 해당합니다.
- A4: 이름은 A0 그대로, 순서만 한 칸 순환
- (ii) test-retest 바닥: A0 반복, 호출 2회 이상

**층 구분**
- 2지선다·Noul / k=3~6 / k=7~17로 나눕니다. [A]가 층마다 반대 방향을 예측하기 때문입니다.

**지표**
- A0 대비 flip(`option_key` 기준)
- 판별 결과 기반 정답률(기존 롤아웃 라벨러)
- A3에서 답이 이름의 원래 뜻을 따른 비율(이름 추종률)
- 첫 자리 선택률 대 정답이 첫 자리에 있는 비율(위치 추종, [A] k=16 진단)

**판정 (사전 등록 제안)**
- 층마다 판단합니다.
- 중립 ID로 전환하는 조건 두 가지를 모두 만족할 때:
  - A1 정답률 ≥ A0 − 2pt (짝 부트스트랩 하한 기준)
  - A3 이름 추종률이 (ii) 바닥보다 유의하게 큼
- 이름을 유지하는 경우: A1 정답률이 A0보다 낮고 차의 95% 하한이 0보다 클 때.
- 순서: A4 flip이 5% 이상이면 C3''를 필수 조건으로 올립니다(E-M3-1 판정 4와 같음).
- 기존 판정 8(치환 flip > 바닥)은 유지하되, 정답률 차 없이 "바꿀 근거"로 읽지 않도록 위 조건을 더합니다.

**표본과 비용**
- [A]는 2지선다 1,200개, 호스트 300개로 1.33% 대 32.5%를 갈랐습니다.
- 우리는 층마다 결정 스텝 300개 이상 × 판 5개 × 반복 2회 ≈ 층당 약 3천 요청, 세 층 합쳐 약 9천 요청입니다.
- 기존 단가(1.5만 요청 ≈ $1)로는 약 $1 미만입니다. [우리 계산]
- 결과 라벨 롤아웃은 기존 라벨러를 그대로 씁니다. 판 수만큼 늘지는 않고, 보기별 라벨은 한 번이면 됩니다.

**결론**
D32는 (i)과 (ii)를 섞은 안을 권합니다.
- R1·R2·R4·R5·R6(설명 필수, 극성·평가 이름 금지, 내부 키 분리, 2지선다 중립 ID)은 지금 기본으로 적용합니다.
- R3(3지선다 이상의 이름 방식)만 E0.5 (i) 결과로 확정합니다.

## 한계
- [A]의 호스트 결과는 2지선다만 있습니다. 3지선다 이상 결과의 모델은 명시 문장을 찾지 못했습니다(로컬 헤드로 추정).
- [B], [C], [E], VeGAS는 초록만 읽었습니다.
- Pydantic 문서와 OpenAI 문서는 WebFetch 요약기로 인용한 문장입니다. PriDe와 [A]는 원문 텍스트를 직접 확인했습니다.
- 로봇 쪽 "의미 있는 이름 대 중립 ID" 직접 비교는 찾지 못했습니다.

주요 파일(읽기만): D:\qdd\docs\design\D12-preemption-0901-0924.md, D:\qdd\docs\design\M3-action-representation.md, D:\qdd\docs\design\M6-skills-jev.md, D:\qdd\docs\design\E-first-experiments.md(§2A, §3.2 H1-c).
