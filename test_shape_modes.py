import cv2
import numpy as np
import pytest

from ascii_common import (
    MASK_MODES, MASK_PAIRS, MASK_RES, MODE_CHARS, SHAPE_MODES, AsciiFrameOptions,
    frame_to_text, is_mask_mode, is_shape_mode, mask_cell_colors, mask_indices,
    process_frame, render_mask_palette, render_shape_palette, shape_indices,
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


def test_fg_only_drops_background_codes():
    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    frame[:, :4] = (200, 100, 50)
    text = frame_to_text(frame, char_w=8, char_h=8, chars=MODE_CHARS["octants"],
                         mode="octants", ansi_colors=True, ansi_fg_only=True)
    assert text == "\x1b[38;2;200;100;50m▌\x1b[0m"


def test_fg_only_fills_blank_cells_with_their_color():
    frame = np.zeros((8, 16, 3), dtype=np.uint8)
    frame[:, :8] = (200, 100, 50)
    frame[:, 8:] = (60, 0, 0)
    for mode in ("octants", "wedges"):
        text = frame_to_text(frame, char_w=8, char_h=8, chars=MODE_CHARS[mode],
                             mode=mode, ansi_colors=True, ansi_fg_only=True)
        assert text == "\x1b[38;2;200;100;50m█\x1b[38;2;60;0;0m█\x1b[0m"



def test_ramp_ansi_keeps_dark_opaque_cells_and_blanks_transparent():
    frame = np.zeros((8, 24, 3), dtype=np.uint8)
    frame[:, 8:16] = (40, 0, 0)
    frame[:, 16:] = (250, 250, 250)
    alpha = np.full((8, 24), 255, dtype=np.uint8)
    alpha[:, :8] = 0
    text = frame_to_text(frame, char_w=8, char_h=8, chars=MODE_CHARS["blocks"], mode="blocks",
                         ansi_colors=True, ansi_fg_only=True, alpha=alpha)
    assert text == " \x1b[38;2;40;0;0m░\x1b[38;2;250;250;250m█\x1b[0m"


def test_fg_only_leaves_transparent_cells_blank():
    frame = np.zeros((8, 16, 3), dtype=np.uint8)
    frame[:, :8] = (200, 100, 50)
    alpha = np.full((8, 16), 255, dtype=np.uint8)
    alpha[:, 8:] = 0
    text = frame_to_text(frame, char_w=8, char_h=8, chars=MODE_CHARS["octants"],
                         mode="octants", ansi_colors=True, ansi_fg_only=True, alpha=alpha)
    assert text == "\x1b[38;2;200;100;50m█ \x1b[0m"

def diagonal_cell(size=48, slope=0.5):
    """Cell lit below the cut from the upper left corner to the lower centre."""
    axis = (np.arange(size) + 0.5) / size
    x, y = np.meshgrid(axis, axis)
    return np.where(x < slope * y, 255, 0).astype(np.uint8)


@pytest.mark.parametrize("mode", MASK_MODES)
def test_mask_alphabets_are_unique_and_complete(mode):
    chars, masks = MASK_MODES[mode]
    assert len(set(chars)) == len(chars)
    assert " " in chars and "█" in chars
    assert masks.shape == (len(chars), MASK_RES * MASK_RES)
    assert (masks >= 0).all() and (masks <= 1).all()


@pytest.mark.parametrize("mode", MASK_MODES)
def test_every_glyph_has_its_complement(mode):
    chars, masks = MASK_MODES[mode]
    reps, mates = MASK_PAIRS[mode]
    assert len(reps) * 2 == len(chars)
    assert np.allclose(masks[reps] + masks[mates], 1.0, atol=1e-4)


def test_wedge_alphabet_covers_the_unicode_run():
    chars = MODE_CHARS["wedges"]
    diagonals = [c for c in chars if 0x1FB3C <= ord(c) <= 0x1FB67]
    assert len(diagonals) == 0x1FB68 - 0x1FB3C


def area_of(char, mode="wedges"):
    chars, masks = MASK_MODES[mode]
    return masks[chars.index(char)].mean()


def test_wedge_areas_match_their_geometry():
    assert area_of("🭀") == pytest.approx(0.25)  # corner to lower centre, quarter cell
    assert area_of("🬼") == pytest.approx(1 / 12, abs=1e-3)  # lower third of the left edge
    assert area_of("🭬") == pytest.approx(0.25)  # left triangular quarter
    assert area_of("🭨") == pytest.approx(0.75)  # its three quarter complement
    assert area_of("▀") == pytest.approx(0.5)


def test_wedge_fits_a_slanted_edge():
    indices = mask_indices(diagonal_cell(), rows=1, cols=1, mode="wedges")
    assert MODE_CHARS["wedges"][indices[0, 0]] == "🭀"


def test_wedge_invert_draws_the_other_half():
    indices = mask_indices(diagonal_cell(), rows=1, cols=1, mode="wedges", invert_brightness=True)
    assert MODE_CHARS["wedges"][indices[0, 0]] == "🭖"


def test_wedge_flat_cells_stay_solid():
    gray = np.zeros((8, 16), dtype=np.uint8)
    gray[:, :8] = 200
    indices = mask_indices(gray, rows=1, cols=2, mode="wedges")
    assert [MODE_CHARS["wedges"][i] for i in indices[0]] == ["█", " "]


def test_hybrid_keeps_whichever_fits_better():
    eighth = np.zeros((16, 16), dtype=np.uint8)
    eighth[:4, :8] = 255  # one octant sub-cell, no wedge can cut that corner
    assert MODE_CHARS["wedges-octants"][mask_indices(eighth, 1, 1, "wedges-octants")[0, 0]] == MODE_CHARS["octants"][1]
    assert MODE_CHARS["wedges-octants"][mask_indices(diagonal_cell(), 1, 1, "wedges-octants")[0, 0]] == "🭀"


def test_hybrid_alphabet_holds_both_sets():
    hybrid = set(MODE_CHARS["wedges-octants"])
    assert hybrid >= set(MODE_CHARS["wedges"]) | set(MODE_CHARS["octants"])


def test_mask_modes_are_exposed_to_the_cli():
    for mode in MASK_MODES:
        assert is_shape_mode(mode) and is_mask_mode(mode)
        assert MODE_CHARS[mode] == MASK_MODES[mode][0]
    assert not is_mask_mode("octants")


def test_render_mask_palette_blends_by_coverage():
    palette = render_mask_palette(6, 8, (0, 0, 0), (255, 255, 255), "wedges")
    chars = MODE_CHARS["wedges"]
    assert palette.shape == (len(chars), 8, 6, 3)
    assert (palette[chars.index(" ")] == 0).all()
    assert (palette[chars.index("█")] == 255).all()
    wedge = palette[chars.index("🭀")]
    assert wedge[7, 0] == pytest.approx(255)  # lower left corner is inside the cut
    assert (wedge[0, 5] == 0).all()  # upper right corner is outside it
    assert wedge.mean() == pytest.approx(255 * 0.25, rel=0.05)


def test_wedge_cell_colors_split_across_the_cut():
    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    frame[:, :8] = (200, 100, 50)
    indices = mask_indices(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), 1, 1, "wedges")
    fg, bg = mask_cell_colors(frame.astype(np.float32), 1, 1, "wedges", indices)
    assert MODE_CHARS["wedges"][indices[0, 0]] == "▌"
    assert fg[0, 0] == pytest.approx([200, 100, 50], abs=1)
    assert bg[0, 0] == pytest.approx([0, 0, 0], abs=1)


def test_frame_to_text_wedges_with_ansi():
    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    frame[:, :8] = (200, 100, 50)
    text = frame_to_text(frame, char_w=16, char_h=16, chars=MODE_CHARS["wedges"],
                         mode="wedges", ansi_colors=True)
    assert text == "\x1b[38;2;200;100;50;48;2;0;0;0m▌\x1b[0m"


def test_process_frame_draws_wedges():
    frame = np.repeat(diagonal_cell()[:, :, np.newaxis], 3, axis=2)
    palette = render_mask_palette(48, 48, (0, 0, 0), (255, 255, 255), "wedges")
    options = AsciiFrameOptions(char_palette=palette, char_w=48, char_h=48, mode="wedges")
    out = process_frame(frame, options)
    assert out.shape == (48, 48, 3)
    assert (out == palette[MODE_CHARS["wedges"].index("🭀")]).all()
