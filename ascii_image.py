import argparse
import sys
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

# Characters from darkest to lightest (White text on black background means @ is brightest)
ASCII_CHARS = [" ", ".", ",", "-", "~", "+", "=", "@", "#", "%", "$"]

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

def process_image_numpy(image_path, font, output_path, scale=1.0):
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
    
    # 1. Measure Font Metrics
    dummy_draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    bbox = dummy_draw.textbbox((0, 0), "@", font=font)
    char_w = bbox[2] - bbox[0]
    char_h = bbox[3] - bbox[1]

    h, w = frame.shape[:2]
    
    # Calculate grid dimensions
    cols = w // char_w
    rows = h // char_h

    print(f"Resolution: {w}x{h}")
    print(f"Grid: {cols}x{rows}")
    print(f"Char Size: {char_w}x{char_h}")
    
    # 2. Pre-render fonts to a lookup table (The Palette)
    # Shape: (11, char_h, char_w, 3)
    char_palette = pre_render_chars(font, char_w, char_h)

    print("Rendering image...")
    
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
    final_image = tiled_chars.reshape(rows * char_h, cols * char_w, 3)
    
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
    
    args = parser.parse_args()
    
    # Set default output filename if not provided
    if args.output is None:
        base, ext = os.path.splitext(args.input)
        args.output = f"{base}_ascii{ext}"
    
    # Font loading
    font_path = "/System/Library/Fonts/Menlo.ttc"
    try:
        font = ImageFont.truetype(font_path, args.fontsize)
        print(f"Font loaded: {font_path}")
    except IOError:
        font = ImageFont.load_default()
        print("Using default font")
    try:
        process_image_numpy(args.input, font, args.output, args.scale)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
