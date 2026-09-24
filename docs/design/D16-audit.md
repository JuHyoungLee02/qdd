# D16 독립 감사: 자료·규칙·신뢰도 (user-log 30)

저장 2026-09-24 04:42 UTC. 감사 에이전트 보고 전문. 메인 원문 재확인: 2609.24170 "GPT-6 Astra achieves 22.48% average success rate and 28.97 Score"(22.58은 없음), 2609.22966 Table 4 "GPT-6 Astra … 28.97 22.58"(2차 인용), Table 3(c) "Harness (Gemini 3.8 Flash, zero-shot) … Full 47.0 … w/o grids 32.4" — W1·W2 사실.


저장소 파일은 하나도 고치지 않았습니다. 내려받은 자료는 모두 `D:\tools\audit_d16`에 있습니다(abs/, abs2/, html/, txt/, hf/, gh/). C 드라이브에는 쓰지 않았습니다.
`intent_check.py` 결과는 "total 36 flagged 0"입니다.

## 범주별 건수
| 범주 | 건수 |
|---|---|
| (1) 틀린 자료: 수치·귀속 | 7건 (그중 [불확실] 1) |
| (1) 과장·조건 누락·출처 이름 없음 | 7건 (그중 [불확실] 3) |
| (1) 그림 | 2건 (그중 [불확실] 1) |
| (2) 금지 표현("아무도 재지 않은") | 2건 (docs) |
| (2) [사용자] 줄을 풀어 씀 | 3건 (docs) |
| (2) "high 기본"이 폐기 표시 없이 남음 | 1건 (정본 두 줄, §26이 덮음) |
| (2) M1 철회 줄이 남음 | 1묶음 (research/v3 보관 문서) |
| (2) 신뢰도 규칙: 신뢰도 낮은 출처를 근거로 씀·표기 누락 | 6건 (그중 [불확실] 1) |
| (2) 정본이 "인용한다"고 정한 문헌 누락 | 1묶음 (5편) |
| (2) 기간 규칙 | bib 위반 0. 이름만 쓴 문헌 1건 [불확실] |
| (2) 빨간 줄 | 0 (스크립트 0건, mindmap 빨간 줄 35개를 손으로 대조해도 모두 원문 전체 항목) |
| (2) 계층을 새로움으로 주장 | 0 |
| bib 서지(제목·저자 전원·연도·id) 불일치 | 0 / 31 |

---

## (1) 틀린 자료

**W1. `paper/sec/4_experiments.tex:102`**
- 인용: "같은 Astra도 RoboDojo 자체 평가~\cite{robodojo2026}에서는 22.6\%"
- 문제: 인용한 원문 값은 22.48%입니다. 22.58은 RoboDawn 논문 Table 4가 옮겨 적은 2차 값입니다. SUMMARY.md:81과 D8:15도 이 2차 값(28.97/22.58)을 원문 값처럼 퍼뜨렸습니다.
- 근거: arxiv.org/html/2609.24170 "GPT-6 Astra achieves 22.48% average success rate and 28.97 Score over 2,100 trials"(표 1도 28.97/22.48). arxiv.org/html/2609.22966 Table 4 "GPT-6 Astra Zhang et al. (2026b) 0 28.97 22.58".
- 고칠 점: "22.5%(22.48%)"로 바꿉니다. SUMMARY:81과 D8:15도 고칩니다.

**W2. `3_method.tex:121`**
- 인용: "RoboDawn은 Astra가 cm 단위 숫자로… 성능을 가장 크게 움직인 요인은 격자 같은 공간 근거(빼면 47\%에서 32\%로 떨어짐)와 결정 횟수였다"
- 문제 1: 격자 절제는 Astra가 아니라 Gemini-3.8-Flash의 RoboTwin 0-shot 결과입니다.
- 문제 2: "가장 크게"는 하네스 구성 요소 안에서만 맞습니다. 샷 수(47.0→62.2)와 모델 선택(14.4→73.6)이 더 크게 움직입니다.
- 근거: 2609.22966 Table 3(c) "Harness (Gemini 3.8 Flash, zero-shot) … Full 47.0 … w/o grids 32.4", Table 3(a)(b).
- 고칠 점: "하네스 구성 요소 절제(Gemini-3.8-Flash)에서 격자 제거가 가장 컸다(47.0→32.4)"로 바꿉니다.

**W3. `3_method.tex:304`**
- 인용: "effort는 성공률보다 결정 수와 시간을 바꾼다. Show-Harness에서는 스텝 수가 37에서 30으로 줄었다."
- 문제: 이 수치는 GPT-5.6-sol 조건이고 Astra가 아닙니다. 출처도 논문 본문이 아니라 프로젝트 페이지입니다.
- 근거: docs/research/v3/16-verify-14-15.md:90 "수치는 프로젝트 페이지 … 논문 본문 문장에는 숫자가 없다". plan.md:44 "Show-Harness GPT-5.6-sol".
- 고칠 점: "(GPT-5.6-sol, 프로젝트 페이지)"를 덧붙입니다.

**W4. `1_intro.tex:11`**
- 인용: "순간 판단을 Astra보다 몇십 배 빠르게 내린다"
- 문제: 확인되지 않은 수치를 사실처럼 썼습니다(CLAUDE.md:19 위반). 사용자 발언(user-log 6)을 검정 본문에 단정문으로 옮긴 것입니다. Jev 지연은 아직 재지 않았습니다.
- 근거: SUMMARY:762 "아직 모르는 것: Jev 한국발 지연", E0 계획.
- 고칠 점: "훨씬 빠를 것으로 기대하며 E0에서 잰다"로 바꾸거나 "몇십 배"를 뺍니다.

**W5. [불확실] `4_experiments.tex:102`**
- 인용: 22.6% 대 35.7% → "인터페이스가 점수를 크게 바꾼다는 뜻이다"
- 문제: 두 값은 프로토콜이 다릅니다. RoboDojo Astra는 공식 과제당 50회, 2,100회, effort medium입니다. RoboDawn은 "average results over 5 runs"이고, D8에 따르면 코드상 reasoning을 켠 조건(Astra high)입니다. 인터페이스 효과와 effort·표본 차이가 섞여 있습니다.
- 근거: 두 원문 HTML, D8:10.
- 고칠 점: "(표본 수·effort가 달라 인터페이스 효과만의 차이는 아님)"을 덧붙입니다.

**W6. `3_method.tex:293`**
- 인용: "모델 스스로의 판단은 늦게 울린다는 증거가 있다(낙관 편향)"
- 문제: 문서는 이것을 "사전 가설"로 둡니다. 근거인 BAGEN(심사 전)은 LLM 에이전트의 예산 자기 추정을 잰 연구이고, 트리거 시점을 잰 것이 아닙니다.
- 근거: SUMMARY:397 "사전 가설: T3b는 T3a보다 늦게 발동", D7("BAGEN은 T3b가 늦을 것이라 예측").
- 고칠 점: "늦게 울릴 것이라는 가설이 있다(예산 자기 추정 낙관, BAGEN)"로 바꿉니다.

**W7. `3_method.tex:73`, `:121`**
- 인용: "가장 강한 VLM도 … 50--77\%", "드론 과제에서는 … 7\% … 40\% … 87--100\%", "GUI에서는 반복 이동이 무너졌다"
- 문제: 수치 주장인데 출처 이름도 \cite도 없습니다(ViPlan, SPF, GUI-Cursor).
- 수치 자체는 맞습니다.
  - ViPlan(2505.13180): 50–77%는 GPT-4.1(open 0.50/0.74/0.77)과 GPT-5.2(nextto 0.52–0.73)를 합친 범위입니다.
  - SPF(2509.22653) Table 2: 7 / 40 / 87 / 100(Claude·Llama는 93.3).
- 참고: SUMMARY:195의 "GPT-5.2 open 0.53~0.59"와 D13:121의 "open 0.50~0.77"은 모델이 달라서 둘 다 맞습니다.
- 고칠 점: 세 논문을 bib에 넣어 인용하고, "GPT-4.1·GPT-5.2"를 명시합니다.

**W8. `3_method.tex:195`, `:219`**
- 인용: "지연을 과소 추정하면 되돌릴 수 없는 위치 점프가 생기고…", "20에서 40, 44에서 80"
- 문제: 출처(WAM 2608.01880, Motubrain Team 단일 팀 저자, 조건당 5회, LOW-MED)를 밝히지 않고 설계 근거로 썼습니다.
- 근거: SUMMARY:297·306.
- 고칠 점: "WAM(프리프린트, 조건당 5회)"을 표기하거나 근거 문장에서 뺍니다.

**W9. `3_method.tex:277`, `:304`**
- 인용: "약 9초 동안 갱신되지 않으면", "지연이 1초만 되어도 다음 경계까지 기다리는 쪽이 … 나았다"
- 문제: 문서가 "우리 계산"(180프레임 / ~20 Hz)과 "우리 읽기"(원문은 역전을 직접 말하지 않음)로 표시한 것을 본문에서는 표지 없이 썼습니다.
- 수치 자체는 원문과 맞습니다. 2607.26789 Table S6, d_lat=10: Wait 34.0 대 23.4 / 25.8 / … / 31.4.
- 고칠 점: "(우리 계산)", "(Table S6에서 우리가 읽은 값)"을 붙입니다.

**W10. [불확실] `3_method.tex:240`**
- 인용: "시간 임계값을 정하는 방식은 SAFE를 따른다"
- 문제: SAFE는 실패 점수에 functional CP 시간 가변 띠를 씁니다. 우리 방식은 단계 소요 시간의 conformal 분위수이고, 문서는 이것을 접목으로 적었습니다.
- 근거: SUMMARY:366.
- 고칠 점: "SAFE의 conformal 보정에서 착안"으로 바꿉니다.

**W11. [불확실] `1_intro.tex:13`**
- 인용: "계층 구조와 Astra 로봇 제어~\cite{agp2026,robodojo2026}"
- 문제: RoboDojo Astra 평가는 Astra 단독에 후처리를 붙인 방식이라 계층 선행이 아닙니다. 계층 선행은 JEV-Star입니다.
- 고칠 점: 계층 선행에는 JEV-Star만 붙입니다.

**그림**
- **G1. `figures/overview.png`**: 실행 상자가 "M5 스킬 100 Hz"로 표시되어 있습니다. 본문(3_method:10·192)에서 M5는 스무딩이고 스킬은 M6입니다. "스킬·제어기 + M5 스무딩"으로 고칩니다.
- **G2. [불확실] `figures/m4_commit.png` (c)**: "LAG → 유지"로 되어 있는데, 표 tab:m4rule은 LAG×합의를 "확정, 시각만 뒤로"로 적습니다. 그림에 "(선택 유지, 시각만 뒤로)"를 붙이면 맞습니다.
- 확인한 그림: prelim_drop(35.32/31.40, 20.92/5.82, 21.25/6.98, 17.92/3.04와 백분율이 원문 Table 3과 일치), eval_protocol, failure_timeline(low 약 3 s, high 약 73 s, L1→L2→L3)은 본문·캡션과 맞습니다.

---

## (2) 규칙 위반

**R1. 금지 표현**
- `docs/design/SUMMARY.md:87`: "아무도 재지 않았다(plan §0)". 같은 칸에 RoboJEV 반례(43/50 대 48/50)가 있어 스스로 모순입니다.
- `docs/plan.md:26`: "…를 아무도 재지 않았다".
- 근거: EVAL:153 문구 규칙 3. D15 B5는 tex에서만 고쳤습니다.
- 고칠 점: "통제된 조건의 측정은 찾지 못했고 커뮤니티 관측은 룰이 앞섰다(LOW)"로 바꿉니다.

**R2. [사용자] 줄을 풀어 씀**
- `SUMMARY.md:316` (M6)
  - 문서: "LLM이 스킬을 불러오고 끝이 아니라 잘게 엮는다. 1년 이내 GitHub 스타 상위 5개 논문을 참고해…"
  - user-log:50 원문: "1년 이내에 나온 GitHub 스타 상위 5개 중에서, LLM이 스킬을 불러오고 끝이 아니라 잘게 엮어 놓은 논문을 참고해 파이프라인을 대충 짜 본다."
  - "잘게 엮은 논문을 참고"가 "잘게 엮는다"라는 설계 지시로 뜻이 바뀌었습니다.
- `plan.md:123` (M8)
  - "실패 판정이 나면", "(예: 한 이미지에 프레임 10개)", "(1)(2)(3)", "실패 시 되돌아갈 곳을 정하는 프레임워크를 참고"로 바뀌어 있습니다.
  - user-log:55–57 원문은 "났을 때는", "예: 이미지 하나에 사진 10개", "어떻게 되돌아갈지 정하는 프레임워크를 참고한다"입니다.
  - plan:8은 D11에서 M8을 원문으로 되돌렸다고 적었지만 이 줄은 남아 있습니다.
- `plan.md:21`: [사용자] 줄에 "GPT-6"을 끼워 넣었고, 같은 줄에 Claude 해석("상위 Astra(느림, 계획) / 하위 Jev…")이 섞여 있습니다.
- 고칠 점: 세 곳 모두 user-log 원문으로 되돌리고 해석은 다른 줄로 뺍니다.

**R3. "high 기본"이 폐기 표시 없이 남음 (낮음)**
- `docs/design/00-interfaces.md:121` (§13) "Astra effort 잠정 기본 high…"와 `:148` (§16).
- "뒤 절이 덮는다" 규칙에 따라 §26(:231)이 덮지만, 줄 안에 폐기 표시가 없습니다.
- 다른 남은 줄(SUMMARY:90·155·662·675, plan:45·241, M8:27, M9:169, E-first:358, EVAL:270)은 모두 바로 아래에 폐기·해소 줄이 있습니다.

**R4. M1 철회 줄이 남음 (낮음)**
- `docs/research/v3/11-perception-image-to-text.md:5·91·149`: 91·149행은 "[사용자] … 변환 방법은 사용자가 정한다"로 [사용자] 표지까지 달려 있습니다.
- `research/v3/README.md:58`, `v3/04:173`, `v3/01:185`에도 남아 있습니다.
- 보관 문서이지만 폐기 표시를 붙여야 합니다.

**R5. 신뢰도 규칙: 신뢰도 낮은 출처를 근거로 쓰거나 표기가 빠짐**
- a) `1_intro.tex:15`, `3_method.tex:111`: Type-Safe(2609.26758)
  - 심사 전, 저자 2명, 코드·HF 없음, 09-22 공개 → LOW-MED.
  - 핵심 동기 근거로 쓰였는데 표지가 없습니다.
  - 수치는 원문과 맞습니다: ".94 to .23", ".8146 to .5806", ".5637 → .2782, 52.42%, n=683".
  - 고칠 점: "(심사 전 프리프린트)"를 붙이거나 동기 문장의 무게를 낮춥니다.
- b) `3_method.tex:335`: MemCompiler(심사 전, 코드·HF 없음, MED-LOW)를 Jev 0–2줄 규칙의 근거로 인용했습니다. SUMMARY:749는 이 문헌을 "잠정 근거"로 분류합니다. 표지를 붙이거나 "착상"으로 낮춥니다.
- c) `3_method.tex:195`: WAM(LOW-MED). W8과 같은 건입니다.
- d) `3_method.tex:304`: RPent 92.63%는 "저장소 리더보드"라고 표시했지만, 반드시 함께 적어야 할 조건이 빠졌습니다(SUMMARY:585 "반드시 … 병기").
  - 빠진 조건: LIBERO-PRO T+S 8칸, seed 1–10, 메모리 스냅샷 두 묶음(157/200 + 584/600).
  - 정지형 약 412 s(약 7분)는 적혀 있습니다.
- e) Artificial Analysis 첫 토큰 값(커뮤니티 측정)
  - 표지 없음: `1_intro.tex:7` "약 73초", `3_method.tex:315`, `fig/recovery.tex` 캡션.
  - `3_method.tex:304`는 "공개 측정 … 우리가 잰 값이 아니며"라고 적었지만 출처 이름이 없습니다.
- f) [불확실] `3_method.tex:222` "ROSClaw": 논문이 없는 저장소입니다. 후보가 PlaiPin/rosclaw 625★와 ros-claw/rosclaw 205★ 둘이라 어느 것인지 모호합니다(D8b 미해소).

**R6. 정본이 "인용한다"고 정한 문헌이 빠짐 (중간)**
- SUMMARY:57–63·271·407·590은 다음 인용을 정했습니다.
  - WCD(2609.02159)·SMC(2609.03236): 차별화 문장 옆.
  - EmbodiedSkills(2609.01281): 실행 뒤 확인 선례.
  - PACT(2609.01662): (a)만으로 부족하다는 동기.
  - REFLEX(2609.26532): M8.
- 본문은 RegenHarness만 인용합니다. `3_method.tex:189`의 "Show-Harness와 RoboDawn에도 있으므로" 목록에도 EmbodiedSkills가 빠졌습니다.

**R7. [불확실] 기간 규칙**
- `4_experiments.tex:99` "AGNOSTOS의 LLM 방법"(X-ICM): SUMMARY:772는 이 방법을 "LLM+스킬 1년 창 밖"으로 분류합니다. 본문에 기간 밖 표시가 없습니다.
- bib 31편 가운데 2025-03-23 이전은 gvl2024(2024-11-07) 하나이고, 3_method:240에 "기간 밖, 기초 문헌" 표시가 있습니다.
- LLM+스킬 1년 규칙: CaP-X(2026-03), PhyAgentOS, Zetta, Harness VLA, Show-Harness 모두 창 안입니다.

**R8. 날짜 기준 불일치 (낮음)**
- `2_related.tex:39`와 `plan.md:178`은 "2026-09-22 색인 기준"입니다.
- 정본 §24(SUMMARY:589)는 "2026-09-23 제출분 기준"으로 바꾸라고 했고, intro:20은 09-23을 씁니다.

**R9. [불확실]**
- user-log 30(04:29 UTC: API 일관성 프롬프팅, 1년 반 이내 논문)이 CLAUDE.md, plan, SUMMARY 어디에도 아직 없습니다.
- CLAUDE.md:4는 새 지시를 "바로 이 파일에 추가한다"고 정합니다. 지금 진행 중일 수 있습니다.

**위반 없음으로 확인한 것**
- `\intent` 빨간 줄: 스크립트 0건. mindmap 35줄을 손으로 대조해도 모두 user-log 항목 전체와 같습니다.
- 스크립트의 한계: 문장이 원문의 부분 문자열인지만 보므로, 문장이 빠진 경우는 못 잡습니다.
- 본문 계층 비새로움 문장(intro:13), effort 기본 low(본문·그림), M1 기본 후보 A(본문).

---

## 주요 수치 원문 대조 결과 (맞음)
- **RoboDojo Table 3** (2607.04434): π0.5 20.92/5.82(72.2%), Spatial Forcing 21.25/6.98(67.2%), X-VLA 17.92/3.04(83.0%).
  - 참고: standard 1위 Hy-Embodied(21.98/1.57, −92.9%)는 그림에서 빠졌습니다. 오류는 아닙니다.
- **Astra** (2609.24170): effort medium, 호출 100회. Gen 셀 33.36/30.50은 (35.32+31.40)/2 및 SR 평균과 일치합니다.
- **RoboDawn**: 53.2 / 46.0, 1-shot 73.6, RoboDojo 35.67 / 47.17, 명령 예산 60→240에서 31.2→47.2, 저자 한계 "too coarse".
- **Type-Safe**: 위 R5-a와 같습니다.
- **JEV-Star**: "combining fast JEV action selection with persistent GPT-6 planning", "medium reasoning effort", "at most one per wall-clock second", "nominal 60-game-second interval and at relevant events", "A failed or delayed planning request leaves the previous valid plan available", "not isolated by a controlled ablation".
- **SPF**: 7 / 40 / 87 / 100.
- **CheckVLA S6**: 34.0 대 23.4–31.4.
- **CaP-X H.4**: 68.29 → 65.43.
- **lmgame**: grok-3-mini Sokoban 5.7, "preliminary".
- **ViPlan**: 위 W7과 같습니다.
- **COPE**: 1B 목표형 30.2 / 절차형 23.2 / 없음 25.2, Llama-3B 42.8→53.0.
- **AgentSpec** (2503.18666, 2025-03-24 공개로 창 안): 95.56 / 70.96, 58.62→54.26.
- **Slow Brain**: 1 Hz 기본, 여러 요청 유지, α=λ/(λ+1)·w(Δt).
- **A3**: "cannot identify confidently incorrect predictions".
- **FaRe**: when / where / which.
- **RIR**: When / Where / What.
- **FLARE**: retry·reset 모두 학습형, pose-level 대 environment-level 구분.

---

## 신뢰도 표 (코디네이터 추가 요청)
- 출처: arXiv 댓글·journal-ref, 저자 소속(HTML), GitHub 별(2026-09-24 조회), HF Papers 추천 수.
- HF 추천 수는 약한 신호입니다(RTC도 0).

**bib 31편**

| 키 (arXiv id, 첫 공개일) | 학회 | 소속 | 별 | HF | 등급 |
|---|---|---|---|---|---|
| black2025rtc (2506.07339, 06-09) | NeurIPS 2025 | Physical Intelligence·UC Berkeley | kinetix 611 | 0 | HIGH |
| shukor2025smolvla (2506.01844, 06-02) | 없음 | Hugging Face | lerobot 27.7k | 166 | HIGH |
| fu2026capx (2603.22435, 03-23) | ICML 2026 (저장소 표기) | NVIDIA·UC Berkeley·Stanford·CMU | 819 | 1 | HIGH |
| ouyang2025reasoningbank (2509.25140, 09-29) | ICLR 2026 | Google | 594 | 15 | HIGH |
| zhang2025ace (2510.04618, 10-06) | ICLR 2026 | SambaNova·Stanford | ace-agent/ace 1,332 | 135 | HIGH |
| showharness2026 (2609.10522, 09-09) | 없음 | NUS Show Lab | 452 | 160 | MED |
| zetta2026 (2608.16590, 08-17) | 없음 | Tsinghua AIR | 1,253 | 152 | MED |
| harnessvla2026 (2607.08448, 07-09) | 없음 | Tsinghua 외 | RPent 980 | 0 | MED |
| phyagentos2026 (2607.16636, 07-18) | 없음 | SYSU(Liang Lin) | 2,485 | 0 | MED |
| checkvla2026 (2607.26789, 07-29) | 없음 | Tsinghua SIGS 등 | 코드 없음 | 없음 | LOW-MED |
| budget2026memory (2606.15017, 06-12) | EMNLP 2026 | — | — | — | HIGH |
| memcompiler2026 (2605.07594, 05-08) | 없음 | USTC·Microsoft | 코드 없음 | 없음 | MED-LOW |
| flare2026 (2608.26645, 08-27) | CVPR 2026 | CUHK·SYSU·Tencent 등 | — | — | HIGH |
| kite2026 (2604.07034, 04-08) | ICRA 2026 | — | 11 | 0 | HIGH |
| agnostos2025 (2505.15660, 05-21) | 없음 | HKUST(GZ) | — | — | MED |
| safe2025 (2506.09937, 06-11) | NeurIPS 2025 | UofT | 109 | 10 | HIGH |
| gvl2024 (2411.04549, 2024-11-07, 기간 밖 표시 있음) | ICLR 2025 | Google DeepMind·UPenn | — | — | HIGH |
| agp2026 (2609.12541, 09-11) | 없음 | Notre Dame | 14 | 17 | LOW-MED |
| robodojo2026 (2609.24170, 09-21) | 없음 | RoboProbe·Tsinghua·Princeton 등 | RoboProbe 21 | 0 | MED-LOW (공개 직후) |
| eventtrig2026 (2609.22587, 09-18) | 없음 | TUM·MBZUAI | — | — | MED-LOW |
| vlash2025 (2512.01031, 11-30) | 없음 | MIT Han Lab·NVIDIA | 504 | 28 | MED-HIGH |
| a2c2 (2509.23224, 09-27) | 없음 | U Tokyo Matsuo Lab | — | — | MED |
| lipo2025 (2506.05165, 06-05) | 없음 | Kwangwoon, 저자 2명 | 코드 없음 | — | LOW (본문은 비교 대상으로만 써서 문제 없음) |
| slowbrain2026 (2606.20458, 06-18) | 없음 | Amazon FAR·UCLA | 코드 없음 | — | MED-LOW (인정할 선행) |
| criticloop2026 (2603.05185, 03-05) | 없음 | CASIA | 코드 없음 | — | LOW-MED (비교 조건) |
| jevstar2026 (2609.27331, 09-23) | 없음 | CASIA·Beijing Zhongguancun Academy | 33 | — | LOW-MED (필수 인정 선행) |
| typesafe2026 (2609.26758, 09-22) | 없음 | NUS·Fudan, 저자 2명 | — | — | LOW-MED (근거로 사용 → R5a) |
| a3commit2026 (2605.11567, 05-12) | 없음 | Monash·Imperial 등 | 6 | — | MED-LOW (필수 선행) |
| robodawn2026 (2609.22966, 09-19) | 없음 | Tsinghua(Shi-Min Hu)·Tencent Hunyuan | 12 | 106 | MED |
| regenharness2026 (2609.27612, 09-23) | 없음 | — | — | — | LOW (계열 선례로만 써서 문제 없음) |
| robodojobench2026 (2607.04434, 07-05) | 없음 | 44인 다기관 | 621 | 15 | MED-HIGH |

**본문에 이름만 나오거나 근거로 쓰인 비인용 문헌**

| 문헌 | 학회·소속 | 별 / HF | 등급 | 본문에서의 쓰임 |
|---|---|---|---|---|
| lmgame-Bench (2505.15146) | UCSD·Berkeley, 저장소는 ICLR 2026 표기 | 981 / 20 | HIGH | "예비" 표시 있음 |
| BALROG (2411.13543) | ICLR 2025, UCL | 272 / 19 | HIGH | 기간 밖 표시 있음, 근거로 쓰지 않음 |
| ViPlan (2505.13180) | EMNLP 2026 Findings | — | HIGH | 이름 없음 |
| SPF (2509.22653) | CoRL 2025 | — | HIGH | 이름 없음 |
| GUI-Cursor (2509.21552) | ICML 2026 | — | HIGH | 이름 없음 |
| FIPER (2510.09459) | NeurIPS 2025, TUM | 55 | HIGH | — |
| COPE (2506.11578) | TMLR 2026, KAIST | 3 | HIGH | — |
| SEAM (2607.04609) | 없음, 저자 4명 | — | LOW-MED | — |
| WAM (2608.01880) | 없음, Motubrain Team | — | LOW-MED | 근거로 사용 → W8·R5c |
| FaRe (2609.18016) | 없음 | HF 없음 | MED-LOW | 설계 정리용이라 문제 없음 |
| RIR (2609.18304) | 없음 | HF 없음 | MED-LOW | 설계 정리용이라 문제 없음 |
| BAGEN (2606.00198) | Northwestern 외, 없음 | — | MED | "증거"로 씀 → W6 |
| REFLEX (2609.26532) | NTU·Singapore, 저자 2명 | HF 0 | LOW | 본문에 없음 → R6 |
| RoboFind (2609.20330) | KIT | — | MED | 본문에 없음 |
| Jev-as-Policy / RoboJEV | 저장소 | 37★ / 3★ | LOW | "커뮤니티·신뢰도 낮음" 표시 있어 문제 없음 |
| RPent 리더보드 | 저장소 | — | — | 조건 누락 → R5d |
| Artificial Analysis | 커뮤니티 측정 | — | — | 표지 누락 → R5e |

---

## bib 서지 확인 결과
arXiv abs 31건을 3초 간격으로 받아 대조했습니다. 31편 모두 제목, 저자 전원과 순서, 연도, arXiv id가 맞습니다. 유일한 차이는 slowbrain2026 첫 저자 이름의 별명 표기("Zhenghao 'Mark' Peng")뿐입니다.

확인한 키: black2025rtc, shukor2025smolvla, fu2026capx, ouyang2025reasoningbank, zhang2025ace, showharness2026, zetta2026, harnessvla2026, phyagentos2026, checkvla2026, budget2026memory, memcompiler2026, flare2026, kite2026, agnostos2025, safe2025, gvl2024, agp2026, robodojo2026, eventtrig2026, vlash2025, a2c2, lipo2025, slowbrain2026, criticloop2026, jevstar2026, typesafe2026, a3commit2026, robodawn2026, regenharness2026, robodojobench2026.

- 첫 공개일은 위 신뢰도 표에 적었습니다.
- 2025-03-23 이전 항목은 gvl2024 하나이고, 인용 자리에 "기간 밖, 기초 문헌" 표시가 있습니다.
- bib 항목은 모두 본문에서 인용되고 있습니다. 반대로 본문 인용 키 가운데 bib에 없는 것도 없습니다.

## 참고 파일
- 감사 대상: `D:\qdd\paper\sec\1_intro.tex`, `D:\qdd\paper\sec\3_method.tex`, `D:\qdd\paper\sec\4_experiments.tex`, `D:\qdd\paper\figures\overview.png`, `D:\qdd\paper\figures\m4_commit.png`, `D:\qdd\docs\design\SUMMARY.md`, `D:\qdd\docs\plan.md`, `D:\qdd\docs\design\00-interfaces.md`, `D:\qdd\docs\design\D8-robodawn-a3-deepread.md`
- 내려받은 자료: `D:\tools\audit_d16\`
