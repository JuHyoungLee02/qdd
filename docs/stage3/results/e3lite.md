# E3-lite: 상태 표현 진단 (정본 §50, E §5 앞당김)

## 사전 등록 (모델 호출 전 고정, 2026-09-24T13:59:11Z `date -u`)

작업 지시문 원문(데이터를 본 뒤 바꾸지 않는다):

- Conditions: state S0 (current ser-A-min-1) / S1 (S0 + one "geometry" block: robot-base frame explained in one line (+x forward away from robot, +y robot-left, +z up), then for the gripper and each present object: position relative to the gripper Δx, Δy, Δz in cm rounded to 1 cm, plus distance) / S2 (S1 + the same offsets also expressed as the magnitude bin names used by mag_coarse). × input {text, text+head image} × model {Qwen3-VL-4B, Qwen3-VL-8B} × option order {fixed, rotated (C3'': cyclic shift by snapshot index, NONE_ESCALATE stays last)}. Same six questions and scoring as jevl_model_select.md.
- Upper bound: a code rule reading only S1 numbers (same bins/frame as the planner) — report its accuracy per question; if it is < 0.95 on dir_xy/dir_z/mag, the question definitions (not the model) are ill-posed: report and stop model conclusions for those questions.
- Primary: accuracy A (pooled, episode-cluster bootstrap 95% CI, paired by snapshot) for each condition; secondary: per-question accuracy, ECE, AUROC, first-position choice rate vs oracle first-position rate, NONE_ESCALATE rate, p95 latency (N=4) for the S1/S2 prompts (longer text).
- Decision rules (fixed now): (1) representation: pick the S with highest A for Qwen-4B text+image if its paired gain over S0 has CI lower bound > 0; ties within CI → the shorter state. (2) model: 8B replaces 4B only if gain CI lower bound > 0 AND N=4 p95 ≤ 0.33 s. (3) image: keep head image only if text+image beats text-only with CI lower bound > 0; otherwise report "image adds nothing at this state" (canon §44 input is revisited). (4) order: if rotated order changes accuracy by more than 2 pt (CI excluding 0) → C3'' rotation becomes mandatory. (5) If the best condition is still below the majority baseline 0.669, report "Jev-L insufficient on this task" as a direction-level finding.

### 운영 세부 (같은 시각 고정 — 원문을 코드에 옮기는 방법)

**데이터·질문·채점**: jevl_model_select.md와 같다. DEV 0–29 × P0/P1/P2 스냅샷(`/data/harvest/data/jsel_dev/`, 새로 생성하지 않음) 중 `oracle` ≠ null 전부(2,387개 × 6질문 = 14,322 항목). 질문·보기·보이는 이름·NONE_ESCALATE 마지막·option_key 채점·argmax NE = 오답·동률은 보기 순서 앞쪽 — `harvest/deccall_snap.py` 그대로. 모델 = `Qwen/Qwen3-VL-4B-Instruct@ebb281ec…`, `Qwen/Qwen3-VL-8B-Instruct@0c351dd0…`(`/data/harvest/models/`), vLLM 0.30.0(`/data/harvest/venv_vllm`), GPU 3 한 장, `VLLM_BATCH_INVARIANT=1`, 서버 옵션 = `jsel/serve.sh`와 같음, 시스템 문장 = `harvest/clients/jevl.py` `SYSTEM`. 이미지 = 스냅샷 머리캠 JPEG q90 그대로.

**상태 S0/S1/S2** (오프라인, 스냅샷 줄의 `state.obs.raw`에서 만든다. Isaac 불필요):
- S0 = 스냅샷 줄의 `text_state` 그대로(`ser-A-min-1`).
- S1 = S0 끝에 한 블록을 붙인다(S0 부분은 바이트 단위로 같음):
  ```
  geometry (robot base frame: +x forward away from the robot, +y robot left, +z up; cm; offsets = object centre minus gripper):
    gripper: x=33 y=-25 z=24 (z = height above the table top)
    o3 mug red: dx=+9 dy=-13 dz=-20 dist=25
    o5 tray blue: …
  ```
  그리퍼 = `obs.raw.grip.pos`(손가락 중점, 테이블 틀 = 로봇 기저 x·y, z는 테이블 윗면 0), 물체 = `obs.raw.objs[k].pos`(중심), `state.present` 물체만 번호순. 모든 값 cm 반올림(파이썬 `round`, 짝수 반올림), dist = 반올림 전 3D 거리의 반올림. 좌표계 확인: `harvest/sim/scene.py` "world x = robot forward, y = robot left, z = up; robot root fixed at the world origin", 테이블 틀 = world x, y, z − 0.85 → 오라클 `cmd_disp_m`과 같은 틀.
- S2 = S1 + 물체 줄마다 `bins: dx=+xlarge dy=-large dz=-tiny dist=xlarge`. 이름 = 오라클 `mag_coarse`와 같은 함수(`planner.MAG_BINS` 로그 최근접, 0.25 cm 미만이면 `tiny`), 부호는 성분 부호(0이면 `+`). 구간은 반올림 전 값으로 계산.

**보기 순서**: fixed = 지금 순서. rotated(C3'') = 스냅샷 전역 번호 i(`jevl_acc.snapshots()` 순서, P0→P1→P2, 시드 오름차순, k 오름차순, 0부터)로 NONE_ESCALATE를 뺀 보기를 왼쪽으로 i mod n칸 순환, NE는 마지막. 6질문 모두 같은 i.

**조건**: 3 상태 × 2 입력 × 2 모델 × 2 순서 = 24 조건, 각 2,387 스냅샷 1회(BI 켬, 결정적). 동시 4 호출에서 동시성 8로 올려도 된다(BI 켬이라 답은 같다 — 이전 결정성 시험 flip 0). 호출 실패는 재시도 3회, 그래도 실패면 오답(따로 보고).

**통계**: A = 14,322 항목 정답률(6질문 합침). 짝 차이 = 같은 (스냅샷, 질문) 항목 정답의 차, 판(kind, seed) 90개 단위 부트스트랩 10,000회(`cluster_bootstrap_ci`, seed 0), 95 % 백분위. ECE 15구간, AUROC(p_chosen→정답). 첫 자리 선택률 = argmax가 보여 준 첫 보기인 비율, 오라클 첫 자리율 = 오라클 key가 보여 준 첫 보기인 비율(질문 합침 + 질문별). 최빈 기준선 0.669(jevl_model_select.md)는 같은 항목에서 다시 계산해 적는다.

**상한 코드 규칙 UB** (`harvest/e3lite.py` `code_rule`; S1 텍스트만 파싱 — geometry 줄의 반올림된 cm 값 + S0의 stage·gripper·facts; 플래너 `_goal` 규칙을 그대로 옮기고 데이터로 문턱을 맞추지 않음):
- 단계 추정: S1 단계 + gripper=open → o3 위로 xy 거리 > 1.5 cm 또는 그리퍼가 머그 중심보다 14.75 + 1.5 cm 넘게 높으면 approach(목표 = o3 xy, 머그 중심 위 14.75 cm, 0.20 m/s), 아니면 descend(목표 = 머그 중심 위 2.95 cm, 0.06 m/s); descend 목표에 0.6 cm 안이면 close(움직임 없음). gripper=closed_holding: S1 단계면 lift(목표 z = 테이블 위 20 cm, 0.08 m/s; 이미 18.5 cm 이상이면 carry로), S2 단계면 o5 xy 거리 > 1.5 cm → carry(목표 = o5 xy, z 20 cm, 0.20 m/s), 아니면 place_descend(머그 바닥 − 트레이 윗면 − 0.3 cm만큼 아래, 0.06 m/s). S2 단계 + gripper=open → retreat(10 cm 위, 0.20 m/s; 이미 머그 중심보다 12 cm 넘게 높으면 done = 움직임 없음). closed_empty → 움직임 없음.
- 한 스텝 변위 = 목표 방향 × min(목표까지 거리, 속도 × 0.33 s) → `planner.oracle_answer`와 같은 함수로 dir_xy·dir_z·mag_coarse.
- target = holding이거나 S2 단계면 o5, 아니면 o3. phase = 목표까지 거리 ≤ 속도 × 0.33 s면 next, 아니면 continue(close는 continue). progress = 늘 valid_progress.
- 진단(판정 밖): 같은 규칙에 반올림 전 값을 넣은 UB-raw도 보고한다(반올림 탓과 정의 탓을 가르기 위함).
- **UB 판정**: dir_xy·dir_z·mag_coarse 각각 UB < 0.95이면 그 질문은 "정의가 S1로 풀 수 없게 되어 있음(ill-posed)"으로 보고하고, 그 질문에 대한 모델 결론(질문별 비교)은 내지 않는다.

**판정 적용 방법**:
- 규칙 (1): Qwen-4B, text+image, fixed 순서에서 S0/S1/S2의 A 비교. 최고 A인 S*가 S0이 아니고 S* − S0 하한 > 0이면 후보. S2가 최고인데 S2 − S1 구간이 0을 포함하면 짧은 S1을 고른다(S1이 S0보다 하한 > 0일 때). 어느 것도 S0보다 하한 > 0이 아니면 S0 유지.
- 규칙 (2): 고른 S, text+image, fixed에서 8B − 4B 하한 > 0 그리고 8B의 그 S 프롬프트 text+image N=4 p95 ≤ 0.33 s일 때만 8B.
- 규칙 (3): 고른 S·모델·fixed에서 text+image − text 하한 > 0이면 이미지 유지, 아니면 "이 상태에서 이미지는 아무것도 더하지 않는다".
- 규칙 (4): 고른 S·모델·입력에서 rotated − fixed의 |차| > 0.02이고 구간이 0을 제외하면 C3'' 필수. 다른 조건들의 순서 효과도 표로 보고(판정은 고른 조건 하나로).
- 규칙 (5): 24 조건 중 A 점추정 최고 조건이 0.669보다 낮으면 "Jev-L insufficient on this task"(방향 수준 발견). 그 조건의 구간이 0.669를 포함하면 함께 적는다.
- 민감도(판정 밖): UB로 ill-posed가 된 질문을 뺀 A로 규칙 (1)–(5)를 다시 적용해 결과가 같은지 적는다. 판정은 원문대로 6질문 합친 A로 한다.

**지연**: `tools/jevl_e3lite.py lat` — 실제 DEV 스냅샷 DecCall(S0/S1/S2 각각, 고정 셔플 순서의 스냅샷 200개 + 워밍업 워커당 10개 버림), N=4, BI 켬, text와 text+image, 4B·8B, 검열 2 s(실패 = inf). 기록: p50/p95, 입력 토큰 중앙값, 측정 때 파드 load. 규칙 (2)의 문턱은 text+image N=4 p95 ≤ 0.33 s.

**시드**: DEV 0–29 스냅샷만 재사용. TEST 1000–1149·TEST-P5 1300–1329·POOL 2000–2119는 읽지도 만들지도 않는다.

---

## 결과 (2026-09-24 15:05Z 작성)

### 요약
- **UB 판정(사전 규칙)**: 코드 규칙 상한이 dir_xy 0.920 · dir_z 0.803 · mag_coarse 0.730 → **세 질문 모두 < 0.95 → ill-posed.** 이 세 질문에 대한 모델 결론은 내지 않는다(아래 표의 해당 열은 참고용).
- **판정 (1)–(5)** (사전 등록, 6질문 합친 A):
  1. 표현 = **S1** (4B text+image fixed: S1 − S0 = +0.049 [+0.043, +0.056], S2 − S0 = +0.014 [+0.006, +0.021]; S1이 최고).
  2. 모델 = **4B 유지** (S1 text+image fixed에서 8B − 4B = −0.058 [−0.064, −0.053]. 8B p95 0.274 s는 문턱 안이지만 정확도 조건 불충족).
  3. 이미지 = **"이 상태에서 이미지는 아무것도 더하지 않는다"** (4B S1 fixed: text+image − text = +0.0001 [−0.003, +0.004]) → 정본 §44 입력(M1 텍스트 + 머리캠 1장)을 다시 검토할 것.
  4. 순서 = **C3'' 회전 필수 아님** (판정 조건 4B S1 text: rotated − fixed = −0.008 [−0.011, −0.004], |차| < 2 pt). 단 다른 조건들에서는 순서 효과가 2 pt를 넘는 경우가 많다(4B S0 +2.6·+3.8 pt, 8B 전 조건 +2.4 ~ +6.4 pt, 아래).
  5. **"Jev-L insufficient on this task"**: 24 조건 중 최고 A = 4B S1 text+image fixed 0.532 [0.527, 0.537] < 최빈 기준선 0.669(구간도 기준선 아래).
- **민감도(판정 밖, ill-posed 3질문을 뺀 target·phase·progress)**: (1) S1, (2) 4B, (3) 이미지 무익, (5) insufficient로 **같다**(최고 8B S0 text rot 0.714 [0.709, 0.720] < 이 세 질문의 최빈 기준선 0.740). (4)만 부호가 다르다: 4B S1 text rotated − fixed = +0.017 [+0.013, +0.021](회전이 이득) — 여전히 2 pt 이하라 필수 아님.

### UB 진단: 방향·크기 정답은 관측 상태로 결정되지 않는다
- 오라클 `dir_xy`·`dir_z`·`mag_coarse`는 **계획기가 명령한 TCP 위치(`cmd_pos`)가 다음 0.33 s 동안 움직이는 양**이다(`planner.decision_points`). 명령은 실제 그리퍼보다 앞서거나 뒤처지고(손가락 중점 − 명령: 성분별 |차| 90백분위 0.8 / 1.7 / 1.4 cm), close·open 단계는 **타이머**(0.6 s·0.5 s)로 넘어가며, 한 스텝 안에서 단계가 바뀌면 두 단계의 움직임이 섞인다.
- 그래서 S1 숫자를 계획기 `_goal` 규칙 그대로 읽는 코드도 0.95에 못 미친다. 반올림 탓이 아니다(반올림 전 값 UB-raw 0.910 / 0.809 / 0.751, 거의 같음). 오차가 큰 곳: carry dir_z(정답 none_z인데 실제 그리퍼 높이 ≠ 명령 높이 20 cm → 규칙은 up, 156건), close의 dir_z·mag, open·retreat의 mag.
- 진단(사후, 판정 밖): 상태에 **없는** 명령 위치 `cmd_pos`를 넣어 줘도 dir_xy 0.952 · dir_z 0.932 · mag 0.825 — 타이머·단계 전환 때문에 mag는 여전히 낮다.
- **결론**: 이 세 질문은 "관측 상태를 보고 다음 움직임을 고르는" 질문이 아니라 "계획기 내부 상태(명령 지연·타이머)를 맞히는" 질문이 되어 있다. 모델 평가에 쓰려면 정답을 상태에서 결정되는 양(예: 단계 목표까지 남은 변위의 방향·구간)으로 다시 정의해야 한다. phase(UB 0.770)도 같은 이유(타이머)로 약하다 — 사전 규칙은 dir·mag에만 걸었으므로 phase는 민감도 분석에 남겼다.

### 1. 조건별 정확도 (주 지표 A, 14,322 항목, 판 90개 부트스트랩 10,000, 호출 오류 0)

| 조건 | A 6질문 [95 % CI] | A target·phase·progress [CI] | ECE | AUROC | NE | 첫 자리 선택 / 오라클 첫 자리 | 입력 토큰 중앙 |
|---|---|---|---|---|---|---|---|
| 4B S0 text+image fixed | 0.4826 [0.4767, 0.4884] | 0.6527 [0.6455, 0.6598] | 0.402 | 0.599 | 0.0009 | 0.680 / 0.413 | 662 |
| **4B S1 text+image fixed** | **0.5320 [0.5268, 0.5373]** | 0.6841 [0.6774, 0.6908] | 0.349 | 0.669 | 0 | 0.502 / 0.413 | 791 |
| 4B S2 text+image fixed | 0.4964 [0.4904, 0.5025] | 0.6697 [0.6613, 0.6778] | 0.365 | 0.655 | 0 | 0.488 / 0.413 | 845 |
| 4B S0 text fixed | 0.4326 [0.4284, 0.4367] | 0.6816 [0.6755, 0.6879] | 0.479 | 0.619 | 0 | 0.747 / 0.413 | 408 |
| 4B S1 text fixed | 0.5318 [0.5273, 0.5366] | 0.6869 [0.6808, 0.6932] | 0.386 | 0.729 | 0 | 0.524 / 0.413 | 537 |
| 4B S2 text fixed | 0.5172 [0.5114, 0.5231] | 0.6829 [0.6763, 0.6895] | 0.368 | 0.703 | 0 | 0.506 / 0.413 | 591 |
| 4B S0 text+image rot | 0.5087 [0.5035, 0.5139] | 0.6813 [0.6736, 0.6889] | 0.386 | 0.661 | 0.0019 | 0.303 / 0.265 | 662 |
| 4B S1 text+image rot | 0.5223 [0.5176, 0.5271] | 0.7037 [0.6971, 0.7104] | 0.370 | 0.707 | 0 | 0.301 / 0.265 | 791 |
| 4B S2 text+image rot | 0.4966 [0.4910, 0.5025] | 0.6975 [0.6901, 0.7048] | 0.379 | 0.695 | 0 | 0.296 / 0.265 | 845 |
| 4B S0 text rot | 0.4710 [0.4669, 0.4749] | 0.6989 [0.6923, 0.7055] | 0.461 | 0.638 | 0 | 0.330 / 0.265 | 408 |
| 4B S1 text rot | 0.5242 [0.5197, 0.5289] | 0.7034 [0.6978, 0.7091] | 0.391 | 0.717 | 0 | 0.273 / 0.265 | 537 |
| 4B S2 text rot | 0.5033 [0.4982, 0.5085] | 0.7062 [0.7001, 0.7124] | 0.397 | 0.696 | 0 | 0.283 / 0.265 | 591 |
| 8B S0 text+image fixed | 0.4294 [0.4241, 0.4346] | 0.5587 [0.5509, 0.5663] | 0.443 | 0.665 | 0.0201 | 0.491 / 0.413 | 662 |
| 8B S1 text+image fixed | 0.4737 [0.4683, 0.4793] | 0.6406 [0.6325, 0.6485] | 0.382 | 0.659 | 0.0145 | 0.483 / 0.413 | 791 |
| 8B S2 text+image fixed | 0.4779 [0.4725, 0.4835] | 0.6387 [0.6298, 0.6474] | 0.387 | 0.652 | 0.0144 | 0.488 / 0.413 | 845 |
| 8B S0 text fixed | 0.4887 [0.4847, 0.4927] | 0.6512 [0.6452, 0.6571] | 0.418 | 0.593 | 0.0374 | 0.591 / 0.413 | 408 |
| 8B S1 text fixed | 0.4886 [0.4845, 0.4928] | 0.6742 [0.6684, 0.6802] | 0.404 | 0.666 | 0.0142 | 0.490 / 0.413 | 537 |
| 8B S2 text fixed | 0.4929 [0.4882, 0.4977] | 0.6771 [0.6710, 0.6832] | 0.389 | 0.691 | 0.0154 | 0.503 / 0.413 | 591 |
| 8B S0 text+image rot | 0.4936 [0.4890, 0.4980] | 0.6878 [0.6807, 0.6947] | 0.397 | 0.724 | 0.0254 | 0.235 / 0.265 | 662 |
| 8B S1 text+image rot | 0.5043 [0.4996, 0.5091] | 0.6875 [0.6820, 0.6931] | 0.376 | 0.726 | 0.0177 | 0.240 / 0.265 | 791 |
| 8B S2 text+image rot | 0.5131 [0.5087, 0.5176] | 0.6857 [0.6795, 0.6920] | 0.375 | 0.712 | 0.0155 | 0.245 / 0.265 | 845 |
| 8B S0 text rot | 0.5247 [0.5206, 0.5287] | 0.7143 [0.7085, 0.7201] | 0.394 | 0.689 | 0.0358 | 0.267 / 0.265 | 408 |
| 8B S1 text rot | 0.5124 [0.5085, 0.5162] | 0.6998 [0.6950, 0.7047] | 0.381 | 0.726 | 0.0200 | 0.265 / 0.265 | 537 |
| 8B S2 text rot | 0.5214 [0.5175, 0.5252] | 0.6991 [0.6942, 0.7041] | 0.381 | 0.702 | 0.0179 | 0.278 / 0.265 | 591 |
| 최빈 기준선 | 0.6691 | 0.7403 | | | | | |

질문별 정확도 (dir·mag 열은 ill-posed라 참고만):

| 조건 | dir_xy | dir_z | mag_coarse | target | phase | progress |
|---|---|---|---|---|---|---|
| 4B S0 img fixed | 0.088 | 0.569 | 0.280 | 0.439 | 0.608 | 0.911 |
| 4B S1 img fixed | 0.093 | 0.524 | 0.523 | 0.437 | 0.697 | 0.919 |
| 4B S2 img fixed | 0.098 | 0.524 | 0.348 | 0.436 | 0.661 | 0.913 |
| 4B S0 txt fixed | 0.074 | 0.317 | 0.160 | 0.436 | 0.698 | 0.911 |
| 4B S1 txt fixed | 0.053 | 0.524 | 0.553 | 0.460 | 0.686 | 0.915 |
| 4B S2 txt fixed | 0.063 | 0.524 | 0.468 | 0.457 | 0.682 | 0.910 |
| 4B S0 img rot | 0.091 | 0.485 | 0.432 | 0.469 | 0.684 | 0.891 |
| 4B S1 img rot | 0.072 | 0.527 | 0.424 | 0.479 | 0.728 | 0.904 |
| 4B S2 img rot | 0.083 | 0.524 | 0.280 | 0.474 | 0.722 | 0.897 |
| 4B S0 txt rot | 0.076 | 0.272 | 0.380 | 0.466 | 0.725 | 0.906 |
| 4B S1 txt rot | 0.054 | 0.502 | 0.479 | 0.473 | 0.728 | 0.909 |
| 4B S2 txt rot | 0.062 | 0.506 | 0.334 | 0.485 | 0.725 | 0.908 |
| 8B S0 img fixed | 0.117 | 0.724 | 0.059 | 0.433 | 0.416 | 0.827 |
| 8B S1 img fixed | 0.160 | 0.695 | 0.065 | 0.435 | 0.596 | 0.891 |
| 8B S2 img fixed | 0.177 | 0.697 | 0.077 | 0.435 | 0.623 | 0.858 |
| 8B S0 txt fixed | 0.181 | 0.745 | 0.053 | 0.440 | 0.655 | 0.858 |
| 8B S1 txt fixed | 0.168 | 0.676 | 0.065 | 0.442 | 0.669 | 0.912 |
| 8B S2 txt fixed | 0.163 | 0.690 | 0.073 | 0.442 | 0.682 | 0.908 |
| 8B S0 img rot | 0.119 | 0.705 | 0.073 | 0.539 | 0.633 | 0.891 |
| 8B S1 img rot | 0.147 | 0.709 | 0.106 | 0.469 | 0.685 | 0.909 |
| 8B S2 img rot | 0.146 | 0.715 | 0.160 | 0.465 | 0.690 | 0.902 |
| 8B S0 txt rot | 0.182 | 0.744 | 0.079 | 0.530 | 0.712 | 0.901 |
| 8B S1 txt rot | 0.160 | 0.700 | 0.114 | 0.469 | 0.711 | 0.920 |
| 8B S2 txt rot | 0.145 | 0.722 | 0.163 | 0.468 | 0.712 | 0.918 |
| **UB 코드 규칙 (S1 숫자)** | 0.920 | 0.803 | 0.730 | 0.965 | 0.770 | 0.925 |
| UB-raw (반올림 전, 진단) | 0.910 | 0.809 | 0.751 | 0.965 | 0.791 | 0.925 |
| 최빈 기준선 | 0.717 | 0.524 | 0.553 | 0.565 | 0.731 | 0.925 |

### 2. 판정에 쓴 짝 차이 (판 부트스트랩 95 % CI)

| 비교 | 6질문 (사전 등록 판정) | target·phase·progress (민감도) |
|---|---|---|
| (1) 4B img fixed S1 − S0 | +0.0494 [+0.0429, +0.0561] | +0.0314 [+0.0258, +0.0371] |
| (1) 4B img fixed S2 − S0 | +0.0138 [+0.0062, +0.0212] | +0.0170 [+0.0112, +0.0227] |
| (2) S1 img fixed 8B − 4B | −0.0583 [−0.0642, −0.0525] | −0.0436 [−0.0510, −0.0364] |
| (3) 4B S1 fixed image − text | +0.0001 [−0.0034, +0.0037] | −0.0028 [−0.0078, +0.0021] |
| (4) 4B S1 text rotated − fixed | −0.0076 [−0.0109, −0.0042] | +0.0165 [+0.0125, +0.0205] |
| (5) 최고 조건 대 최빈 | 4B S1 img fixed 0.532 < 0.669 | 8B S0 txt rot 0.714 < 0.740 |
| **판정** | S1 / 4B / 이미지 무익 / 회전 필수 아님 / insufficient | 같음((4)만 부호 반대, 둘 다 필수 아님) |

참고 짝 차이(6질문): 4B text에서 S1 − S0 +0.099 [+0.094, +0.105]. 4B S0에서 image − text +0.050 [+0.046, +0.055](S0에서만 이미지 이득, S1에서 0, S2에서 −0.021). 8B는 모든 S에서 image − text 음수(−0.015 ~ −0.059). 8B − 4B는 S0 text에서만 +0.056, 나머지 음수.

순서 효과(rotated − fixed, 6질문): 4B S0 img +0.026, S1 img −0.010, S2 img +0.000(구간이 0 포함), S0 txt +0.038, S1 txt −0.008, S2 txt −0.014; 8B S0 img +0.064, S1 img +0.031, S2 img +0.035, S0 txt +0.036, S1 txt +0.024, S2 txt +0.028. 판정 조건(4B S1 text)에서는 2 pt 미만이지만, fixed 순서의 첫 자리 치우침(첫 자리 선택 0.48–0.75 대 오라클 0.41)이 회전하면 사라지고(0.24–0.33 대 0.27), 8B·S0 조건은 2 pt 넘게 오른다.

### 3. 해석 (판정 밖)
- S1의 이득은 **기하를 읽어서가 아니라 답이 한 보기로 쏠린 결과**다. 4B S1 text+image fixed의 선택 분포: dir_z 2,387/2,387 `down`(최빈 0.524와 정확히 같음), mag 2,205 `medium`(최빈), dir_xy `plus_x_plus_y` 1,625 · `plus_x` 597(오라클 최빈 none_xy 1,711), target 2,383 `o3`(오라클 o5가 1,349 — S0 텍스트에 이미 `gripper=closed_holding(o3)`·stage S2가 있는데도). 즉 모델은 S1이 준 상대 좌표로 목표·방향을 고르지 않는다.
- target은 모든 조건에서 0.43–0.54(최빈 0.565 아래, UB 0.965). 상태에서 거의 자명한 질문(holding이거나 S2 → o5)인데 모델이 못 쓴다 — 질문 문구("current motion is about") 해석 문제일 수 있다(검증 안 함).
- phase·progress는 최빈 근처(대부분 continue·advancing).

### 4. 지연 (N=4, BI 켬, 실제 DEV 스냅샷 DecCall 200호출/조건, 워커당 10호출 워밍업 버림, 검열 2 s)

| 모델 | 상태 | 모드 | p50 | p95 | 실패 | 입력 토큰 중앙 | 측정 중 파드 load1 중앙 |
|---|---|---|---|---|---|---|---|
| 4B | S0 | text+image | 0.274 | 0.301 | 0/200 | 666 | 84 |
| 4B | S1 | text+image | 0.209 | 0.264 | 0/200 | 793 | 73 |
| 4B | S2 | text+image | 0.201 | 0.220 | 0/200 | 846 | 59 |
| 4B | S0 | text | 0.130 | 0.152 | 0/200 | 412 | 86 |
| 4B | S1 | text | 0.133 | 0.146 | 0/200 | 539 | 80 |
| 4B | S2 | text | 0.135 | 0.171 | 0/200 | 592 | 64 |
| 8B | S0 | text+image | 0.320 | 0.341 | 0/200 | 666 | 39 |
| 8B | S1 | text+image | 0.249 | **0.274** | 0/200 | 793 | 42 |
| 8B | S2 | text+image | 0.246 | 0.371 | 0/200 | 846 | 49 |
| 8B | S0 | text | 0.161 | 0.198 | 0/200 | 412 | 36 |
| 8B | S1 | text | 0.189 | 0.208 | 0/200 | 539 | 34 |
| 8B | S2 | text | 0.188 | 0.216 | 0/200 | 592 | 40 |

- 측정 내내 다른 작업(POOL 생성·라벨 selfcheck)으로 파드 load가 34–86이었다. vLLM API 서버는 CPU(이미지 디코딩·토큰화)에 민감해 **부하가 측정 순서와 섞여 있다**(4B S0 image가 S1·S2보다 느린 것은 토큰 수가 아니라 부하가 가장 높았던 시점 탓으로 보인다). S1·S2가 늘리는 입력은 +127·+180 토큰이고 text 모드 p50 차이는 0.003–0.028 s로 작다.
- 규칙 (2)에 쓴 값: 8B S1 text+image p95 0.274 s ≤ 0.33 s(지연은 적격, 정확도에서 짐). 최종 조건(4B S1 text) p95 0.146 s.
- sanity(이어 쓰기 접두 재토큰화): 4B·8B 모두 4/4 OK, MISMATCH 0.

## 사후 변경·운영 기록 (숨기지 않고 적음)
1. 4B 첫 기동 때 서버·실행기가 실수로 두 벌 떴다(14:03Z 전후). 발견 즉시 두 벌 모두 PID로 내리고 반쯤 쓰인 지연·sanity 결과를 지운 뒤 한 벌만 다시 띄웠다(14:06Z). 그 시점 정확도 파일은 아직 쓰이지 않았다. 판정에 쓴 모든 수치는 재기동 판이다. 8B는 한 벌만 띄우고 `ps`로 확인했다.
2. 동시 호출 8(사전 등록 허용 범위, BI 켬).
3. 사후 진단 2건(판정 밖): UB의 `cmd_pos` 대체 계산, 선택 분포 표.

## 원자료·파일
- 파드 `/data/harvest/e3lite/`: `acc_<model>_<S>_<img|txt>_<fixed|rot>.jsonl`(24개, 항목별 정답·보기 확률·첫 자리), `lat_<model>.jsonl`, `ub.json`·`ub_rows.jsonl`, `sanity_*.log`, `run.sh`, 서버·실행 로그. 코드 사본 `/data/harvest/code_e3lite/`(공용 `/data/harvest/code`는 건드리지 않음). DEV 스냅샷은 `jsel_dev` 재사용(새로 만들지 않음).
- 로컬(D:\qdd, 커밋 안 함): 새 `harvest/e3lite.py`, `tools/jevl_e3lite.py`, `tools/jevl_e3lite_report.py`, `tests/test_e3lite.py`(12); 수정 `harvest/deccall_snap.py`(`text_state=`·`shift=` 인자, `rotate`; 기본 동작 불변), `harvest/analysis/stats.py`(`cluster_mean_ci`), `tests/test_stats.py`(+1).
- `/data` 밖: 파드에 새 파일 없음. vLLM 서버는 모두 내려 GPU 3을 비웠다(1 MiB).
