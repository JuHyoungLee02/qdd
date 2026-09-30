# E-M35CL — 본 35B 체크포인트 폐루프 확인 (무료, 사전 등록, 보고 전용)

- 작성: CL 에이전트, 2026-09-30 (UTC 시각은 커밋 시각). **결과 전에** 커밋한다. 결과는 `/data/harvest/out/main35_closed/summary.{json,md}`, 나중에 `docs/stage3/results/main35_closed.md`.
- 성격: **보고 전용**. E-MAIN35 판정(`main35_judge.py`, 오프라인 점)에 들어가지 않는다. 판정 규칙이 없다(prereg_main35 §3 '자동 체인 밖, 폐루프' 항목).
- 유료 0원. 이 등록 전에 폐루프 결과를 본 것은 없다(P16). 기존 폐루프 실행기는 가구 장면을 거부하므로(run_closed_x·run_limits) 새 실행기를 쓴다.

## 0. 자체 검사
- **결정**: 학습 중인 main35 체크포인트가 새 물체(OOD-O58)와 L8S 보류 편에서 f35_d보다 폐루프로 나빠 보이는지 — 오프라인 점 판정의 보조 증거, 최적 체크포인트 고르기에 참고.
- **가를 수 있나**: 세트당 58편·약 200편, 한 번씩 실행. 큰 차이(약 15 %p 이상)만 읽는다. 작은 차이는 '구분 안 됨'으로 적는다.
- **멈춤 조건(P18)**: 첫 f35_d 20편에서 오류(error.json) > 10 % 또는 OOD-O58 장면 재현(clutter id 일치) < 90 %이면 멈추고 원인부터 고친다(등록 변경 후 재개).

## 1. 세트
- **OOD-O58**: `/data/harvest/out/l8x_assets/ood_o_eval/eval_list.json`의 58편(13종, 참값 성공만). 수집 명령(render_chain.sh, `plan_ood_o_eval.json`)으로 세계·어지럼 풀을 다시 만든다.
- **L8S 보류**: `/data/harvest/out/main35/data/val_episodes.txt` 222편(main35 학습 제외 3 %; f35_d는 L8S를 본 적 없음). 제외: 여러 단계 과제(X_STEPS), st__/pu__(수집기 행이 필요한 판정), 서랍·고리. 참값 실패 편도 돌리되 **주 지표는 참값 성공 편**. 편마다 그 편을 만든 가장 새 작업 줄(plan5 jobs_l8s4 → l8s3 → l8s2_into → l8s2 → l8s)로 세계를 만든다. 작업을 못 찾은 편은 뺀다(`groups.json` unmapped).
- 명단 고정: `sched.py build` → `/data/harvest/out/main35_closed/groups.json`(묶음·편·제외 사유, digest를 결과에 적는다).

## 2. 조건 (같은 편, 같은 시드)
- `none`(기본) — 먼저 모든 편.
- `light:dim_warm` — 머리 관측마다 조명 변형(limits.LIGHT_LEVELS, prereg_limits와 같은 주입기).
- `head:10:15` — 머리 기울기 +10°·팬 +15°(L8S 학습 지터 범위의 모서리). 시야 검사에 걸리면 절반, 그다음 기본 자세(수집 규칙과 같음). 실제 자세를 편마다 기록한다.

## 3. 모델·실행
- 체크포인트 순서: **f35_d**(`/data/harvest/out/final35/merged_d`) → main35 epoch **0.5 → 1 → 1.5 → 2 → 2.5 → 3**(생기는 대로; 0.5는 판정 대상이 아니지만 가장 먼저 나와 보고용으로 넣는다). 반 에폭 어댑터는 `harvest.teach_35b.merge`로 `/data/harvest/out/main35_closed/merged_ep<e>`에 병합하고, 끝나면 지운다.
- 서버: vLLM BF16(`tools/teach_35b/vllm.sh`, 사고 끔), x3 GPU0(렌더 불가 카드) 한 대가 모든 레인 요청을 배치로 받는다. 한 번에 한 체크포인트.
- 실행기: `harvest.teach_pt.run_closed_l8s` = LimitEpisode(boost1b, d-min, mem_points + fix_loop; c30 f35_d 설정과 같음), 호출 30회·동작 120 s(참값 수집 예산과 같음).
- 레인: 7a2a 렌더 카드 GPU 0·1·3에 카드당 여러 Isaac 레인(CPU 쿼터·nr_throttled를 보고 수 조정, P132). x2 GPU1은 L9 작업이 있어 쓰지 않는다. 편은 mkdir로 나눠 가진다.
- **양보(필수)**: 편 사이마다 `/data/harvest/out/l9/GPU_WANTED`(또는 레인별 WANTED)나 그 카드의 L9 프로세스를 확인 → 지금 편을 끝내고(600 s 넘으면 중단) Isaac을 멈추고 레인 종료, 카드의 마지막 레인이 `<pod>:<gpu> freed <UTC>`를 `/data/harvest/out/l9/GPU_FREED`에 붙인다.

## 4. 지표 (보고만)
- 체크포인트 × 세트 × 조건별 **성공률**(참값 성공 편 기준과 전체), **실패 이유**(fail_stage/end_reason) 분포, 건너뜀·오류 수, 장면 재현(clutter id·지시문 일치) 수.
- f35_d 대비: 같은 편 짝 표(둘 다 성공·main35만·f35_d만·둘 다 실패). 검정·판정 없음.
- 영상: 모든 편 10 fps 머리 | 왼손목 | 오른손목 H.264 → `/data/harvest/videos/main35_closed/<ckpt>/<set>/<cond>/<task>_s<seed>.mp4`, 원본 jpg는 `res/.../frames10/`에 보존, 색인 `index.jsonl`·`index.md`.

## 5. 한계
- 편당 한 번(vLLM 배치 비결정, P46·P110). 조명 변형은 영상 수준. L8S 보류 편은 어지럼 풀을 작업 줄로 재구성하므로 재현 불일치 편이 있을 수 있어 따로 센다.

## 변경 기록
- **변경 1 (2026-09-30 UTC, 실행 중 — 성공률 집계 전, 절차만)**: 사용자 GPU 배분(20:4x KST). 서버 카드 x3 GPU0은 VLA 예약에서 빌린 것이라 `/data/harvest/out/vla/GPU_WANTED`가 생기면 서버를 즉시 내리고 `<pod>:<gpu> freed <UTC>`를 `/data/harvest/out/vla/GPU_FREED`에 붙인다. 그 파일이 없어지고 카드가 비면 다시 띄운다. 서버가 없어진 사이의 편은 모델 실패가 아니므로 실행기가 전송·서버 오류(연결·시간 초과·http 5xx·404)를 세어 한 번이라도 있으면 그 편을 `*.srv_err.<시각>`으로 옮기고 나중에 다시 돌린다. 7a2a GPU2(평가 카드)는 쓰지 않는다. 세트·조건·지표는 그대로.
