# RGB만·하이브리드·깊이 필수 — 세 줄기 입력 방식 조사, 하이브리드(H) 설계, 깊이 있는 공개 데이터 목록 (2026-09-27)

작성 2026-09-26 19:5x–20:3x UTC(2026-09-27 04:5x–05:3x KST), 조사 에이전트. **구현·학습·유료 호출·데이터 내려받기는 하지 않았다.** 웹 검색, arXiv API(날짜·Comments)와 HTML 본문, GitHub API(별 수), HF 논문 API(좋아요), HF 데이터셋 API(라이선스·게이트), TFDS 카탈로그(OXE 깊이 필드), OXE 공식 시트(CSV)만 썼다. 확인 스크립트: `D:\tools\scratch_qdd\hyb_cred.py`·`hyb_arxiv_parse.py`·`hyb_ds.py`·`oxe_depth.py`.

## 사용자 원문 (user-log 148·149, 통제자 경유)

- (148) "아니면3가지 아예 없는 rgb 둘다있는 하이브리드 논문찾아보기 어떤식으로 쓰는지 추가 뎁스ㅡㄴ 필수로 쓰기 이걸 다 비교해볼 필요가 있음"
- (149, 작업 중 추가) "뎁스가 있는 데이터 셋이 있음? 심 데이터는 처리하면 되겠고"
- (작업 중 추가, user-log 147) "데이터는 1년반해제해줄게" → 6절 데이터 목록에는 오래된 데이터도 기간 표시 없이 넣는다. 논문·방법 근거에는 1.5년 규칙이 그대로다.

## 자리

- 정본 §98 보충 1(두 줄기 끝까지, user-log 146): 줄기 D(점 + 깊이 → 코드가 xyz)와 줄기 R(RGB만, xyz 직접)을 E-DIST8 → 강화 단계(1.5) → 최종 35B까지 같은 조건으로 짝 비교한다. 이 문서는 그 사이에 **줄기 H(하이브리드: 깊이가 있으면 쓰고, 없어도 동작)** 를 세 번째로 넣을 근거와 설계를 낸다.
- 우리 실측(E-PT F2, `docs/stage3/results/pt.md`): 한 높이(0.85 m) 학습으로 OOD-H 접근 3D 오차 중앙 — PT(깊이 점) ±3 cm **3.5 mm**, ±7 cm **3.6 mm** / L8-xyz 31.2·70.5 mm / ND-pt(모델이 추정한 top_z로 점을 xyz로) 38.8·92.1 mm(WORSE).
- 깊이 잡음 모형은 이미 있다: `harvest/teach_l8d/depth_noise.py`(`830473f`, σ_z = z²σ_d/(fB), 가림·저질감 구멍, `zed_mini`·`d405` 프리셋).
- T3(단안 깊이로 m 라벨 만들기)는 물체 3D 중심 17.5 cm로 버렸다(user-log 144). 이 문서는 단안 깊이를 **라벨이 아닌 입력 특징**으로 쓰는 문헌만 따로 본다(3.4절).
- 규칙:
  - 1.5년 규칙(논문): 2025-03-26 이후만 근거. arXiv가 그 전이고 학회가 뒤면 **[경계]**, 더 오래된 것은 **[기초]**. 데이터셋에는 적용하지 않는다(user-log 147).
  - 신뢰도 규칙(원문): "신뢰도 낮은 논문과 깃 저장소는 최대한 쓰지 않는다. 쓰느니만 못하다." / "신뢰도가 무조건 있어야 하고, 스타도 어느 정도 있어야 하고, 논문도 좋아요(반응)를 많이 받은 것이어야 한다."
  - 학회가 확인되지 않고 별·좋아요도 적은 것은 **7절 '뒷받침만'** 으로 보낸다.

## 0. 결론 요약

1. **믿을 만한 최근 연구의 하이브리드는 거의 한 가지 틀이다.** 깊이를 **별도 입력 갈래**로 넣고, 학습 때 **깊이를 무작위로 빼서**(또는 깊이 있는 표본과 없는 표본을 섞어서) RGB만으로도 돌게 만든다.
   - FALCON(ICLR 2026): 깊이·카메라 자세를 각각 베르누이로 넣거나 뺀다. CALVIN ABC→D 평균 길이는 RGB만 3.91, 시험 때만 깊이 3.95, 깊이로 학습 3.97로 비슷하다. 그런데 **물체 높이가 바뀌는 실물 과제는 60 % → 80 %** 로 올랐다.
   - RoboRefer(NeurIPS 2025): RGB 인코더를 복사해 초기화한 **별도 깊이 인코더**를 둔다. RGB 표본과 RGB-D 표본을 함께 학습해 두 방식 모두 추론할 수 있다.
   - SpatialRGPT(NeurIPS 2024, [기초]): RGB 연결기에서 초기화한 깊이 연결기를 '플러그인'으로 둔다. 깊이를 넣으면 91.78 %, 빼면 89.80 %다.
2. **깊이를 VLM 본체에 섞는 것은 조심해야 한다.** FALCON은 3D 토큰을 VLM에 넣으면 일반화가 떨어진다고 보고했다(3.91 → 3.79). 그래서 3D 토큰을 행동 헤드로 보냈다. 우리 상위는 행동 헤드가 없는 VLM이므로 이 경고는 H 설계의 첫 위험이다. **깊이 없음(H-off)에서 R보다 나빠지지 않는지**를 짝 비교로 꼭 잰다.
3. **깊이를 입력으로 받지 않고 '보조 과제'로만 쓰는 RGB 계열**도 강하다. 이것은 R 줄기의 강화 후보다(H가 아니다).
   - Spatial Forcing(ICLR 2026, 290★, HF 141): 중간층 시각 특징을 VGGT 특징에 맞춘다. LIBERO 98.5 %로, 깊이 입력 VLA인 GeoVLA 97.7·3D-CAVLA 98.1과 대등하다. 학습은 최대 3.8배 빨랐다.
   - MolmoAct(ICRA 2026)의 깊이 토큰, QDepth-VLA(AAMAS 2026)의 양자화 깊이 보조 손실(빼면 −2.9 %p)도 같은 계열이다.
4. **단안 깊이를 입력으로 쓰는 것은 문헌상 손해가 작다.** SD-VLM(NeurIPS 2025)은 GT 깊이로 학습하고 Depth-Anything-V2 추정 깊이로 추론해도 56.31 %였다(GT 57.71, 깊이 없음 46.73). 다만 그 과제는 정성·정량 QA다. 우리처럼 mm 목표가 필요하면 m 척도 오류(우리 T3 17.5 cm)가 그대로 들어간다. **최소 시험에는 넣지 않고** 강화 단계 후보(H+mono)로 둔다.
5. **권장 H 설계(4절)**: 깊이를 **두 번째 영상**(고정 m 범위 회색조, 같은 비전 인코더)으로 넣고 태그를 붙인다(`depth: sensor|none`). 학습 때 50 %는 깊이를 뺀다. 출력은 **PT 필드(점 + 높이 의도) + R 필드(xyz)를 한 답에** 낸다. 실행할 때는 깊이가 유효하면 PT 변환기를 쓰고, 없으면 xyz를 쓴다.
   - 이렇게 하면 H-on은 D와, H-off는 R과 **바로 짝 비교**된다.
   - 깊이 없는 공개 표본은 답에서 xyz 필드를 **생략**한다. 필드 생략이 곧 손실 가림이다.
6. **최소 무료 시험(5절)**: E-DIST8에 H 팔 하나를 더한다(R·D와 같은 L8-X 데이터·걸음·표본·시드). 평가는 세 방식이다. H-on(GT 깊이) 대 D, H-noisy(`zed_mini` 잡음) 대 D-noisy, H-off(깊이 없음) 대 R. 판정 규칙은 사전 고정한다. 예상은 GPU 약 3–4 GPU-h, 0원이다. **실행하지 않았다.**
7. **깊이 있는 공개 데이터(6절)**:
   - 우리 형식(m 깊이 + 내부·외부값)에 바로 맞는 것은 **BEHAVIOR 2025 데모**(머리·손목, MIT, 게이트 없음)다. OXE 안에서는 taco_play·stanford_robocook·fmb·maniskill·uiuc_d3field·berkeley_autolab_ur5·nyu_franka_play가 RLDS에 깊이 필드를 싣고 있다(TFDS 카탈로그 확인). 그 밖에 RH20T(RGB-D + 보정, 비상업 부분 있음), AgiBot World(깊이 PNG + 내부·외부값, CC BY-NC-SA, 게이트)가 있다.
   - 스테레오 쌍만 있는 것은 **DROID 원본**(ZED SVO, 8.7 TB)과 **RB2**(657편, 우리 기체, T4 보정 있음)다. FoundationStereo 계열로 깊이를 계산해야 한다.
   - MolmoBot은 손목 깊이만 있다(0.05–0.55 m). RefSpatial은 8비트 상대값이고, RoboTwin 2.0·InternData·Galaxea(좌우 머리 RGB만)는 깊이가 없다.
   - 심 데이터(우리 L8-X, RoboTwin 재생, MolmoSpaces)는 사용자 말대로 **처리하면 된다**(재렌더).

## 1. 세 줄기 (우리 말로)

| 줄기 | 입력 | 모델 출력 | xyz를 만드는 곳 | 깊이 없는 데이터 | 실측 근거 |
|---|---|---|---|---|---|
| **R** RGB만 | 머리 RGB(+손목) | xyz 목표(L8/ND-1 형식) | 모델 | 그대로 씀(양 최대) | E-PT: 한 높이 학습 시 OOD-H 31–71 mm |
| **H** 하이브리드 | RGB + **있으면** 깊이 | 점 + 높이 의도 **그리고** xyz | 깊이 유효: 코드(PT 변환기) / 없음: 모델 xyz | 그대로 씀(xyz·점 중 있는 라벨만) | 없음 — 5절 시험이 첫 측정 |
| **D** 깊이 필수 | RGB(+깊이는 코드만 씀) | 점 + 높이 의도 | 코드(깊이 + 보정) | 점 라벨만 쓸 수 있음 | E-PT PT: OOD-H 3.5·3.6 mm |

- D는 모델 입력에 깊이 영상을 넣지 않는다. 깊이는 코드(`resolve.py`)만 쓴다. H는 여기에 (a) 모델 입력 깊이와 (b) 깊이 없을 때의 대체 출력을 더한 것이다.

## 2. 방법 표

신뢰도 등급: **높음** = 주요 학회 + 저장소 별 수백 이상 또는 HF 좋아요 많음. **중** = 학회는 확인됐으나 별이 적거나, 학회는 없으나 별·좋아요가 꽤 있음. 날짜는 arXiv 첫 판(arXiv API 확인). 별은 2026-09-26 GitHub API, 좋아요는 HF 논문 API 기준.

### 2.1 깊이를 입력으로 받는 것 (H·D에 직접)

| 방법 | 깊이가 들어가는 곳 | 깊이가 없을 때 | 보고된 이득 | 출처 신뢰도 |
|---|---|---|---|---|
| **RoboRefer** (2506.04308, 2025-06) | **별도 깊이 인코더 + 투영기**(RGB 것에서 복사해 초기화). RGB-D 학습 중 RGB 인코더는 깊이에 영향받지 않고, 깊이 인코더만 따로 갱신 | RGB만 추론 가능. 기본 평가는 Depth-Anything-V2(상대 깊이)로 만든 깊이 사용 | SFT 공간 이해 평균 89.6 %, RefSpatial-Bench Gemini-2.5-Pro 대비 +17.4 %p(`lit_sweep` 재사용). 깊이 유무 절제 수치는 본문에서 확인 못 함 | 높음: NeurIPS 2025, 267★, HF 43. 기반 NVILA 2B·8B |
| **FALCON** (2510.17439, 2025-10) | VGGT 기반 공간 모델(ESM)에 깊이(+유효 마스크, 14×14 합성곱 인코더)·카메라 자세를 선택 입력으로. 3D 토큰은 **행동 헤드로**(VLM에 안 넣음) | 학습 때 b_d, b_p ~ 베르누이로 깊이·자세를 넣거나 뺌 → 영상만으로도 동작 | CALVIN ABC→D 3.91(RGB) / 3.95(시험 때만 깊이) / 3.97(깊이 학습). 실물 **높이 바뀐 물체 60 → 80 %**. 3D 토큰을 VLM에 넣으면 3.91 → **3.79**. 깊이 추정 δ<1.25 90.9 → 99.8 % | 높음–중: **ICLR 2026**, 39★(적음), HF 28. 기반 Kosmos-2 1.6B |
| **SD-VLM** (2509.17664, 2025-09) | **깊이 위치 부호화**: 깊이 지도를 패치 크기로 평균 풀링 → 사인 부호화 → 영상 임베딩에 더함 | 깊이 없으면 Depth-Anything-V2 추정 깊이 | 깊이 없음 46.73 → 56.31 %(+9.58 %p). GT 학습·GT 추론 57.71, GT 학습·**추정 추론 56.31**, 추정·추정 55.35 | 높음: NeurIPS 2025, 409★, HF 4. LLaVA-1.5-7B LoRA 1에폭 |
| **SpatialVLA** (2501.15830) **[경계]** | Ego3D 위치 부호화: ZoeDepth 단안 깊이 → 역투영 3D 위치 → 사인 + MLP → SigLIP 특징에 더함. 외부값 보정 불필요 | 센서 깊이 필요 없음(늘 단안 추정) | Ego3D를 빼면 Google Robot 변형 집계 콜라 집기 81.6 → 68.9 % | 높음: RSS 2025, 727★, HF 13. arXiv 2025-01이라 경계 |
| **BridgeVLA** (2506.07961, 2025-06) | **깊이로 만든 점군을 정사영 3장(위·앞·옆)으로 렌더**해 VLM에 영상으로 넣음. 출력은 시점별 2D 열지도 → 3D 점으로 역투영 | 점군이 필수(깊이 없으면 못 씀) | RLBench 88.2 %(RVT-2 81.4), COLOSSEUM 64.0(56.7), 실물 3편 학습 95.4 % | 높음: NeurIPS 2025, 229★, HF 12. PaliGemma |
| **UniVLG** (2503.10745) **[경계]** | 2D·3D 공용 구조. RGB-D는 3D 점 특징으로 씀 | 2D 영상은 학습 때 **50 % 확률로 MoGe 단안 점지도로 들어 올림**. 시험 때 2D는 들어 올리지 않음(추정 잡음 방지) | ScanRefer 순위 1위(2025-02). 센서 깊이 대 추정 깊이 직접 비교는 없음 | 높음: ICML 2025, 132★. arXiv 2025-03-13이라 경계 |
| SpatialRGPT (2406.01584) **[기초]** | 같은 영상 인코더로 깊이 지도를 처리하고, **RGB 연결기에서 초기화한 깊이 연결기**를 공간 QA에만 학습 | 플러그인이라 빼도 동작. 학습 깊이는 Metric3Dv2 유사 깊이 | RGB만 89.80 % → 깊이 91.78 %(정성 QA 평균) | NeurIPS 2024, 338★ |
| SpatialBot (2406.13642) **[기초]** | 깊이를 **3채널 uint8 영상**(각 채널 단위 2⁰·2⁵·2¹⁰ mm)으로 같은 인코더에 넣음 + `Depth(point)` 도구 호출로 **글 숫자** 반환 | 센서 없으면 ZoeDepth | 깊이 추정 과제 RGB 58–84 % → RGB-D 99 % 이상 | 학회 미확인, 355★, HF 3 |

### 2.2 깊이를 입력으로 받지 않고 학습 신호로만 (R 강화 후보, 하이브리드 아님)

| 방법 | 방식 | 추론 때 깊이 | 보고된 이득 | 출처 신뢰도 |
|---|---|---|---|---|
| **Spatial Forcing** (2510.12276, 2025-10) | 32층 중 24층 시각 임베딩을 VGGT 3D 특징에 코사인 정렬(L = L_action + α·L_align) | 불필요(구조 추가 없음) | LIBERO 98.5 %(OpenVLA-OFT 97.1, GeoVLA 97.7, 3D-CAVLA 98.1). 학습 최대 3.8배 빠름. 데이터 5 %로 75.8 % | 높음: **ICLR 2026**(OpenReview), 290★, **HF 141** |
| **MolmoAct** (2508.07917) | 답에 깊이 토큰 100개(Depth-Anything-V2 상대 깊이, 영상별 min–max → VQ-VAE 128코드). 깊이 입력은 없음 | 불필요 | `molmoact_deepdive` 참조 | 높음: ICRA 2026, 389★, HF 45 |
| QDepth-VLA (2510.14836) | 깊이 전문가가 VQ-VAE 깊이 코드(K = 256)를 예측(보조 교차엔트로피) | 불필요 | Simpler WidowX 68.5 %. 깊이 손실 빼면 65.6, 화소 회귀로 바꾸면 64.6 | 중: AAMAS 2026, 9★, HF 0 |
| DepthVLM (2605.15876, 2026-05) | **Qwen3-VL 4B·8B**에 DPT식 깊이 헤드. 1단계 헤드만 → 2단계 전체 미세조정. 4.4M 표본 | 입력 불필요(깊이를 출력) | m 깊이 δ1 0.890(DA3 0.877, Metric3Dv2 0.812). MMBench 84.6(원판 84.7) | 중: 학회 미확인, 164★, HF 11. **우리 기반과 같은 Qwen3-VL-8B**라 참고 가치가 큼 |
| Spatial-MLLM (2505.23747) | RGB 영상에서 VGGT 공간 인코더 특징을 더함 | 불필요 | (영상 공간 추론, `cross_embodiment` 문서) | 높음: NeurIPS 2025, 490★, HF 68 |
| DI² "Depth Helps" (2408.05107) **[기초]** | 학습 때 깊이로 '깊이 보완 모듈'을 가르쳐 RGB에서 가상 깊이 특징을 만듦 | 불필요 | (초록 수준) | IROS 2024 |

### 2.3 깊이를 글(숫자)로

| 방법 | 방식 | 출처 신뢰도 |
|---|---|---|
| **SSR** (2505.12448, 2025-05) | Depth Pro 추정 깊이 → SpatialRGPT로 속성 추출 → GPT-4o 근거 글 → Mamba로 잠재 토큰 압축 → Qwen2.5-VL에 끼움. 전체 평균 +18.7. 깊이 없는 경우는 다루지 않음 | 중: NeurIPS 2025, 42★, HF 10 |
| SpatialBot `Depth(point)` [기초] | 모델이 점을 물으면 도구가 그 점의 깊이(mm)를 글로 돌려줌 | 위 표 |

- 우리 PT 변환기가 이미 '점 → 깊이 → xyz'를 코드로 한다. 글 숫자는 D의 역할과 겹친다. H에 넣는다면 '점 몇 개의 깊이 값을 요청 글에 적기'는 싸다. 다만 믿을 만한 VLA 근거가 없어 최소 시험에서는 뺀다.

### 2.4 RGB만 기준 (R의 참조)

| 모델 | 입력 | 출처 신뢰도 |
|---|---|---|
| π0.5 (2504.16054) | RGB 여러 대 + 언어 + 상태. 깊이 없음 | 높음: CoRL 2025 Oral, openpi 14,001★ |
| GR00T N1 (2503.14734) | RGB + 언어 + 상태. 깊이 없음 | 높음: 기술 보고서, Isaac-GR00T 8,132★ |
| Embodied-R1 (2508.13998) | RGB에서 점 찍기(공간 지시) | 높음–중: ICLR 2026, 156★, HF 19 |

## 3. 주제별 정리

### 3.1 모달리티 드롭아웃 / 선택 깊이 입력

- **믿을 만한 VLA·VLM 근거**:
  - FALCON: 깊이·자세 각각 베르누이 → 한 모델로 RGB만 / +깊이 / +깊이+자세. 확률 값은 본문에서 확인 못 함.
  - UniVLG: 2D 표본을 50 %로 3D로 들어 올림(반대 방향의 드롭아웃).
  - RoboRefer: 같은 RefSpatial을 2단계에서 **RGB와 RGB-D 두 방식으로 모두** 다시 씀. 목적은 "영상 인코더가 깊이 단서를 넘어서 공간 이해를 배우게" 하는 것이다(본문).
- **로봇 정책의 옛 근거**: Octo(RSS 2024)·RDT-1B(ICLR 2025)의 관측 토큰 무작위 가림은 **[기초]** 다. 카메라 빠짐 대비용이지 깊이용은 아니다.
- 최근 깊이 드롭아웃 VLA 논문(M3 2608.22419, 증거 게이트 2609.03142 등)은 학회 미확인이라 7절로 보냈다. M3는 손목 영상·언어를 가리며, 깊이는 가리지 않는다.
- **뜻**: 드롭아웃은 '깊이 없어도 동작'을 만드는 표준 장치다. 대신 FALCON의 CALVIN 결과처럼 **평균 성능은 깊이 유무로 거의 안 바뀌고, 높이·크기 변화 같은 기하 과제에서만 차이가 난다.** 우리 평가는 OOD-H가 주 지표라 이 차이를 잡기에 맞다.

### 3.2 깊이를 넣는 형식 다섯 가지 — 우리 Qwen3-VL·Qwen3.5 LoRA + vLLM 서빙에서의 비용

| 형식 | 예 | 모델 코드 변경 | vLLM 서빙 | m 척도 보존 | 깊이 없을 때 | 우리 판단 |
|---|---|---|---|---|---|---|
| ① 추가 채널(RGB-D 4채널) | (VLA에서 드묾) | 패치 임베딩 층 교체 | 사용자 정의 필요 | 가능 | 0 채움 | 사전학습 인코더 분포를 깸 → 비추천 |
| ② 별도 깊이 인코더·연결기 | RoboRefer, SpatialRGPT | 인코더·투영기 복제 | 사용자 정의 모델 등록 필요(35B-A3B MoE 포함) | 가능 | 갈래를 끔 | 근거는 가장 좋지만 비쌈 → **강화 단계 후보** |
| ③ 위치 부호화로 더하기 | SD-VLM, SpatialVLA | 영상 임베딩 뒤 한 줄 훅 | 훅 필요 | 가능(사인 부호화) | 더하지 않음 | 싸지만 서빙 훅 필요 → 강화 단계 후보 |
| ④ 깊이를 **영상으로 렌더**해 같은 인코더에 | SpatialBot(3채널 mm), BridgeVLA(점군 정사영), 로봇 기준 점지도(2607.11498, 뒷받침만) | **없음**(영상 한 장 더) | **그대로** | 고정 범위 부호화면 가능. 영상별 min–max면 상대값(MolmoAct·RefSpatial) | 영상 생략 + 태그 | **최소 시험 채택** |
| ⑤ 점군 토큰 | GeoVLA, PointVLA(모두 7절), 3D-VLA [기초] | 점 인코더 추가 | 사용자 정의 | 가능 | 갈래 끔 | 근거 약함 + FALCON의 "VLM에 3D 토큰 넣으면 일반화 하락" → 비추천 |
| ⑥ 글 숫자 | SSR, SpatialBot 도구 | 없음 | 그대로 | 가능 | 줄 생략 | D의 코드 변환과 겹침 → 보조 후보 |

- ④를 고르는 이유는 세 가지다.
  - 모델·서빙 코드를 건드리지 않는다. 8B·35B-A3B 모두 영상 두 장을 이미 받는다.
  - 같은 비전 인코더로 깊이를 처리하는 선례가 있다(SpatialBot, SpatialRGPT의 인코더 공유).
  - 깊이를 뺀 입력은 R의 입력과 **바이트 단위로 같다**. 그래서 H-off 대 R 비교가 깨끗하다.
- 위험: 두 번째 영상만큼 시각 토큰이 늘어 학습·추론이 느려진다. 깊이 영상은 RGB 해상도의 1/2로 넣어 줄인다. 이것은 시험의 고정값이고, 문헌 근거는 없다.

### 3.3 RGB만 데이터와 RGB-D 데이터를 섞어 학습하기

- RoboRefer: RefSpatial의 모든 표본에 깊이가 있다. 웹 영상은 추정 깊이, CA-1M은 3D, 시뮬은 GT 깊이다. 2단계에서 같은 표본을 RGB와 RGB-D로 **두 번** 쓴다.
- UniVLG: 2D 데이터는 50 % 들어 올림, 3D 데이터는 그대로 쓴다. 시험 때 2D는 들어 올리지 않는다.
- SpatialRGPT: 깊이 연결기는 **공간 QA에만** 학습한다. 일반 QA는 RGB 갈래만 쓴다. 과제별로 가리는 셈이다.
- MolmoAct·π0.5(`cross_embodiment` 문서): 출처별 태그 문장과, 없는 행동 차원은 0 채움 + 가림을 쓴다.
- **우리에게 옮기면**:
  - (a) 요청 글에 `depth: sensor` / `depth: none` 태그를 붙인다. 출처 태그는 기존 E-DIST8 규칙을 따른다.
  - (b) 라벨이 없는 필드는 **답에서 생략**해 손실을 가린다. 예: 공개 픽셀 흐름에는 m xyz가 없으니 점만 넣는다.
  - (c) 깊이 있는 표본도 50 %는 깊이를 빼 같은 상태를 두 방식으로 본다(RoboRefer 2단계 방식).

### 3.4 단안 깊이 유사 라벨로 빈 깊이 채우기 — 입력 특징으로서

- 문헌은 입력으로 쓸 때 손해가 작다고 말한다.
  - SD-VLM: GT → 추정 추론 −1.4 %p.
  - RoboRefer: 기본 평가가 DA-V2 상대 깊이.
  - SpatialVLA: 늘 ZoeDepth.
  - UniVLG: 학습 때만 MoGe로 들어 올리고 시험 때는 쓰지 않는다. 추정 잡음이 2D 성능을 해치는 것을 막으려는 것이다.
- 우리 측정은 m 척도 추정이 3D 중심 17.5 cm, 광선 수직 5.3 cm였다(T3, `public_data_conversion_howto` 11.2절). mm 목표를 내는 우리 과제에서 추정 깊이를 **m 값 그대로** 입력하면, 모델이 그 척도를 믿는 순간 오차가 된다.
- 권고:
  - 최소 시험에서는 **쓰지 않는다**.
  - 강화 단계(1.5)에서 'H+mono' 변형을 연다. 깊이 없는 표본에 단안 깊이 영상을 `depth: estimated` 태그로 넣고, 서열 정보만 쓰도록 영상별 min–max 상대 부호화를 한다(MolmoAct·RoboRefer와 같은 뜻).
  - 관문: H+mono-off가 H-off보다 나은지, 사전등록한 짝 비교로 본다.

### 3.5 깊이가 없거나 잡음일 때의 강건성 보고 방식

| 논문 | 보고한 것 | 빠진 것 |
|---|---|---|
| FALCON | 같은 모델을 RGB만 / +깊이(시험 때) / +깊이(학습)로 따로 평가. 높이·크기 변화 실물 | 깊이 잡음 강도별 곡선 |
| SD-VLM | GT/추정 깊이 × 학습/추론 2×2 | 깊이 완전 결손 |
| SpatialRGPT / SpatialBot | 깊이 유무 절제 | 센서 잡음 |
| RoboRefer | RGB·RGB-D 추론 둘 다 가능하다고만 씀 | 깊이 유무 수치(본문에서 찾지 못함) |
| Spatial Forcing | 깊이 입력 VLA(GeoVLA·3D-CAVLA)와 같은 표에서 비교 | — |

- **공백**: 믿을 만한 VLA·VLM 논문 중 **깊이 잡음 강도(스테레오 오차 모형)별 성능**을 보고한 것은 찾지 못했다. 우리는 `depth_noise.py`의 `zed_mini`로 H-noisy·D-noisy를 따로 잰다(5절). 이것이 곧 실물 이전 위험의 직접 측정이다.

## 4. 권장 H 설계 (Qwen3-VL-8B → Qwen3.5-35B-A3B, LoRA, 코드 변경 최소)

1. **입력**
   - 영상 1: 머리 RGB(R·D와 같음).
   - 영상 2: **있을 때만** 머리 z-깊이.
     - 부호화: **고정 m 범위** 0.25–1.60 m → 8비트 회색조, 가까울수록 밝게. 무효·범위 밖 = 0(검정). 이 범위는 우리 L8-X 머리–탁자 거리를 덮도록 잡은 가정값이며, 등록 전에 L8-X 깊이 분포 1–99 백분위로 다시 정한다.
     - 해상도: RGB의 1/2.
     - 영상별 min–max는 쓰지 않는다. m 뜻이 사라지기 때문이다(MolmoAct·RefSpatial과 다른 점).
   - 요청 글 한 줄: `depth: sensor (head, metric, gray 0.25–1.60 m, near=bright)` 또는 `depth: none`.
   - 인코더·투영기는 공유하고(SpatialBot·SpatialRGPT의 인코더 공유), LoRA는 R·D와 같은 설정을 쓴다.
2. **출력(한 답)**: PT 필드(`point_2d` + `height`)와 R 필드(xyz 목표)를 **둘 다** 낸다. 판단·검증 필드는 기존과 같다.
3. **실행**
   - 깊이가 유효하고, PT 변환기가 그 점에서 물체 영역을 찾으면 → PT 경로(D와 같은 코드).
   - 아니면 → 모델 xyz(R과 같은 채점기).
   - 대체 비율을 로그로 남긴다(`fallback_rate`).
4. **학습 데이터(같은 L8-X 편)**
   - 깊이 있는 각 상태에서 p = 0.5로 영상 2를 뺀다. 확률 값은 FALCON 베르누이·UniVLG 50 %를 참고한 가정값이다.
   - 남긴 것의 절반은 `zed_mini` 잡음을 씌운 깊이로 넣는다(`dataset.build(depth_noise=...)`).
   - 답에는 늘 점과 xyz를 넣는다. 시뮬은 둘 다 참값이 있다.
   - 공개 픽셀 흐름(E-DIST8 +px): 깊이 없음, 답은 점 필드만(xyz 생략 = 손실 가림).
5. **하지 않는 것(이유)**
   - 별도 깊이 인코더(②)·위치 부호화(③): 서빙 코드 변경. H가 이긴 뒤 강화 단계에서 연다.
   - 점군 토큰(⑤): 근거 약함.
   - 단안 깊이 입력: 3.4절.
6. **위험과 확인할 것**
   - (i) FALCON 경고처럼 깊이 영상이 VLM 표현을 흔들어 **H-off가 R보다 나빠질 수** 있다(판정 Q2).
   - (ii) 한 답에 두 출력을 내면 형식 부담이 커져 유효율이 떨어질 수 있다(관문 G-fmt).
   - (iii) E-PT의 ND-pt처럼, 한 높이 데이터에서는 모델 xyz가 z를 외운다. H-off는 L8-X(높이 다양)에서만 뜻이 있다.

## 5. 최소 무료 8B 시험 — E-DIST8의 H 팔 (설계만, 실행 안 함)

- **위치**: E-DIST8에서 R·D를 짝 비교하는 데이터 수준과 **같은 수준 하나**(권고: 공개 픽셀 흐름이 섞인 '+px' 수준. 깊이 없는 표본이 자연히 섞여 혼합 학습을 실제로 시험한다). R·D가 여러 수준에서 돌아도 H는 한 수준만 더한다(비용 최소).
- **같게 두는 것**:
  - Qwen3-VL-8B, LoRA 설정, 걸음 수, 표본 수, 시드, 수집 편(L8-X), 채점기.
  - 평가 세트 DEV·OOD-H(좁게 ±3 cm·넓게 ±7 cm)·OOD-O·OOD-D.
  - R·D와 같은 한 번의 사전 등록 안에 넣는다.
- **평가 방식(같은 상태 집합)**:
  - H-on: GT 깊이. 대조는 D.
  - H-noisy: `zed_mini` 잡음. 대조는 D-noisy — D도 같은 잡음으로 재평가하며, 이것이 D에 추가되는 평가 1회다.
  - H-off: 깊이 없음. 대조는 R.
  - 폐루프: E-PT와 같이 OOD-H s0·s1, 세 방식 각각.
- **주 지표**: OOD-H 접근 3D 오차 중앙(mm). 부 지표는 DEV, 잡기 |z| ≤ 15 mm 비율, `fallback_rate`, 유효율. 판정은 스냅숏 짝 부트스트랩 10,000회, 시드 0(`tools/teach_pt/compare.py`와 같은 방식).
- **관문**:
  - G-fmt: H 유효율 ≥ 0.98.
  - G-fb: H-on의 대체 비율 ≤ 10 %(E-PT 점 라벨 빠짐 6.9 %를 참고).
  - G-same: H-off 요청이 R 요청과 바이트 동일(깊이 줄·영상 2 제외).
- **판정(사전 고정)**:
  - Q1 H-on 대 D: (H − D) 95 % 구간 상한 ≤ +2 mm면 비열등.
  - Q2 H-off 대 R: 상한 ≤ max(5 mm, R 중앙의 10 %)면 비열등. 상한 < 0이면 BETTER.
  - Q3 H-noisy 대 D-noisy: 같은 방식, 여백 +2 mm.
  - 결론 칸:
    - `H_REPLACES_BOTH` — Q1·Q2 비열등. 한 모델로 두 줄기를 덮을 수 있다. 다만 user-log 146에 따라 R·D는 끝까지 계속 들고 가고, 교체는 사용자 결정이다.
    - `H_DEPTH_ONLY` — Q1만 통과.
    - `H_NOT_NEEDED` — Q1 불통.
  - 모든 결론은 버리기 전 재검증 규칙(user-log 143)을 따른다.
- **비용 추정**:
  - 학습 약 1.5–2.5 GPU-h. E-PT 팔 1.3–1.6 GPU-h(816걸음)에 영상 한 장 추가분(1/2 해상도)을 더한 추정이다.
  - 평가 약 1.5 GPU-h(오프라인 3방식 + D-noisy + 폐루프).
  - 합계 약 3–4 GPU-h, **0원**. GPU는 x2 파드 규칙을 따른다.
- **필요 코드(작음)**: 데이터 빌더에 영상 2·태그·드롭아웃·필드 생략, 답 스키마(PT + xyz), 실행기의 분기(PT 변환기 → 실패 시 xyz). 기존 `teach_l8d.dataset`·`pt_schema`·`resolve` 재사용.
- **강화 단계(1.5)로 미루는 변형**:
  - H-sep: 별도 깊이 연결기(RoboRefer·SpatialRGPT식).
  - H-dpe: SD-VLM식 위치 부호화.
  - H+mono: 3.4절.
  - R+SF: Spatial Forcing 보조 정렬. H가 아니라 R 강화 후보다.

## 6. 깊이가 있는 공개 로봇 데이터 (user-log 149, 1.5년 규칙 해제 user-log 147)

깊이 종류: **m 센서**(또는 시뮬 GT m) / **상대 8비트** / **스테레오 쌍만**(깊이는 계산해야 함) / 없음. '게이트'는 HF에서 연락처 공유 동의가 필요한지를 뜻한다(`hyb_ds.py`의 HF API `gated` 값). 크기는 카드 표기다. 내려받은 것은 없다.

| 데이터 | 깊이 종류 | 카메라 | 내부·외부값 | 크기 | 라이선스 · 게이트 | 신뢰도 | H / D 쓰임 · 필요한 처리 |
|---|---|---|---|---|---|---|---|
| **BEHAVIOR-1K 2025 데모** (`behavior-1k/2025-challenge-demos`) | **m 시뮬 GT**. 14비트 로그 양자화를 10비트로 저장해 1 m에서 약 2.4 cm 단위(`public_data_conversion_howto` 6.2 함정 7). 분할 영상도 있음 | 머리 720², 손목 좌우 480²(깊이 셋 다) | `cam_rel_poses`(21) + 알려진 내부값(머리 fx 306) | 1만 편, 1.95 TB | 카드 **MIT**, 게이트 없음. 자산(OmniGibson 장면·물체)은 설치기가 **별도 약관 동의**를 요구한다(`--accept-dataset-tos`). 데모 영상만 쓰면 해당 없음, 재렌더하면 해당. 약관 본문은 미확인 | NeurIPS 2025 챌린지, 1,723★, 좋아요 38 | **D·H 모두 바로.** 양자화 단위(2.4 cm @1 m)가 PT 변환기 오차로 들어가는지 먼저 잰다 |
| **MolmoBot-data** (`allenai/molmobot-data`) | **m 손목만**(0.05–0.55 m, RGB 부호화 mp4). 머리 깊이 없음 | 머리 + 손목 좌우 | 프레임별 보정(기저 기준 EE) | Franka 3.47 TB, RBY1 148 GB | ODC-BY, 게이트 없음 | 학회 미확인, molmospaces 479★ | 머리 기준 D에는 못 씀. H에는 머리 = `depth: none` 표본. 손목 깊이는 손목 입력을 쓸 때만. MolmoSpaces로 재렌더하면 머리 깊이를 얻을 수 있음(API가 GT 깊이 조회를 지원한다고 소개됨, 미시험) |
| RefSpatial (`JingkunAn/RefSpatial`) | **상대 8비트**(영상별 min–max) | 단일 영상 | 내부값 없음 | 250만 표본(HF 250 MB 색인, 원본 약 357 GB) | Apache-2.0, 없음 | NeurIPS 2025, 267★ | m 뜻이 없어 D 불가. H에서는 `depth: none`으로만(또는 H+mono의 상대 입력과 같은 부류) |
| **AI Worker RB2** (`ROBOTIS/Task_0002`) | **스테레오 쌍만**: 머리 ZED Mini 좌·우(657편에만 오른눈). 깊이 스트림 없음 | 머리 좌우 + 손목 2 | 공개 보정 없음. **우리 T4 보정**(보류 2.32 px, 카메라 약 ±4°·5 cm 모호) + 공칭 기선 63 mm·VGA fx 367(정본 §47) | 857편 / 85,474 프레임 | apache-2.0(`robotis_open_data_survey`). 이번 비로그인 HF API는 401 → 게이트 여부 [확인 필요] | 우리 기체, 공식 재게시 | **D·H 가능(처리 후).** 좌우 → FoundationStereo 또는 Fast-FoundationStereo 시차 → z = f·B/d. 확인할 것: mp4 압축 영향, 좌우 정류 여부(ZED 출력이 정류본인지 [확인 필요]), 기선 실측. 관문: 스테레오 깊이 ↔ T4 FK 그리퍼 깊이 차 중앙 ≤ 2 cm, 탁자 평면 흔들림 |
| **DROID 원본** (`gs://gresearch/robotics/droid_raw`) | **스테레오 쌍만**: ZED 2 외부 2대 + ZED Mini 손목. SVO 원본과 `-stereo.mp4` | 외부 2 + 손목 | 내부값은 SVO 안. 외부값은 메타 + 개선 재보정(약 3.6만 장면) | 약 9.2만–9.5만 편, 원본 약 8.7 TB | CC BY 4.0(LeRobot 판 카드는 apache-2.0 표기), 게이트 없음 | RSS 2024 | D·H 가능(처리 후): ZED SDK 깊이 또는 스테레오 mp4 → FoundationStereo. RLDS·LeRobot 판은 **왼눈만·깊이 없음**. 제3자 'droid-metric-depth' 저장소(FoundationStereo 파이프라인)는 신뢰도 미확인 → 참고만 |
| **RH20T** (rh20t.github.io) | **m 센서 RGB-D** 1280×720, 10 Hz | 전역 RGB-D 8–10대 + 손 1–2대 | **보정 폴더**(내부·외부 행렬, 보정 때 그리퍼 자세) | 11만+ 시퀀스, 크기 줄인 판 RGB 약 5 TB · RGBD 약 10 TB | RH20T-C: CC BY-SA 4.0, **RH20T-NC: CC BY-NC 4.0**. HF 공식본 아님(자체 내려받기, 절차 [확인 필요]) | ICRA 2024 | D·H 가능. 전역 카메라라 머리 시점과 다름. 비상업 부분은 연구 한정 |
| **AgiBot World** Alpha·Beta | **깊이 PNG 폴더**(단위·어느 카메라인지 카드에 없음 [확인 필요]) | 여러 시점(머리·손목 등) | 에피소드마다 **내부·외부값** 폴더 | Beta 100만+ 궤적, 2,976 h, 48.1 TB | **CC BY-NC-SA 4.0**, **게이트**(연락처 공유 동의) | IROS 2025 최우수 논문 후보, T-RO 2026(README 표기), 3.2k★, 좋아요 237(Alpha) | 단위 확인 뒤 D·H 후보. 게이트·비상업 동의는 사용자 결정 필요 |
| RoboMIND (`x-humanoid-robomind/RoboMIND`) | 카드에 "시뮬 데이터는 깊이가 당분간 없음"만 있음. 실물 깊이 여부 [확인 필요] | Franka·천궁 휴머노이드·AgileX·UR5e | 카드에 없음 | 10.7만 궤적, 12.3 TB | Apache-2.0, **게이트** | RSS 2025, 좋아요 54 | 깊이 확인 전에는 R용 |
| InternData-A1 | **없음**(RGB 3대) | 머리·손 좌우 | 내부·외부값 **있음**(보강판) | 63만+ 궤적, 7,433 h, 6.72 TB | CC BY-NC-SA 4.0, 게이트 | arXiv 2511.16651, 좋아요 108 | R용. 시뮬이지만 엔진·장면 공개 여부를 모르면 재렌더 불가 |
| InternData-M1 | 없음(RGB 3대) | base ×2 + ego | 카드에 없음 | — | CC BY-NC-SA 4.0, 게이트 | 좋아요 31 | R용 |
| Galaxea Open-World | **없음. 다만 머리 좌·우 RGB 두 대** → 스테레오 쌍일 가능성 | 머리 좌우 + 손목 2, 720×1280, 15 fps | 카드에 보정 없음 | 500+ h, 2.87 TB | CC BY-NC-SA 4.0, 게이트 | arXiv 2509.00576, 좋아요 53 | 기선·내부값이 없어 지금은 R용. 보정이 공개되면 RB2와 같은 처리 |
| RoboTwin 2.0 | **저장 안 됨**(재생하면 가능) | 5기체, 머리·손목 | `config.yml robot_pose` 등 | 2.55 TB | MIT, 없음 | ICML 2026, 2,914★, 좋아요 68 | 시드 + 궤적 재생으로 깊이 렌더(SAPIEN) → D·H |
| **OXE RGB-D 부분** (RLDS에 깊이 필드가 실제로 있음, TFDS 카탈로그 확인) | taco_play `depth_static` 150×200·`depth_gripper` 84×84(float32); berkeley_autolab_ur5 `image_with_depth` 480×640(float32); nyu_franka_play `depth`·`depth_additional_view` 128×128(int32); maniskill `depth`·`wrist_depth` 256²(uint16, 시뮬); stanford_robocook `depth_1–4` 256²(float32); uiuc_d3field `depth_1–4` 360×640(uint16); fmb 옆 2 + 손목 2 256²(float32). **단위는 데이터셋마다 [확인 필요]** | 위 필드 | 시트 '보정 있음': taco_play·maniskill·stanford_robocook·fmb = 예. berkeley_autolab_ur5·nyu_franka_play·uiuc_d3field = 아니오. RLDS 안에 보정 값이 실렸는지는 미확인 | 편 수(시트): taco_play 3,242, berkeley_autolab_ur5 896, nyu_franka_play 456, maniskill 30,000, stanford_robocook 2,460, uiuc_d3field 196, fmb 1,804 | 데이터셋마다 다름(OXE 시트 인용 줄). 개별 라이선스 미확인 | OXE: ICRA 2024 | 보정이 있는 넷(taco_play·maniskill·robocook·fmb)이 D·H 후보. 나머지는 H의 깊이 입력 표본으로만(보정 없이는 PT 변환 불가). 시트는 RT-1·Bridge·DROID·RoboSet·SPOC·DobbE·Plex 등도 '깊이 카메라 있음'으로 적지만, **RLDS 필드에는 깊이가 없다**(수집 때 장비 표기) |
| BridgeData V2 원본 | "깊이는 있을 때 주 고정 카메라 시점"(원본 내려받기). 편 수 미기재 | 주 고정 카메라 | 보정 언급 없음 | — | CC BY 4.0 | CoRL 2023 | 깊이 있는 편 수 확인 전에는 보류 |

- **H·D에 쓸 수 있는 순서(권고)**:
  1. 우리 L8-X 시뮬(GT 깊이 + 잡음 모형) — 주 원천. 이미 있다.
  2. BEHAVIOR 데모 — m 깊이 + 보정 + 과제 물체 GT, MIT, 게이트 없음.
  3. RB2 스테레오(처리 후) — 우리 기체·실물. FoundationStereo(CVPR 2025 Oral, 2,926★) 또는 Fast-FoundationStereo(CVPR 2026, 약 1.5k★, `no_metric_xyz_control_survey` 확인). 관문을 먼저 통과해야 한다.
  4. OXE 보정 있는 RGB-D 넷, RH20T(C 부분).
  5. DROID 원본 스테레오.
  6. AgiBot World(게이트·비상업 → 사용자 동의 필요).
- **스테레오 → m 깊이 처리 공통 절차**: 정류된 좌우 쌍 → 시차 → z = f·B/d → 머리 카메라 z-깊이 영상. 무효 = 0.
  - 우리 PT 변환기(`resolve.depth_points`)가 받는 형식과 같게 만든다.
  - 관문: (a) 탁자 평면 RANSAC 기울기·흔들림, (b) FK 그리퍼 점의 깊이 대 스테레오 깊이 차.
  - 실물 ZED 잡음은 `depth_noise.zed_mini`와 비교해 모형을 보정한다.
- **심 데이터**(사용자 말 "심 데이터는 처리하면 되겠고"): L8-X는 깊이를 이미 렌더한다. RoboTwin·MolmoSpaces·BEHAVIOR(자산 약관 동의 뒤)는 재생·재렌더로 머리 m 깊이를 만들 수 있다. 비용은 렌더 GPU다(x2 파드 규칙).

## 7. 뒷받침만 (신뢰도 부족 또는 미확인 — 결정 근거로 쓰지 않음)

- DepthVLA(2510.13375): 깊이 예측 트랜스포머를 섞은 MoT VLA. 실물 78.5 대 65.0 %. 학회 없음, HF 0, 저장소 미확인.
- GeoVLA(2508.09071): 깊이 → 점군 → 말단 기준 점 임베딩 → 행동 전문가. 학회 없음, 6★, HF 0. Spatial Forcing 표의 비교 대상으로만 인용.
- PointVLA(2503.07511): 점군 주입 블록, 높이 적응 주장. 학회·저장소 없음, HF 0.
- See like a Robot(2607.11498): **로봇 기준 점지도 영상**(픽셀 = 로봇 좌표 xyz)을 π0.5·SmolVLA에 넣음. 카메라를 옮기면 RGB 대비 우위가 커짐. 학회 없음, 3★. 우리 ④ 형식의 변형(xyz 영상)이라 강화 단계에서 다시 볼 만하다.
- M3 모달리티 가림(2608.22419), 증거 게이트 정규화(2609.03142), 깊이 서열 프롬프트(2607.11173, "Work in progress"), GaussVLA(2608.24959, BMVC 2026 표기, 별 미확인), 유사 깊이 확산 정책(Scientific Reports 2026, 본문 접근 못 함).
- GraspVLA(2505.03233): 419★이나 학회 표기 없음. 입력이 RGB만인지 본문에서 확인하지 못함 → R 참조로도 쓰지 않음.
- VLM-3R(2505.20279): 449★, 학회 미확인.
- 3D-VLA(2403.09631, ICML 2024, 638★): [기초]. 3D 생성 세계 모델이라 우리 형식과 멀다.

## 8. 출처

- 논문: https://arxiv.org/abs/2506.04308 · https://arxiv.org/abs/2510.17439 · https://github.com/FALCON-VLA/FALCON · https://arxiv.org/abs/2509.17664 · https://arxiv.org/abs/2501.15830 · https://arxiv.org/abs/2506.07961 · https://arxiv.org/abs/2503.10745 · https://icml.cc/virtual/2025/poster/45879 · https://arxiv.org/abs/2406.01584 · https://arxiv.org/abs/2406.13642 · https://arxiv.org/abs/2510.12276 · https://openreview.net/forum?id=euMVC1DO4k · https://arxiv.org/abs/2508.07917 · https://arxiv.org/abs/2510.14836 · https://arxiv.org/abs/2605.15876 · https://arxiv.org/abs/2505.23747 · https://arxiv.org/abs/2408.05107 · https://arxiv.org/abs/2505.12448 · https://arxiv.org/abs/2504.16054 · https://arxiv.org/abs/2503.14734 · https://arxiv.org/abs/2508.13998
- 뒷받침만: https://arxiv.org/abs/2510.13375 · https://arxiv.org/abs/2508.09071 · https://arxiv.org/abs/2503.07511 · https://arxiv.org/abs/2607.11498 · https://arxiv.org/abs/2608.22419 · https://arxiv.org/abs/2609.03142 · https://arxiv.org/abs/2607.11173
- 데이터: https://huggingface.co/datasets/behavior-1k/2025-challenge-demos · https://huggingface.co/datasets/allenai/molmobot-data · https://huggingface.co/datasets/JingkunAn/RefSpatial · https://droid-dataset.github.io/droid/the-droid-dataset · https://rh20t.github.io/ · https://huggingface.co/datasets/agibot-world/AgiBotWorld-Beta · https://github.com/OpenDriveLab/AgiBot-World · https://huggingface.co/datasets/x-humanoid-robomind/RoboMIND · https://huggingface.co/datasets/InternRobotics/InternData-A1 · https://huggingface.co/datasets/InternRobotics/InternData-M1 · https://huggingface.co/datasets/OpenGalaxea/Galaxea-Open-World-Dataset · https://huggingface.co/datasets/TianxingChen/RoboTwin2.0 · https://rail-berkeley.github.io/bridgedata/ · OXE 시트 https://docs.google.com/spreadsheets/d/1rPBD77tk60AEIGZrGSODwyyzs5FgCU9Uz3h-3_t2A9g · TFDS 카탈로그 https://www.tensorflow.org/datasets/catalog/taco_play (외 berkeley_autolab_ur5·nyu_franka_play_dataset_converted_externally_to_rlds·maniskill_dataset_converted_externally_to_rlds·stanford_robocook_converted_externally_to_rlds·uiuc_d3field·fmb)
- **확인 못 함**: FALCON 베르누이 확률 값, RoboRefer 깊이 유무 절제 수치, AgiBot 깊이 단위·카메라, RoboMIND 실물 깊이, OXE 깊이 단위·RLDS 안 보정 값, RB2 ZED 영상 정류 여부, BEHAVIOR 자산 약관 본문, RH20T 내려받기 절차.
