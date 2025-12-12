#!/usr/bin/env python3
"""
Script to update demo images and videos.
Processes source files and creates ASCII versions and collages.
"""
import subprocess
import os
import sys
from pathlib import Path

# Source files
SOURCES = {
    "images": ["demo/cat_src.png", "demo/cat2_src.png"],
    "video": "cat_src.mp4"
}

FONT_SIZE = 5
FONT_SIZE_VIDEO = 10

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"Error: {description} failed with exit code {result.returncode}")
        sys.exit(1)

def process_images():
    """Process source images to ASCII versions."""
    for img in SOURCES["images"]:
        if not os.path.exists(img):
            print(f"Warning: {img} not found, skipping...")
            continue
        
        output = img.replace(".png", "_ascii.png")
        cmd = ["python3", "ascii_image.py", img, "-f", str(FONT_SIZE), "-o", output]
        run_command(cmd, f"Processing {img} -> {output}")

def process_video():
    """Process source video to ASCII version."""
    video = SOURCES["video"]
    if not os.path.exists(video):
        print(f"Warning: {video} not found, skipping...")
        return
    
    output = video.replace(".mp4", "_ascii.mp4")
    cmd = ["python3", "ascii_video.py", video, "-f", str(FONT_SIZE_VIDEO), "-o", output]
    run_command(cmd, f"Processing {video} -> {output}")

def create_collage(height=None):
    """Create side-by-side collage of original and ASCII video."""
    original = SOURCES["video"]
    ascii_video = original.replace(".mp4", "_ascii.mp4")
    
    if not os.path.exists(original):
        print(f"Warning: {original} not found, skipping collage...")
        return
    if not os.path.exists(ascii_video):
        print(f"Warning: {ascii_video} not found, skipping collage...")
        return
    
    # Get original video dimensions
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", original
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    import json
    info = json.loads(result.stdout)
    orig_width = info["streams"][0]["width"]
    orig_height = info["streams"][0]["height"]
    
    # Create demo directory if it doesn't exist
    os.makedirs("demo", exist_ok=True)
    
    if height:
        # Fixed height collage (480px)
        output = "demo/cat_src_collage.mp4"
        scale_filter = f"scale=-1:{height}"
        # Pad width to even number for libx264
        cmd = [
            "ffmpeg", "-i", original, "-i", ascii_video,
            "-filter_complex",
            f"[0:v]{scale_filter}[v0];[1:v]{scale_filter}[v1];[v0][v1]hstack=inputs=2,pad=ceil(iw/2)*2:ih[v]",
            "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-c:a", "copy",
            "-y", output
        ]
        run_command(cmd, f"Creating collage {output} (height={height}px)")
    else:
        # Full resolution collage (use original height)
        output = "cat_src_collage_fullres.mp4"
        # Scale ASCII video to match original height
        scale_filter = f"scale=-1:{orig_height}"
        # Pad width to even number for libx264
        cmd = [
            "ffmpeg", "-i", original, "-i", ascii_video,
            "-filter_complex",
            f"[0:v]scale={orig_width}:{orig_height}[v0];[1:v]{scale_filter}[v1];[v0][v1]hstack=inputs=2,pad=ceil(iw/2)*2:ih[v]",
            "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-c:a", "copy",
            "-y", output
        ]
        run_command(cmd, f"Creating collage {output} (full resolution)")

def main():
    """Main function."""
    print("="*60)
    print("Updating demo images and videos")
    print("="*60)
    
    # Process images
    process_images()
    
    # Process video
    process_video()
    
    # Create collages
    create_collage(height=480)  # Fixed height
    create_collage(height=None)  # Full resolution
    
    print("\n" + "="*60)
    print("All done!")
    print("="*60)

if __name__ == "__main__":
    main()
