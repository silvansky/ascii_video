"""Interactive text preview: python ascii_image_tui.py image.png [options]."""

import math
from pathlib import Path

from PIL import ImageColor
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer, VerticalScroll
from textual.widgets import Button, Checkbox, Input, Label, Select, Static
from textual.worker import get_current_worker

from ascii_common import MODE_CHARS, load_font
from ascii_image import create_parser, load_scaled_image, render_text


FLAGS = (
    ("invert_brightness", "Invert brightness"),
    ("adjust_aspect_ratio", "Adjust aspect ratio"),
    ("transparent_bg", "Transparent bg"),
    ("ansi_colors", "ANSI colors"),
    ("ansi_fg_only", "ANSI fg only"),
    ("preserve_colors", "Preserve colors*"),
)


class AsciiImageApp(App):
    """Keep controls above an unwrapped, scrollable, true-color preview."""

    CSS = """
    Screen { layout: vertical; }
    #controls { height: auto; max-height: 70%; padding: 0 1; background: $panel; }
    #title { height: 1; text-style: bold; }
    .row { height: 3; align-vertical: middle; }
    .row Label { width: auto; padding: 1 1 0 0; }
    #mode { width: 1fr; }
    #scale, #fontsize { width: 10; }
    .color { width: 1fr; }
    .flags { height: 1; }
    Checkbox { width: 1fr; height: 1; border: none; padding: 0; }
    #filename { width: 1fr; }
    Button { min-width: 8; margin-left: 1; }
    #status { height: 2; }
    #preview-scroll { height: 1fr; background: black; color: white; }
    #preview { width: auto; height: auto; }
    """
    BINDINGS = [("ctrl+s", "save", "Save"), ("ctrl+q", "quit", "Quit")]

    def __init__(self, args):
        super().__init__()
        self.args = args
        self.preview_text = None
        self.revision = 0
        self.preview_timer = None
        self.overwrite_path = None

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="controls"):
            yield Static(Text(f"ASCII Image — {self.args.input}    Tab: controls · Ctrl+S: save · Ctrl+Q: quit"), id="title")
            with Horizontal(classes="row"):
                yield Label("Mode")
                yield Select([(mode, mode) for mode in MODE_CHARS], value=self.args.mode,
                             allow_blank=False, id="mode")
                yield Label(" Scale")
                yield Input(str(self.args.scale), id="scale", tooltip="--scale: positive scale factor")
                yield Label(" Font")
                yield Input(str(self.args.fontsize), id="fontsize", tooltip="--fontsize: positive integer")
            with Horizontal(classes="row"):
                yield Label("BG")
                yield Input(self.args.bg_color, id="bg_color", classes="color", tooltip="Preview background; plain text stores no colors")
                yield Label(" FG")
                yield Input(self.args.fg_color, id="fg_color", classes="color", tooltip="Preview foreground; ANSI colors override this")
                yield Label(" Tint")
                yield Input(self.args.tint or "", id="tint", classes="color", placeholder="optional", tooltip="--tint: applies to ANSI colors")
            for start in (0, 3):
                with Horizontal(classes="flags"):
                    for name, label in FLAGS[start:start + 3]:
                        tooltip = "--" + name.replace("_", "-")
                        if name == "preserve_colors":
                            tooltip += ": image output only; use ANSI colors for text"
                        yield Checkbox(label, value=getattr(self.args, name), id=name, tooltip=tooltip)
            with Horizontal(classes="row"):
                yield Label("Save as")
                yield Input(self.args.output or str(Path(self.args.input).with_suffix(".txt")), id="filename")
                yield Button("Save", id="save", variant="primary", disabled=True)
                yield Button("Quit", id="quit")
            yield Static("Rendering…", id="status", markup=False)
        with ScrollableContainer(id="preview-scroll", can_focus=True):
            yield Static("", id="preview", markup=False)

    def on_mount(self):
        self.schedule_preview()

    @on(Input.Changed)
    @on(Select.Changed)
    @on(Checkbox.Changed)
    def control_changed(self, event):
        if event.control.id == "filename":
            self.overwrite_path = None
        else:
            self.schedule_preview()

    def schedule_preview(self):
        self.revision += 1
        self.preview_text = None
        self.overwrite_path = None
        self.query_one("#save", Button).disabled = True
        if self.preview_timer is not None:
            self.preview_timer.stop()
        self.query_one("#status", Static).update("Rendering…   * Preserve colors affects image output only; use ANSI colors for text.")
        self.preview_timer = self.set_timer(0.15, self.start_preview)

    def start_preview(self):
        try:
            scale = float(self.query_one("#scale", Input).value)
            if not math.isfinite(scale) or scale <= 0:
                raise ValueError("Scale must be a finite number greater than zero")
            fontsize = int(self.query_one("#fontsize", Input).value)
            if fontsize <= 0:
                raise ValueError("Font size must be a positive integer")
            colors = {name: ImageColor.getcolor(self.query_one(f"#{name}", Input).value, "RGB")
                      for name in ("bg_color", "fg_color")}
            tint = self.query_one("#tint", Input).value.strip()
            options = {name: self.query_one(f"#{name}", Checkbox).value for name, _ in FLAGS
                       if name != "preserve_colors"}
            options["mode"] = self.query_one("#mode", Select).value
            options["tint_color"] = ImageColor.getcolor(tint, "RGB") if tint else None
        except (ValueError, OverflowError) as error:
            self.query_one("#status", Static).update(f"Invalid setting: {error}")
            return
        self.render_preview(self.revision, scale, fontsize, options, colors)

    @work(thread=True, exclusive=True)
    def render_preview(self, revision, scale, fontsize, options, colors):
        worker = get_current_worker()
        try:
            frame, alpha = load_scaled_image(self.args.input, scale, options["transparent_bg"])
            text = render_text(frame, alpha, load_font(fontsize, quiet=True), **options)
            rendered = Text.from_ansi(text)
            rendered.no_wrap = True
            rendered.overflow = "ignore"
        except Exception as error:
            if not worker.is_cancelled:
                self.call_from_thread(self.preview_failed, revision, str(error))
            return
        if not worker.is_cancelled:
            self.call_from_thread(self.show_preview, revision, text, rendered, colors)

    def preview_failed(self, revision, error):
        if revision == self.revision:
            self.query_one("#status", Static).update(f"Cannot preview: {error}")

    def show_preview(self, revision, text, rendered, colors):
        if revision != self.revision:
            return  # A previous render must never replace newer settings.
        self.preview_text = text
        preview = self.query_one("#preview", Static)
        preview.update(rendered)
        area = self.query_one("#preview-scroll")
        area.styles.background = "rgb(%d,%d,%d)" % colors["bg_color"]
        area.styles.color = "rgb(%d,%d,%d)" % colors["fg_color"]
        self.query_one("#save", Button).disabled = False
        lines = rendered.plain.splitlines()
        self.query_one("#status", Static).update(
            f"{max(map(len, lines), default=0)} columns × {len(lines)} rows · Scroll preview with arrows or mouse.\n"
            "* Preserve colors affects image output only; use ANSI colors for text."
        )

    @on(Button.Pressed, "#save")
    @on(Input.Submitted, "#filename")
    def action_save(self):
        status = self.query_one("#status", Static)
        if self.preview_text is None:
            status.update("Wait for a valid preview before saving.")
            return
        name = self.query_one("#filename", Input).value.strip()
        if not name:
            status.update("Enter a filename to save.")
            return
        path = Path(name).expanduser()
        if not path.suffix:
            path = path.with_suffix(".txt")
        if path.suffix.lower() != ".txt":
            status.update("Use a .txt filename for text output.")
            return
        try:
            if path.exists() and self.overwrite_path != path:
                self.overwrite_path = path
                status.update(f"{path} already exists. Press Save again to replace it.")
                return
            with path.open("w" if self.overwrite_path == path else "x", encoding="utf-8") as output:
                output.write(self.preview_text)
        except (OSError, ValueError) as error:
            status.update(f"Cannot save: {error}")
            return
        self.overwrite_path = None
        status.update(f"Saved to {path}")

    @on(Button.Pressed, "#quit")
    def quit_clicked(self):
        self.exit()


def main():
    parser = create_parser()
    parser.description = "Interactive ASCII image text preview"
    AsciiImageApp(parser.parse_args()).run()


if __name__ == "__main__":
    main()
