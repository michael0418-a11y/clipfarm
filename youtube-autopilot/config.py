import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

class Config:
    # Required
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

    # Optional upgrades (leave blank to use free fallback)
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
    STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")

    # Channel settings
    CHANNEL_NICHE = os.getenv("CHANNEL_NICHE", "interesting facts")
    TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")

    # BGM: path to a local .mp3/.wav file (royalty-free). Leave blank to skip.
    BGM_PATH = os.getenv("BGM_PATH", "")

    # YouTube
    YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", str(BASE_DIR / "client_secrets.json"))

    OUTPUT_DIR = BASE_DIR / "output"
    TEMP_DIR = BASE_DIR / "temp"
    VIDEO_WIDTH = 1080
    VIDEO_HEIGHT = 1920
    VIDEO_FPS = 30

    def validate(self, need_youtube=True):
        errors = []
        if not self.GROQ_API_KEY:
            errors.append("GROQ_API_KEY is missing — get it free at https://console.groq.com/keys")
        if not self.PEXELS_API_KEY:
            errors.append("PEXELS_API_KEY is missing — get it free at https://www.pexels.com/api/")
        if need_youtube and not Path(self.YOUTUBE_CLIENT_SECRETS).exists():
            errors.append(f"YouTube client_secrets.json not found at {self.YOUTUBE_CLIENT_SECRETS}")
        if errors:
            print("\n❌ Missing configuration:")
            for e in errors:
                print(f"  • {e}")
            print("\nSee SETUP_GUIDE.md for instructions.\n")
            return False
        return True
