import argparse
import sys
import subprocess
import json
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

# --- MOVIEPY IMPORT HANDLER (Handles v1.0 and v2.0) ---
try:
    from moviepy.editor import VideoFileClip, ImageSequenceClip
except ImportError:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.io.ImageSequenceClip import ImageSequenceClip

# Characters from darkest to lightest (White text on black background means @ is brightest)
ASCII_CHARS = [" ", ".", ",", "-", "~", "+", "=", "@", "#", "%", "$"]

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

def pre_render_chars(font, char_width, char_height):
    """
    Renders every ASCII char into a numpy array (stamp) once.
    Returns a numpy array of shape (num_chars, h, w, 3).
    """
    char_images = []
    
    for char in ASCII_CHARS:
        # Create a blank black image for the character
        img = Image.new("RGB", (char_width, char_height), "black")
        draw = ImageDraw.Draw(img)
        
        # Draw the character in white
        # Centering logic can be added here if needed, but top-left usually works for monospaced
        draw.text((0, 0), char, font=font, fill="white")
        
        # Convert to numpy array and append
        char_images.append(np.array(img))
        
    return np.stack(char_images)

def process_video_numpy(clip, font, output_path, scale=1.0, video_path=None):
    """
    Fast processing using Numpy tiling.
    """
    # 1. Measure Font Metrics
    dummy_draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    bbox = dummy_draw.textbbox((0, 0), "@", font=font)
    char_w = bbox[2] - bbox[0]
    char_h = bbox[3] - bbox[1]

    # 2. Resize Logic (MoviePy 1 vs 2 compatibility)
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
    
    # 3. Pre-render fonts to a lookup table (The Palette)
    # Shape: (11, char_h, char_w, 3)
    char_palette = pre_render_chars(font, char_w, char_h)

    processed_frames = []
    
    print("Rendering frames...")
    
    # We use a generator to process frames
    for frame in tqdm(clip.iter_frames(), total=int(clip.fps * clip.duration)):
        
        # A. Pre-processing: Grayscale & Resize
        # We resize the Frame to the Grid Size (small)
        # Convert to B/W
        img_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        img_small = cv2.resize(img_gray, (cols, rows), interpolation=cv2.INTER_NEAREST)

        # B. Map pixels to Indices
        # Map 0-255 brightness to 0-(len(ASCII)-1) indices
        # We explicitly cast to int to use as indices
        indices = (img_small / 255 * (len(ASCII_CHARS) - 1)).astype(int)

        # C. The Magic Trick (Advanced Numpy Indexing)
        # Instead of looping, we use the indices to lookup pixels from the palette.
        # Result shape: (rows, cols, char_h, char_w, 3)
        tiled_chars = char_palette[indices]

        # D. Stitching (Reshaping)
        # We need to rearrange axes to form the final image.
        # Current: (rows, cols, char_h, char_w, 3)
        # Target:  (rows * char_h, cols * char_w, 3)
        
        # Swap axes to: (rows, char_h, cols, char_w, 3)
        tiled_chars = tiled_chars.swapaxes(1, 2)
        
        # Collapse the grid
        final_frame = tiled_chars.reshape(rows * char_h, cols * char_w, 3)
        
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
    
    args = parser.parse_args()
    
    # Set default output filename if not provided
    if args.output is None:
        base, ext = os.path.splitext(args.input)
        args.output = f"{base}_ascii{ext}"
    
    # Font loading
    font_path = "/System/Library/Fonts/Menlo.ttc"
    try:
        font = ImageFont.truetype(font_path, args.fontsize)
    except IOError:
        font = ImageFont.load_default()

    try:
        clip = VideoFileClip(args.input)
        process_video_numpy(clip, font, args.output, args.scale, video_path=args.input)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()