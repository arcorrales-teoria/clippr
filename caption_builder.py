"""
caption_builder.py — Generates an .ASS subtitle file with karaoke-style
word-by-word highlighting for burned-in captions.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── ASS colour constants (AABBGGRR format) ────────────────────────────────────
COLOUR_ACTIVE_WORD = "&H0000FFFF"   # Yellow (BGR: 00 FF FF)
COLOUR_INACTIVE    = "&H00FFFFFF"   # White
COLOUR_OUTLINE     = "&H00000000"   # Black
COLOUR_SHADOW      = "&H80000000"   # Semi-transparent black


def build_ass(
    segments: list[list[dict]],
    output_path: str,
    video_width: int = 1080,
    video_height: int = 1920,
    font_size: int = 65,
) -> str:
    """
    Write an .ASS file with per-word karaoke highlighting.

    Args:
        segments:     Output of transcriber.group_into_segments()
        output_path:  Where to write the .ass file
        video_width:  Output video width (for PlayResX)
        video_height: Output video height (for PlayResY)
        font_size:    Base font size (pt)

    Returns:
        Path to the written .ass file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(_ass_header(video_width, video_height, font_size))
    lines.append("[Events]")
    lines.append(
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    )

    for segment in segments:
        if not segment:
            continue
        seg_start = segment[0]["start"]
        seg_end   = segment[-1]["end"]

        dialogue = _build_karaoke_line(segment, seg_start, seg_end)
        lines.append(dialogue)

    content = "\n".join(lines) + "\n"
    output_path.write_text(content, encoding="utf-8")

    logger.info(f"ASS subtitle file written: {output_path}")
    return str(output_path)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _ass_header(width: int, height: int, font_size: int) -> str:
    # Vertical margin = bottom 12% of frame
    v_margin = int(height * 0.12)

    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},{COLOUR_INACTIVE},{COLOUR_ACTIVE_WORD},{COLOUR_OUTLINE},{COLOUR_SHADOW},-1,0,0,0,100,100,1,0,1,5,3,2,30,30,{v_margin},1"""


def _ts(seconds: float) -> str:
    """Convert float seconds to ASS timestamp H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds % 1) * 100))
    # Clamp centiseconds
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _build_karaoke_line(
    segment: list[dict], seg_start: float, seg_end: float
) -> str:
    """
    Build a single ASS Dialogue line with \\k karaoke tags.

    The entire segment is shown for its full duration.
    Each word is highlighted (SecondaryColour) when it's the active word,
    using the \\k<centiseconds> tag which advances the karaoke pointer.
    """
    # Leading silence before first word
    text_parts = []
    cursor = seg_start

    for i, w in enumerate(segment):
        # Gap before this word (in centiseconds)
        gap_cs = max(0, int(round((w["start"] - cursor) * 100)))
        if gap_cs > 0:
            text_parts.append(f"{{\\k{gap_cs}}}")

        # Duration of this word in centiseconds
        word_cs = max(1, int(round((w["end"] - w["start"]) * 100)))
        # \\kf = filled karaoke (word fill left-to-right); \\k = instant highlight
        text_parts.append(f"{{\\kf{word_cs}}}{w['word']}")

        cursor = w["end"]
        if i < len(segment) - 1:
            text_parts.append(" ")

    text = "".join(text_parts)

    return (
        f"Dialogue: 0,{_ts(seg_start)},{_ts(seg_end)},"
        f"Default,,0,0,0,,{text}"
    )
