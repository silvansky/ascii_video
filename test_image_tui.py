import asyncio
import threading

import numpy as np
import pytest
from PIL import Image
from textual.widgets import Button, Checkbox, Input, Select, Static

from ascii_common import load_font
from ascii_image import create_parser, process_image_numpy
from ascii_image_tui import AsciiImageApp, FLAGS
import ascii_image_tui


@pytest.fixture
def source(tmp_path):
    y, x = np.indices((80, 96))
    pixels = np.stack((x * 2, y * 3, (x + y) % 256), axis=-1).astype(np.uint8)
    path = tmp_path / "source.png"
    Image.fromarray(pixels).save(path)
    return path


async def ready(app, pilot):
    for _ in range(100):
        await pilot.pause(0.05)
        if app.preview_text is not None:
            return
    pytest.fail(f"Preview did not finish: {app.query_one('#status', Static).content}")


def test_controls_preview_and_save_match_cli(source, tmp_path):
    async def check():
        args = create_parser().parse_args([str(source)])
        app = AsciiImageApp(args)
        async with app.run_test(size=(100, 30)) as pilot:
            await ready(app, pilot)
            assert app.query_one("#filename", Input).value == str(source.with_suffix(".txt"))
            assert {widget.id for widget in app.query(Checkbox)} == {name for name, _ in FLAGS}
            assert app.query_one("#preview-scroll").region.y >= app.query_one("#controls").region.bottom
            initial = app.preview_text
            app.query_one("#mode", Select).value = "octants"
            app.query_one("#scale", Input).value = "2"
            for name, _ in FLAGS:
                app.query_one(f"#{name}", Checkbox).value = True
            app.query_one("#tint", Input).value = "orange"
            await pilot.pause(0.2)
            await ready(app, pilot)
            assert app.preview_text != initial
            assert "\x1b[38;2;" in app.preview_text
            assert "\x1b[48;2;" not in app.preview_text
            cli_path = tmp_path / "cli.txt"
            process_image_numpy(str(source), load_font(10), str(cli_path), scale=2,
                                mode="octants", invert_brightness=True, preserve_colors=True,
                                adjust_aspect_ratio=True, ansi_colors=True, ansi_fg_only=True,
                                transparent_bg=True, tint_color=(255, 165, 0))
            assert app.preview_text == cli_path.read_text()
            await pilot.click("#save")
            output = source.with_suffix(".txt")
            assert output.read_text() == app.preview_text
            output.write_text("existing contents")
            await pilot.press("ctrl+s")
            assert output.read_text() == "existing contents"
            await pilot.press("ctrl+s")
            assert output.read_text() == app.preview_text
            app.query_one("#filename", Input).value = str(tmp_path / "custom")
            await pilot.pause()
            await pilot.press("ctrl+s")
            assert (tmp_path / "custom.txt").read_text() == app.preview_text
    asyncio.run(check())


@pytest.mark.parametrize("value", ["", "0", "-1", "nan", "inf", "0.00001"])
def test_invalid_scale_blocks_save_and_recovers(source, value):
    async def check():
        app = AsciiImageApp(create_parser().parse_args([str(source)]))
        async with app.run_test() as pilot:
            await ready(app, pilot)
            app.query_one("#scale", Input).value = value
            await pilot.pause(0.3)
            await app.workers.wait_for_complete()
            assert app.preview_text is None
            assert app.query_one("#save", Button).disabled
            await pilot.press("ctrl+s")
            assert not source.with_suffix(".txt").exists()
            app.query_one("#scale", Input).value = "1"
            await ready(app, pilot)
            assert not app.query_one("#save", Button).disabled
    asyncio.run(check())


def test_missing_image_and_save_errors_are_reported(source, tmp_path):
    async def check():
        app = AsciiImageApp(create_parser().parse_args([str(source)]))
        async with app.run_test() as pilot:
            await ready(app, pilot)
            for filename, message in [(str(tmp_path / "missing" / "out.txt"), "Cannot save"),
                                      (str(source), "Use a .txt"), ("", "Enter a filename")]:
                app.query_one("#filename", Input).value = filename
                await pilot.pause()
                await pilot.press("ctrl+s")
                assert message in str(app.query_one("#status", Static).content)
            source.unlink()
            app.query_one("#scale", Input).value = "2"
            await pilot.pause(0.3)
            await app.workers.wait_for_complete()
            assert "Cannot preview" in str(app.query_one("#status", Static).content)
            assert app.query_one("#save", Button).disabled
    asyncio.run(check())


def test_new_settings_win_over_slow_render(source, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    render = ascii_image_tui.render_text

    def delayed_render(*args, **kwargs):
        if kwargs["mode"] == "blocks":
            started.set()
            release.wait(5)
        return render(*args, **kwargs)

    monkeypatch.setattr(ascii_image_tui, "render_text", delayed_render)

    async def check():
        app = AsciiImageApp(create_parser().parse_args([str(source)]))
        async with app.run_test(size=(80, 24)) as pilot:
            await ready(app, pilot)
            app.query_one("#mode", Select).value = "blocks"
            for _ in range(100):
                await pilot.pause(0.02)
                if started.is_set():
                    break
            assert started.is_set()
            app.query_one("#mode", Select).value = "solidblocks"
            app.query_one("#scale", Input).value = "10"
            await pilot.pause(0.2)
            await ready(app, pilot)
            latest = app.preview_text
            assert set(latest) == {"█", "\n"}
            area = app.query_one("#preview-scroll")
            assert area.virtual_size.width > area.size.width
            assert app.query_one("#save").region.bottom <= area.region.y
            release.set()
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert app.preview_text == latest
    try:
        asyncio.run(check())
    finally:
        release.set()
