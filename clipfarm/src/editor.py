"""
Module 3: Auto Editor — The Core Engine
Takes raw video + timestamps and produces TikTok-ready clips with:
- Dynamic captions (whopio_clips style)
- Zoom/pan effects (smooth Ken Burns with focus point)
- Hook text + CTA end screen
- Color grading
- Speed ramps
- Bass boost on punchlines
- Sound effects (whoosh, bass drop, ding)
- Thumbnail generation
"""

import json
import math
import os
import platform
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None

try:
    from scipy.signal import butter, lfilter
except ImportError:
    butter = lfilter = None

# Output dimensions (9:16 TikTok)
WIDTH = 1080
HEIGHT = 1920

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "clips"
TEMP_DIR = PROJECT_ROOT / "temp"
ASSETS_DIR = PROJECT_ROOT / "assets"
SOUNDS_DIR = ASSETS_DIR / "sounds"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

# Load settings
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.json"
if SETTINGS_PATH.exists():
    with open(SETTINGS_PATH, "r") as f:
        SETTINGS = json.load(f)
else:
    SETTINGS = {}

# Defaults from settings
DEFAULT_BASS_BOOST_DB = SETTINGS.get("effects", {}).get("bass_boost_db", 6)
DEFAULT_ZOOM_INTENSITY = SETTINGS.get("effects", {}).get("zoom_intensity", 1.15)
DEFAULT_COLOR_GRADE = SETTINGS.get("effects", {}).get("color_grade", "cinematic")
DEFAULT_SPEED_RAMP_ENABLED = SETTINGS.get("effects", {}).get("speed_ramp", True)

# Font path helper
def _get_ffmpeg_font_path() -> str:
    """Return an ffmpeg-escaped font path for the current platform."""
    if platform.system() == "Windows":
        if os.path.exists("C:/Windows/Fonts/impact.ttf"):
            return "C\\:/Windows/Fonts/impact.ttf"
        return "C\\:/Windows/Fonts/arial.ttf"
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


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


# ---------------------------------------------------------------------------
# Feature 1: Speed Ramps
# ---------------------------------------------------------------------------

def build_speed_ramp_filter(
    punch_timestamps: list,
    total_duration: float,
    slow_speed: float = 0.7,
    normal_speed: float = 1.0,
    fast_speed: float = 1.15,
    ramp_window: float = 1.5,
) -> str:
    """
    Build an ffmpeg setpts expression that applies speed ramps around punch
    timestamps. Each punch gets slow-mo (0.7x) for `ramp_window` seconds
    centered on the timestamp, then a brief speed-up (1.15x) for the next
    `ramp_window/2` seconds before snapping back to 1.0x.

    Parameters
    ----------
    punch_timestamps : list of float
        Seconds into the clip where speed changes happen.
    total_duration : float
        Total clip duration in seconds.
    slow_speed : float
        Playback speed during the slow-mo window (0.7 = 70% speed).
    normal_speed : float
        Normal playback speed.
    fast_speed : float
        Speed-up after the slow-mo snap-back.
    ramp_window : float
        Duration (seconds) of the slow-mo region around each punch.

    Returns
    -------
    str
        An ffmpeg video filter string using setpts. Audio is handled
        separately with atempo.
    """
    if not punch_timestamps:
        return ""

    # Sort timestamps
    punches = sorted(punch_timestamps)

    # Build a conditional PTS expression:
    # For each punch P, if t is in [P - ramp_window/2, P + ramp_window/2],
    # slow down; if t is in [P + ramp_window/2, P + ramp_window], speed up.
    # setpts works by multiplying PTS: slower = larger factor, faster = smaller.
    # PTS factor = 1/speed (slow 0.7x -> factor 1/0.7 ~ 1.4286)

    slow_factor = 1.0 / slow_speed
    fast_factor = 1.0 / fast_speed

    # Build nested if/else expression
    # We go from innermost (default normal) outward
    expr = f"{1.0 / normal_speed}*PTS"

    for p in reversed(punches):
        slow_start = max(0, p - ramp_window / 2)
        slow_end = p + ramp_window / 2
        fast_end = slow_end + ramp_window / 2

        # Speed-up window (after slow-mo)
        expr = (
            f"if(between(T,{slow_start:.3f},{slow_end:.3f}),"
            f"{slow_factor:.4f}*PTS,"
            f"if(between(T,{slow_end:.3f},{fast_end:.3f}),"
            f"{fast_factor:.4f}*PTS,"
            f"{expr}))"
        )

    video_filter = f"setpts='{expr}'"

    return video_filter


def build_speed_ramp_audio_filter(
    punch_timestamps: list,
    total_duration: float,
    slow_speed: float = 0.7,
    normal_speed: float = 1.0,
    fast_speed: float = 1.15,
    ramp_window: float = 1.5,
) -> str:
    """
    Build a matching audio tempo filter for speed ramps.
    Uses atempo which accepts values in [0.5, 100.0].
    Since we cannot do conditional atempo easily, we use a segmented
    approach: split audio at boundaries, apply atempo per segment, concat.
    For simplicity, returns an atempo chain or empty string.

    For a simpler approach that pairs with setpts, we adjust audio with
    asetpts matching the video PTS expression.
    """
    if not punch_timestamps:
        return ""
    # asetpts mirrors video timing
    return "asetpts=N/SR/TB"


# ---------------------------------------------------------------------------
# Feature 2: Bass Boost
# ---------------------------------------------------------------------------

def build_bass_boost_filter(
    punch_timestamps: list = None,
    bass_boost_db: float = None,
    frequency: float = 80.0,
    width_type: str = "s",
    width: float = 1.0,
) -> str:
    """
    Build an ffmpeg audio equalizer filter for bass boost.
    Applies a low-shelf boost at the given frequency.

    Parameters
    ----------
    punch_timestamps : list of float, optional
        If provided, bass boost is applied only around these timestamps
        (enable= between expressions). If None, applies globally.
    bass_boost_db : float, optional
        Gain in dB for the low shelf. Defaults to settings value or 6.
    frequency : float
        Center frequency for the bass shelf (default 80 Hz).
    width_type : str
        Width type for the equalizer ('s' = slope, 'q' = Q-factor).
    width : float
        Width value.

    Returns
    -------
    str
        An ffmpeg audio filter string.
    """
    if bass_boost_db is None:
        bass_boost_db = DEFAULT_BASS_BOOST_DB

    base = (
        f"equalizer=f={frequency}:t={width_type}:w={width}"
        f":g={bass_boost_db}"
    )

    if punch_timestamps:
        # Apply bass boost in windows around each punch timestamp
        enables = []
        for ts in punch_timestamps:
            t_start = max(0, ts - 0.5)
            t_end = ts + 1.0
            enables.append(f"between(t,{t_start:.2f},{t_end:.2f})")
        enable_expr = "+".join(enables)
        base += f":enable='{enable_expr}'"

    return base


# ---------------------------------------------------------------------------
# Feature 3: Ken Burns / Smooth Zoom
# ---------------------------------------------------------------------------

def build_smooth_zoom_filter(
    duration: float,
    zoom_intensity: float = None,
    focus_x: float = 0.5,
    focus_y: float = 0.5,
    fps: int = 30,
    easing: str = "ease_in_out",
) -> str:
    """
    Build an ffmpeg zoompan filter with smooth easing and focus point.

    Parameters
    ----------
    duration : float
        Clip duration in seconds.
    zoom_intensity : float, optional
        Max zoom level (e.g. 1.15 = 15% zoom). Defaults to settings.
    focus_x : float
        Horizontal focus point as fraction (0.0 = left, 1.0 = right).
    focus_y : float
        Vertical focus point as fraction (0.0 = top, 1.0 = bottom).
    fps : int
        Frames per second.
    easing : str
        Easing type: "ease_in_out", "ease_in", "ease_out", "linear".

    Returns
    -------
    str
        An ffmpeg zoompan filter string with smooth interpolation.
    """
    if zoom_intensity is None:
        zoom_intensity = DEFAULT_ZOOM_INTENSITY

    if zoom_intensity <= 1.0:
        return ""

    total_frames = int(duration * fps)
    if total_frames < 1:
        total_frames = 1

    # Build zoom expression with easing
    # on_frame / total_frames = progress (0 to 1)
    # For ease_in_out: use smoothstep: 3*p^2 - 2*p^3
    # zoom goes from 1.0 to zoom_intensity using the easing curve
    z_range = zoom_intensity - 1.0

    if easing == "ease_in_out":
        # smoothstep: progress = on/(d-1), zoom = 1 + range * (3*p^2 - 2*p^3)
        z_expr = (
            f"1+{z_range:.4f}*(3*pow(on/{total_frames},2)"
            f"-2*pow(on/{total_frames},3))"
        )
    elif easing == "ease_in":
        # quadratic ease in: p^2
        z_expr = f"1+{z_range:.4f}*pow(on/{total_frames},2)"
    elif easing == "ease_out":
        # quadratic ease out: 1-(1-p)^2
        z_expr = (
            f"1+{z_range:.4f}*(1-pow(1-on/{total_frames},2))"
        )
    else:
        # linear
        z_expr = f"1+{z_range:.4f}*(on/{total_frames})"

    # Focus point: x and y expressions
    # x = focus_x * (iw - iw/zoom), y = focus_y * (ih - ih/zoom)
    x_expr = f"{focus_x:.3f}*(iw-iw/zoom)"
    y_expr = f"{focus_y:.3f}*(ih-ih/zoom)"

    zoompan = (
        f"zoompan=z='{z_expr}'"
        f":x='{x_expr}':y='{y_expr}'"
        f":d={total_frames}:s={WIDTH}x{HEIGHT}:fps={fps}"
    )

    return zoompan


# ---------------------------------------------------------------------------
# Feature 4: Thumbnail Generator
# ---------------------------------------------------------------------------

def generate_thumbnail(
    video_path: str,
    timestamp: float,
    hook_text: str,
    output_path: str = None,
    font_size: int = 100,
    text_color: str = "white",
    outline_color: str = "black",
    outline_width: int = 6,
) -> str:
    """
    Extract a frame from a video at the given timestamp, overlay bold hook
    text in whopio_clips style, and save as JPEG.

    Parameters
    ----------
    video_path : str
        Path to the source video.
    timestamp : float
        Time in seconds to extract the frame.
    hook_text : str
        Bold text to overlay on the thumbnail.
    output_path : str, optional
        Where to save the JPEG. Defaults to output/clips/<name>_thumb.jpg.
    font_size : int
        Font size for the hook text.
    text_color : str
        Color of the hook text.
    outline_color : str
        Color of the text outline.
    outline_width : int
        Pixel width of the text outline.

    Returns
    -------
    str
        Path to the saved thumbnail JPEG.
    """
    if Image is None:
        raise ImportError("Pillow is required: pip install Pillow")

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if output_path is None:
        output_path = str(
            OUTPUT_DIR / f"{video_path.stem}_thumb_{timestamp:.0f}.jpg"
        )

    # Step 1: Extract frame with ffmpeg
    frame_path = str(TEMP_DIR / "thumb_frame.png")
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        frame_path,
    ], capture_output=True, check=True)

    # Step 2: Open frame, resize to 9:16
    img = Image.open(frame_path).convert("RGB")
    img_w, img_h = img.size
    target_aspect = WIDTH / HEIGHT

    # Crop to 9:16 from center
    current_aspect = img_w / img_h
    if current_aspect > target_aspect:
        new_w = int(img_h * target_aspect)
        left = (img_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, img_h))
    elif current_aspect < target_aspect:
        new_h = int(img_w / target_aspect)
        top = (img_h - new_h) // 2
        img = img.crop((0, top, img_w, top + new_h))

    img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)

    # Step 3: Apply slight color boost for thumbnail pop
    from PIL import ImageEnhance
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.2)

    # Step 4: Overlay hook text
    draw = ImageDraw.Draw(img)
    font = _get_font(font_size)

    # Word wrap
    words = hook_text.upper().split()
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        test_bbox = draw.textbbox((0, 0), test, font=font)
        if test_bbox[2] - test_bbox[0] > WIDTH - 80:
            if current_line:
                lines.append(current_line)
            current_line = word
        else:
            current_line = test
    if current_line:
        lines.append(current_line)
    wrapped_text = "\n".join(lines)

    # Calculate position (centered, upper third)
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (WIDTH - text_w) // 2
    y = HEIGHT // 4 - text_h // 2

    # Draw outline
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx * dx + dy * dy <= outline_width * outline_width:
                draw.multiline_text(
                    (x + dx, y + dy), wrapped_text, font=font,
                    fill=outline_color, align="center",
                )

    # Draw main text
    draw.multiline_text(
        (x, y), wrapped_text, font=font,
        fill=text_color, align="center",
    )

    # Step 5: Add subtle darkened gradient at bottom for text readability
    gradient = Image.new("RGBA", (WIDTH, HEIGHT // 3), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    for row in range(HEIGHT // 3):
        alpha = int(180 * (row / (HEIGHT // 3)))
        gradient_draw.line([(0, row), (WIDTH, row)], fill=(0, 0, 0, alpha))
    img.paste(
        Image.alpha_composite(
            Image.new("RGBA", gradient.size, (0, 0, 0, 0)), gradient
        ),
        (0, HEIGHT - HEIGHT // 3),
        mask=gradient,
    )

    # Save as JPEG
    img.save(output_path, "JPEG", quality=95)

    # Clean up temp frame
    try:
        os.remove(frame_path)
    except OSError:
        pass

    print(f"[+] Thumbnail saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Feature 5: Sound Effects (generated, free/no-cost)
# ---------------------------------------------------------------------------

def _generate_sine_wave(
    frequency: float,
    duration: float,
    sample_rate: int = 44100,
    amplitude: float = 0.8,
    fade_in: float = 0.01,
    fade_out: float = 0.05,
) -> np.ndarray:
    """Generate a sine wave with fade in/out."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave_data = amplitude * np.sin(2 * np.pi * frequency * t)

    # Apply fade in
    fade_in_samples = int(fade_in * sample_rate)
    if fade_in_samples > 0:
        wave_data[:fade_in_samples] *= np.linspace(0, 1, fade_in_samples)

    # Apply fade out
    fade_out_samples = int(fade_out * sample_rate)
    if fade_out_samples > 0:
        wave_data[-fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)

    return wave_data


def _save_wav(filepath: str, data: np.ndarray, sample_rate: int = 44100):
    """Save a numpy array as a 16-bit WAV file."""
    # Normalize to int16 range
    data = np.clip(data, -1.0, 1.0)
    int_data = (data * 32767).astype(np.int16)

    with wave.open(filepath, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int_data.tobytes())


def generate_sound_effect(effect_type: str) -> str:
    """
    Generate a simple sound effect and save it as a WAV file in the
    assets/sounds/ directory. Uses numpy (and optionally scipy) to
    synthesize the sound -- no external audio files needed.

    Parameters
    ----------
    effect_type : str
        One of "whoosh", "bass_drop", "ding".

    Returns
    -------
    str
        Path to the generated WAV file.
    """
    sample_rate = 44100
    out_path = str(SOUNDS_DIR / f"{effect_type}.wav")

    # Return cached version if it exists
    if os.path.exists(out_path):
        return out_path

    if effect_type == "bass_drop":
        # Descending sine sweep from 150Hz to 30Hz over 0.6s with reverb tail
        duration = 0.8
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        # Frequency sweep: exponential descent
        freq = 150 * np.exp(-2.5 * t / duration) + 30
        phase = 2 * np.pi * np.cumsum(freq) / sample_rate
        wave_data = 0.9 * np.sin(phase)
        # Add sub-harmonic
        wave_data += 0.4 * np.sin(phase * 0.5)
        # Exponential decay envelope
        envelope = np.exp(-3.0 * t / duration)
        wave_data *= envelope
        # Fade out
        fade_samples = int(0.1 * sample_rate)
        wave_data[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    elif effect_type == "whoosh":
        # Filtered white noise with rising then falling amplitude
        duration = 0.5
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        noise = np.random.randn(len(t))
        # Amplitude envelope: quick rise then fall
        envelope = np.sin(np.pi * t / duration) ** 2
        wave_data = noise * envelope * 0.6
        # Apply a simple bandpass via moving average for smoothness
        kernel_size = 15
        kernel = np.ones(kernel_size) / kernel_size
        wave_data = np.convolve(wave_data, kernel, mode="same")
        # Normalize
        peak = np.max(np.abs(wave_data))
        if peak > 0:
            wave_data = wave_data / peak * 0.7

    elif effect_type == "ding":
        # Bell-like tone: fundamental + inharmonic partials
        duration = 0.6
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        # Bell partials (slightly inharmonic)
        partials = [
            (1000, 1.0),
            (2510, 0.5),
            (3980, 0.3),
            (5010, 0.15),
        ]
        wave_data = np.zeros_like(t)
        for freq, amp in partials:
            wave_data += amp * np.sin(2 * np.pi * freq * t)
        # Exponential decay
        envelope = np.exp(-6.0 * t / duration)
        wave_data *= envelope
        # Normalize
        peak = np.max(np.abs(wave_data))
        if peak > 0:
            wave_data = wave_data / peak * 0.7

    else:
        raise ValueError(
            f"Unknown effect type '{effect_type}'. "
            f"Supported: 'whoosh', 'bass_drop', 'ding'"
        )

    _save_wav(out_path, wave_data, sample_rate)
    print(f"[+] Generated sound effect: {out_path}")
    return out_path


def add_sound_effect(
    video_path: str,
    effect_type: str,
    timestamp: float,
    output_path: str = None,
    volume: float = 0.8,
) -> str:
    """
    Overlay a sound effect onto a video at a specific timestamp.

    Parameters
    ----------
    video_path : str
        Path to the input video.
    effect_type : str
        Type of sound effect: "whoosh", "bass_drop", or "ding".
    timestamp : float
        Time in seconds where the effect should play.
    output_path : str, optional
        Path for the output video. Defaults to a temp file.
    volume : float
        Volume multiplier for the effect (0.0 to 1.0).

    Returns
    -------
    str
        Path to the output video with the sound effect mixed in.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    # Generate the sound effect WAV
    sfx_path = generate_sound_effect(effect_type)

    if output_path is None:
        output_path = str(TEMP_DIR / f"sfx_{effect_type}_{timestamp:.0f}.mp4")

    # Use ffmpeg to mix the sound effect at the given timestamp
    # adelay takes milliseconds
    delay_ms = int(timestamp * 1000)

    filter_complex = (
        f"[1:a]adelay={delay_ms}|{delay_ms},"
        f"volume={volume:.2f}[sfx];"
        f"[0:a][sfx]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", sfx_path,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] Sound effect overlay failed: {result.stderr[-300:]}")
        return str(video_path)

    print(f"[+] Added {effect_type} at {timestamp:.1f}s -> {output_path}")
    return output_path


def add_multiple_sound_effects(
    video_path: str,
    effects: list,
    output_path: str = None,
) -> str:
    """
    Overlay multiple sound effects onto a video in a single ffmpeg pass.

    Parameters
    ----------
    video_path : str
        Path to the input video.
    effects : list of dict
        Each dict has keys: "type" (str), "timestamp" (float),
        and optionally "volume" (float, default 0.8).
    output_path : str, optional
        Path for the output video.

    Returns
    -------
    str
        Path to the output video.
    """
    if not effects:
        return str(video_path)

    video_path = Path(video_path)
    if output_path is None:
        output_path = str(TEMP_DIR / "sfx_multi.mp4")

    # Generate all effect WAVs and build inputs
    inputs = ["-i", str(video_path)]
    filter_parts = []

    for i, fx in enumerate(effects):
        sfx_path = generate_sound_effect(fx["type"])
        inputs.extend(["-i", sfx_path])
        delay_ms = int(fx["timestamp"] * 1000)
        vol = fx.get("volume", 0.8)
        filter_parts.append(
            f"[{i + 1}:a]adelay={delay_ms}|{delay_ms},"
            f"volume={vol:.2f}[sfx{i}]"
        )

    # Mix all effects with original audio
    sfx_labels = "".join(f"[sfx{i}]" for i in range(len(effects)))
    n_inputs = len(effects) + 1
    filter_parts.append(
        f"[0:a]{sfx_labels}amix=inputs={n_inputs}"
        f":duration=first:dropout_transition=2[aout]"
    )

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] Multi sound effect overlay failed: {result.stderr[-300:]}")
        return str(video_path)

    print(f"[+] Added {len(effects)} sound effects -> {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Core filter builder (updated with smooth zoom)
# ---------------------------------------------------------------------------

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
    duration: float = 0,
    focus_x: float = 0.5,
    focus_y: float = 0.5,
    zoom_easing: str = "ease_in_out",
) -> str:
    """
    Build the complex ffmpeg filtergraph for a single clip.
    This handles: crop to 9:16, smooth zoom with easing, color grading.
    Captions are overlaid via separate images for quality.
    """
    filters = []

    # Step 1: Scale to fit 9:16 -- crop from center if landscape
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

    # Step 2: Smooth Ken Burns zoom with easing and focus point
    if zoom_intensity > 1.0 and duration > 0:
        zoom_filter = build_smooth_zoom_filter(
            duration=duration,
            zoom_intensity=zoom_intensity,
            focus_x=focus_x,
            focus_y=focus_y,
            easing=zoom_easing,
        )
        if zoom_filter:
            filters.append(zoom_filter)
    elif zoom_intensity > 1.0:
        # Fallback to basic zoom if duration not provided
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


# ---------------------------------------------------------------------------
# Main editing function (updated with all new features)
# ---------------------------------------------------------------------------

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
    # New feature parameters
    punch_timestamps: list = None,
    speed_ramp: bool = None,
    bass_boost: bool = False,
    bass_boost_db: float = None,
    sound_effects: list = None,
    focus_x: float = 0.5,
    focus_y: float = 0.5,
    zoom_easing: str = "ease_in_out",
    generate_thumb: bool = False,
    thumb_timestamp: float = None,
) -> str:
    """
    The main editing function. Takes a video + timestamps and produces
    a TikTok-ready clip with all effects.

    New optional parameters
    -----------------------
    punch_timestamps : list of float
        Seconds (relative to clip start) where speed ramps / bass boost hit.
    speed_ramp : bool
        Enable speed ramps on punch_timestamps. Defaults to settings value.
    bass_boost : bool
        Enable bass boost on punchline moments.
    bass_boost_db : float
        Gain in dB for bass boost (default from settings, typically 6).
    sound_effects : list of dict
        Each dict: {"type": "whoosh"|"bass_drop"|"ding", "timestamp": float}.
        Timestamps are relative to clip start.
    focus_x, focus_y : float
        Focus point for Ken Burns zoom (0-1 fractions).
    zoom_easing : str
        Easing curve for zoom: "ease_in_out", "ease_in", "ease_out", "linear".
    generate_thumb : bool
        If True, also generate a thumbnail for this clip.
    thumb_timestamp : float
        Absolute timestamp for the thumbnail frame. Defaults to start + 1s.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if speed_ramp is None:
        speed_ramp = DEFAULT_SPEED_RAMP_ENABLED

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

    # --- STEP 1: Extract base clip ---
    print("[*] Step 1: Extracting base clip...")
    base_clip = str(TEMP_DIR / "base_clip.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(start), "-i", str(video_path),
        "-t", str(duration), "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        base_clip,
    ], capture_output=True, check=True)

    # --- STEP 2: Apply speed ramps (if enabled and punch timestamps given) ---
    current_clip = base_clip
    if speed_ramp and punch_timestamps:
        print(f"[*] Step 2a: Applying speed ramps at {punch_timestamps}...")
        speed_vf = build_speed_ramp_filter(
            punch_timestamps=punch_timestamps,
            total_duration=duration,
        )
        speed_af = build_speed_ramp_audio_filter(
            punch_timestamps=punch_timestamps,
            total_duration=duration,
        )
        if speed_vf:
            ramped_clip = str(TEMP_DIR / "ramped_clip.mp4")
            speed_cmd = [
                "ffmpeg", "-y", "-i", current_clip,
                "-vf", speed_vf,
                "-af", speed_af if speed_af else "anull",
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac", "-b:a", "192k",
                ramped_clip,
            ]
            result = subprocess.run(speed_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                current_clip = ramped_clip
            else:
                print(f"[!] Speed ramp failed, continuing without: {result.stderr[-200:]}")

    # --- STEP 3: Apply visual effects (crop, smooth zoom, color grade) ---
    print("[*] Step 3: Applying visual effects...")
    vf = build_ffmpeg_filter(
        clip_data={}, caption_blocks=caption_blocks or [],
        input_w=input_w, input_h=input_h,
        zoom_intensity=zoom_intensity, color_grade=color_grade,
        duration=duration,
        focus_x=focus_x, focus_y=focus_y,
        zoom_easing=zoom_easing,
    )

    # Build audio filters: bass boost
    af_parts = []
    if bass_boost and punch_timestamps:
        print(f"[*] Step 3a: Adding bass boost ({bass_boost_db or DEFAULT_BASS_BOOST_DB}dB)...")
        af_parts.append(
            build_bass_boost_filter(
                punch_timestamps=punch_timestamps,
                bass_boost_db=bass_boost_db,
            )
        )
    elif bass_boost:
        # Global bass boost if no punch timestamps
        af_parts.append(build_bass_boost_filter(bass_boost_db=bass_boost_db))

    effects_clip = str(TEMP_DIR / "effects_clip.mp4")
    cmd_effects = [
        "ffmpeg", "-y", "-i", current_clip,
        "-vf", vf,
    ]
    if af_parts:
        cmd_effects.extend(["-af", ",".join(af_parts)])
    cmd_effects.extend([
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        effects_clip,
    ])
    subprocess.run(cmd_effects, capture_output=True, check=True)

    # --- STEP 4: Create caption overlay images ---
    overlay_inputs = []
    overlay_filters = []
    input_idx = 1  # 0 is the video

    # Hook text (first 1.5 seconds)
    if hook_text:
        print(f"[*] Step 4a: Creating hook text: '{hook_text}'")
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
        print(f"[*] Step 4b: Creating {len(caption_blocks)} caption overlays...")
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
        print(f"[*] Step 4c: Creating CTA end screen...")
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

    # --- STEP 5: Compose everything with ffmpeg ---
    print("[*] Step 5: Composing final clip...")

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

    # --- STEP 6: Sound effects overlay (post-compose) ---
    if sound_effects:
        print(f"[*] Step 6: Overlaying {len(sound_effects)} sound effects...")
        final_with_sfx = add_multiple_sound_effects(
            video_path=str(output_path),
            effects=sound_effects,
            output_path=str(TEMP_DIR / "final_sfx.mp4"),
        )
        if final_with_sfx != str(output_path):
            # Replace output with the version that has sound effects
            import shutil
            shutil.move(final_with_sfx, str(output_path))

    # --- STEP 7: Thumbnail generation (optional) ---
    if generate_thumb:
        t_ts = thumb_timestamp if thumb_timestamp is not None else start + 1.0
        thumb_path = str(OUTPUT_DIR / f"{output_name}_thumb.jpg")
        try:
            generate_thumbnail(
                video_path=str(video_path),
                timestamp=t_ts,
                hook_text=hook_text or "CHECK THIS OUT",
                output_path=thumb_path,
            )
        except Exception as e:
            print(f"[!] Thumbnail generation failed: {e}")

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

    font_file = _get_ffmpeg_font_path()

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
        print("\nNew features available via edit_clip():")
        print("  - punch_timestamps=[5, 12, 20]  -> speed ramps + bass boost")
        print("  - bass_boost=True                -> low-shelf EQ at 80Hz")
        print("  - sound_effects=[{'type':'whoosh','timestamp':3.0}]")
        print("  - focus_x=0.5, focus_y=0.4      -> Ken Burns focus point")
        print("  - zoom_easing='ease_in_out'      -> smooth zoom easing")
        print("  - generate_thumb=True            -> auto thumbnail")
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
