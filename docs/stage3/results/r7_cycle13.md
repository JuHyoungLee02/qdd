# R7 객관 검증 순회 — 13회차 (cycle 13, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님; `r7_cycle12.md` §5 표나 `r7c12_fixes.md`의 시험에 기대지 않고 사전 등록 원문에서 대조표를 다시 만들고, 행마다 **구성한 입력 → 실제 함수·런타임 출력**으로 확인함). 작성 2026-09-25 11:05 UTC 무렵(`date -u`; 로컬 시작 약 10:31 UTC, 파드 첫 명령 10:40:22 UTC, 파드 정리 끝 11:01:08 UTC).
- 대상: `D:\qdd` `dev` 커밋 `e6ab856`(= 태그 `stage3-r7fix12`, 커밋 시각 2026-09-25 10:31:21 UTC). 다른 에이전트의 커밋 안 된 PhysX hard-reset 작업(`harvest/sim/scene.py` 수정, `harvest/sim/determinism.py`, `tests/sim/test_hard_reset.py`, `tests/sim/test_determinism_isaac.py`)이 작업 트리에 있어 **작업 트리는 읽지도 쓰지도 않고**(이 보고서 한 파일만 씀) `git -c safe.directory=D:/qdd -c core.autocrlf=false archive e6ab856`(sha256 `480bfc61…`)을 Python tarfile로 `D:\tools\scratch_qdd\r7c13\repo`에 풀어 검토했다. `6b013ac..e6ab856` = 12회차 수정(정본 §77 + 보충), 라벨러 재생 수정·원인 보고(`pool_replay_debug.md`), S-E2E 사전 등록(`prereg_se2e.md`)·단계 B 학습기(재개·층화 검증·evalck), 논문 갱신, user-log 67–70. 파드 사본 = 같은 archive + JSON `CODE_VERSION`(`e6ab8560…`, dirty false); 모든 파드 산출 `meta.git.commit` = `e6ab8560…`, `meta.code_sha` = `adf55e924768bef1`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle7.md`–`r7_cycle12.md`, `r7c7_fixes.md`–`r7c12_fixes.md`, 정본 `00-interfaces.md` §1–§77(뒤 절 우선; [사용자] 제목 절은 그대로; 논문 .tex는 NOTE — 단 §77과 어긋나는 논문 문장은 매시간 논문 갱신용 NOTE로 표시), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`M4-overlap-commit.md`(조건 정의 §4·§5).
- 분류(12회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋과 다르고 정정 표시가 없는 것(후속 정본이 이미 정한 "[결정 필요]"·"메인 확인 요청" 포함), 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 정본에 없는 것.
- 규칙 준수: 저장소 수정·커밋·푸시 없음. 로컬 임시 = `D:\tools\scratch_qdd\r7c13`(스크립트는 모두 Write 도구로 쓰고 경로로 실행; heredoc·`cat >` 0). **절차 실수 1건**: 스크립트 한 줄 수정 명령 앞에 실수로 `python -`가 붙어 표준 입력 대기로 멈춘 것을 바로 멈췄다(TaskStop, 아무것도 실행하지 않음). 파드 = `/data/harvest/tmp/r7c13`(코드 사본·pytest·산출·가짜 루트 카나리, 374 MB)와 내 Isaac 판(10:43:19–10:48:58 UTC)이 만든 `ir/kitcache/cyclo-r7c13_standard`(208 MB)·`cache/pyc_r6/data/harvest/tmp/{r7c13,tmpclhit77q}`·`tmp/{carb.6FZaRp,tmpclhit77q}` — 시작 전 목록과 대조하고 생성 시각(10:43:35·10:44:35 UTC)·pyc 접두(`pyc_r6` = `closed` 워커)로 가려 **모두 지웠다**. 같은 시각대의 다른 새 항목(`tmp/carb.*`·`tmp/tmp*` 10:42 이전·10:50 이후, `kitcache/cyclo-hardreset_*`)은 hard-reset 에이전트 것이라 두었다. GPU: Isaac = GPU 1(`closed --isaac-gpu 1` → `IR_ROOT=cyclo`, 고유 `IR_INST` = `r7c13_standard`, `CUDA_VISIBLE_DEVICES=1`, Isaac 프로세스 1개), GPU 2·3(S-E2E 학습 중) 건드리지 않음, GPU 0 안 씀. **GPU 단계 B 재적재 확인은 빈 GPU가 없어 건너뛰고 CPU로 대신했다**(아래 §6.3). CPU: 파드 cgroup 사용량 약 22코어/32(측정 10 s), 내 작업은 `OMP_WAIT_POLICY=PASSIVE`·스레드 2–4. 시드 DEV·POOL만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 `=dev`·`=cal`만). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. 남의 프로세스 건드리지 않음.

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 3 |
| DOC | 4 |
| SCOPED | 14 |
| NOTE | 14 |

12회차 수정(정본 §77)의 핵심은 **동작으로 확인했다**: (b) 범주 줄 `last_step:`은 C4·C5·C6에서만 실리고 C0–C3·C5'는 늘 `none`(가짜 세계 44판 × 모듈형·융합, 파드 Isaac C5 50호출 {none 2, OK 33, DEVIATE 8, LAG 7}·C5' 50호출 모두 none), 학습 자료 유도 규칙 = 런타임 규칙(무작위 참값 20,000건 불일치 0, 실제 R2 DEV·POOL·jsel_dev 분포가 `r7c12_fixes.md:22` 수치와 정확히 같음), 학습 항목 상태 = 런타임 요청 상태(실제 줄 1,564 요청·400 항목 불일치 0), ser-A-min-2로 question_id가 모두 바뀌고 옛 보정 파일·옛 체크포인트(파드 실제 19개)는 거부, 호출 행의 `probs`·`request_blob`·`response_blob`·`last_step`과 Astra `output_text`·`max_output_tokens`·`effort`·JPEG blob은 모두 내용 해시와 일치. 그러나 12회차 D1의 수정 범위 밖에서 **FLIP_TH 초기값의 추정 방식**이 사전 등록 정의(split conformal, question_id별)와 다르고(D1), **카나리 기준일이 question_id 판본을 무시하고** 옛 판본 기준과 비교되며(D2), **표류 의심 뒤 J5가 재보정 없이 다음 날 다시 켜진다**(D3). 문서 4건: 메인 확인 요청이 §77 보충으로 해결됐는데 표시 없음(D-1), `r6_eval.md:46`의 "런타임에 없는 것 … C5'"(D-2), handoff의 user-log 번호(D-3), CLAUDE.md에 user-log 69·70 제약 없음(D-4). 연속 무결은 **0회 그대로**.

---

## 1. DEFECT

### D1. E0.5 FLIP_TH 초기값이 사전 등록 정의(split conformal, question_id별)가 아니다 — `harvest/eval/e05.py:271-272`, `:332-334`, `:412-425`
- 사전 등록: M4 §4.4 FLIP_TH 행(`M4-overlap-commit.md:287`) 기본값 "성공 실행 flip_score의 1−α 분위(**split conformal**) … E0.5 재생 자료로 먼저 잡는다 … `question_id@vN`**별로 잡는다(J4)**", M4 :44 "임계는 성공 실행으로 conformal 보정", 정본 §28 J4(`00-interfaces.md:260`) "확률 게이트와 **감시는 `question_id@vN`별로만**", 정본 :111 "임계값은 성공 실행으로 conformal 보정". E §2A.5(:253)는 "두 식의 성공 궤적 1−α 분위(FLIP_TH 초기값 후보)", E §4.12(:487)는 CAL 적합이 "E0.5 초기값에서 시작".
- 코드: (i) 스텝 점수 = **질문 5개의 평균**(`step_rows.append((tv / nq, one / nq, …))` :334) — 런타임 `flip_score`는 질문별(`m4._update_flip` :262-270, `try_commit_prefix` :278이 질문별 점수와 비교)이라 척도가 다르다(한 질문의 TV 1/3이 평균 점수로는 1/15). (ii) 분위 = `np.quantile` 선형 보간(`_q` :271-272) — split conformal의 ⌈(n+1)(1−α)⌉번째 값이 아니다(같은 저장소 `calibration.conformal_qhat` :59-64가 그 정의).
- 행동 확인: 파드 실제 모의 `e05 --data jsel_dev/P0,P1 --episodes 2`: `n_success_steps` 47, `flip_th_initial` q0.99 = {tv 0.3333, one_flip 0.6} — split conformal이면 α 0.01·n 47에서 ⌈48 × 0.99⌉ = 48 > 47 → **유한 문턱 없음(inf)**, q0.999도 같다. 로컬 구성 재생(`hand13.py`, `_q` 입력 가로챔): 성공 스텝 24개, `np.quantile` 0.1667(= 최댓값) 대 conformal inf. 후보 키는 `{tv_distance, one_flip}`뿐이고 질문별 값이 없다.
- 정본 기록: 없음(§73 :622는 "직전 창" 폭만, §77 D1은 α만 정함). 12회차 수정 보고(`r7c12_fixes.md:32`)는 M4 :287을 인용하면서 α만 바꿨다. 영향: 판정 1–10은 이 값을 쓰지 않지만, E-M4의 FLIP_TH 시작값(E :487)이 사전 등록과 다른 척도·추정식에서 나오고, 소표본에서 "문턱 없음"이어야 할 곳에 유한 값을 준다.

### D2. 카나리 기준일이 question_id 판본을 보지 않는다 — ser-A-min-2 판이 ser-A-min-1 기준일과 비교된다 — `harvest/eval/canary.py:211-218`
- 사전 등록·정본: E §1.8(:136-140) "고정 스냅샷 × **고정 `question_id@vN`** 소수 세트를 돌려 … 기준일과 비교", "기준일 = 카나리 세트를 처음 돌린 날", §3.7-7(:345-346) 판본(직렬화기 판본 포함)이 바뀌면 게이트를 끄고 재보정; 정본 §77 "보정 파일·**카나리 기준일(질문 id·프롬프트가 바뀜 → 새 기준일)**·qid 등록부 항목도 새로".
- 코드: 기준 파일 선택은 모델 지문과 `set_sha`(스냅샷·프레임)만 본다. `question_ids`는 기록만 하고 대조하지 않는다(보정 파일은 `Calibration.load`가 qid 해시로 거부하는 것과 대조적).
- 행동 확인(파드 scratch 루트, 모의): 실제 `canary/sets/dev_v1` + 옛 기준 `canary_20260924_mock.json`(qid `02e56df7dd80@v1` …, 커밋 `bf745b83`) 복사 → e6ab856 코드로 `canary --model mock --set dev_v1` → 새 파일 qid 5개 모두 다름(`8e7762b83477@v1` …)인데 `baseline` = `cn20260924_mock_ae0d1a`(2026-09-24)로 비교됐다. 모의는 답이 줄에 무관해 표류가 안 나지만, 지문이 그대로인 모델(영점 기반 모델 등)은 다른 프롬프트끼리 비교해 가짜 "표류 의심"을 낼 수 있고, 그 결과가 §77 N6으로 J5를 끈다. 지금 파드의 실모델 카나리(`ed387f59…` = `sftA_pool_v1/merged`)는 모델 자체가 거부되므로 잠재 결함이다.
- 정본 기록: §77은 "새로"라고만 적고, 코드가 이를 강제하지 않는다(결정·SCOPED 없음).

### D3. 카나리 "표류 의심" 뒤 재보정 없이 다음 날 J5가 다시 켜진다 — `harvest/eval/closed.py:169-181`, `canary.latest_canary:149-159`
- 사전 등록: E §1.8(:139) "표류 의심 → 그날 결과를 분리 보고하고, **E1 보정 부분을 다시 돌린 뒤에 게이트를 재사용**", §3.7-7·-8(:346-347) "판정 7대로 끄고 재보정한다". 정본 §77 N6은 이 두 문장을 인용하고 "그날 이후 다시 적합한 보정 파일이면 켠다"를 재사용 조건으로 적었다.
- 코드: `j5_after_canary`는 **가장 최근 카나리 하나**만 본다. 그 카나리가 `drift_suspect: false`이면 보정 파일이 표류 의심 날보다 앞이어도 J5를 켠다.
- 행동 확인(`hand13c.py`, 가짜 루트): 09-20 기준(표류 없음) · 09-21 `drift_suspect: true` · 09-22 `false`, 보정 파일 `utc` 2026-09-20T12:00Z → 09-22 판 `j5_after_canary(0.1, …)` = **(0.1, None)**(켬). 09-22 파일을 지우면 (None, "J5 off …")(끔). 같은 날 경계는 정상(09-24T23:59:59Z → 끔, 09-25T00:00Z → 켬, `utc` 없음 → 끔; `hand13.py` 9건).
- 정본 기록: §77 N6은 "최신 카나리"라는 구현만 적었고, 표류 의심 다음 날 깨끗한 카나리로 재보정 없이 재사용하는 경우는 결정하지 않았다(인용한 사전 등록 문장과 반대 결과).

## 2. DOC

### D-1. §77 보충(10:25 UTC)이 해결한 "메인 확인 요청"에 해결 표시 없음 — `docs/handoff.md:104`, `docs/stage3/results/r7c12_fixes.md:20`, `:57-60`
- handoff 12회차 줄: "진행 중인 S-E2E 체크포인트 포함 — **메인 확인 요청**"; `r7c12_fixes.md:20` "→ 메인 확인 요청", `:57` "## 8. 메인 확인 요청" 항목 1–3(범주 희소성, S-E2E 체크포인트 평가 코드, `stageb_train.prompt_config` serializer 필드). 같은 커밋의 정본 §77 보충 (1)·(2)·(4)가 모두 정했다(본 단계 B 사전 등록 때, 6b013ac 고정 사본으로 판정, 다음 그 파일 수정 때). 선례: 11회차 D-1(handoff 10회차 줄), 12회차 D-2(`r7c9_fixes.md:88`).

### D-2. `docs/stage3/results/r6_eval.md:46` — "런타임에 없는 것: … C-FIX, **C5'**"(C4 = "(b) + newest", C5 = "기본")에 §77 정정 표시 없음
- 같은 줄에는 9회차 정정([정정 R7 9회차, 정본 §74])이 붙어 있지만 §77이 C5'를 런타임 조건으로 넣고(`conditions.py:30`, 파드 Isaac `closed --conditions "C5,C5'"` 실행됨) C4·C5의 "(b)"에 결정 모델 입력 줄을 더한 뒤로는 틀린 현재 서술이다. §77의 코드 쪽(`closed.py` `not_in_runtime`, `conditions.py` 머리 설명)은 고쳤다.

### D-3. `docs/handoff.md:12` — "`docs/user-log.md`: 사용자 발언 전체(1~41번 — **지금은 66번까지**, sweep6 갱신)"
- user-log는 e6ab856에서 70번까지다(67–70: 217f641·70d1186·d9d017d에서 추가). 머리 줄(`:3`)은 10:00 UTC로 갱신됐지만 이 줄은 그대로다.

### D-4. `CLAUDE.md` — user-log 69("1시간마다 논문 업데이트하기로해 앞으로는 꼭")·70(성능이 낮으면 최근 1.5년 논문의 개선법 적용) 제약이 없다
- `CLAUDE.md:4` "사용자가 새 주의사항이나 제약을 말하면 바로 이 파일에 추가한다". 논문 절(`:13-25`)에 매시간 갱신 규칙이 없고, user-log 70은 정본 §77 보충 (1)에만 인용됐다(user-log 67 "GPU 최대 효율 분산"도 운영 규칙 줄에 없음).

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬 `test_latency_ctrl.py:11` 1개 건너뜀, 파드도 같음. EVAL H1–H3 기준선 비교(같은 보충).
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — `gen gen --seeds 10005-10006` 확인 인자 없이 rc 1.
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8(검사기·계획 서명·편집 거리, 확인 헤드 보정 파일 기본 미보정, M9 복구).
- S6. Astra 카나리 "none"(§67 보충) — 파드 C5·C5' `astra` 행 `canary_id` "none".
- S7. S-E2E 체크포인트의 런타임 tau 마스크·DecCall 형식 차이, **그리고 새 코드의 거부**(§77 보충 (2): 6b013ac 고정 사본으로 판정) — 파드 `se2e_A_s0`·`se2e_B_s1` `step_001000`·`step_002000`이 `training_prompt_config`·`check_prompt`에서 "ser-A-min-1 (pre canon §77 …)"로 거부됨(예상된 동작, 결함으로 세지 않음).
- S8. CONTRADICT-soft(§68 K6).
- S9. §73 D5 M4 설계 확장(경계 직후 W 2·γ 1.0, 큐 임계 g, 장면 변화 조기 호출, 미확정 실행 (b) 엄격화).
- S10. §73 N5 E1 범위(`calib` = 판정 1·8).
- S11. §74 보충 E-M4-lat 비례 STALE_MAX, 런타임에 없는 조건 C2'·C2'-S·C2-match·C3'·C3''·C5-A3·C-FIX(`closed.json` `meta.not_in_runtime` 그대로 확인).
- S12. §75 보충 (2) E-M4 판정 7(H = 3 대 H = 1).
- S13. §77 N8 (13): E0.5 `fine_dir`, Jev-L E0 측정 도구, 결정 호출 이미지 원본 저장 안 함, 완료 정의 밖 사전 등록 실험.
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31`·`:117-121` "boundary (ambiguous)" 주석 — e6ab856에 그대로 있음(정본이 보류로 적었으므로 SCOPED; `harvest/sim` 정리 때 처리).

## 4. NOTE
- N1. **(b) 줄의 학습·런타임 짝 맞춤이 한 스텝 어긋난다(§77 (v)에 없는 차이)**. 주기 호출은 경계 틱과 같은 틱에 경계 판정 전에 만들어지므로(`core.act` :460 → :494) 주기 호출이 싣는 범주는 "방금 끝난 스텝"이 아니라 그 앞 스텝이다 — 행동: LAG을 4.29 s 경계에 넣으면 4.29 s 호출은 `OK`, 처음 실리는 것은 4.62 s 주기 호출(조기 호출 없음); DEVIATE는 다음 틱 조기 호출(4.30 s)과 다음 주기 호출에 두 번 실린다. 학습 자료는 스냅샷 k에 "k에서 끝난 스텝"(k−1→k)의 범주를 싣는다. §77 (ii)는 런타임 순서를 적었지만 학습 자료와의 0.33 s 차는 적지 않았다 — 판정 3 전에 한 줄(또는 경계 뒤 호출 생성)을 권함.
- N2. **폐루프 물리가 프로세스 이력에 따라 달라짐(e6ab856)**: 같은 Isaac 워커에서 C5 → C5'(시드 7, 모의 선택기는 `last_step`을 읽지 않음) 순으로 돌리자 스텝 17(약 5.6 s)부터 TCP 0.2 mm 차가 나고 호출 답은 28번째부터 달라졌다(성공·16.58 s는 같음) — `pool_replay_debug.md`의 CPU PhysX 이력 의존과 같은 현상. 같은 워커 안 조건 짝 비교(C5 대 C5' 등)에 조건 효과 밖의 차가 섞인다. 정본에는 이 발견·영향(R2_TRAIN 생성 중지, 폐루프, 라벨 거부권 제외 규칙 1 mm → 비트 동일 886행)이 한 줄도 없다(`labeler.md:40`에만). hard-reset 수정은 커밋 전이라 검토 범위 밖.
- N3. **S-E2E 판정 스크립트**: `prereg_se2e.md:62`가 가리키는 `se2e_verdict.py`는 저장소 밖(`D:\tools\scratch_qdd\se2e_run\`·파드 `/data/harvest/logs/se2e/`, 두 사본 sha256 `41535196…` 같음)이고 사전 등록에 해시가 없다. 구성 로그 18건으로 (a)–(e) 판정을 확인했다(누락 스텝·NaN·재적재 1e-9·evalck 불일치·idx 차·첫 스텝 차·49스텝·최대 5.01 %·중앙값 1.01 % 모두 불합격, 정상 판 bit 통과). 다만 (a)의 "주 학습 rc 0"은 스크립트가 보지 않고(런처 출력에만), "≤" 경계가 부동소수에 약하다(끝 3점 0.65·0.65·0.80 → 평균 0.7000000000000001로 b1 불합격, 0.8 × 3 → b2 불합격, 상대차 정확히 1 %·5 % → 불합격). 실제 손실에서 정확히 같을 일은 드물다 — 스크립트를 커밋하고 해시를 `se2e_train.md`에 적을 것을 권함.
- N4. S-E2E 진행(판정 밖, 읽기만): 두 시드 모두 설정이 사전 등록 §3과 같다(`total_steps` 4686, 검증 300 = RB1 150·RB2 150, eval 500, save 1000, lr 1e-4, λ, KI stop, 시드 0·1), 실행 코드 `stageb_train.py` = e6ab856 블롭(`61c8a7aa…`, `CODE_MANIFEST.txt`), 사전 등록 사본 = 저장소 판. 11:00 UTC 기준 2,601·2,610스텝, 체크포인트 1000·2000, eval 0–2500.
- N5. `e05`·`rd`·`calib`에 존재하지 않는 상대 경로 `--data`(작업 폴더 기준)를 주면 **0편으로 rc 0**(`E05_DONE claim insufficient_data`, `RD_DONE n 0`, `CALIB_DONE`)이 난다 — 빈 입력은 거부하는 편이 안전(절대 경로로 다시 돌린 판은 §6.3).
- N6. 옛 체크포인트 거부(`closed`·`e05 --model …/sftA_pool_v1/merged`)는 rc 1이지만 빈 `--out` 폴더를 남긴다(분할 거부는 폴더 0개).
- N7. `j5_after_canary`는 날짜 단위(같은 날 카나리 전에 맞춘 보정도 켬 — §77 N6 "그날 이후" 문구대로)이고 표류 의심이면 **모든 질문**의 J5를 끈다(사전 등록 판정 7은 "해당 질문군") — 더 보수적이라 NOTE.
- N8. `stagea_train.serializer_of`는 `serializer` 필드가 없는 단계 B 체크포인트를 프롬프트 파일 11개 중 하나라도 해시가 다르면 "ser-A-min-1 (pre canon §77 …)"로 부른다 — 이후 그 파일들의 무관한 수정 뒤에는 오해를 부르는 메시지(어차피 `files_ok`로도 거부). §77 보충 (4)의 필드 추가 권함.
- N9. `e05` 같은 시각 뒤집힘의 "perturbed"는 P0가 아닌 모든 kind(P3·P4 폴더를 주면 포함 — E §2A.4는 P3·P4를 쓰지 않음)이고 가드가 없다.
- N10. 결과 문서 `e3lite.md:7`·`:17`, `pool.md:24`, `r1_perception.md:22`·`:43`은 S0 텍스트를 "ser-A-min-1"로 부른다 — S0 글 자체는 바뀌지 않았고(`serialize_state`), 판본 상수 -2는 DecCall 상태(+ `last_step` 줄)의 판본이다. 옛 계획서 `2026-09-24-stage3-experiments.md:440-500`의 `ser-A-min-1`도 옛 기록.
- N11. **논문(매시간 갱신 때)**: `paper/sec/X_suppl.tex:104` "지금 런타임에 들어 있는 조건은 C0–C6 … C5'는 되먹임 구현과 함께 들어간다"(§77로 C5' 런타임 조건·되먹임 구현됨), `paper/sec/4_setup.tex:29` 확률 분포·요청/응답 원문·Astra 원응답·최대 토큰 "구현 중"(§77 D4로 구현됨), `:31` "R7 12회", "1 mm 기준을 넘은 6.2 % 행(20편) 무효"(현재 `labeler.md:40` 886행·29편·비트 동일 기준), `X_suppl.tex:27` FLIP_TH는 D1 수정과 함께.
- N12. 단계 B 소형 CPU 스모크(`smoke --backbone tiny --device cpu`, 30스텝): 학습 총손실 3.311 → 2.745, eval fm 2.141 → 1.985, **dec 0.745 → 0.757(증가)**, `save_load` `max_abs_action_diff` 0.0·eval 같음, KI 역전파 0.0 — 12회차 N10과 같은 모양(합성 자료·소형).
- N13. 시험 수: 로컬 **898 passed / 12 skipped**(`r7c12_fixes.md:54`와 같음), 파드 CPU **946 passed / 3 skipped**(`:55`와 같음), LeRobot 6 passed. 파드 CUDA 시험은 빈 GPU가 없어 돌리지 않았다.
- N14. 11·12회차 NOTE 중 남은 것(§76 N3 격자 밖 H = 1 표 수, 카나리 `dev_v1` `stale`, TEST2가 `splits.RANGES`에 없음, 1차판 RD Score [가정], E0.5 분당 400 [가정]) 그대로.

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 파드 산출 `meta.prereg.check` = "OK"(e05·rd·calib·closed, 해시 5개). 사전 등록 문서(`E-first`·`EVAL`·`M4`·`prereg_labeler`·`prereg.json`)는 `6b013ac..e6ab856`에서 바뀌지 않았고 `prereg_se2e.md`가 새로 들어왔다. 코드 줄은 `e6ab856` 기준. "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c13\hand13.py`(90건 중 82 통과 — 실패 8 = LAG 창 정의 6(측정 스크립트 쪽; `hand13b.py` 10/10으로 다시 확인)·D1 2), `hand13b.py`, `hand13c.py`(D3), `hand13d.py`(23/23), `verdict_check.py`(18건 중 15 — 3건은 N3 부동소수 경계); **파드** = §6(`pod_copy/*`). 굵게 = 이번에 처음 대조한 행.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 (E :113-120, 정본 §66) | `eval/splits.py:13-42` | `split_of` 29 dev·30 None·549 cal·550 None·1149 test·1150 None·1329 test_p5·2119 pool·2120 None; 파드 가드 19건 + gen 1건 rc 1·출력 폴더 0(모델 거부 2건 빈 폴더, N6) | 일치 |
| 2 | POOL 120 × 10, 경계 사례 30 % 과표집 (E :121, §76 D-2) | `sim/snapshot.py:102-136`, `cli_pool.py` | `boundary_flags` 앞 방향만 [F,T,F,T,F]; 시험 묶음 | 일치(주석 S14) |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` | 시험 묶음(12회차 경계 유지) | 일치 |
| 4 | 분할 = 에피소드 (E :122) | `pool_split`, `calib.halves` | P0·P1·P2 40/40/40, fit 60(섭동별 20) | 일치 |
| 5 | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py:26-38` | 시험 묶음; 파드 Isaac C5·C5' `env_success` True 16.58 s | 일치 |
| 6 | 호출 기록: 질문별 확률·요청/응답 원문(E :125), Astra A6(E :126, 정본 §28 :255), 부가 JSONL(E :127) | `core.py:289-322,408-418`, `ir_policy.write_blobs` | 파드 C5·C5' `call` 100행: `probs` 질문 = `answers` 질문·합 1(100/100), `request_blob` = `request_sha256` = sha256(blob)(100/100), `response_blob` 해시 일치(100/100), 이미지 해시 {cam_head, cam_wrist_right}; `astra` 4행 `output_text`·`max_output_tokens`·`effort`·요청 blob·JPEG blob 해시 일치; `trial_metadata.ours_blobs` 경로 | 일치(§77 D4; 결정 이미지 원본은 S13) |
| 7 | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `stats.py:4` | 파드 e05·rd·calib·closed `meta.bootstrap.n_boot` 10000 | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate` | 파드 closed 단위 "layout seed"; 같은 워커 안 물리 이력 차는 N2 | 일치 |
| 9 | 판정 2 Holm (E :131, :257) | `e05.gain_holm` | 시험 묶음; 파드 e05 `j2_gain_holm` 키 | 일치 |
| 10 | 판정 10 (E :265) | `e05.block_diff_holm` | 파드 `j10_block_pairs_holm` 키, 시험 묶음 | 일치 |
| 11 | 카나리 "하한 > 0, Holm" (E :139) | `harvest/canary.py:31-55` | 파드 scratch 카나리 `drift_suspect` false(모의), 시험 묶음 | 일치 |
| 12 | 판정 절 해시를 실행 기록 첫 줄에 (E :133) | `eval/common.py` | 파드 산출 4종 `meta.prereg.check` OK | 일치 |
| 13 | 카나리 기준일 = 세트를 처음 돌린 날 (E :140) | `eval/canary.py:211-218` | 같은 판본 안에서는 첫날 기준(시험 묶음); 판본 바뀜은 행 85 | 부분 → D2 |
| 14 | 모델 식별 필드가 바뀌어도 같은 처리 (E :139) | `Calibration.load:256-267` | 다른 지문 거부(시험 묶음), qid 해시 다름 거부(`hand13.py`) | 일치 |
| 15 | E0.5 표 = t_s − d_p95 − {0, .33, .66} (E :236) | `e05.vote_steps` | 시험 묶음 | 일치 |
| 16 | 재시험 1회 (E :237) | `e05.py` | 시험 묶음 | 일치 |
| 17 | 같은 시각 K = 3 (E :238) | `e05.py`(`asyncio.gather`) | 파드 `meta.same_k` 3 | 일치 |
| 18 | newest / LA-2·γ 2/3 / C2'' / C2' (E :240) | `analysis/replay.py`, `m4.share_at_least:72` | 2/3·4/6·66/99 참, 66/100·3/5·1/2 거짓 | 일치 |
| 19 | `C_flip` 두 식 (E :242) | `e05.py:77-87` | 시험 묶음 | 정본 기록(§73) |
| 20 | A0–A4, 층 (E :246) | `options.variant`, `e05.analyze` | 파드 e05 층 L3_6·L7_17 | 일치 |
| 21–28 | 판정 1–10 경계 (E :256-265) | `replay.judge_e05`, `e05.py` | 시험 묶음(12회차 경계값 시험 포함 통과), 파드 판정 키 13개 | 일치 |
| 29 | FLIP_TH 후보 α 0.01 (E :253, :487; M4 :285) | `e05.py:242-243,418-425` | 키 q0.99·q0.999·q0.95, `flip_th_initial.alpha` 0.01(로컬·파드) | 일치(§77 D1) |
| 30 | 같은 시각 뒤집힘 성공·섭동 따로, A1–A4 flip (E :253, §27 :243) | `e05.py:338-359,378-383` | 구성: 성공 0.0(n 80)·섭동 0.5(n 80); 실패한 P0만 두면 success n 0·perturbed n 같음; 층마다 a1–a4flip; 파드 success n 275·perturbed n 310 | 일치(P3·P4 N9) |
| 31 | d_p95 = E0 값 (E :236, :278) | `e05 --d-p95` 0.307 | 정본 §55·§74 | 정본 기록 |
| 32 | E0.5 분당 400 [가정] (E :277) | 없음 | — | N14 |
| 33 | E1 자료 반분 (§52) | `calib.halves` | 정본 §73 | 정본 기록 |
| 34 | ECE = 15 동일 질량 (E :320) | `calibration.ece_mass:71` | 시험 묶음, 31항목 유한값 | 일치 |
| 35 | 오답 < 30 → 판정 불가 (E :320) | `calibration.py:215` | 시험 묶음 | 일치 |
| 36 | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat:59-64` | n 10·α .1 → 10, n 5 → inf, n 19 → 18 | 일치 |
| 37–39 | log p 자름·질문별 온도·원 확률 조건 (E :333-335) | `calibration.py` | 시험 묶음 | 일치 |
| 40 | E1 판정 1 (i)–(iv) (E :339) | `calibration.py:210-228` | 시험 묶음; 파드 calib 질문별 `heldout.n_ece` 96 | 일치 |
| 41 | 판정 7 재보정 결속 (E :345-346) | `Calibration.load`, `core.py:128-130` | ser-A-min-1 qid로 맞춘 보정 파일 → "question_id of dir_z: calibrated b6072caa6628@v2 != runtime 99bf6dc67d11@v1" 거부 | 일치 |
| 42 | 판정 8 J5 (E :347) | `calibration.py:229-233` | 시험 묶음 | 일치 |
| 43 | `ambiguous` ECE 제외 (E :359) | `calibration.evaluate` | 파드 `n_ece` 96 | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| 45 | N_max = ⌈d̂/T_c⌉+1 (M4 :258) | `m4.py:178-182` | d̂ 0.307 → 2, 0.33 → 2, 0.34 → 3, 0.9 → 4 | 일치 |
| 46 | γ = 3표 중 2 (E :487, M4 :276) | `m4.py:72-77` | 행 18 | 일치 |
| 47–48 | W 정의·비가역 W+1 (§72, M4 :291) | `m4.py:246-255` | 시험 묶음 | 일치 |
| 49 | τ = 1(접촉 근처 0) (E :487, §7) | `core.near_contact`, `m4._agrees` | 시험 묶음 | 일치 |
| 50 | conformal α 0.01·w 5 ((b) 경계) | 확인 헤드 보정 파일 | 기본 미보정 | SCOPED S5 |
| 51 | STALE_MAX 1.5 s (E :487) | `m4.older_than:56` | 1.5 유지·1.5000001 폐기·0.1+0.2+1.2 유지 | 일치 |
| 52 | C2 = VLM Stream (E :495, M4 :332) | `conditions.py:26`, `m4.py:220-226` | 가짜 세계 C2 요청 모두 none(행 77), 시험 묶음 | 일치 |
| 53 | C0·C1·C3·C4·C5·C6 설정 (M4 :329-345) | `conditions.py:23-32` | `condition("C5'")` = (C5의 M4 값, {b_to_model: False}) | 일치 |
| 54 | C5 = §4.2 전체((b) 범주 → 결정 모델 입력), C5' = 뺌, 판정 3 (M4 :155, :232, :340-342, :361) | `core.b_line:199-205`, `models.build_live_request`, `serialize.with_last_step` | 행 77–82 | 일치(§77; 짝 맞춤은 N1) |
| 55 | H 1과 3 (정본 §2, M4 :188-189) | `m4.early_ask_steps:61`, `closed.py` | `early_ask_steps(0, 0.307, 0.33, 1.0)` = [1, 2, 3]; 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 |
| 56–58 | n_LA 2·조기 호출 당겨 씀·FLIP_TH 끔 (M4 :275, :262, :287) | `m4.py`, `core.py:458-465` | 시험 묶음; DEVIATE 뒤 다음 틱 조기 호출(행 79) | 일치 |
| 59 | 경계 직후 W 2·γ 1.0 등 | 없음 | §73 D5 | SCOPED S9 |
| 60 | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.select_rule:131` | 0.8999 → None, 차 0.02 → plan, 0.0201 → short1 | 일치(재생 수정은 행 98) |
| 61–62 | 폐루프 RD 재표집 = layout 짝, 주 RD = Score (EVAL :182-184) | `closed.py`, `rd.py` | 파드 rd `drop.random` n 135 | 일치 / N14 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | §71 보충 | SCOPED S1 |
| 64–65 | M4b 2,000회, E-M4-lat 비례 STALE_MAX | `m4b/*` / 없음 | §72 예외 / §74 보충 | 일치 / SCOPED S11 |
| 66–67 | H = 1 창·`lead_max` 유한한 양수 (§75, §76 N4) | `m4.py:106-113`, `closed.py:165` | inf·−inf·NaN·0·−0.0·−1 거부, 1e-9·1.0·1.5·1e6 받음; 파드 `--m4-lead-max inf`·`0` rc 1 | 일치 |
| 68 | E0 판정 4 (E :183, :197) | `analysis/latency.py:81,93-116` | 행 94 | 일치 |
| 69 | E-M4 판정 7 | 다스텝 DecCall 없음 | §75 보충 (2) | SCOPED S12 |
| 70 | FROZEN = 송신 시각 기준 (M4 :150) | `m4.py:228` | §77 N3 | 정본 기록 |
| 71 | 카나리 표류 → 분리 보고·재보정 뒤 재사용 (E :139, :347) | `closed.j5_after_canary:169-181` | 행 93 | **불일치 → D3** |
| 72–73 | 응답 모델 필드·재시도 기록 (E :51, :54) | `models.JevLSelector` raw(`model`·`http_status`·토큰·시각), `common.Asker` | 코드; Jev-L 원응답이 `response_blob`에 | 일치 |
| 74 | E0.5 채점 정답 (E :241) | `e05 --truth` labels_v2 | §77 N4 | 정본 기록 |
| 75 | E0.5 표현 `fine_dir`, E1 질문군 (E :239, :299-309) | `common.QUESTIONS` 5 | §77 N5 | SCOPED S13 |
| 76 | Astra 카나리 (E :138) | "none" | §67 보충 | SCOPED S6 |
| **77** | (b) 범주 줄: C4·C5·C6 실음, C0–C3·C5' none (M4 :340-342, §77 (iii)) | `core.b_line:199-205`, `conditions.py:23-32` | 가짜 세계 8조건 × {DEVIATE, CONTRADICT, LAG} × 모듈형·융합 = 44판: C4·C5·C6 첫 요청 none, 경계 뒤 요청이 넣은 범주(LAG은 `hand13b.py`로 다음 주기 호출), C0–C3·C5' 모든 요청 none; 모든 호출 행 `last_step` = 저장 blob 상태 마지막 줄, 융합 `ctx_text`에는 줄 없음; 파드 Isaac C5 {none 2, OK 33, DEVIATE 8, LAG 7}·C5' none 50 | 일치 |
| **78** | 런타임 값 = 마지막으로 끝난 스텝 범주, T1 CONTRADICT 덮어쓰기, 늦은 T2 DEVIATE 올림 (§77 (ii)) | `core.py:353-355,539-549` | `_on_verify` 단위: OK·LAG → DEVIATE, CONTRADICT 유지, 앞선 스텝(ds 불일치)은 안 바꿈, T2 참이면 OK, C5'·C3 none | 일치 |
| **79** | 같은 틱 호출은 경계 전 → 다음 호출부터 (§77 (ii)) | `core.act:458-494` | 4.29 s 경계: 같은 틱 호출 `OK`, 4.30 s 조기 호출 `DEVIATE`; LAG은 4.62 s 주기 호출 | 일치(학습 짝 맞춤 N1) |
| **80** | 학습 자료 값 = 기록된 실행 뒤 확인 + 런타임 규칙 (§77 (iv)) | `deccall_snap.py:31-64` | 무작위 참값 20,000건 `category_of_check` = 런타임 T1/T2 `expected_check` 불일치 0; 첫 스냅샷·k 틈·시드 바뀜 → none; R2 `prev_step` None/T2/T1/단계 전환 → none/DEVIATE/CONTRADICT/OK; 파드 실제 분포 R2 DEV 36편 {none 36, OK 1024, DEVIATE 21}, POOL 120편 {none 44, OK 1155, CONTRADICT 1}, jsel_dev 90편 {none 23, OK 877} = `r7c12_fixes.md:22` | 일치 |
| **81** | 학습 항목 상태 = 런타임 요청 상태 (§77 (i)) | `stagea_data.build_items`, `models.build_live_request` | 파드 실제 POOL 40편 + R2 DEV 12편: S1·IMG 요청 1,564개 상태·질문 불일치 0, 단계 A 항목 400개 마지막 줄 불일치 0 | 일치 |
| **82** | C5' = 줄 유지·값 none (§77 (iii), 보충 (3)) | `core.b_line` | 행 77·78 | 일치 |
| **83** | 형식 판본 ser-A-min-2 → question_id 전부 바뀜 (J1, E §3.7-7) | `serialize.py:5-15`, `qid.py:22` | `SERIALIZER_VERSION` -2; 같은 질문 qid 해시가 -1/-2에서 다름; 잘못된 줄 값 'ok'·'None'·''·'DEVIATED' 거부 | 일치 |
| **84** | 옛 체크포인트 거부 (§77) | `stagea_train.serializer_of:101`, `require_serializer:116`, `fused_model.check_prompt` | 구성 6건(단계 B 필드 없음 + 현재 파일 → 받음; 옛 serialize.py 해시·files_sha 없음 → 거부; 단계 A -1 거부·-2 받음; 옛 config.json args 거부); 파드 실제 19개(단계 A 12, 단계 B 2, S-E2E 스모크 3, S-E2E 진행 4 — S7) 모두 거부, 단계 B는 `check_prompt`도 거부; `closed`·`e05 --model sftA_pool_v1/merged` rc 1 | 일치 |
| **85** | 카나리 세트 = 고정 `question_id@vN`, 판본 바뀌면 새 기준일 (E :138-140, §77) | `canary.py:211-218` | ser-A-min-2 판(qid 5개 새 값)이 ser-A-min-1 기준(09-24)과 비교됨 | **불일치 → D2** |
| **86** | 결정 호출 행 `probs`·`request_blob`·`response_blob`·`last_step` (E :125, §77 D4) | `core.py:289-322`, `reqhash.request_body` | 로컬 가짜 세계 모든 호출 blob 해시 = `request_sha256`; 파드 100/100 | 일치 |
| **87** | Astra 행 원응답·최대 토큰·effort·요청 원문·이미지 원본 (§28 A6) | `core.py:408-418` | 파드 4/4, 이미지 blob sha 일치 | 일치 |
| **88** | 결정 호출 이미지 = 해시만 (§77 [Claude 결정]) | `core.py` | 파드 blob 폴더에 결정 이미지 없음(C5 100 파일 = 요청·응답 json + Astra jpg) | 정본 기록(S13) |
| **89** | FLIP_TH 후보 α 범위 {0.001, 0.01, 0.05} (M4 :285) | `e05.py:242-243` | 행 29 | 일치 |
| **90** | FLIP_TH = 성공 실행 flip_score의 1−α 분위(**split conformal**), **question_id별** (M4 :287, :44; 정본 §28 J4 :260, :111) | `e05.py:271-272,334,418-425` | 질문 평균 점수, `np.quantile`; 파드 n 47 q0.99 0.3333 대 conformal inf, 로컬 n 24 0.1667 대 inf; 질문별 값 없음 | **불일치 → D1** |
| **91** | 같은 시각 뒤집힘 성공(P0 성공)·섭동(P1·P2) (E :253, §2A.4, §77 D2) | `e05.py:338-359` | 행 30 | 일치(N9) |
| **92** | 층별 A0 대비 flip A1–A4 (§27 :243) | `e05.py:378-383` | 행 30 | 일치 |
| **93** | 카나리 표류 의심 → J5 끔, 재보정 뒤 재사용 (E :139, :347, §77 N6) | `closed.py:169-181,401-404` | 같은 날 경계 9건 정상; 09-21 표류 → 09-22 깨끗한 카나리면 재보정 없이 (0.1, None) | **불일치 → D3**(N7) |
| **94** | E0 판정 4: T_c 0.33, lead 1.5, 스텝당 표 중앙값 ≥ 2 (E :183, :197, §77 N7) | `latency.step_votes:93`, `judgment4:108`, `judge_e0:81` | lead 1.5·지연 0.2 → 4, lead 1.0 → 3; 스텝 시작 정확히 도착 셈·1e-6 늦으면 안 셈; None·NaN 안 셈; 중앙값 2 → 가능, 1 → 불가 | 일치 |
| **95** | S-E2E 설정 (`prereg_se2e.md` §3) | `stageb_train.py:189-199,204-214,263-266`, 파드 실행 로그 | 검증 300 = RB1 150·RB2 150, `total_steps` 4686, eval 500·save 1000·시드 0/1·λ·KI; 실행 코드 = e6ab856 블롭 | 일치(N4) |
| **96** | S-E2E 판정 (a)–(e) (§4) | `se2e_verdict.py`(저장소 밖) | 구성 로그 18건(N3) | 일치(부동소수 경계·rc 미계산 N3) |
| **97** | S-E2E 재개·evalck (§3, §4 (c2)·(e)) | `stageb_train.train_loop`, `cmd_evalck:500`, `check_resume_args:216` | 파드 CPU `test_stageb_torch.py` 재개 비트 재현·설정 변경 거부·층화 검증 시험 통과(946 중); 실행 로그에 `idx`·`lr_heads` 기록 | 일치(판정 결과 미정) |
| **98** | 라벨 복원 기준(계획 DC4 ≤ 1 mm; 라벨 규칙은 prereg_labeler) | `sim/labeler.py:177-221,303-330` | 규칙 함수 불변(행 60), 재생은 비트 동일까지 재시도(`REPLAY_TOL` 0); 거부권 제외를 1 mm → 비트 동일로 넓힌 것은 `labeler.md:40`에만 | 일치(정본 미기록 N2) |

### 5.1 12회차 표(`r7_cycle12.md` §5)와의 차이
- 행 6·54: 12회차 불일치(D4·D3) → 이번에 동작으로 일치(행 77–88).
- 행 29·30: 12회차 D1·D2 → α·지표는 일치, 그러나 FLIP_TH 행의 나머지 정의(추정식·질문별)를 M4 :287과 끝까지 대조해 새 행 90 **불일치(D1)**.
- 행 13·71: §77 N6 구현과 §77의 "새 기준일" 문장을 행동으로 확인해 새 행 85 **불일치(D2)**, 93 **불일치(D3)**.
- 새 행 94–98: E0 판정 4, S-E2E 사전 등록, 라벨러 재생 수정.

## 6. 확인한 것 (근거)

### 6.1 12회차 수정(정본 §77)의 독립 확인 (과제 2)
- **D3 (b) 되먹임**: 행 77–82. 가짜 세계 판은 `tests/runtime/fakeworld.py`를 쓰되 요청 기록 선택기·주입 틱·검사 식을 새로 썼다(수정 에이전트 시험과 달리 CONTRADICT·LAG, 모든 조건, 호출 행 ↔ 저장 blob 대조를 포함). 파드 Isaac 모의 DEV 한 판(`closed --model mock --split dev --seeds 7 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c13`, 10:43:19–10:48:58 UTC) → `CLOSED_DONE` C5·C5' 성공 1.0(16.58 s); 저장 요청 blob의 상태마다 `last_step:` 줄이 정확히 하나이고 마지막 줄(100/100).
- **D4 호출 기록**: 행 86–88.
- **D1·D2 E0.5**: 행 29–30·89–92(D1의 나머지 정의는 이번 D1).
- **옛 체크포인트·보정 파일 거부**: 행 83–84, 41.
- **N6·N7**: 행 93·94.

### 6.2 앞 회차 동작 재확인
- γ 정확히 2/3, STALE_MAX 경계, `lead_max` 거부·수락, N_max, conformal q̂, 라벨 규칙, 경계 플래그·섭동 배정(`hand13d.py` 23/23), C2 요청 none·C5 조기 호출(행 77·79), 파드 `meta.m4_H`·`m4_lead_max`·`not_in_runtime`.

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st`로 R2 DEV `/data/harvest/r2/dev/*/*/P0` 전 편 `validate_episode`: **36/36 errors 없음**(standard·dr × mug_tray·mug_marker·bottle_tray 각 6, meta split 모두 dev). LeRobot 내보내기 시험 **6 passed**. |
| 2 모델 | 충족(CPU) | GPU 없음(2·3 = S-E2E, 0·1 = hard-reset 작업·내 Isaac) → CUDA 시험·GPU 재적재 확인은 건너뜀. 파드 CPU `stageb_train smoke --backbone tiny --device cpu`(10:46:38–10:47:10 UTC): 손실 감소(학습 총손실·fm), `save_load` 차 0.0, KI 0.0(N12); CPU 묶음의 `test_stageb_torch.py`(재개 비트 재현·체크포인트 주기·설정 변경 거부)·`test_r7c12_last_step.py`(`check_prompt` 거부) 통과. 진행 중인 S-E2E 실제 GPU 학습(N4). |
| 3 폐루프 | 충족 | §6.1 Isaac 판(`CLOSED_DONE`, 로그 행 필드·blob 확인, `meta.bootstrap` 10000, `meta.prereg` OK). |
| 4 평가 | 충족 | 모의 한 명령(`venv_vllm`, GPU 없음, 절대 경로; 10:49:25–10:49:54 UTC): `e05 --data …/jsel_dev/P0,…/P1 --split dev --episodes 2` → `E05_DONE`(claim `a_as_stabilizer`, 편 4·스냅샷 117·스텝 101, 판정 키 13, `same_k` 3), `rd --variants standard=…,random=…/gen_dev/random/P0 --episodes 1` → `RD_DONE`(n 135), `calib --fit-data …/pool --fit-split pool --heldout …/jsel_dev/P0 --heldout-split dev --episodes 4` → `CALIB_DONE`(질문별 `heldout.n_ece` 96). 모두 rc 0, prereg OK, git `e6ab8560`. (상대 경로 첫 판의 0편 rc 0은 N5.) |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·카나리·시드·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`j5_*`; 정리 뒤 흔적 없음(머리 규칙 줄). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`)
- `e05 --split cal|test|test_p5`, `calib --fit-split cal`, `rd --split test`, `closed --split test --seeds 1000`, `closed --split cal --seeds 549` → "--split X refused: set HARVEST_ALLOW_SPLIT=X (main session only …)". `closed --split dev --seeds 30`·`--split pool --seeds 5` → "not in split … (refused, never opened)". `--isaac-gpu 2` → "0 or 1 only (GPU 2 never renders)". `--conditions C5p`·`C2p` → "runtime has ['C0', …, \"C5'\", 'C6']". `--m4-h 0`, `--m4-lead-max inf`·`0` → ValueError. `HARVEST_ALLOW_SPLIT=dev closed --split test`, `HARVEST_ALLOW_SPLIT=cal e05 --split test` 거부. 옛 체크포인트 `closed`·`e05` 거부(빈 폴더, N6). `gen gen --seeds 10005-10006` → "R2 generates DEV 0-29 only (… --confirm-train)". **20건 모두 rc 1**, 분할·옵션 거부는 출력 폴더 0개.

### 6.5 A. 테스트
- 로컬(`…\r7c13\repo` = e6ab856 archive, Git Bash, `python -m pytest -q -rs -p no:cacheprovider --basetemp=…\r7c13\pt1 -o addopts=""`, TMP·TEMP·TMPDIR = scratch, 10:34:32 UTC 끝): EXIT 0, **898 passed · 12 skipped**(torch 없음 8, inspect_robots 2, pyarrow 1, TODO(P3) 1). hard-reset 에이전트의 커밋 안 된 시험은 사본에 없음.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, TMPDIR·pyc·카나리·qid 등록부 = scratch, 10:43:17–10:46:38 UTC): **946 passed, 3 skipped**, EXIT 0.

### 6.6 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외)
- 정본 범위: handoff `:3`·`:5`·`:83` = §77(맞음). user-log 번호: handoff `:12`(**D-3**).
- "메인 확인"·"[결정 필요]": handoff `:104`, `r7c12_fixes.md:20`·`:57-60`(**D-1**); `r7c10_fixes.md:83` 이하·`r7c9_fixes.md:15`·`:88`은 해결 표시 있음; `se2e_data.md:107`·`e_m4b_meas.md:50`·`:211`은 11·12회차 판단 그대로.
- C5'·되먹임: `r6_eval.md:46`(**D-2**); `conditions.py`·`core.py`·`serialize.py`·`closed.py` 주석, `test_runtime_r6.py:40`은 §77과 맞음; 설계 문서(`D4`, `D6`, `SUMMARY`, `plan.md:112`, `v3/18`)는 사전 등록 조건 문장. 논문 `X_suppl.tex:104`(N11).
- 직렬화기 판본 `ser-A-min-1`: 코드는 모두 -2(`stagea_train.py:113`의 -1은 거부 메시지 문자열); 결과 문서·옛 계획서(N10).
- 호출 기록 필드: `r5_closed_loop.md:117`·`r7_fixes.md:37`은 당시 추가분 기록, 전체 필드라고 주장하지 않음; 논문 `4_setup.tex:29`(N11).
- 재생 결정성: `labeler.md:39-40`·`pool_replay_debug.md`·`r2_datagen.md:14,147` 서로 맞음; 정본 기록 없음(N2).
- 날짜: 정본 §77 10:00 UTC·보충 10:25 UTC, handoff 머리 10:00 UTC, 커밋 10:31:21 UTC, `r7c12_fixes.md` 10:18 UTC — 순서 맞음.

### 6.7 F. 규칙·위생
- 저장소: 작업 트리는 읽지 않고(시작·끝 `git status` = hard-reset 에이전트의 4개 항목 그대로) 이 보고서 한 파일만 추가. 로컬 C:: 이 검토의 산출물 없음(하네스 작업 출력 파일만). 파드: 시작 전 목록과 대조해 내 항목만 삭제, 끝에 내 프로세스 0, `/data` 밖 새 파일 0(`find / -xdev … -newermt 10:40 UTC`), 루트 "C:" 폴더 0. 남의 파일(`/data/harvest/canary`, `r2/dev`, `data/*`, `ckpt/se2e/*`, `logs/se2e`)은 읽기만(카나리 시험은 scratch 복사본).
- 규칙 쪽 결함: CLAUDE.md 제약 누락(**D-4**).

## 7. 다음 순회 전에 할 일 (제안)
1. **D1**: FLIP_TH 초기값을 질문별(`question_id@vN`) 성공 스텝 점수의 split conformal q̂(`calibration.conformal_qhat`)로 내고 n이 모자라면 "문턱 없음"으로 보고 — 또는 정본에 E0.5 초기값의 추정식·척도를 결정으로 적는다(런타임 `flip_score`가 질문별임을 함께).
2. **D2**: 카나리 기준 선택에 `question_ids`(또는 serializer·프롬프트 해시)를 넣어 판본이 바뀌면 새 기준일로 시작.
3. **D3**: 표류 의심 이후에는 그 날짜 뒤에 맞춘 보정 파일이 있을 때만 J5를 켠다(가장 최근 카나리 하나가 아니라 기준 이후의 모든 카나리를 봄) — 또는 정본에 결정.
4. **D-1–D-4**: 해결 표시(§77 보충), `r6_eval.md:46` 정정 표시, handoff user-log 번호, CLAUDE.md에 user-log 69·70(·67) 제약.
5. NOTE N1(학습·런타임 짝 맞춤)·N2(PhysX 이력 의존의 정본 기록)·N3(판정 스크립트 커밋·해시)은 판정 3·E-M4·S-E2E 판정 전에 처리 권함.
