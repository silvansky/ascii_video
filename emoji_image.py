import argparse
import sys
import os
import numpy as np
import cv2
from PIL import Image
from emoji_common import (
    EMOJI_SETS, pre_render_emojis, compute_emoji_colors, frame_to_emoji_text,
    load_emoji_font, parse_colors, process_frame, EmojiFrameOptions, add_common_arguments
)


def process_image(image_path, font, font_size, output_path, emoji_size=32, scale=1.0, bg_color=(0, 0, 0),
                  emoji_set='all'):
    """Process image to emoji art using color matching."""
    # Load image
    img = Image.open(image_path)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    frame = np.array(img)
    
    # Apply scale
    if scale != 1.0:
        h, w = frame.shape[:2]
        new_h, new_w = int(h * scale), int(w * scale)
        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    h, w = frame.shape[:2]
    cols = w // emoji_size
    rows = h // emoji_size
    
    print(f"Resolution: {w}x{h}")
    print(f"Grid: {cols}x{rows}")
    print(f"Emoji Size: {emoji_size}x{emoji_size}")
    
    # Get emojis
    emojis = EMOJI_SETS[emoji_set]
    print(f"Emoji set: {emoji_set} ({len(emojis)} emojis)")

    if output_path.lower().endswith(".txt"):
        print("Computing emoji colors...")
        emoji_colors = compute_emoji_colors(font, font_size, bg_color, emojis)
        print("Rendering text...")
        text = frame_to_emoji_text(frame, emoji_size, emojis, emoji_colors)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved to {output_path}")
        return

    # Pre-render emoji palette and get colors
    print("Pre-rendering emojis...")
    emoji_palette, emoji_colors = pre_render_emojis(font, font_size, emoji_size, bg_color, emojis)
    num_emojis = len(emojis)
    
    print("Rendering image...")
    
    options = EmojiFrameOptions(
        emoji_palette=emoji_palette,
        emoji_colors=emoji_colors,
        emoji_size=emoji_size,
        num_emojis=num_emojis,
        bg_color=bg_color,
        swap_dims=False
    )
    
    final_image = process_frame(frame, options)
    
    output_img = Image.fromarray(final_image.astype(np.uint8))
    output_img.save(output_path)
    print(f"Saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Emoji Image Generator")
    add_common_arguments(parser, input_help="Path to input image file", output_help="Path to output image file")
    args = parser.parse_args()
    
    if args.output is None:
        base, ext = os.path.splitext(args.input)
        args.output = f"{base}_emoji{ext}"
    
    bg_color = parse_colors(args.bg_color)
    font, font_size = load_emoji_font(args.emoji_size)
    
    try:
        process_image(args.input, font, font_size, args.output, args.emoji_size, args.scale, bg_color,
                      args.emoji_set)
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
