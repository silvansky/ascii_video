#!/usr/bin/env python3
"""
Generate ASCII images with different font sizes for demo purposes.
"""
import subprocess
import os
import sys

INPUT_IMAGE = "demo/cat_src.png"
OUTPUT_DIR = "demo/fontsize"

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"Running: {description}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {description} failed")
        print(result.stderr)
        return False
    return True

def main():
    """Generate ASCII images with font sizes 1-20."""
    if not os.path.exists(INPUT_IMAGE):
        print(f"Error: {INPUT_IMAGE} not found")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"Generating ASCII images from {INPUT_IMAGE}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("="*60)
    
    for fontsize in range(1, 21):
        output_file = os.path.join(OUTPUT_DIR, f"cat_src_fontsize_{fontsize:02d}.png")
        cmd = [
            "python3", "ascii_image.py",
            INPUT_IMAGE,
            "-f", str(fontsize),
            "-o", output_file
        ]
        
        success = run_command(cmd, f"Font size {fontsize}")
        if success:
            print(f"  ✓ Created {output_file}")
        else:
            print(f"  ✗ Failed font size {fontsize}")
    
    print("="*60)
    print("Done!")

if __name__ == "__main__":
    main()
