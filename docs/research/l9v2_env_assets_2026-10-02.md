# L9 v2 환경 자산 조사 — 방·배경·가구·재질·장식 (2026-10-02 KST, L9v2-ENV)

- 목적: 설계 §12.3 "엄청난 다양성"(사용자 10-02: "그냥 처음 하는 것처럼 다양한 로봇하고 다양한 환경 이런거 전부 다 가능하게", "l9은 다양성이 훨씬 엄청나면 좋아"), §12.11 원칙(벤치 저격 금지·양보다 다양성·현실감·정직한 보류).
- 허용 라이선스: CC0, CC BY, CC BY-SA, Apache-2.0, MIT만. NC·ND 금지, NOASSERTION·확인 불가 = 확인 전 사용 안 함.
- 원칙 1(벤치 저격 금지): RoboCasa·BEHAVIOR·LIBERO·RoboTwin·SimplerEnv의 장면·자산은 라이선스가 허용해도 **쓰지 않는다**. 모든 자산 행에 출처(source URL + id)를 남겨 관문에서 겹침을 검사할 수 있게 한다.
- 라이선스 확인일: 모두 2026-10-02(원문 페이지·데이터 카드·LICENSE를 직접 읽음). 개수는 같은 날 API·메타데이터 실측.

## 1. 결정 요약

| 출처 | 라이선스(원문) | 확인 위치 | 개수(실측) | 형식 → Isaac Sim 5.1 | 크기(/data) | 결정 |
|---|---|---|---|---|---|---|
| Poly Haven 텍스처 | CC0 ("All assets (HDRIs, textures and 3D models) … licensed as CC0") | https://polyhaven.com/license | 863 (v1에 전부 있음) | 1k JPG diff/nor_gl/rough → UsdPreviewSurface(`materials.author`) | v1 6.0 GB 중 일부 | 유지 |
| Poly Haven HDRI | CC0 | 같음 | 997 (v1 501 + **v2 496**, 남은 실외 전부) | 2k .hdr → DomeLight | v2 +약 5 GB | **채택(전량)** |
| Poly Haven 3D 모델 | CC0 | 같음 | 521 중 실내 범주 395 선별 → **373 변환**(바닥 214·탁자 위 159) | API `usd` 1k + 텍스처 → 감싸기 USD(/Piece/norm/yup, 바닥 중심 원점, Z-up) | 1.8 GB | **채택**(장식) |
| ambientCG 재질 | CC0 1.0 ("copy, modify, distribute … even for commercial purposes") | https://docs.ambientcg.com/license/ | 2,013 중 표면 범주 **+1,326**(v1 450 → 1,776) | 1K-JPG zip → UsdPreviewSurface | v2 +약 2 GB | **채택(표면 범주 전량)** |
| MolmoSpaces ProcTHOR-10k **train** 집 | 데이터 카드: "All other data subsets are licensed under CC BY 4.0"(AI2-THOR 자산), ProcTHOR-10k 배치 Apache-2.0(allenai/procthor-10k, 131★) | https://huggingface.co/datasets/allenai/molmospaces, https://github.com/allenai/procthor-10k | 10,000 집 중 900 시도(v1은 val 360 → 289), 06:30 KST 기준 388/900 처리 중(파드 CPU 100 % 제한, ≈100집/h); test 260은 CPU 때문에 중지 | Isaac USD → `make_visual` 평탄화(.usdc), 작업 구역 비움 검사(`tools/l9/assets/rooms9_table.py`); 끝나면 `tools/l9v2env/merge_rooms.py`로 `assets9/rooms_l9.json`에 합침 | ≈9 GB(진행 중) | **채택**(방 수 확대) |
| Amazon Berkeley Objects(ABO) 3D | CC BY 4.0 ("All models are distributed under Creative Commons Attribution 4.0 International License", Amazon.com 표기) | https://amazon-berkeley-objects.s3.amazonaws.com/index.html | 7,953 중 4,500 선별·**변환 4,500**(바닥 4,095·탁자 위 405; 의자 780·소파 465·탁자 412·장식 332·러그 268·조명 243 …) | glTF 2.0(glb, 4K) → 자체 순수 파이썬 변환기(`tools/l9v2env/abo_decor.py`: 변환 굽기·Y→Z·텍스처 1k) | 12 GB | **채택**(장식; 실제 제품 메시) |
| MolmoSpaces THOR / Objaverse 가구(v1) | CC BY 4.0 / 물체별 CC0·CC BY·CC BY-SA | v1 표 | 862 | v1 그대로 | v1 | 유지 + **과제 가구로 승격**(mesh_furniture) |
| Objaverse 1.0 (LVIS 등) | 전체 ODC-By 1.0, 물체별 CC-BY 721K / CC-BY-NC 25K / CC-BY-NC-SA 52K / CC-BY-SA 16K / CC0 3.5K | https://huggingface.co/datasets/allenai/objaverse | — | — | — | v1 물체 표(CC0·CC BY·CC BY-SA만) 유지, 이번 환경 확장에는 추가 안 함 |
| Google Scanned Objects | CC BY 4.0 (v1·L8S 물체 출처) | v1 표 | — | — | — | 유지 |
| HSSD (hssd-hab) | **cc-by-nc-4.0** | https://huggingface.co/datasets/hssd/hssd-hab | — | — | — | **제외(NC)** |
| RoboCasa | 코드 MIT, 자산 CC BY 4.0 (1.8k★) | https://github.com/robocasa/robocasa | — | — | — | **제외(원칙 1, 벤치)** |
| BEHAVIOR-1K | 코드 MIT (1.7k★); 자산 약관은 페이지에서 확인 불가 | https://github.com/StanfordVL/BEHAVIOR-1K | — | — | — | **제외(원칙 1 + 약관 미확인)** |
| LIBERO·RoboTwin·SimplerEnv 장면 | (해당 레포) | — | — | — | — | **제외(원칙 1)** |
| MolmoSpaces holodeck-/procthor-objaverse | 물체별 Objaverse 라이선스(일부 NC) | v1 기록 | — | — | — | 제외(v1과 같음) |
| 3D-FRONT / 3D-FUTURE | 공식 약관 페이지 확인 실패(404) | tianchi 페이지 | — | — | — | **사용 안 함(확인 불가 = 금지)** |
| Infinigen-Indoors | 코드 BSD-3-Clause(7.3k★), 생성 자산 라이선스 명시 없음 | https://github.com/princeton-vl/infinigen | — | Blender 생성 → USD 내보내기 필요 | — | 보류(파이프라인 크고 생성물 라이선스 미명시) [가설: 나중에 절차적 방 보강용] |

## 2. 축별 수 (v1 → v2, 2026-10-02 실측; 진행 중 항목은 끝나면 갱신)

| 축 | v1 (L9 prod1) | v2 | 비고 |
|---|---|---|---|
| 환경 계열 | 8 | **25** (+ 보류 1 = laundry) | `scene9.FAMILIES` + `scene9_more.MORE_FAMILIES` |
| 배치 규칙 | 40 | **128** | 계열당 5–6 |
| 놓는 곳 종류(노드) | top·zone·seat·cubby·slot·container·stand (7) | + shelf_high·compartment·shelf_low·gap·slope (**12**) | 노드마다 width·depth·clear_above·approach(top/front)·place_class(low/desk/high) |
| 놓는 곳 높이 | 0.32–1.08 m(위 접근) | 0.10–1.60 m | 높은 곳 1.10–1.55, 낮은 곳 0.10–0.30 |
| 장면 밀도 | 없음 | sparse / normal / dense (소품 0 / 1–2 / 3–5) | `add_props` |
| 방 배경 | 289 + 38 | + ProcTHOR train (진행 중) | 실외 2계열은 방 없음 + 실외 HDRI + 바닥판 |
| 메시 가구(배경) | 862 | 862 + PH 바닥 214 + ABO 4,095 (train 분할 3,793) | 프로세스당 6(과제용, 범주별 1) + 14 |
| 탁자 위 장식 | 0 | PH 159 + ABO 405 (train 452) | 프로세스당 8, 장면당 0–3, 팔 띠 밖 |
| 재질(텍스처) | 1,307 | **2,633** | 바닥 역할 새로 사용(바닥판), 실외 바닥 506 |
| 재질 겉모습 | 고정 | UV 배율 0.4–3.0(로그 균등) × 색조(역할별 30–60 %) | `vary9.material_look` |
| HDRI | 501 | **997** | 실외 계열은 실외 HDRI만 |
| 조명 계열 | 11 | **23** (실내 21 / 실외 5, 겹침 3) | 색온도 1,800–8,000 K |
| 머리 시선 | 45° ± 15° | + 위(−0.23–0.35 rad) / 아래(0.80–0.985 rad) | 높은·낮은 곳 편 |

## 3. L8S 가구 종류 → L9 v2 (사용자 10-02 03시: "l9은 그것만으로 학습을 돌릴 예정이기에 진짜 완벽해야해")

| L8S 종류 (`harvest/sim/assets_x/furniture.py`) | L9 v2 계열 / 노드 |
|---|---|
| table | dining·office·conference·craft_workshop·library_study·picnic_outdoor·kids_play / top |
| counter | kitchen·cafe_counter·bathroom_vanity·lab_bench·kitchen_island / top |
| counter_cabinet (벽 수납장 위) | kitchen/wall_cabinet / top(뒤 띠 덮임) |
| shelf_low (단 3개, 윗판 접근) | pantry_shelf (아래판 덮임, 위판 높음) + 고정물 shelf_low(탁자 밑) / top, shelf_low |
| shelf_tall (단 4개, 중간 덮임) | pantry_shelf·warehouse_rack·garage_cart/shelf_unit (위판) + mesh_furniture/shelf / top, compartment |
| low_table | living_low·kids_play·bedside·picnic/camp_table / top |
| bin (탁자 위 통) | crates·totes·baskets·tray 규칙 다수 / container·cubby |
| stand (받침 블록) | `add_stands`(전 계열) / stand |
| multi_level (높이 다른 탁자 둘) | living_low/two_tables·workbench/two_height·office/l_desk·kids_play/two_tables·reception/l_shape·cafe/two_level / top 2개 |
| floor_bin (바닥에 선 상자) | **warehouse_rack/floor_crate (신규)** / container |
| mesh_<범주> (THOR·Objaverse 메시 가구가 작업면) | **mesh_furniture (신규)**: table·counter·shelf·side_table·low_table·seat, 실측 지지면 → top / container / compartment |
| 쟁반·통·접시 등 물체 받침 | 용기 풀(v1, 595) 그대로 |

## 4. 원칙 반영 (§12.11 중 환경 몫)

| 원칙 | 반영 | 상태 |
|---|---|---|
| 1 벤치 저격 금지 | RoboCasa·BEHAVIOR·LIBERO·RoboTwin·SimplerEnv 자산 미사용; 행마다 source + id | 반영 |
| 2 양보다 다양성 | 계열·규칙 층화(plan), 축 값 meta 기록, 다양성 지표(SigLIP + 축별 엔트로피) | 반영(엔트로피 집계는 diversity 보고에) |
| 5 현실감 | 실물 메시(THOR·Objaverse·PH·ABO), CC0 PBR, 사실 조명; 지지면 마찰 무작위화 | **마찰은 미반영** — FX 슬롯 마찰은 L8S 공용 코드(0.6 고정), 근거 범위 원문 미확보 → 열린 문제 |
| 6 정직한 보류 | `scene9.HELDOUT_FAMILIES = ("laundry",)`(25계열 중 1 = 4 %), `all_rules("train")`; 방·재질·HDRI·장식은 id 해시 20 % ood | 반영(계획 도구가 `all_rules("train")`을 쓰도록 주인 몫) |
| 7 사전 검증용 축 기록 | world9 `furniture_scene.env_axes`(계열·규칙·밀도·소품·고정물·놓는 곳 높이 등급·노드 종류·방 종류·실외·재질 역할·UV·색조·HDRI 설정·조명·장식 수·시선) | 반영 |

## 5. 근거와 가설
- 강한 도메인 무작위화(방해물·배경·조명·탁자 높이)가 일반화를 키운다: RoboTwin 2.0 (arXiv 2506.18088, 2025-06, MIT, 2.9k★).
- 환경·물체 수가 늘수록 거듭제곱으로 좋아지고 환경당 시연 수는 일찍 포화: Data Scaling Laws in Imitation Learning (arXiv 2410.18647, 2024-10).
- 계열 정의·치수 범위·UV 배율·색조 비율·밀도 비율·시선 범위·고정물 비율(60 %)은 근거 없는 **가설** — 렌더 스모크 프레임 검수(G2)와 SigLIP 다양성(G4 v2)으로 판정한다.

## 6. 재현
- 재질·HDRI: `tools/l9v2env/fetch_mats.py` → `/data/harvest/assets_l9v2/materials/materials_l9v2.json` (사본 `harvest/l9/assets9/materials_l9v2.json`, 파일 경로 절대값).
- PH 모델: `tools/l9v2env/ph_models.py` → `assets9/decor_ph.json`.
- ABO: `tools/l9v2env/abo_decor.py` → `/data/harvest/assets_l9v2/abo/decor_abo.json`.
- 방: `tools/l9/assets/rooms9_table.py --set procthor-10k-train --n 900` → `/data/harvest/assets_l9v2/rooms/rooms_procthor_train.json`.
- 조사 API 수: `tools/l9v2env/survey_api.py` → `/data/harvest/assets_l9v2/survey/api.json`.

## 7. 렌더 스모크·다양성 (2026-10-02 02:44–06:30 KST, 7a2a GPU 1, Isaac 1개씩)

- 경로: `tools/l9v2env/smoke_rows.py` → `smoke_render.py`(collect9.draw → World9.prepare/reset → 머리 f0 저장, 편은 돌리지 않음) → `sheet.py`(접촉 시트로 직접 봄) → `diversity_smoke.py`(SigLIP + 축별 엔트로피). 결과 `/data/harvest/out/l9v2env/`(smoke1·smoke1b = 중간 코드 116장, smoke_v2 = 최종 코드 99장, smoke_v1 = v1 코드 106장, div_*.json).
- 프레임 검수에서 고친 것: (1) Poly Haven USD의 MaterialX 그래프 → Isaac 시작 +4.4분·텍스처 누락 → glTF→UsdPreviewSurface 변환(P160), (2) 실외 계열 화면에 앞 편의 방이 남음(meta room=null) → 방 주차(P164, v1에도 있던 잠복 버그), (3) 가전·금속 부품에 나무 텍스처, 소품 상자가 대리석 덩어리처럼 보임 → 팔레트별 재질 종류(metal·stone·plastic·wood·paint·paper). 이후 최종 99장에서 Isaac 오류 0, 'can not be found' 0, 시작 시간 v1과 같은 수준(276–437 s, 파드 CPU 100 % 제한 중).
- 열린 문제: Isaac 1개가 kitchen_island/bar_ledge 시드 7000043(왼팔) reset 뒤 48분 멈춤(원인 미확인, py-spy 권한 없음). `isaac.sh`의 `timeout`은 SIGTERM만 보내 Isaac이 살아남아 다음 작업과 2개가 겹침 → IR_INST로 찾아 SIGKILL(P172).
- 일부 ProcTHOR 방 바닥은 원래 밝은 하늘색·노랑(방 자산 색) — 바닥판 문제 아님(재질 기록으로 확인).

| 지표 (머리 f0, 같은 렌더 경로, n = 99) | v1 코드 | v2 최종 | 판정 |
|---|---|---|---|
| 무작위 쌍 코사인 거리 평균 | 0.201 | 0.195 | 넓어지지 않음 (n=106 중간판: 0.2025 대 0.2042 — 잡음 수준) |
| 근접 중복(>0.95) 최근접 비율 | 0 % | 0 % | 같음 |
| 최근접 유사도 중앙값 | 0.881 | 0.881 | 같음 |
| k-means 유효 군집(k=12) | 8.5 | 9.4 | 약간 늘어남 |
| 축 엔트로피(bit): 계열 / 규칙 / 조명 / 재질 / 방 / HDRI | 3.0 / 5.3 / 3.4 / 7.6 / 4.2 / 6.4 | 4.5 / 6.6 / 4.3 / 8.8 / 4.2 / 6.5 | 축 값은 고르게 넓어짐 |
| 새 축: 밀도 / 고정물 / 놓는 곳 등급 / 시선 | — | 1.5 / 2.2 / 1.1 / 0.24 | 새로 생김 |

- 해석(가설): 머리 f0는 집게·팔과 가까운 작업면이 화면 대부분이라 SigLIP 임베딩이 '탁자 위 로봇 팔' 구도에 묶인다. 환경 축을 넓혀도 쌍 거리는 0.20 근처에서 포화. 화면 구도를 바꾸는 축(E-HCAM8 카메라 기하, 높은·낮은 곳 과제의 시선 위·아래, 로봇 위치·방향 범위)이 다음 지렛대 — 과제 층이 새 놓는 곳을 쓰고 HCAM 무작위가 켜진 편으로 다시 잰다. G4 v2 (a) 기준은 이 측정으로는 **미통과**, (b) 0 %로 같음, (c) 약간 개선.
