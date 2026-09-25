# M4. 연속 동작 1단계: 계단식 겹침 호출 + 겹침 구간 자기 확인·갱신 — 모듈 설계 (단계 2)

> **정본 우선**: 모듈 사이 인터페이스·정지·확정 규칙·확률 게이트·시간 값은 `00-interfaces.md`가 우선한다(2026-09-23 22:00 UTC). 이 문서와 다르면 그쪽을 따른다.
> 개정 2026-09-25 01:48 UTC (R7 sweep6, 정본 §43·§44·§47·§58·§60 — 단계 3 결정 안내만 붙임, 본문은 단계 2 당시 기록이라 고치지 않음): 빠른 typed 선택기 Jev는 쓸 수 없어(user-log 46) 로컬 VLM Jev-L(Qwen3-VL-4B, 같은 JevCall 형식 = DecCall)로 바꿨고(§44·§50), 런타임 주 설계는 결정 토큰 + action expert + 확인 헤드를 한 백본에서 내는 융합 모델이며 결과 표는 모듈형 스택과 나란히 둔다(§58·§60). 카메라는 AI Worker 기본 카메라 그대로다(§43: `ZED_M` 쌍둥이·트랙 D-stereo 가상 카메라 폐기). 시뮬 카메라 설정은 humanoid-challenge-env 복사다(§47: 머리 ZED Mini 왼쪽 정류 672×376, VGA 수평 85°·fx 367 — 'ZED Mini 102°×57°'는 센서 최대 화각이라 VGA 모드 값이 아니다; 좌·우 손목 D405 424×240). 최신 상태는 `docs/handoff.md` §2.7·§2.8.
> 개정 2026-09-24 07:18 UTC (정본 §34·§35, D20 반영, `D20-expert-role.md`, user-log 35·36 — D35·D36은 사용자 결정, R 설계는 Claude 결정): §0 (b) 결과 확인 아래에 **(정본 §35) 주 시스템(S + R)에서 `ref(t)` = 투영 뒤 실제 명령**(S 명령 + 코드 투영된 잔차) 줄. `expected_after`는 그대로. 그림자 예측기는 (b)에 넣지 않는다. 위 B 줄(확정 청크)은 E-AE-2 비교 표에만 해당. §7-19.
> 개정 2026-09-24 06:36 UTC (정본 §32·§33, D19 반영, `D19-action-expert.md`, user-log 33·34 — 사용자 결정 B, 세부는 Claude 설계): §0 (b) 결과 확인 아래에 **B 실행기일 때 `ref(t)` = 확정된 행동 청크**(연속 잔차 = 측정값 − 청크) 줄. `expected_after`는 코드 목표 술어로 **그대로**(실행기와 무관, S·B 같음). DEVIATE 2회 연속 [가정]은 phase 폴백 조건이기도 함(폴백 ≠ FAIL). M4 규칙은 전부 코드. §7-18.
> 개정 2026-09-24 (정본 §31, D18 반영, `D18-confidence-patch.md`, user-log 32 — Claude 결정): §4.1 Jev 일관성 규약 중 M4 몫, §4.4 변수 표(q̂ 행)에 **J5 Jev conformal 게이트**(E1 뒤 켤 후보) — `question_id@vN`별 보정 집합으로 문턱을 잡아, 예측 집합이 원소 하나면 M4 확정 후보, 둘 이상이거나 `NONE_ESCALATE`를 포함하면 확정 보류(직전 확정 행동 유지 + 감속, 정지 아님), 같은 결정 지점에서 반복되면 Astra로 올림(M8 `T_j5`). 보장은 단계별 주변 커버리지(에피소드 수준 아님), 교환 가능성은 판본 묶기(J1) + 매일 카나리로 지킨다. E1 전에는 게이트 끔(00 §6) 그대로.
> 개정 2026-09-24 (정본 §28, D17 반영, `D17-api-consistency.md`): §4.1에 **Jev 일관성 규약 J1~J4** 중 M4 몫 — J1 `Vote.question_id`는 `question_id@vN`(문구 + `option_key` 표준 순서 + 보기 설명 + 표시 문자열(공백 포함) + legend + 상태 직렬화기 판본의 해시), 다른 판본의 표는 합치지 않음 / J2 같은 세계 상태 → 바이트까지 같은 텍스트(M1) / J3 합의 표는 **시간차 상태에서만**, 같은 입력 되묻기는 측정용이며 합의 표로 세지 않음, `FLIP_TH`와 LA-2 불일치 해석은 E0.5 (ii) test-retest 바닥 위에서(바닥 p면 잡음만으로 두 호출이 어긋날 확률 약 2p(1−p), 우리 계산) / J4 θ 게이트·`C_flip` 감시는 `question_id@vN`별로만. §4.4 FLIP_TH 행·§5 전제 실험(E0.5)에 바닥 기준, §7-17. C5-A3(A3 재현 기준 조건)는 조건 정의 그대로.
> 개정 2026-09-24 (정본 §27, D14 반영): R5 반영 — §4.1 `Vote`에 `option_key`·`perm_id`·`display_map`, 합의·최빈은 `option_key`로 세고 C3''가 순서를 돌리거나 2지선다 중립 ID의 짝을 바꿀 때 호출마다 `display_id → option_key` 대응표를 기록(§4.1 아래 줄, §3 #15, §7-16). 합의 규칙·판정은 그대로.
> 개정 2026-09-24 (정본 §26, 사용자 결정 user-log 25): 논문 틀 [결정 필요] 18(= D29) 해소 = 한 편(2안) → **E-M4-lat 필수**, E-link(EVAL §4.4 (5))도 필수. §5 순서·§7-11에 반영. 실험 정의·판정은 D6 설계 그대로.
> 개정 2026-09-24 (정본 §24, D12 반영): §0에 D12 선행·동기 줄 추가 — 차별화 보강 문장 "실행 뒤 예측-실제 불일치를 다음 후보 선택 학습에 쓰는 WCD와 달리, 우리는 그것을 합의 원장의 전제 무효화·확정 판정에 쓴다", (a)만으로는 부족하다는 동기(Type-Safe 2609.26758, PACT 2609.01662), 선점 색인 기준 2026-09-23 제출분. §2.1에 WCD(2609.02159)·SMC(2609.03236) 행, §2.2에 EmbodiedSkills(2609.01281) 행, §2.3에 RegenHarness(2609.27612) 행, §6 반대 증거를 동기로 쓰는 줄, §7-15.
> 개정 2026-09-24 (D11 일관성 점검 반영, `D11-final-consistency.md` I-10·C-8): §0 [사용자] 줄을 user-log 원문으로 되돌림("가장 중요" → "굉장히 중요하다" 등), §5 실험 순서에 E0.5 같은 날 가장 먼저·E-M4-gen·E-M4-lat.
> 개정: 2026-09-24 D9(정독) 반영 (`D9-slowbrain-showharness-gptpolicy.md`, 00-interfaces §20): §5 기준 조건을 Slow Brain(2606.20458) 원문대로 정정 — **C2 = VLM Stream**(요청 시각 기준 가장 새 유효 응답 하나, in-flight 상한 없음·실측 보고, 5 s 타임아웃), **C2' = Probability Fusion + 스트리밍**(λ=3, τ=5 s, T_vlm=1, 5 s 타임아웃, S1 = 빠른 층 코드 규칙 점수, Sim = 늦게 온 선택 보기의 코드 예상 궤적 대 현재 보기들, 진행분 잘라냄, d_scale은 우리 작업공간 척도 [가정]), **C2'-S**(Score Fusion λ=1), 선택 **C2-match**. 이전 C2'(표 나이 감쇠 가중 최빈, 반감기 0.33 s)는 우리 변형 **C2''**로 개명(보조). 판정 1·11·11b~11d·14·17과 주 그림 2의 C2'는 원문 충실판을 뜻한다. §0 차별 문장에 "실행 뒤 명령 대 측정 되먹임은 Show-Harness·RoboDawn에도 있다"와 Slow Brain 차이를 적음, §2.1 Slow Brain 행·§3 #12를 원문 사실(응답 사이 일관성 검사 없음, 실행 뒤 확인 없음, 지연 스윕 조건)로 갱신, §2.2 Show-Harness 행, §5.1 (1)에 E-M4-lat가 Slow Brain이 재현하지 않은 장면 변화 조건을 잰다는 해석, §6·§7-14·§8·출처 갱신.
> 개정: 2026-09-24 D8(정독) 반영 (`D8-robodawn-a3-deepread.md`, 00-interfaces §19): §0 새로움 문장을 §19 **차별화 문장(확정)**으로 교체(A3 §6 향후 과제 인용, 차별점 = "(b)가 합의 원장의 전제 무효화·확정에 쓰인다"). §2.1 A3 행을 원문 정독 사실로 갱신(같은 관측 K=8, 누적 궤적 합의, 이중 검증, 가장 긴 검증 접두부, δ = 차원별 std, 결과·표/본문 불일치, 코드 대 논문 차이). §2.2 (b) 표에 **RoboDawn** 행(실행 뒤 reached/partial/failed 되먹임은 있으나 겹친 호출이 없어 표 무효화 없음). 기술 추가: §3 #17·§4.4에 누적 예상 상태 합의·±1 스텝 시간 정렬 후보·데이터 척도 허용 폭, §5에 기준 조건 **C-FIX**(격자 탐색 최적 고정 확정 길이)·지표 평균 확정 길이·호출 수·E0.5 같은 시각 반복 호출 뒤집힘(C5-A3 공정성), §5.1 (4) 관측 열화 스윕, 판정 18·19. §6·§7-13·§8·출처 갱신.
> 개정: 2026-09-24 D7(선점 재검사) 반영 (`D7-preemption-rescan.md`, 00-interfaces §18): §0에 **새로움 문장(수정)** — "합의가 되면 앞 구간을 확정한다"만으로는 새롭지 않다(A3 2605.11567). 새로움 = (1) **시간차로 겹쳐 부른 블랙박스 typed 결정 호출 사이의 합의**와 (2) **실행 뒤 코드 예상 상태 대 측정 상태 비교**를 **함께** 쓰는 확정 규칙, (3) 그 결과로 keep/replace/repair를 고르는 것. §2.1 표·§3 표에 **A3** 행, §5 조건에 **C5-A3**(A3식: 같은 시각 다중 샘플 합의만으로 앞 구간 확정, (b) 없음)와 **판정 17**(C5 대 C5-A3), §2.1 아래 적응형 실행 구간 6편(LOW 관련 연구, id만·미확인), §6·§7-12·§8·출처 갱신.
> 개정: 2026-09-23 D6(모의 심사) 반영 (`D6-mock-review.md`, 00-interfaces §17): §5에 **E0.5를 E0와 같은 날 가장 먼저** 돌리는 규칙, 새 절 **§5.1**(E-M4-lat 인공 지연 주입 스윕 p95 0.3/0.8/2/5 s, 모델 일반성 조건 = B8 logprob 선택기에 같은 확정기, (a)/(b) 분해 그림·P0 무손해·결과 기반 라벨 잘못 확정 비율·epoch 교체 빈도/미확정 실행 비율/번복률 분포) — 새 항목마다 사전 등록 판정(판정 11~16)과 비용·시간 [가정]을 붙였다.
> 개정: 2026-09-23 D5 반영 (`D5-consistency.md` 1-14·2-5·2-6): `C_m4`·`C_flip` 1표 규칙을 M7 채택으로 적음, 과제 이름 E2 → E2a, STALE_MAX 1.5 s를 00 §7 설정 표에 올림.
> 개정: 2026-09-23 정본 §14–§15 반영 (`00-interfaces.md` §14-1·§14-3·§14 실험 조건·§15, `D4-cross-field.md` §5·§10, `D4-cross-field-verification.md` #2·#9·#10·§2-3). 핵심: (1) E-M4에 **C3'**(Adaptive-Consistency식 베이즈 정지 규칙, 표 수만 사용)를 넣고 **C_thresh = 0.9를 명시**했다. 원문 기본값 0.95는 만장일치 4표가 있어야 확정되고, 3표면 0.9375다(§2.1·§4.4·§5). (2) E-M4에 **C3''**(보기 순서 돌리기, M3 §4.6)를 넣었다. 기본값은 아니다. (3) **비가역 보기의 확정 규칙 W+1**: 비가역 여부는 M6 스킬 단계 `effect` 필드에서 읽는다(§4.6 신설, §4.2 의사코드). §7-9·§7-10 해소.
> 개정: 2026-09-23 D4 반영 (`D4-devils-advocate.md` F2·C-3·C-10·C-11·D-3·E-3, 00-interfaces §12·§13): CONTRADICT → 하드 채널은 T1 술어일 때만(그 밖은 `C_m4`), `C_flip` 계산식을 표 분포 거리 + conformal 임계로 교체, LocalAgreement·Sentinel식 `C_flip`을 "잠정 기본"([결정 필요] 4 승인 전)으로 표시, 전제 실험 E0.5(오프라인 표 재생)와 그 사전 판정 연결, 실험 순서를 00 §13으로.
> 개정: 2026-09-23 D1 검증·00-interfaces 반영 (`D1-verification.md` Part A 정정, Part B·C 해소안을 이 문서에 반영했다.)


작성: 2026-09-23 UTC(첫 판 표기 "2026-09-24"는 KST 날짜로 보여 UTC로 고침, D4 C-10). 규칙: `docs/design/README.md`.
읽은 것: `CLAUDE.md`, `plan.md` v4.3(§1, M3, M4, M5, §2.5, §4, §5), `research/v3/README.md`, `v3/06`, `v3/08`, `v3/09`, `v3/18`, `v3/02`(SmolVLA·A2C2), `v3/01`(Jev 지연), `design/M3-action-representation.md` §4.5(결정 스텝 기록).

---

## 0. 사용자 의도와 결론

- **[사용자]** (user-log 11 RTC 적용) 1초에 Jev를 한 번이 아니라 3번 정도 계단식으로 겹쳐 쓴다. **겹치는 부분의 움직임이 제대로 반영됐는지 스스로 감지하고 업데이트하는 시스템이 자동으로 있어야 한다. 이게 굉장히 중요하다.** Jev가 빠르다지만 로봇 동작에서는 빠르지 않으니, 연속 동작처럼 내뱉게 하는 법을 RTC에서 많이 참고한다.
- **전제(새로움 아님, v3/18)**: 비정지와 겹침 요청 자체는 선행이 있다(Slow Brain Fast Planner 2606.20458의 streaming / Jev 데모들의 단일 in-flight + 유지).
- **차별화 문장 (00 §19, D8 확정)**: "A3는 학습된 VLA 한 모델이 같은 관측에서 뽑은 여러 청크의 합의와 조건부 재디코딩으로 실행 전에 확정 길이를 정하며, 외부 증거(세계 모델·상태 전이 예측)는 향후 과제로 남겼다(A3 §6, 원문 확인). 우리는 시간차로 겹쳐 부른 블랙박스 typed 결정 호출 사이의 합의에 실행 뒤 코드 예상 상태 대 측정 상태 비교를 결합해, 전제가 깨진 표를 무효화하고 keep/replace/repair를 고른다."
  - 영어 짧은 판(우리 번역): "A3 fixes the commit length before execution from the consensus of chunks sampled by one trained VLA on the same observation, leaving external evidence (world models, state-transition predictors) to future work (A3 §6). We combine agreement across time-staggered, overlapping black-box typed decision calls with a post-execution check of code-expected versus measured state, invalidating votes whose premises broke and choosing keep/replace/repair."
  - 실행 뒤 명령 대 측정 되먹임 자체는 **Show-Harness**(2609.10522, 프롬프트 문맥 "Last MV_DOWN lowered {moved} of {commanded} cm", §2.2)와 **RoboDawn**(2609.22966, 직전 명령 결과 reached/partial/failed, §2.2)에도 있다(00 §20). 그래서 차별점은 "(b)가 있다"가 아니라 **"(b)가 합의 원장의 전제 무효화·확정 판단에 쓰인다"**는 점이다. 셋((1) 시간차 블랙박스 호출 사이 합의, (2) 실행 뒤 예상 대 측정 비교, (3) keep/replace/repair) 중 하나만으로는 새로움을 주장하지 않는다(00 §18). keep/replace/repair의 뜻(keep = 확정 유지, replace = epoch 교체·전제 깨진 표 폐기 후 새 합의로 교체, repair = M7 → M9 경로로 가는 신호. M4는 신호만 내고 수리를 직접 하지 않는다, 00 §4). 이 문장은 §5 판정 17(C5 대 C5-A3)이 직접 시험한다. 선점 검색 색인 기준: arXiv 2026-09-22 제출분까지(D7).
  - **Slow Brain과의 차이(00 §20, D9)**: [원문] Slow Brain은 요청 시각 기준 가장 새 VLM 선택 하나를 기하 유사도 × 지수 감쇠로 빠른 플래너 점수에 섞을 뿐, 응답 사이 일관성 검사·다수결도 실행 뒤 확인도 없다(§3.3, 부록 C.3). [우리 해석] 우리 M4는 시간차 응답 사이 합의와 실행 뒤 예상 대 측정 비교로 전제가 깨진 표를 무효화하고 확정한다.
  - **D12 선행·동기(00 §24)**: 선점 검색 색인 기준을 arXiv **2026-09-23 제출분**까지로 갱신했다(D12, C1 강한 선점 없음). 부분 겹침 4편을 인용한다 — WCD(2609.02159, §2.1), SMC(2609.03236, §2.1), RegenHarness(2609.27612, 전제 epoch의 stale/version-bound 선례, §2.3), EmbodiedSkills(2609.01281, "실행 뒤 확인 자체"의 선례, §2.2). 차별화 보강 문장: "실행 뒤 예측-실제 불일치를 **다음 후보 선택 학습**에 쓰는 WCD와 달리, 우리는 그것을 합의 원장의 **전제 무효화·확정 판정**에 쓴다." 위 차별화 문장(00 §19)은 그대로다.
  - **(a)만으로는 부족 → (b)가 필요한 근거(00 §24, 반대 증거를 동기로)**: Type-Safe Is Not Error-Free(2609.26758) — "renaming the two options from 0/1 to no/yes changes 70.4 more answers per hundred ... shifts AUC from .94 to .23", hosted 모델도 ".8146 to .5806", "the type-error rate remains 0%". 보기 이름에서 오는 체계적 오류는 반복 호출끼리 합의해도 걸러지지 않는다. PACT(2609.01662, 08-31 제출 → 기간 안): "Repeated inference over one observation can improve predictions without adding an evidential origin." → A3식 같은 관측 반복 샘플 합의와 달리 우리 합의는 시간차 관측과 실행 뒤 측정이라 **증거 출처가 늘어나는 합의**다.
- **결론 [제안]**: 표(원장)를 중심에 둔다. 겹친 호출이 **같은 미래 결정 스텝**에 낸 typed 답을 "표(vote)"로 쌓되, 각 표에 **그 표가 가정한 전제(premise)** = "그 전에 확정된 스텝들이 코드 예상대로 실행된다"를 붙인다.
  - (a) 합의: 전제가 살아 있는 표끼리만 LocalAgreement-2 / RALCP 투표(γ)로 확정한다(**잠정 기본** — 기간 밖 특정 방법이라 [결정 필요] 4 사용자 승인 전, §7-8). 이 부분에 실제로 거를 불일치가 있는지는 폐루프 전에 E0.5로 먼저 잰다(§5). 순서형 보기는 허용 폭 안이면 일치로 친다.
  - (b) 결과 확인: 확정 스텝이 실행되면 (1) **M5가 공개하는 계획 궤적 `ref(t)`** 대비 측정 상태의 연속 잔차와 (2) M3 `expected_after` 술어의 스텝 끝 성립 여부를 **따로** 계산하고, conformal로 보정한 임계로 범주화한다(OK / LAG / DEVIATE / CONTRADICT). 예상 상태를 `ref(t)`로 두어 Ruckig 추종 지연으로 인한 가짜 LAG를 막는다(00-interfaces §3).
  - **(정본 §33) 학습 실행기 B일 때**: `ref(t)`는 확정된 행동 청크 자체다(연속 잔차 = 측정값 − 청크). `expected_after`는 지금처럼 M3 코드 목표 술어로 둔다 — 실행기와 무관하므로 S·B 조건이 같다. M4 (b) DEVIATE 2회 연속 [가정]은 그 phase를 스크립트 스킬로 넘기는 폴백 조건이기도 하다(M6 §4.1.4). 폴백은 FAIL이 아니고 M4 신호 규칙(아래 줄)은 바뀌지 않는다. M4 규칙은 전부 코드로 남는다.
  - **(정본 §35) 주 시스템(스크립트 스킬 S + 구간 제한 잔차 R)일 때**: `ref(t)`는 **투영 뒤 실제 명령** p(t) = S 명령 + 코드 투영된 잔차다(M6 §4.1.4). 그래서 R이 더한 작은 이동은 (b)에서 가짜 LAG·DEVIATE가 되지 않고, 측정값과 실제 명령의 차이만 잔차로 잰다. R이 꺼져 있으면 `ref(t)`는 S 명령 그대로다. `expected_after`는 M3 코드 목표 술어로 그대로다(S·S+R 같음). R은 Jev 방향 d̂·크기 구간 [m_lo, m_hi] 안에서만 움직이므로 확정된 `option_key`의 뜻을 바꾸지 않는다. 그림자 예측기(M7 §4.2)는 (b)에 넣지 않는다. 원장에는 `jev_choice`(권위값)·∫r·포화 비율·R on/off를 함께 기록한다. 위 B 줄은 E-AE-2의 비교 표(학습 실행기 B)에만 해당한다.
  - 둘을 잇는 고리: (b)가 어긋나면 **그 전제에 기대던 표를 모두 무효화**하고(분산 합의의 term 교체와 같은 구조), 조기 호출을 걸고, 범주를 다음 Jev 입력에 넣는다. 호출 사이 불일치가 갑자기 늘면(TIDE, Rewind-IL) (b)보다 먼저 오는 경고로 쓴다.
  - **M4는 신호만 낸다**(00-interfaces §4·§11.2·§13): CONTRADICT → 모순 술어가 **T1(코드 기하, 결정적)일 때만** M7 하드 채널, T2·`unknown` 술어면 M7 소프트 채널 `C_m4`. DEVIATE → M7 소프트 채널 `C_m4`. `flip_score` → M7 소프트 채널 `C_flip`. `flip_score`는 "한 답 대 한 답" 뒤집힘 수가 아니라 **같은 스텝에 쌓인 표 분포와 직전 창 표 분포 사이 거리**(총변동 거리 등)이고, 임계는 성공 실행으로 conformal 보정한다(00 §12). FAIL 판정·정지·M9 호출은 M4가 하지 않는다. FAIL은 M7만 낸다.
  - 갱신: RTC 3구간을 이산판으로 옮긴다. 고정 구간 = 바꾸지 않음(코드 안전 클램프만), 중간 구간 = 현재 선택 유지 + 도전 선택은 FLy식 "유예 창"을 통과해야 교체, 새 구간 = 새 표 채택(가확정).
- 가장 중요한 차용 5개는 §3 끝에 있다.

---

## 1. 역할과 입출력 (우리 구조)

| 항목 | 내용 |
|---|---|
| 위치 | Astra(느림, 세션 계약) → **Jev ~3Hz 계단식 겹침(M3 질문)** → **M4 원장·확정기(코드)** → 스킬/제어기 100Hz+ → M5 스무딩. M7 critic은 M4 신호(범주, `flip_score`)를 입력으로 받는다 |
| 입력 1 | M3 `DecisionStep` 기록(design/M3 §4.5): `ds_id`, `t_state`, `call_id/sent_at/recv_at`, 질문별 `question_id`·`chosen`·`p_chosen`·`p_second`, 코드가 만든 `target`, `expected_after`(예상 결과 술어) |
| 입력 2 | 측정 상태(M1 인식 앞단 + 로봇 고유 감각): 매 제어 주기 |
| 입력 3 | Jev 지연 기록(p50/p95 이동 창). 고정 구간 길이 `d_p95`의 출처 |
| 입력 4 | **M5 계획 궤적 `ref(t)`**(Ruckig 출력). (b)의 예상 상태 |
| 출력 1 | 확정된 결정 스텝 열(스킬/제어기로), 가확정 스텝 열(M5가 미리 볼 수 있게), 스텝별 `commit_window`(= `d_p95`로 계산, M3·M5는 읽기만) |
| 출력 2 | 스텝별 (b) 범주 → 다음 Jev 입력의 한 줄(예: `last_step: LAG`) |
| 출력 3 | **M7로 가는 신호**: CONTRADICT → 하드 채널(**T1 술어일 때만**, T2·`unknown`이면 `C_m4`), DEVIATE → `C_m4`, `flip_score`(표 분포 거리) → `C_flip`(00-interfaces §4·§11.2·§12·§13) |
| 출력 4 | 조기 호출 요청(스케줄러로). `JevCall` 조립(결정 질문 H개 + 감시 질문, 00-interfaces §2) |
| 하지 않는 것 | Jev에게 예상 상태·수치를 묻지 않는다(수치 약함, plan §1). Jev 확률을 가중 평균에 쓰지 않는다(**E1 전에는 확률 게이트도 끈다**, 00-interfaces §6). 되돌릴 수 없는 물리 행동을 "되돌리기"로 가정하지 않는다. **FAIL 판정, 로봇 정지(hold), M9 호출은 하지 않는다**(M7 FAIL을 거친다) |

M3 안에 따라 원장의 열이 바뀐다(plan M4 v4 의존 문단): D안 = 촘촘한 이동 스텝(초당 3개), G/H안 = 결정 지점 열(다음 스킬, 전이 시점, critic 수락, 목표 선택). **확정기 코드는 같다.** "스텝"은 아래에서 둘 다를 뜻한다.

---

## 2. 분야 전체 최고 후보 표

기간: 첫 공개 2025-03-23 이후. 밖이면 "기간 밖, 기초 문헌". 신뢰도는 v3/README 기준. 이번에 원문(HTML 본문 해당 절)을 읽은 것은 ◎, 초록만 ○, 이전 보고서(v3) 원문 확인에 기댄 것은 △.

### 2.1 하위 부분 (a) 호출 사이 합의 → 확정

| 이름 | 분야 | 어디서 최고였나 (조건 포함) | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| **LocalAgreement-n** (Whisper-Streaming 2307.14743, 원 발상 Liu et al. 2020) △◎ | 동시통역/스트리밍 ASR | 연속 두 갱신 출력의 **가장 긴 공통 접두부**만 확정, 확정분은 뒤 갱신이 못 바꿈. 평균 지연 ≈ 청크 크기의 2배(n=2, 영어 3.3초, MinChunk 1초, v3/08 §2.12). **CUNI IWSLT 2025(2506.17077 ◎ §4 "Simultaneous Translation with EuroLLM"; §2 Background에는 LA 정의만 있음 — D1 A.1 #8 정정): "LocalAgreement … the best-performing policy that does not require attention weights"** — EuroLLM이 attention을 안 내줘서 AlignAtt 대신 LA를 씀. 이 논문 안에 LA 대 다른 정책의 비교표는 없다(저자 주장) | 기초 문헌: IJCNLP-AACL 2023 데모. CUNI 2025는 IWSLT 워크숍 시스템 논문(MED). 같은 연구실(Polák·Macháček)의 자기 평가라는 점 주의 | 기간 밖, 기초 문헌 (CUNI 판은 기간 안) | 예 | 아니오 |
| **AlignAtt** (Papi et al. 2023; CUNI·SimulStreaming 2025에서 사용) ◎ | 동시통역 | CUNI 2025가 "state-of-the-art simultaneous policy"로 채택. Papi 2023이 "이전 정책 전부보다 낫다"고 보고(CUNI §2 재인용) | 기초 문헌(Interspeech 2023) | 기간 밖 | 예 | 아니오 |
| └ 우리에게 | | **attention 가중치가 필요 → 블랙박스 Jev에 못 씀.** 그래서 블랙박스 최선은 LA 계열이다(CUNI 원문 문장이 그대로 근거) | | | | |
| **RALCP** (Relaxed Agreement LCP, Wang et al. 2309.06706) ◎ | LLM 동시통역 | 후보 여러 개에서 위치별 최빈 토큰의 표 비율이 γ 이상이면 접두부로 수용. **0.6 부근이 품질·지연 균형**(§3.3, 부록 C.4 그림 6, Llama2-7b-chat). **γ 절제는 MuST-C 3쌍(en-de·en-ro·en-ru), n=6·beam 10 고정**(D1 A.1 #7 정정: 9쌍 아님). γ 탐색 범위(0.1~1.0)는 그림 안 값이라 본문 텍스트로는 확인 못 함. γ가 크면 지연만 크게 늘고 품질 이득 없음. 후보 수(beam)가 늘면 합의가 어려워져 지연 증가 | 기간 밖(2023-09), Monash, **ALTA 2024**(arXiv Comments, 워크숍급). **MLLP-VRAIN IWSLT 2025(2506.18828 ◎)가 γ=0.5 + wait-k 3으로 채택** → 2025년에도 쓰이는 정책 | 기간 밖, 기초 문헌 | 예 | 아니오 |
| **FLy** (Training-Free Loosely Speculative Decoding, 2511.22972) ◎ | LLM 추측 디코딩 | 불일치 위치에서 (1) 엔트로피 게이트: 결정적인 토큰이면 즉시 거부, 여러 답이 가능하면 (2) **유예 창(deferred window) W 토큰 동안 가수용** → 창 안에 또 불일치가 나오면 모델이 "고치려는 것"으로 보고 소급 거부, 아니면 유지. 정확도 99% 이상 유지, 평균 2.81배(Llama-3.1-70B)·5.07배(405B) 가속, 도메인 밖에서 EAGLE-3 대비 1.62배(초록). 원문에서 창 안의 두 번째 불일치는 **앞서 가수용한 토큰을 소급 거부**하는 신호다(§3 #3의 "다시 나오면 교체"는 우리 재해석) | **HIGH: ICLR 2026**(arXiv comment) | 기간 안(2025-11-28) | 예 | 아니오 |
| **Spec-VLA** (2507.22424) △ | VLA 추측 디코딩 | 초안·검증 행동 토큰의 **행동 거리**가 가까우면 수용. 허용 폭 256 bin 중 5~9, 작업 난도에 따라 다름. 수용 길이 +26~44%, 1.22~1.42배 가속, 성공률 유지 | HIGH: EMNLP 2025 main | 기간 안 | 예(규칙 자체) | 예(VLA 내부) |
| **A3** "Dynamic Execution Commitment of Vision-Language-Action Models" (2605.11567, 2026-05-12, Adelaide·SJTU 외) ◎(D8 정독: 본문·부록·프로젝트 페이지·GitHub INCEPTIONwang/A3 코드) | VLA 실행 확정 | [원문] **같은 관측 s_t에서** K=8 청크를 한 배치로 샘플 → **누적 자세 궤적 공간**에서 합의 점수(군집 우세 모드) → 이중 검증: 합의순 조건부 불변성 + 접두부 닫힘 순차 일관성(RTC식 flow inpainting 재디코딩, 추가 순전파 1회) → 모두 통과한 **가장 긴 접두부 확정**. 허용 폭 δ = 차원별 std(0.5/1/1.5×에서 97.9/98.1/97.8). 결과: π0.5 LIBERO 97.9/6.3 → 98.0/9.8(**본문은 98.1/9.7로 표와 불일치**), 실물 Piper 84.6%(고정 최적 확정 길이 79.2%), 가림·블러에서 최대 +10.2, 호출당 지연 253.2 → 289.5 ms. **시간차 호출 사이 비교 없음, 실행 뒤 예상 대 측정 확인 없음**; §6에서 외부 증거(세계 모델·상태 전이 예측기)를 향후 과제로 명시. **공개 코드와 논문 차이**: 군집·medoid·시간 정렬 코드를 해당 파일에서 못 찾음, 첫 행동은 항상 실행 | 학회 표기 없음(D8), D7 위험 MED | 기간 안 | 예(추론 시점, 단 학습된 VLA 필요) | 예 |
| └ 우리에게 | | **(a) 뼈대("합의 → 앞 구간 확정")의 가장 가까운 선행, 필수 인용(00 §18·§19).** 저자 스스로 우리 (b)에 해당하는 외부 증거를 향후 과제로 남겼다(A3 §6). 빌릴 것(00 §19): 누적 결과 기준 합의·시간 정렬·데이터 척도 허용 폭·"최적 고정 확정 길이" 기준선·평균 확정 길이 지표·관측 열화 스윕(§3 #17, §4.4, §5). 차이: ① 한 모델의 **같은 시각** 샘플 — 우리는 **시간차로 겹쳐 부른** 호출(입력 상태가 다름), ② 학습 VLA 내부 — 우리는 블랙박스 typed 결정 모델(Jev), ③ **(b) 실행 뒤 예상 대 측정 비교가 없다**, ④ 결과가 청크 길이뿐 — 우리는 keep/replace/repair. → §0 새로움 문장, §3 #16, §5 C5-A3·판정 17 | | | | |
| **WCD** World-Coherent Decoding (2609.02159, 09-02) ◎(D12 본문 키워드 정독, 메인이 "realized observation audits" 재확인) | 로봇(WAM 후보 선택) | [원문] "samples multiple candidates from a frozen WAM ... After execution, the realized observation audits the selected imagination, yielding an imagination–reality mismatch that trains a lightweight online predictor for future candidate selection". 본문에 consensus·agree·invalid·replan 0회 | D12 판정: C1 **부분**, 이번 창에서 가장 가까움 | 기간 안 | 예(추론 시점, 단 학습된 WAM 필요) | 예 |
| └ 우리에게 | | 차이(D12): ① **같은 시각**에 학습 WAM에서 뽑은 샘플(시간차 블랙박스 typed 호출 아님), ② 샘플 사이 합의가 아니라 내부 신호로 순위, ③ 예상 대 실제 불일치를 다음 선택을 위한 예측기 **학습 신호**로만 쓰고 전제 무효화나 keep/replace/repair 판정에는 쓰지 않음. → A3와 함께 인용, 차별화 보강 문장(§0, 00 §24) | | | | |
| **SMC** Speculative Macro Commit (2609.03236, 09-03) ○(D12 본문 키워드 확인) | LLM 도구 사용 에이전트 | [원문] "a faster speculative drafter model continuously predicts and executes future action chains ... When the actor's next tool call matches the first drafted action, SMC commits the remaining pre-executed draft steps". 본문 robot·embodied 0회. 격리된 스냅샷 위 추측 실행, 물리 측정 확인·전제 무효화 없음 | D12 판정: C1 (a) **부분**, 비로봇 | 기간 안 | 예 | 아니오 |
| └ 우리에게 | | "두 모델 일치로 확정"의 비로봇 선례로 A3 옆에 인용(00 §24). §2.2 AOSpec/SMC 행과 같은 논문 | | | | |
| AdaptiveSpec "Margins, Not Windows" (2609.02897) ○ | LLM 추측 디코딩 | 불일치 초안 토큰의 타깃 확률 / top-1 확률 비가 임계 이상이면 수용(학습 없음). EAGLE-3 대비 처리량 향상(초록 "최대" 수치, 잘림) | LOW: arXiv만, comment 없음 | 기간 안 | 예 | 아니오 |
| Lossy verification 재검토 (2607.26627) ○ | LLM 추측 디코딩 | 완화 수용은 분포를 몰래 바꿔 품질이 불안정해질 수 있음. "절삭형" 완화는 진짜 절삭 샘플링보다 나빠질 수 있다 — **반대 증거**. 같은 초록: 협력형 검증은 설계 원칙(overshoot 억제, supervision 품질)이 draft·target 선형 보간보다 중요하다 | LOW~MED: arXiv만 | 기간 안 | – | – |
| **Speculative Actions** (2510.04371) △ | LLM 에이전트 | 추측 모델 답이 권위 모델과 **일치할 때만 확정**, 되돌릴 수 있는 것만 추측. lossy 판은 last-write-wins. "최대" 55% 예측 정확도, "최대" 20% 지연 감소 | HIGH: ICLR 2026 | 기간 안 | 예 | 아니오 |
| **Slow Brain, Fast Planner** streaming (2606.20458) △ | 로봇(VLM 내비) | [원문, D9 정독] 고정 주기(기본 1 Hz)로 이전 응답을 기다리지 않고 여러 요청 in-flight(**상한은 원문에 없음**), 매 틱 **요청(카메라 프레임) 시각 기준 가장 새** 유효 응답 하나를 기하 유사도 × 지수 감쇠로 빠른 플래너 점수에 융합(Score / Probability Fusion, §3.3 식 1~3). **응답 사이 일관성 검사·다수결 없음, 실행 뒤 확인 없음**(안전장치는 5 s 하드 타임아웃·사람 개입·무효 응답 폐기뿐). 지연 스윕(§4.2 Fig. 6, 수치 표 없음): Score Fusion 5 s까지 >80%, Probability Fusion 5 s에서 약 78%, VLM Hold 4 s에 거의 0, VLM Stream 5 s에서 <20% — 조건: 영상·물리 없는 운동학 시뮬(unicycle), 고정 후보 K=12, 가짜 플래너(σ=1.0, ε=0.3), **지연 오라클 VLM**(언제나 정답). 절제 Table 4(좌회전, Δt=2 s, 5 seed)에서 **감쇠를 끈 쪽이 약간 더 좋음**(3.565 대 3.457 m). 실물(Table 3) 개입/100 m: Stream 4.40, Match(Stream) 2.18, Score Fusion(Stream) 1.31, Prob Fusion(Stream) 0.87 | MED(UCLA), 학회 미확인 | 기간 안 | 예 | **예** |
| 재번역 안정성·마스킹 (Arivazhagan et al. 1912.03393, 2006.00249) ○ | 스트리밍 번역 | 출력 번복(erasure) 지표와 "마지막 k 토큰 숨기기(mask-k)"로 번복 억제 | 기초 문헌(ICASSP 2020 등) | 기간 밖, 기초 문헌 | 예 | 아니오 |
| Raft/Paxos 커밋 (기초 분산 시스템) | 분산 합의 | 과반이 받은 로그 항목만 커밋, 커밋은 되돌리지 않음. 리더 교체(term 증가) 시 **미커밋 항목 폐기** | 기간 밖, 기초 문헌(비유로만) | 기간 밖 | – | – |
| **Adaptive-Consistency** (2305.11860) | LLM 자기 일관성 조기 정지 | 표본을 하나씩 받으며 "현재 최다 답이 끝까지 최다로 남을 사후 확률 > C_thresh"면 멈춘다(§3, Dirichlet 기준). **실험 기본값은 Beta 근사**다. 1위·2위 표 수만 쓰는 Beta(v1+1, v2+1)에 **C_thresh = 0.95**(§4 Hyperparameters). 17개 데이터셋에서 표본 예산 최대 7.9배 감소, 정확도 평균 하락 0.1% 미만(초록) | HIGH (EMNLP 2023 main, 2023.emnlp-main.761, 인용 156) | **기간 밖, 기초 문헌** | 예(표 수만) | 아니오 |
| CGES (2511.02603) | LLM 자기 일관성 | 표본별 신뢰도 점수를 증거로 답 사후를 만들고, 사후 질량이 기준을 넘으면 정지. 5개 벤치 평균 호출 16.0→6.7(−58%), 자기 일관성과 0.4%p 이내. 보정 가정과 잡음 신뢰도 가정("directional drift" 조건) 아래 보장(초록) | MED-LOW (NeurIPS 2025 Efficient Reasoning **워크숍** Spotlight, arXiv판은 확장판, 인용 4) | 2025-11-04, 기간 안 | 예(신뢰도 가중은 확률 필요 → E1 뒤) | 아니오 |
| Atomix (2602.14849) | LLM 에이전트 트랜잭션 | 효과 3분류: Reversible(즉시 실행, 중단 시 역방향 의존 순서로 보상) / Bufferable(커밋 때 적용) / **Irreversible-gated**(이메일·송금·"physical actions", **커밋 게이트를 지나야만 방출**). 추측·경합 작업에서 진 가지의 잔여 효과를 막는다(본문 §2, 초록) | MED-LOW (무학회, 인용 25) | 2026-02-16, 기간 안 | 예 | 아니오(단 원문이 물리 행동을 비가역 게이트 대상으로 직접 꼽음) |

비교에서 뺀 것: 2025-26 SimulMT 학습형 정책(Stable-Prefix 학습 2609.05799, ExPosST 2603.14903, Hierarchical PO 2604.21045, CMU·BeaverTalk IWSLT 2025 미세조정)은 전부 **학습 필요**라 Jev에 못 쓴다. DOA(2605.31432, 학습 없음)는 **self-attention 접근 필요** → 블랙박스 불가. KL 기반 Judge(2601.04766)는 logit 필요.

관련 연구(00 §18, D7, **LOW, id만 옮김·원문 미확인**): 학습 정책 청크의 **적응형 실행 구간(adaptive execution horizon)** 6편 — 2602.21445, 2606.11408, 2606.03847, 2606.00537, 2607.04739, 2608.09125. D7 요약상 모두 "학습 정책이 한 청크를 얼마나 실행할지"를 정하는 쪽이라 M4 (a)와 관련은 있으나, 시간차 블랙박스 호출 사이 합의나 (b)는 D7 요약에 없다. 제목·수치·학회는 확인하지 않았다(§8). 설계 근거로 쓰지 않는다.

### 2.2 하위 부분 (b) 실행 결과 확인 (예상 대 측정)

| 이름 | 분야 | 어디서 최고였나 | 신뢰도 | 기간 | 학습 없이 | 로봇 적용 |
|---|---|---|---|---|---|---|
| **FIPER** (2510.09459) ◎(초록·본문 일부) | 로봇 실패 예측 | 성공 롤아웃 몇 개로만 conformal 보정한 두 점수(관측 OOD, 행동 청크 엔트로피)를 **짧은 창으로 모아 둘 다 임계를 넘을 때만 경보**. 5개 환경에서 기준 방법 대비 가장 높은 정확도·가장 빠른 탐지(초록). **부록 C.4.2**: "CP 기반 임계는 예측보다 탐지 쪽"(D1 A.1 #5 정정: 한계 절이 아님). 한계 절(D)에는 "시간 가변 임계는 제약적"만 있다. **최고 TWA는 CP 보장이 없는 시간 가변 임계(시점별 경험 분위수)에서 나왔다**(C.4.2) → "conformal = 보장된 임계"로 옮기면 원문의 최고 설정과 다르다 | **HIGH: NeurIPS 2025** | 기간 안 | 보정은 예(RND-OE는 학습) | 예 |
| **Rewind-IL / TIDE** (2604.16683) ◎ | 로봇 실패 탐지 | **겹치는 행동 청크끼리의 불일치(TIDE)** = "정책이 예상 밖 상태를 보고 가까운 미래 계획을 다시 생각하는 신호". 성공 롤아웃으로 split conformal 임계(α=0.001, §IV-B). ACT 6과제 균형 정확도 평균 **0.95** 대 FAIL-Detect 0.83, RND 0.59(Table I). 섭동 조건 성공률 18.3→76.7%(Table II, 20회씩; 되감기 복구 포함). Table I·II 조건: **실물 양팔(AgileX Piper) ACT 6과제** | LOW-MED: arXiv만, 2026-04, 프로젝트 페이지. **잠정 근거** | 기간 안 | 예 | 예 |
| 2512.17250 Input Prediction & Mishit Correction △ | 제어(TD-MPC2) | 예측 잠재 대 실제 잠재 차이: 작으면 보정, 크면 큐 비우고 재계획. 추론 500→282회, 보상 −7.1% | LOW(수업 과제) | 기간 안 | 아니오 | 시뮬 |
| VLA-Corrector (2607.01804) / SV-VLA (2604.02965) △ | VLA | 예측 대 실제 특징 편차가 지속되면 청크를 끊음. π0.5 지평 50 성공 48.7→58.7% | MED-LOW | 기간 안 | 아니오 | 예 |
| AOSpec JASV (2608.00881) / SMC (2609.03236) △ | LLM 에이전트 추측 실행 | 추측을 **"행동과 실행 전 환경이 모두 같을 때만"** 수용(JASV). SMC는 live-state replay 일치 필요 | LOW / LOW~MED | 기간 안 | 예 | 아니오 |
| EFR, Evidence-First Reflection (2608.24015) ○ | GUI 에이전트 | 행동 전후 화면에서 **변화 추출**과 **결과 판정**을 두 단계로 분리해야 판정이 근거를 가진다 | LOW: arXiv만 | 기간 안 | 예(프롬프트) | 아니오 |
| **RoboDawn** (2609.22966, Tsinghua·Tencent Hunyuan, 2026-09-19) ◎(D8 정독: 본문·부록·GitHub Hugo-AGI/RoboDawn 코드) | 로봇(에이전트형 VLM 정지형 제어) | [원문] 명령마다 정지 상태까지 실행한 뒤 다음 관측에 **직전 명령 결과**를 넣는다(RoboDojo: 목표 대비 1.5 cm/8° 안이면 reached, 아니면 실제 이동량; reached/partial/failed 되먹임). 턴마다 VLM 1회, 겹쳐 스트리밍은 "가능하다"고만 쓰고 하지 않음. 결정당 추론 9.74 s, 동작 2.09 s(Seed-2.1-Pro) | arXiv, 코드 공개(2026-09-22) | 기간 안 | 예(API VLM) | 예 |
| └ 우리에게 | | **실행 뒤 되먹임 자체는 선행이 있다.** 다만 겹친 호출이 없어 쌓인 표도, 전제 무효화도 없다 → M4 차별점은 "(b)가 합의 원장의 전제 무효화·확정에 쓰인다"(00 §19, §0) | | | | |
| **Show-Harness** (2609.10522, NUS Show Lab, 심사 전) ◎(D9 정독: 본문·PDF Table 2·코드) | 로봇(VLM 정지형 단위 루프) | [원문] 단위마다 프롬프트에 명령 대 실제 이동량을 되먹인다("Last MV_DOWN lowered {moved} of {commanded} cm → already in contact", 부록 7.4.1). 로봇은 블로킹 `decide` 뒤 `step`(코드 확인). 빈 집기는 폭 규칙(≤ 5 mm)으로 되돌림 | arXiv, 코드 공개 | 기간 안 | 예(API VLM) | 예 |
| └ 우리에게 | | 명령 대 측정 되먹임이 **프롬프트 문맥**으로만 쓰이고, 겹친 호출·표·전제 무효화는 없다 → RoboDawn과 같은 이유로 M4 차별점은 "(b)가 합의 원장의 전제 무효화·확정에 쓰인다"(00 §20) | | | | |
| **EmbodiedSkills** (2609.01281, 09-01) ○(D12) | 로봇 스킬 런타임 | [원문] "treats each skill decision as an execution proposal: the runtime checks its prerequisites before execution and verifies the outcome afterward". 본문 asynchronous·agree·expected 모두 0회 | D12 판정: C1 (b) **부분(약함)** | 기간 안 | 예 | 예 |
| └ 우리에게 | | "실행 뒤 확인 자체"의 선례 목록(Show-Harness, RoboDawn)에 추가(00 §24). 겹친 호출·표·전제 무효화는 없다 → 차별점은 그대로 "(b)가 합의 원장의 전제 무효화·확정 판정에 쓰인다" | | | | |
| ProTracer (2609.21369) ○ | 로봇 실패 진단 | 고유 감각 신호로 행동 경계를 잡고 자연어 서술로 바꿔 VLM과 함께 판정(학습 없음) | LOW: arXiv만, 2026-09 | 기간 안 | 예 | 예 |
| Split / Adaptive conformal (Gibbs & Candès 2021), CUSUM (Page 1954), 이벤트 트리거 MPC (Heemels 등) | 통계·제어 | 분포 무관 임계, 온라인 임계 보정(ACI), 누적 표류 탐지, 잔차가 임계를 넘을 때만 재계산 | 기초 문헌 | 기간 밖, 기초 문헌 | 예 | 예(널리) |

LLM 에이전트 쪽의 "예측 대 실제" 확인은 대부분 **LLM이 다음 상태를 예측**하는 세계 모델형이었다(WebSearch 1회, 결과 목록: 2606.25421, 2602.05842 등 — 학습형 또는 LLM 예측). Jev는 수치·예측에 약하므로(plan §1) **예측은 코드가 하는 로봇 잔차 감시 쪽이 우리에게 맞는 최고 후보**다. 판정: (b)의 최고 조합 = **코드가 아는 예상(M5 `ref(t)` + M3 `expected_after` 술어) + 성공 실행으로 보정한 split conformal 임계 + 짧은 창 집계(FIPER) + 느린 표류는 CUSUM**. 모두 학습 없음.

### 2.3 하위 부분 (c) 갱신·수리 규칙, (d) 스케줄러

| 이름 | 분야 | 원문 요지 (수치) | 신뢰도 | 기간 | 학습 없이 |
|---|---|---|---|---|---|
| **RTC** (2506.07339) △ | VLA | 앞 d(추론 지연) 고정, 중간은 지수 감소 가중으로 이전 청크 따름, 끝은 새로 생성. 앞만 고정(hard mask)은 "방향이 더 빨리 바뀐다", soft mask가 연속성에 결정적(§3.2, 그림 4) | HIGH: NeurIPS 2025, PI | 기간 안 | 예(추론 시점) |
| Training-time RTC (2512.05964) △ | VLA | 추론형이 더 유연(부드러운 반영). 지연 분포를 신중히 골라야 함 | MED-HIGH(PI) | 기간 안 | 아니오 |
| **SmolVLA 비동기** (2506.01844) △ | VLA | 큐 비율이 g 아래면 새 요청. HF 블로그: g≈0.7 절충, 시작 0.5. "네트워크 왕복 무시" 가정 | HIGH(HF, 인용 541) | 기간 안 | 예 |
| TypeGo (2607.05482) △ | 로봇+LLM | 크기 3 bounded queue, 하나 꺼내면 하나 채움, 스텝 = (조건 → 스킬) 분기 | MED-LOW | 기간 안 | 예 |
| Event-triggered (2609.22587) △ | VLA | 장면 변화 점수 P90 임계로 추론 간격 조절 | MED(TUM) | 기간 안 | 규칙은 예 |
| BRACE (2608.01428) △ | 로봇 재계획 | cooldown/commit 창 = anti-churn | HIGH: ICML 2026 | 기간 안 | 예 |
| jev-drone / jev-realtime-sdk △ | Jev 데모 | `stale_after_s: 1.5`, 단일 in-flight, 중앙값 0.11초, "21 decisions/s pipelined" | LOW(관행 기술용) | 기간 안 | 예 |
| **RegenHarness** (2609.27612, 09-23) ○(D12 본문 확인) | 에이전트 하네스(사족 로봇 사례 보고 수준) | [원문] "identity- and version-bound commit gate", 판정 "satisfied, violated, ambiguous, stale, or unsafe", "stale means it is no longer valid for the decision"; "A transition residual is a discrepancy between an expected and observed effect". 과제 진행 상태를 확정하는 게이트, 결정 표 합의·비정지 겹침 호출 없음 | D12 판정: epoch 무효화 **부분(약함)** | 기간 안 | 예 |
| └ 우리에게 | | 전제 epoch 설명에서 "버전에 묶인 증거와 낡은(stale) 판정의 선례"로 인용(00 §24) | | | |

Jev 지연(plan §1, v3/01): OpenRouter P50 0.37초(전 지역), robokrunch 데모 p50 0.527 / p95 0.813초(LOW), 업체 70~500ms(미국 서부). **한국 측정 없음 → E0.** 속도 제한 1,200 요청/분(초당 20).

---

## 3. 가져올 것과 접목 방법 (원문 칸과 우리 접목안 칸 분리)

| # | 원문에 있는 것 | 우리 접목안 [제안] | 옮길 때 깨지는 가정 |
|---|---|---|---|
| 1 | **LocalAgreement-2**: 연속 두 갱신의 공통 접두부 확정, 확정분 불변 | 같은 `ds_id`·같은 `question_id`에 대해 **전제가 살아 있는** 최근 두 표가 같으면 확정 후보. 스텝 열의 **앞에서부터만** 확정(접두부 성질: 뒤 스텝은 앞 스텝 결과에 기댄다) | 원문 "갱신"은 입력이 늘어난 같은 문장. 우리는 입력 상태가 바뀐다 → 표에 전제를 붙여 무효화 규칙(#6)으로 보완 |
| 2 | **RALCP**: 위치별 최빈 비율 ≥ γ면 수용, γ=0.6 균형(후보 10개) | 한 스텝에 표가 3개 이상 모이면 최빈 비율 ≥ γ로 확정(3표면 2표 = 0.67). γ는 실험 변수 {0.5, 0.67, 1.0} | 원문 후보는 한 번 호출의 beam 10개. 우리 표는 시간차 호출 2~4개 → 표본이 작다. γ=0.6 값을 그대로 옮기지 않는다 |
| 3 | **FLy 유예 창 + 엔트로피 게이트** | 확정 대기 중(중간 구간) 스텝에 **도전 선택**이 오면 즉시 바꾸지 않고 W개 호출 동안 가수용 대기. 창 안에서 도전 선택이 다시 나오면 교체, 아니면 현 선택 유지. 게이트: (b)가 OK가 아니면 유예 없이 교체(= "결정적 불일치"). 도전 표의 `p_chosen` ≥ θ 게이트는 **E1 뒤에만 켠다**(00-interfaces §6) | 원문 게이트는 타깃 모델 엔트로피(logit). 우리는 Jev 보기 확률의 임계만 씀. E1 전에는 θ 게이트를 끄고 (b)만 |
| 4 | **Spec-VLA 완화 수용**: 행동 거리 가까우면 수용, 허용 폭은 난도별 | 순서형 보기(크기 구간 등)는 인접 τ 칸 이내면 합의로 친다. 순서 없는 보기는 정확 일치만. τ는 실험 변수, 접촉 근처는 τ=0 | 원문은 256 bin, 우리는 로그 간격 5~9 보기(M3) → 한 칸 차이가 원문보다 훨씬 크다 |
| 5 | **RTC 3구간** (고정 d / 지수 감소 가중 / 새 생성) | 이산판(§4.2): 고정 구간 = 시작 시각이 `now + d̂_p95` 이전인 스텝(변경 금지, 코드 안전 클램프만). 중간 구간 = 교체에 필요한 합의 조건이 **고정 경계에 가까울수록 엄격**(연속 가중의 이산판: 경계 직후 스텝은 W=2·γ=1.0, 멀수록 W=1·γ=0.67). 새 구간 = 가장 새 표를 가확정 | 연속 가중 평균은 이산 보기에 없음(평균 금지, M5·SEAM 교훈). "가중"을 "교체 문턱"으로 바꿈 |
| 6 | **Raft term / AOSpec JASV** (전제 동일할 때만 수용) | 모든 표에 `premise_epoch`(그 표가 가정한 확정 접두부 + 예상 상태 버전)를 붙인다. (b)가 DEVIATE/CONTRADICT를 내면 epoch를 올리고 **이전 epoch 표 중 미확정 스텝 표는 전부 폐기**(Raft의 미커밋 항목 폐기와 같은 모양). 확정·실행된 것은 되돌리지 않는다(물리) | JASV는 실행 **전** 상태 대조, 우리는 실행 **후** 예상 대 측정. 분산 합의는 비유일 뿐 근거 아님 |
| 7 | **Rewind-IL TIDE**: 겹친 청크 불일치의 급증 = 예상 밖 상태 신호, conformal 임계 | **[00 §12로 교체]** 매 도착마다 같은 `ds_id`·`question_id`에 쌓인 표들의 보기 분포와 직전 창(예: 직전 1초) 표 분포 사이 거리(총변동 거리 등)를 `flip_score`로 계산한다. 원장이 이미 스텝별 표를 모으므로 추가 호출이 없다. 첫 판의 "새 표가 가확정과 다른 비율(`flip_rate`, 한 답 대 한 답)"은 Sentinel/STAC(CoRL 2024, **기간 밖**) 절제 그림 5에서 한 샘플끼리 비교가 기준 방법보다 나빴다는 근거로 버렸다. 이 계산식은 [결정 필요] 4(기간 밖 특정 방법 사용) 승인 전까지 **잠정 기본**이다. 기간 안 설명 후보: FIPER(NeurIPS 2025)의 성공 롤아웃 conformal 보정·창 집계 — 분포 대 분포 비교 자체의 기간 안 근거는 찾지 못함(확인 필요). 불허하면 "한 답 대 한 답" 뒤집힘 비율로 돌아가고 E0.5에서 두 식을 함께 잰다. 성공 실행으로 잡은 conformal 임계를 넘으면 **(b)보다 먼저 오는 조기 경고**: M4 안에서는 새 확정 중단 + 조기 호출, 밖으로는 `flip_score`를 **M7 소프트 채널 `C_flip`**으로 보낸다. (b)가 OK로 돌아오고 합의가 회복되면 재개 | 원문은 학습 정책의 연속 청크 MSE. 우리는 이산 보기의 표 분포 거리(00 §12) → 임계는 우리 데이터로 새로 잡음 |
| 8 | **FIPER**: 성공 롤아웃으로 conformal 보정, 짧은 창 집계, **두 지표 모두** 넘을 때 경보 | (b) 잔차(위치·자세·그리퍼 폭·접촉 술어)를 성공 실행 N개로 split conformal 보정 → 범주 경계. 창 길이 w 제어 주기 집계. AND 결합(오경보 억제)은 **M7에만** 둔다: (b) DEVIATE(`C_m4`)와 TIDE(`C_flip`)가 M7의 서로 다른 소프트 채널이 되어, 두 채널 이상이면 M7이 FAIL을 낸다(00-interfaces §4). M4 안에 별도 repair 규칙은 두지 않는다 | 원문은 정책 내부 점수. 우리 점수는 코드 예측 잔차라 해석이 쉽다. 폐루프라 교환 가능성 가정이 약함 → ACI(기초 문헌)로 임계를 천천히 적응하는 선택지 |
| 9 | **CUSUM / 이벤트 트리거 MPC** | 한 스텝으로는 임계 안이지만 같은 방향으로 계속 모자라는 표류(LAG 누적)를 CUSUM으로 잡아 DEVIATE로 올림 | 기초 문헌 |
| 10 | **EFR**: 변화 추출과 판정을 분리 | (b)는 코드가 "무엇이 바뀌었나(측정 술어 차이)"를 먼저 만들고, 판정(범주)은 규칙이 한다. Jev에 넘길 때는 범주 한 줄만(관련 없는 내용 금지, plan §1) | 원문은 VLM 반성 모듈 |
| 11 | **SmolVLA 큐 임계 g + TypeGo bounded queue + Event-triggered P90** | 스케줄러(§4.3): 주기 호출 + 확정 스텝 잔량 < g면 즉시 호출 + (b)≠OK 또는 TIDE 경보면 즉시 호출 | SmolVLA "왕복 무시" 가정 폐기, d̂에 왕복 포함 |
| 12 | **Slow Brain streaming**(D9 정독): 요청 시각 기준 가장 새 유효 응답 하나 + Score/Probability Fusion, in-flight 상한 없음, 5 s 하드 타임아웃. 응답 사이 일관성 검사·실행 뒤 확인 없음 | 기준 방법으로 원문대로 재현(00 §20, §5 조건 표): **C2** = VLM Stream, **C2'** = Probability Fusion + 스트리밍, **C2'-S** = Score Fusion, 선택 **C2-match**. 이전 판의 감쇠 가중 최빈은 우리 변형 **C2''**. 우리 설계는 늦게 온 표도 전제가 살아 있으면 표로 쓴다(newest-wins 아님) | 원문 후보는 연속 궤적(카메라 위 번호 달린 선), 우리 보기는 이산 typed 보기 → Sim은 늦게 온 선택 보기의 **코드 예상 결과 궤적**으로 계산하고 d_scale은 우리 작업공간 척도([가정]). 원문 S1은 플래너 점수 → 우리 S1은 빠른 층 **코드 규칙 점수**(Jev logprob를 S1로 쓰면 원문과 다름) |
| 13 | **Adaptive-Consistency 정지 규칙**(EMNLP 2023, 기간 밖): Beta(v1+1, v2+1)로 "1위가 계속 1위일 확률 > C_thresh"면 정지, 기본 C_thresh 0.95 | **우리 접목안(C3')**: 한 `ds_id`·`question_id`에 쌓인 표 수(1위 v1, 2위 v2)만으로 같은 확률을 계산하고, **C_thresh = 0.9**를 넘으면 확정한다. Jev 확률은 쓰지 않으므로 E1 전 확률 게이트 금지(00-interfaces §6)와 충돌하지 않는다. 마감(고정 구간 진입)까지 못 넘으면 지금 규칙대로 가확정 실행(비정지) | 원문은 "표본 추가를 멈춤"이고 우리는 "확정"이다. 원문 표본은 독립 샘플이지만 우리 표는 같은 모델이 비슷한 입력에 답한 것이라 독립이 아니다(§6). 원문 기본 0.95를 그대로 쓰면 스텝당 약 3표로는 확정이 안 된다(§4.4) |
| 14 | **Atomix 비가역 게이트**(기간 안, MED-LOW): 비가역 효과는 커밋 게이트 전에 방출하지 않는다 | **우리 접목안**: 보기가 M6 스킬 단계 `effect: irreversible`에 속하면 확정 조건을 한 단계 엄격하게 한다(유예 창 **W+1**, 00-interfaces §14-3). 가역 보기는 지금 규칙 그대로 | 원문 게이트는 트랜잭션 커밋이다. 우리 "커밋"은 M4 확정일 뿐이고 물리 효과를 되돌릴 수는 없다. 안전은 코드 안전 술어가 맡는다 |
| 15 | **보기 순서 돌리기**(RecSys 2026 Short Table 1, 기간 안 / NAACL 2024, 기간 밖) | **C3''**: 호출마다 보기 순서만 고정 순열 3개로 순환시키고 표는 보기 id(= `option_key`, 정본 §27 R5, 호출마다 `display_id → option_key` 대응표 기록)로 센다(M3 §4.6). 기본값 아님 | 순서가 다르면 엄밀히 같은 입력이 아니다. `flip_score`가 부풀 수 있어 FLIP_TH를 따로 보정한다 |
| 16 | **A3**(2605.11567, 기간 안, D8 정독): 같은 관측에서 K=8 청크 → 누적 궤적 공간 합의 점수 → 합의순 조건부 불변성 + 접두부 닫힘 순차 일관성 이중 검증(재디코딩) → 가장 긴 검증 접두부 확정. 실행 뒤 예상 대 측정 비교 없음(§6 향후 과제) | **기준 조건 C5-A3로만 쓴다(설계에 넣지 않음, §5)**: 초당 호출 수를 같게 두고, 계단식 대신 **같은 시각에 K개 호출**(K = 1초 안 계단 호출 수, 기본 3)을 묶어 보내 스텝별 최빈 비율로 합의 점수를 매긴다. 앞에서부터 합의 ≥ γ인 가장 긴 접두부를 확정한다. 합의 낮은 스텝은 **다음 묶음 호출에 확정 접두부를 전제로 넣어** 다시 묻는다(A3의 "합의 높은 행동을 조건으로 재검증"을 블랙박스 질문으로 옮긴 것, 추가 호출 없음). (b)·epoch 무효화·범주 되먹임·TIDE는 없다 | 원문은 한 모델 내부의 같은 입력 샘플이고 재검증은 디코더 조건부 생성이다. 우리 이식은 블랙박스 재질문이라 "검증"이 원문보다 약하다(C5-A3가 A3를 과소 재현할 수 있음, 결과에 적는다). H=1이면 접두부 길이가 1이라 사실상 다수결이 된다 → C5-A3는 H=3이 주 칸. K=8 대신 K=3이라 원문보다 표본이 적다. 공정성을 위해 같은 시각 반복 호출의 뒤집힘을 E0.5에서 먼저 잰다(§5) |
| 17 | **A3 부수 요소**(D8 정독, 00 §19): 누적 자세 궤적 공간 합의, δ = 차원별 std, "고정 최적 확정 길이" 기준선(실물 79.2% 대 84.6%), 가림·블러 열화 평가 | **(i) 누적 예상 상태 합의**: 증분·순서형 보기(예: D-줌 이동 보기)는 보기 id 일치와 함께 **코드가 계산한 누적 예상 상태**로도 일치를 판정한다. 보기 id가 달라도 확정 접두부부터 누적한 예상 상태가 허용 폭 안이면 일치(§4.4 `agree_mode`). 허용 폭은 **데이터 척도에서 시작**(성공 실행의 스텝별 예상 상태 변화량 차원별 std × {0.5, 1, 1.5}, A3 δ 절제 모양을 빌림). (ii) **시간 정렬 ±1 스텝 허용** 후보(§4.4 `align_tol`). (iii) 기준 조건 **C-FIX**(§5). (iv) 지표 평균 확정 길이·호출 수. (v) 관측 열화 스윕(§5.1 (4)) | 원문은 연속 행동의 누적 궤적이고 같은 관측 샘플이다. 우리는 코드가 이산 보기를 누적한 예상 상태이고 입력이 시간차다. ±1 스텝 정렬은 A3 공개 코드에서 찾지 못한 요소라(D8) 근거가 약하다 → 후보로만 |

**가장 중요한 차용 5개(순서 = 설계에서의 무게)**
1. LocalAgreement(접두부 확정 + 확정 불변) — 블랙박스에서 가장 좋은 합의 정책(CUNI IWSLT 2025 원문 문장). 기간 밖 기초 문헌. **잠정 기본**: 특정 방법이라 [사용자] 기간 예외("큰 주제의 기초 문헌")에 드는지는 사용자 몫이다([결정 필요] 4, plan §5, D4 D-3). 기간 안 대체 근거: CUNI IWSLT 2025(2506.17077, LA 사용), MLLP-VRAIN IWSLT 2025(2506.18828, RALCP γ=0.5 채택). 불허하면 규칙 모양(접두부 확정·확정 불변)은 기간 안 두 시스템 논문을 근거로 유지하고, "기초 문헌" 인용만 뺀다.
2. FLy 유예 창 + 게이트(ICLR 2026) — 흔들림과 진짜 수정을 구분하는 학습 없는 규칙.
3. RTC 3구간(NeurIPS 2025) — 고정/중간/새 구간 틀. 이산판으로 변환.
4. FIPER(NeurIPS 2025) + split conformal — (b) 임계를 성공 실행만으로 정하고, 두 신호 동시 조건으로 오경보를 줄임.
5. Rewind-IL TIDE(잠정, LOW-MED) — "겹친 출력끼리의 불일치 급증 = 실패 신호". (a)를 확정 규칙뿐 아니라 **조기 경고**로도 쓰게 해 준다.

---

## 4. 설계안

### 4.1 자료 구조

```
Vote      { ds_id, question_id, choice(option_key), p_chosen, call_id, sent_at, recv_at,
            t_state, premise_epoch, perm_id, display_map }   # display_map = 이 호출의 display_id → option_key (정본 §27 R5)
Slot(ds)  { ds_id, t_start, zone ∈ {FROZEN, MID, FRESH},
            status ∈ {OPEN, TENTATIVE, CONTESTED, COMMITTED, EXECUTING, VERIFIED, FAILED},
            incumbent, challenger, defer_left, votes[] ,
            expected_after (코드), outcome ∈ {OK, LAG, DEVIATE, CONTRADICT, -} }
Ledger    { slots[ds_id], epoch, d_hat (Jev 지연 p95, 이동 창), flip_score }   # flip_score = 표 분포 거리(00 §12)
```

- 한 번의 Jev 호출(`JevCall`, 00-interfaces §2) = `JevCall{call_id, t_state, epoch, decision_qs[ds_k … ds_k+H−1], monitor_qs[M7 진행 범주, 필요 시 M8 T3b]}`. 결정 질문은 **H개 미래 스텝**(`t_start ≥ sent_at + d_p95`인 첫 스텝부터 H개). monitor_qs는 호출 N번에 한 번(예: 1초에 한 번)만 싣는 안을 둔다. 입력 길이 상한은 설정 표에 둔다. 각 스텝 질문 앞에 "그 전 스텝들이 코드 예상대로 끝났다고 가정한 상태"(코드가 만든 `expected_after` 술어, 바뀐 술어만)를 적는다. 이것이 표의 전제다.
- **H는 1과 3을 비교한다(E-M4)**. H=1은 M3 원안("한 요청 = 한 결정 스텝")이며, 이때 같은 스텝의 여러 표는 **호출 시각을 스텝 시작보다 앞당겨 같은 스텝을 2~3회 묻기**(질문 문구 동일)로 얻는다. H=3이면 D-줌 세밀 질문은 첫 스텝(ds_k)에만 싣는다(M3 §4.2).
- 주기 T_c = 0.33초(설정 표, 사용자 예 "1초 3번"), H = 3이면 각 스텝이 받는 표 수 ≈ min(H, 스텝 간격·H / T_c) = 약 3표. H=1이면 앞당김 횟수만큼.
- **(정본 §27 R5) 합의는 `option_key`로 센다**: 원장·(a) 합의·최빈·결과 라벨은 고정 `option_key`로 되돌려 센다. 표시 이름·표시 순서·`perm_id`·`display_id → option_key` 대응표는 호출마다 `Vote`에 기록한다. C3''가 보기 순서를 돌리거나, 2지선다 중립 ID에서 ID와 내용의 짝을 순열마다 바꿀 때(PriDe cyclic처럼 A↔B 교대) 이 대응표로 표를 합친다. 확률 평균 없이 최빈 보기만 센다(Jev #8, M3 §4.6).
- **(정본 §28, D17) Jev 일관성 규약 중 M4 몫(J1~J4, 정의 정본 M3 §4.1)**:
  - J1 `Vote.question_id`는 `question_id@vN`이다(문구 + `option_key` 표준 순서 + 보기 설명 + 표시 문자열(공백 포함) + legend + 상태 직렬화기 판본의 해시). 한 슬롯의 표는 같은 `question_id@vN`끼리만 합친다. C3''의 순서 순열은 표준 순서로 해시하므로 판본을 바꾸지 않는다(`perm_id`·`display_map`으로 기록, §27 R5 그대로).
  - J2 상태 직렬화는 같은 세계 상태에서 바이트까지 같은 텍스트다(M1 §4.1). 그래서 두 표의 입력 텍스트가 다르면 상태가 바뀐 것이다.
  - J3 **합의 표는 시간차 상태에서만 모은다.** 같은 입력(같은 `t_state` 텍스트) 되묻기는 측정용(E0·E0.5 (ii))이며 합의 표로 세지 않는다(PACT와 같은 방향, 정본 §24). H=1의 "같은 스텝을 호출 시각을 앞당겨 2~3회 묻기"는 서로 다른 `t_state`라 합의 표다. [우리 해석] E-M4 비교 조건 C5-A3(같은 시각 K개 묶음)는 A3 원문을 재현하는 기준 조건이라 조건 정의를 그대로 두고, 기본 C5에만 이 규칙을 적용한다. `FLIP_TH`와 LA-2 불일치 해석은 E0.5 (ii)에서 잰 test-retest 바닥 위에서 한다(두 갈래에서 바닥 p면 잡음만으로 두 호출이 어긋날 확률 약 2p(1−p), 우리 계산 — 호스트 Jev 바닥 1.33%면 약 2.6%).
  - J4 θ 게이트(E1 뒤)와 `C_flip` 감시는 `question_id@vN`별로만 한다(질문 사이 확률 비교 금지, Jev 공식 약점). E1 보정값은 `question_id@vN` × 모델 ID에 묶이고, 판본이 바뀌면 그 질문의 θ 게이트를 끄고 재보정한다.
  - **J5 conformal 게이트 중 M4 몫 (정본 §31, E1 뒤 후보, 정의 M3 §4.1 J5)**: 선행은 이렇게 했다 — KnowNo(2307.01928, 기간 밖 기초 문헌)와 CoFineLLM(2511.06575, MED)은 "When the prediction set is a singleton, the planner executes that action; otherwise, it requests help". 우리는 이렇게 한다: J5를 켠 질문군에서는 θ 게이트 자리에 예측 집합을 쓴다. 예측 집합이 원소 하나(= 고른 보기)인 표만 확정 후보 조건(LA-2·γ)을 채울 수 있다 [우리 해석]. 집합이 둘 이상이거나 `NONE_ESCALATE`를 포함한 표가 오면 그 칸은 확정 보류(직전 확정 행동 유지 + 감속, 정지 아님)이고, 같은 칸·같은 결정 지점에서 보류가 반복되면 M8에 Astra 호출 신호(`T_j5`)를 보낸다. 보장은 단계별 주변 커버리지뿐이라 (a) 합의·(b) 확인·W+1·확정 뒤 불변 규칙은 그대로 돈다.

### 4.2 확정기 상태 기계 (1순위 안, 결정 모양은 M3 안과 무관)

```
on_vote(v):                                   # 도착 순서 무관(out-of-order 허용)
  if v.premise_epoch < ledger.epoch: drop     # 전제 깨진 표 폐기 (#6)
  if now - v.t_state > STALE_MAX: drop        # 1.5 s 시작값 (jev-drone)
  s = slot[v.ds_id]
  if s.zone == FROZEN or s.status >= COMMITTED: log_only(v); return   # 확정 불변 (#1)
  update_flip_score(v, s)                     # 표 분포 대 직전 창 분포 거리 (#7, 00 §12)
  s.votes.append(v)
  if s.status == OPEN:      s.incumbent = v.choice; s.status = TENTATIVE
  elif agrees(v.choice, s.incumbent, tau): pass
  else:                                        # 도전 선택
     if gate_hard(v, s): replace(s, v.choice)  # (b)≠OK. p_chosen≥θ 게이트는 E1 뒤에만
     elif s.challenger == v.choice: s.defer_left -= 1
          if s.defer_left <= 0: replace(s, v.choice)          # 유예 창 통과 (#3)
     else: s.challenger = v.choice; s.defer_left = W(s.zone_dist) + (1 if irreversible(v.choice) or irreversible(s.incumbent) else 0); s.status = CONTESTED   # 비가역 보기 W+1 (§4.6, M6 effect)
  try_commit_prefix()

try_commit_prefix():                           # 앞에서부터만 확정 (#1)
  for s in slots in order, s not COMMITTED:
     if flip_score > FLIP_TH: break            # 조기 경고 중엔 새 확정 중단
     live = [v in s.votes if agrees(v.choice, s.incumbent, tau)]
     if LA2(s) or ( len(s.votes) >= 3 and len(live)/len(s.votes) >= gamma(s.zone_dist) ):   # C3'에서는 이 줄 대신 P_beta(v1, v2) > C_thresh (§5)
          s.status = COMMITTED
     else: break
  # 확정 못 한 스텝이 고정 구간에 들어가면: 가확정(incumbent)을 그대로 실행 (비정지)
  #   → "unconfirmed-executed" 로 기록, (b) 판정 문턱을 한 단계 엄격하게

on_step_executed(s):                           # (b)
  r    = residual(measured, M5.ref(t))          # (1) 연속 잔차: 예상 상태 = M5 계획 궤적 ref(t)
  pred = holds(s.expected_after, measured)      # (2) M3 예상 결과 술어의 스텝 끝 성립 여부 (따로 계산)
  s.outcome = categorize(r, pred, conformal_bounds, window=w) ; cusum.update(r)
  if cusum.alarm: s.outcome = max(s.outcome, DEVIATE)
  next_jev_input.add_line(f"last_step: {s.outcome}")      # (b) → Jev 입력 (C5'와 대조)
  emit_to_M7(s.outcome, flip_score)            # 신호만: CONTRADICT→하드(T1 술어만, T2/unknown→C_m4), DEVIATE→C_m4, flip_score→C_flip
  match s.outcome:
    OK:          s.status = VERIFIED
    LAG:         keep choices; retime later slots (t_start 뒤로); no epoch change   # ref(t) 기준에서만 판정
    DEVIATE:     epoch += 1; reopen all non-FROZEN uncommitted slots; early_call()
    CONTRADICT:  epoch += 1; drop uncommitted votes; early_call()
                 keep_last_committed_action_and_slow_down()   # 정지(hold) 아님. 완전 정지·M9 복구는 M7 FAIL을 거친다
```

결정 표(요약):

| (b) 결과 \ (a) 상태 | 합의(LA2 또는 γ 이상) | 경합(CONTESTED) | flip 급증(TIDE 경보) |
|---|---|---|---|
| OK | **commit** | **keep** 현 선택, 유예 창 진행 | 확정 중단 + 조기 호출(keep) |
| LAG | commit, 시각만 뒤로 | keep | 조기 호출 |
| DEVIATE | epoch↑, 미확정 표 폐기, **replace**(새 epoch 첫 표 가확정) + M7 `C_m4` 신호 | replace + `C_m4` | replace + 조기 호출 + `C_m4`·`C_flip` |
| CONTRADICT | epoch↑, 미확정 표 폐기, **직전 확정 행동 유지 + 감속**, M7 하드 채널 신호(**T1 술어일 때만**. T2·`unknown`이면 `C_m4`, 00 §11.2·§13) | 같음 | 같음 |

- `C_m4`와 `C_flip`은 둘 다 M4에서 나온다. M7 AND 결합이 한 출처 두 신호로 채워지지 않도록, E-M7 전 기본값은 "같은 출처 채널은 합쳐 1표"다(D4 C-11, M7 §4.2가 채택. E-M7 D4f로 확정).
- 표 밖에서 M4가 하는 일은 신호 발송뿐이다. FAIL 판정(소프트 채널 2개 이상 AND, 하드 채널 즉시)은 M7이 하고, FAIL만이 M8 T_fail과 M9를 시작한다(00-interfaces §4).

### 4.3 스케줄러

```
every T_c (0.33 s, 설정 표, 계단식):  if inflight < N_max and rate_ok(): send_call(JevCall)
N_max = ceil(d̂_p95 / T_c) + 1          # p95 0.81 s면 4, p95 0.3 s면 2
early_call() if: committed_ahead / needed < g (0.5 시작, 0.7 비교)   # SmolVLA
                 or (b) ∈ {DEVIATE, CONTRADICT} or flip_score > FLIP_TH
                 or 장면 변화 점수 > P90 두 번 연속                    # Event-triggered
early_call은 주기 슬롯 하나를 당겨 쓴다 (초당 호출 예산 고정, C0~C6 공정성)
d̂ = d_p95: E0 실측값에서 시작, 최근 50회 지연의 p95로 실행 중 갱신 (Training-time RTC 저자 조언의 이산판)
     고정 구간 길이는 d_p95 하나다. M5의 확정 길이와 M3 commit_window는 이 값을 읽기만 한다 (00-interfaces §5)
상태 지문이 같아도 호출은 보낸다 (표 수 확보) — jev-drone식 생략은 비교 변수
```

### 4.4 조정할 변수 (시작값과 범위)

| 변수 | 뜻 | 시작값 | 범위 / 근거 |
|---|---|---|---|
| T_c | 호출 간격 | 0.33 s(설정 표) | 사용자 예 3회/초. {0.2, 0.33, 0.5} |
| H | 호출당 결정 스텝 수 | **1과 3 비교**(설정 표) | E-M4에서 {1, 3}. H=1은 호출 시각 앞당기기로 표 수 확보 |
| d̂ 분위 | 고정 구간 길이 `d_p95` | p95(E0 측정값) | 기본 p95 고정(설정 표). {p90, p99}는 절제로만 (RTC d) |
| n (LA) | 연속 일치 표 수 | 2 | {2, 3} (n↑ → 지연 선형 증가, RALCP 부록 C.4와 같은 경향) |
| γ | 투표 확정 비율 | 0.67 (3표 중 2) | {0.5, 0.67, 1.0}; 원문 0.6(beam 10) |
| τ | 순서형 허용 칸 | 1 (접촉 근처 0) | {0, 1}; Spec-VLA는 난도별 |
| agree_mode | 증분·순서형 보기의 합의 기준 (00 §19) | 보기 id | {보기 id, **누적 예상 상태**}. 누적 예상 상태 = 확정 접두부부터 코드가 누적 계산한 예상 상태. 보기 id가 달라도 누적 결과가 허용 폭 δ_s 안이면 일치(§3 #17) |
| δ_s | 누적 예상 상태 허용 폭 | 성공 실행의 스텝별 예상 상태 변화량 차원별 std × 1 | {0.5, 1, 1.5}× (A3 δ = 차원별 std 모양, 원문 97.9/98.1/97.8). 접촉 근처는 0.5× [가정] |
| align_tol | 시간 정렬 허용 | 0 스텝 | {0, ±1} 후보 (00 §19). ±1이면 이웃 `ds_id`의 표도 같은 스텝 표로 센다 |
| W | 유예 창(호출 수) | 1 (경계 직후 2) | {0, 1, 2}; FLy W. **M5 L1의 "겹친 호출 2개 연속 같은 새 보기"는 W=2 설정으로 흡수**(00-interfaces §5). 보기 교체 규칙은 여기 한 곳뿐 |
| θ | 교체 게이트 확률 | 끔(E1 전) | E1 뒤에 켤 후보 {0.8, 0.9} |
| q̂ (J5) | conformal 문턱(`question_id@vN`별, 정본 §31) | 끔(E1 전) | E1 적합 세트 비순응 점수의 ⌈(n+1)(1−α)⌉/n 분위, α 후보 {0.05, 0.1, 0.2} [가정]. J5를 켠 질문군에서는 θ를 쓰지 않는다 |
| (선택) 확정 길이 게이트 | AAC식: 합의가 길게 이어지면 확정 대기 스텝을 더 앞까지 확정 | 끔 | 확률 게이트(M5 원안 τ_hi 0.8)는 E1 뒤 후보. 고정 구간 길이(`d_p95`)는 바꾸지 않는다 |
| α | conformal 오경보율 | 0.01 | {0.001(Rewind-IL), 0.01, 0.05} |
| w | (b) 집계 창 | 5 제어 주기 | FIPER 부록 C.3이 창 영향 분석(수치 미확인). M7은 스텝 단위 범주를 10Hz 틱에서 읽는다 |
| FLIP_TH | `C_flip` 임계(표 분포 거리) | 성공 실행 flip_score의 1−α 분위(split conformal) | 우리 데이터(00 §12). E0.5 재생 자료로 먼저 잡는다. 잠정 기본([결정 필요] 4). (정본 §28 J3) E0.5 (ii) test-retest 바닥(층별·시간 블록별) 위에서 해석하고, `question_id@vN`별로 잡는다(J4) |
| STALE_MAX | 표 폐기 나이 | 1.5 s | jev-drone |
| g | 큐 임계 | 0.5 | {0.5, 0.7} (HF 블로그) |
| C_thresh | C3' 정지 확률 기준 (Beta(v1+1, v2+1)에서 P(1위가 계속 1위)) | **0.9 (명시)** | {0.9, 0.95}. 우리가 원문 식으로 직접 계산한 값(원문 수치 아님): 만장일치(v2=0)면 P = 1 − 0.5^(v1+1)이다. 2표 0.875, **3표 0.9375**, 4표 0.969. 반대 1표가 있으면 3:1은 0.8125, 4:1은 0.891, 5:1은 0.9375다. → 0.9면 만장일치 3표, 원문 기본 0.95면 만장일치 4표가 필요하다. 스텝당 약 3표(T_c 0.33 s)에서는 0.95로는 한 번도 확정되지 않는다(D4 검증 §2-3) |
| W_irrev | 비가역 보기의 유예 창 | **W+1** (기본 1 → 2, 경계 직후 2 → 3) | 00-interfaces §14-3. 비가역 여부는 M6 `effect` 필드(§4.6) |

### 4.5 대안 안

- **대안 A (간단판, (b) 중심)**: (a)를 확정 조건에서 빼고 "가장 새 표 + 유예 창 W=1"만 쓴다. (b)와 epoch 무효화는 그대로. v3/18 §6의 "(a) 실익이 작을 수 있다" 대비. C4와 거의 같다. **겹침 호출 자체는 끄지 않는다**(00-interfaces §9 C1).
- **대안 B (Slow Brain 확장판)**: 가장 새 응답 + Probability Fusion(C2', 00 §20)에 (b) epoch 무효화만 더함. 합의 없이도 되는지 보는 가장 싼 안.
- **대안 C (M3 목표 지정형일 때)**: 원장 열 = 결정 지점. 표는 같은 `Q_target`·`Q_phase` 반복 질문. 고정 구간 개념은 "스킬이 이미 시작한 목표"로 바뀌고, 중간 구간 교체는 "스킬 재지정"이라 비용이 커서 W를 2로 올린다.

### 4.6 비가역 보기의 확정 규칙 (W+1, 00-interfaces §14-3)

원문
- Atomix(2602.14849, 기간 안, 무학회): 효과를 가역 / 버퍼 가능 / 비가역 게이트로 나누고, 비가역 효과(원문이 "physical actions"를 직접 꼽음)는 커밋 게이트를 지나야만 방출한다. 사가(Garcia-Molina·Salem 1987, 기간 밖 기초 문헌)는 가역 단계에만 보상을 짝짓는다.

우리 접목안
- **비가역 여부는 M4가 정하지 않는다.** M6 스킬 계약의 phase별 `effect` 필드(M6 §4.1.1: `{kind: reversible, compensate: <스킬 id>}` 또는 `{kind: irreversible}`)를 읽는다. 선택 보기가 `irreversible` phase에 들어가게 하거나 그 phase 안에서 효과를 내는 보기면(예: `dp.release`의 `release_now`) `irreversible(choice) = true`다.
- **규칙**: 비가역 보기에 대한 유예 창은 **W+1**이다(§4.2 의사코드, §4.4 W_irrev). 도전 선택으로 비가역 보기가 들어오든, 현 선택이 비가역 보기에서 다른 보기로 바뀌든 같은 창을 쓴다. γ·LA2·C3' 기준은 바꾸지 않는다. "한 단계 엄격"은 W 하나로만 표현한다(규칙 한 곳 원칙, 00-interfaces §5).
- 기존 규칙은 그대로 둔다: grasp/release 전환 보류 1.0 s(설정 표), M6 `dp.release`의 "M4 확정 + 코드 안전 술어(접촉·높이) 둘 다 필요", 정밀 접촉 구간 τ=0.
- M9 연동(참고): M9 재개는 가역 단계의 보상 스킬을 역순으로 실행하고, 비가역 경계를 넘어 되돌리지 않는다(00-interfaces §14-3). M4는 확정·폐기된 표를 되돌리지 않는다는 지금 규칙을 유지한다.
- 옮길 때 깨지는 가정: Atomix의 커밋은 효과 방출 전 게이트이지만, 우리 확정은 결정 채택일 뿐이다. 확정 뒤 실행이 잘못돼도 되돌릴 수 없다. 그래서 W+1은 "잘못 확정 비율"을 낮추려는 장치이고, 안전 장치는 아니다(안전은 코드 술어와 M7 하드 채널).

---

## 5. 비교 실험 (C0~C6, 판정 기준 사전 기록)

**실험 순서(00-interfaces §8·§13·§17, SUMMARY §3.8)**: E0 지연(실제 `JevCall` 크기) → **E0.5 표 재생(오프라인, E0와 같은 날 가장 먼저)** → E1 보정 → E2a 마차(룰 대 Jev C1, M4 없이) → **E-M4**(C0~C6, H=1·3, M3 = D-줌과 H 두 안. 첫 판 E2에 있던 C5 조건 JD-C5·JG-C5·JH-C5는 여기 첫 칸으로 옮겨 왔다. C5-A3·C-FIX 포함) → E-M4-gen → E-M4-lat(§5.1) → E-M3-2(M4 = E-M4 승자) → E-M5-1. 환경은 단일 팔 자작 장면(00 §13).

**전제 실험**
- E0 지연: 한국에서 Jev p50/p95/p99를 **실제 `JevCall` 크기(결정 질문 H개 + 감시 질문, H=1과 3 둘 다)**로 잰다. 동시 in-flight 1~4개일 때 지연 변화, **같은 입력 재호출 시 답이 바뀌는 비율**(재시험 flip; Sun & Xu 2609.26758이 재시험 기준선에서도 뒤집힘이 있음을 보고 — v3/01). 해석: p95 < T_c/2이면 "지연 흡수"라는 겹침의 목적은 약해진다. 이때도 **겹침은 끄지 않고**, 목적을 "같은 스텝에 여러 표 받기(자기 확인)"로 옮겨 유지한다(00-interfaces §9 C1, [사용자] 필수 요구). 끄는 안은 [결정 필요]. 재호출 flip이 0에 가깝고 상태 변화도 작으면 (a)의 합의는 자명하게 일치 → (a)를 흔들림 억제 지표로 정당화.
- **E0.5 표 재생(오프라인, E 문서 §2A)**: E0 스냅샷 풀에 0.33초 간격 연속 스냅샷 열을 함께 저장하고, H=1 "같은 스텝을 시각을 당겨 2~3회 묻기"를 재생으로 흉내 내 (i) 재시험 flip, (ii) 연속 스냅샷 사이 최빈 보기 불일치율(성공 궤적 기준 flip rate), (iii) 결과 기반 라벨 정답률을 newest(C2, 요청 시각 기준 가장 새 응답) 대 LA-2/γ=0.67(C3의 합의 부분) 대 표 나이 감쇠 가중 최빈(C2'', 우리 변형, 이전 판의 C2')으로 잰다. Probability Fusion(C2', 원문 충실판, 00 §20)은 같은 표 묶음에서 값만 함께 계산한다(여러 표의 합의가 아니어서 (a)의 정보를 재지 않으므로 사전 판정에는 쓰지 않음, E §2A.6). 약 $1~5, 벽시계 하루. **사전 판정**: flip rate가 성공 궤적에서 5% 미만(≈0)이고 합의가 newest보다 정답률 +2%p 미만이면, E-M4 전에 M4 컨트리뷰션 문장을 "(b) + 전제 epoch 무효화" 중심으로 좁히고 (a)는 "안정화 장치"로 적는다. **겹침 자체는 끄지 않는다**(00 §9 C1). E0.5는 `C_flip`의 두 계산식(표 분포 거리 대 한 답 대 한 답)과 FLIP_TH 초기값도 함께 준다. **(D8, 00 §19) C5-A3 공정성**: 같은 스냅샷에 **같은 시각 반복 호출**(K=3, A3식 묶음)의 뒤집힘도 따로 잰다. 같은 시각 뒤집힘이 ≈ 0이면 C5-A3의 합의는 자명하게 일치하므로, 판정 17 결과에 "C5-A3는 같은 시각 표본 다양성이 낮아 A3를 과소 재현했을 수 있다"를 붙인다.
- **(D6, 00 §17) E0.5는 실제로 가장 먼저, E0와 같은 날 돌린다.** E0 첫 세션의 잠정 `d_p95`로 재생하고, E0 4일 결과의 최종 `d_p95`가 잠정값과 T_c(0.33 s) 넘게 다르면 최종값으로 한 번 더 재생해 그 결과로 판정한다(사전 등록, 약 $1 추가). flip ≈ 0(성공 궤적 < 5%)이고 합의 이득 < +2%p면 M4 주장을 **E-M4 설계·구현 전에 미리** "(b) 되먹임 + 전제 epoch 무효화"로 좁힌다(E 문서 §2A.8).
- E1 보정이 E-M4보다 먼저다. E1 전에는 θ 등 확률 게이트를 모두 끈다.
- E2a 마차 시험이 먼저다(Jev가 룰보다 낫지 않으면 M4 대상이 사라짐, plan §5). 방향 재검토는 95% 상한 < +5%p일 때만, 그 밖의 비유의는 "결론 유보"(00 §13).
- (b) 보정: 섭동 없는 성공 실행 ≥ 30회로 conformal 경계와 FLIP_TH를 잡는다(평가 에피소드와 분리).
- (정본 §28) E0.5 (ii) test-retest 바닥은 층별(2지선다·Noul / k 3–6 / k 7–17) × 시간 블록별로 잰다. 블록 차가 유의하면 E-M4 폐루프 조건을 같은 시간 블록 안에 교차 배치한다. FLIP_TH·LA-2 불일치는 이 바닥 위에서 해석한다(J3). 실험일마다 매일 카나리(E 문서)를 먼저 돌리고 "표류 의심" 날의 결과는 분리 보고한다.

**조건** (같은 텍스트 상태·스킬·M5·Jev 버전 `jev-1.13.0`·**초당 호출 수 동일**)

| 조건 | 설명 | 대응 선행 |
|---|---|---|
| C0 | 응답까지 정지 후 실행(비교 기준일 뿐 설계 후보 아님) | jev-libero |
| C1 | 단일 in-flight + 직전 행동 유지 | Jev-as-Policy, jev-realtime-sdk |
| C2 | 겹침 + **VLM Stream**(원문 충실판, 00 §20): T_c 고정 주기, 동시 요청 상한 없음(원문에 상한 없음, 실측 in-flight 수 보고), 매 틱 **요청(관측) 시각 기준 가장 새 유효 응답** 하나의 보기를 그대로 적용, 무효 응답 무시, 마지막 유효 응답이 5 s보다 오래되면 기본 행동(타임아웃) | Slow Brain VLM Stream(§3.3, 부록 C.3) |
| C2-match (선택) | C2 + 늦게 온 선택을 현재 보기 중 **코드 예상 결과가 가장 가까운 것**으로 대응(원문 Hold/Stream/Match/Fusion 사다리 재현용) | Slow Brain Match(Stream) |
| **C2'** | 겹침 + **Probability Fusion + 스트리밍**(원문 실물 배포안, 원문 충실판, 00 §20). [원문 식] 매 틱 현재 보기 집합에 대해 p = (1−α)·softmax(S1) + α·softmax(Sim), α = λ/(λ+1)·exp(−Δt/τ), argmax 실행. Sim(τ_i, τ_vlm) = −(1/d_scale)·(1/N_use)·Σ_{n=1..N_use}‖τ_i[n] − τ̂_vlm[n]‖₂, 진행분 잘라냄(f = (L−s₀)/L, N_use = round(N·f)). [원문 값, 부록 E Table 6 실물] λ=3, τ=5 s, T_vlm=1, 하드 타임아웃 5 s(원문 d_scale 0.3 m; 시뮬 기본값 λ=1, τ=3 s는 절제용). [우리 해석] Δt = 지금 − 요청(관측) 시각. **S1 = 빠른 층 코드 규칙 점수**(M3 R 조건 점수 또는 스킬 기본값, Jev logprob 아님). τ̂_vlm = 요청 시각 기준 가장 새 유효 응답이 고른(늦게 온) 보기의 **코드 예상 결과 궤적**, τ_i = 현재 보기 i의 코드 예상 결과 궤적. d_scale은 우리 작업공간 척도로 줄임([가정], 예: 보기 간 평균 거리). 비기하 보기(next_skill, target_id)는 "같은 id면 1, 아니면 0" 또는 예상 상태 거리(우리 확장, 결과에 표기) | Slow Brain Probability Fusion(Stream)(§3.3 식 1~3, 부록 E Table 6) |
| C2'-S | C2'에서 융합만 **Score Fusion**으로: S_fused = S1 + λ·w(Δt)·Sim, w(Δt) = exp(−Δt/τ), argmax, λ=1(Table 6 실물). 원문은 스트리밍에서 λ가 크면 Score Fusion이 불안정하다고 보고 Probability Fusion을 권장 | Slow Brain Score Fusion(Stream) |
| C2'' | **우리 변형(이전 판의 C2')**: 겹침 + 같은 스텝 표들을 표 나이 지수 감쇠 가중 최빈으로 집계(반감기 0.33 s 시작값). 원문이 아니다 — 원문은 여러 응답 투표가 아니라 가장 새 응답 하나를 빠른 층 점수와 섞고, τ=3~5 s는 반감기 약 2.1~3.5 s다(D9). **보조 기준** | 없음(우리 변형) |
| C3 | 겹침 + (a)만(LA2/γ + 유예 창, epoch 무효화 없음) | LocalAgreement·FLy |
| **C3'** | C3에서 (a)의 확정 조건(LA2/γ)을 **Adaptive-Consistency식 베이즈 정지 규칙**으로 바꿈: Beta(v1+1, v2+1)에서 P(1위 유지) > **C_thresh = 0.9**(표 수만, Jev 확률 안 씀). 절제로 C_thresh 0.95도 돌린다 | Adaptive-Consistency(EMNLP 2023, 기간 밖) · CGES(NeurIPS 2025 워크숍) |
| **C3''** | C3 + **보기 순서 돌리기**(같은 문구·같은 보기 집합, 순서만 고정 순열 3개로 순환, M3 §4.6). FLIP_TH는 이 조건의 성공 실행으로 따로 보정 | RecSys 2026 Short Table 1 · NAACL 2024(기간 밖) |
| C4 | 겹침 + (b)만(범주 + epoch 무효화, 가장 새 표) | 2512.17250식, 대안 A |
| **C5** | 겹침 + (a) + (b) + TIDE 경고 (§4.2 전체) | 제안 |
| C5' | C5에서 (b) 범주를 Jev 입력에서 뺌(코드 재계획만) | "(b)는 그냥 MPC" 반론 분리 |
| **C5-A3** | A3식(§3 #16, 00 §18): 같은 시각 K개 묶음 호출(초당 호출 수 동일)의 합의 → 가장 긴 합의 접두부 확정, 합의 낮은 스텝은 확정 접두부를 전제로 다음 묶음에서 재질문. **(b) 없음**(epoch 무효화·범주 되먹임·TIDE 없음) | A3 2605.11567(D7, 필수 비교) |
| **C-FIX** | 합의 없이 각 호출 답의 **앞 k 스텝을 고정 확정**(나머지는 가확정). k는 보정 시드(평가 시드와 분리)에서 격자 탐색({1, 2, 3}, H=3)한 최적값으로 고정. (b) 없음 | A3의 "고정 최적 확정 길이" 기준선(D8, 00 §19) |
| C6 | C5에서 겹침 끔(단일 in-flight 연속 호출 사이 합의) | 겹침 자체의 기여(측정용, 설계 후보 아님) |

**C2 계열 이름 정정(00 §20, D9)**: 이 절과 §5.1의 판정(1, 11, 11b~11d, 14, 17)과 주 그림 2에 나오는 C2'는 모두 위 **원문 충실판**(Probability Fusion + 스트리밍)이다. 2026-09-24 이전 판의 C2'(감쇠 가중 최빈)는 C2''로 바뀌었고, 같은 판정 식을 C2''에도 계산해 **보조로만** 보고한다(판정 근거 아님). C2'-S·C2-match는 기술 통계로 보고한다. 초당 호출 수는 모든 C2 계열에서 C5와 같다. [우리 해석] 함정: S1이 균등이면 Probability Fusion의 argmax가 사실상 늦은 선택만 따라가 C2-match와 같아진다(허수아비 기준). 그래서 S1 정의와 S1 단독 성공률(= R 조건)을 결과에 함께 적는다.

모든 조건을 **H=1과 H=3** 두 값으로 돌린다(C5가 주 비교 대상, 나머지는 H=E0 이후 예산에 맞춰 선택). **C5-A3는 H=3이 주 칸**이다(H=1에서는 접두부 길이가 1이라 다수결로 줄어든다, 00 §18).

**과제**: E2a와 같은 단일 pick-and-place(M3는 D-줌과 H 두 안) + 실행 중 섭동 4종(물체 2cm 이동, 서보 추종 오차 주입, 짧은 가림, 잡기 미끄러짐). 조건당 섭동 종류마다 ≥ 30회 × 3시드(v3/18의 "3시드"만으로는 10%p 차이를 못 가름 → 회수 추가 제안).

**지표**
- 주: 섭동 과제 성공률 / **잘못 확정 비율**(확정 뒤 (b)가 DEVIATE·CONTRADICT인 스텝 / 확정 스텝, 사후 라벨) / **섭동 반응 시간**(섭동 → 새 선택이 실행에 반영).
- 보조: 결정 번복률(스트리밍 번역의 erasure를 옮긴 것: 가확정 뒤 바뀐 스텝 비율), 확정 지연(첫 표 → 확정), **평균 확정 길이**(한 번에 확정된 연속 스텝 수, A3 지표, 00 §19), **에피소드당 호출 수**, 미확정 실행 스텝 비율, 정지 시간, jerk, 완료 시간, 호출 수·지연 p50/p95.
- 통계: 에피소드 단위 짝 bootstrap 95% CI(같은 시드·섭동 짝).

**판정 기준 (실행 전 고정)**
1. **핵심 주장 "(a)+(b) 확정 규칙"**: C5가 C2와 C2'(원문 충실판 Probability Fusion + 스트리밍, 00 §20) 둘 다에 대해 섭동 성공률 +10%p 이상(CI 하한 > 0)이거나, 성공률이 −2%p 이내이면서 잘못 확정 비율 상대 −30% 이상. 3시드 모두 같은 방향. C2''(우리 변형) 대비 같은 값은 보조로 보고한다.
2. **(a)와 (b) 각각의 기여**: C5가 C3·C4 각각보다 주 지표 하나 이상에서 CI 하한 > 0. (E0.5 사전 판정으로 이미 "(b) 중심"으로 좁혔다면, 이 판정은 그 좁힘을 폐루프에서 확인·번복하는 용도로만 쓴다.) **C4와 C5의 성공률 차가 3%p 미만이고 잘못 확정 비율 차가 상대 10% 미만이면 주장을 (b) 중심으로 좁힌다.** C3가 C2 대비 번복률을 상대 30% 이상 줄이면 (a)는 "안정화 장치"로 유지.
3. **(b)가 그냥 MPC인가**: C5가 C5'보다 섭동 성공률 +5%p 이상이면 "(b) 범주를 결정 모델에 되먹임"을 주장. 아니면 "(b)는 코드 감시"로 쓰고 새로움 문장에서 되먹임을 뺀다.
4. **겹침의 기여**: C6이 C5와 성공률 3%p 이내이고 반응 시간이 나쁘지 않으면(중앙값 +10% 이내) "지연 흡수 이득은 작다"고 **보고만** 한다(E0 결과와 대조). **겹침은 기본안에서 빼지 않는다**([사용자] 필수 요구, 00-interfaces §9 C1). 겹침을 끄는 안은 [결정 필요]로 사용자에게 올린다.
5. **비정지 전체 이득**: C5가 C0 대비 완료 시간 −20% 이상이면서 성공률 −2%p 이내.
6. 변수 절제(γ, W, τ, n): C5 안에서만. 한 번에 하나씩, 기본값 대비 CI 하한 > 0일 때만 기본값 교체.
7. **H**: C5(H=3)가 C5(H=1)보다 주 지표 하나 이상에서 CI 하한 > 0이면 H=3, 아니면 입력이 짧은 H=1을 기본으로 제안한다.
8. **C3'(베이즈 정지, C_thresh 0.9)**: C3'가 C3보다(같은 호출 예산) 잘못 확정 비율이 같거나 낮고(상대 +10% 이내) 확정 지연 중앙값이 짧으면 C3'의 확정 조건을 채택 후보로 올린다. 만장일치 3표가 필요하므로 LA2보다 약 T_c(0.33 s) 늦을 것으로 예상한다. 지연이 길고 오확정률 이득이 없으면 LA2를 유지한다. 채택 후보가 되면 C5 안의 변수 절제(판정 6)로 옮겨 (b)와 함께일 때도 확인한다. C_thresh 0.95 절제는 "스텝당 3표에서 확정되지 않는다"를 실측으로 확인하는 용도다(미확정 실행 스텝 비율로 본다).
9. **C3''(순서 돌리기)**: C3''가 C3보다 섭동 성공률이 CI 하한 > 0으로 높거나, 잘못 확정 비율이 상대 −20% 이상 낮으면 순서 돌리기의 기본 전환을 메인 세션에 올린다(M3 §7-7). `flip_score` 오경보(성공 실행에서 `C_flip` 발동)가 C3보다 2배 이상이면 다른 지표와 무관하게 기본 전환하지 않는다.
10. **비가역 W+1**: 조건이 아니라 C5 안의 절제(W_irrev = W 대 W+1)로 잰다. 비가역 보기의 잘못 확정 수가 W+1에서 줄지 않고 비가역 단계 완료 시간만 +10% 넘게 늘면 W+1을 [결정 필요: 메인 세션]으로 되돌린다.
17. **(00 §18, D7) C5 대 C5-A3 — 새로움 문장 시험**(번호는 §5.1 판정 11~16 뒤로 매김): 같은 시드·섭동 짝, H=3 주(H=1은 보조). (i) C5가 C5-A3보다 섭동 성공률 +5%p 이상(짝 부트스트랩 CI 하한 > 0)이거나, 성공률 −2%p 이내이면서 잘못 확정 비율 상대 −30% 이상(두 라벨 모두 같은 방향, 판정 15)이면 §0 새로움 문장(시간차 합의 + (b)를 함께)을 유지한다. (ii) 섭동 성공률 차가 3%p 미만이고 CI가 0을 걸치며 잘못 확정 비율 차도 상대 10% 미만이면, "(a)+(b) 확정 규칙"을 A3 대비 새로움으로 주장하지 않는다. 주장은 판정 2·3이 남긴 부분((b) 되먹임·전제 epoch 무효화)으로 좁혀 보고한다. (iii) C5-A3가 C5보다 높으면(C5 − C5-A3의 CI 상한 < 0) M4 설계 점검을 메인 세션에 올린다. 부가로 C5-A3 대 C3(같은 (a)만, 같은 시각 대 시간차)를 기술 통계로 보고해 "시간차 겹침"의 몫을 적는다. 판정 1의 비교 대상(C2·C2', 00 §20 원문 충실판)은 바꾸지 않는다. E0.5 같은 시각 뒤집힘이 ≈ 0이면 결과에 과소 재현 단서를 붙인다(위 E0.5).
18. **(00 §19, D8) C5 대 C-FIX**: 같은 시드·섭동 짝, H=3. C5가 C-FIX보다 섭동 성공률 CI 하한 > 0이면 "합의 기반 가변 확정이 최적 고정 길이보다 낫다"를 적는다. 차가 3%p 미만이고 CI가 0을 걸치면 "최적 고정 길이로 충분"을 그대로 보고하고 (a)는 판정 2 규칙대로 좁힌다. 두 조건 모두 평균 확정 길이·호출 수를 함께 적는다(A3도 고정 최적 79.2% 대 84.6%로 보고).

### 5.1 D6 모의 심사 추가 (00-interfaces §17, `D6-mock-review.md` R2·R3·메타 사유 4·5)

**(1) E-M4-lat — 인공 지연 주입 스윕** (R3 약점 3, 메타 사유 5)
- 묻는 것: 지연이 커질 때 C1·C2·C2'·C5의 섭동 성공률이 어떻게 떨어지는가. **Slow Brain(2606.20458)과 같은 축**(가로 = 결정 모델 지연, 세로 = 성공률)에 곡선 4개를 그린다. 우리 가로축은 p95로 적는다(원문은 지연 값 스윕).
- 조건: C1·C2·C2'·C5 × 지연 p95 {0.3, 0.8, 2, 5} s = 16칸(C2·C2'는 00 §20 원문 충실판). 표현·H는 E-M4 주 비교의 승자(판정 7) 하나로 고정. 같은 시드·같은 섭동 시각. 초당 호출 수 동일(T_c 0.33 s), 확률 게이트 끔(00 §6). (00 §20) **C2''**(우리 변형)는 보조로 p95 2 s·5 s 두 점만 돈다(2칸 300 에피소드 추가 [가정], 예산이 모자라면 생략하고 그렇게 적는다). 판정 11~11d는 C2'로만 낸다.
- **Slow Brain 곡선과의 관계(00 §20, D9)**: [원문] Fig. 6의 "Score Fusion 5 s까지 >80%, Probability Fusion 5 s에서 약 78%, VLM Stream 5 s에서 <20%"는 영상·물리 없는 운동학 시뮬(unicycle), 고정 후보 K=12(k-means medoid), 가짜 플래너(σ=1.0, ε=0.3), **지연 오라클 VLM**(Δt∈{0, 0.5, …, 5.0} s, 언제나 정답), 참조 과제 최대 100개, 시간 예산 40 s에서 잰 값이다. Table 4(좌회전, Δt=2 s, 5 seed)에서는 **감쇠를 끈 쪽이 약간 더 좋았다**(Prob+horizon-aware 3.565 대 3.457 m). 저자는 감쇠를 "장면 변화에 대한 보험"으로 해석했고, 시뮬 지연 오라클은 장면 변화를 재현하지 못한다고 한계에 적었다. [우리 해석] 우리 섭동(물체 이동·가림 등)은 바로 그 장면 변화 조건이다 → **E-M4-lat는 Slow Brain이 재현하지 않은 칸을 잰다.** 원문 곡선과 값을 겹쳐 그리지 않고 축만 맞춘다. 판정 11d(차이 없으면 주장 삭제)는 유지한다.
- 구현 = **지연 큐**: Jev 응답을 받으면 바로 확정기에 넘기지 않고 큐에 넣고, 목표 지연 표본 d*만큼 지난 뒤 꺼낸다(추가 대기 = max(0, d* − 실측 지연)). d*는 E0 실측 지연 분포를 p95가 목표값이 되도록 척도만 바꿔 뽑는다([가정]: 분포 모양은 지연 크기와 무관). 실측 지연이 d*보다 길면 그대로 쓰고 그 비율을 칸별로 보고한다(E0 p95가 0.3 s보다 크면 0.3 s 점은 "실측 하한"으로 표시). 요청 발사 시각·`d̂`·`N_max`는 목표 분포의 값으로 다시 잡는다(스케줄러가 지연을 아는 조건). 큐는 확정기 앞 한 곳에만 둔다(M5·스킬·M7 하드 채널은 지연 없음).
- 표본: 칸당 섭동 4종 × 10회 × 3시드 = 120 + P0 30 = 150 에피소드 → 16칸 2,400 에피소드. 칸 사이 비교는 같은 시드·섭동 짝이라 짝 부트스트랩(칸당 비짝 CI 폭 약 ±9%p [우리 계산: p=0.5, n=120], 짝이면 더 좁다).
- 사전 등록 판정
  11. **지연 강건성 주장**: C5 − C2'가 p95 2 s와 5 s 두 점 모두에서 섭동 성공률 CI 하한 > 0이면 "지연이 클수록 확정 규칙 이득"을 주장한다. 한 점만이면 그 점으로 한정해 적는다.
  11b. **기울기**: (0.3 s 성공률 − 5 s 성공률)의 C5 값이 C2' 값보다 작고 차의 CI 상한 < 0이면 "지연에 덜 민감"을 곡선 그림 설명에 쓴다.
  11c. **무손해**: 모든 지연 점에서 C5 ≥ C2' − 3%p(짝 차 CI 하한 > −3%p). 어기는 점이 있으면 그 점과 이유(미확정 실행 비율 등)를 본문에 적는다.
  11d. **Slow Brain으로 충분**: 네 점 모두에서 |C5 − C2'| < 3%p이고 CI가 0을 걸치면 "지연 강건성" 문장을 주장에서 빼고, Probability Fusion(C2', 원문 충실판)이 강한 기준임을 그대로 보고한다.
  11e. 5 s 점에서 C5의 미확정 실행 스텝 비율 중앙값이 50%를 넘으면 "(a)는 이 지연에서 사실상 꺼짐"으로 해석해 적는다(§6 위험).
- 비용·시간 [가정]: 에피소드 약 50 s(리셋 포함, 5 s 칸은 약 +20% [가정]) × 2,400 ≈ 35 시간 직렬 → 환경 4개 병렬 약 9~11 시간(벽시계 약 2일). Jev 호출 수는 지연과 무관(초당 호출 수 동일) → E2a 단가(510 에피소드 ≈ $3)로 환산 약 **$15**(범위 $10~20). 지연 큐 구현 약 0.5일. 요청 한도: 3 Hz × 병렬 4 = 720/분 < 1,200/분.

**(2) E-M4-gen — 모델 일반성 조건** (R2 약점 3, 메타 사유 4)
- 묻는 것: C5 > C2가 jev-1.13.0에만 해당하는가. **같은 확정기(C2·C5 코드 그대로)를 B8 logprob 선택기**(GPT-6 Sol/Luna, `none` effort, EVAL §3.1 범주 8)에 붙인다. 같은 질문 템플릿·같은 보기·같은 초당 호출 수. logprob은 기록만 하고 게이트로 쓰지 않는다(00 §6, E1 전과 같은 규칙).
- 조건: {Jev, Sol/Luna} × {C2, C5}. Jev 칸은 E-M4 본 실행 자료를 재사용하지 않고 같은 날 같은 시드로 다시 돈다(판본·시간대 변동 통제). 표본: 조건당 섭동 4종 × 15회 × 3시드 = 180 + P0 30 → 4조건 840 에피소드.
- 사전 등록 판정
  12. **일반성 지지**: Sol/Luna에서 C5 − C2 섭동 성공률 CI 하한 > 0이고 Jev의 C5 − C2와 부호가 같으면 "확정 규칙은 결정 모델을 바꿔도 이득"을 주장한다.
  12b. 부호는 같지만 CI가 0을 걸치면 "방향 일치, 검정력 부족"으로 적고 주장 문구는 "jev-1.13.0에서"로 한정한다.
  12c. 부호가 반대(Sol/Luna에서 C5 < C2, CI 상한 < 0)이면 M4 주장을 jev-1.13.0 한정으로 좁히고 원인(지연 분포 차, 확률 분포 모양)을 E0.5식 재생으로 따로 본다.
  12d. 두 모델의 실측 지연 p95를 함께 적는다. p95 차가 T_c를 넘으면 E-M4-lat 곡선의 해당 지연 점과 비교해 "지연 차 몫"을 분리해 적는다.
- 비용·시간 [가정]: 840 에피소드 ≈ 12 시간 직렬 → 병렬 약 3~4 시간. Jev 약 $5. **Sol/Luna 단가는 이 문서에서 확인 안 함** → 첫 100 요청으로 재추정([가정]). 질문 형식 어댑터(EVAL 범주 8과 공유) 약 1일.

**(3) E-M4 지표 보강** (R2 약점 1·4, R3 질문, 메타 사유 4)
- **(a)/(b) 분해 그림(주 그림 1)**: 섭동별로 C5 − C2를 (C3 − C2)((a) 몫) + (C4 − C2)((b) 몫) + 나머지(상호작용 = (C5 − C2) − (C3 − C2) − (C4 − C2))로 나눈 막대 그림. 옆에 C5 대 C2'·C5 대 C5'(주 그림 2). 각 막대에 짝 부트스트랩 CI.
  13. [판정] (a) 몫의 CI가 0을 걸치고 (b) 몫의 CI 하한 > 0이면 판정 2의 "(b) 중심 좁힘"을 이 그림으로 보고한다(E0.5에서 이미 좁혔다면 확인용). 상호작용 몫의 CI 하한 > 0이면 "(a)+(b) 결합" 문장을 유지할 근거로 적는다.
- **P0(섭동 없음) 무손해**: C5가 P0에서 C2·C2' 각각 대비 성공률 짝 차 CI 하한 > −2%p이고 완료 시간 중앙값 +10% 이내.
  14. [판정] 어기면 "섭동 이득은 무섭동 손해와 맞바꾼 것"으로 본문에 적고, 손해 원인(미확정 실행·epoch 교체)을 (5)의 분포로 분해한다.
- **잘못 확정 비율, 결과 기반 라벨**: 첫 판 지표((b) DEVIATE·CONTRADICT로 사후 라벨)는 (b)를 가진 C4·C5에 유리한 순환이 될 수 있다(R2 약점 4). 그래서 **E2a-off 결과 기반 라벨러**(스냅샷 복원 → 보기마다 한 스텝 실행 → 오라클 플래너로 최대 10 s 짧은 롤아웃 → 최선 보기 집합, E §4.4b)로 확정된 보기가 최선 집합 밖이었는지를 따로 센다. 조건별 확정 스텝 무작위 500개([가정]: 비율 차 약 5%p를 가르는 규모)에 적용.
  15. [판정] 판정 1의 "잘못 확정 비율 상대 −30%" 조항은 **두 라벨 모두에서 같은 방향**일 때만 성립으로 본다. 둘이 갈리면 결과 기반 라벨 값을 주 값으로 쓰고, (b) 라벨 값은 보조로 적는다.
  - 비용 [가정]: 조건 11개 × 500 스텝 × 보기 ≤ 17 × 10 s 시뮬 → GPU 약 10~20 시간(실시간보다 빠르게, E0.5·E2a-off 라벨러 공유). Jev 추가 비용 없음.
- **epoch 교체 빈도·미확정 실행 비율·번복률 분포** (R3 질문, M7 §5 기록과 공유): 에피소드 단위 값(epoch 교체/초, 미확정 실행 스텝/결정 스텝, 가확정 뒤 바뀐 스텝/가확정 스텝)을 조건별·**성공/실패 에피소드 분리** ECDF로 보고한다. E-M4-lat에서는 지연 점별로 같은 분포를 그린다. 평균만 보고하지 않는다.
  16. [판정] (i) 실패 에피소드 중 epoch 교체 빈도가 상한(초당 1회, §6)에 닿은 시간이 에피소드의 20%를 넘는 비율이 10%를 넘으면 "합의 불능 경로"로 보고하고 conformal 임계 대신 ACI 절제를 판정 6 절제에 추가한다. (ii) 성공 에피소드의 미확정 실행 비율 중앙값이 30%를 넘으면 (a)는 성공 실행에서도 대부분 가확정으로 돈다고 적는다. (iii) 실패 에피소드의 번복률 중앙값이 성공 에피소드의 2배 이상이면 번복률을 M7 소프트 채널 후보(`C_flip`과 비교)로 올린다.

**(4) 관측 열화 스윕** (00 §19, D8: A3가 가림·블러에서 최대 +10.2를 보고)
- 묻는 것: 인식 입력이 나빠질 때 C2·C5-A3·C5의 차가 어떻게 바뀌는가. 열화 = M1 인식 앞단 입력 카메라에 가림·블러를 수준 {0, 약, 강}으로 주입([가정]: 수준 정의는 E-M4 전에 성공 실행 인식 오차로 정한다). 표현·H는 E-M4 승자.
- 표본·비용 [가정]: 3조건 × 3수준 × (섭동 4종 × 10회 × 3시드) = 1,080 에피소드, 약 15 시간 직렬 → 병렬 약 4 시간, Jev 약 $6(E2a 단가 환산).
  19. [판정] 강 수준에서 C5 − C5-A3 섭동 성공률 CI 하한 > 0이면 "열화 조건에서 (b) 결합이 합의만보다 낫다"를 적는다. 모든 수준에서 차가 3%p 미만이면 열화 강건성 문장을 쓰지 않는다.

**순서**: E0·E0.5(같은 날) → E1 → E2a → E-M4(주, 분해 그림·P0·결과 기반 라벨·분포 포함) → E-M4-gen → E-M4-lat. E-M4-lat는 승자 표현·H가 정해진 뒤라 마지막이다. 논문 틀([결정 필요] 18)이 2안이면 E-M4-lat는 필수, 1안이면 M4 단독 논문의 필수 실험이다. → (정본 §26) 논문 한 편(2안)으로 정해져 **E-M4-lat 필수**. E-link는 필수(E-M4·E-M4-lat 뒤, EVAL S3 파일럿 뒤), E-real은 조건부(EVAL §4.4).

---

## 6. 반대 증거와 위험

- **같은 모델의 합의는 틀린 답을 못 막는다.** 시간차 호출은 같은 모델이 비슷한 입력을 보는 것이라 일관된 오답을 반복할 수 있다(v3/18 §6, "Too Consistent to Detect" EMNLP 2025 재인용). → (a)는 흔들림 억제·조기 경고, 오답 차단은 (b)가 맡는다. 판정 기준 2가 이를 가른다.
- **완화 수용은 품질을 몰래 깎을 수 있다.** 2607.26627(LOW~MED)은 lossy 검증이 분포를 바꿔 불안정해진다고 보고. τ>0은 접촉 근처에서 끈다.
- **LocalAgreement는 지연을 늘린다**(n=2에서 청크의 약 2배). 우리 구조에선 두 표가 이미 겹쳐 날아오므로 추가 지연은 약 T_c(0.33초)지만, 첫 표가 스텝 시작 `d̂ + T_c`보다 늦으면 확정 못 한 채 고정 구간에 들어간다 → 가확정 실행(비정지 유지). 이 비율이 높으면 (a)는 사실상 꺼진 셈이다 → "미확정 실행 스텝 비율"로 감시.
- **Slow Brain 반론**: 간단한 융합이 지연 5초에서도 약 80%를 지켰다(Score Fusion >80%, Probability Fusion 약 78%, Fig. 6). 단 이 값은 장면 변화 없는 지연 오라클 운동학 시뮬이고, 감쇠가 오히려 약간 손해였던 조건이다(00 §20, §5.1 (1)). C2'(원문 충실판)가 C5와 같으면 우리 규칙은 복잡도만 늘린 것이다(판정 기준 1·11d). S1을 빠른 층 코드 규칙 점수로 두지 않으면 C2'가 C2-match로 줄어 기준이 약해진다 → S1 정의를 결과와 함께 적는다(§5).
- **A3 선점(00 §18, D7 MED; 00 §19, D8 정독)**: "합의 → 앞 구간 확정"은 A3(2605.11567)가 이미 했다. 우리 차이는 시간차 블랙박스 호출·(b)·keep/replace/repair이고, A3 저자는 (b)에 해당하는 외부 증거를 §6에서 향후 과제로 남겼다. 실행 뒤 되먹임만으로는 RoboDawn에도 있어 차별점이 되지 않는다(§0). C5-A3와 차이가 없으면(판정 17 (ii)) (a)+(b) 결합의 새로움이 무너진다. D7 색인은 arXiv 2026-09-22 17:59 UTC 제출분까지다(9/23~24 제출분 미색인).
- **반대 증거를 동기로(00 §24, D12)**: Type-Safe(2609.26758)는 typed 모델의 보기 이름 편향(0/1 → no/yes로 100개당 70.4개 답 변경, AUC .94 → .23, type-error 0%)을, PACT(2609.01662)는 "같은 관측에 대한 반복 추론의 합의는 증거가 아니다"를 보였다. 둘 다 (a)가 (b) 없이 서면 안 된다는 근거라 §0 서술을 돕는다. 동시에 (a)의 이득이 "흔들림 억제"에 그칠 위험도 키운다 — E0.5 판정 1·3과 새 (i)·(ii)(보기 이름 치환 대조, test-retest 바닥, E 문서 §2A)가 잰다. D12가 더 찾은 선행(WCD·SMC·RegenHarness·EmbodiedSkills)은 부분 겹침이며 D12 색인은 2026-09-23 제출분까지다(9/24 제출분 미색인).
- **conformal 가정**: 폐루프에서는 교환 가능성이 깨진다. FIPER 부록 C.4.2도 "CP 임계는 예측보다 탐지"라고 적었고, 원문 최고 TWA는 CP 보장 없는 시간 가변 임계에서 나왔다. 임계가 틀리면 DEVIATE가 과하게 떠서 epoch가 자주 바뀌고 표가 계속 폐기된다(합의 불능). → epoch 교체 빈도 상한(초당 1회)과 ACI 선택지.
- **Rewind-IL은 잠정 근거**(arXiv만, 2026-04). TIDE를 빼도 설계가 서도록 FLIP_TH를 끌 수 있게 둔다.
- **전제 문장이 입력을 늘린다.** 미래 스텝 질문마다 가정 상태를 적고 감시 질문까지 실으면 Jev 입력이 길어진다(관련 없는 내용 늘면 정확도 하락, plan §1). 가정은 바뀐 술어만 적고, 입력 길이 상한은 설정 표로 둔다. H=1 비교가 이 위험을 직접 잰다.
- **E0에서 Jev가 매우 빠르면**(p95 < 0.17초) 지연 흡수용 겹침의 이득이 약해진다(jev-realtime-sdk 21회/초 주장). 이때도 겹침은 "자기 확인(같은 스텝 여러 표)"으로 유지한다(C1).
- **신호만 내는 M4의 비용**: CONTRADICT에서 직접 멈추지 않으므로, M7이 FAIL을 내기까지(하드 채널은 즉시) 직전 확정 행동을 감속하며 이어간다. 이 사이 위험은 코드 안전 클램프와 M7 하드 채널이 맡는다.
- **C3'(Adaptive-Consistency식)의 가정이 깨진다**: 원문 모형은 표본이 교환 가능(독립 샘플)하다고 가정한다. 우리 표는 같은 Jev가 시간차로 비슷한 입력에 답한 것이라 같은 오답이 반복될 수 있고, 그러면 "1위 유지 확률"이 과대평가된다. 또 원문 기본 0.95는 만장일치 4표가 필요해 스텝당 3표에서는 확정되지 않는다(§4.4) → 0.9를 명시했다. 0.9도 LA2보다 느리다.
- **W+1은 근거가 약한 규칙이다**: Atomix는 무학회이고 트랜잭션 도메인이다. SagaLLM(PVLDB 18(12))은 2025-03-15 공개로 기간 8일 밖이다. W+1이라는 크기는 우리 선택이다(판정 10으로 검증).

---

## 7. 열린 질문, [결정 필요]

1. [결정 필요 ①] H: 00-interfaces §2에 따라 **H=1(M3 원안 + 호출 시각 앞당기기)과 H=3을 E-M4에서 비교**하고 판정 기준 7로 정한다. M3 문서도 같은 내용으로 맞췄다.
2. [결정 필요 ②] 확정 못 한 스텝이 고정 구간에 들어갔을 때: 가확정 실행(비정지, 제안 기본) 대 그 스텝만 "직전 행동 유지"(C1식). 사용자 "웬만하면 멈추지 않는다"를 따라 앞 안을 기본으로 둠.
3. [결정 필요 ③] 정밀 접촉 구간에서 τ=0·W=2로 보수화하는 것으로 충분한지, 정밀 접촉 구간의 짧은 정지(동기 실행, WAM 72.5 증거)를 사용자 예외로 인정할지(00-interfaces §4 [결정 필요], plan §5-10).
4. 열린 질문: M5 `ref(t)`와 M3 `expected_after`가 스킬마다 얼마나 정확한가(예상 자체가 틀리면 (b)가 오경보). M6 `predict_after`는 `expected_after`를 만드는 함수 하나로 합친다(00-interfaces §3).
5. 열린 질문: E1 뒤 Jev 확률을 게이트 θ로 켤 때 보정 곡선이 보기 수·질문 유형별로 다를 것 — θ는 질문 유형별. E1 전에는 끈다.
6. 열린 질문: Astra가 계획을 바꿨을 때(M8) epoch를 올리는 것이 맞는가 — 제안: 올린다(계약 변경 = 전제 변경).
7. [결정 필요] 겹침을 끄는 안(C1): 기본은 끄지 않는다. E0·E-M4 결과가 "겹침 이득 없음"이어도 보고만 하고, 끌지는 사용자가 정한다.
8. [결정 필요 4, plan §5] 기간 밖 특정 방법이 정한 기본값: LocalAgreement(합의 규칙), Sentinel/STAC식 `C_flip`(표 분포 거리), RALCP(ALTA 2024). 사용자 승인 전까지 **잠정 기본**이다. 불허 시: LA → 기간 안 CUNI·MLLP-VRAIN 판 근거로 규칙 유지, `C_flip` → "한 답 대 한 답" 뒤집힘 비율(E0.5에서 두 식 비교 결과 첨부).
9. 해소(00-interfaces §14-3): 비가역 보기는 확정 조건을 한 단계 엄격하게(**W+1**) 한다. 비가역 여부는 M6 `effect` 필드에서 읽는다(§4.6). 메인 세션 잠정 결정이며 판정 10으로 검증한다.
10. 해소(00-interfaces §14·§15): E-M4에 C3'(C_thresh 0.9 명시)와 C3''(순서 돌리기, 기본값 아님)를 추가했다. 둘 다 기간 밖 기초 문헌(EMNLP 2023, NAACL 2024)에 기대는 부분이 있어, 기본으로 바꿀 때는 [결정 필요] 4(기간 밖 특정 방법 사용)와 같은 묶음으로 올린다.
11. 해소(00-interfaces §17, D6): E-M4-lat·E-M4-gen·지표 보강을 §5.1에 넣었다(판정 11~16). E-real 최소판(실물 단일 팔)은 [결정 필요] 19, 논문 틀(E-M4-lat 필수 여부 포함)은 [결정 필요] 18(plan §8) → 해소(정본 §26, user-log 25): 한 편, E-M4-lat·E-link 필수.
12. 해소(00-interfaces §18, D7): §0 새로움 문장을 고쳤고, E-M4에 C5-A3와 판정 17을 넣었다. 적응형 실행 구간 6편은 LOW 관련 연구로만 적었다(§2.1 아래).
13. 해소(00-interfaces §19, D8): §0 차별화 문장 확정, A3·RoboDawn 행, 누적 예상 상태 합의·±1 스텝 정렬(후보)·데이터 척도 허용 폭(§4.4), C-FIX·평균 확정 길이·호출 수·관측 열화 스윕(판정 18·19), E0.5 같은 시각 뒤집힘. ±1 스텝 정렬은 기본값이 아니라 후보다.
14. 해소(00-interfaces §20, D9): C2 = VLM Stream, C2' = Probability Fusion + 스트리밍(λ=3, τ=5 s, T_vlm=1, 5 s 타임아웃, S1 = 빠른 층 코드 규칙 점수), C2'-S(Score Fusion λ=1), 선택 C2-match, 이전 C2'는 C2''(우리 변형, 보조). 열린 질문: d_scale 척도와 비기하 보기 유사도(같은 id 1/0 대 예상 상태 거리)는 [가정]이다.
15. 해소(00-interfaces §24, D12): §0 D12 선행·동기 줄, §2.1 WCD·SMC, §2.2 EmbodiedSkills, §2.3 RegenHarness 행을 넣었다. 새 [결정 필요]는 M4에 없다(D32 보기 이름 규칙은 M3·M6, SUMMARY §5.1).
16. 해소(정본 §27, D14): D32 보기 이름 규칙 중 M4 몫은 **R5** — 합의·최빈·원장은 `option_key`로 세고, C3''로 순서를 돌리거나 2지선다 중립 ID의 짝을 바꿀 때 호출마다 `display_id → option_key` 대응표를 기록한다(§4.1 `Vote`). 새 [결정 필요]는 없다.
17. 해소(정본 §28, D17): J1~J4 중 M4 몫 — `Vote.question_id` = `question_id@vN`, 합의 표는 시간차 상태에서만(같은 입력 되묻기는 측정용), `FLIP_TH`·LA-2 불일치는 E0.5 (ii) 바닥 위에서, θ·`C_flip`은 `question_id@vN`별로(§4.1). 새 [결정 필요]는 없다.
18. 해소(정본 §33): B 실행기일 때 `ref(t)` = 확정된 행동 청크, `expected_after`는 변경 없음, DEVIATE 2회 연속 [가정] = phase 폴백 조건(FAIL 아님). 새 [결정 필요]는 없다.
19. 해소(정본 §34·§35): 주 시스템(S + R)에서 `ref(t)` = 투영 뒤 실제 명령, `expected_after`는 변경 없음, 그림자 예측기는 (b)에 넣지 않음. 18번(B)은 E-AE-2 비교 표에만. 새 [결정 필요]는 없다.

---

## 8. 확인 못 한 것 (조사 방법 포함)

- 조사량: arXiv 검색 API 12회(5초 간격, 모두 응답: A01 local agreement SimulMT, A02 SimulMT LLM policy, A03 SimulStreaming, A04 speculative relaxed/lossy/judge, A05 IWSLT 2025 simultaneous, A06 re-translation stability, A07 streaming stable prefix, A08 agent predicted-state verification, A09 runtime monitoring conformal robot, A10 world model LLM agent verification, A11 training-free failure detection, A12 GUI agent post-action verification). WebSearch 1회. 원문 본문 읽음: 2506.17077, 2506.18828, 2309.06706(§3.3·부록 C.4), 2511.22972(§2.2), 2604.16683(§IV-B·Table I–II), 2510.09459(초록·서론·지표 절). 초록만: 2505.24016, 2506.13143, 2512.17648, 2607.26627, 2609.02897, 2609.05799, 2605.31432, 2601.04766, 2609.21369, 2608.24015, 2506.09937.
- **SimulStreaming(Macháček 2025)의 LocalAgreement 대 AlignAtt 정량 비교표**는 찾지 못했다(검색 A03은 Simulstream 툴킷만 잡음). CUNI 원문의 정성 문장만 근거.
- FLy의 과제별 수치·W 기본값, FIPER 부록 C.3(창 크기 영향)의 수치는 읽지 않았다. FIPER NeurIPS 2025 채택은 D1 검증에서 확인됨.
- Rewind-IL 학회 채택 여부, FLy·FIPER·Rewind-IL의 인용 수(S2 API 사용 금지 규칙).
- RALCP 원 논문(2309.06706)의 학회: D1 검증에서 arXiv Comments "Accepted to ALTA 2024" 확인(이 문서 첫 판의 "확인 못 함"을 정정). γ 탐색 범위(그림 6 안의 값)는 여전히 텍스트로 확인 못 함.
- "2025년 이후 스트리밍 LLM 에이전트에서 시간차 호출 합의로 확정"하는 사례: 이번 검색(A01·A02·A07·A08·A10)에서 못 찾음. v3/18의 53개 검색과 합쳐도 **부록에만 있는 방식은 못 잡는다**는 한계는 그대로다. 없다고 단정하지 않는다.
- Jev 재호출 결정성(같은 입력 → 같은 답 비율)과 한국 지연: E0에서 잰다.
- AdaptiveSpec의 확률 비 규칙은 LOW라 설계 기본값에 넣지 않았다(θ 게이트 대안으로만 기록).
- Adaptive-Consistency §3·§4(Beta 근사, C_thresh 0.95)와 CGES 워크숍 채택, Atomix §2 효과 분류는 D4 검증 #9·#10·#2의 원문 확인에 기댄다. 이번에 다시 읽지 않았다. 0.875·0.9375·0.969·0.8125·0.891 등은 원문 식으로 **우리가 계산한 값**이다(원문 수치 아님). 몬테카를로로 교차 확인했다.
- ESC(ICLR 2024)·Flexible Paxos 원문은 읽지 않았다(D4 §15).
- (D7) A3(2605.11567)는 메인 세션의 초록 확인에만 기댄다. 본문(합의 점수 식, 검증 방식, 수치, 학회)은 읽지 않았다. → **(D8) 정독 보고(`D8-robodawn-a3-deepread.md`)로 갱신**: 알고리즘·수치·§6 향후 과제는 D8에 기댄다(이 문서에서 원문을 다시 읽지 않음). 학회 표기 없음. 공개 코드에서 군집·medoid·시간 정렬 부분을 못 찾은 것은 D8 보고 그대로다. 적응형 실행 구간 6편(2602.21445, 2606.11408, 2606.03847, 2606.00537, 2607.04739, 2608.09125)은 **id만** 옮겼고 제목·내용 모두 확인하지 않았다. D7 색인 한계: arXiv API 최신 제출 2026-09-22 17:59 UTC.
- (D9) Slow Brain·Show-Harness 원문 사실은 D9 정독 보고와 메인 세션의 Slow Brain 부록 E Table 6·§3.3 재확인에 기댄다(이 문서에서 원문을 다시 읽지 않음). Slow Brain Fig. 6 점별 값·에피소드 수·Fusion 곡선이 순차인지 스트리밍인지는 미확인, 공개 코드 없음.

## 출처
- https://arxiv.org/abs/2506.17077 (CUNI IWSLT 2025, §4) · https://arxiv.org/abs/2506.18828 (MLLP-VRAIN, 부록 Table 3) · https://arxiv.org/abs/2309.06706 (RALCP §3.3, 부록 C.4, ALTA 2024) · https://arxiv.org/abs/2307.14743 (Whisper-Streaming)
- https://arxiv.org/abs/2511.22972 (FLy, ICLR 2026) · https://arxiv.org/abs/2507.22424 (Spec-VLA) · https://arxiv.org/abs/2609.02897 · https://arxiv.org/abs/2607.26627 · https://arxiv.org/abs/2601.04766 · https://arxiv.org/abs/2510.04371
- https://arxiv.org/abs/2510.09459 (FIPER, NeurIPS 2025, 부록 C.4.2) · https://arxiv.org/abs/2604.16683 (Rewind-IL) · https://arxiv.org/abs/2609.21369 · https://arxiv.org/abs/2608.24015 · https://arxiv.org/abs/2506.09937
- https://arxiv.org/abs/2606.20458 · https://arxiv.org/abs/2506.07339 · https://arxiv.org/abs/2512.05964 · https://arxiv.org/abs/2506.01844 · https://arxiv.org/abs/2607.05482 · https://arxiv.org/abs/2609.22587 · https://arxiv.org/abs/2608.01428 · https://arxiv.org/abs/2608.00881 · https://arxiv.org/abs/2609.03236 · https://arxiv.org/abs/2512.17250
- https://arxiv.org/abs/1912.03393 · https://arxiv.org/abs/2006.00249 (재번역 안정성, 기초 문헌)
- https://arxiv.org/abs/2605.11567 (A3, D7·D8 §6) · https://arxiv.org/abs/2609.22966 (RoboDawn, D8) · 적응형 실행 구간(LOW, 미확인): https://arxiv.org/abs/2602.21445 · https://arxiv.org/abs/2606.11408 · https://arxiv.org/abs/2606.03847 · https://arxiv.org/abs/2606.00537 · https://arxiv.org/abs/2607.04739 · https://arxiv.org/abs/2608.09125 · https://arxiv.org/abs/2609.10522 (Show-Harness, D9) · Slow Brain 2606.20458은 D9 정독(§3.3, 부록 B~E)
- WebSearch 결과 목록(참고만): https://arxiv.org/html/2606.25421 , https://arxiv.org/pdf/2602.05842
