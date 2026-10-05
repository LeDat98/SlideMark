"""LaTeX subset -> OMML (Office Math) and a native equation text box. Pure Python, never raises."""

from __future__ import annotations

from xml.sax.saxutils import escape

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

from ..ir import Placed, Raw
from .util import RenderCtx, hex6

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
A14_NS = "http://schemas.microsoft.com/office/drawing/2010/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"

_GREEK_NAMES = (
    "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho "
    "sigmaf sigma tau upsilon phi chi psi omega"
).split()
GREEK = {n: chr(0x3B1 + i) for i, n in enumerate(_GREEK_NAMES) if n not in ("omicron", "sigmaf")}
GREEK["omicron"] = "\u03bf"
GREEK.update(
    {
        "varepsilon": "ϵ",
        "vartheta": "ϑ",
        "varphi": "ϕ",
        "Gamma": "Γ",
        "Delta": "Δ",
        "Theta": "Θ",
        "Lambda": "Λ",
        "Xi": "Ξ",
        "Pi": "Π",
        "Sigma": "Σ",
        "Phi": "Φ",
        "Psi": "Ψ",
        "Omega": "Ω",
    }
)
SYMBOLS = {
    "times": "×",
    "cdot": "⋅",
    "pm": "±",
    "mp": "∓",
    "div": "÷",
    "leq": "≤",
    "le": "≤",
    "geq": "≥",
    "ge": "≥",
    "neq": "≠",
    "ne": "≠",
    "approx": "≈",
    "equiv": "≡",
    "infty": "∞",
    "rightarrow": "→",
    "to": "→",
    "leftarrow": "←",
    "Rightarrow": "⇒",
    "Leftrightarrow": "⇔",
    "leftrightarrow": "↔",
    "partial": "∂",
    "nabla": "∇",
    "in": "∈",
    "forall": "∀",
    "exists": "∃",
    "ldots": "…",
    "cdots": "⋯",
    "sim": "∼",
    "propto": "∝",
    "degree": "°",
}
NARY = {"sum": "∑", "prod": "∏", "int": "∫", "oint": "∮", "iint": "∬"}
FUNCS = {"sin", "cos", "tan", "log", "ln", "exp", "lim", "max", "min", "det", "sup", "inf"}
ACCENTS = {"hat": "̂", "bar": "̄", "vec": "⃗", "dot": "̇", "tilde": "̃"}
ESCAPED = set("{}%&#_$")
SPACING = {",": " ", ";": " ", ":": " ", "quad": " ", "qquad": "  "}


def _e(tag: str, inner: str) -> str:
    return f"<m:{tag}>{inner}</m:{tag}>"


class _Parser:
    def __init__(self, src: str, sz: int):
        self.s = src
        self.i = 0
        self.sz = sz  # run size in 1/100 pt

    # -- xml pieces
    def run(self, text: str, sty: str | None = None, nor: bool = False) -> str:
        rpr = "<m:rPr><m:nor/></m:rPr>" if nor else (f'<m:rPr><m:sty m:val="{sty}"/></m:rPr>' if sty else "")
        ital = 0 if (nor or sty == "p") else 1
        arpr = (
            f'<a:rPr lang="en-US" sz="{self.sz}" i="{ital}">'
            '<a:latin typeface="Cambria Math"/><a:ea typeface="Cambria Math"/></a:rPr>'
        )
        return f"<m:r>{rpr}{arpr}<m:t>{escape(text)}</m:t></m:r>"

    def ctrl(self) -> str:
        return (
            f'<m:ctrlPr><a:rPr lang="en-US" sz="{self.sz}" i="1">'
            '<a:latin typeface="Cambria Math"/></a:rPr></m:ctrlPr>'
        )

    # -- scanning
    def eof(self) -> bool:
        return self.i >= len(self.s)

    def skip_ws(self) -> None:
        while not self.eof() and self.s[self.i] in " \t":
            self.i += 1

    def peek_cmd(self) -> str | None:
        if self.s.startswith("\\", self.i):
            j = self.i + 1
            while j < len(self.s) and self.s[j].isalpha():
                j += 1
            return self.s[self.i + 1 : j] if j > self.i + 1 else self.s[self.i + 1 : self.i + 2]
        return None

    def seq(self, stop_right: bool = False, stop_brace: bool = False) -> str:
        out: list[str] = []
        while not self.eof():
            c = self.s[self.i]
            if stop_brace and c == "}":
                break
            if stop_right and self.peek_cmd() == "right":
                break
            if c in " \t\n":
                self.i += 1
                continue
            out.append(self.scripted())
        return "".join(out)

    def group_or_atom(self) -> str:
        """Argument of ^ _ \\frac ...: a {group} or a single token."""
        self.skip_ws()
        if self.eof():
            return ""
        if self.s[self.i] == "{":
            self.i += 1
            inner = self.seq(stop_brace=True)
            if not self.eof():
                self.i += 1
            return inner
        return self.atom()

    def scripts(self) -> tuple[str | None, str | None]:
        sub = sup = None
        while not self.eof():
            self.skip_ws()
            if self.s.startswith("^", self.i) and sup is None:
                self.i += 1
                sup = self.group_or_atom()
            elif self.s.startswith("_", self.i) and sub is None:
                self.i += 1
                sub = self.group_or_atom()
            else:
                break
        return sub, sup

    def scripted(self) -> str:
        cmd = self.peek_cmd()
        if cmd in NARY:
            return self.nary(cmd)
        base = self.atom()
        sub, sup = self.scripts()
        b = _e("e", base)
        if sub is not None and sup is not None:
            return _e("sSubSup", _e("sSubSupPr", self.ctrl()) + b + _e("sub", sub) + _e("sup", sup))
        if sup is not None:
            return _e("sSup", _e("sSupPr", self.ctrl()) + b + _e("sup", sup))
        if sub is not None:
            return _e("sSub", _e("sSubPr", self.ctrl()) + b + _e("sub", sub))
        return base

    def nary(self, cmd: str) -> str:
        self.i += 1 + len(cmd)
        sub, sup = self.scripts()
        self.skip_ws()
        end = self.eof() or self.s[self.i] == "}" or self.peek_cmd() == "right"
        body = "" if end else self.scripted()
        lim = "undOvr" if cmd in ("sum", "prod") else "subSup"
        pr = f'<m:chr m:val="{NARY[cmd]}"/><m:limLoc m:val="{lim}"/>'
        pr += '<m:subHide m:val="1"/>' if not sub else ""
        pr += '<m:supHide m:val="1"/>' if not sup else ""
        return _e(
            "nary",
            _e("naryPr", pr + self.ctrl()) + _e("sub", sub or "") + _e("sup", sup or "") + _e("e", body),
        )

    def atom(self) -> str:
        if self.eof():
            return ""
        c = self.s[self.i]
        if c == "{":
            return self.group_or_atom()
        if c == "\\":
            return self.command()
        if c.isdigit() or (c == "." and self.s[self.i + 1 : self.i + 2].isdigit()):
            j = self.i + 1
            while j < len(self.s) and (self.s[j].isdigit() or self.s[j] == "."):
                j += 1
            num = self.s[self.i : j]
            self.i = j
            return self.run(num, "p")
        self.i += 1
        if c.isalpha():
            return self.run(c)
        if c == "-":
            return self.run("−", "p")
        return self.run(c, "p")

    def command(self) -> str:
        name = self.peek_cmd() or ""
        self.i += 1 + len(name)
        if name in ("frac", "dfrac", "tfrac"):
            num = self.group_or_atom()
            den = self.group_or_atom()
            return _e("f", _e("fPr", self.ctrl()) + _e("num", num) + _e("den", den))
        if name == "sqrt":
            deg = ""
            if self.s.startswith("[", self.i):
                k = self.s.find("]", self.i)
                if k > 0:
                    deg = _Parser(self.s[self.i + 1 : k], self.sz).seq()
                    self.i = k + 1
            arg = self.group_or_atom()
            pr = "" if deg else '<m:degHide m:val="1"/>'
            return _e("rad", _e("radPr", pr + self.ctrl()) + _e("deg", deg) + _e("e", arg))
        if name in ("text", "textrm", "mathrm", "mathbf", "operatorname"):
            self.skip_ws()
            if self.s.startswith("{", self.i):
                k = self.s.find("}", self.i)
                k = len(self.s) if k < 0 else k
                txt = self.s[self.i + 1 : k]
                self.i = min(k + 1, len(self.s))
            else:
                txt = self.s[self.i : self.i + 1]
                self.i += 1
            return self.run(txt, nor=True) if name in ("text", "textrm") else self.run(txt, "p")
        if name in ACCENTS:
            arg = self.group_or_atom()
            return _e("acc", _e("accPr", f'<m:chr m:val="{ACCENTS[name]}"/>' + self.ctrl()) + _e("e", arg))
        if name == "left":
            return self.delim()
        if name in GREEK:
            return self.run(GREEK[name], "p" if name[0].isupper() else None)
        if name in SYMBOLS:
            return self.run(SYMBOLS[name], "p")
        if name in FUNCS:
            return self.run(name, "p")
        if name in SPACING:
            return self.run(SPACING[name], "p")
        if name in ESCAPED or name == "|":
            return self.run(name, "p")
        if name in ("\\", ""):
            return ""
        return self.run("\\" + name, nor=True)  # unknown command: keep it literally

    def delim(self) -> str:
        def one() -> str:
            if self.eof():
                return ""
            if self.s[self.i] == "\\":
                n = self.peek_cmd() or ""
                self.i += 1 + len(n)
                return {"{": "{", "}": "}", "|": "‖", "langle": "⟨", "rangle": "⟩", "vert": "|"}.get(n, "")
            c = self.s[self.i]
            self.i += 1
            return "" if c == "." else c

        beg = one()
        inner = self.seq(stop_right=True)
        end = ""
        if self.peek_cmd() == "right":
            self.i += len("\\right")
            end = one()
        pr = f'<m:begChr m:val="{escape(beg)}"/><m:endChr m:val="{escape(end)}"/>'
        return _e("d", _e("dPr", pr + self.ctrl()) + _e("e", inner))


def latex_to_omml(src: str, size_pt: float = 18) -> str:
    """Return ``<m:oMathPara>...</m:oMathPara>`` for a LaTeX subset (one ``m:oMath`` per ``\\\\`` line)."""
    sz = int(round(size_pt * 100))
    lines = [ln for ln in src.replace("\r", "").replace("\n", " ").split("\\\\") if ln.strip()]
    maths = []
    for ln in lines:
        p = _Parser(ln.strip(), sz)
        body = ""
        while not p.eof():
            body += p.seq()
            if not p.eof():  # stray `}` or `\right`
                p.i += 1
        maths.append(_e("oMath", body))
    if not maths:
        raise ValueError("empty equation")
    return "<m:oMathPara>" + "".join(maths) + "</m:oMathPara>"


_SUP = dict(
    zip(
        "0123456789+-=()n",
        "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207a\u207b\u207c\u207d\u207e\u207f",
        strict=True,
    )
)
_SUB = dict(
    zip(
        "0123456789+-=()",
        "\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089\u208a\u208b\u208c\u208d\u208e",
        strict=True,
    )
)


def _linear(node) -> str:
    """Unicode text of an OMML subtree: the fallback for viewers that cannot draw equations."""

    def ch(tag: str) -> str:
        c = node.find(f"{{{M_NS}}}{tag}")
        return _linear(c) if c is not None else ""

    def script(txt: str, table: dict[str, str], mark: str) -> str:
        txt = txt.replace("\u2212", "-")
        return "".join(table[c] for c in txt) if txt and all(c in table for c in txt) else f"{mark}({txt})"

    tag = etree.QName(node).localname if isinstance(node.tag, str) else ""
    if tag == "t":
        return node.text or ""
    if tag == "f":
        return f"({ch('num')})/({ch('den')})"
    if tag == "sSup":
        return ch("e") + script(ch("sup"), _SUP, "^")
    if tag == "sSub":
        return ch("e") + script(ch("sub"), _SUB, "_")
    if tag == "sSubSup":
        return ch("e") + script(ch("sub"), _SUB, "_") + script(ch("sup"), _SUP, "^")
    if tag == "rad":
        deg = ch("deg")
        return (deg and script(deg, _SUP, "")) + "\u221a(" + ch("e") + ")"
    if tag == "nary":
        chr_ = node.find(f"{{{M_NS}}}naryPr/{{{M_NS}}}chr")
        sym = chr_.get(f"{{{M_NS}}}val") if chr_ is not None else "\u2211"
        lo, hi = ch("sub"), ch("sup")
        return sym + (f"[{lo}..{hi}]" if lo or hi else "") + " " + ch("e")
    if tag == "d":
        pr = node.find(f"{{{M_NS}}}dPr")
        beg = (
            pr.find(f"{{{M_NS}}}begChr").get(f"{{{M_NS}}}val")
            if pr is not None and pr.find(f"{{{M_NS}}}begChr") is not None
            else "("
        )
        end = (
            pr.find(f"{{{M_NS}}}endChr").get(f"{{{M_NS}}}val")
            if pr is not None and pr.find(f"{{{M_NS}}}endChr") is not None
            else ")"
        )
        return beg + ch("e") + end
    if tag in ("ctrlPr", "sSupPr", "sSubPr", "sSubSupPr", "fPr", "radPr", "naryPr", "dPr", "accPr", "rPr"):
        return ""
    return "".join(_linear(c) for c in node)


def add_math(rc: RenderCtx, slide, pl: Placed, name: str) -> bool:
    """Native equation text box; False when the source cannot be converted (caller draws a placeholder)."""
    el: Raw = pl.element  # type: ignore[assignment]
    theme = rc.theme
    size = (
        el.style.font_size if el.style and el.style.font_size else theme.sizes.get("body", 18)
    ) * pl.font_scale
    color = hex6(theme, (el.style.color if el.style else None) or "fg")
    try:
        xml = latex_to_omml(el.source, size)
        a14m = etree.fromstring(
            f'<a14:m xmlns:a14="{A14_NS}" xmlns:m="{M_NS}" xmlns:a="{A_NS}">{xml}</a14:m>'
        )
    except Exception:
        return False
    for rpr in a14m.iter(f"{{{A_NS}}}rPr"):
        sf = etree.Element(qn("a:solidFill"))
        etree.SubElement(sf, qn("a:srgbClr")).set("val", color)
        rpr.insert(0, sf)
    shp = slide.shapes.add_textbox(Emu(pl.x), Emu(pl.y), Emu(pl.w), Emu(pl.h))
    shp.name = name
    tf = shp.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para = tf.paragraphs[0]
    para.alignment = PP_ALIGN.CENTER
    # what PowerPoint writes: the equation in mc:Choice (a14), the plain LaTeX source as mc:Fallback
    ac = etree.Element(f"{{{MC_NS}}}AlternateContent", nsmap={"mc": MC_NS})
    choice = etree.SubElement(ac, f"{{{MC_NS}}}Choice", nsmap={"a14": A14_NS})
    choice.set("Requires", "a14")
    choice.append(a14m)
    fallback = etree.SubElement(ac, f"{{{MC_NS}}}Fallback")
    for i, line in enumerate(a14m.iter(f"{{{M_NS}}}oMath")):
        if i:
            para.add_line_break()
            fallback.append(para._p.findall(qn("a:br"))[-1])
        run = para.add_run()
        run.text = _linear(line)
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor.from_string(color)
        para._p.remove(run._r)
        fallback.append(run._r)
    ppr = para._p.find(qn("a:pPr"))
    if ppr is not None:
        ppr.addnext(ac)
    else:
        para._p.insert(0, ac)
    return True
