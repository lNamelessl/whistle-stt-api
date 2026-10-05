"""Environment configuration. Every variable has a default: deploying with no
configuration at all gives a working, open, auto-detecting transcription API."""

import os


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


PORT = int(os.environ.get("PORT", "8000"))
API_KEY = os.environ.get("API_KEY", "").strip()
DEFAULT_LANGUAGE = os.environ.get("WHISTLE_DEFAULT_LANGUAGE", "").strip().lower() or None
CHUNK_LONG_AUDIO = _bool("CHUNK_LONG_AUDIO", False)
MAX_UPLOAD_MB = float(os.environ.get("MAX_UPLOAD_MB", "25"))
MAX_AUDIO_SECONDS = float(os.environ.get("MAX_AUDIO_SECONDS", "900"))

LANGUAGES = ("en", "de", "fr", "es", "it", "nl", "pl")
MAX_SINGLE_PASS_SECONDS = 30.0
MODEL_ID = "whistle"
