"""Whistle engine wrapper: one model per process, guarded by a lock.

The Needle engine is explicitly not thread-safe, and FastAPI runs sync
endpoints in a threadpool, so every transcription passes through this lock.
Requests are serialized by design; scale horizontally with replicas."""

import threading

from needle import Whistle

from . import config

_whistle = None
_load_error = None
_lock = threading.Lock()


def load() -> None:
    """Eagerly load the model at boot so /health reflects real readiness."""
    global _whistle, _load_error
    try:
        _whistle = Whistle()
    except Exception as exc:  # surfaced through /health, never crash the boot
        _load_error = f"{type(exc).__name__}: {exc}"


def is_loaded() -> bool:
    return _whistle is not None


def load_error():
    return _load_error


def transcribe(audio_path: str, language=None, word_timestamps: bool = False) -> dict:
    """Transcribe one 16 kHz mono WAV file. Raises RuntimeError on engine errors."""
    with _lock:
        return _whistle.transcribe(
            audio_path, language=language, word_timestamps=word_timestamps
        )
