"""Wave 2026-11-08 lane C: ``@swimlane`` and ``@sequence`` (editorial diagrams): source model and tokens.

======================  ===========================================================================
token                   meaning
======================  ===========================================================================
``swimlane.head.fill``  lane header band fill (default ``surface``)
``swimlane.head.color`` lane name ink (default: readable on the fill)
``swimlane.head.w``     width of the header band (a length; default 14% of the body, 0.9-1.8 in; for
                        ``dir=v`` the band height: 12% of the body, 0.45-0.9 in)
``swimlane.head.size``  lane name size in pt (default: as large as the band holds)
``swimlane.fill``       lane body fills ``a,b`` cycled (default: none, the slide shows through)
``swimlane.line``       lane outline / separator colour (default ``border``) and ``swimlane.line.w``
``swimlane.step.fill``  step fill (default ``bg``), ``swimlane.step.color`` its ink (default: readable)
``swimlane.step.line``  step outline (default ``muted``), ``swimlane.step.line.w`` its width
``swimlane.step.radius`` step corner radius (a length; default 4pt)
``swimlane.step.ratio`` step height / lane height (default 0.62; it grows when the text needs more)
``swimlane.gap``        air between two step columns (a length; default 22% of a column)
``swimlane.arrow``      arrow colour (default ``render.connector_color``), ``swimlane.arrow.w`` width
``sequence.head.fill``  participant box fill (default ``surface``), ``sequence.head.color`` its ink
``sequence.head.line``  participant box outline (default ``muted``)
``sequence.lifeline``   dashed lifeline colour (default ``muted``), ``sequence.lifeline.w`` its width
``sequence.gap``        air between two participant boxes (a length; default 8% of the body)
``sequence.size``       message label size in pt (default: as large as the rows hold)
``sequence.arrow``      arrow colour (default ``render.connector_color``), ``sequence.arrow.w`` width
======================  ===========================================================================

Source syntax (docs/SYNTAX.md):

- ``@swimlane``: every ``## Lane`` box is a lane (``dir=v`` makes them columns), every list item a step. A
  step sits in the column of its place in the written sequence (1, 2, 3 ... across the whole slide);
  ``- 3: text`` names the column. Arrows join the steps in column order. ``{.focal}`` (any role class)
  styles a step.
- ``@sequence``: one list; ``- A > B: label`` is a message, ``>>`` a dashed reply, ``- A > A: x`` a
  self-message; participants are the names in order of first appearance (a list item without ``>``
  declares participants early: ``- Client, API, DB``).

Fields are theme fields (``Theme`` inherits them), so every token is also a preset key.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import Field

from .forms4 import Forms4Tokens
from .ir import Container, Paragraph, Run, Slide, Text

Length = str | float | int

FORMS = ("swimlane", "sequence")
LANES = (2, 8)  # lanes
PARTS = (2, 8)  # participants
MAX_COLS = 12


class Forms5Tokens(Forms4Tokens):
    """Theme fields of wave 2026-11-08 lane C (``None`` = derive: the layout decides)."""

    # @swimlane
    swimlane_head_fill: str = "surface"
    swimlane_head_color: str | None = None
    swimlane_head_w: Length | None = None
    swimlane_head_size: float | None = None
    swimlane_fill: str | None = None
    swimlane_line: str = "border"
    swimlane_line_w: Length = "0.75pt"
    swimlane_step_fill: str = "bg"
    swimlane_step_color: str | None = None
    swimlane_step_line: str = "muted"
    swimlane_step_line_w: Length = "1pt"
    swimlane_step_radius: Length = "4pt"
    swimlane_step_ratio: float = Field(0.62, ge=0.2, le=0.95)
    swimlane_gap: Length | None = None
    swimlane_arrow: str | None = None
    swimlane_arrow_w: Length | None = None
    # @sequence
    sequence_head_fill: str = "surface"
    sequence_head_color: str | None = None
    sequence_head_line: str = "muted"
    sequence_lifeline: str = "muted"
    sequence_lifeline_w: Length = "0.75pt"
    sequence_gap: Length | None = None
    sequence_size: float | None = None
    sequence_arrow: str | None = None
    sequence_arrow_w: Length | None = None


_COLOR_LISTS = {"swimlane_fill"}
_COLORS = {
    "swimlane_head_fill",
    "swimlane_head_color",
    "swimlane_line",
    "swimlane_step_fill",
    "swimlane_step_color",
    "swimlane_step_line",
    "swimlane_arrow",
    "sequence_head_fill",
    "sequence_head_color",
    "sequence_head_line",
    "sequence_lifeline",
    "sequence_arrow",
}
_LENGTHS = {
    "swimlane_head_w",
    "swimlane_line_w",
    "swimlane_step_line_w",
    "swimlane_step_radius",
    "swimlane_gap",
    "swimlane_arrow_w",
    "sequence_lifeline_w",
    "sequence_gap",
    "sequence_arrow_w",
}
_PTS = {"swimlane_head_size", "sequence_size"}
_NONE = ("none", "null", "off")
_KEEP = {  # tokens whose "none" is a real value (a width, a colour that must exist)
    "swimlane_line",
    "swimlane_line_w",
    "swimlane_step_fill",
    "swimlane_step_line",
    "swimlane_step_line_w",
    "swimlane_step_radius",
    "swimlane_head_fill",
    "sequence_head_fill",
    "sequence_head_line",
    "sequence_lifeline",
    "sequence_lifeline_w",
}


def normalize(path: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]] | None:
    """Validate one of this module's tokens (``None`` = not one of them). Raises ``theme.TokenValueError``."""
    if path not in Forms5Tokens.model_fields or path in Forms4Tokens.model_fields:
        return None
    from .theme import TokenValueError, _color_value, _length_value, _pt_value, _unquote

    v = _unquote(raw)
    key = path.replace("_", ".")
    if path in _COLOR_LISTS:
        if v.lower() in _NONE:
            return [(path, None)]
        items = [p.strip() for p in v.split(",") if p.strip()]
        if not items:
            raise TokenValueError(f"{key} needs a color", f"write {key}=surface,bg")
        return [(path, ",".join(_color_value(p, names) for p in items))]
    if path in _COLORS:
        if v.lower() in _NONE and path not in _KEEP:
            return [(path, None)]
        return [(path, _color_value(raw, names))]
    if path in _PTS:
        if v.lower() in _NONE:
            return [(path, None)]
        return [(path, _pt_value(raw))]
    if path in _LENGTHS:
        if v.lower() in _NONE and path not in _KEEP:
            return [(path, None)]
        return [(path, _length_value(raw))]
    return None


# --------------------------------------------------------------------------- source model

_TAIL = re.compile(r"\s*\{((?:\s*\.[\w-]+)+)\s*\}\s*$")
_COL = re.compile(r"^\s*(\d{1,2})(?::\s+|：\s*)")
_MSG = re.compile(
    r"^\s*(?P<a>[^>:：]+?)\s*(?P<arrow>-{0,2}>{1,2})\s*(?P<b>[^>:：]+?)\s*(?:[:：]\s*(?P<label>.*?))?\s*$"
)


def tail_classes(runs: list[Run]) -> tuple[list[Run], list[str]]:
    """``runs`` without a trailing ``{.focal .store}`` and the class names it held."""
    text = "".join(r.text for r in runs)
    m = _TAIL.search(text)
    if not m:
        return runs, []
    cut = len(text) - m.start()
    out = list(runs)
    while cut > 0 and out:
        last = out[-1]
        if len(last.text) <= cut:
            cut -= len(last.text)
            out.pop()
        else:
            out[-1] = last.model_copy(update={"text": last.text[: len(last.text) - cut]})
            cut = 0
    return out, re.findall(r"\.([\w-]+)", m.group(1))


def _drop_prefix(runs: list[Run], n: int) -> list[Run]:
    out = list(runs)
    while n > 0 and out:
        first = out[0]
        if len(first.text) <= n:
            n -= len(first.text)
            out.pop(0)
        else:
            out[0] = first.model_copy(update={"text": first.text[n:]})
            n = 0
    return out


@dataclass
class Step:
    idx: int  # 1-based, in written order
    lane: int  # 0-based
    col: int  # 1-based
    paras: list[Paragraph]
    classes: list[str] = field(default_factory=list)


def lanes_of(slide: Slide) -> list[Container] | None:
    """The ``## `` lane boxes when the slide holds nothing else, else ``None``."""
    els = slide.elements
    if els and all(isinstance(e, Container) and e.title is not None and e.grid is None for e in els):
        return list(els)  # type: ignore[arg-type]
    return None


def steps_of(lanes: list[Container]) -> list[Step]:
    """The steps of the lanes: one per top-level list item (or plain line), the column of each step is its
    ``N:`` prefix or the column after the previous written step; two steps of a lane never share a column."""
    out: list[Step] = []
    prev = 0
    taken: set[tuple[int, int]] = set()
    for li, lane in enumerate(lanes):
        for t in lane.children:
            if not isinstance(t, Text):
                continue
            for p in t.paragraphs:
                if p.level > 0 and out and out[-1].lane == li:  # a sub-item: one more line of the step
                    out[-1].paras.append(p.model_copy(update={"marker": None, "level": 0}))
                    continue
                if not p.plain.strip():
                    continue
                runs, cls = tail_classes(p.runs)
                m = _COL.match("".join(r.text for r in runs))
                col = int(m.group(1)) if m else prev + 1
                if m:
                    runs = _drop_prefix(runs, m.end())
                col = max(col, 1)
                while (li, col) in taken:
                    col += 1
                taken.add((li, col))
                prev = col
                out.append(
                    Step(len(out) + 1, li, col, [p.model_copy(update={"runs": runs, "marker": None})], cls)
                )
    return out


def swimlane_fits(slide: Slide) -> str | None:
    lanes = lanes_of(slide)
    if lanes is None:
        return "@swimlane needs `## ` lane boxes and nothing else (put other blocks on another slide)"
    lo, hi = LANES
    if not lo <= len(lanes) <= hi:
        return f"@swimlane needs {lo}-{hi} `## ` lane boxes, found {len(lanes)}"
    steps = steps_of(lanes)
    if len(steps) < 2:
        return "@swimlane needs at least 2 steps (list items) in the lanes"
    if max(s.col for s in steps) > MAX_COLS:
        return f"@swimlane holds at most {MAX_COLS} columns: renumber the steps (`- 4: text`) or split it"
    return None


@dataclass
class Msg:
    idx: int  # 1-based, in written order
    src: str
    dst: str
    label: str
    reply: bool
    classes: list[str] = field(default_factory=list)

    @property
    def is_self(self) -> bool:
        return self.src == self.dst


def sequence_of(slide: Slide) -> tuple[list[str], list[Msg]] | None:
    """``(participants in order, messages)`` of a sequence slide (one list, nothing else), else ``None``."""
    els = slide.elements
    if not els or not all(isinstance(e, Text) and e.role == "body" and e.paragraphs for e in els):
        return None
    paras = [p for e in els for p in e.paragraphs if p.level == 0]  # type: ignore[union-attr]
    if not paras or any(p.marker is None for p in paras):
        return None
    declared: list[str] = []
    msgs: list[Msg] = []
    for p in paras:
        runs, cls = tail_classes(p.runs)
        text = "".join(r.text for r in runs).strip()
        m = _MSG.match(text)
        if m:
            label = (m["label"] or "").strip()
            msgs.append(
                Msg(len(msgs) + 1, m["a"].strip(), m["b"].strip(), label, m["arrow"].endswith(">>"), cls)
            )
        elif text and not msgs:
            declared += [x.strip() for x in re.split(r"[,、，]", text) if x.strip()]
    if not msgs:
        return None
    names: list[str] = []
    for n in [*declared, *(x for m in msgs for x in (m.src, m.dst))]:
        if n not in names:
            names.append(n)
    return names, msgs


def sequence_fits(slide: Slide) -> str | None:
    got = sequence_of(slide)
    if got is None:
        return "@sequence needs one list of messages `- Client > API: POST /order` and nothing else"
    names, _msgs = got
    lo, hi = PARTS
    if not lo <= len(names) <= hi:
        return f"@sequence needs {lo}-{hi} participants, found {len(names)}"
    return None


def fits(form: str, slide: Slide) -> str | None:
    """``None`` when the slide holds what ``form`` needs, else one sentence saying what is missing."""
    if form == "swimlane":
        return swimlane_fits(slide)
    if form == "sequence":
        return sequence_fits(slide)
    return None


def graph_of(slide: Slide) -> tuple[int, int, list[str]] | None:
    """``(nodes, arrows, labels)`` of a swimlane / sequence slide for the diagram budget, else ``None``."""
    from . import forms

    form = forms.form_of(slide)
    if form not in FORMS or fits(form, slide) is not None:
        return None
    if form == "swimlane":
        steps = steps_of(lanes_of(slide) or [])
        return len(steps), max(len(steps) - 1, 0), []
    names, msgs = sequence_of(slide) or ([], [])
    return len(names), len(msgs), [m.label for m in msgs if m.label]


def emphasis_marks(slide: Slide) -> int:
    """Steps / messages carrying an emphasis class (``{.focal}``): each one is an emphasis of the slide."""
    from . import forms

    marks = {"focal", "hero", "accent", "danger", "success"}
    try:
        form = forms.form_of(slide)
        if form not in FORMS or fits(form, slide) is not None:
            return 0
        if form == "swimlane":
            return sum(1 for s in steps_of(lanes_of(slide) or []) if marks & set(s.classes))
        return sum(1 for m in (sequence_of(slide) or ([], []))[1] if marks & set(m.classes))
    except Exception:
        return 0


def fit_line(v: dict, text: str) -> tuple[str, list[str]]:
    """The build's fit line of the form."""
    form, n = v.get("form", ""), v.get("n")
    if form == "swimlane":
        return f"swimlane {v.get('lanes')} lanes, {n} steps ({v.get('dir')})", [text]
    return f"sequence {v.get('parts')} participants, {n} messages", [text]
