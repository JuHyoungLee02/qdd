# 09. 저자 본인의 목소리: 블로그·발표·게시물·저장소 README 확인

작성: 2026-09-24, v3 초안 조사 보강. 사용자 요구 "저자의 블로그, 발표, 게시물까지 찾아본다", "정말 최고 성능인지 확인한다"에 대한 보고서.

## 1. 조사 방법과 한계

- WebSearch 9회(한도 15). arXiv 검색 API, Semantic Scholar API, GitHub API는 쓰지 않았다(지시). GitHub는 README 원문(raw.githubusercontent)과 저장소 HTML 페이지(스타 수, 커밋 날짜)만 읽었다.
- 원문을 직접 읽은 것: 논문 본문 16편(RTC, Training-time RTC, π0.7, CaP-X, ACE, Evo-Memory, AGP, RoboDojo 평가, Show-Harness, Zetta, Harness VLA, FLARE PDF / 초록만: FutureRTC, 2606.15017, AgentSpec, Guava), 공식 블로그·문서 7건(PI RTC 페이지, TypeSafe 출시 블로그, TypeSafe 문서 models·coding-agents·primer·confidence, HF async 블로그), 저자 인터뷰 1건(Latent Space, Diogo Almeida), 저장소 README 10개.
- **X(트위터)는 읽지 못했다.** x.com은 402, 미러(xcancel)는 서비스 중단. 그래서 X 스레드 원문은 확인하지 못했다. X 내용은 awesome-jev 목록(제3자 정리, 2026-09-19 기준)처럼 2차 정리를 거친 것만 적었고, 그렇게 표시했다.
- WebFetch 요약은 작은 모델이 만든 것이므로 핵심 수치와 인용은 curl로 원문을 받아 문장을 직접 찾아 확인했다(아래 표의 ORIGINAL-CONFIRMED). WebFetch 요약에만 기댄 것은 SINGLE-SOURCE로 적었다.

## 2. 검증 표

| # | 항목 (저자 발언) | 확인 수준 | 정정/비고 (신뢰도 근거) | 출처 URL |
|---|---|---|---|---|
| 1 | RTC 저자 스스로 밝힌 한계: "추가 계산 부담이 크다", "diffusion·flow 정책에만 쓸 수 있다", 실물 실험에 다리 이동(locomotion) 같은 더 동적인 경우는 없다 | ORIGINAL-CONFIRMED | 논문 6절. NeurIPS 2025 체크리스트 포함(HIGH, PI + Berkeley). 2025-06-09 | https://arxiv.org/html/2506.07339 |
| 2 | RTC 구조: 이미 실행이 정해진 앞부분 d(추론 지연)는 고정, 중간 구간은 **지수적으로 줄어드는 가중치로 이전 청크를 참고**, 끝부분은 새로 생성. 앞부분만 고정하는 방식(hard masking)은 "이전 청크를 잘 따르지 못하고 방향이 더 빨리 바뀐다", soft masking이 "청크 사이 연속성에 결정적" | ORIGINAL-CONFIRMED | 3.2절, 그림 4 | https://arxiv.org/html/2506.07339 |
| 3 | PI 블로그 갱신(2025-12-08): 학습 시점 RTC 후속 논문을 π\*0.6 에스프레소 데모에 썼다 | SINGLE-SOURCE (공식 블로그, WebFetch) | 공식 페이지라 신뢰도 높음 | https://www.pi.website/research/real_time_chunking |
| 4 | Training-time RTC(2512.05964) 저자 한계: "추론 시점 RTC보다 근본적으로 덜 유연하다. 추론 지연에 해당하는 딱딱한(hard) 앞부분만 조건으로 걸 수 있고, 추론 시점 RTC는 그 뒤 행동까지 부드럽게(softly) 반영한다", "학습 때 흉내 낼 지연 분포를 예상 지연에 맞춰 신중히 골라야 한다". 원격 H100에서 평균 종단 지연 108ms(학습형) 대 135ms(추론형), 실물 성능은 동등 | ORIGINAL-CONFIRMED | 6절. PI(Black, Ren, Equi, Levine). 미심사, MED-HIGH(PI) | https://arxiv.org/html/2512.05964v1 |
| 5 | **PI의 현재 선택**: π0.7(2026-04)이 학습 시점 RTC를 쓴다. 학습 때 0~12 스텝 지연 모사, 50Hz에서 최대 240ms | ORIGINAL-CONFIRMED | π0.7 논문 VI-B절 | https://arxiv.org/html/2604.15483v1 |
| 6 | Training-time RTC 논문이 SmolVLA 비동기 방식에 대해: "청크 사이 불연속 문제를 풀지 않아 분포 밖 '떨림(jerk)'이 생긴다" | ORIGINAL-CONFIRMED | 관련 연구 절 | https://arxiv.org/html/2512.05964v1 |
| 7 | HF 비동기 추론 블로그(2025-07-10) 한계: 관측 유사도 필터가 "환경의 동적 변화(물체 위치 변화, 외란)에 적응하지 않는다", "네트워크 왕복 시간이 추론 시간보다 무시할 만큼 작다고 가정", g≈0.7이 좋은 절충, 시작은 g=0.5 | SINGLE-SOURCE (공식 블로그, WebFetch 요약) | HF LeRobot 팀. 인용 문장은 WebFetch 요약에서 가져옴 | https://huggingface.co/blog/async-robot-inference |
| 8 | TypeSafe 출시 블로그(2026-09-15, Diogo Almeida): 보정 측정은 "가장 크고 비싼 외부 모델의 예측을 기준 확률로 쓴다". 데모는 "이미지가 아니라 텍스트 자료구조 상태로 (아직은)". 사람이 끼는 작업은 기존 LLM이 낫다 | SINGLE-SOURCE (공식, WebFetch) | 업체 발언. 보정의 기준이 **정답이 아니라 최상위 LLM 답**이라는 점이 핵심 | https://typesafe.ai/blog/introducing-system-one-models-and-jev |
| 9 | TypeSafe 공식 평가표의 기준 라벨: "GPT-6 Astra와 Claude Fable 5.1(둘 다 high thinking) 응답의 평균으로 만든다". Jev 67.8% 일치, 0.4초 / GPT-5.6 Sol 74.1%, 23.3초 / Opus 5 73.1%, 37.8초 | CONFIRMED-MULTI (awesome-jev가 evals.typesafe.ai를 인용, #8과 일치) | evals.typesafe.ai 원문은 직접 열지 못함. 업체 수치 | https://github.com/Frank-ZY-Dou/awesome-jev (14★) |
| 10 | TypeSafe 문서: 별칭(`jev-latest`)은 새 버전이 나오면 가리키는 모델이 바뀌어 "답이 내 쪽 변경 없이 바뀔 수 있다". 영어가 가장 정확, CJK는 덜 정확 | ORIGINAL-CONFIRMED | docs.typesafe.ai/models.md 원문 | https://docs.typesafe.ai/models.md |
| 11 | Diogo Almeida 인터뷰(Latent Space, 2026-09-21): "중첩 구조가 한 단계 깊어질 때마다 추론이 더 어려워진다", 새 모델을 매우 빨리 낼 계획, 1.13.0을 임시 LTS로 둘 수도, 버전 사이 품질 유지 보장 없음. 실시간은 주력이 아니라고 말함 | SINGLE-SOURCE (WebFetch 요약, 녹취 원문 대조 못 함) | 창업자 본인 발언. 인용은 요약 모델 출력 | https://www.latent.space/p/jev |
| 12 | Simon Willison(2026-09-21): 재순위화·도시 순위 실험. 도시 순위에서 편향 우려, 문서의 "숫자·날짜·적대적 내용에 약함" 재인용. 로봇 언급 없음, 지연 측정 없음 | SINGLE-SOURCE (WebFetch) | 영향력 큰 제3자 블로거 | https://simonwillison.net/2026/Sep/21/jev/ |
| 13 | Alex Molas "Jev can't be calibrated"(2026-09-23): 보정은 데이터 분포에 달려 있어 "TypeSafe 데이터에서 보정돼도 당신 데이터에서는 아닐 수 있다". 공정한 동전 앞면 확률을 0.92로 답함. "Noul이 같은 문제에서 Choice보다 훨씬 잘 보정된다"는 실험 인용. 권고: 라벨 수백 개로 Platt scaling | SINGLE-SOURCE (WebFetch) | 개인 블로그, LOW. 방향은 우리 계획(첫 실험 보정 측정)과 같음 | https://www.alexmolas.com/2026/09/23/jev-cant-be-calibrated.html |
| 14 | systemonemodels.org(비공식 1인 사이트): "하드 실시간 제어는 범위 밖이다. 매 주기 마감을 지켜야 하는 루프는 중앙값 지연이 얼마든 네트워크 요청에 의존할 수 없다" | SINGLE-SOURCE (awesome-jev 인용) | LOW. 다만 설계 원칙으로는 타당 | https://github.com/Frank-ZY-Dou/awesome-jev |
| 15 | 로보크런치 측정(2026-09-19): OpenRouter 경유 Jev p50 0.527초, p95 0.813초(300건, 요청 약 585토큰, 질문 3개). 보정 연구는 안 했다고 명시 | ORIGINAL-CONFIRMED (README) | 2★, LOW. 측정 위치 미기재. 공식 엔드포인트 아님 | https://github.com/robokrunch/jev-physical-ai |
| 16 | Show-Harness 공식 페이지: "사고 강도(thinking effort)는 주로 에피소드를 줄인다. GPT-5.6-sol에서 37 → 30 스텝, 벽시계 3.4배". "계획은 격차가 아니다"(지시 따르기 ≥98%, 하위 계획 ≥97%), 빈 잡기가 6% → 26%로 증가, "모델은 센티미터에서 놓친다" | ORIGINAL-CONFIRMED (프로젝트 페이지 원문) | **plan v3의 "사고량을 늘려도 성공률은 그대로이고 시간만 늘었다"는 부정확**: 스텝 수는 줄었고, 벽시계가 3.4배, 대상 모델은 Astra가 아니라 GPT-5.6-sol. 451★, NUS Show Lab, 미심사(MED) | https://showlab.github.io/Show-Harness/ |
| 17 | Show-Harness 논문 한계: 평행 집게의 한 팔·두 팔만 평가, 촉각·힘 감각 없음 | ORIGINAL-CONFIRMED | 6절 | https://arxiv.org/html/2609.10522 |
| 18 | Show-Harness가 기준 방법으로 CaP-X, H-VLA(=Harness VLA로 추정)를 이겼다고 주장(교차 작업 10개 89%/86% 대 최고 기준 57%) | SINGLE-SOURCE (공식 페이지) | 저자 주장. H-VLA가 Harness VLA인지 원문 대조 못 함 | https://showlab.github.io/Show-Harness/ |
| 19 | Zetta: 런타임 critic은 **코드**이고, LLM은 롤아웃 단위에서 critic·복구를 제안하며, 검증 게이트를 거쳐 채택("세 개의 시간 척도 분리 루프"). 작업마다 개발 시드 50개로 진화 후 분리된 시드로 평가. RPent 대비 추론 지연 91% 감소(11.1배). README 예시 모델은 `gpt-5.6-sol` | ORIGINAL-CONFIRMED | 1,252★, 미심사(MED). **작업별 적응(시드 50개)이 들어간 결과**라 영점(zero-shot) 일반화 비교와 다르다 | https://arxiv.org/html/2608.16590 , https://github.com/air-embodied-brain/Zetta-Embodiment |
| 20 | Harness VLA 저자 한계: "상위 계획기와 하위 VLA 사이 피드백 루프가 열려 있다", 보상 기반 공동 미세조정 없음, 세밀한 이미지 설명 부재가 혼잡한 장기 작업을 제약 | ORIGINAL-CONFIRMED | 5절. 962★, 칭화(MED) | https://arxiv.org/html/2607.08448 |
| 21 | RPent README: LIBERO-PRO 1위 구성이 "Codex / GPT-6 Astra / **low** / reasoning", 92.63%(741/800). 2026-08 "non-reasoning 모드로 평균 실행 시간 약 40% 감소" | ORIGINAL-CONFIRMED (README) | 저장소 발언. effort 대조표는 JS 리더보드라 읽지 못함 | https://github.com/RLinf/RPent |
| 22 | CaP-X 논문 Takeaway 3: "매 턴 원시 RGB를 끼워 넣으면(M2) 텍스트만 쓴 M1보다 **성능이 떨어진다**", 영상 → 구조화된 자연어로 바꾸는 Visual Differencing(M3)이 둘 다보다 낫다. Takeaway 2: 높은 추상화가 성공률을 올리지만 표현력을 제한 | ORIGINAL-CONFIRMED | ICML 2026(HIGH), 819★. 평가 모델에 Astra 없음(2026-03 제출) | https://arxiv.org/html/2603.22435 |
| 23 | CaP-X 프로젝트 페이지: 섭동된 작업에서 학습된 VLA는 "전부 0%" | SINGLE-SOURCE (WebFetch) | 핵심 주장(VLA 일반화 약함)의 근거. 다만 Harness VLA·Zetta는 같은 LIBERO-Pro에서 고정 VLA + 하네스로 90%대 | https://capgym.github.io/ |
| 24 | ReasoningBank 공식 블로그(Google Research, 2026-04-21): 라벨은 LLM-as-a-judge 자기 평가, "단순화를 위해 그냥 덧붙이고, 더 정교한 통합은 향후 과제", 로봇 언급 없음 | SINGLE-SOURCE (공식, WebFetch) | ICLR 2026(HIGH) | https://research.google/blog/reasoningbank-enabling-agents-to-learn-from-experience/ |
| 25 | ACE 저자 한계: "신뢰할 만한 피드백(정답 라벨, 실행 결과)이 없으면 ACE와 Dynamic Cheatsheet 모두 성능이 떨어질 수 있다", "맥락이 가짜 신호로 오염" | ORIGINAL-CONFIRMED | ICLR 2026(HIGH) | https://arxiv.org/html/2510.04618 |
| 26 | Evo-Memory 표 3: 성공·실패 경험을 걸러내지 않고 모두 저장하면 "기준 방법들이 눈에 띄게 나빠진다". Claude 3.7에서 ExpRAG ALFWorld 0.76이지만 ScienceWorld 0.27(ExpRecent 0.34보다 낮음), ReMem 0.92/0.69. 피드백 f는 "정답 여부 신호" | ORIGINAL-CONFIRMED | Google DeepMind + UIUC. 한계 절: 텍스트·목표 지향 작업 위주, 멀티모달·실세계는 향후 | https://arxiv.org/html/2511.20857 |
| 27 | AGP 표 2: Astra low 5/5, 9.9분 [6.0, 19.0] / medium 5/5, 9.2분 / high 5/5, 9.2분 [7.9, 10.6]. "추가 사고 강도의 이득이 제한적". 4.3절: 같은 작업 반복 시 경험 재사용으로 응답 지연이 1회차 대비 5회차에 47.0% 감소 | ORIGINAL-CONFIRMED | 2026-09-11, 미심사. high가 low보다 느리지 않고 시간 분산이 작다(사용자 발언 "옳은 추론이 더 빨리 성공"과 모순되지 않음) | https://arxiv.org/html/2609.12541 |
| 28 | RoboDojo 평가(2609.24170, 2026-09-21): Astra 42작업 평균 22.48%로 공개 정책 40개보다 위, 그러나 "심하게 불균형" — 의미 이해 작업은 강하고 정밀·동적·양팔 협응은 약함. 1회 시연(in-context) 추가는 "전체 이득 없음". 한계 절: 추론 지연과 행동 타이밍이 실패에 준 기여를 분리하지 못함. medium effort, 에피소드당 호출 100회 | ORIGINAL-CONFIRMED | 미심사(MED-LOW) | https://arxiv.org/html/2609.24170 |
| 29 | GPT-as-Policy(Galbot 등): π0.5가 후보 50개를 만들면 Astra가 "π0.5의 앞 1~15 스텝을 따를지, 끝점 교정 1~5개를 직접 낼지" 고른다. 하이브리드 48% 성공, Astra 직접 26%, 교정은 실행 스텝의 14.4%. 모델 고정 `gpt-6-astra` **xhigh** | ORIGINAL-CONFIRMED (README) + 검색 요약 | 526★(v3 기록), 미심사. 보고서 사이트는 JS라 실패 유형 원문을 읽지 못함 | https://github.com/anonymous-report-421/GPT-as-Policy |
| 30 | Robocurve(Jay Chooi 외, 2026-09-04): medium effort, 호출 예산 20. 그릇 19/20, 퍼즐 삽입 2/20(Fable 5.1도 2/20). 시행당 2.5~3.4분. 저자 주의: 시행 비교가 이틀 떨어짐, "모델을 아는 채로 운영자가 채점 → 무의식적 편향 가능", medium만 시험 | SINGLE-SOURCE (공식 페이지, WebFetch) | 제3자 연구 단체, LOW-MED | https://openai.robocurve.org/gpt-6-astra/ |
| 31 | Jev-as-Policy: README 마지막 줄 "Astra + JEV 평가 결과는 후속으로 공개한다". 마지막 커밋 2026-09-21 10:57(+08:00), 커밋 6개, 37★ (YuanKJing 원본, cosmic-snail은 포크 0★). **2026-09-24 현재 결과 미공개** | ORIGINAL-CONFIRMED | 순차 2회 호출(의도 Choice → 축별 positive/negative/stay Choice), 이미지 없음 | https://github.com/YuanKJing/Jev-as-Policy |
| 32 | 독립 비교(openroboto, 단일 시드): 사과→접시, Jev 1.13 성공 226회 호출 $0.019 181.8초 / Astra(영상상 low) 성공 212회 $5.93 707.3초 / GPT-4.1 mini 한도 초과. 저자: "성공률 추정이 아니다", "카메라 인식 입력이 아니다" | SINGLE-SOURCE (awesome-jev 인용) | LOW | https://github.com/Frank-ZY-Dou/awesome-jev |
| 33 | jev-robotics-demo(Fazal Ali): "코드가 작은 이동 후보를 만들고 각 후보를 물리 복사본에서 미리 시뮬레이션, Jev는 이동·잡기·놓기·완료를 고른다". 설계 원칙 "코드는 수학, Jev는 판단" | ORIGINAL-CONFIRMED (README) | 4★, LOW. **M3의 "PIVOT 텍스트판(후보 행동 + 예상 결과)"과 같은 발상의 공개 데모가 있다** | https://github.com/FazalAAli/jev-robotics-demo |
| 34 | jev-drone 저자: "더 단순한 경기장에서 3시드 맞춘 비교는 Jev 이점 없음" | CONFIRMED-MULTI (v3 기록 + awesome-jev) | LOW | https://github.com/RomanSlack/jev-drone |
| 35 | KITE(ICRA 2026): 광학 흐름 봉우리 + 시간 NMS로 움직임 키프레임 선택, 학습 없음(QLoRA 선택), Qwen2.5-VL-7B 위주, GPT-4o·Gemini 2.0도 시험 | SINGLE-SOURCE (프로젝트 페이지) | HIGH(학회). 저자 한계 서술 없음 | https://m80hz.github.io/kite/ |
| 36 | FLARE(CVPR 2026) PDF: 명시적 한계 절 없음. 저자 관점 "취약성은 구조가 아니라 데이터 체계(성공 편향 시연)에서 온다" | ORIGINAL-CONFIRMED | v3 정정 유지 | CVF open access PDF |
| 37 | 2606.15017(EMNLP 2026) 저자 블로그·게시물 | UNCONFIRMED | 찾지 않았다(검색 한도 배분). arXiv v2, EMNLP 2026 채택만 재확인 | https://arxiv.org/abs/2606.15017 |

## 3. 새로 찾은 것과 모듈별 시사점

### M4 (계단식 겹침 호출) — RTC 저자 발언에서 가져올 것
- **"정말 최고인가"**: RTC를 만든 PI는 이제 학습 시점 RTC를 쓴다(π0.7). 학습형 대안(A2C2, VLASH, FutureRTC 2607.24008)도 모두 모델 학습이 필요하다. Jev는 미세조정이 안 되므로(TypeSafe 문서: "고객 데이터로 미세조정하지 않는다") 학습형 계열은 전부 쓸 수 없다. 우리에게 맞는 것은 여전히 **추론 시점 RTC의 구조**다. 학습형 저자들도 "추론 시점 RTC가 더 유연하다"(부드러운 반영)고 적었다.
- **가져올 구조(3구간)** [제안]
  1. 고정 구간: Jev 응답이 오기 전에 실행될 스텝. 길이 d는 **실측 Jev p95 지연**으로 정한다(RTC의 d ≤ s ≤ H − d 제약을 그대로).
  2. 중간 구간: 이전 호출의 선택을 **스텝 거리에 따라 지수적으로 줄어드는 가중치의 사전 선호**로 쓴다. plan v3의 "불합의 + 새 호출 확신 낮음 → 이전 선택 유지(히스테리시스)"를 이 가중치로 구체화한다. RTC 저자는 앞부분만 고정하는 방식(hard masking)이 "방향이 더 빨리 바뀐다"고 했다.
  3. 새 구간: 새 호출로만 채운다.
- 학습형 RTC 저자가 말한 "지연 분포를 신중히 골라야 한다"는 우리에게는 "고정 구간 길이를 지연 분포에서 정해야 한다"로 옮겨진다. 지연이 날마다 바뀌므로(Astra와 같음) 고정 구간 길이도 실행 중에 최근 지연으로 갱신한다.
- HF 비동기 블로그의 가정("네트워크 왕복은 무시할 만하다")은 **우리에게 성립하지 않는다**. Jev는 원격 API라 왕복이 지연의 대부분이다. 큐 임계값 g는 가져오되, 왕복 지연을 따로 재서 d에 넣는다.
- Training-time RTC 저자는 SmolVLA 방식이 청크 사이 떨림을 남긴다고 지적했다. SmolVLA식 큐만으로는 부족하다는 근거이고, M5 스무딩이 반드시 필요하다는 사용자 설계와 맞는다.
- 선행 사례 점검: GPT-as-Policy는 Astra가 "π0.5 청크의 앞 1~15 스텝을 받아들일지"를 고른다. "앞부분만 확정"이라는 발상은 LLM 쪽에도 있다. 다만 느린 Astra가 한 번 판단하는 방식이고, 겹침 호출 사이 합의나 실제 반영 확인은 없다. M4의 선점 판단(v3/01)은 그대로 둔다.
- Harness VLA 저자가 스스로 "상위 계획기와 하위 사이 피드백 루프가 열려 있다"고 한계를 적었다. M4의 (b) 실제 반영 확인 + M7의 폐루프가 이 빈칸을 겨냥한다고 쓸 수 있다.

### Jev 전반 (M1, M3, M4, M10에 걸림)
- **보정의 기준이 정답이 아니다.** 출시 블로그에 따르면 기준 확률은 최상위 외부 모델의 예측이고, 공식 평가표의 기준 라벨도 Astra + Fable 5.1(high) 평균이다. 그래서 "Jev가 보정됐다"는 말은 "최상위 LLM 판단에 맞춰졌다"는 뜻에 가깝다. 이렇게 보면 Jev 성능의 상한은 대략 Astra 판단 수준이다(추론). plan v3의 "보정은 업체 주장뿐, 우리 데이터로 먼저 측정" 결정이 더 강하게 뒷받침된다.
- Molas가 인용한 "Noul이 Choice보다 잘 보정된다"(LOW)는 M3 절제 변수로 넣을 만하다. 같은 판단을 Noul과 Choice로 각각 물어 보정을 비교한다.
- Diogo Almeida: 중첩 구조가 깊어질수록 추론이 어려워진다. → M1 상태는 **평평하게** 둔다(깊은 장면 그래프 JSON 대신 평평한 술어 목록). M1 후보 2(작업 지향 장면 부분 그래프)는 평평하게 펼친 판을 비교 조건으로 둔다.
- 버전: 별칭은 예고 없이 새 모델을 가리키고, 창업자는 "매우 빨리" 새 모델을 낸다고 했다. 품질 유지 보장도 없다. → 모든 실험에서 `jev-1.13.0`처럼 **버전 ID를 고정**하고 응답의 `model` 필드를 기록한다. 보정 측정은 버전별로 다시 한다.
- 실시간: 비공식 사이트이지만 "마감을 지켜야 하는 루프는 네트워크 요청에 기대면 안 된다"는 원칙은 타당하다. 우리 구조에서 Jev는 50Hz 제어 루프 밖(스킬·보간·스무딩이 루프 안)에 있어야 한다. M4의 고정 구간이 그 역할을 한다.
- 지연: 한국 측정은 여전히 없다. 제3자 OpenRouter 경유 p50 0.53초, p95 0.81초(위치 미상, LOW). "1초에 3번"(사용자 예)은 p95 0.8초면 겹침 없이는 불가능하다. 계단식 겹침(동시 요청)이어야 가능하다. 속도 제한 1,200 요청/분 = 초당 20회라 3회/초는 여유 있다.

### M3 (행동 표현)
- Fazal Ali 데모가 "코드가 후보 이동을 물리 복사본에서 미리 시뮬레이션 → Jev가 고른다"를 이미 공개했다(4★, LOW). plan v3의 "PIVOT 텍스트판"은 발상 선점이 있다. 차별은 체계적 평가와 M4 결합에서 찾는다. 논문에서는 이 데모를 관련 사례로 적는다(신뢰도 낮으므로 근거로는 쓰지 않는다).
- Show-Harness 저자: 계획은 거의 포화(≥97%)이고 실패는 "센티미터"(빈 잡기 6→26%)에서 난다. 접촉·정밀 구간은 스킬에 맡기는 M6 방침의 가장 강한 공식 근거다. RoboDojo 평가(Astra는 정밀·동적 작업에 약함)와도 일치한다.

### M8 (Astra 호출, 다중 프레임, effort)
- **CaP-X(ICML 2026) Takeaway 3이 M8 기본값에 직접 걸린다**: 원시 RGB를 매 턴 끼우면 텍스트만 쓴 조건보다 나빠졌고, 영상을 "무엇이 바뀌었는지" 구조화된 자연어로 바꾼 Visual Differencing이 가장 좋았다. plan v3의 M8 기본값은 개별 이미지 6~10장이다. [제안] 비교 조건에 (i) 프레임만, (ii) 프레임 + 코드가 만든 변화 요약 텍스트, (iii) 변화 요약 텍스트만을 넣는다. 단 CaP-X는 코드 생성 과제이고 Astra를 시험하지 않았다. KITE(ICRA 2026)는 반대로 영상 키프레임이 실패 감지에 효과가 있었다. 어느 쪽이 Astra에 맞는지는 측정 전에는 모른다.
- **effort 사실 정정**: plan v3 §1은 "Show-Harness에서도 사고량을 늘려도 성공률은 그대로이고 시간만 늘었다"고 적었다. 공식 페이지 원문은 "사고 강도는 주로 에피소드를 줄인다(37 → 30 스텝), 벽시계 3.4배"이고, 모델은 GPT-5.6-sol이다. AGP에서는 Astra high가 low보다 느리지 않았고(9.2분 대 9.9분) 시간 분산이 작았다. 즉 "effort를 올리면 결정 수가 준다"는 증거가 두 곳에 있다. 사용자 발언("옳은 추론이 더 빨리 성공한다", "속도는 결정 수를 줄여서")과 맞는다. 반대로 RPent는 Astra **low**로 LIBERO-PRO 1위를 했고 non-reasoning 모드로 시간을 40% 줄였다. effort는 계속 실험 축으로 두되, 지표에 "결정 수(스텝 수)"를 넣어야 이 효과를 볼 수 있다.
- 사용된 effort 정리: GPT-as-Policy xhigh, AGP high(기본), Robocurve medium, RoboDojo medium, RPent 1위 low. 연구마다 달라 "Astra 로봇 연구의 표준 effort"는 없다.

### M10 (경험 축적)
- 저자들이 스스로 밝힌 공통 약점: **라벨(피드백) 품질**. ACE("신뢰할 만한 피드백 없으면 성능 하락"), Evo-Memory(실패를 거르지 않고 넣으면 기준 방법이 나빠짐, 피드백은 정답 신호), ReasoningBank(LLM 판정 라벨, 통합은 향후 과제). plan v3의 "센서 술어로 확정한 경험만 Jev 규칙 재료" 결정이 세 저자 발언으로 뒷받침된다.
- Evo-Memory 원문에서 ExpRAG는 ScienceWorld(Claude 3.7)에서 0.27로 ExpRecent(0.34)보다 낮았다. ReMem이 두 환경 모두 가장 좋았다. [제안] M10 골격을 "ExpRAG"라고만 쓰지 말고, ExpRAG는 기준 방법으로, 실패 걸러내기 + 정제(ReMem식)는 본 방법 후보로 적는다.
- AGP: 같은 작업을 반복하면 경험 재사용으로 Astra 응답 지연이 47% 줄었다(1회차 → 5회차, 종속 시행). 메모리는 성공률뿐 아니라 **속도 수단**이다. 사용자 규칙("속도는 결정 수를 줄여서")과 맞는 새 근거다. M10 지표에 Astra 응답 시간을 넣는다.
- RoboDojo: in-context 1회 시연은 전체 이득이 없었다. 교훈을 원시 시연으로 넣는 방식은 우선순위를 낮춘다.

### M6 / 비교 방법
- Zetta의 런타임 critic은 LLM이 아니라 **코드**다. LLM은 롤아웃 단위에서만 critic을 제안한다. plan v3 M6의 "Zetta(Astra가 critic 코드를 만들고 Jev가 매 주기 수락/거부)"는 Zetta 구조가 아니라 우리 변형이다. 수락/거부 주체(Role1)는 Zetta에서 후보 실행 중 상위 결정 권한자이고, 매 제어 주기의 LLM 호출이 아니다. 문구를 "Zetta의 코드 critic을 가져오고, 수락/거부만 Jev로 바꾼다"로 고친다.
- Zetta 수치(LIBERO-Pro 90.8%)는 작업마다 개발 시드 50개로 진화시킨 뒤의 결과다. "학습 없이 새 작업·환경" 주장과 비교할 때 이 적응 예산을 표에 함께 적어야 공정하다.
- Guava(2606.18363, Jiayuan Mao 외): "효과적인 하네스의 세 요소 = 반복 인식-추론-행동 루프, 의미 행동 추상화, 멀티모달 관측". 원문 초록만 봤고 신뢰도(스타, 학회) 미확인. 다음 조사 후보.

## 4. 반대 증거와 위험

- **Jev 보정은 정답이 아니라 LLM 판단 기준**(업체 발언). 로봇 상태처럼 LLM도 틀리는 판단에서는 Jev 확률이 "Astra가 뭐라 할지"의 추정일 수 있다. M4의 합의 판정이 같은 오류를 반복할 위험(v3의 자기 일관 오류)이 더 커진다. → (b) 외부 기준 확인이 필수라는 v3 결론이 강해진다.
- 제3자 Jev 로봇 사례는 모두 단일 시드·단일 시행이다. 3시드 비교에서 이점이 없었다는 보고(jev-drone)가 유일한 반복 측정이다.
- CaP-X는 원시 이미지가 해가 된다고 했고 KITE는 키프레임이 도움이 된다고 했다. 과제(코드 생성 대 실패 감지)가 달라 직접 충돌은 아니지만 M8 기본값을 측정 없이 정하면 안 된다.
- effort: 결정 수를 줄인다는 증거(Show-Harness, AGP)와 low로도 최고 성적이라는 증거(RPent)가 공존한다. 둘 다 과제가 다르다.
- Evo-Memory, 2606.15017 모두 메모리가 항상 이득은 아니라고 보여 준다(v3 유지).

## 5. plan.md에 반영할 제안

[사용자] 의도는 바뀌지 않는다. 아래는 모두 [제안]이다.
1. [제안] §1 Astra "effort에 대한 반대 증거" 문장 정정: "Show-Harness(GPT-5.6-sol): effort가 스텝 수를 37 → 30으로 줄이고 벽시계는 3.4배. AGP(Astra): low/medium/high 모두 5/5, high가 느리지 않고 분산이 작다. RPent 1위는 Astra low." M8 지표에 결정 수(스텝 수)를 추가.
2. [제안] M4에 RTC 3구간 구조를 명시: 고정 구간 = 실측 Jev p95 지연(실행 중 갱신), 중간 구간 = 이전 선택에 스텝 거리별 지수 감소 가중치(히스테리시스 구체화), 새 구간. 근거: RTC 3.2절, Training-time RTC 6절. SmolVLA 큐의 "왕복 무시" 가정은 쓰지 않는다.
3. [제안] Jev 실험 규칙 추가: 버전 ID(`jev-1.13.0`) 고정 + 응답 `model` 기록, 상태는 평평하게(중첩 최소), Noul 대 Choice 보정 비교를 첫 실험 보정 측정에 포함. 보정의 기준이 LLM 판단이라는 업체 발언을 §1에 적는다.
4. [제안] M8 다중 프레임 비교 조건에 CaP-X식 "코드가 만든 변화 요약 텍스트"(이미지 없이 / 이미지와 함께) 추가.
5. [제안] M10: ExpRAG는 기준 방법, 실패 걸러내기·정제(ReMem식)를 본 방법 후보로. 지표에 Astra 응답 시간 추가(AGP 47% 근거).
6. [제안] M6 Zetta 설명 정정(런타임 critic은 코드, LLM은 롤아웃 단위), 평가 표에 비교 방법별 작업 적응 예산(Zetta 개발 시드 50개 등) 열 추가. M3에 Fazal Ali 데모를 "발상 겹침(LOW)"으로 기록.
7. 감시 목록 갱신: Jev-as-Policy Astra+Jev 결과 **2026-09-24 현재 미공개**(마지막 커밋 9/21). Guava 신뢰도 확인.

## 6. 확인 못 한 것

- X 스레드 원문 전부(Kevin Black, Zechen Bai, Dmytro Hrybov, TypeSafe 공식 계정, Jay Chooi). x.com 402, 미러 중단.
- Kevin Black의 발표(강연) 자료. RTC 이후 PI가 추론 시점 RTC를 어떤 조건에서 권하는지 직접 발언은 못 찾았다. 확인된 것은 π0.7이 학습형을 쓴다는 사실뿐이다.
- evals.typesafe.ai 원문, Latent Space 녹취 원문(요약 모델 출력만 봄).
- RPent 리더보드의 effort별 비교(JS 페이지), GPT-as-Policy 보고서의 실패 유형(JS 페이지).
- 2606.15017, ACE, Evo-Memory, Zetta, Harness VLA, CaP-X 저자의 개인 게시물(검색 한도 때문에 찾지 않음).
- Show-Harness의 "H-VLA"가 Harness VLA인지 원문 대조.
- 한국에서의 Jev·Astra 지연(첫 실험에서 잰다).
