"""Controller ruling O2b (review of Task 8): head-image colours alone cannot tell the committed-next-motion arrow
from the remaining-offset-correction arrow (both must live in the one R2-palette-safe green band, O2 review finding
I2), so they must also differ by PATTERN -- solid/filled-head vs. dashed/open-head -- and axis lines must have no
arrowhead at all (unlike the wrist corner box's old design, where axes and both arrows were the same glyph). These
tests check the drawing primitives directly (white-box: _stroke/_head/_axis_line/_arrow are the actual mechanism)
plus one black-box check that the two arrows are not pixel-identical in the full image."""
import numpy as np
from PIL import Image, ImageDraw

from harvest.couple.overlay import CamModel, _arrow, _axis_line, _head, _stroke, draw_overlay


def _canvas():
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _alpha_count(img):
    return int((np.array(img)[:, :, 3] > 0).sum())


def test_filled_head_covers_more_area_than_an_open_head_of_the_same_size():
    img1, d1 = _canvas()
    _head(d1, (50, 50), 0.0, (255, 255, 255), filled=True, size=9)
    img2, d2 = _canvas()
    _head(d2, (50, 50), 0.0, (255, 255, 255), filled=False, size=9)
    assert _alpha_count(img1) > _alpha_count(img2)  # a filled triangle covers strictly more than two open strokes


def test_dashed_stroke_has_gaps_a_solid_stroke_does_not():
    def runs(row):
        row = row.astype(bool)
        return int(np.count_nonzero(row[1:] & ~row[:-1])) + (1 if row[0] else 0)

    img1, d1 = _canvas()
    _stroke(d1, (10, 50), (90, 50), (255, 255, 255), 2, dashed=False, outline=False)
    img2, d2 = _canvas()
    _stroke(d2, (10, 50), (90, 50), (255, 255, 255), 2, dashed=True, outline=False)
    row1 = np.array(img1)[50, :, 3] > 0
    row2 = np.array(img2)[50, :, 3] > 0
    assert runs(row1) == 1        # one continuous run: a solid shaft
    assert runs(row2) > 1         # multiple separate runs: dash gaps


def test_axis_line_has_no_arrowhead_blob_unlike_an_arrow():
    img1, d1 = _canvas()
    _axis_line(d1, (10, 50), (90, 50), (255, 255, 255), width=1)
    img2, d2 = _canvas()
    _arrow(d2, (10, 50), (90, 50), (255, 255, 255), width=1, filled_head=True, head_size=9)
    # the arrow's filled head adds a visible pixel blob well beyond what the (thinner, headless) axis line covers
    assert _alpha_count(img2) > _alpha_count(img1) + 20


def test_next_and_offset_arrows_are_not_pixel_identical_in_the_head_image():
    R = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])
    cam = CamModel.from_dict({"K": [[100, 0, 80], [0, 100, 60], [0, 0, 1]], "R": R.tolist(), "t": [0, 0, 0],
                             "W": 160, "H": 120})
    img = np.zeros((120, 160, 3), np.uint8)
    tip = np.array([1.0, 0.0, 0.0])
    vec = np.array([0.0, -0.15, 0.0])  # long enough (~15 px) for the offset arrow's dashes to show gaps
    base = draw_overlay(img, cam, tip=tip, trace=[], next_vec=None, offset_vec=None, wrist=False)
    nxt = draw_overlay(img, cam, tip=tip, trace=[], next_vec=vec, offset_vec=None, wrist=False)
    off = draw_overlay(img, cam, tip=tip, trace=[], next_vec=None, offset_vec=vec, wrist=False)
    nxt_added = int(np.any(nxt.astype(int) != base.astype(int), axis=2).sum())
    off_added = int(np.any(off.astype(int) != base.astype(int), axis=2).sum())
    assert nxt_added > 0 and off_added > 0 and nxt_added != off_added  # solid+filled vs dashed+open: different pixel counts
