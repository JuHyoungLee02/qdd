# 00. 기반 모델 검증: Jev(TypeSafe AI)와 GPT-6 Astra(OpenAI)

작성일: 2026-09-23 · 대상: `docs/plan.md` (v1)의 두 모델 관련 전제
조사 방법과 한계
- WebSearch 요약(snippet)만으로 교차 확인했다. typesafe.ai, docs.typesafe.ai, openrouter.ai, en.wikipedia.org, openai.robocurve.org 직접 접근은 모두 프록시에 막혔다(시도 1회씩).
- WebSearch는 이 모듈에서 약 33회 사용했고, 세션 전체 한도(200회)가 소진되어 더 검색하지 못했다. 목표(40회 이상)에 못 미친다. 아래 "5) 확인 못 한 것"에 남은 검증 항목을 모았다.
- 출처 신뢰도 표기: **공식**(OpenAI/TypeSafe 문서·블로그·공식 X), **주요 언론/전문 분석**(VentureBeat, Tom's Hardware, CNBC, Al Jazeera, Forbes, Artificial Analysis, Simon Willison), **제3자 평가**(Robocurve, RoboDojo 팀), **낮음**(SEO성 해설 사이트, 이름 없는 GitHub 저장소). 낮음 출처는 "보조 정황"으로만 적고 결론 근거로 쓰지 않았다.

---

## 1) 검증 표

### 1-A. Jev (TypeSafe AI)

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| 개발사 TypeSafe AI, "System One model" | CONFIRMED-MULTI | 공식 블로그 제목이 "Introducing System One Models & Jev". Simon Willison은 "decision models"라는 이름이 낫다고 평함 | https://typesafe.ai/blog/introducing-system-one-models-and-jev , https://simonwillison.net/2026/Sep/21/jev/ , https://www.tomshardware.com/tech-industry/artificial-intelligence/typesafe-ais-jev-offers-an-alternative-to-llms-that-claims-to-be-193x-faster-and-445x-cheaper-system-one-type-model-is-bespoke-for-probabilistic-decision-making |
| 창업자: Diego Almeida (전 OpenAI, ChatGPT/RLHF 공동 개발자로 소개됨) | SINGLE-SOURCE | 검색 요약 1건(MindStudio/Beam 계열)에서만 확인. 인용 전 재확인 필요 | https://www.mindstudio.ai/blog/jev-system-one-model-launch |
| 출시일 2026-09-15 (얼리 액세스) | CONFIRMED-MULTI | 모델 버전은 **Jev 1.13** (`typesafe/jev-1.13`, 별칭 `jev-latest`) | https://openrouter.ai/blog/insights/what-is-jev/ , https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/ , https://agentconn.com/blog/jev-typesafe-new-agent-layer-if-calibration-holds/ |
| plan.md 5절 "Jev는 제한된 얼리 액세스" | **WRONG (이미 바뀜)** | 대기자 명단이 **폐지**됐다. TypeSafe 공식 X: "Jev is now available to everyone. No waitlist." 날짜는 9/20(cryptobriefing)과 9/21(jevmodel.org, 낮음) 두 가지로 보도됨. console.typesafe.ai에서 키 발급 후 `POST https://api.typesafe.ai/v1/systemone`. 신규 가입에 $5 무료 크레딧(요약 기준) | https://x.com/typesafeai/status/2101786156572823624 , https://cryptobriefing.com/typesafe-jev-ai-public-access/ , https://www.explainx.ai/blog/jev-general-availability-no-waitlist-2026 |
| OpenRouter 제공 | CONFIRMED-MULTI | 2026-09-18 추가. 일반 chat 엔드포인트가 아니라 **alpha 단계의 Decisions 엔드포인트** `POST https://openrouter.ai/api/alpha/decisions`. 그 밖에 Cloudflare AI, Pydantic AI, LiteLLM, Langfuse 연동 문서 존재 | https://openrouter.ai/docs/guides/community/jev , https://openrouter.ai/typesafe/jev-1.13 , https://developers.cloudflare.com/ai/models/typesafe/jev/ , https://pydantic.dev/docs/ai/models/typesafe/ |
| 입력은 텍스트만 | CONFIRMED-MULTI | state는 문자열, JSON 객체, 배열을 받음. 모델 페이지 문구: "No image, audio, or video input." 멀티모달은 별도 비전/오디오 앞단 필요 | https://docs.typesafe.ai/models , https://www.llmreference.com/model/jev , https://www.langchain.com/blog/building-a-harness-with-jev |
| 비전 로드맵 | UNCONFIRMED | 공식 로드맵 언급을 찾지 못함. 제3자 GitHub 이슈 "if Jev gains image input"만 있음(희망 사항일 뿐) | https://github.com/buildinternet/uploads/issues/1010 |
| 컨텍스트 길이 | CONFIRMED-MULTI | **요청 전체 64k 토큰, state + 가장 긴 질문 하나 32k 토큰**. llmreference의 "66k"는 65,536을 반올림한 표기로 보임 | https://docs.typesafe.ai/models , https://systemonemodels.org/models/jev/ , https://www.firecrawl.dev/blog/what-is-jev |
| 출력 타입 이름: Choice / Score / Noul | CONFIRMED-MULTI | **Choice**: 보기별 확률 + 전체 confidence, 보기 **최대 255개**. **Score**: 순서 있는 수준 **2~10개**, 연속 점수 + 분포 + confidence. **Noul**: 예/아니오, 참일 확률만 주고 **confidence 필드 없음** | https://www.datacamp.com/blog/system-one-models-jev , https://www.refix.ai/news/jev-choice-score-noul/ , https://flaviocopes.com/jev/ |
| 한 호출에 여러 질문 병렬 응답 (plan M3) | CONFIRMED-MULTI | 같은 state에 여러 질문을 한 요청으로 보내면 한 번의 병렬 패스로 평가되고, 질문을 늘려도 응답 시간이 거의 늘지 않는다고 공식·Simon Willison 모두 설명. 단 **요청당 최대 질문 수는 확인 못 함** | https://simonwillison.net/2026/Sep/21/jev/ , https://www.datacamp.com/blog/system-one-models-jev |
| 확률이 보정(calibrated)되어 있음 | SINGLE-SOURCE(업체 주장) / 독립 검증 부족 | 사후 학습 방법 **RLCD (Reinforcement Learning for Calibrated Decisions)**: 확률이 실제 정답 빈도와 맞도록 보상. 그러나 **2026-09-19 기준 논문, 학습 세부, 보정 곡선이 공개되지 않음**(Forbes도 "과장 너머를 보라"고 논평). 제3자 ECE 측정은 개인 블로그 수준: MMLU 1,200문항 ECE 0.031, 합성 고객지원 티켓 ECE 0.107 (둘 다 SINGLE-SOURCE, 신뢰도 낮음~중간) → **우리 작업 데이터로 직접 보정을 재야 한다** | https://agentconn.com/blog/jev-typesafe-new-agent-layer-if-calibration-holds/ , https://www.forbes.com/sites/lanceeliot/2026/09/18/new-reinforcement-learning-for-calibrated-decisions-makes-ai-headlines-but-look-past-the-hype/ , https://www.dsebastien.net/reinforcement-learning-for-calibrated-decisions-rlcd/ |
| 지연 시간 70~500ms | CONFIRMED-MULTI (업체 수치) | 업체가 밝힌 end-to-end 범위. 여러 매체가 같은 숫자를 반복할 뿐 독립 분포(p50/p95) 측정은 찾지 못함. LiteLLM 블로그: 분류기 용도에서 Haiku 대비 5.43배 빠름. 실제 제어 루프 경험치: **2~10 Hz**, "제공자까지의 네트워크가 하한"(jev-realtime-sdk, 낮음) | https://www.tomshardware.com/tech-industry/artificial-intelligence/typesafe-ais-jev-offers-an-alternative-to-llms-that-claims-to-be-193x-faster-and-445x-cheaper-system-one-type-model-is-bespoke-for-probabilistic-decision-making , https://docs.litellm.ai/blog/jev-auto-router-benchmark , https://github.com/chy4pro/jev-realtime-sdk |
| 속도·비용 배수 ("40~200배") | CONFIRMED이나 **수치가 출처마다 다름** | 대표 수치는 **193.6배 빠름, 444.6배 저렴**(4개 워크플로 사내 평가의 최고치). 다른 곳에서는 "작업당 20~200배 빠름, 40~400배 저렴", "최대 100배"로도 소개됨. 모두 업체 수치 | https://www.tomshardware.com/tech-industry/artificial-intelligence/typesafe-ais-jev-offers-an-alternative-to-llms-that-claims-to-be-193x-faster-and-445x-cheaper-system-one-type-model-is-bespoke-for-probabilistic-decision-making , https://www.mindstudio.ai/blog/jev-computer-use-minecraft-robotics-demos , https://northdenvertribune.com/news-2/typesafe-jev-system-one-model-claims-evals-independent-tests/ |
| 가격 | CONFIRMED-MULTI | 입력 **$0.042 / 1M 토큰**, 출력 무료 | https://simonwillison.net/2026/Sep/21/jev/ , https://www.mindstudio.ai/blog/jev-system-one-model-launch |
| 4개 워크플로 벤치마크 67.8% | CONFIRMED-MULTI, **해석 정정 필요** | 워크플로: 보안 사고 대응, 에이전트 추적 관찰, 송장 처리, 고객 지원. Jev 67.8% ≈ GPT-5.6 Terra 67.9%, GPT-5.6 Sol 74.1%, Opus 5 73.1%보다 낮음. **정답 기준이 GPT-6 Astra와 Fable의 평균 예측**이다. 즉 "정확도"가 아니라 "프런티어 모델과의 일치도"다. 케이스당 비용 약 $0.0004 vs $0.03~0.18, 0.4초 vs 10~38초 | https://www.datacamp.com/blog/system-one-models-jev , https://benchlm.ai/blog/posts/what-is-jev , https://northdenvertribune.com/news-2/typesafe-jev-system-one-model-claims-evals-independent-tests/ |
| 약점: 프롬프트 인젝션 (VentureBeat) | CONFIRMED-MULTI | 공식 한계 문서: "adversarially steer ... can move the answer". VentureBeat 기사 존재. Pydantic 문서: Jev 기반 가드는 결정론적 검사와 **함께** 써야 함 | https://venturebeat.com/security/companies-are-putting-jev-in-charge-of-ai-agent-decisions-and-prompt-injection-can-influence-the-verdict , https://pydantic.dev/docs/ai/models/typesafe/ |
| 약점: 수치·공간 처리 (공식 "jaggedness" 페이지) | CONFIRMED-MULTI, **plan에 없던 핵심 제약** | Jev 1.13 jaggedness 페이지(9/16 또는 9/17 검토, 실패 유형 9개): 수치 정밀도 약함, **세기·수치 표현·Score로 하는 산술 모두 약함**, 날짜를 순서 있는 양이 아닌 텍스트로 읽음, RGB/hex 값이 서로 가까운지 판단 못 함, 간접 참조 단계가 많으면 약함, 질문을 글자 그대로 읽음(부정·범위어), **관련 없는 내용이 state에 늘면 정확도 하락**. 권장: 산술·기하·시간 비교는 코드에서 하고 임계값을 명시. Simon Willison도 "숫자, 날짜, 적대적 내용에 약함" | https://docs.typesafe.ai/model-jaggedness/jev-1.13 , https://simonwillison.net/2026/Sep/21/jev/ , https://wavect.io/blog/jev-ai-decision-model-review/ |
| 로보틱스 사례: jev-drone 500/50/15/2.5 Hz | CONFIRMED-MULTI | MuJoCo, Skydio X2(Menagerie). **500 Hz 기하 제어기 / 50 Hz 유도·안전 반사(항상 안전 권한) / 15 Hz 깊이·분할 → 기호 장면 / Jev 약 2.5 Hz, 조언(advisory)만**. 인식은 고전 CV(전방 5개 거리 구간, 장애물 높이, 윗모서리 보임 여부, 목표 위치). 상승 제안은 측정된 윗모서리가 상승 한계 안일 때만 허용. **주의: 저장소 이슈 #1 "README의 no-Jev 기준선이 HEAD에서 장벽을 통과한다"** → Jev 없이도 된다는 뜻일 수 있어 Jev의 기여가 불분명 | https://github.com/RomanSlack/jev-drone , https://jev-drone.vercel.app/ , https://github.com/RomanSlack/jev-drone/issues/1 |
| 로보틱스 사례: 로봇 팔 | SINGLE-SOURCE~MULTI (데모 수준) | MuJoCo 팔이 빨간 큐브를 맞는 구멍/상자에 넣음. 하네스가 **실시간 기하, 접촉, 제어의 예측 효과, 직전 행동 결과**를 텍스트/JSON으로 줌. "하네스가 많은 일을 했다"는 평. openroboto jev-robot-control: 사과→접시, Jev API 비용은 GPT-6의 약 1/315, 벽시계 시간 약 26%, GPT-6이 제어 주기 7회 적게 씀. 모두 논문 아님 | https://www.mindstudio.ai/blog/jev-computer-use-minecraft-robotics-demos , https://github.com/openroboto-ai/jev-robot-control |
| TypeSafe가 말하는 의도된 용도 | CONFIRMED-MULTI | "게임, 로봇, 시뮬레이션 같은 실시간 루프 안", 라우팅·점수·도구 검증·가드레일. 공식적으로 로봇을 대상으로 언급하지만 로봇 전용 API나 벤치마크는 없음 | https://www.mindstudio.ai/blog/jev-system-one-model-launch , https://beam.ai/agentic-insights/jev-typesafe-ai-agents |

### 1-B. GPT-6 Astra (OpenAI)

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| 공식 이름 GPT-6 Astra, API ID `gpt-6-astra` | CONFIRMED-MULTI | | https://openai.com/index/gpt-6-astra/ , https://developers.openai.com/api/docs/models/gpt-6-astra |
| 출시일 | CONFIRMED-MULTI | **2026-09-03** 승인 조직 대상 출시, 9/04 일반 제공(Wikipedia). ChatGPT 유료 플랜, OpenAI API, Azure, AWS Bedrock. 사이버 민감 기능은 trusted-access 프로그램으로 제한. 형제 모델 Sol, Luna가 9/22 나왔다는 글은 SINGLE-SOURCE(evolink, 낮음) | https://www.cnbc.com/2026/09/03/open-ai-astra-gpt-6-cyber.html , https://en.wikipedia.org/wiki/GPT-6_Astra , https://www.aljazeera.com/economy/2026/9/4/openai-unveils-gpt-6-astra-amid-rising-scrutiny-and-safety |
| 입력: 텍스트 + 이미지, 출력: 텍스트 | CONFIRMED-MULTI | **비디오 입력은 지원된다는 근거 없음** → plan M8의 "연속 프레임"은 여러 이미지 또는 격자 한 장으로 넣어야 함 | https://developers.openai.com/api/docs/models/gpt-6-astra , https://openrouter.ai/openai/gpt-6-astra |
| 요청당 이미지 수 한도 | UNCONFIRMED | 찾지 못함 | — |
| 컨텍스트, 최대 출력 | CONFIRMED-MULTI | 1,050,000 토큰, 최대 출력 128k | https://openrouter.ai/openai/gpt-6-astra , https://apidog.com/blog/gpt-6-astra-api/ |
| 가격 | CONFIRMED-MULTI | $10 입력 / $50 출력 (1M 토큰). 입력 272k 초과 요청은 전체 $20/$75. 캐시 입력 90% 할인. Batch/Flex 반값. **Fast mode: 가격 2배, 속도 최대 2배** | https://www.yottalabs.ai/post/gpt-6-astra-pricing-api-cost-2026 , https://www.layer3labs.io/guides/gpt-6-astra-api-pricing |
| "Astra는 느리다" (CLAUDE.md 제약) | CONFIRMED-MULTI, **추론 강도에 따라 100배 차이** | Artificial Analysis 첫 답변 토큰까지 시간: **low 2.79초, high 45.16초, max 250.18초**. 운영 p95 TTFT 9.43초(최근 7일, 요약 기준). 복구 호출처럼 로봇을 멈추지 않아야 하는 곳은 effort 선택이 곧 설계 변수 | https://artificialanalysis.ai/models/gpt-6-astra-low/providers , https://artificialanalysis.ai/models/gpt-6-astra-high/providers , https://artificialanalysis.ai/models/gpt-6-astra/providers |
| 로봇 제어 95% | CONFIRMED-MULTI, **출처 정정** | OpenAI 발표가 아니라 제3자 **Robocurve** 평가(X에서 Jay Chooi가 소개). 실제 I2RT YAM 팔 2대, 카메라 3개(위, 양 손목) + 고유감각 상태 → 매 턴 **양팔 절대 엔드이펙터 자세(x,y,z,yaw,pitch,roll,gripper)** 출력, IK로 변환. 빨간 블록→그릇 **19/20**(Fable 5.1 8/20, Fable 5 1/20), 시도당 2.5분(Fable 5.1 6.8분), 약 $0.94/회 | https://x.com/chooi_jeq/status/2096064315115839904 , https://openai.robocurve.org/gpt-6-astra/ , https://ai-tldr.dev/releases/robocurve-astra-robot-arms/ , https://news.ycombinator.com/item?id=49582582 |
| 약점: 정밀 실행 | CONFIRMED-MULTI | 원형 퍼즐 조각 삽입 **2/20**(Fable 5.1과 동일). 홈까지 가서 마지막 단계에서 멈춤. $1.36/회. **→ "느린 상위가 정밀 실행을 하위에 넘긴다"는 우리 구조의 동기와 맞음** | https://nomanualbook.substack.com/p/gpt-6-astra-drove-a-robot-arm-the , https://www.kucoin.com/news/flash/openai-s-astra-demonstrates-strong-robot-control-capabilities |
| "zero-shot 휴머노이드" | **WRONG/혼동** | cryptobriefing이 "full humanoid"라고 썼지만, 95%는 **양팔(YAM) 로봇**이다. "시뮬레이션 휴머노이드를 카메라로 제어"는 RoboDojo 보고서 쪽 내용으로 보임. 실제 휴머노이드 결과로 인용하면 안 됨 | https://cryptobriefing.com/astra-agent-controls-humanoid-robot/ , https://arxiv.org/html/2609.24170 |
| 그림 그리는 팔 | SINGLE-SOURCE | 약 $150 SO-101 팔 + 붓 + 카메라로 금문교를 그리고, 카메라 피드백으로 반복 개선 | https://www.mindstudio.ai/blog/gpt6-astra-dangerous-capabilities-safety-fears |
| RoboDojo 평가 보고서 | CONFIRMED-MULTI(존재) | "An Unexpected Robot Policy: Early Evaluations of GPT-6 Astra on RoboDojo and Beyond", arXiv **2609.24170**, Wenbo Zhang 외 11명, 2026-09-16 공개(요약 기준). LLM-as-policy(사전학습 모터 정책 없음), 42개 시뮬 작업 **Score 28.97, 평균 SR 22.48%**, 비교한 공개 정책 40개보다 위. 88건반 피아노를 Shadow hand 2개로 45차원 관절 명령 0.05초 주기 제어기 코드를 작성. **절대 성공률은 낮음(22%)**. 미심사 | https://arxiv.org/abs/2609.24170 , https://github.com/zjwzcx/Awesome-Astra-Embodied-AI |
| 공식 로보틱스 API | UNCONFIRMED(없음으로 보임) | 공식 발표·시스템 카드 요약에서 로봇 API나 로봇 섹션을 찾지 못함. 로봇 결과는 모두 제3자 | https://deploymentsafety.openai.com/gpt-6-astra , https://openai.com/index/gpt-6-astra/ |
| 안전 보고서 "위험 행동 비율" | CONFIRMED-MULTI, **출처 정정** | OpenAI 시스템 카드가 아니라 Robocurve **RoboHarm**(9/18). 5개 시나리오 × 20회 = 100회. Astra: 97회 시도, 거부 2회, **완료 60회**(mixed-news; 다른 매체는 62%라고 써서 수치 불일치). 인형 찌르기 17/20, 보조배터리 물에 넣기 14/20. Fable 5.1은 20회 거부, 34회 완료. OpenAI 시스템 카드 자체는 사이버 "Critical" 등급 첫 모델이라는 점이 확인됨 | https://mixed-news.com/en/gpt-6-astra-roboharm-dangerous-robot-arm-tasks-refused-two/ , https://the-decoder.com/gpt-6-astra-and-claude-fable-turn-robot-arms-into-slapstick-killer-robots-in-new-safety-benchmark/ , https://hothardware.com/news/gpt-6-astra-stabbed-doll-17-times-when-given-control-of-robot-arm |

### 1-C. 선점(scoop) 위험: Astra + Jev, 느린 LLM + Jev 계층

| 항목 | 확인 수준 | 내용과 위험도 | 출처 URL |
|---|---|---|---|
| Minecraft: Astra 상위 계획 + Jev 실시간 행동 | SINGLE-SOURCE (데모 리뷰) | Astra가 계획, Jev가 전투·이동을 맡은 조합이 Jev 단독보다 확실히 나았다고 보도. 같은 글이 "Jev의 가까운 가치는 느린 모델 아래의 빠른 실행층"이라고 정리. **계층 발상 자체는 이미 공개 담론** | https://www.mindstudio.ai/blog/jev-computer-use-minecraft-robotics-demos |
| Jev-as-Policy (GitHub) | SINGLE-SOURCE, 신뢰도 **낮음** | 저장소 설명: "Evaluations of **Astra + JEV on benchmarks such as RoboTwin** will also be released soon." 같은 설명의 저장소가 YuanKJing, cosmic-snail 두 곳(포크/복제 추정). 스타 수·저자 확인 못 함. **직접 선점 위험 신호: 높음** (내용 미공개) | https://github.com/YuanKJing/Jev-as-Policy , https://github.com/cosmic-snail/Jev-as-Policy |
| jev-libero / jev-libero-api | SINGLE-SOURCE, 낮음 | "Fine-grained robot control with Jev, physics previews, and configurable LIBERO tasks." **"Jev로 촘촘한 로봇 제어" 자체도 이미 시도됨** | https://github.com/Dimweaker/jev-libero , https://github.com/jiangmingxuan234-alt/jev-libero-api |
| jev-realtime-sdk | SINGLE-SOURCE, 낮음 | 코드가 가진 내부 tick + Jev 결정 tick(2~10 Hz), 유지 행동, 기호 상태, 안전 필터 후보, dead-man 정책. 7개 Jev 제어 프로젝트(드론 2, 로봇 팔 2, 게임 등)에서 정리 | https://github.com/chy4pro/jev-realtime-sdk |
| Astra 로보틱스 논문 목록 | 존재 확인 | Awesome-Astra-Embodied-AI 목록이 생김. 제목만 확인: "Agent as Policy for Robotic Manipulation"(arXiv 2609.12541), "In-Context Robot Learning with VLM Agents"(arXiv 2609.19138), "Teach and Grow"(arXiv 2608.17209). **내용·저자 미확인**(검색 한도 소진) | https://github.com/zjwzcx/Awesome-Astra-Embodied-AI , https://arxiv.org/pdf/2609.12541 , https://arxiv.org/pdf/2609.19138 |

결론: 검색 범위 안에서 **"Astra + Jev 계층을 로봇 조작에 적용한 심사 논문"은 찾지 못했다.** 그러나 (1) TypeSafe 주변 담론이 이미 "느린 모델 + Jev 빠른 층"을 권장하고, (2) Astra+Jev RoboTwin 평가를 예고한 저장소가 있고, (3) Jev로 LIBERO 세밀 제어를 한 저장소가 있다. plan 4절 컨트리뷰션 1("계층 구조와 공유 스키마")은 **발상만으로는 새롭지 않다**고 보는 것이 안전하다. 새로움은 방법(M4 겹침 검증, M8 호출 방식 비교)과 체계적 평가에서 나와야 한다.

---

## 2) 더 나은 대안 / 최신 SOTA

- **빠른 하위 결정층의 대안**
  - 같은 카테고리의 상용 경쟁 모델은 확인하지 못했다. 한 Hugging Face 데이터셋 이름(`Luni/laya-jev-benchmark`)에 "Laya"라는 비교 대상이 보이지만 정체는 미확인.
  - 오픈소스 "Jev 대안"(openJev-verdict-2.0, 151M ModernBERT, ECE 0.0144 주장)은 개인 저장소이고 검증이 없다. **LOW, 추천하지 않음.** https://github.com/Heman10x-NGU/openJev-verdict-2.0
  - 기준 방법으로는 "일반 LLM의 보기 토큰 logprob를 확률로 쓰는 방식"이 LLM 분야의 표준이다. Jev의 속도·보정 이점을 보이려면 이 기준선이 꼭 필요하다(openroboto 데모도 GPT-6과 비교했다).
- **느린 상위층의 대안**
  - Robocurve 실물 비교에서 Astra(19/20)가 Claude Fable 5.1(8/20)보다 크게 앞섰고, 정밀 삽입은 둘 다 2/20이었다. 현재 공개 증거로는 Astra가 가장 강한 선택이다.
  - 같은 Astra 안에서도 effort(low 2.8초 ~ max 250초)와 fast mode(2배 가격, 최대 2배 속도)가 사실상 "다른 모델"만큼 차이 난다. 모델 교체보다 **effort 선택을 실험 변수로 두는 것**이 더 중요하다.
- **보정(calibration) 검증 방법 (LLM/ML 분야에서 가져올 것)**
  - Jev 확률을 plan M3/M4처럼 "확률 가중 평균", "겹침 구간 확률 비교"에 쓰려면, 먼저 우리 작업 데이터에서 신뢰도 다이어그램과 ECE를 재야 한다. 표준 참고: Guo et al., "On Calibration of Modern Neural Networks", ICML 2017 (temperature scaling). 임계값은 conformal prediction으로 정하는 방법이 있다(plan M7의 SAFE와 같은 계열).
  - 이 두 참고는 이번 세션에서 검색으로 재확인하지 않았다. 잘 알려진 문헌이지만 인용 전 서지 확인 필요.

---

## 3) 반대 증거와 위험

1. **M1 "객체 중심 수치 JSON"이 Jev 공식 약점과 정면으로 부딪힌다.** jaggedness 페이지는 수치 정밀도, 산술, 수치 근접 판단이 약하다고 명시하고, 기하·산술 비교는 코드로 하라고 권한다. 3D 좌표나 상대 벡터를 숫자 그대로 주고 "얼마나 움직일지"를 고르게 하면 성능이 크게 떨어질 수 있다. 실제로 성공한 Jev 로봇 데모들(jev-drone, 로봇 팔)은 모두 **코드가 계산한 기호/부호 오차/정렬 여부/접촉 여부**를 줬다.
   - 정정 제안: 수치는 코드에서 술어와 범주(예: 방향 부호, 거리 구간, 정렬됨/안 됨)로 바꾸고, Jev에는 의미 수준 판단만 맡긴다. 단 CLAUDE.md 규칙상 "카메라→텍스트 변환 방법"은 사용자가 정한다. 이 내용은 결정 재료로만 전달한다.
2. **M3의 "촘촘한 크기 단계 + 확률 가중 평균"**: Score로 하는 산술이 약하다고 공식 문서에 적혀 있다. 보정도 업체 주장뿐이다(논문·곡선 미공개). 확률 가중 평균을 쓰기 전에 보정 측정이 먼저다.
3. **state가 커지면 정확도가 떨어진다.** M4에서 "확정된 앞부분 + 보정값 + diff"를 계속 state에 덧붙이면 이 약점을 건드린다. 짧게 유지해야 한다.
4. **지연 시간**: 70~500ms는 업체 수치이고 네트워크를 포함한 독립 p95는 확인 못 했다. 실사용 보고는 2~10 Hz. M4의 "1초에 3번 계단식 호출"은 범위 안이지만, 500ms 꼬리 지연이면 겹침 설계가 필수다. OpenRouter는 alpha 엔드포인트라 직접 API가 더 안정적일 가능성이 있다(미확인).
5. **67.8%는 정확도가 아니라 Astra/Fable과의 일치도다.** "Jev가 Astra에 비해 얼마나 똑똑한가"의 근거로 쓰면 안 된다.
6. **jev-drone에서 Jev의 기여가 불분명**: no-Jev 기준선이 장벽을 통과한다는 이슈가 있다. 우리 평가의 "Jev 없는 규칙 기반(스킬 다발만)" 기준선이 중요하다는 방증이다.
7. **Astra 로봇 성과는 모두 제3자, 소규모, 미심사.** 95%는 1개 작업 20회. RoboDojo 평균 SR은 22.48%로 낮다. "LLM 기반은 일반화된다"는 핵심 메시지의 근거로 쓰기에는 아직 약하다.
8. **Astra의 안전 문제**(RoboHarm 97/100 시도): 사용자가 "안전은 크게 다루지 않는다"고 했지만, 실물 로봇 실험 시 최소한의 하드웨어 보호(jev-drone처럼 저수준 반사가 항상 우선)는 필요하다. 이는 사실 정리일 뿐 계획 변경 제안은 아니다.
9. **선점 위험**: 1-C 참고. 특히 Jev-as-Policy(Astra + JEV, RoboTwin 예고)는 결과가 나오면 plan의 평가 계획 6번("Astra를 쓰는 기존 논문")과 컨트리뷰션 1에 직접 영향을 준다. 주기적 모니터링이 필요하다.

---

## 4) 이 모듈에 장착할 후보 순위 (모델·설정 선택)

| 순위 | 후보 | 근거 | 신뢰도 근거 |
|---|---|---|---|
| 1 | **하위: Jev 1.13, TypeSafe 직접 API (`api.typesafe.ai/v1/systemone`)** | 대기자 명단 없음, 입력 전용 과금 $0.042/1M, 병렬 다중 질문, Choice 255개·Score 2~10단계. OpenRouter는 alpha라 보조 경로로만 | 공식 X·문서 + 다수 언론(Tom's Hardware, VentureBeat, MarkTechPost). 보정·지연은 업체 수치라 자체 측정 필요 |
| 2 | **상위: GPT-6 Astra, effort를 호출 목적별로 분리** (최초 계획은 high 허용, 실패 복구·주기 호출은 low 또는 fast mode) | TTFT low 2.8초 vs high 45초 vs max 250초. plan M8 "호출 방식 비교"에 effort를 축으로 추가할 가치 | Artificial Analysis(독립 측정, 높음), 공식 가격 문서 |
| 3 | **기준선: 일반 LLM logprob 기반 선택기**(같은 질문을 Astra low 또는 저가 모델에 보기 토큰 확률로) | Jev의 속도·보정 이점을 공정하게 보이기 위한 필수 비교. openroboto 데모가 이미 GPT-6 vs Jev 비용·시간 비교를 함(1/315, 26%) | 방법 자체는 LLM 분야 표준. openroboto 데모는 낮음(참고만) |
| 4 | **보정 측정·재보정 층**: 우리 작업 데이터로 ECE/신뢰도 다이어그램 → 필요하면 temperature scaling 또는 conformal 임계값 | RLCD 논문·곡선 미공개. M3/M4/M7이 모두 확률을 쓰므로 선행 조건 | Guo et al. ICML 2017 등(높음, 이번 세션 서지 미재확인) |
| 제외 | openJev-verdict, 각종 SEO 해설 사이트, 이름 없는 Jev 데모 저장소 | 심사·평판·검증 없음 | LOW |

---

## 5) 확인 못 한 것

- Jev: 요청당 최대 질문 수, 요청 속도 제한(rate limit), 지연 p50/p95의 독립 측정, 비전 로드맵, 대기자 폐지 정확한 날짜(9/20 vs 9/21), jaggedness 페이지 검토 날짜(9/16 vs 9/17)와 9개 실패 유형 전체 원문, 창업자 이력(SINGLE-SOURCE).
- Jev의 보정: 공식 보정 곡선, 독립적이고 신뢰도 높은 ECE 측정.
- Astra: 요청당 이미지 수 한도, 이미지 해상도·토큰 환산, 비디오 입력 계획, 시스템 카드의 로보틱스 관련 절 유무, Sol/Luna(9/22)의 실제 존재와 사양.
- Robocurve/RoboDojo: 원문 확인(프록시 차단). RoboHarm 완료 수 60 vs 62 불일치.
- 선점 후보 논문 3편(2609.12541, 2609.19138, 2608.17209)의 저자·내용, Jev-as-Policy의 실제 공개 결과와 스타 수.
- 검색 한도(세션 200회) 소진으로 위 항목을 추가 검증하지 못했다.
