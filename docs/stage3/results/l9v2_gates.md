# L9 v2 관문 기록 (설계 §12, 2026-10-02~)

## 설계 항목별 구현 표 (관문 보고마다 갱신; 함정 P152)
| 설계 항목 (§) | 상태 | 코드 | 비고 |
|---|---|---|---|
| cuRobo v0.8.0 이상만 (§12.5) | 구현 | `plan9.py` (버전 검사 0.8.0 미만 거부), `plan9_server.py` | Isaac 앱의 warp 1.8.2 때문에 별도 프로세스 |
| antipodal 해석 샘플러 (§12.4) | 구현 | `grasp9.py`, `tools/l9/grasp_gen.py` | 마찰 원뿔 μ 0.4, 손가락 자리 양쪽, 바깥·벽 잡기 |
| GraspGen-X 후보 합류 (§12.4) | 미구현 | — | antipodal 경로 다음 |
| Isaac 들어 올림 + 흔들기 시험 (§12.4) | 구현 (GTEST) | `tools/l9/grasp_test.py`, `gtest9.py` | 유효 = 카탈로그 마찰 흔들기 통과(pass_shake), μ 0.4는 기록 |
| 속이 빈 물체 SDF 충돌체 (§12.4) | 구현 (GTEST), 양산 연결 확인 중 | `gtest9.apply_collider`, `sim/scene._collider_spawn` | 큰 그릇 테두리 잡기는 들어 올림 실패(토크) |
| 지지면·이웃 손가락 여유 (P1 w_free) (§12.12) | 구현 | `rt9.free_opening` (OBB SAT) | 손가락 근위 링크 모형은 거침(GTEST 지적) |
| cuRobo IK 도달 선별 (§12.4) | 구현 | `rt9._valid` → `plan9.ik` | 그리퍼 접촉 링크 제외 |
| 자연스러운 잡기 라벨 규칙 natural_v1 (§12.8) | 구현 | `grasp9.NATURAL/natural_order/part_of/select_natural`, `v2plan.choose` | 머그 손잡이 검출 미구현 |
| 지시 행 ~20 % (§12.8) | 구현 | `v2plan.draws/choose`, `rt9.prechoose` | 첫 집기에만 |
| 회전 구간 영상·기저 (§12.8) | 구현 | `grasp9.rot_img/rot_base` | |
| 도달 불가 대체 순서 + 글 보고 (§12.8) | 구현 | `rt9.next_fallback`, `outcome` 훅 | 최대 6회 |
| 사전 접근·직선 접근·살짝 들기 (§12.5) | 구현 | `plan9.grasp` (plan_grasp), `rt9.motion_for` | 마지막 40 %는 절반 속도 |
| 운반·놓기 높이 변주·위로 빼기 (§12.5) | 구현 | `v2plan.plan`, `rt9.motion_for` | 놓기 자세(눕히기 등)는 미구현 |
| 사람 같은 성향 (§10/§12.5) | 구현 | `rt9._resample` ← motion9 스타일 | |
| 관절 걸음 ≤ 0.04 rad (§12.5) | 구현 (명령), 측정 초과 일부 | `plan9.resample`, `rt9._guard` | 시뮬 관절 한계 밖 계획 거부 |
| P1 사전 벌림 스탠드오프 설정 (§12.12) | 구현 | `TrajExec`, `rt9.open_width` | cuRobo 손가락 잠금 값은 최대 벌림(보수적) |
| P2 힘 제한 닫기·정착·판정·재잡기 (§12.12) | 구현 | `TrajExec.tick`, `rt9.on_grip_done/on_move_done` | CONTACT 상한 +2 cm (스모크 보정, 가설) |
| 패드 원호 낙하 보정 (GTEST) | 구현 | `gtest9.exec_pose` ← `rt9._exec_pose` | 지지면 근처에서만 물림 |
| 형식 v2 라벨 (점·approach·rot, 벌림 칸 없음) (§12.8) | 구현 | `rt9` pt_command 훅, `build9` GRASP 블록·robot 줄 | 최종 문구는 E-GP2 뒤 |
| meta 원시값 (§11.9 목록) (§12.8) | 대부분 구현 | `v2plan.choose`, `rt9.pick_record/episode_meta` | open_cmd_t 등 시간선 일부 |
| E-HCAM8 머리 카메라 무작위화 (§12.6) | v1 경로 재사용 | `hcam9`, `world9` | v2 시범에서 동전 확인 예정 |
| 여러 로봇 (§12.2) | AI Worker 구현, Franka·R1 Pro·G1 진행 (ROBOT) | `robot9`, `curobo9` | |
| 환경 확장 (§12.3) | 진행 (ENV): 25계열/128규칙 | `scene9`, `vary9` | |
| 과제 ≥ 150 (§12.7) | 진행 (TASK): 253 정의, 지금 실행 가능 198 | `task9v2`, `alloc9` | |
| 외부 카메라 짝 (사용자 10-02) | 진행 (CAM) | `ext9` | |
| E-AP1 (§12.12) | 사전등록만 | `docs/stage3/prereg_ap1.md` | 시범 뒤 |

## 시범 경과
- 10-02 03–04시 KST 스모크 8편 × 7판(AI Worker 오른팔): 막힘을 차례로 고침 — cuRobo가 Isaac 앱 안에서 import 불가(warp) → 별도 프로세스; 시작 상태가 관절 한계 위(preroll j7 = 1.82) → 0.03 rad 안으로 자름; cuRobo URDF 한계가 시뮬보다 넓음 → 거부 + ROBOT이 시뮬 한계 −0.03으로 맞춤; 잡은 물체가 지지면 위에서 시작·끝 충돌 → 들기·놓기 때 아래 지지면 제외; 대상 상자 전체를 장애물로 두면 잡기 계획 불가, 빼면 팔이 대상을 침 → 대상 절반 크기 코어만 장애물; 시험 파일 길이 불일치 → idx 기준 복원.
- 10-02 04:13 KST AI Worker 시범 시작(정의 198 × 10편, 레인 8개).
- 04:13–09:10 KST 시범·진단 경과(AI Worker; 판마다 고쳐 재배포):

| 판 (코드) | 편 | 성공 | 관절 튐 > 0.04 | 고친 것 |
|---|---|---|---|---|
| 시범 시작 (2eb6f4b) | 49 | 14 % | 45 % | — |
| 711c431 | 40 | 30 % | 15 % | 직전 명령에서 계획 시작(P181), 다른 곳 닫기는 후보 실패 아님 |
| df06ba9 | 40 | 27 % | 18 % | WIDE도 들어 보고 판정, 운반 대체 경로 |
| 8746e37–8d7efdc | 17 | 12 % | — | 전이 구간 전체 링크 검사(P182), 똑바로 놓기(P183), 놓을 yaw 선택 |
| 진단 dbg3 (깨끗) | 12 | 33 % | 0 | — |
| 진단 dbg4 (깨끗, bbe5ad0) | 12 | **67 %** | 0 | 손–물체 관계 매 호출 재측정, 놓기 높이 0.8–2.5 cm, 받침면 제외(P184), 반복 reopen → 들기 |
| 시범 (be36233, 섭동 p 0.15) | 26 | 38 % | 12 % | 이웃 상자 0.8배(관계 놓기), cuRobo 시드 12·시도 8 |
| Franka 진단 dbgf (깨끗) | 17 | 18 % | 0 | 전이 계획 실패가 주원인 → 분석 중(L9v2-DIAG) |

- 누적 526편 잡기 지표(gate_v2): top 34 %·oblique 37 %·front 12 %·side 11 %(top ≤ 50 % 통과, 계열마다 ≥ 5 % 통과), 회전 영상 구간 12/12, 보이는 점 70 %, 자연 1순위 48 %, 지시 행 12 %, 재잡기 12 %, 닫힘 CONTACT 58 %·WIDE 14 %·EMPTY 7 %. 관문 '계열별 실행 ≥ 70 %'와 '관절 걸음'은 아직 미통과.


- 10-02 09:10–13:00 KST (AI Worker 시범 계속, Franka·R1·G1 시범 시작):

| 판 (코드) | 로봇 | 편 | 성공 | 실패 단계 | 고친 것 |
|---|---|---|---|---|---|
| since 1790898547 (cdc9714–d102de6) | AI Worker | 260 | 39 % | place 89·approach 37·joint_step 18·lift_carry 7·grasp 4·timeout 3 | 직선 이동 세계 충돌 검사, retreat 실패 시 정지 |
| 95e8ce0–3792b9a (11:07~) | AI Worker | 188 | 52 % | place 51·approach 22·joint_step 8·lift_carry 5·grasp 3 | attach 구 ≤ 16(P185), 놓기 yaw 재선택(P187), 명령 걸음 0.034(P188), pre-open 스탠드오프(P189), 대체 잡기 라벨 유지 |
| 95e8ce0–3792b9a | Franka | 85 | 55 % | place 17·approach 10·lift_carry 6·grasp 3 | (첫 33편 79 %, 가족이 늘며 내려감) |
| 3792b9a | R1 Pro | 2 | 1/2 | lift_carry 1 | 면 높이 관문(DIAG 8)·장면 다시 뽑기 |
| 04f9295–3792b9a | G1 | 3 | 0/3 | approach 2·lift_carry 1 | 닫힘 판정 = 손가락 접촉; SKIP 대부분(면 높이 밴드·유효 잡기 없음) → 레인 멈춤, 진단 |

- 놓기 실패의 정체(v2_release_check): 실패 편도 열기 순간 손은 put 자세(dz 중앙 0 mm, dxy 6–8 mm, 성공과 같음) → 연 뒤 대상이 넘어짐. DIAG 10: 열 때 대상 바닥이 면보다 10–34 mm 위(놓을 곳 높이가 카탈로그 값: 누운 책 +22 mm, 2층 쌓기), 열 때 넘어짐 6/11·내려가며 기울어짐 2/11.
- 잡기 분포(95e8ce0~ 성공): AI Worker top 32 %·oblique 39 %·side 18 %·front 12 %, 지시 19 %, 왼 54 / 오른 53; Franka top 25 %.
- 처리량: 13:00 기준 2 h 동안 AI Worker 123 + Franka 49 성공(~86/h). 레인 가동률 ~42 %(재기동 대기·job 부팅) → job 20행, 재기동 묶음.

- 10-02 17:45 KST — 배치 다양성 관문(tools/l9/diversity9.py, 관문 통과 편, 정의×로봇 칸 n ≥ 5 의 중앙값; 로봇 기준 좌표):

| 집합 | 칸(n≥5) | 편 | 중복 조합 | std x | std y | IQR x | IQR y | 대상 yaw 원형 std | 거리 std | 로봇 yaw std |
|---|---|---|---|---|---|---|---|---|---|---|
| v2 AI Worker | 131 | 2,371 | 0 | 0.062 | 0.241 | 0.098 | 0.374 | 0.788 | 0.061 | 0.149 |
| v2 Franka | 89 | 1,245 | 0 | 0.059 | 0.109 | 0.088 | 0.187 | 0.767 | 0.066 | 0.154 |
| 참조 v1 양산 AI Worker | 68 | 5,657 | 0 | 0.066 | 0.270 | 0.110 | 0.509 | 0.731 | 0.067 | 0.160 |

  - 중복 0. AI Worker 의 y 퍼짐은 v1 보다 작음(std −11 %, IQR −27 %) → 관문 '참조 이상' 미달 항목으로 기록, 원인 조사 중(유효 잡기·도달 검사로 장면이 걸러지는 효과로 추정 [가설]). Franka 는 오른팔·받침대 작업 공간이라 y 가 좁음(참조 없음).
  - 계획 행 시드 중복 0(prodA 10,101 · prodA_f 2,119 · prodF_f 1,813 행; 재추첨으로 옮긴 행 292·219, 모두 고유 (seed, family, rule, def)).
  - R1·G1 수정은 로봇 위치를 상수로 바꾸지 않고 로봇별 거리 범위(scene9.DIST_BY_ROBOT)로 하도록 지시함(사용자 10-02).
- 할당(승인 10-02): 로봇별 총 AIW 3.8k / Franka 4.0k / R1 3.7k / G1 3.4k(관절은 G1 제외). 단팔 상한 AIW 2.6k · Franka 3.7k · R1 2.5k · G1 2.2k, 정의×로봇 칸 상한 = 1.15 × 로봇 상한 / 198. tools/l9/capfilter9.py 를 prefilter 체인(CAP=1)에 넣음: 17:45 기준 AIW 기대 2,926(대기열 포함, 상한 도달 → 새 AIW 행 없음), Franka 기대 2,096 → prodF2(3,016행) 추가.

- 10-02 19:50 KST — GraspGen-X 설치 전 라이선스 확인(main 지시, 양팔 담당 확인): NVlabs/GraspGenX 저장소 코드는 Apache-2.0(NVIDIA, 2023–2026), 체크포인트는 NVIDIA Open Model License(기존 승인). README·LICENSE 로 확인: 구 NVlabs/GraspGen 저장소 코드에 의존하지 않음(다른 학습·추론 구조, 독립 코드베이스, README 가 두 저장소를 명시적으로 구분). 금지 조건(구 GraspGen 코드·가중치) 위반 없음 → 설치 승인.
- 용도: 양팔 받는 팔 잡기 후보(물체의 손 안 자세 + 주는 팔 집게를 충돌 형상으로) 생성, G1(Dex3-1 조건화 가능 여부 확인 중) 잡기 후보. 사용자 원칙(10-02 19시대): 기하 표시는 규칙 기반 유지, 세밀한 선택(받는 팔 잡기 위치·손 모양별 잡기·삽입/배치 자세·손잡이 잡기)은 학습 기반 생성기로. 규칙판과 ≥20편 비교 후 나은 쪽만 채택.

- 10-03 00:13 KST — y 퍼짐 수정(tools/l9/ystrat9.py, prefilter9→capfilter9 사이, commit 0ef17f6) 양산 반영 후 ~3시간 AI Worker 결과(diversity9.py 공식과 동일 산식, job 접두 `mpj*`/`*tA*` = YSTRAT 체인 vs `mpa*`/`mpb*` = 기존 체인, 관문 통과 편만):

| 집합 | 칸(n≥5) | 편 | 중복 조합 | IQR y 중앙값 | 성공률(실행분) |
|---|---|---|---|---|---|
| YSTRAT 체인 (mpj*/*tA*) | 55 | 690 | 0 | 0.270 | 25.5 % (576/2,262) |
| 기존 체인 (mpa*/mpb*, 동시간대) | 108 | 1,381 | 0 | 0.286 | — |
| 참조 v1 양산 | 68 | 5,657 | 0 | 0.509 | — |

  - 아직 유의한 개선 없음(0.270 vs 0.286, 오차범위 내) — 순수 CPU 재현 검증(8–24 job 표본, overall iqr_y 0.448→0.493–0.519)과 어긋남. "재잡기 실패로 넓은 y 가 걸러진다" 가설은 기각: 재추첨행(k≠0) 대 비재추첨행(k=0) 실행 성공률이 25.5 % vs 25.8 % 로 동일(스킵 제외). 가장 가능성 높은 원인은 표본 부족 [가설] — 참조 v1 은 칸당 n 이 5,657 편 누적에서 나왔는데 지금은 690–1,381 편뿐이라 칸별 IQR 추정 자체의 분산이 큼. 누적 더 돌린 뒤 재확인 필요.
  - 중복 배치 0 확인(두 체인 모두).

- 10-03 00:18 KST — 빌드 단계 가시성 관문(VLM이 안 보이는 점을 가리키지 않게, harvest/l9/visgate9.py+build9.py, commit 30a0e1d; world9._head_sees 소진 시 SkipScene도 같은 커밋): 화면 밖(5 % 테두리)·너무 작음(apparent radius_px<6)·50 % 이상 가림(teach_l8d.clutter_x.occlusion 재사용) 드롭, 단계 인식(approach→대상만, 그 외→놓을 곳만, 잡은 물체 제외, labels.jsonl "occ" 우선)으로 수정 후 표본(로봇당 ≤500편 또는 전수) head 드롭률: AIW 0.36 %(15/4,110)·Franka 0.09 %(4/4,390)·R1 0.06 %(2/3,562)·G1 0 %(0/11) — 전부 3 % 이내, 잔여 사유는 전부 out_of_frame. 3인칭/external 뷰는 23~28 %(AIW 27.6 %·Franka 23.4 %, R1·G1 은 external_cams 0건)로 더 높으나 고정 카메라가 다른 각도에서 보는 정상 범위로 판단(off/on 별도 채널이라 드롭률이 높아도 그만큼 3인칭 행 수만 줄어듦), 추가 조치 불필요. tests/l9/test_visgate9.py 17개 포함 전체 통과.

### R1 Pro 원인 분해·수정 (L9v2-R1, 10-03 00–02시 KST, 기존 R1 팀)
- 자산 점검: TCP(시뮬=cuRobo 0.01 mm)·관절 한계(시뮬=URDF=yml)·자기충돌 무시쌍 정상 — 불일치 아님.
- 원인 1 (재생 실측, cuRobo 호출 기록 `L9V2_DEBUG_DIR` → r1own/tools/replay.py): READY TCP 가 면 위 9.4 cm(중앙값)라 pilotR 207편 중 142편이 lift_clear 로 시작했고, 그 들기는 빈 세계에서도 IK 불가(팔꿈치 joint4 한계 −1.745 rad). "충돌 없는 경로 없음" 의 대부분은 충돌이 아니라 도달 불가.
- 원인 2: lean 0.8 의 위잡기 작업공간은 torso_link4 앞 ≈0.5–0.65 m 의 좁은 기둥(reach_band.py, 4 yaw, 여유 0.05 rad) — AIW 도달 탐침으로 놓은 물체·놓을 곳의 상당수가 기둥 밖.
- 원인 3: 직선 접근이 1-seed IK 로 팔꿈치 한계에 걸림(다른 IK 가지는 됨), 잡기 자세 자체에서 집게가 설비·통 벽에 닿는 후보(검사에서 접촉 링크를 빼서 통과).
- 수정(R1 전용, 범위/검사, 상수 이동 아님): READY 면 위 ≈21 cm, 운반 여유 U[0.05,0.10] m, 잡기 끝에서 거꾸로 푼 직선 접근 + 관절공간 이동, 잡기 자세 링크 검사, 장면 배치를 R1 측정 도달띠(잡기·운반 높이 둘 다)로. lean 은 0.8 로 동결(0.6: 2/14, 0.4: 0/5 로 이득 없음, 기록 board/humanoid_failed.md).
- 같은 시드(pilotR 잡 20개): 기준 6/36(17 %) → +READY·운반 6/21(29 %) → +거꾸로 접근 16/44(36 %) → +링크 검사(띠 없음) 7/22(32 %) → **+도달띠 vL8B 14/24(58 %), approach 실패 0**, 관절 걸음 위반 1. 다양성(diversity9 --all): 중복 0, std_y 0.33(pilotR 0.20).
- 판정 스윕: /data/harvest/l9v2/r1sweep (pilotR 198정의 × 20행, 라운드로빈, robot_gate9.py).

## 로봇별 자기 카메라 (사양 r2-cams, 사용자 10-03 02시 "각 로봇은 자기 카메라 그대로, 카메라 수 무관")

출처: AI Worker = `FFW_SG2_REAL_cameras.py`·설계 §37/§47(공식 사양: 머리 ZED Mini 스테레오 기선 63 mm, 손목 D405 × 2); Franka = franka_description(카메라 없음); R1 Pro = GalaxeaManipSim `galaxea_sim/robots/r1_pro.py`(abe7f51)·`assets/r1_pro/robot.urdf`(카메라 링크 `zed_link`·`{left,right}_realsense_link` 뿐), BEHAVIOR `r1pro.urdf`(같은 3개), 같은 회사 R1-Lite 공개 데이터(`head_rgb`·`head_right_rgb`·손목 2 → 머리 ZED 는 실물 스테레오); G1 = unitree_ros `g1_29dof_with_hand_rev_1_0.urdf`(센서 링크 `d435_link`·`mid360_link`(라이다)·IMU 2, 손 Dex3-1 에 카메라 없음).

| 로봇 | 실물 기본 카메라 | 지금 렌더 | 차이 | 처리 (10-03 02시 사용자 결정) |
|---|---|---|---|---|
| AI Worker FFW-SG2 | 머리 ZED Mini 스테레오(왼·오), 손목 D405 × 2 | 머리 왼눈(672×376, 85°) + 손목 D405 × 2 | 머리 오른눈 | 불필요 — 추가 안 함 |
| Franka (mast) | 없음(Panda 는 카메라 없음) | 우리 설계: 받침대 D435 + panda_hand D405 | 해당 없음 | 정의된 장비 그대로(r1 카메라 위치) |
| Galaxea R1 Pro | 머리 ZED 스테레오(왼·오) + 손목 RealSense × 2 (가슴·섀시 카메라는 공급사 시뮬·URDF 어디에도 없음 — 미확인) | 머리 ZED 한 눈(100.8°) + 손목 × 2 | 머리 오른눈(가슴·섀시는 미확인) | 오른눈은 AIW 와 같은 원칙으로 추가 안 함; 가슴·섀시는 공식 자료 확인 전 추가 안 함 |
| Unitree G1 | 몸통 D435 하나(+ MID-360 라이다) | D435 + 손바닥 D405 × 2(§9.2 가설, 실물에 없음) | 손바닥 카메라는 실물에 없음 | **빌드에서 손목 뷰 제거**(편은 유지), 게이트 "G1 행 wrist 뷰 0" |

- 형식(views9, specgate9.SPEC_CAMS = `L9v2-spec-final-r2-cams`): 표준 4칸(head·wrist_left·wrist_right·third_person, 고정 순서, 없으면 "(none)") 다음에 그 로봇의 추가 실물 카메라를 `- view: <이름> -- Image k: …` 로 덧붙인다(이름 = `views9.EXTRA_VIEWS`: head_right·chest·torso·base_front/rear/left/right). 이미지 라벨은 빌더·학습기(`teach_l8.dataset.image_labels`)·실행기가 `views9.view_label` 하나를 쓴다. 추가 카메라는 실행기가 cams.json `extra_views` = {이름: 카메라 기록 + "img"} 로 남기면 빌더가 읽는다(지금은 0건).
- 사양 판: 디스크의 편은 그대로(meta spec = final / final-r1, 행에 `episode_spec` 로 기록), 슬롯 빌드의 모든 행에 `spec_version = L9v2-spec-final-r2-cams`. SPEC_FAMILY 로 세 문자열은 한 계열이고, 슬롯 빌드 게이트는 행 전부가 r2-cams 여야 통과(옛 빌더 행 섞임 금지). 추가 뷰 없는 행은 태그만 빼고 이전 빌드와 같다.
- 스키마 게이트(`specgate9.view_schema_errors`, `gates(views=True)`, build_v2 슬롯 빌드에서 항상): 파싱, 표준 4칸 고정 순서, 추가 뷰 이름이 목록에 있음·중복 없음, 이미지 번호 1..n, `image_views` = 나열 순서, 이미지 수 = 나열 수, head = Image 1, 로봇에 없는 표준 칸 금지(G1 wrist), spec_version = r2-cams.
- 함께 고침: build_v2 `--spec` 비교를 계열로(정확 문자열 비교가 Franka r1 편 전부를 빼고 있었음).
- 장면 배치·시야 검사의 로봇별 카메라는 G1·R1 팀 배치 코드 소관(이 변경은 카메라 세트·스키마만).
