"""OMML (Office Math) -> the LaTeX subset of ``render/math.py``; the inverse of ``latex_to_omml``.

Every result is verified: the LaTeX is converted forward again and compared with the source equation
(``roundtrip_ok``), so a caller knows whether the equation is reproduced exactly or only approximated.
"""

from __future__ import annotations

import re

from lxml import etree

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"

_ACC = {v: k for k, v in {"hat": "̂", "bar": "̄", "vec": "⃗", "dot": "̇", "tilde": "̃"}.items()}
_DELIM = {"{": r"\{", "}": r"\}", "‖": r"\|", "⟨": r"\langle ", "⟩": r"\rangle ", "": "."}
_ESCAPED = set("{}%&#_$")


def _q(tag: str) -> str:
    return f"{{{M}}}{tag}"


def _tables():
    from ..render import math as rm

    greek = {v: k for k, v in rm.GREEK.items()}
    symbols = {}
    for k, v in rm.SYMBOLS.items():
        symbols.setdefault(v, k)
    return rm, greek, symbols


def _run(r, rm, greek, symbols) -> str:
    text = "".join(t.text or "" for t in r.findall(_q("t")))
    rpr = r.find(_q("rPr"))
    nor = rpr is not None and rpr.find(_q("nor")) is not None
    sty = None
    if rpr is not None and rpr.find(_q("sty")) is not None:
        sty = rpr.find(_q("sty")).get(_q("val"))
    if nor:
        return text if text.startswith("\\") else "\\text{" + text + "}"
    if sty != "p":  # italic: a single letter or a lower-case Greek letter
        return ("\\" + greek[text] + " ") if text in greek else text
    if re.fullmatch(r"[0-9.]+", text):
        return text
    if text == "−":
        return "-"
    if text in rm.FUNCS:
        return "\\" + text + " "
    if text in greek:
        return "\\" + greek[text] + " "
    if text in symbols:
        return "\\" + symbols[text] + " "
    if text == " ":
        return "\\, "
    if text == "  ":
        return "\\qquad "
    if text == "|":
        return "\\|"
    if len(text) == 1 and not text.isalpha():
        return ("\\" + text) if text in _ESCAPED else text
    return "\\mathrm{" + text + "}"


def _group(parts: list[str]) -> str:
    s = "".join(parts)
    return s


def _arg(el, tag: str, conv) -> str:
    node = el.find(_q(tag))
    return conv(node) if node is not None else ""


def convert(el, tables=None) -> str:
    rm, greek, symbols = tables or _tables()

    def seq(node) -> str:
        out = []
        for c in node:
            if not isinstance(c.tag, str):
                continue
            out.append(one(c))
        return "".join(out)

    def braced(node) -> str:
        """An argument that must be one atom: {…}."""
        return "{" + seq(node) + "}"

    def base_of(node) -> str:
        kids = [c for c in node if isinstance(c.tag, str)]
        s = seq(node)
        if len(kids) == 1 and kids[0].tag == _q("r") and len(s.strip()) <= 1:
            return s
        return "{" + s + "}"

    def one(c) -> str:
        tag = etree.QName(c).localname
        if tag == "r":
            return _run(c, rm, greek, symbols)
        if tag == "f":
            return "\\frac" + braced(c.find(_q("num"))) + braced(c.find(_q("den")))
        if tag == "rad":
            deg = c.find(_q("deg"))
            d = seq(deg) if deg is not None else ""
            return "\\sqrt" + (f"[{d}]" if d else "") + braced(c.find(_q("e")))
        if tag in ("sSup", "sSub", "sSubSup"):
            out = base_of(c.find(_q("e")))
            if tag != "sSup":
                out += "_" + braced(c.find(_q("sub")))
            if tag != "sSub":
                out += "^" + braced(c.find(_q("sup")))
            return out
        if tag == "nary":
            pr = c.find(_q("naryPr"))
            chr_ = pr.find(_q("chr")).get(_q("val")) if pr is not None and pr.find(_q("chr")) is not None else "∑"
            name = next((k for k, v in rm.NARY.items() if v == chr_), "sum")
            sub_hide = pr is not None and pr.find(_q("subHide")) is not None
            sup_hide = pr is not None and pr.find(_q("supHide")) is not None
            out = "\\" + name
            if not sub_hide:
                out += "_" + braced(c.find(_q("sub")))
            if not sup_hide:
                out += "^" + braced(c.find(_q("sup")))
            body = c.find(_q("e"))
            kids = [k for k in body if isinstance(k.tag, str)] if body is not None else []
            if not kids:
                return out + " "
            return out + " " + (seq(body) if len(kids) == 1 else "{" + seq(body) + "}")
        if tag == "d":
            pr = c.find(_q("dPr"))

            def ch(n, default):
                e = pr.find(_q(n)) if pr is not None else None
                return default if e is None else e.get(_q("val"))

            beg, end = ch("begChr", "("), ch("endChr", ")")
            return "\\left" + _DELIM.get(beg, beg) + seq(c.find(_q("e"))) + "\\right" + _DELIM.get(end, end)
        if tag == "acc":
            pr = c.find(_q("accPr"))
            chr_ = pr.find(_q("chr")).get(_q("val")) if pr is not None and pr.find(_q("chr")) is not None else "̂"
            return "\\" + _ACC.get(chr_, "hat") + braced(c.find(_q("e")))
        if tag.endswith("Pr"):
            return ""
        return seq(c)

    if el.tag == _q("oMathPara"):
        return " \\\\ ".join(seq(m) for m in el.findall(_q("oMath")))
    return seq(el)


def _canon(el) -> str:
    """Comparable form of an equation: formatting that depends on size/color is dropped."""
    el = etree.fromstring(etree.tostring(el))
    for rpr in el.iter(f"{{{A}}}rPr"):
        for k in list(rpr.attrib):
            if k == "sz":
                del rpr.attrib[k]
        for sf in rpr.findall(f"{{{A}}}solidFill"):
            rpr.remove(sf)
    return etree.tostring(el, method="c14n").decode()


def omml_to_latex(para_el) -> tuple[str, bool]:
    """(LaTeX, exact): ``exact`` is True when converting the LaTeX forward gives the same equation back."""
    try:
        latex = convert(para_el).strip()
    except Exception:
        return "", False
    try:
        from ..render.math import latex_to_omml

        sz = 1800
        for rpr in para_el.iter(f"{{{A}}}rPr"):
            if rpr.get("sz", "").isdigit():
                sz = int(rpr.get("sz"))
                break
        xml = latex_to_omml(latex, sz / 100)
        again = etree.fromstring(f'<root xmlns:m="{M}" xmlns:a="{A}">{xml}</root>')[0]
        src = para_el
        if src.tag != _q("oMathPara"):
            src = etree.fromstring(f'<root xmlns:m="{M}" xmlns:a="{A}"><m:oMathPara/></root>')[0]
            src.append(etree.fromstring(etree.tostring(para_el)))
        return latex, _canon(again) == _canon(src)
    except Exception:
        return latex, False
