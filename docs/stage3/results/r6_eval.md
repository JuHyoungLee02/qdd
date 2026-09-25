# R6 평가 스크립트 (E0.5 재생 · RD · CAL 보정 · 폐루프 묶음) — 한 명령 실행

- 계획: `docs/superpowers/plans/2026-09-25-e2e-ready.md` 관문 R6. 근거 정본: 00-interfaces §28(J1–J5), §31(J5), §42(시계 트랙·로그), §45(E-M8c), §50–§63, E-first §2A(E0.5 판정 1–10)·§3(E1), EVAL §4.2(std→rnd 짝 RD), M4 §5(C0–C6).
- 실행: 2026-09-24 UTC(R7 2회차 K1 정정 — 처음엔 KST 날짜를 적었다) (파드 `p-test2/juhyoung-native-7a2a`, 파드 UTC 21:00–21:45 무렵). vLLM은 **GPU 2**(렌더 없음 — GPU 3은 시작 시 다른 작업이 쓰고 있었음), Isaac은 **GPU 1**(동시 ≤ 2 프로세스), GPU 0 안 씀. 코드 파드 사본 `/data/harvest/code_r6/`(`tools/r6/sync.sh`, `CODE_VERSION`에 로컬 커밋·dirty 기록), 산출물 `/data/harvest/out/r6/<태그>/`. git 커밋 안 함.
- **§56 규칙**: 아래 수치는 모두 "명령이 끝까지 도는지" 확인용 소규모 판이다. 결과·근거로 인용하지 않는다(단계 A SFT는 POOL fit 편으로 학습됐고, labels_v2 정답은 S1 좌표에서 거의 기계적으로 나온다).

## 1. 명령 (파드, `source /data/harvest/env.sh` 뒤 `cd /data/harvest/code_r6`, 파이썬 = `/data/harvest/venv_vllm/bin/python`)

| 명령 | 하는 일 | 산출물 |
|---|---|---|
| `python -m harvest.eval.e05 --model M --out D --data DIR[,DIR] --split pool\|dev [--episodes N] [--truth labels_v2\|outcome:<rule> --outcome-dirs ...] [--d-p95 0.307] [--same-k 3] [--blocks 2] [--floor-n 0] [--gpu 2]` | E0.5 오프라인 재생(§2A): 연속 스냅샷마다 A0 × K=3 동시(같은 시각 반복, 첫 답 = 표), A1–A4 이름 판 각 1회, 시간 블록 B개 × 바닥 부분집합 2회 연속(test-retest 바닥 (ii)). 결정 스텝 k의 표 = t ≤ t_k − d_p95인 최근 스냅샷 3개. 규칙 newest(C2)·LA-2 γ0.67·C2''·C2'(Probability Fusion)·C2'-S(Score Fusion)·S1 단독을 labels_v2(또는 결과 기반 best 집합)로 채점 → `judge_e05`(판정 1–4·6·9·10) + 판정 5·7·8 | `e05.json`·`e05.md`·`calls.jsonl`(이어 하기) |
| `python -m harvest.eval.rd --model M --out D --variants standard=DIR,random=DIR,dr=DIR --split dev [--compare OTHER_OUT] [--closed --closed-seeds 0-4 --conditions C5 --isaac-gpu 1]` | std→random/dr 짝 RD: 변형별 정확도(질문·섭동별, 최빈 기준선), (kind, seed, k, 질문) 짝 낙폭 A_std − A_var(에피소드 군집 CI), 상대 RD = 1 − A_var/A_std, 짝 없는 차, `--compare`로 두 모델 낙폭 차 dRD. `--closed`면 R5 런타임으로 같은 레이아웃 시드의 폐루프 성공률 RD(짝 부트스트랩) | `rd.json`·`rd.md`·`items.jsonl` |
| `python -m harvest.eval.calib --model M --out D --fit-data DIR --fit-split cal --heldout DIR --heldout-split test\|dev\|pool [--alphas 0.05,0.1,0.2] [--thetas 0.6,0.7,0.8]` | E1: 적합 편을 에피소드로 반분(§52: 반쪽 1 = 질문별 온도, 반쪽 2 = J5 split conformal q̂), 보류 편에서 ECE(등폭·등질량 15구간 — 판정 1·원 확률 규칙은 등질량(E §3.4), R7 7회차 정정·정본 §72; 모든 ECE는 `ambiguous` 스냅샷을 빼고 계산, 그 항목은 `heldout.ambiguous`로 따로 — R7 8회차, 정본 §73)·AUROC·θ 구간 정확도·적용률·J5 커버리지·집합 크기·원소 하나 비율·빈 집합·NE 포함·원소 하나 정확도 + E1 판정 1·8 | `calibration.json`(**런타임이 읽는 파일**, 모델 지문 × question_id 해시에 묶임), `calib.json`·`calib.md` |
| `python -m harvest.eval.closed --model M --out D [--backend modular\|fused] [--seeds 0-4] [--variants standard,random] [--conditions C0,...,C6] [--clock simlat\|sync] [--hb-n 5\|0,5,10,20] [--calibration FILE --j5-alpha 0.1] [--astra mock\|api] [--isaac-gpu 1] [--gpu 2]` | R5 런타임 폐루프 묶음: 바깥 프로세스가 vLLM을 띄우고(pre-R7 뒤: 단계 B 체크포인트면 vLLM 대신 `runtime.fused_model` HF 서버, `closed.py` 머리 설명 'Backends' 줄) 변형마다 Isaac 작업자 하나(`ir_run.sh`, cyclo), 작업자는 몸체를 한 번 만들고 조건(× 하트비트 N)마다 IR `eval()` 한 번. 성공률(시드 군집 CI)·성공 시각·결정 지연 p50/p95·확정 비율·호출·막힘 시간·RTF·M4 epoch·Astra 호출·C0 정지 틱·J5 집계, C5−Cx 짝 차, 변형 있으면 폐루프 RD | `closed.json`·`closed.md`·`<변형>/<조건>/`(IR 로그 + §42 부가 JSONL·프레임·요약) |

- `--model`: 병합 폴더 / LoRA 어댑터 폴더(자동 병합 `tools/stagea_merge.py`, CPU float32, `<out>/merged_<sha>`) / `zero-shot`(Qwen3-VL-4B) / `mock`(GPU 없는 배관 확인). vLLM 설정은 `tools/r5/serve.sh`와 같음(접두 캐시·멀티모달 캐시·이미지 2장·raw logprobs·seed 0·`VLLM_BATCH_INVARIANT=1`), 호출 방식 **lead**(§59). `--url/--served-name`으로 떠 있는 서버를 쓸 수 있다. 배치(`--layout auto`)는 모델의 학습 prompt_config를 따른다(단계 A = H, 영점 = H; HW 지정 가능).
- 모든 출력 JSON의 `meta`: 명령·argv·UTC·git(커밋·dirty)·`code_sha`(harvest/**/*.py 해시)·모델(종류·경로·**지문**(파일 이름·크기 + 작은 파일 전체 + 큰 파일 앞뒤 16 MB의 sha256, 전체 가중치 해시 아님)·학습 prompt_config)·평가 prompt_config sha(카메라 배치·S1 1 mm·시스템 문장·프롬프트 파일 해시)·질문 id·시드·분할·실행 시간. (R7 7회차 추가, 정본 §72) `meta.bootstrap` = 부트스트랩 횟수(`--n-boot` 기본 **10,000** = E §1.7 사전 등록, 7회차 전 기본 2,000은 결함 E1)·seed 0·95% 백분위·재표집 단위(e05·rd·calib = 에피소드, closed = 레이아웃 시드, epoch는 시드 안).

## 2. 분할 보호 (CAL·TEST)

- `harvest/eval/splits.py`: DEV 0–29, POOL 2000–2119는 자유. **CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329는 `--split cal|test|test_p5`와 환경 변수 `HARVEST_ALLOW_SPLIT=<같은 이름>`이 둘 다 있어야** 열린다. **이 변수는 메인 세션만, 그 분할을 쓰는 실험의 사전 등록 시각에 설정한다**(에이전트·스모크는 설정하지 않음).
- 파일을 열기 전에 모든 시드를 선언 분할과 대조(`check_seeds`) — DEV 폴더라고 선언한 곳에 TEST 시드가 있으면 거부, POOL로 선언했는데 DEV 시드면 거부. 폐루프 몸체도 같은 규칙(`aiworker.check_layout_seed`: DEV만, 보호 분할은 변수 일치 때만; POOL은 폐루프 분할이 아님).
- 파드 확인(변수 없이): `closed --split test --seeds 1000`·`e05 --split cal` → 거부 메시지, `closed --split dev --seeds 1000` → "not in split dev" 거부, 출력 폴더도 만들어지지 않음. **이번 작업에서 CAL·TEST 시드는 만들지도 열지도 않았다.**

## 3. 검증 판 (소규모, §56)

| 태그 | 명령·입력 | 끝까지 | 벽시계(초) | 주요 출력(확인용) |
|---|---|---|---|---|
| `e05_sft_pool` | e05, SFT 병합, POOL 첫 6편(170 스냅샷, 호출 1,870) | 예, 오류 0 | 238 (vLLM 준비 133 + 호출 100) | 성공 궤적 연속 flip 0.193, 섭동 창 0.453, 같은 시각 flip 0, 재시험 0.0024, 바닥 0; newest 0.759 / LA-2 0.676 / C2'' 0.759 / C2' 0.754 / C2'-S 0.899 / S1 0.987; `claim = a_as_stabilizer`, 판정 6 단서 켬, 판정 9 두 층 `keep`, A4 flip → C3'' 필요 |
| `e05_sft_pool_outcome` | 같은 호출 캐시, `--truth outcome:time0.33`(결과 기반 best 집합, 결정 스냅샷 275항목) | 예 | 82 (호출 0.1) | newest 0.687 / LA-2 0.666 / S1 0.731 |
| `e05_zs_dev` | e05, 영점, DEV P0·P1 각 3편(172 스냅샷) | 예 | 150 (78 + 69) | newest 0.364, S1 0.999, 이름 치환 flip L7_17 0.756 |
| `calib_sft` | calib, SFT, 적합 POOL 10편(T 5 / J5 5) → 보류 DEV 30편(질문당 804) | 예 | 139 (81 + 52) | T: dir_xy 1.38·dir_z 1.45·mag 1.11·target 0.055·phase 0.68; ECE(보정 뒤) 0.000–0.069; J5 α0.1 커버리지 0.906–1.0; J5 통과 dir_xy·dir_z·target·phase(α 0.1), mag는 α 0.2만; 적합 < 400이라 전부 "보장 없음" |
| `rd_sft` | rd, SFT, standard/random/dr 각 DEV 9편(질문 × 스냅샷 1,265 짝) | 예 | 115 (75 + 37) | A 0.911 / 0.916 / 0.917, 낙폭 −0.006 [−0.013, 0.002] / −0.006 [−0.016, 0.002] |
| `rd_zs` | rd, 영점, 같은 입력, `--compare rd_sft` | 예 | 128 | A 0.420 / 0.428 / 0.413, dRD(영점−SFT) random −0.002 [−0.015, 0.009], dr 0.013 [−0.008, 0.032] |
| `closed_mock` | closed, 모의 선택기, DEV 0–1, C5·C2·C0, 30 s | 예 | 402 | C5·C2 1/2 성공(시드 0), C0 0/2(응답 대기 중 정지 5,460틱 — 설계대로 느림) |
| `closed_mock_c1346` | closed, 모의, DEV 0, C1·C3·C4·C6, 30 s | 예 | 255 | 4조건 모두 성공(13.1–17.1 s), C1·C4 확정 비율 0(합의 없음), C4·C6 epoch 4 |
| `closed_mock_hb` | closed, 모의, `--hb-n 0,10` | 예 | 109 | `C5|hb0` Astra 5회, `C5|hb10` 1회(E-M8c K2-N 격자 경로 확인) |
| `closed_sft_j5` | closed, SFT(jevl, lead, H), `calib_sft/calibration.json` + **J5 α 0.1**, DEV 0, C5·C2, 60 s | 예, 호출 오류 0 | 294 (vLLM 75, 작업자 218) | C5 성공 26.4 s(지연 p50/p95 0.127/0.157 s, J5 통과 273·보류 47·상위 호출 19), C2 실패(place_descend에서 60 s) |
| `closed_fused_mock` | closed, `--backend fused --model mock_fused`, 6 s | 예 | 58 | 인터페이스 확인(청크 = 정지 유지라 성공 없음이 정상) |
| `rd_closed_mock` | rd `--no-offline --closed`, 모의, standard+random, DEV 0–1, C5, 40 s | 예 | 326 | SR 0.5 / 0.5, 폐루프 RD 0.0(짝 2) |

- 테스트(TDD): 로컬 `cd D:/qdd && python -m pytest -q` 전체 통과, 파드 사본(`venv_train` + IR PYTHONPATH)에서 `tests/eval` + `tests/runtime` 통과(TODO 스텁 1 건너뜀). 새 시험 73개: `tests/eval/test_splits.py`(10) · `test_e05_pure.py`(14, 표 시각·규칙·flip·C_flip 두 식·C2'/C2'-S·A3 이름 뜻·섭동 창·블록 차·합성 자료 analyze) · `test_common.py`(11, 이름 판 요청·oracle 차단·키 되돌림·이미지 배치·모델 판별·지문·학습 prompt_config·vLLM 플래그) · `test_calib_pure.py`(7, 온도·q̂·집합·파일 묶기·보류 지표·E1 판정) · `test_rd_pure.py`(5) · `test_closed_pure.py`(6, 집계·짝 RD·하트비트 격자 이름·작업자 경로·작업자 명령 GPU 2 거부) · `test_runtime_r6.py`(14, C1–C6 가짜 세계 완주·C0 대기 정지·J5 보류/상위 호출·지문 불일치 거부·몸체 시드 보호) · `test_cli_mock.py`(6, e05·calib·rd의 mock 끝까지 + 분할 거부; closed는 Isaac이 필요해 파드 판으로 확인).

## 4. 런타임에 더한 것 (R5 코드, 최소 수정)

- `harvest/runtime/conditions.py`(새): M4 §5 최소 조건표 C0–C6 → `M4Params`·`RuntimeConfig` 덮어쓰기. C0 = in-flight 1 + 응답 대기 중 팔 정지(`stop_wait`), C1 = in-flight 1 + newest, C2 = 겹침 + newest(합의·(b) 없음)([정정 R7 9회차, 정본 §74: C2 = 사전 등록 VLM Stream — `agree "stream"`, in-flight 상한 없음·실측 기록, 매 틱 요청 시각 기준 가장 새 유효 응답 적용(시작된 스텝에도), 5 s 타임아웃이면 기본 행동]), C3 = (a)만, C4 = (b) + newest, C5 = 기본(M4 설계), C6 = C5 + in-flight 1. 런타임에 없는 것: C2'/C2'-S/C2-match(e05에서 오프라인 값만), C3', C3'', C5-A3, C-FIX, C5'.
- `m4.py`: `M4Params.agree`("consensus"|"newest", newest는 요청 시각이 가장 새 표가 차지·확정 없음), `feedback_b`(끄면 (b) 결과는 기록만), `max_inflight`(N_max 상한). 기본값은 기존 동작 그대로(기존 15개 시험 통과). [정정 R7 9회차, 정본 §74: `agree`에 "stream"(C2), `n_max_cap`(C2 = False, 상한 없음) 추가, `gamma` = "2/3"(정확 비교)]
- `harvest/runtime/calibration.py`(새): 온도·q̂·집합·평가·E1 판정 순수 함수 + `Calibration.load`(모델 지문·question_id 해시 불일치면 거부 → 게이트 꺼짐).
- `core.py`: `RuntimeConfig.condition / stop_wait / calibration / j5_alpha / j5_escalate_after(2) / model_fingerprint`. 결정 응답이 오면 질문별 온도로 확률 보정, J5가 켜진 질문(보정 파일의 `j5_ok`)에서 집합이 원소 하나면 그 보기가 표, 둘 이상·빈 집합·NE 포함이면 표를 넣지 않고(직전 확정 유지, 정지 아님) 2회 연속이면 하트비트를 당김(`hb.advance`, 사건 기록). 요약에 `condition`·`stop_ticks`·`j5`.
- `aiworker.py`: DEV 전용 검사를 `check_layout_seed`로 바꿈(보호 분할은 변수 일치 때만).

## 5. 발견·한계 (열린 것)

1. **FusedModel 실모델 없음**: `closed --backend fused`는 `mock_fused`만 받는다. 단계 B 체크포인트용 `StageBFused`(vLLM 결정 + HF 청크; (**정정(정본 §67 C4, R7 4회차 M2)**: 실제 구현은 2순위 — decide도 HF 백본의 공유 접두 순전파 한 번으로 결정 확률·문맥 은닉·확인 헤드를 함께 얻고, 확정 뒤 chunk는 캐시된 문맥 + CUDA 그래프 expert. vLLM은 모듈형 기준선 Jev-L에만 쓴다. `harvest/runtime/fused_model.py`)) 어댑터는 R5 열린 문제 7 그대로 — 실체크포인트를 주면 그 메시지로 거부. → **해결(pre-R7 519de26, `pre_r7_fixes.md` 요약 1행·§1, R7 5회차 P2)**: `closed --backend fused`는 `mock_fused` 또는 단계 B 실체크포인트 폴더(stageb.json + adapter/)를 받아 `runtime.fused_model` HF 서버로 돌린다(`harvest/eval/closed.py` 머리 설명 'Backends' 줄, `info["kind"] == "stageb"` 분기). 위 '실모델 없음·거부' 서술은 R6 당시 기록이다.
2. **POOL = SFT 학습 자료**: `e05_sft_pool`의 6편 중 fit 편이 섞여 있다(`meta.episode_data_split`에 기록). 본 E0.5는 학습에 안 쓴 편(POOL eval 편 또는 새 DEV)으로 돌려야 한다 — 명령은 `--seeds`/`--episodes`로 고른다.
3. **labels_v2 정답과 C2'의 S1이 같은 코드 규칙**이라 S1 단독 정답률(0.987–0.999)은 순환이다(결과 문서 meta에 주석). 결과 기반 정답(`--truth outcome:<rule>`)에서는 0.731. **결과 기반 점수식은 아직 사전 등록 규칙으로 확정 전**이라 `time0.33`은 경로 확인용 예시다(라벨러 풀 라벨도 진행 중, 41/120편 완료 시점). → **갱신(정본 §65)**: 점수식은 사전 등록 규칙대로 plan으로 정해졌으나 판별력이 없어(0.025) 거부권 용도로만 쓴다. 결정층 정답은 labels_v2(§54·§65).
4. **지연**: e05 호출 지연(A0 p95 0.85–1.67 s)은 동시 부하(스냅샷 8 × K 3) 아래 값이라 E0 지연이 아니다. d_p95는 `--d-p95`(기본 0.307 = 단계 A 판정 조건 p95)로 받고, §2A.8 재실행 규칙은 E0 최종값으로 판단한다(meta에 명시).
5. **J5 빈 집합**: 적합 반쪽이 거의 전부 정답이면 q̂가 아주 작아 보류 편에서 빈 집합이 생긴다(dir_xy 약 7 %). 순수 split conformal 그대로 두고 `empty_rate`로 보고, 런타임은 빈 집합을 보류로 처리. target은 적합 오답 0이라 T = 0.055(하한 근처)로 뾰족해진다 — 판정 표에서 AUROC "판정 불가"(오답 < 30)로 θ 게이트는 꺼짐.
6. **폐루프 관찰(런타임 쪽, 판정 밖)**: 모의 선택기가 DEV 시드 1에서 30–40 s 안에 descend 단계 잡기 재시도 3회로 실패(시드 0은 16.5 s 성공). R5는 시드 0만 확인했었다 — 스킬 S 잡기 쪽 문제로 보이며 R5 소유자 확인 필요. random 변형 모의 판은 표준과 궤적이 같았다(모의 선택기는 시각 변화를 보지 않고 오라클 상태만 읽으므로 예상된 결과). → **해결(pre-R7 519de26, `pre_r7_fixes.md` §3)**: 원인 = 스킬 S에 쥠 디바운스(0.15 s)가 없었다 → `skills.py` `HOLD_DEBOUNCE_S`, DEV 0–9 P0 모의 10/10 성공.
7. **E-M8c**: `--hb-n` 격자(K2-N)만 있다. K1(T_sub 단계 경계 질의)·K3(Gemini 원문 충실판)·K4(호출 수 맞춘 사건 전용)는 런타임 훅이 없다(R5 열린 문제 1). → **해결(pre-R7 519de26, `pre_r7_fixes.md` §4)**: `runtime/astra_hb.py` K0–K4 + `closed --hb-mode/--hb-budget/--astra scripted`.
8. vLLM은 호출이 모두 캐시에 있어도 뜬다(`e05_sft_pool_outcome` 78 s 낭비) — 필요하면 `--url`로 떠 있는 서버를 쓴다.
9. 모델 지문은 전체 가중치 해시가 아니라 앞뒤 16 MB 표본 해시다(속도). 보정 파일 묶기에는 충분하나 비트 단위 동일성 보장은 아니다.

## 6. 파일

- 새: `harvest/eval/{__init__,splits,common,e05,rd,calib,closed}.py`, `harvest/runtime/{conditions,calibration}.py`, `tests/eval/*`(conftest + 시험 8개), `tools/r6/sync.sh`, 이 문서.
- 수정: `harvest/runtime/m4.py`, `harvest/runtime/core.py`, `harvest/runtime/aiworker.py`(위 4절).
- /data 밖에 쓴 것: 없음(로컬은 D:만, pytest 임시 = `D:/tools/scratch_qdd/pytest_tmp`; 파드는 `/data/harvest/code_r6`, `/data/harvest/out/r6`, `/data/harvest/tmp/r6_pytest`, 캐시 `/data/harvest/cache/*`).
