# E-CL15 — 본 35B ep1.5 폐루프, 학습에 없던 환경 (시범, 무료, 사전 등록)

- 작성: CL15 에이전트, 2026-10-01 KST(UTC 시각은 커밋 시각). **렌더 전에** 커밋한다. 결과: `/data/harvest/out/cl15/summary.{json,md}`, 영상 `/data/harvest/videos/cl15/T1/`(색인 `index.md`, `index.jsonl`).
- 사용자 원문(10-01 14시경 KST): "그럼 1.5가지고 하는 테스크를 볼 수 있을까? 동영상으로 시도해서 성공, 실패하는거. … 아예 한번도 보지 않은 테스크에 대한 성능평가도 있음 좋을듯 …" → 범위 조정 원문: "t1,3만 물론 학습때 안쓴 환경이어야하고", "한 10개씩이면 돼 너무 많다 지금은", "L8S 과제의 테스크들에서 각각 하나씩만 뽑아서 동일하게 만들면되잖아 10개만 …", "그냥 T1만빨리해서 렌더하자 T3는 보류".
- **시범 n=10/단. 본 평가(단마다 40–60편, T3 포함)는 이후 별도 등록.** 판정 없음(보고 전용), 신뢰구간만 적는다.

## 단
- **T1 (실행)**: L8S 과제 그대로, **환경은 35B 학습에 없던 것**. 장면 기하·물체·과제·시드는 L8S 보류 편(main35 학습 제외 3 %, E-M35CL `groups.json`의 참값 성공 편)을 쓰고, 보이는 환경을 L8S 자산 라이브러리의 **보류(ood) 분할**로 바꾼다: iTHOR 방 배경(`fx.room_split`, 이름 해시 20 %), Poly Haven 재질·실내 HDRI(`materials.split_of`, id 해시 20 %). L8S 학습 렌더는 코드상 항상 train 분할만 썼다(run_collect: 방 = train(ood_s 외), `materials.pick` 기본 train, `hdr_paths(cat, "train")`). 실행기 = `harvest.cl15.run_t1`(= `run_closed_l8s` 그대로 + 위 세 분할만 ood로 바꾸는 패치).
  - 편 고르기(결과 전 고정, `tools/cl15/prep.py`): 과제 종류(과제 이름의 `__` 앞) 마다 1편, 종류 안에서 sha256("cl15:<task>:<seed>") 첫 편. 종류 = ov_* 7종(ov_into·left·right·front·behind·between·basket) + 기본 과제 중 후보가 가장 많은 3종(bottle_bin, bottle_tray, mug_left_of_bottle — 후보 2편 동률 4종 중 이름순). 총 10편.
- **T2**: 사용자 지시로 뺌.
- **T3 (보류)**: L9 장면·과제(오른팔, L9 ood 방·재질·HDRI·ood_o 물체)로 하는 미경험 과제. 사용자 "T3는 보류" — 실행기 연결(`collect9.draw/register_task` + `make_world9(split="ood")` + 같은 CLEpisode)만 설계, 이번에 돌리지 않음.

## 겹침 검사 (렌더 전·후, `tools/cl15/overlap.py` → `/data/harvest/out/cl15/overlap.json`)
- 학습 쪽: `train_main35.jsonl` 행의 이미지 → 편 폴더 → `scene.json`의 방 이름·HDRI 이름·가구 종류. T1 쪽: 실행기가 고를 수 있는 ood 방·HDRI·재질 풀과 실제로 쓴 것(`res/env_used.jsonl`).
- PASS = (학습 방 ∩ ood 방) = ∅, (학습 HDRI ∩ ood HDRI) = ∅, 학습 방·HDRI 중 ood 분할인 것 0, 실제 사용한 방·HDRI가 학습에 없음, 실제 사용 재질이 전부 ood 분할. FAIL이면 결과에 그대로 적고 '학습에 없던 환경' 주장을 하지 않는다.
- 한계: 가구 기하(가구 종류·메시 조각)와 물체는 L8S와 같다(과제를 '그대로' 두기 위함). 조명 원판 광원은 연속 무작위(분할 없음).

## 실행
- 상위: main35 **ep1.5** 병합본(`/data/harvest/out/main35/merged_ep1.5`), vLLM BF16, 7a2a GPU2(평가 카드, 렌더 아님), 사고 끔.
- 실행기 설정: E-M35CL과 같음(LimitEpisode, d-min, mem_points + fix_loop, 기존 LoopGuard 유지) + **loop break 켬**(`--loop-break --stall-n 3`, prereg_main35_closed2 §3 정의; 아직 채택 판정 전이라 E-M35CL(끔)과 직접 비교는 참고만). 호출 30·동작 120 s. 조건 none만.
- 렌더: 7a2a GPU3을 L9에서 빌림. 준비되면 `/data/harvest/out/cl15/READY_FOR_LANES`, L9 쪽이 비우고 `LANES_GO_7a2a_3`을 만들면 레인 시작, 끝나면 `DONE` + `/data/harvest/out/l9/GPU_FREED`에 한 줄. 멈춤: `touch /data/harvest/out/cl15/STOP`.

## 지표 (보고만)
- 성공률 + Wilson 95 % 구간(n=10이라 넓다 — 시범).
- 실패 유형: 실행기 기록 `fail_stage/end_reason`(approach·grasp·lift·place × stage_cap_calls·stall·stop·motion 등) 그대로 센다. 상위 3개를 보고.
- 참고 열: 같은 편의 E-M35CL 결과(학습 환경, 있는 체크포인트만).
- 영상: 모든 편 10 fps 머리 | 왼손목 | 오른손목 H.264, 원본 jpg 보존. 성공 2편·실패 2편을 골라 노트북 `D:\tools\pdf_out\cl15_videos\`(28 MB 이하).

## 변경 기록
- 변경 1 (렌더 전, 결과 없음): 기본 과제 3종 이름 정정 — prep.py 규칙(후보 수 내림차순, 동률은 이름순)대로 mug_stand가 아니라 mug_left_of_bottle. 렌더 전 겹침 검사 PASS(학습 편 폴더 7,670개: 방 28·HDRI 56, ood 풀 방 10·HDRI 10·재질 16, 교집합 0).
