"""L9 v2 asset lists: Poly Haven decor (floor pieces join the mesh furniture, tabletop pieces their own pool),
materials v2 (absolute paths), licences."""
import os

from harvest.l9 import assets9 as A9


def test_ph_floor_pieces_in_furniture_mesh():
    fm = A9.furniture_mesh("train")
    ph = [k for k, r in fm.items() if str(r.get("source", "")).startswith("https://polyhaven.com/")]
    assert len(ph) >= 100 and all(fm[k].get("kind") != "tabletop" for k in ph)
    assert all(A9.licence_ok(fm[k]["license"]) for k in ph)


def test_tabletop_pool():
    allt = A9.tabletop_decor("train")
    assert len(allt) >= 80 and all(r["kind"] == "tabletop" for r in allt.values())
    a, b = A9.tabletop_for(0), A9.tabletop_for(1)
    assert len(a) == A9.TABLETOP_N and set(a) != set(b)
    assert not set(A9.tabletop_decor("ood")) & set(allt)


def test_materials_v2_absolute():
    import json
    t = json.load(open(os.path.join(A9.DIR, "materials_l9v2.json")))["materials"]
    assert len(t) >= 1500
    for r in t.values():
        assert all(os.path.isabs(v) or v.startswith("/") for v in r["files"].values())
        assert A9.licence_ok(r["license"])


def test_hint_pools_non_empty():
    import json
    from harvest.l9 import world9 as W
    cat = {}
    for fn in ("materials_l9.json", "materials_l9v2.json"):
        cat.update(json.load(open(os.path.join(A9.DIR, fn)))["materials"])
    for h in W.HINT_GROUPS:
        assert len(W.hint_pool(cat, h, "train")) >= 5, h
    assert W.material_pool(cat, "floor", "train", "outdoor") and W.material_pool(cat, "floor", "train", "indoor")


def test_import_order_fresh(tmp_path):
    """assets9.mesh_for / vary9 light pick before scene9 is imported (no circular import with scene9_more)."""
    import subprocess
    import sys
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    f = tmp_path / "imp.py"
    f.write_text("import sys\nsys.path.insert(0, %r)\nfrom harvest.l9 import assets9 as A9\nassert len(A9.mesh_for(1)) > 6\n"
                 "from harvest.l9 import vary9 as V\nprint(V.pick_light_family(1, 'picnic_outdoor'))\n" % root)
    r = subprocess.run([sys.executable, str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]
