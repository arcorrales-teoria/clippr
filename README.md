# clippr

Local CLI tool that converts any video into a vertical 9:16 clip with automatic
speaker tracking and karaoke-style burned-in captions — no cloud services, no
paid APIs, everything runs on your machine.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python      | 3.10+   | `python3 --version` |
| FFmpeg      | any recent | `brew install ffmpeg` (macOS) · `sudo apt install ffmpeg` (Linux) |
| pip         | latest  | `pip install --upgrade pip` |
| CUDA (GPU)  | optional | Whisper + YOLO auto-detect and use CUDA if available |

---

## Installation

```bash
# 1. Install FFmpeg (macOS)
brew install ffmpeg

# 1. Install FFmpeg (Ubuntu / Debian)
sudo apt install ffmpeg -y

# 2. Install Python dependencies
pip install -r ~/Desktop/clippr/requirements.txt
```

On first run the tool will automatically download:
- **YOLOv8n weights** (~6 MB)  — from Ultralytics
- **Whisper model** (~500 MB for `small`)  — from OpenAI / HuggingFace

Both are cached locally and never re-downloaded.

---

## Usage

### Minimal (output auto-saved to `clippr/outputs/`)

```bash
python ~/Desktop/clippr/main.py --input talk.mp4
```

### Full options

```bash
python ~/Desktop/clippr/main.py \
  --input  talk.mp4 \
  --output ~/Desktop/clippr/outputs/clip.mp4 \
  --model  small \
  --lang   es
```

### All flags

| Flag | Default | Description |
|------|---------|-------------|
| `--input` / `-i` | *(required)* | Path to source video |
| `--output` / `-o` | `outputs/<name>_clip.mp4` | Output MP4 path |
| `--model` / `-m` | `small` | Whisper model: `tiny` `base` `small` `medium` `large` |
| `--lang` / `-l` | `es` | Language hint for Whisper (ISO 639-1 code) |
| `--max-width` | `1080` | Output width in px (height = width × 16/9) |
| `--sample-every` | `3` | YOLO processes 1 of every N frames (higher = faster) |
| `--verbose` / `-v` | off | Enable debug logging |
| `--skip-preload` | off | Skip model download check on startup |

---

## Output

The rendered MP4 is saved at `~/Desktop/clippr/outputs/<original_name>_clip.mp4`
(or the path you provided with `--output`).

The file is ready to upload directly to:
- Instagram Reels
- TikTok
- YouTube Shorts

---

## How it works

```
Input video
    │
    ▼
[1] YOLOv8n detects persons per frame (every 3rd frame by default)
    │
    ▼
[2] Rolling-average + exponential smoother removes camera jitter
    │
    ├──▶ [3] Whisper transcribes audio → word-level timestamps
    │              │
    │              ▼
    │         [4] caption_builder generates .ASS karaoke subtitle file
    │
    ▼
[5] FFmpeg single-pass pipeline:
      sendcmd dynamic crop  →  scale to 9:16  →  subtitle burn  →  H.264 export
```

---

## Performance estimates

| Whisper model | Quality | ~VRAM | 10-min video (CPU) | 10-min video (GPU) |
|---------------|---------|-------|--------------------|--------------------|
| `tiny`        | draft   | 1 GB  | ~2 min             | <1 min             |
| `base`        | good    | 1 GB  | ~3 min             | ~1 min             |
| `small`       | great   | 2 GB  | ~6 min             | ~2 min             |
| `medium`      | very good | 5 GB | ~15 min           | ~4 min             |
| `large`       | best    | 10 GB | ~30 min            | ~8 min             |

YOLO tracking adds roughly 1–3× real-time on CPU, much less on GPU.
FFmpeg rendering is nearly always real-time or faster.

---

## GPU acceleration

If CUDA is available, both Whisper and YOLOv8 will use it automatically — no
configuration needed. Check with:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

On Apple Silicon (M1/M2/M3) Whisper can use MPS:

```bash
python -c "import torch; print(torch.backends.mps.is_available())"
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `FFmpeg not found` | `brew install ffmpeg` or `sudo apt install ffmpeg` |
| `No module named 'whisper'` | `pip install openai-whisper` |
| `No module named 'ultralytics'` | `pip install ultralytics` |
| Captions missing | Check `outputs/ffmpeg.log` for ASS filter errors |
| Video is just black | Check `outputs/ffmpeg.log` — likely a crop/scale mismatch |
| Very slow on CPU | Use `--model tiny` or `--sample-every 5` for faster processing |

Detailed FFmpeg output is always written to `~/Desktop/clippr/outputs/ffmpeg.log`.
