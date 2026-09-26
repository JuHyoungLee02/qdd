# E-VLA-solo VLA 단독이 의미가 있는가 + 느린 재생 — 사전 등록 (2026-09-26T09:44:01Z, 본 실행 전)

작성 포크 에이전트(E-SR1e 에이전트가 통제자 메시지로 분기). 근거: 사용자 발언 user-log 107 "Vla는 혼자서 의미가 있는지도 보긴해야해 그리고 로본의 동작 속도자체도 조금 느리게 가져가도 좋을듯", E-Couple 사전 실행 B5(VLA 단독 0/12, `results/couple_dry.md` bd3a8ba), 그 원인 분해 `results/vla_alone_diag.md`(런타임 교착 8/12 + VLA 자체 실패 4/12). 결과는 `docs/stage3/results/vla_solo.md`.

## 0. 성격, 바뀌는 결정, 자체 검사(user-log 87)
- **무료 폐루프 시험**(유료 0원, `--astra none --couple off`; 러너가 다른 값은 거부). 시뮬 R2 DEV(E-Couple 사전 실행과 같은 장면·같은 체크포인트 `ckpt/sr1c/c1/last`·같은 런타임 사본 `code_couple_dry_9322853`). 새 파일만: `tools/vla_alone/*`(러너 훅·분석·판정·진단), `tests/test_vla_alone.py`. `harvest/` 무수정(깃 런타임 무수정 — 훅은 Isaac 작업자 안에서만).
- **이 결과로 바뀌는 결정**:
  (a) **Q1 VLA 단독의 의미** — TASK_MEANINGFUL(어느 VLA 팔이든 성공 ≥ 4/12 ≈ 30 %, 통제자 관문 값) → 유료 E-Couple의 VLA 단독 짝 비교가 성립(바닥 아님), 그 팔의 조건(C3/C5·속도)을 E-Couple 기준 조건 후보로; PROGRESS_ONLY(성공은 없지만 제자리 기준선보다 확실히 머그에 다가감) → VLA 단독은 '접근까지만 의미', E-Couple 유료 금지 유지, 재학습 체크포인트(ser-A-min-3)에서 같은 관문 재측정; NOT_MEANINGFUL → VLA 단독은 이 과제에서 의미 없음, 결합 구조 주장(P3)은 VLA를 바꾸기 전까지 보류.
  (b) **Q2 느린 재생** — ADOPT_S(0.75배 또는 0.5배가 성공 +2편 이상이고 지나침이 줄어듦) → 정본 한 줄 "속도 낮추기는 검증 후 채택"의 검증 통과로 그 배속을 VLA 재생 기본값 후보로; NOT_ADOPTED → 1.0배 유지(느린 재생은 지나침·맴돌기의 해법이 아님).
  (c) **Q3 교착 확인** — CONFIRMED(C5 12편 중 ≥ 6편이 영구 hold로 끝나고 C3가 더 멀리 감) → 런타임 결함으로 결합 통제자에게 수정 요청(T1 모순 hold 중 되돌리는 청크 허용·hold 상한·열림 문턱), E-Couple 전 필수 수정 항목; NOT_CONFIRMED → 진단의 교착 가설을 약화로 기록.
- **이 표본으로 가를 수 있나**: 팔당 12편(DEV 0–5 × standard·dr). 성공 차 +2편(0.17)은 작은 효과를 못 가르지만 결정 규칙은 '쓸 만한가'(≥ 4/12)와 '분명한가'(+2편 + 지나침 감소)만 가른다. 진행 비교는 짝 12쌍 중 ≥ 10쌍(부호 검정 p ≈ 0.019)이라 우연을 가른다. 과제 하나(mug_tray P0) — 일반화는 가르지 않는다.
- **더 싼 사전 실행**: 0.3 — 진단은 기존 기록만(CPU), 사전 실행은 1장면 15 s × 4팔(A·D·F·G).

### 0.1 원인 가설과 성립 조건(P81)
| # | 가설(진단에서) | 이 실험의 확인 | 팔 |
|---|---|---|---|
| H1 | 런타임 교착(T1 모순 → hold → 결정 비움 → 청크 버림)이 0/12의 주원인 | C3((b) 되먹임 끔 = hold 없음, 나머지 같음) 대 C5 | A 대 B |
| H2 | 청크를 빨리 재생해 머그를 지나친다(지나침 중앙 43 mm) | 같은 청크를 0.75·0.5배로 재생(행 사이 선형 보간, 틱당 관절 변화도 같은 비로 줄어 0.04 rad/틱 규칙에 유리) | B 대 C·D, A 대 E |
| H3 | VLA의 폐루프 방향 결정이 우연 수준(36 %) | 계획기 규칙 기준선(같은 런타임·특권 결정·스킬 직선 이동)과 제자리 기준선 사이 어디인가 | F·G |

### 0.2 팔(고정)
| 팔 | 정책 | 조건 | 재생 배속 |
|---|---|---|---|
| A | VLA `sr1c/c1` fused | C5(E-Couple 사전 실행과 같음) | 1.0 |
| B | 〃 | C3((a)만, (b) 되먹임 없음 → hold 없음) | 1.0 |
| C | 〃 | C3 | 0.75 |
| D | 〃 | C3 | 0.5 |
| E | 〃 | C5 | 0.5 |
| F | 계획기 규칙 기준선: modular `--model mock`(labels_v2 S1 코드 규칙 = 특권 결정, 스킬 S의 직선 제한 이동) | C5 | 1.0 |
| G | 제자리 기준선: fused `--model mock_fused --vla-noop 1`(특권 결정 + 편 첫 관절을 끝까지 유지하는 청크) | C5 | 1.0 |
- 모두 DEV 시드 0–5 × standard·dr, 편당 최대 60 s(사전 실행과 같음), `--clock simlat`, 메인 파드 **GPU 3만**(Isaac 렌더 + fused 서버; GPU 2는 렌더 금지, GPU 0·1·x2는 쓰지 않음), 두 변형 병렬 작업자.
- 배속 구현(`tools/vla_alone/vla_closed.py`): fused는 런타임의 청크 재생 시계(`core._advance_play_clock`, 결합 감속과 같은 식)를 결합이 꺼진 때도 매 틱 배속 S로 전진 → 청크 행 k가 t0 + k·dt/S에 재생; modular(F)는 스킬 `speed_scale`(F는 1.0만).

## 1. 질문
E-SR1c C1 VLA를 결합 없이 폐루프로 돌릴 때 (1) 제자리·계획기 규칙 기준선 사이에서 어디까지 가는가(성공·최소 거리·도달 단계·멈춤 시간), (2) 청크를 느리게 재생하면 지나침과 맴돌기가 줄고 성공이 느는가, (3) 0/12의 주원인이 런타임 교착인가?

## 2. 실행
- 고정 사본 `/data/harvest/code_vla_solo_<등록 커밋>` = `code_couple_dry_9322853` 복사 + 이 등록 커밋의 `tools/vla_alone/`(LF). 구동 `bash tools/vla_alone/run_vla.sh <사본> main`(팔 순서 F → G → A → B → C → D → E, 끝나면 `analyze`), 출력 `/data/harvest/out/vla_solo/<팔>/`(런타임 기록 + `vla_trace_<변형>.jsonl` 100 Hz 궤적 + `video/` 2 Hz 프레임), 로그 `/data/harvest/logs/vla_solo/lanes.out`.

## 3. 지표 (편별, `tools/vla_alone/analyze_vla.py`)
성공(`env_success`), 손가락 중점–머그 최소 3D·xy 거리(mm, 특권 시뮬 값 — 분석에만), 도달 단계(approach < descend < close < lift < carry < place_descend < open < retreat < done), 멈춤 시간(TCP 속도 < 5 mm/s(0.5 s 창)이면서 close·open·done이 아닌 시간), hold 시간·영구 hold(첫 hold부터 끝까지), 지나침(첫 close 전, 처음 접근축에 대한 (g − 머그)xy 투영 최대, > 0 = 넘어감), 편 시간, 관절 계단(틱당 관절 명령 변화 > 0.04 rad인 틱 수), approach 이동 속도 중앙(mm/s).

## 4. 판정 (고정, `analyze_vla.py` 머리말과 같음)
- **G-bench**: F 성공 ≥ 10/12 — 아니면 시험대 자체가 의심 → 판정 없음·재설계.
- **Q1**: TASK_MEANINGFUL ⇔ A–E 중 하나라도 성공 ≥ 4/12; 아니면 PROGRESS_ONLY ⇔ A–E 중 하나가 G와 짝 12쌍 중 ≥ 10쌍에서 최소 3D 거리가 20 mm 이상 작고 중앙 ≤ 40 mm; 아니면 NOT_MEANINGFUL. '의미의 출처'는 단계별 표(도달 단계·거리·멈춤)로 서술(판정 밖).
- **Q2**: S ∈ {C 0.75, D 0.5}에 대해 ADOPT_S ⇔ 성공(S) − 성공(B) ≥ 2편 ∧ 지나침 중앙(S) < 지나침 중앙(B); 없으면 NOT_ADOPTED. E 대 A는 판정 밖 보고.
- **Q3**: CONFIRMED ⇔ A 12편 중 영구 hold ≥ 6 ∧ (B 도달 단계 중앙 > A ∨ 성공(B) > 성공(A)).

## 5. 도중 관문과 변경 규칙
- G0(사전 실행, 등록 전): 네 팔(A·D·F·G) 1편씩 rc 0·궤적·요약 생성, D의 approach 이동 속도가 A의 0.35–0.65배(배속 적용 확인), G의 TCP 최대 이동 < 50 mm(제자리 확인, 0.3).
- 본 실행 중: 팔마다 12/12 편 요약·궤적(없으면 멈춤), 작업자 Traceback 0. 결함(버그·무효 > 10 %·시간 2배(팔당 예상 약 20분 → 40분)·관문 실패) → 멈춤 → 재설계 → 이 문서 8절 변경 기록(`date -u`) → 커밋 → 재개. 판정 규칙·문턱은 바꾸지 않는다.

## 6. 해석 한계
시뮬(R2)·과제 하나·12편·체크포인트 하나(E-SR1c C1, 5질문 판 — 재학습 ser-A-min-3 전). 거리·지나침은 특권 시뮬 값. C3는 (b)의 hold뿐 아니라 (b)의 epoch 무효화·조기 호출도 끈다(교착만 떼어 낸 조건이 아님 — H1의 확인은 '교착을 포함한 (b)'의 효과). 느린 재생은 결정 주기(0.33 s)를 바꾸지 않으므로 거리당 결정 수가 늘어난다(효과의 일부일 수 있음). 계획기 규칙 기준선은 특권 결정이라 상한 참고이지 경쟁 방법이 아니다.

## 7. 코드(LF sha256 앞 16)
| 파일 | LF sha256 앞 16 |
|---|---|
| `tools/vla_alone/analyze_vla.py` | `10ac29cdfd53aba5` |
| `tools/vla_alone/demo_ref.py` | `26d3c53089022541` |
| `tools/vla_alone/diag_couple_dry.py` | `eccf54b1e9d2a07f` |
| `tools/vla_alone/diag_table.py` | `c20f3a4c8811247f` |
| `tools/vla_alone/vla_closed.py` | `c3c3ee1e9f885a31` |
| `tools/vla_alone/run_vla.sh` | `76a51a9019502d78` |
| `tests/test_vla_alone.py` | `bb99b596935a12b7` |

## 8. 이미 본 것 / 하지 않는 것 / 변경 기록
- 이미 본 것: E-Couple 사전 실행 결과·기록 전부(진단 `vla_alone_diag.md`), 사전 실행 G0 값(0.3 — 성공·거리 값은 1편·15 s라 판정과 무관).
- 하지 않음: 유료 호출, 결합 켬, 런타임·체크포인트 수정, 재학습, GPU 0·1·2·x2.
- 변경 기록: (없음)

### 0.3 사전 실행 (등록 전)
- 개발 사본 `/data/harvest/tmp/vla_alone/code` = `code_couple_dry_9322853` 복사 + `tools/vla_alone`, 메인 파드 GPU 3(당시 유휴 확인, 07:43Z·09:43Z nvidia-smi).
- **진단**(CPU, 기존 기록만, 07:3x–07:40Z): `results/vla_alone_diag.md` — VLA 단독 0/12 중 8편이 런타임 교착(T1 모순 → hold 고리), 4편이 VLA 자체 실패, 지나침 중앙 43 mm, 폐루프 방향 답 머그 적중 36 %.
- **G0 사전 실행**(07:43–07:55Z, dev0 standard 1편 × 15 s × A·D·F·G): 네 팔 rc 0, 작업자 Traceback 0, 궤적·요약 생성, 분석 rc 0. D의 approach 이동 속도 중앙 34.2 mm/s = A 72.8 mm/s의 **0.47배**(배속 적용 확인, 문턱 0.35–0.65 안). F(계획기 규칙)는 15 s 안에 place_descend까지(지나침 4.7 mm) — 60 s 본 실행에서 끝낼 수 있는 속도. 판정 스크립트는 15 s·1편이라 G-bench 실패(NO_VERDICT_BENCH)로 끝남(의도대로, 값은 판정과 무관).
- **G0에서 잡은 결함 1**: 제자리 팔 G(`mock_fused` 그대로)가 15 s에 TCP **278 mm** 움직임 — 원본 mock은 매 청크를 '지금 측정한 관절'로 다시 잡아 중력에 처진 자세를 계속 따라가므로 제자리가 아니다. → `vla_closed.py --vla-noop 1`: 편의 첫 청크 요청 때 관절을 끝까지 유지. 재실행(09:41–09:43Z) 최대 이동 **39.9 mm**(첫 청크 전 약 0.2 s의 초기 처짐) — 제자리 기준선으로 씀. G0 문턱을 '< 5 mm'에서 **'< 50 mm'**로 고쳐 등록(이 값을 본 뒤 정한 것임을 밝힘; 판정 문턱이 아니라 기준선 온전성 관문).
- 관찰(판정 밖): D(0.5배)의 관절 계단(틱당 > 0.04 rad) 21틱 대 A 6틱 — 느린 재생에서 청크 전환 계단이 오히려 늘 수 있다(본 실행에서 보고).
- 로컬 시험 `tests/test_vla_alone.py` 4 통과.
- 쉼: 07:55Z–09:40Z 세션 한도로 작업이 멈췄다가 재개(파드 실행 없음).
