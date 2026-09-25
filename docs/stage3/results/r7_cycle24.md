# R7 객관 검증 순회 — 24회차 (cycle 24, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle23.md` §5 표·결론을 근거로 쓰지 않고 사전 등록 원문에서 대조표를 다시 만들었다. 행마다 **21·22·23회차와 다른 새 경계값으로 구성한 입력 → 실제 함수·CLI 출력** 또는 **파드 원자료 재계산**으로 확인했다). 작성 2026-09-25 17:55 UTC 무렵(로컬 시작 17:20:08 UTC, 파드 첫 명령 17:29:11 UTC, 파드 정리 끝 17:45:19 UTC). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`6e3fda6`**(`6e3fda6d3781b1b8…`, 커밋 시각 2026-09-25 17:19:37 UTC, "R7 cycle 23 FAIL (DOC 1: handoff §2.8 missing cycle-22 line) — fix records in the same commit as the report; NOTE fixes N17/N18/N21/N22/N25"). `git diff --stat a4cddad 6e3fda6` = 9파일 **문서만**(커밋 5개: 2b7ba25 MolmoAct 연구 문서, c915535 정본 §84·스펙 §14, a5816e1 §84 보충 1·스펙 §15, 190af17 §84 보충 2·스펙 §16, 6e3fda6 23회차 보고서·정정): `00-interfaces.md`(+17/−1), `draft-log.md`(+2), `handoff.md`(+4/−1), 새 `docs/research/molmoact_deepdive_2026-09-26.md`(+321), `direction-log.md`(+2), 새 `r7_cycle23.md`(+224), `se2e_data.md`(:62 한 줄), 스펙(+32), `user-log.md`(+9, 85·86). `harvest/`·`tools/`·`tests/`·사전 등록 원문(`prereg*.md`·`prereg.json`·`E-first`·`EVAL`·`M4`)·계획 `2026-09-25-e2e-ready.md`·`CLAUDE.md`·`paper/` 변경 **0**(`a4cddad..6e3fda6`·`3a3d76c..a4cddad` 모두 같은 명령으로 0줄). a4cddad 이후 **새 사전 등록 커밋 없음**(`prereg_ma1.md`·`prereg_astra_motion.md`는 대상 커밋 트리에 없다 — 대상 뒤 06355f0·a62164d로 커밋됨, N40). 작업 트리의 다른 에이전트 미커밋 파일(`harvest/astra_motion/`, `tests/astra_motion/`, `harvest/train/se2e_a3d.py` 등)은 **검토 대상 아님**. `git -c core.autocrlf=false archive 6e3fda6`(커밋 해시를 고정)을 Python tarfile로 `D:\tools\scratch_qdd\r7c24\repo`에 풀었다(**510파일** = 23회차 508 + `r7_cycle23.md` + MolmoAct 연구 문서). 파드 사본 = 같은 archive(`/data/harvest/tmp/r7c24/code`, 511파일 = + JSON `CODE_VERSION` `6e3fda6d…`, dirty false); 파드 산출 `meta.git.commit` = `6e3fda6d3781…`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle7.md`–`r7_cycle23.md`(특히 21–23), 정본 `00-interfaces.md` §1–§84(끝의 §84 보충 1·2까지; 뒤 절 우선; [사용자] 제목 절은 그대로; 논문 .tex는 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`·`prereg_se2e_temporal.md`·`prereg_se2e_motion_confirm.md`·`M4-overlap-commit.md`.
- 분류(23회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·같은 문서의 뒤 결과와 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 기록이 없는 것. 정본이 "나중에 할 일"로 적은 것(§82·§84 구현, §83 런타임 적용, 확인 실험 결과)은 SCOPED. 승인된 설계(스펙)의 내용은 지금 코드를 틀리게 말하지 않는 한 SCOPED/NOTE. 연구 문서의 제안 목록·[결정 필요]는 지금의 결정·구조를 틀리게 말하지 않는 한 NOTE. 원문이 맞고 렌더에서만 빠지는 것은 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c24`(C: 쓰기 없음; 하네스 작업 출력 파일만). **모든 스크립트는 Write 도구로 쓰고 경로로 실행**(heredoc·`cat >`·`python -`·인라인 `python -c`·PowerShell 문자열 조립 없음; 두 스크립트는 Edit 도구로 고친 뒤 다시 실행). 로컬 pytest는 Git Bash(N31), basetemp `…\r7c24\pt`. 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c24`, `source /data/harvest/env.sh`, 업로드 = `tar -cf - | kubectl exec -i … tar -xf -`(파드 스크립트 CR 바이트 0을 업로드마다 확인). **절차상 어긋남(내 쪽, 17:29–17:30 UTC, 정리 완료)**: 첫 업로드를 Git Bash에서 `MSYS_NO_PATHCONV` 없이 보내 MSYS가 인자 `/data/harvest/…`를 `C:/Program Files/Git/data/harvest/…`로 바꿨고, 파드 작업 디렉터리가 `/`라 **파드 루트 파일 시스템에 `/C:/Program Files/Git/data/harvest/tmp/r7c24/up`(src.tar 19.6 MB + 2파일)이 생겼다**(/data 밖). 발견 즉시(17:30 UTC) 그 트리 전체(모두 17:29:33 UTC 생성 — 내 명령 시각)를 지웠고, 이후 모든 kubectl은 `MSYS_NO_PATHCONV=1`로 보냈다; 정리 스크립트 끝에서 `/C:` 부재를 다시 확인. GPU: Isaac = GPU 1에 **내 프로세스 하나**(`--inst-prefix r7c24`, `IR_INST` `r7c24_standard`, `IR_ROOT=cyclo`; 같은 시각 GPU 0·1의 R2_TRAIN Isaac 워커와 17:38:15 UTC에 시작한 다른 에이전트의 `astra_motion` Isaac 실행 — 건드리지 않음), GPU 2·3에는 아무것도 올리지 않음(가드 12·13은 워커 전에 거부). CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`, 한 번에 한 묶음(CPU 시험 → 가드·평가·데이터 → Isaac → se2e_c1 점검 순차). 시드 DEV·POOL만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 요청과 **다른** 값으로만). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. `ckpt/se2e*`·`logs/se2e*`·`data/se2e*`·`r2/dev`·`code_se2e_confirm`·`tmp/ma1`는 **읽기만**(ma1은 이름·시각 목록만); 확인 실험 예측 파일(`pred*.jsonl`)은 열지 않았고, 판정 파일은 **구조 필드만**(항목·스냅샷 수, 규칙 블록, 표지) 읽고 효과·정확도·구간 값은 출력하지 않았다.

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 1 |
| SCOPED | 21 |
| NOTE | 44 |

코드·사전 등록은 3a3d76c·a4cddad와 바이트가 같고 모든 행동 확인이 통과했다: 로컬 **1014 passed / 15 skipped**(Git Bash, 176.1 s), 파드 CPU **1130 passed / 4 skipped**(116.1 s), LeRobot 6 passed; 가드 **27건** 모두 rc 1(21–23회차와 다른 값, `--m4-lead-max nan`·`inf`, `--hb-mode K6`·`k2`, `--conditions "C5,c5'"` 포함); R2 DEV `validate_episode` **36/36** + 23회차와 다른 편(dr/mug_tray ep2)·다른 종류의 음성 대조 3종(프레임 시각 2e-6 s 어긋남, 머리 이미지 경로 누락, `hold_n` +1 → 모두 검출, 무수정 사본 오류 0); 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 모두 완료; 새 시드 **DEV 11**에서 같은 Isaac 워커 C5 → C5' 행동 **1,526개 비트 동일**; 로컬 구성 시험 `check24.py` **57/57**, `verdict24.py` **10/10**, `prereg_hash.py --check` OK, 제어 문자 전수 0·변경 문서 표 칸 수 불일치 0. se2e_c1은 `SHA256SUMS` 5/5 OK, **22·23회차와 다른 10편**(RB1 11·143·289·434·580, RB2 11·172·345·518·691)에 등록된 `reconvert --hist`를 다시 돌린 출력이 판 폴더 줄과 바이트 동일(152·103줄), 7행마다 1행(RB1 3,633·RB2 2,483행) 원본 parquet에서 내 코드로 계산한 후방 차분과 오차 0.0. 확인 실험은 파드에서 끝났다(드라이버 17:20:48–49Z, 판정 파일 17:21:44–45Z): 네 판 설정 = 등록 §2, `CODE_HASHES` 등록값 6/6 × 4, 판정 파일 구조(검증 1,799·네 판 같은 항목 수 5,397·규칙 블록 = 등록, 확인 사본의 판정 스크립트 sha `fa7299062cc5e1d1`) — 결과 문서는 대상 뒤 커밋(7dced6a)이라 SCOPED.

**23회차 정정**은 실제 diff와 맞다: handoff §2.8에 22회차(PASS, 연속 무결 1)·23회차(FAIL, DOC 1) 줄, `:3` 갱신 시각 17:19 UTC, draft-log·direction-log에 같은 두 줄, 모두 보고서와 **같은 커밋**(6e3fda6 `--stat`: 보고서 + handoff + draft-log + direction-log); NOTE N17(스펙 "읽는 법" 문단)·N18(§84 보충 2 아래 '§82 편당 1–3회를 흐름에 한해 대체' 문장)·N21/N22(§82 보충 2 끝 표시)·N25(`se2e_data.md:62` 표시를 비고 칸 안으로 — 표 칸 수 검사 불일치 0)도 들어갔다.

**DOC 1건**: handoff §2.7 "사용자 대기 항목"(`handoff.md:88`)이 정본 §84(17:11 UTC, 대상보다 앞선 커밋 c915535)가 해소한 두 항목 — §82 'falsify 먼저 평가 뒤 Astra 호출' [결정 필요], Astra 움직임 인터페이스 설계(브레인스토밍 진행 중·"설계 초안") — 을 여전히 사용자 확인 대기로 적고 있고, handoff 머리는 "마지막 갱신 17:19 UTC"라 현재 상태로 읽힌다(D-1; 11회차 D-1 "§75 보충 뒤에도 '결정 필요'"와 같은 성격). **연속 무결 0 유지.** 검토 중 HEAD가 코드·사전 등록을 포함한 커밋 7개(ed478e4까지)로 움직였다(N40) — 25회차는 새 코드(E-MA1 G0·판정 스크립트·trace 모델 시험)와 새 사전 등록(`prereg_ma1.md`·`prereg_astra_motion.md`)을 행동으로 확인해야 한다.

---

## 1. DEFECT

없음.

(검토한 후보와 판단: ① 확인 판정 스크립트가 **한 판에서 항목 줄 하나가 빠진 입력**도 받아들인다(`verdict24` M7d: motion_s2 2,999항목, rc 0) — 23회차 중복 항목과 같은 입력 검사 범위 문제이고 `n_items`가 출력에 남으며, 실제 파드 판정 파일은 네 판 항목·스냅샷 수가 모두 같다(5,397/1,799; 300 판 900/300) → NOTE N3 확장. ② `replay_bit_identical`이 `False`(bool)를 불신 — JSON에서 읽은 행에 생길 일 없는 값이고 방향도 안전(불신) → N2. ③ 정본 §84 보충 2(흐름 호출 = 동시 1개, 답 직후 다음 요청)는 지금 코드(§45 K2: 답 뒤 N = 5 s, 동시 1개)와 다르지만 §84가 "런타임 코드 구현은 R7 E2E 준비 기준점 뒤"라 적었다 → SCOPED S18.)

## 2. DOC

- **D-1. `docs/handoff.md:88`(§2.7 "사용자 대기 항목") — 정본 §84가 해소한 결정 두 개를 여전히 "사용자 확인 대기"로 적는다.** `:88`의 현재 대기 목록(15:27 UTC 갱신 토막) = "(1) 정본 §82 'falsify 먼저 평가 뒤 Astra 호출' [결정 필요], (2) Astra 유료 실행(E-Astra-necessity·E-Astra-motion 탐침) 승인 — 한도 약 10만 원, (3) Astra 움직임 인터페이스 설계(브레인스토밍 진행 중, user-log 77·78)", 16:08 토막 "Astra 움직임 인터페이스(A+B·손끝 목표 순서) 설계는 탐침 결과 뒤 확정", 16:47 토막 "설계 초안 `docs/superpowers/specs/2026-09-26-astra-vla-coupling-design.md`". 그런데 정본 §84(2026-09-25 17:11 UTC, user-log 85 "1~3 다 허용할게", 커밋 c915535 — 대상 6e3fda6보다 앞)는 "**§82 [결정 필요] 해소 — falsify 먼저 평가**"(`00-interfaces.md:747`, 보충 1 `:751` 재사용 한 번 상한)와 "**Astra–VLA 결합 설계 승인** … 승인된 설계로 삼는다"(`:745`)를 결정했다. handoff 머리 `:3`은 "마지막 갱신: 2026-09-25 17:19 UTC"라 이 목록을 현재 상태로 읽게 하고, 목록 토막에 §84 정정 표시가 없다. 같은 문서 `:118`(23회차 줄)이 "결합 설계 승인"을 말하지만 falsify 결정은 어디에도 없어, 다음 세션은 이미 받은 사용자 결정을 다시 물을 수 있다. (2)의 유료 실행 승인은 §84가 다루지 않아(§84는 E-MA1 = 유료 아님) 대기로 남는 것이 맞다. 같은 누락: `:84` "핵심 결정"에 §84(결합 설계 승인·E-MA1·falsify 먼저·MolmoAct 주 참고·보충 2 직렬 흐름 호출)가 없다(§82는 표시가 붙어 있음). 11회차 D-1("handoff 10회차 줄의 판정 7·lead_max가 §75 보충 뒤에도 '결정 필요'")과 같은 성격 → DOC. **고칠 것**: `:88` 끝에 "[→ 갱신 …, R7 24회차 D-1: 정본 §84(user-log 85)로 (1) falsify 먼저 평가 결정(재사용 한 번 상한, 보충 1)·(3) 결합 설계 승인 — 남은 대기 = (2) 유료 실행 승인(탐침 예산은 user-log 87 기준)]", `:84`에 "[→ 정본 §84: …]" 한 토막, `:3` 시각. 재발 방지: 정본에 [사용자 결정] 절을 더하는 커밋에서 handoff §2.7 대기 목록을 같은 커밋에 고친다.

(검토했지만 DOC로 올리지 않은 후보: 스펙 `:1` 제목 "(초안)"·`:3` "상태: 초안 — 사용자 검토 전, 구현 전"과 `:7` 머리 개정 문단의 "1 Hz 계단식 호출 … 그대로 유지한다" — 같은 문서 §14 "이 설계 전체가 사용자 승인됨"·§16 "계단식 … 대체"와 정본 §84·§84 보충 2와 다르지만, `:17` "읽는 법"이 "§3의 계단식 호출은 §16이 대체 … 충돌하면 머리 개정 문단과 §11–§16이 우선"이라 적었고 승인된 설계 내용이며 지금 코드를 틀리게 말하지 않는다 → N17(남은 것). `astra_role:239`·`:515` "기본은 매번 호출한다"([결정 필요]) — 연구 문서 제안 → N7. §84 보충 1의 "1 Hz 조밀 호출은 접촉 근처·사건 직후 창에서만"이 보충 2로 대체되었는데 표시 없음 — 같은 절의 뒤 보충이 "§15의 단계 적응 겹쳐 부르기를 대체"라고 이름을 들어 덮음 → N35. 스펙 §15의 비용 추정 산술 → N36(대체된 내용). draft-log에 §84 결정 줄 없음 → 기록 문서 N38.)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드 GPU 0·1 R2_TRAIN Isaac 워커 진행 중(`gen gen --seeds 10000-10599 --confirm-train`, 읽기만); 확인 인자 없는 `gen gen --seeds 35000` rc 1(가드 19).
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
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — 6e3fda6에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. **정본 §82 구현**(K5 모드·`harvest/astra/jobs.py`·`closed --upper`·T_nov·계약 캐시·J2 경로·`astra_slot.py`·Qwen3-VL-32B) **및 §84 결합 설계 구현**(보충 2 흐름 호출 = 동시 1개·답 직후 다음 요청, 두 층 M4, Astra 카메라 3대·덧그림, §11 부드러운 반영, falsify 먼저 평가 + 재사용 한 번 상한) — §82 "R7 관문 뒤 착수", §84 "런타임 코드 구현은 R7 E2E 준비 기준점(연속 무결 2회) 뒤". 지금 코드: `CADENCES` = K0–K4, "K5"·"serial"·"k2" 거부(`check24` C3), 파드 `closed --hb-mode K6`·`k2` → 워커 전 거부(가드 26·27), `RuntimeConfig()` = ("K2", 5.0)(C5), Astra 요청 이미지 = 머리 1장(S3, 파드 Astra 4행 이미지 해시 1개), `harvest/` 원문에 `falsify`·`trace5`·`eetrace` 0곳(S5), 파드 DEV 11 Astra 호출 겹침 0(hb 5.0 → 8.0, sub 8.59 → 11.59 — §45 K2의 동시 1개, 답 뒤 5 s).
- S19. **정본 §83 런타임 적용**(새 직렬화 판본·런타임 속도 구간화·보정/카나리 재생성·R2 항목의 같은 줄) — "R7 관문 뒤 착수". 6e3fda6: `harvest/serialize` 원문에 움직임 줄 없음(`check24` D3), 파드 결정 호출 요청 92/92 `motion:` 없음.
- S20. **§83 확인 실험 결과**(`prereg_se2e_motion_confirm.md`): 파드에서 네 판 학습·예측·판정 끝(판정 파일 17:21:44Z·17:21:45Z). 결과 문서·정본 §83 보충은 대상 뒤 커밋(7dced6a, N40)이라 이 회차 판정 밖 — 구조 확인만(행 147–149).
- S21. **정본 §84 E-MA1**(사전 등록 `prereg_ma1.md`를 첫 학습 전에 커밋, 관문 G0 먼저, 기존 `PROMPT_FILES_B` 해시 불변·새 옵션 파일, GPU 2·3이 빈 뒤) — 대상 트리에 등록·코드 없음. 파드 17:31 UTC 상태: `/data/harvest/tmp/ma1`에 G0 준비 파일(`dl_molmo2.py`·`setup_molmo2.sh` 등)만, 학습 프로세스 없음(`stageb_train`·ma1 학습 0), GPU 2 0 MiB. 등록 커밋(06355f0, 17:32:42 UTC)·G0 결과(ee1b000)는 25회차.

## 4. NOTE
- N1. (그대로) `stageb_train predict`·`evalck`는 체크포인트 `prompt_config`를 자기 옵션과 대조하지 않는다.
- N2. (그대로) `cli_label.replay_max`의 NaN 순서 의존. 읽는 쪽 `replay_bit_identical`은 새 경우(정수 0·`-0.0`·3−3.0 → 신뢰, 5e-324·nan·None·[0.0]·"0" → 불신)도 올바름; `False`/`True`(bool) → 둘 다 불신(JSON 행에는 생기지 않는 값, 안전한 쪽).
- N3. (확장) `temporal_verdict.py`·`motion_confirm_verdict.py` 입력 검사는 `assert`·`KeyError`·argparse이고, 등록 판정 집합(검증 전체 1,799)을 스크립트가 확인하지 않으며, 한 판 파일 안의 **중복 항목**(23회차)과 **빠진 항목**(24회차 `verdict24` M7d: motion_s2 2,999/3,000항목 rc 0)을 받아들인다 — `n_items`가 출력에 남아 읽을 때 구분 가능. 판 이름 중복·판 누락·모르는 판 이름(`none_s3`)은 rc ≠ 0(M7). 실제 파드 판정 파일은 네 판 항목·스냅샷 수가 같다(행 147). 판정 스크립트는 등록 해시로 고정돼 있으니 결과 문서에 "네 판 `n_items` 같음" 한 줄을 권함.
- N4. (그대로) Astra 시간 초과 뒤 재송신 모양 — §84 보충 2("답(또는 시간 초과)이 오면 다음 요청")가 방향을 정했으니 구현 때 시간 초과 값·늦게 온 답 처리를 정본에 한 줄로 권함.
- N5. (그대로) `se2e_diag.md:131` 6절 제안 (a) D2′는 8절로 사실상 수행.
- N6. (그대로) `se2e_diag.md:13` "약 9k까지만" 제한.
- N7. (확장) 연구 문서 `astra_role_2026-09-25.md:239`·`:515` "같은 진단 반복 시 falsify 먼저 … [결정 필요]. 기본은 매번 호출한다"는 정본 §84(falsify 먼저, 재사용 한 번 상한)로 결정됐고, `:517` J6 effort high는 §82 보충 2로 사실상 정해졌다 — 연구 문서 제안이라 NOTE; "→ §84"·"→ §82 보충 2" 표시 권함.
- N8. (확장) `CLAUDE.md:32`(user-log 76 비용 한도 줄) 위치; `CLAUDE.md:48`·정본 `:11`의 "1초에 Jev를 … 3번 계단식으로 겹쳐"는 하위 VLM(Jev→VLA) 호출 요구로 §84 보충 2(Astra 흐름 호출만 직렬 1개)와 충돌하지 않는다(대상이 다름).
- N9. (그대로) `steering_representation_2026-09-25.md:33`·`:81` §82 표시가 GFM 렌더에서 사라짐.
- N10. (그대로) `e05`는 `--out` 폴더를 거부 전에 만든다 — 가드 25(`e05 --data jsel_dev/P0 --split pool --seeds 2060` → "no episode selected" rc 1)가 빈 `g25/`를 남김.
- N11. (그대로) 카나리 `--force` 같은 날 재실행이 그날 표류 파일을 덮는다.
- N12. (해소 기록) 23회차 D-1 정정: handoff §2.8 `:117`·`:118`, `:3` 17:19 UTC, draft-log `:465`·`:466`, direction-log `:69`·`:70` — 모두 보고서와 같은 커밋 6e3fda6(`git show --stat`로 확인, 23회차 §7-1 권고대로).
- N13. (그대로) `draft-log.md:462` "커밋 안 함" 관용 표기.
- N14. (그대로) `prereg_se2e_temporal.md` §7 등록 해시 = 파드 `code_se2e_temporal` 사본.
- N15. (그대로) `e_m4b_meas.md:36`·`:51`은 사전 등록 원문 복사.
- N16. (그대로, §84와 대조) `2026-09-25-e2e-ready.md:12`·`:26` "Astra 하트비트"는 지금 실행 계층 서술 — 정본 §82·§84 구현 때 계획 문장도 바꿀 것.
- N17. (부분 해소) 스펙 `:17` "읽는 법"이 들어가 §1–§10의 '손끝 목표' 문장과 §3 계단식이 대체되었음을 적었다. 남은 것: `:1` 제목 "(초안)"·`:3` "상태: 초안 — 사용자 검토 전, 구현 전"(§14 `:168` "이 설계 전체가 사용자 승인됨", 정본 §84 `:745`와 다름), `:7` 머리 개정 문단의 "1 Hz 계단식 호출 … 그대로 유지한다"(§16·정본 §84 보충 2가 대체). `:17`은 "충돌하면 머리 개정 문단과 §11–§16이 우선"이라 머리 문단과 §16이 서로 충돌할 때의 순서가 적혀 있지 않다(첫 문장 "§3의 계단식은 §16이 대체"로 실질은 풀림, 정본은 명확). 승인된 설계라 NOTE; `:3`을 "승인(정본 §84, user-log 85), 구현 전"으로, `:7` "1 Hz 계단식 호출"에 "[→ §16]" 표시 권함.
- N18. (해소 + 남은 것) 정본 `:756`이 "보충 2의 흐름 호출(직렬 1개)은 §82의 '편당 1–3회' 호출 정책을 결합 설계의 실행 중 흐름에 한해 **대체**(뒤 절 우선), J1–J6의 다른 호출 시점은 §82 그대로"라 덮는 범위를 적었다. 남은 것: §82 `:726` "강등: 5 s 하트비트(→ J5 저빈도 감사로 대체)"·`:724` 원칙("Astra만 할 수 있는 일에만")과 흐름 호출의 관계(흐름 호출은 진행 평가 + 수치 명령이라 하트비트 ack와 다른 일)는 적혀 있지 않다 — 뒤 절 우선으로 충돌은 없음; 한 구절 권함.
- N19. (그대로) 스펙 `:152` 토큰 수(460 대 §59 466), `:115` "low 1회 ≈ $0.02" 원자료 미확인(추정 표시), `:159` MolmoAct 학회 표기 — MolmoAct 연구 문서 `:33`(ICRA 2026, OpenReview 기록)와 같음.
- N20. (그대로) `se2e_temporal.md` §5 표의 분 단위 반올림.
- N21. (부분) 정본 §82 보충 2(`:741`) 끝에 23회차 N21·N22 표시가 붙었지만 내용은 N22(목표 문구·호출 방식 대체)이고, §83 뒤에 적힌 위치 표시("§83 뒤에 적음")는 없다 — 선택 사항.
- N22. (해소) §82 보충 2 "다음 손끝 목표" 문구에 "16:33 UTC '일반 조종법만' 결정 전 서술 — 목표 표현은 쓰지 않는다" 표시.
- N23. (그대로, 재확인) 등록 §5 "무수정" 해시 3개(`stageb_data.py` `a61a7cf6…`, `stageb_model.py` `255c78cf…`, `se2e_temporal.py` `9fd650fc…`)는 LF 블롭을 CRLF로 바꾼 바이트의 해시와 같다(`check24` H3) — 파드 CRLF 사본에서 잰 값. 사본의 `harvest/`·`tools/`·`tests/` 265파일 LF 내용 = 6e3fda6(차이 0; 다른 것은 `docs/` 16·`paper/` 20·`CODE_VERSION`).
- N24. (그대로) 등록 §3 "(none)끼리·(motion)끼리 시드 간 정확도 차"는 판정 스크립트 출력에 따로 없음.
- N25. (해소) `se2e_data.md:62` 정정 표시가 비고 칸 안으로 옮겨졌다(`ctrlscan24` 표 칸 수 검사: 변경된 문서 9개의 모든 표 행이 머리 칸 수와 같음).
- N26. (그대로) 등록 고정 시점: 등록 머리 15:52:12Z < none 판 드라이버 15:53:07Z < 커밋 44c907d 15:53:42Z < 첫 학습 스텝; motion 판 `CODE_HASHES` 16:36:32Z·16:36:40Z — 모두 등록 뒤. 판정 파일 17:21:44Z(모든 판 예측 뒤 17:20:48–49Z).
- N27. (해소) 23회차 N27(draft-log·direction-log 22회차 줄) — 들어감(N12).
- N28. (그대로) `RuntimeConfig.astra_effort`(`core.py:79`)는 기록용, 실제 호출은 상수 `EFFORT` — 정본 §82 보충 2와 맞고 바꿀 경로가 없다(`check24` S1·S2, 파드 Astra 4행 effort low·요청 본문 low 4/4).
- N29. (그대로) `motion_confirm_verdict.bootstrap`은 세 층을 한 `default_rng(0)` 흐름으로 차례로 뽑는다 — `verdict24` M5 재구현(‘all’ 먼저, 층이 흐름을 이어감)이 세 층 모두 오차 0. 이번 입력에서는 전이 층을 새 시드 0 흐름으로 뽑아도 같은 분위 격자점이 나왔다(격자 간격 1/2400이라 우연히 일치; 23회차는 약 3e-4 차).
- N30. (그대로) 로컬 시험의 셸 의존(`harvest/load/session.py:15` `_tz()`가 외부 `date` 호출 — PowerShell에서 2 failed). 이번 회차는 처음부터 Git Bash.
- N31. 시험 수: 로컬 **1014 passed / 15 skipped**(176.1 s, 17:21:41–17:24:38Z), 파드 CPU **1130 passed / 4 skipped**(116.1 s, 17:32:49–17:34:49Z), LeRobot 6 passed(29.0 s). 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다.
- N32. 단계 B 소형 CPU 스모크(17:37:17Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–23회차와 같은 값 — 결정적), expert p50 0.023 s·전체 p50 0.073 s(CPU, 참고), 맥락 토큰 454.
- N33. DEV 11 판: 행동 1,526·15.26 s·호출 46, `last_step` {none 1, OK 30, LAG 7, DEVIATE 6, CONTRADICT 2}, 확정 비율 0.8979, 결정 3.016/s, Astra 2(hb 5.0 → 8.0, sub 8.59 → 11.59). 파일명 `dev11-P0-standard-e0`.
- N34. 가드 12·13(`--isaac-gpu 3`·`2`)의 거부 문구는 "only (GPU 2 never renders)"로 GPU 3을 이름으로 들지 않는다(동작은 둘 다 rc 1·출력 없음) — 표현만.
- N35. 정본 §84 보충 1 셋째 항목(`:753` "1 Hz 조밀 호출은 접촉 근처·사건 직후 창에서만, 나머지는 느린 간격")은 보충 2(`:755` "§15의 단계 적응 겹쳐 부르기를 **대체**", "빈 공간 구간 쉬기는 비용이 넘칠 때만 쓰는 선택지")로 덮였는데 그 항목에 표시가 없다 — 같은 절의 뒤 보충이 이름을 들어 대체해 충돌은 없음; "[→ 보충 2]" 표시 권함.
- N36. 스펙 §15 `:180` "기본 = 단계 적응 간격 … 추정 1분당 약 0.5–0.9천 원(접촉 창 비율 20–40 % 가정)" — 같은 절의 단가(1회 28원, 1 Hz = 60회/분 = 약 1,700원/분)와 3 s 간격(20회/분)으로 다시 계산하면 28 × (60f + 20(1−f)) = 784원(f 0.2)–1,008원(f 0.4), 사건 직후 창을 더하면 그 이상 → 약 0.8–1.0천 원/분. 이 기본안은 §16·정본 §84 보충 2로 대체되어 지금 결정에 영향 없음(보충 2의 "L = 3–5 s면 약 340–560원/분" = 28 × 60/L은 재계산과 같음, §15의 "1,700원/분·전 실험 약 60분"도 같음).
- N37. 정본 §84 보충 2는 [사용자 결정]으로 적혔지만 "동시 요청 1개"라는 구체 해석은 Claude의 해석이고 user-log 86에 "(에피소드당 한 번이라는 뜻이면 사용자 정정을 받아 고친다.)"로 남아 있다 — 정본 문장에 "(해석, user-log 86)" 한 구절 권함.
- N38. 기록 문서: `draft-log.md`에 정본 §84·보충 1·2(user-log 84–86) 결정 줄이 없고, direction-log `:69`·`:70`(22·23회차) 행은 앞 행들의 여섯 질문 형식("1 예 / 2 예 / …")을 따르지 않는다 — 기록 문서라 NOTE.
- N39. MolmoAct 연구 문서(`docs/research/molmoact_deepdive_2026-09-26.md`)가 지금 코드·결과를 말한 문장은 모두 맞다: `ExpertConfig.ctx_dim` 2560·expert 폭 768·깊이 8(`stageb_expert.py:30`·`:38`·`:39`), `AuxGeomHead` 학습된 질의 주의 풀링(`:178`–`:187`), 백본 한 층 은닉 상태(`stageb_model.py:100` `hidden_states[self.layer]`), `PROMPT_FILES_B`(`stageb_train.py:56`), `MODEL_REV` `ebb281ec…`, `AUX_REG`(`stageb_data.py:70`), RB2 스테레오 657편·RB1 718편(`se2e_data.md:20`·`:43`), E-TC FULL p95 0.0946–0.0983 s·칸당 2,119–2,450 s(`se2e_temporal.md:55`–`:70`), §47 fx 367·85°. §6 E-MA1 초안은 "등록 문서로 옮기기 전 초안"이라 적혀 있고 정본 §84와 같은 요인·관문 G0.
- N40. 검토 중 HEAD가 **ed478e4**로 움직였다(7dced6a 확인 실험 결과·정본 §83 보충, 06355f0 E-MA1 사전 등록 + G0·판정 코드, a62164d 탐침 사전 등록, 5320dd2·075c505 user-log 87, ee1b000 G0 실패 기록, ed478e4 `CLAUDE.md` 규칙) — `git diff --stat 6e3fda6 ed478e4` = 19파일 +1,756(코드 `tools/ma1/g0.py`·`g0_point.py`·`ma1_verdict.py`, 시험 `tests/train/test_se2e_trace_model.py` 등 포함). 이 보고서는 6e3fda6만 판정한다. 25회차는 새 코드를 행동으로(`ma1_verdict.py` 등록 해시·경계값, G0 판정 문턱 12/30 px), 새 사전 등록 두 개를 정본 §84·user-log 87과 대조해야 한다.
- N41. (절차, 내 쪽) 머리 "규칙 준수"의 파드 루트 쓰기 사고(17:29:33 UTC 생성, 17:30 UTC 삭제, 끝에 `/C:` 부재 확인). 원인: Git Bash에서 kubectl 인자 경로가 MSYS 변환됨. 다음 순회는 Git Bash에서 kubectl을 부를 때 `MSYS_NO_PATHCONV=1`을 처음부터 쓸 것.
- N42. 내 Isaac 창(17:37:56–17:42:27Z) 안에 새로 생긴 `ir/kitcache/cyclo-astram_refs`(17:38:15Z)는 다른 에이전트의 `harvest.astra_motion.run`(`IR_INST=astram_refs`, `TMPDIR=/data/harvest/code_astra_motion/tmp`) 것이라 건드리지 않았다. 같은 초에 생긴 `tmp/tmpfxfx7oe4`(+ `pyc_r6` 거울)는 내 워커 것으로 판별(내 워커 명령 `TMPDIR=/data/harvest/tmp`·`PYTHONPYCACHEPREFIX=…/pyc_r6` — `closed.py:192`–`:194`; 그 에이전트는 TMPDIR이 다름; 23회차의 같은 +19–22 s 패턴).
- N43. 확인 실험 판정 파일 구조(값은 읽지 않음): `verdict_full.json` `n_val_snapshots` 1,799·`label` valfull·`rule` = {0.015, 0.0, 0.01, 10000, 0}, 네 판 항목/스냅샷 수 동일(전체 5,397/1,799, 전이 3,462/1,154, 정상 1,935/645); `verdict_300.json` 300·900항목(전이 201); 확인 사본의 판정 스크립트 sha16 `fa7299062cc5e1d1` = 등록. 전이 스냅샷 비율 1,154/1,799 = 64.1 %(등록 `:19` "val 행 1,921, 전이 65.07 %"는 로더 전 행 기준 — 다른 모집단).
- N44. 파드 상태 목록은 이번에 `TZ=UTC`로 찍었다(23회차 N37의 KST+"Z" 실수 재발 없음).

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**(`check24` H1), 파드 산출 `meta.prereg.check` = "OK"(closed). 원문 인용 줄은 `refcheck24.py`로 다시 읽어 확인(E :107·:113·:120–122·:125·:126·:130·:131·:133·:136·:139·:236·:240·:242·:253·:256·:265·:320·:330·:333·:346·:487, EVAL :182·:184·:186, M4 :150·:155·:188·:232·:258·:263·:276·:285·:287·:340, labeler :11–12, 계획 :9–14). 코드 줄은 6e3fda6 기준(3a3d76c·a4cddad와 블롭 동일). "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c24\check24.py`(A–H·S·V·R, 57/57), `verdict24.py`(M1–M8, 10/10), `ctrlscan24.py`, `refcheck24.py`; **파드** = §6(`pod_cpu24.sh`, `pod_eval24.sh`, `data24.py`, `pod_isaac24.sh`, `closed24.py`, `c1_24.sh`·`c1rows24.py`, `conf24.py`, `verdmeta24.py`, `who24.sh`). "시험 묶음" = 해당 구현을 부르는 저장소 시험이 로컬 1014·파드 1130 묶음에서 통과. 모든 경계값은 21·22·23회차와 다르게 새로 골랐다.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149(TEST2 1150–1299) / TEST-P5 1300–1329 / POOL 2000–2119 / R2_TRAIN 10000–59999 (E :113-120, §66) | `eval/splits.py`, `datagen/gen.py` | 로컬 A1 새 경계 24값(3·17·26/33·496·503·540·546/553·1003·1120·1148/1150·1299·1301·1328/1331·1997·2001·2118/2121·9997·60000·−1) 모두 기대 분할, A2 `test_p5`는 env 없음·`test`·`cal` 거부/`test_p5` 통과, `cal`에 `pool` 거부/`cal` 통과, dev·pool 무조건 통과, A3 "Dev"·" pool"·"calib"·"test-p5"·"r2"·"" 거부, A4 [3, 26, 33]·[2118, 2121] 통째 거부·문자열 시드 수용, A6 R2 가드 12경우(3·26 무확인 허용, 33·60010·2060·520·1120·9990·1320 거부, 10003·59980 확인 시만), A7 10080·59980·20000 eval, 10081·59981·33333 fit; 파드 가드 27건 rc 1(§6.4) | 일치 |
| 2 | POOL 120 × 10, 경계 30 % 과표집 (E :121, §76 D-2) | `sim/snapshot.py:29-31` | 코드 무변경, 시험 묶음 | 일치(주석 S14) |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` | 시험 묶음 | 일치 |
| 4 | 분할 = 에피소드 (E :122) | `stagea_data.split_of`, `calib.halves` | 시험 묶음; 파드 `CALIB_DONE` | 일치 |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py`, `config.py` | 시험 묶음; 파드 Isaac **DEV 11** C5·C5' 성공(15.26 s, `terminations` success 1) | 일치 |
| **6** | 호출 기록: 질문별 확률·요청/응답 원문(E :125), Astra A6(E :126, §28) | `core.py` | **파드 DEV 11 C5·C5' 결정 호출 92행**: `sha256(request_blob)` = `request_sha256` 92/92, 이미지 해시가 요청 본문에 92/92, 응답 blob 해시 92/92, `probs` 질문 = `answers` 질문·합 1·[0,1] 92/92, `canary_id` 92/92, `question_id@vN` 92/92; Astra 4행: 요청 해시·머리캠 JPEG 해시·effort low(행·요청 본문)·600·`output_text` 4/4 | 일치 |
| **7** | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `analysis/stats.py` | 로컬 E3 일반 경로 = 군집 합 경로(새 37군집·seed 13), **E4 군집 안 행 1배 대 4배 → 구간 동일**; 파드 closed `meta.bootstrap` n_boot 10000·seed 0·percentile | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate`, `stats.cluster_diff_ci` | 파드 C5 대 C5' 같은 워커 | 일치 |
| **9–12** | 판정 2 Holm, 판정 10, 카나리 Holm, 판정 절 해시 (E :131, :265, :139, :133) | `stats.holm`, `canary.py`, `eval/common.py` | 로컬 E5 **다섯 가설을 정확한 문턱값에**: (0.01, 0.0125, 0.05/3, 0.025, 0.05) → 모두 기각, 둘째 0.0126 > 0.05/4 → 첫째만 기각(입력 순서 뒤집어 줌), 두 가설 (0.025, 0.05) → 둘 다 기각; `meta.prereg` OK | 일치 |
| **13, 85** | 카나리 기준일 = 같은 세트 × 같은 `question_id@vN` 집합의 첫날 (E :136-140, §79 D2) | `eval/canary.py` | 로컬 G1: 다른 세트 실행 건너뜀, 상위 집합 맵 = 다른 사슬(r1), 키 순서만 다른 같은 맵 → 첫 실행 r2, 한 질문 판본만 다른 맵(m@v3) = 다른 사슬(r3), 다른 세트에 없는 맵 → None | 일치(N11) |
| 14 | 모델 식별 필드가 바뀌어도 같은 처리 (E :139) | `Calibration.load`, `latest_canary` | 시험 묶음(코드 무변경) | 일치 |
| 15–17 | E0.5 표·재시험·같은 시각 K = 3 (E :236-238) | `e05.py` | 시험 묶음; 파드 `e05 --data jsel_dev/P2 --split dev --episodes 4` → `E05_DONE` | 일치 |
| **18** | γ 2/3 (E :240, M4 :276) | `m4.share_at_least` | 로컬 B1 새 비율(16/24·22/33·3000/4500·9/13·5/7 참, 21/32·2999/4500·2/4 거짓) | 일치 |
| 19–20 | `C_flip` 두 식, A0–A4·층 (E :242, :246) | `e05.py` | 시험 묶음 | 정본 기록(§73) / 일치 |
| **21–28** | 판정 1–10 경계 (E :256-265) | `replay.judge_e05`, `stats.at_least/below` | 로컬 E1 CMP_EPS: `at_least(0.7+0.1, 0.8)` 참, `below(0.8, 0.7+0.1)` 거짓, `at_least(0.05−1e-11, 0.05)` 거짓·`below(같은 값)` 참, `at_least(0.05−5e-13, 0.05)` 참(상대 1e-12 안); 파드 `E05_DONE` 2회 | 일치 |
| 29, 89 | FLIP_TH 후보 α 0.01·범위 (E :253, :487; M4 :285) | `e05.py` | 시험 묶음 | 일치 |
| 30 | 같은 시각 뒤집힘 성공·섭동 따로 (E :253, §27) | `e05.py` | 시험 묶음 | 일치 |
| 31–33 | d_p95 = E0 값, 분당 400 [가정], E1 반분 | `M4Params.d_p95_init`, `calib.halves` | 시험 묶음; d̂ 이동 창은 행 45 | 정본 기록 |
| 34–35 | ECE 15 동일 질량, 오답 < 30 판정 불가 (E :320) | `calibration.ece_mass` | 로컬 E6(600예측·15구간 → 0.3177 ∈ [0, 1]) | 일치 |
| **36** | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat` | 로컬 E2 새 n(유리수 기준값과 대조): 99·α 0.05 → 95, 18·0.05 → inf, 20·0.05 → 20, 9·α 0.1 → 9(10 × 0.9 부동소수 경계), 8·0.1 → inf, 149·α 0.01 → 149 | 일치 |
| 37–43 | log p 자름·질문별 온도·원 확률·판정 1·7·8·`ambiguous` ECE 제외 (E :333-346) | `calibration.py`, `core.py` | 시험 묶음; 파드 `calib --heldout jsel_dev/P0 --episodes 4` → `CALIB_DONE` | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| **45** | N_max = ⌈d̂/T_c⌉+1, d̂ = 최근 50회 p95 (M4 :258, :263) | `m4.CommitLedger.n_max`, `d_hat`, `d_window` 50 | 로컬 B9: d̂ 1.65 → 6(정확히 5.0 경계), 1.6501 → 7; **창 50**: 1..70 ms → 68 ms(21..70의 48번째), 1..49 ms(n 49) → 47 ms(⌈46.55⌉ = 47번째) | 일치 |
| 46–49 | γ·W·비가역 W+1·τ | `m4.py` | 시험 묶음; B8 기본값 | 일치 |
| 50 | conformal α 0.01·w 5 ((b) 경계) | 확인 헤드 보정 파일 | 기본 미보정 | SCOPED S5 |
| **51** | STALE_MAX 1.5 s (E :487) | `m4.older_than` | 로컬 B3: **250 Hz** 틱 위치 1,000곳 모두에서 375틱 유지·376틱 버림, B4 +9.5e-10 유지·+1.05e-9 버림(T_EPS 1e-9 바로 양쪽) | 일치 |
| 52–53 | C2 = VLM Stream, C0–C6 설정 (M4 :329-345) | `conditions.py`, `m4.py` | 파드 `--conditions "C5,c5'"` → "refused before any worker"(가드 16) | 일치 |
| **54** | C5 = §4.2 전체, C5' = (b) 범주 뺌(줄은 none), 판정 3 (M4 :155, :232, :340-342, :361; §77 보충 (3)) | `core.b_line`, `core._boundary` | **파드 Isaac DEV 11**: C5 `last_step` {none 1, OK 30, LAG 7, DEVIATE 6, CONTRADICT 2}, C5' none 46/46, 요청 본문 마지막 `last_step:` 줄 = 행 값 92/92 | 일치 |
| 55 | H 1과 3 (정본 §2, M4 :188-189) | `m4.early_ask_steps`, `M4Params.H` | 로컬 B8 기본 H 3; 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 |
| **56–58** | n_LA 2·조기 호출 당겨 씀·FLIP_TH 끔; H = 1 = 같은 스텝 앞당겨 2~3회 (§75) | `m4.py`, `core.py` | 로컬 B5 다섯 창을 **정확한 유리수 창과 대조**: (0.66, 0.33, 0.33, 1.32) → [3..6](양 끝 0.99·1.98 정확 경계), (0.1, 0.23, 0.33, 0.5) → [1](하한 정확 0.33), (1.0, 0.32, 0.33, 0.99) → [4..6], (0.5, 0.9, 0.33, 0.8) → [5](창 빔 → d 뒤 첫 스텝), (0, 0, 0.33, 0) → [0](창 한 점); B8 n_LA 2·FLIP_TH None | 일치 |
| 59 | 경계 직후 W 2·γ 1.0 등 | 없음 | §73 D5 | SCOPED S9 |
| **60** | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.select_rule` | 로컬 E7: 0.72 − 0.70(부동소수 0.020000000000000018) → plan, 0.72001 → time0.33, 오라클 0.9 단독 → plan(적격), 0.89999 단독 → None | 일치 |
| 61–62 | 폐루프 RD 재표집 = layout 짝, 주 RD = Score (EVAL :182-184) | `closed.py`, `rd.py` | 파드 `rd --variants standard=jsel_dev,dr=gen_dev/dr/P0 --episodes 2` → `RD_DONE` | 일치 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | §71 보충 | SCOPED S1 |
| 64–65 | M4b 2,000회, E-M4-lat 비례 STALE_MAX | `m4b/*` / 없음 | §72 예외 / §74 보충 | 일치 / SCOPED S11 |
| **66–67** | H = 1 창·`lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py:165`, `:390` | 로컬 B8b `M4Params(lead_max=nan / inf / 0 / −0.5)` 모두 거부; 파드 `--m4-lead-max nan`·`inf` → "refused before any worker"(가드 14·15); B8 기본 1.0 | 일치 |
| 68 | E0 판정 4 | `analysis/latency.py` | 시험 묶음 | 일치 |
| 69 | E-M4 판정 7 | 없음 | §75 보충 (2) | SCOPED S12 |
| 70 | FROZEN = 송신 시각 기준 (M4 :150) | `m4.py` | §77 N3 | 정본 기록 |
| 71, 93 | 카나리 표류 → J5 끔, 재보정 뒤 재사용 (E :139, :347, §77 N6, §79 D3) | `closed.j5_after_canary`, `canary.latest_canary` | 시험 묶음(코드 무변경) | 일치(N11) |
| 72–76 | 응답 모델 필드·재시도 기록, E0.5 정답, `fine_dir`, Astra 카나리 | `models`, `common` | §77 N4·N5, §67 보충; 파드 결정 호출 `canary_id` 92/92 | 일치 / SCOPED S13·S6 |
| 77–79 | (b) 범주 줄·런타임 값·경계 틱 호출 = 방금 끝난 스텝 (M4 :232, §77, §79 N1) | `core.b_line`, `core.act` | 행 54; 시험 묶음 | 일치 |
| **80–84** | 학습 자료 값·C5' none·ser-A-min-2·옛 체크포인트 거부 (§77 (iv), §77 보충 (1)) | `serialize.with_last_step` | 로컬 D2 `LAST_STEP_VALUES` 닫힌 집합, "Lag"·" OK"·"none " 거부, "CONTRADICT"·"none" 수용 | 일치 |
| 86–88 | 결정 호출 행 `probs`·blob·`last_step`, Astra 원응답, 결정 이미지는 해시만 | `core.py`, `reqhash.request_body` | 행 6 | 일치 / 정본 기록 |
| 90 | FLIP_TH = 성공 실행 flip_score의 1−α 분위, 질문별 (M4 :287, §79 D1) | `e05.flip_th_conformal` | 시험 묶음(같은 순위 규칙 = 행 36) | 일치 |
| 91–92 | 같은 시각 뒤집힘 성공·섭동, 층별 A0 대비 flip | `e05.py` | 시험 묶음 | 일치 |
| 94 | E0 판정 4 집계 (§77 N7) | `latency.step_votes`, `judgment4` | 시험 묶음 | 일치 |
| 95–97, 105, 115–117, 119 | S-E2E 설정·판정 (a)–(e)·재개·evalck·판정 스크립트 입력 검사·고정본 (`prereg_se2e.md` §3·§4, §77 보충 2, §80 N1) | `tools/se2e/se2e_verdict.py` | 코드·로그 무변경(3a3d76c 대비 블롭 동일); 시험 묶음 | 일치 |
| **98** | 라벨 복원 기준(비트 동일, §78 (1)) | `stagea_data.replay_bit_identical` | 로컬 D1 새 8경우(N2) | 일치(N2) |
| **99** | 에피소드마다 PhysX 장면 재생성, 모든 호출자 기본 (§78 결정) | `sim/scene.py` | **파드 Isaac 한 워커 C5 → C5'(DEV 11, 모의 선택기, 17:37:56–17:42:27 UTC)**: 행동 **1,526개 비트 동일**(첫 차이 없음, 행동 시각열 동일), 호출 46개·Astra 2개 같은 수·같은 시각, `code_sha` `a2a7c8394ad45fd6` | 일치(행렬 S16) |
| 100, 118, 132 | 라벨 신뢰 = 재생 비트 동일, 뺀 수와 질문 범위 기록 (§78 (1), §80 D1, §81 N3) | `eval/common.load_truth` | 파드 `e05 --split pool --seeds 2011,2066,2113 --truth outcome:plan` → rc 0, `E05_DONE` | 일치 |
| 101 | R2_TRAIN은 하드 리셋 빌드, 옛 녹화 처리 보류 (§78 (2)(3)) | 파드 실행(읽기만) | GPU 0·1 R2_TRAIN Isaac 워커 진행 중(`--seeds 10000-10599 --confirm-train`) | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 선택 거부, `determinism` 시드 검사가 `--out` 앞 (§79 N5, §80 N3) | `eval/common.load_episodes`, `sim/determinism.py` | 가드 22(`fresh --seed 1150`)·23(`history --seeds 540`) → "only DEV 0-29 and POOL" rc 1·폴더 없음, 가드 24(`canary build-set --seeds 1310-1311`)·25(`e05 --split pool --seeds 2060`, P0) → "no episode selected" | 일치(e05 폴더 N10) |
| 103 | Isaac 워커 `OMP_WAIT_POLICY=PASSIVE` (§79) | `closed.worker_cmd` | 내 Isaac 워커가 이 명령으로 돌아 `CLOSED_DONE`; `--isaac-gpu 3`·`2` rc 1(가드 12·13) | 일치(N34) |
| 104 | e05 qid 등록부 기본 = `<out>` (§79) | `e05.py` | 시험 묶음 | 일치 |
| 106–114, 133–136 | S-E2E 진단 D1–D3·§7 규모 곡선 (`prereg_se2e_diag.md`) | 파드 고정 사본, `se2e_diag.md` | 코드·로그·문서 불변(3a3d76c 대비) | 일치(N5·N6) |
| 121–129 | E-TC(`prereg_se2e_temporal.md` §2–§8): 옵션 끔 = 기준, V 구성, M 구간·드롭아웃, 지표·층, 채택 규칙, 판정 재현 | `se2e_temporal.py`, `temporal_verdict.py` | `temporal_verdict.py` `992d3e20…` = 등록(`check24` H2); 로컬 F1 Δ 0.3 s: 30 Hz k 10·31 → 1·22, 10 Hz k 4·17 → 1·14; **F2a 팔 구간을 관절 속도 노름으로**(세 관절 2-3-6-7 분할: 하한×0.9999999 still·×1.0000001 slow·상한×0.9999999 slow·×1.0000001 fast·1e-12 still), F2b 그리퍼 1.000001배 opening/closing·0.999999배 still, F3 20 Hz [1, 1.5, 1.5, 0.25, 4, 4] → [0, 10, 0, −25, 75, 0], F4 50,000표본 0.2997·(스텝, 시드) 난수·다른 시드 다름·전역 불변 | 일치(N14·N20) |
| 130–131 | §81 N2 재개 검사 키, §81 N10 라벨 쓰기 null | `stageb_train.py`, `cli_label.replay_max` | 파드 시험 통과 | 일치(N2) |
| **137** | Astra 호출 주기 = 하트비트(응답 + N, N = 5 s) + 단계 경계 + 사건, in-flight 1, 15 s → 재송신, gpt-6-astra·low·600 (§45; 실행 중 low = §82 보충 2) | `runtime/astra_hb.py`, `core.py` | 로컬 C1 송신 1.5 뒤 2.0 없음(진행 중), 응답 4.75 뒤 9.7499 없음·9.75 hb, C2 송신 9.75 → 24.75 유지·24.7500001 초과, C4 모델·effort·600; **파드 판 Astra: hb 5.0 → 8.0, 경계 sub 8.59 → 11.59, 겹침 0**(종료 15.26 전 다음 hb 없음) | 일치(N4) |
| 138 | LeRobot v2.1 내보내기 = ROBOTIS 형식(§63), 30 Hz·원본 해상도·관절 행동(§66) | `datagen/lerobot_export.py` | **파드 새 2편**(dr/mug_tray ep3·standard/mug_tray ep0, 둘 다 `valid_for_training` 참) `export` → 2편·535프레임, `verify` 오류 0·PSNR 최소 39.67 dB·lerobot 0.3.3 적재 535프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참; LeRobot 시험 6 passed | 일치 |
| 139 | R2 DEV 구조 검사(§66, 완료 정의 1) | `datagen/validate.py` | 파드 `/data/harvest/r2/dev/*/*/P0` 전 편 **36/36 오류 없음**(6폴더 × 6), `valid_for_training` 메타 불일치 0; **음성 대조 3종**(dr/mug_tray ep2, 261프레임): 무수정 사본 오류 0, 가운데 프레임 `t` +2e-6 s → "frame time off the 30 Hz grid by 2.00e-06 s", k87 `cam_head` 경로 누락 → "k87: missing cam_head"·"images 521 != frames 261 x cams 2", `hold_n` 한 값 +1 → "hold_n does not add up to the episode duration" | 일치 |
| **140** | 정본 §82: 강등·J1–J6·K5 모드 등은 "구현(다음)·R7 관문 뒤" | 없음(현 구현 = §45 K0–K4) | 로컬 C3·C5, 파드 가드 26·27 | SCOPED S18 |
| **141** | 정본 §83: 움직임 줄 채택·V 불채택; 누수 수정·확인 실험·런타임 적용은 다음 일 | 누수 수정·확인 등록 = 행 142–150; 런타임 없음 | `check24` D3, 파드 요청 92/92 `motion:` 없음 | 일치 / SCOPED S19·S20 |
| **142** | 속도 누수 수정: v[k] = (x[k] − x[k−1]) × 10 Hz, v[0] = 0, = `backward_velocity` (`prereg_se2e_motion_confirm.md:10`) | `harvest/train/se2e_data.py:134-140`, `:185` | 로컬 V1 61×19 무작위 보행에서 손 계산과 비트 동일, V2 모든 k에서 `backward_velocity`와 비트 동일, V3 k = 0·7·30·59 뒤 모든 프레임을 x² − 11로 바꿔도 0..k 행 불변, V4 1프레임 → 0, V6 5 Hz = 0.5배, V7 `episode_rows`(RB2 19차원, 보폭 3) 행마다 자기 팔 후방 차분·k = 0 행 0; **파드 `c1rows24`: 7행마다 1행(RB1 3,633·RB2 2,483, k = 0 행 109·121) 원본 parquet에서 내 코드로 계산한 후방 차분과 일치(최대 오차 0.0), 나머지 필드 = 옛 행, `motion_src` = 행 속도·`k_prev` = max(0, k−3)** | 일치 |
| **143** | 재변환: qd·grip[1] 외 모든 필드가 같지 않으면 멈춤, `hist_fields` 추가, 현재 프레임은 링크 (`:11`) | `tools/se2e_convert.py:241-337` | 로컬 R1 속도만 바뀐 새 행 수용·나머지 = 옛 행(두 카메라 이미지 포함), **R2 새 12종 변경 거부**(seed, arm, H, bimanual, split, `action_full` +1e-12, `state_full` ×(1−1e-13), `names_full`, `proprio_mask`, grip[0] +1e-9, `fps_src`, `action_script` +1e-10), R3 옛 행에 필드 빠짐·새 행 하나 빠짐·한 행 중복 거부, R5 `--hist` 행, R6 `--conv` = `--src`·`--conv` = `--src` 부모·`..`로 `--src` 아래를 가리키는 경로·`--src` 아래 상대 경로 → rc 1(폴더 안 만듦), 기존 출력 "exists" rc 1·파일 불변; **파드: 등록된 `reconvert --hist`를 22·23회차와 다른 10편에 다시 돌린 출력이 `se2e_c1` 같은 줄과 바이트 동일(152·103줄)** | 일치 |
| **144** | 판본 `se2e_c1` 표 (`:12-23`) | 파드 `/data/harvest/data/se2e_c1`(읽기만) | `sha256sum -c SHA256SUMS.txt` **5/5 OK** — 23회차 확인 뒤 불변 | 일치 |
| **145** | 분할·키 불변: train 37,484 / val 1,799, 결정 프롬프트 입력 불변 (`:22`, `:24`) | `se2e_data.load_se2e`, `stageb_train.stratified_val` | 파드 네 판 학습 로그 `config`: `n_train` 37,484·`n_val` 1,799(4/4); 판정 파일 `n_val_snapshots` 1,799(N43) | 일치 |
| **146** | 설계: (single, none)·(single, motion) × 시드 1·2, 2,000스텝·묶음 8·lr 1e-4/1e-4·워밍업 3 % + 코사인·검증 300(150/0)·500마다 평가, motion 칸 `--motion-line se2e-motion@v1 --motion-bins se2e_c1/motion_bins.json`·드롭아웃 0.3, GPU 2 = none_s1 → motion_s1, GPU 3 = none_s2 → motion_s2 (`:26-31`) | 파드 판 로그 `config`, 드라이버 기록 | **`conf24`(네 판 모두 끝난 뒤)**: 네 판 묶음 8·`max_steps` 2000(학습 사건 2,000, 마지막 스텝 2000)·lr 1e-4·`lr_heads` 1e-4·시드 1/2·`val_per_kind` 150·`val_seed` 0·`eval_every` 500(평가 사건 5개, 값 안 읽음)·`se2e_root` = `se2e_c1/conv`·cosine·부분집합 0·`init_weights`/`resume` 빈 값·IMG·KI stop; motion 두 판 `motion_line` se2e-motion@v1·`motion_bins` se2e_c1·드롭아웃 0.3, none 두 판 `motion_line` none; lr 네 판 모두 워밍업 60 + 코사인과 최대 차 8.1e-4 × 1e-4; 드라이버: GPU 2 none_s1 → motion_s1, GPU 3 none_s2 → motion_s2, 각 판 뒤 predict300 → predictfull | 일치 / 결과는 SCOPED S20 |
| **147** | 지표·판정: e_s, 합동 = ½(e_1 + e_2), 스냅샷 군집 부트스트랩(네 판 같은 추출, 10,000, 시드 0, 95 %); 확인됨 ⇔ 합동 ≥ +0.015 ∧ 하한 > 0(엄격) ∧ 합동 전이 ≥ −0.01, CMP_EPS 1e-12 (`:33-42`) | `tools/se2e/motion_confirm_verdict.py:27-28,32-67,90-93` | **로컬 `verdict24` 10/10**(스냅샷 1,000 = 전이 400·정상 600, 3,000항목, 보기 3개): M1 (30 + 60)/2/3000 = 정확히 +0.015(정상 행만)·전이 0 → 확인됨, M1c 89/6000 → 거짓; M2 **시드마다 다른** 전이 손실 −8·−16/1200 → 합동 정확히 −0.01 → 참, −25/2400 → 거짓(전체 +0.079여도 확인 안 됨); M3 같은 네 판 → 하한 정확히 0 → 거짓, 손실 45+45 → 합동 −0.015; M4 기준선이 다른 두 시드 +0.02·+0.04 → 합동 0.03·변동 +0.02, 교환 → 합동·구간 같고 변동 부호만; **M5 내 재구현 = 세 층 구간 모두 오차 0**(N29); M6 1,799 입력 `n_val_snapshots`·`label`·`rule` 기록; M7 판 이름 중복·판 누락·모르는 판 이름 rc ≠ 0(빠진 항목은 N3); M8 acc = 항목 평균·NLL = 3보기 −log p; **파드 판정 파일 구조: 1,799·네 판 같은 항목 수·규칙 블록 = 등록(N43)** | 일치(N3·N24·N29) |
| **148** | 판정 스크립트 해시 `fa7299062cc5e1d1`·코드 해시 (`:42`, `:47-48`) | 파드 `code_se2e_confirm`, 판 `CODE_HASHES.txt` | 로컬 H2 = archive 블롭, H3 무수정 3개 = CRLF 형태(N23); 파드 네 판 `CODE_HASHES` 등록값 6/6(4/4), 확인 사본 판정 스크립트 sha16 = 등록, 사본 `harvest/`·`tools/`·`tests/` LF 내용 = 6e3fda6(차이 0) | 일치(N23) |
| **149** | 등록은 어느 판도 학습하기 전; 결과 뒤 문턱·층·검증 집합·구간값 불변 (`:1-3`, `:5-7`) | 커밋·로그 시각 | N26; 6e3fda6까지 등록 문서·판정 스크립트 변경 없음; 판정 파일 17:21:44Z = 모든 예측(17:20:49Z) 뒤, 사본 스크립트 = 등록 해시 | 일치(N26) |
| 150 | 하지 않는 것: `se2e`·`se2e_t` 덮어쓰기, `PROMPT_FILES`·`stageb_data`·`stageb_model`·`harvest/runtime` 수정, GPU 0·1, 유료 API, CAL/TEST (`:52-53`) | 파드 실행 | 옛 `se2e/conv` 행이 `c1rows24`·재변환의 원본으로 온전(재변환 출력 = 판 폴더 줄), 판 GPU 2·3(드라이버 기록), 사본의 `harvest/runtime` 등 = 6e3fda6 | 일치 |
| **151** | 정본 §82 보충 2: 실행 중 Astra effort = low, high는 비교 실험·오프라인 일에서만 (`00-interfaces.md:741`) | `astra_hb.py:33` `EFFORT` "low", `core.py:265`·`:268`·`:413`, `RuntimeConfig.astra_effort` `:79` | 로컬 S1·S2·C4; **파드 Astra 4행: 행 effort low·요청 본문 `"effort": "low"` 4/4**; §84 보충 1·스펙 §15 "high는 흐름에 쓰지 않는다"와 같음 | 일치(N28) |
| **152** | **정본 §84·보충 1·2: 결합 설계 승인(구현은 R7 E2E 준비 기준점 뒤), falsify 먼저 평가·재사용 한 번 상한, Astra 흐름 호출 = 동시 1개(답 직후 최신 관측으로 다음 요청), 비용 상한·80 % 정지, §82 '편당 1–3회'를 흐름에 한해 대체 (`:743`–`:756`)** | 없음(현 구현 = §45 K2) | 로컬 C3("serial"·"K5"·"k2" 거부)·C5(K2, 5 s)·S3(Astra 이미지 1장)·S5(`falsify`·`trace5`·`eetrace` 0곳), 파드 가드 26·27, DEV 11 Astra 겹침 0·답 뒤 5 s; 새 정본 문장과 기존 정본·코드의 현재 시제 대조(§6.2): 모순 없음(§82 호출 정책 대체 범위 명시, N18·N35·N37) | SCOPED S18 / NOTE |
| 153 | 정본 §84 E-MA1: 사전 등록을 첫 학습 전에 커밋, G0 먼저, `PROMPT_FILES_B` 해시 불변(새 옵션 파일), GPU 2·3이 빈 뒤 (`:746`) | 대상 트리에 없음 | 파드 17:31 UTC: `tmp/ma1` G0 준비 파일만·학습 프로세스 0; `PROMPT_FILES_B` = (`stageb_data.py`, `stageb_model.py`)(`stageb_train.py:56`) 블롭 불변(H3) | SCOPED S21(N40) |

### 5.1 23회차 표와의 차이
- 행 152를 "결합 스펙 초안"에서 **정본 §84·보충 1·2**로 바꾸고 행 153(E-MA1 등록 규칙)을 더했다. 판정 변화 없음(모두 일치·SCOPED·NOTE). 근거 교체: 행 1(새 경계 24값·R2 12경우·새 가드 27건), 5·6·54·99·137(새 시드 DEV 11, 92행, 행동 1,526개), 7(1배 대 4배), 9–12(다섯 가설 정확한 문턱), 13(판본 다른 맵), 36·45(창 50, n 49)·51(250 Hz)·56–58·60·66–67(nan·inf 거부)(새 경계값·유리수 기준), 121–129(세 관절 노름 분할·20 Hz), 138(다른 두 편), 139(다른 편·새 음성 대조 3종), 142–149(22·23회차와 다른 재변환 10편·7행마다 표본·네 판 끝난 설정·판정 파일 구조).

## 6. 확인한 것 (근거)

### 6.1 변경분·23회차 정정 확인 (과제 1·2)
- `git diff a4cddad 6e3fda6`(문서만): 정본 `:741` 끝 표시 토막(23회차 N21·N22), 새 §84(`:743`–`:748`)·보충 1(`:750`–`:753`)·보충 2(`:755`–`:756`, N18 대체 범위 문장 포함); 스펙 `:17` "읽는 법"(N17)·§14–§16(`:166`–`:194`); handoff `:3` 시각·§2.8 `:117`(22회차, "[→ 추가 … 23회차 D-1]" 표시)·`:118`(23회차); draft-log `:465`·`:466`; direction-log `:69`·`:70`; `se2e_data.md:62` 표시를 비고 칸 안으로(N25); user-log 85·86; MolmoAct 연구 문서 새 파일; `r7_cycle23.md`. 코드·시험·사전 등록 변경 0.
- 23회차 권고 반영: §7-1(D-1 + N27) **모두 들어감**, 보고서와 같은 커밋(`git show --stat 6e3fda6`); §7-2 선택 항목 중 N25 해소, N21은 표시만(위치 표시 없음), N7 연구 문서 표시·N29/N3 결과 문서 한 줄(결과 문서는 대상 뒤)·N31 코드는 안 들어감(선택). §7-3 확인 항목: §84가 §82 호출 정책을 덮는 범위를 명시했는지 → **예**(`:756`), §82 [결정 필요] → §84가 해소(`:747`), 승인된 스펙에 N17 옛 문장 → "읽는 법"으로 처리(상태 줄·머리 문단은 N17), **handoff 핵심 결정·대기 항목이 §84를 반영하는지 → 아니오(D-1)**, 확인 실험 판정 파일 → 등록 규칙·해시대로(N43, 결과 문서는 대상 뒤).
- **제어 문자·줄 끝 전수**(`ctrlscan24.py`, archive 텍스트 461파일): `\r\r\n` 0, 외톨이 `\r` 0, CRLF 0, `\t` 0, 기타 C0·C1·영폭 문자 0, BOM 0, UTF-8 아님 0. 끝 줄바꿈 없음 1(`prereg.json` — 해시가 고정한 원문). 변경된 md 9개의 표 행 칸 수 = 머리 칸 수(불일치 0).

### 6.2 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외)
- falsify(`falsify`): 정본 `:199`(M10 필드)·`:730`(§82 [결정 필요] — §84 `:747`이 "해소"라 적어 뒤 절 우선)·`:747`·`:751`, 스펙 `:131`(§10 열린 결정 — 같은 문서 `:175`가 "정본 §84로 해소")·`:187`, `astra_role:239`·`:515`(N7), **handoff `:88`(D-1)**, user-log `:365`. 그 밖 M10·SUMMARY는 필드 정의.
- 대기·초안 표지(`결정 필요|검토 전|확인 대기`): handoff `:88`(D-1), 스펙 `:3`(N17); 나머지는 옛 판 기록(draft-log 앞부분, handoff §2.6 이전 규칙).
- 호출 방식 어휘(`계단식|1 Hz|동시 ≤|겹쳐 부르|직렬 1개`): Astra 흐름 호출을 계단식으로 적은 곳은 스펙 `:7`·§3·§15(대체 표시 `:17`·§16, N17)와 정본 §84 보충 1 `:753`(N35)뿐; `CLAUDE.md:48`·정본 `:11`·`:67`·SUMMARY `:140`·M4·D25는 하위 VLM(Jev→VLA) 겹침 호출(사용자 요구 — §84 보충 2와 대상이 다름, N8); 정본 `:410`은 GPT-as-Policy 인용. 지금 코드 구조를 계단식 Astra로 적은 현재 서술 0.
- 새 정본 문장 대 코드(현재 시제): §84 "기존 체크포인트 해시(`PROMPT_FILES_B`의 `stageb_data.py`·`stageb_model.py`)" = `stageb_train.py:56`; 보충 2 "늦게 온 답 처리·두 답 합의 유지" = 스펙 §3·§11(미구현, S18); 스펙 §15 "`core.near_contact` ≤ 5 cm" = `core.py:44`–`:54`(`CFG.near_in_m` 5 cm). 틀린 코드 서술 0.
- 회차 상태(`2[2-3]회차|연속 무결`): handoff `:117`·`:118`, draft-log `:465`·`:466`, direction-log `:69`·`:70` — 모두 커밋된 결과와 같음.

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st` + 코드 사본으로 R2 DEV 전 편 `validate_episode` **36/36** + 음성 대조 3종 검출; LeRobot 시험 6 passed; 새 두 편 내보내기·검증·lerobot 적재(행 138). S-E2E 판 `se2e_c1` 해시·재변환·표본 재계산(행 142–145). |
| 2 모델 | 충족(CPU) | GPU 학습 없음 → CUDA 시험·GPU 재적재 건너뜀. 파드 CPU 스모크(N32), CPU 묶음의 `test_stageb_torch.py`·`test_r7c15_resume_keys.py`·`test_se2e_temporal_qwen.py`·`test_se2e_reconvert.py`·`test_se2e_motion_confirm_verdict.py` 통과. |
| 3 폐루프 | 충족 | Isaac 한 워커(`closed --model mock --split dev --seeds 11 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c24`, 17:37:56–17:42:27 UTC, `IR_INST` `r7c24_standard`): `CLOSED_DONE` C5·C5' 성공 1.0, 15.26 s, 호출 46·오류 0, 확정 비율 0.8979, 결정 3.016/s, 행 필드·blob(행 6), `meta.bootstrap` 10000, `prereg` OK, git `6e3fda6d`, `code_sha` `a2a7c8394ad45fd6`, 하드 리셋 빌드 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 17:35:00–17:35:38 UTC): `e05`(P2, 4편) → `E05_DONE`, `rd`(standard + dr/P0, 2편) → `RD_DONE`, `calib`(P0, 4편) → `CALIB_DONE`, `e05 --split pool --seeds 2011,2066,2113 --truth outcome:plan` → `E05_DONE`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래(내 업로드 사고는 N41·정리 완료), `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.6). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`, 17:34:52–17:35:00 UTC, 21–23회차와 다른 값)
- 1 `e05 --data P0 --split test --seeds 1075`, 2 `e05 --data P2 --split cal --seeds 525`, 3 `calib --fit-split test_p5`, 4 `calib --heldout-split test`, 5 `rd --split test_p5`, 6–8 `closed --split test --seeds 1111`·`cal 511`·`test_p5 1315` → "refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 5,45`, 10 `pool --seeds 2200`, 11 `dev --seeds 520` → "not in split … never opened"; 12–13 `--isaac-gpu 3`·`2` → "(GPU 2 never renders)"(N34); 14 `--m4-lead-max nan`, 15 `--m4-lead-max inf`, 16 `--conditions "C5,c5'"` → "refused before any worker"; 17 `HARVEST_ALLOW_SPLIT=test_p5` + `closed --split test --seeds 1001`, 18 `=pool` + `e05 --split cal` → 거부; 19 `gen --seeds 35000`(확인 없음), 20 `--seeds 60001 --confirm-train`, 21 `--seeds 1329 --confirm-train` → 거부; 22 `determinism fresh --seed 1150`, 23 `history --seeds 540` → "only DEV 0-29 and POOL"; 24 `canary build-set --seeds 1310-1311` → "no episode selected"; 25 `e05 --split pool --seeds 2060`(P0) → "no episode selected"; **26 `closed --hb-mode K6`, 27 `--hb-mode k2` → "from ('K0', …, 'K4')"**(§82 K5·§84 흐름 호출 미구현이 워커 전에 거부됨). **27건 모두 rc 1**; 출력 폴더는 25번(e05)의 빈 폴더 하나(N10), 나머지 0.

### 6.5 A. 테스트
- 로컬(`…\r7c24\repo` = 6e3fda6 archive, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider -q" --basetemp=D:/tools/scratch_qdd/r7c24/pt`): EXIT 0, **1014 passed · 15 skipped**(torch·isaaclab·inspect_robots 없음, pyarrow LeRobot, P3 스텁).
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, TMPDIR·pyc·카나리·qid 등록부 = scratch): **1130 passed, 4 skipped**, EXIT 0(17:34:49Z).
- 파드 LeRobot(`venv_e3st` + `r2/pylib_lerobot`·`pylib_pytest`): **6 passed**.

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함). 검토 시작 때 HEAD = 6e3fda6(작업 트리에 다른 에이전트의 미커밋 코드); 끝날 때 HEAD = ed478e4(N40) — 내가 만든 것 아님, 건드리지 않음. 로컬 C:에 이 검토의 산출물 없음(하네스 작업 출력 파일만). 로컬 `reconvert` 거부 시험은 내 임시 폴더 아래 경로만 썼고 거부 경로에 폴더가 생기지 않음(R6).
- 파드 정리(`clean24.sh`, 경로를 하나씩 적은 스크립트, `bash -s`로 보냄, 열린 핸들 0 확인 뒤, 17:45:19 UTC): `tmp/r7c24`(코드 사본·가드·평가·재변환 산출 포함), 내 Isaac 판이 만든 `tmp/carb.Zsmu6U`(생성 17:37:57Z)·`tmp/tmpfxfx7oe4`(17:38:15Z)·`cache/pyc_r6/data/harvest/tmp/tmpfxfx7oe4`·`cache/pyc_r6/data/harvest/tmp/r7c24`(17:37:57Z), `ir/kitcache/cyclo-r7c24_standard`(208 MB, 17:37:56Z). 판별: Isaac 앞뒤 목록 차이 + 생성 시각 + 워커 환경(N42). `ir/kitcache/cyclo-astram_refs`는 다른 에이전트 것이라 남김. 앞서 17:30 UTC에 파드 루트 `/C:` 트리 삭제(N41). 끝에 `tmp`·`kitcache`·`pyc_r6`의 r7c24 항목 0, `/C:` 없음, 명령줄에 r7c24가 든 프로세스 0. 확인 실험 폴더(`ckpt/se2e_confirm`, `logs/se2e_confirm`, `data/se2e_c1`, `code_se2e_confirm`)와 `tmp/ma1`·`logs/ma1`은 읽기만(예측 파일 열지 않음, 평가 값·판정 값 읽지 않음, ma1은 이름·시각만).
- 로컬 임시(`D:\tools\scratch_qdd\r7c24`: `src.tar`, `repo/`, `pt/`, `tmp/`, `tv/`, `pod/`, 스크립트·출력)는 다음 순회 대조용으로 남김(C: 아님).
- 절차(내 쪽): 파드 루트 쓰기 사고(N41). `check24.py` 첫 실행의 H2가 무수정 3파일의 등록 해시를 LF 블롭과 비교해 1건 FAIL → 등록값이 CRLF 사본 해시라는 23회차 N23대로 H3(CRLF 형태)로 나눠 57/57. `refcheck24.py` 첫 실행이 cp949 출력 오류 → UTF-8 출력으로 고쳐 다시 실행. `verdmeta24.py`는 네 판 수 비교 한 줄을 더해 다시 실행(값 출력 없음).

## 7. 다음 순회 전에 할 일 (제안)
1. **D-1**: handoff `:88` 대기 목록에 §84 정정 토막(falsify 먼저 결정·결합 설계 승인, 남은 대기 = 유료 실행 승인 — user-log 87 기준), `:84` 핵심 결정에 §84 한 토막, `:3` 시각. 정본에 [사용자 결정] 절을 더하는 커밋마다 handoff §2.7을 같은 커밋에 고치는지 `git show --stat`로 확인.
2. (선택, NOTE) N17 스펙 `:3` 상태 줄·`:7` "1 Hz 계단식" 표시, N35 §84 보충 1 셋째 항목 "[→ 보충 2]", N37 보충 2 "(해석, user-log 86)", N18 §82 강등 줄과의 관계 한 구절, N7 `astra_role:239`·`:515`·`:517` 표시, N38 draft-log §84 줄, N3 결과 문서에 "네 판 `n_items` 같음".
3. 25회차 대상은 ed478e4 이후 HEAD(확인 실험 결과·정본 §83 보충, E-MA1 사전 등록 + `tools/ma1/*`·trace 모델 시험 코드, G0 실패 기록, 탐침 사전 등록, user-log 87, `CLAUDE.md` 규칙), **연속 무결 0에서, 새 코드 포함**. 확인할 것: `prereg_ma1.md`의 해시 줄 = 커밋 블롭, `ma1_verdict.py`·`g0.py` 문턱(12/30 px 등)을 경계값 입력으로, G0 실패 뒤 "R2 시뮬로 옮김"(§84)과 기록(ee1b000)의 일치, 등록 시각 < 첫 G0 실행, `prereg_astra_motion.md` 예산(user-log 87 1.5만 원)과 정본 §82 보충(10만 원 한도)·user-log 76의 관계, 확인 실험 결과 문서가 판정 파일·등록 규칙과 같은지(N3·N29 한 줄 포함), Git Bash kubectl은 `MSYS_NO_PATHCONV=1`(N41).
