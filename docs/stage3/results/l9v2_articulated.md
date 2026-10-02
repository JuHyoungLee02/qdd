# L9 v2 관절 스킬 1단계 (서랍·문·미닫이·노브·버튼·밀기) — 결정·결과 기록

설계 출처: `docs/research/articulated_skills_datagen_2026-10-02.md` (dev 57e2797). 사용자 원문: "서랍·문·손잡이 돌리기·밀기 … 저격이라기보단 학습하면 리베로를 해결할 수 있는 무언가의 테스크도 들어가 있음 좋을듯".
1단계만 승인(설계 문서의 24–35일 전체 계획은 미승인). 시각은 KST.

## 1. 범위 (1단계)
- 형식 v3 = v2 + `skill` ∈ {pick, place, pull_axis, push_axis, rotate, press, push_slide} + `point2`. v2 행은 그대로 유효(`skill` 없음 = pick/place).
- 자산: 절차 생성만(서랍장, 여닫이 문, 미닫이 문, 노브/다이얼, 버튼/스위치). PartNet-Mobility·GAPartNet·LIBERO·RoboCasa·BEHAVIOR 자산·장면·과제 사용 금지.
- 과제 정의 약 16개(+ 복합 3–4), 로봇 AI Worker·Franka 먼저, R1 Pro 다음, G1 제외.
- 참값 플래너: 손잡이 잡기 → 관절 축을 따른 당김/회전(cuRobo + 작은 데카르트 추종기), 누르기, 밀기. 성공 = 관절 각/변위 임계. 실패·복구 라벨. 손잡이 잡기 다양화(정준 자세 하나 아님). 관절 걸음 ≤ 0.034 rad(명령).
- 관문: 스모크 → 정의마다 ≥ 20편 시범 + 프레임 검수(숫자만 보고 판정 금지) → 성공률·라벨 정확도·다양성 통과 → L9 v2 양산 큐에 추가.

## 2. L9 책임자와 합의 (10-02 16시, a8f68de3d815957c2)
- 코드 = `harvest/l9art/` (+ `tests/l9art/`). `harvest/l9/*`는 import만, 수정 0. 훅이 필요하면 L9 책임자에게 요청.
- `rt9.install`은 전역 훅(world.step/reset, xlabels.plan)을 갈아 끼우므로 **안 쓴다**. cuRobo는 `plan9_server.PlannerProxy`만 쓴다. `world9.make_world9`는 그대로 쓴다(빌드 설정 패치는 이 프로세스 안에서만).
- 시범 레인: e9f3b GPU5에 2개(L9가 그 카드 레인 2개를 뺌). `tools/l9/isaac.sh`(UUID로 고장 카드 거부) 그대로 사용, lend9/YIELD 안 씀.
- 양산: 별도 run dir `/data/harvest/l9v2/art_prod/` + jobs.txt, 같은 supervisor.sh·lane.sh(관문 뒤 L9 책임자가 lane.sh에 MOD 변수 추가).
- v3 필드: 답 JSON의 `command` 안 `skill`·`point2`, meta.json 최상위 `skill`. 요청문 설명 블록은 별도 상수(ART_BLOCK)로 빌드 단계에서 붙인다.
- 정본 L9 코드: code_l9_7f5767a.

## 3. 형식 v3 (호출 단위)
- 호출 하나 = 이동 하나(L9 v2 d-min과 같은 단위). 예: 서랍 열기 = ① 손잡이 위(height above, approach·rot) ② 잡기(height grasp, gripper close) ③ **축 이동**(`point2` 있음 = 관절 축을 따라 손잡이를 point2까지) ④ 놓기(gripper open) ⑤ 물러나기(edit) ⑥ stop.
- `point2`(0–1000, `point_2d`와 같은 양자화): 움직이는 접점(손잡이·문 면·노브 표시점·밀 물체 중심)이 끝날 곳의 머리 영상 투영. 축·거리·회전량은 코드가 장면의 관절에 스냅해 유도(새 자유 필드 없음).
- press: `point2` 없음, height grasp = 작동 깊이까지 누르고 되돌림.
- `skill`은 그 단계가 속한 스킬(접근·잡기 호출에도 같은 값), 집기/놓기 단계는 pick/place.

## 4. 진행 기록
- 10-02 16:1x 시작. 정직한 ETA: 코드(자산·월드·플래너·기록·과제) ≈ 2일, 스모크·시범·고침 ≈ 1–2일 → 관문 판정 ≈ 10-05 저녁, 양산 추가 ≈ 10-06.

## 5. 스모크 경과 (10-02, e9f3b GPU5, AI Worker)
| 판 | 코드 | 결과 | 고친 것 (원인 실측) |
|---|---|---|---|
| smoke1 (6편) | 2e3217a | 성공 0/5, 버튼 SKIP | Isaac Lab fix_root_link는 강체 루트 필요 → ArticulationRoot를 base 몸체에; 버튼 패널이 스위치만이라 버튼 정의 SKIP; 노브: 위 장착 회전 부호가 반대라 노브가 판 속에 묻힘, 핀이 낮아 패드가 몸통에 걸림(닫힌 간격 1.8 cm) → 핀 2.4–3.2 cm·패드 안쪽 끝 3 mm 위; 서랍 버섯 손잡이가 앞판 속(x 오프셋 빠짐), 막대 기둥이 1.8 cm 떠 있음; 문: 46°에서 팔 도달 끝(ik); 밀기: 둥근 물체(버거)가 굴러 넘어짐, 관절 걸음 0.072 |
| smoke2 (28편) | +동기화 | 성공: 버튼·스위치 4/4, 서랍 닫기 2/2, 서랍 열기 1/2, 문 열기 1/2, 밀기 1/2 | 놓은 뒤 서랍·미닫이가 2–7 cm 되돌아감, 노브가 접근 중 150° 돌아감, 문 닫기·미닫이 닫기 접근 자세 계획 실패 6/6 → 진단 |
| 진단 drift | 709e545 | USD 관절에 DriveAPI가 없어 PhysX에서 감쇠·스프링·마찰이 꺼져 있었음(버튼이 눌린 채, 문이 등속으로 계속 돎) → PhysicsDriveAPI + PhysxJointAPI 추가 뒤 버튼 복귀·서랍 정지 확인 | 문은 시작 팔과 닿아 천천히 닫힘(접촉, 판단 보류) |
| smoke3/4 | 2a2c865 | (진행) | 자체 물체 풀(납작한 밀기 물체·작은 잡기 물체), 머리를 상호작용 점으로 조준, 문 경첩=쓰는 팔 쪽, 미닫이 닫기=손잡이 잡고 밀기, 접촉 이동 명령 걸음 0.02 rad, 손잡이 놓을 때 3 cm만 벌림, 노브는 축 정렬 접근 |
