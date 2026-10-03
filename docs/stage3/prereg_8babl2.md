# E-8BABL2 — 논문용 검증 2종: 7,500편 재판정(A) · 새 로봇 적응(B) (사전 등록, 진행 중 갱신)

- 작성: 통제자(Sonnet 에이전트), 10-03. E-TP1/E-GP2/8Babl 파이프라인(code_8babl_r1, x8_build.py, gp2_worker.sh 류, cfd6e676 리포트 수정판) 재사용. juhyoung-0(24코어, CPU 빌드 전용) + fe08 GPU1·4·6/7a2a GPU2(사용자 승인)/x2 GPU0/x3 GPU0(통제자 범위).
- 금지 그대로: 양산 레인·렌더 카드 안 건드림, juhyoung-0은 CPU만, heredoc 파이썬 금지(전부 .py 파일), 실행 중 스크립트 미수정.

## 규모 변경 기록 (사용자 결정, 10-03 저녁 KST)
- 처음 지시: A는 pilot1/pilotF/pilotG에서 7,500편(실제 가용 6,344편, pilotG 거의 비어 shortfall 기록) 재판정.
- **변경(사용자)**: "검증용은 5분의 1 규모면 충분" → A 학습 세트 **약 1,500편**(실제 1,282편: r1pro gen2 풀이 157편뿐이라 그만큼 shortfall), eval 300편, **전부 gen2**(`/data/harvest/l9v2/gen2/<robot>/collect`, spec L9v2-general, 4로봇: ffw_sg2·franka_mast·r1pro·g1)에서 로봇당 고르게(375/75 목표, round-robin by task definition). gen2 third-person(external_cams) 존재 확인됨(표본 300편 중 로봇별 18~31%) → TP1 on/onaux도 gen2로 그대로 진행(옛 데이터로 축소할 필요 없음).
- 이미 돌고 있던 6,344편 학습(fe08 GPU1·4·6, off_s0/on_s0/on_s1)은 **새 1,500편 큐가 준비될 때까지 그대로 둔다**(카드 비는 시간 최소화). 준비되면 중단+교체(메인이 직접, 통제자가 한 줄 명령 전달).
- GP2(a/b) "다음 갈래부터"도 gen2 우선 + 모자란 만큼만 pilot으로 채움(비중은 결과에 기록).
- tip_overlay(손끝 표시) vs TCP 고리 비교: **건너뜀** — `harvest/l9/build9.py`·`harvest/astra_solo/overlay.py`에 그런 옵션이 없음(grep 확인, 없음). 오버레이는 시뮬 수집 시점에 베이크되어 재생기 수정 없이는 불가(8Babl exp2와 같은 이유).

## A 데이터 (gen2, 1/5 규모)
- 선택: `/data/x8_cpu7500/tp1_g2/episodes_g2.json`(x8b2_select_gen2_4robot.py) — train 1,282(ffw_sg2 375·franka_mast 375·r1pro 157·g1 375), eval 300(로봇당 75).
- 빌드: `x8b2_safe_build.py`(편 단위 try/except 스킵 — build9.build 자체는 그대로, gen2 spec(L9v2-general)이 TP1 strict spec-gate merge()의 전제와 달라 원본 tp1_build.py/gp2_build.py의 일괄 처리 대신 편 단위 버전을 씀, 스킵 수는 `*.skipped.json`에 기록).
  - TP1: 한 번만(slots=1,third_person=1)으로 짓고 ego/ego+3인칭으로 나눠 off/on 바이트를 맞춘다(원본 tp1_build.py merge()와 같은 발상). onaux는 tp1_aux.py(원본) --frac 0.15.
  - GP2: slots=0,third_person=0,grasp_format=1 한 번 짓고 원본 `gp2_build.py arms`로 a/b 분기.
- (작성 시점) 행 빌드 진행 중, juhyoung-0 CPU 공유(기존 gp2v2 20파트 + B-gen2 6개 작업과 동시), 완료 여부는 `/data/x8_cpu7500/chain.log`·`tp1_g2/`·`gp2_g2/`에서 확인.

## B 데이터 (R1/G1 적응, gen2)
- 선택: `/data/x8_cpu7500/r1g1_gen2/r1g1_gen2_pool.json`(x8b2_select_r1g1_gen2.py, eval 하한 60) — R1: train_pool 168 · eval 60(60개 정의 고르게). G1: train_pool 579 · eval 60.
- 50/200편 서브셋(r1_200은 168로 cap, g1_200은 200 그대로) + eval은 `x8b2_train_safe.py`/`x8b2_eval_safe.py`(편 단위 스킵)로 짓는다. 기준 모델은 기존 `/data/harvest/out/tp1/merged/off_s0_final`(AIW+Franka, 재사용, 새 학습 없음) — zero-shot은 그대로 평가, 50/200은 이 체크포인트에서 이어 학습.
- 배치: x2 GPU0 = r1_50_gen2→r1_200_gen2→(여유 시 옛 pilot r1_200), x3 GPU0 = g1_50_gen2→g1_200_gen2→(여유 시 옛 pilot g1_200), 7a2a GPU2 = zeroshot_r1_gen2→zeroshot_g1_gen2→(여유 시 2번째 시드).
- 옛 pilot 기반 R1/G1 held-out(`r1g1/eval_r1.jsonl`·`eval_g1.jsonl`)은 원래 보류분(81/103편)이 전부 구형식이라 build9가 처리 못 해(KeyError 'gt' 등) 편 단위 스킵으로 대체 추출(r1: train_pool 잔여 43편 중 11편 성공/83행, g1: 103편 중 53편 성공/107행) — gen2 쪽이 준비되면 이게 주 결과, 옛 pilot 결과는 참고용.

## 판정
- TP1/GP2: 기존 사전등록(`prereg_tp1.md`/`prereg_gp2.md`) 규칙 그대로(바꾸지 않음), "1,500편 재판정" 절로 `docs/stage3/results/tp1.md`·`gp2_pilot.md`에 추가.
- B(R1/G1): zero-shot 대비 50편·200편 추가 학습의 그 로봇 held-out 개선(점 px·접근·rot·skill·arm 정확도), 표본이 작으면(특히 옛 pilot r1 eval 83행/11편) '표본 한계' 표시.
