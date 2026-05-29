"""
transcriber.py — Local Whisper transcription with word-level timestamps.
Uses openai-whisper (local inference, no API calls).
"""

import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Max words per caption segment and max duration in seconds
MAX_WORDS_PER_SEGMENT = 5
MAX_SEGMENT_DURATION = 2.5


def transcribe(
    video_path: str,
    model_size: str = "small",
    language: str = "es",
) -> list[dict]:
    """
    Transcribe audio from a video file using local Whisper.

    Returns:
        List of word dicts: [{"word": str, "start": float, "end": float}]
    """
    try:
        import whisper
    except ImportError:
        raise ImportError(
            "openai-whisper not installed. Run: pip install openai-whisper"
        )

    video_path = Path(video_path)

    # Extract audio to a temp WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = tmp.name

    logger.info(f"Extracting audio from {video_path.name}...")
    _extract_audio(str(video_path), audio_path)

    logger.info(f"Loading Whisper model: {model_size}...")
    model = whisper.load_model(model_size)

    logger.info(f"Transcribing (language={language})...")
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        verbose=False,
    )

    # Flatten all word-level timestamps
    words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            text = w["word"].strip()
            if not text:
                continue
            words.append(
                {
                    "word": text.upper(),
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                }
            )

    # Clean up temp audio
    try:
        Path(audio_path).unlink()
    except Exception:
        pass

    logger.info(f"Transcription complete: {len(words)} words found.")
    return words


def group_into_segments(words: list[dict]) -> list[list[dict]]:
    """
    Group a flat word list into caption segments of ≤MAX_WORDS_PER_SEGMENT
    words or ≤MAX_SEGMENT_DURATION seconds.

    Returns:
        List of segments, each a list of word dicts.
    """
    segments = []
    current = []

    for word in words:
        if not current:
            current.append(word)
            continue

        seg_duration = word["end"] - current[0]["start"]
        if (
            len(current) >= MAX_WORDS_PER_SEGMENT
            or seg_duration > MAX_SEGMENT_DURATION
        ):
            segments.append(current)
            current = [word]
        else:
            current.append(word)

    if current:
        segments.append(current)

    return segments


def _ffmpeg_bin() -> str:
    import shutil
    from pathlib import Path as P
    full = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
    return full if P(full).exists() else (shutil.which("ffmpeg") or "ffmpeg")


def _extract_audio(video_path: str, audio_out: str) -> None:
    """Extract mono 16kHz WAV audio from video using FFmpeg."""
    cmd = [
        _ffmpeg_bin(),
        "-y",
        "-i", video_path,
        "-ac", "1",
        "-ar", "16000",
        "-vn",
        audio_out,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg audio extraction failed:\n{result.stderr}"
        )
