# v2 감사 보고서: M3 (촘촘한 객관식 행동 표현), M4 (RTC식 계단 겹침 Jev 호출), M5 (액션 스무딩)

작성일: 2026-09-23
대상: `docs/plan.md` v1의 M3, M4, M5

조사 한계:
- WebSearch만 쓸 수 있었다. arXiv, HF, GitHub 원문은 프록시에 막혔다(`huggingface.co` WebFetch도 EGRESS_BLOCKED).
- 세션 전체 검색 한도(200회)가 이 모듈 조사 도중에 다 찼다. 이 모듈에는 약 30회만 썼다. 그래서 **LLM/VLM 쪽 문헌 조사(이산 선택 확률 → 연속값 변환, 토큰 수준 일관성 등)는 거의 못 했다.** 5절에 정리했다.
- HF 업보트, GitHub 스타는 한 번도 확인하지 못했다. 신뢰도는 학회, 소속, 인용 여부로만 매겼다.

신뢰도 등급(CREDIBILITY RULE):
- HIGH: 동료 심사 학회(NeurIPS/ICLR/RSS 등)이거나 잘 알려진 랩
- MEDIUM: arXiv만 있지만 알려진 랩이거나, 다른 논문의 비교 기준으로 쓰임
- LOW: arXiv만 있고, 잘 알려지지 않은 그룹이며, 반응이 확인되지 않음. **추천하지 않는다.**

---

## 1) 검증 표

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| RTC: "Real-Time Execution of Action Chunking Flow Policies", Kevin Black, Manuel Y. Galliker, Sergey Levine, arXiv 2506.07339, NeurIPS 2025 | CONFIRMED-MULTI | 제목, 저자, ID, 학회 모두 맞다. 2025-06 공개로 기간 안에 든다. 신뢰도 HIGH(Physical Intelligence, NeurIPS). **범위 주의**: diffusion/flow 정책용 inference-time inpainting 알고리즘이다. guidance를 쓰므로 Jev 같은 블랙박스 Choice 모델에는 그대로 쓸 수 없다. 발상(고정, 겹침 조건화, soft mask)만 가져올 수 있다. | https://arxiv.org/abs/2506.07339 , https://neurips.cc/virtual/2025/poster/117747 , https://proceedings.neurips.cc/paper_files/paper/2025/hash/300ccb2187dedd4edcc07f7e76d8e553-Abstract-Conference.html |
| RTC 주장: 300ms 넘는 지연에도 강건 | CONFIRMED-MULTI | 원문 표현은 "inference delays in excess of 300 milliseconds"이고, 모델 예측 구간의 30%가 넘는 지연이다. 실제 로봇 실험에서는 주입한 지연에 성능이 전혀 떨어지지 않았다. | https://www.pi.website/research/real_time_chunking , https://arxiv.org/html/2506.07339v1 |
| RTC 주장: 20% 빠름 | CONFIRMED-MULTI | 비교 대상은 **synchronous inference**다(같은 동작을 20% 빨리 수행). temporal ensembling과 비교한 수치가 아니다. plan에는 이 수치가 없으니 인용할 때 비교 대상을 정확히 쓴다. | https://www.pi.website/research/real_time_chunking , https://arxiv.org/html/2506.07339v1 |
| RTC 주장: temporal ensembling보다 부드러움 | CONFIRMED-MULTI | 맞다. 더 강한 사실도 있다. **temporal ensembling은 다봉(multi-modal) 행동 분포를 처리하지 못해 대부분의 시나리오에서 실패했다.** 실제 로봇에서는 진동이 커서 보호 정지가 걸려 아예 실행되지 않았다. 이 결과는 M3의 "확률 가중 평균" 안에 직접 불리한 증거다(3절). | https://arxiv.org/html/2506.07339v1 , https://www.researchgate.net/publication/392529801_Real-Time_Execution_of_Action_Chunking_Flow_Policies |
| Training-time RTC: "Training-Time Action Conditioning for Efficient Real-Time Chunking", Kevin Black, Allen Z. Ren, Michael Equi, Sergey Levine, arXiv 2512.05964 (2025-12-05) | CONFIRMED-MULTI(존재, 저자, 주장) / 학회는 UNCONFIRMED | plan의 "추론 오버헤드 없이 확정된 앞부분을 조건으로 준다"는 맞다. 방법은 학습할 때 지연을 흉내 내고 action prefix를 조건으로 주는 것이다. 지연이 클수록 inference-time RTC보다 낫고, π0.6으로 box building과 espresso 실제 실험을 했다. 저자가 직접 밝힌 **한계**: (1) 지연에 해당하는 "hard" prefix만 조건으로 줄 수 있어서, inference-time RTC처럼 prefix 너머를 soft하게 반영하지 못한다. (2) 학습 때 흉내 낼 지연 분포를 예상 지연에 맞춰 골라야 한다. **Jev는 학습할 수 없으므로** 이 방법은 "확정 prefix를 입력에 넣는다"는 프롬프트 설계로만 옮겨진다. 신뢰도 HIGH(PI). | https://arxiv.org/html/2512.05964v1 , https://huggingface.co/papers/2512.05964 , https://arxiv.org/pdf/2512.05964 |
| A2C2: "Leave No Observation Behind: Real-time Correction for VLA Action Chunks", Kohei Sendai, Maxime Alvarez, Tatsuya Matsushima, Yutaka Matsuo, Yusuke Iwasawa, arXiv 2509.23224 | CONFIRMED-MULTI(존재, 주장) / ICLR 2026은 SINGLE-SOURCE | plan에 제목과 저자가 없었으니 추가한다. 소속은 도쿄대 Matsuo-Iwasawa 랩이다. 검색 요약 하나는 "ICLR 2026 published", 다른 하나는 "submitted to ICLR 2026"이라고 해서 채택 여부가 확실하지 않다. 신뢰도 MEDIUM-HIGH. | https://arxiv.org/abs/2509.23224 , https://www.alphaxiv.org/abs/2509.23224 |
| A2C2 주장: RTC 대비 Kinetix +23, LIBERO Spatial +7 | CONFIRMED-MULTI | 단위는 %p다. Kinetix 12개 작업에서 +23%p, LIBERO Spatial에서 +7%p다. plan은 Kinetix만 적었다. **정정할 점**: A2C2는 base VLA의 feature와 최신 관측을 받는 **학습형** 보정 헤드다. Jev 뒤에 그대로 붙일 수 없다. | https://arxiv.org/abs/2509.23224 , https://www.emergentmind.com/topics/asynchronous-action-chunk-correction-a2c2 |
| A2C2 주장: 4.7ms | UNCONFIRMED | 검색 요약에서는 "lightweight, minimal overhead"라는 말만 보였고 4.7ms라는 수치는 찾지 못했다. 원문으로 확인하기 전에는 인용하지 않는다. | https://www.emergentmind.com/topics/asynchronous-action-chunk-correction-a2c2 |
| 비교 연구: "Understanding Asynchronous Inference Methods for Vision-Language-Action Models", arXiv 2605.08168 | CONFIRMED-MULTI(존재, 결론) | 비교한 방법은 IT-RTC, TT-RTC, VLASH, A2C2 네 가지다. Kinetix와 LIBERO에서 지연을 최대 20 제어 스텝까지 줬다. 결론: A2C2가 Kinetix에서 가장 효과적이었고(d=8까지 solve rate 90% 이상), LIBERO에서는 **d=4부터** 앞섰다. IT-RTC는 지연이 작을 때는 경쟁력이 있지만, 조각이 길고(H=30) 지연이 크면 크게 떨어졌다. TT-RTC는 학습형 방법 중 가장 강건했다. A2C2는 다른 방법과 함께 쓸 수 있다. **정정**: plan의 "A2C2가 전반적으로 가장 강했다"는 조금 과장이다. 긴 조각과 큰 지연 조건에서 가장 강했다. **신뢰도 LOW-MEDIUM**: 저자는 Ayoub Agouzoul 1명이고, arXiv에만 있으며, 학회는 확인되지 않았다. 결론은 참고만 하고 핵심 근거로 삼지 않는다. | https://arxiv.org/abs/2605.08168 , https://arxiv.org/html/2605.08168 |
| SmolVLA (arXiv 2506.01844): 큐가 임계값 아래로 내려가면 다음 조각 요청 | CONFIRMED-MULTI | 맞다. 논문에서는 g, 코드에서는 `chunk_size_threshold`다. 신뢰도 HIGH(Hugging Face LeRobot, 널리 쓰임). 우리 구조에 가장 쉽게 옮길 수 있는 비동기 스케줄러다. | https://arxiv.org/pdf/2506.01844 , https://huggingface.co/docs/lerobot/async , https://huggingface.co/blog/async-robot-inference |
| BID (arXiv 2408.17355, ICLR 2025) | CONFIRMED-MULTI | 저자는 Yuejiang Liu, Jubayer Ibn Hamid, Annie Xie, Yoonho Lee, Maximilian Du, Chelsea Finn(Stanford)이다. 기준은 backward coherence와 forward contrast다. **제목 정정**: 최신판(v3)과 ICLR 페이지의 제목은 "Bidirectional Decoding: Improving Action Chunking via Closed-Loop Resampling"이다. 첫 판 제목은 "...via Guided Test-Time Sampling"이었다. 1.5년 기간 밖이지만 신뢰도 HIGH. | https://arxiv.org/abs/2408.17355 , https://iclr.cc/virtual/2025/32377 |
| VLASH (arXiv 2512.01031) | CONFIRMED-MULTI(존재, 주장) / 날짜 불일치 | 제목은 "VLASH: Real-Time VLAs via Future-State-Aware Asynchronous Inference"이고 MIT(Han Lab)다. 이전에 보낸 action chunk로 실행 시점의 로봇 상태를 추정하고, 그 상태를 조건으로 준다. synchronous 대비 최대 2.03배 빠르고 반응 지연은 최대 17.4배 줄었다. 한 검색 요약은 게시일을 2026-07-26이라고 했지만, ID 2512는 2025-12 첫 판을 뜻한다. 그 날짜는 개정판일 가능성이 크다(미확인). 신뢰도 MEDIUM-HIGH. | https://arxiv.org/abs/2512.01031 , https://www.rle.mit.edu/vlash-real-time-vlas-via-future-state-aware-asynchronous-inference |
| Legato (arXiv 2602.12978) | CONFIRMED-MULTI | 제목은 "Learning Native Continuation for Action Chunking Flow Policies"이고 2026-02-13 공개다. **RSS 2026에 채택**됐다(roboticsconference.org program). 실제 로봇 5개 작업에서 RTC 대비 궤적 부드러움과 작업 완료 시간이 각각 약 10% 나아졌다. 저자는 RTC가 정책 바깥에 있어서 "spurious multimodal switching"이 생긴다고 지적한다. 학습형이라서 Jev에는 직접 쓸 수 없다. 신뢰도 HIGH. | https://arxiv.org/html/2602.12978v1 , https://roboticsconference.org/program/papers/58/ , https://lyfeng001.github.io/Legato/ |
| Event-Triggered Async Inference (arXiv 2609.22587) | CONFIRMED-MULTI | 제목은 "React When You Need To: Event-Triggered Asynchronous Inference for VLA Policies"다. Yansong Wu, Huaqing Li, Tianding Hou, Lingyun Chen, Alois Knoll(TUM, MBZUAI), 2026-09-18 공개다. 장면 변화량에 따라 추론 간격을 바꾼다. 평균 성공률 95%로 가장 강한 기준 방법보다 55%p 높았다. 공개된 지 5일밖에 안 돼 반응을 확인할 수 없다. 신뢰도 MEDIUM(알려진 랩이지만 심사 전). | https://arxiv.org/abs/2609.22587 , https://react-when-you-need-to.github.io/ |
| ABPolicy (arXiv 2602.23901) | CONFIRMED-MULTI | "ABPolicy: Asynchronous B-Spline Flow Policy for Real-Time and Smooth Robotic Manipulation", Tianjin University, 2026-02-27 공개다. B-spline 제어점 공간에서 동작하는 flow 정책이고, 양방향 예측과 refitting으로 조각 사이 연속성을 맞춘다. 학습형이다. 신뢰도 **LOW-MEDIUM**(arXiv만 있고 반응 미확인). 추천에서 뺀다. | https://arxiv.org/abs/2602.23901 |
| SMILE (arXiv 2608.29432) | CONFIRMED-MULTI | Jongwoo Park, …, Michael S. Ryoo(Stony Brook, Salesforce AI Research)다. B-spline 계수를 예측하는 방식이고, 행동 표현만 바꾼다. SmolVLA에 적용했을 때 경계가 아닌 구간의 가속도가 78.6%, 속도 부호 변화율이 42.3% 줄었다. 학습형이다. 신뢰도 MEDIUM(알려진 연구자, arXiv만 있음). | https://arxiv.org/abs/2608.29432 |
| LiPo (arXiv 2506.05165) | CONFIRMED-MULTI | 저자는 Dongwoo Son, Suhan Park다. 구성은 (1) 지연을 고려해 겹치는 조각을 미리 생성하는 스케줄링, (2) 겹침 구간 선형 블렌딩, (3) jerk 최소화 궤적 최적화다. **학습이 필요 없는 후처리**다. 던지기 성공률이 80%에서 90%로 올랐다. International Journal of Control, Automation, and Systems(Springer)에 실렸다. 신뢰도 MEDIUM(동료 심사 저널이지만 최상위 학회는 아님). | https://arxiv.org/abs/2506.05165 , https://link.springer.com/article/10.1007/s12555-025-0537-0 |
| ACT temporal ensembling (arXiv 2304.13705) | CONFIRMED-MULTI | 가중치는 w_i = exp(-m·i)다. 1.5년 기간 밖이다. RTC 논문에서 다봉 분포 때문에 실패한 기준 방법이므로, **기준 방법으로만** 쓴다. | https://arxiv.org/pdf/2304.13705 , https://arxiv.org/html/2506.07339v1 |
| FAST (arXiv 2501.09747) | CONFIRMED-MULTI(존재, 저자, 주장) / 학회 UNCONFIRMED | 저자는 Pertsch, Stachowicz, Ichter, Driess, Nair, Vuong, Mees, Finn, Levine다. 방법은 DCT, 계수 양자화, BPE 순서다. 핵심 주장은 "차원별, 스텝별 단순 binning은 고주파 데이터에서 성능이 나쁘다"는 것이다. 2025-01 공개라 1.5년 기간 밖이다. 신뢰도 HIGH(PI). plan에는 인용되지 않았다. | https://arxiv.org/abs/2501.09747 , https://www.pi.website/download/fast.pdf |
| Slow Brain, Fast Planner (arXiv 2606.20458) | CONFIRMED-MULTI | 제목은 "Slow Brain, Fast Planner: Latency-Resilient VLM-Augmented Urban Navigation"이고, Zhenghao "Mark" Peng 외 4명, 2026-06-18 공개다. VLM이 planner 후보 중 **인덱스를 고르고(이산 선택)**, 학습 없는 궤적 수준 융합층이 **오래된(stale) VLM 선택**을 기하 유사도와 지수 감쇠로 실시간 planner 점수에 녹인다. ADE가 30% 줄었다. **우리 구조(느린 선택자, 빠른 실행)와 가장 가까운 선례다.** 신뢰도 MEDIUM(arXiv만 있음). | https://arxiv.org/abs/2606.20458 |
| plan의 "RTC식 겹침 조각을 텍스트 결정 모델(LLM)에 적용한 연구는 없다" | 부분적으로 WRONG(범위 조정 필요) | 가까운 선행 연구가 있다. (a) **Real-Time Execution with Autoregressive Policies** (arXiv 2606.13355, 2026-06-11): 토큰 기반 autoregressive 정책에서 tokenization horizon 조정과 constrained decoding으로 실시간 비동기 실행을 했다. 같은 수준의 flow 정책보다 나았고, 다중 궤적 디코딩 오버헤드는 약 13ms였다. (b) Slow Brain, Fast Planner: 느린 VLM의 이산 선택을 오래된 상태 그대로 실시간 제어와 융합했다. 다만 "텍스트 전용 API LLM이 확률이 붙은 typed choice를 내고, 계단식 겹침 호출과 겹침 구간 자기 검증을 한다"는 조합은 이번 조사에서 찾지 못했다. 컨트리뷰션 문구를 좁혀야 한다. | https://arxiv.org/abs/2606.13355 , https://arxiv.org/abs/2606.20458 |

---

## 2) 더 나은 대안 / 최신 SOTA (2026-09 기준)

### 2.1 비동기, 겹침 방법의 현황
검색으로 확인한 흐름은 다음과 같다.
1. Inference-time RTC(NeurIPS 2025)
2. 학습형 prefix 조건화: TT-RTC(PI), Legato(RSS 2026), Soft RTC(2605.25537, LOW)
3. 미래 상태 추정 조건화: VLASH(MIT), FutureRTC(2607.24008, LOW)
4. 스텝별 잔차 보정: A2C2
5. 빠른 채널과 느린 채널 분리: πR²(2607.26055, CMU Tulsiani, 2026-07). 시뮬레이션에서 최대 +23%, 실제에서 최대 +30%(가장 강한 기준 방법 대비)다.
6. 추론 시점 조절: SmolVLA 큐 임계값, Event-triggered(2609.22587)

- 출처: https://arxiv.org/abs/2605.25537 , https://arxiv.org/abs/2607.24008 , https://arxiv.org/abs/2607.26055

**"가장 좋은 방법"에 대한 판단**
- 공통 조건 비교는 비교 연구(2605.08168) 하나뿐이고, 신뢰도가 LOW-MEDIUM이다. 여기서는 긴 조각과 큰 지연에서 A2C2가 가장 좋았고, 학습형 중에서는 TT-RTC가 가장 강건했다.
- 동료 심사를 거친 것 중 RTC보다 낫다고 보인 것은 Legato(RSS 2026, 부드러움과 완료 시간 약 10%)와 A2C2(RTC 대비 +23%p, ICLR 2026 채택은 단일 출처)다.
- 결론: **"2026-09 기준으로 확정된 1위는 없다"가 정직한 답이다.** 증거는 "A2C2(보정) + TT-RTC/Legato(학습형 prefix 조건화)의 조합"이 가장 강하다는 쪽으로 기운다. 출처: https://arxiv.org/html/2605.08168 , https://roboticsconference.org/program/papers/58/

**우리에게 중요한 점: 위 방법 대부분은 정책을 학습시키거나 flow guidance를 쓴다. Jev는 둘 다 할 수 없다.** 그래서 "무엇이 가장 좋은가"보다 "어떤 발상이 학습 없이 블랙박스 Choice 모델로 옮겨지는가"가 기준이다.

| 발상 | 원 방법 | Jev로 옮길 수 있나 |
|---|---|---|
| 확정 prefix를 조건으로 준다 | TT-RTC | 가능. 프롬프트에 "이미 확정된 d스텝"을 넣으면 된다(plan 3번과 같다). |
| 실행 시점 상태를 미리 굴려서 입력한다 | VLASH | **가능하고, plan에 빠져 있다.** Jev 호출 시점의 상태가 아니라, 확정 동작을 적용한 뒤 응답 도착 시점의 예상 상태(M1 JSON)를 넣는다. 학습이 필요 없다. |
| 매 제어 스텝 최신 관측으로 작은 보정 | A2C2 | 부분적으로 가능. 학습 헤드 대신 기하 기반 servo 보정(목표 − 그리퍼 벡터 등)으로 바꿔야 한다. |
| 후보 여러 개 중 이전 결정과 가장 일관된 것을 고른다 | BID | 가능. Jev가 준 확률과 이전 조각과의 일관성을 곱해서 고른다. |
| 오래된 이산 선택을 기하 유사도와 지수 감쇠로 실시간 제어에 녹인다 | Slow Brain, Fast Planner | **가능하고, 우리 구조와 가장 잘 맞는다.** Jev가 늦게 답해도 선택의 영향력이 시간에 따라 줄어든다. |
| 추론 간격을 장면 변화에 맞춘다 | Event-triggered | 가능. M1의 diff 크기를 트리거로 쓴다. |

### 2.2 스무딩
- 2026년 흐름은 **B-spline을 행동 표현으로 쓰는 것**이다(ABPolicy, SMILE, B-spline Policy 2607.09648, LieSpline-DP 2609.15162). 모두 학습형이라 Jev에 직접 쓸 수 없다.
- **학습 없이 쓸 수 있는 것**은 LiPo다(겹침 선형 블렌딩과 jerk 최소화 최적화). 저널 게재까지 확인했다.
- plan의 "B-스플라인 적합 1순위"는 방향은 맞다. 다만 근거로 든 ABPolicy와 SMILE은 학습형 정책이다. "이미 나온 경유점에 B-spline을 맞추는" 방식의 근거로는 LiPo(최적화 후처리)가 더 정확하다.
- 출처: https://arxiv.org/abs/2607.09648 , https://arxiv.org/html/2609.15162v1 , https://arxiv.org/abs/2506.05165

### 2.3 M3 행동 이산화
- FAST(PI)는 스텝별, 차원별 binning이 고주파에서 나쁘다고 보였다. 시간 방향으로 압축한 표현(DCT)이 낫다는 뜻이다. https://arxiv.org/abs/2501.09747
- 2606.13355는 토큰 정책에서 tokenization horizon이 실시간성의 핵심 조절 손잡이라고 보였다. https://arxiv.org/abs/2606.13355
- 이 두 결과를 종합한 [제안]:
  - Jev가 제어 스텝마다 Δ방향과 크기를 고르는 방식은 스텝끼리 서로 강하게 겹친다.
  - 대신 **저주파 경유점이나 스플라인 제어점을 객관식으로 고르게** 하고, M5(B-spline/LiPo)가 고주파로 채우게 한다.
  - 그러면 M3와 M5가 같은 표현(제어점)을 공유한다.
  - 이것은 검색 근거를 바탕으로 한 추론이고, 실험으로 확인해야 한다.

---

## 3) 반대 증거와 위험

1. **확률 가중 평균의 위험(M3)**
   - RTC 논문에서 temporal ensembling은 다봉 행동 분포를 평균 내다가 대부분 실패했고, 실제 로봇에서는 진동으로 보호 정지가 걸렸다. https://arxiv.org/html/2506.07339v1
   - Legato 저자도 RTC가 "spurious multimodal switching"을 일으킨다고 지적했다. https://arxiv.org/html/2602.12978v1
   - Jev의 보기 확률이 "왼쪽 0.45, 오른쪽 0.45"처럼 두 봉우리이면, 가중 평균은 "거의 정지"라는 잘못된 동작이 된다.
   - [제안] 순서가 있는 보기(크기 단계)에서, 분포가 한 봉우리일 때만 기댓값을 쓴다. 방향처럼 범주형인 보기는 최빈값(mode)을 쓰고, 확률은 신뢰도 게이트로만 쓴다.
2. **RTC 계열은 모두 flow/diffusion 정책을 전제한다.** inpainting guidance와 학습형 prefix 조건화 모두 Jev에 그대로 적용되지 않는다. "RTC를 적용했다"고 쓰면 과장이다. "RTC의 발상(고정, 겹침 조건화, soft 가중)을 텍스트 결정 모델로 옮겼다"로 써야 한다.
3. **지연의 크기**
   - RTC가 다룬 지연은 300ms 수준이다.
   - Jev는 70~500ms인데, 여러 축의 Choice를 여러 스텝씩 묻는 호출이면 더 길어질 수 있다(미확인).
   - 비교 연구에서 IT-RTC는 긴 조각과 큰 지연에서 크게 떨어졌다. https://arxiv.org/html/2605.08168
   - 겹침 방식만 믿지 말고, VLASH식 상태 굴리기와 A2C2식 빠른 보정을 함께 두는 것이 안전하다.
4. **1초에 3번 계단식 호출의 비용과 일관성**: API 호출 수가 3배가 된다. 같은 입력에서도 LLM 응답이 흔들릴 수 있다. 그러면 겹침 불일치가 정보가 아니라 잡음이 될 위험이 있다. 이 부분의 선행 증거는 찾지 못했다.
5. **컨트리뷰션 주장의 위험**: autoregressive 토큰 정책의 실시간 실행(2606.13355)과 느린 VLM 이산 선택의 지연 강건 융합(2606.20458)이 이미 있다. "선행 연구 없음"이라고 쓰면 심사에서 반박당한다.
6. **비교 연구의 신뢰도**: 2605.08168은 저자 1명이고 arXiv에만 있다. "A2C2가 가장 강하다"를 핵심 근거로 쓰면 위험하다. A2C2 원 논문(RTC 대비 +23/+7%p)을 1차 근거로 쓴다.

---

## 4) 이 모듈에 장착할 모듈 후보 순위

### M4 (계단식 겹침 호출과 자기 검증)
1. **SmolVLA식 큐 임계값 비동기 스케줄러 + 확정 prefix 고정(RTC/TT-RTC 발상)**
   - 근거: 학습이 필요 없고 구현이 쉽다.
   - 신뢰도: SmolVLA는 HIGH(Hugging Face, LeRobot 공식 문서). RTC는 HIGH(NeurIPS 2025, PI). TT-RTC는 HIGH(PI, 학회 미확인).
   - https://huggingface.co/docs/lerobot/async , https://arxiv.org/abs/2506.07339
2. **VLASH식 미래 상태 굴리기**
   - Jev 입력에 "응답 도착 시점의 예상 상태"를 넣는다. plan에 없는 핵심 보완이다. 학습 없이 옮길 수 있다.
   - 신뢰도: MEDIUM-HIGH(MIT Han Lab). 비교 연구에서도 4대 방법 중 하나로 다뤄졌다.
   - https://arxiv.org/abs/2512.01031
3. **Slow Brain, Fast Planner식 stale 선택 융합(기하 유사도 × 지수 감쇠)**
   - 겹침 구간에서 이전 조각과 새 조각을 섞는 가중치 규칙으로 쓴다. RTC soft mask의 텍스트 선택 버전이라 할 수 있다.
   - 신뢰도: MEDIUM(arXiv만 있음, 학습 불필요, 구조가 가장 가깝다).
   - https://arxiv.org/abs/2606.20458
4. **A2C2 발상의 비학습 보정층**
   - 매 제어 스텝 최신 상태로 기하 보정을 한다. plan 5번의 "오차 보정"은 다음 Jev 호출에 넣는 느린 루프라서, A2C2처럼 매 스텝 도는 빠른 루프가 따로 필요하다.
   - 신뢰도: A2C2는 MEDIUM-HIGH(도쿄대, ICLR 2026 단일 출처).
   - https://arxiv.org/abs/2509.23224
5. **BID식 일관성 기반 선택**
   - Jev 확률 × 이전 조각과의 일관성으로 보기를 고른다.
   - 신뢰도: HIGH(ICLR 2025, Stanford Finn). 기간 밖이다.
   - https://arxiv.org/abs/2408.17355
6. (선택) **Event-triggered 추론 간격**
   - M1 diff를 트리거로 쓴다.
   - 신뢰도: MEDIUM(TUM Knoll, 공개 5일).
   - https://arxiv.org/abs/2609.22587

### M5 (스무딩)
1. **LiPo식 후처리**(겹침 선형 블렌딩 + jerk 최소화 최적화)
   - 학습이 필요 없는 유일한 확인된 선택지다.
   - 신뢰도: MEDIUM(Springer IJCAS 저널).
   - https://arxiv.org/abs/2506.05165
2. **B-spline 제어점 표현**(M3와 공유)
   - 근거는 SMILE(MEDIUM)이다. B-spline 표현이 jitter를 크게 줄였다.
   - 학습형 결과를 표현 선택의 근거로만 쓴다.
   - https://arxiv.org/abs/2608.29432
3. 기준 방법: temporal ensembling(ACT), 지수 평활
   - 비교용으로만 쓴다. RTC 논문에서 실패했다.
- **추천에서 뺌(LOW)**: ABPolicy, Soft RTC(2605.25537), FutureRTC, PAINT(2606.19774), GROOVE(2609.13695), SEAM(2607.04609). 모두 arXiv만 있고 그룹이나 반응이 확인되지 않았다.

### M3 (행동 표현)
1. **저주파 경유점/제어점 객관식 + 크기는 순서형 보기** (FAST와 2606.13355에서 도출한 [제안])
   - 한 봉우리일 때만 기댓값을 쓰고, 범주형 보기는 최빈값을 쓴다.
2. plan 원안(스텝별 방향, 크기, 회전, 그리퍼 Choice)
   - FAST가 보인 "스텝별 binning의 한계"에 해당할 위험이 있다. 비교 실험 대상으로 둔다.

---

## 5) 확인 못 한 것

- **LLM/VLM 쪽 조사(검색 한도 소진으로 못 함)**
  - LLM이 낸 숫자 토큰이나 보기 확률을 연속값으로 바꾸는 방법(예: 확률 기댓값 디코딩, regression-aware inference, 분류로 바꾼 회귀인 HL-Gauss 류)
  - LLM 출력의 보정(calibration)과 일관성(self-consistency)
  - 토큰 수준 런타임 제어(검색 결과에 ATLAS-RTC, arXiv 2603.27905 제목만 보였고 내용 미확인)
  - 이 조사는 다음 세션에서 해야 한다. **M3의 "확률 → 연속값" 부분은 현재 근거가 없다.**
- **이산화와 좌표 선택 방법들**(PIVOT의 반복 시각 프롬프트, CARP의 coarse-to-fine, RT-2/OpenVLA의 256-bin): 이번 세션에서 검색으로 확인하지 못했다. 이름만 알고 수치, 날짜, 학회를 검증하지 않았으므로 인용하지 않는다.
- A2C2의 4.7ms 수치, A2C2의 ICLR 2026 최종 채택(출처 하나만 확인)
- Training-time RTC와 FAST의 학회 채택 여부
- VLASH 첫 판 날짜(2025-12로 추정, 한 요약은 2026-07-26이라고 함)
- 모든 항목의 HF 업보트와 GitHub 스타(접근 차단)
- Kevin Black / Physical Intelligence의 블로그, 강연, X에서 말한 RTC 한계: PI 연구 페이지와 TT-RTC 논문에 적힌 한계(inpainting 오버헤드, hard prefix만 가능, 지연 분포 선택 필요)만 확인했다. 강연이나 X 스레드는 찾지 못했다.
- 2606.13355(autoregressive 실시간 실행)의 학회 채택 여부와 저자 소속
- πR²(2607.26055)의 학회 채택 여부
- "Why Does Action Chunking Improve Behavioral Cloning Performance in Robotic Control?"(arXiv 2608.02547): 제목만 보였고 내용 미확인
- 이 모듈에 쓴 검색은 약 30회다(목표는 40회 이상). 세션 한도 200회가 차서 더 할 수 없었다.
