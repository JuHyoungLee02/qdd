# 본 35B 학습 — 최종 채택 구성 (정본 요약)

채택된 것만 적는다. 취소·기각된 안(H, H+C′, grid 오버레이, 3인칭 데이터, DROID 등)은 user-log·results 문서에 이력으로만 남긴다.
갱신: 2026-09-29 KST. 근거 링크는 각 줄 끝.

## 방법
- **D**: VLM은 점(0–1000 정규화) + 단계 의도만 출력하고, xyz는 코드가 센서 깊이로 계산한다. 학습에 깊이는 필요 없고, 실행할 때 깊이 카메라가 필요하다. (user-log 159, canon §98 supp 3, results/final35.md)
- 손 정보는 입력하지 않는다. (user-log 154)
- 모델: Qwen3.5-35B-A3B LoRA r16 (attention·DeltaNet·shared experts).
- 이미지: 원(ring) 표시판을 쓰고 격자는 쓰지 않는다. 머리 시점만 쓰고 3인칭·어안은 쓰지 않는다. (view8.md)

## 학습 데이터
| 묶음 | 내용 | 상태 |
|---|---|---|
| L8S-real (b4) | 실물 자산·방 배경·조명/HDR·CC0 재질·목 무작위 ~15%(pan±15°, tilt±10°, roll 0, 대상·목표가 보일 때만), 헷갈림 물체 ~20%, 쟁반 ≤10% | 시범3·재검수 후 양산 |
| L8S-simple | 기존 단순 장면을 b4 조명·배경으로 다시 생성, 도형 <15% | 양산 |
| L8S-drawer (b3d) | 서랍 과제 | 양산 |
| 공개 점 데이터 | 검증 통과 31,202행(투영 ≤5 px, SAM, 이름 일치, 머리 시점), 반복 ≤1.5×, 실효 비율 약 59% (목표 75%) | 완료 (opratio.md) |
| AgiBot v3 물체 점 | 1,384행(이름·마스크 4중 재검증, 통과율 41%) | 완료 (data_inventory) |
| RB2 실측 | 원래 G용이던 약 4,000행을 학습으로 옮김 | 완료 (user-log 172) |

제외: 품질 제외분, 3인칭(RH20T·DROID), 관문 경계 행, PixMo, 어안(MolmoBot fisheye/gopro), 일반 평가 세트 G 분할. (user-log 165, 169)

## 학습 설정
- 파드 안에서만 DDP. global batch 24(micro 2 × accum 3 × 4 GPU), expandable_segments.
- `--save-every`/`--resume` 전체 상태 저장 (harvest/teach_l8/ckpt.py, dd2ef12).
- 시운전: 최대 메모리 86.8–95 GB, 3.1 s/step, 12.6만 행 기준 약 9 h. (98f2a79)
- 8 GPU로 가면 accum을 조정해 global batch 24를 유지한다.

## 비교·평가
- 사전등록 먼저. 판정은 A/A로 보정한 여유와 중앙값, >20 mm 실패율로 한다. (tools/teach_pt/ni_judge.py, 54e7998, user-log 186)
- 평가 세트:
  - L8-X 세트
  - 일반 평가 G (gsplit_g166, RB2 held-out 1,506행, Where2Place 여유 −0.10, RefSpatial-Bench)
  - 대규모 폐루프
  - 한계 지도
- [미확정 제안] 이번 판에 관절 과제(서랍 열기 등 새 어휘)는 학습에 넣지 않는다. 평가에서도 뺀다. 사용자 결정 대기.
- [미확정 제안] 추가 GPU가 오면 8 GPU로 학습한다.

## 로봇 시작 자세 (L8S 변경 21, 데이터와 실행 공통)
- 머리: head_joint1 0.785 rad(45°), head_joint2 0(편의 약 15 %만 pan ±15°·tilt ±10° 무작위), 롤 고정.
- 오른팔: 장면 초기화 뒤 오른손 TCP를 작업 면 기준 (x 0.15, y −0.42, z +0.40 m, 로봇 기준 좌표; 변경 24, 이전 변경 21은 0.22, −0.42, +0.30)로 먼저 옮긴 자세에서 시작한다(`teach_l8d.clutter_x.ARM_START`, 걸음당 관절 ≤ 0.035 rad). 머리캠 시야에서 탁자 위를 가리지 않게 하려는 것이다. 편마다 도달한 관절값은 scene.json `furniture.arm_start.q_arm`에 남는다. 실행(폐루프·실로봇)도 같은 목표 TCP로 옮긴 뒤 시작한다.
- 관절 속도: 오른팔 관절은 걸음당 ≤ 0.04 rad(명령 0.035), 집게 손가락은 설계상 빠르게 닫혀 이 기준에서 뺀다(meta.max_dq_rad = 팔, max_dq_finger_rad = 손가락).
