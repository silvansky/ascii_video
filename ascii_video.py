import argparse
import sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip, ImageSequenceClip
from tqdm import tqdm
import os

# Standard ASCII density string (darkest to lightest)
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

def pixel_to_ascii(image, range_width=25):
    """
    Maps grayscale pixel values to ASCII characters.
    """
    pixels = np.array(image)
    # Normalize pixel values to match the length of ASCII_CHARS
    # 255 (white) // 25 = 10 (index of '.')
    ascii_str = ""
    for pixel_value in pixels:
        ascii_str += ASCII_CHARS[pixel_value // range_width]
    return ascii_str

def process_frame(frame, font, char_width, char_height, num_cols, num_rows):
    """
    Takes a video frame, converts it to ASCII, and renders it back to an image.
    """
    # Convert OpenCV frame (BGR) to PIL Image (RGB)
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    # Convert to grayscale for intensity calculation
    img_gray = img.convert("L")
    
    # Resize image to the dimensions of our ASCII grid
    # This determines how "blocky" the ASCII looks
    img_small = img_gray.resize((num_cols, num_rows))
    
    # Get raw pixel data
    pixels = list(img_small.getdata())
    
    # Create the output canvas (Black background)
    output_width = num_cols * char_width
    output_height = num_rows * char_height
    output_image = Image.new("RGB", (output_width, output_height), color="black")
    draw = ImageDraw.Draw(output_image)
    
    # Map pixels to characters and draw them
    # Optimizing: Drawing line by line is faster than char by char
    for i in range(num_rows):
        line_chars = ""
        for j in range(num_cols):
            intensity = pixels[i * num_cols + j]
            # Map 0-255 to 0-10 index
            char_index = min(intensity // 25, len(ASCII_CHARS) - 1)
            line_chars += ASCII_CHARS[char_index]
        
        # Draw the whole line of text
        draw.text((0, i * char_height), line_chars, fill="white", font=font)

    # Convert back to numpy array for MoviePy
    return np.array(output_image)

def main():
    parser = argparse.ArgumentParser(description="Convert video to ASCII art video.")
    parser.add_argument("input", help="Path to input video file")
    parser.add_argument("-o", "--output", help="Path to output video file", default="output_ascii.mp4")
    parser.add_argument("-f", "--fontsize", type=int, help="Font size (lower = higher res, slower)", default=10)
    parser.add_argument("-s", "--scale", type=float, help="Output scale (1.0 = original size)", default=1.0)
    
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output
    font_size = args.fontsize

    # macOS specific font path for a good monospaced font
    font_path = "/System/Library/Fonts/Menlo.ttc"
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        print("Menlo font not found, falling back to default.")
        font = ImageFont.load_default()

    # Calculate character dimensions
    # We use a dummy character to measure size
    dummy_draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    bbox = dummy_draw.textbbox((0, 0), "@", font=font)
    char_width = bbox[2] - bbox[0]
    char_height = bbox[3] - bbox[1]

    # Load Video
    try:
        clip = VideoFileClip(input_path)
    except Exception as e:
        print(f"Error loading video: {e}")
        sys.exit(1)

    # Resize input based on scale argument
    if args.scale != 1.0:
        clip = clip.resize(args.scale)

    width, height = clip.size
    
    # Calculate how many ASCII columns/rows fit in the video frame
    num_cols = width // char_width
    num_rows = height // char_height

    print(f"Input Resolution: {width}x{height}")
    print(f"ASCII Grid: {num_cols}x{num_rows} characters")
    print(f"Processing... (Press Ctrl+C to cancel)")

    processed_frames = []

    # Process frames
    # We use iter_frames for efficient generator access
    try:
        for frame in tqdm(clip.iter_frames(), total=int(clip.fps * clip.duration), unit="frames"):
            new_frame = process_frame(frame, font, char_width, char_height, num_cols, num_rows)
            processed_frames.append(new_frame)
    except KeyboardInterrupt:
        print("\nProcess interrupted. Saving what we have so far...")

    if not processed_frames:
        print("No frames processed.")
        sys.exit(1)

    print("Compiling video...")
    
    # Create new clip from frames
    final_clip = ImageSequenceClip(processed_frames, fps=clip.fps)
    
    # Attach original audio if it exists
    if clip.audio:
        # If we interrupted early, cut the audio to match
        audio = clip.audio.subclip(0, final_clip.duration)
        final_clip = final_clip.set_audio(audio)

    # Write output
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    print(f"Done! Saved to {output_path}")

if __name__ == "__main__":
    main()