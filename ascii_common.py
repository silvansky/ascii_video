"""
Common utilities for ASCII image and video processing.
"""
import sys
import argparse
from dataclasses import dataclass
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageColor

# Characters from darkest to lightest (White text on black background means @ is brightest)
ASCII_CHARS = [" ", ".", ",", "-", "~", "+", "=", "@", "#", "%", "$"]

# ASCII block characters from darkest to lightest
ASCII_BLOCKS = [" ", "░", "▒", "▓", "█"]

# Alphabet letters from darkest to lightest (measured brightness order)
# Space is added at the beginning for the darkest color
ASCII_ALPHABET = [' ', 'r', 'j', 'v', 'x', 'c', 'z', 'l', 'Y', 'L', 'n', 'u', 's', 'y', 'J', 'w', 'i', 't', 'T', 'f', 'C', 'o', 'V', 'I', 'k', 'F', 'S', 'h', 'X', 'a', 'Z', 'm', 'A', 'p', 'q', 'U', 'P', 'e', 'K', 'G', 'b', 'd', 'O', 'H', 'E', 'g', 'D', 'Q', 'R', 'W', 'M', 'B', 'N']

# Digits from darkest to lightest (measured brightness order)
# Space is added at the beginning for the darkest color
ASCII_DIGITS = [' ', '7', '1', '2', '4', '3', '5', '6', '9', '8', '0']

# Alphanumeric characters (letters + digits) from darkest to lightest (measured brightness order)
# Space is added at the beginning for the darkest color
ASCII_ALPHANUMERIC = [' ', 'r', 'v', 'x', 'c', 'z', 'l', '7', 'j', 'Y', 'L', 'n', 'u', 's', 'y', 'J', 'w', 'i', '1', 't', 'T', 'f', 'C', 'o', 'V', 'I', '2', 'k', 'F', 'S', 'h', 'X', '4', 'a', 'Z', '3', 'm', 'A', '5', 'p', 'q', 'U', 'P', 'e', 'K', 'G', 'b', 'd', '6', '9', 'O', 'H', 'E', 'g', 'D', 'Q', 'R', '8', 'W', 'M', 'B', 'N', '0']

# Braille dots from darkest (empty) to lightest (full cell), by dot density
ASCII_DOTS = [' ', '⠁', '⠃', '⠇', '⠏', '⠟', '⠿', '⡿', '⣿']

@dataclass
class AsciiFrameOptions:
    """Options for processing a frame into ASCII art."""
    char_palette: np.ndarray  # Pre-rendered character palette, shape (num_chars, char_h, char_w, 3)
    char_w: int  # Character width in pixels
    char_h: int  # Character height in pixels
    invert_brightness: bool = False  # If True, invert brightness mapping
    num_chars: int = None  # Number of characters in palette (if None, uses len(char_palette))
    preserve_colors: bool = False  # If True, preserve original colors and skip grayscale/normalization
    bg_color: tuple = (0, 0, 0)  # Background color tuple (RGB) - used for color preservation
    fg_color: tuple = (255, 255, 255)  # Foreground color tuple (RGB) - used for color preservation
    swap_dims: bool = False  # If True, swap h and w (for rotated videos)
    tint_color: tuple = None  # Tint color tuple (RGB) - applied when preserve_colors is True

MODE_CHARS = {
    "chars": ASCII_CHARS,
    "blocks": ASCII_BLOCKS,
    "alphabet": ASCII_ALPHABET,
    "digits": ASCII_DIGITS,
    "alphanumeric": ASCII_ALPHANUMERIC,
    "dots": ASCII_DOTS,
}

def select_chars(mode="chars"):
    """Return the character set list based on mode."""
    return MODE_CHARS[mode]

def pre_render_chars(font, char_width, char_height, bg_color, fg_color, mode="chars"):
    """
    Renders every ASCII char into a numpy array (stamp) once.
    Returns a numpy array of shape (num_chars, h, w, 3).
    """
    chars = select_chars(mode)
    
    # Measure font metrics to establish baseline alignment
    # Use a reference character to set baseline, then ensure all characters fit
    dummy_img = Image.new("RGB", (char_width * 2, char_height * 2))
    dummy_draw = ImageDraw.Draw(dummy_img)
    
    # Find the minimum left and top across all characters to establish baseline
    # Use the same measurement approach as measure_font_metrics for consistency
    min_left = float('inf')
    min_top = float('inf')
    for char in chars:
        bbox = dummy_draw.textbbox((0, 0), char, font=font)
        min_left = min(min_left, bbox[0])
        min_top = min(min_top, bbox[1])
    
    # Baseline offset positions characters so the leftmost/topmost aligns at (0,0)
    # Use same calculation as in measure_font_metrics, then round to integer for rendering
    baseline_offset_x = int(round(-min_left))
    baseline_offset_y = int(round(-min_top))
    
    char_images = []
    
    for char in chars:
        # Create a blank image for the character with background color
        img = Image.new("RGB", (char_width, char_height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Draw character at baseline offset position with integer coordinates
        # PIL's text rendering handles antialiasing automatically, which is fine for most cases
        # Using integer positions helps avoid sub-pixel positioning issues
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

def add_common_arguments(parser, input_help="Path to input file", output_help="Path to output file"):
    """
    Add common ASCII processing arguments to an ArgumentParser.
    
    Args:
        parser: argparse.ArgumentParser instance
        input_help: Help text for input argument
        output_help: Help text for output argument
    """
    parser.add_argument("input", help=input_help)
    parser.add_argument("-o", "--output", help=output_help, default=None)
    parser.add_argument("-f", "--fontsize", type=int, help="Font size", default=10)
    parser.add_argument("-s", "--scale", type=float, help="Scale (0.5 is faster)", default=1.0)
    parser.add_argument("--bg-color", help="Background color (e.g., 'black', '#000000')", default="black")
    parser.add_argument("--fg-color", help="Foreground color (e.g., 'white', '#FFFFFF')", default="white")
    parser.add_argument("--invert-brightness", action="store_true", help="Invert brightness mapping (bright areas become dark characters)")
    parser.add_argument("--mode", choices=list(MODE_CHARS.keys()), default="chars", help="Character set: 'chars' (default), 'blocks' (█ ▓ ▒ ░ space), 'alphabet' (a-z, A-Z), 'digits' (0-9), 'alphanumeric' (a-z, A-Z, 0-9), or 'dots' (braille ⠁⠿⣿)")
    parser.add_argument("--preserve-colors", action="store_true", help="Preserve original colors (ignores fg-color, disables grayscale and normalization)")
    parser.add_argument("--tint", help="Tint color to apply when --preserve-colors is set (e.g., 'red', '#FF0000')", default=None)
    parser.add_argument("--adjust-aspect-ratio", action="store_true", help="For .txt output, adjust source image AR to compensate for terminal cell aspect (~1:2) so output is not stretched")

def measure_font_metrics(font):
    """
    Measure character width and height for a given font.
    Measures all characters from all character sets to find maximum dimensions.
    Measures characters as they will be rendered (with baseline alignment).
    Returns (char_width, char_height) tuple.
    """
    # Use a larger temporary image to measure characters
    temp_size = 1000
    dummy_img = Image.new("RGB", (temp_size, temp_size))
    dummy_draw = ImageDraw.Draw(dummy_img)
    
    # Collect all characters from all sets
    all_chars = set(ASCII_CHARS + ASCII_BLOCKS + ASCII_ALPHABET + ASCII_DIGITS + ASCII_ALPHANUMERIC + ASCII_DOTS)
    
    # First pass: find baseline offsets (minimum left and top)
    min_left = float('inf')
    min_top = float('inf')
    for char in all_chars:
        bbox = dummy_draw.textbbox((0, 0), char, font=font)
        min_left = min(min_left, bbox[0])
        min_top = min(min_top, bbox[1])
    
    baseline_offset_x = -min_left
    baseline_offset_y = -min_top
    
    # Second pass: measure each character when drawn at baseline offset position
    # This gives us the actual extents as they will be rendered
    max_right = 0
    max_bottom = 0
    min_rendered_left = float('inf')
    min_rendered_top = float('inf')
    
    for char in all_chars:
        # Measure character when drawn at baseline offset (as it will be rendered)
        bbox = dummy_draw.textbbox((baseline_offset_x, baseline_offset_y), char, font=font)
        min_rendered_left = min(min_rendered_left, bbox[0])
        min_rendered_top = min(min_rendered_top, bbox[1])
        max_right = max(max_right, bbox[2])
        max_bottom = max(max_bottom, bbox[3])
    
    # Calculate dimensions needed to fit all characters in their rendered positions
    char_w = max_right - min_rendered_left
    char_h = max_bottom - min_rendered_top
    
    # Add adaptive padding to prevent clipping
    # Use more generous padding to ensure no clipping occurs
    # For small fonts, use fixed pixel padding; for larger fonts, use percentage
    if char_w < 10:
        padding_w = max(2, int(round(char_w * 0.15)))  # At least 2px or 15% for very small fonts
    elif char_w < 20:
        padding_w = max(2, int(round(char_w * 0.18)))  # At least 2px or 18% for small fonts
    else:
        padding_w = max(4, int(round(char_w * 0.25)))  # At least 4px or 25% for larger fonts
    
    if char_h < 10:
        padding_h = max(2, int(round(char_h * 0.15)))  # At least 2px or 15% for very small fonts
    elif char_h < 20:
        padding_h = max(2, int(round(char_h * 0.18)))  # At least 2px or 18% for small fonts
    else:
        padding_h = max(4, int(round(char_h * 0.25)))  # At least 4px or 25% for larger fonts
    
    # Return integer dimensions
    return int(round(char_w + padding_w)), int(round(char_h + padding_h))

def frame_to_text(frame, char_w, char_h, chars, invert_brightness=False, swap_dims=False):
    """
    Convert a frame (RGB numpy array) into a multi-line ASCII string.
    Uses grayscale + min/max normalization for character selection.
    """
    h, w = frame.shape[:2]
    if swap_dims:
        h, w = w, h
    cols = w // char_w
    rows = h // char_h

    img_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    img_small = cv2.resize(img_gray, (cols, rows), interpolation=cv2.INTER_NEAREST)

    num_chars = len(chars)
    img_min, img_max = img_small.min(), img_small.max()
    if img_max > img_min:
        img_normalized = (img_small - img_min) / (img_max - img_min)
    else:
        img_normalized = img_small / 255.0

    if invert_brightness:
        indices = ((1.0 - img_normalized) * (num_chars - 1)).astype(int)
    else:
        indices = (img_normalized * (num_chars - 1)).astype(int)
    indices = np.clip(indices, 0, num_chars - 1)

    return "\n".join("".join(chars[idx] for idx in row) for row in indices)

def process_frame(frame, options):
    """
    Process a single frame (numpy array) into ASCII art.
    
    Args:
        frame: numpy array of shape (h, w, 3) - RGB image
        options: AsciiFrameOptions object containing processing parameters
    
    Returns:
        numpy array of shape (rows * char_h, cols * char_w, 3) - ASCII art image
    """
    h, w = frame.shape[:2]
    if options.swap_dims:
        h, w = w, h
    
    # Calculate grid dimensions
    cols = w // options.char_w
    rows = h // options.char_h
    
    if options.preserve_colors:
        # Preserve colors mode: skip grayscale and normalization
        # Resize RGB frame to grid size
        img_small_rgb = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_AREA)
        
        # Calculate brightness for character selection (but don't normalize)
        # Use luminance formula: 0.299*R + 0.587*G + 0.114*B
        img_brightness = (0.299 * img_small_rgb[:, :, 0] + 
                         0.587 * img_small_rgb[:, :, 1] + 
                         0.114 * img_small_rgb[:, :, 2])
        
        num_chars = options.num_chars if options.num_chars is not None else len(options.char_palette)
        
        # Map brightness directly to indices without normalization
        # Use full 0-255 range mapped to 0-(num_chars-1)
        if options.invert_brightness:
            indices = ((255.0 - img_brightness) / 255.0 * (num_chars - 1)).astype(int)
        else:
            indices = (img_brightness / 255.0 * (num_chars - 1)).astype(int)
        
        indices = np.clip(indices, 0, num_chars - 1)
        
        # Get selected characters
        tiled_chars = options.char_palette[indices]  # (rows, cols, char_h, char_w, 3)
        
        # Colorize characters based on original pixel colors
        bg_color_arr = np.array(options.bg_color, dtype=np.float32)
        fg_color_arr = np.array(options.fg_color, dtype=np.float32)
        
        # Expand sampled colors to match character dimensions
        cell_colors = img_small_rgb.astype(np.float32)  # (rows, cols, 3)
        cell_colors_expanded = cell_colors[:, :, np.newaxis, np.newaxis, :]  # (rows, cols, 1, 1, 3)
        
        # Create mask using luminance-based approach for better antialiasing handling
        # Convert character pixels to grayscale to determine character intensity
        tiled_chars_float = tiled_chars.astype(np.float32)
        
        # Calculate luminance of each pixel in the character
        char_luminance = (0.299 * tiled_chars_float[:, :, :, :, 0] + 
                         0.587 * tiled_chars_float[:, :, :, :, 1] + 
                         0.114 * tiled_chars_float[:, :, :, :, 2])
        
        # Calculate luminance of bg and fg colors
        bg_lum = 0.299 * bg_color_arr[0] + 0.587 * bg_color_arr[1] + 0.114 * bg_color_arr[2]
        fg_lum = 0.299 * fg_color_arr[0] + 0.587 * fg_color_arr[1] + 0.114 * fg_color_arr[2]
        
        # Create mask based on how close pixel luminance is to fg vs bg
        # Normalize to 0-1 range where 1 = fully foreground, 0 = fully background
        if abs(fg_lum - bg_lum) > 1e-6:
            fg_mask = np.clip((char_luminance - bg_lum) / (fg_lum - bg_lum), 0.0, 1.0)
        else:
            # If fg and bg have same luminance, use color distance instead
            char_diff_fg = np.sum((tiled_chars_float - fg_color_arr) ** 2, axis=-1)
            char_diff_bg = np.sum((tiled_chars_float - bg_color_arr) ** 2, axis=-1)
            total_diff = char_diff_fg + char_diff_bg
            fg_mask = np.where(total_diff > 1e-6, 1.0 - (char_diff_fg / total_diff), 0.5)
        
        fg_mask = fg_mask[:, :, :, :, np.newaxis]  # Add channel dimension
        
        # Apply tint if specified
        if options.tint_color is not None:
            tint_arr = np.array(options.tint_color, dtype=np.float32) / 255.0
            cell_colors_expanded = cell_colors_expanded * tint_arr
        
        # Apply color: blend sampled color with character based on mask
        # This preserves antialiasing and character shape
        tiled_chars = (cell_colors_expanded * fg_mask + 
                      bg_color_arr * (1.0 - fg_mask)).astype(np.uint8)
        
    else:
        # Original mode: Grayscale & Normalize
        img_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        img_small = cv2.resize(img_gray, (cols, rows), interpolation=cv2.INTER_NEAREST)

        # Map pixels to Indices
        num_chars = options.num_chars if options.num_chars is not None else len(options.char_palette)
        
        # Normalize to 0-1 range using min/max to ensure full range is used
        img_min = img_small.min()
        img_max = img_small.max()
        if img_max > img_min:
            img_normalized = (img_small - img_min) / (img_max - img_min)
        else:
            img_normalized = img_small / 255.0
        
        if options.invert_brightness:
            indices = ((1.0 - img_normalized) * (num_chars - 1)).astype(int)
        else:
            indices = (img_normalized * (num_chars - 1)).astype(int)
        
        indices = np.clip(indices, 0, num_chars - 1)

        # The Magic Trick (Advanced Numpy Indexing)
        tiled_chars = options.char_palette[indices]

    # Stitching (Reshaping)
    # Swap axes to: (rows, char_h, cols, char_w, 3)
    tiled_chars = tiled_chars.swapaxes(1, 2)
    
    # Collapse the grid
    final_frame = tiled_chars.reshape(rows * options.char_h, cols * options.char_w, 3)
    
    return final_frame
