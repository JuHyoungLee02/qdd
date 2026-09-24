# D9 원문 정독: Slow Brain(2606.20458) · Show-Harness(2609.10522) · GPT-as-Policy(Galbot 기술 보고서)

작성: 2026-09-24 00:35 UTC. 정독 에이전트 보고 전문을 메인 세션이 저장(수치·설정은 줄이지 않음 — D8 요약 실수의 교훈). 메인 세션 원문 재확인: Slow Brain 부록 E Table 6(τ 5 s, d_scale 0.3 m, Score λ 1.0, Prob λ 3.0, T_vlm 1.0, 하드 타임아웃 5 s), §3.3 "newest-by-timestamp response".
작업 규칙: WebSearch·GitHub API 없음, 요청 간격 2초 이상.
읽은 원문: Slow Brain arXiv HTML v1 전문 + 부록 A~G(공개 코드·프로젝트 페이지 링크 없음, 2026-06-18, Amazon FAR·UCLA 등) / Show-Harness arXiv HTML 전문 + PDF Table 2 + 프로젝트 페이지 + GitHub README + 코드 8개(plugins/README.md, plugins/{action_chunk, variable_step, recovery, smooth, dagger}/plugin.py, core/launch.py, core/runners/real.py, configs/robot_franka.yaml) / GPT-as-Policy README, `hybrid_rollout/robodojo/SOURCE.json`, 보고서 사이트 data.json, 사이트 본문과 SKILL.md·gate_prompt.md·teacher_context.md.

## 1. Slow Brain, Fast Planner (2606.20458)
### 원문 사실
- **VLM이 고르는 것(§3.1, §3.2, 부록 A.1)**: 플래너 후보 번호 k*∈{1..K} 또는 "stop". 후보는 카메라 영상 위 번호 달린 색 선. 파싱 실패·시간 초과면 플래너 최고점(argmax S1). 실물 기본값: S2E 앵커 64개 중 점수 상위 K=18(부록 A.2), K는 18 부근에서 포화, 24 넘으면 오히려 복잡(Fig. 4B). 플래너 점수·목표를 VLM에 숨기는 편이 좋았다(점수를 보이면 플래너 순위를 따라감, §4.1).
- **융합(§3.3 식 1~3)**: Sim(τ_i, τ_vlm) = −(1/d_scale)·(1/N_use)·Σ_{n=1..N_use} ‖τ_i[n] − τ̂_vlm[n]‖₂. τ̂_vlm = VLM이 고른 궤적을 오도메트리로 현재 좌표계로 옮긴 것. 현재 위치를 그 궤적에 투영해 진행 호 길이 s₀, 남은 비율 f=(L−s₀)/L, N_use=round(N·f). 감쇠 w(Δt)=exp(−Δt/τ_decay)("typically 3–5 s"). Score Fusion: S_fused = S1 + λ·w(Δt)·Sim, argmax 실행. Probability Fusion: p = (1−α)·softmax(S1) + α·softmax(Sim), α = λ/(λ+1)·w(Δt) ≤ 1.
- 실물 기본값(부록 E Table 6): τ=5 s, d_scale=0.3 m, Score λ=1.0, Prob λ=3.0, T_vlm=1.0, 하드 타임아웃 5 s. 시뮬 기본값 τ=3, λ=1(부록 D.3).
- **스트리밍(§3.3, 부록 B.6, C.3)**: 고정 주기(기본 1 Hz), 이전 응답을 기다리지 않음, 여러 요청 in-flight(**상한은 원문에 없음**), 매 틱 도착한 응답 중 **요청(카메라 프레임) 시각 기준 가장 새것 하나**와 융합, 도착 순서 역전 흔함. 요청마다 단조 증가 ID + 프레임 시각. 순차 모드(in-flight 1)는 Hold·Match에만.
- **응답 사이 일관성 검사·다수결: 없음.** **실행 뒤 확인: 없음.** 안전장치는 하드 타임아웃(마지막 유효 응답 > 5 s면 정지 또는 플래너만), 사람 개입, 무효 응답 폐기뿐.
- **지연 스윕(§4.2 Fig. 6, 수치 표 없음)**: Score Fusion 5 s까지 >80%, Probability Fusion 5 s에서 약 78%, VLM Hold 2 s 넘어 붕괴·4 s에 거의 0, VLM Stream 5 s에서 <20%. 조건: 영상·물리 없는 운동학 시뮬(unicycle), 고정 후보 K=12(k-means medoid), "가짜 플래너"(σ=1.0, ε=0.3 확률로 점수 전체 무작위 교체), 지연 오라클 VLM(Δt∈{0, 0.5, …, 5.0} s, 언제나 정답), 참조 과제 최대 100개, 시간 예산 40 s(부록 B.1~B.5). Fig. 6의 에피소드 수, Fusion 곡선이 순차인지 스트리밍인지 미명시. 스트리밍에서 λ가 크면 Score Fusion 불안정 → Probability Fusion 권장.
- **절제(부록 D)**: Table 4(좌회전, Δt=2 s, 5 seed) 시뮬에서 **감쇠를 끈 쪽이 약간 더 좋음**(Prob+horizon-aware 3.565 대 3.457 m). 저자 해석(D.2): 지연 오라클은 틀리지 않으니 감쇠는 "장면 변화에 대한 보험". Table 5: τ·λ 모두 단조(클수록 좋음), 기본점 (3, 1)은 평탄 영역.
- **실물(§4.3 Table 3)**: 5 경로, 4G, Gemini 2.5 Flash Lite, 중앙 지연 약 2.7 s(1.7~4.5 s, Fig. 8). 개입/100 m: Local 3.49, Hold 8.15, Stream 4.40, Match(Stream) 2.18, Score Fusion(Stream) 1.31, Prob Fusion(Stream) 0.87.
- 오프라인(§4.1): 어려운 장면 약 2,000개에서 ADE 플래너 1.64 m → VLM 1.16 m(−30%), 오라클 0.39 m. 평범한 장면에서는 VLM이 더 나쁨.
- 저자 한계: 후보에 좋은 것이 없으면 소용없음, 평범한 상황에서 이득 없음, 시뮬 지연 오라클은 장면 변화를 재현 못 함, 향후 과제 = 플래너가 불확실할 때만 부르는 적응형 호출.
### 우리 해석
- **C2 = VLM Stream**: T_c 고정 주기, 동시 요청 상한 없음(실측 보고), **요청 시각 기준** 가장 새 유효 응답의 보기를 그대로 적용, 무효는 무시, 5 s 타임아웃이면 기본 행동. 보조 **C2-match**(늦은 선택을 현재 보기 중 예상 결과가 가장 가까운 것으로 대응) → Hold/Stream/Match/Fusion 사다리 재현.
- **C2' = Probability Fusion + 스트리밍(원문 실물 배포안)**, Score Fusion은 C2'-S. 매 틱 현재 보기 집합 = 원문의 "새 후보", τ_vlm = 늦게 온 선택 보기의 **코드 예상 결과 궤적**(진행분 잘라냄, f·N_use), d_scale은 우리 작업공간 척도로 줄임([가정], 예: 보기 간 평균 거리), 초기값 λ=3, τ=5 s(실물) 또는 λ=1, τ=3 s(시뮬), T_vlm=1, 타임아웃 5 s, Δt = 지금 − 요청(관측) 시각.
- **핵심 함정**: S1(빠른 층 점수)이 필요하다. 균등이면 Prob Fusion argmax가 사실상 늦은 선택만 따라가 C2-match와 같아진다. 원문 구조 = 빠른 층 **코드 규칙 기본값(M3 R 조건 점수 또는 스킬 기본값)**, 느린 층 Jev. Jev 자신의 logprob를 S1로 쓰면 원문과 다르다.
- **현재 문서 불일치**: E-first §2A의 C2'("표 나이 지수 감쇠 가중 최빈, 반감기 0.33 s")는 원문이 아니다(원문은 여러 응답 투표가 아니라 가장 새 응답 하나를 빠른 층 점수와 섞음, τ=3~5 s는 반감기 약 2.1~3.5 s). → 이름을 C2''로 바꾸고 원문 충실판 C2'를 따로 둔다. 비기하 보기(next_skill, target_id)의 유사도는 "같은 id면 1, 아니면 0" 또는 예상 상태 거리(우리 확장, 표기).
- E-M4-lat: "5 s에서도 80%"는 장면 변화 없는 지연 오라클 운동학 시뮬이고 감쇠가 오히려 손해였던 조건. 우리 섭동(물체 이동·가림)은 저자가 "재현 못 한다"고 한 장면 변화 조건 → E-M4-lat는 Slow Brain이 비운 칸을 잰다. 판정 11d(차이 없으면 주장 삭제)는 유지.
- 차별화 초안: "Slow Brain은 가장 새 VLM 선택 하나를 기하 유사도 × 지수 감쇠로 빠른 플래너 점수에 섞을 뿐, 응답 사이 일관성이나 실행 뒤 예상 대 측정 비교를 쓰지 않는다(§3.3, 부록 C.3). 우리 M4는 시간차 응답 사이 합의와 실행 뒤 예상 대 측정 비교로 전제가 깨진 표를 무효화하고 확정한다."

## 2. Show-Harness (2609.10522, NUS Show Lab, 심사 전)
### 원문 사실
- **의미 행동 단위(§3.2)**: 이동 6개 MV_FWD, MV_BACK, MV_LEFT, MV_RIGHT, MV_UP, MV_DOWN(방향은 그 시점 기준 시점에 상대적), 회전 ROTATE_CW/CCW(x, y, z 축 지정), GRASP, RELEASE, DONE, 양팔이면 쉬는 팔 STILL(부록 7.4.1). 회전 단위는 필요한 과제에서만(실험 15°, 코드 설정 rotate_step_deg: 40). 인터프리터(식 4)가 6-DoF 세트포인트에 σ, θ를 더하고 작업공간·스텝 한계로 투영, 위반 행동은 실행 전 차단.
- **Adaptive Step(§5.1, variable_step)**: 목표가 손목 카메라에 보이면 2 cm, 안 보이면 4 cm. 코드: MV_UP이거나 탁자 위 높이 > high_above_table(0.08 m)이거나 손목에 안 보이면 coarse. coarse 기본값 코드 0.05 m, 설정 0.04 m. "보이나"는 VLM이 매 응답에 적는 `WRIST: YES/NO`.
- **Action Chunking(action_chunk)**: `WRIST: NO`일 때만 `PLAN: M1, M2, …` 최대 step_num=3개 개루프 실행(action_chunk_step_num: 3). 보이면 호출당 행동 하나. 복구 개입이면 남은 청크 폐기.
- **단위마다 되먹임(부록 7.4.1)**: 그리퍼 높이, 한 스텝 이동량, "높으면 먼저 내려가라", "Last MV_DOWN lowered {moved} of {commanded} cm → already in contact"(명령 대 실제 이동량), 최근 행동 5개(코드 RECENT_MOVES_MAX=3), 진동 금지, 복구 메모. 하위 과제 완료는 VLM이 이미지로(DONE WHEN).
- **로봇이 기다린다(코드 확인, 논문 본문엔 명시 없음)**: `real.py`가 블로킹 `controller.decide(...)` 뒤 `controller.step(token)`. dagger 주석 "Key events … including while the VLM API call is in flight", launch.py "a step already takes tens of seconds". 에피소드 50 스텝 상한(§5.1).
- **빈 집기 복구(recovery, §5.4.3)**: 측정 폭 ≤ 5 mm → RELEASE, 가장 가까운 GRASP 하위 목표로 되돌림, 기록 삭제, 프롬프트 메모. 닫았는데 열린 폭이면 STOP 최대 3 스텝 대기. GRASP 단계 DONE이 폭 검증 실패면 거부. 들고 가다 잃으면 되돌림. 이미지·VLM 없는 폭 규칙. 빼면 96 → 72%(주 실패 = 감지 안 된 빈 집기).
- **추론 강도(§5.4.1, 프로젝트 페이지)**: 성공률 이득 거의 없고 스텝만 줄어듦. 페이지 "37 to 30 steps for GPT-5.6-sol, at 3.4× the wall-clock", 본문은 "e.g., 3.4× for GPT-5.6-sol"만(비교한 두 강도 미명시, low→high로 보임). Gemini-3.1 Pro·GPT-5.6-sol·Opus 5는 86~96%, GPT-5.6-luna·Gemini-3.6-flash는 72~78%. 유효 단위 출력률 >98%. 빈 집기 비율은 모델 순위가 내려갈수록 6% → 26%. Chess-cannon 오류는 계획이 아니라 세밀한 집기·놓기.
- **주요 결과(PDF Table 2)**: 교차 과제(10과제 × 10회) 평균 π0.5 39.0, GR00T 35.0, H-VLA 50.0, G-VLA 13.0, CaP-X 44.0, RATS 57.0, **ZS 89.0, FT 86.0**(ZS는 Banana→Bowl만 6/10, 나머지 7~10/10). 교차 환경 ZS 100, FT 88. sim-to-real FT 13/20, π0.5·GR00T 0/20. 교차 기체 ZS 93, FT 87.
- **플러그인 절제(Fig. 9, 전체 96%에서 하나씩 뺌)**: Multi-View 58 / Proprioception 68 / Subtask Planning 60 / Action Chunking 끄면 96%(호출 32), 선택적 96%(26, −19%), 항상 켜면 74%(20) / Adaptive Step fine 2 cm만 82%(38 스텝), coarse 4 cm만 70%(22), 적응 96%(30) / Action History 빼면 76%(스텝 39 대 30) / Failure Recovery 빼면 72 / Visual Prompt(손잡이) 40→85 / Situated Planning(숨은 물체) 35→85. 스텝·호출 수는 프로젝트 페이지 그림에서 읽은 값.
- **1 cm 실험 수치 불일치**: 본문 ZS 60→82, FT 40→65, π0.5 18%(세밀 데이터 추가 학습 62%) / 그림·페이지 60→**80**, π0.5 **15→60**. 인용 시 둘 다.
- 저자 한계(§6): 평행 그리퍼 단일·양팔만, 휴머노이드·손재주 손·촉각·힘은 향후 과제.
### 우리 해석
- M3: 촘촘함 = "접촉 근처 호출당 행동 하나 + 2 cm(1 cm) + 단위마다 되먹임, 멀면 4 cm + 최대 3개 청크". 항상 청크면 74% → D8 해석("촘촘함 = 접촉 근처 결정 빈도·공간 근거") 재지지. 전환 신호는 코드 규칙이 아니라 VLM이 쓰는 WRIST: YES/NO → 우리 M3("코드가 거리 범주로 크기")와 다른 설계임을 SH 조건에 명시.
- SH 기준선 원문판: 행동 단위 목록 그대로, 2/4 cm(설정 기준)·MV_UP 4 cm, 청크 3, 기록 3~5, 폭 5 mm 빈 집기 되돌림, 50 스텝 상한, **정지형(블로킹) 루프**. 벽시계 트랙이면 "기다림 없음" 변형을 따로 표시.
- M4: "Last MV_DOWN lowered X of Y cm"는 **명령 대 측정을 프롬프트로 되먹이는 선행** → 차별 문장에 "실행 뒤 예상 대 측정 자체는 Show-Harness(프롬프트 문맥)와 RoboDawn(reached/partial)에도 있다. 우리는 그것을 합의 원장의 전제 무효화와 확정 판정에 쓴다".
- M6·M9: Subtask Planning(시각 완료 기준, 전이는 VLM 판정) ↔ M6 `dp.next_skill`, Situated Planning(불확실한 분기는 증거가 보일 때까지 미룸) ↔ M6 결정 지점 "보류", 빈 집기 복구(폭 규칙 → 가장 가까운 GRASP로 되돌림) = M9 L1 `resume_ckpt_<k>` 구조의 원문 근거.
- 차별화 초안: "Show-Harness는 VLM 호출 동안 로봇이 멈추는 정지형 단위 루프(블로킹 decide → step, 스텝당 수십 초)이고, 추론 강도는 성공이 아니라 스텝 수만 줄였다(37→30, 벽시계 3.4×). 우리는 멈추지 않고 겹쳐 부른다."

## 3. GPT-as-Policy ("GPT 6 Astra as an Embodied Policy")
- 저자 Su, Zheng, Yan, Li Yi, Zhizheng Zhang, He Wang(사이트에 Galbot 로고, 소속 목록 비어 있음). 기술 보고서 + 코드, arXiv·심사 없음, 2026-09-13. README 인용 URL `eval-of-gpt-6-astra-as-policy`와 저장소 이름 `GPT-as-Policy` 불일치.
### 원문 사실
- **루프(§2.1, SKILL.md)**: **매 결정 지점** π0.5가 50×14 관절 후보(H50), 체크포인트 `RoboDojo-sim-arx_x5-joint-0/59999`, 설정 `pi05_base_aloha_full_sim_arx-x5_seed_0`(SOURCE.json). Astra(`gpt-6-astra`, **xhigh 고정**, Codex CLI 에이전트, 이미지·코드 실행·노트 도구)가 카메라 3대 RGB(긴 변 480 px), 14D 고유감각, 측정 양팔 EEF, 후보 FK 궤적, 과제 성공 조건, step_id/max, 대화 기록을 보고 선택: `student`(후보 1~15 스텝 실행) / `edit`(1~5 스텝 오프셋, 팔당 5 cm / 0.35 rad 이내) / `eef`(1~5 스텝 절대 목표). 실행 뒤 새 관측 → π0.5 재추론 → Astra 판정.
- **호출 시점: 실패 때만이 아니라 매 청크 경계.** gate_prompt.md 원문: 직전 청크 실행 결과와 다음 청크 의도를 따로 평가(execution not_started/progressing/failed/uncertain/recovered, intent aligned/misaligned/uncertain). "**An edit/eef takeover requires execution_status=failed or intent_status=misaligned. Uncertainty alone … is not a takeover reason.** After recovery, hand back." 되돌리기 금지, 물체 참값 사용 금지.
- **동기(정지)**: "Three blocking services", 초록 "Treating robotics like a pausable video game … real-world physics has no pause button … latency remains a hugely unresolved issue", Table 3 주석 "Physical duration … excludes model-response latency". **호출당 지연 값 미보고.**
- **결과(RoboDojo 10과제 × 5회, 짝 맞춤 seed, data.json)**: 표준 41 + 무작위 9(무작위는 숫자 배열·상자 담기·옷 개기 3과제에서 과제당 2 표준 + 3 무작위). 하이브리드 24/50 = 48%, Score 62.60 / Direct 13/50 = 26%, Score 37.81(점수 있는 48건). 같은 부분집합 π0.5 공개 수치 재가중 참고치 15.67% / 24.43("same-seed 재실행 아님"). 과제 선택: π0.5 공식 성공률 0~72%를 4구간으로 나눠 6/2/1/1개.
- 교정 비율: 실행 42,750 스텝 중 π0.5 36,576(85.6%), Astra 교정 6,174(14.4%). 결정(청크) 3,776회 ≈ 에피소드당 75.5회, 결정당 약 11.3 스텝(0.45 s 시뮬 시간). 토큰 624.8M(Direct 1.13B, −44.8%), 입력 약 97% 캐시. Direct 결정 7,729회(2.05배). (에피소드당·스텝당은 에이전트 계산.)
- 과제별(하이브리드 / Direct): 병→쓰레기통 5/5·1/5, 옷 개기 5/5·2/5, 탑 쌓기 3/5·0/5, 순서 정리 2/5·0/5, make_kong 2/5·0/5, 물체 분류 3/5·**5/5**, 말로 지정 분류 1/5·2/5, 가장 큰 수 2/5·2/5, 상자 담기 1/5·1/5, 책상 정리 0/5·0/5.
- RoboLab(Fig. 4): Direct 49/50, 하이브리드 46/50, π0.5 18/50, Cosmos3-Nano 18/50, DreamZero 17/50.
- 저자 한계(§5, §7): 청크 안 미끄러짐·충돌은 다음 관측까지 모름, 반복 집기 실패가 예산 소모, 행동 사전지식·인터페이스·청크 길이를 동시에 바꿔 요인 분리 못함, 지연 미해결.
- 재현성: SOURCE.json "native_integration_verified_company_backend_not_yet_run", README "The release has not rerun paid model or GPU experiments", 시뮬 자산·체크포인트 미포함.
### 우리 해석
- M8·M9: 매 청크 Astra 호출 + 개입은 실패·의도 불일치로 게이트, 기다리는 동안 시뮬 정지 → "게이트된 개입"은 사용자 원칙에 가깝지만 호출 빈도(에피소드당 약 75회, xhigh)와 정지는 "안 멈춘다"와 정반대. gate_prompt의 두 질문(직전 청크 결과 / 다음 청크 의도)과 "불확실만으로는 개입 금지"는 M9 L2 `dp.critic_accept`와 M7 FAIL 기준에 빌릴 만하다.
- **B6b 원문판**: 같은 π0.5 체크포인트, Astra xhigh, Codex 에이전트, H50, student 1~15 / edit·eef 1~5, 5 cm / 0.35 rad, gate 원문, 25 Hz, 청크 경계 관측, **동기 정지**, 짝 맞춤 사례 `public_results/evaluation_cases.json`. + **B6b-wall**(Astra 생각 중에도 시뮬 진행, 직전 확정 행동 유지 또는 π0.5 계속) = 저자가 못 푼 지연을 직접 재는 조건.
- EVAL의 "10과제가 standard인지 random인지" → 섞여 있음(표준 41 + 무작위 9, 무작위는 3과제만).
- "Astra 쓰는 기존 연구" 문장: "GPT-as-Policy는 매 청크 경계에서 Astra(xhigh)를 동기로 불러 π0.5 후보를 실패·의도 불일치일 때만 교정했다(교정 14.4%, 48% 대 Direct 26%). 시뮬을 멈춘 채였고 모델 지연은 물리 시간에서 제외했다(Table 3). 우리는 실패 신호가 날 때만 Astra를 비동기로 부르고 그동안 아래 층이 로봇을 계속 움직인다."

## 정본 반영 제안 (메인 세션 채택 → 정본 §20)
1. E-first §2A·M4 §5의 C2'를 원문대로: 요청 시각 기준 가장 새 응답 + Prob Fusion(λ=3, τ=5 s, 5 s 타임아웃) + 빠른 층 S1 = 규칙 점수. 현재 "감쇠 가중 최빈, 반감기 0.33 s"는 C2''로 개명. C2-match 선택 추가.
2. M4 차별 문장에 "실행 뒤 명령 대 측정 되먹임은 Show-Harness·RoboDawn에도 있다" 추가.
3. EVAL B6b 원문 설정 + B6b-wall, standard/random 질문 해결 표시.
4. M3 SH 조건: 2/4 cm, 청크 3, WRIST 신호, 정지형 루프. 1 cm 수치 본문 82 / 그림 80 병기.

## 확인 못 한 것
- Slow Brain Fig. 6 점별 값·에피소드 수·Fusion 곡선 요청 모드, 공개 코드 없음.
- Show-Harness 추론 강도 비교의 두 강도.
- GPT-as-Policy 호출당 지연, Astra 추론 강도 외 설정(config.toml은 `.invalid` 자리표시자).
