# E-LIB1 — LIBERO에 π0·π0-FAST 공식 체크포인트 팔 추가 (사전 등록, 보고 전용)

- 작성: LIB0 에이전트, 2026-10-02 03시대 KST. **결과를 보기 전에** 커밋한다.
- 근거: 사용자 원문(10-02 03시대) "pi0.5에서 자기들 논문이 다른거랑 비교하면서 내놨던걸 한 것도 우리가 직접 해보면 좋을듯 … 진짜 여러개를 다 비교 테스트". FAST 논문(arXiv 2501.09747)과 KI 논문(2505.23705)의 LIBERO 비교표를 같은 조건에서 직접 재현한다.
- 팔(모두 LIBERO로 미세조정된 공식 체크포인트, openpi):
  - **P0** = `pi0_libero`(config pi0_libero)
  - **PF** = `pi0_fast_libero`(config pi0_fast_libero, openpi 이슈 #849에 0 % 보고가 있다 — 그대로 잰다)
- 조건: E-LIB0 R과 **완전히 같다**.
  - 같은 200편(4묶음 × 10과제 × 초기 상태 0–4), openpi `examples/libero/main.py` 경로, replan 5, max_steps
  - 우리 실행기(`harvest.lib0.run_pi`), venv_libero, 78dc CPU OSMesa
- 서버: x3 GPU0(메모리 0.3씩), 포트 P0 :8705, PF :8706.
- 지표: prereg_lib0 §4. 표에는 참고 줄로 넣는다(LIBERO로 학습했으므로 우리 무학습 팔과 조건이 다르다).
- 공개 수치(FAST 표): π0 96.8/98.8/95.8/85.2, π0-FAST 96.4/96.8/88.6/60.2. 우리 재현과 나란히 적는다.

## 변경 기록
- (없음)
