#!/usr/bin/env python3
"""
Measure brightness of symbols and sort them in ascending order (darkest to lightest).
"""
import argparse
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ascii_common import load_font, measure_font_metrics

def measure_char_brightness(char, font, bg_color=(0, 0, 0), fg_color=(255, 255, 255)):
    """
    Measure the brightness of a character when rendered.
    Returns average pixel brightness (0-255).
    """
    # Measure font metrics
    char_w, char_h = measure_font_metrics(font)
    
    # Create image with background color
    img = Image.new("RGB", (char_w, char_h), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Measure baseline offset
    dummy_img = Image.new("RGB", (char_w * 2, char_h * 2))
    dummy_draw = ImageDraw.Draw(dummy_img)
    ref_bbox = dummy_draw.textbbox((0, 0), char, font=font)
    baseline_offset_x = -ref_bbox[0]
    baseline_offset_y = -ref_bbox[1]
    
    # Draw character
    draw.text((baseline_offset_x, baseline_offset_y), char, font=font, fill=fg_color)
    
    # Convert to numpy array and calculate average brightness
    img_array = np.array(img)
    
    # Calculate luminance: 0.299*R + 0.587*G + 0.114*B
    brightness = (0.299 * img_array[:, :, 0] + 
                  0.587 * img_array[:, :, 1] + 
                  0.114 * img_array[:, :, 2])
    
    return brightness.mean()

def main():
    parser = argparse.ArgumentParser(
        description="Measure brightness of symbols and sort them in ascending order (darkest to lightest)"
    )
    parser.add_argument(
        "symbols",
        nargs="*",
        help="Symbols to measure (space-separated). If not provided, reads from stdin."
    )
    parser.add_argument(
        "-f", "--fontsize",
        type=int,
        default=10,
        help="Font size (default: 10)"
    )
    parser.add_argument(
        "--font-path",
        default="/System/Library/Fonts/Menlo.ttc",
        help="Path to font file (default: /System/Library/Fonts/Menlo.ttc)"
    )
    parser.add_argument(
        "--bg-color",
        default="black",
        help="Background color (default: black)"
    )
    parser.add_argument(
        "--fg-color",
        default="white",
        help="Foreground color (default: white)"
    )
    parser.add_argument(
        "--show-values",
        action="store_true",
        help="Show brightness values alongside symbols"
    )
    
    args = parser.parse_args()
    
    # Get symbols from args or stdin
    if args.symbols:
        symbols = args.symbols
    else:
        # Read from stdin
        if sys.stdin.isatty():
            print("Enter symbols (one per line, or space-separated on one line):")
        symbols = []
        for line in sys.stdin:
            line = line.strip()
            if line:
                # Split by spaces if multiple symbols on one line
                symbols.extend(line.split())
    
    if not symbols:
        print("Error: No symbols provided", file=sys.stderr)
        sys.exit(1)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_symbols = []
    for symbol in symbols:
        if symbol not in seen:
            seen.add(symbol)
            unique_symbols.append(symbol)
    
    if len(unique_symbols) < len(symbols):
        print(f"Removed {len(symbols) - len(unique_symbols)} duplicate(s).")
    
    # Add space as darkest symbol if not already present
    has_space = ' ' in unique_symbols
    if not has_space:
        unique_symbols.insert(0, ' ')
        print("Added space character as darkest symbol.")
    
    # Load font
    font = load_font(args.fontsize, args.font_path)
    
    # Parse colors
    from PIL import ImageColor
    try:
        bg_color = ImageColor.getcolor(args.bg_color, "RGB")
        fg_color = ImageColor.getcolor(args.fg_color, "RGB")
    except ValueError as e:
        print(f"Error: Invalid color format. {e}", file=sys.stderr)
        sys.exit(1)
    
    # Measure brightness for each symbol
    print(f"Measuring brightness of {len(unique_symbols)} symbol(s)...")
    symbol_brightness = []
    
    for symbol in unique_symbols:
        brightness = measure_char_brightness(symbol, font, bg_color, fg_color)
        symbol_brightness.append((symbol, brightness))
    
    # Sort by brightness (ascending - darkest to lightest)
    # Ensure space is always first (darkest)
    space_entry = None
    other_entries = []
    for entry in symbol_brightness:
        if entry[0] == ' ':
            space_entry = entry
        else:
            other_entries.append(entry)
    
    other_entries.sort(key=lambda x: x[1])
    
    # Reconstruct with space first
    if space_entry:
        symbol_brightness = [space_entry] + other_entries
    else:
        symbol_brightness = other_entries
    
    # Output results
    print("\nSorted symbols (darkest to lightest):")
    print("-" * 50)
    
    if args.show_values:
        for symbol, brightness in symbol_brightness:
            print(f"{symbol!r:10} {brightness:8.2f}")
    else:
        # Output as Python list format
        sorted_symbols = [s for s, _ in symbol_brightness]
        print("[" + ", ".join(repr(s) for s in sorted_symbols) + "]")
        
        # Also output as string for easy copy-paste
        print("\nAs string:")
        print("".join(sorted_symbols))
        
        # Show values in a comment
        print("\nBrightness values:")
        print("# " + ", ".join(f"{s!r}:{b:.1f}" for s, b in symbol_brightness))

if __name__ == "__main__":
    main()
