# Astra API 모델 ID와 첫 호출 (T9 Step 1)

- 확인 2026-09-24T08:41Z: `GET /v1/models`에서 이름에 astra 또는 gpt-6이 들어간 ID = `gpt-6-astra`, `gpt-6-luna`, `gpt-6-sol`. Astra 호출은 `gpt-6-astra`로 고정한다(정본 §28 A6: 응답의 `model` 필드도 `gpt-6-astra`로 확인).
- 스모크 1회(effort low, 입력 20토큰, 출력 10토큰, 추론 토큰 0): HTTP 200, 첫 토큰 2.975 s, 완료 3.288 s. 조사값(Artificial Analysis 약 3 s)과 맞다. 한 번 잰 값이라 설계값으로 쓰지 않는다.
- 비용 절약 결정(user-log 43): E0 §2.3의 첫 토큰(low·high 각 20회)과 같은 입력 반복(입력 3개 × low 50·high 5)은 **스냅샷 풀(T13) 뒤 실제 T_fail 입력으로 한 번만** 잰다. 합성 입력으로 먼저 재면 같은 측정을 두 번 하게 된다.
