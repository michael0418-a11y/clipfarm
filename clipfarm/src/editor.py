"""
Module 3: Auto Editor — The Core Engine
Takes raw video + timestamps and produces TikTok-ready clips with:
- Dynamic captions (whopio_clips style)
- Zoom/pan effects
- Hook text + CTA end screen
- Color grading
- Speed ramps
"""

import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None

# Output dimensions (9:16 TikTok)
WIDTH = 1080
HEIGHT = 1920

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "clips"
TEMP_DIR = PROJECT_ROOT / "temp"
ASSETS_DIR = PROJECT_ROOT / "assets"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def _get_font(size: int):
    """Get a bold font, falling back gracefully."""
    if ImageFont is None:
        return None

    # Try common bold fonts
    font_names = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    # Check for custom font in assets
    custom_fonts = list(ASSETS_DIR.glob("fonts/*.ttf"))
    if custom_fonts:
        font_names.insert(0, str(custom_fonts[0]))

    for font_path in font_names:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue

    return ImageFont.load_default()


def create_text_image(
    text: str,
    width: int = WIDTH,
    font_size: int = 80,
    color: str = "white",
    outline_color: str = "black",
    outline_width: int = 4,
    bg_color: str = None,
    padding: int = 20,
) -> str:
    """
    Create a transparent PNG with styled text (whopio_clips style).
    Returns path to the PNG.
    """
    if Image is None:
        raise ImportError("Pillow is required: pip install Pillow")

    font = _get_font(font_size)

    # Measure text
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Word wrap if too wide
    if text_w > width - padding * 2:
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            test_bbox = draw.textbbox((0, 0), test, font=font)
            if test_bbox[2] - test_bbox[0] > width - padding * 2:
                if current_line:
                    lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)
        text = "\n".join(lines)

        # Recalculate
        bbox = draw.multiline_textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

    img_w = text_w + padding * 2 + outline_width * 2
    img_h = text_h + padding * 2 + outline_width * 2

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Optional background
    if bg_color:
        draw.rounded_rectangle(
            [0, 0, img_w, img_h],
            radius=15,
            fill=bg_color,
        )

    x = padding + outline_width
    y = padding + outline_width

    # Draw outline by drawing text offset in all directions
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx * dx + dy * dy <= outline_width * outline_width:
                draw.multiline_text(
                    (x + dx, y + dy), text, font=font,
                    fill=outline_color, align="center",
                )

    # Draw main text
    draw.multiline_text((x, y), text, font=font, fill=color, align="center")

    # Save
    out_path = TEMP_DIR / f"text_{hash(text) & 0xFFFFFFFF:08x}.png"
    img.save(str(out_path))
    return str(out_path)


def build_ffmpeg_filter(
    clip_data: dict,
    caption_blocks: list,
    input_w: int,
    input_h: int,
    hook_text: str = "",
    cta_text: str = "Follow for more",
    handle: str = "@yourhandle",
    zoom_intensity: float = 1.15,
    color_grade: str = "cinematic",
) -> str:
    """
    Build the complex ffmpeg filtergraph for a single clip.
    This handles: crop to 9:16, zoom, color grading.
    Captions are overlaid via separate images for quality.
    """
    filters = []

    # Step 1: Scale to fit 9:16 — crop from center if landscape
    aspect = input_w / input_h
    target_aspect = WIDTH / HEIGHT  # 0.5625

    if aspect > target_aspect:
        # Landscape: crop width
        new_w = int(input_h * target_aspect)
        crop_x = (input_w - new_w) // 2
        filters.append(f"crop={new_w}:{input_h}:{crop_x}:0")
    elif aspect < target_aspect:
        # Portrait but wrong ratio
        new_h = int(input_w / target_aspect)
        crop_y = (input_h - new_h) // 2
        filters.append(f"crop={input_w}:{new_h}:0:{crop_y}")

    filters.append(f"scale={WIDTH}:{HEIGHT}")

    # Step 2: Subtle zoom effect (slow ken burns)
    # zoompan creates a slow zoom over the clip duration
    # We'll use a simpler approach: slight scale + position animation
    if zoom_intensity > 1.0:
        z = zoom_intensity
        filters.append(
            f"zoompan=z='min(zoom+0.0005,{z})':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d=1:s={WIDTH}x{HEIGHT}:fps=30"
        )

    # Step 3: Color grading
    if color_grade == "cinematic":
        filters.append("eq=contrast=1.1:brightness=0.02:saturation=1.2")
        filters.append("curves=preset=cross_process")
    elif color_grade == "vibrant":
        filters.append("eq=contrast=1.05:saturation=1.4:brightness=0.03")
    elif color_grade == "dark":
        filters.append("eq=contrast=1.2:brightness=-0.05:saturation=0.9")
        filters.append("vignette=PI/4")

    # Step 4: Subtle vignette for cinematic feel
    filters.append("vignette=PI/5")

    return ",".join(filters)


def edit_clip(
    video_path: str,
    start: float,
    end: float,
    hook_text: str = "WAIT FOR IT",
    caption_blocks: list = None,
    cta_text: str = "Follow for more",
    handle: str = "@yourhandle",
    output_name: str = None,
    zoom_intensity: float = 1.15,
    color_grade: str = "cinematic",
    hook_duration: float = 1.5,
    cta_duration: float = 2.0,
) -> str:
    """
    The main editing function. Takes a video + timestamps and produces
    a TikTok-ready clip with all effects.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if not output_name:
        output_name = f"clip_{start:.0f}_{end:.0f}"
    output_path = OUTPUT_DIR / f"{output_name}.mp4"

    duration = end - start
    print(f"[*] Editing clip: {start:.1f}s - {end:.1f}s ({duration:.1f}s)")

    # Get video info
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", str(video_path),
    ]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True)
    video_info = json.loads(probe.stdout)
    v_stream = next(s for s in video_info["streams"] if s["codec_type"] == "video")
    input_w = int(v_stream["width"])
    input_h = int(v_stream["height"])

    # --- STEP 1: Extract and process base clip ---
    print("[*] Step 1: Extracting base clip...")
    base_clip = str(TEMP_DIR / "base_clip.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(start), "-i", str(video_path),
        "-t", str(duration), "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        base_clip,
    ], capture_output=True, check=True)

    # --- STEP 2: Apply visual effects (crop, zoom, color grade) ---
    print("[*] Step 2: Applying visual effects...")
    vf = build_ffmpeg_filter(
        clip_data={}, caption_blocks=caption_blocks or [],
        input_w=input_w, input_h=input_h,
        zoom_intensity=zoom_intensity, color_grade=color_grade,
    )
    effects_clip = str(TEMP_DIR / "effects_clip.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", base_clip,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "copy",
        effects_clip,
    ], capture_output=True, check=True)

    # --- STEP 3: Create caption overlay images ---
    overlay_inputs = []
    overlay_filters = []
    input_idx = 1  # 0 is the video

    # Hook text (first 1.5 seconds)
    if hook_text:
        print(f"[*] Step 3a: Creating hook text: '{hook_text}'")
        hook_img = create_text_image(
            hook_text, font_size=90, color="white",
            outline_width=5, bg_color="#CC000000",
        )
        overlay_inputs.extend(["-i", hook_img])
        overlay_filters.append(
            f"[{input_idx}]format=rgba[hook];"
            f"[tmp{input_idx-1}][hook]overlay=(W-w)/2:(H-h)/3:"
            f"enable='between(t,0,{hook_duration})'"
            f"[tmp{input_idx}]"
        )
        input_idx += 1

    # Caption blocks
    if caption_blocks:
        print(f"[*] Step 3b: Creating {len(caption_blocks)} caption overlays...")
        # Limit to avoid ffmpeg input limit issues
        blocks_to_use = caption_blocks[:30]
        for i, block in enumerate(blocks_to_use):
            # Adjust timestamps relative to clip start
            t_start = block["start"] - start
            t_end = block["end"] - start
            if t_start < 0 or t_end > duration:
                continue

            cap_img = create_text_image(
                block["text"].upper(), font_size=72, color="white",
                outline_width=4,
            )
            overlay_inputs.extend(["-i", cap_img])
            overlay_filters.append(
                f"[{input_idx}]format=rgba[cap{i}];"
                f"[tmp{input_idx-1}][cap{i}]overlay=(W-w)/2:(H*3/4-h/2):"
                f"enable='between(t,{t_start:.2f},{t_end:.2f})'"
                f"[tmp{input_idx}]"
            )
            input_idx += 1

    # CTA end screen
    if cta_text:
        print(f"[*] Step 3c: Creating CTA end screen...")
        cta_full = f"{cta_text}\n{handle}"
        cta_img = create_text_image(
            cta_full, font_size=70, color="white",
            outline_width=4, bg_color="#DD000000",
        )
        cta_start = max(0, duration - cta_duration)
        overlay_inputs.extend(["-i", cta_img])
        overlay_filters.append(
            f"[{input_idx}]format=rgba[cta];"
            f"[tmp{input_idx-1}][cta]overlay=(W-w)/2:(H-h)/2:"
            f"enable='between(t,{cta_start:.2f},{duration:.2f})'"
            f"[tmp{input_idx}]"
        )
        input_idx += 1

    # --- STEP 4: Compose everything with ffmpeg ---
    print("[*] Step 4: Composing final clip...")

    if overlay_filters:
        # Build the filter chain
        # Start: [0:v] -> [tmp0]
        full_filter = f"[0:v]null[tmp0];"
        full_filter += ";".join(overlay_filters)
        # Map the last tmp
        last_tmp = f"[tmp{input_idx-1}]"

        cmd = [
            "ffmpeg", "-y",
            "-i", effects_clip,
            *overlay_inputs,
            "-filter_complex", full_filter,
            "-map", last_tmp,
            "-map", "0:a?",
            "-c:v", "libx264", "-preset", "medium",
            "-b:v", "8M",
            "-c:a", "aac", "-b:a", "192k",
            "-r", "30",
            "-movflags", "+faststart",
            str(output_path),
        ]
    else:
        # No overlays, just copy
        cmd = [
            "ffmpeg", "-y",
            "-i", effects_clip,
            "-c:v", "libx264", "-preset", "medium",
            "-b:v", "8M",
            "-c:a", "aac", "-b:a", "192k",
            "-r", "30",
            "-movflags", "+faststart",
            str(output_path),
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback: simpler approach without overlays
        print(f"[!] Complex filter failed, trying simple edit...")
        cmd_simple = [
            "ffmpeg", "-y",
            "-i", effects_clip,
            "-c:v", "libx264", "-preset", "medium",
            "-b:v", "8M", "-c:a", "aac",
            "-r", "30", "-movflags", "+faststart",
            str(output_path),
        ]
        subprocess.run(cmd_simple, capture_output=True, check=True)

    # Clean temp files
    for tmp in TEMP_DIR.glob("*.mp4"):
        tmp.unlink(missing_ok=True)

    print(f"[+] Clip saved: {output_path}")
    return str(output_path)


def edit_clip_simple(
    video_path: str,
    start: float,
    end: float,
    hook_text: str = "WAIT FOR IT",
    handle: str = "@yourhandle",
    output_name: str = None,
) -> str:
    """
    Simplified single-pass editor using ffmpeg drawtext.
    Faster, no Pillow dependency, works everywhere.
    """
    video_path = Path(video_path)
    if not output_name:
        output_name = f"clip_{start:.0f}_{end:.0f}"
    output_path = OUTPUT_DIR / f"{output_name}.mp4"

    duration = end - start
    cta_start = max(0, duration - 2)

    # Detect input size
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", str(video_path),
    ]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True)
    info = json.loads(probe.stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    iw, ih = int(v["width"]), int(v["height"])

    # Build filter: crop to 9:16, add text overlays
    aspect = iw / ih
    if aspect > 9 / 16:
        crop = f"crop=ih*9/16:ih"
    else:
        crop = f"crop=iw:iw*16/9"

    # Escape text for ffmpeg drawtext (Windows-safe)
    def _esc(t):
        return t.replace("\\", "\\\\").replace("'", "\u2019").replace(":", "\\:").replace("%", "%%")

    hook_esc = _esc(hook_text)
    handle_esc = _esc(handle)

    # Find a usable font (Windows: colon needs single backslash escape in ffmpeg)
    import platform
    if platform.system() == "Windows":
        font_file = "C\\:/Windows/Fonts/impact.ttf"
        if not os.path.exists("C:/Windows/Fonts/impact.ttf"):
            font_file = "C\\:/Windows/Fonts/arial.ttf"
    else:
        font_file = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    vf = (
        f"{crop},scale={WIDTH}:{HEIGHT},"
        f"eq=contrast=1.1:brightness=0.02:saturation=1.2,"
        f"vignette=PI/5,"
        # Hook text (first 1.5s)
        f"drawtext=text='{hook_esc}':"
        f"fontfile='{font_file}':"
        f"fontsize=80:fontcolor=white:borderw=5:bordercolor=black:"
        f"x=(w-tw)/2:y=h/3:"
        f"enable='between(t,0,1.5)',"
        # CTA line 1 (last 2s)
        f"drawtext=text='Follow for more':"
        f"fontfile='{font_file}':"
        f"fontsize=60:fontcolor=white:borderw=4:bordercolor=black:"
        f"x=(w-tw)/2:y=(h/2-50):"
        f"enable='between(t,{cta_start},{duration})',"
        # CTA line 2 - handle
        f"drawtext=text='{handle_esc}':"
        f"fontfile='{font_file}':"
        f"fontsize=55:fontcolor=yellow:borderw=4:bordercolor=black:"
        f"x=(w-tw)/2:y=(h/2+30):"
        f"enable='between(t,{cta_start},{duration})'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-i", str(video_path), "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-b:v", "8M",
        "-c:a", "aac", "-b:a", "192k",
        "-r", "30", "-movflags", "+faststart",
        str(output_path),
    ]

    print(f"[*] Editing clip (simple mode): {start:.1f}s - {end:.1f}s")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] ffmpeg error: {result.stderr[-500:]}")
        raise RuntimeError("ffmpeg failed")

    print(f"[+] Clip saved: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python editor.py <video> <start_sec> <end_sec> [hook_text]")
        sys.exit(1)

    video = sys.argv[1]
    start = float(sys.argv[2])
    end = float(sys.argv[3])
    hook = sys.argv[4] if len(sys.argv) > 4 else "WAIT FOR IT"

    try:
        path = edit_clip(video, start, end, hook_text=hook)
    except Exception as e:
        print(f"[!] Full editor failed ({e}), trying simple mode...")
        path = edit_clip_simple(video, start, end, hook_text=hook)

    print(f"\nDone! Output: {path}")
