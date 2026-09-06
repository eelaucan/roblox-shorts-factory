"""Upload the finished MP4 to YouTube as PRIVATE, optionally with a publishAt time.

Never sets privacy to 'public' directly. A scheduled video stays private until
`publishAt`, and you can always cancel by leaving it private in YouTube Studio.

First run opens a browser for OAuth consent and writes token.json (gitignored).
"""
from __future__ import annotations

import os
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = Path("token.json")


def _service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "client_secret.json")
            if not Path(secret).exists():
                raise FileNotFoundError(
                    f"OAuth client secret not found at {secret!r}. Create a Desktop-app "
                    "OAuth client in Google Cloud Console and point YOUTUBE_CLIENT_SECRET at it."
                )
            flow = InstalledAppFlow.from_client_secrets_file(secret, SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload(mp4: Path, *, title: str, description: str, config: dict,
           publish_at: str | None = None) -> str:
    """Returns the new video id. `publish_at` is RFC3339 UTC, e.g. 2026-09-10T17:00:00Z."""
    from googleapiclient.http import MediaFileUpload

    pcfg = config["publish"]
    status: dict = {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": bool(pcfg.get("made_for_kids", False)),
    }
    if publish_at:
        status["publishAt"] = publish_at

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": pcfg.get("tags", []),
            "categoryId": str(pcfg.get("category_id", "24")),
        },
        "status": status,
    }

    media = MediaFileUpload(str(mp4), mimetype="video/mp4", resumable=True)
    request = _service().videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    while response is None:
        progress, response = request.next_chunk()
        if progress:
            print(f"  [youtube] {int(progress.progress() * 100)}%")
    vid = response["id"]
    when = f"scheduled for {publish_at}" if publish_at else "private (unlisted publish)"
    print(f"  [youtube] uploaded https://youtu.be/{vid} — {when}")
    return vid
