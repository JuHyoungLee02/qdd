# E-8BABL2 — ConnectError 오염 전수 감사

작성: 통제자, 10-04. 배경: off_v4(오늘 새 v4 평가)에서 replies.jsonl의 55.3%가 `"error": "ConnectError"`였는데 이를 "모델 필드 누락"으로 잘못 집계했던 사고(`answer_fields.md` 긴급정정 참조)를 발견 — 오늘·과거의 다른 8B 비교들도 같은 오염이 있는지 전수 확인.

## 표 (`x8b2_audit_connerr.py`, replies.jsonl 원자료에서 error 키 직접 집계)

| 문서 | 갈래 | n | conn_err_rate | parse_fail(유효분) |
|---|---|---|---|---|
| tip_overlay.md | ring_s0 | 1,394 | **0.000** | 0.000 |
| tip_overlay.md | ring_s1 | 1,394 | **0.000** | 0.000 |
| tip_overlay.md | ring_s2 | 1,394 | **0.000** | 0.000 |
| tip_overlay.md | tip_s0 | 1,394 | **0.000** | 0.000 |
| tip_overlay.md | tip_s2 | 1,394 | **0.000** | 0.000 |
| gp2_pilot.md 1단계 | a_s0_final | 1,525 | **0.000** | 0.000 |
| gp2_pilot.md 1단계 | a_s2_final | 1,525 | **0.000** | 0.000 |
| gp2_pilot.md 1단계 | b_s0_final | 1,525 | **0.000** | 0.000 |
| gp2_pilot.md 1단계 | b_s2_final | 1,525 | **0.000** | 0.000 |
| gp2_pilot.md 2단계(l9only) | a_s0_final | 1,904 | **0.000** | 0.000 |
| gp2_pilot.md 2단계(l9only) | a_s2_final | 1,904 | **0.000** | 0.000 |
| gp2_pilot.md 2단계(l9only) | b_s0_final | 1,904 | **0.000** | 0.000 |
| gp2_pilot.md 2단계(l9only) | b_s2_final | 1,904 | **0.000** | 0.000 |
| tp1.md(옛 l9test) | off_s0_final | 3,749 | **0.000** | 0.000 |
| tp1.md(옛 l9test) | off_s1_final | 3,749 | **0.000** | 0.000 |
| tp1.md(옛 l9test) | on_s0_final | 3,749 | **0.000** | 0.000 |
| tp1.md(옛 l9test) | onaux_s0_final | 3,749 | **0.000** | 0.000 |
| robot_adapt.md | zeroshot_r1 | 83 | **0.000** | 0.000 |
| robot_adapt.md | r1_50 | 83 | **0.000** | 0.000 |
| robot_adapt.md | zeroshot_r1_gen2 | 228 | **0.000** | 0.000 |
| robot_adapt.md | r1_50_gen2 | 228 | **0.000** | 0.000 |
| robot_adapt.md | r1_200_gen2 | 228 | **0.000** | 0.000 |
| (오늘, v4) answer_fields.md | **off_v4** | 2,336 | **0.553** | 0.000 |

`r1_200`·`g1_50`·`g1_200`·`zeroshot_g1`·`g1_50_gen2`·`g1_200_gen2`·`zeroshot_g1_gen2`: replies.jsonl 없음(TRAIN_FAIL로 평가 전 단계에서 중단됐던 갈래, robot_adapt.md에 이미 그렇게 기록돼 있음 — 감사 대상 아님).

## 판정 (c)

- **TIP_WORSE(TCP 고리 유지) — 유지.** ring/tip 전부 conn_err 0%, 이미 깨끗한 데이터로 판정됐다.
- **GP2 1·2단계(rot_bin_img 유지) — 유지.** 전부 conn_err 0%.
- **TP1(off/on/onaux) 옛 l9test 판정 — 유지.** conn_err 0%.
- **robot_adapt(R1 zero-shot/50/gen2) — 유지.** 있는 갈래 전부 conn_err 0%.
- **오염은 오늘(10-04) off_v4 단 1건뿐**이며 이미 정정 처리됨(`answer_fields.md` 긴급정정 섹션). 같은 날 만든 fieldsB·fmtfix 등 다른 v4 파생 갈래는 TRAIN_FAIL로 아직 평가 자체가 없어 이 감사 대상에 안 들어간다 — 평가가 나오는 대로 conn_err_rate를 먼저 확인하는 걸 표준 절차로 한다.

## 원인(짐작)

off_v4만 유독 55%였던 건 오늘 하루 동시에 여러 v4 평가 vLLM 서버·학습 큐가 겹쳐 돈 시점과 맞물린다(시간상 그 즈음 카드 경쟁이 가장 심했음) — 다른 과거 갈래들은 단독으로 돌았다. 서빙 동시접속 제한(`--max-num-seqs`) 없이 평가 요청을 그대로 던진 것이 유력 원인으로 보이나, 재발 방지용 새 평가 러너(재시도+동시접속 제한)는 별도 작업으로 진행 중.
