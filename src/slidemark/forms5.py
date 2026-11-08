"""Wave 2026-11-08 lane C: ``@swimlane`` and ``@sequence`` (editorial diagrams): source model and tokens.

======================  ===========================================================================
token                   meaning
======================  ===========================================================================
``swimlane.head.fill``  lane caption fill (default none: a mono-capitals caption, no filled header)
``swimlane.head.color`` lane name ink (default: readable on the fill)
``swimlane.head.w``     width of the header band (a length; default 14% of the body, 0.9-1.8 in; for
                        ``dir=v`` the band height: 12% of the body, 0.45-0.9 in)
``swimlane.head.size``  lane name size in pt (default: as large as the band holds)
``swimlane.name.size``  step name size in pt (default 12; the sublabel and tag sizes follow the diagram kit)
``swimlane.fill``       lane body fills ``a,b`` cycled (default: none, the slide shows through)
``swimlane.line``       lane outline / separator colour (default ``border``) and ``swimlane.line.w``
``swimlane.step.fill``  step fill (default: the ``node`` class card), ``swimlane.step.color`` its ink
``swimlane.step.line``  step outline (default: the ``node`` class), ``swimlane.step.line.w`` its width
``swimlane.step.radius`` step corner radius (a length; default 4pt)
``swimlane.step.ratio`` (unused since the diagram kit sizes a step to its text; kept so old decks parse)
``swimlane.gap``        air between two step columns (a length; default 22% of a column)
``swimlane.arrow``      arrow colour (default ``render.connector_color``), ``swimlane.arrow.w`` width
``sequence.head.fill``  participant card fill (default: the ``node`` class), ``sequence.head.color`` its ink
``sequence.head.line``  participant card outline (default: the ``node`` class)
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
- ``@sequence``: one list; ``- A > B: label`` is a message, ``>>`` / ``-->`` a dashed reply, ``=>`` primary,
  ``~>`` HTTP, ``- A > A: x`` a self-message; participants are the names in order of first appearance (a list
  item without ``>`` declares participants early, with tags and sublabels:
  ``- [EXT] Client: Browser, API, DB``).
- Diagram kit (docs/SYNTAX.md): ``- 3: [TAG] Name: sublabel > LABEL {.focal}``; the arrow symbol and label at
  the end style the arrow that leaves the step (``>`` ``=>`` ``~>`` ``-->``).

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

_TAG = re.compile(r"^\s*\[([^\[\]]{1,12})\]\s*")
_KIND_OF = {
    ">": "flow",
    "->": "flow",
    "→": "flow",
    "=>": "primary",
    "~>": "http",
    "-->": "return",
    ">>": "return",
}


def split_tag(text: str) -> tuple[str, str]:
    """``[EXT] Reader`` -> (``Reader``, ``EXT``); a malformed ``[`` stays text. Never raises."""
    m = _TAG.match(text)
    if not m or not m.group(1).strip():
        return text.strip(), ""
    return text[m.end() :].strip(), m.group(1).strip()


def split_sub(text: str) -> tuple[str, str]:
    """``Name: sub`` (first colon, ASCII or full-width) -> (name, sub)."""
    parts = re.split(r"[:：]", text, maxsplit=1)
    return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")


def kind_of(sym: str) -> str:
    """The arrow kind of a symbol (``>`` flow, ``=>`` primary, ``~>`` http, ``-->`` / ``>>`` return)."""
    s = sym.strip()
    if s in _KIND_OF:
        return _KIND_OF[s]
    return "return" if s.endswith(">>") else "flow"


FORMS = ("swimlane", "sequence")
LANES = (2, 8)  # lanes
PARTS = (2, 8)  # participants
MAX_COLS = 12


class Forms5Tokens(Forms4Tokens):
    """Theme fields of wave 2026-11-08 lane C (``None`` = derive: the layout decides)."""

    # @swimlane
    swimlane_head_fill: str | None = None
    swimlane_head_color: str | None = None
    swimlane_head_w: Length | None = None
    swimlane_head_size: float | None = None
    swimlane_name_size: float = 12.0  # step names (``size=N`` on the slide wins)
    swimlane_fill: str | None = None
    swimlane_line: str = "border"
    swimlane_line_w: Length = "0.75pt"
    swimlane_step_fill: str | None = None
    swimlane_step_color: str | None = None
    swimlane_step_line: str | None = None
    swimlane_step_line_w: Length | None = None
    swimlane_step_radius: Length | None = None
    swimlane_step_ratio: float = Field(0.62, ge=0.2, le=0.95)
    swimlane_gap: Length | None = None
    swimlane_arrow: str | None = None
    swimlane_arrow_w: Length | None = None
    # @sequence
    sequence_head_fill: str | None = None
    sequence_head_color: str | None = None
    sequence_head_line: str | None = None
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
_PTS = {"swimlane_head_size", "swimlane_name_size", "sequence_size"}
_NONE = ("none", "null", "off")
_KEEP = {  # tokens whose "none" is a real value (a width, a colour that must exist)
    "swimlane_line",
    "swimlane_line_w",
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

_SUB = re.compile(r":\s+|：\s*")  # a colon that starts a sublabel (not the one in `10:30`)
_TAIL = re.compile(r"\s*\{((?:\s*\.[\w-]+)+)\s*\}\s*$")
_COL = re.compile(r"^\s*(\d{1,2})(?::\s+|：\s*)")
_MSG = re.compile(
    r"^\s*(?P<a>[^>:：]+?)\s*(?P<arrow>~>|=>|-{0,2}>{1,2})\s*(?P<b>[^>:：]+?)\s*(?:[:：]\s*(?P<label>.*?))?\s*$"
)
_HAND = re.compile(r"\s+(-->|~>|=>|>)(?:\s+(.*?))?\s*$")  # `- Open PR > HANDOFF`: the arrow out of this step
_CLS = re.compile(r"\s*\{((?:\s*\.[\w-]+)+)\s*\}\s*$")


def split_classes(text: str) -> tuple[str, list[str]]:
    """``text {.focal .store}`` -> (``text``, [``focal``, ``store``]); other braces stay text."""
    m = _CLS.search(text)
    if not m:
        return text.strip(), []
    return text[: m.start()].strip(), re.findall(r"\.([\w-]+)", m.group(1))


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
    tag: str = ""  # `[REVIEW] Check`: the type tag
    sub: str = ""  # `Check: fact-check`: the sublabel
    kind: str = "flow"  # the arrow out of this step: flow | primary | http | return (`>` `=>` `~>` `-->`)
    label: str = ""  # its label: `- Open PR > HANDOFF`

    @property
    def name(self) -> str:
        return self.paras[0].plain.strip() if self.paras else ""

    @property
    def subs(self) -> list[str]:
        """The sublabel lines: the ``: sub`` text, then the sub-items of the step."""
        return [x for x in [self.sub, *(p.plain.strip() for p in self.paras[1:])] if x]


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
                text = "".join(r.text for r in runs)
                kind, label = "flow", ""
                hm = _HAND.search(text)
                if hm:
                    kind, label = kind_of(hm.group(1)), (hm.group(2) or "").strip()
                    text = text[: hm.start()]
                text, tag = split_tag(text)
                ms = _SUB.search(text)
                text, sub = (
                    (text[: ms.start()].strip(), text[ms.end() :].strip()) if ms else (text.strip(), "")
                )
                if hm or tag or sub:
                    runs = [Run(text=text)]
                while (li, col) in taken:
                    col += 1
                taken.add((li, col))
                prev = col
                out.append(
                    Step(
                        len(out) + 1,
                        li,
                        col,
                        [p.model_copy(update={"runs": runs, "marker": None})],
                        cls,
                        tag,
                        sub,
                        kind,
                        label,
                    )
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
    kind: str = "flow"  # flow | primary | http | return (`>` `=>` `~>` `-->`; `>>` is `-->`)

    @property
    def is_self(self) -> bool:
        return self.src == self.dst


@dataclass
class Part:
    """A participant: ``[EXT] Reader: Browser {.focal}`` on the declaring line."""

    name: str
    tag: str = ""
    sub: str = ""
    classes: list[str] = field(default_factory=list)


def sequence_model(slide: Slide) -> tuple[list[Part], list[Msg]] | None:
    """``(participants in order, messages)`` of a sequence slide (one list, nothing else), else ``None``."""
    els = slide.elements
    if not els or not all(isinstance(e, Text) and e.role == "body" and e.paragraphs for e in els):
        return None
    paras = [p for e in els for p in e.paragraphs if p.level == 0]  # type: ignore[union-attr]
    if not paras or any(p.marker is None for p in paras):
        return None
    declared: dict[str, Part] = {}
    msgs: list[Msg] = []
    for p in paras:
        runs, cls = tail_classes(p.runs)
        text = "".join(r.text for r in runs).strip()
        m = _MSG.match(text)
        if m:
            label = (m["label"] or "").strip()
            kind = kind_of(m["arrow"])
            msgs.append(
                Msg(len(msgs) + 1, m["a"].strip(), m["b"].strip(), label, kind == "return", cls, kind)
            )
        elif text and not msgs:
            pieces = re.split(r"[,、，]", text)
            for pi, piece in enumerate(pieces):
                body, pcls = split_classes(piece)
                if pi == len(pieces) - 1:
                    pcls = [*pcls, *cls]  # the line's trailing `{.focal}` belongs to its last participant
                body, tag = split_tag(body)
                name, sub = split_sub(body)
                if name:
                    declared.setdefault(name, Part(name, tag, sub, pcls))
    if not msgs:
        return None
    parts: dict[str, Part] = dict(declared)
    for x in (y for m in msgs for y in (m.src, m.dst)):
        parts.setdefault(x, Part(x))
    return list(parts.values()), msgs


def sequence_of(slide: Slide) -> tuple[list[str], list[Msg]] | None:
    """``(participant names in order, messages)`` of a sequence slide, else ``None``."""
    got = sequence_model(slide)
    return None if got is None else ([x.name for x in got[0]], got[1])


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
        return len(steps), max(len(steps) - 1, 0), [x.label for x in steps if x.label]
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
        parts, msgs = sequence_model(slide) or ([], [])
        return sum(1 for m in msgs if marks & set(m.classes)) + sum(
            1 for x in parts if marks & set(x.classes)
        )
    except Exception:
        return 0


def fit_line(v: dict, text: str) -> tuple[str, list[str]]:
    """The build's fit line of the form."""
    form, n = v.get("form", ""), v.get("n")
    if form == "swimlane":
        return f"swimlane {v.get('lanes')} lanes, {n} steps ({v.get('dir')})", [text]
    return f"sequence {v.get('parts')} participants, {n} messages", [text]
