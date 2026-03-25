# YouTube Autopilot — Setup Guide

## Step 1: Get Your Free API Keys

### A) Google Gemini API (free — 1,500 requests/day)
1. Go to https://aistudio.google.com/apikey
2. Sign in with your Google account
3. Click **"Create API key"**
4. Copy the key

### B) Pexels API (free — stock footage)
1. Go to https://www.pexels.com/api/
2. Click **"Get Started"** and create a free account
3. Go to your dashboard → copy your API key

### C) YouTube Data API (free — upload quota)
1. Go to https://console.cloud.google.com/
2. Create a new project (e.g. "YouTube Autopilot")
3. Go to **APIs & Services → Library**
4. Search for **"YouTube Data API v3"** → Enable it
5. Go to **APIs & Services → Credentials**
6. Click **"Create Credentials" → "OAuth client ID"**
7. Application type: **Desktop app**
8. Click Create → **Download JSON**
9. Rename the downloaded file to `client_secrets.json`
10. Move it into the `youtube-autopilot/` folder

---

## Step 2: Configure Your Channel

1. Copy `.env.example` to `.env`
2. Fill in your API keys:

```
GEMINI_API_KEY=AIza...
PEXELS_API_KEY=your_pexels_key...
CHANNEL_NICHE=interesting facts about space
TTS_VOICE=en-US-AriaNeural
```

### Available voices (edge-tts):
- `en-US-AriaNeural` — friendly female (default)
- `en-US-GuyNeural` — male voice
- `en-GB-SoniaNeural` — British female
- `en-AU-NatashaNeural` — Australian female

---

## Step 3: Test It (No Upload)

```bash
cd youtube-autopilot
python main.py --dry-run
```

This generates the video WITHOUT uploading. Check the `output/` folder.

---

## Step 4: Run It (With Upload)

First run will open a browser window asking you to sign into YouTube — that's normal.
After that, it's fully automatic.

```bash
python main.py
```

Or with a specific topic:

```bash
python main.py --topic "Why Do We Dream?"
```

---

## Step 5: Set Up n8n for Auto-Scheduling

n8n runs the script every day at 9am automatically.

```bash
# Install n8n globally (one time)
npm install -g n8n

# Start n8n
n8n start
```

1. Open http://localhost:5678
2. Go to **Workflows → Import from File**
3. Import `n8n_workflow.json`
4. Activate the workflow (toggle in top right)

Done! n8n will now run the autopilot every day at 9am.

---

## Folder Structure After First Run

```
youtube-autopilot/
├── output/
│   └── Why_Do_We_Dream/
│       ├── content.json       ← script + metadata
│       ├── audio/             ← TTS mp3 files
│       ├── clips/             ← Pexels stock footage
│       ├── final_video.mp4    ← assembled video
│       └── thumbnail.jpg      ← thumbnail image
├── token.pickle               ← YouTube auth (auto-created)
└── ...
```

---

## Troubleshooting

**"GEMINI_API_KEY is missing"** → Make sure `.env` file exists and has your key.

**"No such file: client_secrets.json"** → Download it from Google Cloud Console (Step 1C).

**Pexels clips not downloading** → Check your Pexels API key in `.env`.

**YouTube upload fails first time** → A browser window will open — just sign in and approve access.

**FFmpeg errors** → Make sure FFmpeg is in your PATH. Run `ffmpeg -version` to check.
