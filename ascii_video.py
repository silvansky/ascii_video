import argparse
import sys
import subprocess
import json
import os
import numpy as np
from tqdm import tqdm

# --- MOVIEPY IMPORT HANDLER (Handles v1.0 and v2.0) ---
try:
    from moviepy.editor import VideoFileClip, ImageSequenceClip
except ImportError:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.io.ImageSequenceClip import ImageSequenceClip

from ascii_common import (
    ASCII_CHARS, ASCII_BLOCKS, pre_render_chars, load_font, parse_colors,
    measure_font_metrics, process_frame
)

def get_video_rotation(video_path):
    """
    Get rotation metadata from video file using ffprobe.
    Returns rotation angle in degrees (0, 90, 180, 270) or 0 if not found.
    """
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', '-select_streams', 'v:0', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        if 'streams' in data and len(data['streams']) > 0:
            stream = data['streams'][0]
            # Check for rotation in tags or side_data_list
            rotation = 0
            if 'tags' in stream and 'rotate' in stream['tags']:
                rotation = int(stream['tags']['rotate'])
            elif 'side_data_list' in stream:
                for side_data in stream['side_data_list']:
                    if side_data.get('rotation'):
                        rotation = side_data['rotation']
                        break
            
            # Normalize rotation to 0, 90, 180, 270
            rotation = rotation % 360
            if rotation not in [0, 90, 180, 270]:
                rotation = 0
            return rotation
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, ValueError):
        pass
    
    return 0


def process_video_numpy(clip, font, output_path, scale=1.0, video_path=None, bg_color="black", fg_color="white", invert_brightness=False, use_blocks=False):
    """
    Fast processing using Numpy tiling.
    """
    # Measure font metrics
    char_w, char_h = measure_font_metrics(font)

    # Resize Logic (MoviePy 1 vs 2 compatibility)
    if scale != 1.0:
        try:
            clip = clip.resize(scale)
        except AttributeError:
            clip = clip.resized(scale)

    w, h = clip.size
    
    # Account for video rotation metadata (swap dimensions if rotated 90/270 degrees)
    if video_path:
        rotation = get_video_rotation(video_path)
        if rotation in [90, 270]:
            w, h = h, w
    
    # Calculate grid dimensions
    cols = w // char_w
    rows = h // char_h

    print(f"Resolution: {w}x{h}")
    print(f"Grid: {cols}x{rows}")
    print(f"Char Size: {char_w}x{char_h}")
    
    # Pre-render fonts to a lookup table (The Palette)
    char_palette = pre_render_chars(font, char_w, char_h, bg_color, fg_color, use_blocks)
    num_chars = len(ASCII_BLOCKS) if use_blocks else len(ASCII_CHARS)

    processed_frames = []
    
    print("Rendering frames...")
    
    # We use a generator to process frames
    for frame in tqdm(clip.iter_frames(), total=int(clip.fps * clip.duration)):
        # Process frame using common function
        final_frame = process_frame(frame, char_palette, char_w, char_h, invert_brightness, num_chars)
        processed_frames.append(final_frame)

    print("Encoding video...")
    final_clip = ImageSequenceClip(processed_frames, fps=clip.fps)
    
    if clip.audio:
        final_clip = final_clip.set_audio(clip.audio)
        
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

def main():
    parser = argparse.ArgumentParser(description="Fast ASCII Video Generator")
    parser.add_argument("input", help="Path to input video file")
    parser.add_argument("-o", "--output", help="Path to output video file", default=None)
    parser.add_argument("-f", "--fontsize", type=int, help="Font size", default=10)
    parser.add_argument("-s", "--scale", type=float, help="Scale (0.5 is faster)", default=1.0)
    parser.add_argument("--bg-color", help="Background color (e.g., 'black', '#000000')", default="black")
    parser.add_argument("--fg-color", help="Foreground color (e.g., 'white', '#FFFFFF')", default="white")
    parser.add_argument("--invert-brightness", action="store_true", help="Invert brightness mapping (bright areas become dark characters)")
    parser.add_argument("--blocks", action="store_true", help="Use ASCII block characters (█ ▓ ▒ ░ space) instead of regular characters")
    
    args = parser.parse_args()
    
    # Set default output filename if not provided
    if args.output is None:
        base, ext = os.path.splitext(args.input)
        args.output = f"{base}_ascii{ext}"
    
    # Parse colors
    bg_color, fg_color = parse_colors(args.bg_color, args.fg_color)
    
    # Font loading
    font = load_font(args.fontsize)
    try:
        clip = VideoFileClip(args.input)
        process_video_numpy(clip, font, args.output, args.scale, video_path=args.input, bg_color=bg_color, fg_color=fg_color, invert_brightness=args.invert_brightness, use_blocks=args.blocks)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()