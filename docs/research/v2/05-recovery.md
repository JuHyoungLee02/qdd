# M9 실패 복구: v1 계획 감사 보고서 (v2)

- 작성일: 2026-09-23
- 범위: `docs/plan.md`의 M9(실패 복구)와, M9에서 가져다 쓰는 M2와 M8의 인용
- 시간 창: 2025-03-23 이후 (1.5년)
- 검증 방법: WebSearch 검색 요약만 사용했다. arXiv 직접 접근은 프록시가 막았다(`EGRESS_BLOCKED`).
- **중요한 한계**: 이 세션에서 검색 예산(세션 전체 200회)이 조사 도중에 바닥났다. 그래서 LLM/VLM 쪽 문헌 조사와 일부 venue·인용 수 확인을 끝내지 못했다. 끝내지 못한 항목은 5절에 모두 적었다.

---

## 1) 검증 표

확인 수준 기준:
- CONFIRMED-MULTI: 서로 다른 출처 두 곳 이상이 일치한다.
- SINGLE-SOURCE: arXiv 초록 또는 그 미러 한 곳에서만 확인했다.
- UNCONFIRMED: 확인하지 못했다.
- WRONG: 틀렸다. 정정 내용을 함께 적었다.

신뢰도 기준 (사용자 CREDIBILITY RULE):
- HIGH: 동료 심사 학회 채택이 확인됐거나, 잘 알려진 연구실의 논문이다.
- MED: arXiv에만 있지만 저명한 연구실이나 저자의 논문이다.
- LOW: arXiv에만 있고 저자가 덜 알려졌으며, 반응(traction)도 확인되지 않았다.

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| **B2FF** (2606.09258) "Back to the Familiar Future: Failure Recovery for VLA Policies via Pre-Imagined Milestone Selection" | CONFIRMED-MULTI (존재, 56.3→74.0) | 수치는 맞다. 다만 v1이 빠뜨린 조건이 셋 있다. (1) 결과는 "**복구 시점을 주입한 실패에 맞춘(controlled recovery timing aligned with the injected failure)**" 조건에서 나왔다. 사실상 실패 시점을 오라클로 준 셈이다. (2) 이정표는 **미래 이미지를 생성하는 foresight VLA(UD-VLA)**가 만든 시각 목표다. 텍스트 술어가 아니다. (3) 실로봇 결과는 90회 시행에서 전체 61.1%였고, 선택기를 가볍게 튜닝해야 했다. 표준 LIBERO에서는 91.3→93.7이었다. 저자, 소속, venue는 확인하지 못했다. **신뢰도 LOW** | https://arxiv.org/abs/2606.09258 , https://arxiv.org/html/2606.09258 , https://awesomepapers.io/robotics/papers/2606.09258 |
| **FailSafe** (2510.01642) "FailSafe: Reasoning and Recovery from Failures in Vision-Language-Action Models" | CONFIRMED-MULTI | "최대 +22.6%"는 정확히는 "Pi-0-FAST, OpenVLA, OpenVLA-OFT **세 VLA의 평균** 향상이 최대 22.6%"이고, **ManiSkill 시뮬레이터**에서 나온 수치다. 학습 대상은 VLA가 아니라 **LLaVA-OV-7B를 미세조정한 FailSafe-VLM**이다. 외부 VLM이 복구 행동을 내는 구조라서 우리 구조(Astra가 개입)와 형태가 가깝다. 저자는 Lin, Duan, Fang, D. Fox, R. Krishna, C. Tan, B. Wen이고 소속은 NTU, A*STAR CFAR, AI2, UW다. 학회 채택은 확인하지 못했다. **신뢰도 MED** | https://arxiv.org/abs/2510.01642 , https://www.semanticscholar.org/paper/af31bfbeb448afdd18af3a74da765ca75cfbb91c , https://paperswithcode.co/paper/2510.01642 |
| **Sentinel-VLA** (2605.01191) "Sentinel-VLA: A Metacognitive VLA Model with Active Status Monitoring for Dynamic Reasoning and Error Recovery" | CONFIRMED-MULTI | ICML 2026 포스터로 확인했다. "π0 대비 30% 이상"은 **실세계 실험**의 과업 성공률이다. EC-Gen은 오류 복구 궤적 **2.6M+ transition**을 합성한다. 여기에 Orthogonal Continual Adapter 기반의 지속 학습을 더했다. VLA 전체를 학습하는 방법이라 우리 구조에 그대로 쓸 수 없다. **신뢰도 HIGH (venue 확인)** | https://arxiv.org/abs/2605.01191 , https://icml.cc/virtual/2026/poster/61750 |
| **FAR** (2607.01111) "FAR: Failure-Aware Retry for Test-Time Recovery and Continual Policy Improvement" | CONFIRMED-MULTI (수치) / **부분 WRONG (설명)** | v1은 "재시도 + 동작 섭동"이라고 적었다. 정정: 핵심은 **Failure-Contrastive Preference Adaptation**이다. 가치 추정으로 실패를 일으킨 행동을 찾고, 실패 예시와 대안 양성 예시로 **테스트 시간에 정책을 업데이트**한다. 가벼운 동작 섭동은 그 위에 더한 보조 장치다. 성공한 복구 궤적은 지속 학습에도 쓴다. **학습이 필요 없는 방법이 아니다.** 결과는 diffusion policy 대비 시뮬레이션 +17.6%, 실세계 +11.7%다. 실험은 시뮬레이션 3개 벤치마크의 9개 작업과 xArm 실세계 3개 작업이다. 저자는 Hao, Syed, Ichnowski, Schneider(CMU)이고, 2026-07-01에 공개됐다. **신뢰도 MED** | https://arxiv.org/abs/2607.01111 , https://semanticscholar.org/paper/89a0613a49517c552450cdb1fe68261badd14faa |
| **STAR** (2503.06060) "STAR: A Foundation Model-driven Framework for Robust Task Planning and Failure Recovery in Robotic Systems" | CONFIRMED-MULTI | **시간 창 밖이다.** 2025-03-08에 공개돼 기준일 2025-03-23보다 15일 이르다. 3×3 격자 결과("정확도는 비슷, 응답 시간과 비용 개선")는 맞다. 복구 성공률은 78%이고, 실패가 나면 "재실행으로 풀지, 계획을 바꿀지"를 판정한다. venue는 확인하지 못했다. **신뢰도 LOW** | https://arxiv.org/html/2503.06060 , https://awesomepapers.io/robotics/papers/2503.06060 |
| **Guardian** (2512.01946) | CONFIRMED-MULTI | **제목이 바뀌었다.** v1 제목은 "Guardian: Detecting Robotic Planning and Execution Errors with VLMs"였다. PDF 제목은 "Guardian: Detecting Robotic Manipulation Failures with VLMs"이고, v3 제목은 "Scaling Cross-Environment Failure Reasoning Data for Vision-Language Robotic Manipulation"이다. 저자는 Pacaud, Garcia, S. Chen, C. Schmid(Inria/ENS)이고 데이터셋은 GuardianFail-36k다. **실패 감지** 논문이지 복구 논문이 아니다. **신뢰도 MED** (Schmid 연구실, venue 미확인) | https://arxiv.org/abs/2512.01946 , https://arxiv.org/html/2512.01946v3 |
| **ReCoVLA** (2606.09630) "ReCoVLA: VLM-Guided Reward Compilation for Failure Recovery in VLA Policies" | CONFIRMED-MULTI (존재, 방법) | VLA를 고정한 채 외부 VLM이 실패 유형과 복구 단계를 추론한다. 그 결과로 보상 마스크를 고르고, **시뮬레이터에서 residual RL 정책을 학습**한 뒤 zero-shot으로 sim-to-real 배포한다. 학습이 필요하다. 소속은 USC, MERL, Harvard이고 공개일은 2026-06-08이다. 정량 수치는 확인하지 못했다("baseline을 평균적으로 앞선다"는 문장만 확인). **신뢰도 MED-LOW** | https://arxiv.org/abs/2606.09630 |
| **RePO-VLA** (2605.09410) | CONFIRMED-MULTI (존재, 방법) | 성공, 복구, 실패 궤적에 서로 다른 역할을 준다. 방법은 RAI와 VCR 두 단계이고, PAS-VF 가치 함수를 쓰며, 추론할 때 v=1.0으로 조건을 건다. VLA를 학습하는 방법이다. 공개일은 2026-05-10이고 수치는 확인하지 못했다. **신뢰도 LOW** | https://arxiv.org/abs/2605.09410 |
| **DreamAvoid** (2605.11750) | CONFIRMED-MULTI (존재, 방법) | 복구가 아니라 **실패 회피**다. 위험 구간에서 VLA 후보 행동 청크 여러 개를 학습된 Dream Evaluator로 미리 상상해 보고 고른다. 평가기 학습이 필요하다. 공개일은 2026-05-12이고 수치는 확인하지 못했다. **신뢰도 LOW** | https://arxiv.org/abs/2605.11750 |
| **FLARE** (2608.26645) "FLARE: A Failure-Aware Framework for Autonomous Correction and Recovery in Visual-Language Robotic Manipulation" | CONFIRMED-MULTI | **CVPR 2026 채택을 확인했다** (CVF open access에 논문이 있다). 실패를 "로봇 자세 오류(ID)"와 "환경 파괴(OOD)"로 나눈다. **Retry**는 섭동과 bridging 데이터 증강으로 VLA를 학습시킨다. **Reset**은 MLLM이 실패 영상을 오프라인으로 분석해서 물체 수준의 reset 스킬을 배우게 한다. 실행 중에는 **온라인 MLLM 모니터가 retry와 reset을 오간다.** 저자는 G. Zhao, …, Guanbin Li다. 수치는 확인하지 못했다. **신뢰도 HIGH (venue 확인)** | https://arxiv.org/abs/2608.26645 , https://openaccess.thecvf.com/content/CVPR2026/papers/Zhao_FLARE_A_Failure-Aware_Framework_for_Autonomous_Correction_and_Recovery_in_CVPR_2026_paper.pdf , https://en.papernotes.org/CVPR2026/robotics/flare_a_failure-aware_framework_for_autonomous_correction_and_recovery_in_visual/ |
| **Imagining Recovery / CoRe** (2608.14822) | CONFIRMED-MULTI (존재, 수치 문구) | **학습 없이** 고정된 VLA를 복구한다. 최근의 괜찮았던 상태에서 정책이 어떻게 이어갔을지를 합성 관측으로 상상한다. 그런 다음 로봇과 **장면**을 최소한으로 재정렬한다. 수치는 "**최대** +85.0%p, 물리적 복원 42.2% 감소"로, 최대값이지 평균이 아니다. 장면 재정렬을 누가 어떻게 하는지는 확인하지 못했다. 저자는 Yanyan Zhang 외(Case Western Reserve)이고 공개일은 2026-08-14다. **신뢰도 LOW** | https://arxiv.org/abs/2608.14822 , https://www.alphaxiv.org/@yanyan-zhang |
| **AHA** "AHA: A Vision-Language-Model for Detecting and Reasoning Over Failures in Robotic Manipulation" | CONFIRMED-MULTI | ICLR 2025, NVIDIA/UW, NVlabs에서 코드 공개. **arXiv 첫 공개가 2024년이라 시간 창 밖이다**(venue인 ICLR 2025는 창 안). arXiv ID는 이 세션에서 확인하지 못했다. 실패 **감지와 설명**용이다. GPT-4o ICL보다 10.3% 높았고, LLM/VLM 기반 프레임워크 세 개에 붙였을 때 평균 +21.4%였다. **신뢰도 HIGH** | https://iclr.cc/virtual/2025/poster/30106 , https://github.com/NVlabs/AHA (검색 결과로만 확인했고 직접 접근하지 않음) |
| **RACER** (2409.14674) | CONFIRMED-MULTI | ICRA 2025, sled-group(UMich). **arXiv가 2024-09라 시간 창 밖이다.** VLM 감독자가 풍부한 언어 지시를 주고, 언어 조건 정책이 행동한다. 정책 학습이 필요하다(RLBench, RVT 대비). **신뢰도 HIGH** | https://arxiv.org/abs/2409.14674 , https://ieeexplore.ieee.org/iel8/11127273/11127223/11127799.pdf |
| v1 주장: "기법 간 공통 벤치마크 비교가 없다" | 대체로 맞다. 단, 갱신이 필요하다 | **LIBERO-RECOVER (2609.05178, 2026-09-04)**가 새로 나왔다. 복구 시나리오 2178개, 하위 작업 130개, 복구 난이도 4단계(L1–L4), 평가 차원 16개로 이뤄졌다. 다만 평가한 대상은 **기본 VLA**(π0, π0-FAST, GR00T N1.5, OpenVLA-OFT)다. 모든 모델이 50% 넘게 떨어졌다. 예를 들어 LIBERO-Spatial에서 π0는 L1 40.0%에서 L4 6.7%로, OFT는 40.0%에서 9.3%로 떨어졌다. B2FF, FailSafe, FAR 같은 **복구 기법끼리의 직접 비교는 이 벤치마크에서도 확인되지 않았다.** B2FF의 "failure-injected LIBERO"는 B2FF가 직접 만든 설정이다. RoboFail은 확인하지 못했다. | https://arxiv.org/abs/2609.05178 , https://arxiv.org/html/2609.05178 |

M2에서 B2FF를 인용한 부분(`plan.md` 64행)도 같은 한계를 가진다. B2FF의 이정표는 텍스트 술어가 아니라 생성된 **이미지**다.

---

## 2) 더 나은 대안/최신 SOTA

**결론: 복구 기법끼리 같은 벤치마크에서 직접 비교한 결과가 없다. 그래서 "가장 좋은 방법"은 수치로 정할 수 없다.** 각 논문은 자기 기준 모델과 자기 실패 주입 방식으로만 평가했다. 예를 들어 B2FF는 UD-VLA와 자체 주입 실패로, FailSafe는 ManiSkill에서 세 VLA로, FAR는 diffusion policy로 평가했다. 따라서 "56.3→74.0"과 "+22.6%"와 "+85%p(최대)"는 서로 비교할 수 없다.

조사 중 새로 찾은 관련 항목:

| 항목 | 성격 | 학습 필요 | 비고 / 신뢰도 | 출처 |
|---|---|---|---|---|
| FLARE (CVPR 2026) | Retry/Reset 두 갈래 + 온라인 MLLM 모니터 | Retry 쪽은 VLA 학습이 필요하다. Reset 스킬 발굴과 모니터는 MLLM이 맡는다 | 실패를 ID(자세 오류)와 OOD(환경 파괴)로 나누는 분류가 v1의 "재시도 → 되돌리기 → 재계획" 사다리와 가장 가깝고, 동료 심사를 거친 근거다. **HIGH** | 위 표 |
| LIBERO-RECOVER (2609.05178) | 복구 벤치마크 | – | 앞으로 복구 기법을 비교할 공통 기준이 될 수 있다. 나온 지 3주 된 arXiv 논문이고 저자와 반응은 확인하지 못했다. **LOW (현재)** | https://arxiv.org/abs/2609.05178 |
| ProbeAct (2606.09740) | 학습 없는 런타임 개입 (hidden-state probe + 운동학 상태 기계 + CBF 필터) | VLA 가중치는 그대로 두지만 probe를 학습한다 | LIBERO-plus에서 OFT 69.6→74.1로 향상폭이 작다. VLA 내부 특징이 필요해서 Jev/Astra 구조에는 맞지 않는다. **LOW** | https://arxiv.org/abs/2606.09740 |
| VLA-Corrector (2609.06508) | 단계(approach/align/grasp/transport/place)를 아는 검증기 + 복구 프롬프트 | 검증기를 학습한다 | "접근–정렬–잡기–운반–놓기" 단계별 실패 패턴은 M7/M9의 술어 설계에 참고할 수 있다. **LOW** | https://arxiv.org/abs/2609.06508 |
| Causal-History Test-Time Scaling for Failure Recovery in Autoregressive World-Action Models (2609.18016) | 존재만 확인 | 확인 못 함 | 내용은 확인하지 못했다 | https://arxiv.org/pdf/2609.18016 (검색 목록) |
| REVOLVE (2609.14633), Fail-RAG (2606.19598), Foresight (2606.23085), VLA-FAIL (2606.21386), "Learning Actionable Manipulation Recovery via Counterfactual Failure Synthesis" (2603.13528), "Deployment-Time Reliability of Learned Robot Policies" (2603.11400, 서베이로 보임) | 검색 목록에서 존재만 확인 | – | 내용, 수치, 신뢰도 모두 확인하지 못했다. 추천하지 않는다 | 각 arXiv 링크 |

**학습 없는 방법과 VLA 학습이 필요한 방법의 구분** (우리 구조, 즉 API LLM + 스킬 기반과 맞는지 기준):

- **학습 없음 / API LLM과 맞음**
  - STAR: 창 밖이고 신뢰도 LOW.
  - FLARE의 MLLM 모니터와 reset 스킬 전환 부분.
  - AHA식 실패 설명 형식: 모델은 학습됐지만 **출력 형식**만 가져다 쓸 수 있다.
- **학습 없음이지만 VLA 전용이라 우리 구조에 옮기기 어려움**
  - B2FF: foresight VLA의 이미지 목표에 의존한다.
  - CoRe: VLA 정책의 이어갈 경로를 상상한다.
  - ProbeAct: VLA hidden state가 필요하다.
- **학습 필요**
  - FailSafe: VLM 미세조정.
  - Sentinel-VLA: VLA와 EC-Gen 데이터.
  - FAR: 테스트 시간 선호 업데이트.
  - ReCoVLA: residual RL.
  - RePO-VLA, DreamAvoid, RACER.
  - FLARE Retry: 데이터 증강으로 VLA를 학습한다.

**LLM/VLM 쪽 문헌**: 사용자 규칙에 따르면 여기도 조사해야 한다. 그러나 검색 예산이 바닥나 이 세션에서는 **한 건도 검증하지 못했다**. 에이전트의 backtracking, self-reflection, 체크포인트 복원 같은 계열이 후보다. 이 계열은 이름만 알 뿐 날짜, venue, 수치를 확인하지 못했으므로 여기에 적지 않는다(5절 참조).

---

## 3) 반대 증거와 위험

1. **B2FF를 v1 사다리의 2단계 근거로 쓰기 어렵다.**
   - 신뢰도: 저자, 소속, venue가 확인되지 않아 LOW다. 사용자 규칙상 추천 근거로 쓰면 안 된다.
   - 조건: 복구 시점을 실패에 맞춰 준 **통제된 조건**의 결과다. 실제 감지기가 늦거나 틀리면 얼마나 떨어지는지는 보고되지 않았다(확인 범위 안에서).
   - 이정표 형태: 이정표는 **생성된 미래 이미지**다. Jev는 텍스트만 받으므로 "Astra가 텍스트 이정표를 주면 같은 효과가 난다"는 가정은 검증된 적이 없다.
2. **v1은 FAR를 "학습 없는 재시도 + 섭동"처럼 요약했지만 틀렸다.** FAR의 핵심은 테스트 시간에 정책을 업데이트하는 것이다. 섭동만 떼어 낸 효과(ablation)는 확인하지 못했다. 따라서 "Jev가 약간 바꾼 동작으로 재시도하면 된다"는 1단계에는 FAR가 직접 근거가 되지 못한다.
3. **LIBERO-RECOVER에 따르면 최신 VLA 모두 자연 발생 실패에서 50% 넘게 떨어진다.** 복구가 필요하다는 근거로는 강하다(프로젝트 핵심 메시지와도 맞는다). 그러나 이것은 VLA 쪽 증거일 뿐이다. LLM 기반 복구가 더 낫다는 증거는 아니다. OFT를 복구 데이터와 섞어 학습하면 복구율이 20.8→25.4로 조금 오르고 표준 LIBERO 성공률은 약간 떨어졌다. 학습만으로는 한계가 있다는 신호로 읽을 수 있다.
4. **감지가 병목이다.** 복구는 감지가 맞아야 작동한다. v1 M7이 인용한 FailBench(2609.03611)는 VLM 판별기 최고 성능이 균형 정확도 0.77이라고 보고했다. 이 수치는 M7 담당 영역이라 여기서 재검증하지 않았다. B2FF와 FLARE처럼 감지를 통제하거나 모니터를 따로 두는 논문의 수치는 이 오차를 반영하지 않을 수 있다.
5. **"최대(up to)" 수치를 조심해야 한다.** FailSafe의 22.6%는 여러 설정 중 최댓값의 평균이다. CoRe의 85.0%p는 최댓값이다. 평균 성능이 아니다.
6. **시간 창 문제.** STAR, AHA, RACER는 arXiv 첫 공개가 창 밖이다. v1의 M8은 STAR를 핵심 근거로 쓰고 있다.

---

## 4) 이 모듈에 장착할 모듈 후보 순위

기준은 네 가지다: (a) 신뢰도, (b) API LLM(Astra)과 텍스트 전용 Jev 구조에 학습 없이 쓸 수 있는가, (c) 스킬 기반 파지와 맞는가, (d) 일반화 메시지와 충돌하지 않는가. LOW 신뢰도 항목은 순위에서 뺐다.

1. **FLARE의 Retry/Reset 이원 구조 + 온라인 MLLM 모니터** (CVPR 2026, 신뢰도 HIGH)
   - 실패를 "자세 오류 → 재시도"와 "환경 파괴 → reset 스킬"로 나누고, MLLM이 둘 사이를 오간다. 우리 구조에서는 Astra가 모니터이고 reset은 파라미터 스킬이다.
   - VLA 학습이 필요한 부분(섭동 데이터 증강)은 빼고, 분류와 전환 구조만 쓴다.
   - 주의: 수치를 확인하지 못했다. 전환 구조만 따로 떼어 낸 효과도 확인하지 못했다.
2. **FailSafe의 "실패 → 실행 가능한 복구 행동" 출력 형식과 실패 생성 파이프라인** (Fox, Krishna, Wen / UW, AI2, NTU, 신뢰도 MED)
   - 외부 VLM이 VLA를 대신해 복구 행동을 내는 구조가 Astra의 개입과 같다.
   - 쓰는 방법 두 가지: (i) 복구 행동 형식을 Astra 출력 스키마로 참고한다. (ii) 모션 플래너가 있는 시뮬레이터에서 실패 사례를 자동 생성하는 방식을 **평가용 실패 주입**에 쓴다.
   - 미세조정된 VLM 자체는 API 구조와 맞지 않는다.
3. **AHA식 실패 감지와 설명 형식** (ICLR 2025, NVlabs, 신뢰도 HIGH, 단 arXiv가 창 밖)
   - 실패를 자유 형식 언어로 설명하게 한다. 그 설명을 LLM 기반 프레임워크에 넣었더니 과업 성공률이 평균 +21.4%였다. Astra 재계획의 입력으로 쓸 근거다.
   - 창 밖이므로 사용자가 허용하면 쓴다.
4. **Sentinel-VLA의 "필요할 때만 깊게 추론" 트리거** (ICML 2026, 신뢰도 HIGH)
   - 복구 자체보다 M8(호출 시점)에 맞는 근거다.
   - 복구 성능(+30%)은 EC-Gen으로 VLA를 학습해서 얻은 것이라 그대로 가져올 수 없다.
5. **FAR** (CMU, 신뢰도 MED)
   - 쓸 수 있는 것은 "실패를 일으킨 행동을 찾고 그 주변을 피해서 재시도한다"는 **개념**뿐이다.
   - 실제 방법은 정책을 업데이트하므로 학습 없는 1단계의 근거로 쓰면 안 된다.

**순위에서 뺀 것**:
- 신뢰도 LOW: B2FF, CoRe(Imagining Recovery), ProbeAct, DreamAvoid, RePO-VLA, VLA-Corrector.
- 창 밖이고 신뢰도 LOW: STAR.
- ReCoVLA: MERL 소속이지만 residual RL 학습이 필요하고 수치를 확인하지 못했다.
- v1 사다리의 2단계("B2FF 방식")는 근거를 **FLARE의 reset 갈래**로 바꾸는 것이 신뢰도 면에서 낫다. 이것은 제안이므로 사용자 결정 전에는 `plan.md`에 넣지 않는다.

---

## 5) 확인 못 한 것

- **LLM/VLM 쪽 복구 문헌 전체**: 에이전트의 backtracking, 롤백, self-reflection, 트리 탐색 기반 복구 등. 검색 예산이 바닥나 한 건도 검증하지 못했다. 사용자 규칙("로봇 분야에 답이 있다고 가정하지 말 것")을 따르려면 검색 예산을 늘려 다시 조사해야 한다.
- B2FF의 저자, 소속, venue, HF upvote, GitHub 스타. 감지가 부정확할 때의 성능.
- FailSafe의 학회 채택 여부.
- FLARE의 정량 수치.
- ReCoVLA, RePO-VLA, DreamAvoid의 수치.
- CoRe의 장면 재정렬 방식(사람이 개입하는지).
- LIBERO-RECOVER의 저자와 venue. 복구 기법(B2FF 등)을 이 벤치마크로 평가했는지.
- RoboFail 벤치마크의 존재와 내용.
- 2609.18016(Causal-History TTS)의 내용.
- AHA의 arXiv ID와 첫 공개일 정확값.
- 모든 항목의 인용 수, HF Papers upvote, GitHub 스타 수. 저장소 접근이 금지돼 있고 검색 예산도 바닥났다.
- 작성자 블로그, 발표, X 스레드에서 저자가 직접 말한 한계. 검색 요약에서는 찾지 못했다.
