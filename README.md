# Whistle STT API

An OpenAI-compatible speech-to-text API powered by [Whistle](https://huggingface.co/Cactus-Compute/whistle),
Cactus Compute's 16.9 MB on-device transcription model. CPU-only, ~200-400 MB of
RAM — small enough for free-tier containers where multi-GB Whisper images do not fit.

Deploys on Railway with **zero configuration and zero credentials**: the model and
engine are baked into the image at build time, so boot makes no network calls.

## What you get

- `POST /v1/audio/transcriptions` — OpenAI-compatible multipart endpoint
  (`file`, `model`, `language`, `response_format` = `json` / `text` / `verbose_json`)
- Word-level timestamps via `response_format=verbose_json`
- Auto language detection across 7 languages: English, German, French, Spanish,
  Italian, Dutch, Polish
- Input formats: anything ffmpeg decodes — mp3, webm/m4a (voice memos), wav, flac, ogg
- `GET /v1/models`, `GET /health` (also reports live memory usage)

## One-click deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.com/deploy/whistle-stt-api)

## Quick start

```bash
curl https://your-service.up.railway.app/v1/audio/transcriptions \
  -F file=@clip.mp3 \
  -F model=whistle
# {"text": "the quick brown fox jumps over the lazy dog"}

curl https://your-service.up.railway.app/v1/audio/transcriptions \
  -F file=@clip.mp3 -F response_format=verbose_json
# {"text": "...", "language": "en", "duration": 4.2,
#  "words": [{"word": "the", "start": 0.08, "end": 0.15, ...}], "segments": []}
```

With an API key (set the `API_KEY` variable), send `-H "Authorization: Bearer <key>"`.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8000` | HTTP port |
| `API_KEY` | *(empty = open)* | Require `Authorization: Bearer <key>` when set |
| `WHISTLE_DEFAULT_LANGUAGE` | *(empty = auto)* | Force a language when requests omit `language` (`en de fr es it nl pl`) |
| `CHUNK_LONG_AUDIO` | `false` | `true` = transcribe clips longer than 30 s as sequential 30 s chunks |
| `MAX_UPLOAD_MB` | `25` | Upload size cap (413 beyond) |
| `MAX_AUDIO_SECONDS` | `900` | Audio length cap after decoding (413 beyond) |
| `NEEDLE_TELEMETRY` / `DO_NOT_TRACK` | `0` / `1` | Upstream telemetry disabled (baked in) |

## Honest disclosures

- **7 languages only**: en, de, fr, es, it, nl, pl. Requests in other languages
  produce garbage or empty output.
- **30 seconds per pass**: the engine processes at most 30 s at a time. Longer
  audio is rejected by default; set `CHUNK_LONG_AUDIO=true` for fixed-boundary
  sequential chunking (a word straddling a boundary may be cut; there is no VAD).
- **Early-stage model**: Whistle was announced 2026-10-02; published benchmarks
  are from an Apple M4 Pro. Accuracy on server x86_64 CPUs may differ — try your
  own audio before committing.
- **Throughput**: requests are serialized in-process (the engine is not
  thread-safe). Long files with `CHUNK_LONG_AUDIO=true` hold the queue; scale
  with Railway replicas for concurrency.
- Upstream telemetry is disabled via `NEEDLE_TELEMETRY=0` and `DO_NOT_TRACK=1`;
  `HF_HUB_OFFLINE=1` guarantees the running service never calls Hugging Face.

## Comparison with Whisper templates

Whisper-class templates (faster-whisper, Speaches) are more accurate and support
dozens of languages, but need 1-4+ GB of RAM and model weights downloaded at
boot. Whistle trades coverage for footprint: a single 16.9 MB file, ~200-400 MB
total container memory, instant cold start. Choose it for short clips, free-tier
limits, and the seven supported languages.

## Links

- Model + weights: https://huggingface.co/Cactus-Compute/whistle
- Engine (`cactus-needle`): https://github.com/cactus-compute/needle
- API source: this repository (`app/`)

## License

Apache-2.0 (matching the engine and weights). See `LICENSE`.
