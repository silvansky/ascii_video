"""
Common utilities for ASCII image and video processing.
"""
import sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageColor

# Characters from darkest to lightest (White text on black background means @ is brightest)
ASCII_CHARS = [" ", ".", ",", "-", "~", "+", "=", "@", "#", "%", "$"]

def pre_render_chars(font, char_width, char_height, bg_color, fg_color):
    """
    Renders every ASCII char into a numpy array (stamp) once.
    Returns a numpy array of shape (num_chars, h, w, 3).
    """
    # Measure font metrics using a reference character to establish baseline
    dummy_img = Image.new("RGB", (char_width * 2, char_height * 2))
    dummy_draw = ImageDraw.Draw(dummy_img)
    ref_bbox = dummy_draw.textbbox((0, 0), "@", font=font)
    
    # Use consistent baseline offset for all characters
    # This ensures all characters align properly
    baseline_offset_x = -ref_bbox[0]
    baseline_offset_y = -ref_bbox[1]
    
    char_images = []
    
    for char in ASCII_CHARS:
        # Create a blank image for the character with background color
        img = Image.new("RGB", (char_width, char_height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Draw all characters at the same baseline offset for consistent alignment
        draw.text((baseline_offset_x, baseline_offset_y), char, font=font, fill=fg_color)
        
        # Convert to numpy array and append
        char_images.append(np.array(img))
    
    return np.stack(char_images)

def load_font(fontsize=10, font_path="/System/Library/Fonts/Menlo.ttc"):
    """
    Load font from path, fallback to default if not found.
    Returns ImageFont object.
    """
    try:
        font = ImageFont.truetype(font_path, fontsize)
        print(f"Font loaded: {font_path}")
        return font
    except IOError:
        font = ImageFont.load_default()
        print("Using default font")
        return font

def parse_colors(bg_color_str, fg_color_str):
    """
    Parse color strings to RGB tuples.
    Returns (bg_color, fg_color) tuple.
    Raises ValueError on invalid color format.
    """
    try:
        bg_color = ImageColor.getcolor(bg_color_str, "RGB")
        fg_color = ImageColor.getcolor(fg_color_str, "RGB")
        return bg_color, fg_color
    except ValueError as e:
        print(f"Error: Invalid color format. {e}")
        sys.exit(1)

def measure_font_metrics(font):
    """
    Measure character width and height for a given font.
    Returns (char_width, char_height) tuple.
    """
    dummy_draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    bbox = dummy_draw.textbbox((0, 0), "@", font=font)
    char_w = bbox[2] - bbox[0]
    char_h = bbox[3] - bbox[1]
    return char_w, char_h

def process_frame(frame, char_palette, char_w, char_h, invert_brightness=False):
    """
    Process a single frame (numpy array) into ASCII art.
    
    Args:
        frame: numpy array of shape (h, w, 3) - RGB image
        char_palette: pre-rendered character palette, shape (num_chars, char_h, char_w, 3)
        char_w: character width in pixels
        char_h: character height in pixels
        invert_brightness: if True, invert brightness mapping
    
    Returns:
        numpy array of shape (rows * char_h, cols * char_w, 3) - ASCII art image
    """
    h, w = frame.shape[:2]
    
    # Calculate grid dimensions
    cols = w // char_w
    rows = h // char_h
    
    # A. Pre-processing: Grayscale & Resize
    # We resize the Frame to the Grid Size (small)
    # Convert to B/W
    img_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    img_small = cv2.resize(img_gray, (cols, rows), interpolation=cv2.INTER_NEAREST)

    # B. Map pixels to Indices
    # Map 0-255 brightness to 0-(len(ASCII)-1) indices
    # We explicitly cast to int to use as indices
    if invert_brightness:
        indices = ((255 - img_small) / 255 * (len(ASCII_CHARS) - 1)).astype(int)
    else:
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
    
    return final_frame
