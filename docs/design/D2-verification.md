# D2 검증: M1·M2·M6·M10 새 출처 원문 대조 + 정본·모듈 사이 일관성 + 사용자 의도

- 작성: 2026-09-24, 독립 검증 에이전트(이번 라운드 외부 API 단독 사용).
- 읽은 것: `design/README.md`, `00-interfaces.md`(정본), `M1`·`M2`·`M6`·`M10`, 대조용 `M4`·`M7` 해당 절, `user-log.md` 3·11항, `D:\qdd\CLAUDE.md`, `plan.md` 63·103행.
- 방법: arXiv abs 약 40편(2.2초 간격, 제목·첫 공개일·comments·journal-ref), arXiv HTML 본문 15편(표·절 직접 대조), ACL Anthology 2026.acl-long.27 페이지, MCP 2025-06-18 Tools 명세 페이지 + `schema.ts`(raw 파일, API 아님), agentskills.io/specification. Semantic Scholar batch 1회(인용 수, 2026-09-24 측정). arXiv 검색 API·GitHub API 쓰지 않음.
- 판정 기호: **맞음** / **정정 필요**(문서 문장이 원문과 다름) / **조건 보완**(맞지만 조건이 빠져 과장 위험) / **학회 미확인**.
- "새 출처" = `docs/research/v3/*.md`에 arXiv 번호가 없는 것. GPSFSM(v3/07)·SkillsBench(v3/03)는 v3에 있으나 요청 우선 목록이라 함께 봤다.

---

## Part A. 원문 대조

### A1. 우선 목록 (본문 표·절까지 확인)

| 출처 | 첫 공개 / 기간 | 학회(원문 표기) | 인용(S2) | 문서 주장 → 판정 | 원문 위치·근거 |
|---|---|---|---|---|---|
| **FocusAgent** 2510.03204 (M1) | 2025-10-03 / 안 | **TMLR 08/2026** (comments) — 맞음 | 15 | 53.6 대 53.2: **맞음**(Table 1·2, WorkArena L1, GPT-4.1 백본, 검색기 GPT-5-mini, 가지치기 61%). "50~63% 가지치기": **맞음**(Table 1 FocusAgent 변형 56~63%, Table 2 GPT-4.1 51~61%·Claude-3.7 50~51%). "BM25·임베딩은 **200줄** 단위에서 42~46": **정정 필요** → 200 **토큰** 청크, 42.4~45.8(Table 1). "성공률 거의 유지": **조건 보완** — 강한 검색기(5-mini)일 때만. qwen3-8b 검색기는 43.9(−9.7p), 본문 "retrieval is highly dependent on the retriever LLM capability"(Table 1 아래 문단) | Table 1, Table 2, §5 본문 |
| **ACON** 2510.00615 (M1) | 2025-10-01 / 안 | **ICML 2026** — 맞음 | 98 | AppWorld 최대 토큰 −25% 이상 정확도 유지, 8-목표 QA −54.5%에 EM/F1 상승(§4.2), o3+대조 피드백 최선(§4.5, Table 3): **모두 맞음**. 대조 부분집합 정의("압축 없이 성공·압축으로 실패")도 §3.3과 일치. 참고: 초록 전체 범위는 26~54% | §3.3, §4.2, §4.5 Table 3 |
| **ViPlan** 2505.13180 (M1) | 2025-05-19 / 안 | **EMNLP 2026 Findings** (journal-ref) → M1 "학회 미확인": **정정 필요** | 9 | leftOf·rightOf·on 거의 완벽, clear 더 어려움, nextto·open·reachable 최강 모델도 <90%, 최대 120개 술어: **맞음**(§5 본문, 부록 M Table 17~20, Figure 16). 46% 대 9%(BW), 5% 대 34%(HH): **맞음**(초록·Table 1, 모델 평균). "술어 정확도가 대체로 ≥90%": **조건 보완** — 원문은 "≥90% for many model families"(부록 개별 결과 절)이고 HH에서는 약한 모델 nextto 0.12~0.55(Table 19). M1 §8 "부록 M 숫자 못 봄"은 Table 17~20에 있음 | §5, App. M Table 17–20, Fig. 16 |
| **Read More, Think More** 2604.01535 (M1) | 2026-04-02 / 안 | comments 없음 → **학회 미확인** 유지 | 4 | Table 1 수치(6,720 / 56,653 토큰, GPT-5.1 high 55.8→73.3, Sonnet 4.6 52.4→67.0, gpt-oss-20b high 46.4→27.6, Llama-3.1-70B 18.2→3.6): **모두 맞음**. "+14~17%p"(M1 §6-1): **조건 보완** — 두 모델(Sonnet 4.6, GPT-5.1 high)만. 같은 "상위 능력" 묶음의 **o3-mini(high)는 −7.6**, gemini budget=128은 +6.0. "강한 모델은 HTML이 낫다"는 모델·추론 예산 의존. §3.4 diff: **맞음**(토큰 39,011→13,670 ≈ 35%, gpt-5.1 low 50.9→53.3, o3-mini 43.3→46.1). 단 **gemini-2.5-flash budget=128은 diff가 full보다 −6.1(39.4→33.3)**, gpt-oss-120b high −2.1 — M1 §8 "Table 5 못 봄"은 위 값으로 채울 수 있음 | Table 1, Table 5, §3.4 |
| **AgentSpec** 2503.18666 (M2) | 2025-03-24 / 안(경계 +1일) | **ICSE 2026**, Proc. ICSE'26 pp. 2938–2950 — 맞음 | 221 | 트리거+술어+집행, 코드 >90% 차단, 체화 위험 행동 전부 제거: **맞음**(초록, §1). **조건 보완**: 이 수치는 **사람이 쓴 규칙** 기준. **LLM(o1)이 생성한 규칙은 체화에서 정밀도 95.56%·재현율 70.96%**(초록·§1). M2는 Astra가 규칙(`forbidden`)을 쓰므로 이 재현율 수치가 더 가까운 근거 | 초록, §1, §3.2 |
| **PlanAhead** 2605.29927 (M2) | 2026-05-28 / 안 | "submitted to EMNLP, waiting for acceptance" → 학회 미확인 — 맞음 | 0 | 4형식, 3모델, 158 Hard, N=5, 모델마다 최적 형식 다름(GPT-4.1-mini 서사, Qwen 체크리스트, Gemini 의사코드), 정적 > 동적 자주: **맞음**(§3, §4). **정정 필요**: "Table 4: 4.1-mini 체크리스트 32.5~84.0" → 이 구간은 **Table 5(STC, 해결 과제 일관성)**. **Table 4(AR)** 의 같은 칸은 **1.20~4.79**. 저자는 "AR 추정은 매우 안정적(highly stable)"이라 씀 → "부트스트랩 구간이 넓다"는 STC에만 해당. 추가 조건: Hard 과제 AR 절대값이 **약 1~11%**로 매우 낮다 | §3, §4 Table 1, App. B Table 4·5 |
| **Magentic-One** 2411.04468 (M2) | 2024-11-07 / **기간 밖** 표시 맞음 | comments 없음 | 273 | 과제 원장(사실·찾을 사실·유도·추측·계획), 진행 원장 다섯 질문, 정체 카운터 ≤2 → 바깥 고리: **맞음**(§3 워크플로 본문, Fig. 2) | §3 |
| **GPSFSM** 2607.15674 (M6) | 2026-07-17 / 안 | **IROS 2026 채택**(comments) — 맞음 | 0 | 사건 촉발 전이, Sequential/Recovery/Parallel-Any/All, Capabilities2 파라미터·사건: **맞음**(§III). "BTGenBot보다 계획 생성 성공률 **일관되게** 높음": **정정 필요** — GPT 모델에서는 Fabric 90% 성공·10% 부분 대 BTGenBot 54/11/34%, **로컬 모델에서는 BTGenBot이 더 나음(13/35/52 대 10/22/68)**. 5개 항법 과제, 사람 평가자 3명 판정 | Table I, §IV 본문 |
| **BATON** 2608.16889 (M6·M10) | 2026-08-17 / 안 | comments 없음 → 심사 전 — 맞음 | 1 | exit만 있고 entry 없음, invocation(손목 카메라 확인 뒤 VLA 호출)·handoff·lookahead, 파라미터 갱신 없음, RoboMemArena +11.6·+14.9, "Edges are keyed by transition type rather than by task": **모두 맞음**(초록, §1·§3 본문 문장). 초록은 "%", 본문은 "points" — %p로 읽는 게 맞다. USC 소속 확인 | 초록, 본문 전이 절, 메모리 절 |
| **Agent Skills 명세** (M6) | 명세(날짜 2025-12-18은 2차 출처) | 표준 | — | name ≤64자(소문자·숫자·하이픈), description ≤1024, 선택 license·compatibility(≤500자)·metadata(문자열→문자열 맵)·allowed-tools(실험), 점진 공개 ~100 / <5000 / 필요 시, 본문 500줄 이하: **맞음**. 누락: 선택 필드 `license`. `metadata`의 `harvest.version` 키 사용은 명세 허용 범위(고유한 키 이름 권장) | agentskills.io/specification |
| **MCP 2025-06-18** (M6) | 2025-06-18 / 안 | 표준 | — | inputSchema, outputSchema(있으면 서버 MUST 준수), `isError` 대 프로토콜 오류, 힌트 4종, "untrusted": **맞음**. **조건 보완**: 클라이언트 검증은 **SHOULD**(권장)이지 "해야 함"이 아님. 명세 문장은 "clients MUST consider tool annotations to be untrusted unless they come from trusted servers", schema.ts는 "Clients should never make tool use decisions based on ToolAnnotations received from untrusted servers". 기본값 주의: `destructiveHint` 기본 true, `idempotentHint` 기본 false, 둘 다 `readOnlyHint==false`일 때만 의미. 접목 주의(우리 판단): idempotent(같은 인자로 반복 호출해도 추가 효과 없음)는 로봇 접근·정렬 단계에서 대개 성립하지 않으므로 `retry_safe`로 옮길 때 뜻이 바뀐다 | Tools 절 "Output Schema"·"Error Handling"·annotations, schema.ts ToolAnnotations |
| **2505.16067** Experience-following (M10) | 2025-05-21 / 안 | **ACL 2026 long**: ACL Anthology 2026.acl-long.27 페이지를 열어 제목 일치 확인 → 맞음(M10 §8 "페이지 미열람"은 해소). S2 venue도 ACL | 97 | Table 1 네 열 값(고정 67.53/16.75/40.11/71.50, 전부 추가 55.48/13.05/32.32/59.90, 엄격 70.95/38.50/51.00/85.40): **맞음**. 지표: RegAgent SR, EHRAgent ACC, AgentDriver SR, CIC-IoT ACC. "엄격 = 사람 판정": 맞음(Table 1 캡션). Table 2 "이력 기반 삭제 + 엄격 판정이 대개 최고, 결합 삭제가 메모리 최소": **맞음**(캡션). **조건 보완**(M10 접목): 원문 삭제 규칙은 "**n회 이상 꺼낸 뒤** 평균 효용 ≤ β"(§4.1). M10의 "실패 수 > 성공 수" 규칙에는 최소 꺼냄 횟수 n이 없다 | Table 1, §4.1, Table 2 |
| **Proactive Memory Agent** 2607.08716 (M10) | 2026-07-09 / 안 | comments 없음, 심사 전 — 맞음. Meta AI 소속 확인 | 3 | +8.3pp(Terminal-Bench 2.0), +6.8pp(τ², 과제 가중): **맞음**. **조건 보완 3가지**: (1) 두 수치는 **약한 행동 에이전트 Sonnet 4.5**일 때. Opus 4.6은 +2.4/+2.5(Table 1). (2) "고정 주기": 실험 설정은 **첫 스텝과 이후 매 스텝** 실행(§4.1). (3) "선택적 개입이 항상 주입보다 나음": **macro 평균에서만**. micro에서는 Always inject가 0.3p 앞섬(저자: 실행 분산 이내, §4.3 Table 2). "always-on injection can be competitive but less balanced"는 원문 그대로가 아닌 요약. 또 이 메모리는 **한 과제 안(실행 중)** 메모리이고 에피소드 사이 경험 축적이 아니다 → M10 출력 A에 옮길 때 범위 차이 명시 필요 | Table 1, §4.1, §4.3 Table 2 |
| **PragmaBot** 2507.16713 (M10) | 2025-07-22 / 안 | **RA-L 채택**(comments) — 맞음. S2 venue RA-L | 3 | STM 35→84%, 12개 실물 시나리오(8개 처음) 단일 시도 22→80%, RAG > 통째 프롬프트: **맞음**(초록, Table II·III, §V-D). **조건 보완**: (1) 22%는 **다른 방법(COME, LTM 없음)** 기준이지 같은 시스템의 LTM 끔이 아니다. (2) LTM 100항목 중 **96개는 단순 과제의 교시용(instructional) 경험**이고 과제에서 얻은 것은 4개(§V-C). 따라서 M10 §2.2·§6의 "VLM 자기 판정 라벨로도 실물 22→80%"는 **정정 필요** — 이득의 대부분을 자기 판정 라벨로 돌릴 수 없다. (3) RAG 대 전체 LTM은 **첫 행동 정확도** 89% 대 74%(실행 없음, Fig. 7) | 초록, §IV-D, §V-C, Table III, Fig. 7 |
| **GEPA** 2507.19457 (M10) | 2025-07-25 / 안 | **ICLR 2026 (Oral)** — 맞음 | 391 | GRPO 대비 평균 +6%, 최대 +20%, 롤아웃 최대 35배 적음, MIPROv2 +10% 이상: **맞음**(v2 초록). **조건 보완**(M10 접목 표): GEPA의 Pareto는 "**문제 인스턴스별 최고 후보들을 남겨 거기서 뽑는** 다양성 장치"(§3.1)이다. M10의 "어느 시드에서도 성공률을 떨어뜨리지 않는 것만 채택"은 **비열화 제약**으로 뜻이 다르다. 이름만 빌린 것임을 적어야 한다 | 초록, §1, §3.1 |
| **2604.27003** (M10) | 2026-04-29 / 안 | "Working in progress" — LOW-MED 표기 맞음 | 4 | ReMe, ALFWorld·BabyAI, Insight 양의 전이·Raw 음의 전이(A→B), 음의 전이는 어려운 사례에 집중, 세밀도·빈도 비단조, 오염 3종, 적응-망각 상충: **맞음**(§3.2, §4, 초록 기여 목록). 수치 예: A→B ALF Raw 80.5→71.0(FWT −9.5), Insight 65.5→72.0(+6.5). **조건 보완**: B→A ALF는 Insight도 −2.5 → "Insight는 양의 전이"는 방향·환경 의존 | Table(Study 1), §3.2, §3.4 |
| **SkillsBench** 2602.12670 v4 (M6·M10) | 2026-02-13 / 안 | comments 없음(v3/03에서 "반응 HIGH") | S2 미포함(요청 목록 밖) | −8.1 ~ −11.5pp: **맞음**(v4 본문: Claude Code+Opus 4.7 −8.1, Codex+GPT-5.5 −11.3, Gemini CLI+Gemini 3.1 Pro −11.5). 조건: 에이전트가 **skill-creator로 스킬 팩을 먼저 만들고 그 팩만으로 풀이**(부록 D.6). 같은 설정에서 **사람이 다듬은 스킬은 +18.2 ~ +24.8pp** — M6 (a')·(c) 쪽 근거로 함께 적을 가치가 있다 | 본문 self-generated 문단, App. D.6 |

### A2. 나머지 새 출처 (abs 페이지·초록 대조)

| 출처 | 첫 공개 | 학회 표기 | 인용(S2) | 판정 |
|---|---|---|---|---|
| lmgame-Bench 2505.15146 (M1) | 2025-05-21 | 없음 | 43 | 학회 미확인 유지. 수치 인용 없음 — 맞음 |
| Lost in Aggregation 2606.22219 (M1) | 2026-06-20 | 없음 | 0 | 1,050 미로, 10×10에서 거의 0, 단일 수준 30~75%, 첫 오류 59% 분기·1% 전역: **맞음**(초록). 추가 조건: 오류 분석은 multi-hot, 지각(Fine) 39%도 큼 |
| QSTRBench 2605.18380 (M1) | 2026-05-18 | 없음(74쪽) | 0 | 학회 미확인. 수치 인용 없음 |
| Complexity Trap 2508.21433 (M1) | 2025-08-29 | NeurIPS'25 DL4C 워크숍 — 맞음 | 32 | "비용 절반, 요약과 같은 해결률": **맞음** |
| SWE-Pruner 2601.16746 (M1) | 2026-01-23 | 없음 | 37 | 23~54% 감소, 성공률 상승: **맞음** |
| Signal-Driven Observation 2606.06708 (M1) | 2026-06-04 | **ICML 2026 FAGEN 워크숍** — 맞음 | 0 | 입장 논문, 서술 맞음 |
| A11y-Compressor 2605.00551 (M1) | 2026-05-01 | ACL SRW 2026 — 맞음 | 0 | 22%, +5.1%p: **맞음** |
| ScreenParse 2602.14276 (M1) | 2026-02-15 | ICML 2026 — 맞음 | 3 | PageIoU 0.592 대 0.294: **맞음** |
| MoA→BT 2603.01113 (M6) | 2026-03-01 | 없음 | 0 | 사람 응답 약 27% 감소: **맞음**. 조건: **칵테일 만들기 한 과제** |
| SkillWrapper 2511.18203 (M6) | 2025-11-22 | 없음 | 0 | "provably sound and complete": 맞음(초록). 학회 미확인 |
| Agent Skills 서베이 2602.12430 (M6) | 2026-02-12 | Agent Skills '26 워크숍 @ ACM CAIS 2026 — 맞음 | 99 | 26.1% 취약, 4단 게이트: **맞음**. 조건: 26.1%는 서베이가 인용한 다른 연구의 수치 |
| Video-to-BT 2509.16611, 2606.10808, Wake 2501.03968 (M6) | 2025-09-20 / 2026-06-09 / **2025-01-07(기간 밖 표시 맞음)** | 없음 | —/—/10 | M6 §0 읽음 목록. 표 인용 없음 또는 기간 밖 표시 맞음 |
| Training-Free GRPO 2510.08191 (M10) | 2025-10-09 | 없음 | 50 | 학회 미확인 — 맞음 |
| 2604.14004 (M10) | 2026-04-15 | Preprint | 2 | 평균 +3.7%: **맞음**. "추상 통찰 전이" 방향 맞음(메타 지식·검증 루틴) |
| 2511.21730 (M10) | 2025-11-21 | 없음 | 2 | 임베딩 새 문맥에서 급락, LLM 절차 추상 전이: **맞음** |
| 2606.29774 (M10) | 2026-06-29 | 없음 | 1 | 거친→세밀 구조 검색 > 비구조·임베딩: **맞음**(초록) |
| 2606.20978 (M2) | 2026-06-18 | ICML 2026 DL4C 워크숍 — 맞음 | 0 | 76.7→90.7%: **맞음**. 조건 보완: **과제 43개**(모호한 지시), 순열 검정 |
| 2608.02645 (M2) | 2026-07-31 | 없음 | 4 | 중복 감소·성공률 비슷, 시뮬 주입 실패: **맞음** |
| Memento 2508.16153 (M10 §8) | 2025-08-22 | 없음 | — | 표에 넣지 않음 — 처리 맞음 |
| 기간 밖 표시 대상: SpatialEval 2406.14852(NeurIPS 2024), RoboSpatial 2411.16537(CVPR 2025 Oral), Provence 2501.16214(ICLR 2025) | 2024-06 / 2024-11 / 2025-01 | 모두 comments와 일치 | — | 기간 밖 표시·학회 **맞음** |

### A3. 신뢰도 표기 갱신 제안 (인용 수, S2 2026-09-24)
- ViPlan: "MED, 학회 미확인" → **EMNLP 2026 Findings, 인용 9**.
- 2505.16067: 인용 97, ACL 2026 확인 완료.
- AgentSpec 221, GEPA 391, Magentic-One 273, ACON 98, FocusAgent 15, lmgame-Bench 43.
- 인용 0~4: PlanAhead 0, GPSFSM 0, BATON 1, PragmaBot 3, Proactive MA 3, Read More 4, 2604.27003 4. 이 중 **BATON(1)은 M6 계약 필드(`entry`·`lookahead_req`)와 M10 검색 키 1순위를 좌우**한다(A·C 참고).

---

## Part B. 정본(00-interfaces.md)·모듈 사이 일관성

| # | 위치 | 모순 | 제안 |
|---|---|---|---|
| B1 | M2 `decision_points[].qid` 대 M6 `decision_points` 대 M10 키 | M2는 **Astra가 단계마다** 결정 지점을 쓰고 id가 단계 범위(`S1.target_part`, `S2.fine`). M6는 **스킬 계약에 고정된** 전역 id(`dp.approach_dir`, `dp.release`). M10 Jev 규칙 키는 `(skill_id, dp_id, 술어)` 정확 일치라 **M6 id만 가정**한다. M2 식 id면 에피소드마다 이름이 달라 규칙이 한 번도 맞지 않는다. M2 §7-3은 [결정 필요]로 올렸으나 M6·M10에는 그 결정이 걸려 있다는 표시가 없다 | 00-interfaces에 "결정 지점 id = 스킬 계약의 전역 id, Astra는 인스턴스(인자·트리거)만 채움"처럼 한 줄로 정하거나, 세 문서에 같은 [결정 필요]를 건다 |
| B2 | M2 `stages[]` 대 M6 `contract.json` 필드 이름 | 같은 개념 이름이 다르다: `pre`↔`entry`, `done`↔`exit`, `inv`↔`invariants_by_phase`, `T_exp_s`↔`budget`(단계별), `substeps`(approach·align·**lower·release**)↔`phases`(approach·align·**grasp·lift**), `stop`(단계 술어 목록)↔`stop`(phase별 식). M7 입력은 `pre_k`·`done_k`·`inv_k`(M2 쪽 이름) | 정본에 필드 대응표 추가(스킬 계약 = 스킬 불변, 세션 계약 단계 = 스킬 인스턴스) |
| B3 | M6 술어 대 M1 어휘 대 M2 검사기 | M2 검사기 2번은 "모든 술어 이름이 M1 어휘 또는 `custom_predicates` 안"이어야 통과. M6 예시의 `gripper_open`, `lifted(target, >=3cm)`, `aligned_yaw`, `dist_to_pregrasp < tol`, M2 예시의 `lifted`, `touch`, `exists`, `tilt(o3)>30deg`, M10 규칙의 `top_clear`, `contact_under`, `next_skill`은 **M1 T1/T2/T3 목록에 없다**. 수치 인자가 붙은 술어(`>=3cm`)는 M2 DSL 형식과도 다르다 | M1 어휘 표를 정본 부록으로 올리고 세 문서 예시를 거기에 맞춤 |
| B4 | M1 술어 등급(T1/T2/T3, `unknown`, `id_uncertain`, `occluded`) 대 M7 채널 | M7 하드 층 H1(불변 위반 2틱)·H3(`pre_k` 거짓)은 **등급을 구분하지 않는다**. M6 스킬 `entry`의 `reachable(target)`은 M1 **T2(임계값 민감)**, M1 권고상 불확실하면 `unknown`. `unknown`·`occluded`가 H3에서 거짓으로 계산되면 즉시 FAIL → 오경보. 정본 §4에도 규칙 없음 | 정본 §4에 "하드 층은 T1만, T2는 히스테리시스 후, T3·unknown은 소프트 채널 또는 M8"을 한 줄로 |
| B5 | M2 `assumptions` → "M7 신호(소프트 채널 후보)" | 정본 §4·M7 §4의 소프트 채널은 C_stag·C_dead·C_jev·C_m4·C_flip뿐. `C_assume` 같은 채널은 정의되지 않았다. M2 R4는 "코드가 M8을 부른다"고 해 FAIL 없이 Astra를 부르는 경로가 된다(정본은 M8 호출 경로를 M7 FAIL/WARN으로 적음) | 가정 거짓 = M7 소프트 채널 추가 또는 M8 (2)/(3) 호출 사유로 명시 |
| B6 | M2 R2 계약 교체 → `premise_epoch` 증가 대 M4 | M4 §4.2는 epoch를 DEVIATE·CONTRADICT에서만 올리고, 계약 변경 epoch 증가는 M4 §7-6 **열린 질문(제안)**. M4 `premise_epoch` 정의("확정 접두부 + 예상 상태 버전")에 계약 버전이 없다. 정본에는 이 규칙이 없다. 방향은 같지만 확정 안 됨 | 정본 §5에 "계약 버전 교체 = epoch +1"을 넣거나 [결정 필요]로 |
| B7 | M2 R3 대 M4 FROZEN·정본 §5 | R3 "결정 스텝 경계에서만 교체, FROZEN 건드리지 않음"은 정본 §5와 맞음. 단 "`irreversible` 단계 진행 중이면 그 하위 단계 끝까지 기다린다"는 M2 단계 수준 `irreversible`을 쓰고, M6는 phase 수준 `annotations.irreversible_phases`(스킬 작성자) + "코드 안전 규칙이 최종". 누가 되돌릴 수 없음을 정하나가 두 곳 | M2 §7-4와 M6 annotations를 한 [결정 필요]로 묶음 |
| B8 | M6 §4.1.3 `default_on_timeout` = "현재 단계 유지 + **안전 대기**" | 정본 §4: 정지 허용은 T0와 M9 L3뿐, 나머지는 "직전 확정 행동 유지 + 감속". "안전 대기"가 정지를 뜻하면 정본·사용자 원칙 위반. 또 이 필드는 M6 `contract.json` 예시에 없다 | "직전 확정 행동 유지 + 감속, 완전 정지는 M7 FAIL 경유"로 문구 교체 |
| B9 | M6 결정 지점 원칙 (5) "확률은 게이트(보정 E1 전)" | 정본 §6: **E1 전에는 확률 게이트를 끄고 최빈 선택만**. M6 문구는 "E1 전에 게이트로 쓴다"로 읽힐 수 있다 | "확률 게이트는 E1 뒤에만(그 전 최빈)"으로 |
| B10 | M6 `dp.critic_accept`(Jev가 critic 제안 수락/거절) 대 정본 §4 | "FAIL은 M7만". critic 제안이 FAIL 계열이면 Jev의 `reject_continue`가 M7 판정을 뒤집는 두 번째 판정자가 된다. M7 §1 "Jev·Astra·M4는 입력 채널이지 판정자가 아니다"와도 충돌 | 제안 범위를 FAIL 아래(WARN·모드 제안)로 한정한다고 적기 |
| B11 | M6 `dp.grasp_result` "M7 입력(S5)" | M7 S5 보기 = {유효 진행, 허용 변화, 실패, 복구 중}. M6 보기 = {secure, slipping, empty, uncertain}. 같은 입력 이름에 보기 집합이 다르다 | 보기 대응 규칙 또는 별도 입력 id |
| B12 | M6 approach 보기 | dp 표는 `top` 포함 4개, 같은 문서의 `pick-side-grasp` inputSchema는 `side_*` 3개. 스킬별 보기라면 표에 "스킬 inputSchema에서 가져옴"을 적어야 한다(M10 규칙 `prefer side_front`의 대상 집합도 같이) | 표 주석 |
| B13 | M1·M6·M7·M10의 M1 후보 이름 | M1은 **후보 A/B/C**, M6·M7·M10은 "**M1 후보 1** 가정". 이름이 달라 무엇을 가정했는지 흐리다(내용상 A) | "M1 후보 A"로 통일 |
| B14 | M10 L1 라벨 대 정본 §3 | 정본: M4(b)는 `ref(t)` 잔차와 `expected_after` 일치를 **따로** 계산. M10 L1은 `expected_after` 대 측정만으로 OK/LAG/DEVIATE/CONTRADICT를 매긴다. LAG는 `ref(t)` 기준에서만 나오므로(M4 §4.2 "LAG … ref(t) 기준에서만 판정") L1 설명이 부정확 | "M4(b) 범주를 그대로 기록"으로 |
| B15 | M1 지연 예산 대 정본 §7 | M1 "3Hz 결정 주기(333 ms)" = 정본 T_c 0.33 s — 맞음. near 들어가기 5 cm = 정본 §7 — 맞음(나가기 6 cm는 M1 제안, 정본에 없음) | 정본 설정 표에 히스테리시스 폭 칸 추가 제안 |

---

## Part C. 사용자 의도 (user-log 3·11항, `D:\qdd\CLAUDE.md`)

| # | 위치 | 문제 | 판정 |
|---|---|---|---|
| C1 | M6 §4.4 "기존 스킬" | user-log 3 "물체를 보고 **스킬을 생성해서** 잡는 방법들이 많지만 실패할 때가 있다". M6는 이것이 (b)에 가깝다고 스스로 적고 [결정 필요]로 올렸다(규칙 준수). 그러나 **1순위 제안은 (a')**이고 E-M6-1·E-M6-2 공통 조건 "같은 스킬 몸체"가 사실상 (a') 기준이다. 사용자 문장과 다른 기본값이 실험 설계 전체에 깔려 있다 | [결정 필요]는 있으나 **기본값 쪽이 사용자 문장과 반대**. (b)를 본 조건으로 둔 E-M6-1 변형을 병기하거나 "1순위" 표현을 빼는 게 안전 |
| C2 | M1 §7-1 "E3 먼저, 그 전 **임시 기본은 A**" + M6·M7·M10 "M1 후보 1 가정" | CLAUDE.md: "바꾸는 방법은 아직 정해지지 않았으므로 **사용자가 정하기 전에는 임의로 정하지 않는다**." [결정 필요]는 달려 있지만 "임시 기본 A"와 세 문서의 전제가 사실상 결정을 앞당긴다(v3/17 B4에서 이미 지적된 문제의 반복) | 조건부 가정임을 각 문서 머리에 "사용자 결정 전 임시 가정"으로 명시하고, 결정되면 다시 볼 목록(M3·M4(b)·M6·M7·M9·M10)을 정본에 |
| C3 | M1 [사용자] "변환 방법은 사용자가 정한다" | user-log 11(1)에는 이 문장이 없고 출처는 `D:\qdd\CLAUDE.md` 제약 절·plan.md 63행. 사용자 지시가 맞으므로 **내용은 맞음**. 출처 표기(user-log가 아니라 CLAUDE.md)만 보완 | 경미 |
| C4 | M1 V-free를 후보에서 제외 | 사용자는 "AI 전 분야에서 가장 효율적인 변환"을 찾으라 했다. VLM 자유 서술 중심 변환을 후보에서 빼고 대조 조건으로만 둔 것은 범위를 줄인 것. [결정 필요](§7-2)로 올려 규칙은 지켰다 | 준수. 단 C2와 같은 뿌리 |
| C5 | M6·M10에서 **BATON(심사 전, 인용 1)**이 계약 필드·검색 키 1순위를 좌우 | CLAUDE.md 신뢰도 기준 "신뢰도 낮은 논문은 최대한 쓰지 않는다, 쓰느니만 못하다". M6 표기 LOW-MED인데 `entry`·`lookahead_req`와 M10 키 1순위(전이 유형)가 거기서 나온다. 비슷하게 PlanAhead(인용 0)가 M2 형식 선택 근거 | 대체 근거(`entry`는 행동 트리 PA-BT·사전조건 문헌, 전이 키는 PhyAgentOS provenance·scope)를 병기하고 BATON은 "착상 출처"로 낮추기 |
| C6 | 정지 원칙 | M2 E-M2-2의 W(기다림) 조건은 비교용으로 명시 — 준수. **M6 `default_on_timeout` "안전 대기"**(B8)는 [결정 필요] 없이 정지 가능성이 있는 기본값 → 사용자 원칙("그 이후에는 웬만하면 멈추지 않는다") 위반 소지 | 수정 필요(B8) |
| C7 | effort | M10 "Astra effort 고정, 낮추기 금지", M2 E-M2-2 "low/high 실측 분포는 지연 재현용, 기본안 아님" — 준수 | 문제 없음 |
| C8 | "(11) 안전은 크게 다루지 않는다" | M2 AgentSpec(안전 DSL)·M6 annotations는 **계약 형식** 차용이라 안전 연구 확대는 아니다. 다만 M2 R3의 "안전 쪽" 대기, M6 "코드 안전 규칙이 최종"이 늘면 범위가 커질 수 있다 | 현재는 문제 없음, 관찰만 |
| C9 | [사용자] 인용 줄 원문 대조 | M2 §0([사용자] 2줄) = user-log 11(2)·정지 항목, M6 §1 = user-log 11 스킬·3항, M10 §1 = user-log 11(9): **모두 원문과 같은 뜻**, 바뀐 것 없음 | 문제 없음 |
| C10 | M6 기간 규칙 | CLAUDE.md "LLM+스킬 결합 논문은 1년 이내" → M6 표 기준 ≥2025-09-23 적용, 표 안 논문 모두 그 이후(Wake만 기간 밖 표시). MCP(2025-06)는 논문이 아니라 표준이라 1년 반 규칙 안 | 준수 |

---

## 확인 못 한 것
- lmgame-Bench·Magentic-One·Read More·Proactive MA의 학회 채택(OpenReview는 보지 않음).
- Agent Skills 공개 표준화 날짜 2025-12-18(1차 출처 미확인, M6 표기 유지).
- A2 항목 중 초록만 본 것(2606.29774, 2511.21730, 2604.14004, 2608.02645, SkillWrapper)의 본문 표.
- SkillsBench는 S2 batch에 넣지 않아 인용 미측정(요청 목록의 v3 기존 출처).
- M3·M8·M9 문서와의 일관성은 이번 범위 밖(M4·M7만 해당 절 대조).
