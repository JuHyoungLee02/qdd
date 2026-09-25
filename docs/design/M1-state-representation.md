# M1. 이미지 → Jev 입력 (상태 표현) — 모듈 설계

> **정본 우선**: 모듈 사이 인터페이스·정지·확정 규칙·확률 게이트·시간 값은 `00-interfaces.md`가 우선한다(2026-09-23 22:00 UTC). 이 문서와 다르면 그쪽을 따른다.
> 개정 2026-09-25 01:48 UTC (R7 sweep6, 정본 §43·§44·§47·§58·§60 — 단계 3 결정 안내만 붙임, 본문은 단계 2 당시 기록이라 고치지 않음): 빠른 typed 선택기 Jev는 쓸 수 없어(user-log 46) 로컬 VLM Jev-L(Qwen3-VL-4B, 같은 JevCall 형식 = DecCall)로 바꿨고(§44·§50), 런타임 주 설계는 결정 토큰 + action expert + 확인 헤드를 한 백본에서 내는 융합 모델이며 결과 표는 모듈형 스택과 나란히 둔다(§58·§60). 카메라는 AI Worker 기본 카메라 그대로다(§43: `ZED_M` 쌍둥이·트랙 D-stereo 가상 카메라 폐기). 시뮬 카메라 설정은 humanoid-challenge-env 복사다(§47: 머리 ZED Mini 왼쪽 정류 672×376, VGA 수평 85°·fx 367 — 'ZED Mini 102°×57°'는 센서 최대 화각이라 VGA 모드 값이 아니다; 좌·우 손목 D405 424×240). 최신 상태는 `docs/handoff.md` §2.7·§2.8.
> 개정 2026-09-24 07:39 UTC (정본 §36~§39, D21 반영, `D21-aiworker-zed.md`, user-log 37~39 — 로봇·카메라·실물 SG2·힘 입력은 사용자 결정, 깊이·격자·장면·정합 세부는 Claude 결정): §4 공통 층에 **(정본 §36~§37) 카메라와 깊이** 줄 — 머리 ZED Mini(스테레오) + 손목 D405 × 2, **깊이 켬**(ROBOTIS 기본 `depth_mode: 'NONE'`을 바꿈): 머리 1순위 ZED SDK NEURAL, 비교 조건 Fast-FoundationStereo(ZED SDK `CUSTOM` 모드로 주입), 손목 D405 센서 깊이, SVO(원시 스테레오) 기록. §5 끝에 **E3-ST**(ROBOTIS HF 공개 데이터의 머리 스테레오 쌍으로 술어 안정성만 재는 오프라인 시험, `E-first-experiments.md` §5.10). §7-3 카메라 구성(D2c) 해소 = 스테레오(§7-8). 술어 등록부·후보 A 기본·E3는 바뀌지 않는다.
> 개정 2026-09-24 06:36 UTC (정본 §32·§33, D19 반영, `D19-action-expert.md`, user-log 33·34 — 사용자 결정 B, 세부는 Claude 설계): §4.0에 **학습 실행기 B와의 관계** 줄 — 공유 M1 앞단이 대상·관련 물체의 **crop + 마스크**(손목·머리 카메라)를 실행기에 준다(전체 장면 원본은 넣지 않음 [가정]). **술어 등록부는 바뀌지 않는다**(Jev 입력·M7 T1은 코드 계산 그대로). §7-7.
> 개정 2026-09-24 (정본 §28, D17 반영, `D17-api-consistency.md`): §4.1 후보 A에 **직렬화 정규화(J2)** 주석 — 같은 세계 상태 → 바이트까지 같은 텍스트(id·등록부 순, 고정 구간 숫자, 나이 범주). 직렬화기 판본은 Jev `question_id@vN`(J1) 해시와 Astra 입력 정규화(A2)에 들어간다. 후보 선택·E3 판정은 바꾸지 않는다.
> 개정 2026-09-24 (정본 §26, 사용자 결정 user-log 25): "변환 방법은 사용자가 정한다" 줄과 그 출처 표기 줄을 지움 — 사용자가 한 말이 아니다("내가 딱히 저런 말을 한 적은 없는 것 같은데 너가 알아서 진행해줘"). 변환 방법은 Claude가 정한다 → **기본 = 후보 A**(ID 술어 표 + 변화 절, 근거 수 1위), 후보 B·C는 E3 비교 조건. §0 머리·§4 제목·§4.0·§4.1 제목·§5 목적·§7-1을 이에 맞춤. D2 해소. E3 판정 기준 1~7은 그대로(이제 기본 A를 확인하고 B·C 채택 여부를 정하는 데 쓴다).
> 개정 2026-09-24 (정본 §25, D13 반영, `D13-m1-m2-m5-deepread.md` §1·§2): lmgame-Bench 출처 위치 정정("복잡 그래픽 게임에서 효과 작음"은 §3.1 본문, Table 2 아님), 수치(Sokoban 상자 1.0~1.3 → 5.3~6.0개, 3회), 2048에서 강한 모델 이득 없음·음수, **텍스트 전용 모델이 기호 표만으로 참가·상위권**(Jev에 가장 직접적인 기간 안 근거), 저자 "preliminary" 추가. ViPlan에서 가장 강한 모델(GPT-5.2)도 HH nextto 0.52~0.73·open 0.53~0.59·reachable 0.42~0.63, 파생 술어 `clear`는 우연 수준 근처 → 조작적 정의·파생 술어 코드 계산(§3 #10)의 원문 근거. E3에 정답 yes/no 균형, yes·no 정확도 분리, 물체 수별 곡선 추가.
> 개정 2026-09-24 (D11 일관성 점검 반영, `D11-final-consistency.md` I-5): [사용자] 줄을 user-log 11 (1) 원문으로 되돌리고, "변환 방법은 사용자가 정한다"를 따로 떼어 출처 표지를 "[사용자 — CLAUDE.md '연구 주제에서 확인된 제약'(첫 세션부터), user-log에는 원문 없음]"로 바꿈(규칙 자체는 그대로).
> 개정: 2026-09-23 D5 반영 (`D5-consistency.md` 1-14·1-15·1-18): E3 데이터를 단일 팔 자작 장면 스냅샷 풀(E3a·E3b)로, `h_lift`·`tilt_max`를 00 §7 설정 표에 올림, §6-6의 `reachable` 등급 표기를 등록부(T2)와 맞춤.
> 개정: 2026-09-23 D2 검증·00-interfaces §11 반영 (`D2-verification.md` Part A 정정, Part B·C 해소안. 핵심: "임시 기본 A" 삭제 — 다른 모듈은 특정 후보가 아니라 §4.0 **술어 등록부 인터페이스**에만 의존한다. M2·M6·M7·M10 예시의 술어를 모두 등록부에 올리고 등급(T1/T2/T3)을 붙였다. 단계 필드 이름은 `phases`/`entry`/`exit`/`invariants`로 통일.)


- 작성: 2026-09-23 UTC, 단계 2 라운드 D2 설계 에이전트(M1·M2, 이번 라운드 arXiv 검색 API 전담)
- **[사용자]** (user-log 11 (1)) Jev는 이미지를 못 본다. LLM/VLM/VLA 논문뿐 아니라 텍스트와 이미지를 제대로 변환하는 다른 분야 연구에서 가장 효율적인 방법을 찾는다.
- (정본 §26, user-log 25) 변환 방법은 Claude가 정해 진행한다. 이 문서는 **기본 = 후보 A**(ID 술어 표 + 변화 절, 근거 수 1위)로 정한다. 후보 B·C도 끝까지 명세하고(스키마 예, 지연 예산, 실패 방식) E3 비교 조건으로 둔다. E3가 기본 A를 확인하고, 판정 4·5·6에 맞으면 B·C로 바꾼다. (옛 줄 "변환 방법은 사용자가 정한다 → 이 문서는 최종안을 고르지 않는다"는 사용자가 한 말이 아니라서 지웠다.)
- 이 문서가 전제하는 다른 문서: `docs/research/v3/04`(문법보다 내용), `v3/11`(인식 앞단 순위), `v3/14`(M2), `docs/design/M3`(`DecisionStep`, `expected_after`), `M4`(`t_state`, `premise_epoch`), `M7`(`exit_k`·`entry_k`·`invariants_k`, 00-interfaces §11.1 이름), `M9`(체크포인트 = 술어 벡터).

## 0. 조사 방법과 한계
- arXiv 검색 API 13회(5초 간격), WebSearch 6회(한도 10), arXiv abs 약 25편, 본문 HTML 표·절까지 읽은 것 9편(FocusAgent 2510.03204, Read More Think More 2604.01535, lmgame-Bench 2505.15146, ACON 2510.00615, AgileThinker 2511.04898 Tab.10, CaP-X 2603.22435 VDM 절·부록 K.3, ViPlan 2505.13180, PlanAhead 2605.29927, Structured Interfaces 2510.16643은 v3/04에서).
- Semantic Scholar·GitHub API는 쓰지 않았다(규칙). 인용 수·스타는 v3/19에 있는 것만 옮기고, 새 문헌은 "미측정".
- Jev로 직접 잰 것은 하나도 없다. "접목안" 칸은 모두 추론이다.
- 검색어(부재 주장용 기록): `abs:"web agent" AND abs:pruning AND abs:observation`, `abs:"context pruning" AND abs:agent`, `abs:"screen parsing" OR abs:"accessibility tree" AND abs:"token"`, `abs:game AND abs:harness AND abs:perception AND abs:benchmark`, `abs:"scene graph" AND abs:"language model" AND abs:serialization`, `abs:"change description" OR abs:"state difference" AND abs:"LLM agent"`, `abs:"spatial relations" AND abs:"text-only" AND abs:LLM`, `abs:"predicate" AND abs:"vision-language" AND abs:"symbolic" AND abs:manipulation`, WebSearch: lmgame-Bench perception ablation / VLM spatial reasoning reliable relations / text-only spatial reasoning 2025 / VLM predicate classification accuracy manipulation.

---

## 1. 역할과 입출력

| 항목 | 내용 |
|---|---|
| 위치 | 카메라(+깊이) → 인식 앞단(코드·로컬 모델) → **M1 직렬화기(코드)** → Jev 상태(텍스트) / 같은 ID로 Astra용 Set-of-Mark 이미지 |
| 입력 | 인식 앞단 산출(추적 ID, 마스크, 3D 중심·크기, 자세 있으면 자세), 로봇 고유 감각(그리퍼 폭, 힘, 말단 자세), **M2 세션 계약**(관련 ID 목록, 단계 원장의 술어 이름, 금지 술어), 직전 Jev 요청의 상태(변화 계산용) |
| 출력 | (1) Jev `state` 텍스트: 현재 상태 전체(관련 부분만) + 변화 절 + 시각, (2) 모든 술어의 참/거짓 표(코드가 쓰는 것, M4(b)·M7·M9가 읽음), (3) Astra용 번호 표시 이미지(M2·M8) |
| 쓰는 곳 | M3(질문의 보기 이름과 예상 결과 술어가 이 어휘를 쓴다), M4(`t_state`, 전제 상태), M7(단계 술어·채널 등급), M9(체크포인트 = 술어 벡터), M2(Astra가 계약에 쓰는 술어 이름 = 이 어휘), M6(스킬 `entry`/`exit`/`invariants`/`stop`), M10(규칙 조건 술어). **모두 §4.0 술어 등록부 하나만 참조한다**(00-interfaces §11.1) |
| 불변 규칙(v4 공통) | Jev에 숫자 계산을 시키지 않는다(범주·참거짓), 관련 없는 내용 넣지 않는다, 영어, 평평한 상태, 버전 고정 |

**전제 경고(plan v4 그대로)**: M2·M3·M4(b)·M7·M9는 "코드가 기하를 계산해 술어를 만든다"를 전제로 쓰였다. 이 전제는 이 문서의 후보 A·B에서는 성립하고, 후보 C에서도 "술어 부분"은 성립한다. 코드 술어를 전혀 쓰지 않는 변환(예: VLM이 매 프레임 자유 서술)은 다른 모듈 설계를 깨므로 이 문서는 후보가 아니라 **대조 조건**으로만 둔다. [결정 필요]

---

## 2. 분야 전체 최고 후보 표

신뢰도: HIGH / MED / LOW(추천 안 함). "기간 밖" = 첫 공개 2025-03-23 이전, 기초 문헌으로만.

### 2.1 인식 → 텍스트 파이프라인 (LLM 에이전트 전 분야)

| 이름 | 분야 | 어디서 최고였나 (조건, 표 위치) | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| **lmgame-Bench 인식 모듈** (2505.15146) | 게임 에이전트 | 격자 게임(Sokoban 등)에서 **게임 백엔드가 읽은 기호 상태 표**("Box at (2,3)")를 주면 Gemini·o4-mini가 크게 오름 — 절대값은 Sokoban 상자 **1.0~1.3개 → 5.3~6.0개**(Table 2, 3회 평균, +Vision 조건). 2048에서는 강한 모델의 이득이 없거나 음수(gemini 120.5 → 117.4), 약한 모델은 오름(llama 44.6 → 73.7) → 이득은 모델 능력에 따라 다르다. **텍스트 전용 모델도 기호 표만 받고 참가해 상위권**(Table 1: grok-3-mini Sokoban 5.7, deepseek-r1 Sokoban 1.3) — 이미지를 못 보는 Jev에 가장 직접적인 기간 안 근거. 복잡한 그래픽 게임(마리오, Ace Attorney)에서 o3가 만든 **텍스트 설명**은 효과가 작다(**§3.1 본문 문장**. Table 2에는 Mario·Ace Attorney 행이 없다. §25 D13 정정). 저자 한계: "results should be considered preliminary"(부록 E) | MED(UCSD·Berkeley·MBZUAI, 학회 미확인, 인용 미측정) | 안 | 예 | 아니오 |
| **CaP-X VDM** (2603.22435) | 로봇 코드 에이전트 | 12개 모델 다중 턴: **VLM이 이미지를 구조화 텍스트로 바꿔 주는 VDM(M3 조건)이 원시 RGB를 매 턴 넣는 조건(M2)보다 일관되게 낫고, 원시 RGB는 오히려 성공률을 낮춤**(Figure 5, 본문). VDM = 첫 턴 장면 설명 + 과제 관련 속성, 이후 턴 **이전 대비 차이 + 완료 여부**. VDM 백본은 Gemini-3-Pro(부록 K.3, 상한을 보려고 가장 강한 모델) | HIGH(ICML 2026, 819★, v3/02) | 안(경계일) | 예 | **예** |
| **OmniParser V2** | GUI | 검출기 ID·상자 + 캡셔너 → 번호 목록 → 텍스트 LLM. GPT-4o와 ScreenSpot-Pro 39.6, A100 0.6 s/프레임(v3/11) | HIGH(25k★) | **기간 밖, 기초 문헌** | 예 | 아니오 |
| **ScreenParse / ScreenVLM** (2602.14276) | GUI | 316M VLM이 화면 전체 요소를 압축 마크업(ScreenTag)으로 출력, PageIoU 0.592 대 큰 VLM 0.294(초록) | HIGH(ICML 2026) | 안 | 학습형 | 아니오 |
| **Read More, Think More** (2604.01535) | 웹 에이전트 | WorkArena L1 Table 1: **강한 모델은 긴 HTML(56,653 토큰)이 짧은 접근성 트리(6,720)보다 좋고**(GPT-5.1 high 55.8→73.3, Sonnet 4.6 52.4→67.0), **약한 모델은 반대**(gpt-oss-20b high 46.4→27.6, Llama-3.1-70B 18.2→3.6). **조건(D2 A1)**: 이 방향은 모델·추론 예산 의존이다 — 같은 "상위 능력" 묶음의 o3-mini(high)는 HTML에서 **−7.6**, gemini budget=128은 +6.0. 관측 이력(과거 9스텝)을 **전체 대신 문자 단위 diff로** 넣으면 토큰 약 35%(39,011→13,670)에 gpt-5.1 low 50.9→53.3, o3-mini 43.3→46.1(§3.4). 단 **gemini-2.5-flash budget=128은 diff가 full보다 −6.1(39.4→33.3)**, gpt-oss-120b high −2.1(Table 5) | MED(NEC, 학회 미확인, 인용 4) | 안 | 예 | 아니오 |
| **A11y-Compressor** (2605.00551) | GUI | OSWorld: 접근성 트리를 구조화·중복 제거로 **입력 22%**, 성공률 평균 +5.1%p(초록) | MED-LOW(ACL SRW 2026) | 안 | 예 | 아니오 |
| **Structured Interfaces for 3D SG** (2510.16643) | 로봇 LLM | 큰 3D 장면 그래프: 질의로 부분만 가져오면 0.77 대 전체 0.33, 토큰 2,395 대 582,202(Table I·IV, v3/04) | MED(MIT) | 안 | 예 | 예 |
| MomaGraph (2512.16909) | 로봇 | 공간+기능+상태 그래프 먼저 → 계획, +4~5%p(자체 벤치, v3/04) | MED | 안 | 예(폐쇄 모델) | 예 |
| SpatialEval (2406.14852) | LLM/VLM | **텍스트만 준 LLM이 이미지를 더 받은 VLM보다 공간 과제에서 자주 낫다**, 텍스트 단서가 충분하면 VLM도 이미지를 덜 본다(초록) | HIGH(NeurIPS 2024) | **기간 밖, 기초 문헌** | — | — |
| Lost in Aggregation (2606.22219) | LLM 공간 | 미로 1,050개: 입력 4형식 중 **구조화 좌표 텍스트가 렌더 이미지보다 훨씬 낫다**. 한 번에 전체 풀이는 10×10에서 거의 0, 같은 모델이 단일 수준 질문(국소·분기·전역)은 30~75%. 첫 오류 59%가 분기 선택, 전역 방향 오류 1%(초록) | LOW-MED(학회 미확인) | 안 | — | 아니오 |

### 2.2 관련도 필터 / 상태 가지치기 (질의 조건부, 2025~26)

| 이름 | 분야 | 어디서 최고였나 | 신뢰도 | 기간 | 학습 없이 | 로봇 |
|---|---|---|---|---|---|---|
| **FocusAgent** (2510.03204) | 웹 | 작은 LLM이 과제 목표로 접근성 트리 줄을 골라 **50~63% 가지치기**(Table 1 변형 56~63%, Table 2 GPT-4.1 51~61%·Claude-3.7 50~51%). 성공률은 **검색기가 강할 때(GPT-5-mini)만 거의 유지**(WorkArena L1, GPT-4.1 백본: 기준 53.6 대 FocusAgent(5-mini) 53.2, Table 1·2). **qwen3-8b 검색기는 43.9(−9.7p)**, 원문 "retrieval is highly dependent on the retriever LLM capability". **BM25·임베딩 검색은 청크 크기에 민감**(**200 토큰** 청크에서 42.4~45.8, Table 1). 주입 공격 성공률도 낮춤 | HIGH(TMLR 08/2026, 인용 15) | 안 | 예 | 아니오 |
| **ACON** (2510.00615) | LLM 에이전트 | 관측·이력 압축 **지침(자연어)을 실패 대조로 최적화**: 압축 없이 성공·압축해서 실패한 과제만 모아 최적화 LLM이 "무엇을 잃었나" 피드백 → 지침 갱신. AppWorld 최대 토큰 −25% 이상 정확도 유지, 8-목표 QA −54.5%에 EM/F1 상승(§4.2). 최적화기는 o3 + 대조 피드백이 최선(§4.5) | HIGH(ICML 2026) | 안 | **예(프롬프트 최적화)** | 아니오 |
| **The Complexity Trap** (2508.21433) | 코드 에이전트 | SWE-bench Verified, 모델 5설정: **오래된 관측 가리기(단순)가 LLM 요약과 같은 해결률에 비용 절반** | MED(NeurIPS'25 DL4C 워크숍) | 안 | 예 | 아니오 |
| SWE-Pruner (2601.16746) | 코드 에이전트 | 에이전트가 목표 힌트를 쓰고 0.6B 스키머가 줄 선택, 토큰 23~54% 감소에 성공률 오히려 상승(초록) | MED(학회 미확인) | 안 | 학습형 스키머 | 아니오 |
| Signal-Driven Observation (2606.06708) | 웹 | 관측 빈도를 행동 빈도에서 떼고 **신호(URL 전환, 새 요소, 행동 실패, 외부 사건)가 뜰 때만 전체를 다시 읽는** 설계 제안(수치 없음, 입장 논문) | LOW-MED(ICML 2026 워크숍) | 안 | 예 | 아니오 |
| Provence (2501.16214) | RAG | 문장 단위 가지치기 + 재순위, 필요한 가지치기 양을 스스로 판단(초록) | HIGH(ICLR 2025) | **기간 밖(2025-01)** | 학습형 | 아니오 |
| Context Length Alone Hurts (2510.05381) | LLM | 관련 정보를 다 찾아도 **길이만으로 13.9~85% 하락**, 가려도 하락(v3/04) | HIGH(EMNLP 2025 F) | 안 | — | — |

### 2.3 공간 술어 어휘의 신뢰도

| 이름 | 분야 | 무엇이 믿을 만했나 | 신뢰도 | 기간 |
|---|---|---|---|---|
| **ViPlan** (2505.13180) | VLM + 기호 계획 | VLM이 술어 참/거짓을 답하는 grounder: Blocksworld에서 **leftOf·rightOf·on은 강한 모델이 거의 완벽, clear는 더 어려움**. 가정 환경에서 **nextto·open·reachable은 가장 강한 모델도 90% 미만**. 술어 정확도는 **"많은 모델 계열에서" ≥90%**(부록 개별 결과 절)이지만 가정 환경(HH)에서 약한 모델의 nextto는 0.12~0.55(부록 M Table 19). (§25 D13) **가장 강한 모델(GPT-5.2)도 HH nextto 0.52~0.73, open 0.53~0.59, reachable 0.42~0.63**(Table 19, Simple/Medium/Hard). 원문은 낮은 이유를 "ambiguity of the domain … can require a degree of interpretation"으로 적고, 정의가 분명한 holding·inside는 높다. 파생 술어 `clear`("topmost of its column")는 일부 모델이 우연 수준 0.50 근처, 물체가 많을수록 정확도 하락, 모델별 yes 편향(Molmo, AyaVision)·no 편향(DeepSeek-VL2)(부록 M). **한 에피소드에 최대 120개 술어를 맞혀야 해서 오류가 누적**, 과제 성공은 낮다(본문 §5, 부록 M Table 17~20, Figure 16). VLM-as-grounder 46% 대 VLM-as-planner 9%(BW), 가정 환경은 5% 대 34%(Table 1, 모델 평균) | MED(Aalto·FBK, **EMNLP 2026 Findings**(journal-ref, D2 A1), 인용 9) | 안 |
| **OmniSpatial** (2506.03135) | VLM | 기본 관계(왼/오, 가깝/멀, 개수)는 최신 추론 VLM이 90% 넘어 포화, 복합 공간(관점 전환·동역학 등) o3 56.33% 대 사람 92.63%(v3/11) | HIGH(ICLR 2026) | 안 |
| **QSTRBench** (2605.18380) | LLM | 정성 공간·시간 계산(RCC-8, 방위, Allen 등)의 **합성(composition)** 질문: 최신 모델 모두 찍기보다 낫지만 일관되게 다 맞히지 못함, 계산마다 편차 큼(PA 쉬움, RCC-22 가장 어려움)(초록) | MED-LOW(학회 미확인) | 안 |
| FloorplanQA (2507.07644) | LLM | JSON 평면도: 얕은 질의는 맞히나 **물리 제약·공간 일관성 위반**, JSON↔XML ±3%p(v3/04) | HIGH(ICML 2026) | 안 |
| RoboSpatial (2411.16537) | VLM 로봇 | 관계를 **공간 맥락(빈 공간) / 호환(들어가나) / 배치(왼·오·앞·뒤·위·아래)** 세 범주, 기준 좌표계를 ego·world·object 셋으로 나눔. 기성 VLM은 좌표계 이해가 약함(초록) | HIGH(CVPR 2025 Oral) | **기간 밖(2024-11), 기초 문헌** |

### 2.4 변화(델타) 서술

| 이름 | 분야 | 무엇 | 신뢰도 | 기간 |
|---|---|---|---|---|
| **CaP-X VDM** | 로봇 | 첫 턴 전체 장면 설명 → 이후 턴 **"무엇이 바뀌었나 + 과제가 끝났나"**. 이 텍스트는 **VLM이 만든 것**(우리 제안인 코드 diff와 다름, v4.1 정정 사항) | HIGH | 안 |
| **Read More, Think More §3.4** | 웹 | 과거 9스텝 이력을 전체 대신 **이전 관측과의 문자 diff**로 넣음 → 토큰 약 1/3, 성능 비슷 또는 더 좋음. **현재 관측은 전체로 준 상태에서 이력만 diff**(원문 설정) | MED | 안 |
| Complexity Trap | 코드 | 오래된 관측은 가리고 최근 것만 → 요약만큼 좋음 | MED | 안 |
| Signal-Driven Observation | 웹 | 사건 신호가 뜰 때만 재관측 | LOW-MED | 안 |

부재 기록: "로봇 상태를 텍스트 diff로 LLM에 주는 형식을 전체 상태 대비로 잰 연구"는 이번 검색어(위 0절)로 찾지 못했다. 부재를 주장하지는 않는다.

---

## 3. 가져올 것과 접목 방법 (원문 칸 / 우리 접목안 칸 분리)

| # | 원문 (무엇을 했나) | 우리 접목안 [제안] | 옮길 때 깨지는 것 |
|---|---|---|---|
| 1 | lmgame-Bench: 백엔드 기호 상태 표가 격자 게임에서 큰 이득(상자 1.0~1.3 → 5.3~6.0개, 3회), 텍스트 전용 모델도 기호 표만으로 상위권, VLM 텍스트 설명은 복잡한 그래픽에서 이득 작음(§3.1 본문), 강한 모델은 2048에서 이득 없음·음수, 저자 "preliminary" | Jev 상태의 뼈대는 **인식 앞단이 만든 기호 표**(ID·범주·참거짓)로 하고, VLM 자유 서술은 뼈대가 아니라 보조 칸으로만(후보 C) | 게임 백엔드 상태는 **오라클**이다. 우리 인식 앞단은 오류가 있다 → E3에 인식 잡음 조건 필수 |
| 2 | CaP-X VDM: 첫 턴 장면 설명 + 이후 턴 차이·완료 여부, 원시 이미지 끼워 넣기보다 낫다 | (a) 상태 텍스트에 **변화 절**을 둔다. (b) 단 변화는 **코드가 술어 표 두 개를 비교해 만든다**(ms, 결정적). VLM(Astra) VDM식 서술은 Astra가 호출될 때(M8)만 부가 | VDM은 턴 기반 코드 에이전트(초 단위). 3Hz 루프에 VLM VDM을 넣으면 지연이 맞지 않는다 |
| 3 | Read More §3.4: 현재 관측은 전체 + **이력만** diff | **Jev가 diff만으로 상태를 재구성하게 하지 않는다**(과제 규칙). 매 요청 = 현재 상태 전체(관련 부분) + 최근 변화 목록(최대 k개, 시각 붙음) | 원문은 문자 diff. 우리는 술어 단위 diff(`on(obj_3,tray): false→true @t-0.4s`) |
| 4 | Read More Table 1: 강한 모델 두 개(Sonnet 4.6, GPT-5.1 high)는 자세한 관측, 약한 모델은 압축 관측이 유리. 같은 상위 묶음의 o3-mini(high)는 반대(−7.6) — 모델·추론 예산 의존 | Jev의 "능력 등급"은 모른다(공개 안 됨). **"작게 넣는다"는 가정을 E3에서 시험**: 관련 부분(A) 대 장면 전체(A-full) 조건 | Jev는 빠른 결정 모델. 강한 모델 쪽 결과를 그대로 믿으면 안 되고, 약한 모델 쪽 결과도 그대로 믿으면 안 된다 |
| 5 | FocusAgent: 과제 목표로 관련 줄을 LLM이 고름(강한 검색기일 때만 성공률 유지), BM25·임베딩은 청크 크기에 민감 | 관련도 판단을 **실행 루프 밖으로** 뺀다: Astra가 세션 계약에 `relevant_ids`와 `relevant_predicates`를 적고(계획 시 1회), 코드가 매 프레임 그 목록 + 규칙(그리퍼와 접촉 중인 것, 경로를 막는 것, 새로 나타난 것)으로 거른다. LLM 검색기를 3Hz에 넣지 않는다 | FocusAgent의 검색기는 매 스텝 돈다. 우리는 계획 시 1회라 장면이 바뀌면 목록이 낡는다 → "새 ID 등장" 규칙과 M8 재호출로 보완 |
| 6 | ACON: 압축 지침을 **실패 대조**(전체로는 성공, 압축으로는 실패)로 자연어 최적화, 학습 없음 | 오프라인 E3 뒤에 **직렬화 규칙(무엇을 남기나)을 Astra가 대조 실패 사례로 고치는 루프**: 같은 결정 문항을 A-full로는 맞히고 A로는 틀린 사례만 모아 Astra에게 "무엇이 빠졌나"를 묻고 규칙(코드 설정)을 갱신. M10 경험 축적과 같은 모양 | ACON은 압축기가 LLM. 우리 압축기는 코드라 Astra 피드백을 **코드 규칙(포함 조건)으로 번역**해야 한다(사람 검토 필요) |
| 7 | Complexity Trap / SDO: 오래된 관측 가리기, 사건 신호 때만 재관측 | 변화 절은 **최근 N초만**, 그보다 오래된 변화는 버린다(원장 상태로 흡수). 인식 앞단의 무거운 부분(영역 캡션, 자세 초기화)은 신호(새 ID, ID 교체 의심, 접촉 변화, M7 WARN) 때만 | — |
| 8 | ViPlan: leftOf/rightOf/on은 VLM도 거의 완벽, nextto/open/reachable은 <90%(가장 강한 GPT-5.2도 0.42~0.73), 원인은 해석이 필요한 모호한 정의, 술어 오류가 누적 | 술어를 **신뢰 등급**으로 나눈다(전체 목록은 §4.0 술어 등록부가 정본): T1 코드 기하로 결정적(on, inside, above, left_of(로봇 기준), near 범주, holding(그리퍼 폭+힘), in_contact) / T2 코드지만 임계값 민감(aligned, reachable(IK), clear, graspable) / T3 VLM 필요(open, lid_on, empty, 재질). T3는 매 프레임 넣지 않고 **측정 시각 붙여 캐시**, 불확실하면 `unknown`. (§25 D13) 등록부 술어는 **모두 설정 표 문턱을 쓰는 조작적 정의**로 둔다(원문: 모호한 정의가 낮은 정확도의 원인). T3 `open`을 VLM으로 만들면 정확도 50~77%를 전제로 설계한다 | ViPlan은 VLM이 술어를 답한 결과. 우리 T1은 코드라 그 수치가 곧 우리 정확도는 아니다. 코드 술어의 오류원은 깊이·분할이다 |
| 9 | ViPlan 오류 누적(120개) | Jev에 주는 술어 개수를 **결정에 필요한 것으로 제한**(M3 질문마다 필요한 술어만 강조 절에 복사) + M4(b)·M7이 술어 뒤집힘을 감시 | — |
| 10 | QSTRBench: 관계 **합성**은 최신 모델도 흔들림 / Lost in Aggregation: 한 번에 전체 풀이는 무너지고 단일 수준 질문은 됨 | Jev에게 "A가 B 위, B가 C 안 → A는 C 안?" 같은 **추론 사슬을 시키지 않는다**. 필요한 관계는 코드가 **직접** 계산해 적는다(전이 폐쇄 포함). 질문은 한 수준씩(M3의 질문 분해와 같은 방향). (§25 D13) 파생 술어 `clear`·`top_clear`·`path_clear`도 코드로 직접 계산한다 — ViPlan 부록 M에서 파생 술어 `clear`는 VLM이 우연 수준 근처였다(원문 근거) | — |
| 11 | RoboSpatial: 기준 좌표계 셋(ego/world/object), 관계 범주 셋(맥락/호환/배치) | 방향 술어는 **로봇 기준 좌표계 하나로 고정**하고 이름에 박는다(`left_of_robot`). 호환 술어(`fits_in(obj, slot)`)는 코드 기하로 | 기간 밖 기초 문헌 — 어휘 분류만 빌린다 |
| 12 | SpatialEval: 텍스트 단서가 충분하면 텍스트 LLM이 VLM 이상 | "텍스트화가 정보를 잃는다"는 걱정에 대한 약한 반대 근거. 단 기간 밖, 수치 미확인 | — |
| 13 | OmniParser/ScreenParse: 번호 붙은 요소 목록, 압축 마크업 | ID는 **짧고 안정된 토큰**(`o3`), 이름은 범주+구분 속성(`o3 mug red`), 목록 순서는 ID 순 고정(보기 순서 편향 방지, M3) | ScreenParse는 학습형 — 형식 발상만 |

---

## 4. 설계안: 순위 매긴 후보 A / B / C (기본 = A, Claude 결정, 정본 §26 — E3가 확인)

공통 층(세 후보 모두 같음)
- 인식 앞단(v3/11 순위 그대로): SAM 3.1 추적 ID → 깊이(스테레오면 Fast-FoundationStereo, RGB-D면 센서) → 3D 중심·크기 → 필요한 물체만 FoundationPose. 이 문서는 인식 앞단을 다시 고르지 않는다.
- **(정본 §36·§37) 카메라와 깊이 — AI Worker 기준**(로봇·카메라는 사용자 결정 user-log 37, 깊이 방식은 Claude 결정): 사용자 원문 "스테레오캠을 쓸 생각이고"·"스테레오캠이니까 뭐 뎁스나 이런 것도 가능은 할것 같고"(user-log 37). 카메라 = 머리 **ZED Mini**(102°×57°, 기선 63 mm, 머리 pitch −50°~30°·yaw −20°~20°) + 손목 **RealSense D405 × 2**(7–50 cm). ROBOTIS 기본 설정은 **깊이 끔**(`depth_mode: 'NONE'`, VGA 30 fps)이므로 이를 바꾼다. 머리 깊이 1순위 = **ZED SDK NEURAL**(Orin 공식 30 FPS 수치는 ZED X 기준, ZED Mini 실측 필요), 비교 조건 = **Fast-FoundationStereo**(CVPR 2026, NVIDIA, 1,497★; ZED SDK `CUSTOM` 모드로 같은 경로 주입 — 원문 "feed the SDK your own disparity or depth"). 손목은 D405 센서 깊이(근거리, 접촉 근처 담당). 기록은 **SVO**(원시 스테레오)로 남겨 깊이 모드를 나중에 바꿔 비교한다(원문 "SVO files store only the raw unrectified images … can be replayed later with any depth mode"). 오차 추정(우리 계산, 시차 오차 0.25 px 가정): VGA에서 0.6 m 약 5 mm, 1.0 m 약 15 mm → T1 술어 문턱(cm 단위)에 대체로 충분. 위 줄의 "스테레오면 Fast-FoundationStereo"는 비교 조건으로 그대로 남는다. → **정정(정본 §43·§47, R7 sweep6)**: 'ZED Mini 102°×57°'는 센서 최대 화각이다. 쓰는 VGA 672×376 모드(왼쪽 정류 영상)는 수평 85°·fx 367 px(실측 camera_info 364.0)다. 위 오차 추정 '0.6 m 약 5 mm, 1.0 m 약 15 mm'는 fx ≈ 272 px(102°)로 계산한 값이라, fx 367이면 약 3.9 mm·약 10.8 mm다(같은 식, 시차 오차 0.25 px, 우리 계산). 시뮬 카메라는 §47 설정 복사(머리 672×376, 좌·우 손목 D405 424×240)이고 카메라 추가는 하지 않는다(§43).
- 술어 계산기(코드): §3 #8의 T1/T2/T3 어휘. 임계값에는 **히스테리시스 띠**(예: `near` 들어가기 5cm — `00-interfaces.md` §7 설정 표의 near 구간 값 — 나가기 6cm)를 둬서 경계에서 술어가 깜빡이지 않게 한다(추론, 튜닝 대상).
- 시각: 모든 상태에 `t_state`(프레임 번호·시각) — M4·M2와 공유.
- 불확실 표시: 추적 ID 교체 의심 `id_uncertain`, 가려짐 `occluded(since=…)`, T3 술어 `unknown`. Jev는 "모름"을 모름으로 받는다(추측값을 넣지 않는다).

### 4.0 술어 등록부 (모듈 사이 인터페이스, 00-interfaces §11.1) [제안]
- **등록부는 하나다.** M2 계약(`goal`·`assumptions`·`entry`/`exit`/`invariants`/`stop`·`forbidden`), M3 `expected_after`, M6 스킬 계약, M7 채널, M10 규칙은 모두 이 표의 이름만 쓴다. 표에 없는 술어는 M2 `custom_predicates`(허용 DSL)로만 들어오고, 등급은 구성 함수 중 가장 낮은 등급을 따른다.
- **다른 모듈은 이 등록부 인터페이스에만 의존한다.** 후보 A·B·C는 모두 이 등록부의 술어를 낸다(B는 부품 노드 인자를, C는 T3 칸을 더 채울 뿐). 그래서 M1 변환 방법 선택(기본 A, E3 결과로 B·C로 바꿀 수 있음, §7-1)이 다른 모듈 인터페이스를 바꾸지 않는다.
- **(정본 §33) 학습 실행기 B와의 관계**: 공유 M1 앞단(검출·분할·추적)이 대상·관련 물체의 **crop + 마스크**(손목·머리 카메라)를 만들어 학습 실행기(M6 §4.1.4)에 준다. 전체 장면 원본 이미지는 넣지 않는다 [가정]. 실행기가 흡수하는 것은 M1의 "접촉 근처 세밀 기하" 일부뿐이다. **등록부는 바뀌지 않는다**: Jev 입력과 M7 T1 판정은 지금처럼 코드가 계산한 술어다. 선행: HiVLA(2604.14125, MED)의 DiT 액션 익스퍼트가 "global context, high-resolution object-centric crops and skill semantics"를 순서대로 cross-attention한다.
- **이름 규칙**: 수치 인자를 이름·인자에 넣지 않는다(`lifted(o, >=3cm)` 대신 `lifted(o)`, 문턱값은 설정 표). 인자는 ID·부품 ID·`gripper`·`any`만. 부정은 `not p(...)`.
- **등급**: T1 = 코드 기하·고유 감각으로 결정적(히스테리시스 띠 포함) / T2 = 코드지만 임계값 민감(보정·조명·깊이 오차에 흔들림) / T3 = VLM 또는 Astra가 필요. 모든 술어는 값 `true/false/unknown`을 가지며 `occluded`·`id_uncertain`인 물체의 술어는 `unknown`이다.
- **M7 하드 채널(즉시 FAIL)은 T1 술어만 쓴다. T2와 `unknown`은 소프트 채널로만 들어간다**(00-interfaces §11.2). 등급은 이 표의 열이 정본이다.

| 술어 | 뜻(코드 정의 요지) | 등급 | 쓰는 곳(예시 출처) |
|---|---|---|---|
| `exists(o)` | 추적 ID가 살아 있음(가려짐이면 `unknown`) | T1 | M2 `assumptions` |
| `on(a,b)` | a 바닥면이 b 윗면 위, 접촉 + 수직 지지 | T1 | M1, M2 `goal`·`exit` |
| `inside(a,b)` | a 중심이 b 내부 부피 안 | T1 | M1 |
| `above(a,b)` | a가 b 투영 영역 위, 접촉 없음 | T1 | M1 |
| `left_of_robot(a,b)` 등 방향 6종 | 로봇 기준 좌표계 방향(RoboSpatial 어휘, 좌표계 고정) | T1 | M1 |
| `near(a,b)` | 거리 ≤ 5 cm 들어가기 / 6 cm 나가기(00-interfaces §7, 히스테리시스) | T1 | M1, M2 `when` |
| `in_contact(a,b)` | 접촉(기하 간격 ≤ ε 또는 힘 센서) | T1 | M1, M2 `stop`, M7 contact 구간 |
| `touch(o)` | `in_contact(gripper 또는 팔, o)` | T1 | M2 `forbidden` |
| `holding(o)` / `holding(any)` | 그리퍼 폭 + 힘으로 o를 쥠(`held_by_gripper`는 표시 이름) | T1 | M2, M6 `exit`·`invariants`, M7 H1 |
| `gripper_open` | 그리퍼 폭 ≥ 열림 문턱 | T1 | M6 `entry` |
| `lifted(o)` | o가 원래 지지면에서 ≥ `h_lift`(00 §7 설정 표, 초기 3 cm) 떠 있음 | T1 | M2 `exit`, M6 `exit` |
| `upright(o)` / `tilt_ok(o)` | 기울기 ≤ `tilt_max`(00 §7 설정 표, 초기 30°) | T1 | M1, M2 `forbidden`(옛 `tilt(o3)>30deg`) |
| `contact_under(o)` | 쥔 o의 아래면이 놓을 면에 닿음(`in_contact(o, 놓을 면)`) | T1 | M10 규칙, M6 `dp.release` 안전 술어 |
| `aligned(a,b)`, `aligned_xy(a,b)`, `aligned_x(a,b)`, `aligned_yaw(a,b)` | 정렬 오차 ≤ 문턱 | T2 | M1, M6 `stop` |
| `at_pregrasp(o)` | 말단이 o의 사전 파지 자세 허용 오차 안(옛 `dist_to_pregrasp < tol`) | T2 | M6 `stop` |
| `reachable(o)` | IK 해 존재(여유 포함) | T2 | M6 `entry` |
| `clear(o)` | o 위에 다른 물체 없음 | T2 | M1, M2 `assumptions` |
| `top_clear(o)` | o 위쪽 접근 공간이 비어 있음(위 잡기용) | T2 | M10 규칙 |
| `path_clear(a->b)` | 쓸고 가는 부피에 장애물 없음 | T2 | M1, M2 `assumptions` |
| `graspable(o)`, `fits_in(a,b)` | 파지 후보 존재 / 크기 호환 | T2 | M1 |
| `contact_stable` | 접촉 힘 변동이 창(설정 표) 안에서 문턱 이하 | T2 | M6 `reentry` |
| `collision_risk(opt)`, `next_entry_ok(opt)` | 보기 opt의 예상 결과: 충돌 위험 / 다음 스킬 `entry` 성립(코드가 보기마다 계산) | T2 | M6 `expected_after` |
| `failure_evidence_cleared` | M7 사건 문맥의 발동 술어가 모두 정상으로 돌아옴 | 구성 술어의 최저 등급 | M6 `reentry` |
| `open(o)`, `lid_on(o)`, `empty(o)`/`contents`, `material` | 의미 상태·속성 | T3(측정 시각 캐시) | M1, M2 `objects.attrs` |
| `opens`, `part_of`, `can_contain` (간선) | 기능·부품 관계(Astra가 계획 시 적고 코드가 유지) | T3 | 후보 B |
| 문맥 변수 `next_skill`, `stage`, `phase`, `skill` | 술어가 아니라 계약·실행기 상태에서 읽는 값(결정적) | T1(문맥) | M10 규칙 조건, M6 `lookahead_req` |

- 등록부 버전은 M2 계약 검사기와 M10 규칙 키가 같이 고정한다. 새 술어 추가는 오프라인 경로(검사기 목록 갱신)로만.

### 4.1 후보 A (근거 수 1위, **기본**, 정본 §26): **ID 술어 표 + 변화 절**
- 원문 근거: lmgame-Bench(기호 표), OmniParser(번호 목록), FocusAgent·2510.05381(관련 부분만), ViPlan(술어 등급), CaP-X·Read More(변화 서술, 현재 전체 + 이력 diff).
- 구성: `objects`(관련 ID만) / `robot` / `facts`(T1·T2 술어 중 참인 것 + 계약이 이름 붙인 술어는 거짓도) / `changes`(최근 3초, 최대 8개) / `stage`(M2 원장의 현재 단계와 그 `exit`·`invariants` 술어 값).
- 스키마 예(영어, 실제 Jev 입력):
```
t_state: f1287 (t=42.90s)   contract: c7 stage: S2 "place mug o3 on tray o5"
robot: gripper=closed_holding(o3) wrist_force=light arm=moving
objects:
  o3 mug red        | held_by_gripper | upright
  o5 tray blue      | on(table)       | clear=yes
  o8 bottle green   | on(table)       | near(o5)
facts: above(o3,o5)=no  near(o3,o5)=yes  aligned_xy(o3,o5)=no  in_contact(o3,o5)=no
       path_clear(o3->o5)=yes  forbidden: touch(o8)=no
stage S2: exit=on(o3,o5)=no  invariants=holding(o3)=yes  elapsed=normal
changes (last 3s):
  -2.1s near(o3,o5): no->yes
  -0.4s aligned_x(o3,o5): no->yes
```
- 토큰(추정): 관련 물체 3~6개에서 약 150~350 토큰. Jev 한도(state 32k)의 1% 미만.
- **직렬화 정규화 (정본 §28 J2)**: 같은 세계 상태 → **바이트까지 같은 텍스트**. 물체 줄은 id 순, 술어는 등록부(§4.0) 순, 숫자는 고정 구간(고정 자릿수), 시각·나이는 범주(`elapsed=normal` 같은 상대 범주)로 적는다. 공백·구두점·줄바꿈도 고정한다(라벨 앞 공백만으로 정답률 최대 11% — 2509.15020, EMNLP 2025, HIGH). 그래야 같은 입력 반복(test-retest)을 잴 수 있고, 두 Jev 답의 불일치가 상태 변화에서 왔는지 가를 수 있다(M4 J3). 직렬화기 판본은 Jev `question_id@vN` 해시(J1, M3 §4.1)에 들어가므로 직렬화 규칙을 고치면 판본이 오르고 E1 게이트는 재보정 전까지 꺼진다(J4). Astra에 주는 같은 텍스트도 이 정규화를 그대로 쓴다(M2 §4.5 A2). [우리 해석] `t_state`·프레임 번호처럼 매 호출 바뀌는 줄은 세계 상태가 아니라 시각 표지다 — 같은 입력 반복 측정에서는 이 줄까지 같게 둔다(E 문서 §2.3·§2A.3).
- 장점: 결정적, ms 단위, M3 `expected_after`·M4(b)·M7·M9가 **같은 술어 이름**을 쓴다. 단점: 기하로 못 쓰는 상태(뚜껑, 내용물, 천의 모양)는 T3에 기대고 T3는 느리다.

### 4.2 후보 B (근거 수 2위): **작업 부분 그래프 (노드·간선 줄 목록)**
- 원문 근거: Structured Interfaces(부분 그래프 질의 0.77 대 전체 0.33), MomaGraph(공간+기능+부품+상태), ConceptGraphs·HOV-SG(기초).
- A와 다른 점: 물체의 **부품 노드**(`o3.handle`, `o7.drawer_1`)와 **기능 간선**(`o7.handle opens o7.drawer_1`, `o2 can_contain o3`)을 둔다. 부분 그래프 선택 = 계약의 `relevant_ids`에서 k=1 홉.
- 스키마 예:
```
t_state: f1287  contract: c7 stage: S3 "open drawer o7.d1, put o3 inside"
nodes: o3 mug red [held] ; o7 cabinet [static] ; o7.d1 drawer [closed] ; o7.h1 handle [visible]
edges: o7.h1 -opens-> o7.d1 ; o7.d1 -part_of-> o7 ; o3 -fits_in-> o7.d1 (code: yes)
       gripper -near-> o7.h1 ; o3 -above-> table
changes (last 3s): -1.0s gripper near(o7.h1): no->yes
```
- 토큰: A와 비슷하거나 1.2~1.5배(추정). 관절 물체·다단계 과제에서 이득이 기대되고(추론), 단순 pick-and-place에서는 A와 같을 것(v3/04 추론 유지).
- 단점: 부품 분할·기능 간선의 인식 오류원이 늘어난다. 기능 간선은 누가 만드나 → **Astra가 계획 시 1회 적고 코드가 유지**(M2 계약의 `affordances` 칸).

### 4.3 후보 C (근거 수 3위): **A + 영역 캡션 + Astra VDM식 서술 칸**
- 원문 근거: CaP-X VDM(텍스트 차이 서술 > 원시 이미지), OmniParser(캡셔너), DAM(영역 캡션, v3/11).
- A에 두 칸을 더한다: `attrs`(새 ID 등장 시 1회 영역 캡셔너가 쓴 속성: `material=glass, lid=on`, 측정 시각 붙음), `astra_note`(Astra가 **호출됐을 때만** 쓴 한두 문장 서술과 차이 요약, `from t_state=f1100`처럼 기준 시각 붙음).
- 스키마 예(A 뒤에 추가):
```
attrs: o3 {material=ceramic, contents=empty @f1050} ; o5 {surface=flat @f1050}
astra_note (@f1100, age 6.2s): "Mug is held slightly tilted; tray has a raised rim on the far side — approach from the near side."
```
- 장점: 기하로 안 잡히는 의미 정보가 들어간다. 단점: 비결정적, 낡음(age), **길이 증가**(2510.05381의 길이 손실), 자유 서술이 Jev 판단을 흔들 위험. Astra 서술은 M2 계약과 겹친다 → M2와 경계 정리 필요.

### 4.4 대조 조건(후보 아님, E3에만)
- **A-full**: A 형식, 장면 전체 물체·술어(관련 필터 끔). Read More의 "자세한 관측이 나을 수 있다"를 우리 쪽에서 확인.
- **N-num**: 술어 대신 **숫자 좌표**(`o3 at (0.412, -0.108, 0.231) m`). Jev 수치 약점(공식) 확인용 음성 대조.
- **D-only**: 변화 절만(현재 상태 없음). "diff만으로 재구성 금지" 규칙의 근거를 우리 데이터로 확인.
- **V-free**: 코드 술어 없이 VLM(로컬 또는 Astra)이 매 요청 자유 서술. 다른 모듈 전제를 깨는 조건이라 **오프라인 정확도 비교에만**.

### 4.5 지연 예산 (목표값 [제안], 측정 전)
| 단계 | 목표 p50 / p95 | 근거 |
|---|---|---|
| 분할·추적(SAM 3.1, 물체 5~15개) | 30 / 60 ms | v3/11: 이미지 30 ms H200, 3.1 중간 개수 32 FPS H100 — 우리 GPU 미측정 |
| 깊이(Fast-FS 또는 센서) | 30 / 50 ms | 4090 30 ms(논문) |
| 3D 중심·술어 계산(코드) | 3 / 8 ms | 추정 |
| 직렬화(A/B) | < 1 ms | 문자열 |
| **M1 합계(A/B)** | **≤ 70 / 120 ms** | 3Hz 결정 주기(333 ms)의 1/3 이내 |
| C의 영역 캡션(DAM) | 새 ID 때만, 수백 ms~초(미측정) | 루프 밖 비동기, 결과는 다음 요청부터 |
| C의 Astra 서술 | 초~수십 초 | M8이 호출할 때만 |
| Jev 요청(참고) | OpenRouter P50 0.37 s(미국) | M4 E0에서 한국 측정 |
- 규칙: M1이 p95를 넘기면 **직전 상태 + `t_state`를 그대로** 보낸다(나이 표시). M4는 `t_state`로 시간 정렬하므로 늦은 상태가 조용히 섞이지 않는다.

---

## 5. 비교 실험 E3 (오프라인, 판정 기준 사전 등록)

목적: M1 기본 후보 A(Claude 결정, 정본 §26)를 확인하고, B·C로 바꿀 근거가 있는지 본다. 판정 4·5·6에 맞으면 Claude가 기본을 바꾸고 그 사실을 SUMMARY·plan에 적는다.

- **데이터**: E 문서 §1.4·§5.3의 **단일 팔 자작 장면** 스냅샷 풀(00 §13: E0~E3는 자작 장면, 본 평가 RoboDojo와 섞지 않음). E3a = pick-and-place 스냅샷 600개(E §1.5 POOL), E3b = 관절 물체·뚜껑 과제를 장면에 더한 뒤. 스냅샷마다 **시뮬 오라클 정답**이 있는 질문:
  - Q1 목표 선택(M3 G안 `Q_target`), Q2 단계 완료 판정(M7 `exit_k`), Q3 다음 보기(M3 H안 `Q_fine_dir`, 정답 = 오라클 플래너 방향), Q4 계약 위반 여부(금지 술어).
- **조건**: A / B / C / A-full / N-num / D-only / V-free(가능한 스냅샷만). 인식은 두 수준: **오라클 인식**(시뮬 상태) / **실제 인식**(SAM 3.1 + 깊이, 같은 프레임). 인식 잡음 주입 하위 조건: ID 교체 5%, 물체 누락 5%, 깊이 +2cm 편향.
- **Jev 설정**: 버전 고정, 영어, 같은 질문 문구·보기(확률 비교 규칙 #8), 보기 순서 ID 정렬 고정. 호출당 반복 3회(비결정성 측정).
- **문항 균형**(§25 D13, ViPlan 부록 M의 yes/no 편향 관찰): 참/거짓 문항의 정답 yes/no 비율을 맞춘다.
- **지표**: 질문 유형별 정답률(Jev 최빈 보기), **정답이 yes인 문항과 no인 문항의 정확도 분리 보고**, **장면 물체 수별 정확도 곡선**(ViPlan: 물체가 많을수록 하락)(§25 D13), `NONE_ESCALATE` 비율, 입력 토큰, Jev 지연 p50/p95, M1 직렬화 지연 p50/p95, 오류 유형(술어 오류 전파 / Jev 추론 오류) 분해.
- **판정 기준(실행 전 고정)**
  1. **필터 효과**: A가 A-full보다 평균 정답률이 **2%p 이상 낮지 않고** 토큰이 50% 이상 적으면 "관련 부분만" 원칙 유지. A-full이 3%p 이상 높으면 [결정 필요]로 올린다(Read More의 강한 모델 쪽 결과가 Jev에도 성립). 기록할 예상(판정 기준은 바꾸지 않음, §25 D13): 강한 모델은 기호 표 이득이 작을 수 있다(lmgame 2048 gemini −3.1).
  2. **숫자 대조**: N-num이 A보다 Q1·Q3에서 5%p 이상 낮으면 "Jev에 숫자 금지" 규칙을 확정 근거로 기록.
  3. **diff 단독 금지**: D-only가 A보다 Q2에서 10%p 이상 낮으면 규칙 유지(예상). 차이가 3%p 미만이면 변화 절의 가치를 따로 본다(A 대 A-변화 절 제거).
  4. **B 채택 조건**: 관절 물체 과제 하위 집합에서 B가 A보다 5%p 이상 높고, 단순 과제에서 2%p 이상 낮지 않으면 "과제 유형별 B" 제안.
  5. **C 채택 조건**: T3가 필요한 질문(뚜껑·내용물)에서 C가 A보다 5%p 이상 높고, 나머지 질문에서 2%p 이상 낮지 않으면 C 제안. 나머지에서 떨어지면 `astra_note`를 빼고 `attrs`만 남긴 C' 재시험.
  6. **인식 민감도**: 오라클 → 실제 인식 하락폭이 후보 사이에 5%p 이상 차이 나면, 정답률보다 **하락폭이 작은 후보**를 권고 1순위로(환경 일반화 주장과 직결, plan §3).
  7. 모든 비교는 스냅샷 부트스트랩 95% 구간으로 보고, 구간이 겹치면 "차이 없음"으로 적는다.
- **E3 뒤 선택 루프(ACON식, 선택 사항)**: A-full 정답·A 오답 사례를 모아 Astra가 포함 규칙 수정을 제안 → 사람 검토 → 코드 규칙 갱신 → 보류 집합에서 재평가(과적합 방지: 스냅샷 70/30 분할).
- **(정본 §37) E3-ST — 로봇 없이 지금 할 수 있는 스테레오 안정성 시험** [제안]: ROBOTIS 공개 데이터(HF `ROBOTIS/Task_0001` 718편·`Task_0002` 857편, LeRobot v2.1, 10 fps)에 머리 좌우 스테레오 쌍(376×672)이 있다 → Fast-FS → SAM 3.1 → 3D 중심 → 술어의 프레임 간 **안정성**을 잰다. 정답 자세가 없어 정확도는 못 잰다. 한계: mp4 압축이 정합을 해칠 수 있음 [가정], 보정값(기선·내부 행렬)이 데이터에 없음 [미확인]. 프로토콜은 `E-first-experiments.md` §5.10.

---

## 6. 반대 증거와 위험
1. **Read More, Think More**: 강한 모델 두 개(Sonnet 4.6, GPT-5.1 high)에게는 자세한 원본(HTML)이 압축보다 14~17%p 좋았다(같은 상위 묶음의 o3-mini(high)는 −7.6, 모델·추론 예산 의존). "짧게"가 언제나 옳지 않고, "길게"도 언제나 옳지 않다. Jev가 어느 쪽인지 모른다 → E3 판정 1.
2. **lmgame-Bench의 기호 상태는 오라클**이다. 인식 오류가 있는 실제 로봇에서 같은 이득이 난다는 근거는 없다. 표본도 3회(o1·o3는 1회)이고 저자 스스로 "preliminary"라 적었다(§25 D13). ViPlan은 술어 정확도가 많은 모델 계열에서 ≥90%여도 누적 오류로 과제가 무너졌다.
3. **CaP-X VDM은 VLM이 만든 텍스트**이고 가장 강한 VLM(Gemini-3-Pro)으로 상한을 본 것이다. 코드 diff가 같은 효과를 낸다는 근거는 없다(우리 제안).
4. **관련도 목록이 계획 시 1회**라 장면 변화(새 방해물)를 놓칠 수 있다. FocusAgent는 매 스텝 검색한다. 규칙 기반 추가(새 ID, 경로 막음)로 보완하지만 검증 안 됨.
5. **술어 임계값**이 깊이 스케일 오차에 민감(v3/11 위험 7). 히스테리시스는 깜빡임을 줄이지만 판정을 늦춘다.
6. **T3 술어(open, lid_on 등)는 VLM이 해도 90% 미만**(ViPlan에서 VLM의 reachable·nextto도 90% 미만이지만 우리 `reachable`은 코드 IK라 T2다). 코드로 대체할 방법이 없는 과제(천, 액체)에서는 A의 장점이 줄어든다.
7. 텍스트화가 정보를 잃는 문제: 이미지를 본 VLM이 쓸 수 있는 단서(미묘한 기울기, 미끄러짐)가 술어 표에서 사라진다. SpatialEval(텍스트 ≥ 비전)은 기간 밖이고 과제가 다르다.
8. 형식(JSON/줄 표) 효과는 작다는 근거(FloorplanQA ±3%p)가 있지만, 낯선 압축 표기는 손실 보고(TOON/TRON, LOW). 후보 스키마는 흔한 줄 표기로 둔다.

## 7. 열린 질문, [결정 필요]
1. **해소(정본 §26, user-log 25)** M1 변환 방법: **기본 = 후보 A**(Claude 결정), B·C는 E3 비교 조건. 옛 문구 "[결정 필요, 사용자] … 이 문서는 임시 기본값을 두지 않는다(D2 C2, 00-interfaces §11.3)"는 "변환 방법은 사용자가 정한다"(사용자가 한 말이 아님)에 기대던 것이라 폐기. 다른 모듈은 여전히 §4.0 술어 등록부 인터페이스에만 의존한다. E3가 기본 A를 확인한다. 결정되면 다시 볼 목록: M3·M4(b)·M6·M7·M9·M10(등록부 밖 칸을 쓰는 곳).
2. [결정 필요] 코드 술어를 쓰지 않는 방식(V-free)을 후보에서 뺀 것: 다른 모듈 전제 때문이다. 사용자가 VLM 서술 중심을 원하면 M3·M4(b)·M7·M9를 다시 봐야 한다.
3. [결정 필요] 카메라 구성(스테레오 / RGB-D / 단안) — 깊이 1순위와 술어 정확도가 바뀐다(v3/11).
4. 열린 질문: 관련 ID 목록의 주인 — Astra(계획 시) 대 코드 규칙 대 둘 다. 이 문서는 둘 다(합집합)를 제안.
5. 열린 질문: T3 술어를 누가 만드나 — 로컬 VLM(루프 밖), Astra(호출 시), 스킬 센서(뚜껑 열림을 힘으로). 과제마다 다를 것.
6. 열린 질문: 변화 절의 창(3초, 8개)과 술어 히스테리시스 폭은 E3 부수 측정으로 정한다.
7. 해소(정본 §33): 공유 M1 앞단이 학습 실행기에 crop + 마스크를 준다. 술어 등록부·후보 A 기본·E3는 바뀌지 않는다(§4.0). 새 [결정 필요]는 없다.
8. 해소(정본 §36·§37, user-log 37): 3번 카메라 구성(D2c) = **스테레오**(머리 ZED Mini + 손목 D405 × 2). 깊이 = 머리 ZED SDK NEURAL 1순위·Fast-FS 비교(`CUSTOM` 주입), 손목 D405 센서 깊이, SVO 기록(§4 공통 층). 로봇 없이 E3-ST(§5 끝). 새 [결정 필요]는 없다.

## 8. 확인 못 한 것
- lmgame-Bench 학회 채택 여부(abs에 표기 없음)와 저자 소속 본문 확인. Table 1·2 수치는 해소(§25 D13 원문 확인).
- CaP-X Figure 5의 VDM 대 RGB 수치(그림이라 숫자를 뽑지 못함, 방향만 본문 문장으로 확인).
- Read More §3.4 Table 5의 모델별 diff 수치: D2 검증 값으로 채웠다(gemini-2.5-flash budget=128 −6.1, gpt-oss-120b high −2.1). 나머지 셀은 옮기지 않았다.
- ViPlan 부록 M 술어별 정확도 숫자: D2 검증이 Table 17~20에 있음을 확인(HH 약한 모델 nextto 0.12~0.55). 이 문서는 그 요지만 옮겼다. 학회는 EMNLP 2026 Findings로 확인(D2).
- SpatialEval·RoboSpatial·Provence 본문 수치(초록만, 둘은 기간 밖).
- QSTRBench, Lost in Aggregation 본문(초록만).
- 새 문헌의 인용 수·스타(API 금지).
- 로봇 상태 텍스트 diff 대 전체 상태를 같은 조건에서 비교한 연구(찾지 못함, 검색어 0절, 부재 주장 안 함).
- 우리 GPU에서 인식 앞단 지연, 한국에서 Jev 지연.
- (정본 §37, D21) ZED Mini 지연과 Orin에서의 ZED Mini NEURAL FPS, Fast-FS의 Orin 실측, ROBOTIS HF 데이터의 보정값과 라이선스 [미확인].
