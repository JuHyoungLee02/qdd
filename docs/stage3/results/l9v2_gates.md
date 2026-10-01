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
