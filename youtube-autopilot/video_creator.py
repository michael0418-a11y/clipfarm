import subprocess
import shutil
import json
from pathlib import Path

from tts_generator import TTSGenerator

W, H = 1080, 1920
FPS = 30
FONT_PATH = "C\\:/Windows/Fonts/impact.ttf"   # Impact — classic Shorts font


def ffmpeg_escape(text: str) -> str:
    text = text.replace("\\", "\\\\")
    for ch in ("'", "\u2018", "\u2019", "\u201b", "\u02bc", "\u0060"):
        text = text.replace(ch, "")
    text = text.replace(":", r"\:")
    text = text.replace("%", r"\%")
    text = text.replace("[", r"\[")
    text = text.replace("]", r"\]")
    return text


class VideoCreator:
    def create(
        self,
        sections: list,
        audio_files: list[Path],
        image_files: list[Path],
        timing_files: list[Path],
        output_path: Path,
        bgm_path: Path = None,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_dir = output_path.parent / "_tmp_clips"
        tmp_dir.mkdir(exist_ok=True)

        clip_paths = []
        for i, (section, audio_f, image_f, timing_f) in enumerate(
            zip(sections, audio_files, image_files, timing_files)
        ):
            duration = TTSGenerator.get_duration(audio_f) + 0.3
            word_timings = []
            if timing_f and timing_f.exists():
                with open(timing_f) as f:
                    word_timings = json.load(f)

            clip_out = tmp_dir / f"clip_{i:02d}.mp4"
            self._build_clip(audio_f, image_f, duration, word_timings, clip_out)
            clip_paths.append(clip_out)

        list_file = tmp_dir / "filelist.txt"
        with open(list_file, "w") as f:
            for cp in clip_paths:
                f.write(f"file '{cp.resolve()}'\n")

        concat_out = tmp_dir / "concat.mp4" if bgm_path and bgm_path.exists() else output_path
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
             "-c:v", "libx264", "-preset", "fast", "-crf", "23",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(concat_out)],
            check=True, capture_output=True,
        )

        if bgm_path and bgm_path.exists():
            self._mix_bgm(concat_out, bgm_path, output_path)

        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass
        return output_path

    def _build_clip(
        self,
        audio_path: Path,
        image_path: Path,
        duration: float,
        word_timings: list,
        output_path: Path,
    ):
        frames = max(1, int(duration * FPS))

        if image_path and image_path.exists():
            video_input = ["-loop", "1", "-i", str(image_path)]
        else:
            video_input = ["-f", "lavfi", "-i", f"color=c=0x0f0f1e:size={W}x{H}:rate={FPS}"]

        # Scale up 20% to give zoompan room, then Ken Burns slow zoom-in
        zoom_w = int(W * 1.2)
        zoom_h = int(H * 1.2)

        vf = (
            f"scale={zoom_w}:{zoom_h}:force_original_aspect_ratio=increase,"
            f"crop={zoom_w}:{zoom_h}:(iw-{zoom_w})/2:(ih-{zoom_h})/2,"
            f"zoompan=z='min(zoom+0.0005,1.1)':d={frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
            f"setsar=1,"
            f"eq=brightness=-0.05:contrast=1.1:saturation=0.85"
        )

        caption_filter = self._build_caption_filter(word_timings)
        if caption_filter:
            vf += "," + caption_filter

        cmd = [
            "ffmpeg", "-y",
            *video_input,
            "-i", str(audio_path),
            "-t", str(duration),
            "-vf", vf,
            "-r", str(FPS),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def _build_caption_filter(self, word_timings: list) -> str:
        """Word-by-word captions: Impact font, white text, thick black outline — no box."""
        if not word_timings:
            return ""
        filters = []
        for wt in word_timings:
            word = ffmpeg_escape(wt["word"].upper())
            start = wt["start"]
            end = wt["end"] + 0.05
            filters.append(
                f"drawtext=text='{word}'"
                f":fontfile='{FONT_PATH}'"
                f":fontsize=95:fontcolor=white"
                f":bordercolor=black:borderw=6"
                f":x=(w-text_w)/2:y=h*0.63"
                f":enable='between(t\\,{start:.4f}\\,{end:.4f})'"
            )
        return ",".join(filters)

    def _mix_bgm(self, video_path: Path, bgm_path: Path, output_path: Path):
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path),
             "-stream_loop", "-1", "-i", str(bgm_path),
             "-filter_complex",
             "[1:a]volume=0.15[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
             "-map", "0:v", "-map", "[aout]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart", str(output_path)],
            check=True, capture_output=True,
        )
