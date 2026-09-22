import numpy as np
import pytest

from ascii_common import (
    MODE_CHARS, SHAPE_MODES, frame_to_text, is_shape_mode,
    render_shape_palette, shape_indices,
)


@pytest.mark.parametrize("mode", SHAPE_MODES)
def test_every_pattern_has_a_unique_glyph(mode):
    sub_x, sub_y, chars = SHAPE_MODES[mode]
    assert len(chars) == 2 ** (sub_x * sub_y)
    assert len(set(chars)) == len(chars)
    assert chars[0] == " "
    assert chars[-1] == "█"


def test_known_octant_patterns():
    chars = MODE_CHARS["octants"]
    assert chars[0b00001111] == "▀"
    assert chars[0b11110000] == "▄"
    assert chars[0b01010101] == "▌"
    assert chars[0b10101010] == "▐"


def test_modes_are_exposed_to_the_cli():
    for mode in SHAPE_MODES:
        assert is_shape_mode(mode)
        assert MODE_CHARS[mode] is SHAPE_MODES[mode][2]
    assert not is_shape_mode("chars")


def half_lit_frame(w=16, h=16):
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, : w // 2] = 255
    return frame


def test_shape_indices_follow_sub_cell_layout():
    gray = np.zeros((8, 8), dtype=np.uint8)
    gray[:, :4] = 255
    indices = shape_indices(gray, rows=1, cols=1, mode="octants")
    assert MODE_CHARS["octants"][indices[0, 0]] == "▌"


def test_shape_indices_invert():
    gray = np.zeros((8, 8), dtype=np.uint8)
    gray[:, :4] = 255
    indices = shape_indices(gray, rows=1, cols=1, mode="octants", invert_brightness=True)
    assert MODE_CHARS["octants"][indices[0, 0]] == "▐"


def test_flat_cells_are_solid_not_noisy():
    gray = np.zeros((8, 16), dtype=np.uint8)
    gray[:, :8] = 200
    indices = shape_indices(gray, rows=1, cols=2, mode="octants")
    assert [MODE_CHARS["octants"][i] for i in indices[0]] == ["█", " "]


def test_frame_to_text_uses_sub_cell_resolution():
    frame = half_lit_frame(w=16, h=16)
    text = frame_to_text(frame, char_w=8, char_h=8, chars=MODE_CHARS["octants"], mode="octants")
    assert text.splitlines() == ["█ ", "█ "]


def test_render_shape_palette_tiles_the_whole_cell():
    palette = render_shape_palette(6, 8, (0, 0, 0), (255, 255, 255), "octants")
    assert palette.shape == (256, 8, 6, 3)
    assert (palette[0] == 0).all()
    assert (palette[-1] == 255).all()
    top_left = palette[0b00000001]
    assert (top_left[0:2, 0:3] == 255).all()
    assert top_left.sum() == 2 * 3 * 3 * 255
