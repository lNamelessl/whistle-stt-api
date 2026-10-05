# Whistle STT API — 16.9 MB on-device speech-to-text

An OpenAI-compatible transcription API (`POST /v1/audio/transcriptions`) powered by
[Whistle](https://huggingface.co/Cactus-Compute/whistle), Cactus Compute's 16.9 MB
on-device speech-recognition model. One click deploys a FastAPI service that transcribes
mp3, m4a, webm, wav and more on CPU — in about 120 MB of RAM, small enough for
free-tier containers where multi-GB Whisper images do not fit.

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/trHp_c)

## What you get

- **OpenAI-compatible endpoint**: `POST /v1/audio/transcriptions` with `file`, `model`,
  `language`, `response_format` (`json`, `text`, or `verbose_json` with word-level timestamps) —
  drop-in for clients that target `api.openai.com/v1/audio/transcriptions`
- **7 languages** with auto-detection: English, German, French, Spanish, Italian, Dutch, Polish
- **Word-level timestamps** via `verbose_json`, plus `GET /v1/models` and a `GET /health`
  endpoint that reports live memory usage
- **Zero configuration and zero credentials**: model and engine are baked into the image at
  build time; the running container makes no network calls (`HF_HUB_OFFLINE=1`) and upstream
  telemetry is disabled (`NEEDLE_TELEMETRY=0`, `DO_NOT_TRACK=1`)
- **Optional API key**: set `API_KEY` to require `Authorization: Bearer <key>`

## Quick start after deploy

```bash
curl https://your-service.up.railway.app/v1/audio/transcriptions \
  -F file=@clip.mp3 -F model=whistle
# {"text": "the quick brown fox jumps over the lazy dog"}

curl https://your-service.up.railway.app/v1/audio/transcriptions \
  -F file=@clip.mp3 -F response_format=verbose_json
```

## Configuration (all optional — the template deploys with none of them set)

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8000` | HTTP port (pre-configured) |
| `API_KEY` | *(empty = open)* | Require `Authorization: Bearer <key>` when set |
| `WHISTLE_DEFAULT_LANGUAGE` | *(empty = auto)* | Force a language when requests omit `language` |
| `CHUNK_LONG_AUDIO` | `false` | Transcribe clips longer than 30 s as sequential 30 s chunks |
| `MAX_UPLOAD_MB` | `25` | Upload size cap (413 beyond) |
| `MAX_AUDIO_SECONDS` | `900` | Audio length cap after decoding (413 beyond) |

## Honest disclosures

- Whistle supports **only these 7 languages**: en, de, fr, es, it, nl, pl. Other languages
  produce garbage or empty output. Whisper-class models cover dozens of languages and are more
  accurate; this template trades coverage for a ~100x smaller footprint.
- The engine processes **at most 30 seconds per pass**. Longer audio is rejected with a clear
  error unless you set `CHUNK_LONG_AUDIO=true`, which uses fixed 30 s boundaries (a word
  straddling a boundary may be cut; there is no VAD).
- **Early-stage model**: Whistle was announced 2026-10-02 and its published benchmarks come
  from an Apple M4 Pro. Accuracy on server x86_64 CPUs may differ — in our smoke tests,
  short English and Spanish clips transcribed perfectly, with occasional errors on fast,
  dense English pangrams. Evaluate with your own audio.
- Requests are **serialized in-process** (the engine is not thread-safe); scale with Railway
  replicas for concurrency.

# Deploy and Host

## About Hosting

Deploying this template provisions exactly one Railway service: a Docker container built from
the [public repo](https://github.com/lNamelessl/whistle-stt-api) (`python:3.12-slim` + ffmpeg +
`cactus-needle==3.1.0`, with the Whistle weights and engine binary baked in at build time).
Railway assigns a public domain automatically and health-checks `/health` (restart on failure,
up to 10 retries). There are no databases, no required variables, and no credentials: the only
pre-set variable is `PORT=8000`, and every other setting ships as a sane image default listed
in the table above. Idling memory is ~80 MB; expect roughly 120 MB under load, comfortably
within free-tier limits.

## Why Deploy

The Whistle engine is a library, not a service: getting from `pip install cactus-needle` to a
running API means wrapping it in a server, pinning the exact model and engine versions,
downloading weights at build time (so boots are offline), converting arbitrary audio to
16 kHz mono WAV, serializing access to a non-thread-safe engine, and matching OpenAI's request
and error shapes. This template does all of that and verifies it: word timestamps, language
auto-detection, mp3/m4a/webm decoding, the 30 s clamp, API-key gating, and a ≤512 MB memory
envelope are all smoke-tested before every publish.

## Common Use Cases

- Adding speech-to-text to apps hosted on free-tier containers, where Whisper's multi-GB
  memory footprint does not fit
- Transcribing short voice notes (voicemail, WhatsApp/webm, iOS m4a memos) in English, German,
  French, Spanish, Italian, Dutch, or Polish
- An OpenAI-compatible drop-in: point an existing `openai` SDK client at your Railway domain
  and switch `base_url` — no code changes beyond the endpoint
- Privacy-conscious pipelines: audio is processed in-container and the running service makes
  no outbound calls

## Dependencies for

This template is self-contained: no external services, APIs, or accounts are required.

### Deployment Dependencies

- A Railway account (Hobby plan or trial works — the service fits free-tier memory limits)
- That is all. The model weights (16,919,407 B `whistle.cact`) and engine binary are downloaded
  once during the image build on Railway's builders and baked into the image; the deployed
  container needs no Hugging Face access, API keys, or volumes at runtime
