import importlib.util, pathlib
import pytest

spec = importlib.util.spec_from_file_location("ph", pathlib.Path(__file__).parents[1] / "tools/prereg_hash.py")
ph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ph)

DOC = "## 2\n### 2.7 판정 기준 (사전 등록)\nA\r\nB\n### 2.8 다음\nC\n"


def test_hash_ignores_crlf_and_stops_at_next_heading():
    h1 = ph.section_hash(DOC, "### 2.7")
    h2 = ph.section_hash(DOC.replace("\r\n", "\n"), "### 2.7")
    assert h1 == h2
    assert h1 != ph.section_hash(DOC.replace("B", "B2"), "### 2.7")
    assert h1 == ph.section_hash(DOC.replace("C", "C2"), "### 2.7")


def test_missing_heading_raises():
    with pytest.raises(KeyError):
        ph.section_hash(DOC, "### 9.9")
