# E-H2H-T2 — 재부상 뒤 공정 재비교: T1+T4 대 C′ (시드 3개, xyz·D·H 줄기) (무료, 사전 등록)

- **상태: 등록**(학습 전 커밋). 결과는 `docs/stage3/results/h2h.md` 'E-H2H-T2' 절에 쓴다. 통제자 지시(규칙 6 / user-log 143: 재부상 뒤 같은 조건 짝 비교를 한 번 더 한 뒤 결정).
- 이미 본 것(P16): E-H2H-T 대체 판(9/9 SAME), 추가 판 seed 0(`35a90e7`: add_cp OOD-H BETTER, add_t1t4 OOD-H-lift·D WORSE, t1t4 대 cp 3세트 WORSE). E-DIST8의 B-D·B-H·B+px-D·B+px-H(seed 0)는 PT-ND가 학습했고 오프라인 결과 일부를 보드에서 봤다 — 재사용한다.
- 모든 공개 팔은 **추가 방식**(기본 표본 수는 비공개 팔과 같게, 걸음 비례).

## 1. 팔
**xyz(v2) 줄기** — `tools/xemb/proto/h2h_run.sh`(SEED·H2H_STEPS), 평가 = E-H2H-T 9세트:
- `add_t1t4` s1·s2, `add_cp` s1·s2 (seed 0은 추가 판 재사용; 8,521행, 1,066걸음).
- **확인 판** `add_both` s0: 기본 6,521 + C′ 2,000 + T1+T4 1,000(추가 판 묶음에서 앞 1,000행) = 9,521행, **1,191걸음**(= ⌈9,521 × 2 / 16⌉).

**D 줄기**(점 출력 → C′ 행은 형식상 못 씀: T1+T4 효과만) — E-DIST8 도구(`mix_pack.py`, `dist8_eval_seq.sh`, B 수준 평가 세트):
- `d_px` = B+px-D와 같은 파일(B-D 기본 + t1t4_pixel 25 %, 1,088걸음) s1·s2; `d_base` = B-D(816걸음) s1·s2. seed 0은 PT-ND의 B+px-D·B-D 재사용.

**H 줄기**(최종 비교 대상) — 같은 도구:
- `h_px` = B+px-H 파일 s1·s2 (seed 0 = PT-ND B+px-H 재사용).
- `h_cp` = B-H 기본 + C′ 묶음(추가 판과 같은 2,000행) 25 %, 1,088걸음, s0·s1·s2.
- `h_both` = B-H 기본 + C′ 16.7 % + t1t4_pixel 8.3 %, 1,088걸음, s0.

## 2. 판정 (E-PT 5.2 규칙, 스냅숏 짝 부트스트랩)
- 주: **H 줄기 h_px 대 h_cp**, 시드마다 판정 + 세 시드 합동(스냅숏 차를 시드별로 이어 붙인 부트스트랩). 합동 BETTER/WORSE가 결정, 시드 간 방향이 갈리면 'SAME(불안정)'.
- xyz: add_t1t4 대 add_cp 같은 방식(시드 0 포함 3시드). add_both 대 add_cp·add_t1t4(s0).
- D: d_px 대 d_base 3시드 합동 → T1+T4 팩이 D에 이득인가.
- 세트: xyz = E-H2H-T 9세트, D·H = E-DIST8 B 수준 세트(주 OOD 기하 평균 + OOD-H).
- **결정 규칙**: H 합동에서 한쪽이 BETTER → 그쪽을 최종 35B 공개 묶음의 주 팩으로. SAME → 둘 다 넣는다(비율은 h_both·add_both 결과로: both가 둘 중 나은 쪽에 비열등이면 both). WORSE 쪽도 폐기하지 않고 비율만 낮춘다.

## 3. 자원·순서
- e9f3 GPU 4–7(PT-ND와 조율, 35B 시작 전까지). 우선순위: H(h_cp s0 → h_px s1 → h_cp s1 → h_px s2 → h_cp s2 → h_both s0) → D(d_px s1·s2, d_base s1·s2) → xyz(add_both s0, add_t1t4 s1·s2, add_cp s1·s2). 35B 시작 때 끝나지 않은 팔은 '미완'.
- 한계: 공개 팔 계산량 +1/3(추가 방식), 폐루프 없음.
