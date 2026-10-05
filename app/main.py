"""Whistle STT API: an OpenAI-compatible transcription endpoint on the
Cactus Compute Whistle on-device model (16.9 MB, CPU-only, 7 languages)."""

import os
import secrets
import tempfile
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import audio, config, engine

STARTED_AT = time.time()


@asynccontextmanager
async def lifespan(_: FastAPI):
    engine.load()
    yield


app = FastAPI(title="Whistle STT API", version="1.0.0", lifespan=lifespan)


class OpenAIError(Exception):
    """An error rendered in OpenAI's error envelope."""

    def __init__(self, status: int, message: str, err_type: str, code: str = None):
        self.status = status
        self.message = message
        self.err_type = err_type
        self.code = code


def _envelope(status: int, message: str, err_type: str, code: str = None):
    return JSONResponse(
        {"error": {"message": message, "type": err_type, "param": None, "code": code}},
        status_code=status,
    )


@app.exception_handler(OpenAIError)
async def _openai_error_handler(_, exc: OpenAIError):
    return _envelope(exc.status, exc.message, exc.err_type, exc.code)


@app.exception_handler(RequestValidationError)
async def _validation_handler(_, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    return _envelope(
        400, f"invalid request: {first.get('msg', 'validation failed')}",
        "invalid_request_error", "invalid_form",
    )


@app.exception_handler(StarletteHTTPException)
async def _http_handler(_, exc: StarletteHTTPException):
    return _envelope(exc.status_code, str(exc.detail), "invalid_request_error")


@app.exception_handler(audio.AudioError)
async def _audio_error_handler(_, exc: audio.AudioError):
    return _envelope(400, str(exc), "invalid_request_error", "undecodable_audio")


def _require_auth(request: Request) -> None:
    if not config.API_KEY:
        return
    header = request.headers.get("authorization", "")
    token = header[7:] if header.startswith("Bearer ") else ""
    if not token or not secrets.compare_digest(token, config.API_KEY):
        raise OpenAIError(
            401, "Invalid API key. Pass it as 'Authorization: Bearer <key>'.",
            "authentication_error", "invalid_api_key",
        )


def _rss_mb():
    try:
        with open("/proc/self/status", "r", encoding="ascii") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024, 1)
    except OSError:
        pass
    return None


@app.get("/health")
def health():
    loaded = engine.is_loaded()
    body = {
        "status": "ok" if loaded else "unavailable",
        "model_loaded": loaded,
        "memory_mb": _rss_mb(),
        "uptime_s": round(time.time() - STARTED_AT, 1),
    }
    if engine.load_error():
        body["error"] = engine.load_error()
    return JSONResponse(body, status_code=200 if loaded else 503)


@app.get("/")
def root():
    return {
        "service": "whistle-stt-api",
        "model": config.MODEL_ID,
        "languages": list(config.LANGUAGES),
        "endpoints": ["/v1/audio/transcriptions", "/v1/models", "/health"],
    }


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [{
            "id": config.MODEL_ID,
            "object": "model",
            "created": 1759708800,
            "owned_by": "cactus-compute",
        }],
    }


@app.post("/v1/audio/transcriptions")
async def transcriptions(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form("whistle"),
    language: str = Form(""),
    response_format: str = Form("json"),
):
    _require_auth(request)
    if response_format not in ("json", "text", "verbose_json"):
        raise OpenAIError(
            400, f"response_format must be one of json, text, verbose_json (got {response_format!r})",
            "invalid_request_error", "response_format",
        )
    lang = (language or "").strip().lower()
    if lang and lang not in config.LANGUAGES:
        raise OpenAIError(
            400, f"language must be one of {', '.join(config.LANGUAGES)}, or empty for auto-detect (got {lang!r})",
            "invalid_request_error", "language",
        )
    requested_language = lang or config.DEFAULT_LANGUAGE

    cap = int(config.MAX_UPLOAD_MB * 1024 * 1024)
    size = 0
    fd, upload_path = tempfile.mkstemp(suffix=".upload")
    try:
        with os.fdopen(fd, "wb") as sink:
            while True:
                block = await file.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                if size > cap:
                    raise OpenAIError(
                        413, f"upload exceeds MAX_UPLOAD_MB={config.MAX_UPLOAD_MB:g}",
                        "invalid_request_error", "file_too_large",
                    )
                sink.write(block)
        if size == 0:
            raise OpenAIError(400, "empty audio file", "invalid_request_error", "file")

        wav_path = audio.convert_to_wav(upload_path)
        try:
            duration = audio.duration_seconds(wav_path)
            if duration <= 0:
                raise OpenAIError(400, "file contains no audio frames", "invalid_request_error", "file")
            if duration > config.MAX_AUDIO_SECONDS:
                raise OpenAIError(
                    413, f"audio is {duration:.0f}s, above MAX_AUDIO_SECONDS={config.MAX_AUDIO_SECONDS:g}",
                    "invalid_request_error", "audio_too_long",
                )
            result = _transcribe(wav_path, duration, requested_language,
                                 response_format == "verbose_json")
        finally:
            audio.unlink(wav_path)
    finally:
        audio.unlink(upload_path)

    return _format_response(result, duration, response_format)


def _transcribe(wav_path: str, duration: float, language, want_words: bool) -> dict:
    if duration <= config.MAX_SINGLE_PASS_SECONDS:
        return _one_pass(wav_path, language, want_words)
    if not config.CHUNK_LONG_AUDIO:
        raise OpenAIError(
            413, f"audio is {duration:.1f}s; the engine accepts at most "
                 f"{config.MAX_SINGLE_PASS_SECONDS:g}s per pass. Split the audio client-side, "
                 f"or set CHUNK_LONG_AUDIO=true to transcribe it in sequential chunks.",
            "invalid_request_error", "audio_too_long",
        )
    return _transcribe_chunked(wav_path, duration, language, want_words)


def _one_pass(wav_path: str, language, want_words: bool) -> dict:
    try:
        return engine.transcribe(wav_path, language=language, word_timestamps=want_words)
    except (RuntimeError, OSError) as exc:
        raise OpenAIError(500, f"transcription failed: {exc}", "engine_error") from exc


def _transcribe_chunked(wav_path: str, duration: float, language, want_words: bool) -> dict:
    texts, words, detected = [], [], ""
    for start, end in audio.chunk_bounds(duration, config.MAX_SINGLE_PASS_SECONDS):
        fd, chunk_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            audio.slice_to_wav(wav_path, start, end, chunk_path)
            part = _one_pass(chunk_path, language, want_words)
        finally:
            audio.unlink(chunk_path)
        texts.append((part.get("text") or "").strip())
        detected = detected or part.get("language") or ""
        for word in part.get("words") or []:
            words.append({
                "word": word.get("word"),
                "start": round(word.get("start", 0.0) + start, 3),
                "end": round(word.get("end", 0.0) + start, 3),
                "probability": word.get("probability"),
            })
    return {"text": " ".join(t for t in texts if t), "language": detected, "words": words}


def _format_response(result: dict, duration: float, response_format: str):
    text = result.get("text", "")
    if response_format == "text":
        return PlainTextResponse(text)
    if response_format == "verbose_json":
        return {
            "text": text,
            "language": result.get("language") or None,
            "duration": round(duration, 3),
            "words": [{
                "word": w.get("word"),
                "start": round(w.get("start", 0.0), 3),
                "end": round(w.get("end", 0.0), 3),
                "probability": w.get("probability"),
            } for w in (result.get("words") or [])],
            "segments": [],
        }
    return {"text": text}
