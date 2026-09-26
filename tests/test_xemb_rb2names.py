"""tools/xemb/src_rb2.names_of: object names from the RB2 instruction (no generic 'object' / 'target')."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xemb.src_rb2 import names_of  # noqa: E402


def test_put_into():
    assert names_of("Put the black wrench into the crate.") == ("black wrench", "crate")
    assert names_of("Put the tool with the wooden handle into the crate.") == ("tool with the wooden handle", "crate")


def test_place_on_and_grasp():
    assert names_of("Place the crate on the table.") == ("crate", "table")
    assert names_of("Grasp the handle of the crate.") == ("handle of the crate", "table")
