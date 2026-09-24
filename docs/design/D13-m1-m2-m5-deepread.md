# D13 원문 정독: M1·M2·M5 핵심 원천

저장: 2026-09-24 02:11 UTC(`date -u`). 정독 에이전트 보고 전문(줄이지 않음). 메인 원문 재확인(에이전트가 받아 둔 원문 텍스트 대조): COPE "rather than a guideline (how to solve the task) as before"·Stage 2 "guideline-type plan" / AgentSpec "precision of 95.56% and recall of 70.96%"·"banned the pour action" / WAM "workable floor"·"hard position jump" / FluxVLA Table 11 1.17 ms·Xeon 8336C·"does not evaluate coupled-joint or Cartesian" / RTC 코드 `w * jnp.expm1(w) / (jnp.e - 1)` / AgileThinker abs 코멘트 "30 pages"뿐(ICLR 표기 없음). 모두 일치.


작성: 2026-09-24. D:\qdd의 저장소 파일은 하나도 고치지 않았다. curl만 썼고 요청 사이 간격은 3초다. WebSearch와 GitHub API는 쓰지 않았다.

**읽은 범위**
- 9편 모두 arXiv abs와 HTML 본문을 읽었다. PDF는 HTML로 충분해 열지 않았다.
- 코드는 RTC 저장소(`Physical-Intelligence/real-time-chunking-kinetix`)의 README와 `src/model.py`를 읽었다.

**원천을 고른 기준**: 설계의 기본값·문턱·근거 문장이 가장 많이 기대는 것부터 골랐다.
- M1: lmgame-Bench(수치 미추출 표시가 있던 것), ViPlan(술어 등급의 근거)
- M2: COPE(목표형 중심의 근거), AgentSpec(재현율 70.96%의 근거), AgileThinker(낡은 계약 처리 R1의 근거)
- M5: RTC(L2 가중 모양, T_b·τ_b), SEAM, WAM(블렌딩 반대 근거), FluxVLA Table 11(Ruckig 1.17 ms, "다음 검증 1순위")
- 뺀 것: CaP-X VDM은 D10a, FocusAgent·Read More는 D2, 관성화·HPF는 D4 검증이 이미 원문을 확인해서 이번 대상에서 뺐다.

---

## 요약: 설계 근거가 흔들리는 불일치 5건

1. **COPE (M2 §3 #1, §6-1)**
   - 큰 계획기가 작은 실행기를 도운 조건(Llama-3B 42.8 → 53.0)은 목표형이 아니었다. **절차형(guideline) 계획**이었다.
   - COPE 본 방법의 Stage 2도 큰 모델이 "guideline-type plan"을 준다.
   - "목표형 > 절차형"은 Llama-1B **자기 계획**에서만 나왔다.
   - 그래서 "절차 서술은 Jev에 보내지 않는다"의 근거로 COPE를 쓸 수 없다. 원문은 오히려 반대 방향이다.
2. **AgentSpec (M2 §3 #4·§6-8, 00 §11.4)**
   - "재현율 70.96% → 위험의 약 3할을 놓침"이라는 해석은 원문 지표 정의와 맞지 않는다.
   - Table 6은 처음 보는 위험 사례의 **집행률 95.56%**를 보고한다.
   - 70.96%는 "안전 짝 사례"를 써서 낸 값이다. 본문은 이 값을 두고 놓침(false negative)과 과차단(false positive)을 둘 다 설명한다. 정의가 모호하다.
3. **WAM (M5 §4 대안 문단)**
   - "사후 블렌딩이 async 대비 이득이 거의 없었다(37.5 대 40)"는 끼우기 과제 하나에서만 맞다.
   - 컨베이어는 20 → 40, 전자레인지는 44 → 80이었다.
   - 저자 결론은 "workable floor"다. "L1+L3만"을 지지하는 근거로 쓰는 것은 선택적 인용이다.
4. **RTC (M5 L2, 00 §7 T_b·τ_b)**
   - 원문 soft mask는 순수 지수 exp(−t/τ)가 아니다. `c·(e^c−1)/(e−1)` 꼴로, 구간 끝에서 정확히 0이 되고 앞에 가중 1인 고정 구간이 있다.
   - 우리 w(t)=exp(−t/0.1)은 T_b=0.3 s에서 e^−3 ≈ 0.050이 남는다. 블렌드 끝에서 5% 계단이 생긴다(우리 계산).
5. **AgileThinker (M2 §2.2)**
   - 우리 표기 "HIGH(ICLR 2026)"을 abs 페이지에서 확인할 수 없다. 코멘트는 "30 pages"뿐이다.
   - Table 10 인용은 반응 단독 두 열 가운데 한 열만 옮겼다.

---

## 1. lmgame-Bench (2505.15146) — M1

### 원문 사실
- 서지: 첫 공개 2025-05-21(v1), v2 2025-06-03. abs에 학회·코멘트 표기가 없다. 저자 Hu·Huo·Zhang·Yu·Xing·Stoica·Rosing·Jin·Zhang.
- **인식 모듈(§2.2.1)**
  - 원문: "For grid-based games (Sokoban, Candy Crush, 2048, Tetris), the module converts the visual layout into a text-based table **from game backends**, listing object coordinates and their properties, e.g. "Box at (2,3)"".
  - 복잡한 그래픽 게임(Super Mario, Ace Attorney)은 o3가 텍스트 설명을 만든다. §3.1 원문: "perception module plays a less significant role and model performance still primarily relies on a model's vision understanding capability".
  - **이 문장은 본문 서술이다. Table 2에는 Mario·Ace Attorney 행이 없다.**
- **Table 2**: 3회 평균. Sokoban 지표는 "첫 교착까지 전 레벨에 걸쳐 목표에 밀어 넣은 상자 수"(부록 G). 값은 ZS / +Memory / +Vision / +Both 순서다.

| 모델 | Sokoban | 2048 |
|---|---|---|
| o4-mini | 1.3 / 1.3 / 5.3 / 5.3 | 97.6 / 115.1 / 117.0 / 120.6 |
| gemini-2.5-pro-03-25(thinking) | 1.0 / 1.0 / 6.0 / 4.3 | 120.5 / 118.0 / 117.4 / 117.3 |
| claude-3.7(thinking) | 0.0 / 0.3 / 0.7 / 2.3 | 114.2 / 107.1 / 115.3 / 113.3 |
| llama-4-maverick | 0 / 0 / 0 / 0 | 44.6 / 98.1 / 73.7 / 106.0 |
| claude-3.5-sonnet | 0 / 0 / 0 / 0 | 57.8 / 102.5 / 66.3 / 108.2 |
| gpt-4o | 0 / 0 / 0 / 0 | 70.4 / 107.0 / 73.3 / 106.7 |

- **Table 1(하네스 끔 / 켬, 모듈 전부 합친 것)**
  - **텍스트 전용 모델도 하네스(기호 표)만으로 참가한다.** 예:
    - grok-3-mini-beta: Sokoban 5.7, Tetris 21.3, 2048 118.6
    - deepseek-r1: Sokoban 1.3, Candy 447.3
  - o3는 Sokoban 2.0 → 8.0.
  - Mario는 하네스를 켜도 모델에 따라 내려갔다. claude-3.5 1540.0 → 1267.7, o1 1434 → 855, gemini-2.5-flash 1540.7 → 1395.0.
  - Ace Attorney에서 텍스트 전용 모델은 0.0이다.
- **저자 한계(부록 E)**: "Given the tiny sample due to the cost of running latest models, results should be considered preliminary". o1·o3는 1회 실행이다.

### 우리 해석과 불일치
- "Table 2 정성 서술 — 수치 표는 이번에 못 뽑음"은 이제 해소됐다. 다만 **"복잡한 그래픽 게임에서 효과가 작다"는 Table 2가 아니라 §3.1 본문 문장**이다. 문서 위치 표기를 고쳐야 한다.
- "Gemini·o4-mini가 크게 오름"의 절대값은 **상자 1.0~1.3개 → 5.3~6.0개**다. 표본은 3회다.
- 2048에서는 **강한 모델이 기호 표로 얻는 이득이 없거나 음수**다(gemini 120.5 → 117.4). 약한 모델은 오른다(llama 44.6 → 73.7). 이득은 모델 능력에 따라 다르다. M1 §6-1(Read More)과 같은 결이다.
- **텍스트 전용 모델이 기호 표만 받고 상위권에 든다**(grok-3-mini Sokoban 5.7, 전체 2위). 이미지를 못 보는 Jev에게 가장 직접적인 기간 안 근거다. 문서에는 빠져 있다.

### 정본 반영 제안
- [제안] M1 §2.1 lmgame 행
  - 출처를 "§3.1 본문 + Table 2(Sokoban·2048만)"로 고친다.
  - 수치(상자 수 1.0~1.3 → 5.3~6.0, 3회)를 적는다.
  - "텍스트 전용 모델(grok-3-mini, deepseek-r1)이 기호 표만으로 참가·상위권"을 추가한다.
  - "저자 스스로 preliminary"를 적는다.
- [접목] E3 판정 1(A 대 A-full) 옆에 기록할 예상을 적는다: "강한 모델은 기호 표 이득이 작을 수 있다(2048 gemini −3.1)". 판정 기준은 바꾸지 않는다.

---

## 2. ViPlan (2505.13180) — M1

### 원문 사실
- 서지: 첫 공개 2025-05-19, v3 2026-09-01. journal-ref **EMNLP 2026 Findings** 확인. Aalto 등.
- **Table 1(모델 평균)**

| 방법 | BW | HH |
|---|---|---|
| Ground | 0.47 | 0.04 |
| Ground+CoT | 0.44 | 0.06 |
| Ground+Mem | 0.47 | 0.05 |
| Ground+Mem+CoT | 0.45 | 0.05 |
| grounder 평균 | 0.46 | 0.05 |
| planner 평균 | 0.09 | 0.34 |

- 본문: grounder는 HH에서 "reaching at most a success rate of 6%".
- 부록 H 원문: "models generally show very high accuracy (≥ 90% for many model families); however ... one episode requires up to 120 questions to be answered correctly".
- 부록 M
  - `clear`를 "Is the block x the topmost of its column?"로 물었는데, **파생 술어(derived predicate)라서 일부 모델은 우연 수준 0.50**에 가까웠다.
  - **물체가 많아질수록 정확도가 떨어진다.**
  - HH의 nextto·open·reachable이 낮은 이유를 원문은 이렇게 적는다: "ambiguity of the domain … can require a degree of interpretation". 정의가 분명한 holding·inside는 높다.
  - 일부 모델은 "yes" 편향(Molmo, AyaVision), 다른 모델은 "no" 편향(DeepSeek-VL2)을 보인다.
- **Table 19(HH, Ground, Simple / Medium / Hard)**
  - GPT-5.2: nextto 0.52 / 0.64 / 0.73, open 0.59 / 0.53 / 0.53, reachable 0.49 / 0.42 / 0.63
  - GPT-4.1: nextto 0.52 / 0.55 / 0.56, open 0.50 / 0.74 / 0.77
  - Mistral-Small-3.1: nextto 0.72~0.79, reachable 0.28~0.40
  - AyaVision 8B: nextto 0.12 / 0.14 / 0.19
- **한계**
  - HH에서는 VLM에 특권 정보를 준다.
  - 시드는 하나이고, 오차는 split당 25문제 사이의 변동이다.
  - 모델 선택에 벤치마크 과제를 썼으므로 "may be optimistic".

### 우리 해석과 불일치
- M1의 "가정 환경(HH)에서 약한 모델의 nextto는 0.12~0.55"는 실제보다 좋게 읽힌다. **가장 강한 폐쇄 모델도 nextto 0.52~0.73, open 0.50~0.77, reachable 0.42~0.63**이다. 90%보다 훨씬 아래다. M1 표의 "90% 미만"은 틀리지 않았지만 크기를 가린다.
- 그 밖(46% 대 9%, 5% 대 34%, 120개, EMNLP 2026 F)은 원문과 맞다.

### 정본 반영 제안
- [제안] M1 §2.3·§6-6
  - "가장 강한 모델(GPT-5.2)도 nextto 0.52~0.73, open 0.53~0.59, reachable 0.42~0.63"을 그대로 적는다.
  - T3 `open`을 VLM으로 만들면 **"정확도 50~77%"를 전제로** 설계한다.
- [접목] 원문의 낮은 정확도 원인은 "해석이 필요한 모호한 정의"다. 그래서 등록부 술어는 **모두 설정 표 문턱을 쓰는 조작적 정의**로 둔다. 지금 M1 §4.0 이름 규칙과 같은 방향이다. 이것을 근거 문장으로 추가한다.
- [접목] `clear`가 파생 술어라서 VLM이 약하다는 결과는, `clear`·`top_clear`·`path_clear`를 **코드로 직접 계산**하는 M1 #10 규칙의 원문 근거다.
- [제안] E3 설계
  - 정답 yes/no 비율을 맞춘다.
  - 정답이 yes인 문항과 no인 문항의 정확도를 따로 보고한다(원문의 편향 관찰).
  - 장면 물체 수별 정확도 곡선을 추가한다.

---

## 3. COPE: Efficient LLM Collaboration via Planning (2506.11578) — M2

### 원문 사실
- 서지: 첫 공개 2025-06-13, v5 2026-08-25. 코멘트 "Accepted at TMLR 2026" 확인.
- **Table 1(MATH-500, 행 = 실행기, 열 = 계획기)**

| 실행기 | Base | GPT-mini | Llama-3B | Llama-1B |
|---|---|---|---|---|
| GPT-mini | 73.8 | 76.2 | 70.6 | 69.6 |
| Llama-3B | 42.8 | 53.0 | 37.6 | 32.8 |
| Llama-1B | 25.2 | 36.4 | 26.0 | 23.2 |

- **Table 2(Llama-1B 자기 계획)**: None 25.2 / Guideline 23.2 / Goal 30.2.
- 원문 Observation 3: "we prompt the model to generate a goal (what to achieve) rather than a guideline (how to solve the task) **as before**". 즉 **Table 1의 계획은 guideline(절차)형**이다.
- **Stage 2 원문**: "the large model generating a new **guideline-type plan** g^L … The small model … leveraging both the original plan g^S [small's goal] and the new plan g^L".
- 프롬프트(Table 17)
  - 목표형: "State the goal … in one sentence."
  - 절차형: "Explain how to solve … Focus on strategy and key ideas. Respond in just one or two sentences."
- **Table 8(MATH-500, EXAONE-3.5-2.4B 작은 모델, 정확도 / 비용)**: No-plan cascade 71.2 / 265, COPE 74.4 / 212, Plan-only(큰 모델 계획 → 작은 모델 실행, 1단계) 56.8 / 101, Verify-only 52.2 / 769, Self-plan(큰 모델) 75.6 / 435.
- **ALFWorld(Table 7, 134과제, Qwen3-8B 작은 모델 + GPT-4.1 큰 모델)**: COPE 44.8% 대 Large 42.5%. 비용 8.64 대 11.06 USD. 매 행동 스텝 다수결이다.
- **한계(§6)**
  - "Consensus and perplexity are model-based, uncalibrated proxies and may indicate high confidence for incorrect outputs."
  - Stage 3에 도달하는 28.7%에서는 큰 모델을 한 번 부를 때보다 비용이 1.25배다.
  - 지연이 늘어난다.

### 우리 해석과 불일치
- M2 §2.1의 COPE 행은 이렇게 적는다: "큰 계획기 → 작은 실행기 도움(42.8→53.0%) … 목표형 30.2 / 절차형 23.2 / 없음 25.2(1B 자기 계획)".
  - 이 조합은 **큰 계획기가 절차형으로 도운 결과와 작은 모델의 자기 목표형 결과를 한 줄에 붙인 것**이다.
  - 원문에서 큰 → 작은 방향의 이득은 **절차형(1~2문장 전략)**에서 나왔다.
  - COPE 본 방법도 **작은 모델 자신의 목표 + 큰 모델의 절차를 함께** 준다.
- M2 §3 #1 "Jev 조각의 중심 = 완료 술어, 절차 서술은 스킬 이름으로만"은 COPE가 지지하지 않는다. 원문은 오히려 **큰 계획기의 짧은 절차가 작은 실행기에 도움**이라는 반대 증거다.
- 문서의 주의문 "큰 계획기가 목표형을 준 조건은 원문에 없다"는 맞다. 다만 한 단계 더 나가 "그 조건의 이득은 절차형에서 나왔다"를 적어야 한다.
- 추가 사실: 큰 모델 계획만 주는 Plan-only는 56.8로, 계획 없는 cascade 71.2보다 낮다. 계획만으로는 부족하다는 뜻이다.

### 정본 반영 제안
- [제안] M2 §2.1·§3 #1·§6-1의 근거 문장을 고친다: "COPE: 큰 → 작은 이득(42.8 → 53.0)은 **절차형 1~2문장**, 목표형 우위는 **1B 자기 계획**뿐. 본 방법 Stage 2 = 작은 모델 목표 + 큰 모델 절차."
- [제안] 기본 v1(목표 중심)은 우리 구조(M4·M7·M9가 술어를 읽는다)와 AgentSpec 모양에 기대는 설계 선택으로 **유지**한다. **COPE는 v1의 근거 목록에서 뺀다.**
- [제안] E-M2-1 조건 추가
  - **B-COPE** = v1 조각 + Astra 절차 1~2문장("strategy and key ideas", COPE 원문 프롬프트 모양)
  - 판정 2(대안 B가 3%p 이상 높으면 [결정 필요])를 B-COPE에도 적용한다.
- [결정 필요] 선택 사항: `rationale`/`how`를 Jev 기본 입력에서 빼는 현재 기본값의 근거가 약해졌다. E-M2-1 결과 전까지 기본은 그대로 두되, 근거 약화를 사용자에게 알린다. 사용자 의도 문장("Astra가 본 것과 원하는 것을 효율적으로 전달")은 건드리지 않는다.

---

## 4. AgentSpec (2503.18666) — M2

### 원문 사실
- 서지: 첫 공개 **2025-03-24**(기간 안, 경계 +1일), v3 2025-07-31. journal-ref "Proc. ICSE'26, pages 2938-2950" 확인.
- **사람이 쓴 규칙(Table 4, 체화, SafeAgentBench)**
  - 위험 10범주 모두 규칙을 켜면 위험 수행 0%. 예: Breakage 78.57% → 0%, Property Damage 68.75% → 0%.
  - **Safe 과제 수행 58.62% → 54.26%**(−4.36%p).
- **LLM 생성 규칙(§5.3, Table 6)**: o1, 개발자 규칙 3개 예시와 in-context 예시.

| 대상 | #Scenario | #Example | #Rule | Enforced(%) |
|---|---|---|---|---|
| Code | 750 | 75 | 25 | 87.26 |
| Embodied | 250 | 25 | 10 | **95.56** |
| AV | 8 | 0 | 6 | 62.50 |

  - Enforced 정의 원문: "the percentage of unseen risky scenarios in which the LLM-generated rules are successfully applied".
- **지표 문장 원문**: "the overall **precision** of the LLM-generated rules is acceptable, successfully enforcing 95.56% of the risky cases. Since SafeAgentBench additionally provides **safe counterparts** of the risky cases, we also evaluate the **recall**, which is 70.96%."
  - 이어서 놓침 사례를 든다: 불붙은 초 확인 누락, 와인 든 주전자.
  - 과차단 사례도 든다: "the LLM-generated rule simply banned the pour action entirely … (e.g., watering a houseplant)".
- 체화 에이전트의 입력은 "find mug / pick mug / pour" 같은 **고수준 텍스트 행동 계획**이다.
- 오버헤드: 파싱 1.42 ms, 술어 평가 1.11 ms(체화) / 2.83 ms(코드). 체화 에이전트 평균 실행은 9.82 s.
- **한계(§6.3)**: "deterministic enforcement at discrete execution checkpoints … lacks support for trajectory-based safety analysis".

### 우리 해석과 불일치
- M2 §3 #4·§6-8과 00 §11.4는 "재현율 70.96%(약 3할 놓침) → Astra가 쓴 forbidden은 위험의 약 3할을 놓칠 수 있다"고 읽는다.
  - 원문의 "precision"은 위험 사례 집행률(95.56%, 놓침 약 4.4%)이다.
  - "recall" 70.96%는 안전 짝 사례를 쓴 값이다.
  - 본문은 놓침과 과차단(pour 전면 금지)을 둘 다 이 값의 원인처럼 설명한다. **정의가 일관되지 않는다.**
  - "3할을 놓친다"는 원문에서 바로 나오지 않는다. 적어도 **과차단(정상 행동을 막음)**이 함께 섞인 값이다.
- 설계 결론("Astra forbidden만 믿지 않고 M7 하드 층을 독립으로")은 그대로 타당하다. 다만 이유가 "놓침"에 더해 **"과도하게 경직된 금지"**가 된다.
- 우리에게는 과차단이 더 아프다. 오경보 FAIL은 정지나 Astra 재호출로 이어지기 때문이다.
- 사람이 쓴 규칙도 안전 과제 수행을 4.36%p 깎았다. 규칙 비용을 보여 주는 원문 수치다.

### 정본 반영 제안
- [제안] 00 §11.4와 M2 §2.1·§3 #4·§6-8의 문장을 고친다: "LLM(o1) 생성 규칙: 처음 보는 위험 사례 집행률 95.56%(Table 6), 안전 짝 사례로 낸 'recall' 70.96%(원문 정의 모호, 놓침과 과차단을 함께 설명). 사람 규칙도 안전 과제 수행 58.62 → 54.26%."
- [제안] E-M2-3 지표 추가: **`forbidden` 과차단률**. 정상 성공 에피소드에서 `forbidden` DFA가 거부 상태에 들어간 비율을 에피소드 단위로 잰다. 판정 후보: 과차단률 > 5%이면 `enforce: fail` 규칙을 `escalate`로 낮추는 규칙을 검토한다([제안]).
- [접목] 원문 한계("이산 체크포인트, 궤적 예측 없음")는 우리 DFA 감시(10 Hz 술어 전이)가 원문보다 촘촘하다는 차이로 적는다. 이것도 이산 사건 위의 감시다.

---

## 5. AgileThinker: Real-Time Reasoning Agents in Evolving Environments (2511.04898) — M2

### 원문 사실
- 서지: 첫 공개 2025-11-07. **abs 코멘트는 "30 pages"뿐이고 ICLR 표기가 없다.** HTML 본문에도 "ICLR" 문자열이 없다.
- 본 실험은 DeepSeek 모델뿐이다. 원문 한계: 다른 업체는 추론 흔적을 주지 않는다.
- 각 설정은 32회(게임 시드 8 × 샘플링 시드 4)다. **Table 10의 표본 수는 따로 적혀 있지 않다.**
- **Table 10**: Gemini-2.5-Flash, Freeway 중간 난이도. "reactive thread to reference the final non-thinking tokens produced by planning thread after its reasoning is completed".

| 토큰/스텝 | 반응(생각 끔) | 반응(생각 켬 + 예산) | 계획 | 반응+계획 |
|---|---|---|---|---|
| 32k | 0.12 | 0.93 | 0.93 | 0.92 |
| 16k | 0.12 | 0.76 | 0.70 | 0.70 |
| 8k | 0.12 | 0.09 | 0.25 | 0.31 |
| 4k | 0.12 | 0.00 | 0.05 | 0.26 |

- Gemini의 예산 제어는 토큰 수를 정확히 지키지 못하고 자주 넘긴다(Figure 9).

### 우리 해석과 불일치
- M2는 "8k 0.31 대 반응 단독 0.09·계획 단독 0.25, 4k 0.26 대 0.00·0.05"라고 적는다. 반응 단독의 **생각 끔 열(0.12)**을 뺐다. 4k에서 결합 0.26은 생각 끔 반응 0.12보다도 높으니 결론은 같다.
- **"16k·32k는 차이 없음"은 부정확하다.** 16k에서는 반응(생각 켬) 0.76이 결합 0.70보다 0.06 높다. 압박이 약하면 결합이 약간 손해다.
- 신뢰도 "HIGH(ICLR 2026)"는 확인되지 않았다.

### 정본 반영 제안
- [제안] M2 §2.2의 신뢰도를 "MED(학회 [미확인], abs 코멘트 '30 pages'만)"로 내린다. 표는 네 열을 그대로 옮긴다.
- [제안] M2 §6-5에 추가한다: "16k에서는 결합(0.70)이 반응 단독(0.76)보다 낮음 → 압박이 약할 때 '가장 새 계약 참조'가 손해일 수 있다". E-M2-2의 Astra 지연 축(낮은·높은 지연)에서 L+A 대 L의 차이를 지연 구간별로 따로 보고하는 조건을 추가한다.

---

## 6. RTC: Real-Time Execution of Action Chunking Flow Policies (2506.07339) — M5

### 원문 사실
- 서지: 첫 공개 2025-06-09, v2 2025-12-05. 코멘트 "published in NeurIPS 2025" 확인.
- **soft mask(식 5)**
  - W_i = 1 (i < d)
  - W_i = c_i·(e^{c_i} − 1)/(e − 1) (d ≤ i < H − s)
  - W_i = 0 (i ≥ H − s)
  - c_i = (H − s − i)/(H − s − d + 1)
  - 코드 `get_prefix_weights`: 선형 ramp w에 `w·expm1(w)/(e−1)`을 곱한다. 구간 끝(`end`)부터는 0이다.
  - 원문 설명: "The first d actions get a weight of 1 … the actions in between get weights that exponentially decay from 1 to 0".
  - **부록 A.4 Fig. 8**: "Exponential decay performs the best overall, although linear decay is very close behind".
- 이 가중은 **인페인팅 guidance 가중**이다. 두 궤적을 섞는 가중이 아니다. 가이던스 상한 β = 5이고, β가 크면 저크가 늘어난다(A.2).
- **하이퍼파라미터(Table 4)**
  - 공통: n = 5, β = 5
  - 시뮬: H = 8
  - 실물: H = 50, Δt = 20 ms(50 Hz), s_min = 25, 지연 버퍼 b = 10
  - 다음 지연은 "d = max(Q)"로 보수적으로 추정한다(Algorithm 1).
- **시뮬(Kinetix 12과제)**
  - 점마다 2048회, Wilson 95% 구간.
  - "TE performs poorly across the board, even with an inference delay of d = 0 … averages of valid actions are not necessarily valid".
  - hard masking은 soft보다 조금 나쁘고, d가 작을수록 차이가 크다.
- **실물(π0.5, 6 DoF 양팔 2대)**
  - 6과제 × 방법·지연 조합마다 10회. 총 480 에피소드, 28시간.
  - 성냥 과제 등 과제별 점수는 그림으로만 있다.
  - 원문: "RTC achieves the best score at all inference delays with a statistically significant result at +100 and +200ms".
  - TE 두 변형은 +100·+200 ms에서 "protective stop"이 걸려 실행하지 못했다.
  - 동기 방식보다 같은 동작이 20% 빠르다(Fig. 1).
- **지연**: π0.5 76 ms → RTC 97 ms. 디노이징 스텝당 2.5배다.
- **한계**: 계산 부담이 크고, 확산·흐름 정책에만 적용된다. 실물 결과에 보행이 없다.

### 우리 해석과 불일치
- M5 L2 규칙 1(00 §7: T_b = 0.3 s, τ_b = 0.1 s)은 w(t) = exp(−(t − t0)/τ_b)이고 "RTC soft mask 모양"이라고 적는다. 원문 모양과 두 가지가 다르다.
  - (a) 원문은 **앞에 가중 1인 고정 구간(d 스텝)**이 있다.
  - (b) 원문은 **구간 끝에서 정확히 0**이다. 우리 식은 t0 + 0.3 s에서 e^−3 ≈ 0.0498이 남는다. 블렌드가 끝나는 순간 옛 궤적 몫 약 5%가 한꺼번에 빠져 작은 계단이 생긴다(우리 계산).
- 원문 절제에서 지수와 선형이 거의 같았다. 그래서 τ_b 튜닝(E-M5-2의 {0.05, 0.1, 0.2})보다 **구간 길이와 고정 구간**이 더 본질적인 변수일 가능성이 크다([가정]).
- "TE는 지연 0에서도 나쁨"은 **Kinetix 다봉 동적 과제(힘 제어)**의 결과다. 실물(위치 제어)에서 TE의 실패는 지연을 넣었을 때의 진동(protective stop)이었다. M5 §6의 약한 근거 표기는 맞다.

### 정본 반영 제안
- [제안] 00 §7과 M5 L2 규칙 1의 가중식을 RTC 식 5의 시간판으로 바꾼다.
  - t < t0 + T_f이면 w = 1(T_f = 고정 구간)
  - t0 + T_f ≤ t < t0 + T_b이면 w = c(e^c − 1)/(e − 1), c = (t0 + T_b − t)/(T_b − T_f)
  - 그 뒤는 0
  - 초기값은 T_f = 0 또는 M4 `commit_window`와 같게 둔다([가정]). T_b = 0.3 s는 그대로 둔다.
  - τ_b는 없앤다. 00 §7 표에서 "τ_b 0.1 s"를 "schedule = exp(RTC 식 5)"로 바꾼다.
- [제안] E-M5-2의 τ_b 스윕 대신 두 스윕을 둔다: schedule {exp, linear}(원문 절제 재현), T_b ∈ {0.2, 0.3, 0.5} s.
- [접목] M4 `d_p95`의 대안 조건으로 RTC식 "최근 10회 최대값"을 E-M4 부수 비교에 둘 수 있다. 기본값은 바꾸지 않는다.

---

## 7. SEAM (2607.04609) — M5

### 원문 사실
- 서지: 첫 공개 2026-07-06. 코멘트 "8 pages, 4 figures, 5 tables", 학회 표기 없음. South China University of Technology.
- 설정은 **동기 청크 실행(synchronous chunked execution)**이다. π0.5, LIBERO-10, 과제당 130 에피소드.
- 비교 방법 설정 원문: ACT-TE는 "standard coefficient k = 0.01 and queries the policy at every environment step". RTC는 권장값.
- **Table 2**: 성공률 / 경계 jerk / 내부 jerk / 전이 불연속 / 경계 가속 분산 / 청크당 ms.

| 방법 | 성공 | BJ | IJ | CD | AV_b | ms/청크 |
|---|---|---|---|---|---|---|
| π0.5 기본 | 94.8 | 0.195 | 0.094 | 0.172 | 0.165 | 282.2 |
| + ACT-TE | 82.7 | 0.031 | 0.031 | 0.062 | 0.006 | 282.2 |
| + RTC | 95.1 | 0.090 | 0.075 | 0.089 | 0.094 | 344.6 (1.22×) |
| + SEAM | 95.7 | 0.141 | 0.074 | 0.126 | 0.094 | 286.0 (1.01×) |

- **Table 3 T1**: 기본 91.5, SEAM 99.2, RTC 90.8, ACT-TE 58.5.
- Fig. 4 원문: "ACT-TE over-smooths contact timing, and **RTC can lock into a failed alignment**". §5 원문: "RTC can preserve a failed early grasp through its stronger continuation constraint".
- Table 4 λ 스윕: λ를 키우면 성공이 떨어진다. λ = 0.15에서 92.8%, 0.2에서 89.5%. 원문: "supports using a weak closed-form correction rather than forcing the denoising trajectory toward the previous chunk too aggressively".

### 우리 해석과 불일치
- M5 표의 수치(94.8 / 82.7 / 95.1 / 95.7, jerk 0.195 / 0.031)는 원문과 맞다.
- 문서가 빠뜨린 것:
  - ACT-TE는 **매 스텝 질의**였다.
  - 동기 실행 설정이었다.
  - **강한 연속성 제약(RTC)이 실패한 정렬을 고착시킨다**는 반대 관찰이 있다. 같은 보기끼리 이어 붙이는 L2와 M4 확정 쪽의 위험 근거다.

### 정본 반영 제안
- [제안] M5 §6에 "강한 이어붙이기의 고착 위험(SEAM Fig. 4, RTC가 실패한 초기 파지를 유지)"을 반대 근거로 추가한다. 신뢰도는 LOW-MED를 유지한다.
- [제안] E-M5-1 지표 추가: **"잘못된 접근 유지 시간"**. M4 (b)가 불일치를 낸 뒤에도 같은 보기 블렌딩이 계속된 시간이다. S4와 S3를 비교한다.

---

## 8. WAM 실시간 배치 연구 (2608.01880) — M5·M2

### 원문 사실
- 서지: 첫 공개 2026-08-03, v2 2026-08-11. 저자 표기 **"Motubrain Team"**. 프로젝트 motubrain.cn, GitHub `shengshu-ai/Motubrain`. 학회 표기 없음.
- 설정
  - 양팔 end-effector 로봇, **10 Hz**, 청크 H = 24.
  - 지연 구간은 1~8스텝, 나머지 겹침은 9~20스텝(Fig. 3).
  - 방법·과제 조합마다 **5회**.
- 방법 정의
  - `async+blend` = 겹침 구간 사후 가중 평균.
  - `simple` = 디노이징 중 블렌딩. 가중 "w(t) = 1 for t ≤ d_est and decreases to zero at t = H − s", RTC와 같은 모양.
  - `infer` = inference-time RTC.
  - `train` = prefix 조건 학습.
- **점수(100점 만점)**

| 과제 | 결과 |
|---|---|
| Pick Up Conveyor(동적) | sync 20, async 20, async+blend 40, infer 30, simple 80, **train 96**(61.24 s) |
| Block Into Slot(정밀) | sync 72.5, train 70(12.13 s 대 sync 19.4 s), async 40, async+blend 37.5, **simple 27.5**. infer 값은 본문에 없음(그림만) |
| Food Into Microwave(장기) | train 96, sync 96(85.18 s), simple 80(60.24 s, 저크 최저), async+blend 80, async 44 |

- 원문 결론
  - "async+blend, with only accurate temporal alignment and a straightforward weighting step, establishes a **workable floor**".
  - 시간 정렬: "When d > d_est … a hard position jump that no blending strategy can recover from. Conversely, when d < d_est … the impact is generally mild."
- 원문 한계(Fig. 6): 장애물이 갑자기 나타나면 "the prefix constraint becomes harmful, and none of the blending strategies discussed here are equipped to handle abrupt environmental changes".

### 우리 해석과 불일치
- M5 §4 대안 문단의 "WAM에서 사후 블렌딩이 async 대비 이득이 거의 없었다(37.5 대 40)"는 **끼우기 과제 하나**에서만 맞다. 컨베이어는 20 → 40, 전자레인지는 44 → 80이었다. 원문 결론은 "workable floor"다. **"L1+L3만" 대안을 지지하는 근거로 쓰면 선택적 인용**이다.
- M2 §2.2는 WAM을 **MED**, M5는 **LOW-MED**로 적는다. 등급이 서로 다르다. 저자는 팀 이름만 있고 학회 표기가 없다.
- 원문의 d > d_est 비대칭(늦으면 치명, 이르면 경미)은 우리 `d_p95`(보수적 추정)의 직접 근거다. 문서에는 없다.
- Fig. 6(갑작스러운 환경 변화에서는 이전 청크 제약이 해롭다)은 우리 규칙 2("다른 보기면 평균 안 함")를 지지한다. 동시에 **같은 보기라도 섭동 직후의 L2 블렌딩은 해로울 수 있다**는 경고다.

### 정본 반영 제안
- [제안] M5 §4 대안 문단을 고친다: "WAM: 사후 블렌딩은 끼우기에서 40 → 37.5(이득 없음), 컨베이어 20 → 40, 전자레인지 44 → 80. 저자 결론은 'workable floor'." 대안 "L1+L3만"의 지지 근거에서 WAM을 빼고 "혼재"로 적는다.
- [제안] M2 §2.2의 WAM 신뢰도를 LOW-MED로 맞춘다. M5 §8 "소속 확인"은 "Motubrain Team(GitHub shengshu-ai), 개인 저자 미표기"로 해소한다.
- [접목] 00 §7 `d_p95` 비고에 "WAM: 지연을 과소 추정하면 되돌릴 수 없는 위치 점프, 과대 추정은 경미 → 보수적 분위수 사용 근거"를 추가한다.
- [제안] M5 L2 규칙 1에 조건을 추가한다: **M4 `premise_epoch`가 바뀐 직후 또는 M4 (b) 불일치 WARN 중에는 같은 보기라도 블렌딩하지 않는다**(WAM Fig. 6 + SEAM 고착 관찰). E-M5-1에 S4 대 S4-epoch 조건으로 넣는다.

---

## 9. FluxVLA Engine (2609.17210) — M5 L3

### 원문 사실
- 서지: 첫 공개 2026-09-15, 학회 표기 없음, 저자 24명.
- **Table 11 원문 캡션**: "Project-reported trajectory post-processing latency for a **12-DoF, 50-step synthetic trajectory** on an **Intel Xeon Platinum 8336C** CPU. Values include warmed solver execution but exclude policy inference and robot I/O."
  - Joint MPC(Tracking) 4.90 ms
  - Ruckig filter(Tracking) **1.17 ms**
  - "approximately 4.19× faster"
  - "should not be interpreted as a general hardware ranking"
- 범위 원문: "Both implementations process each selected joint separately; this experiment does **not evaluate coupled-joint or Cartesian** post-processing."
- Ruckig 원문: "it can introduce reference lag because each update prioritizes feasible motion from the current kinematic state".
- MPC
  - 목적함수는 w_trk·추종 + λ‖z‖² + w_term·끝 위치 + w_stop·끝 속도. 3중 적분기, v·a·j 상자 제약, OSQP.
  - "does not model coupled robot dynamics, torque, collision, or workspace constraints".
  - "Joint MPC favors closer tracking … Ruckig favors lower processing latency". **수치 비교는 없다.**
- 설정 축: Execution mode tracking / **settle**(최종 목표로 가서 정지), Boundary handling **stitching**(이전 처리 궤적의 시간 정렬된 앞부분을 재사용).
- Fig. 6은 Training-time RTC + joint MPC의 정성 흔적이다(Ruckig 아님). 원문: "does not isolate … or establish an effect on task-level performance".

### 우리 해석과 불일치
- D1에서 "미검증, 다음 검증 1순위"였던 **1.17 ms가 원문과 일치**한다. 해소된다.
- 조건(12자유도, 50스텝 합성 궤적, Xeon 8336C, 관절 분리)을 함께 적어야 한다.
- M5 L3의 "직교 공간 또는 관절"에서 **직교 공간은 원문이 평가하지 않았다.**
- "MPC 추적이 기준에 더 가까움"은 정성 문장뿐이다.

### 정본 반영 제안
- [제안] M5 §2 #4·#5와 §8을 고친다: "Table 11 원문 확인: 12-DoF·50스텝 합성·Xeon 8336C, Ruckig 1.17 ms / 관절 MPC 4.90 ms, 관절 분리만, 과제 효과 미측정(저자 명시), MPC 추종 우위는 정성."
- [가정] L3의 직교 공간판은 근거가 없다. 기간 안 근거와 맞추려면 **관절 공간 Ruckig을 1순위**로 둔다. 확정은 M5 §7-2와 함께 한다.
- [접목] FluxVLA의 "settle 모드"는 우리 micro-dwell(S4d)과 같은 모양이다. "stitching"(처리된 앞부분 재사용)은 L2 고정 구간(T_f)과 같은 모양이다. 둘 다 조건 설명의 선례로 인용할 수 있다.

---

## 모듈별 정본 반영 목록(요약)

**M1**
- lmgame 출처 위치와 수치를 고친다. 텍스트 전용 모델 결과를 추가하고 preliminary 표기를 붙인다.
- ViPlan에서 강한 모델도 nextto·open·reachable이 0.42~0.77임을 명시한다.
- 조작적 정의와 파생 술어를 코드로 계산하는 규칙의 근거를 추가한다.
- E3에 yes/no 균형과 물체 수별 곡선을 넣는다.

**M2**
- COPE 근거를 고친다(큰 → 작은 이득은 절차형). v1 근거에서 COPE를 빼고 E-M2-1에 B-COPE 조건을 둔다.
- AgentSpec 지표를 정정하고 E-M2-3에 과차단률을 넣는다.
- AgileThinker 등급을 내리고(학회 미확인) 네 열을 옮긴다. 16k 역전을 적는다.
- WAM 등급을 LOW-MED로 통일한다.

**M5·00 §7**
- L2 가중식을 RTC 식 5 시간판으로 바꾸고 τ_b를 없앤다. schedule·T_b 스윕을 둔다.
- WAM 인용을 정정한다(대안 지지 근거에서 뺀다).
- epoch 교체·불일치 WARN 중 블렌딩 금지 조건과 S4-epoch 조건을 둔다.
- SEAM 고착 반대 근거와 "잘못된 접근 유지 시간" 지표를 넣는다.
- FluxVLA 1.17 ms 조건을 명시하고 관절 공간을 1순위로 둔다([가정]).

[사용자] 줄은 하나도 바꾸지 않는다.
- M5의 "L2(VLA식 블렌딩) 기본 유지"(00 §9 C3)는 그대로다. 위 제안은 L2의 가중 모양과 켜는 조건만 바꾼다.
- M2 기본 v1은 사용자 의도가 아니라 설계 선택이다. 근거만 고친다. 바꿀지는 E-M2-1 결과로 정하고, 필요하면 [결정 필요]로 올린다.

---

## 확인 못 한 것
- **lmgame-Bench**: 학회 채택(abs에 표기 없음). 저자 소속은 본문에서 따로 확인하지 않았다.
- **AgileThinker**: ICLR 2026 채택 여부([미확인], abs 코멘트는 "30 pages"뿐). Table 10의 표본 수(본문에 적혀 있지 않음).
- **AgentSpec**: "precision 95.56 / recall 70.96"의 정확한 계산식. 본문 정의가 모호하고, 코드 저장소는 읽지 않았다.
- **RTC**: 실물 과제별 점수와 처리량 수치(Fig. 6 그림 속 값). 부록 A.4 Fig. 8 schedule 절제의 수치(그림).
- **WAM**: Block Into Slot의 infer 점수, 과제별 RMS jerk 수치(Fig. 5 그림만). 개인 저자 명단. 학회.
- **SEAM**: T8~T10 행 일부는 추출 텍스트에서 잘려 T1~T7과 전체 합계만 옮겼다. 코드 저장소는 확인하지 않았다.
- **FluxVLA**: 코드 저장소 설정값(Ruckig 한계값 기본값)은 읽지 않았다.
- **COPE**: 코드는 확인하지 않았다. Table 8 작은 모델 조합은 EXAONE-3.5-2.4B까지만 본문으로 확인했고, 큰 모델 이름은 그 절에서 다시 읽지 않았다.
- **이번에 다시 읽지 않은 것**: CaP-X VDM(D10a 확인분), FocusAgent·Read More(D2 확인분), 관성화 원문(Bollo SIGGRAPH 2017 Talk, GDC 2018)과 Half Pound Filter(D4 확인분), Ruckig 원 논문(2105.04830, 기간 밖 기초 문헌), 명세 패턴(Dwyer 1999)·런타임 검증(Bauer 외 2011).
- **로봇 쪽 사례를 찾지 못한 것**: "큰 계획기가 작은 실행기에 목표형과 절차형을 준 조건을 로봇에서 비교한 연구"는 이번에도 검색하지 않았다. 부재를 주장하지 않는다.

## 작업 파일 (스크래치 디렉터리)
- 원문 텍스트: `C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER\1a853580-8a79-4164-a03a-eeb77b9f612f\scratchpad\dr\`
  - 파일 이름: `<arXivID>_abs.txt`, `<arXivID>_html.txt`
  - RTC 코드: `rtc_model.py`, `rtc_readme.md`
