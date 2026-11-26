#!/usr/bin/env python3
"""
Create animated GIF from fontsize demo images.
"""
import os
from PIL import Image

INPUT_DIR = "demo/fontsize"
OUTPUT_GIF = "demo/fontsize_animation.gif"

def main():
    """Create animated GIF from fontsize images."""
    if not os.path.exists(INPUT_DIR):
        print(f"Error: {INPUT_DIR} not found")
        return
    
    # Get all fontsize images, sorted by font size
    images = []
    for i in range(1, 21):
        filename = f"cat_src_fontsize_{i:02d}.png"
        filepath = os.path.join(INPUT_DIR, filename)
        if os.path.exists(filepath):
            images.append(Image.open(filepath))
        else:
            print(f"Warning: {filepath} not found, skipping...")
    
    if not images:
        print("No images found to create GIF")
        return
    
    print(f"Creating animated GIF from {len(images)} images...")
    print(f"Output: {OUTPUT_GIF}")
    
    # Create animated GIF
    # duration is in milliseconds (500ms = 0.5 seconds per frame)
    images[0].save(
        OUTPUT_GIF,
        save_all=True,
        append_images=images[1:],
        duration=500,  # 500ms per frame
        loop=0  # 0 means infinite loop
    )
    
    print(f"✓ Created {OUTPUT_GIF}")

if __name__ == "__main__":
    main()
