# 04. 지도 — 코드·데이터·체크포인트·파드·GPU

확인 시각 2026-09-25 18:4x UTC(로컬 `ls`, 파드 `ls /data/harvest`; 21:07·21:30 UTC에 R2_TRAIN·탐침·E-MA1b 줄 재확인 — 2026-09-25 21:30 UTC, R7 29회차 N106; 23:28 UTC에 R2_TRAIN 두 줄을 파드 `ls /data/harvest/r2`로 재확인). 바뀌면 같은 커밋에서 고친다. **이 장은 위치만 적고 진행 상태(생성 중·진행 중 등)는 적지 않는다 — 지금 상태는 `docs/handoff.md`** [→ 2026-09-25 21:07 UTC, R7 28회차 D-2: 상태 꼬리표가 두 번 낡아 규칙으로 뺌].

## 저장소 (`D:\qdd`, 브랜치 dev만 — main 금지)
| 경로 | 무엇 |
|---|---|
| `harvest/runtime/` | 런타임: `core`(실행기), `m4`(확정·교체), `conditions`(C0–C6), `skills`(스킬 S·쥠 디바운스), `calibration`(J5), `measure`(V1h·T1), `fused_model`(단계 B 서버), `fused_action`, `astra_hb`(K0–K4), `aiworker`·`ir_policy`(Inspect Robots), `clock`·`latency_ctrl`·`reqhash` |
| `harvest/eval/` | `e05`(E0.5 재생)·`rd`·`calib`·`closed`(폐루프 묶음)·`canary`·`splits`(분할 보호)·`common` |
| `harvest/analysis/` | `stats`(`N_BOOT` 10,000, `CMP_EPS` 절대 1e-12)·`replay`·`latency` |
| `harvest/sim/` | `scene`(하드 리셋 `Env.reset`)·`planner`(오라클)·`labeler`·`randomize`(random/dr)·`determinism`·`perturb`·`snapshot`·`run_dev` |
| `harvest/datagen/` | R2 생성기(`gen`·`episode`·`rows`·`timing`·`validate`·`lerobot_export`·`queue`) |
| `harvest/train/` | 단계 A `stagea_*`, 단계 B `stageb_data`·`stageb_model`(**체크포인트 해시 대상 — 함부로 고치지 않음**)·`stageb_train`·`stageb_expert`, `prefix_share`, S-E2E `se2e_data`(후방 차분)·`se2e_temporal*`, MolmoAct `se2e_trace*`·`se2e_a3d`, 옵션 CLI 포장 `se2e_cam3`(E-CAM3)·`se2e_kvcond`(E-MA3; 기준 파일 무수정) |
| `harvest/perception/`, `harvest/stereo/`, `harvest/m4b/` | R1 인식(기준선·진단), E3-ST, 확인 헤드 V1h |
| `harvest/clients/` | `astra`·`jevl`·`jev` 클라이언트 |
| `harvest/astra_motion/` | E-Astra-motion 탐침 코드(3500f54) [→ 2026-09-25 21:07 UTC, R7 28회차 D-2] |
| `harvest/couple/` | 결합 패키지: `params`(`CoupleParams`)·`schema`(astra-couple@v1)·`prompt`·`mock`(Task 1)·`gate`(의미 게이트: 나이·불확실·개입 자격·손목 근거, Task 2)·`cost`(가격표·비용 장부, Task 3)·`stream`(`SerialStream`, 직렬 흐름: 동시 1개)·`mock`의 `ScriptedCoupleAstra`(모의 Astra 클라이언트, Task 4)·`layer`(`AstraLayer`: Astra 층 두 답 합의 히스테리시스·`same_edit`/`flipped`·flip·F1 keep·stop claim, Task 5); 뒤 과제가 모듈을 더한다 |
| `harvest/serialize.py`, `deccall_snap.py`, `labels_v2.py`, `qid.py` | 직렬화(ser-A-min-2)·결정 호출·정답·질문 id |
| `tools/se2e/` | `se2e_verdict`·`temporal_verdict`·`temporal_latency`·`motion_confirm_verdict`(등록 때 고정) |
| `tools/ma1/` | `g0`·`g0_point`·`ma1_verdict`·`build_a3d`·`ma1b_verdict` |
| `tools/cam3/`, `tools/ma3/`, `tools/se2e/paired_verdict.py` | E-CAM3 `build_cam3`·`cam3_latency`·`cam3_verdict`; E-MA3 `chunk_eval`·`ma3_latency`·`ma3_verdict`; 공통 짝 비교(등록 때 고정) |
| `tools/ma2/`, `harvest/train/r2_ma2.py` | E-MA2(명령 입력, R2): 옵션 파일 CLI 포장 `r2_ma2`(`--ma2 c0/c1/c2`, `ma2eval` 돌린 명령 평가) + `build_ma2`(결정 스냅샷 뷰·되짚기 명령·평가 집합·화살표)·`ma2_latency`·`ma2_verdict`(등록 때 고정) |
| `tools/sr0/` | E-SR0(조이스틱 준수, 학습 없음): `sr0_eval`(decide → chunk 경로에서 결정만 반사실로, 조건 20·22개), `sr0_gate`(기존 평가 재현 관문), `sr0_verdict`(A_xy·우연·A_z·ρ·그리퍼, 등록 때 고정 + 변경 1), `run_sr0.sh` |
| `tools/` 기타 | `se2e_convert.py`(`reconvert --hist`), `labels_v2_eval.py`, `prereg_hash.py --check`, `intent_check.py`·`user_line_check.py`(빨간 줄·[사용자] 줄), `stagea_merge.py`, `r5/`·`r6/`(파드 동기화), `pod_sync.sh` |
| `tests/` | 전체 시험(로컬은 Git Bash에서 `pytest`; PowerShell에서는 2개 실패 — P33) |
| `tests/couple/` | `harvest/couple/` 시험(`test_schema.py`, Task 1; `test_gate.py`, Task 2; `test_cost.py`, Task 3; `test_stream.py`, Task 4; `test_layer.py`, Task 5) |
| `docs/design/00-interfaces.md` | **정본**(마지막 절까지가 현재 판) |
| `docs/stage3/` | 사전 등록 `prereg_*.md`·`prereg.json`, 결과 `results/`, `direction-log.md` |
| `docs/superpowers/specs/`·`plans/` | 결합 설계(승인)·구현 계획(16과제) |
| `docs/research/` | 조사 문서(1.5년·신뢰도 규칙) |
| `paper/` | CVPR author-kit 구조 논문 + 한국어 마인드맵(`mindmap.tex`), 그림 `figures/src/make_figs.py`; PDF는 `D:\tools\pdf_out\` |
| `D:\tools\scratch_qdd\` | 로컬 임시(작업별 하위 폴더). C: 금지 |

## 파드 (`p-test2` 네임스페이스)
| 파드 | 용도 |
|---|---|
| `juhyoung-native-7a2a` (노드 h200-03-w-7a2a, GPU 4장 0–3) | 주 작업 파드 — **반납·삭제 금지** |
| `juhyoung-native-7a2a-x2` (GPU 2장) | 보조(이 세션 점검 때 비어 있음) |
| `juhyoung-0` | 이 프로젝트에서 쓰지 않음 `[미검증]` |

- GPU 역할(7a2a): **0·1 = Isaac 렌더**(R2_TRAIN·R7 폐루프), **2 = 계산만(렌더 금지)**(학습), **3 = vLLM·보조 VLM 서버 자리**(탐침 Qwen3-VL-8B 포트 8341; 서버가 없을 때는 실험 학습에도 씀 — 지금 쓰임은 handoff §0) [→ 2026-09-25 21:50 UTC, R7 30회차 N121]. 남의 프로세스는 건드리지 않는다.
- 셸: Git Bash에서 kubectl은 `MSYS_NO_PATHCONV=1`(P26). 업로드는 `tar -cf - | kubectl exec -i … tar -xf -`. 파드 작업은 `/data`만, 시작 `source /data/harvest/env.sh`, `OMP_WAIT_POLICY=PASSIVE`.
- Isaac 실행: `ir_run.sh IR_ROOT=cyclo`, 작업자마다 `IR_INST=<이름>`(kit 캐시 `ir/kitcache/cyclo-<IR_INST>`).

## 파드 경로 (`/data/harvest/`)
| 경로 | 무엇 |
|---|---|
| `env.sh`, `venv_vllm`, `venv_train`, `venv_sam3`, `pylib_molmo2` | 환경(모델별 venv) |
| `models/` | Qwen3-VL-4B·8B-Instruct, gemma-4-E4B-it, Molmo2-ER, sam3.1, sam2, gdino-base, ffs |
| `code_<작업>/` | 실험별 **고정 코드 사본**(예: `code_se2e_run`·`code_se2e_temporal`·`code_se2e_confirm`·`code_ma1_g0`·`code_ma1b`·`code_cam3`·`code_ma3`·`code_ma2`·`code_r2train_e8e1864`·`code_astra_motion`). 새 사본은 LF archive(P21) |
| `data/pool/`, `data/pool.labels_v2.jsonl` | 풀 120편(옛 소프트 리셋 물리 — 새 물리로 재현 안 됨) |
| `data/jsel_dev/`, `data/gen_dev/` | DEV 스냅샷(standard / random·dr) |
| `data/se2e` → `se2e_t` → **`se2e_c1`** | S-E2E 행: 원판(중앙 차분 누수) → 움직임 출처 필드 추가 → **누수 수정판(현재 사용)** |
| `r2/dev*`, `r2/train/`, `r2/train_lerobot/`, `r2train/`, `data/r2/` | R2 DEV 생성물·LeRobot 내보내기(`r2/dev_lerobot`), **R2_TRAIN 원본 `r2/train/<variant>/<task>/<P0\|P1\|P2>`**(단계 B `--pool` 폴더, 합본 `<kind>.stageb.jsonl`·`CODE_VERSION` e8e1864), R2_TRAIN LeRobot v2.1 `r2/train_lerobot/<variant>_<task>`(6개), 운영 스크립트·로그 `r2train/`, 폐기한 첫 파일럿(옛 물리 6b013ac) `data/r2/train_pilot_prefix_6b013ac` — [R/r2_train_gen](../stage3/results/r2_train_gen.md) §11 |
| `ckpt/se2e/{se2e_A_s0,se2e_B_s1}` | S-E2E PASS 체크포인트(ser-A-min-1 — 폐루프에 안 씀) |
| `ckpt/se2e_scale/{1000,9371,18742,37484}`, `ckpt/se2e_diag` | 규모 곡선·진단 |
| `ckpt/se2e_temporal/{single_motion,video2_none,video2_motion}` | E-TC 칸(옛 데이터판 — 재사용 불가) |
| `ckpt/se2e_confirm/{none,motion}_s{1,2}` | 움직임 줄 확인(se2e_c1) — E-MA1b 기준 칸 |
| `ckpt/ma1b/` | E-MA1b 체크포인트 `a3d_s{1,2}`(불채택, `results/ma1b.md`) [→ 2026-09-25 21:07 UTC, R7 28회차 D-2] |
| `ckpt/cam3/`, `ckpt/ma3/`, `data/cam3/` | E-CAM3 `cam3_s{1,2}`·E-MA3 `kv_s{1,2}`(둘 다 불채택, `results/cam3.md`·`ma3.md`), 반대 손목 프레임 `data/cam3/img_cam3/`(36,177장) |
| `ckpt/ma2/`, `data/ma2/`, `logs/ma2/` | E-MA2 `c0`·`c1`·`c2`(판정 NONE, `results/ma2.md`), 결정 스냅샷 뷰 `data/ma2/view/`(img는 R2_TRAIN 원본 링크)·명령 표 `cmd/`·`eval_set.json`(1,200)·화살표 `arrow/`(79,495장) |
| `logs/sr0/`, `code_sr0`·`code_sr0_v` | E-SR0 평가 출력 `sr0_motion_s{1,2}.jsonl`·`sr0_c0.jsonl`, `verdict.json`(WEAK, `results/sr0.md`), 재집계 `recount.json`·진단 `diag.json` |
| `ckpt/stageA/sftA_pool_v1` | 단계 A SFT(병합 `merged/`) |
| `logs/<실험>/` | 예측·판정 JSON(`se2e_confirm/verdict_full.json` 등), 탐침 비용 장부 `logs/astra_motion/cost.jsonl` |
| `out/<작업>/` | 폐루프·장면·E3-ST 산출물 |
| `tmp/<작업>/` | 임시(작업 끝나면 자기 경로만 정리) |

## 데이터 판본·분할
- 시드 분할: DEV 0–29(자유), POOL 2000–2119, **CAL 500–549 · TEST 1000–1149 · TEST-P5 1300–1329는 `HARVEST_ALLOW_SPLIT` 없이는 거부**, 순수 로직 시험 시드 3000–3199, R2_TRAIN 시드 영역 10000–59999 [→ 정정 2026-09-25 20:01 UTC, R7 26회차 N55]; 생성한 R2_TRAIN = P0 10000–10599 · P1 10600–10799 · P2 10800–10999 × 과제 3 × {standard, dr} = 6,000편(유효 5,126), 분할 시드 % 20 == 0 → eval. 생성 뒤 `gen check`(2026-09-25 21:57:32–22:32:29 UTC)가 18폴더를 모두 다시 병합했고, 폴더마다 합본 `<kind>.stageb.jsonl` 행 수 = 유효 편 행 합(전체 1,495,348)·시드 집합 = 유효 시드 집합으로 확인했다([R/r2_train_gen](../stage3/results/r2_train_gen.md) §5). 단계 B는 이 합본을 `--pool` 폴더로 읽는다 — 앞으로 편을 더 만들면 같은 병합·확인을 다시 돌린다(N94) [→ 2026-09-25 23:28 UTC, R2_TRAIN 결과: 26–32회차 괄호(파일럿 병합분 서술, N141)를 최종 병합 사실로 정리]
- S-E2E: RB1(`ROBOTIS/Task_0001`, 라이선스 미표기 → 내부용) + RB2(`Task_0002`, apache-2.0), 10 Hz, 검증 1,799(층화 300 = `val_keys_sha e22f6d8ef7fc`).
- 직렬화: `ser-A-min-2`(마지막 줄 `last_step:`), 움직임 줄 `se2e-motion@v1`(런타임 적용은 계획 Task 12 = ser-A-min-3, 기존 체크포인트를 모두 거부하게 되므로 E-MA1b 뒤).

## 자주 쓰는 명령 (자세한 인자는 [R/r6_eval](../stage3/results/r6_eval.md) 1절)
- 평가: `python -m harvest.eval.{e05,rd,calib,closed} …`(파드, `source /data/harvest/env.sh` 뒤).
- 사전 등록 해시 확인: `python tools/prereg_hash.py --check`.
- 빨간 줄 검사: `python tools/intent_check.py`(논문 커밋 전 0).
- S-E2E 재변환: `python tools/se2e_convert.py reconvert --hist …`(다른 필드가 바뀌면 거부).
