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


def test_sgr_builds_truecolor_codes():
    from ascii_common import sgr

    assert sgr((1, 2, 3)) == "\x1b[38;2;1;2;3m"
    assert sgr((1, 2, 3), (4, 5, 6)) == "\x1b[38;2;1;2;3;48;2;4;5;6m"
    assert sgr(None, (4, 5, 6)) == "\x1b[48;2;4;5;6m"
    assert sgr() == ""


def ansi_of(patterns, fg, bg=None):
    from ascii_common import ansi_text

    chars = MODE_CHARS["octants"]
    indices = np.array([patterns])
    fg = np.array([fg], dtype=float)
    bg = None if bg is None else np.array([bg], dtype=float)
    return ansi_text(indices, chars, fg, bg)


def test_ansi_repeats_nothing_and_resets():
    line = ansi_of([0b11111111, 0b11111111], [(10, 20, 30), (10, 20, 30)])
    assert line == "\x1b[38;2;10;20;30m██\x1b[0m"


def test_ansi_omits_colors_the_glyph_cannot_show():
    blank = ansi_of([0], [(10, 20, 30)], [(1, 2, 3)])
    assert "38;2" not in blank and "48;2;1;2;3" in blank

    solid = ansi_of([255], [(10, 20, 30)], [(1, 2, 3)])
    assert "48;2" not in solid and "38;2;10;20;30" in solid


def test_frame_to_text_ansi_colors_lit_and_unlit_separately():
    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    frame[:, :4] = (200, 100, 50)  # left half bright, right half black
    text = frame_to_text(frame, char_w=8, char_h=8, chars=MODE_CHARS["octants"],
                         mode="octants", ansi_colors=True)
    assert text == "\x1b[38;2;200;100;50;48;2;0;0;0m▌\x1b[0m"


def test_frame_to_text_ansi_tint():
    frame = np.full((8, 8, 3), 255, dtype=np.uint8)
    frame[:, 4:] = 0
    text = frame_to_text(frame, char_w=8, char_h=8, chars=MODE_CHARS["octants"],
                         mode="octants", ansi_colors=True, tint_color=(255, 0, 0))
    assert "38;2;255;0;0" in text


def test_ramp_mode_ansi_has_foreground_only():
    frame = np.full((8, 8, 3), 255, dtype=np.uint8)
    text = frame_to_text(frame, char_w=8, char_h=8, chars=MODE_CHARS["chars"], ansi_colors=True)
    assert "38;2;255;255;255" in text and "48;2" not in text
