# Harvest

로봇 상위 정책을 학습 가능한 크기의 VLM으로 만드는 연구 저장소다. 시뮬레이터(Isaac Sim)로 만든 다양한 탁상·방 장면(L8S)과 검증된 공개 로봇 데이터의 점 라벨로 Qwen3.5-35B-A3B를 LoRA 학습하고, L8-X 세트·일반 평가 G·폐루프·한계 지도로 평가한다.

## 최종 방법: D (점 + 단계 의도, xyz는 코드가 계산)

- VLM은 머리 영상 위의 **점(0–1000 정규화 픽셀) + 단계 의도**만 출력한다.
- 로봇 좌표 xyz는 **코드(resolver)** 가 센서 깊이와 카메라 보정으로 계산한다(`harvest/astra_solo/resolve.py`). 학습에는 깊이가 필요 없고, 실행에는 깊이 카메라가 필요하다.
- 손 정보는 입력하지 않는다(학습 때만 쓴다). 조종 행은 머리 영상(손끝 표시 원만 그림)과 오른손목 영상(아무것도 그리지 않음) 두 장, 공개 점 행은 머리 시점 한 장만 쓴다(격자·3인칭·어안은 쓰지 않는다).
- 모델: Qwen3.5-35B-A3B LoRA r16(attention·DeltaNet·shared experts), 파드 안 DDP, global batch 24.
- 본 학습: L8S 전량(약 5.1만 행) + 공개 점(약 3.8만 행). 공개 행은 같은 행을 2배까지만 반복하고 시뮬 행의 0.75배를 넘지 않는다. 3 에폭, 체크포인트 1·1.5·2·2.5·3 에폭, 자동 평가는 2 → 1.5 → 2.5 순서, 최적 에폭은 학습에 쓰지 않은 검증 분할로 고른다.
- VLA 층은 기각이 아니라 보류다. 지금은 상위 단독을 먼저 다듬고, 2단계 결합 때 늘 쓰는 조이스틱으로 복원한다(user-log 188).

채택 구성 전체는 한 쪽 요약 **[docs/stage3/main35_recipe.md](docs/stage3/main35_recipe.md)** 에 있다.

## 저장소 구성 (지금 쓰는 것)

| 경로 | 내용 |
|---|---|
| `harvest/sim/` | Isaac 장면·무작위화·자산(`assets_x/`)·과제 등록 |
| `harvest/teach_l8d/` | L8-D / L8-X / **L8S** 생성기(`run_collect`, `variant drf` = L8S 규칙)·서랍·관절 과제·깊이 잡음·영상 증강·JSONL 빌더 |
| `harvest/teach_l8/` | L8 행 형식·라벨·평가, **학습 전체 상태 저장·재개 `ckpt.py`** |
| `harvest/teach_35b/` | 35B LoRA 학습(`train`)·데이터(`data`)·병합(`merge`) |
| `harvest/astra_solo/` | 실행 인터페이스(점 → xyz **resolver** `resolve.py`, D/H 스키마·에피소드) |
| `harvest/teach_pt/`, `harvest/teach_strip8/` | 최소 요청 형식(`min_format`)·폐루프 실행기(`run_closed_x`, boost 실행기)·한계 지도(`limits`, `run_limits`) |
| `harvest/` 기타(`runtime`, `eval`, `train`, `datagen`, `couple`, …) | 위 모듈이 import하는 공용 코드 |
| `tools/teach_l8d/` | L8S 생성 계획·레인·Isaac 실행·동결(`freeze.py`)·빌드(`build.py`)·관문 |
| `tools/l8x_assets/` | L8-X 실물 자산·관절 고정물 관문·통계 |
| `tools/xemb/` | 공개 데이터 → 점 행 변환(`to_points`, `pointlab`), AgiBot·RB2 등 원천, 일반 평가 분할 `gsplit`, 비교 묶음(h2h) |
| `tools/final35/` | 본 35B 체인: 빌드 → 학습 → 병합 → 평가 → 폐루프 |
| `tools/teach_35b/`, `tools/teach_l8/` | 학습·vLLM 서빙·정지·재개 확인 스크립트 |
| `tools/teach_pt/` | 판정 `ni_judge.py`, G 평가 `geval.py`, 공개 점 비율·시점 비교(opratio·view8·stage8) |
| `tools/teach_strip8/` | 한계 지도 체인(`limits_chain.sh`)·대규모 폐루프(`c30_lane.sh`)·resolver v2 비교·표 |
| `tools/ir/` | Isaac 실행 래퍼(`ir_run.sh`) |
| `tests/` | 단위 시험(`pytest`) |
| `docs/` | 정본·결과·사전 등록·기록책·사용자 발언 |
| `paper/` | 논문(CVPR 양식)·마인드맵 |

`archive/` 에는 실행 경로에서 더 이상 참조되지 않는 옛 실험 도구 폴더 8개(`tools/` 아래 `conf`·`couple_dry`·`mar2d`·`marr_real`·`open_vlm`·`pre_r7`·`sr1b`·`sr1e`), 그 폴더만 시험하던 `tests/` 8개, 옛 superpowers 계획·설계를 원래 경로 그대로 옮겨 두었다(git mv, 기록 보존용). 중단·보류된 방향이라도 살아 있는 코드와 폴더를 함께 쓰는 파일(예: `tools/teach_pt/build_min.py`는 E-C35 체인이 씀)은 제자리에 두었다.

## 주요 단계 실행

파드에서 `/data` 아래 고정 코드 사본(`/data/harvest/code_<작업>`)으로 돌린다. 먼저 `source /data/harvest/env.sh`. Isaac 렌더 금지 카드 규칙은 `tools/teach_l8d/isaac.sh` 가 강제한다.

1. **L8S 생성**
   - 계획·잡 목록: `python tools/teach_l8d/plan.py <gate.json> <n_train> <out dir> <lanes> --x --pod <dir>`
   - 레인 실행: `bash tools/teach_l8d/lane.sh <code dir> <gpu> <jobs_k.txt> <lane tag>` (한 줄 = `harvest.teach_l8d.run_collect` 한 프로세스)
   - 묶음 동결: `python tools/teach_l8d/freeze.py <collect>/<split> <manifest.json> <tasks>`
2. **공개 데이터 점 변환**: `python -m xemb.to_points X_ROOT OUT_ROOT SOURCE ...` (PYTHONPATH=`<code dir>/tools`), 학습 파일은 `python -m xemb.gsplit check TRAIN_JSONL` 로 G 누수 검사.
3. **빌드**: `bash tools/final35/build.sh <code dir> d [<pack>:<share> ...]` (큰 묶음은 `split_build.sh`), 내부에서 `tools/teach_l8d/build.py --manifest`.
4. **35B 학습**: `bash tools/final35/chain.sh <code dir> d <train cand> <min cards> <eval cand> <cl serve> <cl render> <port> ...` (빌드 → `tools/teach_35b/train.sh` → `harvest.teach_35b.merge` → 평가 → 폐루프). 단독 학습은 `tools/teach_35b/train.sh <code dir> <gpus> <data.jsonl> <out dir> --save-every N --resume`.
5. **평가**
   - L8-X 오프라인: `bash tools/final35/eval.sh <code dir> <gpu> <tag> <merged> d-min <port>`
   - 판정: `python tools/teach_pt/ni_judge.py aa ...` / `judge ...` (A/A 여유, 중앙값·>20 mm 실패율)
   - 일반 평가 G: `python tools/teach_pt/geval.py --data g_eval.jsonl --url http://127.0.0.1:PORT --name NAME --out DIR` (분할 `docs/stage3/gsplit_g166.json`)
   - 폐루프: `bash tools/final35/closed.sh ...`, 대규모 `tools/teach_strip8/c30_lane.sh`
   - 한계 지도: `bash tools/teach_strip8/limits_chain.sh <code dir> <render gpu> <x2 pod ip>`
6. 시험: 저장소 루트에서 `pytest` (Git Bash).

## 문서

- 채택 구성 요약: [docs/stage3/main35_recipe.md](docs/stage3/main35_recipe.md), 나중 문제·걱정거리: [docs/later_problems.md](docs/later_problems.md)
- 정본(설계 결정): [docs/design/00-interfaces.md](docs/design/00-interfaces.md)
- 사용자 발언 원문: [docs/user-log.md](docs/user-log.md)
- 결과: [docs/stage3/results/](docs/stage3/results/) (본 35B: [final35.md](docs/stage3/results/final35.md)), 사전 등록 `docs/stage3/prereg_*.md`
- 인수인계: [docs/handoff.md](docs/handoff.md), 기록책: [docs/book/README.md](docs/book/README.md)
- 작업 규칙: [CLAUDE.md](CLAUDE.md)
