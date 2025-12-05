# ASCII Video Converter

Convert videos to ASCII art videos.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install opencv-python pillow==9.5.0 moviepy==1.0.3 tqdm numpy
```

**Note:** This tool requires `ffmpeg` (specifically `ffprobe`) to be installed on your system for reading video rotation metadata. Install it via:
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg` (Debian/Ubuntu) or `sudo yum install ffmpeg` (RHEL/CentOS)
- Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Usage

```bash
python ascii_video.py <input_video> [options]
```

### Options

- `-o, --output`: Path to output video file (default: input filename with `_ascii` suffix, e.g., `input.mp4` → `input_ascii.mp4`)
- `-f, --fontsize`: Font size - lower values = higher resolution but slower processing (default: 10)
- `-s, --scale`: Output scale factor - 1.0 = original size (default: 1.0)

### Examples

```bash
# Basic conversion (outputs to input_ascii.mp4)
python ascii_video.py input.mp4

# Custom output filename
python ascii_video.py input.mp4 -o my_ascii_video.mp4

# Higher resolution (smaller font)
python ascii_video.py input.mp4 -f 8

# Scale down the input video
python ascii_video.py input.mp4 -s 0.5
```
