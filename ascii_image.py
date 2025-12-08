import argparse
import sys
import os
import numpy as np
import cv2
from PIL import Image
from ascii_common import (
    ASCII_CHARS, ASCII_BLOCKS, pre_render_chars, load_font, parse_colors,
    measure_font_metrics, process_frame
)

def process_image_numpy(image_path, font, output_path, scale=1.0, bg_color="black", fg_color="white", invert_brightness=False, use_blocks=False, preserve_colors=False):
    """
    Fast processing using Numpy tiling.
    """
    # Load image
    img = Image.open(image_path)
    
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Convert to numpy array
    frame = np.array(img)
    
    # Apply scale if needed
    if scale != 1.0:
        h, w = frame.shape[:2]
        new_h, new_w = int(h * scale), int(w * scale)
        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    # Measure font metrics
    char_w, char_h = measure_font_metrics(font)

    h, w = frame.shape[:2]
    
    # Calculate grid dimensions
    cols = w // char_w
    rows = h // char_h

    print(f"Resolution: {w}x{h}")
    print(f"Grid: {cols}x{rows}")
    print(f"Char Size: {char_w}x{char_h}")
    
    # Pre-render fonts to a lookup table (The Palette)
    char_palette = pre_render_chars(font, char_w, char_h, bg_color, fg_color, use_blocks)
    num_chars = len(ASCII_BLOCKS) if use_blocks else len(ASCII_CHARS)

    print("Rendering image...")
    
    # Process frame using common function
    final_image = process_frame(frame, char_palette, char_w, char_h, invert_brightness, num_chars, preserve_colors, bg_color, fg_color)
    
    # Convert back to PIL Image and save
    output_img = Image.fromarray(final_image.astype(np.uint8))
    output_img.save(output_path)
    print(f"Saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Fast ASCII Image Generator")
    parser.add_argument("input", help="Path to input image file")
    parser.add_argument("-o", "--output", help="Path to output image file", default=None)
    parser.add_argument("-f", "--fontsize", type=int, help="Font size", default=10)
    parser.add_argument("-s", "--scale", type=float, help="Scale (0.5 is faster)", default=1.0)
    parser.add_argument("--bg-color", help="Background color (e.g., 'black', '#000000')", default="black")
    parser.add_argument("--fg-color", help="Foreground color (e.g., 'white', '#FFFFFF')", default="white")
    parser.add_argument("--invert-brightness", action="store_true", help="Invert brightness mapping (bright areas become dark characters)")
    parser.add_argument("--blocks", action="store_true", help="Use ASCII block characters (█ ▓ ▒ ░ space) instead of regular characters")
    parser.add_argument("--preserve-colors", action="store_true", help="Preserve original colors (ignores fg-color, disables grayscale and normalization)")
    
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
        process_image_numpy(args.input, font, args.output, args.scale, bg_color, fg_color, args.invert_brightness, args.blocks, args.preserve_colors)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
