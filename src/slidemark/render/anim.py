"""Build animations (``p:timing``): blocks and paragraphs appear one by one on click.

Structure follows what PowerPoint writes: ``tnLst > par > cTn[tmRoot] > childTnLst > seq[mainSeq]``, one
``par`` per click, an *Appear* entrance effect (``presetClass="entr" presetID="1"``) per animated target and
``bldLst`` entries for text shapes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lxml import etree

from ..ir import Chart, Code, Container, Placed, Shape, Text

_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_STATIC_ROLES = ("title", "subtitle", "lead", "footnote", "conclusion")
_TOL = 2  # EMU tolerance for "inside the card"


@dataclass
class _Target:
    spid: int
    para: tuple[int, int] | None = None  # paragraph range (start, end) for a paragraph build


@dataclass
class _Click:
    targets: list[_Target] = field(default_factory=list)


def _is_static(pl: Placed) -> bool:
    el = pl.element
    if isinstance(el, Text):
        return el.role in _STATIC_ROLES or bool(el.attrs.get("field"))
    return isinstance(el, Shape) and el.shape == "line"


def _inside(inner: Placed, outer: Placed) -> bool:
    return (
        inner.x >= outer.x - _TOL
        and inner.y >= outer.y - _TOL
        and inner.x + inner.w <= outer.x + outer.w + _TOL
        and inner.y + inner.h <= outer.y + outer.h + _TOL
    )


def _filled(pl: Placed) -> bool:
    return bool(pl.style.fill or pl.style.line)


def _para_groups(pl: Placed, n_actual: int) -> list[tuple[int, int]]:
    """Paragraph ranges: one per top-level paragraph, sub-levels belong to their parent."""
    paras = pl.element.paragraphs  # type: ignore[union-attr]
    n = min(len(paras), n_actual) if n_actual else len(paras)
    groups: list[list[int]] = []
    for i in range(n):
        if not groups or paras[i].level == 0:
            groups.append([i, i])
        else:
            groups[-1][1] = i
    return [(a, b) for a, b in groups]


def plan_clicks(
    items: list[Placed],
    shape_ids: list[list[int]],
    slide_build: bool,
    n_paras: dict[int, int] | None = None,
) -> tuple[list[_Click], dict[int, str]]:
    """Group the slide's items into click steps; also returns ``{spid: bldLst kind}``."""
    n_paras = n_paras or {}
    cand = [
        i
        for i, pl in enumerate(items)
        if shape_ids[i] and not _is_static(pl) and (slide_build or "build" in pl.element.classes)
    ]
    done: set[int] = set()
    clicks: list[_Click] = []
    bld: dict[int, str] = {}
    carry: list[_Target] = []  # flow arrows wait for the next block
    for i in cand:
        if i in done:
            continue
        pl = items[i]
        el = pl.element
        ids = shape_ids[i]
        if isinstance(el, Shape) and el.shape.startswith("arrow-") and not el.paragraphs:
            carry += [_Target(s) for s in ids]
            _register(pl, ids, bld)
            continue
        click = _Click(carry)
        carry = []
        if isinstance(el, Container):
            for s in ids:
                click.targets.append(_Target(s))
            for j in cand:
                if j != i and j not in done and j > i and _inside(items[j], pl):
                    done.add(j)
                    click.targets += [_Target(s) for s in shape_ids[j]]
                    _register(items[j], shape_ids[j], bld)
            _register(pl, ids, bld)
        elif isinstance(el, Text) and not _filled(pl) and ids:
            groups = _para_groups(pl, n_paras.get(ids[0], 0))
            if len(groups) > 1:
                bld[ids[0]] = "para"
                for k, (a, b) in enumerate(groups):
                    if k == 0:
                        click.targets.append(_Target(ids[0], (a, b)))
                    else:
                        clicks.append(click)
                        click = _Click([_Target(ids[0], (a, b))])
            else:
                click.targets.append(_Target(ids[0]))
                bld[ids[0]] = "text"
        else:
            click.targets += [_Target(s) for s in ids]
            _register(pl, ids, bld)
        clicks.append(click)
    if carry and clicks:  # trailing arrows: appear with the last block
        clicks[-1].targets += carry
    return clicks, bld


def _kind(pl: Placed) -> str | None:
    """The ``bldLst`` entry a rendered element needs: text, shape (autoshape with a body), chart or none."""
    el = pl.element
    if isinstance(el, Text):
        return "shape" if _filled(pl) else "text"
    if isinstance(el, (Shape, Container, Code)):
        return "shape"
    return "chart" if isinstance(el, Chart) else None


def _register(pl: Placed, ids: list[int], bld: dict[int, str]) -> None:
    kind = _kind(pl)
    if ids and kind and ids[0] not in bld:
        bld[ids[0]] = kind


class _Ids:
    def __init__(self) -> None:
        self.n = 0

    def __call__(self) -> int:
        self.n += 1
        return self.n


def _effect(nid: _Ids, t: _Target, node: str, grp: bool) -> str:
    tgt = f'<p:spTgt spid="{t.spid}"/>'
    if t.para is not None:
        tgt = (
            f'<p:spTgt spid="{t.spid}"><p:txEl><p:pRg st="{t.para[0]}" end="{t.para[1]}"/></p:txEl></p:spTgt>'
        )
    g = ' grpId="0"' if grp else ""
    return (
        f'<p:par><p:cTn id="{nid()}" presetID="1" presetClass="entr" presetSubtype="0" fill="hold"{g}'
        f' nodeType="{node}"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
        f'<p:set><p:cBhvr><p:cTn id="{nid()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/>'
        f"</p:stCondLst></p:cTn><p:tgtEl>{tgt}</p:tgtEl><p:attrNameLst><p:attrName>style.visibility"
        f'</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>'
        f"</p:childTnLst></p:cTn></p:par>"
    )


def build_timing(
    items: list[Placed],
    shape_ids: list[list[int]],
    slide_build: bool,
    n_paras: dict[int, int] | None = None,
) -> etree._Element | None:
    """The ``p:timing`` element for a slide, or ``None`` when nothing is animated."""
    clicks, bld = plan_clicks(items, shape_ids, slide_build, n_paras)
    clicks = [c for c in clicks if c.targets]
    if not clicks:
        return None
    nid = _Ids()
    root, main = nid(), nid()
    body = []
    for c in clicks:
        outer, inner = nid(), nid()
        effects = "".join(
            _effect(nid, t, "clickEffect" if k == 0 else "withEffect", t.spid in bld)
            for k, t in enumerate(c.targets)
        )
        body.append(
            f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>'
            f'<p:childTnLst><p:par><p:cTn id="{inner}" fill="hold"><p:stCondLst><p:cond delay="0"/>'
            f"</p:stCondLst><p:childTnLst>{effects}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>"
        )
    blds = []
    for spid, kind in bld.items():
        if kind == "para":
            blds.append(f'<p:bldP spid="{spid}" grpId="0" build="p"/>')
        elif kind == "text":
            blds.append(f'<p:bldP spid="{spid}" grpId="0"/>')
        elif kind == "shape":
            blds.append(f'<p:bldP spid="{spid}" grpId="0" animBg="1"/>')
        elif kind == "chart":
            blds.append(f'<p:bldGraphic spid="{spid}" grpId="0"><p:bldAsOne/></p:bldGraphic>')
    bld_xml = f"<p:bldLst>{''.join(blds)}</p:bldLst>" if blds else ""
    xml = (
        f'<p:timing xmlns:p="{_NS_P}"><p:tnLst><p:par><p:cTn id="{root}" dur="indefinite" restart="never" '
        f'nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="{main}" '
        f'dur="indefinite" nodeType="mainSeq"><p:childTnLst>{"".join(body)}</p:childTnLst></p:cTn>'
        '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
        "</p:prevCondLst>"
        '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
        "</p:nextCondLst>"
        f"</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>{bld_xml}</p:timing>"
    )
    return etree.fromstring(xml)
