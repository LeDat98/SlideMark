"""Token diet for an imported deck (DL3d, ``docs/AGENT_COST.md``): shorter text, the same slides.

The importer states every size, colour and stripe it reads, and the finished ``deck.md`` of a foreign deck
grew to 46% of the python-pptx script. The writers (``emit``, ``runs``) already skip what a surrounding
element gives; this pass works on the finished text, where the whole deck is visible:

* **colour names**: a ``#RRGGBB`` that the deck uses ``MIN_USES`` times becomes a ``colors:`` name
  (``secondary`` / ``accent`` / ``muted`` when the theme does not already use that role, else a short name
  derived from the hue: ``teal``, ``gray``, ``tint``); white and black are the CSS names; every attribute that
  wrote the hex says the name instead;
* **class form**: ``[x]{color=muted}`` -> ``[x]{.muted}``;
* **derived values**: ``bold`` in a bold heading, white ink on a dark fill, and the layout's own
  ``rows.size`` / ``table_header_color`` ... are left out when the build reproduces them;
* **hoisting**: a ``style:`` token that two or more slides repeat with the same value moves into the deck
  header once (a slide that has another value keeps its own: the first writer still wins).

Nothing is trusted: every edit is applied to the text and a build must give the same slide XML as before
(``signature``). An edit that changes a pixel is bisected out; naming a text colour (a theme name is moved
by the readable-ink rule, a hex is not) falls back to naming only the fills and lines. A deck that does not
build is returned untouched. ``slim`` never raises.
"""

from __future__ import annotations

import colorsys
import hashlib
import re
import tempfile
import zipfile
from collections import Counter
from collections.abc import Callable
from pathlib import Path

MIN_USES = 3  # a hex is named from its third use: `name=#RRGGBB` in the header costs about two uses

_HEX = re.compile(r"#[0-9A-Fa-f]{6}(?![0-9A-Za-z])")
_ATTR = re.compile(r"""([\w.\-]+)=("[^"]*"|'[^']*'|[^\s"'{}]+)""")
_GROUP = re.compile(r"\{([^{}]*)\}")
_TOKEN = re.compile(r'(?:[^\s"]|"[^"]*")+')
_TEXT_KEY = re.compile(r"(^|[._-])color$")
_HEAD_LINE = re.compile(r"(colors|fonts|sizes|style|lang|footer|num|size|density|sections|theme):")
_ROLES_CHROMATIC = ("secondary", "accent")
_ROLES_GRAY = ("muted",)
_RANK = ("primary", "secondary", "accent", "muted", "success", "danger")
_CSS = {"FFFFFF": "white", "000000": "black"}  # CSS names need no `colors:` entry
_DERIVED = (  # style tokens the layout reproduces by itself when the original was drawn the usual way
    "table_header_color",
    "cover.bar_w",
    "rows.size",
    "conclusion.size",
)
_LATE = ("quote.mark.color",)  # derived from a colour name the deck declares (`accent`)
_BASE = ("bg", "fg", "surface", "border", "muted")  # theme names the readable-ink rule never moves
_GONE = "\x00"  # a line an in-place edit emptied (removed once the step is done)

Edit = Callable[[str], str]
TRACE: list | None = None  # debugging: (groups tried, accepted, edit names) per build of `_bisect`


# --------------------------------------------------------------------------- the build check


_CLR = re.compile(rb'(srgbClr val=")([0-9A-Fa-f]{6})(")')
# what the viewer sees: slides, charts, notes, layouts and masters (the theme part only lists the palette)
_DRAWN = re.compile(r"ppt/(slides|charts|notesSlides|slideLayouts|slideMasters)/[^/]+\.(xml|rels)")
_NEAR = 3  # a colour that moves by up to 3/255 per channel is the same colour to the eye


def signature(text: str, base_dir: str | Path | None = None) -> tuple[str, list[int]] | None:
    """What a build of ``text`` draws: (hash of the slide, chart, notes, layout and master XML with the
    colour values taken out, the colour values in order); None when the build fails."""
    try:
        from ..build import build

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "d.pptx"
            build(text, out, base_dir=base_dir or tmp)
            h = hashlib.sha1()
            colours: list[int] = []
            with zipfile.ZipFile(out) as z:
                for name in sorted(z.namelist()):
                    if _DRAWN.match(name):
                        raw = re.sub(rb"\{[0-9A-F-]{36}\}", b"{G}", z.read(name))
                        colours += [int(m.group(2), 16) for m in _CLR.finditer(raw)]
                        h.update(name.encode())
                        h.update(_CLR.sub(rb"\1\3", raw))
            return h.hexdigest(), colours
    except Exception:
        return None


def _near(a: int, b: int) -> bool:
    return all(abs(((a >> k) & 255) - ((b >> k) & 255)) <= _NEAR for k in (0, 8, 16))


def _same(a, b) -> bool:
    """Two signatures draw the same slides (colours within ``_NEAR`` of each other)."""
    return (
        a is not None
        and b is not None
        and a[0] == b[0]
        and len(a[1]) == len(b[1])
        and all(_near(x, y) for x, y in zip(a[1], b[1], strict=True))
    )


def same_slides(a: str, b: str, base_dir: str | Path | None = None) -> bool:
    """True when two decks build to the same slide XML (the test helper: remove a token, rebuild, compare)."""
    return _same(signature(a, base_dir), signature(b, base_dir))


def _clean(text: str) -> str:
    return "\n".join(ln for ln in text.split("\n") if ln != _GONE) if _GONE in text else text


def _bisect(text: str, groups: list[list[Edit]], ok: Callable[[str, str], bool]) -> str:
    """Apply the edit groups that keep ``ok(before, after)`` true. A group is a list of alternatives, best
    first."""
    if not groups:
        return text
    cand = text
    for g in groups:
        cand = g[0](cand)
    if cand == text:
        return text
    good = ok(_clean(text), _clean(cand))
    if TRACE is not None:
        TRACE.append((len(groups), good, [g[0].__doc__ for g in groups]))
    if good:
        return cand
    if len(groups) == 1:
        return _bisect(text, [groups[0][1:]], ok) if len(groups[0]) > 1 else text
    mid = len(groups) // 2
    return _bisect(_bisect(text, groups[:mid], ok), groups[mid:], ok)


def _split(text: str) -> tuple[str, list[str]]:
    """(header, one text per slide) of a deck."""
    lines = text.split("\n")
    body = _fence_body(lines)
    end = _head_end(lines, body)
    slides: list[list[str]] = []
    for i in range(end, len(lines)):
        if lines[i].startswith("# ") and not body[i]:
            slides.append([])
        slides[-1].append(lines[i])
    return "\n".join(lines[:end]), ["\n".join(s) for s in slides]


class Checker:
    """Says whether an edit left the slides as they were. The deck as first read is the truth; an edit that
    only touches some slides is judged on those slides built alone (a tenth of a deck build each), anything
    else on the whole deck."""

    def __init__(self, text: str, base_dir: str | Path | None = None):
        self.base_dir = base_dir
        self.cache: dict[str, tuple[str, list[int]] | None] = {}
        self.base = self.sig(text)

    def sig(self, text: str):
        if text not in self.cache:
            self.cache[text] = signature(text, self.base_dir)
        return self.cache[text]

    def whole(self, text: str) -> bool:
        return _same(self.sig(text), self.base)

    def ok(self, before: str, after: str) -> bool:
        hb, sb = _split(before)
        ha, sa = _split(after)
        if hb != ha or len(sb) != len(sa):
            return self.whole(after)
        return all(
            _same(self.sig(ha + "\n" + a), self.sig(hb + "\n" + b))
            for a, b in zip(sa, sb, strict=True)
            if a != b
        )


# --------------------------------------------------------------------------- reading the text


def _fence_body(lines: list[str]) -> list[bool]:
    """True for the lines inside a fenced block (the fence lines themselves are not body)."""
    out, inside = [], False
    for ln in lines:
        if ln.startswith(("```", "~~~")):
            inside = not inside
            out.append(False)
        else:
            out.append(inside)
    return out


def _head_end(lines: list[str], body: list[bool]) -> int:
    """Index of the first slide heading (the header is everything before it)."""
    return next((i for i, ln in enumerate(lines) if ln.startswith("# ") and not body[i]), len(lines))


def _regions(line: str) -> list[tuple[int, int]]:
    """Where a line states attributes: a ``style:`` / ``sizes:`` / ``@`` line, or its ``{...}`` groups."""
    for head in ("style:", "sizes:"):
        if line.startswith(head + " "):
            return [(len(head), len(line))]
    if line.startswith(("colors:", "fonts:")):
        return []
    if line.startswith("@"):
        return [(1, len(line))]
    return [(m.start(1), m.end(1)) for m in _GROUP.finditer(line)]


def _map_values(line: str, fn: Callable[[str, str], str]) -> str:
    """``line`` with every attribute value ``v`` of key ``k`` replaced by ``fn(k, v)``."""
    out, pos = [], 0
    for a, b in _regions(line):
        out.append(line[pos:a])
        out.append(_ATTR.sub(lambda m: f"{m.group(1)}={fn(m.group(1), m.group(2))}", line[a:b]))
        pos = b
    out.append(line[pos:])
    return "".join(out)


def _declared(lines: list[str]) -> dict[str, str]:
    """name -> RRGGBB of the header's ``colors:`` lines."""
    got: dict[str, str] = {}
    for ln in lines:
        if ln.startswith("colors: "):
            for k, v in _ATTR.findall(ln[len("colors:") :]):
                if _HEX.fullmatch(v):
                    got[k] = v.lstrip("#").upper()
    return got


def _declare(text: str, name: str, hexv: str) -> str:
    """``name=#RRGGBB`` on the header's ``colors:`` line (a new first line when there is none)."""
    lines = text.split("\n")
    end = _head_end(lines, _fence_body(lines))
    entry = f"{name}=#{hexv}"
    for i in range(end):
        if lines[i].startswith("colors: "):
            if name in _declared([lines[i]]):
                return text
            lines[i] += " " + entry
            return "\n".join(lines)
    return "\n".join([f"colors: {entry}", *([""] if end == 0 else []), *lines])


def _line_edit(edits: dict[int, Callable[[str], str]], doc: str) -> Edit:
    """An edit that rewrites the given lines in place (a line is never added or removed here)."""

    def edit(text: str) -> str:
        lines = text.split("\n")
        for i, fn in edits.items():
            if i < len(lines):
                lines[i] = fn(lines[i])
        return "\n".join(lines)

    edit.__doc__ = doc
    return edit


# --------------------------------------------------------------------------- colour names


def _hsv(hexv: str) -> tuple[float, float, float]:
    r, g, b = (int(hexv[i : i + 2], 16) / 255 for i in (0, 2, 4))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s, v


_HUES = (
    (15, "red"),
    (40, "orange"),
    (52, "amber"),
    (70, "yellow"),
    (100, "lime"),
    (160, "green"),
    (190, "teal"),
    (205, "cyan"),
    (255, "blue"),
    (275, "indigo"),
    (310, "purple"),
    (345, "pink"),
)


def derive_name(hexv: str) -> str:
    """A short colour word for ``RRGGBB`` (``teal``, ``navy``, ``gray``, ``tint``), unique via the caller."""
    h, s, v = _hsv(hexv)
    if s < 0.2:
        return "tint" if v > 0.85 else "gray" if v > 0.3 else "ink"
    if v > 0.9 and s < 0.3:
        return "tint"
    word = next((w for lim, w in _HUES if h < lim), "red")
    return "navy" if word == "blue" and v < 0.45 else word


def _is_text_key(key: str) -> bool:
    return bool(_TEXT_KEY.search(key))


def _name_edit(hexv: str, name: str, text_too: bool, declare: bool = True) -> Edit:
    """Say ``name`` where an attribute wrote ``#hexv`` (colour-text attributes only when ``text_too``)."""

    def sub(key: str, val: str) -> str:
        if not text_too and _is_text_key(key):
            return val
        return _HEX.sub(lambda m: name if m.group(0)[1:].upper() == hexv else m.group(0), val)

    def edit(text: str) -> str:
        lines = text.split("\n")
        body = _fence_body(lines)
        out = "\n".join(ln if body[i] else _map_values(ln, sub) for i, ln in enumerate(lines))
        return _declare(out, name, hexv) if declare else out

    edit.__doc__ = f"{hexv}->{name}{'' if text_too else ' (no text)'}"
    return edit


def _theme_names() -> set[str]:
    try:
        from ..parser.css import known_color_names

        return set(known_color_names(None))
    except Exception:
        return set(_RANK) | {"bg", "fg", "surface", "border"}


def _uses_name(lines: list[str], body: list[bool], name: str) -> bool:
    """The deck's attributes (or ``==`` marks, for ``accent``) already rely on the theme's ``name``."""
    pat = re.compile(rf"(?<![\w-]){re.escape(name)}(?![\w-])")
    for i, ln in enumerate(lines):
        if body[i]:
            continue
        if name == "accent" and "==" in ln:
            return True
        if any(pat.search(ln[a:b]) for a, b in _regions(ln)):
            return True
    return False


def _text_safe(hexv: str, bg: str = "FFFFFF", surface: str = "F3F4F6") -> bool:
    """A theme name is moved by the readable-ink rule unless it reads on the page: 4.5:1 on bg and surface."""
    from ..contrast import ratio

    return min(ratio("#" + hexv, "#" + bg), ratio("#" + hexv, "#" + surface)) >= 4.5


def _near_default(role: str, hexv: str, header: list[str]) -> bool:
    """The deck uses the theme's ``role`` as it is, but the neutral default is the same colour as ``hexv`` to
    the eye: the deck may declare it (no ``theme:`` line, so the neutral palette is the base)."""
    if any(ln.startswith("theme:") for ln in header):
        return False
    try:
        from ..theme import NEUTRAL_COLORS

        return _near(int(NEUTRAL_COLORS[role].lstrip("#"), 16), int(hexv, 16))
    except (KeyError, ValueError):
        return False


def _alts(hexv: str, name: str, safe: bool, declare: bool = True) -> list[Edit]:
    nontext = _name_edit(hexv, name, False, declare)
    return [_name_edit(hexv, name, True, declare), nontext] if safe else [nontext]


def _color_groups(text: str) -> list[list[Edit]]:
    lines = text.split("\n")
    body = _fence_body(lines)
    end = _head_end(lines, body)
    declared = _declared(lines[:end])
    bg, surface = declared.get("bg", "FFFFFF"), declared.get("surface", "F3F4F6")
    by_hex: dict[str, str] = {}
    for name in sorted(declared, key=lambda n: _RANK.index(n) if n in _RANK else len(_RANK)):
        by_hex.setdefault(declared[name], name)
    count: Counter[str] = Counter()
    for i, ln in enumerate(lines):
        if body[i]:
            continue
        for a, b in _regions(ln):
            count.update(h[1:].upper() for h in _HEX.findall(ln[a:b]))
    groups: list[list[Edit]] = []
    for hexv, css in _CSS.items():
        if count[hexv] and hexv not in by_hex:
            groups.append(_alts(hexv, css, True, declare=False))
    for hexv, name in by_hex.items():
        if count[hexv]:
            groups.append(_alts(hexv, name, name in _BASE or _text_safe(hexv, bg, surface)))
    known = _theme_names()
    taken = set(declared) | {n for n in known if _uses_name(lines, body, n)}
    for hexv, n in count.most_common():
        if hexv in by_hex or hexv in _CSS or n < MIN_USES:
            continue
        _h, sat, val = _hsv(hexv)
        roles = _ROLES_GRAY if sat < 0.2 and 0.3 < val < 0.9 else _ROLES_CHROMATIC if sat >= 0.2 else ()
        derived, k = derive_name(hexv), 2
        while derived in taken or derived in known:
            derived, k = f"{derive_name(hexv)}{k}", k + 1
        role = next((r for r in roles if r not in taken or _near_default(r, hexv, lines[:end])), None)
        safe = role in _BASE or _text_safe(hexv, bg, surface)
        alts = _alts(hexv, role, safe) if role else []
        alts += _alts(hexv, derived, safe)
        groups.append(alts)
        taken.add(role or derived)
    return groups


# --------------------------------------------------------------------------- class form of a span colour


def _class_edit(name: str) -> Edit:
    """``[x]{size=26 color=muted}`` -> ``[x]{size=26 .muted}`` (a span only: a box keeps ``color=``)."""
    pat = re.compile(rf"(?<![\w.-])color={re.escape(name)}(?![\w-])")

    def one(ln: str) -> str:
        return _GROUP.sub(
            lambda m: (
                "{" + pat.sub("." + name, m.group(1)) + "}"
                if m.start() > 0 and ln[m.start() - 1] == "]"
                else m.group(0)
            ),
            ln,
        )

    def edit(text: str) -> str:
        lines = text.split("\n")
        body = _fence_body(lines)
        return "\n".join(one(ln) if "]{" in ln and not body[i] else ln for i, ln in enumerate(lines))

    edit.__doc__ = f"color={name} -> .{name}"
    return edit


def _class_groups(text: str) -> list[list[Edit]]:
    names = sorted(set(re.findall(r"\]\{[^{}]*?color=([A-Za-z][\w-]*)", text)))
    return [[_class_edit(n)] for n in names]


# --------------------------------------------------------------------------- values the build derives


def _drop_span_tokens(ln: str, drop: Callable[[str], bool]) -> str:
    """``ln`` without the span attributes ``drop`` names; a span left empty is unwrapped."""

    def fix(m: re.Match[str]) -> str:
        toks = [t for t in _TOKEN.findall(m.group(2)) if not drop(t)]
        if len(toks) == len(_TOKEN.findall(m.group(2))):
            return m.group(0)
        return f"[{m.group(1)}]{{{' '.join(toks)}}}" if toks else m.group(1)

    return re.sub(r"\[((?:[^\[\]\\]|\\.|\[[^\[\]]*\])*)\]\{([^{}]*)\}", fix, ln)


def _drop_box_tokens(ln: str, drop: Callable[[str], bool]) -> str:
    """``ln`` without the box attributes ``drop`` names (the trailing ``{...}`` of a heading)."""
    m = re.search(r"\s\{([^{}]*)\}$", ln)
    if not m:
        return ln
    toks = _TOKEN.findall(m.group(1))
    keep = [t for t in toks if not drop(t)]
    if len(keep) == len(toks):
        return ln
    return ln[: m.start()] + (f" {{{' '.join(keep)}}}" if keep else "")


def _is_white(tok: str) -> bool:
    return tok.lower() in ("color=white", "color=#ffffff")


def _boxes(lines: list[str], body: list[bool]) -> list[list[int]]:
    """Line indexes of every box: its ``##`` heading and the lines under it up to the next heading."""
    out: list[list[int]] = []
    cur: list[int] = []
    for i, ln in enumerate(lines):
        if body[i]:
            if cur:
                cur.append(i)
            continue
        if ln.startswith(("# ", "## ", "### ", "@")):
            if cur:
                out.append(cur)
            cur = [i] if ln.startswith(("## ", "### ")) else []
        elif cur:
            cur.append(i)
    if cur:
        out.append(cur)
    return out


def _white_on_fill(heading: str, declared: dict[str, str]) -> bool:
    """The box states a fill that white reads on (the readable-ink rule then picks white by itself)."""
    from ..contrast import ratio

    m = re.search(r"(?<![\w.-])fill=([^\s}]+)", heading)
    if not m:
        return False
    v = m.group(1).strip("\"'")
    hexv = v.lstrip("#").upper() if _HEX.fullmatch(v) else declared.get(v)
    return bool(hexv) and ratio("#FFFFFF", "#" + hexv) >= 4.5


def _derived_groups(text: str) -> list[list[Edit]]:
    lines = text.split("\n")
    body = _fence_body(lines)
    groups: list[list[Edit]] = []
    # `bold` inside a heading: the heading is bold already
    edits = {
        i: (lambda ln: _drop_span_tokens(ln, lambda t: t in ("bold", "bold=true")))
        for i, ln in enumerate(lines)
        if ln.startswith(("## ", "### ")) and not body[i] and re.search(r"\]\{[^{}]*\bbold\b", ln)
    }
    groups += [[_line_edit({i: fn}, "bold in heading")] for i, fn in edits.items()]
    # white ink on a filled box: the readable-ink rule gives it
    declared = _declared(lines[: _head_end(lines, body)])
    for box in _boxes(lines, body):
        if not _white_on_fill(lines[box[0]], declared):
            continue
        for i in box:
            if not body[i] and "color=" in lines[i].lower():
                fix = lambda ln: _drop_box_tokens(_drop_span_tokens(ln, _is_white), _is_white)  # noqa: E731
                groups.append([_line_edit({i: fix}, "white ink on fill")])
    return groups + _style_drops(lines, body, _DERIVED)


def _is_size(tok: str) -> bool:
    return tok.startswith("size=")


def _last_span(ln: str, drop: Callable[[str], bool]) -> str:
    """``ln`` with the attributes ``drop`` names removed from its last span only."""
    ms = list(re.finditer(r"\]\{([^{}]*)\}", ln))
    if not ms:
        return ln
    m = ms[-1]
    toks = [t for t in _TOKEN.findall(m.group(1)) if not drop(t)]
    if len(toks) == len(_TOKEN.findall(m.group(1))):
        return ln
    return ln[: m.start()] + ("]{" + " ".join(toks) + "}" if toks else "]") + ln[m.end() :]


def _note_groups(text: str) -> list[list[Edit]]:
    """The size of a note the layout scales by itself: the last span of a ``@rows`` bar, the last line of a
    ``.kpi`` card (drawn smaller than the figure above it)."""
    lines = text.split("\n")
    body = _fence_body(lines)
    groups: list[list[Edit]] = []
    in_rows = False
    for i, ln in enumerate(lines):
        if body[i]:
            continue
        if ln.startswith("# "):
            in_rows = False
        elif ln.startswith("@"):
            in_rows = in_rows or "rows" in ln[1:].split()
        elif in_rows and re.match(r"(- |\d+\. )", ln) and ln.count("]{") >= 2:
            groups.append([_line_edit({i: lambda s: _last_span(s, _is_size)}, "note size in a bar")])
    for box in _boxes(lines, body):
        if ".kpi" not in lines[box[0]]:
            continue
        last = [i for i in box[1:] if lines[i].strip() and not body[i]]
        if last and lines[last[-1]].startswith("[") and "]{" in lines[last[-1]]:
            groups.append([_line_edit({last[-1]: lambda s: _last_span(s, _is_size)}, "note size in a card")])
    return groups


def _late_groups(text: str) -> list[list[Edit]]:
    """Tokens that are redundant only once the colours have their names (``quote.mark.color=accent``)."""
    lines = text.split("\n")
    return _style_drops(lines, _fence_body(lines), _LATE)


def _style_drops(lines: list[str], body: list[bool], keys: tuple[str, ...]) -> list[list[Edit]]:
    """One group per ``style:`` token whose key the build derives by itself."""
    groups: list[list[Edit]] = []
    for i, ln in enumerate(lines):
        if body[i] or not ln.startswith("style: "):
            continue
        for tok in _TOKEN.findall(ln[len("style:") :]):
            if tok.split("=", 1)[0] in keys:
                groups.append([_line_edit({i: lambda s, tok=tok: _drop_style_token(s, tok)}, f"drop {tok}")])
    return groups


def _drop_style_token(ln: str, tok: str) -> str:
    toks = _TOKEN.findall(ln[len("style:") :])
    if tok not in toks:
        return ln
    toks.remove(tok)
    return "style: " + " ".join(toks) if toks else _GONE


# --------------------------------------------------------------------------- one class, one border side

_BORDER = re.compile(r"([\w-]+)\.border-(top|left|right|bottom)=")


def _border_sides(lines: list[str], body: list[bool], end: int) -> dict[str, dict[int, set[str]]]:
    """class -> slide -> the border sides that slide's ``style:`` line gives it."""
    sides: dict[str, dict[int, set[str]]] = {}
    slide = 0
    for i in range(end, len(lines)):
        if body[i]:
            continue
        if lines[i].startswith("# "):
            slide += 1
        if lines[i].startswith("style: "):
            for tok in _TOKEN.findall(lines[i][len("style:") :]):
                m = _BORDER.match(tok)
                if m:
                    sides.setdefault(m.group(1), {}).setdefault(slide, set()).add(m.group(2))
    return sides


def _rename_plan(text: str) -> dict[tuple[int, str], str]:
    """(slide, class) -> new class name, for a class drawn with different border sides on different slides."""
    lines = text.split("\n")
    body = _fence_body(lines)
    sides = _border_sides(lines, body, _head_end(lines, body))
    used = set(re.findall(r"(?<![\w.-])\.([A-Za-z][\w-]*)", text))
    plan: dict[tuple[int, str], str] = {}
    for cls, per in sides.items():
        count = Counter(side for ss in per.values() for side in ss)
        if len(count) < 2 or any(len(ss) > 1 for ss in per.values()):
            continue
        keep = max(count, key=lambda k: count[k])
        names: dict[str, str] = {}
        for sl, ss in per.items():
            (side,) = ss
            if side != keep:
                if side not in names:
                    new = side[0] + cls
                    while new in used or new in sides:
                        new += "x"
                    used.add(new)
                    names[side] = new
                plan[(sl, cls)] = names[side]
    return plan


def _rename_groups(text: str) -> list[list[Edit]]:
    """A card class that one slide draws with a top border and another with a left one (``s1``) is two
    classes: the side that fewer slides use gets its own name (``ls1``), so each side can be hoisted."""
    plan = _rename_plan(text)
    if not plan:
        return []

    def one(ln: str, cls: str, new: str, style: bool) -> str:
        if style:
            return re.sub(rf"(?<![\w.-]){re.escape(cls)}\.", new + ".", ln)
        pat = re.compile(rf"(?<![\w.=-])\.{re.escape(cls)}(?![\w-])")
        return _GROUP.sub(lambda m: "{" + pat.sub("." + new, m.group(1)) + "}", ln)

    def edit(text: str) -> str:
        lines = text.split("\n")
        body = _fence_body(lines)
        slide = 0
        for i, ln in enumerate(lines):
            if body[i]:
                continue
            if ln.startswith("# "):
                slide += 1
            for (sl, cls), new in plan.items():
                if sl == slide:
                    lines[i] = ln = one(ln, cls, new, ln.startswith("style: "))
        return "\n".join(lines)

    edit.__doc__ = "rename border classes"
    return [[edit]]


# --------------------------------------------------------------------------- hoisting slide style tokens


def _header_slot(lines: list[str], end: int) -> int:
    """Where a new header line goes: after the last header token line (before a css fence)."""
    last = -1
    for i in range(end):
        if _HEAD_LINE.match(lines[i]):
            last = i
    return last + 1


def _hoist_edit(head: str, tok: str) -> Edit:
    key = tok.split("=", 1)[0]

    def edit(text: str) -> str:
        lines = text.split("\n")
        body = _fence_body(lines)
        end = _head_end(lines, body)
        for i in range(end):  # the header already states the key: nothing to hoist
            if lines[i].startswith(head + " ") and any(
                t.split("=", 1)[0] == key for t in _TOKEN.findall(lines[i][len(head) :])
            ):
                return text
        out = lines[:end]
        for i in range(end, len(lines)):
            ln = lines[i]
            if not body[i] and ln.startswith(head + " "):
                toks = _TOKEN.findall(ln[len(head) :])
                if tok in toks:
                    toks.remove(tok)
                    if not toks:
                        continue
                    ln = head + " " + " ".join(toks)
            out.append(ln)
        for i in range(end):
            if out[i].startswith(head + " "):
                out[i] += " " + tok
                return "\n".join(out)
        out.insert(_header_slot(out, end), f"{head} {tok}")
        if end == 0:  # (a deck with no header yet: the header needs its blank line)
            out.insert(1, "")
        return "\n".join(out)

    edit.__doc__ = f"hoist {tok}"
    return edit


def _hoist_groups(text: str) -> list[list[Edit]]:
    lines = text.split("\n")
    body = _fence_body(lines)
    end = _head_end(lines, body)
    seen: dict[tuple[str, str], set[int]] = {}
    keys: dict[str, set[int]] = {}  # key -> slides stating it
    classes: dict[str, set[int]] = {}  # class (first dotted segment of a key) -> slides using it
    slide = 0
    for i in range(end, len(lines)):
        ln = lines[i]
        if body[i]:
            continue
        if ln.startswith("# "):
            slide += 1
        for head in ("style:", "sizes:"):
            if ln.startswith(head + " "):
                for tok in _TOKEN.findall(ln[len(head) :]):
                    key = tok.split("=", 1)[0]
                    seen.setdefault((head, tok), set()).add(slide)
                    keys.setdefault(key, set()).add(slide)
                    classes.setdefault(key.split(".", 1)[0], set()).add(slide)
    out = []
    for (head, tok), at in seen.items():
        key = tok.split("=", 1)[0]
        # a slide that styles the same class but not this key would inherit it from the header: skip
        if len(at) >= 2 and classes[key.split(".", 1)[0]] <= keys[key]:
            out.append([_hoist_edit(head, tok)])
    return out


# --------------------------------------------------------------------------- driver

STEPS = (
    _derived_groups,
    _note_groups,
    _color_groups,
    _late_groups,
    _class_groups,
    _rename_groups,
    _hoist_groups,
)


def slim(text: str, base_dir: str | Path | None = None, *, verify: bool = True) -> str:
    """``text`` with the colour names, class forms and hoisted tokens that keep every slide identical.

    ``verify=False`` applies every edit without building (the unit tests of single edits use it)."""
    try:
        chk = Checker(text, base_dir) if verify else None
        if chk is not None and chk.base is None:
            return text
        ok: Callable[[str, str], bool] = chk.ok if chk is not None else (lambda a, b: True)
        for step in STEPS:
            after = _clean(_bisect(text, step(text), ok))
            if (
                chk is None or after == text or chk.whole(after)
            ):  # (slides built alone miss cross-slide effects)
                text = after
        return text
    except Exception:
        return text
