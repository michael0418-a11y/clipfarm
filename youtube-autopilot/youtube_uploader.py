import os
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = Path(__file__).parent / "token.pickle"


def _get_credentials(client_secrets_file: str):
    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return creds


class YouTubeUploader:
    def __init__(self, client_secrets_file: str):
        self.client_secrets_file = client_secrets_file
        self._service = None

    def _get_service(self):
        if not self._service:
            creds = _get_credentials(self.client_secrets_file)
            self._service = build("youtube", "v3", credentials=creds)
        return self._service

    def upload(
        self,
        video_path: Path,
        thumbnail_path: Path,
        title: str,
        description: str,
        tags: list[str],
        category_id: str = "27",   # 27 = Education
        privacy: str = "public",
    ) -> str:
        youtube = self._get_service()

        # Ensure #Shorts hashtag is in description for YouTube Shorts classification
        if "#Shorts" not in description and "#shorts" not in description:
            description = "#Shorts\n\n" + description

        body = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags + (["shorts"] if "shorts" not in [t.lower() for t in tags] else []),
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")

        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  Upload {int(status.progress() * 100)}%")

        video_id = response["id"]

        # Set thumbnail (requires verified YouTube account; skip if not permitted)
        if thumbnail_path and thumbnail_path.exists():
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(str(thumbnail_path))
                ).execute()
            except Exception as e:
                print(f"  ⚠️  Thumbnail skipped: {e}")

        return video_id
