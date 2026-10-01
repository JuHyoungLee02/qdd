# E-SIM1 — 본 35B(무학습) SimplerEnv WidowX + Bridge 시범, π0.5와 같은 조건 비교 (사전 등록)

- 작성: LIB0 에이전트, 2026-10-02 03시대 KST. **결과를 보기 전에** 커밋한다. 판정과 지표는 prereg_lib0 §4와 같고, 보고 전용 시범이다.
- 사용자 원문(10-02 03시대 KST):
  - "pi0.5에서 자기들 논문이 다른거랑 비교하면서 내놨던걸 한 것도 우리가 직접 해보면 좋을듯 … 진짜 여러개를 다 비교 테스트 해보는 걸로 하자"
  - "3인칭 금지를 내가 풀게 … 허용은 해볼게"
- 원칙(prereg_sim0 변경 2와 같음): 지금 모델 그대로 쓴다. 어댑터에는 WidowX 실제 설정값만 넣고, 잡기 위치 규칙은 넣지 않는다.

## 설정 (SimplerEnv 표준 `octo_bridge.sh`)
- 과제 4개 × 편 0–23 = **96편/팔**:
  - spoon on towel, carrot on plate, stack green on yellow(장면 `bridge_table_1_v1`, 오버레이 `bridge_real_eval_1`, 로봇 (0.147, 0.028), 60걸음)
  - eggplant in basket(장면 `bridge_table_1_v2`, 오버레이 `bridge_sink`, 로봇 (0.127, 0.06), 120걸음)
- 제어는 5 Hz·sim 500 Hz이고, `arm_pd_ee_target_delta_pose_align2_gripper_pd_joint_pos`를 쓴다.
- 카메라 `3rd_view_camera`(640×480, 로봇 `base_link`에 고정된 3인칭)를 머리 자리에 넣는다. 손목캠은 없다(빈 영상 + 문구, E-SIM0와 같음).
- 렌더는 CPU Vulkan(lavapipe)이고, 시뮬은 78dc CPU에서 돈다.
- 성공은 env `success`이고, 처음 참이 된 걸음에서 끝낸다(두 팔 같음).

## 팔
- **A**: 본 35B ep2.5(7a2a GPU2).
  - 어댑터(실측, `tools/sim0/widowx_geom.py`):
    - 닫힘 축 y. 다 연 손가락 링크 간격 7.36 cm를 × 0.107/0.0736로 바꾼다.
    - 집게 +1 열기 / −1 닫기(절대값).
    - TCP = `ee_gripper_link`(곧장 아래). 손가락은 TCP 위 3 cm까지, 몸통은 TCP 위 3 cm부터다.
    - 작업 상자 x 0.15–0.55, y −0.30–0.30, z 0.5–40 cm.
    - 로봇 이름 문장: "a robot arm (WidowX 250)".
    - 제어기가 '직전 목표'에 델타를 더하므로, 실행기 기준점 차분을 보낸다. 자세는 시작 자세다.
- **B**: π0.5 base(무학습). 입력 형식은 E-SIM0 B와 같다.
  - 정규화는 Octo 공개 `bridge_dataset` 행동 통계에 분위수 근사를 쓴다.
  - 출력은 SimplerEnv Octo `widowx_bridge` 래퍼와 같다: world_vector, 회전 오일러 → 축각, 집게 open > 0.5 → +1, 아니면 −1.
- **참고 줄**: 공개 수치(π0.5·π0 Bridge 미세조정, 제3자 표)를 둔다. 조사표(`docs/research/pi_family_evals_2026-10-02.md`)에서 공개 체크포인트로 직접 돌릴 수 있는 비교 대상(π0 open-pi-zero Bridge, Octo 등)이 확인되면 변경으로 팔을 더한다.

## 자체 검사
- **G1(실행 전, 모델 없이)**: 변환기 xy 오차는 큐브 2.2 mm, 당근 13.9 mm, 숟가락 35.7 mm, 가지 156.8 mm다.
  - 큐브(몸체 원점 = 보이는 중심)로 기하는 맞음을 확인했다.
  - 길쭉하거나 바구니에 가린 물체는 몸체 원점과 보이는 중심이 달라서 오차가 크다. 검사 정의의 한계로 적고 통과로 본다.
- **G2**: A 형식 오류율 50 % 미만이어야 한다.

## 변경 기록
- (없음)
