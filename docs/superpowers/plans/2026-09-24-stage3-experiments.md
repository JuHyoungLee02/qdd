# 단계 3 첫 실험 구현 계획 (0주 준비 → E0 · E0.5 · E3-ST · Inspect Robots P0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

작성 2026-09-24 UTC, Claude(메인 세션). 사용자 지시(user-log 42): "3단계 실험 계획을 아주 철저하게 짠 다음에 실행에 들어가자 주기적으로 방향성이 맞는지에 대한 검사를 계속 해줘야 돼 틀리면은 그냥 처음부터 돌아가도 돼"

> 개정 2026-09-25 01:48 UTC (R7 sweep6, 정본 §44·§58, user-log 46): Jev는 쓸 수 없다 — 이 계획의 Jev 실호출 과제(T5 Step 6·T8 E0·T15 E0.5 실행, 이후 E1·E2a)는 동결됐고(`docs/stage3/direction-log.md` 09:44), 빠른 선택기는 Jev-L(§44·§50) → 융합 모델(§58)로 바뀌었다. 지금 계획은 `2026-09-25-e2e-ready.md`. 아래 Jev 서술은 당시 기록이다.
> 개정 user-log 44(정본 §43): 카메라는 AI Worker 기본 그대로 — T11 Step 2 교체.

**Goal:** 사전 등록된 첫 실험 E0(Jev 지연)·E0.5(오프라인 표 재생)·E3-ST(오프라인 스테레오 안정성)를 실제로 돌려 판정을 내고, 1차 평가 하네스 Inspect Robots를 P0(설치·스모크)까지 세운다. 매 관문마다 방향성 검사를 통과해야 다음으로 간다.

**Architecture:** 순수 파이썬 패키지 `harvest/`(술어·직렬화·Jev/Astra 클라이언트·부하 발생기·분석)는 로컬(D:)과 파드에서 같은 코드로 돈다. 시뮬 의존 부분(`harvest/sim/`: 장면·오라클 플래너·스냅샷·라벨러)은 파드 `juhyoung-native-7a2a`의 Isaac Sim 5.1 chroot에서만 돈다. 모든 판정은 `harvest/analysis/`의 코드로 계산하고, 판정 절 해시를 실행 기록 첫 줄에 남긴다.

**Tech Stack:** Python 3.11+(로컬 3.13, 파드 Isaac 파이썬 3.11), numpy, httpx(HTTP/1.1 keep-alive), pytest, Isaac Sim 5.1.0 / Isaac Lab 2.3.0, cyclo_lab(ROBOTIS), Stereolabs ZED Isaac Sim 확장, Inspect Robots v0.59.0(커밋 `7e506e3`), Fast-FoundationStereo, SAM 3.1, HF `datasets`/LeRobot.

**Spec:** `docs/design/E-first-experiments.md`(실험 절차 정본) + `docs/design/00-interfaces.md` §1–§42(뒤 절 우선) + `docs/design/M1-state-representation.md` §4.0(술어 등록부) + `docs/design/D23-inspect-robots-integration.md`(P0).

## Global Constraints

- `main` 금지. 모든 커밋은 `dev`에만, 푸시는 `git -c safe.directory=D:/qdd push -q origin dev`.
- 작업 드라이브는 D만. 로컬 임시 파일 `D:\tools\scratch_qdd`, pip 설치 `--target D:/tools/pylib`, pytest는 `-p no:cacheprovider`, matplotlib `MPLCONFIGDIR=D:/tools/mplcache`. C 드라이브에 쓰지 않는다.
- 비밀값(TypeSafe·OpenAI 키)은 저장소·로그·커밋에 절대 넣지 않는다. 로컬은 사용자가 알려 준 파일 경로, 파드는 `/data/.typesafe_token`·`/data/.openai_token`(stdin으로 1회 전달). 요청 기록에는 헤더를 저장하지 않는다.
- Jev: `model = "jev-1.13.0"` 고정(별칭 금지), 엔드포인트 `POST https://api.typesafe.ai/v1/systemone`, SDK 재시도 끔(`max_retries=0`), 모든 상태·질문 영어.
- Astra: effort 기본 `low`, 실험은 `low`와 `high` 둘 다(정본 §26). 단일 실행 비교로 결론 내지 않는다(정본 §28).
- 판정 기준은 `E-first-experiments.md`의 사전 등록 그대로. 실행 뒤 바꾸려면 "사후 변경" 절에 이유와 원 기준 결과를 같이 적는다.
- 시드 세트: DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119. **TEST·TEST-P5는 이 계획에서 생성·열람 금지.** 보류 섭동 P3·P4는 이 계획에서 쓰지 않는다.
- 파드는 `juhyoung-native-7a2a`(노드 h200-03-w-7a2a) 하나. 파드를 삭제·반납하지 않는다. 렌더 작업은 GPU 0·1·3만.
- 시각은 `date -u`로 찍는다(추측 금지). 사용자 보고는 한국어로 짧게.
- 신뢰도 규칙(user-log 14): "신뢰도 낮은 논문과 깃 저장소는 최대한 쓰지 않는다. 쓰느니만 못하다." / "신뢰도가 무조건 있어야 하고, 스타도 어느 정도 있어야 하고, 논문도 좋아요(반응)를 많이 받은 것이어야 한다." 새 외부 도구를 들일 때 적용.
- 매 과제 끝에 `docs/draft-log.md`에 한 줄(시각·한 일·교훈).

## Review Focus

1. **Jev 429·5xx·타임아웃**: 지연 표본에서 빼지 않고 실패로 세며 p95에 +∞로 들어가야 한다 → Task 7 `test_censored_p95_counts_failures_as_inf`.
2. **응답 `model`이 `jev-1.13.0`이 아님**: 그 세션 전체가 분리 표시돼야 한다 → Task 5 `test_model_mismatch_flags_session`.
3. **보기 순서·이름을 바꾼 판(A1–A4)의 답**: 반드시 `option_key`(표준 뜻)로 되돌려 세야 한다. 이름으로 세면 flip이 가짜로 부풀어 오른다 → Task 4 `test_answer_maps_back_to_option_key_for_all_variants`.
4. **히스테리시스 경계에서의 술어 깜빡임**: 5.0–6.0 cm 사이를 오가는 거리에서 `near`가 이전 값을 유지해야 한다 → Task 2 `test_near_hysteresis_holds_between_bands`.
5. **스냅샷 복원 뒤 물리 교란**: 상태를 쓴 직후 한 걸음에서 물체가 움직이면 라벨이 오염된다(과거 Task C 교훈: 진단 쓰기가 컵을 흔들었다) → Task 13 `restore_drift_check`(복원 후 0.5 s 무명령 정착 편차 ≤ 1 mm).

---

## 방향성 검사 (사용자 지시의 핵심)

### 관문(DC)과 되돌아가기 규칙

| 관문 | 언제 | 통과 조건 | 실패 시 |
|---|---|---|---|
| **DC0** 계획 | 이 계획 커밋 직후, 실행 전 | 아래 "방향 질문 6개" 모두 예. 사용자가 계획을 봤음 | 계획 재작성 |
| **DC1** 인터페이스 | Task 1–5 끝 | 직렬화·JevCall·option_key가 정본 §2·§27·§28과 문자 단위로 맞음(`tests/test_canon_conformance.py`) | Task 1부터 다시 |
| **DC2** E0 첫 세션 | Task 8 첫 파드 세션 뒤 | E0 판정 3이 (a)–(d). 운영점 실패율 ≤ 2% | **(e)면 멈추고 사용자 논의**(E-first §2.7-3(e)). 다른 실패는 Task 6부터 |
| **DC3** 하네스 | Task 10 끝 | Inspect Robots가 Isaac 5.1 chroot에서 스모크 3모드 통과, RTF 기록됨 | 하네스 판단 재검토 → 사용자 보고(1차 평가는 사용자 결정 §41이라 Claude가 바꾸지 않는다) |
| **DC4** 장면·풀 | Task 13 끝 | 오라클 플래너 DEV 성공률 ≥ 90%, 복원 정착 편차 ≤ 1 mm, 풀 1,200 스냅샷 | Task 11부터 다시 |
| **DC5** E0.5 판정 | Task 15 끝 | 판정 1–10 계산 완료, 결과를 정본 절로 기록 | 판정 1이면 M4 주장 좁힘 → 논문·정본 수정 후 다음 계획 |
| **DC6** E3-ST | Task 16 끝 | 안정성 수치 산출. 탐색 측정이라 문턱 없음 | 데이터 결함이면 E3-ST 보류 표시 |

- 관문을 통과하면 git 태그 `stage3-dcN`을 단다(dev 커밋에만, 푸시 `--tags` 아님: `git push origin stage3-dcN`).
- **"처음부터 돌아가기"(user-log 42)**: 방향이 틀렸다고 판정되면(버그가 아니라 전제가 틀림) 마지막으로 통과한 태그로 돌아가 **그 뒤 계획을 다시 쓴다**. 판정이 전제 자체(예: Jev 초당 3회 루프, 겹침 합의의 정보)를 뒤집으면 DC0으로 돌아가 이 계획 전체를 다시 쓴다. 이미 잰 측정 자료는 버리지 않고 `data/` 아래에 보존한다(자료는 틀리지 않았다).
- 되돌아갈 때마다 `docs/stage3/direction-log.md`에 날짜·관문·틀린 전제·근거·돌아간 지점을 적는다.

### 방향 질문 6개 (모든 관문과 30분 루프 점검에서 같은 질문)

1. 지금 하는 일이 user-log 항목이나 정본 절 번호 하나로 설명되나? (못 하면 멈춤)
2. 사용자 핵심 주장 — "느린 API 계획기(Astra) + 빠른 typed 결정(Jev)으로 멈추지 않는 로봇 실행", 새로움은 M4와 평가뿐(CLAUDE.md) — 을 재는 쪽으로 가고 있나?
3. 사전 등록 판정 절의 해시가 첫 실행 기록 해시와 같은가? (`tools/prereg_hash.py --check`)
4. 규칙 위반이 없나: main, C 드라이브, 비밀값 커밋, TEST 시드 열람, 신뢰도 규칙.
5. 최근 결과 중 계획의 전제를 흔드는 것이 있나? (예: p95 > 2 s, flip ≈ 0, 장면 RTF ≪ 1) 있으면 해당 관문 실패로 처리.
6. 마감(CVPR 2026-11-16 AoE)까지 남은 주와 계획상 남은 공수가 맞나? 모자라면 표본이 아니라 범위를 줄일 안을 사용자에게 올린다.

- **주기**: 세션 cron 30분마다 질문 1·4·5를 빠르게, 관문마다 6개 전부. 결과는 `docs/stage3/direction-log.md`에 한 줄.

---

## File Structure

```
harvest/                      # 새 파이썬 패키지 (저장소 루트)
  __init__.py
  config.py                   # 정본 §7 설정 표 값 (T_c, near 띠, h_lift, tilt_max ...)
  predicates.py               # M1 §4.0 T1 술어 계산기 (numpy, 히스테리시스)
  serialize.py                # 최소 직렬화(후보 A 모양) + J2 정규화
  qid.py                      # question_id@vN 해시 (J1)
  options.py                  # 보기 이름 규칙 R1–R6, 판 A0–A4, option_key 되돌림
  jevcall.py                  # JevCall 요청 조립 (E §1.2)
  clients/
    __init__.py
    jev.py                    # httpx 클라이언트, 시각 필드, 원문 저장, 재시도 없음
    astra.py                  # OpenAI Responses 스트리밍, 첫 토큰 시각
  record.py                   # JSONL 기록기 (E §1.6 필드)
  load/
    __init__.py
    closed_loop.py            # in-flight N 유지 부하
    open_loop.py              # T_c 주기 송신, N_cap 건너뜀
    session.py                # E0 세션 1회 (curl 분해 + 부하 + 결정성 20개)
  analysis/
    __init__.py
    latency.py                # 검열 p95, 판정 1–7
    replay.py                 # E0.5 규칙(newest/LA-2/C2''/C2') + 판정 1–10
    stats.py                  # 에피소드 군집 부트스트랩, Holm
  canary.py                   # 매일 카나리 (E §1.8)
  sim/                        # 파드 전용 (Isaac)
    __init__.py
    scene.py                  # AI Worker 한 팔 + ZED_M + 머그/트레이
    oracle_state.py           # 시뮬 참 자세 → predicates 입력
    planner.py                # 오라클 스크립트 플래너 + 섭동 P0–P2
    snapshot.py               # 0.33 s 연속 스냅샷, 전체 상태 저장·복원
    labeler.py                # 결과 기반 라벨러
  stereo/                     # E3-ST
    __init__.py
    data.py                   # ROBOTIS HF 에피소드 → 좌우 프레임
    pipeline.py               # Fast-FS → SAM 3.1 → 3D 중심 → 술어
tests/
  test_config.py test_predicates.py test_serialize.py test_qid.py test_options.py
  test_jevcall.py test_jev_client.py test_record.py test_load.py test_latency.py
  test_replay.py test_stats.py test_canary.py test_canon_conformance.py
  sim/test_snapshot_logic.py   # 순수 로직만(Isaac 없이)
tools/
  prereg_hash.py              # 판정 절 SHA-256 기록·검사
  pod_sync.sh                 # harvest/를 파드 /data/juhyoung_qdd/ 로 복사 (exec cat 방식)
docs/stage3/
  direction-log.md            # 방향성 검사 기록
  prereg.json                 # 판정 절 해시
data/                         # .gitignore — 원자료는 파드 /data/juhyoung_qdd/data 에
```

- 파드 작업 폴더: `/data/juhyoung_qdd/`(코드 사본 + `data/` 원자료). 원자료는 git에 넣지 않고 요약 CSV·그림만 `docs/stage3/results/`에 커밋.

---

### Task 0: 방향성 검사 도구와 사전 등록 해시

**Files:**
- Create: `tools/prereg_hash.py`, `docs/stage3/direction-log.md`, `docs/stage3/prereg.json`, `tests/test_prereg.py`, `pytest.ini`, `.gitignore` 항목 `data/`

**Interfaces:**
- Produces: `section_hash(md_text: str, heading: str) -> str`(해당 `###` 절 본문 SHA-256, 줄 끝 LF로 정규화), CLI `python tools/prereg_hash.py --write | --check`

- [ ] **Step 1: 실패하는 테스트**

```python
# tests/test_prereg.py
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("ph", pathlib.Path(__file__).parents[1] / "tools/prereg_hash.py")
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

DOC = "## 2\n### 2.7 판정 기준 (사전 등록)\nA\r\nB\n### 2.8 다음\nC\n"

def test_hash_ignores_crlf_and_stops_at_next_heading():
    h1 = ph.section_hash(DOC, "### 2.7")
    h2 = ph.section_hash(DOC.replace("\r\n", "\n"), "### 2.7")
    assert h1 == h2
    assert h1 != ph.section_hash(DOC.replace("B", "B2"), "### 2.7")
    assert h1 == ph.section_hash(DOC.replace("C", "C2"), "### 2.7")

def test_missing_heading_raises():
    import pytest
    with pytest.raises(KeyError):
        ph.section_hash(DOC, "### 9.9")
```

- [ ] **Step 2: 실패 확인** — `cd D:/qdd && python -m pytest -p no:cacheprovider tests/test_prereg.py -q` → FAIL(파일 없음)

- [ ] **Step 3: 구현**

```python
# tools/prereg_hash.py
"""Pre-registration hashes for E-first judgment sections (E §1.7)."""
import argparse, hashlib, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/design/E-first-experiments.md"
OUT = ROOT / "docs/stage3/prereg.json"
SECTIONS = ["### 2.7", "### 2A.6", "### 3.7", "### 4.8", "### 5.6"]

def section_hash(md_text: str, heading: str) -> str:
    lines = md_text.replace("\r\n", "\n").split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith(heading)), None)
    if start is None:
        raise KeyError(heading)
    body = []
    for l in lines[start + 1:]:
        if l.startswith("## ") or l.startswith("### "):
            break
        body.append(l)
    return hashlib.sha256("\n".join(body).strip().encode("utf-8")).hexdigest()

def current() -> dict:
    text = DOC.read_text(encoding="utf-8")
    return {s: section_hash(text, s) for s in SECTIONS}

def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.write:
        now = subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%MZ"], capture_output=True, text=True).stdout.strip()
        OUT.write_text(json.dumps({"written_utc": now, "hashes": current()}, indent=1), encoding="utf-8")
        print("written", now); return 0
    saved = json.loads(OUT.read_text(encoding="utf-8"))["hashes"]
    bad = [s for s, h in current().items() if saved.get(s) != h]
    print("OK" if not bad else f"CHANGED {bad}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
addopts = -p no:cacheprovider -q
```

`docs/stage3/direction-log.md` 첫 줄: `# 단계 3 방향성 검사 기록 (user-log 42)` + 표 머리 `| 시각 UTC | 관문/루프 | 질문 1–6 결과 | 조치 |`.

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/test_prereg.py` → 2 passed. 그다음 `python tools/prereg_hash.py --write` → `written <시각>`, `--check` → `OK`.
- [ ] **Step 5: 커밋** — `git add tools/prereg_hash.py tests/test_prereg.py pytest.ini .gitignore docs/stage3/` → `stage3 T0: pre-registration hashes and direction log`

---

### Task 1: 패키지 뼈대와 설정 표

**Files:**
- Create: `harvest/__init__.py`, `harvest/config.py`, `tests/test_config.py`
- 참고: `docs/design/00-interfaces.md` §7(설정 표)

**Interfaces:**
- Produces: `harvest.config.CFG`(frozen dataclass): `T_c=0.33`, `near_in_m=0.05`, `near_out_m=0.06`, `h_lift_m=0.03`, `tilt_max_deg=30.0`, `success_hold_s=1.0`, `episode_limit_s=60.0`, `snapshot_dt_s=0.33`, `sim_dt=0.01`, `decimation=5`, `jev_model="jev-1.13.0"`, `jev_url="https://api.typesafe.ai/v1/systemone"`, `timeout_s=2.0`.

- [ ] **Step 1: 실패 테스트**

```python
# tests/test_config.py
from harvest.config import CFG
import dataclasses, pytest

def test_canonical_values():
    assert CFG.T_c == 0.33 and CFG.near_in_m == 0.05 and CFG.near_out_m == 0.06
    assert CFG.jev_model == "jev-1.13.0" and "latest" not in CFG.jev_model
    assert CFG.near_out_m > CFG.near_in_m

def test_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        CFG.T_c = 0.5
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/test_config.py` → ModuleNotFoundError
- [ ] **Step 3: 구현** — Step 1 이전에 §7 표의 각 값을 `00-interfaces.md`에서 grep으로 확인(`grep -n "near\|h_lift\|tilt_max\|T_c" docs/design/00-interfaces.md | head -40`). 값이 다르면 **정본 값이 이긴다**: 테스트와 구현을 정본 값으로 고친다.

```python
# harvest/config.py
"""Canonical setting table (00-interfaces §7). Change only via canon."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    T_c: float = 0.33
    near_in_m: float = 0.05
    near_out_m: float = 0.06
    h_lift_m: float = 0.03
    tilt_max_deg: float = 30.0
    success_hold_s: float = 1.0
    episode_limit_s: float = 60.0
    snapshot_dt_s: float = 0.33
    sim_dt: float = 0.01
    decimation: int = 5
    jev_model: str = "jev-1.13.0"
    jev_url: str = "https://api.typesafe.ai/v1/systemone"
    timeout_s: float = 2.0

CFG = Config()
```

`harvest/__init__.py`: `__version__ = "0.1.0"`

- [ ] **Step 4: 통과 확인** — 2 passed
- [ ] **Step 5: 커밋** — `stage3 T1: harvest package and canonical config`

---

### Task 2: T1 술어 계산기 (히스테리시스 포함)

**Files:**
- Create: `harvest/predicates.py`, `tests/test_predicates.py`

**Interfaces:**
- Consumes: `CFG`
- Produces:
  - `@dataclass Obj(id: str, pos: np.ndarray(3), quat_wxyz: np.ndarray(4), half_extents: np.ndarray(3))`
  - `@dataclass Gripper(width_m: float, effort: float, pos: np.ndarray(3))`
  - `class PredicateState` — 이전 값을 기억(히스테리시스), `update(objs: dict[str,Obj], grip: Gripper, contacts: set[frozenset[str]], support: dict[str,str]) -> dict[str, bool|None]`, 키 형식 `"near(o3,o5)"`, `"on(o3,o5)"`, `"holding(o3)"`, `"upright(o3)"`, `"lifted(o3)"`, `"above(o3,o5)"`, `"in_contact(o3,o5)"`, `"gripper_open"`
  - 값 `None` = unknown(가려짐·ID 불확실 표시가 붙은 물체)

- [ ] **Step 1: 실패 테스트**

```python
# tests/test_predicates.py
import numpy as np
from harvest.predicates import Obj, Gripper, PredicateState

I = np.array([1.0, 0, 0, 0])
def obj(i, x, y, z, h=0.05): return Obj(i, np.array([x, y, z]), I.copy(), np.array([h, h, h]))
G_OPEN = Gripper(width_m=0.10, effort=0.0, pos=np.array([0, 0, 0.5]))

def run(ps, o3, o5, contacts=frozenset(), grip=G_OPEN, support=None):
    return ps.update({"o3": o3, "o5": o5}, grip, set(contacts), support or {"o3": "table", "o5": "table"})

def test_near_hysteresis_holds_between_bands():
    ps = PredicateState()
    assert run(ps, obj("o3", 0.070, 0, 0), obj("o5", 0, 0, 0))["near(o3,o5)"] is False
    assert run(ps, obj("o3", 0.055, 0, 0), obj("o5", 0, 0, 0))["near(o3,o5)"] is False   # in band, stays
    assert run(ps, obj("o3", 0.049, 0, 0), obj("o5", 0, 0, 0))["near(o3,o5)"] is True    # enters < 5 cm
    assert run(ps, obj("o3", 0.058, 0, 0), obj("o5", 0, 0, 0))["near(o3,o5)"] is True    # in band, stays
    assert run(ps, obj("o3", 0.061, 0, 0), obj("o5", 0, 0, 0))["near(o3,o5)"] is False   # exits > 6 cm

def test_on_requires_contact_and_support_above():
    ps = PredicateState()
    o5 = obj("o5", 0, 0, 0.02, h=0.02)
    o3 = obj("o3", 0, 0, 0.02 + 0.02 + 0.05)
    r = run(ps, o3, o5, contacts={frozenset({"o3", "o5"})}, support={"o3": "o5", "o5": "table"})
    assert r["on(o3,o5)"] is True
    r = run(ps, o3, o5, contacts=set(), support={"o3": "o5", "o5": "table"})
    assert r["on(o3,o5)"] is False

def test_upright_uses_tilt_max():
    ps = PredicateState()
    ang = np.deg2rad(40)
    tilted = Obj("o3", np.zeros(3), np.array([np.cos(ang/2), np.sin(ang/2), 0, 0]), np.full(3, .05))
    assert run(ps, tilted, obj("o5", 1, 1, 0))["upright(o3)"] is False
    assert run(ps, obj("o3", 0, 0, 0), obj("o5", 1, 1, 0))["upright(o3)"] is True

def test_holding_needs_closed_width_and_effort_and_contact():
    ps = PredicateState()
    g = Gripper(width_m=0.04, effort=5.0, pos=np.array([0, 0, 0.1]))
    r = run(ps, obj("o3", 0, 0, 0.1), obj("o5", 1, 1, 0), contacts={frozenset({"gripper", "o3"})}, grip=g)
    assert r["holding(o3)"] is True
    r = run(ps, obj("o3", 0, 0, 0.1), obj("o5", 1, 1, 0), contacts=set(), grip=g)
    assert r["holding(o3)"] is False

def test_unknown_propagates():
    ps = PredicateState()
    o3 = obj("o3", 0, 0, 0); o3.occluded = True
    assert run(ps, o3, obj("o5", 0.01, 0, 0))["near(o3,o5)"] is None
```

- [ ] **Step 2: 실패 확인** — ImportError
- [ ] **Step 3: 구현**

```python
# harvest/predicates.py
"""T1 predicate calculator (M1 §4.0 registry), with hysteresis bands (M1 §4 line 120)."""
from __future__ import annotations
from dataclasses import dataclass, field
import itertools
import numpy as np
from .config import CFG

GRIP_OPEN_M = 0.08      # [가정] RH-P12-RN 0–107.6 mm; open threshold, tune in sim
GRIP_EFFORT_MIN = 1.0   # [가정] effort units from sim joint effort

@dataclass
class Obj:
    id: str
    pos: np.ndarray
    quat_wxyz: np.ndarray
    half_extents: np.ndarray
    occluded: bool = False
    id_uncertain: bool = False

@dataclass
class Gripper:
    width_m: float
    effort: float
    pos: np.ndarray

def _tilt_deg(q: np.ndarray) -> float:
    w, x, y, z = q
    # body z-axis in world: third column of rotation matrix
    zx = 2 * (x * z + w * y); zy = 2 * (y * z - w * x); zz = 1 - 2 * (x * x + y * y)
    return float(np.degrees(np.arccos(np.clip(zz / np.linalg.norm([zx, zy, zz]), -1, 1))))

@dataclass
class PredicateState:
    _near: dict = field(default_factory=dict)

    def update(self, objs, grip, contacts, support):
        out: dict[str, bool | None] = {}
        unknown = {k for k, o in objs.items() if o.occluded or o.id_uncertain}
        for a, b in itertools.permutations(objs, 2):
            A, B = objs[a], objs[b]
            if a in unknown or b in unknown:
                for p in ("near", "on", "above", "in_contact"):
                    out[f"{p}({a},{b})"] = None
                continue
            d = float(np.linalg.norm(A.pos - B.pos))
            key = (a, b)
            prev = self._near.get(key, False)
            now = d < CFG.near_in_m if not prev else d <= CFG.near_out_m
            self._near[key] = now
            out[f"near({a},{b})"] = now
            touching = frozenset({a, b}) in contacts
            out[f"in_contact({a},{b})"] = touching
            above_xy = (abs(A.pos[0] - B.pos[0]) <= B.half_extents[0]
                        and abs(A.pos[1] - B.pos[1]) <= B.half_extents[1])
            higher = A.pos[2] > B.pos[2]
            out[f"above({a},{b})"] = bool(above_xy and higher and not touching)
            out[f"on({a},{b})"] = bool(touching and support.get(a) == b and higher)
        for a, A in objs.items():
            if a in unknown:
                for p in ("holding", "upright", "lifted"):
                    out[f"{p}({a})"] = None
                continue
            out[f"upright({a})"] = _tilt_deg(A.quat_wxyz) <= CFG.tilt_max_deg
            gripped = frozenset({"gripper", a}) in contacts
            out[f"holding({a})"] = bool(gripped and grip.width_m < GRIP_OPEN_M and grip.effort >= GRIP_EFFORT_MIN)
            out[f"lifted({a})"] = bool(support.get(a) is None and A.pos[2] - A.half_extents[2] >= CFG.h_lift_m)
        out["gripper_open"] = grip.width_m >= GRIP_OPEN_M
        return out
```

주의: `lifted`의 기준면 높이는 Task 12에서 시뮬 탁상 높이를 원점으로 두는 좌표로 맞춘다(탁상 윗면 z = 0). 이 규약을 `oracle_state.py` 머리 주석에 적는다.

- [ ] **Step 4: 통과 확인** — 5 passed
- [ ] **Step 5: 커밋** — `stage3 T2: T1 predicate calculator with hysteresis`

---

### Task 3: 최소 직렬화 · J2 정규화 · question_id@vN

**Files:**
- Create: `harvest/serialize.py`, `harvest/qid.py`, `tests/test_serialize.py`, `tests/test_qid.py`

**Interfaces:**
- Consumes: 술어 dict(Task 2)
- Produces:
  - `serialize_state(t_state: str, contract: str, stage: dict, robot_line: str, objects: list[tuple[str,str,str,str]], facts: dict[str,bool|None], named: set[str], changes: list[tuple[float,str,str,str]]) -> str` — E §1.2 예와 같은 줄 형식. `facts`는 참인 것 + `named`(계약이 이름 붙인 술어)는 거짓도, 이름순 정렬. `changes`는 최근 3 s·최대 8개, 시각 오름차순. `None`은 `unknown`.
  - `canonicalize(text: str) -> str` — J2: 줄 끝 LF, 줄 끝 공백 제거, 연속 공백 1칸(선행 들여쓰기 제외), NFC.
  - `SERIALIZER_VERSION = "ser-A-min-1"`
  - `question_id(text: str, option_keys: list[str], option_desc: dict[str,str], display: dict[str,str], legend: str|None) -> str` — `sha256(canonical json)[:12] + "@v" + N`, N은 `qid_registry.json`의 같은 앞부분 등장 순번(없으면 1).

- [ ] **Step 1: 실패 테스트**

```python
# tests/test_serialize.py
from harvest.serialize import serialize_state, canonicalize, SERIALIZER_VERSION

def test_facts_true_plus_named_false_sorted_and_unknown():
    s = serialize_state("f1287 (t=42.90s)", "c7", {"id": "S2", "text": "place mug o3 on tray o5",
                        "exit": "on(o3,o5)", "invariants": ["holding(o3)"], "elapsed": "normal"},
                        "gripper=closed_holding(o3) wrist_force=light arm=moving",
                        [("o3", "mug red", "held_by_gripper", "upright"), ("o5", "tray blue", "on(table)", "clear=yes")],
                        {"near(o3,o5)": True, "on(o3,o5)": False, "above(o3,o5)": False, "in_contact(o3,o5)": None},
                        {"on(o3,o5)", "in_contact(o3,o5)"},
                        [(-0.4, "aligned_x(o3,o5)", "no", "yes")])
    facts = [l for l in s.split("\n") if l.startswith("facts:")][0]
    assert facts == "facts: in_contact(o3,o5)=unknown near(o3,o5)=yes on(o3,o5)=no"
    assert "above(o3,o5)" not in s
    assert s.startswith("t_state: f1287 (t=42.90s)  contract: c7  stage: S2")
    assert SERIALIZER_VERSION == "ser-A-min-1"

def test_changes_capped_at_8_and_3s():
    ch = [(-0.1 * i, f"p{i}", "no", "yes") for i in range(40)]
    s = serialize_state("t", "c", {"id": "S1", "text": "x", "exit": "e", "invariants": [], "elapsed": "normal"},
                        "r", [], {}, set(), ch)
    lines = s.split("changes (last 3s): ")[1].split("; ")
    assert len(lines) == 8

def test_canonicalize_idempotent_and_crlf():
    a = "x  y \r\nz\t\n"
    assert canonicalize(a) == canonicalize(canonicalize(a)) == "x y\nz"
```

```python
# tests/test_qid.py
from harvest.qid import question_id

def test_same_content_same_id_whitespace_insensitive(tmp_path, monkeypatch):
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "r.json"))
    a = question_id("Which dir?", ["a", "b"], {"a": "up", "b": "down"}, {"a": "A", "b": "B"}, None)
    b = question_id("Which  dir? ", ["a", "b"], {"a": "up", "b": "down"}, {"a": "A", "b": "B"}, None)
    assert a == b and a.endswith("@v1")

def test_display_change_changes_id(tmp_path, monkeypatch):
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "r.json"))
    a = question_id("Q", ["a", "b"], {"a": "up", "b": "down"}, {"a": "A", "b": "B"}, None)
    b = question_id("Q", ["a", "b"], {"a": "up", "b": "down"}, {"a": "X", "b": "B"}, None)
    assert a != b
```

- [ ] **Step 2: 실패 확인**
- [ ] **Step 3: 구현**

```python
# harvest/serialize.py
"""Minimal serialization (candidate-A shape, E §1.4 measurement format) + J2 canonicalization (canon §28)."""
import re, unicodedata

SERIALIZER_VERSION = "ser-A-min-1"

def _v(x):
    return "unknown" if x is None else ("yes" if x else "no")

def canonicalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\t", " "))
    out = []
    for line in text.split("\n"):
        lead = len(line) - len(line.lstrip(" "))
        out.append(" " * lead + re.sub(r" {2,}", " ", line.strip()))
    return "\n".join(out).strip("\n")

def serialize_state(t_state, contract, stage, robot_line, objects, facts, named, changes):
    lines = [f"t_state: {t_state}  contract: {contract}  stage: {stage['id']} \"{stage['text']}\"",
             f"robot: {robot_line}", "objects:"]
    for oid, desc, support, pose in objects:
        lines.append(f"  {oid} {desc} | {support} | {pose}")
    shown = sorted(k for k, v in facts.items() if v is True or k in named)
    lines.append("facts: " + " ".join(f"{k}={_v(facts[k])}" for k in shown))
    inv = " ".join(f"{p}" for p in stage["invariants"])
    lines.append(f"stage {stage['id']}: exit={stage['exit']} invariants={inv} elapsed={stage['elapsed']}")
    recent = sorted([c for c in changes if c[0] >= -3.0], key=lambda c: c[0])[-8:]
    lines.append("changes (last 3s): " + "; ".join(f"{t:+.1f}s {p}: {a}->{b}" for t, p, a, b in recent))
    return "\n".join(lines)
```

```python
# harvest/qid.py
"""question_id@vN (canon §28 J1): hash of wording + option_key order + descriptions + display + legend + serializer."""
import hashlib, json, os, pathlib
from .serialize import canonicalize, SERIALIZER_VERSION

def _registry() -> pathlib.Path:
    return pathlib.Path(os.environ.get("HARVEST_QID_REGISTRY", "docs/stage3/qid_registry.json"))

def question_id(text, option_keys, option_desc, display, legend):
    payload = json.dumps({"q": canonicalize(text), "keys": list(option_keys),
                          "desc": {k: canonicalize(option_desc[k]) for k in option_keys},
                          "display": {k: display[k] for k in option_keys},  # exact, spaces included
                          "legend": legend, "ser": SERIALIZER_VERSION}, sort_keys=True, ensure_ascii=False)
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    reg = _registry()
    data = json.loads(reg.read_text(encoding="utf-8")) if reg.exists() else {}
    if h not in data:
        data[h] = len(data) + 1
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return f"{h}@v{data[h]}"
```

주의: `display`는 정규화하지 않는다(정본 §28 "표시 문자열(공백 포함)").

- [ ] **Step 4: 통과 확인** — 5 passed
- [ ] **Step 5: 커밋** — `stage3 T3: serializer, J2 canonicalization, question_id@vN`

---

### Task 4: 보기 이름 규칙과 판 A0–A4, option_key 되돌림

**Files:**
- Create: `harvest/options.py`, `tests/test_options.py`
- 참고: 정본 §27(R1–R6), E §2A.3 (i) 확장판

**Interfaces:**
- Produces:
  - `@dataclass Option(key: str, name: str, desc: str)` — `key`는 표준 뜻(option_key), `name`은 모델에 보이는 이름
  - `variant(opts: list[Option], v: str, seed: int) -> list[Option]` — `v ∈ {"A0","A1","A2","A3","A4"}`: A0 그대로 / A1 중립 문자(`opt_a`, `opt_b`, …) / A2 무작위 5자(seed 고정) / A3 이름을 설명과 한 칸 어긋나게(이름 i ← 원래 이름 i+1, 설명·key 그대로) / A4 이름·설명 그대로 순서만 한 칸 순환. `NONE_ESCALATE`는 모든 판에서 이름·위치 고정(맨 끝).
  - `to_option_key(opts_shown: list[Option], answer_name: str) -> str`
  - `layer(k: int, qtype: str) -> str` — `"L2"`(2지선다·Noul) / `"L3_6"` / `"L7_17"`

- [ ] **Step 1: 실패 테스트**

```python
# tests/test_options.py
from harvest.options import Option, variant, to_option_key, layer
BASE = [Option("up", "up", "Move up."), Option("down", "down", "Move down."),
        Option("hold", "hold", "Keep position."), Option("NONE_ESCALATE", "NONE_ESCALATE", "None fits.")]

def test_answer_maps_back_to_option_key_for_all_variants():
    for v in ["A0", "A1", "A2", "A3", "A4"]:
        shown = variant(BASE, v, seed=7)
        for o in shown:
            assert to_option_key(shown, o.name) == o.key

def test_none_escalate_fixed_last_everywhere():
    for v in ["A0", "A1", "A2", "A3", "A4"]:
        shown = variant(BASE, v, seed=1)
        assert shown[-1].key == shown[-1].name == "NONE_ESCALATE"

def test_a3_misaligns_names_but_keeps_desc_key_pairs():
    shown = variant(BASE, "A3", seed=0)
    assert [o.key for o in shown] == ["up", "down", "hold", "NONE_ESCALATE"]
    assert [o.desc for o in shown] == [o.desc for o in BASE]
    assert [o.name for o in shown[:3]] == ["down", "hold", "up"]

def test_a4_rotates_order_only():
    shown = variant(BASE, "A4", seed=0)
    assert [o.key for o in shown[:3]] == ["down", "hold", "up"]
    assert all(o.name == o.key for o in shown)

def test_a2_deterministic_by_seed():
    assert [o.name for o in variant(BASE, "A2", 3)] == [o.name for o in variant(BASE, "A2", 3)]

def test_layers():
    assert layer(2, "choice") == "L2" and layer(0, "noul") == "L2"
    assert layer(4, "choice") == "L3_6" and layer(10, "choice") == "L7_17"
```

- [ ] **Step 2: 실패 확인**
- [ ] **Step 3: 구현**

```python
# harvest/options.py
"""Option naming variants A0-A4 (canon §27, E §2A.3 (i)); answers always counted by option_key (R5)."""
from dataclasses import dataclass, replace
import random, string

@dataclass(frozen=True)
class Option:
    key: str
    name: str
    desc: str

NE = "NONE_ESCALATE"

def _split(opts):
    body = [o for o in opts if o.key != NE]
    tail = [o for o in opts if o.key == NE]
    return body, tail

def variant(opts, v, seed):
    body, tail = _split(opts)
    if v == "A0":
        out = body
    elif v == "A1":
        out = [replace(o, name=f"opt_{string.ascii_lowercase[i]}") for i, o in enumerate(body)]
    elif v == "A2":
        rng = random.Random(seed)
        names = set()
        while len(names) < len(body):
            names.add("".join(rng.choice(string.ascii_lowercase) for _ in range(5)))
        out = [replace(o, name=n) for o, n in zip(body, sorted(names, key=lambda s: rng.random()))]
    elif v == "A3":
        out = [replace(o, name=body[(i + 1) % len(body)].name) for i, o in enumerate(body)]
    elif v == "A4":
        out = body[1:] + body[:1]
    else:
        raise ValueError(v)
    return list(out) + tail

def to_option_key(shown, answer_name):
    for o in shown:
        if o.name == answer_name:
            return o.key
    raise KeyError(answer_name)

def layer(k, qtype):
    if qtype == "noul" or k <= 2:
        return "L2"
    return "L3_6" if k <= 6 else "L7_17"
```

- [ ] **Step 4: 통과 확인** — 6 passed
- [ ] **Step 5: 커밋** — `stage3 T4: option variants A0-A4 with option_key mapping`

---

### Task 5: JevCall 조립기와 Jev 클라이언트

**Files:**
- Create: `harvest/jevcall.py`, `harvest/clients/__init__.py`, `harvest/clients/jev.py`, `harvest/record.py`, `tests/test_jevcall.py`, `tests/test_jev_client.py`, `tests/test_record.py`, `tests/test_canon_conformance.py`

**Interfaces:**
- Consumes: `serialize_state`, `Option`, `variant`, `question_id`, `CFG`
- Produces:
  - `build_choice(key: str, instructions: str|dict, opts: list[Option]) -> tuple[str, dict]` — `(질문 키, {"type":"choice","instructions":…,"criteria":{name: desc}})`, `criteria` 삽입 순서 = 보기 순서
  - `build_request(state: str, questions: list[tuple[str,dict]]) -> dict` — `{"model": CFG.jev_model, "state": canonicalize(state), "questions": {…}}`
  - `class JevClient(token: str, transport=None)` — `httpx.Client(http2=False, timeout=CFG.timeout_s, transport=transport)`, 재시도 없음; `call(req: dict, meta: dict) -> CallRecord`
  - `@dataclass CallRecord`: E §1.6 필드(`call_id, experiment, condition, seed, t_send, t_first_byte, t_done, http_status, retry_n=0, input_tokens, output_tokens, model, model_ok, answers:{qkey:{choice, probabilities, confidence}}, raw_request, raw_response, error`)
  - `class Recorder(path)` — `write(rec: CallRecord)` JSONL 한 줄, `flush()`; 헤더(토큰)는 절대 쓰지 않는다
- 응답 파싱 규칙: 문서(`docs/research/v3/01-models-preemption.md:42`) 기준 질문별 `choice`·`probabilities`·`confidence`(Score는 `score`·`legend`). 실제 응답 형식은 **Step 6 실호출로 확인**하고, 다르면 파서와 테스트 고정값을 실제 원문으로 바꾼다.

- [ ] **Step 1: 실패 테스트**

```python
# tests/test_jevcall.py
from harvest.jevcall import build_choice, build_request
from harvest.options import Option

def test_criteria_order_and_model():
    opts = [Option("up", "up", "Move up."), Option("down", "down", "Move down.")]
    k, q = build_choice("ds1.dir_z", "Which way?", opts)
    req = build_request("s  a\r\n", [(k, q)])
    assert req["model"] == "jev-1.13.0"
    assert list(req["questions"]["ds1.dir_z"]["criteria"]) == ["up", "down"]
    assert req["state"] == "s a"
```

```python
# tests/test_jev_client.py
import json, httpx
from harvest.clients.jev import JevClient

def _transport(status=200, model="jev-1.13.0"):
    def handler(request):
        assert "authorization" in {k.lower() for k in request.headers}
        body = {"model": model, "usage": {"input_tokens": 1200, "output_tokens": 0},
                "answers": {"ds1.dir_z": {"choice": "up", "probabilities": {"up": 0.9, "down": 0.1}, "confidence": 0.9}}}
        return httpx.Response(status, json=body)
    return httpx.MockTransport(handler)

REQ = {"model": "jev-1.13.0", "state": "s", "questions": {"ds1.dir_z": {"type": "choice", "instructions": "q", "criteria": {"up": "u", "down": "d"}}}}

def test_parses_answer_and_times():
    r = JevClient("tok", transport=_transport()).call(REQ, {"experiment": "T"})
    assert r.http_status == 200 and r.answers["ds1.dir_z"]["choice"] == "up"
    assert r.t_send <= r.t_first_byte <= r.t_done and r.retry_n == 0 and r.model_ok

def test_model_mismatch_flags_session():
    r = JevClient("tok", transport=_transport(model="jev-1.14.0")).call(REQ, {})
    assert r.model_ok is False

def test_http_error_is_recorded_not_raised():
    r = JevClient("tok", transport=_transport(status=429)).call(REQ, {})
    assert r.http_status == 429 and r.error is not None

def test_timeout_recorded():
    def boom(request): raise httpx.ReadTimeout("t", request=request)
    r = JevClient("tok", transport=httpx.MockTransport(boom)).call(REQ, {})
    assert r.http_status is None and r.error == "timeout"
```

```python
# tests/test_record.py
import json
from harvest.record import Recorder
from harvest.clients.jev import CallRecord

def test_no_secret_in_jsonl(tmp_path):
    rec = CallRecord(call_id="c1", raw_request={"model": "jev-1.13.0"}, raw_response={})
    p = tmp_path / "x.jsonl"
    with Recorder(p) as w:
        w.write(rec)
    line = p.read_text(encoding="utf-8")
    assert "tok" not in line.lower().replace("tokens", "") and json.loads(line)["call_id"] == "c1"
```

```python
# tests/test_canon_conformance.py  (DC1 gate)
import pathlib, re
CANON = pathlib.Path("docs/design/E-first-experiments.md").read_text(encoding="utf-8")

def test_endpoint_and_model_match_canon():
    from harvest.config import CFG
    assert CFG.jev_url in CANON and f'"model": "{CFG.jev_model}"' in CANON

def test_question_key_scheme():
    assert re.search(r"`ds<번호>\.<질문>` / `mon\.progress` / `mon\.t3b`", CANON)

def test_dir_split_option_counts():
    # M3 §4.2 D4 C-6: dir_xy = 8 + none_xy + NONE_ESCALATE = 10, dir_z = 4
    from harvest.jevcall import DIR_XY, DIR_Z
    assert len(DIR_XY) == 10 and len(DIR_Z) == 4
```

- [ ] **Step 2: 실패 확인**
- [ ] **Step 3: 구현**

```python
# harvest/jevcall.py
"""JevCall request builder (E §1.2)."""
from .config import CFG
from .options import Option
from .serialize import canonicalize

_XY = ["plus_x", "minus_x", "plus_y", "minus_y", "plus_x_plus_y", "plus_x_minus_y", "minus_x_plus_y", "minus_x_minus_y"]
_XY_DESC = {"plus_x": "Move toward +x (away from robot).", "minus_x": "Move toward -x (toward robot).",
            "plus_y": "Move toward +y (robot left).", "minus_y": "Move toward -y (robot right).",
            "plus_x_plus_y": "Move diagonally +x,+y.", "plus_x_minus_y": "Move diagonally +x,-y.",
            "minus_x_plus_y": "Move diagonally -x,+y.", "minus_x_minus_y": "Move diagonally -x,-y."}
NE = Option("NONE_ESCALATE", "NONE_ESCALATE", "None of the options fits the situation.")
DIR_XY = [Option(k, k, _XY_DESC[k]) for k in _XY] + [Option("none_xy", "none_xy", "No horizontal motion."), NE]
DIR_Z = [Option("up", "up", "Move up."), Option("down", "down", "Move down."),
         Option("none_z", "none_z", "No vertical motion."), NE]
MAG = [Option("tiny", "tiny", "about 0.5 cm"), Option("small", "small", "about 1 cm"),
       Option("medium", "medium", "about 2 cm"), Option("large", "large", "about 4 cm"),
       Option("xlarge", "xlarge", "about 8 cm"), NE]   # cm values are [가정] (E §1.2)

def build_choice(key, instructions, opts):
    return key, {"type": "choice", "instructions": instructions,
                 "criteria": {o.name: o.desc for o in opts}}

def build_request(state, questions):
    return {"model": CFG.jev_model, "state": canonicalize(state), "questions": dict(questions)}
```

주의: `DIR_XY`의 보기 이름은 **R1 금지어 교체(정본 §27 끝, handoff §2.5 "E0 전 할 일")**를 반영해야 한다. 구현 전에 `grep -n "R1" docs/design/00-interfaces.md`로 금지어 목록을 읽고, 위 이름 중 걸리는 것이 있으면 바꾼 뒤 테스트의 기대 이름도 같이 바꾼다.

```python
# harvest/clients/jev.py
"""Jev HTTP client: keep-alive, no retries, timing fields, raw JSON kept (E §1.1, §1.6)."""
from __future__ import annotations
import time, uuid
from dataclasses import dataclass, field
import httpx
from ..config import CFG

@dataclass
class CallRecord:
    call_id: str = ""
    experiment: str = ""
    condition: str = ""
    seed: int | None = None
    t_send: float = 0.0
    t_first_byte: float = 0.0
    t_done: float = 0.0
    http_status: int | None = None
    retry_n: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None
    model_ok: bool = True
    answers: dict = field(default_factory=dict)
    raw_request: dict = field(default_factory=dict)
    raw_response: dict | None = None
    error: str | None = None
    meta: dict = field(default_factory=dict)

class JevClient:
    def __init__(self, token: str, transport: httpx.BaseTransport | None = None):
        self._c = httpx.Client(timeout=CFG.timeout_s, transport=transport,
                               headers={"Authorization": f"Bearer {token}"})

    def call(self, req: dict, meta: dict) -> CallRecord:
        r = CallRecord(call_id=uuid.uuid4().hex, raw_request=req, meta=dict(meta),
                       experiment=meta.get("experiment", ""), condition=meta.get("condition", ""),
                       seed=meta.get("seed"))
        r.t_send = time.monotonic()
        try:
            with self._c.stream("POST", CFG.jev_url, json=req) as resp:
                it = resp.iter_bytes()
                first = next(it, b"")
                r.t_first_byte = time.monotonic()
                body = first + b"".join(it)
                r.t_done = time.monotonic()
                r.http_status = resp.status_code
            if r.http_status != 200:
                r.error = f"http_{r.http_status}"
                return r
            data = httpx.Response(200, content=body).json()
            r.raw_response = data
            r.model = data.get("model")
            r.model_ok = r.model == CFG.jev_model
            u = data.get("usage") or {}
            r.input_tokens, r.output_tokens = u.get("input_tokens"), u.get("output_tokens")
            r.answers = data.get("answers") or data.get("questions") or {}
        except httpx.TimeoutException:
            r.t_done = time.monotonic(); r.t_first_byte = r.t_first_byte or r.t_done
            r.error = "timeout"
        except httpx.HTTPError as e:
            r.t_done = time.monotonic(); r.t_first_byte = r.t_first_byte or r.t_done
            r.error = type(e).__name__
        return r
```

```python
# harvest/record.py
"""JSONL recorder; never writes headers or secrets."""
import dataclasses, json, pathlib

class Recorder:
    def __init__(self, path):
        self.path = pathlib.Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
    def __enter__(self):
        self._f = open(self.path, "a", encoding="utf-8"); return self
    def write(self, rec):
        self._f.write(json.dumps(dataclasses.asdict(rec), ensure_ascii=False) + "\n")
    def __exit__(self, *a):
        self._f.close()
```

`tests/test_record.py`의 `"tok"` 검사는 토큰 값이 기록에 섞이지 않았는지 보는 것이다(필드 이름 `input_tokens`는 제외하고 셈).

- [ ] **Step 4: 통과 확인** — `python -m pytest` 전체 → 모두 passed
- [ ] **Step 5: 커밋** — `stage3 T5: JevCall builder, Jev client, recorder, canon conformance`
- [ ] **Step 6: 실호출 1회(사용자 키 필요)** — 로컬에서 `python -m harvest.clients.jev_smoke`(아래)를 한 번 돌려 실제 응답 원문을 `D:/tools/scratch_qdd/jev_smoke.json`에 저장하고 필드 이름을 확인한다. 다르면 `call()` 파싱과 `tests/test_jev_client.py` 고정 응답을 실제 모양으로 고치고 다시 통과시킨 뒤 커밋 `stage3 T5: parse real Jev response shape`.

```python
# harvest/clients/jev_smoke.py
import json, os, pathlib, sys
from harvest.clients.jev import JevClient
from harvest.jevcall import build_choice, build_request, DIR_Z
tok = pathlib.Path(os.environ["HARVEST_JEV_TOKEN_FILE"]).read_text().strip()
k, q = build_choice("ds1.dir_z", "The mug is 3 cm above the tray. Which vertical motion places it?", DIR_Z)
r = JevClient(tok).call(build_request("objects: o3 mug above o5 tray", [(k, q)]), {"experiment": "smoke"})
out = pathlib.Path("D:/tools/scratch_qdd/jev_smoke.json")
out.write_text(json.dumps({"status": r.http_status, "latency": r.t_done - r.t_send, "resp": r.raw_response, "err": r.error}, indent=1))
print(r.http_status, round(r.t_done - r.t_send, 3), r.error)
```

- [ ] **DC1 관문** — `python -m pytest tests/test_canon_conformance.py` 통과 + 방향 질문 6개 → `direction-log.md` 기록 → 태그 `stage3-dc1`.

---

### Task 6: E0 부하 발생기와 세션 실행기

**Files:**
- Create: `harvest/load/__init__.py`, `harvest/load/closed_loop.py`, `harvest/load/open_loop.py`, `harvest/load/session.py`, `harvest/load/payloads.py`, `tests/test_load.py`

**Interfaces:**
- Consumes: `JevClient.call`, `Recorder`, `build_request`
- Produces:
  - `payloads.make(size: str, i: int) -> dict` — 크기 등급 S1/S3/G1/X8(E §1.3). 매 요청 `t_state`에 프레임 번호 `i`를 넣어 캐시를 피한다(E §2.10). `payloads.fixed(j: int) -> dict` — 결정성 측정용 고정 20개(j = 0..19, 완전히 같은 바이트).
  - `closed_loop(call: Callable[[dict, dict], CallRecord], make: Callable[[int], dict], n_inflight: int, n_total: int, meta: dict) -> list[CallRecord]` — 스레드 풀, 응답이 오면 곧바로 다음 요청
  - `open_loop(call, make, T_c: float, duration_s: float, n_cap: int, meta) -> tuple[list[CallRecord], int]` — 주기 송신, in-flight가 `n_cap`이면 건너뛰고 건너뜀 수 반환
  - `run_session(client, out_dir, slot_label: str, sizes=("S1","S3","G1"), ns=(1,2,3,4,6,8), per_cell=300)` — curl 분해 20회 → 닫힌 스윕 → X8(N=1,4) → 열린 루프(S1·S3 × T_c 0.2/0.33/0.5, 60 s) → 결정성 20개. 기록 파일 `e0_<UTC>_<slot>.jsonl`, 첫 줄은 사전 등록 해시 + 시각(KST·PDT) + 위치(pod/pc).
- 속도 제한: 전체 합계 20 요청/초를 넘지 않도록 토큰 버킷(`RateLimiter(rps=18)`)을 `call` 앞에 둔다. E0.5와 같은 날이면 E0.5 몫 400/분을 뺀다(E §2A.8).

- [ ] **Step 1: 실패 테스트** (가짜 지연 transport 사용)

```python
# tests/test_load.py
import threading, time
from harvest.clients.jev import CallRecord
from harvest.load.closed_loop import closed_loop
from harvest.load.open_loop import open_loop
from harvest.load.payloads import make, fixed

def fake_call_factory(delay):
    lock = threading.Lock(); state = {"now": 0, "peak": 0}
    def call(req, meta):
        with lock:
            state["now"] += 1; state["peak"] = max(state["peak"], state["now"])
        t0 = time.monotonic(); time.sleep(delay)
        with lock:
            state["now"] -= 1
        return CallRecord(t_send=t0, t_first_byte=t0 + delay, t_done=time.monotonic(), http_status=200, meta=meta)
    return call, state

def test_closed_loop_keeps_n_inflight():
    call, st = fake_call_factory(0.05)
    recs = closed_loop(call, lambda i: {"i": i}, n_inflight=4, n_total=40, meta={})
    assert len(recs) == 40 and st["peak"] == 4

def test_open_loop_skips_when_cap_reached():
    call, st = fake_call_factory(0.5)
    recs, skipped = open_loop(call, lambda i: {"i": i}, T_c=0.05, duration_s=1.0, n_cap=2, meta={})
    assert st["peak"] <= 2 and skipped > 0

def test_payload_sizes_and_cache_busting():
    a, b = make("S1", 1), make("S1", 2)
    assert a["state"] != b["state"] and set(a["questions"]) == set(b["questions"])
    assert len(make("X8", 0)["state"]) > 4 * len(make("S1", 0)["state"])
    assert fixed(3) == fixed(3)
```

- [ ] **Step 2: 실패 확인**
- [ ] **Step 3: 구현**

```python
# harvest/load/closed_loop.py
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait

def closed_loop(call, make, n_inflight, n_total, meta):
    out, i = [], 0
    with ThreadPoolExecutor(max_workers=n_inflight) as ex:
        live = set()
        while i < n_total or live:
            while i < n_total and len(live) < n_inflight:
                live.add(ex.submit(call, make(i), {**meta, "N": n_inflight, "i": i})); i += 1
            done, live = wait(live, return_when=FIRST_COMPLETED)
            out.extend(f.result() for f in done)
    return out
```

```python
# harvest/load/open_loop.py
import threading, time
from concurrent.futures import ThreadPoolExecutor

def open_loop(call, make, T_c, duration_s, n_cap, meta):
    out, lock, live = [], threading.Lock(), [0]
    skipped, i = 0, 0
    def run(req, m):
        try:
            r = call(req, m)
            with lock: out.append(r)
        finally:
            with lock: live[0] -= 1
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=n_cap) as ex:
        k = 0
        while True:
            t_next = t0 + k * T_c
            if t_next - t0 >= duration_s: break
            time.sleep(max(0.0, t_next - time.monotonic()))
            with lock:
                full = live[0] >= n_cap
                if not full: live[0] += 1
            if full: skipped += 1
            else:
                ex.submit(run, make(i), {**meta, "T_c": T_c, "i": i}); i += 1
            k += 1
    return out, skipped
```

```python
# harvest/load/payloads.py
"""Payload generator by size class (E §1.3). Templates are realistic but synthetic until the pool exists (E §2.3)."""
from ..jevcall import build_choice, build_request, DIR_XY, DIR_Z, MAG
from ..options import Option

_OBJ = "  o3 mug red | held_by_gripper | upright\n  o5 tray blue | on(table) | clear=yes"
_FILL = "\n".join(f"  o{k} distractor_{k} | on(table) | upright" for k in range(10, 90))

def _state(i, extra=""):
    return (f"t_state: f{i} (t={i*0.33:.2f}s)  contract: c7  stage: S2 \"place mug o3 on tray o5\"\n"
            f"robot: gripper=closed_holding(o3) wrist_force=light arm=moving\nobjects:\n{_OBJ}{extra}\n"
            "facts: near(o3,o5)=yes aligned_xy(o3,o5)=no in_contact(o3,o5)=no\n"
            "stage S2: exit=on(o3,o5) invariants=holding(o3) elapsed=normal\n"
            "changes (last 3s): -0.4s aligned_x(o3,o5): no->yes")

_PROG = [Option("valid_progress", "valid_progress", "Stage is progressing."),
         Option("allowed_change", "allowed_change", "Change is allowed."),
         Option("failure", "failure", "Stage failed."), Option("recovering", "recovering", "Recovering."),
         Option("NONE_ESCALATE", "NONE_ESCALATE", "Cannot tell from the state.")]

def _dz(n):
    q = "Which direction should the gripper move during step {} toward exit of S2?".format(n)
    return [build_choice(f"{n}.dir_xy", q, DIR_XY), build_choice(f"{n}.dir_z", q, DIR_Z),
            build_choice(f"{n}.mag_coarse", "How far?", MAG)]

def make(size, i):
    mon = [build_choice("mon.progress", "Considering the change since the last step, how is stage S2 going?", _PROG)]
    if size == "S1": qs = _dz("ds412") + mon
    elif size == "S3": qs = _dz("ds412") + _dz("ds413") + _dz("ds414") + mon
    elif size == "G1": qs = [build_choice("ds.target", "Which object is the target?", [Option("o5", "o5", "blue tray"), Option("NONE_ESCALATE", "NONE_ESCALATE", "None fits.")])] + mon
    elif size == "X8": return build_request(_state(i, "\n" + _FILL * 3), _dz("ds412") + mon)
    else: raise ValueError(size)
    return build_request(_state(i), qs)

def fixed(j):
    return make("S1", 100000 + j)
```

`harvest/load/session.py`는 위 두 부하와 `payloads`를 E §2.3 순서대로 부르고, 시작 때 `subprocess.run(["curl","-s","-o","/dev/null","-w","%{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer} %{time_total}", CFG.jev_url, "-X","POST", …])`를 20회 돌려 같은 JSONL에 `{"kind":"curl", …}`로 남긴다(헤더 인자는 기록하지 않는다). 첫 줄 `{"kind":"header","prereg": <prereg.json hashes>, "utc":…, "kst":…, "pdt":…, "site": "pod"|"pc"}`.

- [ ] **Step 4: 통과 확인** — 3 passed(+ 이전 전부)
- [ ] **Step 5: 커밋** — `stage3 T6: E0 load generators and session runner`

---

### Task 7: E0 분석과 판정 1–7 (코드로)

**Files:**
- Create: `harvest/analysis/__init__.py`, `harvest/analysis/stats.py`, `harvest/analysis/latency.py`, `tests/test_latency.py`, `tests/test_stats.py`

**Interfaces:**
- Produces:
  - `censored_quantile(lat: list[float|None], q: float, cap_s=2.0) -> float` — 실패(None)와 `> cap_s`는 `inf`. 실패율 > 1−q면 `inf`.
  - `cluster_bootstrap_ci(values_by_cluster: dict[str, list[float]], stat: Callable, n=10000, seed=0) -> tuple[float,float]`
  - `holm(pvals: dict[str,float], alpha=0.05) -> dict[str,bool]`
  - `judge_e0(records: list[dict], T_c=0.33) -> dict` — 키 `d_p95_S1`, `d_p95_S3`, `worst_slot_ratio`, `N_max`, `case`("a"–"e"), `votes_per_step_median`, `size_penalty_s`, `determinism_flip`, `max_dp`, `site_gap_s`, `notes[]`. 판정 문턱은 E §2.7 그대로(0.165 / 0.33 / 1.0 / 2.0 s, 실패율 2%, 동시성 벌점 1.25, 시간대 1.3, 크기 0.05 s·T_c, 위치 0.1 s).

- [ ] **Step 1: 실패 테스트**

```python
# tests/test_latency.py
import math
from harvest.analysis.latency import censored_quantile, judge_e0

def test_censored_p95_counts_failures_as_inf():
    lat = [0.3] * 94 + [None] * 6
    assert censored_quantile(lat, 0.95) == math.inf
    lat = [0.3] * 96 + [None] * 4
    assert censored_quantile(lat, 0.95) == math.inf or censored_quantile(lat, 0.95) >= 0.3
    assert censored_quantile([0.1] * 100, 0.95) == 0.1
    assert censored_quantile([0.1] * 95 + [2.5] * 5, 0.95) >= 0.1

def _recs(lat, size="S1", N=1, slot="02", site="pod", ok=True):
    return [{"size": size, "N": N, "slot": slot, "site": site, "lat": lat, "ok": ok} for _ in range(300)]

def test_case_boundaries():
    for lat, case in [(0.10, "a"), (0.25, "b"), (0.6, "c"), (1.5, "d"), (2.5, "e")]:
        recs = _recs(lat) + _recs(lat, size="S3")
        assert judge_e0(recs)["case"] == case

def test_failure_rate_over_2pct_is_case_e():
    recs = _recs(0.3)[:290] + [{"size": "S1", "N": 1, "slot": "02", "site": "pod", "lat": None, "ok": False}] * 10
    recs += _recs(0.3, size="S3")
    assert judge_e0(recs)["case"] == "e"

def test_nmax_formula():
    recs = _recs(0.6) + _recs(0.6, size="S3") + _recs(0.6, N=3) + _recs(0.6, N=4)
    assert judge_e0(recs)["N_max"] == math.ceil(0.6 / 0.33) + 1
```

```python
# tests/test_stats.py
from harvest.analysis.stats import cluster_bootstrap_ci, holm

def test_bootstrap_ci_contains_mean():
    lo, hi = cluster_bootstrap_ci({f"e{i}": [i % 2] * 5 for i in range(40)}, lambda xs: sum(xs) / len(xs), n=2000)
    assert lo < 0.5 < hi

def test_holm_orders():
    r = holm({"a": 0.001, "b": 0.04, "c": 0.03})
    assert r["a"] is True and r["b"] is False
```

- [ ] **Step 2: 실패 확인**
- [ ] **Step 3: 구현**

```python
# harvest/analysis/stats.py
import numpy as np

def cluster_bootstrap_ci(values_by_cluster, stat, n=10000, seed=0, level=0.95):
    keys = list(values_by_cluster); rng = np.random.default_rng(seed); out = []
    for _ in range(n):
        pick = rng.choice(len(keys), len(keys), replace=True)
        xs = [v for j in pick for v in values_by_cluster[keys[j]]]
        out.append(stat(xs))
    a = (1 - level) / 2
    return float(np.quantile(out, a)), float(np.quantile(out, 1 - a))

def holm(pvals, alpha=0.05):
    items = sorted(pvals.items(), key=lambda kv: kv[1]); m = len(items); res = {}; stop = False
    for i, (k, p) in enumerate(items):
        if stop or p > alpha / (m - i):
            stop = True; res[k] = False
        else:
            res[k] = True
    return res
```

```python
# harvest/analysis/latency.py
"""E0 judgments 1-7 (E §2.7) computed from records {size, N, slot, site, lat(s)|None, ok}."""
import math
from collections import defaultdict
import numpy as np

def censored_quantile(lat, q, cap_s=2.0):
    xs = sorted(math.inf if (x is None or x > cap_s) else x for x in lat)
    if not xs: return math.inf
    idx = min(len(xs) - 1, int(math.ceil(q * len(xs))) - 1)
    return xs[idx]

def judge_e0(records, T_c=0.33):
    by = defaultdict(list)
    for r in records:
        if r.get("site", "pod") == "pod":
            by[(r["size"], r["N"])].append(r["lat"] if r["ok"] else None)
    s1 = [x for (s, n), v in by.items() if s == "S1" for x in v]
    s3 = [x for (s, n), v in by.items() if s == "S3" for x in v]
    L1, L3 = censored_quantile(s1, 0.95), censored_quantile(s3, 0.95)
    fail = sum(x is None for x in s1) / max(1, len(s1))
    L = max(L1, L3)
    if L > 2.0 or fail > 0.02: case = "e"
    elif L > 1.0: case = "d"
    elif L > T_c: case = "c"
    elif L >= T_c / 2: case = "b"
    else: case = "a"
    n_max = math.ceil(L1 / T_c) + 1 if math.isfinite(L1) else None
    base = censored_quantile(by.get(("S1", 1), []), 0.95)
    if n_max:
        while n_max > 1 and ("S1", n_max) in by and censored_quantile(by[("S1", n_max)], 0.95) / base > 1.25:
            n_max -= 1
    slots = defaultdict(list)
    for r in records:
        if r.get("site", "pod") == "pod" and r["size"] == "S1":
            slots[r["slot"]].append(r["lat"] if r["ok"] else None)
    sp = [censored_quantile(v, 0.95) for v in slots.values()]
    worst = max(sp) / L1 if sp and math.isfinite(L1) and L1 > 0 else math.inf
    notes = []
    if worst > 1.3: notes.append("block-randomize closed-loop conditions by time slot (judgment 1)")
    size_pen = L3 - L1
    if size_pen > T_c: notes.append("H=3 latency penalty (judgment 5)")
    return {"d_p95_S1": L1, "d_p95_S3": L3, "fail_rate_S1": fail, "case": case, "N_max": n_max,
            "worst_slot_ratio": worst, "size_penalty_s": size_pen, "notes": notes}
```

판정 4(스텝당 표 수)·6(결정성)·7(위치 차)은 `judge_e0_extra(open_loop_records, determinism_records, pc_records)`로 같은 파일에 넣는다. 테스트: 열린 루프 재생에서 지연 0.2 s·T_c 0.33·lead_max 1.5 s면 스텝당 표 중앙값 ≥ 2, 지연 1.4 s면 < 2.

```python
def votes_per_step(latencies, T_c=0.33, lead_max=1.5, d_p95=None):
    """Offline M4 replay (E §2.6): asks at t_s - lead_max ... t_s - d_p95 every T_c; counts answers arriving before t_s - d_p95... boundary."""
    d = d_p95 if d_p95 is not None else float(np.quantile([x for x in latencies if x is not None], 0.95))
    sends = np.arange(-lead_max, -d + 1e-9, T_c)
    out = []
    for k in range(len(latencies) // max(1, len(sends))):
        chunk = latencies[k * len(sends):(k + 1) * len(sends)]
        out.append(sum(1 for s, l in zip(sends, chunk) if l is not None and s + l <= 0.0))
    return float(np.median(out)) if out else 0.0
```

테스트 추가:
```python
from harvest.analysis.latency import votes_per_step
def test_votes_per_step():
    assert votes_per_step([0.2] * 300, d_p95=0.2) >= 2
    assert votes_per_step([1.4] * 300, d_p95=1.4) < 2
```

- [ ] **Step 4: 통과 확인**
- [ ] **Step 5: 커밋** — `stage3 T7: E0 censored latency analysis and judgments`

---

### Task 8: 파드 배치와 E0 첫 세션 (DC2)

**Files:**
- Create: `tools/pod_sync.sh`, `harvest/cli_e0.py`
- 파드: `/data/juhyoung_qdd/{code,data,logs}`

**Interfaces:**
- Consumes: `run_session`, `judge_e0`
- Produces: `python -m harvest.cli_e0 --slot KST02 --site pod --out /data/juhyoung_qdd/data/e0` → JSONL + `summary.json`(judge_e0 결과)

- [ ] **Step 1: 파드 파이썬 확인** — `kubectl -n p-test2 exec juhyoung-native-7a2a -- bash -lc 'python3 --version; python3 -c "import httpx,numpy" 2>&1'`. httpx가 없으면 `pip install --target /data/juhyoung_qdd/pylib httpx numpy pytest` 후 `PYTHONPATH=/data/juhyoung_qdd/pylib:/data/juhyoung_qdd/code`.
- [ ] **Step 2: 동기화 스크립트**

```bash
# tools/pod_sync.sh — copy harvest/ + tests/ to pod via exec cat (kubectl cp times out on large files; memory: reference_video_tools)
set -euo pipefail
POD=juhyoung-native-7a2a; NS=p-test2; DST=/data/juhyoung_qdd/code
cd "$(dirname "$0")/.."
tar czf - harvest tests pytest.ini docs/stage3/prereg.json | kubectl -n $NS exec -i $POD -- bash -c "mkdir -p $DST && tar xzf - -C $DST"
kubectl -n $NS exec $POD -- bash -c "cd $DST && PYTHONPATH=/data/juhyoung_qdd/pylib:$DST python3 -m pytest -q"
```

기대: 파드에서도 전 테스트 통과.
- [ ] **Step 3: 토큰 전달(사용자 확인 뒤)** — 로컬 키 파일을 stdin으로 1회: `kubectl -n p-test2 exec -i juhyoung-native-7a2a -- bash -c 'umask 077; cat > /data/.typesafe_token' < <키 파일>`. 로그·명령 기록에 키 값이 찍히지 않게 파일 리다이렉트만 쓴다.
- [ ] **Step 4: 첫 세션 실행(백그라운드)** — `kubectl … exec juhyoung-native-7a2a -- bash -c 'cd /data/juhyoung_qdd/code && nohup env PYTHONPATH=… HARVEST_JEV_TOKEN_FILE=/data/.typesafe_token python3 -m harvest.cli_e0 --slot $(TZ=Asia/Seoul date +KST%H) --site pod --out /data/juhyoung_qdd/data/e0 > /data/juhyoung_qdd/logs/e0_$(date -u +%H%M).log 2>&1 &'`. 약 15–20분.
- [ ] **Step 5: 결과 확인** — `summary.json`의 `case`, `d_p95_S1`, `fail_rate_S1`, `N_max`와 첫 10요청의 `input_tokens`(E §1.3 등급 추정 교정).
- [ ] **Step 6: 로컬 PC 1세션(보조 위치)** — 같은 CLI를 `--site pc --out D:/tools/scratch_qdd/e0_pc`로 1회.
- [ ] **Step 7: DC2 관문** — case (a)–(d)면 통과·태그 `stage3-dc2`, 잠정 `d_p95`를 `docs/stage3/results/e0_session1.md`에 기록. **case (e)면 즉시 멈추고 사용자에게 보고**(E §2.7-3(e) "E2a 전에 사용자와 방향 논의"). 이 경우 E0.5는 잠정 `d_p95`로 그대로 돌리되 다음 계획은 사용자 결정 뒤.
- [ ] **Step 8: 남은 23세션 예약** — 파드에서 `cron`이 없으면 `while` 루프 스크립트 `e0_schedule.sh`가 KST 02·06·10·14·18·22시 슬롯에 세션을 돌리고, 슬롯 사이 대기는 `sleep`(파드 스크립트 안이라 허용). 평일 3일 + 주말 1일. 중지 파일 `/data/juhyoung_qdd/STOP_E0`.
- [ ] **Step 9: 커밋** — `stage3 T8: E0 on pod, first session and schedule`(요약 md만, 원자료 제외)

---

### Task 9: Astra 첫 토큰 · 같은 입력 반복 · 매일 카나리

**Files:**
- Create: `harvest/clients/astra.py`, `harvest/canary.py`, `harvest/cli_astra.py`, `tests/test_canary.py`, `tests/test_astra_client.py`

**Interfaces:**
- Produces:
  - `class AstraClient(token, model: str, transport=None)` — OpenAI Responses API 스트리밍(`stream=True`), `call(input: list, effort: str, max_output_tokens: int, meta) -> AstraRecord(t_send, t_first_token, t_done, usage, output_text, model_field, prompt_id, image_sha256s, error)`. 재시도 없음.
  - `plan_signature(plan_json: dict) -> str` — 단계 스킬 열 + 결정 지점 id + 물체 역할의 해시(정본 §28)
  - `canary_run(jev: JevClient, astra: AstraClient|None, day: str, out) -> dict` — Jev 고정 스냅샷 × 고정 `question_id@vN` 세트 N=10회씩 + Astra low 고정 입력 1–2개. `canary_compare(base: dict, today: dict, floor: float) -> {"drift_suspect": bool, …}`
- **모델 문자열**: 사용자·정본 표기는 "GPT-6 Astra". 실제 API 모델 ID는 [미확인] → Step 1에서 `GET /v1/models`로 이름에 `astra`가 들어간 ID를 찾아 `docs/stage3/results/astra_model_id.md`에 적고 그 값을 쓴다. 못 찾으면 멈추고 사용자에게 묻는다.

- [ ] **Step 1: 모델 ID 확인**(키 필요) — `python -c` 스크립트로 모델 목록에서 `astra` 포함 ID만 출력(키는 파일에서 읽고 출력하지 않음).
- [ ] **Step 2: 실패 테스트**

```python
# tests/test_canary.py
from harvest.canary import canary_compare, plan_signature

def test_signature_ignores_wording_changes():
    a = {"stages": [{"skill": "pick", "obj": "o3"}, {"skill": "place", "obj": "o3", "target": "o5"}], "decision_points": ["dp1"], "roles": {"o3": "target", "o5": "goal"}, "note": "x"}
    b = dict(a, note="different words")
    assert plan_signature(a) == plan_signature(b)
    c = dict(a, roles={"o3": "target", "o5": "obstacle"})
    assert plan_signature(a) != plan_signature(c)

def test_drift_flag():
    base = {"q1": ["a"] * 10, "q2": ["b"] * 10}
    same = {"q1": ["a"] * 10, "q2": ["b"] * 10}
    moved = {"q1": ["c"] * 10, "q2": ["c"] * 10}
    assert canary_compare(base, same, floor=0.05)["drift_suspect"] is False
    assert canary_compare(base, moved, floor=0.05)["drift_suspect"] is True
```

```python
# tests/test_astra_client.py
import httpx, json
from harvest.clients.astra import AstraClient

def test_first_token_time_recorded():
    events = ('data: {"type":"response.output_text.delta","delta":"{"}\n\n'
              'data: {"type":"response.completed","response":{"model":"m","usage":{"output_tokens":5}}}\n\n')
    t = httpx.MockTransport(lambda r: httpx.Response(200, content=events.encode(), headers={"content-type": "text/event-stream"}))
    rec = AstraClient("k", "m", transport=t).call([{"role": "user", "content": "hi"}], "low", 100, {})
    assert rec.t_send <= rec.t_first_token <= rec.t_done and rec.output_text == "{" and rec.model_field == "m"
```

- [ ] **Step 3: 구현** — `astra.py`는 `httpx.Client.stream("POST", "https://api.openai.com/v1/responses", json={"model": model, "input": input, "reasoning": {"effort": effort}, "max_output_tokens": max_output_tokens, "stream": True})`로 SSE 줄을 읽어 첫 `response.output_text.delta`에서 `t_first_token`, `response.completed`에서 usage·model을 뽑는다. 이미지 입력은 바이트 SHA-256을 `image_sha256s`에 적는다(정본 §28 A6). `canary.py`의 `plan_signature`는 `json.dumps({"skills":[(s["skill"], s.get("obj"), s.get("target")) …], "dps": sorted(decision_points), "roles": roles}, sort_keys=True)`의 SHA-256 앞 16자. `canary_compare`는 질문별 최빈 불일치율 평균이 `floor`의 2배를 넘고 부트스트랩 하한 > 0이면 `drift_suspect=True`.
- [ ] **Step 4: 통과 확인**
- [ ] **Step 5: 실측(E0 첫 평일)** — T_fail 입력은 스냅샷 풀이 생기기 전이라 **합성 격자 이미지 1장(약 3,600 토큰) + 텍스트 약 2k**로 만든다(E §2.3, 풀 생긴 뒤 실제 입력으로 3개 교체). effort low 20회·high 20회 첫 토큰. 같은 입력 반복: 입력 3개 × low 50회(2604.22411 절차) × high 5회 [가정: high 횟수는 첫 10요청 비용으로 확정]. 결과 `docs/stage3/results/astra_first_token.md`.
- [ ] **Step 6: 카나리 기준일** — E0 첫날 `canary_run`을 기준으로 저장, 이후 매 실험일 첫 실행 전에 돌린다.
- [ ] **Step 7: 커밋** — `stage3 T9: Astra client, first-token, repetition, daily canary`

---

### Task 10: Inspect Robots P0 (DC3)

**Files:**
- Create: `docs/stage3/results/p0_inspect_robots.md`, 파드 `/data/juhyoung_qdd/ir/`

**Interfaces:**
- Produces: Isaac 5.1 chroot 파이썬에 `inspect-robots==v0.59.0`(git 커밋 `7e506e3`) + 플러그인 `inspect-robots-agent`, `inspect-robots-isaacsim` 설치, `smoke_async.py` 3모드 결과, Franka boot_proof 결과, RTF.

- [ ] **Step 1: chroot 진입 방식 확인** — `/data/juhyoung_infra/HANDOFF.md`를 읽고 기존 Isaac 실행 명령(bwrap/shimbin)을 그대로 쓴다. 읽은 명령을 결과 파일에 옮겨 적는다.
- [ ] **Step 2: 소스 고정 설치** — `git clone https://github.com/robocurve/inspect-robots /data/juhyoung_qdd/ir/src && cd … && git checkout 7e506e3 && git rev-parse HEAD`(기대 `7e506e3…`). Isaac 파이썬으로 `pip install --target /data/juhyoung_qdd/ir/pylib -e . -e plugins/inspect-robots-agent -e plugins/inspect-robots-isaacsim`. 설치 뒤 Isaac 자체 패키지 판본이 바뀌지 않았는지 `pip list` 전후 비교(차이는 결과 파일에).
- [ ] **Step 3: `inspect-robots doctor`**(또는 README의 점검 명령) — 출력 전체를 결과 파일에.
- [ ] **Step 4: 스모크** — D23의 `D:/tools/audit_d23/smoke/smoke_async.py`를 파드로 복사해 실행. 기대: sync/simlat/wall 3모드 통과, 하네스 오버헤드 수십 µs/스텝.
- [ ] **Step 5: Isaac 부팅 증명** — `plugins/inspect-robots-isaacsim/scripts/boot_proof.py`를 GPU 0·1·3 중 하나(`CUDA_VISIBLE_DEVICES=0`)로. 실패 시 Isaac Lab 2.3 호환 문제로 기록([미확인] 해소 여부).
- [ ] **Step 6: RTF 측정** — Franka Lift 과제를 카메라 켜고 60 s 돌려 `sim_time / wall_time`.
- [ ] **Step 7: agent + Astra low 1회**(키가 있으면) — cubepick 한 판. 경로가 돈다는 확인만, 수치는 근거로 쓰지 않는다(정본 §40).
- [ ] **Step 8: DC3 관문** — Step 4·5 통과면 태그 `stage3-dc3`. 실패하면 원인과 우회안(예: 헤드리스 렌더 설정, 판본 조정)을 적고 **사용자에게 보고**(1차 평가 하네스는 사용자 결정).
- [ ] **Step 9: 커밋** — `stage3 T10: Inspect Robots P0 on Isaac 5.1 pod`

---

### Task 11: 시뮬 장면 — AI Worker 한 팔 + ZED_M + 머그/트레이

**Files:**
- Create: `harvest/sim/__init__.py`, `harvest/sim/scene.py`, `harvest/sim/oracle_state.py`, `docs/stage3/results/scene_bringup.md`
- 파드: cyclo_lab 클론 `/data/juhyoung_qdd/cyclo_lab`

**Interfaces:**
- Produces:
  - `make_env(seed: int, headless=True, cameras=("zedm_left",), arm="right") -> Env` — Isaac Lab `ManagerBasedRLEnv` 래퍼, `sim.dt=0.01`, `decimation=5`
  - `Env.step(q_target: np.ndarray(8)) -> None`(7 관절 + 그리퍼 폭), `Env.sim_time -> float`
  - `oracle_objects(env) -> tuple[dict[str,Obj], Gripper, set[frozenset[str]], dict[str,str]]` — Task 2 입력 그대로(탁상 윗면 z = 0 좌표)
  - `SCENE_SPEC`: 대상 `o3 mug red`, 놓을 곳 `o5 tray blue`, 방해물 0–2개(`o8`, `o9`), 초기 배치 = 시드로 결정

- [ ] **Step 1: 로봇 모델 결정 순서(정본 §38 → §37)** — cyclo_lab에서 `grep -rn "FFW_SG2\|FFW-SG2\|FFW_BG2" source/ | head`로 과제 등록 이름을 확인. SG2 한 팔로 팔 관절만 제어하는 설정이 되면 SG2, 안 되면 BG2. 선택과 근거를 `scene_bringup.md`에.
- [ ] **Step 2: 기본 카메라 그대로 (정본 §43, user-log 44)** — 카메라를 추가·교체·이동하지 않는다. cyclo_lab 모델에 기본으로 달린 머리캠·손목캠 목록(이름·prim 경로·해상도·화각·깊이 출력 가능 여부·머리 좌우 쌍 여부)을 `scene_bringup.md`에 표로 적고, `make_env(cameras=…)`는 그 기본 카메라 이름만 받는다. 오라클 깊이는 기본 카메라의 렌더러 깊이 출력만 켠다. (첫 판의 ZED_M 확장·기선 63 mm 카메라 추가안은 폐기.)
- [ ] **Step 3: 머그·트레이 에셋** — Isaac 기본 에셋 또는 `/data/juhyoung_infra/isaac_assets`에서 고른다. 충돌 모양·질량·마찰을 `scene_bringup.md`에.
- [ ] **Step 4: 순수 로직 테스트(로컬)** — `tests/sim/test_snapshot_logic.py`에 `oracle_state`의 좌표 변환(월드 → 탁상 윗면 원점) 함수만 Isaac 없이 테스트:

```python
from harvest.sim.oracle_state import to_table_frame
import numpy as np
def test_table_frame_origin():
    p = to_table_frame(np.array([0.5, 0.1, 0.80]), table_top_z=0.75)
    assert np.allclose(p, [0.5, 0.1, 0.05])
```

`to_table_frame`는 Isaac 임포트 없이 정의(파일 위쪽), Isaac 의존 함수는 함수 안에서 임포트.
- [ ] **Step 5: 부팅 확인(파드)** — 시드 0으로 장면을 띄워 100스텝, 머그가 탁상 위에 정착(속도 < 1 mm/s)하는지와 RTF를 기록. 카메라 한 장 PNG를 `docs/stage3/results/scene_seed0.png`로(프레임으로 검증 — 메모리 규칙).
- [ ] **Step 6: 커밋** — `stage3 T11: single-arm AI Worker scene with ZED_M twin`

---

### Task 12: 오라클 플래너 · 섭동 P0–P2 · 성공 판정

**Files:**
- Create: `harvest/sim/planner.py`, `harvest/sim/perturb.py`, `tests/sim/test_planner_logic.py`

**Interfaces:**
- Consumes: `make_env`, `oracle_objects`, `PredicateState`
- Produces:
  - `OraclePlanner(env).step() -> np.ndarray(8)` — 단계 FSM: approach(머그 위 10 cm) → descend → close → lift(≥ h_lift) → carry(트레이 위) → descend(contact_under) → open → retreat. IK는 Isaac Lab `DifferentialIKController`.
  - `decision_points(planner) -> list[(t, ds_id, oracle_answer)]` — 결정 스텝마다 오라클 정답(방향 dir_xy·dir_z, 크기 구간, 그립)
  - `perturb(env, kind: "P0"|"P1"|"P2", seed) -> None` — **DEV 공개 섭동만**. P0 = 없음. P1·P2의 정의는 `grep -n "P1\|P2" docs/design/E-first-experiments.md` §4.5 표를 그대로 옮긴다(시각·크기는 시드로 결정).
  - `success(ps_history) -> bool` — `on(o3,o5) ∧ ¬holding(o3) ∧ upright(o3)` 1 s 연속, 60 s 제한, 탁상 밖 낙하 즉시 실패
- 순수 로직 테스트: FSM 전이(술어 dict 열을 넣어 단계가 맞게 넘어가는지)와 `success`의 1 s 연속 조건.

```python
# tests/sim/test_planner_logic.py
from harvest.sim.planner import success_from_history

def test_success_needs_one_second_continuous():
    ok = {"on(o3,o5)": True, "holding(o3)": False, "upright(o3)": True}
    bad = dict(ok, **{"upright(o3)": False})
    hist = [(i * 0.05, ok) for i in range(15)] + [(0.75, bad)] + [(0.8 + i * 0.05, ok) for i in range(21)]
    assert success_from_history(hist) is True
    assert success_from_history([(i * 0.05, ok) for i in range(15)]) is False
```

- [ ] **Step 1–4**: 테스트 작성 → 실패 → 구현 → 통과(로컬). 섭동 표를 옮길 때 원문 줄을 주석으로 붙인다.
- [ ] **Step 5: DEV 성공률(파드)** — 시드 0–29 × P0에서 플래너 성공률. **≥ 90%가 DC4 조건 일부.** 실패 판은 단계별로 분해해 기록(메모리 규칙: 접근 IK/파지/놓기 편차 mm로 나눔, 뭉뚱그리지 않음).
- [ ] **Step 6: 커밋** — `stage3 T12: oracle planner, DEV perturbations, success predicate`

---

### Task 13: 스냅샷 풀 (연속 0.33 s 열 + 전체 상태) (DC4)

**Files:**
- Create: `harvest/sim/snapshot.py`, `harvest/cli_pool.py`

**Interfaces:**
- Produces:
  - `save_state(env) -> dict` — 관절 위치·속도, 모든 강체 자세·속도, 그리퍼, 플래너 FSM 상태, `sim_time`, RNG 상태
  - `restore_state(env, s: dict) -> None` — **한 번만 쓰고**, 이후 명령 없이 0.5 s 정착 편차를 잰다
  - `restore_drift_check(env, s) -> float` — 복원 후 0.5 s 동안 물체 최대 위치 편차(m). **≤ 0.001이어야 한다**
  - 풀 파일: `/data/juhyoung_qdd/data/pool/ep<seed>.npz` + `ep<seed>.jsonl`(결정 시점 스냅샷 10개 + 연속 스냅샷 열의 텍스트 상태·오라클 정답·`ambiguous` 표시)
  - 경계 사례 30% 과표집: 히스테리시스 띠 안 술어가 있는 결정 시점을 우선 뽑는다. 가중치 열 `w_natural`, `w_oversample`.

- [ ] **Step 1: 복원 교란 시험 먼저** — 시드 0 에피소드에서 10개 시점을 저장·복원해 `restore_drift_check`. 1 mm 넘으면 복원 방식을 바꾼다(과거 교훈: 재생 전 `write_joint_state_to_sim` 측정 쓰기가 컵을 흔들었다 — 복원은 **한 번만**, 매 스텝 쓰기 금지).
- [ ] **Step 2: 풀 생성** — POOL 시드 2000–2119, 섭동 P0–P2만(시드로 배정), GPU 0·1·3에 프로세스 3개로 나눠(하네스·Isaac 모두 순차라 병렬은 프로세스 분할 — 정본 §42).
- [ ] **Step 3: 풀 점검** — 스냅샷 수 1,200, 에피소드 단위 분할 표시, `ambiguous` 비율, 과표집 비율 30% ± 2%, 연속 스냅샷 간격 0.33 s ± 0.01.
- [ ] **Step 4: DC4 관문** — DEV 성공률 ≥ 90% + 복원 편차 ≤ 1 mm + 풀 1,200 → 태그 `stage3-dc4`. 방향 질문 6개.
- [ ] **Step 5: 커밋** — `stage3 T13: snapshot pool with continuous snapshots`(풀 요약 md만)

---

### Task 14: 결과 기반 라벨러

**Files:**
- Create: `harvest/sim/labeler.py`, `harvest/cli_label.py`

**Interfaces:**
- Consumes: `restore_state`, `OraclePlanner`, `success_from_history`
- Produces: `label(env, snap: dict, question: str, options: list[Option]) -> {"best": set[str], "scores": {option_key: float}}` — 보기마다 복원 → 그 보기 한 스텝 실행 → 오라클 플래너로 최대 10 s(시뮬 시간) → 성공이면 1, 아니면 진행 점수(단계 번호 + 잔여 거리 정규화). 최고 점수와 같은 보기 **집합**이 정답(E §2A.3, D4 F5).
- 라벨은 보기 이름 판(A0–A4)과 무관하게 `option_key`당 한 번만(E §2A.7).

- [ ] **Step 1: 순수 로직 테스트** — `best_set({"a":1.0,"b":1.0,"c":0.4}) == {"a","b"}`, 동점 허용 오차 1e-6.
- [ ] **Step 2: 파드 검증** — DEV 에피소드 3개에서 오라클 정답 보기가 `best` 집합에 드는 비율 ≥ 95%(라벨러 자체 점검). 아니면 롤아웃 길이·점수식을 고치고 이유를 기록.
- [ ] **Step 3: 풀 전체 라벨** — `dir_xy`, `dir_z`, `mag_coarse`, H안(`target`, `phase`, `fine_dir`) 결정 스텝 전부. 프레임 기록 없이(`--record` 끔, 빠른 검증 규칙).
- [ ] **Step 4: 커밋** — `stage3 T14: outcome-based labeler`

---

### Task 15: E0.5 재생 실행과 판정 1–10 (DC5)

**Files:**
- Create: `harvest/replay.py`, `harvest/analysis/replay.py`, `harvest/cli_e05.py`, `tests/test_replay.py`, `docs/stage3/results/e05.md`

**Interfaces:**
- Consumes: 풀, 라벨, 잠정 `d_p95`(Task 8), `JevClient`, `variant`, `to_option_key`
- Produces:
  - `replay_plan(pool, d_p95, T_c=0.33) -> list[Ask]` — 결정 스텝마다: 시차 3표(t_s − d_p95 − {0, 0.33, 0.66}) + 재시험 1 + 같은 시각 K=3 + 판 A0–A4 + (ii) A0 반복 2회. 층별 300 스텝 이상.
  - 규칙: `newest(votes)`, `la2(votes, gamma=0.67)`(합의 안 되면 첫 표), `c2pp(votes, half_life=0.33)`, `c2p(votes, s1_scores, lam=3, tau=5, T_vlm=1)`(값만), `c2p_s`(λ=1, 기록만)
  - `judge_e05(results) -> dict` — E §2A.6 판정 1–10을 그대로 코드로. 반환: `claim`("narrow_to_b" | "keep_a" | "a_as_stabilizer"), `c_flip_default`, `c5a3_caveat: bool`, `name_rule` 층별("neutral" | "keep" | "undecided"), `c3pp_required: bool`, `time_block_effect: bool`
- 요청 속도 400/분 이하(E §2A.8).

- [ ] **Step 1: 실패 테스트**

```python
# tests/test_replay.py
from harvest.analysis.replay import newest, la2, c2pp, judge_e05

def V(*pairs): return [{"t_req": t, "key": k} for t, k in pairs]

def test_newest_uses_request_time():
    assert newest(V((-1.0, "a"), (-0.3, "b"), (-0.6, "c"))) == "b"

def test_la2_consensus_or_first():
    assert la2(V((-1.0, "a"), (-0.6, "a"), (-0.3, "b"))) == "a"
    assert la2(V((-1.0, "a"), (-0.6, "b"), (-0.3, "c"))) == "a"

def test_c2pp_decay_prefers_recent_ties():
    assert c2pp(V((-1.0, "a"), (-0.3, "b"))) == "b"

def test_judgment1_narrows_claim():
    res = {"flip_rate_success": 0.01, "gain_la2": 0.005, "gain_c2pp": 0.004, "gain_la2_lo": -0.01, "gain_c2pp_lo": -0.01}
    assert judge_e05(res)["claim"] == "narrow_to_b"

def test_judgment2_keeps_a():
    res = {"flip_rate_success": 0.08, "gain_la2": 0.03, "gain_c2pp": 0.01, "gain_la2_lo": 0.005, "gain_c2pp_lo": -0.01}
    assert judge_e05(res)["claim"] == "keep_a"

def test_judgment3_stabilizer():
    res = {"flip_rate_success": 0.08, "gain_la2": 0.01, "gain_c2pp": 0.01, "gain_la2_lo": -0.01, "gain_c2pp_lo": -0.01}
    assert judge_e05(res)["claim"] == "a_as_stabilizer"
```

- [ ] **Step 2: 실패 확인**
- [ ] **Step 3: 구현**

```python
# harvest/analysis/replay.py
"""E0.5 comparison rules and pre-registered judgments (E §2A.6)."""
import math
from collections import Counter

def newest(votes):
    return max(votes, key=lambda v: v["t_req"])["key"]

def la2(votes, gamma=2 / 3):
    # γ = 0.67 in the canon means "2 of 3"; compare with tolerance so 2/3 = 0.667 passes
    c = Counter(v["key"] for v in votes); k, n = c.most_common(1)[0]
    ok = n >= 2 and n / len(votes) >= gamma - 1e-3
    return k if ok else sorted(votes, key=lambda v: v["t_req"])[0]["key"]

def c2pp(votes, half_life=0.33):
    w = Counter()
    for v in votes:
        w[v["key"]] += 0.5 ** (-v["t_req"] / half_life)
    return w.most_common(1)[0][0]

def judge_e05(r):
    out = {}
    flip = r["flip_rate_success"]
    any_gain = (r["gain_la2"] >= 0.02 and r["gain_la2_lo"] > 0) or (r["gain_c2pp"] >= 0.02 and r["gain_c2pp_lo"] > 0)
    if flip < 0.05 and r["gain_la2"] < 0.02 and r["gain_c2pp"] < 0.02:
        out["claim"] = "narrow_to_b"
    elif flip >= 0.05 and any_gain:
        out["claim"] = "keep_a"
    elif flip >= 0.05:
        out["claim"] = "a_as_stabilizer"
    else:
        out["claim"] = "undecided"   # flip < 5% but gain ≥ 2pt: not covered by 1-3, report as-is
    if "perturb_flip" in r:
        out["c_flip_keep"] = r["perturb_flip"] >= 2 * flip and r["auroc_best"] >= 0.7
        out["c_flip_default"] = r["auroc_best_name"] if r["auroc_gap"] >= 0.03 else "tv_distance"
    if "same_time_flip" in r:
        out["c5a3_caveat"] = r["same_time_flip"] < 0.01
    if "layers" in r:
        out["name_rule"] = {}
        for L, d in r["layers"].items():
            if d["a1_minus_a0_lo"] >= -0.02 and d["a3_follow_minus_floor_lo"] > 0:
                out["name_rule"][L] = "neutral"
            elif d["a0_minus_a1_lo"] > 0:
                out["name_rule"][L] = "keep"
            else:
                out["name_rule"][L] = "undecided"
        out["c3pp_required"] = any(d["a4_flip"] >= 0.05 for d in r["layers"].values())
    if "block_diff_lo" in r:
        out["time_block_effect"] = r["block_diff_lo"] > 0
    return out
```

`"undecided"` 분기는 사전 등록 판정 1–3이 덮지 않는 경우(flip < 5%인데 이득 ≥ 2%p)를 숨기지 않으려는 것이다. 결과 문서에 그대로 적고 판정을 새로 만들지 않는다.

- [ ] **Step 4: 통과 확인**
- [ ] **Step 5: 실행(파드)** — `python -m harvest.cli_e05 --pool … --labels … --d-p95 <잠정값> --rpm 400`. 첫 실행 기록 첫 줄에 `prereg.json` 해시.
- [ ] **Step 6: 분석** — 성공·섭동 궤적 분리, 에피소드 군집 부트스트랩 10,000회, Holm. `judge_e05` 결과를 `docs/stage3/results/e05.md`에 표로. 개루프 한계 문장을 결과에 명시(E §2A.6 끝).
- [ ] **Step 7: 재실행 규칙** — E0 4일 뒤 최종 `d_p95`가 잠정값과 0.33 s 넘게 다르면 재생 1회 더, 그 결과로 판정(첫 결과도 보고).
- [ ] **Step 8: DC5 관문** — 판정을 정본 새 절(§43 이후)로 기록. `claim == "narrow_to_b"`면 **M4 컨트리뷰션 문장을 (b) 중심으로 좁히는 수정**을 논문·SUMMARY·M4에 반영(판정 1이 요구하는 것, 방향 수정이지 되돌아가기 아님). 방향 질문 6개 → 태그 `stage3-dc5`.
- [ ] **Step 9: 커밋** — `stage3 T15: E0.5 replay, judgments 1-10`

---

### Task 16: E3-ST 오프라인 스테레오 안정성 (DC6, E0와 병행 가능)

**Files:**
- Create: `harvest/stereo/__init__.py`, `harvest/stereo/data.py`, `harvest/stereo/pipeline.py`, `harvest/cli_e3st.py`, `tests/test_stereo_metrics.py`, `docs/stage3/results/e3st.md`

**Interfaces:**
- Produces:
  - `load_pairs(repo: str, episode: int, max_frames: int) -> Iterator[(t, left: np.ndarray, right: np.ndarray)]` — `ROBOTIS/Task_0001_CoffeeClassification`·`Task_0002_OrderPicking`, 키 `cam_head`·`cam_head_right`(D21). 실제 키 이름은 Step 1에서 메타데이터로 확인.
  - `centroid_3d(depth: np.ndarray, mask: np.ndarray, K: np.ndarray) -> np.ndarray(3)` — 마스크 안 유효 깊이의 중앙값 역투영
  - `stability(centroids: list[np.ndarray]) -> {"median_jitter_mm", "p95_jitter_mm"}`, `flip_rate(pred_series: list[bool|None]) -> float`
- 한계(결과에 명시): 정답 자세 없음 → 정확도 아님, mp4 압축, 보정값 미확인(기선 63 mm·내부 행렬은 ZED Mini 공칭값 [가정]).

- [ ] **Step 1: 데이터 확인** — HF 메타데이터(`meta/info.json`)만 먼저 받아 카메라 키·해상도·fps·라이선스를 `e3st.md`에. 라이선스가 사용 불가면 E3-ST 보류 표시하고 멈춤.
- [ ] **Step 2: 실패 테스트**

```python
# tests/test_stereo_metrics.py
import numpy as np
from harvest.stereo.pipeline import centroid_3d, stability, flip_rate

def test_centroid_backprojects_center():
    K = np.array([[500, 0, 50], [0, 500, 50], [0, 0, 1.0]])
    depth = np.full((100, 100), 1.0); mask = np.zeros((100, 100), bool); mask[45:56, 45:56] = True
    c = centroid_3d(depth, mask, K)
    assert np.allclose(c, [0, 0, 1.0], atol=1e-3)

def test_stability_mm():
    cs = [np.array([0, 0, 1.0]) + np.array([0.001 * (i % 2), 0, 0]) for i in range(10)]
    s = stability(cs)
    assert 0.9 <= s["median_jitter_mm"] <= 1.1

def test_flip_rate_ignores_unknown():
    assert flip_rate([True, True, None, False, False]) == 1 / 3
```

- [ ] **Step 3: 구현** — `centroid_3d`는 마스크 픽셀 `(u,v,z)`를 `K⁻¹[u,v,1]·z`로 역투영한 뒤 성분별 중앙값. `stability`는 연속 프레임 사이 유클리드 거리(mm)의 중앙값·p95. `flip_rate`는 `None`(unknown)을 먼저 빼고 남은 값의 연속 쌍 중 값이 바뀐 비율(`[T,T,None,F,F]` → `[T,T,F,F]` → 3쌍 중 1 = 1/3).
- [ ] **Step 4: 모델 준비(파드, GPU 0)** — Fast-FoundationStereo(NVIDIA 공식 저장소, CVPR 2026, 1,497★)와 SAM 3.1(Meta 공식)을 `/data/juhyoung_qdd/models/`에 받는다. 두 저장소 커밋 해시를 기록.
- [ ] **Step 5: 실행** — 과제별 에피소드 20편 × 최대 300프레임(10 fps, 30 s). 물체 프롬프트는 과제 문장에서 뽑은 명사(예: "cup", "box"). T1 술어는 `near`·`above`(두 물체가 보일 때)만.
- [ ] **Step 6: 결과** — `e3st.md`에 과제별 중앙값·p95 흔들림(mm), 술어 뒤집힘 비율, 깊이 무효 비율, 예시 프레임 4장(좌 영상 + 깊이 + 마스크). 이 값은 "M1 T1 문턱(cm)에 비해 흔들림이 작은가"를 보는 탐색 자료다. 판정 문턱 없음.
- [ ] **Step 7: DC6 관문** — 방향 질문 6개, 태그 `stage3-dc6`.
- [ ] **Step 8: 커밋** — `stage3 T16: E3-ST offline stereo stability`

---

## 이 계획 뒤 (관문 통과 뒤 따로 계획을 쓴다)

| 다음 계획 | 선행 관문 | 내용 |
|---|---|---|
| E1 보정 + E-M3-1 | DC4 | 풀·라벨 위 질문 유형·보기 이름·수·위치 보정, J5 conformal 준비 |
| E3a M1 형식 | DC4 | 후보 A/B/C·대조군 오프라인 비교(Astra 포함) |
| E2a 마차 시험 | DC2·DC5·E1 | 룰 대 Jev C1(M4 없이), TEST 시드 첫 개봉 |
| Inspect Robots P1–P4 | DC3 | `aiworker` 몸체·`OursPolicy`·기준선·짝 파일럿 |

- 일정 확인(방향 질문 6): 오늘 2026-09-24, 마감 2026-11-16 AoE까지 약 7.5주. 이 계획(0주 + 1주)은 약 2주로 잡는다. E2a·P1–P4·E-M4까지 합치면 남는 여유가 적다 → 2주차 DC마다 범위 축소안을 같이 올린다.

## 실행 전 사용자 확인이 필요한 것

1. **TypeSafe(Jev) API 키 파일 위치** — 메모리에 없다. 알려 주시면 파드에는 stdin으로 1회만 옮긴다.
2. **Astra 호출 키** — 메모리의 OpenAI 키 파일(`openai_api_key.txt`)을 Astra 호출에 써도 되는지.
3. **비용 한도** — 이 계획의 추정: Jev E0 약 $14–18 + E0.5 약 $1–5, Astra 첫 토큰·반복 약 $5–20 [가정]. 합계 약 $20–45.
