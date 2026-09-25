# R7 객관 검증 순회 — 34회차 (cycle 34, 연속 무결 카운트 1에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle33.md`의 표·결론을 근거로 쓰지 않고 972b0be의 바뀐 줄마다 diff·원 문서·파드 원자료·파드 명령 출력으로 다시 확인했다 — 책 P68). 가드·음성 대조·Isaac 시드·모의 평가 입력은 **21–33회차와 다른 새 값**. 작성 2026-09-25 23:20 UTC 무렵(archive 22:58:46Z, 로컬 사본 풀기 22:59:17Z, 파드 첫 명령 22:59:44Z, 파드 정리 끝 23:15:10Z). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`972b0be`**(`972b0be3eb775753483fa82021af1ec3d9f4b0e3`, 커밋 시각 2026-09-26 07:57:04 +0900 = **2026-09-25 22:57:04 UTC**, "R7 cycle 33 baseline PASS (clean count 1) — records only"). `d0e25f4..972b0be` = 커밋 1개, 4파일, 모두 문서(draft-log +1, handoff 3줄 수정 + 1줄 추가, direction-log +1, 새 `r7_cycle33.md`); **코드·시험·사전 등록·정본·책 변경 0**(`check34` H1). 뒤 커밋은 범위 밖. 작업 트리에는 이 보고서 말고 다른 에이전트의 미커밋 `docs/stage3/results/r2_train_gen.md`(22:56:10Z 작성)가 있다 — 읽기만 했다.
- **범위 나눔(33회차와 같은 틀)**: **기준선 판정**(연속 무결 카운트) = `harvest/`·`tools/`(실험 도구 제외)·시험·정본·사전 등록·handoff·기록·결과 문서·기록책. **실험 코드 절**(따로 판정) = 972b0be 이하에 커밋됐으나 아직 검토되지 않은 실험 코드.
- **지시 전제와 다른 점**: 지시문은 "handoff §0 R2_TRAIN 줄(확인 22:35 UTC)은 d0e25f4 뒤 그대로"라고 했으나, 972b0be는 이 줄을 **R2_TRAIN 운영 에이전트가 쓴 새 줄(확인 22:56 UTC)로 바꿨다**(`git diff d0e25f4 972b0be -- docs/handoff.md` `@@ -11,2 +11,2 @@`). 그래서 이 줄을 바뀐 줄로 보고 모든 주장을 파드 원자료로 다시 셌다(§6.2).
- 사본: `git -c core.autocrlf=false archive 972b0be`(tar 주석 = `972b0be3eb77…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c34\repo`에 풀었다(**597파일** = 33회차 596 + `r7_cycle33.md`, 텍스트 513파일 CR 0). 파드 사본 = 같은 tar(텍스트 멤버 CR 0 확인 뒤)를 `kubectl exec -i … tar -xf -`로 `/data/harvest/tmp/r7c34/code`(598파일 = + `CODE_VERSION`), 코드 사본 텍스트 CR 0, 올린 스크립트 CR 0(올릴 때마다 확인). 파드 산출 `meta.git.commit` = `972b0be3eb77…`, dirty false.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle33.md`, 정본 `00-interfaces.md` §1–마지막 절(보충 포함, 뒤 절 우선), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록(`prereg.json` 해시, `prereg_*.md` 10개, E-first `§1.5`·`§1.6` 원문), 기록책 README 규칙(`:8`–`:11`)과 02-pitfalls P01–P71.
- 분류(33회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·결과 문서·원자료와 다르고 정정 표시가 없는 것. handoff §0의 줄은 **그 줄의 확인 시각에 참이면** 뒤에 일이 진행돼도 낡은 것으로 보지 않는다. SCOPED·NOTE는 33회차 정의 그대로.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c34`(C: 쓰기 없음). 스크립트는 전부 Write 도구로 쓰고 경로로 실행(heredoc·`cat >`·`python -`·`python -c`·sed 생성 없음; `check34.py` 초안에 들어간 `python -c` 자리표시 줄은 실행 전에 지웠다). 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c34`, `source /data/harvest/env.sh`, 모든 kubectl에 `MSYS_NO_PATHCONV=1`. GPU: Isaac = GPU 1에 **내 프로세스 하나**(`IR_ROOT=cyclo`, `IR_INST` `r7c34_standard`, `--inst-prefix r7c34`); GPU 0·2·3에는 아무것도 올리지 않음. 남의 프로세스(R2_TRAIN `export_all.sh` 6개 + 부모 = 7, 22:36:47Z 시작)는 건드리지 않음; R2_TRAIN 파일·로그는 읽기만. CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`. 시드 DEV·POOL만. 유료 API 없음. 비밀값 출력·검색 없음.

## 판정 (기준선): **FAIL** (DOC 1 → 연속 무결 1 → **0**)

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 1 |
| SCOPED | 20 |
| NOTE | 128 |

## 판정 (실험 코드 절, 카운트와 별개): **해당 없음 — 972b0be 이하에 검토되지 않은 실험 코드 없음**

`d0e25f4..972b0be`에 코드 경로 0(H1). 그 앞의 마지막 실험 코드(E-CAM3·E-MA3, `5c46056`·`40895f8`)는 28–33회차가 검토했고 33회차가 판정을 재계산했다. 확인만 다시 함: 사전 등록 문서에 적힌 (경로, LF 블롭 sha256 앞 16) 쌍 **26개**(`prereg_cam3` 9·`prereg_ma3` 8·`prereg_ma1` 4·`prereg_ma1b` 5)를 등록 원문에서 직접 읽어 972b0be 사본과 비교 → 불일치 0(`hashes34.py`).

**기준선 코드는 33회차 대상(d0e25f4)과 바이트가 같고 모든 동작 검사가 통과했다**: 로컬 **1133 passed / 20 skipped**(231.6 s), 파드 CPU **1280 passed / 4 skipped**(167.7 s), LeRobot 6 passed; 가드 **33건 + 재설계 2건** 모두 rc ≠ 0이고 거부 사유가 맞다(21–33회차와 다른 경계값); R2 DEV `validate_episode` **36/36** + **새 종류 대조 15종**(통과해야 할 경계 4종 통과, 검출해야 할 9종 모두 검출, 관찰 2종); 실데이터 훑기(DEV 36편 10,651프레임 + R2_TRAIN 새 3폴더 **마지막** 100시드씩 300편 91,716프레임: 불일치 0); 모의 평가 한 명령씩 완료; 새 시드 **DEV 16**에서 같은 Isaac 워커 C5 → C5' 행동 **1,611개 비트 동일**; R2_TRAIN 18폴더 독립 재집계(유효 5,126·행 1,495,348·결정 152,409, 18/18 일치). **실패 사유는 문서 한 줄**: 972b0be의 handoff §0 R2_TRAIN 줄이 커밋에 없는 결과 문서를 가리킨다(D-1).

---

## 1. DEFECT

없음. (`git diff --name-status d0e25f4 972b0be`에 `harvest/`·`tools/`·`tests/`·`prereg*`·정본·책 경로 0 — `check34` H1.)

## 2. DOC

- **D-1. `docs/handoff.md:11` (972b0be) — §0 R2_TRAIN 줄이 커밋에 없는 결과 문서를 현재형으로 가리킨다.** 줄 끝 "결과 `docs/stage3/results/r2_train_gen.md`." — 이 파일은 972b0be에 없다(`git ls-tree 972b0be docs/stage3/results/`에 0건; 작업 트리의 미커밋 파일, mtime 22:56:10Z, 머리에 "git 커밋 안 함(메인 세션이 커밋)"). `check34` H12가 handoff §0·§2.8에서 찾은 **유일한 없는 경로**다. 확인 시각 규칙으로 덮이지 않는 이유: 이것은 뒤에 일이 진행돼 낡은 상태가 아니라, 커밋된 판에서 처음부터 참이 된 적이 없는 저장소 경로 참조다(새 세션이 handoff를 먼저 읽고 이 경로를 열면 없다). 경위: "records only" 커밋이 다른 에이전트가 작업 트리에서 고친 handoff 줄을 함께 싣고, 그 줄이 가리키는 결과 문서는 싣지 않았다(P14 "남의 미커밋 … 중간 상태가 커밋됨"과 같은 모양; 33회차 보고서 8절 2도 "결과 문서를 커밋할 때 §0 줄을 지운다"고 적었다). 같은 줄의 **다른 주장은 모두 참**이다(§6.2 — 수치 전부 독립 재집계와 같음).
  - **고침**: R2_TRAIN 결과 커밋에서 `r2_train_gen.md`를 싣고 **같은 커밋에서** README `:11` 규칙대로 §0 R2_TRAIN 줄을 지운다(LeRobot 내보내기가 아직 돌면 그 부분만 새 확인 시각의 짧은 §0 줄로 남김); 같은 커밋에 책 01 `:69` R2_TRAIN 행(`[결과 전]` → `끝` + 링크), 04 `:63` N141 괄호 정리, 05 GPU 시간, 06 한 줄, draft-log·direction-log 줄. 결과 커밋 전에 §0 줄을 다시 커밋해야 한다면 "결과 문서 작성됨(미커밋, 메인 세션 커밋 예정)"처럼 커밋 상태를 적는다. 앞으로 기록 커밋은 `git add`를 파일·줄 단위로 하고, 남이 고친 §0 줄이 섞이면 그 줄의 인용 경로가 커밋에 있는지 H12 식으로 확인한다.

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN(§66, §77 N8 (4)) — 생성·`gen check`·병합 검증 끝(§6.2), 결과 문서 커밋은 메인 세션 일(D-1 고침과 같이). LeRobot 내보내기 6개 실행 중(23:14:43Z에 데이터셋마다 287–340편). 확인 인자 없는 `--seeds 10003` 거부(가드 19).
- S3. CAL 보정·TEST 평가(`HARVEST_ALLOW_SPLIT`) — 가드 §6.3.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8. S6. Astra 카나리 "none"(§67 보충). S7. S-E2E 체크포인트 런타임 형식 차(§77 보충 (2), §80). S8. CONTRADICT-soft(§68 K6). S9. §73 D5 M4 설계 확장. S10. §73 N5 E1 범위. S11. §74 보충 E-M4-lat 비례 STALE_MAX. S12. §75 보충 (2) E-M4 판정 7. S13. §77 N8 (13) 완료 정의 밖 사전 등록 실험. S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석(그대로). S15. §79 보충 `flip_th` 질문별 사전화. S16. §78 "남은 것"(dr·random 변형, CUDA PhysX, P2 결정성 행렬). S17. §78 (2) 옛 물리 녹화 재녹화·재라벨(책 01 `:70` `[예정]`).
- S18. 정본 §82·§84·§86(+보충) 결합 설계 구현("R7 관문 뒤") — `closed --hb-mode K10`·`"K3,K4"`(예산 없음) 워커 전 거부(가드 26·27), DEV 16 Astra 요청 이미지 1장·effort low·600, 흐름 호출 없음.
- S19. 정본 §83 런타임 적용("R7 관문 뒤") — DEV 16 결정 호출 요청 96/96 `motion:` 없음.
- S20. 탐침 E-Astra-motion 결과의 E-Couple 재측정(§86).

## 4. NOTE
- N1–N3, N5–N11, N13–N21, N23, N26, N28–N30, N34, N36, N38, N39, N45, N46, N49–N53, N57, N58, N71, N73, N74, N79, N90, N91, N94, N129, N131–N138, N142–N148, N151–N155. (그대로.) N10 재현: 가드 25(`e05 --data jsel_dev/P0 --split pool --seeds 2105`)가 빈 `g25/`를 남김. N141: 책 `04:63` 괄호 정리는 R2_TRAIN 결과 커밋에서(D-1 고침). N155 재현: DEV 16도 `astra_by_kind {hb 2, sub 1}` 대 Astra 행 2.
- N4, N47, N48, N54–N56, N66–N70, N72, N84–N88, N92, N93, N102–N108, N116–N122, N128, N130, N139–N141(표시), N149. (해소·표시, 그대로.) N109–N115, N123–N127, N156–N160(이전 회차 자체 기록).
- **N150.** (해소) 옛 §0 R2_TRAIN 줄(확인 22:35)은 972b0be에서 새 줄로 바뀌었다. 계산: 33회차 117 − 해소 1(N150) + 새 12(N161–N172) = **128**.
- **N161.** 새 §0 R2_TRAIN 줄의 세부 표기(모두 참, 표기만): ① "생성 6,000/6,000 끝(21:56:28Z)" = `logs/workers.log` "WORKER w2 done 21:56:28"(33회차는 npz·jsonl 마지막 mtime 21:56:26Z를 썼다 — 출처가 달라 2 s 차); ② 출처 괄호 "파드 `/data/harvest/r2train/final/` 산출물"인데 로더 확인 로그는 `r2train/loadercheck/full18.log`(final 밖); ③ "22:56Z에 데이터셋마다 약 150–175편" — parquet mtime 기준 22:56:00Z 145–172, 22:56:59Z 153–181("약"으로 덮임).
- **N162.** handoff `:138` 33회차 줄에 다른 §2.8 줄과 달리 보고 시각이 없다("R7 33회차(대상 d0e25f4)"). 판정·수치(DEFECT 0·DOC 0·SCOPED 20·NOTE 117)는 보고서와 같다(H10).
- **N163.** 972b0be 커밋 메시지 "records only"와 draft-log `:485`·§2.8 `:138`은 §0 R2_TRAIN 줄 교체를 말하지 않는다(D-1 경위). R2_TRAIN 에이전트의 확인 작업(`verify_merge.py` 22:33:24Z, `--reload-check` 22:46:33Z, `loadcount` 22:55:53Z)은 draft-log에 줄이 없다 — 결과 커밋 때 함께 적기를 권함.
- **N164.** (책 갱신 기록 전 이력 훑기, H5 — 이번 회차에 범위를 모든 책 변경 커밋 18개로 넓힘) 06 줄이 없는 커밋 2개: `e15270a`(책 처음 작성, 06 장이 생기기 전 — 06 `:6` 줄이 사후 기록), `641547e`(README 목차, 14 s 뒤 `6483397`가 "앞 커밋에서 갱신 기록 줄을 빠뜨려 여기서 보충" 줄을 더함). 둘 다 정정 표시가 있는 이력 → NOTE. 나머지 16개는 장 목록·시각(≤ 커밋 시각)·칸 수 4 모두 맞음.
- **N165.** (검증기 관찰, 새 종류 `auxnan`·`execbig`) 행 `aux.reg` 값 하나를 NaN으로, `action_exec` 값 하나를 1e6으로 바꿔도 오류 0 — `check_row`(`stageb_data.py:131`–`:161`)는 aux 이름만 보고 값의 유한성은 보지 않으며, 행동 값 범위는 보지 않는다(N142·N143·N154 계열). 권함: 기준점 태그 뒤 TDD로 aux 값 유한성 한 줄.
- **N166.** `e05 --truth outcome:plan`(POOL 2033·2072·2108)은 `E05_DONE`이지만 claim `insufficient_data` — `judge_input`에 `flip_rate_success`가 없다(`e05.py:482`–`:483`, 입력 세 편의 데이터 문제이고 코드 경로는 끝까지 돔; 33회차 입력 2019·2081·2117은 `a_as_stabilizer`). `retest_flip` n 415, 사전 등록 해시 OK.
- **N167.** 시험 수: 로컬 **1133 passed / 20 skipped**(231.6 s, 22:59:20–23:03:13Z, Git Bash, `-o addopts="-p no:cacheprovider"`, `-o tmp_path_retention_policy=failed`, basetemp `r7c34/pt`, `PYTHONDONTWRITEBYTECODE=1`; 건너뜀 = torch 15·isaaclab 1·LeRobot pyarrow 1·inspect_robots 2·TODO 1), 파드 CPU **1280 passed / 4 skipped**(167.7 s, 끝 23:02:48Z), 경고 1(기존), LeRobot 6 passed(18.0 s). 로컬 `tools/prereg_hash.py --check` → OK, `tools/intent_check.py` → total 124 flagged 0.
- **N168.** 단계 B 소형 CPU 스모크(23:09:11Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–33회차와 같음 — 결정적), expert p50 0.042 s·전체 p50 0.118 s, 맥락 토큰 454, dec_acc 0.292 → 0.708.
- **N169.** DEV 16 판: 행동 1,611·16.11 s 성공 종료(`terminations` success 1), 결정 호출 48(조건마다), C5 `last_step` {none 1, OK 32, LAG 6, DEVIATE 9}, C5' none 48/48, 확정 비율 0.902, 결정 2.981/s, rtf 0.5066, 지연 p50·p95 0.3 s, Astra 행 2(hb 5.0 → 8.0, sub 8.01 → 11.01, 겹침 0), `hb_mode` K2, `code_sha` `df7fcd9234b49658`(28–33회차와 같음), 파일명 `dev16-P0-standard-e0`, 판 208.2 s(23:10:33–23:14:01Z). 파드 GPU 전·후 모두 0 MiB(0–3).
- **N170.** (절차, 자체 점검) ① 실험 옵트인 가드 29·30을 처음에 `se2e_cam3 evalck`로 `--ckpt` 없이 설계해 argparse(rc 2, "the following arguments are required: --ckpt")에서 멈춰 `--cam3` 검사에 닿지 못했다 → `--ckpt`(없는 폴더)를 넣어 29b(`--data r2`)·30b(`--data se2e`, 움직임 줄 없음)로 다시 돌림: 각각 "--cam3: --data se2e only"·"--cam3: with the motion line (prereg_cam3 cells)", rc 1, 체크포인트를 열기 전 거부. ② 음성 대조 원본 = standard/mug_tray/P0의 **세 번째** 유효 편 ep2(261프레임; 25–33회차 원본과 다름). ③ LeRobot 새 입력: 유효 standard/mug_tray/P0 ep0·dr/bottle_tray/P0 ep5(26–33회차와 겹치지 않음) + 무효 dr/bottle_tray/P0 ep1 — DEV 무효 편 4개가 모두 이미 쓰였으므로 한 번만 쓰인(31회차) 것을 다시 씀. ④ 가드 13 `--isaac-gpu +1`은 문자열 검사(`closed.py:38`·`:391`)로 워커 전 거부됨을 코드로 먼저 확인하고 골랐다(`0.0`류는 쓰지 않음). ⑤ 정리 스크립트는 `bash -s`로 흘려 명령줄에 태그가 없게 했고 자기 매칭은 `grep 'r7c[3]4'`로 피했다. ⑥ 지시 전제("§0 R2_TRAIN 줄 불변")가 diff와 달라 그 줄을 바뀐 줄로 검토했다.
- **N171.** 텍스트 위생·기계 검사(`check34`): 사본 텍스트 513파일 CR 0; 변경 md 4개 BOM·CR·C0·C1·영폭 0, 표 행 칸 수 불일치 0(H3); 책 7장 표 칸 수 불일치 0, 링크 108개 끊김 0(H4); 이 범위 책 변경 0 → 06 줄 불필요(H5 전 이력은 N164); 현재형 진행 상태 검색(H9) — 02·06 이력 인용, README·04 규칙 문장, `01:38` "(아직)", `03:13`·`03:63` "실행 중 흐름/Astra effort"(결정 내용)뿐; R7 보고서 판정 줄(H10): 33개, PASS [6, 16, 20, 22, 31, 33], FAIL 27개 — handoff §2.8 33줄 모두 같은 판정, 30–33회차는 네 건수까지 같음; 책 01 상태 칸(H11) 3표 **40칸** — `끝` 34·`` `[예정]` `` 5·`` `[결과 전]` `` 1(R2_TRAIN `:69`, 결과 문서 미커밋이므로 맞음), 벗어난 칸 0; handoff §0·§2.8 저장소 경로(H12) — 없는 경로 1(D-1).
- **N172.** R2_TRAIN 에이전트의 로더 확인은 `code_r2train_e8e1864` 사본으로 돌았다. `git diff e8e1864 972b0be -- harvest/train/stageb_data.py`는 빈 결과(`stageb_train.py`만 +283/−31, 옵트인 옵션) → `load_for_training` 표본 수 1,495,348은 기준선 코드에도 그대로 적용된다.

---

## 5. 사전 등록 대조표 (원 등록 문서에서 다시 만든 행, 행마다 이번 회차의 새 입력으로 행동 확인)

`prereg.json` 해시(E-first §2.7·2A.6·3.7·4.8·5.6): 로컬 `prereg_hash.py --check` OK, 파드 산출 `meta.prereg.check` = OK(closed·e05 둘 다). 사전 등록 md 10개·계획·정본은 d0e25f4와 같다(H1). 원문 재확인: E-first `§1.5` 표(DEV 0~29 / CAL 500~549 / TEST 1000~1149 / TEST-P5 1300~1329 / POOL 2000~2119 / R2_TRAIN 10000~59999) = `eval/splits.py:13`–`:14` `RANGES`; 성공 규칙 "1 s 연속·60 s·낙하 즉시 실패"(E `:107`) = `sim/planner.py:27`–`:34`(`success_hold_s`)·`:416` off_table·`:431` time_limit; 부트스트랩 10,000 = `analysis/stats.py:4`; γ 2/3 = `runtime/m4.py:46` `GAMMA = "2/3"`; H 3·STALE_MAX 1.5·lead_max 1.0 = `m4.py:83`·`:88`·`:106`; Astra = `astra_hb.py:33`–`:34`(gpt-6-astra, low, 600; K0–K4). "확인" 열: **로컬** = `check34.py`·`hashes34.py`, **파드** = §6(`pod_cpu34.sh`, `pod_eval34.sh`·`data34.py`·`gtxt34.sh`·`guard34b.sh`·`e05o34.py`·`lr34.sh`, `pod_isaac34.sh`·`closed34.py`, `r2ls34.sh`·`r2show34.sh`·`r2verify34.py`, `attr34.sh`·`clean34.sh`).

| # | 사전 등록 값·절차 (출처) | 구현 | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 분할 DEV/CAL/TEST/TEST-P5/POOL/R2_TRAIN (E §1.5, §66) | `eval/splits.py`, `datagen/gen.py` | 가드(§6.3): TEST 1058·1140, CAL 541·527, TEST-P5 1308, DEV 2,34·1330, POOL 2150, gen 10003(확인 없음)·9995·60002(확인 있음), determinism 505·15,1311, 다른 분할 허용 2건(17 `dev`→cal·18 `cal`→test_p5) → 모두 거부 | 일치 |
| 2–4 | POOL 과표집·`ambiguous` 띠·에피소드 분할 (E :121-122) | `sim/snapshot.py`, `calib.halves` | `calib --heldout jsel_dev/P2 --episodes 3` → `CALIB_DONE`; 가드 3(`--fit-split cal`, heldout-split pool)·4(`--heldout-split test_p5`, heldout P0) 거부 | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | DEV 16 C5·C5' 둘 다 **성공 종료** 16.11 s·1,611스텝, 두 조건 같음 | 일치 |
| **6** | 호출 기록·Astra A6 (E §1.6, §28) | `core.py` | **DEV 16 결정 호출 96행**(조건마다 48): 요청 blob 해시·이미지 해시 포함·응답 blob·`probs`·`canary_id`·`question_id@vN` 96/96; Astra 4행 해시·effort low·600·이미지 1장·`output_text` 4/4 | 일치(N155) |
| 7–12 | 군집 부트스트랩 10,000, Holm, 판정 절 해시 | `analysis/stats.py`, `eval/common.py` | 파드 `meta.bootstrap` n_boot 10000·seed 0·percentile; `meta.prereg` OK; 시험 묶음 | 일치 |
| 13–17 | 카나리 기준일, 모델 식별 필드, E0.5 | `eval/canary.py`, `e05.py` | `e05 --data jsel_dev/P2 --split dev --episodes 3` → `E05_DONE`(claim `insufficient_data`); 가드 24(`canary build-set --data jsel_dev/P1 --seeds 3140-3141`) 거부 | 일치(N11) |
| 18–50 | γ 2/3, `C_flip`, 판정 1–10, FLIP_TH, ECE, J5 q̂, N_max·d̂ | `m4`, `stats`, `calibration` | 코드 무변경·시험 묶음; `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 / SCOPED S5 |
| **51–58** | STALE_MAX, C0–C6, C5·C5', H, n_LA (M4 §4, §75, §77) | `m4`, `conditions`, `core.b_line` | 가드 16 `"C5,C8"` → "condition 'C8': runtime has ['C0' … 'C6']", 가드 33 `--m4-h=-7` → "M4 H = -7 … >= 1"; **DEV 16 C5 `last_step` {none 1, OK 32, LAG 6, DEVIATE 9}, C5' none 48/48, 요청 본문 마지막 `last_step:` 줄 = 행 값 96/96** | 일치 |
| 59, 63–65 | W 2, H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §73 D5, §71 보충, §74 보충 | SCOPED S9·S1·S11 |
| 60 | 라벨 규칙 | `sim/labeler.select_rule` | 코드 무변경·시험 묶음 | 일치 |
| 61–62 | RD 재표집 (EVAL :182-184) | `rd.py` | `rd --variants standard=jsel_dev,dr=gen_dev/dr/P0 --episodes 2` → `RD_DONE`(dr 낙폭 0.0, n 275); 가드 5 `rd --variants dr=gen_dev/dr/P0 --split test` 거부 | 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 가드 14 `--m4-lead-max=-3` → "lead_max = -3.0 … finite > 0 s", 15 `=2e308` → "lead_max = inf …", 워커 전 거부 | 일치 |
| 68–94 | E0 판정 4, E-M4 판정 7, 카나리 표류, (b) 범주, `last_step` | `latency`, `canary`, `core`, `serialize` | 행 6·54; 시험 묶음 | 일치 / SCOPED S12·S13·S6 |
| 95–97, 105–136 | S-E2E·진단·E-TC·움직임 줄 확인 | `tools/se2e/*`, `se2e_temporal*.py` | 코드 블롭 불변(H1); 파드 `se2e_c1` `sha256sum -c` **5/5 OK**(23:14Z) | 일치 |
| **98, 100, 118, 132** | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1) | `stagea_data.replay_bit_identical`, `eval/common.load_truth` | `e05 --split pool --seeds 2033,2072,2108 --truth outcome:plan` → `E05_DONE`(claim `insufficient_data`, N166) | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **Isaac 한 워커 C5 → C5'(DEV 16, 23:10:33–23:14:01Z)**: 행동 **1,611개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 48·Astra 2 같은 수·같은 시각 | 일치(S16) |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | `code_r2train_e8e1864`(태그 stage3-hardreset); 18폴더 독립 재집계 18/18(§6.2) | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, 시드 검사가 `--out` 앞 | `common.load_episodes`, `sim/determinism.py` | 가드 22·23 → "only DEV 0-29 and POOL 2000-2119"(폴더 없음); 24·25 → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 | `closed.worker_cmd` | 내 워커 `CLOSED_DONE`; 가드 12·13 `--isaac-gpu 6`·`+1` → "0 or 1 only" | 일치(N34) |
| 137 | Astra 주기·in-flight 1·low·600 (§45, §82 보충 2) | `runtime/astra_hb.py` | DEV 16 hb 5.0 → 8.0, sub 8.01 → 11.01, 겹침 0; 가드 26 `K10`·27 `"K3,K4"`(예산 없음) 거부 | 일치(N155) |
| 138 | LeRobot v2.1 내보내기 | `datagen/lerobot_export.py` | **새 입력**(standard/mug_tray/P0 ep0·dr/bottle_tray/P0 ep5 참, dr/bottle_tray/P0 ep1 **거짓**): 내보낸 편 2·551프레임(274 + 277, 무효 편 건너뜀 ✓), `verify` 오류 0·PSNR 최소 39.22 dB·lerobot 0.3.3 적재 551프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참 | 일치 |
| **139** | R2 DEV 구조 검사 (§66, 완료 정의 1, `r2_datagen.md:55`) | `datagen/validate.py` | **36/36 오류 없음**, 검증기 대 메타 `valid_for_training` 불일치 0; **새 대조 15종**(standard/mug_tray/P0 ep2, 261프레임): 무수정 오류 0; 행 k78 `hz 30.0` → 오류 0; 행 k117 `valid [1, 0 × 14]` → 오류 0; 행 k156 proprio 여분 키 → 오류 0; 행 k39 `action_exec` 한 값 +inf → "action_exec: … finite"; 행 k182 `valid` 끝 −1 → "valid: H values in {0,1}"; 행 k221 `seed` 삭제 → "missing field 'seed'"; 행 k13 `aux` 삭제 → "missing field 'aux'"; 행 k91 `proprio.grip` 1값 → "proprio.grip: 2 values"; 프레임 k0 시각 +1/30 s → "off the 30 Hz grid by 3.33e-02 s"(+ hold_n); 프레임 k130 머리 경로 `""` → "k130: missing cam_head" + "images 521 != frames 261 x cams 2"; 첫 행(k0) 삭제 → "stageb rows are not one per non-terminal frame"; npz `tau` 첫 값 NaN → "npz tau: … non-finite". 관찰: `auxnan`·`execbig` 오류 0(N165). 실데이터 훑기 불일치 0(행·라벨 시드, 행 kind, decision 표지, 시각) | 일치 |
| **140–141, 152** | 정본 §82·§84·§86(+보충) 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 가드 26·27, 요청 `motion:` 없음 | SCOPED S18·S19 |
| 151 | §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT` | DEV 16 Astra 4행 effort low | 일치 |
| 153 | 정본 §85: 유료·GPU 실험 = 자체 검사 | — | 이 범위 새 실험 없음 | 일치 |
| 154 | 기준선 파일 `stageb_train.py` 기본 경로 불변 | — | 코드 변경 0(H1); 가드 28(`predict --aux-extra a3d@v4` → argparse "invalid choice … ('none', 'a3d@v1')") | 일치 |
| **155** | 책 `docs/book/` 현재 서술·수치 = 출처 | — | 이 범위 책 변경 0; 상태 칸 40개 0 벗어남, 링크 108개 끊김 0, 표 칸 수 0 불일치, 전 이력 06 줄(N164) | 일치 |
| **156** | 정본 = 마지막 절까지 | — | 정본 무변경(H1) | 일치 |
| **157** | 사전 등록 E-CAM3·E-MA3 판정·데이터·경로 | `se2e_cam3`, `se2e_kvcond` | 옵트인 가드 29b(`evalck --data r2` → "--data se2e only")·30b(`evalck --data se2e` 움직임 줄 없음 → "with the motion line")·31(`kvcond@v4`)·32(`"cam3@v1 "` 끝 공백) 거부; 등록 블롭 해시 26/26 | 일치(N170 ①) |
| **158** | handoff §0 = 확인 시각에 참인 진행 상태, 결과 커밋 때 삭제(README `:11`, P69) | — | R7 줄(22:57) 참; R2_TRAIN 줄(22:56) 수치 모두 참(§6.2) **그러나 커밋에 없는 결과 문서 경로를 인용** | **DOC D-1** |

### 5.1 33회차 표와의 차이
- 근거 교체: 행 1(새 경계 가드), 5·6·51–58·99·137·151(DEV 16), 13–17·61–62(jsel_dev/P2·gen_dev/dr/P0), 2–4(jsel_dev/P2), 66–67(`-3`·`2e308`), 98(POOL 2033·2072·2108), 101(18폴더 재집계), 138(새 입력), 139(새 대조 15종 + 새 R2_TRAIN 폴더의 마지막 100시드), 157(재설계 가드 + 등록 해시 26쌍), 158(D-1).

## 6. 확인한 것 (근거)

### 6.1 변경분
- `git diff --name-status d0e25f4 972b0be`: M draft-log(`:485` +1), handoff(`:3` 머리 22:36 → 22:57, `:11` §0 R2_TRAIN 줄 **교체**, `:12` §0 R7 줄 교체, `:138` §2.8 33회차 줄 +1), direction-log(`:80` +1); A `r7_cycle33.md`.

### 6.2 바뀐 줄마다 대 원자료
| 바뀐 줄 | 원자료·원 문서 | 판정 |
|---|---|---|
| handoff `:3` "마지막 갱신 22:57 UTC" | ≤ 커밋 22:57:04Z | 맞음 |
| handoff `:11` "생성 6,000/6,000 끝(21:56:28Z)" | `workers.log` w2 done 21:56:28; 18폴더 메타 6,000(재집계) | 맞음(N161 ①) |
| 같은 줄 "`gen check` 21:57:32Z–22:32:29Z 종료 0" | `check.log` `CHECK_START 21:57:32Z`, `CHECK_EXIT 0 22:32:29Z wall_s=2097` | 맞음 |
| 같은 줄 "`verify_merge.py`(22:33:24Z): 18폴더 모두 병합 행 수 = 유효 편 행 합, 행·라벨 시드 집합 = 유효 시드 집합, 누락 0 → 유효 5,126·행 1,495,348·결정 152,409" | `verify_merge.json` mtime 22:33:24Z `all_ok` true; **독립 재집계**(`r2verify34.py`, 에이전트 스크립트 안 씀: 편별 행 파일 줄 합·병합 파일 줄 수·정규식 시드 집합·메타 `n_decisions` 합): 18/18 일치, 유효 5,126, 편별 행 합 = 병합 행 = 1,495,348, 라벨 줄 = 메타 결정 합 = 152,409, 병합 mtime 22:01:16–22:32:29Z | 맞음 |
| 같은 줄 "`stageb_train --data r2 --reload-check` 18폴더 통과(22:46:33Z)" | `full18.log` config `data r2`·`reload_check` true·pool 18폴더, `save_load max_abs_action_diff 0.0`, `EXIT 0 wall_s=577`, mtime 22:46:33Z | 맞음(N172) |
| 같은 줄 "`load_for_training` 표본 1,495,348 = 병합 행(22:55:53Z)" | `loadcount.log` 총 samples 1,495,348(train 1,423,354·val 71,994), mtime 22:55:53Z | 맞음 |
| 같은 줄 "LeRobot 내보내기 6개 22:36Z부터 실행 중(22:56Z 약 150–175편)" | `export_all.sh` 22:36:47 시작, 첫 parquet 22:36:51Z; 22:56:00Z 145–172 / 22:56:59Z 153–181 | 맞음(N161 ③) |
| 같은 줄 "결과 `docs/stage3/results/r2_train_gen.md`" | **972b0be에 없음**(작업 트리 미커밋, 22:56:10Z) | **DOC D-1** |
| 같은 줄 32회차 D-1 표시 | 32회차 보고서·33회차 N150 | 맞음 |
| handoff `:12` R7 "(확인 22:57 UTC) 33회차 기준선 PASS(연속 무결 1) → 34회차가 PASS면 E2E 준비 기준점 태그" | `r7_cycle33.md:11`; 계획 R7 "2회 연속" | 맞음 |
| handoff `:138` 33회차 줄 "DEFECT 0, DOC 0, SCOPED 20, NOTE 117 … 실험 절 PASS … N154 … N155" | `r7_cycle33.md:11`–`:20`, `:69`–`:70` | 맞음(N162) |
| draft-log `:485` "22:57 UTC 기록: R7 33회차 기준선 PASS(연속 무결 1; 대상 d0e25f4), 실험 절 PASS." | 보고서; 22:57 ≤ 커밋 | 맞음 |
| direction-log `:80` "22:57 \| R7 33회차 \| 결함 0 · 문서 0, E-CAM3·E-MA3 판정 재계산 일치 \| PASS → 연속 무결 1"(칸 4) | 보고서 | 맞음 |
| `r7_cycle33.md` 전체 | 표본 대조: 로컬 1133/20(235.1 s), 파드 1280/4(166.6 s), 가드 33건 rc, DEV 6 1,551 비트 동일·호출 47·`last_step` 분포·Astra 시각, 정리 출력 — `D:\tools\scratch_qdd\r7c33` 원 출력과 같음 | 맞음 |

### 6.3 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 23:07:30–23:07:49Z + 재설계 2건, 21–33회차와 다른 값; 사유는 `gtxt34.sh`로 로그 마지막 오류 줄 확인)
1 `e05 --data jsel_dev/P0 --split test --seeds 1058`, 2 `e05 --data jsel_dev/P1 --split cal --seeds 541`, 3 `calib --fit-split cal --heldout P0 --heldout-split pool`, 4 `calib --fit-split pool --heldout P0 --heldout-split test_p5`, 5 `rd --variants dr=gen_dev/dr/P0 --split test`, 6–8 `closed --split test --seeds 1140`·`cal 527`·`test_p5 1308` → "--split … refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 2,34` → "seeds [34] are not in split dev", 10 `pool --seeds 2150`, 11 `dev --seeds 1330` → "(refused, never opened)"; 12–13 `--isaac-gpu 6`·`+1` → "0 or 1 only (GPU 2 never renders)"; 14 `--m4-lead-max=-3`, 15 `=2e308` → "lead_max = -3.0 / inf … finite > 0 s"; 16 `--conditions "C5,C8"` → "condition 'C8': runtime has [...]"; 17 `HARVEST_ALLOW_SPLIT=dev` + `closed --split cal --seeds 527` → "set HARVEST_ALLOW_SPLIT=cal", 18 `=cal` + `e05 --data P0 --split test_p5 --seeds 1308` → "set HARVEST_ALLOW_SPLIT=test_p5"; 19 `gen --seeds 10003`(확인 없음) → "R2_TRAIN 10000-59999 needs --confirm-train", 20 `--seeds 9995 --confirm-train`, 21 `--seeds 60002 --confirm-train` → "every other seed is refused"; 22 `determinism fresh --seed 505`, 23 `history --seeds 15,1311` → "only DEV 0-29 and POOL 2000-2119"; 24 `canary build-set --data P1 --seeds 3140-3141`, 25 `e05 --data P0 --split pool --seeds 2105` → "no episode selected"; 26 `--hb-mode K10` → "from ('K0', …, 'K4')", 27 `--hb-mode "K3,K4"`(예산 없음) → "K4 needs --hb-budget"; 28 `stageb_train predict --aux-extra a3d@v4` → argparse "invalid choice" rc 2. **실험 옵트인 가드**: 29·30 첫 설계는 `--ckpt` 누락으로 argparse rc 2(N170 ①) → **29b** `se2e_cam3 evalck --data r2 --ckpt <없음> --cam3 cam3@v1` → "--cam3: --data se2e only", **30b** `… --data se2e …`(움직임 줄 없음) → "--cam3: with the motion line (prereg_cam3 cells)"(둘 다 rc 1, 체크포인트 폴더 생성 없음), 31 `se2e_kvcond train --expert-cond kvcond@v4`, 32 `se2e_cam3 train --cam3 "cam3@v1 "` → argparse "invalid choice" rc 2. **추가**: 33 `closed --m4-h=-7` → "M4 H = -7: decision steps per call must be >= 1". **판정용 33건(29·30은 29b·30b) 모두 rc ≠ 0**; 출력 폴더는 25번 빈 폴더 하나(N10).

### 6.4 A. 테스트
- 로컬(`…\r7c34\repo`, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/r7c34/pt tests`): EXIT 0, **1133 passed · 20 skipped**.
- 파드 CPU(`venv_train`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`): **1280 passed, 4 skipped**, EXIT 0. 파드 LeRobot(`venv_e3st`): **6 passed**.

### 6.5 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV **36/36** + 새 대조 15종 + 실데이터 훑기(DEV 36·R2_TRAIN 300편 불일치 0); R2_TRAIN 18폴더 재집계 18/18; LeRobot 시험 6 passed, 새 편 내보내기·검증·적재(무효 편 건너뜀); `se2e_c1` **5/5 OK**. |
| 2 모델 | 충족(CPU) | CPU 스모크(N168), CPU 묶음의 단계 B·실험 시험 통과, 기준선 코드 무변경; R2_TRAIN 로더 확인(N172). GPU 학습 없음. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 16 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c34`: `CLOSED_DONE`, 호출 48·오류 0, 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 23:07:49–23:08:22Z): `e05` → `E05_DONE`, `rd` → `RD_DONE`, `calib` → `CALIB_DONE`, `e05 --truth outcome:plan` → `E05_DONE`(N166). |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.6). |

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함). 남의 미커밋 `r2_train_gen.md`는 읽기만.
- 파드 정리 대상 판별(`attr34.sh`, 23:14:43Z): 내 Isaac 창(23:10:33–23:14:01Z)에 생긴 `tmp/carb.BLB7BA`(23:10:34)·`tmp/tmp0wogwgou`(23:10:53)·`pyc_r6/…/tmp0wogwgou`·`pyc_r6/…/r7c34`(772 KB)·`kitcache/cyclo-r7c34_standard`(208 MB). 그 시각 `TMPDIR=/data/harvest/tmp`이거나 `pyc_r6` 접두인 다른 프로세스 0 → 모두 내 것.
- 파드 정리(`clean34.sh`, 경로를 하나씩 적은 스크립트를 `bash -s`로, 열린 핸들 0 확인 뒤, 23:15:10Z): `tmp/r7c34`(508 MB), 위 Isaac 항목 5개. 끝에 r7c34 항목 0(tmp·kitcache·pyc_r6·pyc), 파드 루트 `/C:` 없음, 명령줄에 r7c34가 든 프로세스 0, `IR_INST=r7c34` 프로세스 0, 열린 핸들 0, GPU 0–3 모두 0 MiB. 남의 `export_all.sh` 7개 그대로.
- 로컬: 추출 사본 `repo/`·pytest basetemp `pt/`·archive `a34.tar` 삭제, 스크립트·작은 출력만 남김; 지시대로 `D:\tools\scratch_qdd\r7c32` 삭제 — r7c 폴더는 r7c33·r7c34만. C: 쓰기 없음.

## 7. 실험 코드 절
검토할 새 실험 코드 없음(위 판정 절). 등록 블롭 해시 26/26 일치.

## 8. 다음 순회 전에 할 일 (제안)
1. **34회차 기준선 FAIL(DOC 1) — 연속 무결 0.** 코드는 무결; 35회차가 기준선 PASS면 연속 1.
2. D-1 고침 = R2_TRAIN 결과 커밋(§2 D-1 고침 목록을 한 커밋에). 정정 문장·수치는 파드 명령 출력으로 확인한 뒤(P68); 이 보고서 §6.2의 재집계 값과 같아야 한다.
3. 기록 커밋은 파일·줄 단위 add(P14), 커밋 전에 handoff §0·§2.8의 저장소 경로가 커밋에 있는지 확인(H12 방식).
4. (선택, NOTE) N161–N163 표기, N165(aux 값 유한성 — N142·N143·N154와 함께 태그 뒤 TDD), N152·N153·N155(33회차 그대로).
5. 35회차 대상은 972b0be 이후 HEAD, **연속 무결 0에서**.
