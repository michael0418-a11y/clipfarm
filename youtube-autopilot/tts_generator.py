import asyncio
import json
import subprocess
import requests
from pathlib import Path
import edge_tts


class TTSGenerator:
    def __init__(self, voice: str = "en-US-AriaNeural", elevenlabs_key: str = None):
        self.voice = voice
        self.elevenlabs_key = elevenlabs_key
        self._el_voice_id = "nPczCjzI2devNBz1zQrb"  # Brian

    # ── Edge-TTS with word timing ─────────────────────────────────────────────

    async def _generate_edge(self, text: str, audio_path: Path, timing_path: Path):
        communicate = edge_tts.Communicate(text, self.voice)
        audio_chunks = []
        word_timings = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 10_000_000      # 100ns → seconds
                duration = chunk["duration"] / 10_000_000
                word_timings.append({
                    "word": chunk["text"],
                    "start": round(start, 4),
                    "end": round(start + duration, 4),
                })

        audio_path.write_bytes(b"".join(audio_chunks))
        with open(timing_path, "w") as f:
            json.dump(word_timings, f)

    # ── ElevenLabs (no word timing — estimate from duration) ──────────────────

    def _generate_elevenlabs(self, text: str, audio_path: Path) -> bool:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self._el_voice_id}"
            headers = {"xi-api-key": self.elevenlabs_key, "Content-Type": "application/json"}
            payload = {
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                audio_path.write_bytes(resp.content)
                return True
            print(f"  ⚠️  ElevenLabs error {resp.status_code}, falling back to Edge-TTS")
            return False
        except Exception as e:
            print(f"  ⚠️  ElevenLabs failed ({e}), falling back to Edge-TTS")
            return False

    def _estimate_timing(self, text: str, audio_path: Path, timing_path: Path):
        """Estimate word timing proportionally when exact timing isn't available."""
        duration = self.get_duration(audio_path)
        words = text.split()
        if not words:
            with open(timing_path, "w") as f:
                json.dump([], f)
            return
        secs_per_word = duration / len(words)
        timings = [
            {"word": w, "start": round(i * secs_per_word, 4), "end": round((i + 1) * secs_per_word, 4)}
            for i, w in enumerate(words)
        ]
        with open(timing_path, "w") as f:
            json.dump(timings, f)

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_sections(self, script: list, output_dir: Path):
        """Returns (audio_files, timing_files)."""
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_files, timing_files = [], []
        engine = "ElevenLabs" if self.elevenlabs_key else "Edge-TTS"

        for section in script:
            i = section["section"]
            text = section["text"]
            audio_path = output_dir / f"section_{i:02d}.mp3"
            timing_path = output_dir / f"section_{i:02d}_timing.json"

            if self.elevenlabs_key:
                success = self._generate_elevenlabs(text, audio_path)
                if success:
                    self._estimate_timing(text, audio_path, timing_path)
                else:
                    asyncio.run(self._generate_edge(text, audio_path, timing_path))
            else:
                asyncio.run(self._generate_edge(text, audio_path, timing_path))

            audio_files.append(audio_path)
            timing_files.append(timing_path)
            print(f"  ✓ TTS section {i} [{engine}]")

        return audio_files, timing_files

    @staticmethod
    def get_duration(audio_path: Path) -> float:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True,
        )
        return float(result.stdout.strip())
