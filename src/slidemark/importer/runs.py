"""Runs of one paragraph that differ in size or colour -> ``[420]{size=28 bold=true color=primary}`` spans.

A foreign deck mixes sizes and colours inside one line (a small label, a big number, a small grey note).
SlideMark states that with a span: ``size=`` is exact pt (never grown or shrunk by the layout), ``bold=``
``italic=`` and ``color=`` (a colour name, ``#RRGGBB``, or the class ``.muted``) ride in the same braces.

``span`` is the one writer: ``emit.inline`` calls it, and any other emitter (a box heading, a table cell,
a KPI value line) can call it for a run it writes itself. ``is_mixed`` says whether a paragraph needs spans
at all, so a uniform paragraph keeps the short ``**bold**`` form.
"""

from __future__ import annotations

from .read import RunT


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


def span(
    body: str,
    r: RunT,
    *,
    pin: bool,
    tint: bool = False,
    names: dict[str, str] | None = None,
    fg: str | None = None,
) -> str | None:
    """``body`` wrapped as ``[body]{...}`` for run ``r``, or ``None`` when the run needs no span.

    ``pin``: the paragraph mixes sizes (``mixed_sizes``), so the run's own size is written (``size=28``).
    ``tint``: it mixes colours (``mixed_colors``), so a run colour that is not the deck text colour ``fg`` is
    written (every coloured run when ``fg`` is unknown). Bold and italic go into the span too (the caller
    then skips ``**``). ``names`` maps ``RRGGBB`` to a colour name."""
    attrs: list[str] = []
    if pin and r.size:
        attrs.append(f"size={r.size:g}")
    color = r.color.lstrip("#").upper() if r.color else None
    if tint and color and color != (fg or "").lstrip("#").upper() and not r.badge:
        tok = color_token(color, names)
        attrs.append(".muted" if tok == "muted" else f"color={tok}")
    if not attrs:
        return None
    if r.bold and not r.badge:
        attrs.insert(1 if attrs and attrs[0].startswith("size=") else 0, "bold=true")
    if r.italic:
        attrs.append("italic=true")
    return f"[{body}]{{{' '.join(attrs)}}}"
