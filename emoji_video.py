import argparse
import sys
import subprocess
import json
import os
import numpy as np
from tqdm import tqdm

try:
    from moviepy.editor import VideoFileClip, ImageSequenceClip
except ImportError:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.io.ImageSequenceClip import ImageSequenceClip

from emoji_common import (
    EMOJI_SETS, pre_render_emojis, load_emoji_font, parse_colors,
    process_frame, EmojiFrameOptions, add_common_arguments
)


def get_video_rotation(video_path):
    """Get rotation metadata from video file using ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', '-select_streams', 'v:0', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        if 'streams' in data and len(data['streams']) > 0:
            stream = data['streams'][0]
            rotation = 0
            if 'tags' in stream and 'rotate' in stream['tags']:
                rotation = int(stream['tags']['rotate'])
            elif 'side_data_list' in stream:
                for side_data in stream['side_data_list']:
                    if side_data.get('rotation'):
                        rotation = side_data['rotation']
                        break
            
            rotation = rotation % 360
            if rotation not in [0, 90, 180, 270]:
                rotation = 0
            return rotation
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, ValueError):
        pass
    
    return 0


def process_video(clip, font, font_size, output_path, emoji_size=32, scale=1.0, video_path=None,
                  bg_color=(0, 0, 0), emoji_set='all'):
    """Process video to emoji art using color matching."""
    
    # Resize
    if scale != 1.0:
        try:
            clip = clip.resize(scale)
        except AttributeError:
            clip = clip.resized(scale)
    
    w, h = clip.size
    
    # Handle rotation
    rotation = 0
    swap_dims = False
    if video_path:
        rotation = get_video_rotation(video_path)
        print(f"Video rotation: {rotation}°")
        if rotation in [90, 270]:
            print(f"Swapping dimensions for rotation: {w}x{h} -> {h}x{w}")
            w, h = h, w
            swap_dims = True
    
    cols = w // emoji_size
    rows = h // emoji_size
    
    print(f"Resolution: {w}x{h}")
    print(f"Grid: {cols}x{rows}")
    print(f"Emoji Size: {emoji_size}x{emoji_size}")
    
    # Get emojis
    emojis = EMOJI_SETS[emoji_set]
    print(f"Emoji set: {emoji_set} ({len(emojis)} emojis)")
    
    # Pre-render emoji palette
    print("Pre-rendering emojis...")
    emoji_palette, emoji_colors = pre_render_emojis(font, font_size, emoji_size, bg_color, emojis)
    num_emojis = len(emojis)
    
    options = EmojiFrameOptions(
        emoji_palette=emoji_palette,
        emoji_colors=emoji_colors,
        emoji_size=emoji_size,
        num_emojis=num_emojis,
        bg_color=bg_color,
        swap_dims=swap_dims
    )
    
    processed_frames = []
    
    print("Rendering frames...")
    for frame in tqdm(clip.iter_frames(), total=int(clip.fps * clip.duration)):
        final_frame = process_frame(frame, options)
        processed_frames.append(final_frame)
    
    print("Encoding video...")
    final_clip = ImageSequenceClip(processed_frames, fps=clip.fps)
    
    if clip.audio:
        final_clip = final_clip.set_audio(clip.audio)
    
    final_w, final_h = final_clip.size
    print(f"Resulting video resolution: {final_w}x{final_h}")
    
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")


def main():
    parser = argparse.ArgumentParser(description="Emoji Video Generator")
    add_common_arguments(parser, input_help="Path to input video file", output_help="Path to output video file")
    args = parser.parse_args()
    
    if args.output is None:
        base, ext = os.path.splitext(args.input)
        args.output = f"{base}_emoji{ext}"
    
    bg_color = parse_colors(args.bg_color)
    font, font_size = load_emoji_font(args.emoji_size)
    
    try:
        clip = VideoFileClip(args.input)
        process_video(clip, font, font_size, args.output, args.emoji_size, args.scale, video_path=args.input,
                      bg_color=bg_color, emoji_set=args.emoji_set)
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
