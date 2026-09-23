# M7 진행 판별 / M8 Astra 호출 시점·다중 프레임 — v1 계획 감사 (v2)

작성일: 2026-09-23. 대상: `docs/plan.md`의 M7, M8.

조사 한계 (먼저 밝혀 둔다)
- 네트워크: WebSearch만 쓸 수 있었다. arXiv, HF 등 원문 페이지는 프록시에서 막혔다(huggingface.co 확인: EGRESS_BLOCKED). 모든 내용은 검색 결과 요약(snippet)으로 확인했다.
- **검색 예산 소진**: 세션 전체 WebSearch 한도(200회)가 이 모듈 조사 도중에 다 떨어졌다(이 모듈에서 약 30회 사용). 그래서 아래는 조사하지 못했다. (a) CoMuRoS, AHA 검증, (b) 주기/이벤트/시간 초과 호출의 정량 비교(로봇, 고전 event-triggered control, LLM 에이전트), (c) 일반 VLM 분야의 격자 대 개별 프레임 대 비디오 비교, (d) 저자 블로그와 발표. 이것들은 5절에 "확인 못 함"으로 모았다. **"선행 비교가 없다"(plan.md 4절 3번)는 이번에도 확인하지 못했다. 없다는 증거가 아니다.**
- 신뢰도 표기: HIGH = 동료 심사 학회(NeurIPS/ICML/ICLR/CoRL 등) 또는 이름난 연구실 + 반응 확인. MED = 이름난 연구실이지만 심사 전이거나, 심사는 됐지만 반응 정보가 없음. LOW = arXiv에만 있고, 알려진 그룹이 아니고, 반응도 확인되지 않음. 인용 수, HF 추천 수, GitHub 스타는 검색 요약에 나오지 않아 **어느 항목도 확인하지 못했다.**

---

## 1) 검증 표

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| VLAC (2509.15937) "관측 쌍 + 목표 → 진행 변화량, 완료 신호. 퇴보·정체 감지" | CONFIRMED-MULTI | 제목: "A Vision-Language-Action-Critic Model for Robotic Real-World Reinforcement Learning". 2025-09-19 제출. InternVL 기반이고 대규모 데이터로 **학습한** 모델이다. 퇴보·정체 감지는 음성 샘플을 만들어 학습시킨 결과다. 한 번의 in-context 예시로 새 작업에 옮길 수 있다고 주장한다. OpenReview 제목은 "VLAC: A Generalist Action-Critic Model via Pair-wise Progress Understanding"이다. 심사 결과는 확인하지 못했다. 코드는 InternRobotics에서 공개했다. 기간 안. 신뢰도 MED (InternRobotics, 심사 결과 미확인). **API 제로샷 모듈이 아니다.** | https://arxiv.org/abs/2509.15937 , https://huggingface.co/papers/2509.15937 , https://openreview.net/forum?id=PmYX0XiQQ0 , https://github.com/InternRobotics/VLAC |
| π\*0.6 / RECAP (2511.14759) "V(s')−V(s)를 좋아짐/나빠짐으로 이진화" | CONFIRMED-MULTI (보완 필요) | Physical Intelligence 작업이다. 가치 함수는 분포형이다. 성공 에피소드에서는 **완료까지 남은 스텝 수의 음수**를, 실패 에피소드에서는 큰 음수를 예측한다. 이 값으로 advantage를 구하고, "positive/negative" 텍스트 토큰으로 이진화해서 정책에 조건으로 넣는다. 즉 핵심은 "진행도 = 남은 시간"이라는 정의다. VLA 학습용이라 우리 쪽에는 **정의만** 가져올 수 있다. 기간 안. 신뢰도 HIGH (PI, Levine 공식 발표). | https://arxiv.org/abs/2511.14759 , https://www.alphaxiv.org/abs/2511.14759v1 , https://x.com/svlevine/status/1990574918548029928 |
| TOPReward (2602.19313) "토큰 확률을 진행도로. **Jev의 확률 출력과 잘 맞는다**" | 논문 존재·방법: CONFIRMED-MULTI. "Jev와 잘 맞는다": **WRONG** | 제목: "TOPReward: Token Probabilities as Hidden Zero-Shot Rewards for Robotics". 2026-02-22 제출, 2026-07-22 개정. 학습이 필요 없다. **비디오를 보는 VLM** 내부 logit에서 "작업이 완료됐다"의 확률을 읽는다. Qwen3-VL에서 평균 VOC 0.947이다. 정정할 점: (1) Jev는 텍스트만 받으므로 비디오 조건부 확률을 낼 수 없다. Jev의 확률은 텍스트 상태를 조건으로 한 값이라 TOPReward와는 다른 신호다. (2) logit을 직접 읽어야 해서 오픈 가중치 모델에 맞는다. Gemini-2.5-Pro에서는 GVL(0.541)이 TOPReward(0.433)보다 나았다(OXE). 저자는 강제되는 chat template 탓으로 본다. 따라서 **API 모델(Astra)에 쓰면 성능이 떨어질 위험이 크다.** 기간 안. 신뢰도 MED (프로젝트 페이지 있음, 심사 여부 미확인). | https://arxiv.org/abs/2602.19313 , https://www.alphaxiv.org/overview/2602.19313v1 , https://topreward.github.io/webpage/ |
| ProcVLM (2605.08774) "하위 작업 구조 진행도 + 남은 단계 추론" | CONFIRMED-MULTI | 정식 제목: "ProcVLM: Learning Procedure-Grounded Progress Rewards for Robotic Manipulation". 남은 원자 동작을 먼저 추론한 뒤 진행도를 추정한다. ProcCorpus-60M(30개 데이터셋, 40만 궤적)과 20B 토큰으로 **학습한** VLM이다. API 제로샷 모듈이 아니다. "남은 단계를 먼저 추론한다"는 프롬프트 설계만 가져올 수 있다. 기간 안. 신뢰도 LOW~MED (심사·반응 미확인). | https://arxiv.org/abs/2605.08774 , https://arxiv.org/html/2605.08774v1 |
| SARM / SARM2 | CONFIRMED-MULTI | SARM (2509.25358): 단계 인식 보상 모델. **ICLR 2026 게재.** T-shirt 접기에서 83%/67%, 기본 BC는 8%/0%. SARM2 (2606.10305): 여러 작업을 다루는 단계 인식 보상 모델(행동 기본 단위 단계 추정기 + MMoE 가치 헤드). 10개 작업에서 가치 MSE를 80% 줄였다. SARM2는 "일반 VLM 보상 모델은 긴 작업의 세밀한 진행도를 재기에 너무 거칠다"고 명시한다. 둘 다 **학습형**이다. 신뢰도: SARM HIGH (ICLR), SARM2 MED (심사 전). | https://arxiv.org/abs/2509.25358 , https://arxiv.org/abs/2606.10305 , https://qianzhong-chen.github.io/sarm2.github.io/ |
| RARM | CONFIRMED (arXiv + ResearchGate) | "RARM: Confidence-Gated Progress Reward Modeling for RL in Manipulation" (2606.22027). 성공 시연 1개를 기준으로 삼는 비교기다. 로봇 데이터 없이 일반 비디오로 한 번 학습한다. 확신이 있는 전진만 보상해서 오탐을 줄인다. 로컬 모델이 필요하다. 신뢰도 LOW (심사·반응 미확인). | https://arxiv.org/abs/2606.22027 , https://www.researchgate.net/publication/407507354 |
| 2608.13474 | CONFIRMED (arXiv) | "Decoding Task Progress from VLA Representations" (Cornell: Bhardwaj, Duan, Dan, Wei-Chiu Ma, Preston Culbertson, 2026-08-13). 진행도(궤적에서 남은 시간을 정규화한 값)를 VLA 잔차 스트림에서 선형으로 읽을 수 있다. 정체 감지에 쓸 수 있다. **VLA 내부가 필요**하므로 API에는 쓸 수 없다. 신뢰도 MED. | https://arxiv.org/abs/2608.13474 |
| 서베이 2607.21655 | CONFIRMED-MULTI | "Progress Reward Modeling for Robotic Learning: A Comprehensive Survey" (Jianshu Zhang 외, Han Liu 교신, 2026-07-22). 진행 모델을 입출력 인터페이스, 방법, 데이터·벤치마크로 나눠 정리했다. 신뢰도 MED (서베이). | https://arxiv.org/abs/2607.21655 , https://huggingface.co/papers/2607.21655 |
| SAFE (2506.09937) "시간에 따라 달라지는 임계값을 conformal로" | CONFIRMED-MULTI | **NeurIPS 2025 게재** (proceedings에서 확인). 점수는 **VLA 내부 특징**으로 학습한다. 임계값은 functional CP로 정한다. 성공 궤적 점수 분포에서 μ_t + h_t를 만들고, 성공 궤적이 모든 t에서 이 선 아래에 있을 확률을 1−α 이상으로 보장한다. 점수 모델은 쓸 수 없지만 **임계값 방법은 어떤 스칼라 점수에도 붙일 수 있다** (예: Jev 진행 확률). 신뢰도 HIGH. | https://proceedings.neurips.cc/paper_files/paper/2025/file/392d0d05e2f514063e6ce6f8b370834c-Paper-Conference.pdf , https://arxiv.org/abs/2506.09937 |
| FailBench (2609.03611) 0.77 / 접촉 ≤0.60 / 성공 쪽 편향 | CONFIRMED-MULTI (세 수치 모두) | 제목: "FailBench: How Reliable are VLMs at Judging Robot Task Success?". 14개 출처의 시도 2,197개, VLM 판별기 13개를 평가했다. 최고 평균 균형 정확도 0.77. 접촉이 많은 조립 작업에서는 0.60을 넘은 모델이 없다. 애매하면 "성공"으로 치우치고, **추론 노력을 늘려도 편향이 남는다**. 추가 사실: 실패 판별용으로 미세조정한 모델이 범용 VLM과 자기 원본 모델보다 **일관되게 못했다**. 2026-09 제출이라 반응은 아직 알 수 없다. 신뢰도 MED (새 벤치마크). | https://arxiv.org/abs/2609.03611 , https://blog.pebblous.ai/report/robot-vlm-success-judge-ambiguity-bias/en/ |
| Sentinel-VLA (2605.01191, ICML 2026, 60.0 / 46.0 / 30.7) | CONFIRMED-MULTI | ICML 2026 포스터 확인. Piper 팔 실제 3개 작업 평균: Sentinel-VLA 60.0%, PI0 46.0%, OpenVLA 30.7%. 처음 계획할 때와 오류를 감지했을 때만 깊게 추론한다. 다만 감시 모듈은 **VLA 안에서 학습된 모듈**이고, SECL과 OC-Adapter로 계속 학습한다. 호출 방식끼리의 비교(주기 대 이벤트)는 요약에 나오지 않았다. 신뢰도 HIGH (ICML). | https://icml.cc/virtual/2026/poster/61750 , https://arxiv.org/html/2605.01191v1 |
| FPC-VLA (2509.04018) "키프레임에서만 VLM 감독자 호출" | CONFIRMED-MULTI | 감독자는 키프레임에서만 켜지고, 방향과 크기를 담은 자연어 교정을 낸다. 키프레임에서만 켜서 실행 시간 영향이 작다고 한다. 키프레임을 어떻게 정의하는지는 요약에서 확인하지 못했다. 감독자는 학습된다(수작업 라벨 없이). ScienceDirect 저널판도 있다(PII로 보아 Expert Systems with Applications로 추정, 미확인). 신뢰도 MED. | https://arxiv.org/abs/2509.04018 , https://www.sciencedirect.com/science/article/abs/pii/S095741742600655X , https://fpcvla.github.io/ |
| Sentinel (2410.04640) "경과 시간을 주면 제때 끝날지 판단에 도움 → (3)번 근거" | 존재·venue: CONFIRMED-MULTI. "경과 시간" 주장: **UNCONFIRMED** | "Unpacking Failure Modes of Generative Policies: Runtime Monitoring of Consistency and Progress", **CoRL 2024** (PMLR v270), Stanford (Agia 외). STAC(행동 분포의 시간 일관성)와 VLM 진행 감시를 합쳐서, 각각 따로 쓸 때보다 실패를 18% 더 잡았다. 경과 시간 입력 효과는 요약에서 확인하지 못했다. 1.5년 기준보다 오래됐다. 신뢰도 HIGH. | https://proceedings.mlr.press/v270/agia25a.html , https://arxiv.org/abs/2410.04640 , https://sites.google.com/stanford.edu/sentinel |
| STAR (2503.06060) "9프레임 3×3 격자 한 장, 정확도 비슷, 빠르고 쌈" | SINGLE-SOURCE (논문 본문 요약) | Sakib & Yu Sun, 2025-03-08, arXiv에만 있음. 모델은 **GPT-4V**다(오래된 모델). 프레임은 **주기적으로** 뽑았다. 격자와 9장 개별 입력의 정확도가 비슷했고, 격자가 응답 시간과 비용을 줄였다. 기간 경계(2025-03-23) 직전이라 **1.5년 기준을 살짝 벗어난다**. 신뢰도 LOW~MED (심사 미확인, 반응 미확인). | https://arxiv.org/abs/2503.06060 , https://arxiv.org/html/2503.06060 |
| Guardian (2512.01946) "격자는 세부를 잃어 개별 입력 선택. 0.74 → 0.83" | 수치: CONFIRMED (논문 v1 요약). 해석: **부분 WRONG** | Pacaud, Garcia, Shizhe Chen, **Cordelia Schmid** (Inria/ENS Willow). v3 제목은 "Scaling Cross-Environment Failure Reasoning Data for Vision-Language Robotic Manipulation"으로 바뀌었다. 정정할 점: 0.74 → 0.83은 **여러 카메라 시점(multi-view)**을 따로 넣었는지, 격자로 이어 붙였는지의 비교다(실행 정확도 기준, 계획 정확도는 0.82 → 0.84). 시간 순 프레임의 비교가 아니다. 또 모델은 **미세조정한 InternVL3-8B**다. 그래서 STAR(API, 시간 순 프레임)와 "엇갈린다"고 볼 수 없다. 서로 다른 축을 쟀다. OpenReview 제출은 있지만 결과는 미확인. 신뢰도 MED~HIGH (연구실 기준). | https://arxiv.org/html/2512.01946v1 , https://arxiv.org/abs/2512.01946 , https://openreview.net/forum?id=wps46mtC9B , https://www.di.ens.fr/willow/research/guardian/ |
| KITE (2604.07034) | CONFIRMED (arXiv + 프로젝트 페이지) | Hosseinzadeh, Wong, Feras Dayoub, 2026-04-08. **학습 없이** 동작이 두드러진 키프레임을 고르고, 열린 어휘 검출 결과와 조감도(BEV) 배치 그림, 타임스탬프를 붙여 기성 VLM에 넣는다. RoboFAC에서 기본 Qwen2.5-VL보다 크게 좋아졌고, RoboFAC로 미세조정한 모델과 견줄 만했다. 신뢰도 LOW~MED (심사 미확인). | https://arxiv.org/abs/2604.07034 , https://m80hz.github.io/kite/ |
| AHA | UNCONFIRMED (직접 검증 못 함) | 확인된 것은 Guardian 논문의 "AHA는 여러 이미지를 격자 한 장으로 이어 붙인다"는 서술뿐이다. 제목, ID, venue는 검색 예산이 떨어져 확인하지 못했다. | https://arxiv.org/html/2512.01946v1 |
| CoMuRoS (2511.22354) | UNCONFIRMED | 검색 예산이 떨어져 확인하지 못했다. | — |

---

## 2) 더 나은 대안 / 최신 SOTA

### M7 진행 판별: API 제로샷 조건에서 쓸 수 있는 것
기준: 학습이 없어야 하고, API 모델 또는 텍스트 상태에서 동작해야 한다.
- **GVL 방식 프롬프트** (섞은 프레임을 주고 프레임마다 진행 %를 묻는 방식): TOPReward 논문 스스로 "GVL은 GPT-4, Gemini 같은 독점 모델에서 잘 되고 오픈 모델에서는 거의 실패한다"고 보고했다. Gemini-2.5-Pro, OXE에서 GVL 0.541 대 TOPReward 0.433. Astra 같은 **API 모델에는 TOPReward보다 GVL 방식이 맞다**. GVL 원 논문의 venue와 ID는 이번에 확인하지 못했다. OpenGVL 벤치마크(2509.17321)가 있다. https://www.alphaxiv.org/overview/2602.19313v1 , https://arxiv.org/pdf/2509.17321
- **TOPReward**: 쓸 수 있는 경우는 두 가지다. Astra API가 logprob을 주는 경우, 또는 로컬에서 오픈 VLM(Qwen3-VL)을 쓰는 경우. 오픈 VLM에서는 가장 강한 제로샷 결과다(VOC 0.947).
- 진행 추정기를 평가하는 도구: PRM-as-a-Judge 1.5 / RoboPulse++ (2608.14284)는 PRM 신뢰도 벤치마크다. 어느 추정기가 가장 좋은지 순위는 요약에서 확인하지 못했다. https://arxiv.org/abs/2608.14284
- 그 밖에 이름만 확인하고 내용은 확인하지 못한 것: RoboReward (2601.00675), Robometer (2603.02115), RynnValue (2608.09853), Dream2Reward (2608.18787), RoboProcessBench (2606.13040). 모두 학습형 보상 모델이나 벤치마크로 보인다. 제로샷 적합성은 미확인.
- **FailBench가 주는 중요한 시사점**: 실패 판별용으로 미세조정한 모델이 범용 VLM보다 못했다. 우리의 "학습 없이 API로" 방향에 직접 힘을 싣는 증거다. 동시에 접촉 판정은 0.60 이하라서, **접촉과 파지는 VLM이 아니라 센서 술어(그리퍼 폭, 힘)로 판정해야 한다**. https://arxiv.org/abs/2609.03611

### M8 호출 시점과 다중 프레임
- **KITE 방식 증거 구성** (동작이 두드러진 키프레임 + BEV 배치 그림 + 타임스탬프, 학습 없음)이 "균일 10프레임 격자"보다 설계 근거가 낫다. 단, 신뢰도는 LOW~MED다. https://arxiv.org/abs/2604.07034
- 격자 대 개별: 시간 순 프레임을 API 모델에 넣는 비교는 STAR(GPT-4V, 비슷한 정확도) 하나뿐이다. 시점별 이미지를 따로 넣는 쪽이 낫다는 근거는 Guardian(미세조정 8B 모델)이다. 일반 VLM 쪽 문헌은 제목만 찾았다: "More Images, More Problems? A Controlled Analysis of VLM Failure Modes" (2601.07812), "Grid2Matrix: Revealing Digital Agnosia in Vision-Language Models" (2604.09687). 내용은 미확인이다. https://arxiv.org/html/2601.07812 , https://arxiv.org/pdf/2604.09687
- 이벤트 기반 호출: 제목만 확인한 것은 "Plan Along the Way: Event-Triggered Foundation-Model Planning for TAMP Execution in Partially Observable Manipulation" (2608.28075)이다. **주기 호출과 이벤트 호출을 비교했을 수 있어서 최우선으로 원문을 확인해야 한다.** https://arxiv.org/html/2608.28075 . 관련 제목: SkipVLA (2609.20648), CommitFlow (2609.21908), VLA-Corrector (2607.01804). 모두 내용 미확인.

---

## 3) 반대 증거와 위험

1. **VLM 성공 판정 자체가 약하다.** 최고가 0.77이고, 접촉 작업은 거의 우연 수준이며, 애매하면 "성공"으로 치우친다(FailBench). Astra에게 "실패했나?"를 물어 트리거로 쓰면 **실패를 놓치는 쪽**(성공으로 잘못 판정)이 체계적으로 생긴다. 파지 실패가 기본 사례인 우리 과제에서 치명적이다.
2. **v1 M7의 참고 문헌 대부분이 학습형이다** (VLAC, RECAP, ProcVLM, SARM/2, RARM, SAFE의 점수, 2608.13474). 모두 VLA 내부나 로봇 데이터 학습이 필요해서 "LLM 기반은 일반화된다"는 메시지와 충돌한다. 학습 없이 바로 쓸 수 있는 것은 TOPReward(logit 필요)와 GVL 방식뿐이다.
3. **TOPReward와 Jev의 연결은 성립하지 않는다.** Jev는 텍스트만 보므로, Jev의 확률은 상태 인코더(M1)의 품질에 그대로 묶인다. 인코더가 틀리면 진행 확률도 틀린다.
4. SARM2 저자는 "일반 VLM 보상 모델은 긴 작업의 세밀한 진행도에 너무 거칠다"고 했다. 제로샷 VLM 진행도를 촘촘한 진행 신호로 쓰는 것에 대한 반대 증거다.
5. 격자 입력의 근거(STAR)는 GPT-4V 시절의 단일 논문이고, 심사도 반응도 확인되지 않았다(LOW~MED). 개별 입력의 근거(Guardian)는 multi-view이고 미세조정 모델이다. **어느 쪽도 우리 조건(최신 API 모델, 시간 순 실패 영상)에 바로 옮길 수 없다.**
6. Sentinel-VLA와 FPC-VLA의 "필요할 때만 호출"은 호출 방식끼리의 통제된 비교가 아니다. 학습된 감시기를 쓴 전체 시스템의 성능이다. 그래서 (1) 주기, (2) 정한 순간, (3) 시간 초과의 우열에 대한 증거가 되지 못한다.
7. Sentinel(2410.04640)의 "경과 시간 입력이 도움이 된다"는 이번에 확인하지 못했다. 확인 전에는 (3)번 방식의 근거로 쓰지 않는다.

---

## 4) 이 모듈에 장착할 모듈 후보 순위

### M7 진행 판별
| 순위 | 후보 | 이유 | 신뢰도 근거 |
|---|---|---|---|
| 1 | **센서·술어 기반 완료 판정 + "남은 시간" 정의** (RECAP의 "진행도 = 완료까지 남은 스텝"을 개념으로만 가져온다) | 접촉과 파지는 VLM이 약하다(FailBench ≤0.60). 술어와 그리퍼 센서가 가장 믿을 만하다. 남은 시간 정의는 M2의 예상 소요 시간과 바로 이어진다. | RECAP: PI, HIGH. FailBench: MED |
| 2 | **SAFE의 functional conformal 시간 가변 임계값** (점수 모델은 쓰지 않는다. Jev 진행 확률이나 술어 점수에 붙인다) | 학습 없이 성공 궤적 몇 개로 보정할 수 있다. 오경보율을 α로 조절한다. | NeurIPS 2025, HIGH |
| 3 | **GVL 방식 제로샷 진행 추정 (Astra 또는 API VLM)**: 드물게 검증할 때용 | API 독점 모델에서 TOPReward보다 나았다(Gemini 0.541 대 0.433). 느리므로 촘촘한 신호가 아니라 확인용이다. | TOPReward 논문 보고. GVL 원 논문 venue 미확인 → MED |
| 4 | **TOPReward** (logprob을 주는 API 또는 로컬 오픈 VLM일 때만) | 오픈 VLM 제로샷 최고 수준(VOC 0.947). chat template이 있으면 성능이 떨어진다. | MED (심사 미확인) |
| 제외 | VLAC, ProcVLM, SARM/SARM2, RARM, 2608.13474 | 학습형이거나 VLA 내부가 필요하다. 일반화 메시지와 충돌한다. VLAC(공개 가중치)는 **비교용 기준 방법**으로만 고려한다. RARM과 ProcVLM은 신뢰도 LOW~MED라 추천하지 않는다. | — |

### M8 호출 시점과 다중 프레임
| 순위 | 후보 | 이유 | 신뢰도 근거 |
|---|---|---|---|
| 1 | **이벤트 호출 (M7이 실패나 정체로 판정하거나, 예상 시간을 넘겼을 때)** | Sentinel-VLA와 FPC-VLA 모두 "필요할 때만" 호출로 성능을 유지했다. 단, 방식끼리의 통제 비교는 아니다. | Sentinel-VLA ICML 2026 HIGH, FPC-VLA MED |
| 2 | **STAC식 일관성 신호 + 진행 감시의 결합** (Sentinel): 이상 트리거 입력으로 쓴다 | 두 감지기를 합치면 실패를 18% 더 잡았다. Jev 겹침 불일치(M4)가 STAC 역할을 할 수 있다. | CoRL 2024 HIGH (기간 밖, 개념만) |
| 3 | **키프레임 선택 + 구조화 증거 (KITE)** 를 균일 격자 대신 쓴다 | 학습 없이 기성 VLM의 실패 분석을 개선했다. | LOW~MED → 원문 확인 전에는 보조로만 |
| 4 | 격자 대 개별 이미지: **실험 항목으로 유지** (현 증거로는 결론을 낼 수 없다) | STAR(LOW~MED, 시간 순 프레임, API)와 Guardian(multi-view, 미세조정)이 서로 다른 축을 쟀다. | — |

---

## 5) 확인 못 한 것
- CoMuRoS (2511.22354): 존재, 내용, venue 모두 미확인.
- AHA: 제목, ID, venue 미확인. Guardian을 통해 "격자로 이어 붙이는 방식"이라는 것만 확인했다.
- Sentinel(2410.04640)의 "경과 시간 입력 효과".
- FPC-VLA의 키프레임 정의. 저널 이름.
- 주기 / 이벤트 / 시간 초과 호출의 정량 비교: 로봇, 고전 event-triggered control, LLM 에이전트 모두 검색하지 못했다(예산 소진). 후보로 2608.28075 원문을 먼저 확인해야 한다.
- 일반 VLM 분야의 격자 대 개별 프레임 대 비디오 비교: 2601.07812와 2604.09687은 제목만 확인했다.
- GVL 원 논문의 ID와 venue. 최신 API 모델에서의 성능.
- Astra API가 logprob을 주는지 (TOPReward를 쓸 수 있는지 여부).
- 모든 항목의 인용 수, HF 추천 수, GitHub 스타. 저자 블로그와 발표.
- VLAC, Guardian, TOPReward의 최종 심사 결과.
