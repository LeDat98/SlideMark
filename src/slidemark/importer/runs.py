"""What the foreign-deck recognisers and the emitter share (``recognise`` forms, ``recognise2`` design,
``emit.inline``).

* **the guard**: ``is_slidemark_deck`` is computed once per deck (``DeckInfo.foreign``); neither recogniser
  looks at shape names slide by slide any more;
* **ownership**: ``claim`` / ``free``. A shape belongs to the first recogniser that claims it (``Item.rec``);
  the other one skips it. Order in ``build_slide``: ``recognise2`` (chrome, background, steps, takeaway bar,
  tables, charts, chart panel) first, then ``recognise`` (quote, badges, panel, tiles, bars, dark cards);
* **spans**: ``put_span`` / ``span_runs`` set ``RunT.span`` and ``wrap_span`` is the ONE function that writes
  ``[text]{...}``, so a run is wrapped once, bold is stated once (``**x**`` inside, or ``bold=true`` in the
  span when the policy asks) and a span that carries a colour replaces the colour markup. A recogniser sets
  the span while it reads shapes; ``emit.inline`` adds what a paragraph that mixes sizes or colours needs
  (``mixed_sizes`` / ``mixed_colors`` / ``mixed_block`` / ``block_colors`` decide, ``with_span`` / ``span``
  write the tokens through ``put_span``); a key a recogniser already set is never written twice;
* **style lines**: ``merge_lines`` joins every ``style:`` (and ``sizes:``) line of a slide into one, the first
  writer of a key wins.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import replace

from .read import RunT

# shape names only SlideMark's own renderer gives (`Card 3`, `Text 5`, `Title`, `band`, `KPI value` ...)
OWN_NAME = re.compile(
    r"(Title|Subtitle|Lead|Footer|Slide Number|Conclusion|Footnote|band(?: .*)?|[Rr]ule|Background"
    r"|KPI (?:value|caption)|icon \S+"
    r"|(Card|Text|Heading|Shape|Step|Row|Item|KPI|Num|Pill|Rows|Code|Callout)( \d+.*)?)"
)


def is_slidemark_deck(datas) -> bool:
    """True when a shape carries a name only SlideMark's own renderer gives: the deck was built by SlideMark,
    even if it has no design part to say so. Computed once per deck (``DeckInfo.foreign``)."""
    return any(OWN_NAME.fullmatch((it.name or "").strip()) for sd in datas for it in sd.items)


def is_foreign(deck) -> bool:
    """The one guard both recognisers use: no design part and no SlideMark shape names in the deck."""
    return bool(getattr(deck, "foreign", False))


# --------------------------------------------------------------------------- ownership


def claim(it, rec: str, role: str | None = None) -> None:
    """Mark ``it`` as read by a recogniser (``rec``: the form); ``role`` keeps it out of title detection."""
    it.rec = rec
    if role is not None:
        it.role = role


def free(it) -> bool:
    """No recogniser owns ``it`` and it has no role yet."""
    return not it.rec and it.role is None


# --------------------------------------------------------------------------- spans


def _keys(span: str) -> set[str]:
    return {t.split("=", 1)[0] for t in span.split()}


def span_has(r, key: str) -> bool:
    """The run's span states ``key`` (``color`` also when a colour class such as ``.muted`` does)."""
    keys = _keys(r.span)
    return key in keys or (key == "color" and any(k.startswith(".") for k in keys))


def put_span(r, parts: Iterable[str], bold: bool = False) -> None:
    """Add ``size=34`` / ``color=#RRGGBB`` tokens to the run's span (a key already there is kept). ``bold``:
    the span says ``bold=true`` itself when the run is bold; otherwise the run keeps its ``**`` markup."""
    have = _keys(r.span)
    new = [p for p in parts if p and p.split("=", 1)[0] not in have]
    if new and bold and r.bold and "bold" not in have:
        new.append("bold=true")
    if new:
        r.span = " ".join([*([r.span] if r.span else []), *new])


def span_runs(
    paras,
    *,
    size_off: Callable[[object], bool],
    color_of: Callable[[object], str | None],
    bold: bool = False,
    multi_only: bool = False,
) -> None:
    """Give every text run that differs from its surroundings a span. ``size_off(run)`` says the size is
    stated, ``color_of(run)`` is the colour text (``#E08A1E`` or a token name) or None; ``multi_only`` leaves
    a text of a single run alone (a heading, a lone number)."""
    runs = [r for p in paras for r in p.runs if r.text.strip()]
    if not runs or (multi_only and len(runs) < 2):
        return
    for r in runs:
        parts = []
        if r.size and size_off(r):
            parts.append(f"size={r.size:g}")
        if (c := color_of(r)) is not None:
            parts.append(f"color={c}")
        put_span(r, parts, bold=bold)


def wrap_span(body: str, r) -> str:
    """``[body]{size=26 color=#E08A1E}`` for a run with a span (code runs never get one)."""
    return f"[{body}]{{{r.span}}}" if r.span and not r.code else body


# --------------------------------------------------------------------------- mixed paragraphs (emit.inline)


def mixed_sizes(runs: list[RunT]) -> bool:
    """True when the runs with text carry two or more different sizes (an unsized run counts as one)."""
    seen = {r.size for r in runs if r.text.strip()}
    return len(seen) > 1 and any(s is not None for s in seen)


def mixed_block(paras: list) -> bool:
    """True when the paragraphs of one text block are drawn at clearly different sizes (a 32pt price over a
    12pt note, each on its own line): every paragraph then pins its size, or the rebuilt lines would all take
    the box's one size. Sizes within 15% of each other (bullets of one list) do not count."""
    got = [p.size for p in paras if p.size and any(r.text.strip() for r in p.runs)]
    return len(got) >= 2 and max(got) >= 1.15 * min(got)


def block_colors(paras: list, prefer: str | None = None) -> tuple[bool | None, str | None]:
    """(``tint``, base colour) of a text block: when its paragraphs differ in colour (a white price over an
    amber one on a dark panel) the colour of most of the text is the block's own and is not written; ``None``
    (decide per paragraph) when the block has one colour or none. ``prefer`` (the deck text colour) is the
    base when the block uses it."""
    count: dict[str, int] = {}
    for p in paras:
        for r in p.runs:
            if r.text.strip() and r.color and not r.badge:
                count[r.color.upper()] = count.get(r.color.upper(), 0) + len(r.text.strip())
    if len(count) < 2:
        return None, None
    base = (prefer or "").lstrip("#").upper()
    return True, base if base in count else max(count, key=lambda k: count[k])


def mixed_colors(runs: list[RunT]) -> bool:
    """True when the runs with text (badges aside) carry two or more different colours."""
    seen = {(r.color or "").upper() for r in runs if r.text.strip() and not r.badge}
    return len(seen) > 1


def color_token(color: str, names: dict[str, str] | None = None) -> str:
    """``primary`` for a colour the deck names, else ``#RRGGBB``."""
    hexv = color.lstrip("#").upper()
    name = (names or {}).get(hexv)
    return name if name else f"#{hexv}"


def with_span(
    r: RunT,
    *,
    pin: bool,
    tint: bool = False,
    names: dict[str, str] | None = None,
    fg: str | None = None,
    bold: bool | None = None,
) -> RunT:
    """A copy of ``r`` whose span also states what its paragraph mixes (or ``r`` itself when nothing is to be
    said). ``pin``: the paragraph mixes sizes (``mixed_sizes``), so the run's own size is written
    (``size=28``). ``tint``: it mixes colours (``mixed_colors``), so a run colour that is not the deck text
    colour ``fg`` is written (every coloured run when ``fg`` is unknown); ``names`` maps ``RRGGBB`` to a
    colour name. Bold and italic ride in the span (``bold`` overrides ``r.bold``, e.g. False when the theme
    already makes the text bold), so the caller skips ``**`` / ``*``. Keys the run's span already has are
    kept, never repeated (``put_span``)."""
    size = f"size={r.size:g}" if pin and r.size else None
    colour = None
    color = r.color.lstrip("#").upper() if r.color else None
    if (
        tint
        and color
        and color != (fg or "").lstrip("#").upper()
        and not r.badge
        and not span_has(r, "color")
    ):
        tok = color_token(color, names)
        colour = ".muted" if tok == "muted" else f"color={tok}"
    if size is None and colour is None:
        return r
    parts = [size, "bold=true" if (r.bold if bold is None else bold) and not r.badge else None, colour]
    if r.italic:
        parts.append("italic=true")
    out = replace(r)
    put_span(out, [x for x in parts if x])
    return out


def span(
    body: str,
    r: RunT,
    *,
    pin: bool,
    tint: bool = False,
    names: dict[str, str] | None = None,
    fg: str | None = None,
) -> str | None:
    """``body`` wrapped as ``[body]{...}`` for run ``r`` (through ``wrap_span``), or ``None`` when the run
    needs no span. The one-call form of ``with_span`` for an emitter that writes a run itself."""
    out = with_span(r, pin=pin, tint=tint, names=names, fg=fg)
    return wrap_span(body, out) if out is not r else None


# --------------------------------------------------------------------------- slide ``style:`` lines

_TOKEN = re.compile(r'(?:[^\s"]|"[^"]*")+')
_MERGED = ("style:", "sizes:")


def merge_lines(lines: list[str | None]) -> list[str]:
    """One ``style:`` line and one ``sizes:`` line per slide: tokens of every writer, the first writer of a
    key keeps it. Other lines stay as they are; a merged line sits where its first line was."""
    out: list[str] = []
    slot: dict[str, int] = {}
    seen: dict[str, set[str]] = {}
    for ln in lines:
        if ln is None:
            continue
        head = next((h for h in _MERGED if ln.startswith(h + " ")), None)
        if head is None:
            out.append(ln)
            continue
        have = seen.setdefault(head, set())
        toks = [t for t in _TOKEN.findall(ln[len(head) :]) if t.split("=", 1)[0] not in have]
        have.update(t.split("=", 1)[0] for t in toks)
        if not toks:
            continue
        if head in slot:
            out[slot[head]] += " " + " ".join(toks)
        else:
            slot[head] = len(out)
            out.append(head + " " + " ".join(toks))
    return out
