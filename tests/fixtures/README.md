# Test fixtures

Known-transcript clips used to sanity-check the deployed API (WER spot check,
language auto-detect, format conversion, and the 30 s clamp). Generated with
Windows SAPI TTS (en-US) and edge-tts (es-ES, de-DE, en-US).

| File | Duration | Language | Ground-truth transcript |
|---|---|---|---|
| `hello_en.wav` | 3.4 s | en | The quick brown fox jumps over the lazy dog. |
| `timestamps_en.wav` | 6.4 s | en | Welcome to the whistle speech to text API. This clip tests word level timestamps. |
| `hello_en.m4a` | 3.4 s | en | (m4a/AAC copy of hello_en.wav) |
| `hello_en.webm` | 3.4 s | en | (webm/Opus copy of hello_en.wav) |
| `hello_es.mp3` | 8.8 s | es | Hola, buenos días. El sol brilla sobre la montaña y el mar está en calma. Es un día perfecto para caminar. |
| `hello_de.mp3` | 9.0 s | de | Guten Morgen. Das Wetter ist heute schön und die Vögel singen im Garten. Wir trinken Kaffee auf der Terrasse. |
| `long_en.mp3` | 39.2 s | en | This is a longer test clip for the chunking mode. (…) Bright vixens jump dozy fowl quack. |

Note: these are synthetic TTS voices, used only as smoke tests — not as a
substitute for real-world audio evaluation.
