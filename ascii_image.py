import argparse
import sys
import os
import numpy as np
import cv2
from PIL import Image
from ascii_common import (
    ASCII_CHARS, ASCII_BLOCKS, ASCII_ALPHABET, ASCII_DIGITS, ASCII_ALPHANUMERIC, pre_render_chars, load_font, parse_colors,
    measure_font_metrics, process_frame, AsciiFrameOptions, add_common_arguments
)

def process_image_numpy(image_path, font, output_path, scale=1.0, bg_color="black", fg_color="white", invert_brightness=False, use_blocks=False, use_alphabet=False, use_digits=False, use_alphanumeric=False, preserve_colors=False):
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
    char_palette = pre_render_chars(font, char_w, char_h, bg_color, fg_color, use_blocks, use_alphabet, use_digits, use_alphanumeric)
    if use_alphanumeric:
        num_chars = len(ASCII_ALPHANUMERIC)
    elif use_digits:
        num_chars = len(ASCII_DIGITS)
    elif use_alphabet:
        num_chars = len(ASCII_ALPHABET)
    elif use_blocks:
        num_chars = len(ASCII_BLOCKS)
    else:
        num_chars = len(ASCII_CHARS)

    print("Rendering image...")
    
    # Create options object
    options = AsciiFrameOptions(
        char_palette=char_palette,
        char_w=char_w,
        char_h=char_h,
        invert_brightness=invert_brightness,
        num_chars=num_chars,
        preserve_colors=preserve_colors,
        bg_color=bg_color,
        fg_color=fg_color,
        swap_dims=False
    )
    
    # Process frame using common function
    final_image = process_frame(frame, options)
    
    # Convert back to PIL Image and save
    output_img = Image.fromarray(final_image.astype(np.uint8))
    output_img.save(output_path)
    print(f"Saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Fast ASCII Image Generator")
    add_common_arguments(parser, input_help="Path to input image file", output_help="Path to output image file")
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
        process_image_numpy(args.input, font, args.output, args.scale, bg_color, fg_color, args.invert_brightness, args.blocks, args.alphabet, args.digits, args.alphanumeric, args.preserve_colors)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
