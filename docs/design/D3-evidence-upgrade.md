# D3. 약한 근거 상향 조사 (evidence upgrade)

작성: 2026-09-23 22:25 UTC 전후, 모듈 설계 조사 에이전트. 다른 파일은 고치지 않았다. 커밋하지 않았다.
근거 규칙: `docs/design/README.md`, `00-interfaces.md`(정본), `plan.md` §1 신뢰도 지표·§6, `docs/research/v3/19-credibility-metrics.md` 목록 1(LOW 핵심 근거).

## 0. 조사 방법과 한계
- **사용자 규칙 [사용자]**: 신뢰도 낮은 자료는 없느니만 못하다. 학회 채택·인용 많은 것 우선, 분야 무관(LLM/VLM/로봇/제어/ML), 기간 ≥ 2025-03-23. 큰 주제의 기초 문헌은 예외로 쓰되 **"기간 밖, 기초 문헌"**으로 표시한다.
- arXiv 검색 API(이번 라운드에서 이 에이전트만 허용): 검색 16회 + `id_list` 1회, 모두 6초 이상 간격. 검색어는 부록 A에 적었다. 검색 API의 적중률이 낮아서, 후보 대부분은 이미 알려진 문헌을 id로 확인하는 방식으로 찾았다(한계).
- Semantic Scholar batch: **2회**(허용 한도). 측정 시각 2026-09-23 22:21 UTC, 22:24 UTC. 표의 "인용" 값은 모두 S2 값이다.
- GitHub API: 쓰지 않았다. 스타는 "-"로 둔다.
- WebSearch 4회(Rewind-IL 학회, 2512.24661 학회, PLANEX 삼각표, Åström–Bernhardsson 2002). WebFetch 1회(Nilsson 삼각표 PDF, 본문은 로컬에서 추출했다).
- **원문 본문을 읽은 것**(arXiv HTML 전문을 받아 해당 절을 검색했다): Sentinel(2410.04640v2), BID(2408.17355v4), RTC(2506.07339v2), BacktrackAgent(2505.20660v1), Xiong 외(2306.13063v2), 2512.24661v1, Rewind-IL(2604.16683v1), 2505.16067v2, DoReMi(2307.00329v4), Nilsson "Triangle-Table Trees"(1990, 기술 노트 PDF).
- **초록만 읽은 것**: Colledanchise 외 ICRA 2019(1611.00230), CLAG(2603.15421), Mallen 외(2212.10511). 나머지는 기존 지식과 arXiv 코멘트·S2 venue로만 확인했다. 표에 "초록만" 또는 "본문 미열람"이라고 적었다.
- 등급 규칙은 v3/19 §2를 따른다(HIGH = 주요 학회 채택 확인, 또는 유명 연구실 + 인용 ≥ 20).

## 1. 한눈에 보기

| # | 약한 고리(현재 근거, 등급) | 가장 강한 대체·보강 근거 | 판정 |
|---|---|---|---|
| 1 | M9 "사전조건이 참인 가장 늦은 체크포인트로 되돌아가고, 반성은 남긴다"(FaRe·RIR, LOW) | 되돌아갈 지점: PLANEX/삼각표(Fikes·Hart·Nilsson 1972, 인용 1,258, 기초) + BT 백체이닝(ICRA 2019, 인용 131, 기초) / LLM 되감기: LATS(ICML 2024, 646, 기초), BacktrackAgent(EMNLP 2025, 25), WebRollback(EACL 2026, 13) / 반성 유지: Reflexion(NeurIPS 2023, 5,372, 기초) | **근거 상향** (되돌아갈 지점 규칙) / 반성 유지 부분은 **유지(잠정)** |
| 2 | M5 "겹친 청크 평균은 정밀도를 깎는다, 같은 모드끼리만 블렌딩"(SEAM·WAM, LOW) | RTC(NeurIPS 2025, 236) 시뮬레이션 그림 5 + 실물 그림 6 / BID(ICLR 2025, 52, 기간 밖) §5.2.1·부록 A.4 / Diffusion Policy(RSS 2023, 4,297, 기초) | **근거 상향** |
| 3 | M8 이벤트 호출 대 주기 호출(CheckVLA, LOW-MED) | Tabuada 2007(IEEE TAC, 4,546, 기초), Heemels 외 2012(CDC, 1,922, 기초), Åström–Bernhardsson 2002(CDC, 인용 미측정, 기초) / 로봇 LLM: DoReMi(IROS 2024, 96, 기간 밖) | **근거 상향**(원리). 호출 수를 맞춘 LLM 비교는 여전히 우리 실험 몫 |
| 4 | M10 "작은 실행기에는 골라 넣은 규칙이 통째 주입보다 낫다"(MemCompiler, MED-LOW) | Shi 외(ICML 2023, 1,224, 기초), Mallen 외(ACL 2023, 1,457, 기초), Yoran 외(ICLR 2024, 476, 기초), Lost in the Middle(TACL 2024, 5,111, 기초), Context Length Alone Hurts(EMNLP 2025 Findings, 163), 2505.16067(ACL, 97), CLAG(ACL 2026 Findings, 2) | 원리는 **근거 상향**. "0~2개" 수치와 −83.3%는 **유지(잠정)** |
| 5 | M4/M7 호출 사이 불일치 `C_flip`(Rewind-IL TIDE, LOW-MED) | Sentinel/STAC(CoRL 2024, 79, 기간 밖) + FIPER(NeurIPS 2025, 39) + FAIL-Detect(RSS 2025, 72, 기간 밖 12일) / LLM: Self-Consistency(ICLR 2023, 7,719), SelfCheckGPT(EMNLP 2023, 1,230), 의미 엔트로피(Nature 2024, 1,753), Xiong 외 §5.3(ICLR 2024, 1,197) | **근거 상향**. 단 Sentinel 절제가 "한 샘플끼리의 비교"를 반박 → `flip_score` 계산식은 **설계 재검토 필요** |
| 6 | M8 T3b "LLM의 진행·시간 자기 판단은 낙관적이다"(BAGEN, MED 미심사) | Xiong 외(ICLR 2024, 1,197, 기초) §5.1 / Kapoor 외(NeurIPS 2024, 115, 기초) / 에이전트 직접 근거: 2512.24661(arXiv, 11, 학회 미확인, RAND·UK AISI) | **근거 상향**(과신 일반). "경과 시간 대비 이진 판단"에 대한 직접 근거는 여전히 없음 |
| (참고) | M4 선행 Slow Brain(LOW) | 강등·대체 불필요. 우리 주장의 근거가 아니라 인정해야 할 선행이다(plan §1). 다만 "겹침 + 감쇠 융합" 선행으로는 RTC·BID(심사 통과)를 함께 적는 게 공정하다 | 유지 |

---

## 2. 고리별 상세

### 2.1 M9: 되돌아갈 지점 = 사전조건이 참인 가장 늦은 체크포인트, 반성은 남긴다

현재 설계(M9, plan §M9): "언제 / 어디로 / 무엇을 남길지"(FaRe 2609.18016, RIR 2609.18304, 둘 다 인용 0 → LOW). "어디로" = 사전조건 술어가 모두 참인 가장 늦은 체크포인트. 남길 것 = 목표·환경 지식·시도 이정표·실패 분석.

| 이름 | 분야 | 원문 내용(위치) | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| PLANEX / 삼각표 (Fikes, Hart, Nilsson 1972, *Artificial Intelligence* 3; 설명은 Nilsson 1990 "Triangle-Table Trees" 기술 노트) | 고전 계획·실행 감시 | 삼각표의 i번째 커널은 "행동 a_i..a_N이 실행 가능하고 목표 효과를 내기 위한 사전조건"이다. 탐색 절차는 **목표 쪽에서 거꾸로** 커널을 검사해 만족하지 않는 것을 failed로 표시한다(Nilsson 1990 §B·§C, 본문 읽음). 즉 **현재 상태가 만족하는 가장 늦은 커널의 행동부터 다시 실행**한다. 만족하는 커널이 없으면 재계획(웹 검색 요약, Fritz 조사 문서 인용) | HIGH(기초). S2 인용 1,258(S2 연도 표기 1993은 재수록으로 보임) | **기간 밖, 기초 문헌** | 예 | 예(Shakey) |
| Towards Blended Reactive Planning and Acting using Behavior Trees (Colledanchise, Almeida, Ögren) | 로봇 BT | 초록: 목표 조건에서 백체이닝으로 BT를 만든다. "외부가 행동을 되돌리면 재계획 없이 다시 실행하고, 외부가 도와주면 해당 행동을 건너뛴다" | HIGH(ICRA 2019, 인용 131) | **기간 밖, 기초 문헌** | 예 | 예 |
| LATS (Language Agent Tree Search) | LLM 에이전트 | 트리 탐색으로 이전 상태로 되돌아가 다른 가지를 시도하고, 실패 궤적에서 만든 반성을 다음 시도에 넣는다(본문 미열람, 기존 지식) | HIGH(ICML 2024, 646) | 기간 밖, 기초 | 예(환경 되돌리기 전제) | 아니오 |
| BacktrackAgent (2505.20660) | GUI 에이전트 | 오류 페이지를 판정(Judger)하면 **이전 페이지로 되돌아가** 반성(Reflector)을 넣고 행동을 다시 만든다(그림 2). 절제 Table 3(Mobile3M): 되감기 장치(Judger·Verifier·Reflector) 전부 뺌 48.46 → 전체 54.11 과제 성공률(+5.65%p). Judger만 빼도 48.79. **실제 실행으로 다음 페이지를 얻을 때만** 이득(모의 실행이면 +0.70) | HIGH(S2 venue EMNLP 2025, 인용 25; main/Findings 구분 미확인) | 안(2025-05-27) | **아니오**(7B SFT+RL) | 아니오 |
| WebRollback (2504.11788) | 웹 에이전트 | 명시적 되감기 장치(plan에 이미 보조로 있음) | MED-HIGH(EACL 2026, 13) | 안 | - | 아니오 |
| Rewind-IL (2604.16683) | 로봇 IL | 실패 감지 시 "**가장 늦은 검증된 안전 상태**로 되감고 정책 상태를 비운 뒤 추론을 다시 시작"(초록·본문). 체크포인트는 VLM이 시연에서 미리 고름 | **S2 venue = IEEE RA-L 2026이지만 arXiv 코멘트·웹 검색 모두 확인 안 됨** → MED(확인 전) | 안 | 예 | 예 |
| Reflexion (2303.11366) | LLM 에이전트 | 실패 뒤 말로 된 반성을 에피소드 메모리에 남겨 다음 시도에 넣는다 | HIGH(NeurIPS 2023, 5,372) | 기간 밖, 기초 | 예 | 아니오 |

**가져올 것과 접목**
| 원문 | 우리 접목안 |
|---|---|
| 삼각표: 목표 쪽부터 커널(사전조건)을 거꾸로 검사해 처음 참인 커널의 행동부터 실행 | M9 "어디로" 규칙의 **정본 근거를 FaRe에서 삼각표로 바꾼다.** 체크포인트 k의 커널 = M6 스킬 `phases[k].entry` 술어 ∧ 이후 단계가 필요로 하는 유지 술어(M1 등록부). M9는 목표 쪽부터 검사해 처음 참인 k로 재개. 새 id를 만들지 않는다(00-interfaces §11.1) |
| BT 백체이닝: 외부가 되돌리면 재실행, 도와주면 건너뜀(재계획 없이) | Astra 응답을 기다리는 동안 아래 층(M9 L1·L2)이 멈추지 않고 할 일이 바로 이것이다(00-interfaces §4 "정지 아님"과 맞음) |
| BacktrackAgent·LATS·Reflexion: 되감기 + 반성을 다음 시도 입력에 | "무엇을 남길지"의 반성 부분. **로봇에는 실제 되감기(환경 복원)가 불가능**하므로 LATS·RIR의 "환경 복원 전제"는 그대로 못 쓴다. 우리는 "상태 복원"이 아니라 **"계획 위치 복원 + 물리 재스테이징"**이다(우리 해석) |

**반대 증거·주의**
- BacktrackAgent는 학습형(SFT+RL)이고 되감기가 GUI에서 공짜다. 절제에서 **반성(Reflector)만의 기여는 따로 나오지 않는다**(Judger·Verifier·Reflector 묶음). "반성을 남기면 좋다"의 직접 근거로는 약하다.
- VRL-Bench(LOW, plan 반대 증거)와 2606.15017(EMNLP 2026)은 반성 메모리가 단순 재시도보다 나쁠 수 있다고 한다. 반성 유지 부분은 E-M9에서 "메모리 없는 재시도" 조건과 맞붙여야 한다.
- 삼각표는 결정적 술어를 전제로 한다. 우리 술어 중 T2·T3(임계 민감, VLM)는 커널 판정에 쓰면 흔들린다 → **커널에는 T1 술어만** 쓰는 것을 제안(00-interfaces §11.2 하드 채널 규칙과 같은 논리, 우리 제안).

**판정**: "되돌아갈 지점" 규칙은 **근거 상향**(고전 기초 문헌 + ICRA + ICML·EMNLP LLM 되감기). FaRe·RIR은 "로봇·LLM 최근 사례"라는 보조로 내린다. "반성 남기기"는 **유지(잠정)**: Reflexion은 강하지만 로봇 되감기와 조건이 다르고, 반대 증거가 있다.

### 2.2 M5: 겹친 청크를 평균하면 정밀도가 깎인다, 같은 모드끼리만 블렌딩

현재 근거: SEAM(2607.04609, 인용 4, LOW) 94.8→82.7%, WAM(2608.01880, 인용 1, LOW) 부분 점수.

| 이름 | 원문 내용(위치) | 신뢰도 | 기간 |
|---|---|---|---|
| RTC (2506.07339v2) | 시뮬레이션(그림 5, 지연 그래프): "**TE는 지연 0에서도 전반적으로 성능이 나쁘다. 벤치마크의 다중 모드성 때문이다 — 유효한 행동들의 평균이 유효한 행동이라는 보장은 없다**." 실물(그림 6): "TE 두 변형(sparse·dense) 모두 +100 ms·+200 ms 지연에서 **진동이 너무 커 보호 정지가 걸려 실행 자체가 안 됐다**." 단, "TE sparse는 흔들림을 크게 줄였다"는 서술도 있다 | HIGH(NeurIPS 2025, 236) | 안 |
| BID (2408.17355v4) | §5.2.1: EMA(= 시간 앙상블)는 여러 과제에서 경쟁력 있지만 7개 중 2개 과제에서 성능이 떨어진다. 저자 추정: "연속 청크가 **다른 잠재 전략**을 따를 때 평균은 그럴듯한 전략이 되지 않는다"(부록 A.4). 부록 A.4: 최적 감쇠율이 과제마다 크게 다르다(그림 13). 그림 7: **BID(전략 일관성을 먼저 맞춤) + EMA가 기본 대비 상대 46% 향상** | HIGH(ICLR 2025, S2 venue, 52) | **기간 밖**(2024-08, 기초에 가까운 기준 방법) |
| Diffusion Policy (2303.04137) | 회귀 정책이 두 모드를 평균해 무효 행동을 낸다는 다중 모드성 논증(본문 이번에 재확인 안 함) | HIGH(RSS 2023, 4,297) | 기간 밖, 기초 |
| ACT (2304.13705) | **반대 방향**: 시간 앙상블을 제안했고 부드러움과 성공률에 도움된다고 보고(수치 이번에 재확인 안 함) | HIGH(RSS 2023, 2,410) | 기간 밖, 기초 |

**가져올 것과 접목**
| 원문 | 우리 접목안 |
|---|---|
| RTC: 평균이 아니라 이전 청크에 맞추는 guided inpainting | M5 L2(RTC식 감쇠 블렌딩, 00-interfaces §9 C3 기본 유지)는 그대로. 근거 인용을 SEAM → RTC 그림 5·6으로 바꾼다 |
| BID: 먼저 같은 전략(모드)인 후보를 고르고, 그다음 EMA | **"같은 보기끼리만 블렌딩"과 거의 같은 구조의 심사 통과 근거.** 우리 판에서 "모드" = Jev가 고른 이산 보기(M3), 같은 보기일 때만 L2 감쇠, 다르면 M4 규칙으로 교체(블렌딩 없음) |
| BID 부록 A.4: 감쇠율 민감 | E-M5-1에서 감쇠율을 한 값으로 고정하지 말고 과제별 스윕을 넣는다 |

**반대 증거**: ACT 원문, BID의 "EMA가 여러 과제에서 경쟁력 있음", RTC의 "TE sparse가 흔들림을 줄임". 즉 "평균은 늘 나쁘다"가 아니라 **"모드가 다를 때 평균이 나쁘다"**가 심사 통과 근거가 지지하는 범위다. 우리 주장도 이 범위로 좁혀 적는다.
- 주의: RTC·BID는 연속 행동 확산/흐름 정책이다. 우리 M5는 Ruckig 계획 궤적(`ref(t)`)을 블렌딩하므로 "평균이 무효 행동"이 되는 기제는 같지만(두 목표 사이 평균 위치), 수치를 옮길 수는 없다.

**판정**: **근거 상향**. SEAM·WAM은 보조("최근 사례")로 내린다. 정밀 접촉 정지 [결정 필요](00-interfaces §4)의 근거는 여전히 WAM 하나뿐이라, 그 [결정 필요]는 근거가 약한 채로 둔다.

### 2.3 M8: 이벤트 호출 대 주기 호출

현재 근거: CheckVLA(2607.26789, LOW-MED) 호출 수 맞춤 10.1 대 10.2회 +8.5%p, Learning When to Plan(ICLR 미채택).

| 이름 | 원문 내용 | 신뢰도 | 기간 |
|---|---|---|---|
| Åström & Bernhardsson 2002, "Comparison of Riemann and Lebesgue sampling for first order stochastic systems" (CDC 2002, pp. 2011–2016) | 주기 표본(Riemann) 대 임계 통과 시 표본(Lebesgue, 이벤트 기반)을 비교해, 단순 계에서 이벤트 기반이 더 좋은 성능(웹 검색 요약, 본문 미열람). 잘 알려진 내용은 **같은 평균 표본율에서** 비교한다는 점 | HIGH(기초), 인용 미측정(S2 DOI 조회 실패) | 기간 밖, 기초 |
| Tabuada 2007, "Event-Triggered Real-Time Scheduling of Stabilizing Control Tasks" | 상태 오차가 임계를 넘을 때만 제어 작업을 실행해 안정성을 유지(본문 미열람) | HIGH(IEEE TAC, 4,546) | 기간 밖, 기초 |
| Heemels, Johansson, Tabuada 2012, "An introduction to event-triggered and self-triggered control" | 이벤트·자기 트리거 제어 입문(plan이 이미 self-triggered 근거로 인용) | HIGH(CDC 2012, 1,922) | 기간 밖, 기초 |
| DoReMi (2307.00329v4) | LLM이 계획과 함께 **제약**을 만들고, VLM이 1초마다 제약을 검사, 위반 시 **즉시** LLM 재계획. 비교: 각 스킬이 끝날 때만 재계획하는 Inner Monologue 등. Table I·II: 교란이 커질수록 DoReMi 쪽 성공률·시간 우위(예: Table I 원문 서술 "IM·CLIPort는 스킬 끝에서만 재계획해 실행 시간이 길다"). **열 대응은 이번에 확인 못 해 수치는 옮기지 않는다** | HIGH(IROS 2024, 96) | 기간 밖(2023-07) |

**가져올 것과 접목**
| 원문 | 우리 접목안 |
|---|---|
| 이벤트 기반 표본은 "같은 평균 표본율"로 주기 표본과 비교해야 공정 | E-M8a의 "호출 수를 맞춘 비교" 설계 근거를 CheckVLA에서 이 제어 이론 틀로 옮긴다. CheckVLA는 실험 설계 참고로만 |
| DoReMi: 싼 감시기(주기, 1 Hz) + 비싼 계획기(이벤트) | 우리 구조(M7 코드 critic 주기 감시 + Astra 이벤트 호출)와 같은 모양. 사용자 원칙 "실패할 때마다 Astra"의 로봇 LLM 선례로 인용 |

**반대 증거·빈 곳**: 제어 이론 결과는 선형·단순 확률계이고 "호출 결과가 계획"인 LLM 계층 구조에 그대로 옮겨지지 않는다. DoReMi는 "이벤트 대 스킬 끝 재계획"이지 "이벤트 대 같은 호출 수의 주기 호출"이 아니다. **호출 수를 맞춘 LLM/VLM 계층 호출 비교는 심사 통과 문헌에서 찾지 못했다**(검색어 부록 A 5·11번; 부재 주장 아님).

**판정**: **근거 상향**(원리와 로봇 선례). 호출 방식의 우열은 사용자 요구대로 E-M8a가 정한다.

### 2.4 M10: 작은 실행기에는 골라 넣은 소수 규칙이 통째 주입보다 낫다

현재 근거: MemCompiler(2605.07594, 인용 5, MED-LOW) "통째 주입이 조합 절반 넘게에서 음수, 최대 −83.3%".

| 이름 | 원문 내용 | 신뢰도 | 기간 |
|---|---|---|---|
| Shi 외, "LLMs Can Be Easily Distracted by Irrelevant Context" (2302.00093) | 관련 없는 문맥을 넣으면 수학 추론 정확도가 크게 떨어진다(GSM-IC) (본문 이번에 재확인 안 함) | HIGH(ICML 2023, 1,224) | 기간 밖, 기초 |
| Mallen 외, "When Not to Trust Language Models" (2212.10511) | 초록: 검색 결과를 **필요할 때만** 넣는 적응형 검색이 성능을 올리고 비용을 줄인다(인기 높은 질문은 검색 없이도 경쟁력) | HIGH(ACL 2023, 1,457) | 기간 밖, 기초 |
| Yoran 외, "Making RALMs Robust to Irrelevant Context" (2310.01558) | 관련 없는 검색 결과가 성능을 해친다(본문 미열람) | HIGH(ICLR 2024, 476) | 기간 밖, 기초 |
| Lost in the Middle (2307.03172) | 긴 문맥 가운데 정보를 잘 못 쓴다 | HIGH(TACL 2024, 5,111) | 기간 밖, 기초 |
| Context Length Alone Hurts (2510.05381) | 완벽한 검색이어도 길이만으로 성능 저하(plan M1이 이미 인용) | HIGH(EMNLP 2025 Findings, 163) | 안 |
| 2505.16067 | 본문 §3: add-all 대 선별 추가(자동 판정/엄격한 사람 판정). "경험 따르기" 성질 때문에 틀린 기록이 **오류 전파**를 일으킨다 → 품질 조절이 중요 | HIGH(S2 venue ACL, 인용 97. **S2 연도 2025, 00-interfaces §11은 ACL 2026으로 적음 — 연도 재확인 필요**) | 안 |
| CLAG (2603.15421) | 초록: "작은 언어 모델(SLM)은 **관련 없는 문맥에 특히 취약**"하다는 전제로, 군집별 메모리와 2단계 거르기로 방해 기록을 뺀다. SLM 3종에서 개선 | HIGH(ACL 2026 Findings, 인용 2) — 전제 문장은 선행 인용이지 이 논문 측정이 아닐 수 있음(본문 미열람) | 안 |

**가져올 것과 접목**
| 원문 | 우리 접목안 |
|---|---|
| 관련 없는 문맥이 해친다(Shi, Yoran, Lost in the Middle, 길이만으로도 해침) | Jev 입력에 교훈 목록을 통째로 넣지 않는다는 원칙의 근거를 이 기초 문헌들로 바꾼다 |
| 필요할 때만 넣는다(Mallen 적응형 검색) | (스킬, 결정 지점 id, 술어) 키가 정확히 맞을 때만 넣고, 없으면 침묵(M10 설계 그대로) |
| 선별 추가(2505.16067) | 센서 술어로 확정한 것만 Jev 규칙 재료(M10 설계 그대로) |

**빈 곳**: Jev가 "작은 모델"인지는 공개되지 않았다. "0~2개"라는 개수와 "−83.3%"는 MemCompiler에만 있다. 개수는 E-M10에서 {0, 2, 5, 전체}로 재야 한다(우리 제안).

**판정**: 원리는 **근거 상향**. 개수·수치는 **유지(잠정)** — MemCompiler를 단독 근거로 쓰지 않는다.

### 2.5 M4/M7: 호출 사이 불일치 급증 = 실패 신호 (`C_flip`)

현재 근거: Rewind-IL TIDE(2604.16683, LOW-MED; S2는 RA-L 2026 표기, 미확인).

| 이름 | 분야 | 원문 내용(위치) | 신뢰도 | 기간 |
|---|---|---|---|---|
| **Sentinel / STAC** (2410.04640v2) | 로봇 | §4.1: 연속한 두 시점에서 **겹치는 행동 구간**의 분포 사이 통계적 거리(MMD, KL)를 재고 궤적을 따라 누적. 성공 롤아웃만으로 conformal 임계 → 오경보율 상한(명제 1). Table 1(Close Box, 3시드) STAC 종합 정확도 96%. Table 2(실물 Push Chair, 성공 10·실패 10): STAC TPR 0.80 / TNR 0.90, GPT-4o 영상 QA 0.90/1.00, 둘 합친 Sentinel 1.00/0.90. **그림 5 절제: 통계적이지 않은 거리(최소 거리)로 시간 일관성을 재면 다중 모드성을 놓쳐 기준 방법보다도 나쁘다.** Table 1의 "Temporal Non-Distr. Min."은 OOD에서 TNR 0.27 | HIGH(CoRL 2024, 79) | **기간 밖**(2024-10) |
| FIPER (2510.09459) | 로봇 | 두 지표 AND + conformal(plan·M7이 이미 사용) | HIGH(NeurIPS 2025, 39) | 안 |
| FAIL-Detect (2503.08558) | 로봇 | 실패 데이터 없이 성공 데이터로 점수 + conformal(본문 미열람) | HIGH(RSS 2025, 72) | **기간 밖**(2025-03-11, 12일 차이) |
| Self-Consistency (2203.11171) | LLM | 여러 추론 경로의 다수결. 합의 정도가 정확도와 관련(본문 미열람) | HIGH(ICLR 2023, 7,719) | 기간 밖, 기초 |
| SelfCheckGPT (2303.08896) | LLM | 여러 샘플 사이 불일치로 환각 탐지 | HIGH(EMNLP 2023, 1,230) | 기간 밖, 기초 |
| 의미 엔트로피 (Farquhar 외, Nature 2024; 선행 Kuhn 외 ICLR 2023) | LLM | 답을 의미 군집으로 묶은 뒤 엔트로피 → 환각(작화) 탐지 | HIGH(Nature, 1,753 / ICLR 2023, 950) | 기간 밖, 기초 |
| Xiong 외 (2306.13063v2) §5.3 | LLM | "여러 응답 사이의 분산이 실패 예측을 개선한다"(절 제목·요약) | HIGH(ICLR 2024, 1,197) | 기간 밖, 기초 |

**가져올 것과 접목**
| 원문 | 우리 접목안 |
|---|---|
| STAC: 겹친 구간의 **분포** 사이 거리, 성공 롤아웃 conformal | `C_flip`의 정본 근거를 TIDE → **STAC(CoRL 2024)**로 바꾼다. TIDE는 "최근 실물 사례"로 보조 |
| STAC 절제: 한 샘플끼리의 최소 거리는 다중 모드에서 실패(OOD 오경보 큼) | **현재 `flip_score` = "새 표가 기존 표와 다른 비율"은 한 샘플끼리 비교에 가깝다 → 재검토.** M4 원장에는 같은 스텝에 여러 표가 쌓이므로(00-interfaces §9 C1 "같은 스텝에 여러 표"), 스텝별 **보기 분포(표 빈도)** 를 만들고 연속 도착 사이 분포 거리(예: 총변동 거리 또는 의미 엔트로피 변화)로 바꾸는 안을 제안. 이산 보기라 의미 군집은 필요 없다(보기 = 군집) |
| 의미 엔트로피·SelfCheckGPT: 같은 입력 반복 샘플의 불일치 | 우리 표는 **관측이 바뀐 뒤의 호출**이라 같은 입력 반복이 아니다. 관측 변화에 따른 정상 변경과 불확실성을 구분하려면, `ref(t)` 잔차(M4 (b))가 OK인데 분포가 흔들리는 경우만 `C_flip`으로 보는 조건을 둔다(우리 제안, M7 AND 결합과 맞음) |

**판정**: **근거 상향**(CoRL·NeurIPS·RSS 로봇 + ICLR·EMNLP·Nature LLM). 다만 가장 강한 근거(Sentinel)가 **"한 샘플 비교"를 직접 반박**하므로, `flip_score` 계산식은 **설계 재검토 필요**(분포 거리로). 00-interfaces의 "C_flip을 빼도 설계가 선다"는 안전장치는 유지.

### 2.6 M8 T3b: LLM의 진행·시간 자기 판단은 낙관적이다

현재 근거: BAGEN(2606.00198, 인용 6, arXiv만).

| 이름 | 원문 내용(위치) | 신뢰도 | 기간 |
|---|---|---|---|
| Xiong 외, "Can LLMs Express Their Uncertainty?" (2306.13063v2) | §5.1 "LLM은 말로 확신도를 밝힐 때 과신한다". 요약: 확신도 값이 **대부분 80~100%**, 5의 배수. 모델이 커져도 개선은 부족 | HIGH(ICLR 2024, 1,197) | 기간 밖, 기초 |
| Kapoor 외, "LLMs Must Be Taught to Know What They Don't Know" (2406.08391) | 프롬프트만으로는 보정이 부족하고 소량 미세조정이 필요(본문 미열람) | HIGH(NeurIPS 2024, 115) | 기간 밖, 기초 |
| 2512.24661 "Do LLMs Know What They Are Capable Of?" (Barkan·Black·Sourbut; RAND, UK AISI) | 요약·§1: 시험한 모든 LLM이 자기 성공 확률을 **과신**. 실험 3(SWE-Bench Verified, 도구 호출마다 성공 확률 질의): **여러 프런티어 모델의 과신이 과제를 진행할수록 커진다**, 추론 모델이 비추론 모델보다 낫지 않다. 실패 경험을 문맥에 주면 일부 모델만 과신이 줄고, 완전히 없어지진 않는다 | MED(arXiv만, 인용 11, 학회 미확인 — 웹 검색 결과가 ICLR 2026이라 했으나 요약기의 추정이라 채택 안 함) | 안(2025-12-31) |

**가져올 것과 접목**
| 원문 | 우리 접목안 |
|---|---|
| 말로 한 확신도는 과신(ICLR 2024), 다단계 에이전트에서 진행할수록 과신 증가(2512.24661) | M8 사전 가설 "T3b는 T3a보다 늦게 발동한다"의 근거를 BAGEN 단독 → Xiong(ICLR 2024) + 2512.24661 + BAGEN으로 바꾼다 |
| 2512.24661: 실패 경험을 문맥에 주면 일부 모델은 과신이 준다 | T3b 조건에 "최근 실패 사례 1~2개 문맥 제공" 변형을 넣을 수 있다(M10과 연결, 우리 제안) |
| 00-interfaces §6: 확률 게이트는 E1 전 끔 | 과신 근거가 이 규칙을 더 강하게 받친다. T3b는 확률이 아니라 **이진 범주**로 묻는다(M8 설계 그대로) |

**반대 증거**: Kadavath 외 2022(arXiv, 인용 2,049): 형식을 잘 맞춘 객관식에서는 대체로 보정됨. Tian 외 "Just Ask for Calibration"(EMNLP 2023, 946): RLHF 모델은 말로 한 확신도가 토큰 확률보다 나을 수 있다. 2512.24661 자체도 "대부분 모델이 무작위보다 나은 판별력"이라 했다. → "쓸모없다"가 아니라 **"낙관 쪽으로 치우친다"**가 근거가 지지하는 범위.

**빈 곳**: "경과 시간 대비 이미 끝났어야 하는가"를 이진으로 묻는 직접 연구는 이번에도 못 찾았다(검색어 부록 A 6·14번; 부재 주장 아님).

**판정**: **근거 상향**(과신 일반은 ICLR 2024 기초 + 다단계 에이전트 MED). T3b 가설 방향은 유지.

## 3. 정본·개별 문서에 반영할 것 [제안] (메인 세션 판단)
1. M9: "어디로" 근거를 PLANEX 삼각표(기간 밖, 기초) + BT 백체이닝(ICRA 2019, 기초)으로 바꾸고 FaRe·RIR은 보조. 커널 판정은 T1 술어만.
2. M5: 겹침 평균 반대 증거를 RTC 그림 5·6 + BID §5.2.1·A.4로 바꾸고, 주장 범위를 "모드가 다를 때"로 좁힌다. ACT를 반대 증거로 추가.
3. M8: 호출 비교 설계 근거에 Åström–Bernhardsson·Tabuada·DoReMi 추가, CheckVLA는 참고로.
4. M10: "통째 주입 금지" 원리 근거를 Shi·Mallen·Yoran·Lost in the Middle·2510.05381로. "0~2개"는 E-M10 스윕으로.
5. M4/M7: `C_flip` 근거를 Sentinel/STAC로, **`flip_score`를 스텝별 표 분포 사이 거리로 바꾸는 안을 [결정 필요]로 올린다**(한 샘플 비교는 Sentinel 절제가 반박).
6. M8 T3b: 과신 근거에 Xiong(ICLR 2024)·2512.24661 추가.
7. 사소한 정정 후보: 2505.16067의 학회 연도(S2 = ACL 2025, 00-interfaces = ACL 2026)를 원문 코멘트·ACL Anthology로 확인. Rewind-IL "RA-L 2026"(S2만)도 확인 전까지 LOW-MED 유지.

## 4. 확인 못 한 것
- Åström–Bernhardsson 2002 본문·수치, Tabuada 2007 본문, LATS·Reflexion·Shi·Yoran·Kapoor·Diffusion Policy·ACT 본문(이번엔 기존 지식과 초록·코멘트로만). 이 중 수치를 옮긴 것은 없다.
- DoReMi Table I·II의 열 대응(방법 이름 ↔ 열).
- BacktrackAgent가 EMNLP 2025 main인지 Findings인지.
- Rewind-IL RA-L 채택(S2 venue만), 2512.24661 학회 채택.
- Colledanchise ICRA 2019·CLAG는 초록만.
- 스타(GitHub API 금지).

## 부록 A. arXiv 검색 API 검색어 (2026-09-23 22:0x~22:1x UTC)
1. `abs:backtracking AND abs:"LLM agent" AND abs:error`
2. `abs:rollback AND abs:agent AND abs:checkpoint AND abs:language`
3. `ti:"behavior tree" AND abs:recovery AND abs:"language model"`
4. `abs:"temporal ensembling" AND abs:"action chunk"`
5. `abs:"event-triggered" AND abs:"large language model" AND abs:replanning`
6. `abs:overconfident AND abs:agent AND abs:"predict" AND abs:success AND abs:"language model"`
7. `abs:"failure detection" AND abs:consistency AND abs:"action chunk"`
8. `abs:memory AND abs:agent AND abs:"irrelevant" AND abs:"experience" AND abs:retrieval`
9. `ti:backtracking AND abs:agent AND abs:GUI`
10. `abs:reflection AND abs:backtrack AND abs:"tree search" AND abs:"language agent"` (0건)
11. `abs:"when to replan" AND abs:robot AND abs:language`
12. `abs:"self-consistency" AND abs:robot AND abs:"failure"`
13. `abs:"temporal ensembling" AND abs:multimodal AND abs:policy AND abs:decoding` (0건)
14. `ti:agents AND abs:calibration AND abs:"task success" AND abs:"self-evaluation"` (0건)
15. `abs:"precondition" AND abs:"resume" AND abs:"task and motion planning" AND abs:failure` (0건)
16. `abs:"lessons" AND abs:"small" AND abs:"models" AND abs:"hurt" AND abs:memory AND abs:agent` (0건)
- `id_list` 1회(30개 id, 첫 공개일·코멘트 확인).
- 검색에서 새로 건진 것: 2512.24661, BacktrackAgent, BEAP-Agent(ICASSP 2026, 인용 1 → 쓰지 않음), CLAG, 2503.15202(CASE 2025, 인용 7 → 쓰지 않음), Continue or Replan?(2608.03483, 인용 1 → 쓰지 않음).

## 부록 B. 출처
- https://arxiv.org/abs/2410.04640 · https://arxiv.org/abs/2408.17355 · https://arxiv.org/abs/2506.07339 · https://arxiv.org/abs/2505.20660 · https://arxiv.org/abs/2306.13063 · https://arxiv.org/abs/2512.24661 · https://arxiv.org/abs/2604.16683 · https://arxiv.org/abs/2505.16067 · https://arxiv.org/abs/2307.00329 · https://arxiv.org/abs/1611.00230 · https://arxiv.org/abs/2603.15421 · https://arxiv.org/abs/2212.10511 · https://arxiv.org/abs/2503.08558 · https://arxiv.org/abs/2510.09459
- Nilsson, Triangle-Table Trees (1990): http://ai.stanford.edu/~nilsson/tritable.pdf
- Åström & Bernhardsson 2002: https://portal.research.lu.se/en/publications/comparison-of-riemann-and-lebesgue-sampling-for-first-order-stoch/
- PLANEX 요약: http://www.cs.toronto.edu/~fritz/publications/depth_oral.pdf
- Semantic Scholar batch API(인용 수, 2회).
