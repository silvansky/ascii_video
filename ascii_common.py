"""
Common utilities for ASCII image and video processing.
"""
import sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageColor

# Characters from darkest to lightest (White text on black background means @ is brightest)
ASCII_CHARS = [" ", ".", ",", "-", "~", "+", "=", "@", "#", "%", "$"]

# ASCII block characters from darkest to lightest
ASCII_BLOCKS = [" ", "░", "▒", "▓", "█"]

def pre_render_chars(font, char_width, char_height, bg_color, fg_color, use_blocks=False):
    """
    Renders every ASCII char into a numpy array (stamp) once.
    Returns a numpy array of shape (num_chars, h, w, 3).
    """
    # Select character set
    chars = ASCII_BLOCKS if use_blocks else ASCII_CHARS
    
    # Measure font metrics using a reference character to establish baseline
    dummy_img = Image.new("RGB", (char_width * 2, char_height * 2))
    dummy_draw = ImageDraw.Draw(dummy_img)
    ref_char = "█" if use_blocks else "@"
    ref_bbox = dummy_draw.textbbox((0, 0), ref_char, font=font)
    
    # Use consistent baseline offset for all characters
    # This ensures all characters align properly
    baseline_offset_x = -ref_bbox[0]
    baseline_offset_y = -ref_bbox[1]
    
    char_images = []
    
    for char in chars:
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

def process_frame(frame, char_palette, char_w, char_h, invert_brightness=False, num_chars=None, preserve_colors=False, bg_color=(0, 0, 0), fg_color=(255, 255, 255)):
    """
    Process a single frame (numpy array) into ASCII art.
    
    Args:
        frame: numpy array of shape (h, w, 3) - RGB image
        char_palette: pre-rendered character palette, shape (num_chars, char_h, char_w, 3)
        char_w: character width in pixels
        char_h: character height in pixels
        invert_brightness: if True, invert brightness mapping
        num_chars: number of characters in palette (if None, uses len(char_palette))
        preserve_colors: if True, preserve original colors and skip grayscale/normalization
        bg_color: background color tuple (RGB) - used for color preservation
        fg_color: foreground color tuple (RGB) - used for color preservation
    
    Returns:
        numpy array of shape (rows * char_h, cols * char_w, 3) - ASCII art image
    """
    h, w = frame.shape[:2]
    
    # Calculate grid dimensions
    cols = w // char_w
    rows = h // char_h
    
    if preserve_colors:
        # Preserve colors mode: skip grayscale and normalization
        # Resize RGB frame to grid size
        img_small_rgb = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_AREA)
        
        # Calculate brightness for character selection (but don't normalize)
        # Use luminance formula: 0.299*R + 0.587*G + 0.114*B
        img_brightness = (0.299 * img_small_rgb[:, :, 0] + 
                         0.587 * img_small_rgb[:, :, 1] + 
                         0.114 * img_small_rgb[:, :, 2])
        
        if num_chars is None:
            num_chars = len(char_palette)
        
        # Map brightness directly to indices without normalization
        # Use full 0-255 range mapped to 0-(num_chars-1)
        if invert_brightness:
            indices = ((255.0 - img_brightness) / 255.0 * (num_chars - 1)).astype(int)
        else:
            indices = (img_brightness / 255.0 * (num_chars - 1)).astype(int)
        
        indices = np.clip(indices, 0, num_chars - 1)
        
        # Get selected characters
        tiled_chars = char_palette[indices]  # (rows, cols, char_h, char_w, 3)
        
        # Colorize characters based on original pixel colors
        bg_color_arr = np.array(bg_color, dtype=np.float32)
        fg_color_arr = np.array(fg_color, dtype=np.float32)
        
        # Expand sampled colors to match character dimensions
        cell_colors = img_small_rgb.astype(np.float32)  # (rows, cols, 3)
        cell_colors_expanded = cell_colors[:, :, np.newaxis, np.newaxis, :]  # (rows, cols, 1, 1, 3)
        
        # Create mask: pixels that are closer to fg_color than bg_color (character pixels)
        tiled_chars_float = tiled_chars.astype(np.float32)
        char_diff_fg = np.sum((tiled_chars_float - fg_color_arr) ** 2, axis=-1, keepdims=True)
        char_diff_bg = np.sum((tiled_chars_float - bg_color_arr) ** 2, axis=-1, keepdims=True)
        fg_mask = (char_diff_fg < char_diff_bg).astype(np.float32)  # (rows, cols, char_h, char_w, 1)
        
        # Apply color: character pixels get the sampled color, background is black
        tiled_chars = (cell_colors_expanded * fg_mask).astype(np.uint8)
        
    else:
        # Original mode: Grayscale & Normalize
        img_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        img_small = cv2.resize(img_gray, (cols, rows), interpolation=cv2.INTER_NEAREST)

        # Map pixels to Indices
        if num_chars is None:
            num_chars = len(char_palette)
        
        # Normalize to 0-1 range using min/max to ensure full range is used
        img_min = img_small.min()
        img_max = img_small.max()
        if img_max > img_min:
            img_normalized = (img_small - img_min) / (img_max - img_min)
        else:
            img_normalized = img_small / 255.0
        
        if invert_brightness:
            indices = ((1.0 - img_normalized) * (num_chars - 1)).astype(int)
        else:
            indices = (img_normalized * (num_chars - 1)).astype(int)
        
        indices = np.clip(indices, 0, num_chars - 1)

        # The Magic Trick (Advanced Numpy Indexing)
        tiled_chars = char_palette[indices]

    # Stitching (Reshaping)
    # Swap axes to: (rows, char_h, cols, char_w, 3)
    tiled_chars = tiled_chars.swapaxes(1, 2)
    
    # Collapse the grid
    final_frame = tiled_chars.reshape(rows * char_h, cols * char_w, 3)
    
    return final_frame
