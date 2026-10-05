"""Build-time bake for the Whistle STT API image.

Downloads the engine binary and whistle weights into /app/models, then runs a
sine-wave transcription through the exact resolution path the server uses at
runtime (NEEDLE3_LIB_PATH + NEEDLE_WHISTLE_WEIGHTS). An engine that cannot
load or run on this platform fails the Docker build right here.
"""

import math
import os
import sys

MODELS_DIR = os.environ.get("MODELS_DIR", "/app/models")


def main() -> None:
    from needle.agent import fetch

    weights = fetch.fetch_weights("whistle", dest_dir=MODELS_DIR)
    lib = fetch.fetch_library(dest_dir=MODELS_DIR, generation=3)
    print(f"[warmup] baked weights {weights} ({os.path.getsize(weights)} bytes)")
    print(f"[warmup] baked engine  {lib} ({os.path.getsize(lib)} bytes)")

    os.environ["NEEDLE_WHISTLE_WEIGHTS"] = weights
    os.environ["NEEDLE3_LIB_PATH"] = lib

    from needle import Whistle

    whistle = Whistle()
    samples = [0.3 * math.sin(2 * math.pi * 440 * i / 16000) for i in range(16000)]
    result = whistle.transcribe(samples, word_timestamps=True)
    missing = {"text", "language", "ttft_ms", "decode_tps"} - set(result)
    if missing:
        raise SystemExit(f"[warmup] engine output missing keys: {sorted(missing)}")
    print(f"[warmup] smoke test on {sys.platform}: text={result['text']!r} keys={sorted(result)}")
    print("[warmup] OK")


if __name__ == "__main__":
    main()
