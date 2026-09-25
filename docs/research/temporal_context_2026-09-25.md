# 시간 맥락(이력·속도·이전 행동)과 데이터 규모 — 문헌 조사 (2026-09-25)

작성: 문헌 조사 에이전트, 2026-09-25. 사용자 규칙 user-log 70(성능이 낮으면 비슷한 최근 논문이 그 성능을 어떻게 올렸는지 찾아 적용) 적용.
출발점: `docs/stage3/results/se2e_diag.md` — 결정 정확도 약 0.72, 오답은 거의 "움직이냐 마냐·크기 한 칸"(방향 부호 반대 8/155), train≈val, 라벨 모호성 상한 약 0.93, 결정 프롬프트는 **단일 시점**(머리 + 활성 손목 이미지, 그리퍼 열림/닫힘·팔 텍스트, 속도·과거 프레임 없음). 1k 표본(8 에폭) 0.56 → 37k(1 에폭) 0.72.

규칙: (1) 1.5년 규칙 — 대략 2025-03 이후 발표분만. (2) 신뢰도 규칙 — 상위 학회 채택(arXiv Comments·OpenReview로 확인) 또는 대형 연구실 + 별 많은 저장소. 확인 못 한 것·기준 미달은 7절에 **제외 사유와 함께** 적었다. 숫자는 논문 본문·표에서 옮겼고, 그림에서 읽은 근사값은 "≈"로 표시했다. 별 수는 2026-09-25 GitHub API 값.

## 1. 요약 (먼저 해볼 것 3개)

| 순위 | 무엇 | 기대 이득 | 구현 비용 | 지연 비용(결정 호출) | 프롬프트 해시 |
|---|---|---|---|---|---|
| 1 | **과거 프레임 1장을 Qwen3-VL "2프레임 비디오"로**: 카메라마다 [t−Δ, t] (Δ = 0.3 s = 10 Hz 3스텝 ≈ 결정 주기) | 높음(가설) — 오답 유형(움직임 유무·크기)에 직접. VLA 이력 입력의 이득은 MEM·HAMLET·MemoryVLA·RoboMME에서 반복 확인 | 중 — 스냅샷·직렬화·런타임 프레임 버퍼 | **LLM 토큰 거의 0 증가**(정지 이미지도 이미 2프레임으로 복제되어 인코딩됨, 2.4절) + 타임스탬프 텍스트 수 토큰 | **바뀜**(카메라 배치·serializer 새 판) |
| 2 | **움직임 텍스트 한 줄**(행 `proprio.qd`·`grip` 속도에서 거친 구간: 정지/느림/빠름 + 주 이동 방향) + **학습 때 줄 드롭아웃** | 중 — 정상 운동 구간은 쉽게 고치나, 전환 시점에서 고유감각 지배로 오히려 나빠질 위험(GAP, ICLR 2026) | 낮음 | 약 10–20 토큰 | **바뀜**(serializer 새 판) |
| 3 | **데이터: 표본 수가 아니라 에피소드·장면 다양성으로 늘리고, 학습 곡선 3–4점을 먼저 잰다** + 2 에폭째를 lr 감쇠까지 포함해 재기 | 중 — 2점 외삽으로 10배에 ≈0.78(거친 추정). Data Scaling Laws(ICLR 2025 Oral)·π0.5(CoRL 2025 Oral): 다양성 > 같은 환경 반복 | 낮음(학습 옵션만) | 없음 | **안 바뀜**(`stageb_train.py`는 해시 대상 밖) |

- 1·2는 **한 사전 등록에서 같은 데이터로 2×2 격자**(없음 / 비디오 / 속도줄 / 둘 다)로 재는 것을 권한다. 지표는 전체 dec_acc와 함께 **전환 층**(다음 0.33 s 안에 라벨이 바뀌는 스냅샷, `harvest/sim/snapshot.boundary_flags`와 같은 정의) 정확도를 따로 본다 — GAP·PTP가 보고한 실패가 바로 이 층에서 나타난다.
- 무엇을 "안" 할지: 긴 기억(분 단위 메모리 뱅크, MemER·MemoryVLA 방식)은 우리 오답(0.3 s 단위 움직임 판단)에 맞지 않고 비용이 크다(RoboMME에서 MemER ≈ 5× 연산). 결정 호출 입력에 **이전 행동(청크) 자체를 넣는 것**은 복사(copycat) 위험이 가장 커서 뒤로 미룬다(3절).

## 2. 근거 — 출처별

### 2.1 다중 프레임·이력 이미지 입력 (VLA)

| 출처 | 한 일 | 측정 이득(정확한 수·조건) | 우리와의 관련 | 신뢰도 근거 |
|---|---|---|---|---|
| **MEM: Multi-Scale Embodied Memory for VLA** (Torne, Pertsch, Walke 외, Physical Intelligence; arXiv 2603.03596, 2026-03) | ViT에 공간 주의(프레임 내)와 인과-시간 주의(프레임 간)를 번갈아 넣은 비디오 인코더. 사전학습 6프레임(과거 5 + 현재, 1 s 간격), 후학습 최대 18프레임(54 s). **과거 프레임의 패치 표현은 인코더 뒤에서 버려 LLM 토큰 수가 단일 프레임과 같다.** 새 학습 파라미터 없음(고정 사인 시간 위치 부호). 장기 기억은 언어 요약 | π0.6 대비(그림 읽음): 레시피 준비 ≈70% vs 기억 없음 ≈15%, 주방 정리 ≈65% vs ≈10%; 맥락 내 적응: 젓가락 집기 ≈80% vs ≈40%, 냉장고 열기 ≈75% vs ≈30%. H100·카메라 4대에서 실시간 지연 유지(RTC와 함께) | **가장 가까운 설계 선례**: 토큰 수 불변으로 짧은 시간 맥락을 VLM에 넣는 법. 저자들이 "기억 추가가 인과 혼동으로 성능을 떨어뜨린다는 선행 보고"를 직접 언급하고, 다양한 사전학습 데이터(최적성·속도·제어 주파수가 제각각)를 견고성 이유로 든다 | 대형 연구실(PI) 공식 연구 페이지 pi.website/research/memory. 학회 채택은 확인 못 함(프리프린트). openpi 저장소 별 13,994(MEM 코드 포함 여부는 확인 못 함) |
| **HAMLET: Switch your VLA into a History-Aware Policy** (Koo 외, KAIST 계열; **ICLR 2026**; arXiv 2510.00695) | 사전학습 VLA에 시점당 "moment token" 4개(시간 대조 학습으로 초기화) + 2층 인과 트랜스포머 메모리 모듈, 과거 4시점 | GR00T N1.5 기준: 이력 의존 실제 과제 평균 **29.2% → 76.4%**(+47.2 pt; Pick-and-Place Twice 12.5→66.7, Cover-and-Stack 37.5→79.2, Swap Cubes 37.5→83.3). RoboCasa(100 시연) 62.6→65.4, LIBERO 평균 95.6→97.6, LIBERO-Long 87.8→92.2. **단순 다중 프레임 입력은 RoboCasa에서 62.6→59.3으로 오히려 하락.** 지연: 기준 80.5 ms → HAMLET 82.4 ms(1.02×), 단순 4프레임 108.5 ms(1.35×), 메모리 289→566 MB | (a) 이력은 도움되지만 **넣는 방식이 중요**: 원시 프레임을 그냥 더 넣으면 떨어질 수 있다. (b) 압축 토큰(시점당 4개)이면 지연이 거의 안 늘어남 | ICLR 2026(arXiv Comments·프로젝트 페이지). 코드 myungkyuKoo/HAMLET-Isaac-GR00T 별 38(2026-06 생성, 적음) |
| **MemoryVLA** (Shi 외, MEGVII·Tsinghua 계열; **ICLR 2026**; arXiv 2508.19236) | 7B Prismatic VLM, 지각 토큰 256 + 인지 토큰 1을 메모리 뱅크(최대 L=16)에 저장, 교차 주의 검색 + 게이트 융합 + 인접 유사 항목 병합, 확산 행동 전문가 | SimplerEnv-Bridge 71.9%(CogACT-Large 대비 +14.6), Fractal 72.7%(+4.6), LIBERO 평균 96.5%, 실제 장기 시간 의존 과제 83%(CogACT 대비 +26). 절제: L=16이 최적(L=4·64는 67.7%), 게이트 융합 71.9 vs 단순 덧셈 67.7, 시간 위치 부호 69.8→71.9 | 이력이 이득인 것은 확인. 다만 설계가 무겁고(7B, 메모리 뱅크) 목표가 긴 시간 의존성이라 우리 0.3 s 판단에는 과함 | ICLR 2026(OpenReview Poster). 코드 shihao1895/MemoryVLA 별 347 |
| **RoboMME: Benchmarking and Understanding Memory for Robotic Generalist Policies** (Dai, …, Yuejiang Liu, Chelsea Finn, Nima Fazeli, Joyce Chai; **ICML 2026 Oral**; arXiv 2603.04639) | π0.5 위에 기억 변형 14개(기호: 언어 부목표 / 지각: TokenDrop·FrameSamp / 순환: TTT·RMT) × 통합 방식 3개(맥락 토큰·변조기(adaLN)·전문가) 비교, 16과제 | 기억 없는 π0.5 전체 17.93%(세기 과제 30.00%) → 최고 실용 변형 **FrameSamp + 변조기 44.51%**. 오라클 언어 부목표 84.08%(정답 주석 사용). "기억 표현의 효과는 과제에 크게 의존", "**지각 기억은 시간 민감 행동·움직임 모방에 결정적**", "변조기 통합이 TokenDrop·FrameSamp 모두에서 최고"(사전학습 구조를 덜 흔듦). GroundSG+QwenVL ≈3×, MemER ≈5× 연산 | 우리 오답(시간 민감한 움직임 판단)에 맞는 것은 **지각(프레임) 기억**. 프레임 샘플링이 가장 좋은 비용 대비 효과. 단, 그 결과는 행동 전문가 쪽 통합 — 우리 결정 토큰(VLM 출력)에 넣을 때 이득은 우리가 재야 함 | ICML 2026 Oral(arXiv Comments·프로젝트 페이지). 코드 RoboMME/robomme_policy_learning 별 88 |
| **MemER: Scaling Up Memory for Robot Control via Experience Retrieval** (Sridhar, Pan, Sharma, Finn; **ICLR 2026 Poster**; arXiv 2510.20328) | Qwen2.5-VL-7B 상위 정책이 관련 과거 핵심 프레임을 골라 저수준 π0.5에 지시 | "분 단위 기억이 필요한" 실제 과제 3개에서 선행 방법 능가(초록). RoboMME 측정 연산 ≈5× | 분 단위 기억용 — 우리 문제(0.3 s 움직임)와 규모가 다름. 참고만 | ICLR 2026(OpenReview). 코드 별 수는 확인 안 함(관련성 낮아 생략) |

### 2.2 고유감각·속도·행동 이력 입력과 복사(copycat)·인과 혼동 함정

| 출처 | 한 일 | 측정 이득/손실 | 우리와의 관련 | 신뢰도 근거 |
|---|---|---|---|---|
| **When would Vision-Proprioception Policies Fail in Robotic Manipulation?** (Lu, Xia, Wu, Lu, Hu; Renmin Univ.; **ICLR 2026**; arXiv 2602.12032) | 시각 + 고유감각 정책이 **움직임 전환 구간**(목표 위치 찾기 등)에서 시각을 덜 쓰는 현상을 개입 실험으로 확인. 원인: 고유감각이 손실을 더 빨리 줄여 최적화를 지배. 해법 GAP: 변화점 검출로 구간 분할 → LSTM으로 전환 확률 추정 → 전환 구간에서 고유감각 기울기 축소 | Meta-World: 시각만 82.6–91.8%, **단순 연결(시각+고유감각) 74.6–78.4%**, GAP 94.2–96%. 실제(단·양팔): 시각만 20회 중 9–18, GAP 13–20. 요약: 고유감각 추가 시 시각만 대비 평균 −15.8% | **우리 오답 유형과 정확히 겹친다**: "움직이냐 마냐"는 전환 구간 판단이다. 속도 줄을 넣으면 "지금 움직임 = 다음도 움직임" 지름길이 생겨 정상 구간 점수는 오르고 전환 구간은 나빠질 수 있다 → 층별 평가·드롭아웃 필수 | ICLR 2026(arXiv Comments·프로젝트 페이지). 코드 GeWu-Lab/GAP 별 10(적음 — 학회 채택이 근거) |
| **Learning Long-Context Diffusion Policies via Past-Token Prediction (PTP)** (Torne, Tang, Liu, Finn; Stanford; **CoRL 2025**, RSS 2025 RoboReps 워크숍 최우수 논문; arXiv 2505.09561) | 긴 관측 이력(16 스텝) 정책에 **과거 행동 토큰도 함께 예측**하게 하는 보조 목표. 시각 인코더는 짧은 맥락으로 먼저 학습 → 긴 맥락은 캐시 임베딩으로 정책 머리만 학습(10× 이상 빠름). 시험 시 과거와 일관된 후보를 고르는 자기 검증 | 표 3(성공률, PTP / 이력 없음 / 이력 있으나 PTP 없음): Square 89/79/**17**, Tool Hang 75/51/**0**, Transport 67/60/**0**, Long-Horizon ALOHA 98/28/20, Long-Horizon Square 93/12/3, Push-T 62/67/59. 실제 평균 ≈70% vs 이력 없음 ≈15%(그림). 흥미점: 현대 확산 정책은 복사와 **반대로** 과거 행동을 너무 **안** 쓴다(행동 예측 가능성 비가 전문가 대비 10–100× 약함) | (a) **이력을 그냥 넣으면 0%까지 떨어질 수 있다** — 넣을 때는 보조 목표/정규화가 필요. (b) 우리 결정 헤드에 적용하면 "과거 시점의 결정(또는 움직임 구간)도 맞히게" 하는 보조 손실 형태 | CoRL 2025(프로젝트 페이지 long-context-dp.github.io). Finn 연구실. 코드 long-context-dp/ldp 별 68 |
| **OpenVLA-OFT: Fine-Tuning VLA Models: Optimizing Speed and Success** (Kim, Finn, Liang; **RSS 2025**; arXiv 2502.19645) | 병렬 디코딩 + 행동 청크 + 연속 L1. 손목 카메라 + 고유감각 상태 추가 판 비교 | LIBERO 평균 95.3%(3인칭 이미지만, 수정 데이터) → **97.1%**(손목 + 고유감각, 원 데이터); Long 90.7 → 94.5. 처리량 4.2 → 109.7 Hz(26×), 지연 0.240 → 0.073 s | 현재 시점 고유감각은 **작은** 이득(두 행이 데이터 판도 달라 순수 효과는 더 작을 수 있음). 속도·이력은 다루지 않음 | RSS 2025(arXiv Comments). 코드 moojink/openvla-oft 별 1,399. 발표 2025-02 말로 1.5년 경계선(학회는 2025-06) |
| **AR-VLA: True Autoregressive Action Expert for VLA** (Hu 외, INSAIT·ETH; **RSS 2026**; arXiv 2603.10126) | 청크 대신 긴 수명 기억을 가진 자기회귀 행동 전문가, 시각-언어 앞부분을 갱신하며 재정렬 | 초록: "이력 인식이 우수하고 궤적이 훨씬 부드러우며 성공률은 SOTA와 비슷" — 정확한 수치는 이번 조사에서 옮기지 않음 | 행동 전문가(청크 호출) 쪽 이야기. 결정 정확도와는 간접 | RSS 2026(arXiv Comments). 코드 별 확인 안 함 → 참고만 |

복사·인과 혼동 정리(위 출처들의 공통 결론):
- 이력(관측이든 고유감각이든)을 **그냥** 붙이면 떨어질 수 있다: HAMLET RoboCasa 62.6→59.3, PTP no-PTP 0% 과제들, GAP −15.8%. MEM도 "선행 보고의 인과 혼동 저하"를 명시한다.
- 피한 방법: (i) 압축·정규화된 이력 표현(HAMLET 시점당 4토큰, MEM 과거 패치 버림, RoboMME 변조기 통합), (ii) 보조 목표로 이력 사용을 강제·조정(PTP 과거 토큰 예측, GAP 전환 구간 기울기 축소), (iii) 데이터 다양성(MEM: 최적성·속도·주파수가 제각각인 사전학습 혼합).
- 우리에게 주는 규칙: 속도 줄·이전 결정 줄처럼 **라벨과 거의 같은 값을 주는 입력**은 드롭아웃(예: 학습 30%에서 줄을 `unknown`으로)과 **전환 층 평가**를 같이 한다. 이전 행동 청크를 결정 입력에 넣는 것은 가장 위험해 마지막 순서.

### 2.3 값싼 대안 — 프레임 차분·광류 토큰·이전 행동 조건·청크 앙상블

| 출처 | 한 일 | 결과 | 우리와의 관련 | 신뢰도 |
|---|---|---|---|---|
| **Real-Time Execution of Action Chunking Flow Policies (RTC)** (Black, Galliker, Levine; PI; **NeurIPS 2025**; arXiv 2506.07339) | 다음 청크를 현재 청크 실행 중에 생성, 확실히 실행될 앞부분은 "고정", 나머지는 "인페인팅"(이전 행동 조건). 재학습 불필요 | Kinetix 동적 과제 12개 + 실제 양팔 과제 6개에서 지연이 커도 높은 성공률 유지(성냥 켜기 등). 수치는 본 조사에서 옮기지 않음 | **청크 호출** 쪽의 이전 행동 조건(부드러움·지연 흡수). 결정 정확도 문제의 해법은 아님. 추론 시 방법이라 해시 영향 없음 | NeurIPS 2025(arXiv Comments). 코드 Physical-Intelligence/real-time-chunking-kinetix 별 612 |
| **Training-Time Action Conditioning for Efficient RTC** (Black, Ren, Equi, Levine; PI; arXiv 2512.05964) | 학습 때 추론 지연을 모사하고 행동 앞부분을 직접 조건으로 줌 | 초록: 지연이 클수록 추론 시 RTC보다 우수, 실제에서 비슷한 성능·더 낮은 연산 | 청크 호출용. 학습 시 방법이라 `stageb_model.py`·`stageb_data.py` 수정 → 해시 바뀜 | 대형 연구실(PI) 프리프린트, 학회 확인 못 함 → 보조 근거 |
| 프레임 차분·광류 토큰 (FlowVLA 2508.18269, CronusVLA 2506.19816, MotionVLA 2606.08288 등) | 광류·잠재 움직임을 VLA에 넣음 | — | 아이디어는 맞닿지만 **신뢰도 기준 미달**(7절). 상위 학회 채택된 2025-03 이후 광류/차분 입력 VLA 근거는 이번 조사에서 찾지 못했다 | 제외 |
| 청크 시간 앙상블(ACT, 2023) | 겹치는 청크를 지수 가중 평균 | — | 1.5년 규칙 밖. 결정 정확도와 무관(부드러움용) | 제외(기간) |

값싼 대안에 대한 판단: 차분 이미지나 광류는 **추가 모델·전처리가 필요하고 근거가 약하다**. 같은 정보를 Qwen3-VL이 이미 가진 2프레임 시간 패치(2.4절)로 공짜에 가깝게 넣을 수 있으므로 그쪽을 먼저 권한다.

### 2.4 지연·토큰 비용 (Qwen3-VL-4B, 약 3 Hz 결정, 카메라 2대)

사실(검증함):
- Qwen3-VL-4B-Instruct `config.json`: `patch_size` 16, **`temporal_patch_size` 2**, `spatial_merge_size` 2, 비전 깊이 24, DeepStack 층 [5, 11, 17], 텍스트 36층·hidden 2560. → LLM에 들어가는 시각 토큰 ≈ (H/32)·(W/32)·(T/2).
- transformers Qwen2-VL 계열 이미지 처리기는 **정지 이미지를 `temporal_patch_size`만큼 복제**(`.expand(..., temporal_patch_size, ...)`)하고 grid_t = 1로 둔다. 즉 지금도 이미지 한 장은 "같은 프레임 2장짜리 비디오"로 인코딩된다. **[t−Δ, t] 두 프레임을 비디오로 주면 grid_t는 그대로 1 → LLM 시각 토큰 수·ViT 연산이 지금과 같다.** 차이는 Qwen3-VL이 시간 패치마다 붙이는 타임스탬프 텍스트(`<3.0 seconds>` 형식, Qwen3-VL Technical Report arXiv 2511.21631) 몇 토큰.
- 주의: 두 프레임은 3D 합성곱 패치 임베딩에서 한 토큰으로 섞인다 — 움직임은 암묵적으로만 남는다. Qwen3-VL이 비디오로 사전학습되었으니 움직임 표현이 있을 것으로 기대하지만, **로봇 결정에서 이 방식의 이득을 잰 신뢰할 만한 논문은 찾지 못했다(우리 가설)**. 비디오 처리기 기본 해상도(min/max pixels)가 이미지 처리기와 다를 수 있으니 같은 값으로 맞춰야 토큰 수가 같다.

비교 수치(출처):
- HAMLET(GR00T N1.5, 2.7B): 단순 4프레임 입력 80.5 → 108.5 ms(1.35×), 압축 토큰 82.4 ms(1.02×).
- MEM(PI): 과거 패치 버림으로 토큰 수 불변, H100 카메라 4대에서 실시간.
- OpenVLA-OFT: 7B VLA 지연 0.240 → 0.073 s(병렬 디코딩·청크).

우리 예산에 대입(추정, 실측 필요): 결정 p95 목표 0.28–0.33 s, 6회차 융합 결정 p50 0.331 s(`r7_cycle7.md` N6)로 이미 예산 끝에 있다.
- 권고 1(2프레임 비디오): LLM 토큰 +수 개 → 지연 증가 거의 없음(ViT 입력만 복제 대신 실제 과거 프레임). 런타임에 카메라별 과거 프레임 버퍼만 필요.
- 대안(과거 프레임을 별도 이미지로 추가): 카메라 2대 × 과거 1장이면 시각 토큰이 2배. 4B 모델 사전 채움(prefill)은 토큰 수에 거의 비례하므로 결정 지연이 수십 ms 이상 늘 수 있다(HAMLET의 +35%와 같은 방향). 예산이 빠듯해 두 번째 선택.
- 권고 2(속도 줄): +10–20 텍스트 토큰, 무시 가능.
- 실측 방법: 융합 서버 `t_decide_s`를 같은 파드 CPU 부하 기록과 함께(§r7_cycle7 N6 교훈) 50회 이상.

### 2.5 데이터 규모 근거 (1k → 37k 곡선 해석)

| 출처 | 결과 | 신뢰도 |
|---|---|---|
| **Data Scaling Laws in Imitation Learning for Robotic Manipulation** (Lin, Hu, …, Yang Gao; Tsinghua; **ICLR 2025 Oral**; arXiv 2410.18647) | 시연 4만+·실제 시행 1.5만+. 일반화는 **환경 수·물체 수에 대해 대략 거듭제곱 법칙**; 환경·물체당 시연이 문턱(그들 전략은 환경당 50)을 넘으면 더 모아도 거의 안 는다. 32개 환경 데이터로 새 환경·새 물체 ≈90% 성공 | ICLR 2025 Oral(프로젝트 페이지). 코드 Fanqi-Lin/Data-Scaling-Laws 별 217. arXiv 2024-10이지만 학회 발표 2025-04라 경계선으로 포함 |
| **π0.5: a VLA with Open-World Generalization** (Physical Intelligence; **CoRL 2025 Oral**; arXiv 2504.16054) | 학습 장소 수 3·12·22·53·82·104로 늘릴수록 4과제 성능이 대체로 오름, **104곳 모델 ≈ 시험 환경에서 직접 학습한 모델**. 이동 조작 데이터 ≈400시간 / ≈100 가정, 1단계 예제의 97.6%가 이동 조작 밖 출처; 다중 환경·교차 로봇 데이터를 빼면 유의하게 하락 | CoRL 2025 Oral(OpenReview). openpi 별 13,994 |
| OpenVLA-OFT (위) | LIBERO 과제당 50개(스위트당 500), ALOHA 과제 20–300 시연으로 미세조정 | RSS 2025 |

우리 곡선에 대한 해석:
- 두 점(1k·8 에폭 0.56, 37k·1 에폭 0.72)만 있고 에폭·스케줄이 달라 교란되어 있다. 그래도 상한 0.93 대비 초과 오차로 거듭제곱을 맞추면 (0.93−0.72)/(0.93−0.56) = 0.57 = 37^b → b ≈ −0.16. 이대로면 **10배(≈37만)에 ≈0.78, 100배에 ≈0.82** — 데이터만으로 0.9에 가기는 비싸다(거친 추정, 결정에 쓰지 말 것).
- 10 Hz 스냅샷 37k는 서로 강하게 상관된다. 위 두 논문은 **유효 표본 = 에피소드·장면·물체의 다양성**이라고 말한다. 늘릴 때는 같은 에피소드의 촘촘한 프레임보다 새 에피소드·새 장면을 우선하고, 학습 곡선은 **에피소드 단위 부분집합**(예: 1/8·1/4·1/2·전체, 같은 스텝 수·같은 감쇠 스케줄)으로 3–4점을 먼저 잰다.
- D1 결과(A의 마지막 개선 대부분이 lr 감쇠 효과)와 D2(1k 아직 외우는 중)를 보면, "2 에폭째를 감쇠까지 포함해" 재는 것이 데이터 추가 전의 가장 싼 확인이다.
- 시간 맥락과 데이터는 서로 대체가 아니다: 단일 프레임으로는 "지금 움직이는 중인가"가 원리상 안 보이는 경우가 있어(상한 0.93과 0.72의 차이 중 일부), 그 부분은 데이터를 늘려도 줄지 않는다. 1·2번 격자 실험이 이 몫을 가른다.

## 3. 먼저 해볼 것 — 순위와 이유 (융합 2호출 런타임: decide → chunk)

1. **2프레임 비디오 입력(결정·청크 공통 맥락)** — 기대 이득 높음 / 구현 중 / 지연 거의 0.
   - 근거: VLA 이력 입력의 반복된 이득(MEM ≈+40–55 pt 장기·적응 과제, HAMLET +47.2 pt 이력 과제, RoboMME 지각 기억 17.93→44.51%, "지각 기억은 시간 민감 행동에 결정적"). 토큰 불변 설계는 MEM이 선례.
   - 위험: 단순 다중 프레임이 떨어진 사례(HAMLET RoboCasa −3.3 pt). 대책: 학습 때 과거 프레임을 일정 확률로 현재 프레임 복제로 바꾸는 드롭아웃(= 지금 입력과 같은 분포), 전환 층 평가.
   - Δ 선택: 결정 주기 0.33 s와 같은 3스텝(0.3 s)을 기본, 1스텝(0.1 s)을 비교 칸으로. 10 Hz 공개 데이터라 프레임이 이미 있다.
2. **움직임 텍스트 줄 + 드롭아웃** — 기대 이득 중 / 구현 낮음 / 지연 무시 가능.
   - 근거: 오답이 "움직임 유무·크기"라 직접 정보. 행 계약에 `proprio.qd`·`grip[1]`(폭 속도)가 이미 있다(S-E2E에서 기록 여부는 `proprio_mask`로 확인 필요 — `tau`는 미기록).
   - 위험: GAP(ICLR 2026)의 전환 구간 고유감각 지배, PTP의 무조건 이력 붕괴. 대책: 거친 구간화(3단계), 줄 드롭아웃, 전환 층 따로 보고. 전환 층에서 떨어지면 채택하지 않는다.
3. **데이터: 에피소드 다양성 기준 학습 곡선 + 감쇠 포함 2 에폭** — 기대 이득 중 / 구현 낮음 / 지연 0 / 해시 불변.
   - 근거: Data Scaling Laws(ICLR 2025 Oral), π0.5(CoRL 2025 Oral).
4. (다음 단계) **PTP식 보조 목표**: 결정 헤드가 과거 시점(t−Δ)의 결정 라벨도 맞히게 — 이력 입력을 넣은 뒤 이력을 "쓰게" 강제. `stageb_model.py`/`stageb_data.py` 수정이라 해시 바뀜.
5. (청크 호출 품질용, 결정 정확도와 별개) **RTC 추론 시 인페인팅** — 해시 불변. 학습 시 RTC는 해시 바뀜.

## 4. 체크포인트 프롬프트 해시에 미치는 영향 (정본 §71 보충·§77)

해시 대상: `stagea_train.PROMPT_FILES`(`clients/jevl.py`·`deccall_snap.py`·`jevcall.py`·`options.py`·`e3lite.py`·`serialize.py`·`train/stagea_data.py`·`stagea_loss.py`·`prefix_share.py`)와 `stageb_train.PROMPT_FILES_B`(`train/stageb_data.py`·`train/stageb_model.py`). 바이트가 바뀌면 `runtime/fused_model.check_prompt`가 기존 체크포인트를 거부한다. 형식이 바뀌면 `serialize.SERIALIZER_VERSION`(현재 "ser-A-min-2")도 새 판이어야 하고, `question_id@vN`이 바뀌어 보정 파일(`Calibration.load`)도 다시 만들어야 한다.

| 변경 | 건드리는 파일(예상) | 해시 | serializer 판 | 기타 |
|---|---|---|---|---|
| 2프레임 비디오 입력 | `stageb_data.images_of`·`CAMERA_LAYOUT`("D27v1" → 새 값)·`camera_config`, `deccall_snap`·`stagea_data`의 이미지 목록, 런타임 `build_live_request` 프레임 버퍼 | **바뀜** | **새 판**(카메라 배치가 question_id 해시 입력, §59) | 보정 재생성, 기존 체크포인트 재학습 |
| 과거 프레임을 별도 이미지로 | 위와 같음 | **바뀜** | **새 판** | 지연 실측 필수 |
| 움직임 텍스트 줄 | `serialize.py`(상태 줄), `stageb_data.image_only_state`, `deccall_snap`(스냅샷에 값 싣기) | **바뀜** | **새 판** | 행동 전문가 `ctx_text`에 넣을지 따로 결정 |
| PTP식 과거 결정 보조 손실 | `stageb_model.py`(헤드·손실), `stageb_data.py`(과거 라벨 조인) | **바뀜** | 입력 형식 불변이면 그대로 가능 | `files_sha` 불일치로 재학습 |
| 행동 전문가에 고유감각 이력 | `stageb_model.py`·`stageb_data.py` | **바뀜** | 그대로 가능 | 결정 정확도와는 간접 |
| 학습 시 RTC(행동 앞부분 조건) | `stageb_model.py`·`stageb_data.py` | **바뀜** | 그대로 가능 | |
| 추론 시 RTC | `harvest/runtime/*`만 | 불변 | 불변 | |
| 데이터 추가·부분집합 학습 곡선·2 에폭·lr 감쇠 | `stageb_train.py` 옵션(해시 대상 밖), 데이터 파일 | **불변** | 불변 | §77 메모: 다음에 `stageb_train.prompt_config`를 고칠 때 `"serializer"` 필드를 넣기로 되어 있음 — 이 파일 수정 자체는 해시에 안 들어감 |

## 5. 권하는 다음 사전 등록 틀 (제안, 결정은 메인 세션)

- 같은 37k 학습·같은 스케줄에서 2×2: {기준, 2프레임 비디오 Δ=0.3 s} × {속도 줄 없음, 속도 줄 + 30% 드롭아웃}. 시드 2개 이상.
- 지표: 검증 dec_acc 전체, 전환 층 dec_acc, 정상 운동 층 dec_acc, 질문별(dir_xy·dir_z·mag_coarse), 결정 지연 p95.
- 채택 문턱 예시: 전체 +3 pt 이상이면서 전환 층이 기준보다 떨어지지 않을 것(GAP식 실패 배제).
- 병행(해시 불변): 에피소드 단위 부분집합 1/8·1/4·1/2·1 학습 곡선.

## 6. 출처 목록

| # | 출처 | 학회/연도 | arXiv | 코드·별(2026-09-25) |
|---|---|---|---|---|
| 1 | MEM: Multi-Scale Embodied Memory for VLA Models | PI 프리프린트 2026-03 | 2603.03596 | openpi 13,994(MEM 코드 포함 여부 미확인) |
| 2 | HAMLET: Switch your VLA into a History-Aware Policy | ICLR 2026 | 2510.00695 | HAMLET-Isaac-GR00T 38 |
| 3 | MemoryVLA: Perceptual-Cognitive Memory in VLA Models | ICLR 2026 | 2508.19236 | MemoryVLA 347 |
| 4 | RoboMME: Benchmarking and Understanding Memory for Robotic Generalist Policies | ICML 2026 Oral | 2603.04639 | robomme_policy_learning 88 |
| 5 | MemER: Scaling Up Memory for Robot Control via Experience Retrieval | ICLR 2026 Poster | 2510.20328 | (미확인) |
| 6 | When would Vision-Proprioception Policies Fail in Robotic Manipulation? (GAP) | ICLR 2026 | 2602.12032 | GeWu-Lab/GAP 10 |
| 7 | Learning Long-Context Diffusion Policies via Past-Token Prediction | CoRL 2025 | 2505.09561 | long-context-dp/ldp 68 |
| 8 | Fine-Tuning VLA Models: Optimizing Speed and Success (OpenVLA-OFT) | RSS 2025 | 2502.19645 | openvla-oft 1,399 |
| 9 | AR-VLA: True Autoregressive Action Expert for VLA Models | RSS 2026 | 2603.10126 | (미확인) |
| 10 | Real-Time Execution of Action Chunking Flow Policies (RTC) | NeurIPS 2025 | 2506.07339 | real-time-chunking-kinetix 612 |
| 11 | Training-Time Action Conditioning for Efficient Real-Time Chunking | PI 프리프린트 2025-12 | 2512.05964 | — |
| 12 | Data Scaling Laws in Imitation Learning for Robotic Manipulation | ICLR 2025 Oral | 2410.18647 | Data-Scaling-Laws 217 |
| 13 | π0.5: a VLA with Open-World Generalization | CoRL 2025 Oral | 2504.16054 | openpi 13,994 |
| 14 | Qwen3-VL Technical Report + HF `Qwen/Qwen3-VL-4B-Instruct` config.json + transformers `image_processing_qwen2_vl.py` | 기술 보고 2025-11 | 2511.21631 | (모델 사양 사실 확인용) |

## 7. 제외한 것과 이유

| 항목 | 이유 |
|---|---|
| ContextVLA (2510.04246, KAIST·RLWRLD·UC Berkeley) — 8프레임을 맥락 토큰 1개로 압축, π0 Simpler-WidowX 41.8→56.2% 등 보고 | **ICLR 2026 거절**(OpenReview `Rejected_Submission`, 심사 4/10·"단순 다중 프레임 기준선과의 비교 불명확" 지적), 코드 별 20. 신뢰도 규칙상 근거로 쓰지 않음 |
| CronusVLA (2506.19816) | 상위 학회 채택 확인 안 됨(OpenReview에 CoRR만) |
| FlowVLA (2508.18269) | 상위 학회 채택 확인 안 됨(CoRR만) |
| MotionVLA (2606.08288), PRISM/Scaling Short-Term Memory (2606.16178), Present but Not Remembered (2607.03372), 2026 여름의 기타 메모리 VLA 프리프린트 다수 | 학회 채택 표기 없음, 발표 직후라 반응 검증 불가 |
| TraceVLA (2412.10345, ICLR 2025) | arXiv 2024-12 — 1.5년 규칙 밖 |
| Fighting Copycat Agents (NeurIPS 2020), ACT 시간 앙상블(2023) | 1.5년 규칙 밖 — 용어 출처로만 언급 |

## 8. 이 조사의 한계

- MEM·PTP 실제 수치 일부는 그림에서 읽은 근사값(≈).
- "2프레임 비디오로 토큰 불변" 효과는 처리기 코드·모델 설정으로 확인한 **비용** 사실이고, 로봇 결정 정확도 **이득**은 직접 잰 신뢰할 만한 논문이 없어 가설이다.
- 웹 검색 할당량이 소진되어 arXiv API·OpenReview API·GitHub API·논문 HTML로 직접 확인했다. 그 과정에서 놓친 2025-03 이후 상위 학회 논문이 있을 수 있다(특히 광류·차분 입력 VLA).
