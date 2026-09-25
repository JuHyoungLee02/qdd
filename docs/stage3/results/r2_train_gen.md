# R2_TRAIN 대량 생성 — 단계 B 학습 데이터 6,000편 (시드 10000–10999 × 과제 3 × {standard, dr})

작성 2026-09-25 UTC(파드 `date -u`), R2_TRAIN 운영 에이전트. git 커밋 안 함(메인 세션이 커밋).
근거: 정본 `00-interfaces.md` §66(R2_TRAIN 시드 10000–59999, `--confirm-train`), §34(D35: 학습 데이터는 standard·dr만, random 금지), §78(PhysX 하드 리셋, 커밋 e8e1864), `r2_datagen.md` §2·§7·§8(생성기·계획), `physx_hard_reset.md`.
파드 `p-test2/juhyoung-native-7a2a`, Isaac = `/data/harvest/ir/ir_run.sh`(IR_ROOT=cyclo, 프로세스마다 IR_INST 다름), CPU PhysX, **렌더 GPU 0·1만**(GPU 2는 작은 로더 확인에만, GPU 3 안 씀). 모든 산출물은 `/data/harvest` 아래. CAL/TEST 시드·random 변형 없음, 유료 API 없음.
**코드 고정: 커밋 e8e1864f3f9c8801a662d1783b2f34aeba5609cc(태그 stage3-hardreset)** — `git -c core.autocrlf=false archive e8e1864`을 `/data/harvest/code_r2train_e8e1864`에 풀었다(third_party 포함). 판본 표지 `CODE_VERSION`(JSON, 커밋·태그·dirty false)을 코드 사본과 출력 루트 `/data/harvest/r2/train/CODE_VERSION`에 두었다. 저장소 코드는 한 줄도 고치지 않았다.

## 1. 결론

| 항목 | 결과 |
|---|---|
| 생성 | **6,000/6,000편**(항목 = (변형, 과제, 섭동, 시드) 전부 완료, 잠금 잔여 0, 프로세스 48회 모두 종료 코드 0, Traceback 0) |
| 구조 검사(`gen check` → `validate_episode`) | **6,000/6,000 통과**(오류 0, 경고 0) |
| 성공 = 학습 유효 | **5,126편(85.4 %)** — mug_tray 1,982/2,000(99.1 %) · mug_marker 1,974/2,000(98.7 %) · bottle_tray 1,170/2,000(58.5 %) |
| 변형별 | standard 2,569/3,000(85.6 %) · dr 2,557/3,000(85.2 %) |
| 섭동별 | P0 3,102/3,600(86.2 %) · P1 988/1,200(82.3 %) · P2 1,036/1,200(86.3 %) |
| 프레임 | 전체 1,806,160 / **유효 편 1,500,474** · R4 행(= 단계 B 표본) **1,495,348** · 결정 항목(labels_v2) **152,409** |
| 분할(시드 % 20 == 0 → eval) | 유효 편 fit 4,877 / eval 249(시드 50개 × 6 = 300편 중 유효) — 코드(`gen.split_of`, `stagea_data.SPLIT` fit→train·eval→val)와 데이터(`split` 필드) 모두 확인 |
| 병합(N94 주의 반영) | 생성 끝난 뒤 `gen check`로 18폴더 전부 다시 병합(21:57:32–22:32:29Z; 폴더별 합본 파일 22:01–22:32Z). **18/18 폴더에서 병합 행 수 = 유효 편 n_rows 합, 행·라벨 시드 집합 = 유효 시드 집합, 계획 항목 누락 0**(§5) |
| 결정성(새 빌드) | 파일럿 편 3개를 새 프로세스·다른 편을 먼저 돈 프로세스에서 다시 녹화 → **3/3 항목, 비교 8쌍 모두 틱별 물리 배열 비트 동일**(§3.3) |
| 단계 B 로더(`stageb_train train --data r2 --reload-check`) | 18폴더 전부 적재 → **표본 1,495,348(= 병합 행) · train 1,423,354 / val 71,994**, hz 30 · H 15, 3스텝 학습 뒤 저장→재적재 **행동 차 0.0, 평가 동일**(§7) |
| LeRobot v2.1 | (variant, task)별 6개 데이터셋 — `[결과 전]`(확인 2026-09-25 23:27 UTC, 내보내기 실행 중; §6) |
| 벽시계 | 11:16:17Z(파일럿 시작) → 21:56:28Z(마지막 편) = **10 h 40 min**, Isaac 프로세스 누적 52.8 h |
| 용량 | 원본 **107.9 GB**(`du -sb`), LeRobot `[결과 전]`(§6) |

## 2. 경과

1. **첫 파일럿(6b013ac, 폐기)** 09:09–09:50Z: GPU 1에 2프로세스. 120편(구조 120/120, 성공 107). 도중 메인 세션이 CPU PhysX가 `env.reset()` 너머로 장면 내부 상태를 들고 간다는 근본 원인(`pool_replay_debug.md`)을 찾아 중지 지시 → 내 프로세스만 종료, 출력은 지우지 않고 `/data/harvest/data/r2/train_pilot_prefix_6b013ac`로, 로그는 `/data/harvest/r2train/logs_pilot_6b013ac/`로 옮겼다(이번 데이터와 섞이지 않음).
   - 이 판에서 CPU 문제를 찾았다: gen 프로세스 하나가 약 11코어를 태웠고 파드 cgroup(32코어 쿼터)이 계속 스로틀됐다. 원인은 libgomp 스레드 약 63개가 각 22 %씩 헛도는 것(대기 정책 active). 실행기에 `OMP_WAIT_POLICY=PASSIVE`만 더했다(스레드 수·수치 그대로) → 프로세스당 약 3–4코어.
2. **재기동(e8e1864)** 11:16Z: 메인이 하드 리셋 커밋을 주어 새 코드 사본·새 출력 루트로 파일럿부터 다시.
3. 파일럿 420편(11:16–12:17Z, GPU 1·0에 2+2프로세스) → 검사·분석(§3) → 이상 없음 → 본 생성은 파일럿 작업자가 끝나는 대로 자리를 이어받아 자동 시작(같은 큐라 파일럿 편은 그대로 본 데이터의 일부).
4. 본 생성 12:15–21:56Z: GPU 1에 3프로세스(w1·w2·w5) + GPU 0에 2프로세스(w3·w4) = 최대 5. 각 자리는 6개 작업((변형, 섭동 띠))을 돌려 순서로(standard 먼저/dr 먼저) 돈다. 결정성 확인 6프로세스는 이 자리 안에서 차례로 돌았다(동시 5 넘지 않음).
5. 21:57–22:32Z 전체 `gen check`(검증·도장·병합) → 병합 검증 → 분석 → LeRobot 내보내기 6개 병렬 + 로더 확인.

## 3. 파일럿 (시드 P0 10000–10029 · P1 10600–10619 · P2 10800–10819 × 과제 3 × 변형 2 = 420편)

### 3.1 성공률 (성공 = 학습 유효; 구조 검사 420/420)

| 과제 | 섭동 | standard | dr | DEV(r2_datagen §4.1, P0) |
|---|---|---|---|---|
| mug_tray | P0 / P1 / P2 | 30/30 · 19/20 · 20/20 | 30/30 · 19/20 · 20/20 | 12/12 |
| mug_marker | P0 / P1 / P2 | 30/30 · 19/20 · 20/20 | 30/30 · 19/20 · 20/20 | 12/12 |
| bottle_tray | P0 / P1 / P2 | 20/30 · 11/20 · 10/20 | 19/30 · 11/20 · 10/20 | 8/12 |

- 합계 357/420(85.0 %): mug_tray 138/140, mug_marker 138/140, **bottle_tray 81/140(57.9 %)**. P0 병 39/60(65 %)은 DEV 8/12(67 %)와 같은 수준이고, 정본 §66이 병 수율 약 67 %를 감수하기로 했으므로 중지 사유가 아니라고 판단했다.
- 유효 편 프레임 104,322, R4 행 103,965, 결정 항목 10,613, 분할 fit 335 / eval 22.

### 3.2 실패 원인(파일럿 63편)
- bottle_tray 59: 놓기(release) 55 — **트레이 위에 놓였으나 쓰러짐 32**, 트레이 밖(놓을 곳 위 아님) 15, 탁상 밖으로 떨어짐 8 — + 옮기기(carry) 2 + 접근 IK 2. 쥐기·들기 실패 0.
- mug_marker 2(P1: 들기 1, 옮기기 1), mug_tray 2(P1: 접근 IK 2). P1은 접근 중 대상이 옮겨지는 섭동이라 이 단계 실패가 생긴다.

### 3.3 결정성 확인 (하드 리셋 빌드, 녹화 3종 비교)
`harvest/sim/determinism.py`는 DEV 시드만 받으므로, 생성기 자체로 같은 항목을 다른 이력의 프로세스에서 다시 녹화하고 `ep<seed>.npz`의 틱별 배열 전부(t, q, qd, tau, q_target, grip, grip_q, grip_tau, tcp, obj_pose[5 물체 × 7], action, action_real, hold_n, phase_id, truth)를 비트 비교했다(`detcmp.py`). 이미지는 비교하지 않았다(RTX 렌더러 자체가 비결정, `physx_hard_reset.md` §3).

| 항목 | 파일럿 녹화(긴 이력 작업자, 앞 편 수) | 새 프로세스(첫 편) | 이력 프로세스(앞 편 수) | 결과 |
|---|---|---|---|---|
| standard bottle_tray P0 10003 | 2 | 0 (GPU 1) | 4 (시드 10001 과제 3 + 10003 mug_tray) | **3/3 비트 동일**, 307프레임, 성공 |
| dr mug_marker P1 10605 | 8 | 0 (GPU 0) | 5 | **3/3 비트 동일**, 329프레임, P1 사건 포함 |
| standard mug_tray P2 10805 | 7 | 0 (GPU 1) | 3 | **3/3 비트 동일**, 264프레임, P2 사건 포함 |

- 녹화 GPU가 달라도(0/1) 같다(물리는 CPU). 새 빌드에서는 한 시드의 궤적이 프로세스 이력과 무관하다 — 옛 빌드의 "같은 시드가 여러 이산 궤적 중 하나"(`pool_replay_debug.md`)가 이 데이터에는 없다.

## 4. 본 생성 결과 (6,000편, 시드 10000–10999)

### 4.1 편 수 (시도 = 구조 통과 / 성공 = 유효)

| 변형 | 과제 | P0 (600) | P1 (200) | P2 (200) | 합 |
|---|---|---|---|---|---|
| standard | mug_tray | 600 | 191 | 200 | 991/1,000 |
| standard | mug_marker | 597 | 190 | 200 | 987/1,000 |
| standard | bottle_tray | 357 | 115 | 119 | 591/1,000 |
| dr | mug_tray | 600 | 191 | 200 | 991/1,000 |
| dr | mug_marker | 598 | 189 | 200 | 987/1,000 |
| dr | bottle_tray | 350 | 112 | 117 | 579/1,000 |
| **합** | | **3,102/3,600** | **988/1,200** | **1,036/1,200** | **5,126/6,000** |

- 모든 칸에서 구조 검사 통과 = 시도 수(6,000/6,000). 실패 편은 지우지 않고 `valid_for_training = false`로 표시만 했다(합본·LeRobot에서 제외, 실패 데이터로 재사용 가능).
- 유효 편 한 편 평균 293프레임(9.8 s 시뮬), 결정 항목 약 30.

### 4.2 프레임·행·결정 항목 (유효 편)

| 변형 | 과제 | 유효 편 프레임 | R4 행 | labels_v2 결정 항목 | fit / eval |
|---|---|---|---|---|---|
| standard | mug_tray | 288,003 | 287,012 | 29,254 | 942 / 49 |
| standard | mug_marker | 288,565 | 287,578 | 29,306 | 940 / 47 |
| standard | bottle_tray | 175,471 | 174,880 | 17,826 | 563 / 28 |
| dr | mug_tray | 288,001 | 287,010 | 29,257 | 942 / 49 |
| dr | mug_marker | 288,656 | 287,669 | 29,316 | 940 / 47 |
| dr | bottle_tray | 171,778 | 171,199 | 17,450 | 550 / 29 |
| **합** | | **1,500,474** | **1,495,348** | **152,409** | **4,877 / 249** |

(전체 프레임은 실패 편 포함 1,806,160.)

### 4.3 실패 원인 874편 — 단계별 분해

| 단계(`meta.stage` + 끝 상태) | bottle_tray | mug_marker | mug_tray | 합 |
|---|---|---|---|---|
| 접근 IK(approach/descend 도달 실패) | 18 | 10 | 4 | 32 |
| 쥐기(close) | 0 | 7 | 3 | 10 |
| 들기(lift) | 7 | 7 | 5 | 19 |
| 옮기기(carry) | 11 | 2 | 2 | 15 |
| 놓기 — **놓을 곳 위에서 쓰러짐**(on 참, upright 거짓) | 384 | 0 | 4 | 388 |
| 놓기 — 놓을 곳 밖(on 거짓) | 237 | 0 | 0 | 237 |
| 놓기 — 탁상 밖으로 떨어짐(`off_table`) | 173 | 0 | 0 | 173 |
| **합** | **830** | **26** | **18** | **874** |

- **실패의 91 %(798/874)가 병의 놓기 단계**다. 병은 쥔 채 20–24° 기울어(파지점이 위쪽, r2_datagen §4.1) 놓을 때 넘어지거나 굴러 나간다. 쥐기·들기 실패는 과제를 통틀어 29편뿐이다.
- 섭동별 병: P0 357+350 / 1,200(58.9 %), P1 227/400(56.8 %), P2 236/400(59.0 %) — 섭동과 거의 무관(병 수율은 파지 자세가 정한다).
- 머그 과제의 실패 44편 중 P1이 39편(대상 이동 뒤 접근 IK 12·들기 12·쥐기 7·옮기기 4·놓을 곳 위 전도 4), P0 5편(mug_marker: 쥐기 3·접근 IK 2), P2 0편.
- 변형별 차이는 작다(standard 431 / dr 443 실패).

## 5. 병합·검사 (R7 28회차 N94 반영)

- 파일럿 시점(12:20Z)의 `P*.stageb.jsonl`·`check.json`은 파일럿 병합분뿐이었다(N94 지적). 생성이 끝난 뒤(21:56:28Z) 다시 돌렸다:
  `PYTHONPATH=/data/harvest/code_r2train_e8e1864 /data/harvest/venv_e3st/bin/python -m harvest.datagen.gen check --out /data/harvest/r2/train`
  → 2026-09-25T21:57:32Z 시작, **22:32:29Z 끝(35분, 종료 0)**, `CHECK {"episodes": 6000, "success": 5126, "valid": 5126, "frames": 1806160, "rows": 1800160, "gb": 101.661}`(`rows`는 실패 편 포함 전체 행). 폴더별 합본 파일 수정 시각 22:01:16Z–22:32:29Z.
- 병합 검증(`verify_merge.py`, 22:32Z 뒤): 18폴더 모두 ok.

| 폴더 | 편 | 유효 | 병합 행(`<folder>.stageb.jsonl`) | 병합 labels_v2 | 시드 범위(행) |
|---|---|---|---|---|---|
| standard/mug_tray/P0 | 600 | 600 | 171,553 | 17,493 | 10000–10599 |
| standard/mug_tray/P1 | 200 | 191 | 58,031 | 5,907 | 10600–10799 |
| standard/mug_tray/P2 | 200 | 200 | 57,428 | 5,854 | 10800–10999 |
| standard/bottle_tray/P0 | 600 | 357 | 105,291 | 10,731 | 10002–10599 |
| standard/bottle_tray/P1 | 200 | 115 | 34,941 | 3,560 | 10600–10799 |
| standard/bottle_tray/P2 | 200 | 119 | 34,648 | 3,535 | 10800–10994 |
| standard/mug_marker/P0 | 600 | 597 | 172,917 | 17,627 | 10000–10599 |
| standard/mug_marker/P1 | 200 | 190 | 57,003 | 5,806 | 10600–10799 |
| standard/mug_marker/P2 | 200 | 200 | 57,658 | 5,873 | 10800–10999 |
| dr/mug_tray/P0 | 600 | 600 | 171,560 | 17,495 | 10000–10599 |
| dr/mug_tray/P1 | 200 | 191 | 58,018 | 5,908 | 10600–10799 |
| dr/mug_tray/P2 | 200 | 200 | 57,432 | 5,854 | 10800–10999 |
| dr/bottle_tray/P0 | 600 | 350 | 103,244 | 10,523 | 10002–10599 |
| dr/bottle_tray/P1 | 200 | 112 | 34,004 | 3,463 | 10600–10799 |
| dr/bottle_tray/P2 | 200 | 117 | 33,951 | 3,464 | 10800–10999 |
| dr/mug_marker/P0 | 600 | 598 | 173,334 | 17,669 | 10000–10599 |
| dr/mug_marker/P1 | 200 | 189 | 56,685 | 5,774 | 10600–10799 |
| dr/mug_marker/P2 | 200 | 200 | 57,650 | 5,873 | 10800–10999 |
| **합** | **6,000** | **5,126** | **1,495,348** | **152,409** | |

- 각 폴더: 병합 행 수 = 유효 편 `n_rows` 합, 행 파일과 라벨 파일의 시드 집합 = 유효 편 시드 집합(실패 편만 빠짐), 섭동 띠의 모든 시드가 편으로 존재(누락 0, 띠 밖 시드 0). 시드 범위 끝이 10002·10994인 폴더는 그 끝 시드들이 실패 편이라서다.

## 6. LeRobot v2.1 내보내기

`[결과 전]` (확인 2026-09-25 23:27 UTC): `export_all.sh`가 22:36Z부터 (variant, task)별 6개를 병렬로 내보내는 중 — 데이터셋마다 유효 편만(`valid_for_training`), 기대 편 수 standard/dr × mug_tray 991·mug_marker 987·bottle_tray 591/579. 23:27Z에 381–453편씩 끝(약 9편/분/데이터셋, 원본 DEV 판 4.1 s/편보다 느림 — 6개 동시 + 로더 확인 적재와 CPU 공유). 각 내보내기 뒤 `lerobot_export verify`(행 수·timestamp·영상 프레임 수·PSNR·npz 행동 일치 + lerobot 0.3.3 `LeRobotDataset` 적재)가 이어서 돈다. 편 수·프레임·용량·verify 결과는 끝난 뒤 이 절에 적는다. 그 전에는 LeRobot 판을 쓰지 않는다(단계 B 로더는 원본 폴더를 읽으므로 학습 준비와는 무관).

- 방식: 내보내기 도구는 `<src>/*/*/*/ep*.meta.json`을 훑으므로, 데이터셋마다 보기 루트 `/data/harvest/r2/train_views/<variant>_<task>/<variant>/<task>`(원본 과제 폴더로의 심볼릭 링크)를 만들어 `--src`로 준다 — 코드 변경 없음. 결과 `/data/harvest/r2/train_lerobot/<variant>_<task>/`(meta/info.json v2.1·fps 30·`r2_episodes.jsonl`로 원본 추적), 로그 `/data/harvest/r2train/logs/export/`.

## 7. 단계 B 로더 확인

- 명령(GPU 2, 계산 전용 — 렌더 없음): `stageb_train train --data r2 --pool <18폴더> --run full18 --out-root /data/harvest/r2train/loadercheck --max-steps 3 --max-train 16 --max-val 4 --batch 2 --eval-every 2 --reload-check`(`loadercheck.sh`, venv_train, PYTHONPATH = 고정 사본).
- 22:36:56Z 시작 → 적재·학습·재적재 끝 22:46Z(577 s, 대부분 18폴더 적재). 설정 기록: `data r2`, `hz 30`, `H 15`, 팔 right만, `grip_space open01@v1`(`sim_width_m`), **val 71,994 표본**(eval 시드), 학습 표본은 `--max-train 16` 부분집합. 3스텝 뒤 저장 → 재적재: `max_abs_action_diff 0.0`, 평가·정규화 동일(`eval_equal`, `norm_equal` 참). 파일럿 폴더 2개(standard mug_tray P1 + dr bottle_tray P2)로도 12:37Z에 같은 확인 통과(val 581).
- 전체 표본 수 확인(CPU, `loadcount.py` = `stageb_data.load_for_training("r2", pool=폴더)`를 18폴더에 차례로, 524 s): **표본 1,495,348 = 병합 행 1,495,348**(폴더마다 일치), train 1,423,354 / val 71,994(4.8 %), 결정 질문 항목 759,350(결정 프레임 152,409 × 약 5문항), 모든 폴더 hz 30·H 15.

## 8. 자원·처리량

- 벽시계: 파일럿 11:16:17Z → 마지막 편 21:56:28Z = 10 h 40 min(본 생성 약 9 h 40 min). 평균 약 560편/h(5프로세스). 프로세스당 편 29.7 s = 기록 20.8 s(시뮬 10.0 s) + prefix 선행 실행 8.9 s(편 평균, `check.json`); 쓰기·검사 약 0.5 s는 별도.
- Isaac 프로세스 누적(로그 START–EXIT 합): 생성 GPU 1 31.3 h + GPU 0 21.1 h, 결정성 확인 0.5 h = **52.8 h**. GPU 점유 시간(장치): GPU 0·GPU 1 각각 약 10.7 h(프로세스당 메모리 약 4 GB, 사용률 20–50 %). GPU 2: 로더 확인 약 11 min(파일럿 1 min + 전체 10 min). GPU 3 안 씀. 폐기한 첫 파일럿(6b013ac)은 GPU 1에서 09:09–09:50Z(약 0.7 h, 2프로세스) 별도.
- CPU(파드 cgroup `cpu.stat`, 1분 간격 `cpumon.log`): 정상 상태 5프로세스 합 18–22코어(쿼터 32), 스로틀 0 %. 스로틀은 (a) 5개 자리가 동시에 다음 작업으로 넘어가며 Isaac을 새로 띄울 때(17:02–17:07, 18:09–18:13, 20:03–20:06Z, 각 5분 안팎 100 %)와 (b) 다른 에이전트의 Isaac 작업(closed 평가·astra_motion, OMP 대기 정책 active) 시작 때 잠깐 생겼고 곧 풀려 프로세스를 줄이지 않았다. `/proc/loadavg`는 노드 전체(128코어) 값이라 판단에 쓰지 않았다.
- 디스크: 원본 107.9 GB(standard 46.4 GB · dr 61.6 GB; dr은 무작위 재질로 JPEG가 큼), 결정성 확인 사본 `/data/harvest/r2train/det/` 소량.

## 9. 명령 (파드)

```
# 코드 고정 (로컬 → 파드)
git -C D:/qdd -c core.autocrlf=false archive e8e1864 > code_e8e1864.tar   # → /data/harvest/code_r2train_e8e1864 + CODE_VERSION
# 실행기 /data/harvest/r2train/: run.sh(IR_ROOT=cyclo, IR_INST=r2t_<tag>, CUDA_VISIBLE_DEVICES 0|1만, OMP_WAIT_POLICY=PASSIVE,
#   HOME/TMPDIR/캐시 /data), worker.sh(작업 목록 차례로), full_slot.sh(6작업 회전), det_run.sh, cpumon.py, status.py
./run.sh <tag> <gpu> gen --out /data/harvest/r2/train --variant {standard|dr} --tasks all --kinds P0 --seeds 10000-10599 --confirm-train
#   (P1 10600-10799, P2 10800-10999; 파일럿 P0 10000-10029 · P1 10600-10619 · P2 10800-10819)
# 검사·병합·분석
python -m harvest.datagen.gen check --out /data/harvest/r2/train          # venv_e3st, PYTHONPATH=code_r2train_e8e1864
python3 verify_merge.py /data/harvest/r2/train ; python3 analyze.py /data/harvest/r2/train [시드 명세]
# 결정성
./det_run.sh <gpu> a|b ; python detcmp.py <variant> <task> <kind> <seed> /data/harvest/r2/train det/fresh<n> det/hist<n>
# LeRobot (6개 병렬: 보기 루트 /data/harvest/r2/train_views/<variant>_<task>/<variant>/<task> → 원본 폴더 심볼릭 링크)
./export_all.sh   # lerobot_export export/verify --src <보기> --dst /data/harvest/r2/train_lerobot/<variant>_<task>
# 로더
./loadercheck.sh full18 <18폴더 쉼표 목록>
```

## 10. 한계·주의

- 교사는 오라클 스크립트 계획기(특권 상태), 이미지는 렌더 참값이다(r2_datagen §9).
- **병 수율 58.5 %**: 병 과제의 유효 편은 1,170편(머그 과제의 약 60 %)이라 과제 비율이 고르지 않다. 학습에서 과제 균형이 필요하면 표집 가중치로 맞춘다.
- 생성기의 `prefix`(정규 선행 실행, 편당 평균 8.9 s)는 하드 리셋 뒤에는 결과에 영향이 없다(`physx_hard_reset.md` §4 추론, 따로 검증 안 됨). 코드를 고치지 않는다는 지시에 따라 그대로 돌렸다 — 프로세스 시간의 약 30 %. 다음 대량 생성 전에 prefix를 빼는 판(결정성 행렬로 확인)을 권한다.
- 이미지는 비트 재현되지 않는다(렌더러 비결정, 평균 |픽셀 차| ≤ 1.2/255). 물리·행동·라벨은 재현된다(§3.3).
- 결과 기반 라벨(재실행 복원)은 붙이지 않았다(정본 §66 (3)).

## 11. 파일

- 데이터: 원본 `/data/harvest/r2/train/`(`<variant>/<task>/<kind>/ep<seed>.{jsonl,npz,meta.json}`, `img/ep<seed>/`, `rows/`, 합본 `<kind>.stageb.jsonl`·`<kind>.labels_v2.jsonl`, `check.json`, `CODE_VERSION`, `_workers/` 체인 로그), LeRobot `/data/harvest/r2/train_lerobot/<variant>_<task>/`(§6).
- 운영: `/data/harvest/r2train/`(실행 스크립트, `logs/`(작업자별 생성 로그·`cpumon.log`·`workers.log`·`export/`), `final/`(check.log, verify_merge.json, analyze_full.json, analyze_pilot.json, invocations.txt, du.txt, loadcount.log), `pilot/`, `det/`(재녹화·cmp*.json), `loadercheck/`).
- 폐기한 첫 파일럿(6b013ac): `/data/harvest/data/r2/train_pilot_prefix_6b013ac/`, 로그 `/data/harvest/r2train/logs_pilot_6b013ac/`.
- 코드 사본: `/data/harvest/code_r2train_e8e1864/`(사용), `/data/harvest/code_r2train/`(6b013ac, 첫 파일럿).
- 로컬: 실행 스크립트 원본 `D:\tools\scratch_qdd\r2train\pod\`, 로컬 대기 스크립트 `D:\tools\scratch_qdd\r2train\`. C: 쓰지 않음.
