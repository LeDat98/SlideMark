"""What the two foreign-deck recognisers share (``recognise`` forms, ``recognise2`` design).

* **the guard**: ``is_slidemark_deck`` is computed once per deck (``DeckInfo.foreign``); neither recogniser
  looks at shape names slide by slide any more;
* **ownership**: ``claim`` / ``free``. A shape belongs to the first recogniser that claims it (``Item.rec``);
  the other one skips it. Order in ``build_slide``: ``recognise2`` (chrome, background, steps, takeaway bar,
  tables, charts, chart panel) first, then ``recognise`` (quote, badges, panel, tiles, bars, dark cards);
* **spans**: ``put_span`` / ``span_runs`` set ``RunT.span`` and ``wrap_span`` writes it, so a run is wrapped
  once, bold is stated once (``**x**`` inside, or ``bold=true`` in the span when the policy asks) and a span
  that carries a colour replaces the colour markup;
* **style lines**: ``merge_lines`` joins every ``style:`` (and ``sizes:``) line of a slide into one, the first
  writer of a key wins.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

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
    return key in _keys(r.span)


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
