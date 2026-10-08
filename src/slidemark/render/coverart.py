"""Cover art, render side: a thin line (or a ring outline) that is only partly opaque.

The layout (``layout/coverart.py``) names every shape ``Cover art N`` and gives a line or a ring outline the
attribute ``line_alpha`` (0..1); a fill's opacity is the ordinary ``opacity`` style. python-pptx has no
alpha on an outline, so the ``a:alpha`` child is written on the colour of the ``a:ln`` here. Never raises:
a shape whose outline has no solid colour is left as it is.
"""

from __future__ import annotations

from lxml import etree
from pptx.oxml.ns import qn


def set_line_alpha(line, alpha) -> None:
    """Make the solid colour of ``line`` (a python-pptx ``LineFormat``) ``alpha`` opaque (0..1)."""
    try:
        a = float(alpha)
    except (TypeError, ValueError):
        return
    if not 0 <= a < 1:
        return
    ln = line._get_or_add_ln()
    clr = ln.find(qn("a:solidFill"))
    clr = clr[0] if clr is not None and len(clr) else None
    if clr is None:
        return
    for old in clr.findall(qn("a:alpha")):
        clr.remove(old)
    etree.SubElement(clr, qn("a:alpha")).set("val", str(round(a * 100000)))
