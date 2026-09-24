# GPT-6 Sol·Luna 사전 시험 (Jev 대체 후보 A, user-log 46)

측정 2026-09-24T09:46Z, 한국 로컬 PC, OpenAI Responses API, `reasoning.effort = none`, 짧은 텍스트 3지선다(A=up/B=down/C=none), `max_output_tokens 16`, `top_logprobs 5`, `include = [message.output_text.logprobs]`. 호출 총 10회.

| 모델 | 답 | 보기 logprob | 지연(연결 재사용 4회) |
|---|---|---|---|
| gpt-6-luna | B | B −0.275, C −1.438 | 1.04 / 1.17 / 1.12 / 2.91 s (중앙 1.17 s) |
| gpt-6-sol | B | B 0.0 (한쪽에 몰림) | 1.31 / 1.64 / 1.05 / 1.57 s |

- 첫 호출(새 연결)은 두 모델 모두 약 2.4 s.
- 해석: 보기 확률은 받을 수 있다(Luna는 분포가 퍼져 있음, Sol은 확신 1.0). 지연은 E0 판정 3 기준 (d) 1–2 s 구간이고 가끔 3 s — 0.33 s 주기의 결정에는 느리다. 표본 4회라 설계값이 아니다.
