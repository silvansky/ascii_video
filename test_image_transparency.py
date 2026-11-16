import numpy as np
import pytest
from PIL import Image

import ascii_image


@pytest.mark.parametrize("mode", ["chars", "octants", "wedges"])
@pytest.mark.parametrize("preserve_colors", [False, True])
def test_transparent_image_keeps_foreground_and_source_alpha(tmp_path, monkeypatch, mode, preserve_colors):
    monkeypatch.setattr(ascii_image, "measure_font_metrics", lambda font: (16, 16))
    source = np.full((32, 32, 4), 255, dtype=np.uint8)
    source[:, 8:16, :3] = 0
    source[:16, :, 3] = 128
    source[16:, :, 3] = 0
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    Image.fromarray(source).save(input_path)

    ascii_image.process_image_numpy(
        str(input_path), ascii_image.load_font(10), str(output_path),
        mode=mode, fg_color=(10, 20, 30), preserve_colors=preserve_colors,
        tint_color=(255, 0, 0), transparent_bg=True,
    )

    with Image.open(output_path) as result:
        assert result.mode == "RGBA"
        pixels = np.array(result)
    assert pixels[:16, :, 3].max() == 128
    assert (pixels[16:, :, 3] == 0).all()
    assert (pixels[:16, :16, 3] == 0).any()  # Space around glyphs stays clear.
    visible = pixels[..., 3] > 0
    if preserve_colors:
        assert (pixels[..., 1:3][visible] == 0).all()  # Tint is preserved.
        assert pixels[..., 0][visible].max() == 255
    else:
        assert (pixels[..., :3][visible] == (10, 20, 30)).all()


def test_transparent_background_rejects_jpeg(tmp_path):
    with pytest.raises(ValueError, match="requires PNG, WebP or TIFF"):
        ascii_image.process_image_numpy("unused.png", None, str(tmp_path / "out.jpg"), transparent_bg=True)


def test_transparent_cli_defaults_to_png(tmp_path, monkeypatch):
    input_path = tmp_path / "input.jpg"
    Image.new("RGB", (64, 64), "white").save(input_path)
    monkeypatch.setattr("sys.argv", ["ascii_image.py", str(input_path), "--transparent-bg"])
    ascii_image.main()
    with Image.open(tmp_path / "input_ascii.png") as result:
        assert result.mode == "RGBA"
        assert result.getchannel("A").getextrema() == (0, 255)


@pytest.mark.parametrize("mode", ["chars", "sextants", "wedges"])
@pytest.mark.parametrize("fg_only", [False, True])
def test_transparent_ansi_keeps_dark_background_blank(mode, fg_only):
    from ascii_common import MODE_CHARS, frame_to_text

    frame = np.full((16, 32, 3), 255, dtype=np.uint8)
    frame[:, :16] = 1  # Near-black JPEG background with no alpha channel.
    text = frame_to_text(
        frame, 16, 16, MODE_CHARS[mode], mode=mode,
        ansi_colors=True, ansi_fg_only=fg_only, transparent_bg=True,
    )
    assert text.startswith(" \x1b[38;2;255;255;255m")
    assert "48;2" not in text
    assert text.endswith("\x1b[0m")


def test_transparent_text_cli(tmp_path, monkeypatch):
    import re

    source = np.full((64, 64, 3), 255, dtype=np.uint8)
    source[:, :32] = 1
    input_path = tmp_path / "input.jpg"
    output_path = tmp_path / "output.txt"
    Image.fromarray(source).save(input_path)
    monkeypatch.setattr("sys.argv", [
        "ascii_image.py", str(input_path), "--mode", "sextants", "--ansi-colors",
        "--adjust-aspect-ratio", "--ansi-fg-only", "--transparent-bg", "-o", str(output_path),
    ])
    ascii_image.main()
    text = output_path.read_text()
    assert "48;2" not in text
    plain = re.sub(r"\x1b\[[0-9;]*m", "", text)
    assert all(line.startswith(" ") and line.endswith("█") for line in plain.splitlines())


@pytest.mark.parametrize("mode", ["quadrants", "sextants", "octants", "wedges", "wedges-octants", "blocks"])
def test_transparent_fg_only_preserves_opaque_solid_colors(mode):
    from ascii_common import MODE_CHARS, frame_to_text

    frame = np.zeros((16, 64, 3), dtype=np.uint8)
    frame[:, 16:32] = (255, 0, 0)  # Red is below the grayscale midpoint.
    frame[:, 48:] = 255
    alpha = np.full((16, 64), 255, dtype=np.uint8)
    alpha[:, :16] = 0
    text = frame_to_text(
        frame, 16, 16, MODE_CHARS[mode], mode=mode,
        ansi_colors=True, ansi_fg_only=True, transparent_bg=True, alpha=alpha,
    )
    red_glyph, black_glyph = ("░", "░") if mode == "blocks" else ("█", "█")
    assert text == (
        f" \x1b[38;2;255;0;0m{red_glyph}"
        f"\x1b[38;2;0;0;0m{black_glyph}\x1b[38;2;255;255;255m█\x1b[0m"
    )


@pytest.mark.parametrize("mode", ["quadrants", "sextants", "octants", "wedges", "wedges-octants", "blocks"])
def test_transparent_fg_only_without_alpha_keeps_red_and_dark_gray(mode):
    from ascii_common import MODE_CHARS, frame_to_text

    frame = np.full((16, 64, 3), 2, dtype=np.uint8)
    frame[:, 16:32] = (255, 0, 0)
    frame[:, 32:48] = 20
    frame[:, 48:] = 255
    text = frame_to_text(
        frame, 16, 16, MODE_CHARS[mode], mode=mode,
        ansi_colors=True, ansi_fg_only=True, transparent_bg=True,
    )
    glyph = "░" if mode == "blocks" else "█"
    assert text == (
        f" \x1b[38;2;255;0;0m{glyph}"
        f"\x1b[38;2;20;20;20m{glyph}\x1b[38;2;255;255;255m█\x1b[0m"
    )


def test_transparent_fg_only_preserves_enclosed_black_details_without_alpha():
    from ascii_common import MODE_CHARS, frame_to_text

    frame = np.full((80, 80, 3), 2, dtype=np.uint8)
    frame[16:64, 16:64] = (255, 0, 0)
    frame[32:48, 32:48] = 0
    text = frame_to_text(
        frame, 16, 16, MODE_CHARS["sextants"], mode="sextants",
        ansi_colors=True, ansi_fg_only=True, transparent_bg=True,
    )
    assert text.splitlines()[0] == "     \x1b[0m"
    assert text.splitlines()[2] == (
        " \x1b[38;2;255;0;0m█\x1b[38;2;0;0;0m█\x1b[38;2;255;0;0m█ \x1b[0m"
    )
