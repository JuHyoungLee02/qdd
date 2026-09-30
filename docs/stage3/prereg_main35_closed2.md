# E-M35CL2 — 폐루프 정체 감지 + 루프 깨기(loop break) 켬/끔 짝 비교 (무료, 사전 등록, 아직 실행 안 함)

- 작성: LOOPFIX 에이전트, 2026-10-01 KST (UTC 시각은 커밋 시각). **실행 전·결과 전에** 커밋한다.
- 근거: `docs/stage3/results/m35cl_stagecap_diag.md`(E-M35CL 진단) 고칠 것 1번, 사용자 승인(10-01) — 코드만, 재학습 없음.
- **시작 조건(필수)**: 렌더 카드(7a2a GPU0·1·3)는 지금 L9 양산 몫이다. 카드가 비고 **사용자가 시작을 확인한 뒤에만** 띄운다. 이 등록은 실행 허가가 아니다.
- 실행 중인 E-M35CL(`code_m35cl_d2b737a`, prereg_main35_closed.md)은 건드리지 않는다(등록상 도중 프로토콜 변경 금지). 이 실험은 새 코드 사본(`git -c core.autocrlf=false archive`, `/data/harvest/code_m35cl2_<hash>`)으로만 돈다.
- 유료 0원.

## 0. 자체 검사
- **결정**: 폐루프 실행기에 루프 깨기를 기본으로 켤지(이후 모든 상위 폐루프·결합 실험의 기본값). 상한(30호출)을 올릴지는 이 실험이 아니다(§6).
- **가를 수 있나**: 같은 편·같은 시드 짝 비교(켬 대 끔)라 편 사이 난이도 차가 빠진다. none 조건 세트당 약 216편(OOD-O58 58 + L8S 보류 약 158). 진단상 상한 실패 109편 중 정체 63편 — 힌트가 먹히면 수 %p, 안 먹혀도 호출 수는 크게 준다. 작은 성공률 차(<5 %p)는 '구분 안 됨'으로 적는다.
- **멈춤 조건(P18)**: (1) 켬 팔 첫 20편에서 오류(error.json) > 10 %, (2) 켬 팔 첫 40편에서 'stall'로 끝난 편 중 마지막 3호출 동안 TCP-목표 거리가 호출당 5 mm 넘게 줄던 편(= 수렴 중이던 편을 잘못 끊음)이 10 % 초과, (3) 끔 팔이 E-M35CL 같은 편 결과와 성공률 10 %p 넘게 다름(재현 실패). 하나라도 걸리면 멈추고 원인부터 고친 뒤 등록 '변경'으로 재개.

## 1. 세트·조건 (E-M35CL과 같음)
- 세트: E-M35CL의 `groups.json` 그대로(OOD-O58 58편 + L8S 보류, 제외 규칙 동일). digest를 결과에 적고, E-M35CL digest와 같아야 한다.
- 조건: `none`(주), `light:dim_warm`, `head:10:15`. none을 두 모델·두 팔 모두 먼저 끝내고 변형 조건을 돈다.
- 호출 상한 **30 그대로**(`--stop-calls 30`), 동작 상한 120 s 그대로. 실행기 설정은 E-M35CL과 같다(LimitEpisode, d-min, mem_points + fix_loop, 기존 LoopGuard 유지).

## 2. 모델·팔
- 모델: **f35_d**(`/data/harvest/out/final35/merged_d`)와 **main35 최적 체크포인트**(prereg_main35 §3 규칙: L8S 검증 >20 mm 실패율 최저 → 공개 점 적중 → 뒤 체크포인트). 시작 때 최적이 정해져 있지 않으면 시작 전에 '변경'으로 어느 체크포인트인지 적는다.
- 팔(같은 편·같은 시드, 같은 서버에서 번갈아):
  - **off** = `run_closed_l8s` 기본(루프 깨기 없음, E-M35CL과 같은 실행).
  - **on** = `run_closed_l8s --loop-break --stall-n 3`.
- E-M35CL의 같은 체크포인트 결과는 참고 열로만 쓴다(주 비교는 이 실험 안의 off 대 on — vLLM 배치 비결정 P46·P110 때문에 같은 시점에 같이 돈다).

## 3. 루프 깨기 정의 (코드 `harvest/teach_strip8/stall.py`, 테스트 `tests/teach_strip8/test_stall.py`)
- 호출 하나 = 명령 열쇠(mode, height, gripper, **실행 목표 = 작업 상자 clip 뒤 목표**) + 결과(정착 TCP, 잡음 여부, 패드 간격).
- 반복: 호출 i의 열쇠가 호출 i−p(p = 1, 또는 2 = 2주기, 예: above↔lift)와 같고(목표 15 mm 안), 결과도 i−p와 같음(TCP 이동 < 10 mm, 잡음 같음, 패드 간격 차 ≤ 5 mm, TCP가 목표에 5 mm 이상 가까워지지 않음 = 진짜 수렴은 반복 아님).
- 연속 반복 2번(= 같은 결과 3호출, 2주기는 4호출) → 그 호출의 결과 칸(상위의 기존 '직전 명령과 결과' 칸, 입력 형식 불변)에 어댑터 문장 한 줄을 붙인다. 기록 칸이 영어라 문장도 영어:
  - 막힘/클립: `NO CHANGE: 3 calls in a row gave the same result (BLOCKED: the arm cannot get closer to this target) -- point at a different spot or object, or choose another step`
  - 도달: `NO CHANGE: 3 calls in a row gave the same result (the target was reached, but the task step did not change) -- do the next step, or choose a different point or object`
  - 2주기: `NO CHANGE: the last 4 calls alternated between the same two commands and the robot keeps returning to the same poses (the task step did not change) -- do the next step, or choose a different point or object`
- 힌트 뒤 같은 주기의 다음 명령(열쇠가 호출 i−p와 같음)은 **실행하지 않고** 결과 칸에 `not executed: this command already gave the same result N times and would change nothing -- choose a different point, object or step`.
- 힌트 뒤 정체 호출(건너뜀 또는 실행했지만 반복)이 **3번** 더 → 편 종료, `end_reason = "stall"`(상한 `stage_cap_calls`와 구분). 결과가 바뀐 호출이 하나라도 나오면 전부 초기화(새 정체는 처음부터 다시 셈).
- 기존 LoopGuard(도달한 'above' 반복 → grasp/place 전환)는 그대로 둔다: 클립된 자리에서 자동으로 잡으면 허공을 잡기 때문. LoopGuard가 명령을 바꾼 호출은 바뀐 명령으로 센다.
- 결과 파일 `result.json`의 `stall` 블록: 힌트·건너뜀 호출 번호, 종료 호출, 호출별 (action, period, streak), 허용치.

## 4. 지표·판정
- **주 지표**: none 조건, 참값 성공 편 기준 성공률, 모델별 on − off(같은 편 짝). 짝 표(둘 다 성공·on만·off만·둘 다 실패)와 McNemar 정확 검정(양측).
- **판정(모델별, 둘 다 적용)**:
  - **ADOPT**: on − off ≥ −2 %p 이고 on의 편당 평균 호출 수가 off보다 적다 → 이후 폐루프·결합 실험의 실행기 기본값을 켬으로 바꾼다(해당 실험 등록에 명시).
  - **BETTER**(ADOPT에 더해 기록): on만 성공 > off만 성공, McNemar p < 0.05.
  - **WORSE**: on − off ≤ −5 %p(어느 모델이든) → 채택 안 함, 'stall'로 끝난 편 영상으로 원인 분해 후 새 등록.
  - 그 사이(−5 < 차 < −2 %p, 또는 호출 수가 안 줄면) → **구분 안 됨**, 기본값 안 바꿈.
- **부 지표(보고)**: 종료 이유 분포(stall·stage_cap_calls·stop 등), 편당 호출 수·sim 시간, 힌트 뒤 다음 명령이 달라진 비율과 그 뒤 성공률(= 상위가 문장을 알아듣는지), 2주기 대 1주기 힌트 수, 진단 원인 A(정체)·B(오표적)·C(클립)·D(진행 판단)로 on 실패 재분해(`tools/main35_closed/diag_stagecap` 같은 기준), light·head 조건의 on − off.
- 영상: 모든 편 10 fps 머리 | 왼손목 | 오른손목, `/data/harvest/videos/main35_closed2/<ckpt>/<arm>/<set>/<cond>/`, 원본 프레임 보존, 색인 `index.jsonl`·`index.md`. 힌트가 나온 편은 결과 문서에 프레임으로 몇 편 확인한다.

## 5. 실행(시작 조건 충족 뒤)
- 결과 루트 `/data/harvest/out/main35_closed2`(E-M35CL 루트와 분리), 로그 `logs/main35_closed2`. 팔은 체크포인트 이름 뒤 `_lb`로 구분(`f35d` / `f35d_lb` 등). 이 루트·팔 이름을 받는 스케줄러·레인 스크립트 손질은 시작 전 별도 커밋(편 로직 무변경)으로 한다.
- 서버·렌더·양보 규칙은 E-M35CL §3·변경 1과 같다: 서버 x3 GPU0(VLA GPU_WANTED 생기면 즉시 내림), 렌더 7a2a GPU0·1·3만, 편 사이마다 L9 GPU_WANTED 확인 후 비움, 서버 오류 편은 `*.srv_err`로 옮겨 재실행. 7a2a GPU2·x2 GPU0 안 씀.

## 6. 이 등록이 아닌 것 (나중 별도 팔)
- **상한 올리기(30 → 45 등)는 이 실험에 넣지 않는다.** 진단상 단독 효과 +1–3 %p. 루프 깨기 결과가 나온 뒤, 켬 상태에서 상한만 바꾸는 별도 팔을 새 등록(또는 이 등록의 '변경')으로만 돈다.
- 상위 판단 데이터(진단 고칠 것 2: 닮은꼴 속 정답 가리키기·BLOCKED 뒤 다시 가리키기·진행 판단)는 다음 본 학습 몫이다.

## 7. 한계
- 편당 한 번(배치 비결정). 힌트 문장은 상위가 학습 때 본 적 없는 문장이다 — 알아듣는지 자체가 부 지표다. 'stall' 조기 종료는 상한 전 호출을 아끼지만, 진단상 21–30호출에 성공한 편은 118편 중 1편이라 잃는 성공은 작다고 본다(멈춤 조건 2로 감시).

## 변경 기록
- (없음)
