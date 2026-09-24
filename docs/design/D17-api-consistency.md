# D17 API 일관성·프롬프트 설계 조사 (user-log 30)

저장 2026-09-24 04:40 UTC. 조사 에이전트 보고 전문. 신뢰도 기준(user-log 14: 학회·소속·GitHub 스타·HF 좋아요·인용 수)을 적용해 LOW 12편은 근거에서 제외. 메인 원문 재확인: 2506.09501 v1 2025-06-11·"9%"(abs), NeurIPS 2025 Oral은 저자 저장소 README(nanomaoli/llm_reproducibility)에서 확인(abs에는 표기 없음) / 2512.03816 v1 2025-12-03·ICLR·"1,000"·"one step of fine-tuning" / 2509.01790 EMNLP 2025 Main·"heuristic evaluation methods" / 2604.24039 v1 2026-04-27·MLSys·"plan locality" / 2506.14852 v1 2025-06-17·NeurIPS·"50.31". 나머지 인용문은 에이전트가 요약 도구로 뽑은 것이라 본문 반영 전 원문 대조 필요.

## API 일관성 조사 (D17 성격): Astra·Jev 일관성 유지 프롬프팅·측정 프로토콜 (2026-09-24)

D:\qdd는 읽기만 했습니다. 내려받은 자료는 D:\tools\audit_d17\(abs/, hf/, gh/)에만 두었습니다.
**조사 한계**
- Semantic Scholar API가 계속 429를 돌려 인용 수는 Atil(126)만 확인했습니다. 나머지 인용 수는 "미확인"입니다.
- HF 추천 수: 페이지가 있는 논문만 적었습니다. 크기가 약 52,953 B인 응답은 페이지 없음으로 판정했습니다.
- GitHub 스타는 04:35 UTC에 저장소 HTML을 직접 받아 읽었습니다.
- 인용문은 arXiv abs/html을 요약 도구로 거쳐 뽑았습니다. 본문 반영 전에 원문 PDF와 한 번 더 대조하는 것을 권합니다.

### 1. 권고에 쓰는 근거 (HIGH/MED)

**(1) 비결정성: 원인과 측정**
- **Yuan 외, 2506.09501** (v1 2025-06-11, NeurIPS 2025 Oral, HF 20, 코드 118★) [HIGH]
  - 인용: "under bfloat16 precision with greedy decoding, a reasoning model like DeepSeek-R1-Distill-Qwen-7B can exhibit up to 9% variation in accuracy and 9,000 tokens difference in response length due to differences in GPU count, type, and evaluation batch size."
  - 추론(reasoning) 모델일수록 심하고, 초기 토큰의 반올림 차이가 번져 나갑니다.
  - [접목] Astra는 추론 모델이므로 temperature나 seed로 결정성을 얻을 수 없다고 전제합니다. 서버 쪽 해결(LayerCast)은 우리가 쓸 수 없습니다.
- **Thinking Machines "Defeating Nondeterminism in LLM Inference"** (2025-09, 블로그라 논문 아님. batch_invariant_ops 1,079★, SGLang이 채택) [HIGH-커뮤니티, 비논문]
  - 내용: 비결정성의 원인은 배치 비불변(batch non-invariance) 커널입니다. 같은 요청이라도 서버 부하(배치 크기)에 따라 결과가 달라집니다.
  - [접목] 호스트 Jev의 test-retest 바닥(1.33%)은 시간대·부하에 따라 달라질 수 있습니다. 그래서 바닥을 시간 블록별로 재야 합니다([가정]).
- **Atil 외, 2408.04667** (v1 2024-08-06, 기간 밖 기초 문헌. S2 인용 126) [MED]
  - 인용: "accuracy variations up to 15% across naturally occurring runs", "none of the LLMs consistently delivers repeatable accuracy across all tasks."
  - 결정적 설정(temperature 0 등)에서의 반복 불일치를 재는 지표 TARr@N/TARa@N을 제안했습니다.
- **Messina·Scotta, 2604.22411** (v1 2026-04-24, journal-ref TMLR 2026-02, RAI CRITS) [MED]
  - T=0에서의 "background temperature"를 추정합니다.
  - 절차: 프롬프트마다 T=0으로 M ≥ 50회 돌려 exact-match 비율과 K-S 거리를 봅니다.
  - 시범 결과: gpt-4.1-nano 0.075, gemini-2.0-flash 0.065, claude-sonnet-4는 0("identical").
  - [접목] Jev·Astra의 같은 입력 반복을 이 방식(최빈 일치 비율)으로 보고합니다.
- **Bjarnason·Silva·Monperrus (KTH), 2602.07150** (v1 2026-02-06, ICLR 2026 Workshop Agents in the Wild, HF 2, 9★) [MED]
  - 인용: "single-run pass@1 estimates vary by 2.2 to 6.0 percentage points". T=0에서도 표준편차가 1.5pp를 넘습니다.
  - 궤적은 극초반에 갈라집니다. 기본 온도에서는 중앙값 5번째 토큰에서, T=0에서도 약 32~56번째 토큰에서 갈라집니다.
  - 필요한 반복 수: 2%p 차이를 검출하려면 약 9회, 1%p면 36회입니다.
  - [접목] E-M8a·E2a의 Astra 조건 비교에는 반복 실행과 검정력 계산이 필요합니다.
- **ReasonBENCH, 2512.07795** (v1 2025-12-08, Aarhus·EPFL·IIT Delhi, 학회 없음, HF 1) [MED]
  - 인용: "the inter-quartile range at T=0 is comparable to—and in several cells wider than—the range at T=0.7"
  - 인용: "Spending more on test-time reasoning reliably increases cost, but buys neither higher quality nor lower variance."
  - 권장 반복 수는 n = 30(최소 n ≥ 9)입니다.
  - [접목] effort high가 분산을 줄여 준다고 가정하지 않습니다. 사용자 결정인 low 기본과 low·high 비교를 그대로 유지하고, 비교할 때 분산도 함께 보고합니다.

**(2) 호스트 모델 표류(drift)와 감시**
- **Chauvin 외 (Inria/CNRS), 2512.03816 "Log Probability Tracking of LLM APIs"** (v1 2025-12-03, ICLR 2026) [HIGH]
  - 방법: 한 글자 프롬프트("x")에 출력 1토큰을 받고, 토큰 logprob 평균으로 검정합니다. 비교할 분포마다 N = 10을 씁니다.
  - 인용: "changes as small as one step of fine-tuning", "1,000x cheaper".
  - 실측: 189개 엔드포인트를 4개월 넘게 감시해 변경 의심 37건을 찾았습니다(엔드포인트당 연 0.86건). 이 중 34건은 오픈 가중치 모델이었습니다.
  - [접목] Jev는 보기 확률을 돌려주므로 고정 카나리 질문의 확률 분포를 날마다 추적하는 데 바로 옮길 수 있습니다. Astra는 logprob이 없어 적용할 수 없습니다.
- **Leshin 외 + Daniel Kang (UIUC), 2603.19022 "Behavioral Fingerprints"** (v1 2026-03-19, 댓글은 "submitted to CAIS 2026 System Demonstrations"라 채택 미확인) [MED-LOW, 보조로만]
  - 방법: 고정 프롬프트 세트로 요청 800건을 보내 출력 임베딩을 모으고, 프롬프트별 energy distance를 합해 순열검정과 e-value로 순차 감시합니다.
  - 모델·버전·양자화·추론 스택 변경은 다음 지문에서 바로 잡혔습니다. temperature 0.7 → 0.6 변경은 지문 18개가 쌓여야 잡혔습니다.
  - [접목] logprob이 없는 Astra의 표류 감시 틀로 씁니다. 다만 이 논문만으로 설계를 정하지는 않고, Chen 외와 함께 씁니다.
- **Chen·Zaharia·Zou, 2307.09009** (v1 2023-07-18, 기간 밖 기초 문헌) [HIGH-기초]
  - 인용: "GPT-4 (March 2023) … 84% accuracy … GPT-4 (June 2023) … 51%", "highlighting the need for continuous monitoring of LLMs."

**(3) 프롬프트 형식·순서·입력 민감도**
- **Sclar 외 FormatSpread, 2310.11324** (ICLR 2024, 기간 밖 기초 문헌) [HIGH-기초]
  - 인용: "performance differences of up to 76 accuracy points when evaluated using LLaMA-2-13B"
  - 형식 하나가 아니라 여러 형식에 걸친 범위를 보고하라고 권합니다.
- **Hua 외 "Flaw or Artifact?", 2509.01790** (v1 2025-09-01, EMNLP 2025 Main) [HIGH]
  - 인용: "much of the prompt sensitivity stems from heuristic evaluation methods, including log-likelihood scoring and rigid answer matching"
  - LLM-as-judge로 평가하면 분산이 크게 줄었습니다(모델 7개, 템플릿 12개).
  - [접목] Jev는 typed 선택이라 문자열 매칭에서 오는 인공물은 적습니다. 남는 민감도(보기 이름·순서)는 §27 규칙과 E0.5에서 잽니다.
- **Mind the Gap, 2509.15020** (EMNLP 2025 Main, HF 4) [HIGH]
  - 라벨 문자 앞 공백을 어떻게 토큰화하느냐만으로 정답률이 최대 11% 움직였고, 보기 순서를 바꾼 효과보다 컸습니다.
  - [접목] Jev 보기 표시 문자열(공백·구두점)도 템플릿 해시에 넣어 고정합니다.
- **Rosenfeld·Glazer·Fetaya (Bar-Ilan), 2511.11206 "Questioning the Stability of VQA"** (v1 2025-11-14, 학회 없음, HF 1) [MED]
  - GPT-4o는 패딩·크롭만으로 인스턴스의 0.08이 답을 바꿨고, 섭동 전체로는 0.14였습니다(이미지 기준 0.93).
  - 모든 섭동에 안정한 표본의 정답률은 0.91로, 기준 0.78보다 높았습니다.
  - [접목] Astra 격자 이미지의 해상도·패딩·배치·덧그림 글꼴을 바이트 단위로 고정합니다. 반복 호출 사이 불일치는 "틀렸을 가능성" 신호로 씁니다.
- **Pecher 외 (KInIT), 2602.04297** (v1 2026-02-04, 학회 없음) [MED-LOW, 보조로만]
  - 인용: "underspecified prompts exhibit higher performance variance". 지시를 명확히 쓸수록 안정적이었습니다.

**(4) 구조화 출력**
- **Lee·D'Antoni·Berg-Kirkpatrick (UCSD), 2604.03616 "The Format Tax"** (v1 2026-04-04, 학회 없음, HF 0) [MED]
  - 인용: "format-requesting instructions alone cause most of the accuracy loss, before any decoder constraint is applied"
  - 오픈 가중치 모델 평균 −3.9pp, grammar-constrained decoding(GCD)이 추가로 −1.6pp였습니다.
  - 자유 서술 후 2턴째에 형식으로 바꾸는 방식은 72개 비교 중 42개에서 유의하게 나아졌습니다(평균 +6.8pp). extended thinking은 평균 +9.2pp였습니다.
  - 인용: "most recent closed-weight models show little to no format tax"
  - [접목] Astra는 추론 모델이고 폐쇄 모델이라 JSON 계약 스키마를 그대로 유지합니다. E-M2-3 첫 시도 통과율이 80% 미만일 때만 "자유 계획 → 2턴 스키마 변환"을 비교 조건으로 넣습니다.

**(5) 재계획 일관성과 계획 고정(anchoring)**
- **AgenticCache, 2604.24039** (v1 2026-04-27, MLSys 2026, SNU·Stanford) [HIGH]
  - 인용: "embodied tasks exhibit strong plan locality, where the next plan is largely predictable from the current one"
  - 예: "go grasp target" 다음이 "put into container"인 경우가 59.7%였습니다.
  - 성공률 +22%, 지연 −65%, 토큰 −50%. 백그라운드 LLM이 k스텝 뒤 실제 실행 궤적과 비교해 캐시를 검증합니다.
- **Agentic Plan Caching, 2506.14852** (v1 2025-06-17, NeurIPS 2025) [HIGH]
  - 구조화된 계획 템플릿을 저장·적응·재사용해 비용 −50.31%, 지연 −27.28%를 얻었습니다.
- **Liu 외 (UIUC·IBM), 2604.12147 "From Plan to Action"** (v1 2026-04-13, ACM DOI 10.1145/3832783.3834400, 학회 이름 미확인) [MED-HIGH]
  - 궤적 21,120개를 분석했습니다.
  - 인용: "periodic plan reminders can mitigate plan violations"
  - 초반에 모델 전략과 맞지 않는 단계를 넣으면 성능이 떨어졌습니다.
- **2609.19654 "Replan, Repair, or Edit?"** (v1 2026-09-17, 학회 없음, 1주 전 공개) [MED-LOW, 보조로만]
  - 인용: "Successful hierarchical and local repairs made fewer edits and retained more accepted commitments than full replanning"
- [종합 접목] M2 R6(patch 재계획)을 실행 중 재계획의 **기본값**으로 올리고, "유지가 기본, 바꾸는 단계만 이유와 함께"를 제안합니다([제안], 사용자 원칙에는 영향 없음).

**(6) 적은 호출로 투표하기**
- 이미 설계에 있는 Adaptive-Consistency(기간 밖 기초 문헌)를 그대로 씁니다.
- CGES(2511.02603, NeurIPS 2025 워크숍 예비판)는 58% 절감(16.0 → 6.7회)을 보고했지만 [MED-LOW]이고, 확신 신호가 필요해 logprob이 없는 Astra에는 맞지 않습니다.
- DeepConf(2508.15260, HF 92, 414★)도 토큰 logprob이 필요해 Astra에 **적용할 수 없습니다**.

### 2. 제외 (신뢰도 LOW, 권고 근거로 쓰지 않음)
- 2601.19934: 단독 저자, 학회 없음.
- 2606.13685 "Coin Flip Judge": 단독 저자, 학회 없음. ID는 2606인데 abs v1 날짜가 2026-04-23으로 서로 어긋납니다. flip 13.6%, 다수결에 11회 필요라는 수치가 있지만 쓰지 않습니다.
- 2606.19544 "Reliability without Validity": 학회 없음. test-retest > 0.95인데 위치 편향 > 0.10이라는 결과는 방향이 일치해 참고만 합니다.
- 2604.11581: 단독 저자, 학회 없음.
- 2604.26954: NCME 발표, 단독 저자.
- 2607.09665 FSI: 단독 저자.
- 2606.09410 "Capacity, Not Format": 단독 저자.
- 2603.02601 AgentAssay: 단독 저자 기술 보고서.
- 2608.04066: 단독 저자, 7쪽.
- 2603.20985 "Consistent but Dangerous": 의료 CVPR 워크숍, MED-LOW. "일관되지만 이미지를 안 봄"은 PACT 논점과 같은 방향이라 방향 근거로만 둡니다.
- 2603.03111: 학회 없음.
- 2601.17768 LLM-42: MSR, 29★. 서버 쪽 기법이라 우리가 쓸 수 없습니다.

### 3. 제안 1: Astra 일관성 프로토콜 (정본 §28 후보) [제안]
- **A1 템플릿 고정과 버전**
  - `astra_prompt_id` = SHA-256(시스템 문장 + 계약 JSON 스키마 + 스킬 카드 + 술어 어휘 + 예시 계약 + 격자 렌더러 버전).
  - 실험 도중에는 바꾸지 않고, 버전은 실험 사이에만 올립니다. 매 호출 기록합니다.
  - 모델은 날짜가 박힌 스냅샷 ID로 고정하고 별칭은 쓰지 않습니다. 응답의 model/fingerprint 필드를 기록합니다. 다만 Astra API에 이런 필드가 있는지는 **미확인 [가정]**입니다.
  - 근거: FormatSpread, Chen 외, Log-prob Tracking.
- **A2 입력 정규화**
  - 텍스트: 물체는 id 순, 술어는 등록부 순서, 숫자는 고정 자릿수, 시각은 상대 시각 범주로 적습니다.
  - 이미지: 격자 배치, 해상도, `detail` 명시, 패딩, 덧그림 글꼴·위치를 고정하고 프레임은 시간순으로 둡니다.
  - 순서: 정적 부분(시스템·스키마·카드)을 앞에, 동적 부분(상태·프레임·실패 문맥)을 뒤에 둡니다.
  - 이렇게 하면 prefix 캐시에도 유리합니다. 다만 캐시가 결정성을 보장하지는 않습니다.
  - 근거: VQA stability, Mind the Gap, Pecher.
- **A3 출력 스키마**: 지금의 계약 JSON과 검사기 1~6을 유지합니다. 2턴 변환은 조건부 비교로만 둡니다(Format Tax).
- **A4 재계획 고정(anchoring)** (M2 R6 강화)
  - T0 이후 재계획 입력: 활성 계약 + `based_on` 이후 변한 사실 목록 + 이미 VERIFIED·EXECUTING인 단계.
  - 출력: 기본은 `patch`입니다. 바꾸는 단계마다 `change_reason`에 근거가 된 변화 사실 id를 붙이게 하고, 이미 실행된 단계는 바꿀 수 없게 합니다.
  - 매 호출 재계획 편집 거리(바뀐 단계 수)를 기록합니다. 근거 사실 id가 없는 변경은 경고(`C_assume` 쪽 로그)로 남깁니다.
  - 계획 요약을 Jev 조각에 계속 싣는 것은 이미 설계에 있습니다("periodic plan reminders"와 같은 방향).
  - 근거: AgenticCache, APC, Plan-to-Action (보조 2609.19654).
- **A5 투표 여부와 횟수**
  - T0(정지 허용), effort low: K = 3을 **병렬**로 부릅니다. 벽시계로는 가장 느린 호출 하나 정도(약 3 s대, [가정], E0에서 측정)입니다.
  - "계획 서명"을 정의합니다: 단계 스킬 열 + 결정 지점 id + 물체 역할. 셋 모두 같으면 채택하고, 2/3이면 다수를 채택합니다. 셋 다 다르면 검사기를 통과한 것 중 첫 번째를 쓰고 `plan_unstable`를 기록합니다. 추가 호출은 하지 않습니다.
  - T_fail·T3처럼 비정지인 호출은 K = 1입니다. 투표 때문에 지연을 늘리지 않고, 오류는 검사기와 M4 (b)가 잡습니다.
  - effort high(첫 토큰 약 73 s)에서는 투표하지 않습니다.
  - 해석: 같은 관측에 대한 반복은 분산만 줄이고 증거는 늘리지 않습니다(PACT). 반복 사이 불일치는 "틀렸을 가능성" 신호로만 씁니다(VQA stability). effort를 올려도 분산이 준다는 보장은 없습니다(ReasonBENCH).
  - K = 3과 규칙은 설계 선택([가정])이고, E0 Astra 반복 결과로 확정합니다.
- **A6 재현 기록**
  - 요청 원문 전체(이미지 바이트 해시 + 원본 저장), `astra_prompt_id`, 모델 ID, effort, 최대 토큰, 사용량(추론 토큰 포함), 첫 토큰 시각·완료 시각, 원응답, 검사기 결과, 계획 서명, patch 편집 거리, KST·PDT 시각.

### 4. 제안 2: Jev 일관성 프로토콜 (정본 §28 후보) [제안]
- **J1 질문 버전**
  - `question_id@vN` = 해시(문구 + option_key 표준 순서 + 보기 설명 + 표시 문자열(공백 포함) + legend + 상태 직렬화기 버전).
  - 지금의 `question_id`(문구·보기 해시)를 넓힌 것입니다. §27 R5의 `perm_id`·대응표 기록은 그대로입니다.
- **J2 상태 직렬화 정규화**: 같은 세계 상태 → 바이트까지 같은 텍스트가 되게 합니다. M1 후보 A 표를 id·등록부 순서로 적고, 숫자는 고정 구간으로 나누고, 나이는 범주로 적습니다. 그래야 test-retest를 잴 수 있고, 불일치가 상태 변화에서 온 것인지 구분됩니다.
- **J3 M4와의 관계**
  - 합의 표는 지금처럼 시간차 상태에서만 모읍니다. 같은 입력을 되묻는 것은 합의 표로 세지 않습니다(PACT와 같은 방향). 같은 입력 반복은 측정용일 뿐입니다.
  - [우리 계산, 독립 가정] 호출마다 최빈 보기에서 벗어날 확률이 p이고 두 갈래 결정이라면, 두 호출이 잡음만으로 어긋날 확률은 약 2p(1−p)입니다. 논문 바닥 1.33%면 약 2.6%입니다.
  - 따라서 `FLIP_TH`와 LA-2 불일치 해석은 E0.5 (ii)에서 잰 바닥 위에서 해야 합니다(E0 판정 6을 더 분명히 한 것).
- **J4 확률 사용**: 질문이 다르면 확률끼리 비교할 수 없습니다(공식 약점). 게이트와 표류 감시는 모두 `question_id@vN`별로 합니다.

### 5. 제안 3: 측정에 더할 것
- **E0에 추가: Astra 같은 입력 반복**
  - 실제 T_fail 입력 3개 × effort {low, high} × 반복. low는 background-temperature 절차대로 입력당 여러 번, high는 비용 때문에 적게 돌립니다(횟수는 [가정], 비용 추정 뒤 확정).
  - 지표: 계획 서명 exact-match 비율, 필드 단위 flip, patch 편집 거리 분포, 지연.
  - 판정: low의 서명 불일치가 high보다 유의하게 클 때만(짝 부트스트랩 95% 하한 > 0) "low는 투표 K = 3 필요"로 확정합니다. 아니면 A5를 T0 전용으로 유지합니다.
- **E0.5 (ii) 확장**
  - test-retest를 층별(2지선다·Noul / k = 3~6 / k = 7~17)과 시간 블록별로 따로 잽니다.
  - 판정: 블록 사이 바닥 차이가 유의하면, 폐루프 조건을 같은 시간 블록 안에 교차 배치합니다(E0 판정 1을 이 근거로 확장).
- **매일 카나리 (새 항목, E0 이후 모든 실험일)**
  - Jev: 고정 스냅샷 × 고정 `question_id@vN` 소수 세트를 그날 첫 실행 전에 돌려 최빈 보기와 확률 분포를 기준일과 비교합니다(Log-prob Tracking식).
  - Astra: 고정 입력 1~2개를 low로 돌려 계획 서명을 비교합니다(Behavioral Fingerprints식).
  - 판정: 기준 대비 불일치가 그날 test-retest 바닥보다 유의하게 크면(95% 하한 > 0, Holm) "표류 의심"입니다. 그날 결과는 분리 보고하고, E1 보정 부분을 다시 돌린 뒤 게이트를 재사용합니다. `model` 필드가 바뀌어도 같은 처리를 합니다.
- **E1에 추가**: 보정값은 `question_id@vN`과 모델 ID에 묶습니다. 버전이 바뀌면 그 질문의 게이트를 끄고 재보정합니다.
- **E-M8a·E2a의 Astra 조건**: 반복 실행과 검정력 계산을 사전 등록합니다(KTH: 2%p에 약 9회, ReasonBENCH: n ≥ 9). 한 번 실행한 비교로는 결론을 내지 않습니다.

### 6. 사용자에게 알릴 것과 한계
- **사용자 원칙은 바뀌지 않습니다.** 실패 시 Astra 호출, 겹침 3회/초, effort low 기본 + low·high 비교가 그대로입니다. 투표는 T0에만 두어 비정지 원칙과 충돌하지 않습니다.
- **API 기능 미확인 [가정]**: Astra에 seed, 응답 fingerprint 필드, prompt caching이 있는지 확인하지 못했습니다. Jev에 seed가 있는지도 확인하지 못했습니다. 어떤 경우든 temperature 0이나 seed로 결정성을 얻을 수 없다는 전제는 유지합니다(NeurIPS Oral, Thinking Machines).
- **제안 규칙의 값은 설계 선택입니다.** K = 3, 계획 서명 정의, 카나리 크기는 논문에서 가져온 값이 아니므로 [가정]으로 표시했고, E0에서 확정합니다.
- **인용 수는 대부분 미확인입니다**(Semantic Scholar 429 때문).
- **[결정 필요]** 두 가지:
  - (가) T0 병렬 K = 3 투표를 기본으로 둘지
  - (나) 실행 중 재계획을 patch 기본으로 올릴지(M2 R6 → 기본)

파일: D:\tools\audit_d17\abs\*.html (arXiv abs 원본), D:\tools\audit_d17\hf\*.html (HF 추천 수), D:\tools\audit_d17\gh\*.html (GitHub 스타 04:35 UTC)
