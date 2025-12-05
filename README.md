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

## Usage

```bash
python ascii_video.py <input_video> [options]
```

### Options

- `-o, --output`: Path to output video file (default: `output_ascii.mp4`)
- `-f, --fontsize`: Font size - lower values = higher resolution but slower processing (default: 10)
- `-s, --scale`: Output scale factor - 1.0 = original size (default: 1.0)

### Examples

```bash
# Basic conversion
python ascii_video.py input.mp4

# Custom output filename
python ascii_video.py input.mp4 -o my_ascii_video.mp4

# Higher resolution (smaller font)
python ascii_video.py input.mp4 -f 8

# Scale down the input video
python ascii_video.py input.mp4 -s 0.5
```
