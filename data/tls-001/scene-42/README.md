# TLS-001 / Scene 42 — Demo Take Asset

Ships with the vision subsystem so the demo can run without asking judges
to generate their own footage.

## Files

- `take-03-keyframe.png` — Sarah in her apartment with the damaged handheld
  camera prop (cracked lens on the left face, dented top corner). Generated
  during the Contest Period with **Google Gemini `gemini-2.5-flash-image`**
  via the Gemini API.
- `take-03.mp4` — 5-second 720p H.264 wrap of the keyframe with a slow zoom,
  produced with ffmpeg. Serves as the video input for Google Cloud Video
  Intelligence in the demo pipeline.

## Bucket layout

Both files are also uploaded to:
```
gs://continuum-tls-001-assets/tls-001/scene-42/take-03.mp4
gs://continuum-tls-001-assets/tls-001/scene-42/take-03-keyframe.png
```

## Reproduce

```
python scripts/run_vision_real.py
```

Runs Video Intelligence + Gemini multimodal + Imagen embeddings against
the GCS URI above and prints structured observations.

## Compliance note

Every model used to produce this asset is a Google Cloud service — the
image comes from Gemini image generation, and ffmpeg is a non-AI codec.
No non-Google AI touched this file.
