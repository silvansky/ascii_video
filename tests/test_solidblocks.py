import numpy as np
import pytest

from ascii_common import (
    AsciiFrameOptions, MODE_CHARS, frame_to_text, pre_render_chars, process_frame,
)


@pytest.mark.parametrize("invert", [False, True])
@pytest.mark.parametrize("ansi", [False, True])
@pytest.mark.parametrize("transparent", [False, True])
def test_solidblocks_keeps_dark_cells_solid(invert, ansi, transparent):
    frame = np.zeros((8, 32, 3), dtype=np.uint8)
    frame[:, :8] = (1, 2, 3)
    frame[:, 16:24] = (120, 20, 60)
    frame[:, 24:] = 255
    text = frame_to_text(
        frame, 8, 8, MODE_CHARS["solidblocks"], mode="solidblocks",
        invert_brightness=invert, ansi_colors=ansi, transparent_bg=transparent,
    )
    if ansi:
        first = " " if transparent else "\x1b[38;2;1;2;3m█"
        assert text == (first + "\x1b[38;2;0;0;0m█\x1b[38;2;120;20;60m█"
                        "\x1b[38;2;255;255;255m█\x1b[0m")
    else:
        assert text == (" ███" if transparent else "████")


def test_solidblocks_respects_alpha_and_averages_source_colors():
    frame = np.full((8, 16, 3), (200, 100, 50), dtype=np.uint8)
    frame[:4, :8] = (100, 0, 50)
    alpha = np.full((8, 16), 255, dtype=np.uint8)
    alpha[:, 8:] = 0
    text = frame_to_text(
        frame, 8, 8, MODE_CHARS["solidblocks"], mode="solidblocks",
        ansi_colors=True, ansi_fg_only=True, alpha=alpha, tint_color=(255, 0, 255),
    )
    assert text == "\x1b[38;2;150;0;50m█ \x1b[0m"


@pytest.mark.parametrize("preserve_colors", [False, True])
@pytest.mark.parametrize("invert", [False, True])
def test_solidblocks_raster_fills_entire_cells(preserve_colors, invert):
    palette = pre_render_chars(None, 8, 8, (0, 0, 0), (255, 255, 255), "solidblocks")
    frame = np.zeros((8, 16, 3), dtype=np.uint8)
    frame[:, 8:] = (120, 20, 60)
    result = process_frame(frame, AsciiFrameOptions(
        char_palette=palette, char_w=8, char_h=8, mode="solidblocks",
        preserve_colors=preserve_colors, invert_brightness=invert,
        alpha_palette=palette[..., 0],
    ))
    np.testing.assert_array_equal(result[..., :3], frame if preserve_colors else np.full_like(frame, 255))
    assert np.all(result[..., 3] == 255)
