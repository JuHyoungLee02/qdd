# R7 12회차 지적 수정 (DEFECT D1–D4, DOC D-1·D-2, NOTE N1–N8)

- 작성 2026-09-25 10:18 UTC(`date -u`). 대상 `D:\qdd` `dev` — 시작 때 HEAD `6b013ac`, 작업 중 다른 에이전트 커밋으로 HEAD `900869c`(S-E2E 사전 등록·`stageb_train.py`, 논문, 라벨러 재생 조사; 이 수정과 겹치는 파일 없음) + 작업 트리. 커밋·푸시 안 함(메인 세션). 입력 보고서 `docs/stage3/results/r7_cycle12.md`(FAIL, DEFECT 4, DOC 3).
- 원칙: 사전 등록(`E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`, 조건 정의 `M4-overlap-commit.md`)과 정본은 구속한다. 코드는 사전 등록 문장을 그대로 구현했고, 문장이 열어 둔 값·한계는 정본 **§77**(끝에 덧붙임)에 적었다. 사전 등록 문서는 바꾸지 않았다(`python tools/prereg_hash.py --check` OK).
- 동시 작업: `harvest/sim/*`·`tests/sim/*`(재생 조사 에이전트), `harvest/train/stageb_train.py`·`docs/stage3/prereg_se2e.md`·`se2e_train.md`(S-E2E 에이전트), `harvest/datagen/*`(R2_TRAIN 생성, 6b013ac 고정)는 건드리지 않았다. GPU는 쓰지 않았다(파드는 CPU만). `[사용자]` 줄·사용자 인용 수정 없음. `paper/` 수정 없음.
- 로컬 임시 `D:\tools\scratch_qdd\r7c12fix`(6b013ac 사본 `base/`, 파드 사본 `podcode/`, 대조 `char_run.py`·`char_cmp.py`·`char_cmp.txt`, 크기 `blob_sizes.py`). 파드 `juhyoung-native-7a2a:/data/harvest/tmp/r7c12fix`(324 MB)는 끝에 지웠다(10:16 UTC); 시작(09:59 UTC) 뒤 `/data/harvest`에 새로 생긴 다른 경로는 모두 다른 작업(R2 생성·S-E2E·재생 조사)의 것이다.
- 절차 실수 1건: 빈 명령을 확인하려다 Git Bash에서 `python -`를 한 번 띄웠다(표준 입력 대기, 아무것도 실행하지 않음) — 바로 멈췄다(TaskStop). 파드 파일 전송은 `kubectl exec -i … bash -c "cat > <pod path>"`(파드 쪽 리디렉션, 로컬 heredoc 아님).

## 1. D3 — (b) 범주를 결정 모델 입력에 (가장 중요)

사전 등록 원문(정본 §77에 인용): M4 §4.2 `next_jev_input.add_line(f"last_step: {s.outcome}")  # (b) → Jev 입력 (C5'와 대조)`(:232), §3 #10 "Jev에 넘길 때는 범주 한 줄만"(:155), §0 "범주를 다음 Jev 입력에 넣는다"(:43), 조건 C4 "(b)만(범주 + epoch 무효화, 가장 새 표)"(:340), C5 "§4.2 전체"(:341), **C5' "C5에서 (b) 범주를 Jev 입력에서 뺌(코드 재계획만)"**(:342), 판정 3(:361). 정본 §58(결정 모델 = 융합 VLA의 결정 토큰, 모듈형 기준선 = Jev-L), §60·§61·§64(범주의 출처 = T1 고유 감각 + V1h).

| 무엇 | 결정 |
|---|---|
| 형식 | 모든 DecCall 상태의 마지막 줄 `last_step: <none\|OK\|LAG\|DEVIATE\|CONTRADICT>`(`serialize.with_last_step`, `deccall_snap.build_snapshot_request`, `models.build_live_request(last_step=)`). 행동 전문가 문맥(`ctx_text`)에는 없음. |
| 판본 | `SERIALIZER_VERSION` **ser-A-min-1 → ser-A-min-2**(J1 직렬화기 판본 → question_id 전부 바뀜 → 옛 보정 파일 거부). 단계 A `prompt_config.serializer`. 옛 체크포인트 거부: `eval/common.training_prompt_config`(e05·calib·rd·closed·canary 공통 입구), `fused_model.check_prompt`(`serializer_ok`). 단계 B는 `stageb_train.prompt_config`(S-E2E 파일)에 필드가 없어 프롬프트 파일이 바이트 단위로 같을 때만 현재 판본으로 읽음(`stagea_train.serializer_of`) — 다음에 그 파일을 고칠 때 `"serializer"` 한 줄 추가 권함. |
| 런타임 값 | `OursRuntime.b_line()` = 마지막으로 끝난 스텝의 (b) 범주(경계: 잔차 → T1 CONTRADICT; 그 스텝의 늦은 T2 DEVIATE가 OK·LAG를 DEVIATE로), 첫 스텝 전 none. 같은 틱 호출은 경계 판정 전에 만들어지므로 다음 호출부터(DEVIATE·CONTRADICT는 조기 호출로 다음 틱). 호출 행에 `last_step` 기록. |
| 조건 | C4·C5·C6 범주 실음; C0–C3 항상 none(원래 (b) 없음); **C5' 런타임 조건 추가** = C5 + `b_to_model=False`(원장 epoch·재개방·hold 그대로). C5'의 "뺌" = 줄을 지우지 않고 none(학습 모델 입력 분포 유지, 범주 정보만 제거) — [Claude 결정, 정본 §77]. 폴더명 `C5p`. |
| 학습 자료 | 그 편이 기록한 실행 뒤 확인 → 런타임 규칙(`deccall_snap.category_of_check`: 스텝 안 단계 전환 → OK, T1 기대 어긋남 → CONTRADICT, T2 → DEVIATE). R2 줄 = 이미 기록된 `verify.prev_step`(**생성기 변경 불필요** — 지금 도는 R2_TRAIN 자료에서 그대로 유도됨), POOL·DEV(`cli_pool`) 줄 = 앞 스냅샷 단계 기대를 이번 기록 술어(`truth9`, contact_stall 모름)로. 첫 스냅샷 none. S-E2E는 자체 문맥(`se2e.*@v1`)이라 줄 없음. 적용: `stagea_data.build_items`, `stageb_data.load_stageb`, `eval/common.load_episodes`, 카나리 FusedAsker, `fused_model.bench`. |
| 무효화 | 지금까지의 **모든 체크포인트**(단계 A §55·단계 B·R4·V1h·S-E2E 스모크; 모두 §56 파이프라인 확인용), **진행 중인 S-E2E 학습의 체크포인트**(6b013ac 프롬프트 파일 고정)도 새 코드의 검사에서 거부된다 → 메인 확인 요청 [해결 R7 13회차 D-1: 정본 §77 보충 (2)(2026-09-25 10:25 UTC) — S-E2E 판정은 6b013ac 고정 사본으로, 이 체크포인트는 폐루프에 쓰지 않음]. 보정 파일·카나리 기준·qid 등록부 새로(카나리 기준일의 판본 대조는 [R7 13회차 D2, 정본 §79]). |

파드 기록 자료에서 유도한 값(읽기 전용, 결정 스냅샷): R2 DEV 36편 — none 36, OK 1,024, **DEVIATE 21**(예: 놓은 뒤 `on(o8,o5)` 기대 어긋남); POOL 120편 — none 44(모두 k0), OK 1,155, CONTRADICT 1; jsel_dev 90편 — none 23, OK 877. → DEVIATE·CONTRADICT가 드물다(학습 신호가 약할 수 있음, 메인 확인 요청 1 [해결 R7 13회차 D-1: 정본 §77 보충 (1) — 본 단계 B 학습 사전 등록 때 정함]).

알려 둘 한계(정본 §77 (v)): 자료에는 잔차 범주(LAG·잔차 DEVIATE)가 없어 런타임 LAG는 학습에서 못 본 값; 자료 = 시뮬 참값, 런타임 = T1 규칙 + V1h conformal; 모듈형 백엔드는 V1h가 없어 런타임 T2 DEVIATE 없음.

## 2. D4 — 호출 재현 기록
- 결정 호출 행: `probs`(질문별 보기 확률, option_key; 보정 시 `probs_cal`), `last_step`, `request_blob`(= `request_sha256`, 해시한 정규 JSON 본문 그대로), `response_blob`(백엔드 원응답 — Jev-L CallRecord 이름별 확률·확신·n_seq·토큰·시각, 융합 `/decide` 응답, 모의 규칙 답; `ModelResult.raw`).
- Astra 행: `output_text`(원응답), `max_output_tokens`, `effort`, `request_blob`(요약 텍스트가 든 요청 본문), 머리캠 JPEG 원본 blob.
- 저장: `<run>/blobs/<sha256>.{json,jpg}` 내용 주소, 한 번만(`ir_policy.write_blobs`, `trial_metadata.ours_blobs`). 크기(가짜 세계 60 s): 결정 요청 2.4–2.8 KB·응답 0.55 KB × 181 + Astra ≈ 0.55–0.6 MB/편. **결정 호출 이미지 바이트는 해시만**(원본 저장 시 약 18 MB/편) — [Claude 결정, 정본 §77]; Astra 이미지는 원본 저장(§28 A6).

## 3. D1·D2 — E0.5 지표
- D1: `flip_th_candidates` 키 q0.99·q0.999·q0.95(α 0.01 사전 등록 + M4 α 범위 0.001·0.05), `flip_th_initial` = α 0.01. α 0.1 제거.
- D2: `same_time_flip_by_trajectory` {success = P0 성공 편, perturbed = P1·P2 편 전 스텝}; 층별 `a1flip`(= subst)·`a2flip`·`a3flip`·`a4flip`. 판정 6은 사전 등록 문장대로 합친 값. 보고서 표에 두 줄 추가.

## 4. DOC·NOTE
- D-1 handoff `:3`·`:5`·`:83` → §1~§77·지금 §77, 머리 시각 10:00 UTC, §2.8 12회차 줄(병렬 시작한 S-E2E·R2_TRAIN 포함). D-2 `r7c9_fixes.md:88` 해결 표시. N1 `r7c10_fixes.md:72` 표시를 넷째 칸 안으로. N2 `closed.py` 주석 "finite". **D-3 보류**(`snapshot.py`는 재생 조사 에이전트 영역 — 정본 §77에 보류로 적음).
- N3 FROZEN = 송신 시각 기준(정본 §77 한 줄). N4 E0.5 채점 = labels_v2, 판정 7 순환(무엇을 보일 수 있고 없는지 정본 §77). N5 `fine_dir` 묻지 않음 → SCOPED. **N6 구현**: 카나리 `drift_suspect`이고 보정 파일이 그 날보다 앞이면 J5 끔(`closed.j5_after_canary`, spec·meta `j5_alpha` None + `j5_canary_gate`; E §3.7-8 :347 "끄고 재보정"). **N7 구현**: `latency.step_votes`·`judgment4`(스텝당 표 중앙값 ≥ 2, lead 1.5·1.0), `judge_e0` 출력 `j4`; Jev-L E0 측정 도구는 여전히 없음(SCOPED). N8 SCOPED 모음 = 정본 §77 마지막 목록.

## 5. 시험 (RED → GREEN)
| 새 시험 | RED(수정 전) | GREEN |
|---|---|---|
| `tests/runtime/test_r7c12_b_feedback.py`(12: 강제 DEVIATE 뒤 C4·C5·C6 × 모듈형·융합 다음 요청이 DEVIATE, C5'·C0–C3는 none, C5' = C5 + b_to_model만) | 요청에 `last_step:` 줄 0개 | 통과 |
| `tests/train/test_r7c12_last_step.py`(6: 판본, POOL 유도, R2 `verify.prev_step` 유도, 학습 항목 = 런타임 요청 같은 줄, 단계 A 옛 판 거부, 융합 `check_prompt` 거부 — 마지막은 torch 필요라 파드에서) | 속성 없음·줄 없음·KeyError | 통과(로컬 5 + 파드 6) |
| `tests/runtime/test_r7c12_call_log.py`(3: 확률·요청/응답 blob 해시 일치·Astra 필드·blob 쓰기) | KeyError·ImportError | 통과 |
| `tests/eval/test_r7c12_e05.py`(3) | q0.99 없음·키 없음 | 통과 |
| `tests/eval/test_r7c12_canary_gate.py`(7) | 함수 없음, spec α 0.1 그대로 | 통과 |
| `tests/test_r7c12_e0_j4.py`(3) | 함수·`j4` 없음 | 통과 |
기존 시험 5개는 의도된 형식 변경에 맞게 기대값만 고침(`test_serialize` 판본, `test_deccall_snap` 상태 끝 줄, `test_stageb_data` 항목 = 문맥 + `last_step: none`, `test_runtime_r6` 조건 목록 + C5', `test_common` 옛 run 거부).

## 6. 무작위 대조 (6b013ac 대 수정본, 가짜 세계)
`char_run.py`: 160판 = 8조건(C0–C6, C5') × 20, H ∈ {1, 3}, W 0–2, 잡음 선택기 0/15/30 %, 지연 {0.2–1.6} 고정 또는 흔들림, 시작 오프셋, 무작위 틱에 강제 DEVIATE. 6b013ac와 비교 가능한 140판(C5'는 옛 코드에 없음): **행동 바이트 해시·원장 counts·epoch·호출 수·`last_step` 줄을 뺀 요청 상태가 모두 같다.** 달라진 것은 요청 상태 마지막 줄뿐 — C4·C5·C6 요청 2,068개 중 범주(OK·DEVIATE)를 실은 것 1,968개(나머지는 첫 스텝 전 none), C0–C3·C5' 요청 3,438개는 모두 none. 모의 선택기는 이 줄을 읽지 않으므로 행동 차이는 학습 모델에서만 생긴다(판정 3이 재는 것). (첫 판에서 폐루프 뒤 늦게 끝난 워커 호출이 목록에 섞여 몇 판이 다르게 보였다 — 측정 스크립트 쪽 경쟁이라 `pool.shutdown(wait=True)` 뒤 읽도록 고쳐 다시 돌림.)

## 7. 시험 묶음
- 로컬(Git Bash, TMP·basetemp = D:): 마지막 판(10:21 UTC, 재생 조사 에이전트의 커밋 안 된 새 시험 파일 2개 `--ignore`) **898 passed, 12 skipped**(건너뜀 = torch 없음 8(새 `check_prompt` 시험 포함), inspect_robots 2, pyarrow 1, TODO(P3) 1; 새 시험 34개 수집). 그 직전 판(10:17 UTC)은 재생 조사 에이전트가 그사이 추가한 커밋 안 된 파일(`harvest/sim/scene.py` 수정, `harvest/sim/determinism.py`, `tests/sim/test_hard_reset.py`·`test_determinism_isaac.py`)이 섞여 905 passed, 13 skipped, **1 failed = `tests/sim/test_hard_reset.py::test_new_scene_is_built_with_the_seeds_object_poses`(그 에이전트의 작업 중 파일, 이 수정과 무관 — 고치지 않음)**.
- 파드 CPU(`juhyoung-native-7a2a`, `venv_train`, `CUDA_VISIBLE_DEVICES=""`, 코드 = `git -c core.autocrlf=false archive 900869c` + 이 수정 파일(재생 조사 에이전트의 커밋 안 된 파일 제외), third_party 포함, tar sha256 `6c2bbc38…`): **946 passed, 3 skipped**, rc 0(10:12–10:15 UTC). 첫 판은 7 failed — 내가 만든 `CODE_VERSION`을 JSON이 아닌 글로 써서 `common.git_commit`이 읽지 못한 것(설정 실수), JSON으로 고쳐 다시 돌림. 새 시험 34개 파드 통과(torch 있는 `check_prompt` 시험 포함).

## 8. 메인 확인 요청
[해결 R7 13회차 D-1: 세 항목 모두 정본 §77 보충(2026-09-25 10:25 UTC, 메인 결정)이 정했다 — 1은 (1), 2는 (2), 3은 (4)]
1. R2 자료의 `last_step` 범주가 드묾(DEV 1,081 중 DEVIATE 21, CONTRADICT 0) — 본 학습 전 분포 확인·가중 여부. [해결: §77 보충 (1) 본 단계 B 학습 사전 등록 때 정함(비 OK 가중·섭동 설계)]
2. 진행 중인 S-E2E 체크포인트: 새 코드의 `check_prompt`·`training_prompt_config`는 옛 판본으로 거부한다. S-E2E 평가를 6b013ac 코드로 할지, `strict_prompt=False` 진단으로만 볼지. [해결: §77 보충 (2) S-E2E 판정은 6b013ac 고정 사본으로, 이 체크포인트는 폐루프에 쓰지 않음]
3. (선택) `stageb_train.prompt_config`에 `"serializer": SERIALIZER_VERSION` 한 줄(S-E2E 에이전트 파일이라 이 수정에서 안 넣음). [해결: §77 보충 (4) 다음 그 파일 수정 때]
