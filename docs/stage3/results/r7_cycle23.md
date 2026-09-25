# R7 객관 검증 순회 — 23회차 (cycle 23, 연속 무결 카운트 1에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle22.md` §5 표·결론을 근거로 쓰지 않고 사전 등록 원문에서 대조표를 다시 만들었다. 행마다 **21·22회차와 다른 새 경계값으로 구성한 입력 → 실제 함수·CLI 출력** 또는 **파드 원자료 재계산**으로 확인했다). 작성 2026-09-25 17:25 UTC 무렵(로컬 시작 16:47:46 UTC, 파드 첫 명령 16:57:24 UTC, 파드 정리 끝 17:11:28 UTC). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`a4cddad`**(`a4cddad3a675c7ab…`, 커밋 시각 2026-09-25 16:47:18 UTC, "R7 cycle 22 PASS (clean count 1); mark central-difference notes as old-data only, update probe scope in handoff"). `git diff --stat 3a3d76c a4cddad` = 7파일 **문서만**: `docs/design/00-interfaces.md`(+2, §82 보충 2), 새 `docs/superpowers/specs/2026-09-26-astra-vla-coupling-design.md`(+162), `docs/user-log.md`(+15, 83·84), `docs/handoff.md`(:88 한 줄), `docs/stage3/results/r7_cycle22.md`(새), `se2e_data.md`(:62·:96 표시), `se2e_temporal.md`(:81 표시). `harvest/`·`tools/`·`tests/`·사전 등록 원문(`prereg*.md`·`prereg.json`·`E-first`·`EVAL`·`M4`·계획 e2e-ready) 변경 **0**(같은 명령으로 확인). 작업 트리의 다른 에이전트 미커밋 파일(`harvest/astra_motion/`, `tests/astra_motion/`, `docs/stage3/prereg_astra_motion.md`)은 **검토 대상 아님**(archive에 없음 확인). `git -c core.autocrlf=false archive a4cddad`를 Python tarfile로 `D:\tools\scratch_qdd\r7c23\repo`에 풀었다(**508파일** = 22회차 506 + 스펙 + `r7_cycle22.md`). 파드 사본 = 같은 archive(`/data/harvest/tmp/r7c23/code`, 509파일 = + JSON `CODE_VERSION` `a4cddad3…`, dirty false); 파드 산출 `meta.git.commit` = `a4cddad3a675…`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle7.md`–`r7_cycle22.md`, 정본 `00-interfaces.md` §1–§83 + 끝의 "§82 보충 2"(뒤 절 우선; [사용자] 제목 절은 그대로; 논문 .tex는 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`·`prereg_se2e_temporal.md`·`prereg_se2e_motion_confirm.md`·`M4-overlap-commit.md`.
- 분류(22회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·같은 문서의 뒤 결과와 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 기록이 없는 것. 정본이 "나중에 할 일"로 적은 것(§82 구현, §83 런타임 적용, 확인 실험 결과)은 SCOPED. 연구 문서·설계 초안의 제안 목록·[결정 필요]는 지금의 결정·구조를 틀리게 말하지 않는 한 NOTE. 원문이 맞고 렌더에서만 빠지는 것은 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c23`. 스크립트는 Write 도구로 쓰고 경로로 실행(heredoc·`cat >`·`python -` 없음). **절차상 어긋남(내 쪽, 결과 영향 없음)**: (1) 부동소수 확인 한 줄(`python -c "…0.95*60…"`)과 파드 메타 두 개 출력(`python3 -c`)을 인라인으로 실행, (2) `ctrlscan23.py`는 22회차 스크립트를 PowerShell 문자열 치환으로 복사해 만들었다(Write 도구 아님, LF·BOM 없음) — 규칙 문구("Write 도구로 쓰고 경로로 실행")에서 벗어나므로 기록한다. 파드 업로드 = `tar -cf - | kubectl exec -i … tar -xf -`(파드 스크립트 CR 바이트 0을 세 번 확인), 정리 = `bash -s < clean23.sh`(경로를 하나씩 적음, 열린 핸들 0 확인 뒤). 로컬 pytest basetemp = `…\r7c23\pt`·`pt3`, C: 쓰기 없음(하네스 작업 출력 파일만). 파드 = `juhyoung-native-7a2a`, `/data/harvest/tmp/r7c23`. GPU: Isaac = GPU 1에 **내 프로세스 하나**(`--inst-prefix r7c23`, `IR_INST` `r7c23_standard`, `IR_ROOT=cyclo`; 같은 시각 GPU 0·1의 R2_TRAIN Isaac 워커 — 건드리지 않음), GPU 2·3(확인 실험 motion 칸 학습 중)에는 아무것도 올리지 않음(가드 12·13은 워커 전에 거부). CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`, 한 번에 한 묶음(CPU 시험 → 가드·평가·데이터 → Isaac → se2e_c1 점검 순차). 시드 DEV·POOL만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 요청과 **다른** 값으로만). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. `ckpt/se2e*`·`logs/se2e*`·`data/se2e*`·`r2/dev`·`code_se2e_confirm`는 **읽기만**; 확인 실험 예측 파일(`pred*.jsonl`)은 열지 않았고, 학습 로그의 평가 사건은 **개수만 세고 값은 읽지 않았다**(실험 중간 결과를 보지 않기 위해).

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 1 |
| SCOPED | 20 |
| NOTE | 37 |

코드·사전 등록은 3a3d76c와 바이트가 같고 모든 행동 확인이 통과했다: 로컬 **1014 passed / 15 skipped**(Git Bash; PowerShell에서는 `date` 실행 파일이 없어 2개 실패 — N31), 파드 CPU **1130 passed / 4 skipped**, LeRobot 6 passed; 가드 **26건** 모두 rc 1(21·22회차와 다른 값, `--hb-mode K5`·`K2,K5` 2건 추가); R2 DEV `validate_episode` **36/36** + 음성 대조 2종(행동 한 값 NaN, labels_v2 한 줄 삭제 → 둘 다 검출); 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 모두 완료; 새 시드 **DEV 8**에서 같은 Isaac 워커 C5 → C5' 행동 **1,426개 비트 동일**; 로컬 구성 시험 `check23.py` **53/53**, `verdict23.py` **11/11**, `verdict23b.py` 1/1, `prereg_hash.py --check` OK. se2e_c1은 `SHA256SUMS` 5/5 OK, **22회차와 다른 10편**(RB1 88·268·447·627·716, RB2 107·321·535·749·855)에 등록된 `reconvert --hist`를 다시 돌린 출력이 판 폴더 줄과 바이트 동일(176·94줄), 5행마다 1행(8,563행) 내 코드 후방 차분과 오차 0.0. 확인 실험 motion 두 판의 설정이 등록 §2와 같다.

**정본 §82 보충 2**(실행 중 Astra effort = low, high는 비교·오프라인에서만, Astra–VLA RTC식 보완)는 정본 §26·§82 effort 줄·코드(`astra_hb.EFFORT` = "low", 요청 본문·클라이언트 호출 모두 이 상수, 파드 Astra 행 4/4 effort low)와 어긋나지 않는다. **Astra–VLA 결합 스펙**은 머리에 "초안 — 사용자 검토 전, 구현 전"이 있고, 지금 구조를 말하는 문장(VLA 입력 = 머리 + 활성 손목, labels_v2 = 목표 기준 Δ, `skills.project`, M4 규칙 §72–§75, M5)은 정본·코드와 맞는다 → 제안 내용은 NOTE.

**DOC 1건**: 이번 커밋(a4cddad)이 22회차 보고서를 커밋하고 handoff `:88`을 고쳤지만, handoff가 "회차별 판정·연속 무결 횟수는 §2.8 마지막 줄"(`:3`)이라고 가리키는 그 마지막 줄(`:116`)은 여전히 21회차 FAIL·"22회차는 … 0부터"다 — 커밋된 결과(22회차 PASS, 연속 무결 1)와 다르고 정정 표시가 없다(D-1). 22회차 NOTE N12·N19·N21·N22 정정은 실제로 들어갔다(N12는 handoff 링크, 나머지는 결과 문서 표시; `se2e_data.md:62` 표시는 표 칸 수 때문에 렌더에서 빠짐 — N25). **연속 무결 0으로 돌아감.** 검토 중 HEAD가 문서만 바뀐 커밋 3개(a5816e1까지, 정본 §84·§84 보충 1 = 결합 설계 승인)로 움직였다(N36).

---

## 1. DEFECT

없음.

(검토한 후보와 판단: ① `RuntimeConfig.astra_effort`(`harvest/runtime/core.py:79`)는 `policy_config`에 기록되지만 실제 요청 본문(`:265`)·클라이언트 호출(`:268`)은 상수 `EFFORT`를 쓴다 — 이 필드를 바꾸는 CLI·설정 경로가 없고(`closed.py`에 effort 옵션 없음, 필드 대입 0곳, `check23` S2), 정본 §82 보충 2가 실행 중 = low로 정했으므로 기록과 동작이 어긋나는 실행이 생길 수 없다 → NOTE N28. ② 확인 판정 스크립트가 한 판 파일 안의 **중복 항목 줄**을 받아들인다(2,401항목, rc 0; `verdict23` M7c) — 입력이 `stageb_train predict` 출력이고 등록 판정 규칙·문턱은 그대로 → NOTE N3 확장. ③ 전이·정상 층 부트스트랩 구간은 'all' 층 10,000회 뒤 **같은 난수 흐름을 이어서** 뽑는다(시드 0에서 새로 시작하지 않음; `verdict23b` 재구현 일치) — 판정 규칙은 'all' 하한만 쓰고 그 값은 시드 0 첫 흐름이라 등록과 같다 → NOTE N29.)

## 2. DOC

- **D-1. `docs/handoff.md:3`·`:116`(§2.8 마지막 줄) — 22회차 결과·현재 연속 무결 횟수가 handoff에 없다.** `:3` "마지막 갱신: 2026-09-25 16:08 UTC (… 회차별 판정·연속 무결 횟수는 §2.8 마지막 줄 …)" → `:116`(마지막 줄) = "R7 21회차 … FAIL … 22회차는 새 코드를 포함한 HEAD에서 0부터". 같은 커밋 a4cddad가 `docs/stage3/results/r7_cycle22.md`(판정 PASS, "연속 무결 1회")를 커밋했고 커밋 메시지도 "R7 cycle 22 PASS (clean count 1)"이며, 같은 커밋이 handoff `:88`에 "R7 22회차 N12" 갱신까지 넣었다. 그런데 handoff가 현재 상태의 출처로 지정한 줄은 21회차 상태(연속 무결 0, 22회차 대기)를 말한다 — 다음 세션이 handoff만 읽으면 관문 상태를 틀리게 안다. 앞선 회차는 모두 보고서 커밋과 같은 커밋에 §2.8 줄을 넣었다(`git log -S`: 20회차 줄 = 874cb33, 21회차 줄 = 3611de6). 정정 표시 없음 → DOC(18·19·21회차의 handoff 상태 줄 DOC와 같은 성격; 7회차 N1은 마지막 줄이 맞아서 NOTE였다). 같은 누락: `docs/draft-log.md`(마지막 R7 줄 `:464` = 21회차)·`docs/stage3/direction-log.md`(마지막 행 `:68` = 21회차) — 기록 문서라 N27로 둔다. **고칠 것**: handoff §2.8 끝에 "R7 22회차(2026-09-25 16:45 UTC) PASS(대상 3a3d76c): DEFECT 0, DOC 0, SCOPED 20, NOTE 30 — 연속 무결 1회 …"와 이 23회차 줄, `:3` 갱신 시각; draft-log·direction-log에 같은 줄. 재발 방지: 순회 보고서를 커밋할 때 handoff §2.8 줄을 같은 커밋에 넣는지 확인(21회차 교훈처럼 "보고서 커밋 = handoff 줄" 체크).

(검토했지만 DOC로 올리지 않은 후보: 정본 §82 보충 2 "Astra는 느리지만 과제 흐름·다음 손끝 목표를 알고" — 같은 날 16:33 UTC user-log 83 "목표를 공간에 표현하는 것 조차 안하고"보다 앞선 서술이지만 Astra 능력의 성격 묘사이고 설계는 "탐침 결과로 확정"이라 적어 결정이 아님 → N22. 보충 2가 §83 뒤에 있는 위치 → N21. 스펙 §1·§3·§5·§7의 "목표열·현재 목표" 문장이 머리의 16:33 개정("대체된다")과 어긋남 — 사용자 검토 전 초안의 내부 불일치, 지금 구조를 말하지 않음 → N17. 스펙의 1 Hz 계단식 호출이 정본 §82 호출 정책(편당 1–3회, 5 s 하트비트 강등)과 다름 — 제안, 채택에는 정본 결정 필요 → N18. `se2e_data.md:62` 정정 표시가 표 머리보다 한 칸 많은 칸 → 원문에는 있음 → N25. handoff `:3` 머리 시각 16:08(파일은 16:47 수정) → D-1에 포함.)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드 GPU 0·1 R2_TRAIN Isaac 워커 진행 중(읽기만); 확인 인자 없는 `gen gen --seeds 59999` rc 1(가드 18).
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8(M9 복구·T_fail 뒤 하트비트 정지, A5′ 검사·계약 편집, 확인 헤드 보정 파일 기본 미보정).
- S6. Astra 카나리 "none"(§67 보충).
- S7. S-E2E 계열 체크포인트의 런타임 형식 차이(§77 보충 (2), §80).
- S8. CONTRADICT-soft(§68 K6).
- S9. §73 D5 M4 설계 확장.
- S10. §73 N5 E1 범위.
- S11. §74 보충 E-M4-lat 비례 STALE_MAX.
- S12. §75 보충 (2) E-M4 판정 7.
- S13. §77 N8 (13): 완료 정의 밖 사전 등록 실험.
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — a4cddad에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. **정본 §82 구현**(K5 모드·`harvest/astra/jobs.py`·`closed --upper`·T_nov·계약 캐시·J2 경로·`astra_slot.py`·Qwen3-VL-32B, 유료 실행은 사용자 승인 뒤) 및 **§82 보충 2의 RTC식 결합 설계**(스펙 초안) — "R7 관문 뒤 착수"·"탐침 결과로 확정". 지금 코드: `CADENCES` = K0–K4, "K5"·"1Hz"·"K2 " 거부(`check23` C3), 파드 `closed --hb-mode K5`·`K2,K5` → 워커 전 거부(가드 25·26), `RuntimeConfig()` = ("K2", 5.0), Astra 요청 이미지 = 머리 1장(`check23` S3, 파드 Astra 4행 이미지 해시 1개), 파드 판 `meta.hb_mode` K2·`hb_n` 5.
- S19. **정본 §83 런타임 적용**(새 직렬화 판본·런타임 속도 구간화·보정/카나리 재생성·R2 항목의 같은 줄) — "R7 관문 뒤 착수". a4cddad: `harvest/serialize` 원문에 움직임 줄 없음(`check23` D3), 파드 결정 호출 요청 86/86 `motion:` 없음.
- S20. **§83 확인 실험 결과**(`prereg_se2e_motion_confirm.md`): 파드에서 진행 중 — (single, none) 두 판 학습·예측 끝(드라이버 기록 16:30:56Z·16:31:03Z 학습, 예측 전체 16:36:32Z·16:36:40Z), (single, motion) 두 판 학습 중(17:10:45Z에 스텝 1,760·1,768/2,000). 판정 파일(`verdict_full.json`·`verdict_300.json`)·결과 문서(`se2e_motion_confirm.md`) 없음.

## 4. NOTE
- N1. (그대로) `stageb_train predict`·`evalck`는 체크포인트 `prompt_config`를 자기 옵션과 대조하지 않는다.
- N2. (그대로) `cli_label.replay_max`의 NaN 순서 의존. 읽는 쪽 `replay_bit_identical`은 새 경우(정수 2−2·0.5−0.5 → 신뢰, 1e-15·−inf·"0.0"·0j·`np.int64(0)`·필드 없음 → 불신)도 올바름. `np.int64(0)`을 불신하는 것은 JSON에서 읽은 행에는 생기지 않는 값이라 영향 없음.
- N3. (확장) `temporal_verdict.py`·`motion_confirm_verdict.py`의 입력 검사는 `assert`·`KeyError`·argparse이고, 등록 판정 집합(검증 전체 1,799)을 스크립트가 확인하지 않으며(300 판에도 `verdict.confirmed` 출력), **한 판 파일 안의 중복 항목 줄을 받아들인다**(`verdict23` M7c: 2,401항목 rc 0 — `n_items`가 출력에 남아 읽을 때 구분 가능). 판 이름 중복·판 누락은 rc ≠ 0(M7; 누락은 `--pred nargs=4`의 argparse 오류로 거부 — 메시지는 "--trans required").
- N4. (그대로) Astra 시간 초과 뒤 재송신 모양 — K5 구현 때 정본에 정하기를 권함.
- N5. (그대로) `se2e_diag.md:131` 6절 제안 (a) D2′는 8절로 사실상 수행.
- N6. (그대로) `se2e_diag.md:13` "약 9k까지만" 제한.
- N7. (그대로, 보충 2와 대조) `astra_role_2026-09-25.md:517` "J6 effort high(오프라인)는 [결정 필요]" — 정본 §82 보충 2가 "high는 … 오프라인 일(J1 첫 컴파일 비교, J6)에서만 측정"으로 사실상 정했다. 연구 문서라 NOTE; 다음 정리 때 "→ §82 보충 2" 표시 권함.
- N8. (그대로) `CLAUDE.md:32`(user-log 76 비용 한도 줄) 위치.
- N9. (그대로) `steering_representation_2026-09-25.md:33`·`:81` §82 표시가 GFM 렌더에서 사라짐.
- N10. (그대로) `e05`는 `--out` 폴더를 거부 전에 만든다 — 가드 24(`e05 --split pool --seeds 2119`, P2 → "no episode selected" rc 1)가 빈 `g24/`를 남김.
- N11. (그대로) 카나리 `--force` 같은 날 재실행이 그날 표류 파일을 덮는다.
- N12. (해소) 22회차 N12: handoff `:88`에 탐침 범위 변경(user-log 83)·`prereg_astra_motion.md`("커밋되면")·스펙 링크가 들어갔다. 그 등록 문서는 a4cddad 트리에 아직 없다(미커밋) — "커밋되면"으로 정직하게 적혀 있음.
- N13. (그대로) `draft-log.md:462` "커밋 안 함" 관용 표기.
- N14. (그대로) `prereg_se2e_temporal.md` §7 등록 해시 = 파드 `code_se2e_temporal` 사본.
- N15. (그대로) `e_m4b_meas.md:36`·`:51`은 사전 등록 원문 복사.
- N16. (그대로) `2026-09-25-e2e-ready.md:12`·`:26` "Astra 하트비트"는 지금 실행 계층 서술.
- N17. **스펙 초안 내부 불일치**: 머리 개정(16:33 UTC, `specs/2026-09-26-astra-vla-coupling-design.md:7`)은 "2절 목표 해석기, 4절 목표열, 6절 현재 목표 입력, 9절 P 변형은 대체된다"고 하지만 같은 결과로 바뀌어야 할 `:19`(1절 요약 "다음 손끝 목표들"), `:38`·`:41`(3절 "현재 목표 T_i"), `:89`–`:92`(5절 "Astra 확정 목표"), `:109`(7절 "목표 해석 실패"), `:121`(9절 1 "목표 공간 표현(P-pc / P-plane / P-tri / S)")는 그대로다. 사용자 검토 전 초안이라 NOTE; 승인판(정본 §84, a5816e1)에서 정리됐는지는 24회차가 본다.
- N18. **스펙의 호출 구조 대 정본 §82 호출 정책**: 스펙 3절 "1 Hz 계단식(동시 ≤ 3)"·적응 간격은 정본 §82 `:727` "결정이 바뀔 수 있을 때만 호출. 예상 성공 편 1–3회"·`:726` "5 s 하트비트 강등"과 다르다. 스펙은 §82를 J1–J6·비용 한도 근거로만 인용하고 이 차이를 "정본 결정 필요"로 적지 않았다(10절 열린 결정에 없음). 초안 제안이라 NOTE — 채택 시 정본에 §82 호출 정책을 덮는 절이 필요(a5816e1의 §84가 그 역할인지 24회차 확인).
- N19. 스펙 `:152` "머리 + 양 손목(252 + 104 + 104 = 460)" 대 정본 §59 `:515` "양팔 스킬 약 466"(이미지 표지 토큰 포함 여부 차이로 보임) — 수치 근거 한 줄 권함. `:115` "low 1회 ≈ $0.02(Task C 기록 기준 추정)"은 이 저장소에서 원자료를 확인하지 못함(추정으로 표시됨). `:159` "MolmoAct ICRA 2026"은 연구 문서 `steering_representation:219`(OpenReview 기록)와 같음.
- N20. (그대로, 22회차 N20) `se2e_temporal.md` §5 표의 분 단위 반올림.
- N21. **정본 §82 보충 2의 위치**: "§82 보충 2"가 §83 뒤(`00-interfaces.md:741`, 파일 끝)에 붙어 있다. 시각(16:17 UTC)이 §83(15:40 UTC)보다 뒤라 "뒤 절 우선" 규칙과 충돌은 없고, 내용이 §83과 겹치지 않는다. 찾기 쉽게 §82 끝으로 옮기거나 "(§83 뒤에 적음)" 표시 권함.
- N22. **보충 2 대 user-log 83 뒤 발언**: 보충 2(16:17 UTC)는 "Astra는 … 다음 손끝 목표를 알고"라고 적었고, user-log 83의 16:33 UTC 선택("네, 일반 조종법만" — 목표를 공간에 표현하지 않음)은 정본에 없다(스펙 머리 개정에만). 보충 2는 성격 묘사이고 "설계는 … 탐침 결과로 확정"이라 결정 충돌은 아니다. (a5816e1 §84가 이를 정본에 넣었는지는 24회차.)
- N23. (그대로) **파드 확인 실험 사본의 CRLF**: 등록 §5 무수정 해시 3개 = CRLF 사본 해시. 이번 확인: 네 판 `CODE_HASHES` 등록값 6/6, 사본의 `harvest/`·`tools/`·`tests/` 265파일 LF 내용 = a4cddad(차이 0; 다른 것은 `docs/` 14·`paper/` 20·`CODE_VERSION`뿐 — `conf23b.py`).
- N24. (그대로) 등록 §3 "(none) 칸끼리·(motion) 칸끼리의 시드 간 정확도 차"는 판정 스크립트 출력에 따로 없음(`runs` 칸별 값으로 계산 가능).
- N25. **`se2e_data.md:62` 정정 표시가 렌더에서 빠짐**: 3칸 표(`:56` 머리 `| 필드 | 값 | 비고 |`)에 22회차 N21 표시를 네 번째 칸으로 붙였다(`split('|')` 결과 머리·행 모두 5조각이나 행은 끝 파이프가 없어 4칸) → GFM은 머리보다 많은 칸을 버리므로 표시가 보이지 않는다(원문에는 있음, N9와 같은 모양). 비고 칸 안으로 옮기기 권함. `:96`·`se2e_temporal.md:81` 표시는 보임.
- N26. (그대로) 등록 고정 시점: 등록 머리 15:52:12Z < none 판 드라이버 15:53:07Z < 커밋 44c907d 15:53:42Z < 첫 학습 스텝 15:54:13Z; motion 판 `CODE_HASHES` 16:36:32Z·16:36:40Z, 첫 스텝 16:37:41Z·16:37:49Z — 모두 등록 뒤.
- N27. `draft-log.md`(마지막 R7 줄 `:464` = 21회차)·`direction-log.md`(마지막 행 `:68` = 21회차)에 22회차 줄이 없다 — 기록 문서라 NOTE; D-1과 함께 넣기 권함.
- N28. `RuntimeConfig.astra_effort`(`core.py:79`)는 기록용이고 실제 호출은 상수 `EFFORT`(`:265`, `:268`, `:413`) — 정본 §82 보충 2(실행 중 low)와 맞고 바꿀 경로가 없다(§1 후보 ①). 정본 §82·E-first의 high 비교 조건을 런타임 경로로 돌릴 때(E-Astra-necessity 폐루프) 필드를 호출에 연결하고 시험을 권함.
- N29. `motion_confirm_verdict.bootstrap`은 세 층을 **한 `default_rng(0)` 흐름으로 차례로** 뽑는다(`tools/se2e/motion_confirm_verdict.py:47-60`): 'all' = 시드 0 첫 10,000회(등록 §3 그대로, 판정에 쓰임), 전이·정상 = 그 뒤 흐름. 등록 원문만 보고 층마다 시드 0으로 새로 뽑는 재구현은 전이 구간이 약 3e-4 다르다(`verdict23` M5: 도구 [0.027325, 0.039667] 대 새 시드 [0.027000, 0.039667]; 이어진 흐름 재구현은 세 층 모두 오차 0 — `verdict23b`). 보고 항목뿐이라 NOTE; 결과 문서에 한 줄 권함.
- N30. (읽기 도움) 로컬 B9 첫 시도에서 내 기대값(1..60 ms 전체의 p95 = 57 ms)이 틀렸다 — `CommitLedger.d_hat`은 **최근 50회**(`M4Params.d_window` 50, `m4.py:92`, `:154`)의 p95이고 이는 M4 `:263` "최근 50회 지연의 p95로 실행 중 갱신"과 같다. 기대값을 등록대로 고쳐(11..60 → 48번째 58 ms, 1..50 → 48 ms, 1..51 → 49 ms) 통과.
- N31. **로컬 시험의 셸 의존**: PowerShell에서 돌린 첫 로컬 묶음은 2 failed(`tests/test_cli_e0.py::test_main_writes_session_and_summary`, `tests/test_load.py::test_run_session_writes_header_curl_and_all_phases`) — `harvest/load/session.py:15` `_tz()`가 외부 `date` 실행 파일을 부르는데 Windows PowerShell PATH에는 없다(`FileNotFoundError`). 같은 archive를 Git Bash에서 돌리면 1014 passed(22회차와 같은 환경). 코드 무변경(54bb2da부터)·파드 통과라 NOTE; 파이썬 `datetime`으로 바꾸면 셸 무관해진다.
- N32. 시험 수: 로컬 **1014 passed / 15 skipped**(147.1 s, Git Bash), 파드 CPU **1130 passed / 4 skipped**(119.9 s, 17:00:55Z 끝), LeRobot 6 passed(18.9 s). 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다.
- N33. 단계 B 소형 CPU 스모크(17:04 UTC): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21·22회차와 같은 값 — 결정적), expert p50 0.091 s·전체 p50 0.199 s(CPU, 참고).
- N34. DEV 8 판은 22회차 DEV 17 판과 길이가 같다(행동 1,426·14.26 s·호출 43) — 모의 선택기·스크립트 계획기의 단계 시각이 같아서이고, 내용은 다르다(`last_step` 분포 {none 1, OK 31, LAG 8, DEVIATE 3} 대 {1, 33, 5, 4}, 확정 비율 0.9273 대 0.9045). 파일명 `dev8-P0-standard-e0`.
- N35. user-log 84(MolmoAct 깊이 참조)는 a4cddad에서 user-log에만 있다(handoff·계획에 할 일 없음) — 이후 2b7ba25(`docs/research/molmoact_deepdive_2026-09-26.md`)로 반영됨.
- N36. 검토 중 HEAD가 **a5816e1**로 움직였다(2b7ba25 MolmoAct 연구 문서, c915535 "canon §84 + spec §14: coupling design approved, E-MA1 approved, falsify-first decided", a5816e1 "canon §84 supp 1 + spec §15") — `git diff --stat a4cddad a5816e1` = `00-interfaces.md` +12, 스펙 +23, 새 연구 문서 +321, `user-log.md` +5, **코드 변경 없음**, handoff 변경 없음(D-1 그대로). 이 보고서는 a4cddad만 판정한다.
- N37. 파드 상태 목록(`setup23.sh`)의 `ls --time-style=+%FT%TZ`는 파드 현지 시각(KST)에 문자 "Z"를 붙여 찍었다(내 스크립트 실수) — 이 보고서의 확인 실험 시각은 드라이버·학습 로그의 UTC 값만 인용했다.

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**(`check23` H1), 파드 산출 `meta.prereg.check` = "OK"(closed). 코드 줄은 a4cddad 기준(3a3d76c와 블롭 동일). "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c23\check23.py`(A–H·S·V·R, 53/53), `verdict23.py`(M1–M8, 11/11), `verdict23b.py`, `ctrlscan23.py`; **파드** = §6(`pod_cpu23.sh`, `pod_eval23.sh`, `data23.py`, `pod_isaac23.sh`, `closed23.py`, `c1_23.sh`·`c1rows23.py`, `conf23.py`·`conf23b.py`). "시험 묶음" = 해당 구현을 부르는 저장소 시험이 로컬 1014·파드 1130 묶음에서 통과. 모든 경계값은 21·22회차와 다르게 새로 골랐다.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149(TEST2 1150–1299) / TEST-P5 1300–1329 / POOL 2000–2119 / R2_TRAIN 10000–59999 (E :113-120, §66) | `eval/splits.py`, `datagen/gen.py` | 로컬 A1 새 경계 24값(2·15·27/32·497·502·530·547/552·1002·1100·1147/1152·1298·1302·1327/1332·1998·2002·2117/2122·9998·12345·−3) 모두 기대 분할, A2 `test` env 없음·`test_p5`·`cal` 거부/`test` 통과, `cal`에 `test` 거부, A3 "Pool"·"dev "·"r2_train"·"TEST"·"test2" 거부, A4 [27, 32]·[2002, 1998] 통째 거부·문자열 시드 수용(["2", 27], [2117, "2002"]), A6 R2 가드 12경우(2·27 무확인 허용, 32·60003·2050·530·1100·9998·1310 거부, 10002·59990 확인 시만), A7 10060·59940·30000 eval, 10061·59941·12345 fit; 파드 가드 26건 rc 1(§6.4) | 일치 |
| 2 | POOL 120 × 10, 경계 30 % 과표집 (E :121, §76 D-2) | `sim/snapshot.py:29-31` | 코드 무변경, 시험 묶음 | 일치(주석 S14) |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` | 시험 묶음 | 일치 |
| 4 | 분할 = 에피소드 (E :122) | `stagea_data.split_of`, `calib.halves` | 시험 묶음; 파드 `CALIB_DONE` | 일치 |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py`, `config.py` | 시험 묶음; 파드 Isaac **DEV 8** C5·C5' 성공(14.26 s, `terminations` success 1) | 일치 |
| **6** | 호출 기록: 질문별 확률·요청/응답 원문(E :125), Astra A6(E :126, §28) | `core.py` | **파드 DEV 8 C5·C5' 결정 호출 86행**: `sha256(request_blob)` = `request_sha256` 86/86, 이미지 해시가 요청 본문에 86/86, 응답 blob 해시 86/86, `probs` 질문 = `answers` 질문·합 1·[0,1] 86/86, `canary_id` 86/86, `question_id@vN` 86/86; Astra 4행: 요청 해시·머리캠 JPEG 해시·effort low(행·요청 본문 모두)·600·`output_text` 4/4 | 일치 |
| **7** | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `analysis/stats.py` | 로컬 E3 일반 경로 = 군집 합 경로(새 43군집·seed 11), **E4 군집 안 행 1배 대 6배 → 구간 동일**; 파드 closed `meta.bootstrap` n_boot 10000·seed 0·percentile | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate`, `stats.cluster_diff_ci` | 파드 C5 대 C5' 같은 워커 | 일치 |
| **9–12** | 판정 2 Holm, 판정 10, 카나리 Holm, 판정 절 해시 (E :131, :265, :139, :133) | `stats.holm`, `canary.py`, `eval/common.py` | 로컬 E5 **네 가설을 정확한 문턱값에**: (0.0125, 0.05/3, 0.025, 0.05) → 모두 기각(≤, CMP_EPS), (0.0125, 0.017, 0.02, 0.05) → 둘째 0.017 > 0.05/3에서 멈춤(입력 순서 뒤집어 줌), 세 가설 (0.0125, 0.0126, 0.9) → 앞 둘 기각·0.9 유지; `meta.prereg` OK | 일치 |
| **13, 85** | 카나리 기준일 = 같은 세트 × 같은 `question_id@vN` 집합의 첫날 (E :136-140, §79 D2) | `eval/canary.py` | 로컬 G1: 세트 없는 실행 건너뜀, **상위 집합 맵은 다른 사슬**(r1), 키 순서만 다른 같은 맵 → 첫 실행 r2, 부분 맵 → None | 일치(N11) |
| 14 | 모델 식별 필드가 바뀌어도 같은 처리 (E :139) | `Calibration.load`, `latest_canary` | 시험 묶음(코드 무변경) | 일치 |
| 15–17 | E0.5 표·재시험·같은 시각 K = 3 (E :236-238) | `e05.py` | 시험 묶음; 파드 `e05 --data jsel_dev/P1 --split dev --episodes 3` → `E05_DONE` | 일치 |
| **18** | γ 2/3 (E :240, M4 :276) | `m4.share_at_least` | 로컬 B1 새 비율(8/12·14/21·2000/3000·10/15 참, 1999/3000·7/11·3/5·0/1 거짓) | 일치 |
| 19–20 | `C_flip` 두 식, A0–A4·층 (E :242, :246) | `e05.py` | 시험 묶음 | 정본 기록(§73) / 일치 |
| **21–28** | 판정 1–10 경계 (E :256-265) | `replay.judge_e05`, `stats.at_least/below` | 로컬 E1 CMP_EPS: `at_least(0.1+0.2, 0.3)` 참, `below(0.3, 0.1+0.2)` 거짓, `at_least(0.07−2e-9, 0.07)` 거짓·`below(같은 값)` 참; 파드 `E05_DONE` | 일치 |
| 29, 89 | FLIP_TH 후보 α 0.01·범위 (E :253, :487; M4 :285) | `e05.py` | 시험 묶음 | 일치 |
| 30 | 같은 시각 뒤집힘 성공·섭동 따로 (E :253, §27) | `e05.py` | 시험 묶음 | 일치 |
| 31–33 | d_p95 = E0 값, 분당 400 [가정], E1 반분 | `M4Params.d_p95_init`, `calib.halves` | 시험 묶음; d̂ 이동 창은 행 45 | 정본 기록 |
| 34–35 | ECE 15 동일 질량, 오답 < 30 판정 불가 (E :320) | `calibration.ece_mass` | 로컬 E6(450예측·15구간 → [0, 1] 안) | 일치 |
| **36** | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat` | 로컬 E2 새 n(유리수 기준값과 대조): 59·α 0.05 → 57, 19·0.05 → 19, 79·α 0.025 → 78, 38 → inf, 39 → 39, 29·α 0.1 → 27 | 일치 |
| 37–43 | log p 자름·질문별 온도·원 확률·판정 1·7·8·`ambiguous` ECE 제외 (E :333-346) | `calibration.py`, `core.py` | 시험 묶음; 파드 `calib --heldout jsel_dev/P1 --episodes 3` → `CALIB_DONE` | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| **45** | N_max = ⌈d̂/T_c⌉+1, d̂ = 최근 50회 p95 (M4 :258, :263) | `m4.CommitLedger.n_max`, `d_hat`, `d_window` 50 | 로컬 B9: d̂ 1.32 → 5(정확히 4.0 경계), 1.3201 → 6; **창 50**: 1..60 ms → 58 ms(11..60의 48번째), 1..50 → 48 ms, 1..51 → 49 ms(N30) | 일치 |
| 46–49 | γ·W·비가역 W+1·τ | `m4.py` | 시험 묶음; B8 기본값 | 일치 |
| 50 | conformal α 0.01·w 5 ((b) 경계) | 확인 헤드 보정 파일 | 기본 미보정 | SCOPED S5 |
| **51** | STALE_MAX 1.5 s (E :487) | `m4.older_than` | 로컬 B3: **400 Hz** 틱 위치 1,300곳 모두에서 600틱 유지·601틱 버림, B4 +9e-10 유지·+1.1e-9 버림(T_EPS 1e-9 바로 양쪽) | 일치 |
| 52–53 | C2 = VLM Stream, C0–C6 설정 (M4 :329-345) | `conditions.py`, `m4.py` | 파드 `--conditions "C5,C5''"` → "refused before any worker"(가드 15) | 일치 |
| **54** | C5 = §4.2 전체, C5' = (b) 범주 뺌(줄은 none), 판정 3 (M4 :155, :232, :340-342, :361; §77 보충 (3)) | `core.b_line`, `core._boundary` | **파드 Isaac DEV 8**: C5 `last_step` {none 1, OK 31, LAG 8, DEVIATE 3}, C5' none 43/43, 요청 본문 마지막 `last_step:` 줄 = 행 값 86/86 | 일치 |
| 55 | H 1과 3 (정본 §2, M4 :188-189) | `m4.early_ask_steps`, `M4Params.H` | 로컬 B8 기본 H 3; 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 |
| **56–58** | n_LA 2·조기 호출 당겨 씀·FLIP_TH 끔; H = 1 = 같은 스텝 앞당겨 2~3회 (§75) | `m4.py`, `core.py` | 로컬 B5 다섯 창을 **정확한 유리수 창과 대조**: (0.5, 0.33, 0.33, 1.65) → [3..6](양 끝 포함, 6·0.33 = 1.98 = 0.5+1.65 정확 경계), (0.2, 0.46, 0.33, 0.99) → [2, 3], (0.33, 0.0, 0.33, 0.33) → [1, 2](d = 0), (2.0, 0.1, 0.33, 0.25) → [7](창 빔), (1.32, 0.99, 0.33, 0.99) → [7](창 한 점); B8 n_LA 2·FLIP_TH None | 일치 |
| 59 | 경계 직후 W 2·γ 1.0 등 | 없음 | §73 D5 | SCOPED S9 |
| **60** | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.select_rule` | 로컬 E7: 차 정확히 0.02(0.60 대 0.62) → plan, 0.6201 → time0.33, 오라클 정확히 0.90 단독 → plan(적격), 0.8999 단독 → None | 일치 |
| 61–62 | 폐루프 RD 재표집 = layout 짝, 주 RD = Score (EVAL :182-184) | `closed.py`, `rd.py` | 파드 `rd --variants standard=jsel_dev,random=gen_dev/random/P0 --episodes 3` → `RD_DONE` | 일치 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | §71 보충 | SCOPED S1 |
| 64–65 | M4b 2,000회, E-M4-lat 비례 STALE_MAX | `m4b/*` / 없음 | §72 예외 / §74 보충 | 일치 / SCOPED S11 |
| **66–67** | H = 1 창·`lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 파드 `--m4-lead-max 0` 거부(가드 14); 로컬 B8 기본 1.0 | 일치 |
| 68 | E0 판정 4 | `analysis/latency.py` | 시험 묶음 | 일치 |
| 69 | E-M4 판정 7 | 없음 | §75 보충 (2) | SCOPED S12 |
| 70 | FROZEN = 송신 시각 기준 (M4 :150) | `m4.py` | §77 N3 | 정본 기록 |
| 71, 93 | 카나리 표류 → J5 끔, 재보정 뒤 재사용 (E :139, :347, §77 N6, §79 D3) | `closed.j5_after_canary`, `canary.latest_canary` | 시험 묶음(코드 무변경) | 일치(N11) |
| 72–76 | 응답 모델 필드·재시도 기록, E0.5 정답, `fine_dir`, Astra 카나리 | `models`, `common` | §77 N4·N5, §67 보충; 파드 결정 호출 `canary_id` 86/86 | 일치 / SCOPED S13·S6 |
| 77–79 | (b) 범주 줄·런타임 값·경계 틱 호출 = 방금 끝난 스텝 (M4 :232, §77, §79 N1) | `core.b_line`, `core.act` | 행 54; 시험 묶음 | 일치 |
| **80–84** | 학습 자료 값·C5' none·ser-A-min-2·옛 체크포인트 거부 (§77 (iv), §77 보충 (1)) | `serialize.with_last_step` | 로컬 D2 `LAST_STEP_VALUES` 닫힌 집합, "ok"·"DEVIATE\n"·"" 거부·"LAG" 수용 | 일치 |
| 86–88 | 결정 호출 행 `probs`·blob·`last_step`, Astra 원응답, 결정 이미지는 해시만 | `core.py`, `reqhash.request_body` | 행 6 | 일치 / 정본 기록 |
| 90 | FLIP_TH = 성공 실행 flip_score의 1−α 분위, 질문별 (M4 :287, §79 D1) | `e05.flip_th_conformal` | 시험 묶음(같은 순위 규칙 = 행 36) | 일치 |
| 91–92 | 같은 시각 뒤집힘 성공·섭동, 층별 A0 대비 flip | `e05.py` | 시험 묶음 | 일치 |
| 94 | E0 판정 4 집계 (§77 N7) | `latency.step_votes`, `judgment4` | 시험 묶음 | 일치 |
| 95–97, 105, 115–117, 119 | S-E2E 설정·판정 (a)–(e)·재개·evalck·판정 스크립트 입력 검사·고정본 (`prereg_se2e.md` §3·§4, §77 보충 2, §80 N1) | `tools/se2e/se2e_verdict.py` | 코드·로그 무변경(3a3d76c 대비 블롭 동일); 시험 묶음 | 일치 |
| **98** | 라벨 복원 기준(비트 동일, §78 (1)) | `stagea_data.replay_bit_identical` | 로컬 D1 새 8경우(N2) | 일치(N2) |
| **99** | 에피소드마다 PhysX 장면 재생성, 모든 호출자 기본 (§78 결정) | `sim/scene.py` | **파드 Isaac 한 워커 C5 → C5'(DEV 8, 모의 선택기, 17:04:38–17:09:16 UTC)**: 행동 **1,426개 비트 동일**(첫 차이 없음, 행동 시각열 동일), 호출 43개·Astra 2개 같은 수·같은 시각, `code_sha` `a2a7c8394ad45fd6` | 일치(행렬 S16) |
| 100, 118, 132 | 라벨 신뢰 = 재생 비트 동일, 뺀 수와 질문 범위 기록 (§78 (1), §80 D1, §81 N3) | `eval/common.load_truth` | 파드 `e05 --split pool --seeds 2003,2047,2101 --truth outcome:plan` → rc 0, `E05_DONE` | 일치 |
| 101 | R2_TRAIN은 하드 리셋 빌드, 옛 녹화 처리 보류 (§78 (2)(3)) | 파드 실행(읽기만) | GPU 0·1 R2_TRAIN Isaac 워커 진행 중 | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 선택 거부, `determinism` 시드 검사가 `--out` 앞 (§79 N5, §80 N3) | `eval/common.load_episodes`, `sim/determinism.py` | 가드 21(`fresh --seed 2120`)·22(`history --seeds 1000`) → "only DEV 0-29 and POOL" rc 1·폴더 없음, 가드 23(`canary build-set --seeds 500-501`)·24(`e05 --split pool --seeds 2119`) → "no episode selected" | 일치(e05 폴더 N10) |
| 103 | Isaac 워커 `OMP_WAIT_POLICY=PASSIVE` (§79) | `closed.worker_cmd` | 내 Isaac 워커가 이 명령으로 돌아 `CLOSED_DONE`; `--isaac-gpu 2`·`3` rc 1(가드 12·13) | 일치 |
| 104 | e05 qid 등록부 기본 = `<out>` (§79) | `e05.py` | 시험 묶음 | 일치 |
| 106–114, 133–136 | S-E2E 진단 D1–D3·§7 규모 곡선 (`prereg_se2e_diag.md`) | 파드 고정 사본, `se2e_diag.md` | 코드·로그·문서 불변(3a3d76c 대비) | 일치(N5·N6) |
| 121–129 | E-TC(`prereg_se2e_temporal.md` §2–§8): 옵션 끔 = 기준, V 구성, M 구간·드롭아웃, 지표·층, 채택 규칙, 판정 재현 | `se2e_temporal.py`, `temporal_verdict.py` | `temporal_verdict.py` `992d3e20…` = 등록(`check23` H2); 로컬 F1 Δ 0.3 s: 30 Hz k 5·9·20 → 0·0·11, 10 Hz k 2 → 0; **F2a 팔 구간을 관절 속도 노름으로**(두 관절 3-4-5 분할: 하한×0.999999 still·×1.000001 slow·상한×0.999999 slow·×1.000001 fast·0 still), F2b 그리퍼 1.00001배 opening/closing·0.99999배·0 still, F3 30 Hz [2, −1, −1, 3.5, 3, 0] → [0, −90, 0, 135, −15, −90], F4 40,000표본 0.3·(스텝, 시드) 난수·다른 시드 다름·전역 불변 | 일치(N14·N20) |
| 130–131 | §81 N2 재개 검사 키, §81 N10 라벨 쓰기 null | `stageb_train.py`, `cli_label.replay_max` | 파드 시험 통과 | 일치(N2) |
| **137** | Astra 호출 주기 = 하트비트(응답 + N, N = 5 s) + 단계 경계 + 사건, in-flight 1, 15 s → 재송신, gpt-6-astra·low·600 (§45; 실행 중 low = §82 보충 2) | `runtime/astra_hb.py`, `core.py` | 로컬 C1 송신 3.0 뒤 3.5 없음(진행 중), 응답 7.25 뒤 12.2499 없음·12.25 hb, C2 송신 12.25 → 27.25 유지·27.2500001 초과, C4 모델·effort·600; **파드 판 Astra: hb 5.0 → 8.0, 경계 sub 8.01 → 11.01**(종료 14.26 전 다음 hb 없음) | 일치(N4) |
| 138 | LeRobot v2.1 내보내기 = ROBOTIS 형식(§63), 30 Hz·원본 해상도·관절 행동(§66) | `datagen/lerobot_export.py` | **파드 새 2편**(dr/bottle_tray ep1 = `valid_for_training` 거짓 → 건너뜀, standard/mug_marker ep5) `export` → 1편·288프레임, `verify` 오류 0·PSNR 최소 39.09 dB·lerobot 0.3.3 적재 288프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참; LeRobot 시험 6 passed | 일치 |
| 139 | R2 DEV 구조 검사(§66, 완료 정의 1) | `datagen/validate.py` | 파드 `/data/harvest/r2/dev/*/*/P0` 전 편 **36/36 오류 없음**(6폴더 × 6), `valid_for_training` 메타 불일치 0; **음성 대조 2종**(standard/bottle_tray ep4): 무수정 사본 오류 0, `action` 한 값 NaN → "npz action: length 360 (want 360) or non-finite", `labels_v2` 끝 한 줄 삭제 → "labels_v2 rows != decision frames" | 일치 |
| **140** | 정본 §82: 강등·J1–J6·K5 모드 등은 "구현(다음)·R7 관문 뒤" | 없음(현 구현 = §45 K0–K4) | 로컬 C3·C5, 파드 가드 25·26 | SCOPED S18 |
| **141** | 정본 §83: 움직임 줄 채택·V 불채택; 누수 수정·확인 실험·런타임 적용은 다음 일 | 누수 수정·확인 등록 = 행 142–150; 런타임 없음 | `check23` D3, 파드 요청 86/86 `motion:` 없음 | 일치 / SCOPED S19·S20 |
| **142** | 속도 누수 수정: v[k] = (x[k] − x[k−1]) × 10 Hz, v[0] = 0, = `backward_velocity` (`prereg_se2e_motion_confirm.md:10`) | `harvest/train/se2e_data.py:134-140`, `:185` | 로컬 V1 47×16 무작위 보행에서 손 계산과 비트 동일, V2 모든 k에서 `backward_velocity`와 비트 동일, V3 k = 2·11·23·45 뒤 모든 프레임을 −7x+3으로 바꿔도 0..k 행 불변, V4 2프레임 → [0, 차분·hz], V6 15 Hz = 1.5배, V7 `episode_rows`(RB1, 보폭 4) 행마다 자기 팔 후방 차분·k = 0 행 0; **파드 `c1rows23`: 5행마다 1행(RB1 5,087·RB2 3,476) 원본 parquet에서 내 코드로 계산한 후방 차분과 일치(최대 오차 0.0), 나머지 필드 = 옛 행** | 일치 |
| **143** | 재변환: qd·grip[1] 외 모든 필드가 같지 않으면 멈춤, `hist_fields` 추가, 현재 프레임은 링크 (`:11`) | `tools/se2e_convert.py:241-337` | 로컬 R1 속도만 바뀐 새 행 수용·나머지 = 옛 행(이미지·회전 포함), **R2 새 11종 변경 거부**(k, hz, `action_exec` 마지막 −1e-14, valid 마지막, q ×(1+1e-13), tau 길이, grip 길이, proprio 새 키, labels_src, task, kind), R3 옛 행 여분 필드·두 행 순서 바꿈·한 행 추가 거부, R5 `--hist` 행, R6 `--conv`가 `--src` 두 단계 아래·`--src` 부모 아래 형제·끝 구분자 붙은 `--src` = `--conv` → rc 1, 기존 출력 "exists" rc 1·파일 불변; **파드: 등록된 `reconvert --hist`를 22회차와 다른 10편에 다시 돌린 출력이 `se2e_c1` 같은 줄과 바이트 동일(176·94줄)** | 일치(`KEEP_FROM_OLD` 설계 메모는 22회차 N25 그대로) |
| **144** | 판본 `se2e_c1` 표 (`:12-23`) | 파드 `/data/harvest/data/se2e_c1`(읽기만) | `sha256sum -c SHA256SUMS.txt` **5/5 OK**(RB1·RB2 행 파일·`motion_bins.json`·`transition_val.json`·`reconvert.json`) — 22회차 확인 뒤 불변 | 일치 |
| **145** | 분할·키 불변: train 37,484 / val 1,799, 결정 프롬프트 입력 불변 (`:22`, `:24`) | `se2e_data.load_se2e`, `stageb_train.stratified_val` | 파드 네 판 학습 로그 `config`: `n_train` 37,484·`n_val` 1,799(4/4); 로더 코드 블롭·데이터 sha 불변(행 144) | 일치 |
| **146** | 설계: (single, none)·(single, motion) × 시드 1·2, 2,000스텝·묶음 8·lr 1e-4/1e-4·워밍업 3 % + 코사인·검증 300(150/0)·500마다 평가, motion 칸 `--motion-line se2e-motion@v1 --motion-bins se2e_c1/motion_bins.json`·드롭아웃 0.3 (`:26-31`) | 파드 `logs/se2e_confirm/run.sh`, 판 로그 `config` | **`conf23`(22회차 뒤 시작한 motion 두 판 포함)**: motion_s1·s2 `config` = 묶음 8·`max_steps` 2000·lr 1e-4·`lr_heads` 1e-4·시드 1/2·`val_per_kind` 150·`val_seed` 0·`eval_every` 500·**`motion_line` se2e-motion@v1·`motion_bins` `/data/harvest/data/se2e_c1/motion_bins.json`·`motion_dropout` 0.3**·`se2e_root` = `se2e_c1/conv`·cosine·부분집합 없음·`init_weights`/`resume` 빈 값·IMG·KI stop; `prompt_config` sha motion `7d1cf93de7b5`(옵션 해시에 `se2e_data.py` 포함 = 등록 §5 "새 판 표지") 대 none `6ee05d18ad30`; lr 네 판 모두 워밍업 60 + 코사인과 최대 차 8.1e-4 × 1e-4(스텝 2 = 5e-6, 60 = 1e-4, 500 = 8.78e-5); 드라이버 motion 시작 16:36:32Z(GPU 3)·16:36:41Z(GPU 2) | 일치 / 판정은 SCOPED S20 |
| **147** | 지표·판정: e_s, 합동 = ½(e_1 + e_2), 스냅샷 군집 부트스트랩(네 판 같은 추출, 10,000, 시드 0, 95 %); 확인됨 ⇔ 합동 ≥ +0.015 ∧ 하한 > 0(엄격) ∧ 합동 전이 ≥ −0.01, CMP_EPS 1e-12 (`:33-42`) | `tools/se2e/motion_confirm_verdict.py:27-28,32-67,90-93` | **로컬 `verdict23` 11/11**(스냅샷 800 = 전이 500·정상 300, 2,400항목, 보기 3개): M1 e 24·48/2400(정상 행만) → 합동 정확히 +0.015·전이 정확히 0 → 확인됨, M1c 71/4800 → 거짓; M2 **시드마다 다른** 전이 손실 −10·−20/1500 → 합동 정확히 −0.01 → 참, −31/3000 → 거짓(전체 +0.077이어도 확인 안 됨); M3 같은 네 판 → 하한 정확히 0 → 거짓, 손실 → 합동 −0.0125; M4 기준선이 다른 두 시드 0.025·0.045 → 합동 0.035·변동 +0.02, 교환 → 합동·구간 같고 변동 부호만; **M5 내 재구현 = 'all' 구간(오차 0)**, 전이 구간은 이어진 흐름(N29, `verdict23b` 세 층 오차 0); M6 1,799 입력 `n_val_snapshots`·`label`·`rule` 기록; M7 판 이름 중복·판 누락 rc ≠ 0(중복 항목은 N3); M8 acc = 항목 평균·NLL = 3보기 −log p | 일치(N3·N24·N29) |
| **148** | 판정 스크립트 해시 `fa7299062cc5e1d1`·코드 해시 (`:42`, `:47-48`) | 파드 `code_se2e_confirm`, 판 `CODE_HASHES.txt` | 로컬 H2 = archive 블롭; 파드 네 판 `CODE_HASHES` 등록값 6/6(4/4), 사본 `harvest/`·`tools/`·`tests/` LF 내용 = a4cddad(차이 0) | 일치(N23) |
| **149** | 등록은 어느 판도 학습하기 전; 결과 뒤 문턱·층·검증 집합·구간값 불변 (`:1-3`, `:5-7`) | 커밋·로그 시각 | N26; a4cddad까지 등록 문서·판정 스크립트 변경 없음; 판정 파일 아직 없음 | 일치(N26) |
| 150 | 하지 않는 것: `se2e`·`se2e_t` 덮어쓰기, `PROMPT_FILES`·`stageb_data`·`stageb_model`·`harvest/runtime` 수정, GPU 0·1, 유료 API, CAL/TEST (`:52-53`) | 파드 실행 | 옛 `se2e/conv` 행이 `c1rows23`·재변환의 원본으로 온전(재변환 출력 = 판 폴더 줄), 판 GPU 2·3(드라이버 기록), 사본의 `harvest/runtime` 등 = a4cddad | 일치 |
| **151** | **정본 §82 보충 2: 실행 중 Astra effort = low, high는 실시간 경로에서 쓰지 않고 비교 실험·오프라인 일(J1 첫 컴파일 비교, J6)에서만 (`00-interfaces.md:741`)** | `astra_hb.py:33` `EFFORT` "low", `core.py:265`·`:268`·`:413`, `RuntimeConfig.astra_effort` `:79` | 로컬 S1 요청 본문 `"effort": EFFORT`·클라이언트 `astra.call(inp, EFFORT, …)`·기본 low, S2 effort를 바꾸는 CLI·설정 경로 없음, C4; **파드 Astra 4행: 행 effort low·요청 본문 `"effort": "low"` 4/4**; 정본 §26·§82 `:728`·E-first `:11`·`:388`(high는 비교 조건)과 문장 충돌 없음(§6.2) | 일치(N28) |
| 152 | Astra–VLA 결합 스펙(초안, 사용자 검토 전) — 1 Hz 계단식·두 층 M4·세 카메라·덧그림·E-CAM3·E-TRACE | 없음 | 로컬 S3 Astra 요청 이미지 1장(머리), C3 1 Hz 모드 없음; 스펙의 현재 구조 서술(§57·§59 머리 + 활성 손목, labels_v2 목표 기준 Δ `labels_v2.py:4`, `skills.project` `runtime/skills.py:55`, M4 §72–§75, M5)은 코드·정본과 같음 | NOTE(N17–N19) / SCOPED S18 |

### 5.1 22회차 표와의 차이
- 새 행 151(정본 §82 보충 2)·152(결합 스펙 초안). 판정 변화 없음(모두 일치·SCOPED·NOTE). 근거 교체: 행 1(새 경계 24값·R2 12경우·새 가드 26건), 5·6·54·99·137(새 시드 DEV 8, 86행, 행동 1,426개), 7(1배 대 6배), 9–12(네 가설 정확한 문턱), 13(상위 집합·키 순서), 36·45(창 50 확인)·51(400 Hz)·56–58·60(새 경계값·유리수 기준), 121–129(노름 분할 입력·30 Hz), 138(무효 편 건너뜀 + 다른 편), 139(음성 대조 2종), 142–148(22회차와 다른 재변환 10편·표본 행·motion 판 설정). 행 145는 로더 재실행 대신 네 판 학습 로그의 `n_train`/`n_val`과 데이터 sha 불변으로 확인했다.

## 6. 확인한 것 (근거)

### 6.1 변경분·22회차 정정 확인 (과제 1·2)
- `git diff 3a3d76c a4cddad`: 정본 `:740-741` 보충 2 두 줄(빈 줄 + 본문), handoff `:88` 대기 항목 줄 끝에 "[→ 갱신 16:47 UTC, R7 22회차 N12: …]" 한 토막, `se2e_data.md:62`·`:96`·`se2e_temporal.md:81` 끝에 같은 "[→ 정정 16:47 UTC, R7 22회차 N19/N21/N22: 이 설명은 옛 판 se2e·se2e_t에 해당 … se2e_c1부터는 인과 후방 차분]" 토막, user-log 83(16:17–16:42 발언 10개)·84, 스펙 새 파일, `r7_cycle22.md`. 코드·시험·사전 등록 변경 0.
- 22회차 권고 반영: N12(handoff 링크) 해소, N19·N21 결과 문서 표시 들어감(`:62`는 렌더 누락 N25), N22(`se2e_temporal.py` docstring)는 등록 해시 때문에 코드 대신 문서 표시로 처리 — 22회차 권고(확인 실험 뒤 수정)와 맞음. N23(CRLF 사본 해시 한 줄)·N3·N24(결과 문서에서 1,799 판만 인용)은 결과 문서가 아직 없어 해당 없음. **22회차 §7-2 권고 중 handoff §2.8 줄은 빠짐(D-1).**
- **제어 문자·줄 끝 전수**(`ctrlscan23.py`, archive 텍스트 459파일): `\r\r\n` 0, 외톨이 `\r` 0, CRLF 0, `\t` 0, 기타 C0·C1·영폭 문자 0, BOM 0, UTF-8 아님 0. 끝 줄바꿈 없음 1(`prereg.json` — 해시가 고정한 원문).

### 6.2 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외)
- effort(`effort\s*high|high effort|실시간.*high`): 정본 `:148`(§16 옛 서술, "(§26으로 폐기: 기본 low, low·high 비교)" 표시)·`:254`(§28 A5 "effort high 조건에서는 투표 안 함" — 비교 조건 규칙)·`:728`(§82)·`:741`(보충 2), `E-first:11`·`:387`(폐기 표시)·`:388`·`:608`·`:645`·`:657`, `M2:279`, `M8:197`, `D17:41`·`:139`, `STAGE2-CLOSE:160`·`:201`, `SUMMARY:845`, `astra_role:414`·`:517`(N7), 논문 마인드맵 `4_experiments.tex:15`("low가 기본, low·high 둘 다 보고"). **실행 중 경로를 high로 적은 현재 서술 0**; high 계약·조건은 모두 "비교 조건"으로 적혀 보충 2와 같다.
- 결합 설계 어휘(`RTC식|1 Hz|계단식|coupling`): 스펙 외에는 정본 `:69`(M5 L2 RTC식 블렌딩 — 다른 뜻)·`:741`, `plan.md:229`·`D1`·`D3`·`D5`·`D8`·`D13`(M5·RTC 블렌딩), handoff `:88` — 1 Hz Astra 호출을 현재 구조로 적은 곳 0.
- 속도 출처(`중앙 차분|np.gradient`): 22회차 목록에서 `se2e_data.md:62`·`:96`·`se2e_temporal.md:81`에 표시가 붙은 것 말고 변화 없음. S-E2E 새 판을 중앙 차분이라 적은 줄 0.
- 회차 상태(`22회차|연속 무결`): handoff는 `:88`(22회차 N12 인용)뿐이고 §2.8 줄 없음(D-1), draft-log·direction-log 줄 없음(N27).

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st` + 코드 사본으로 R2 DEV 전 편 `validate_episode` **36/36** + 음성 대조 2종 검출; LeRobot 시험 6 passed; 새 편 내보내기·검증·lerobot 적재(행 138, 무효 편 건너뜀 포함). S-E2E 판 `se2e_c1` 해시·재변환·표본 재계산(행 142–145). |
| 2 모델 | 충족(CPU) | GPU 학습 없음 → CUDA 시험·GPU 재적재 건너뜀. 파드 CPU 스모크(N33), CPU 묶음의 `test_stageb_torch.py`·`test_r7c15_resume_keys.py`·`test_se2e_temporal_qwen.py`·`test_se2e_reconvert.py`·`test_se2e_motion_confirm_verdict.py` 통과. |
| 3 폐루프 | 충족 | Isaac 한 워커(`closed --model mock --split dev --seeds 8 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c23`, 17:04:38–17:09:16 UTC, `IR_INST` `r7c23_standard`): `CLOSED_DONE` C5·C5' 성공 1.0, 14.26 s, 호출 43·오류 0, 확정 비율 0.9273, 결정 3.018/s, 행 필드·blob(행 6), `meta.bootstrap` 10000, `prereg` OK, git `a4cddad3`, `code_sha` `a2a7c8394ad45fd6`, 하드 리셋 빌드 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 17:01:06–17:01:59 UTC): `e05`(P1, 3편) → `E05_DONE`, `rd`(3편) → `RD_DONE`, `calib`(P1, 3편) → `CALIB_DONE`, `e05 --split pool --seeds 2003,2047,2101 --truth outcome:plan` → `E05_DONE`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.6). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`, 17:00:58–17:01:06 UTC, 21·22회차와 다른 값)
- 1 `e05 --data P1 --split test`, 2 `e05 --data P2 --split test_p5 --seeds 1329`, 3 `calib --fit-split cal`, 4 `calib --heldout-split test_p5`, 5 `rd --split cal`, 6–8 `closed --split test --seeds 1000`·`cal 549`·`test_p5 1329` → "refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 8,30`, 10 `pool --seeds 1999`, 11 `dev --seeds 2000` → "not in split … never opened"; 12–13 `--isaac-gpu 2`·`3` → "(GPU 2 never renders)"; 14 `--m4-lead-max 0`, 15 `--conditions "C5,C5''"` → "refused before any worker"; 16 `HARVEST_ALLOW_SPLIT=cal` + `closed --split test --seeds 1000`, 17 `=test` + `e05 --split cal` → 거부; 18 `gen --seeds 59999`(확인 없음), 19 `--seeds 9999 --confirm-train`, 20 `--seeds 2000 --confirm-train` → 거부; 21 `determinism fresh --seed 2120`, 22 `history --seeds 1000` → "only DEV 0-29 and POOL"; 23 `canary build-set --seeds 500-501` → "no episode selected"; 24 `e05 --split pool --seeds 2119`(P2) → "no episode selected"; **25 `closed --hb-mode K5`, 26 `--hb-mode K2,K5` → "from ('K0', …, 'K4')"**(§82 K5 미구현이 워커 전에 거부됨). **26건 모두 rc 1**; 출력 폴더는 24번(e05)의 빈 폴더 하나(N10), 나머지 0.

### 6.5 A. 테스트
- 로컬(`…\r7c23\repo` = a4cddad archive, `python -m pytest -rs -o addopts="-p no:cacheprovider -q"`): Git Bash에서 `--basetemp=D:/tools/scratch_qdd/r7c23/pt3` → EXIT 0, **1014 passed · 15 skipped**. 먼저 PowerShell에서 돌린 판(`pt`)은 1012 passed · 2 failed(N31, `date` 실행 파일 없음).
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, TMPDIR·pyc·카나리·qid 등록부 = scratch): **1130 passed, 4 skipped**, EXIT 0(17:00:55Z).
- 파드 LeRobot(`venv_e3st` + `r2/pylib_lerobot`·`pylib_pytest`): **6 passed**.

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함). 검토 시작 때 HEAD = a4cddad(작업 트리에 다른 에이전트의 미커밋 코드); 끝날 때 HEAD = a5816e1(N36) — 내가 만든 것 아님, 건드리지 않음. 로컬 C:에 이 검토의 산출물 없음(하네스 작업 출력 파일만). 로컬 `reconvert` 거부 시험은 내 임시 폴더 아래 경로만 썼다.
- 파드 정리(`clean23.sh`, 경로를 하나씩 적은 스크립트, 열린 핸들 0 확인 뒤, 17:11:28 UTC): `tmp/r7c23`(코드 사본·가드·평가·재변환 산출 포함), 내 Isaac 판이 만든 `tmp/carb.XI4Ww9`(생성 17:04:39Z)·`tmp/tmpyecxe0sn`(17:05:00Z)·`cache/pyc_r6/data/harvest/tmp/tmpyecxe0sn`·`cache/pyc_r6/data/harvest/tmp/r7c23`, `ir/kitcache/cyclo-r7c23_standard`(208 MB). 판별: Isaac 앞뒤 목록 차이, 생성 시각이 내 Isaac 창 안. 끝에 `tmp`·`kitcache`·`pyc_r6`의 r7c23 항목 0, 명령줄에 r7c23이 든 프로세스 0. 확인 실험 폴더(`ckpt/se2e_confirm`, `logs/se2e_confirm`, `data/se2e_c1`, `code_se2e_confirm`)는 읽기만 했다(예측 파일 열지 않음, 평가 값 읽지 않음).
- 로컬 임시(`D:\tools\scratch_qdd\r7c23`: `src.tar`, `repo/`, `pt/`·`pt2/`·`pt3/`, `tmp/`, `tv/`, `pod/`, 스크립트·출력)는 다음 순회 대조용으로 남김(C: 아님).
- 절차(내 쪽, 결과 영향 없음): 머리의 인라인 `python -c` 3건·PowerShell로 만든 `ctrlscan23.py`; `check23.py` 첫 실행에서 B9 기대값 오류(N30)와 `heartbeat_input` 호출 인자 오류(내 스크립트) → 고쳐 다시 돌림; 첫 `conf23.py`의 파일 비교 필터가 절대 경로 문자열로 걸러 모든 폴더를 세었다 → 상대 경로로 비교하는 `conf23b.py`로 행 148 결과.

## 7. 다음 순회 전에 할 일 (제안)
1. **D-1**: handoff §2.8 끝에 22회차(PASS, 연속 무결 1)·23회차(FAIL, DOC 1, 연속 무결 0) 줄, `:3` 갱신 시각; draft-log·direction-log에 같은 줄(N27). 보고서를 커밋하는 커밋에 handoff 줄이 들어갔는지 `git show --stat`로 확인.
2. (선택, NOTE) N25 `se2e_data.md:62` 표시를 비고 칸 안으로; N21 보충 2 위치 표시; N7 `astra_role:517`에 "→ §82 보충 2"; N29·N3 결과 문서(`se2e_motion_confirm.md`)에 층별 구간의 난수 흐름·항목 수 확인 한 줄; N31 `session._tz`를 파이썬 시각으로.
3. 24회차 대상은 a5816e1 이후 HEAD(정본 §84·§84 보충 1 = 결합 설계 승인, 스펙 §14–§15, MolmoAct 연구 문서 — 문서만), 연속 무결 0에서. 확인할 것: §84가 §82 호출 정책(편당 1–3회·하트비트 강등)·§82 [결정 필요](falsify 먼저)·보충 2와 어떻게 관계를 적는지(덮는 범위 명시), 승인된 스펙에 N17의 옛 '목표' 문장이 남았는지, handoff 핵심 결정·대기 항목이 §84를 반영하는지, 확인 실험이 끝났다면 판정 파일이 등록 규칙·스크립트 해시대로 나왔는지(검증 1,799, 네 판 같은 키).
