# M2. Astra → Jev 전달 (세션 계약) — 모듈 설계

> **정본 우선**: 모듈 사이 인터페이스·정지·확정 규칙·확률 게이트·시간 값은 `00-interfaces.md`가 우선한다. 이 문서의 계약 교체 규칙(§4.2)은 정지를 만들지 않는다(교체 대기 중에도 직전 확정 행동 유지, `00-interfaces.md` §4). E-M2-2의 W(기다림) 조건은 비교용이며 기본안이 아니다.

- 작성: 2026-09-23 UTC, 단계 2 라운드 D2 설계 에이전트(M1·M2, 이번 라운드 arXiv 검색 API 전담)
- **[사용자]** M1과 거의 같은 문제로 본다. Astra는 이미지를 보고 명령하지만 Jev는 이미지를 못 보므로, Astra가 본 것과 원하는 것을 Jev에게 효율적으로 전달하는 방법이 필요하다.
- [사용자] Astra가 처음 계획할 때는 로봇이 멈춰도 되고, 그 뒤에는 웬만하면 멈추지 않는다(실패로 다시 생각할 때만 예외). 실패 판정이 나면 Astra를 부른다(M8).
- 이 문서는 M1과 짝이다. M1이 "카메라 → 텍스트"라면 M2는 "Astra의 판단 → Jev가 읽을 수 있는 typed 계약". **계약 안 술어 이름은 M1 어휘를 그대로 쓴다.** M1 변환 방법은 사용자가 정하므로, 계약의 술어 칸도 그 결정에 묶인다([결정 필요], M1 §7).
- 조사 방법·검색어·한계는 M1 문서 0절과 같다(같은 에이전트, 같은 라운드). M2용으로 추가로 읽은 것: PlanAhead(2605.29927) 본문 표, Magentic-One(2411.04468) §3 원장, AgileThinker Tab.10, AgentSpec 초록, 2608.02645·2606.15285·2606.20978 초록.

---

## 1. 역할과 입출력

| 항목 | 내용 |
|---|---|
| 위치 | Astra(느림, 이미지 입력: Set-of-Mark 번호 이미지 + M1 텍스트 상태) → **계약 검사기(코드)** → 계약 저장소(버전) → Jev 요청 조립기(M3)·M4 원장·M7 critic·M8 호출기·M9 복구 |
| 입력(Astra에게) | 과제 지시, SoM 이미지(M1이 붙인 ID와 같은 번호), M1 상태 텍스트(같은 `t_state`), 스킬 목록(이름·사전·사후 술어·stop 술어, M6), 술어 어휘(M1), 이전 계약·실패 사건 문맥(재계획일 때, M8·M9), M10 규칙 |
| 출력 | **세션 계약(Session Contract)** JSON 한 개. 코드가 검사해 통과하면 새 버전으로 게시 |
| Jev가 보는 것 | 계약 전체가 아니라 **현재 단계에 필요한 조각**(현재 단계의 목표·완료 술어·금지 술어·결정 지점 질문·관련 ID). M1 원칙(관련 없는 내용 넣지 않기)과 같다 |
| 코드가 보는 것 | 계약 전체(원장, 술어 정의, 마감, 체크포인트, 예상 실패 목록) |

---

## 2. 분야 전체 최고 후보 표

### 2.1 계획기 → 실행기 전달 형식

| 이름 | 분야 | 어디서 최고였나 (조건) | 신뢰도 | 기간 | 학습 없이 | 로봇 |
|---|---|---|---|---|---|---|
| **COPE** (2506.11578) | LLM 협업 | 계획 = 한두 문장. 큰 계획기 → 작은 실행기 도움(Llama-3B 42.8→53.0%, GPT-4o-mini 계획). **목표형 30.2 / 절차형 23.2 / 없음 25.2**(Llama-1B **자기 계획** 조건, MATH-500). 작은 계획기 → 큰 실행기는 해로움(v3/14 원문 확인) | HIGH(TMLR 2026) | 안 | 예 | 아니오 |
| **PlanAhead** (2605.29927) | 웹 에이전트 | 계획 형식 4종(순차 하위목표 / 서사 / 의사코드 / 체크리스트), 계획기·실행기 3모델 조합, WebArena Hard 158과제 × 5회. **가장 좋은 형식이 실행기 모델마다 다르다**(GPT-4.1-mini는 서사, Qwen-2.5-VL은 체크리스트·순차, Gemini 계획+실행은 의사코드). 정적 계획이 동적 단일 에이전트보다 자주 낫다. 부트스트랩 구간이 넓다(Table 4: 예 4.1-mini 체크리스트 32.5~84.0) | MED-LOW(Mila 등, EMNLP 투고 중) | 안 | 예 | 아니오 |
| **Magentic-One 원장** (2411.04468) | 다중 에이전트 | 바깥 고리 **과제 원장**(확인된 사실, 찾을 사실, 유도할 사실, 추측, 계획), 안쪽 고리 **진행 원장** 다섯 질문(완료됐나 / 반복 중인가 / 전진 중인가 / 다음 누구 / 무슨 지시). 정체 카운터 ≤2 넘으면 바깥 고리 재계획(§3 본문) | HIGH(Microsoft, 반응 큼 — 수치 미측정) | **기간 밖(2024-11), 기초 문헌** | 예 | 아니오 |
| **AgentSpec** (2503.18666) | LLM 에이전트 안전 | 규칙 = **트리거 + 술어 + 집행**의 DSL. 코드 에이전트 90% 이상 위험 실행 차단, 체화 에이전트 위험 행동 전부 제거(초록) | HIGH(ICSE 2026) | 안(2025-03-24) | 예 | 체화 시뮬 |
| **Code-as-Monitor** (2412.04455) | 로봇 | VLM이 제약 요소를 정의하고 만족 여부 **코드**를 생성, 실시간 감시. 심한 방해 +28.7%p(v3/04) | HIGH(CVPR 2025) | **기간 밖, 기초 문헌(개념)** | 예 | 예 |
| MAST (2503.13657) | 다중 에이전트 실패 분석 | 실패 유형 중 "과제 명세 불이행", "종료 조건 모름"(v3/14) | MED | 기간 밖(6일), 기초 | — | — |
| Anthropic 다중 에이전트 블로그 | 업체 | 하위 에이전트 지시 네 요소: 목표, 출력 형식, 도구·출처, 과제 경계(v3/14) | MED | 안 | 예 | 아니오 |
| Plan-then-Execute 입장 (2605.14290) | 웹 | WebArena 80%가 실행 중 LLM 없는 프로그램 계획으로 가능, 전제는 효과를 미리 아는 typed 행동(v3/14) | MED-LOW | 안 | 예 | 아니오 |
| 계층 시연 구조 (2606.20978) | 웹 | 같은 행동 열을 **이름 붙은 계층 하위목표로 묶으면** 모호한 지시 과제에서 76.7→90.7%(p=0.034), 정확한 지시에서는 효과 없음(초록) | LOW-MED(ICML 2026 DL4C 워크숍) | 안 | 예 | 아니오 |
| 검증된 도구 호출 (2608.02645) | 에이전트 | 도구 호출에 **사후조건 검증 + 재시도 전 검증 + 멱등 키** → 중복 행동 크게 감소, 성공률 비슷(초록, 시뮬 주입 실패) | LOW(소속·학회 미확인) | 안 | 예 | 아니오 |

### 2.2 낡은 계획 처리 (계획기가 느릴 때)

| 이름 | 분야 | 무엇 | 신뢰도 | 기간 | 로봇 |
|---|---|---|---|---|---|
| **AgileThinker** (2511.04898) | 실시간 LLM | 반응 스레드가 계획 스레드의 부분 추론을 참조. 추론 흔적 비공개 모델(Gemini-2.5-Flash)에서는 **계획의 최종 출력만 참조**하는 축소판(Tab. 10, Freeway 중간): 8k 토큰/스텝 0.31 대 반응 단독 0.09·계획 단독 0.25, 4k 0.26 대 0.00·0.05, 16k·32k는 차이 없음 | HIGH(ICLR 2026) | 안 | 아니오 |
| **Slow Brain, Fast Planner** (2606.20458) | 로봇 | 블랙박스 VLM에 1Hz로 기다리지 않고 여러 요청, **가장 새 답 + 지수 감쇠 융합**, 로봇 무정지(plan v4.2, 메인 세션 원문 확인) | LOW(인정해야 할 선행) | 안 | 예 |
| 비동기 의미-행동 분리 (2606.15285) | VLA | 저주파 이해 모듈이 의미 조건을 비동기 갱신, 고주파 행동 모듈이 **낡은 의미 조건** 아래 계속 동작. 낡음 대책 = 최근 행동 이력 조건화 + 시간 어긋남 학습(초록) | LOW(학회 미확인) | 안 | 예(학습형) |
| WAM 실시간 연구 (2608.01880) | 로봇 | 관측·예측·실행 **시간 정렬이 먼저**(v3/14) | MED | 안 | 예 |
| Raft term / 낙관적 동시성 제어 | 분산 시스템 | 버전(term) 낮은 명령 거부 | 기초(비유) | 기간 밖 | — |

---

## 3. 가져올 것과 접목 방법 (원문 / 우리 접목안 분리)

| # | 원문 | 우리 접목안 [제안] | 옮길 때 주의 |
|---|---|---|---|
| 1 | COPE: 작은 실행기에는 목표형 > 절차형(1B 자기 계획 조건) | Jev에 가는 계약 조각의 중심 = **완료 술어(무엇이 참이 되어야 하나)**. 절차 서술은 스킬 이름으로만. Astra 자유 서술 `rationale`은 코드·로그용이고 Jev에는 기본으로 보내지 않는다(E-M2 조건으로 시험) | 큰 계획기가 목표형을 준 조건은 원문에 없다(plan v4.3 주의 그대로) |
| 2 | PlanAhead: 최적 계획 형식이 실행기 모델마다 다름, 구간 넓음 | "어느 형식이 최고"를 문헌에서 옮기지 않고 **Jev로 잰다**(E-M2 형식 축). 기본은 체크리스트형(원장의 술어 목록)이 우리 구조와 가장 가깝다 | 신뢰도 MED-LOW, 웹 과제 |
| 3 | Magentic-One: 과제 원장(사실·추측·계획) / 진행 원장(완료? 반복? 전진? 다음? 지시?) | 계약 = **과제 원장**(Astra가 씀). 진행 원장의 다섯 질문은 우리 구조에서 **코드 critic(M7)과 Jev typed 질문으로 나뉜다**: 완료 = `done_k` 코드 판정, 반복·전진 = M7 정체 규칙, 다음 행동 = Jev M3 질문. Astra의 "추측"은 `assumptions`(가정 술어)로 분리해 코드가 매 틱 검사 | 기간 밖 기초 문헌. 원문은 한 LLM이 다섯 질문에 답한다. 우리는 느린 Astra를 루프에서 뺀다 |
| 4 | AgentSpec: 트리거 + 술어 + 집행 | 계약의 `forbidden`·`monitors` 칸을 이 모양으로: `{when: <트리거>, check: <술어>, enforce: fail / skip / escalate}`. 집행은 코드. `fail`은 직접 정지가 아니라 M7 하드 채널 신호다(`00-interfaces.md` §4: FAIL은 M7만). Jev에는 금지 술어의 **현재 값**만 보인다 | 원문은 사람이 쓴 규칙. 우리는 Astra가 쓰고 코드 검사기가 어휘·문법 검사 |
| 5 | Code-as-Monitor: VLM이 제약을 코드로, 실시간 평가 | 어휘에 없는 술어가 필요하면 Astra가 `custom_predicates`에 **작은 코드 식**(허용된 기하 함수만 쓰는 DSL)을 적고, 코드가 평가해 참/거짓만 Jev에 넣는다 | 임의 코드 실행 금지 — 허용 함수 목록(거리, 각도, 포함, 접촉, 속도)만 |
| 6 | Anthropic 네 요소, MAST "종료 조건 모름" | 계약 필수 칸 검사: 목표(`done`), 출력 형식(Jev 질문의 보기 집합), 도구(스킬), **경계**(`forbidden`, `scope`). 완료 술어 없는 단계는 검사기가 거부 | — |
| 7 | 계층 시연(워크숍): 이름 붙은 계층 하위목표가 모호한 지시에서 도움 | 원장은 **단계(stage) → 하위 단계(substep) 2층**, 각각 짧은 영어 이름. M9 "거친→세밀 재개점"(RIR)과 같은 2층 | LOW-MED |
| 8 | 검증된 도구 호출: 사후조건 검증, 재시도 전 검증, 멱등 키 | 각 단계의 `post`(= `done_k`)는 **스킬이 "끝났다"고 돌려줘도 코드가 측정 술어로 다시 확인**. 재시도 전 `post`가 이미 참이면 재시도하지 않는다(중복 잡기 방지). 단계 ID = 멱등 키 | LOW — 발상만 |
| 9 | AgileThinker 축소판: 계획의 **최종 출력만** 참조, 반응 쪽은 계속 결정. 압박이 셀 때(4k·8k)만 이득 | Astra 응답을 기다리지 않는다. Jev는 **항상 가장 최근에 게시된 계약 버전**으로 결정하고, 새 버전이 오면 다음 결정 스텝부터 교체. Jev 입력에 `contract: c7 (based_on f1100, age 6.2s)`를 적어 낡음을 드러낸다 | Astra 추론 흔적은 볼 수 없다(OpenAI 추론 모델). 이득이 압박 조건에서만 나왔다는 점을 과장하지 않는다 |
| 10 | Slow Brain: 가장 새 답 + 감쇠 융합 | 계약은 **융합하지 않는다**(계약은 구조물이라 평균이 없다). 대신 "가장 새 **유효** 계약" 규칙: 새 계약이 기준 상태(`based_on`) 이후 바뀐 사실과 충돌하면(가정 술어 거짓) 게시하지 않고 M8에 재호출 신호 | 비교 조건 C2로 남긴다(M4 문서) |
| 11 | WAM: 시간 정렬 먼저 / Raft term | 계약에 `based_on_t_state` 필수, 게시 시 `contract_version` 증가 → **M4 `premise_epoch`도 증가**(M4 §7 열린 질문 6의 제안과 일치) | — |
| 12 | 2606.15285: 낡은 의미 조건 아래 최근 행동 이력으로 버팀(학습형) | 학습은 못 옮긴다. 옮길 수 있는 것: 낡은 계약 아래에서는 Jev 질문에 **최근 확정 행동 2~3개**를 함께 보인다(M4 원장에서) | LOW, 학습형 |

---

## 4. 설계안

### 4.1 1순위: 세션 계약 v1 (목표 중심 + 가정 술어 + 버전)

필드(모두 영어 값, 술어 이름은 M1 어휘):

| 필드 | 뜻 | 누가 쓰나 / 누가 읽나 |
|---|---|---|
| `contract_id`, `version`, `parent_version` | 버전 사슬 | 코드 / 전 모듈 |
| `based_on_t_state` | Astra가 본 프레임·시각 (SoM 이미지와 M1 텍스트의 `t_state`) | Astra / M4(epoch)·Jev(나이 표시) |
| `goal` | 과제 전체 완료 술어 집합 | Astra / M7 |
| `relevant_ids`, `relevant_predicates` | M1 관련도 필터 입력 | Astra / M1 |
| `objects` | ID별 역할 한 단어(`target`, `container`, `obstacle`)와 Astra가 본 속성(T3 술어 초깃값, 측정 시각 붙음) | Astra / M1(T3 캐시), Jev |
| `assumptions` | 계획이 기대는 가정 술어(물체 존재, 경로 비어 있음, 뚜껑 닫힘 등). **거짓이 되면 계약이 낡은 것** | Astra / 코드가 매 틱 검사 → M7 신호(소프트 채널 후보) + M8 재호출 요청, M9 ID/OOD |
| `stages[]` | 단계 원장. 각 단계: `id`, `name`, `skill`, `pre`, `done`, `inv`, `stop`, `T_exp_s`, `substeps[]`, `decision_points[]`, `checkpoint`(true면 M9 재개점), `irreversible`(true면 M8 T2 순간) | Astra / M3·M4·M6·M7·M8·M9 |
| `decision_points[]` | Jev에게 물을 typed 질문 틀: `qid`, `when`(트리거 술어), `options`(ID·이름, M3가 예상 결과 술어를 붙임), 항상 `NONE_ESCALATE` 포함 | Astra 틀 + 코드가 보기 채움 / Jev(M3) |
| `forbidden[]` | `{when, check, enforce}`(AgentSpec 모양) | Astra / 코드 집행, Jev는 현재 값만 |
| `expected_failures[]` | 예상 실패 목록(`slip_during_transport`, `grasp_miss` 등)과 권장 아래 층 대응 | Astra / M9(ID 판정) |
| `custom_predicates[]` | 어휘 밖 술어를 허용 DSL로(`dist(o3.rim, o9.spout) < 0.02`) | Astra / 코드 평가 → M1 facts |
| `rationale` | Astra 자유 서술(2~3문장) | Astra / 로그·M10. **Jev 기본 입력에서 제외**(E-M2에서 시험) |

예(단순 배치 과제, 계약 전체 — 코드가 보는 것):
```json
{
  "contract_id": "ep42", "version": 7, "parent_version": 6,
  "based_on_t_state": "f1100",
  "goal": ["on(o3,o5)"],
  "relevant_ids": ["o3", "o5", "o8"],
  "relevant_predicates": ["holding", "above", "near", "aligned_xy", "in_contact", "on", "touch"],
  "objects": {"o3": {"role": "target", "attrs": {"contents": "empty@f1100"}},
              "o5": {"role": "container"}, "o8": {"role": "obstacle"}},
  "assumptions": ["exists(o3)", "exists(o5)", "path_clear(gripper->o3)", "clear(o5)"],
  "stages": [
    {"id": "S1", "name": "grasp mug", "skill": "grasp_top", "pre": ["not holding(any)"],
     "done": ["holding(o3)", "lifted(o3)"], "inv": [], "stop": ["holding(o3)"], "T_exp_s": 6,
     "checkpoint": true, "irreversible": false,
     "decision_points": [{"qid": "S1.target_part", "when": "near(gripper,o3)",
                          "options": ["o3.body", "o3.handle", "NONE_ESCALATE"]}]},
    {"id": "S2", "name": "place mug on tray", "skill": "place_on", "pre": ["holding(o3)"],
     "done": ["on(o3,o5)", "not holding(o3)"], "inv": ["holding(o3)"], "stop": ["in_contact(o3,o5)"],
     "T_exp_s": 8, "checkpoint": true, "irreversible": true,
     "substeps": ["approach", "align", "lower", "release"],
     "decision_points": [{"qid": "S2.fine", "when": "near(o3,o5)", "options": "M3.Q_fine_dir"}]}
  ],
  "forbidden": [{"when": "always", "check": "touch(o8)", "enforce": "fail"},
                {"when": "stage==S2", "check": "tilt(o3)>30deg", "enforce": "escalate"}],
  "expected_failures": [{"event": "grasp_miss", "lower_layer": "retry_grasp_once"},
                        {"event": "slip_during_transport", "lower_layer": "stop_and_regrasp"}],
  "custom_predicates": [],
  "rationale": "Handle faces away; top grasp is safer. Tray rim on far side, approach from near side."
}
```
(`tilt(o3)>30deg`의 숫자 비교는 **코드**가 한다. Jev는 `tilt_ok(o3)=yes/no`만 본다.)

Jev가 실제로 받는 조각(M1 상태 앞에 붙음, 현재 단계 S2 기준):
```
contract: ep42 v7 (based_on f1100, age 6.2s)  assumptions: all_true
goal: on(o3,o5)
stage S2 "place mug on tray" [substep: align]  done_when: on(o3,o5) and not holding(o3)
forbidden now: touch(o8)=no  tilt_ok(o3)=yes
recent committed: approach, approach, align(+x)
```

계약 검사기(코드, 게시 전)
1. JSON 스키마·필수 칸(각 단계 `done` 비지 않음, `NONE_ESCALATE` 포함) 검사. 실패하면 Astra에 오류 목록과 함께 1회 재요청(구조화 출력 재시도).
2. 모든 술어 이름이 M1 어휘 또는 `custom_predicates` 안에 있는지.
3. `based_on_t_state` 이후 바뀐 사실(M1 변화 기록) 중 `assumptions`와 충돌하는 것이 있는지 → 있으면 게시 보류 + M8 재호출(낡은 계약).
4. 첫 단계 `pre`가 지금 측정 상태에서 참인지(거짓이면 M9 재개점 계산으로 넘김).

### 4.2 낡은 계약 처리 규칙 (AgileThinker 축소판 + 버전)
- **R1 기다리지 않는다**: 첫 계약 전만 정지 허용([사용자]). 이후 Astra 요청 중에도 Jev는 현재 계약으로 계속 결정한다.
- **R2 가장 새 유효 버전만**: 계약 저장소는 버전 하나만 활성. 새 버전 게시 = 활성 교체 + M4 `premise_epoch` 증가(이전 epoch의 미확정 표 폐기, M4 §4.2). 이미 확정·실행된 것은 되돌리지 않는다.
- **R3 교체 시점**: 결정 스텝 경계에서만 교체(M4 FROZEN 구간 안 스텝은 건드리지 않음). `irreversible` 단계 진행 중이면 그 하위 단계 끝까지 기다린다(추론, 안전 쪽).
- **R4 낡음 표시**: Jev 조각에 `age`와 `assumptions: all_true` 또는 `<거짓 목록>`을 항상 적는다. 거짓 가정이 있으면 모든 Jev 질문의 `NONE_ESCALATE`가 자연스러운 선택이 되도록 보인다(Jev가 무시해도 코드가 M8을 부른다 — 판정 주체는 코드 critic 하나, plan v4 원칙).
- **R5 순서 뒤바뀜**: 늦게 보낸 요청의 답이 먼저 오면 `based_on_t_state`가 더 새 것만 받는다(Raft term 비유). 같은 기준 시각이면 나중 도착 것.
- **R6 부분 갱신**: 재계획 때 Astra가 전체 계약 대신 `patch`(바꿀 단계만, `parent_version` 명시)를 낼 수 있다. 검사기는 patch 적용 결과를 전체 검사. 목적: Astra 출력 토큰·지연 감소(추론, 측정 필요).

### 4.3 대안
- **대안 B (절차 포함형)**: 각 단계에 Astra의 절차 서술(`how`: "approach from the near side, lower slowly")을 Jev 조각에도 넣는다. COPE 결과의 반대 방향을 우리 데이터로 확인하는 조건.
- **대안 C (체크리스트만)**: `stages[].done`만 체크리스트로(스킬·결정 지점 없음), Jev가 다음 단계를 스스로 고른다. PlanAhead 체크리스트형·Magentic-One 진행 원장에 가까움. 스킬 결합(M6)을 느슨하게 할 때의 비교 조건.
- **대안 D (서사형)**: Astra 자연어 계획 문단 하나(PlanAhead 서사형, GPT 계열에서 최선이었던 것). typed 칸이 없어 M4·M7·M9가 쓸 술어가 없으므로 **Jev 판단 정확도 비교에만**.

---

## 5. 비교 실험 (판정 기준 사전 등록)

### E-M2-1 전달 형식 (오프라인, M1 E3와 같은 스냅샷 재사용)
- 조건: 1순위 v1 조각 / v1 + `rationale` / 대안 B(절차 포함) / 대안 C(체크리스트만) / 대안 D(서사형). 모두 같은 Astra 계약에서 기계적으로 만든다(Astra 호출 1회, 형식만 바꿈).
- 질문: M1 E3의 Q1~Q4 + Q5 "지금 단계가 끝났나"(done 술어가 참/거짓/모름), Q6 "다음 단계로 넘어가도 되나".
- 지표: 정답률, `NONE_ESCALATE` 비율, 입력 토큰, Jev 지연.
- 판정(실행 전 고정):
  1. v1 + `rationale`이 v1보다 2%p 이상 높지 않으면 `rationale`은 Jev 입력에서 뺀다(관련 없는 내용 원칙).
  2. 대안 B가 v1보다 3%p 이상 높으면 [결정 필요]로 올린다(COPE 방향이 Jev에서 뒤집힘).
  3. 대안 C가 Q6에서 v1보다 5%p 이상 낮으면 "단계 전이는 코드가 `done`으로" 규칙 유지.
  4. 대안 D가 v1보다 높아도 typed 칸이 없으므로 채택하지 않고, 차이를 "typed화 비용"으로 보고한다.
  5. 부트스트랩 95% 구간이 겹치면 "차이 없음".

### E-M2-2 낡은 계약 처리 (시뮬 폐루프)
- 조건: W 기다림(Astra 응답까지 정지) / L 가장 새 계약 즉시 교체(R2, 가정 검사 없음) / L+A R1~R5 전부(1순위) / F Slow Brain식(여러 요청, 가장 새 답, 가정 검사 없음).
- 섭동: 계획 도중 물체 밀기(가정 `path_clear` 깨짐), 목표 물체 이동, Astra 지연 인위 증가(low/high effort 실측 분포에서 뽑음 — effort 낮추기가 기본안이라는 뜻이 아니라 지연 축을 재현하는 것).
- 지표: 성공률, 완료 시간, 정지 시간, 낡은 계약으로 실행한 결정 스텝 수(가정 거짓인데 실행), 계약 교체 뒤 epoch 폐기 표 수, Astra 호출 수.
- 판정(실행 전 고정):
  1. L+A가 W보다 성공률이 3%p 이상 낮지 않고 정지 시간이 50% 이상 짧으면 1순위 유지.
  2. L+A가 L보다 "가정 거짓 상태 실행 스텝"을 절반 이하로 줄이지 못하면 `assumptions` 검사를 단순화(존재·경로만).
  3. F가 L+A보다 성공률 3%p 이상 높으면 [결정 필요](융합 방식 채택 여부).
  4. 각 조건 에피소드 ≥ 50, 3개 시드, 평균 ± 표준편차.

### E-M2-3 계약 품질 (Astra 쪽, 부수)
- 측정: 검사기 통과율(첫 시도 / 재요청 후), 어휘 밖 술어 비율, `T_exp_s` 대 실측 단계 시간 비율(M7 `D_k` 대체값 1.5×T_exp의 근거), 가정 술어 누락으로 인한 실패 수.
- 판정: 첫 시도 통과율 < 80%면 계약 스키마를 줄이거나(필수 칸만) 예시 계약을 프롬프트에 넣는 조건을 추가 시험.

---

## 6. 반대 증거와 위험
1. **COPE 근거의 조건**: 1B 자기 계획, 수학 문제. 큰 계획기가 작은 실행기에게 목표형을 준 조건은 없다. Jev의 규모·능력은 공개되지 않았다.
2. **PlanAhead**: 최적 형식이 모델마다 달랐다 → 우리가 고른 "체크리스트형 typed 계약"이 Jev에게 최적이라는 문헌 근거는 없다. E-M2-1이 필요.
3. **계약이 길어지면** M1과 같은 길이 손실(2510.05381). Jev 조각을 현재 단계로 자르는 이유. 전체 계약은 코드만 읽는다.
4. **Astra가 typed 계약을 틀리게 쓸 위험**: 술어 오기, 가정 누락, 현실과 안 맞는 `T_exp`. 검사기는 문법만 잡고 의미 오류(잘못된 완료 조건)는 못 잡는다. MAST의 "명세 불이행" 실패가 우리 쪽에서도 날 수 있다.
5. **낡은 계약**: AgileThinker의 축소판 이득은 시간 압박이 셀 때만(4k·8k) 나왔고 16k·32k에서는 없었다. "항상 가장 새 계약"이 늘 이득이라고 말할 근거는 없다.
6. **가정 술어 검사가 과민하면** 재호출이 잦아진다(M8 호출 수 증가). M7 conformal 임계와 같은 문제 — 가정 술어에도 히스테리시스·지속 시간 조건(예: 0.5초 연속 거짓)을 둔다(추론).
7. **Slow Brain식 융합(F)이 더 단순하고 더 나을 수 있다**. 선행이므로 반드시 비교 조건으로 둔다.
8. 계약·사전·사후조건 문헌 다수가 LOW(2608.02645, 2602.22302 등). "계약 형식이 실행기를 좋게 한다"를 HIGH 근거로 말할 수 없다(v3/14 결론 유지). HIGH 근거는 AgentSpec(집행 쪽)과 Code-as-Monitor(감시 쪽, 기간 밖)뿐이다.

## 7. 열린 질문, [결정 필요]
1. [결정 필요, 사용자] M1 변환 방법 결정이 M2 술어 칸을 정한다(M1 §7-1).
2. [결정 필요] `rationale`(Astra 자유 서술)을 Jev에 줄지 — E-M2-1 판정 1로 정하자는 제안.
3. [결정 필요] 단계 원장의 결정 지점(`decision_points`)을 Astra가 쓸지, M6 스킬 정의에 고정해 둘지(M6 문서와 맞춰야 함).
4. [결정 필요] 정해 둔 순간(M8 T2)을 계약의 `irreversible` 칸으로 Astra가 적게 할지, 사용자가 목록을 정할지(M8 §7과 같은 질문).
5. 열린 질문: 재계획 때 patch 대 전체 계약 — Astra 출력 지연 측정 뒤 결정.
6. 열린 질문: 계약 버전 교체 = M4 epoch 증가(제안). M4 문서 열린 질문 6과 합의 필요.
7. 열린 질문: `custom_predicates` 허용 DSL의 범위(거리·각도·포함·접촉·속도). 너무 넓으면 검사·안전 문제, 너무 좁으면 Code-as-Monitor 이득을 잃는다.

## 8. 확인 못 한 것
- AgentSpec 본문(체화 과제 설정, 규칙 예) — 초록만.
- PlanAhead Table 1의 형식별 AR 점수(표 본문 파싱 실패, 부트스트랩 구간 표만 읽음)와 학회 채택.
- Magentic-One 원장 효과를 따로 뗀 절제 수치(본문 §3 설명만 읽음).
- 2606.15285·2606.20978·2608.02645 본문(초록만).
- 큰 계획기 → 작은 실행기에 목표형 대 절차형을 준 조건의 연구(찾지 못함. 검색: `abs:planner AND abs:executor AND abs:"small language model" AND abs:plan`, WebSearch "planner executor plan format structured vs natural language small executor"). 부재 주장 안 함.
- Astra가 이 스키마로 구조화 출력을 낼 때의 지연·통과율(미측정, E-M2-3).
