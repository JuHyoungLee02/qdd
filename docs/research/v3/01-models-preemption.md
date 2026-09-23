# 01. 기반 모델 원문 재검증 + 선점 추적

작성: 2026-09-24 (v3 초안 조사). 대상: `docs/plan.md` v2 §1(두 모델 사실), §4(컨트리뷰션 후보), `docs/research/v2/00-models.md`의 "확인 못 한 것".

---

## 1. 조사 방법과 한계

- **원문 직접 읽기 (curl)**
  - TypeSafe 문서: `docs.typesafe.ai/llms.txt`, `sitemap.xml`로 전체 목록(약 120쪽)을 확인한 뒤, 23쪽을 `.md` 원문으로 받아 읽었다(jaggedness, api, models, primitives/choice·score·noul·advanced, confidence, machine-learning-primer, state, system-one, how-to-build, fan-out, parallel_questions cookbook, SDK retries/constants/exceptions, use-case-map 등).
  - TypeSafe 홈페이지, 출시 블로그(2026-09-15) 본문, OpenRouter Jev 모델 페이지와 가이드.
  - TypeSafe 공식 X 게시물(대기자 명단 폐지)은 fxtwitter API로 원문과 시각을 확인했다.
  - OpenAI 문서(`.md` 원문): 모델 페이지 `gpt-6-astra`, 이미지·비전 가이드, reasoning 가이드, latest-model(GPT-6) 가이드, fast mode, pricing.
  - Artificial Analysis 제공자 페이지 5개(Astra low/medium/high/xhigh/max).
  - GitHub: README 5개(Jev-as-Policy, jev-libero, Awesome-Astra-Embodied-AI, GPT-as-Policy, awesome-jev), 저장소 메타데이터 9개. 조사 도중 GitHub API 비인증 한도에 걸려 일부 스타 수는 웹 페이지에서 읽었다.
  - arXiv: 원문 HTML(초록 + 관련 절)을 읽은 논문 5편(2609.12541, 2609.19138, 2608.17209, 2609.24170, 2607.08448). arXiv 웹 검색 결과에서 초록 전문을 읽은 논문 9편(2609.26758, 2609.26532, 2609.26550, 2609.25845, 2609.24965, 2609.23959, 2609.23886, 2607.17213, 2609.20330).
- **arXiv API(export.arxiv.org)는 429로 막혔다.** 대신 `arxiv.org/search` 웹 검색을 썼다. 검색어: `Jev`, `TypeSafe`, `"System One model"`, `"decision model" robot`, `"calibrated decisions"`, `GPT-6 Astra robot`(최신순 50건).
- **WebSearch 4회 사용** (한도 15회).
  - `"Jev as Policy" robot Astra`
  - `Jev TypeSafe robot arm manipulation Astra planner hierarchical`
  - `Jev real-time chunking overlapping calls robot action smoothing asynchronous`
  - `GPT-6 Astra robot "reasoning effort" replanning frequency event-triggered comparison latency`
- Semantic Scholar도 429에 자주 걸려 인용 수는 일부만 얻었다.
- 한계
  - Artificial Analysis 수치는 매일 바뀌는 실시간 값이다(아래 표는 2026-09-24에 읽은 값).
  - Jev를 직접 호출해 지연이나 보정을 재지는 않았다. 이번 과제 범위 밖이다.

---

## 2. 검증 표

### 2-A. Jev (TypeSafe AI)

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| jaggedness 페이지 검토일 | ORIGINAL-CONFIRMED | **"Last reviewed 2026-09-17"** (v2의 "9/16 또는 9/17" 정리). 대상 `jev-1.13` | https://docs.typesafe.ai/model-jaggedness/jev-1.13 |
| 실패 유형 9개와 공식 권장 | ORIGINAL-CONFIRMED | 전문을 아래 §2-A-1에 옮겼다. v2가 요약에서 빠뜨린 것: **#7 지시와 기준의 모순**, **#8 상식적 구조 불변성이 보장되지 않음**, **#9 생성 금지**, **Score 기댓값으로 크기를 보간하지 말 것**. v2의 "세기"는 counting(개수 세기)을 말한다 | 같은 곳 |
| 요청당 최대 질문 수 | ORIGINAL-CONFIRMED (**개수 제한은 없음**) | 문서 어디에도 질문 개수 상한이 없다. 제한은 토큰뿐이다: **요청 전체(state + 모든 질문) 64k, state + 가장 긴 질문 하나 32k.** "state를 한 번 읽고 모든 질문을 병렬로 평가한다." 공식 cookbook 수치: 질문 13개를 한 번에 보내면 0.27초, 따로 13번 보내면 2.71초(10.0배 빠르고 12.2배 저렴). 블로그와 문서 사례에서는 한 요청에 218개 줄 id를 Choice 하나로 점수 매긴 경우도 있다 | https://docs.typesafe.ai/models , https://docs.typesafe.ai/cookbooks/parallel_questions.md , https://docs.typesafe.ai/patterns/fan-out |
| 속도 제한 | ORIGINAL-CONFIRMED (신규) | **250,000 토큰/초, 1,200 요청/분**(= 초당 20회). 초과하면 429, 과부하면 529. 문서 경고: "수요 때문에 **예고 없이 바뀔 수 있다**." SDK 기본 재시도: `max_retries=2`, backoff 0.5~5초, timeout 30초 | https://docs.typesafe.ai/models , https://docs.typesafe.ai/api , https://docs.typesafe.ai/sdk/python/api/retries |
| 지연 | ORIGINAL-CONFIRMED (업체 수치) + 제3자 측정 1건 | 출처마다 수치가 다르다.<br>• 블로그: "70ms–500ms".<br>• how-to-build 문서: "Most queries complete in about 100 ms".<br>• use-case-map: "real-time speeds (150ms)".<br>• **블로그 단서: "평가는 대체로 서부 해안에 있는 우리 노트북에서 돌렸다(서비스도 그곳에 있다)"** → 한국에서 호출하면 왕복 지연이 더해진다(우리 측정은 없음).<br>• **OpenRouter P50 0.37초**(1주, 전 지역, 독립 집계). 가용성 99.84%(3일).<br>• robokrunch 데모: p50 0.527초, p95 0.813초(LOW) | https://typesafe.ai/blog/introducing-system-one-models-and-jev , https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md , https://openrouter.ai/typesafe/jev-1.13 |
| Choice 보기 수 | ORIGINAL-CONFIRMED | "maximum of 255 options per Choice". 블로그: 보기가 많을 때는 내부에서 2단계(따로 점수 → 명시적 선택)로 처리하므로 **가끔 느려진다** | https://docs.typesafe.ai/api , 블로그 |
| Score 단계 | ORIGINAL-CONFIRMED | "at least two levels; the API accepts up to 10". 응답은 `score`(확률 가중값, 단계 사이 값 가능), `legend`, `probabilities`, `confidence` | https://docs.typesafe.ai/api |
| Noul | ORIGINAL-CONFIRMED | 응답은 `noul`(0~1)만 있고 confidence는 없다. `criteria.true/false`로 예/아니오의 뜻을 적을 수 있다 | 같은 곳 |
| confidence의 정의 | ORIGINAL-CONFIRMED (신규) | 확률 분포에서 **계산한 통계량**이다. 문서 위젯 코드: `(K·p_max − 1)/(K − 1)`. 확률 외에 새 정보는 없다. 문서도 "필요하면 다른 척도를 직접 계산하라"고 한다 | https://docs.typesafe.ai/confidence.md |
| 보정(calibration) 공개 자료 | ORIGINAL-CONFIRMED (**곡선·논문 없음**) | 문서 설명은 정의뿐이다("0.8을 준 것들은 약 80%가 맞아야 한다", "집단 단위이지 개별 정답 보장이 아니다"). **보정 곡선, ECE, RLCD 논문은 문서, 블로그, 홈페이지 어디에도 없다.** FAQ 답은 정적 HTML에 없어 읽지 못했다 | https://docs.typesafe.ai/introduction/machine-learning-primer.md , https://docs.typesafe.ai/concepts/system-one.md |
| 보정에 대한 제3자 수치 | SINGLE-SOURCE, **LOW** | this-that-model-1.0(2609.23886, 2026-09-20). 제3자 68문항에서 **Jev 정확도 0.765, Brier 0.133**. 저자 모델은 0.941 / 0.042. 경쟁 모델 저자의 측정이라 이해 상충이 있다 | https://arxiv.org/abs/2609.23886 |
| 언어 | ORIGINAL-CONFIRMED (신규) | "English is the primary training language ... CJK scripts are handled but not equally well" → **state와 질문은 영어로 쓴다** | https://docs.typesafe.ai/models |
| 미세조정 | ORIGINAL-CONFIRMED (신규) | 고객 데이터로 fine-tune이나 LoRA를 하지 않는다. 모든 계정이 같은 가중치를 쓴다. 적응은 state, instructions, criteria로만 한다. 임계값을 조정했다면 `jev-1.13.0`으로 **버전을 고정**하라고 권한다 | https://docs.typesafe.ai/models |
| 입력 | ORIGINAL-CONFIRMED | "Text only ... No image, audio, or video input." 블로그 Doom 데모 단서: "not on images **(yet…)**" → 비전 계획을 암시할 뿐 로드맵은 없다 | 같은 곳, 블로그 |
| 로봇 관련 공식 지침 | ORIGINAL-CONFIRMED (**없음**) | 문서 전체에 robot 단어가 없다. use-case-map은 "게임이나 UI에 넣을 수 있다"고만 한다. awesome-jev 관리자도 "로봇·물리 안전 지침 없음"을 확인했다 | https://docs.typesafe.ai/concepts/use-case-map.md , https://github.com/Frank-ZY-Dou/awesome-jev |
| 대기자 명단 폐지 날짜 | ORIGINAL-CONFIRMED | TypeSafe 공식 X, **2026-09-20 21:30:43 UTC**(한국 시간 9/21 06:30). 원문: "Jev is now available to everyone. No waitlist." v2의 9/20과 9/21은 같은 사건을 시간대만 달리 적은 것이다 | https://x.com/typesafeai/status/2101786156572823624 |
| 창업자 이름 | **WRONG (v2)** | v2의 **"Diego Almeida"는 틀렸다. "Diogo Almeida"**다. 블로그 서명은 "founder"이고 primer 문서는 "cofounder". 공식 문서: "RLHF ... co-invented by Diogo Almeida" | 블로그, https://docs.typesafe.ai/introduction/machine-learning-primer.md |
| 가격 | ORIGINAL-CONFIRMED | 입력 $0.042/1M($42/1B), 출력 무료. 블로그: "보조금이 아니라고 증명할 수는 없다. 가격은 내려갈 것으로 본다" | https://docs.typesafe.ai/models , 블로그 |
| OpenRouter | ORIGINAL-CONFIRMED | 경로가 둘이다: **Decisions API `POST /api/alpha/decisions`(아직 alpha)**, **System One API `POST /api/v1/systemone`**(TypeSafe SDK의 base URL만 바꾸면 된다). OpenRouter 등록일 2026-09-18. OpenRouter 페이지의 컨텍스트 표기는 **32K**다(공식 64k/32k 중 32k만 적은 것으로 보임) | https://openrouter.ai/docs/guides/community/jev , https://openrouter.ai/typesafe/jev-1.13 |
| 67.8%의 기준 | ORIGINAL-CONFIRMED | 블로그: 기준 확률은 "Astra와 Fable의 평균"이다(v2 해석과 같음). 업체도 "OpenAI와 Anthropic 쪽으로 치우친다", "모델 역량팀이 만들어서 편향이 있을 수 있다"고 인정한다 | 블로그 |

#### 2-A-1. Jev 1.13 jaggedness 전문 (2026-09-17 검토판)

| # | 실패 유형 | 공식 권장 ("Do this instead") | 원문 핵심 |
|---|---|---|---|
| 1 | Literal reading | Write the exact condition, criteria for each available option | 범위어, 부정, 암묵 조건을 글자 그대로 읽는다. 해석이 필요하면 **글자 그대로 읽히는 질문 두 개로 나누고 코드에서 합친다** |
| 2 | Math and Numbers | Keep the arithmetic in code | (a) **개수를 세지 못한다**. 코드로 후보를 돌며 후보마다 질문 하나씩. (b) **수치 표현이 약하다**. RGB나 hex가 서로 가까운지 판단하지 못한다. 코드에서 수치를 **이름 붙인 구간**으로 바꿔 준다. (c) **Score 기댓값으로 두 단계 사이의 정확한 크기를 보간하지 말 것.** 임계값 판정에는 써도 된다 |
| 3 | Date and time comparison | Extract components; compare in code | 날짜를 순서 있는 양이 아니라 텍스트로 읽는다. 요소 추출(Choice)만 맡기고 비교는 코드에서 |
| 4 | Indirection | Reduce hops; point to the relevant state | 이중 부정이나 "속성의 속성"에 약하다. state 필드를 이름으로 가리킨다 |
| 5 | Large state full of irrelevant detail | Filter first; send only what the question needs | 관련 없는 내용이 방해물이 된다("context rot"). 걸러낼 수 없으면 Noul로 관련성부터 거른다 |
| 6 | Adversarial content | Write precise prompts, test edge cases | state를 적대적 입력으로 보지 않는다. 주입된 지시가 답을 움직인다 |
| 7 | Contradictory instructions and criteria | Align the criteria and instruction | 예: true가 "아니오"를 뜻하는 Noul은 성능이 떨어진다 |
| 8 | Common-sense structural invariants | Ask each decision one way; enforce identities in code | **같은 질문이라도 Noul `0.22`와 Choice `yes 0.01`처럼 다르게 나온다. 긍정과 부정 Noul의 합이 0.72 + 0.47 = 1.19가 된다.** "Noul에서 맞춘 임계값을 Choice로 옮기지 말 것. 서로 다른 질문 사이에 산술 항등식을 기대하지 말 것." Choice는 상대적(어느 것), Noul은 절대적(각각 참인가) |
| 9 | Generation | Use a generative model | 생성은 하지 않는다. 추출은 후보를 먼저 뽑아 Choice로 고르게 한다 |

### 2-B. GPT-6 Astra (OpenAI)

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| effort 단계 | ORIGINAL-CONFIRMED | **`low`, `medium`, `high`, `xhigh`, `max`.** Astra는 **`none`을 지원하지 않는다**(Sol과 Luna는 지원). effort와 별개로 `reasoning.mode = pro`가 있다. 새 기능: 대화 중 `configuration_update` 항목으로 **캐시를 유지한 채 effort를 바꿀 수 있다** | https://developers.openai.com/api/docs/models/gpt-6-astra.md , https://developers.openai.com/api/docs/guides/latest-model.md , https://developers.openai.com/api/docs/guides/reasoning.md |
| **logprobs** | ORIGINAL-CONFIRMED, **plan에 영향이 큼** | 공식 문서: "effort가 `none`이 아니면 `temperature`, `top_p`, `top_logprobs`를 빼라. Chat Completions에서는 `logprobs`도 빼라." Astra에는 `none`이 없으므로 **Astra로는 logprob를 얻을 수 없다.** plan §3의 "logprob 기반 일반 LLM 선택기", M7의 TOPReward식 사용은 Astra로 할 수 없다. Sol이나 Luna를 `none`으로 쓸 때만 가능하다 | 같은 곳 |
| 입력 모달리티 | ORIGINAL-CONFIRMED | 텍스트와 이미지만 받는다. 출력은 텍스트. **Videos, Realtime, Live 엔드포인트는 "Not supported"** → 비디오 입력은 없다(v2와 같음, 이제 원문 확인) | 모델 페이지 |
| 요청당 이미지 수 | ORIGINAL-CONFIRMED (v2에서는 UNCONFIRMED) | **요청당 최대 1,500장, 요청 전체 512MB.** 이미지 한 장당 패치 30,000개 초과 시 거부(자동 축소하지 않음) | https://developers.openai.com/api/docs/guides/images-vision.md |
| 이미지 토큰 계산 | ORIGINAL-CONFIRMED | 32×32 px 패치 수 × **1.2**(Astra 배수).<br>• `low`: 512×512 안으로 맞춘다 → 최대 256패치 ≈ **308토큰**.<br>• `high`: 2,500패치 예산 → 1024² = 1,229토큰, 2048²는 1600²로 줄여 3,000토큰.<br>• `original`: 원본 크기(한 변 65,535px, 30,000패치까지).<br>• **`auto`(기본값)는 `original`과 같다** → 지정하지 않으면 큰 이미지가 그대로 비싸게 들어간다 | 같은 곳 |
| 컨텍스트와 출력 | ORIGINAL-CONFIRMED | 컨텍스트 1,050,000, **최대 입력 922,000**, 최대 출력 128,000, 지식 기준일 2026-04-30 | 모델 페이지 |
| 가격 | ORIGINAL-CONFIRMED | 입력 $10, 캐시 입력 $1, 캐시 쓰기 $12.5, 출력 $50 (1M 토큰). 입력 272K 초과 시 입력 2배, 출력 1.5배. Batch와 Flex는 50%. **Fast mode는 2배($20 / $100)** | 모델 페이지, https://developers.openai.com/api/docs/pricing.md |
| Fast mode | ORIGINAL-CONFIRMED, **v2 정정** | Priority processing이 2026-07-30에 Fast mode로 이름을 바꿨다(`service_tier: "fast"`). 공식 문서의 "up to 2.5×"는 Sol에 대한 문장이고, **Astra의 속도 배수는 적혀 있지 않다.** v2의 "속도 최대 2배"는 원문 근거가 없다. **"Fast mode for GPT-6 Astra does not include a latency SLA."** 트래픽이 급증하면 일부 요청이 standard로 강등될 수 있다 | https://developers.openai.com/api/docs/guides/fast-mode.md |
| 첫 답변 토큰까지 시간 (Artificial Analysis, 2026-09-24에 읽음) | CONFIRMED (독립 측정, 실시간 값) | **low 3.03초, medium 5.86초, high 73.16초, xhigh 198.11초, max 352.15초**(OpenAI; Bedrock은 335.21초). 출력 속도는 약 45~52 토큰/초. **v2 수치(low 2.79 / high 45.16 / max 250.18초)는 과거 스냅샷이다. 값이 날마다 바뀌고 특히 high가 크게 늘었다.** 인용할 때는 날짜를 함께 적는다 | https://artificialanalysis.ai/models/gpt-6-astra-low/providers (… -medium, -high, -xhigh, /gpt-6-astra/providers) |
| 속도 제한 | ORIGINAL-CONFIRMED | Tier 1: 500 요청/분, 50만 토큰/분 … Tier 5: 15,000 요청/분, 4,000만 토큰/분 | 모델 페이지 |
| GPT-6 Sol과 Luna의 존재 | ORIGINAL-CONFIRMED (v2에서는 SINGLE-SOURCE) | 공식 가이드: "GPT-6 model family includes GPT-6 Astra, GPT-6 Sol, and GPT-6 Luna". 가격: Sol $2/$10, Luna $0.10/$0.50. 둘 다 `none` effort 지원 → logprob 기준 방법 후보 | latest-model 가이드, pricing |
| 비동기 도구 호출, 중간 조정 | ORIGINAL-CONFIRMED (신규) | GPT-6 신기능. `async: true` 도구(모델이 도구 결과를 기다리지 않고 계속 진행), **mid-turn steering**(작업 중에 WebSocket으로 새 지시를 넣는다) → M8의 "멈추지 않는 Astra 호출"에 쓸 수 있는 API 기능 | latest-model 가이드 |
| 이미지 한계 (공식) | ORIGINAL-CONFIRMED | "정밀한 공간 위치 파악(체스 판 위치 등)에 약하다", 개수 세기는 근사치, 회전된 이미지나 파노라마·어안 이미지에 약하다 | images-vision 가이드 |

### 2-C. 선점 후보 원문 확인

| 항목 | 확인 수준 | 내용 (원문 기준) | 출처 URL |
|---|---|---|---|
| YuanKJing/Jev-as-Policy | ORIGINAL-CONFIRMED | **37★, 포크 2, 생성 2026-09-21, 마지막 푸시 9/21.** README: Dmytro Hrybov의 X 데모(2026-09-18, 좋아요 628, 조회 4.5만)가 공개한 "Jev as Policy" 구조를 재현한 것이다. MuJoCo Panda에서 **업데이트마다 순차 호출 2번**: ① intent Choice(approach/grasp/lift/carry/lower/release/withdraw/finish), ② x/y/z ∈ {positive, negative, stay}, fingers ∈ {open, close, stay}. 로컬 DLS IK, 20ms 서보, 100ms 목표 필터. 결과는 참고 녹화 1편뿐이다. **"Astra + JEV 평가 결과는 후속 공개"는 아직 없다.** 겹침 호출이나 자기 검증은 없다 | https://github.com/YuanKJing/Jev-as-Policy , https://x.com/dimentary/status/2101018760371171420 |
| cosmic-snail/Jev-as-Policy | ORIGINAL-CONFIRMED | YuanKJing의 **포크**다(0★, 2026-09-23). 독립 작업이 아니다 | GitHub API |
| Dimweaker/jev-libero | ORIGINAL-CONFIRMED | **63★, 생성 2026-09-19.** 층별 Jev 선택(intent → 접촉·동작 계열 → 원자 입력 27종). 각 후보를 **되돌릴 수 있는 시뮬레이터 분기로 최대 8스텝(0.4초) 미리 실행**해 효과를 보고 고른다. 이는 시뮬레이터 특권이라 실물에서는 쓸 수 없다. 결과는 과제 3개에 **성공 예시 1편씩**(seed 1): 전자레인지 14회 결정, 서랍 20회, 수프 캔 40회. 성공률 통계는 없다. jiangmingxuan234-alt/jev-libero-api는 포크다 | https://github.com/Dimweaker/jev-libero |
| Awesome-Astra-Embodied-AI | ORIGINAL-CONFIRMED | **1,006★, 생성 2026-09-12.** 사례 36개와 평가 보고서 4개. **Jev와 결합한 사례는 0개**다. **v2 정정: 이 목록(9/21 푸시본)에는 v2가 "목록에 있다"고 적은 arXiv 3편(2609.12541, 2609.19138, 2608.17209)이 없다.** 목록에 있는 것은 GPT-Policy-Eval 저장소, GPT-as-Policy, RoboDojo, RoboCurve, Harness VLA 등이다 | https://github.com/zjwzcx/Awesome-Astra-Embodied-AI |
| awesome-jev (Frank-ZY-Dou) | ORIGINAL-CONFIRMED (신규) | 14★. 2026-09-19~20 기준 Jev 로봇·시뮬 사례 전수 목록. 관리자 주석: "arXiv에서 'TypeSafe', 'Jev'를 검색했으나 동료 심사 평가는 없음." **Astra + Jev 로봇 사례는 둘뿐이고 둘 다 실측이 없다**: AliUraish/Jev_SO101("Astra가 두 시점을 해석하고 Jev가 typed skill을 고르며 unsafe/done 질문을 판정한다", README가 "합성 오케스트레이션이지 물리 시뮬이 아님"이라고 밝힘), rokbenko/quackd("TypeSafe API로 실행한 적 없음") | https://github.com/Frank-ZY-Dou/awesome-jev |

---

## 3. 새로 찾은 것과 모듈별 시사점

### 3-1. 선점 위험 표 ★

우리 컨트리뷰션 후보(plan §4):
- **C-M4**: 객관식 결정 모델의 계단식 겹침 호출 + 확률 기반 자기 검증 업데이트 + 응답 시점 상태 예측
- **C-M8**: Astra 호출 방식(주기 / 이벤트 / 시간 초과) × effort 정량 비교
- **C-M6**: 스킬 내부 결정 지점을 typed 질문으로 여는 결합

| 논문/저장소 | 무엇을 하나 (원문 기준) | C-M4 겹침 | C-M8 겹침 | C-M6 겹침 | 신뢰도 근거 | 위험도 |
|---|---|---|---|---|---|---|
| **Jev-as-Policy** (YuanKJing, 원 데모는 Dmytro Hrybov X 2026-09-18) | Jev 순차 2회 호출(intent → 축별 부호 Choice), 로컬 IK·서보. "Astra + JEV를 RoboTwin 등에서 평가해 곧 공개" 예고 | 낮음. 겹침·자기 검증이 없고, 한 업데이트 안에서 순차로 부른다 | **예고된 결과가 나오면 중간.** Astra+Jev 로봇 평가 자체를 선점한다. 호출 방식이나 effort 비교를 할지는 알 수 없다 | 낮음~중간. intent Choice ≈ 단계 선택이지만 기존 스킬 결합은 아니다 | 37★, 생성 3일, 저자 소속 불명 → LOW | **중간 (감시 1순위)** |
| **jev-libero** (Dimweaker) | 층별 Jev 선택 + 시뮬 분기 미리보기 + 27개 미세 입력 | 없음 | 없음 | 낮음 | 63★, 예시 1편씩 → LOW | 낮음 (M3 "촘촘한 행동" 발상은 이미 공개) |
| **Jev_SO101** (AliUraish), **quackd** (rokbenko) | Astra가 장면을 해석하고 Jev가 typed skill과 unsafe/done을 판정. 실측 없음 | 없음 | 낮음 | **발상 수준에서 중간.** "Jev로 스킬 고르기 + 완료 판정 Noul"은 공개됐다 | 스타 미확인(API 한도), 합성 데모 → LOW | 낮음~중간 |
| **REFLEX** (arXiv 2609.26532, 2026-09-22, Wu & Lim) | LLM 에이전트(로봇 아님)에서 Jev를 빠른 typed 결정층으로 쓰고, **confidence가 낮거나 생성이 필요할 때만** 강한 LLM을 부른다. 100개 과제에서 95% 성공, 강한 모델 호출 72.7% 감소 | 없음 | **발상 수준에서 중간.** "Jev confidence 기반 상위 호출"은 이미 논문으로 나왔다. 로봇도 아니고 effort×호출 방식 비교도 아니다 | 낮음 | arXiv만, 이틀 됨 → LOW | 중간 (관련 연구로 인용하고 차별화해야 함) |
| **Agent as Policy (AGP)** (arXiv 2609.12541, 2026-09-11, Notre Dame·UCSD·SDSU, Meng Jiang) | Codex/Claude Code 에이전트가 실물 로봇을 직접 조종한다(코드 작성, 동작 명령, 결과 보고 수정). 조립, 블록, 주사위, 던지기, 수건. 8개 구성 중 7개에서 80% 이상. **Astra effort low/medium/high 비교**(부품 두 쌍 조립, 5회씩 모두 5/5, 9.9 / 9.2 / 9.2분). 경험 파일 누적: 응답 지연 −47.0%(1회차 → 5회차), Terra가 Astra의 경험을 쓰면 1/5 → 4/5 | 없음 | **부분.** effort 비교는 이미 있다. 다만 과제 1개, 5회, 로봇이 에이전트를 기다리는 구조이고, 호출 시점(주기/이벤트/시간 초과) 비교는 없다 | 낮음 | 인용 2(S2), 미심사, 교수급 저자 → LOW~MED | **중간** ("effort가 성공률에 영향 없음" 결과가 있어 우리 C-M8의 새로움이 줄어든다) |
| **GPT-Policy** (arXiv 2609.19138, 2026-09-16, Morphi Robot, 상하이 창지연구원, 푸단 외) | 문맥 컴파일러(과제 관련 시각 전이 보존) + VLM이 행동 제안 + 제약 제어기가 행동마다 검증·실행·결과 보고. 실물 로봇, 조건당 3회 | 없음 | 낮음 | 낮음 | 저장소 cheng-haha/GPT-Policy 270★, 미심사 → LOW~MED | 낮음 (M1·M8의 "연속 프레임 문맥" 설계에 참고) |
| **Teach and Grow (TGL)** (arXiv 2608.17209, 상하이교통대 Hesheng Wang) | Astra + Codex. 시연에서 하위 목표를 뽑아 폐루프 **Skill Block**으로 만들고, 검증된 것은 Skill Library에, 조건과 수리 기록은 Experience Memory에 둔다. **LIBERO 4개 묶음 평균 99.9%, LIBERO-Plus 92.4%** | 없음 | 없음 | **중간.** Astra가 스킬을 잘게 조합하고 검증한다. 다만 빠른 하위 결정 모델은 없다 | 미심사, 유명 로봇 연구실 → MED | 중간 (M6·M10 관련 연구, 기준 방법 후보) |
| **Harness VLA / RPent** (arXiv 2607.08448, 칭화대 외, 2026-07-09) | 기억을 가진 에이전트가 고정 VLA를 재시도 가능한 접촉 프리미티브로 쓰고 분석적 프리미티브와 조합한다. 실행 기록에서 성공 규칙과 실패 모델을 학습한다. LIBERO-Pro +38.6%p, RoboCasa365 +25.4%p. 프로젝트 페이지에서 **2026-09-17부터 Astra를 계획기로 사용**. 계획기는 프리미티브가 끝날 때까지 기다린다(동기식) | 없음 | 낮음 | **중간.** 스킬(프리미티브) 조합 + 실패 복구 + 기억 | RPent 962★, 인용 23 → MED~HIGH | 중간 (M6/M9/M10에서 **반드시 비교해야 할 기존 방법**) |
| **GPT-as-Policy** (Galbot, He Wang·Li Yi 교신) | Astra(`xhigh`)가 π0.5의 행동을 검토하고 필요하면 고친다. RoboDojo 10개 과제에서 48% 성공(Astra 단독 26%). **실행 스텝의 14.4%에서 수정** | 없음 | **중간.** "느린 모델이 빠른 정책에 언제 개입하나"의 실측이 있다. 하위가 Jev가 아니라 VLA다 | 낮음 | 526★, 미심사 → MED | 중간 |
| **RoboDojo 평가** (arXiv 2609.24170, 2026-09-21 제출, 보고서 사이트는 9/16. RoboDojo·RoboProbe, HKU·칭화·버클리·프린스턴·MIT·PKU) | LLM-as-policy. Astra 42개 과제 **평균 성공률 22.48%, Score 28.97**(2,100회). GPT-5.5는 0.88%. **medium effort**, 에피소드당 모델 호출 100회 예산. 한 번 시연을 보여줘도 전체 평균 이득은 없다 | 없음 | 없음 | 없음 | 인용 1, 미심사 → MED | 낮음 ("Astra만" 기준 방법의 근거 자료) |

**결론 (부재 주장의 범위)**
- 검색 범위(§1의 arXiv 검색어 6개, WebSearch 4회, awesome-jev·Awesome-Astra 두 목록 전수)에서 다음 둘은 **찾지 못했다**.
  - "결정 모델(Jev 또는 유사 모델)을 1초에 여러 번 겹쳐 호출하고, 겹침 구간을 확률로 스스로 검증"하는 작업.
  - Jev를 로봇에 쓴 arXiv 논문.
- 따라서 **C-M4는 현재 선점되지 않았다(2026-09-24 기준).**
- C-M8은 부분적으로 겹친다. AGP가 effort를 비교했고, REFLEX는 confidence 기반 호출을, GPT-as-Policy는 개입 비율을 다뤘다. **"호출 시점 × effort × 로봇이 멈추지 않는 조건"의 조합**으로 범위를 좁혀야 한다.
- C-M6은 발상 수준에서 공개 데모(Jev_SO101)와 겹친다. 새로움은 **CaP-X류 스킬 내부 결정 지점의 체계적 개방과 평가**에서 나와야 한다.
- **v2와 plan §3의 "Astra를 쓴 출판 논문은 아직 없다"는 이제 틀렸다(WRONG).** 미심사 arXiv로 AGP, GPT-Policy, TGL, RoboDojo가 있고, Harness VLA도 Astra판을 쓴다.

### 3-2. Jev 관련 신규 arXiv 논문 (모두 2026-09-19~22, 미심사, LOW. 설계 위험 신호로만 쓴다)

| 논문 | 내용 | 우리 모듈에 주는 의미 |
|---|---|---|
| 2609.26758 "Type-Safe Is Not Error-Free" (Sun & Xu) | **보기 이름만 0/1에서 no/yes로 바꿔도** 판정이 뒤집힌다. 1,200개 결정에서 AUC 0.94 → 0.23. 호스팅 Jev에서도 AUC 0.8146 → 0.5806, 재시험 기준선 대비 24배 많이 뒤집힌다. **보기 이름을 무작위 문자열로 바꾸면 정확도 손실 없이 중립으로 돌아간다.** 보기 수가 많을수록 효과가 커진다 | **M3**: `positive/negative/stay` 같은 극성 있는 보기 이름은 위험할 수 있다. 보기 이름(의미 있는 이름 / 중립 / 무작위)을 절제 실험 변수로 둔다. 공식 #1, #7과도 맞는다 |
| 2609.23886 this-that-model-1.0 | 제3자 68문항에서 Jev 0.765 / Brier 0.133 | 보정을 직접 측정해야 한다는 근거를 하나 더한다(이해 상충 있음) |
| 2609.26532 REFLEX | 위 표 참고 | C-M8 관련 연구 |
| 2609.26550 JEV-as-a-Judge | 최고 LLM 판정기와 3%p 이내, 비용 0.36%. **격차는 confidence가 낮은 결정에 몰려 있다** | M7/M8의 confidence 게이트 설계를 뒷받침한다 |
| 2609.25845 Visual Jev | 공개 VLM 백본에서 이미지를 한 번 인코딩하고 질문 여러 개를 배치로 처리해 보기 확률을 읽는다. 질문 32개 기준 8.9배 빠르다 | **M1 후보(사용자 결정 사항)**: "이미지 → 텍스트 변환" 대신 이미지 입력 Jev식 모델을 병행하는 선택지가 생겼다. 확정하지 않는다 |

### 3-3. 모듈별로 가져올 것

- **M3 (행동 표현)**
  - 공식 #2(c): "Score 기댓값으로 두 단계 사이 크기를 보간하지 말라." plan M3의 "확률 가중 평균으로 크기 결정"은 **공식 권장에 어긋난다.**
  - 크기는 Choice 최빈값(또는 코드가 정한 이름 붙은 구간)으로 정한다. 확률 가중값은 임계값 판정에만 쓴다.
- **M4 (겹침 + 자기 검증)**
  - 공식 #8: 서로 다른 질문(Noul과 Choice, 긍정과 부정) 사이에 산술 관계를 기대하지 말라.
  - → **겹침 검증은 "같은 질문 문구, 같은 보기 집합, 같은 질문 유형"끼리의 비교로만 설계한다.** 이전 호출의 Choice 분포와 다음 호출의 Choice 분포를 비교하는 식이다.
  - 속도 제한(초당 20회, 토큰 25만/초)과 질문 개수 무제한(64k 안) 덕분에 초당 3회 계단식 호출은 한도 안이다.
  - 병렬 질문은 추가 지연이 거의 없으므로, 겹침 구간 검증 질문을 **같은 요청에 추측 질문(speculative fan-out)으로 함께 넣는 것**이 공식 패턴과 맞다.
- **M8 (Astra 호출)**
  - Astra의 `configuration_update`(캐시를 유지하며 effort 변경), 비동기 도구 호출, mid-turn steering을 쓰면 "로봇을 멈추지 않는 Astra 호출"을 API 수준에서 구현할 수 있다.
  - 이미지는 `detail`을 반드시 명시한다. 기본값 `auto`는 `original`과 같다.
  - 비용 예: 512×512 `low` 이미지 한 장은 약 308토큰이다. 프레임 10장이면 약 3.1k토큰, 약 $0.03.
- **기준 방법 (plan §3)**
  - "logprob 기반 일반 LLM 선택기"는 Astra로 만들 수 없다. **GPT-6 Sol 또는 Luna를 `effort=none`으로** 쓰거나, TypeSafe 공식 `system-one-adapter-python`(LLM이 같은 Choice/Score/Noul API로 답하게 하는 어댑터, `llm_answer_mode="probabilities"`)을 쓴다. 후자는 Astra에도 적용할 수 있지만 **말로 적은 확률**이지 logprob가 아니다.

---

## 4. 반대 증거와 위험

1. **Jev 보정은 여전히 업체 주장뿐이다.**
   - 공식 자료는 정의만 있고 곡선이나 논문이 없다. 유일한 제3자 수치(Brier 0.133, 정확도 0.765)는 경쟁 모델 저자가 쟀다.
   - 공식 #8은 같은 뜻의 질문이라도 확률이 서로 맞지 않는다고 인정한다(1.19 사례). **"확률 기반 자기 검증"의 전제가 약하다.** 보정 측정을 첫 실험으로 두자는 제안(plan §5)이 더 중요해졌다.
2. **보기 이름의 극성 효과**(2609.26758, LOW)가 사실이면 방향 보기(positive/negative)를 쓰는 기존 Jev 로봇 데모 전부와 우리 M3 원안이 영향을 받는다. 재현이 필요하다.
3. **지연**
   - 업체 수치(70~500ms, 약 100ms)는 미국 서부에서 잰 값이다. OpenRouter 전 지역 P50은 0.37초다.
   - 한국에서 호출하면 더 느릴 수 있다(측정하지 않았다). 초당 3회 호출이면 응답이 겹치는 것이 기본 상황이 된다.
   - 속도 제한도 "예고 없이 바뀔 수 있다."
4. **Astra 지연은 날마다 바뀐다.** high가 45초(v2)에서 73초(오늘)로 늘었다. effort 비교 실험은 같은 날, 같은 조건에서 벽시계 시간을 직접 재야 한다. Fast mode는 Astra 속도 배수가 공개되지 않았고 SLA도 없다.
5. **AGP 결과: Astra effort가 올라가도 성공률과 시간이 같았다**(과제 1개, 5회씩). "effort가 설계 변수"라는 우리 전제에 반대 증거가 될 수 있다. 과제가 단순했을 수도 있다.
6. **RoboDojo: 한 번 시연을 보여줘도 전체 평균 이득이 없다.** Astra에 연속 프레임이나 예시를 주는 설계(M8, M10)의 효과를 당연하게 보면 안 된다.
7. **Jev-as-Policy의 "Astra+Jev RoboTwin 결과"가 공개되면** "Astra + Jev 로봇" 평가의 첫 공개 사례를 뺏긴다. 저장소 신뢰도는 낮지만 속도 경쟁이다.
8. **Jev의 로봇 기여 자체가 불분명하다.**
   - jev-drone 저자: "더 단순한 경기장의 3-seed 비교에서는 Jev의 이점이 없었다."
   - jevduck: "Jev가 결정론적 감독기보다 낫다는 통제 비교는 아직 없다."
   - → "룰베이스(스킬 다발만)" 기준 방법이 핵심이다.

---

## 5. plan.md에 반영할 제안

**[사용자] (변경 없음, 재확인)**
- Jev는 텍스트만 받는다. 카메라 → 텍스트 변환 방법은 사용자가 정한다.
- Astra 호출 방식은 비교 실험으로 정한다.

**[제안]**
1. §1 Jev
   - 창업자 이름을 "Diogo Almeida"로 고친다.
   - 대기자 명단 폐지를 "2026-09-20 21:30 UTC"로 확정한다.
   - 속도 제한 "1,200 요청/분, 250k 토큰/초(변동 가능)"를 추가한다.
   - "요청당 최대 질문 수: 개수 제한 없음, 64k/32k 토큰 한도"로 바꾼다.
   - "영어가 가장 정확하다"를 추가한다.
   - "confidence는 확률에서 계산한 값"임을 적는다.
2. §1 jaggedness 항목에 **#8 "질문 사이 확률 항등식 불성립"**과 **#2(c) "Score 기댓값으로 크기 보간 금지"**를 추가하고, M3와 M4 설계 제약으로 연결한다. CLAUDE.md의 모델 제약 절에도 반영할지는 메인 세션이 판단한다.
3. §1 Astra
   - effort 목록을 `low/medium/high/xhigh/max`(none 없음)로 고친다.
   - **"logprob를 쓸 수 없다"**를 추가한다.
   - 요청당 이미지 1,500장, 패치 토큰 계산, 기본값 `auto`가 `original`과 같다는 점을 추가한다.
   - Fast mode는 "2배 가격, Astra 속도 배수 미공개, SLA 없음"으로 고친다.
   - TTFT는 "2026-09-24 기준 low 3.0 / medium 5.9 / high 73 / xhigh 198 / max 352초, 날마다 변동"으로 고친다.
4. §3 기준 방법
   - "Astra를 쓴 출판 논문은 아직 없다"를 **"미심사 arXiv로 AGP(2609.12541), GPT-Policy(2609.19138), TGL(2608.17209), RoboDojo(2609.24170)가 있고, Harness VLA(2607.08448)도 Astra판을 쓴다"**로 고친다.
   - LLM+스킬(Astra) 기준 방법 후보로 **Harness VLA/RPent**(962★, 인용 23)와 **TGL**을 검토한다.
   - "logprob 선택기"는 GPT-6 Sol/Luna(`effort=none`)나 TypeSafe system-one-adapter로 바꾼다.
5. §4 컨트리뷰션
   - C-M4는 유지한다(선점 없음 확인).
   - C-M8은 **"로봇이 멈추지 않는 조건에서 호출 시점 × effort"**로 좁히고, AGP·REFLEX·GPT-as-Policy를 관련 연구로 명시한다.
   - C-M6은 Jev_SO101 같은 공개 데모와의 차별점(체계적 결정 지점 개방 + 정량 평가)을 적는다.
6. M3 절제 실험 변수에 **보기 이름 형식(의미 있는 이름 / 중립 / 무작위 문자열)**을 추가한다.
7. 첫 실험(보정 측정)에 **질문 유형(Choice와 Noul)별로 따로 보정을 재는 것**과 **한국에서 호출할 때의 지연 분포(p50/p95)**를 포함한다.
8. [결정 필요] M1 후보에 "이미지 입력 Jev식 모델(Visual Jev, LOW)"을 참고용으로 둘지는 사용자가 정한다.

**감시 목록** (주기적으로 확인)
- YuanKJing/Jev-as-Policy의 Astra+Jev 결과 공개 여부
- arXiv 검색어 `Jev`의 로봇 논문
- awesome-jev 목록 갱신
- TypeSafe 보정 곡선이나 RLCD 논문 공개

---

## 6. 확인 못 한 것

- TypeSafe FAQ 답(정적 HTML에 없음). 비전 입력 공식 로드맵.
- Jev의 한국발 실제 지연, 보정 곡선(직접 호출 안 함).
- Astra Fast mode의 실제 속도 배수.
- GPT-as-Policy가 Astra를 호출하는 스케줄(시뮬을 멈추는지 여부). README만 읽었고 보고서 본문은 읽지 않았다.
- TGL v1(2026-08-17)이 Astra 공개(9/03)보다 앞선다. Astra 내용은 이후 판본(검색 목록상 9/19 갱신)에 들어간 것으로 보이지만 판본별 차이는 확인하지 않았다.
- Jev_SO101, quackd, awesome-jev의 스타 수 일부(GitHub API 한도).
- 인용 수: 2609.19138, 2608.17209(Semantic Scholar 429).
- 2608.28075(event-triggered FM planning): 이 주제 범위 밖이라 읽지 않았다.

## 참고 URL (주요)
- https://docs.typesafe.ai/llms.txt , https://docs.typesafe.ai/model-jaggedness/jev-1.13 , https://docs.typesafe.ai/api , https://docs.typesafe.ai/models , https://docs.typesafe.ai/confidence
- https://typesafe.ai/blog/introducing-system-one-models-and-jev , https://x.com/typesafeai/status/2101786156572823624
- https://openrouter.ai/typesafe/jev-1.13 , https://openrouter.ai/docs/guides/community/jev
- https://developers.openai.com/api/docs/models/gpt-6-astra , https://developers.openai.com/api/docs/guides/images-vision , https://developers.openai.com/api/docs/guides/latest-model , https://developers.openai.com/api/docs/guides/fast-mode , https://developers.openai.com/api/docs/guides/reasoning
- https://artificialanalysis.ai/models/gpt-6-astra/providers
- https://github.com/YuanKJing/Jev-as-Policy , https://github.com/Dimweaker/jev-libero , https://github.com/zjwzcx/Awesome-Astra-Embodied-AI , https://github.com/Frank-ZY-Dou/awesome-jev , https://github.com/anonymous-report-421/GPT-as-Policy , https://github.com/RLinf/RPent , https://github.com/typesafe-ai/system-one-adapter-python
- https://arxiv.org/abs/2609.12541 , https://arxiv.org/abs/2609.19138 , https://arxiv.org/abs/2608.17209 , https://arxiv.org/abs/2609.24170 , https://arxiv.org/abs/2607.08448 , https://arxiv.org/abs/2609.26758 , https://arxiv.org/abs/2609.26532 , https://arxiv.org/abs/2609.23886 , https://arxiv.org/abs/2609.25845
