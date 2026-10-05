"""Audio plumbing: ffmpeg decoding, duration, and chunk slicing.

Everything that reaches the engine is a 16 kHz mono 16-bit PCM WAV tempfile,
so the engine never needs to resample (that would require the soxr extra)."""

import math
import os
import subprocess
import tempfile
import wave

FFMPEG_TIMEOUT = 120  # seconds of CPU time per conversion


class AudioError(ValueError):
    """Input audio could not be decoded."""


def convert_to_wav(src: str) -> str:
    """Decode any ffmpeg-readable audio (mp3, webm, m4a, wav, ...) to 16 kHz
    mono 16-bit PCM WAV. The input format is probed from content, so the
    uploaded file's name and extension do not matter."""
    fd, dst = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    cmd = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-i", src,
        "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", "-f", "wav", dst,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
    except subprocess.TimeoutExpired:
        unlink(dst)
        raise AudioError("audio decoding timed out") from None
    if proc.returncode != 0 or os.path.getsize(dst) == 0:
        detail = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        unlink(dst)
        raise AudioError(
            f"could not decode audio: {detail[-1] if detail else 'unknown error'}"
        )
    return dst


def duration_seconds(path: str) -> float:
    """Exact duration from the converted WAV itself (frames / rate)."""
    with wave.open(path, "rb") as w:
        return w.getnframes() / float(w.getframerate())


def slice_to_wav(src: str, start_s: float, end_s: float, dst: str) -> float:
    """Copy [start_s, end_s) of src into dst; returns the seconds written."""
    with wave.open(src, "rb") as r:
        rate, width, channels = r.getframerate(), r.getsampwidth(), r.getnchannels()
        start = max(0, int(start_s * rate))
        stop = int(end_s * rate)
        r.setpos(start)
        frames = r.readframes(max(0, stop - start))
    with wave.open(dst, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(frames)
    return len(frames) / float(width * channels * rate)


def chunk_bounds(duration: float, limit: float):
    """Yield (start, end) windows of at most `limit` seconds covering duration."""
    total = int(math.ceil(duration / limit))
    for index in range(total):
        yield (index * limit, min((index + 1) * limit, duration))


def unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass
