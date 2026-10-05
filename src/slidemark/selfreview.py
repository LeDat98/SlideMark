"""Self-review loop behind ``slidemark review --fix``: build -> lint + critique (+ pixel checks) -> automatic
SOURCE edits -> rebuild, until the score stops improving or ``MAX_ROUNDS`` rounds.

Edits (each deterministic, tried on a trial build and kept only when it helps; content text is never
changed except to split it across slides or to move a title's tail into the lead):

1. ``check --fix`` mechanical fixes (unknown tokens, missing ``@end``, ...), see ``fix.py``.
2. Overflow / too dense slide: ``dense`` on the slide's ``@`` line when that clears it, else split the slide
   at a box / list item / table row boundary (``Title (1/2)``, table header and box heading repeated).
3. Low contrast on a color the deck declared: swap it for ``render.ink_dark`` / ``ink_light``.
4. ``design-long-title``: the tail of the title moves into the ``>`` lead.
5. With PNGs: ``pixel-contrast`` warnings from the rendered pixels (gradient / image backgrounds); a declared
   text color is swapped like in 3.
"""

from __future__ import annotations

import tempfile
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import redesign
from .fix import RULES as _FIX_RULES
from .fix import Fixed, fix_text
from .ir import Container, Deck, Diagnostic, Placed, Slide, Table, Text

MAX_ROUNDS = 3
FILLER = ["# Filler", "- a", "- b", "- c"]
DENSITY_RULES = {"overflow", "tiny-text", "design-too-many-blocks", "design-wall-of-text"}
PIXEL_MIN_RATIO = 3.0
_OWNED = DENSITY_RULES | {"contrast", "design-long-title", "pixel-contrast"} | set(_FIX_RULES)


# --------------------------------------------------------------------------- analysis


@dataclass
class Analysis:
    deck: Deck
    diags: list[Diagnostic]
    score: int
    placed: list[list[Placed]] = field(default_factory=list)
    theme: object | None = None
    pixel_bg: dict[tuple[int, int | None], tuple[float, float, float]] = field(default_factory=dict)

    @property
    def warnings(self) -> int:
        return sum(1 for d in self.diags if d.level in ("warning", "error"))

    @property
    def fixable(self) -> int:
        """Diagnostics this loop owns (others, such as ``design-empty-band``, belong to the layout)."""
        return sum(1 for d in self.diags if d.rule in _OWNED and d.level in ("warning", "error"))

    @property
    def dense(self) -> int:
        return sum(1 for s in self.deck.slides if s.html is None and too_dense(s))


def analyze(text: str, base_dir: str | Path | None = None, *, is_json: bool = False) -> Analysis:
    """Parse, lay out, lint and critique a deck. Never raises: failures become diagnostics."""
    from .critique import critique, review_score

    if is_json:
        from .jsonio import load_deck

        deck = load_deck(text)
    else:
        from .parser import parse

        deck = parse(text)
    diags = list(deck.diagnostics)
    placed: list[list[Placed]] = []
    theme = None
    if not any(d.level == "error" for d in deck.diagnostics):
        try:
            from .layout import layout_slide
            from .lint import lint
            from .template import deck_theme, template_size

            deck.attrs.setdefault("base_dir", str(Path(base_dir or ".").resolve()))
            theme, tdiags = deck_theme(deck, deck.attrs["base_dir"])
            diags.extend(tdiags)
            if size := template_size(theme):
                deck.size = size
            try:
                placed = [layout_slide(s, deck, theme, i) for i, s in enumerate(deck.slides)]
            finally:
                if any(s.html is not None for s in deck.slides):
                    from .layout.htmlslide import close_shared

                    close_shared()
            seen = {(d.rule, d.slide) for d in diags}
            diags.extend(d for d in lint(deck, placed, theme) if (d.rule, d.slide) not in seen)
            diags.extend(critique(deck, placed, theme))
        except NotImplementedError:
            pass
        except Exception as e:
            diags.append(
                Diagnostic(
                    level="warning",
                    message=f"review failed: {type(e).__name__}: {e}",
                    rule="check-layout",
                    hint="report this deck as a bug; the diagnostics above are still valid",
                )
            )
    return Analysis(deck, diags, review_score(diags, len(deck.slides)), placed, theme)


def too_dense(slide: Slide) -> bool:
    """The SKILL.md limits: more than 4 boxes with a box of more than 6 bullets, or a table of more than 8
    data rows."""
    boxes = [e for e in slide.elements if isinstance(e, Container)]

    def bullets(c: Container) -> int:
        return sum(1 for ch in c.children if isinstance(ch, Text) for p in ch.paragraphs if p.marker)

    if len(boxes) > 4 and any(bullets(b) > 6 for b in boxes):
        return True
    tables = [e for e in slide.elements if isinstance(e, Table)]
    tables += [ch for b in boxes for ch in b.children if isinstance(ch, Table)]
    return any(len(t.rows) - t.header_rows > 8 for t in tables)


# --------------------------------------------------------------------------- pixel check


def _rgb255(c: tuple[float, float, float]) -> tuple[int, int, int]:
    return tuple(round(v * 255) for v in c)  # type: ignore[return-value]


def pixel_check(ana: Analysis, pngs: list[Path]) -> list[Diagnostic]:
    """Contrast of text against the *rendered* pixels around it, on slides whose background (or whose text
    box fill) is a gradient or picture, where ``lint`` cannot judge. Fills ``ana.pixel_bg`` for the fixer."""
    out: list[Diagnostic] = []
    theme = ana.theme
    if theme is None or not pngs:
        return out
    try:
        from PIL import Image

        from .layout import css
        from .lint import _GRADIENT, _is_image, _label, _rgba, contrast_ratio
        from .units import slide_size
    except ImportError:
        return out

    def plain(fill: str | None) -> bool:
        return not fill or not (_GRADIENT.match(fill) or _is_image(fill, theme))

    try:
        W, _H = slide_size(ana.deck.size)
    except ValueError:
        W, _H = slide_size("16:9")
    for i, slide in enumerate(ana.deck.slides):
        if i >= len(pngs) or i >= len(ana.placed) or slide.hidden:
            continue
        try:
            slide_fill = slide.background or css.slide_style(ana.deck, slide, i).fill
        except Exception:
            slide_fill = slide.background
        special_bg = not plain(slide_fill)
        try:
            img = Image.open(pngs[i]).convert("RGB")
        except OSError:
            continue
        scale = img.width / W
        for p in ana.placed[i]:
            paras = getattr(p.element, "paragraphs", None)
            if not paras or not any(q.plain.strip() for q in paras):
                continue
            if plain(p.style.fill) and not special_bg:
                continue
            if p.style.fill and plain(p.style.fill) and _rgba(p.style.fill, theme):
                continue  # a solid card on top: lint judged it
            fg = _rgba(p.style.color or "fg", theme)
            if not fg:
                continue
            box = (
                max(0, int(p.x * scale)),
                max(0, int(p.y * scale)),
                min(img.width, int((p.x + p.w) * scale)),
                min(img.height, int((p.y + p.h) * scale)),
            )
            if box[2] - box[0] < 8 or box[3] - box[1] < 8:
                continue
            crop = img.crop(box)
            crop.thumbnail((64, 64))
            px = list(crop.get_flattened_data() if hasattr(crop, "get_flattened_data") else crop.getdata())
            ft = _rgb255(fg[0])
            rest = [c for c in px if sum(abs(a - b) for a, b in zip(c, ft, strict=True)) > 60] or px
            mode = Counter((c[0] >> 4, c[1] >> 4, c[2] >> 4) for c in rest).most_common(1)[0][0]
            sel = [c for c in rest if (c[0] >> 4, c[1] >> 4, c[2] >> 4) == mode]
            bg = tuple(sum(c[k] for c in sel) / len(sel) / 255 for k in range(3))
            ratio = contrast_ratio(fg[0], bg)  # type: ignore[arg-type]
            if ratio < PIXEL_MIN_RATIO:
                line = getattr(p.element, "line", None)
                out.append(
                    Diagnostic(
                        level="warning",
                        message=f"{_label(p)} has {ratio:.1f}:1 contrast on the rendered background",
                        slide=i + 1,
                        line=line,
                        rule="pixel-contrast",
                        hint="set `{color=#FFF}` or `{color=#111}` on it, or put a solid `fill` behind it",
                    )
                )
                ana.pixel_bg[(i + 1, line)] = bg  # type: ignore[assignment]
    return out


def render_pngs(text: str, base_dir: str | Path | None, out_dir: Path) -> list[Path]:
    """Build ``text`` and render PNGs to ``out_dir``; [] when LibreOffice is missing or anything fails."""
    try:
        from .build import build
        from .preview import have_soffice, pptx_to_pngs

        if not have_soffice():
            return []
        with tempfile.TemporaryDirectory(prefix="slidemark-") as tmp:
            pptx = Path(tmp) / "deck.pptx"
            build(text, pptx, base_dir=base_dir or Path.cwd())
            return pptx_to_pngs(pptx, out_dir)
    except Exception:
        return []


# --------------------------------------------------------------------------- trial builds


def _penalty(diags: list[Diagnostic]) -> int:
    from .critique import WEIGHTS

    total = 0
    for d in diags:
        if d.rule in WEIGHTS:
            total += WEIGHTS[d.rule] if d.level == "warning" else 1
        elif d.level == "error":
            total += 15
        elif d.level == "warning":
            total += 6
        else:
            total += 1
    return total


@dataclass
class _Key:
    targets: int
    warnings: int
    penalty: int

    def better_than(self, base: _Key) -> bool:
        if self.warnings > base.warnings:
            return False
        return (self.targets, self.warnings, self.penalty) < (base.targets, base.warnings, base.penalty)


class _Trial:
    """Builds ``header + filler + regions`` and judges the regions (slides 2..n). The filler keeps the first
    real slide from being taken for a cover."""

    def __init__(self, header: list[str], base_dir: str | Path | None):
        self.header, self.base_dir = header, base_dir
        self.cache: dict[str, tuple[Analysis, list[int]]] = {}

    def run(self, regs: list[list[str]]) -> tuple[Analysis, list[int]]:
        lines = [*self.header, *FILLER]
        offsets = []
        for r in regs:
            lines.append("")
            offsets.append(len(lines))
            lines.extend(r)
        text = "\n".join(lines)
        if text not in self.cache:
            self.cache[text] = (analyze(text, self.base_dir), offsets)
        return self.cache[text]

    def diags(self, regs: list[list[str]]) -> tuple[list[Diagnostic], Analysis, int]:
        ana, offsets = self.run(regs)
        return [d for d in ana.diags if (d.slide or 0) >= 2], ana, offsets[0]

    def key(self, regs: list[list[str]], rules: set[str], *, structural: bool = False) -> _Key:
        ds, ana, _ = self.diags(regs)
        t = sum(1 for d in ds if d.rule in rules)
        if structural:
            t += sum(1 for s in ana.deck.slides[1:] if too_dense(s))
        warns = sum(1 for d in ds if d.level in ("warning", "error"))
        return _Key(t, warns, _penalty(ds))


def _region(lines: list[str]) -> redesign.Region:
    from .parser.core import fence_map

    return redesign.Region(lines, fence_map(lines)[0], 0)


def _inks(ana: Analysis) -> list[str]:
    r = getattr(ana.theme, "render", None)
    return [getattr(r, "ink_dark", "#1F2937"), getattr(r, "ink_light", "#FFFFFF")]


def _fix_region(
    region: redesign.Region, header: list[str], base_dir: str | Path | None, ana: Analysis, idx: int
) -> tuple[list[str], list[Fixed]]:
    """Edits for one slide: long title, declared low-contrast colors, then density (dense / split)."""
    trial = _Trial(header, base_dir)
    cur = list(region.lines)
    fixed: list[Fixed] = []
    where = region.start + 1
    inks = _inks(ana)

    def note(rule: str, what: str) -> None:
        fixed.append(Fixed(where, rule, what))

    # 1. long title -> lead
    ds, _, _ = trial.diags([cur])
    if any(d.rule == "design-long-title" for d in ds):
        base = trial.key([cur], {"design-long-title"})
        for cand in redesign.title_candidates(_region(cur)):
            if trial.key([cand], {"design-long-title"}).better_than(base):
                cur = cand
                note("long-title", "moved the title tail into the `>` lead")
                break
    # 2. contrast on a declared color
    for _ in range(6):
        ds, _, off = trial.diags([cur])
        bad = [d for d in ds if d.rule == "contrast"]
        if not bad:
            break
        base = trial.key([cur], {"contrast"})
        done = False
        for d in bad[:4]:
            rel = (d.line - 1 - off) if d.line else None
            for cand in redesign.contrast_candidates(_region(cur), rel, inks):
                if trial.key([cand], {"contrast"}).better_than(base):
                    cur, done = cand, True
                    note("contrast-color", "swapped a failing declared color for ink_dark/ink_light")
                    break
            if done:
                break
        if not done:
            break
    # 3. density: `dense` when it clears the slide, else the smallest split that does
    ds, ana1, _ = trial.diags([cur])
    by_diag = any(d.rule in DENSITY_RULES for d in ds)
    if by_diag or (len(ana1.deck.slides) > 1 and too_dense(ana1.deck.slides[1])):
        base = trial.key([cur], DENSITY_RULES, structural=True)

        def key(lines: list[str]) -> _Key:
            return trial.key([lines], DENSITY_RULES, structural=True)

        dense = redesign.add_dense(_region(cur))
        if dense is not None and key(dense).targets == 0 and key(dense).better_than(base):
            cur = dense
            note("dense", "added `dense` to the slide's @ line")
        else:
            best: tuple[_Key, str, list[str]] | None = None
            for what, cand in redesign.split_candidates(_region(cur)):
                k = key(cand)
                # a diagnosed overflow / wall of text may trade for a sparse-slide warning; a mere
                # guideline violation (too many boxes / rows) must not add warnings
                if k.targets == 0 and (by_diag or k.warnings <= base.warnings):
                    if best is None or (k.warnings, k.penalty) < (best[0].warnings, best[0].penalty):
                        best = (k, what, cand)
                    if k.warnings <= base.warnings:
                        break
            if best is not None:
                cur = best[2]
                note("split-slide", best[1])
    return cur, fixed


def _fix_pixels(
    region: redesign.Region, ana: Analysis, idx: int, header: list[str]
) -> tuple[list[str], list[Fixed]]:
    """Swap a declared text color on a slide whose rendered pixels give it low contrast."""
    from .lint import contrast_ratio

    cur = list(region.lines)
    fixed: list[Fixed] = []
    ink_d, ink_l = _inks(ana)
    for d in [d for d in ana.diags if d.rule == "pixel-contrast" and d.slide == idx + 1]:
        bg = ana.pixel_bg.get((idx + 1, d.line))
        if bg is None:
            continue
        from .lint import _hex

        best = max((ink_d, ink_l), key=lambda c: contrast_ratio(_hex(c, ana.theme) or (0, 0, 0), bg))  # type: ignore[arg-type]
        rel = (d.line - 1 - region.start) if d.line else None
        for cand in redesign.contrast_candidates(_region(cur), rel, [best]):
            cur = cand
            fixed.append(Fixed(region.start + 1, "pixel-contrast", f"declared color -> {best}"))
            break
    return cur, fixed


# --------------------------------------------------------------------------- driver


@dataclass
class Result:
    text: str
    before: Analysis
    after: Analysis
    fixed: list[Fixed]
    rounds: int

    @property
    def changed(self) -> bool:
        return bool(self.fixed)


def _full(text: str, base_dir: str | Path | None, png_dir: Path | None) -> Analysis:
    ana = analyze(text, base_dir)
    if png_dir is not None and not any(d.level == "error" for d in ana.diags):
        pngs = render_pngs(text, base_dir, png_dir)
        if pngs:
            judged = {(d.slide, d.line) for d in ana.diags if d.rule == "contrast"}
            ana.diags.extend(d for d in pixel_check(ana, pngs) if (d.slide, d.line) not in judged)
            from .critique import review_score

            ana.score = review_score(ana.diags, len(ana.deck.slides))
    return ana


def _progress(a: Analysis, b: Analysis) -> bool:
    """``a`` is better than ``b``: fewer warnings, or the same and a higher score."""
    return (a.fixable + a.dense, a.warnings, -a.score) < (b.fixable + b.dense, b.warnings, -b.score)


def _design_round(
    text: str, ana: Analysis, base_dir: str | Path | None, png_dir: Path | None
) -> tuple[str, list[Fixed]]:
    got = redesign.regions(text)
    if got is None or any(d.level == "error" for d in ana.diags):
        return text, []
    header, regs = got
    if len(regs) != len(ana.deck.slides):
        return text, []  # the source view and the parser disagree: do not touch the design
    lines = redesign.split_lines(text)
    fixed: list[Fixed] = []
    for idx in range(len(regs) - 1, -1, -1):
        reg, slide = regs[idx], ana.deck.slides[idx]
        mine = [d for d in ana.diags if d.slide == idx + 1]
        wanted = (
            any(d.rule in DENSITY_RULES | {"contrast", "design-long-title", "pixel-contrast"} for d in mine)
            or too_dense(slide)
        ) and slide.html is None
        if not wanted:
            continue
        try:
            new, fx = _fix_region(reg, header, base_dir, ana, idx)
            if any(d.rule == "pixel-contrast" for d in mine):
                if not any(f.rule == "split-slide" for f in fx):
                    r2 = _region(new)
                    r2.start = reg.start
                    new, fx2 = _fix_pixels(r2, ana, idx, header)
                    fx = fx + fx2
        except Exception:  # a fixer must never break the review
            continue
        if new != reg.lines:
            lines[reg.start : reg.start + len(reg.lines)] = new
            fixed.extend(fx)
    return "\n".join(lines), fixed[::-1]


def self_review(
    text: str,
    base_dir: str | Path | None = None,
    *,
    png_dir: Path | None = None,
    max_rounds: int = MAX_ROUNDS,
    log: Callable[[str], None] | None = None,
) -> Result:
    """Run the loop on Markdown ``text``; returns the best text found (the input when nothing helps)."""
    eol = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    rendered: list[str] = []

    def full(t: str) -> Analysis:
        rendered[:] = [t]
        return _full(t, base_dir, png_dir)

    before = cur_ana = full(text)
    cur = text
    fixed: list[Fixed] = []
    rounds = 0
    from .parser import parse

    for _ in range(max_rounds):
        step: list[Fixed] = []
        new, mech = fix_text(cur, lambda t: parse(t).diagnostics)
        step += mech
        ana = full(new) if new != cur else cur_ana
        new2, design = _design_round(new, ana, base_dir, png_dir)
        step += design
        if new2 == cur:
            break
        final = full(new2) if new2 != new else ana
        if not _progress(final, cur_ana):
            break
        cur, cur_ana, rounds = new2, final, rounds + 1
        fixed += step
        if log:
            for f in step:
                log(str(f))
        if cur_ana.warnings == 0 and cur_ana.dense == 0:
            break
    if png_dir is not None and rendered and rendered[0] != cur:
        render_pngs(cur, base_dir, png_dir)  # leave the PNGs of the text we return
    return Result(cur.replace("\n", eol) if eol != "\n" else cur, before, cur_ana, fixed, rounds)
