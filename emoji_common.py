"""
Common utilities for Emoji image and video processing.
"""
import sys
import argparse
from dataclasses import dataclass
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageColor

# Emoji sets
EMOJI_SMILES = list("😀😃😄😁😆😅🤣😂🙂🙃😉😊😇🥰😍🤩😘😗☺😚😙🥲😋😛😜🤪😝🤑🤗🤭🤫🤔🤐🤨😐😑😶😏😒🙄😬🤥😌😔😪🤤😴😷🤒🤕🤢🤮🤧🥵🥶🥴😵🤯🤠🥳🥸😎🤓🧐😕😟🙁☹😮😯😲😳🥺🥹😦😧😨😰😥😢😭😱😖😣😞😓😩😫🥱😤😡😠🤬😈👿💀☠💩🤡👹👺👻👽👾🤖😺😸😹😻😼😽🙀😿😾")

EMOJI_FOOD = list("🍎🍊🍋🍌🍉🍇🍓🍒🍑🥭🍍🥥🥝🍅🥑🥦🥬🥒🌶🌽🥕🧄🧅🥔🍠🥐🥯🍞🥖🥨🧀🥚🍳🧈🥞🧇🥓🥩🍗🍖🌭🍔🍟🍕🥪🥙🌮🌯🥗🥘🥫🍝🍜🍲🍛🍣🍱🥟🍤🍙🍚🍘🍥🥠🥮🍢🍡🍧🍨🍦🥧🧁🍰🎂🍮🍭🍬🍫🍿🍩🍪🌰🥜🍯🥛🍼☕🍵🧃🥤🍶🍺🍻🥂🍷🥃🍸🍹🍾")

EMOJI_ANIMALS = list("🐶🐱🐭🐹🐰🦊🐻🐼🐨🐯🦁🐮🐷🐽🐸🐵🙈🙉🙊🐒🐔🐧🐦🐤🐣🐥🦆🦅🦉🦇🐺🐗🐴🦄🐝🐛🦋🐌🐞🐜🐢🐍🦎🦖🦕🐙🦑🦐🦞🦀🐡🐠🐟🐬🐳🐋🦈🐊🐅🐆🦓🦍🐘🦛🦏🐪🐫🦒🦘🐃🐂🐄🐎🐖🐏🐑🐐🦌🐕🐩🐈🐓🦃🦚🦜🦢🦩🐇🦝🦨🦡🦦🦥🐁🐀🐿🦔🐾")

EMOJI_ALL = EMOJI_SMILES + EMOJI_FOOD + EMOJI_ANIMALS

EMOJI_SETS = {
    'all': EMOJI_ALL,
    'smiles': EMOJI_SMILES,
    'food': EMOJI_FOOD,
    'animals': EMOJI_ANIMALS,
}


@dataclass
class EmojiFrameOptions:
    """Options for processing a frame into emoji art."""
    emoji_palette: np.ndarray  # Pre-rendered emoji palette, shape (num_emojis, size, size, 3)
    emoji_colors: np.ndarray   # Average color of each emoji, shape (num_emojis, 3)
    emoji_size: int
    num_emojis: int = None
    bg_color: tuple = (0, 0, 0)
    swap_dims: bool = False


def get_emoji_average_color(emoji, font, size, bg_color):
    """Get the average color of an emoji (excluding background)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Center the emoji
    bbox = draw.textbbox((0, 0), emoji, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2 - bbox[0]
    y = (size - text_h) // 2 - bbox[1]
    
    draw.text((x, y), emoji, font=font, embedded_color=True)
    
    arr = np.array(img)
    rgb = arr[:, :, :3].astype(np.float32)
    alpha = arr[:, :, 3].astype(np.float32) / 255.0
    
    # Calculate weighted average color
    if alpha.sum() > 0:
        r = (rgb[:, :, 0] * alpha).sum() / alpha.sum()
        g = (rgb[:, :, 1] * alpha).sum() / alpha.sum()
        b = (rgb[:, :, 2] * alpha).sum() / alpha.sum()
        return np.array([r, g, b])
    else:
        return np.array(bg_color, dtype=np.float32)


def pre_render_emojis(font, font_size, target_size, bg_color, emojis):
    """
    Renders every emoji into a numpy array once.
    Renders at font_size then scales to target_size if different.
    Returns (palette, colors) where:
      - palette: shape (num_emojis, target_size, target_size, 3)
      - colors: shape (num_emojis, 3) - average color of each emoji
    """
    emoji_images = []
    emoji_colors = []
    
    for emoji in emojis:
        # Get average color (at font_size)
        avg_color = get_emoji_average_color(emoji, font, font_size, bg_color)
        emoji_colors.append(avg_color)
        
        # Create image with background color at font_size
        img = Image.new("RGBA", (font_size, font_size), (*bg_color, 255))
        draw = ImageDraw.Draw(img)
        
        # Center the emoji
        bbox = draw.textbbox((0, 0), emoji, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (font_size - text_w) // 2 - bbox[0]
        y = (font_size - text_h) // 2 - bbox[1]
        
        draw.text((x, y), emoji, font=font, embedded_color=True)
        
        # Convert to RGB
        rgb_img = Image.new("RGB", (font_size, font_size), bg_color)
        rgb_img.paste(img, mask=img.split()[3])
        
        # Scale to target size if needed
        if font_size != target_size:
            rgb_img = rgb_img.resize((target_size, target_size), Image.LANCZOS)
        
        emoji_images.append(np.array(rgb_img))
    
    return np.stack(emoji_images), np.stack(emoji_colors)


VALID_EMOJI_SIZES = [20, 32, 40, 48, 52, 64, 96, 160]


def find_nearest_valid_size(size):
    """Find the nearest valid emoji font size."""
    return min(VALID_EMOJI_SIZES, key=lambda x: abs(x - size))


def load_emoji_font(size=32):
    """Load Apple Color Emoji font at a valid size."""
    font_path = "/System/Library/Fonts/Apple Color Emoji.ttc"
    
    # Try requested size first
    try:
        font = ImageFont.truetype(font_path, size)
        return font, size
    except (IOError, OSError):
        pass
    
    # Find nearest valid size
    valid_size = find_nearest_valid_size(size)
    try:
        font = ImageFont.truetype(font_path, valid_size)
        print(f"Emoji font loaded at size {valid_size} (requested {size}, will scale)")
        return font, valid_size
    except (IOError, OSError):
        pass
    
    # Try Linux fallback
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", size)
        return font, size
    except (IOError, OSError):
        print("Error: No emoji font found")
        sys.exit(1)


def parse_colors(bg_color_str):
    """Parse background color string to RGB tuple."""
    try:
        bg_color = ImageColor.getcolor(bg_color_str, "RGB")
        return bg_color
    except ValueError as e:
        print(f"Error: Invalid color format. {e}")
        sys.exit(1)


def add_common_arguments(parser, input_help="Path to input file", output_help="Path to output file"):
    """Add common emoji processing arguments to an ArgumentParser."""
    parser.add_argument("input", help=input_help)
    parser.add_argument("-o", "--output", help=output_help, default=None)
    parser.add_argument("-e", "--emoji-size", type=int, help="Emoji size in pixels", default=32)
    parser.add_argument("-s", "--scale", type=float, help="Scale (0.5 is faster)", default=1.0)
    parser.add_argument("--bg-color", help="Background color (e.g., 'black', '#000000')", default="black")
    parser.add_argument("--emoji-set", choices=['all', 'smiles', 'food', 'animals'], default='all',
                        help="Emoji set to use (default: all)")


def process_frame(frame, options):
    """
    Process a single frame (numpy array) into emoji art.
    Selects emojis based on color matching.
    
    Args:
        frame: numpy array of shape (h, w, 3) - RGB image
        options: EmojiFrameOptions object
    
    Returns:
        numpy array of shape (rows * emoji_size, cols * emoji_size, 3)
    """
    h, w = frame.shape[:2]
    if options.swap_dims:
        h, w = w, h
    
    size = options.emoji_size
    cols = w // size
    rows = h // size
    
    num_emojis = options.num_emojis if options.num_emojis is not None else len(options.emoji_palette)
    
    # Resize RGB frame to grid size
    img_small = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_AREA).astype(np.float32)
    
    # Find closest emoji for each cell by color distance
    # img_small: (rows, cols, 3)
    # emoji_colors: (num_emojis, 3)
    
    # Expand dims for broadcasting
    img_expanded = img_small[:, :, np.newaxis, :]  # (rows, cols, 1, 3)
    colors_expanded = options.emoji_colors[np.newaxis, np.newaxis, :, :]  # (1, 1, num_emojis, 3)
    
    # Calculate squared color distance
    diff = img_expanded - colors_expanded  # (rows, cols, num_emojis, 3)
    distances = np.sum(diff ** 2, axis=-1)  # (rows, cols, num_emojis)
    
    # Find index of closest emoji
    indices = np.argmin(distances, axis=-1)  # (rows, cols)
    
    # Get selected emojis
    tiled_emojis = options.emoji_palette[indices]  # (rows, cols, size, size, 3)
    
    # Stitch together
    tiled_emojis = tiled_emojis.swapaxes(1, 2)
    final_frame = tiled_emojis.reshape(rows * size, cols * size, 3)
    
    return final_frame
