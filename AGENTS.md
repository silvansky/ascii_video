# Repository instructions

## Documentation

- Update `README.md` whenever command-line arguments change, new tools are added, or setup, configuration, dependencies, or usage changes.
- Keep documented commands, options, defaults, and examples consistent with the implementation.
- Update this file when module responsibilities or the development workflow change.

## Project overview

This is a flat Python script repository for converting images and videos into
ASCII or emoji art, with an interactive terminal preview for ASCII images.
Run commands from the repository root; there is no package build step.

## Architecture

| File | Responsibility |
| --- | --- |
| `ascii_common.py` | Shared ASCII engine: mode registries, glyph geometry, font metrics, palette rendering, brightness/shape matching, ANSI text, transparency helpers, `AsciiFrameOptions`, and common CLI arguments. |
| `ascii_image.py` | ASCII image CLI, input loading/scaling, image or UTF-8 `.txt` output, and transparency handling. Exposes `create_parser`, `load_scaled_image`, and `render_text` for the TUI. |
| `ascii_video.py` | ASCII video CLI, rotation metadata via `ffprobe`, frame conversion through the shared engine, and MoviePy encoding with source audio. |
| `ascii_image_tui.py` | Textual app using the image CLI's parser and text rendering pipeline; debounced background previews, ANSI display, and text saving. |
| `emoji_common.py` | Emoji sets, font loading, average-color matching, pre-rendered palettes, `EmojiFrameOptions`, and common emoji CLI arguments. |
| `emoji_image.py`, `emoji_video.py` | Emoji image/text and video entry points using the shared emoji engine. |
| `measure_brightness.py` | Utility for measuring glyph brightness to help construct character ramps. |
| `update_demo.py`, `update_demo_inverted.py` | Generate demo conversions and comparison collages from configured source paths. |
| `generate_fontsize_demo.py`, `create_fontsize_gif.py` | Generate font-size examples and assemble their animation. |
| `test_*.py` | Pytest coverage for shape modes, solid blocks, transparency, and the TUI. |

Image inputs are loaded with Pillow into RGB NumPy arrays; OpenCV handles
resizing and grayscale calculations. Raster conversion pre-renders a glyph
palette, selects glyphs per cell, and tiles them into an output array. Text
conversion emits Unicode glyphs with optional ANSI escapes. Emoji selection
uses nearest average RGB color. Video scripts iterate MoviePy frames through
the shared renderer, collect the results, and encode H.264/AAC at the source FPS.

## Setup and commands

Use an existing project environment when available, or create one:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install pytest
```

- Runtime dependencies live in `requirements.txt`; Pillow and MoviePy are pinned, and Textual is constrained to major version 8. Do not casually upgrade these while changing rendering code.
- Pytest is needed for development but is not listed in the runtime requirements.
- Video processing requires FFmpeg, including `ffprobe`, on `PATH` (`brew install ffmpeg` on macOS).
- The project is tested on macOS. ASCII defaults to Menlo with a Pillow default-font fallback. Emoji rendering tries Apple Color Emoji, then a Linux Noto Color Emoji path; supported bitmap font sizes matter.

```bash
# Inspect CLI options without converting media.
python ascii_image.py --help
python ascii_video.py --help
python ascii_image_tui.py --help
python emoji_image.py --help
python emoji_video.py --help

# Run the existing suite, or the files relevant to a change.
python -m pytest -q
python -m pytest -q test_shape_modes.py test_solidblocks.py
python -m pytest -q test_image_transparency.py
python -m pytest -q test_image_tui.py
```

TUI tests use Textual's headless `run_test()` and `asyncio.run()`; they do not
require an interactive terminal or a separate pytest asyncio plugin. Prefer
small synthetic images and temporary output paths for regression tests.
For video changes, also smoke-test a short clip and check orientation, FPS,
and audio; the existing suite does not cover video encoding or emoji rendering.

## Implementation guidance

- Keep rendering logic in the corresponding `*_common.py` module. Entry points should handle parsing, input/output, and orchestration. Reuse the image helpers in the TUI so saved text matches CLI output.
- Put shared flags in `add_common_arguments`; keep image-only flags in `ascii_image.create_parser`. When adding an option, check its propagation through callers, frame options, and applicable TUI controls, as well as CLI help and README examples.
- Arrays passed to the renderers are RGB, not OpenCV's usual BGR. Keep source alpha separate during loading/scaling and preserve output dtype and dimensions.
- Preserve palette reuse and vectorized cell operations; avoid moving glyph rendering or other reusable work into per-frame loops.
- Brightness ramps, rectangular sub-cell modes (`quadrants`, `sextants`, `octants`), and mask modes (`wedges`, `wedges-octants`) have different selection paths. A new mode needs consistent registration, text glyphs, raster rendering, and relevant regression coverage.
- Shape glyphs are drawn geometrically for raster output; text output depends on terminal Unicode support. Font metrics still determine the ASCII cell dimensions.
- `solidblocks` fills every opaque cell regardless of brightness or inversion. Transparent text cells remain spaces.
- `--preserve-colors` controls raster colors. Text colors use `--ansi-colors` or `--ansi-fg-only`; foreground-only output must not emit background color codes. Preserve ANSI reset behavior.
- With `--transparent-bg`, respect explicit source alpha. If alpha is absent, key exact RGB matches to the original top-left pixel before scaling or aspect correction, including enclosed regions. Do not replace this with approximate matching or flood fill.
- Transparent raster output supports PNG, WebP, and TIFF and defaults to PNG. Keep text transparency and raster alpha behavior consistent with their tests.
- Preserve the TUI's worker cancellation and revision checks so stale renders cannot replace newer settings. Save only a valid current preview, and retain the second-save confirmation for overwriting files.
- Video conversion currently retains all processed frames in memory. Use short clips for routine checks and consider memory use when changing this pipeline.

## Repository assets

The root contains many ASCII `.txt` outputs and media files. Treat them as
user assets; do not overwrite, delete, or regenerate them as incidental cleanup.
Use temporary directories for test output. Demo helpers use configured `demo/`
paths, whose source media may be absent from a checkout. Inspect those paths
before running helpers. Generated `.txt` files and many media extensions are
ignored by `.gitignore`; root `requirements.txt` is exempt and remains tracked.
Art `.txt` outputs stay local and are not tracked. Check explicitly whether any
intended demo artifact will be tracked.
