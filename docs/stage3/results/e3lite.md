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
