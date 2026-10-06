"""Phrase-aware line breaks for CJK paragraphs (render only).

Viewers break CJK text between any two characters ("平均年" / "齢"). A designer breaks at phrase
(bunsetsu) boundaries ("点検技術者の" / "平均年齢"). :func:`plan_breaks` segments the paragraph with BudouX
(lazy import, optional at run time) and, when the viewer model predicts a break inside a phrase, packs whole
phrases into lines. It returns the cut offsets for the renderer, which writes soft breaks there, only when
the packed paragraph needs no more lines than the layout reserved (box heights never change).
"""

from __future__ import annotations

from bisect import bisect_right

from ..ir import Paragraph, Style
from . import measure
from .measure import NO_END, NO_START, VIEWER_GAP, WJ

SOFT_BREAK_MARK = "sm"  # value of ``bmk`` on the rPr of an inserted ``a:br``; the importer drops those breaks

_parser = None
_parser_failed = False


def _phrases(text: str) -> list[str] | None:
    global _parser, _parser_failed
    if _parser_failed:
        return None
    if _parser is None:
        try:
            import budoux

            _parser = budoux.load_default_japanese_parser()
        except Exception:  # not installed or broken: no phrase breaks, never an error
            _parser_failed = True
            return None
    return _parser.parse(text)


def phrase_cuts(text: str) -> list[int]:
    """Offsets in ``text`` where a new phrase starts (sorted, without 0)."""
    out, pos = [], 0
    for ph in _phrases(text) or []:
        pos += len(ph)
        out.append(pos)
    return out[:-1]


_Flat = list[tuple[str, int, int]]  # (char as the viewer sees it, run index, offset in the run text; -1 = gap)


def _flatten(texts: list[str], gap_em: float) -> _Flat:
    flat: _Flat = []
    for ri, t in enumerate(texts):
        v = measure._viewer_text(t, VIEWER_GAP * round(gap_em / measure.VIEWER_GAP_EM) if gap_em > 0 else "")
        j = 0
        for ch in v:
            if ch == VIEWER_GAP:
                flat.append((ch, ri, -1))
                continue
            while j < len(t) and t[j] != ch:  # a joiner the viewer drops
                j += 1
            flat.append((ch, ri, j))
            j += 1
    return flat


def _can_cut(flat: _Flat, e: int) -> bool:
    """May a viewer-model line end before flat[e]?"""
    a, b = flat[e - 1][0], flat[e][0]
    if a in NO_END or b in NO_START or WJ in (a, b) or " " in (a, b) and a != " ":
        return False
    if a == " ":
        return True
    if measure.is_katakana(a) and measure.is_katakana(b):
        return False
    return measure.is_cjk(a) or measure.is_cjk(b) or b == VIEWER_GAP


class _Measure:
    def __init__(self, flat: _Flat, segs: list, size: float, font: str | None):
        self.flat, self.size, self.font = flat, size, font
        self.flags = [s[1:] for s in segs]

    def fits(self, s: int, e: int, width: float, sp: float) -> bool:
        segs: list = []
        for ch, ri, _ in self.flat[s:e]:
            if segs and segs[-1][0] == ri:
                segs[-1][1].append(ch)
            else:
                segs.append((ri, [ch]))
        seg_t = [("".join(c), *self.flags[ri]) for ri, c in segs]
        return measure._count_lines(seg_t, width, self.size, self.font, sp)[0] <= 1

    def end(self, s: int, width: float, sp: float, cands: list[int]) -> int:
        """Largest candidate end > s whose line [s, end) fits; -1 when none."""
        lo, hi, best = bisect_right(cands, s), len(cands) - 1, -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.fits(s, cands[mid], width, sp):
                best, lo = cands[mid], mid + 1
            else:
                hi = mid - 1
        return best


def _natural_starts(m: _Measure, width: float, sp: float) -> list[int] | None:
    n = len(m.flat)
    cands = [e for e in range(1, n) if _can_cut(m.flat, e)] + [n]
    starts, s = [], 0
    while s < n:
        e = m.end(s, width, sp, cands)
        if e < 0:
            return None
        if e >= n:
            break
        starts.append(e)
        s = e
    return starts


def plan_breaks(
    p: Paragraph,
    style: Style,
    width_pt: float,
    size_pt: float,
    sq: float,
    *,
    mono: bool = False,
) -> tuple[dict[int, list[int]], float] | None:
    """Soft-break offsets for paragraph ``p`` and the letter spacing to render it with, or ``None``.

    ``{run index: [offsets in the run's bound text]}``. ``sq`` is the orphan squeeze the renderer would
    use. ``None`` when nothing to do: the viewer already breaks at phrase boundaries, the paragraph is not
    CJK, has badges, hard breaks, explicit spacing or a text transform, no phrase packing exists, or it
    would need more lines than the model reserved."""
    tk = measure.tokens()
    if not tk.cjk_phrase_break or mono or measure._explicit_spacing(style, p) or not p.runs:
        return None
    if not measure.has_cjk(p.plain) or any(r.highlight or r.code for r in p.runs):
        return None
    _, tf = measure.text_spacing(style, p)
    if tf:
        return None
    bold = bool((p.style and p.style.bold) or style.bold)
    segs = measure.para_segments(p, bold, mono, tf)
    texts = [s[0] for s in segs]
    if any(c in t for t in texts for c in "\n\v\r"):
        return None
    font = style.font
    reserved = measure.count_lines(segs, width_pt, size_pt, font, 0.0)
    if reserved < 1 or measure.count_lines(segs, width_pt, size_pt, font, sq) < 1:
        return None
    flat = _flatten(texts, tk.cjk_latin_gap)
    n = len(flat)
    if n < 4:
        return None
    m = _Measure(flat, segs, size_pt, font)
    plain = "".join(c for c, _, o in flat if o >= 0)
    if not any(measure.is_cjk(c) for c in plain):
        return None
    # phrase boundaries as flat indices (before the gap markers that precede the phrase's first character)
    pos_of = {}
    k = 0
    for i, (_, _, o) in enumerate(flat):
        if o >= 0:
            pos_of[k] = i
            k += 1
    bounds = set()
    for c in phrase_cuts(plain):
        i = pos_of.get(c)
        if i is None:
            continue
        while i > 0 and flat[i - 1][2] < 0:
            i -= 1
        while i < n and flat[i][0] == " ":
            i += 1  # a space stays at the end of the previous line
        if 0 < i < n and _can_cut(flat, i):
            bounds.add(i)
    if not bounds:
        return None
    cands = sorted(bounds) + [n]
    for sp in dict.fromkeys((0.0, sq)):
        wnat = width_pt
        nat = _natural_starts(m, wnat, sp)
        if nat is None or not nat:
            if sp == sq:
                return None
            continue
        if all(e in bounds for e in nat):
            return None  # the viewer breaks between phrases already
        cuts: list[int] = []
        s, ok = 0, True
        width = width_pt * (1.0 - tk.cjk_phrase_margin)
        while s < n:
            e = m.end(s, width, sp, cands)
            if e < 0:
                ok = False
                break
            if e >= n:
                break
            cuts.append(e)
            s = e
        if ok and len(cuts) + 1 <= reserved:
            out: dict[int, list[int]] = {}
            for e in cuts:
                j = e
                while j < n and flat[j][2] < 0:
                    j += 1
                ri, off = (flat[j][1], flat[j][2]) if j < n else (flat[-1][1], 1 << 30)
                out.setdefault(ri, []).append(off)
            return out, sp
    return None
