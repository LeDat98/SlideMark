"""Text metrics with Pillow: estimate wrapped line counts and heights without PowerPoint.

Latin text is measured with Liberation Sans (metric-compatible with Arial, slightly wider than Calibri, so the
estimate errs on the safe side). Full-width CJK characters count as 1em. Word wrap for Latin, per-character
wrap with simple kinsoku rules for CJK. The renderer imports the shared constants so that both sides agree.
"""

from __future__ import annotations

import unicodedata
from functools import cache

from ..ir import Paragraph, Style
from ..units import EMU_PER_PT

try:  # Pillow is a hard dependency, but never fail on a broken install
    from PIL import ImageFont
except Exception:  # pragma: no cover
    ImageFont = None  # type: ignore[assignment]

LINE_LATIN = 1.2  # line height / font size
LINE_CJK = 1.3
PARA_GAP = 0.25  # space before every paragraph but the first, x font size
SAFETY = 1.03  # estimate inflation
CELL_PAD_X = 91440  # 0.1in, table cell margins (renderer applies the same)
CELL_PAD_Y = 45720  # 0.05in

_FONT_PATHS = {
    "regular": [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "DejaVuSans.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "DejaVuSans-Bold.ttf",
    ],
}

# Kinsoku shori. No line may start with a NO_START char (closing punctuation, small kana, long vowel mark)
# or end with a NO_END char (opening bracket). Violations are fixed by pushing the previous character down
# to the next line (oikomi-free "oidashi"), which is the conservative choice: it never needs fewer lines than
# the real renderer. The renderer writes ``eaLnBrk="1" hangingPunct="0"`` so PowerPoint behaves the same.
NO_START = set(
    "、。，．・：；！？）］｝〕〉》」』】ー゛゜ゝゞぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ々〻‼⁇⁈⁉"
    "､｡｣ﾞﾟ,.!?:;)]}%"
)
NO_END = set("（［｛〔〈《「『【｢([{")


@cache
def _font(kind: str):
    if ImageFont is None:
        return None
    for path in _FONT_PATHS[kind]:
        try:
            return ImageFont.truetype(path, 100)
        except Exception:
            continue
    return None


def is_cjk(ch: str) -> bool:
    return unicodedata.east_asian_width(ch) in ("W", "F")


def has_cjk(text: str) -> bool:
    return any(is_cjk(c) for c in text)


@cache
def char_em(ch: str, kind: str = "regular") -> float:
    """Advance width of one character in em units (kind: regular, bold, mono)."""
    if is_cjk(ch):
        return 1.0
    if unicodedata.east_asian_width(ch) == "H":
        return 0.5
    if kind == "mono":
        return 0.6
    f = _font(kind)
    if f is None:
        return 0.55
    try:
        return f.getlength(ch) / 100
    except Exception:
        return 0.55


def text_em(text: str, bold: bool = False, mono: bool = False) -> float:
    kind = "mono" if mono else ("bold" if bold else "regular")
    return sum(char_em(c, kind) for c in text)


def list_indent(size_pt: float, level: int) -> tuple[int, int]:
    """(marL, indent) in EMU for a list paragraph; indent is negative (hanging bullet)."""
    hang = round(size_pt * 1.3 * EMU_PER_PT)
    return hang * (level + 1), -hang


def _units(segments: list[tuple[str, bool, bool]]) -> list[tuple[float, float, str, bool, str]]:
    """Split styled text into wrap units: (width_em, trailing_space_em, first_char, hard_break, last_char)."""
    units: list[tuple[float, float, str, bool, str]] = []
    st = {"word": "", "w": 0.0, "sp": 0.0}

    def flush():
        if st["word"] or st["sp"]:
            units.append((st["w"], st["sp"], st["word"][:1], False, st["word"][-1:]))
        st["word"], st["w"], st["sp"] = "", 0.0, 0.0

    for text, bold, mono in segments:
        kind = "mono" if mono else ("bold" if bold else "regular")
        for ch in text:
            if ch in "\n\v":
                flush()
                units.append((0.0, 0.0, "", True, ""))
            elif ch in " \t":
                st["sp"] += char_em(" ", kind)
            elif is_cjk(ch) or ch in NO_START or ch in NO_END:
                if is_cjk(ch):
                    flush()
                    units.append((char_em(ch, kind), 0.0, ch, False, ch))
                else:  # ASCII/half-width punctuation stays glued to its word
                    if st["sp"]:
                        flush()
                    st["word"] += ch
                    st["w"] += char_em(ch, kind)
            else:
                if st["sp"]:
                    flush()
                st["word"] += ch
                st["w"] += char_em(ch, kind)
    flush()
    return units


def count_lines(segments: list[tuple[str, bool, bool]], width_pt: float, size_pt: float) -> int:
    """Number of lines the styled text needs in ``width_pt`` at ``size_pt`` (with kinsoku)."""
    width = max(width_pt / max(size_pt, 1.0), 1.0)  # in em
    lines, cur = 1, 0.0
    line: list[tuple[float, float, str, bool, str]] = []  # units on the current line
    for u in _units(segments):
        w, sp, first, hard, _last = u
        if hard:
            lines += 1
            cur = 0.0
            line = []
            continue
        if cur > 0 and cur + w > width + 1e-6:
            # wrap before ``u``; kinsoku may drag trailing CJK units of this line down with it
            carry: list[tuple[float, float, str, bool, str]] = []
            starts_bad = first in NO_START and is_cjk(first)
            while len(line) > 1 and (starts_bad or (line[-1][4] in NO_END and is_cjk(line[-1][4]))):
                prev = line.pop()
                carry.insert(0, prev)
                starts_bad = prev[2] in NO_START and is_cjk(prev[2])
            lines += 1
            line = carry
            cur = sum(c[0] + c[1] for c in carry)
        if w > width:  # long word: breaks anywhere
            n = int(-(-w // width))
            lines += n - 1
            cur = w - (n - 1) * width
            line = [u]
        else:
            cur += w
            line.append(u)
        cur += sp
    return lines


def para_segments(p: Paragraph, bold: bool = False, mono: bool = False) -> list[tuple[str, bool, bool]]:
    return [(r.text, bold or r.bold, mono or r.code) for r in p.runs]


def paragraphs_height(
    paragraphs: list[Paragraph],
    width_emu: float,
    style: Style,
    scale: float = 1.0,
    *,
    default_size: float = 18,
    mono: bool = False,
) -> float:
    """Estimated height in EMU of ``paragraphs`` wrapped into ``width_emu`` (insets already removed)."""
    base = style.font_size or default_size
    total_pt = 0.0
    for i, p in enumerate(paragraphs):
        size = (p.style.font_size if p.style and p.style.font_size else base) * scale
        indent = list_indent(size, p.level)[0] if p.marker else 0
        wpt = (width_emu - indent) / EMU_PER_PT
        bold = bool((p.style and p.style.bold) or style.bold)
        lines = count_lines(para_segments(p, bold, mono), wpt, size)
        ls = (p.style.line_spacing if p.style and p.style.line_spacing else style.line_spacing) or 1.0
        lh = size * (LINE_CJK if has_cjk(p.plain) else LINE_LATIN) * ls
        total_pt += lines * lh + (size * PARA_GAP if i > 0 else 0)
    return total_pt * EMU_PER_PT * SAFETY


def code_height(text: str, width_emu: float, size_pt: float) -> float:
    """Height in EMU of a code block body (monospace, wrapped at the box width)."""
    cols = max(int(width_emu / EMU_PER_PT / (size_pt * 0.6)), 1)
    lines = 0
    for line in text.expandtabs(4).split("\n"):
        lines += max(1, -(-len(line) // cols))
    return lines * size_pt * LINE_LATIN * EMU_PER_PT * SAFETY


def effective_scale(base_size: float, scale: float, min_font: float) -> float:
    """Autofit factor for an element: never shrink below ``min_font`` pt, never grow."""
    if scale >= 1.0 or base_size <= min_font:
        return 1.0
    return min(1.0, max(scale, min_font / base_size))
