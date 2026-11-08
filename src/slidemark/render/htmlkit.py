"""The built-in CSS kit of ```html fences: a few short class names give the editorial diagram look.

Injected into the page *before* the author's own CSS (the author's rules and inline styles win). Every value
is a theme variable (``--accent``, ``--font-mono`` ... see ``htmlimg._tokens``), so a deck's colors and fonts
restyle the kit. Only kit classes are styled, never bare elements or SVG tags: presentational attributes of
the author's own markup (``<text fill=...>``) must keep winning.

Rules and class vocabulary adapted from diagram-design by Cathryn Lavery (MIT): mono UPPERCASE tracked
eyebrows and tags, hairline cards, one accent for the focal element, a legend strip, the three arrow markers.
Sizes are slide sizes (a block is about 1180 x 490 px): labels 12-14 px, names 18-20 px.
"""

# ruff: noqa: E501  (the embedded CSS keeps long lines)
from __future__ import annotations

__all__ = ["KIT_CSS", "KIT_DEFS"]

# arrowheads the author can reference without writing <defs>: marker-end="url(#arrow)" / #arrow-primary / #arrow-link
KIT_DEFS = (
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'
    '<marker id="arrow" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0,9 3.5,0 7"/></marker>'
    '<marker id="arrow-primary" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0,9 3.5,0 7"/></marker>'
    '<marker id="arrow-link" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0,9 3.5,0 7"/></marker>'
    "</defs></svg>"
)

KIT_CSS = """
#arrow polygon{fill:var(--muted)}#arrow-primary polygon{fill:var(--accent)}#arrow-link polygon{fill:var(--link,var(--secondary))}
.eyebrow,.label,.tag,.sub,.meta,.badge,.cat{font-family:var(--font-mono);font-weight:500;text-transform:uppercase;letter-spacing:.14em;line-height:1.2;font-style:normal}
.eyebrow{font-size:13px;letter-spacing:.18em;color:var(--muted)}
.label{display:inline-block;font-size:13px;letter-spacing:.06em;color:var(--muted);background:var(--bg);padding:2px 6px}
.tag{display:inline-block;font-size:12px;letter-spacing:.08em;color:var(--muted);border:1px solid var(--border);border-radius:2px;padding:3px 6px}
.sub,.meta{text-transform:none;font-weight:400;letter-spacing:0;font-size:14px;color:var(--muted)}
.muted{color:var(--muted)}
text.eyebrow,text.label,text.tag,text.sub,text.meta,text.cat{fill:var(--muted)}
text.cat{font-family:var(--font-body);font-weight:600;font-size:15px;letter-spacing:.06em;fill:var(--primary);text-anchor:middle}
text.sub{fill:var(--muted);font-size:14px}
text.cat.hot{fill:var(--accent)}
.node{display:block;background:var(--card-fill,var(--surface,#fff));border:1px solid var(--secondary);border-radius:4px;padding:10px 14px;color:var(--primary);fill:var(--card-fill,var(--surface,#fff));stroke:var(--secondary);stroke-width:1;rx:4px}
.node b{display:block;font-family:var(--font-body);font-weight:600;font-size:19px;line-height:1.25;color:var(--primary)}
.node .tag{margin:0 0 6px}
.node .sub{margin-top:3px}
.node.focal{background:rgba(var(--accent-rgb),.08);border-color:var(--accent);fill:rgba(var(--accent-rgb),.08);stroke:var(--accent)}
.node.focal .tag{color:var(--accent);border-color:var(--accent)}
.node.store{background:rgba(var(--fg-rgb),.05);border-color:var(--muted);fill:rgba(var(--fg-rgb),.05);stroke:var(--muted)}
.node.external{background:rgba(var(--fg-rgb),.03);border-color:var(--border);fill:rgba(var(--fg-rgb),.03);stroke:var(--border)}
.node.input{background:rgba(var(--secondary-rgb),.1);border-color:var(--muted);fill:rgba(var(--secondary-rgb),.1);stroke:var(--muted)}
.node.optional{background:transparent;border-style:dashed;border-color:var(--muted);fill:none;stroke:var(--muted);stroke-dasharray:4 3}
.node.security{background:rgba(var(--accent-rgb),.05);border-style:dashed;border-color:var(--accent);fill:rgba(var(--accent-rgb),.05);stroke:var(--accent);stroke-dasharray:4 4}
.stack{display:flex;flex-direction:column;justify-content:var(--stack-justify,flex-start);gap:14px;height:100%}
.stack>.grow,.stack>.board{flex:var(--board-flex,1);min-height:0}
.board{display:flex;gap:20px;align-items:var(--board-align,stretch)}
.board>*{flex:1;min-width:0}
.eyebrow.rule{border-bottom:1px solid var(--border);padding-bottom:8px}
.col{flex:1;display:flex;flex-direction:column;gap:12px;background:rgba(var(--fg-rgb),.04);border-radius:6px;padding-bottom:16px}
.col>header{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border);font-family:var(--font-body);font-weight:600;font-size:19px;color:var(--primary)}
.col>.card{margin:0 16px}
.badge{display:inline-block;font-size:13px;letter-spacing:.06em;color:var(--muted);border:1px solid var(--border);border-radius:3px;padding:2px 10px}
.badge.over{color:var(--accent);border-color:var(--accent)}
.card{background:var(--card-fill,var(--surface,#fff));border:1px solid var(--secondary);border-radius:6px;padding:12px 14px;color:var(--primary)}
.card b{display:block;font-family:var(--font-body);font-weight:600;font-size:17px;line-height:1.25;color:var(--primary)}
.card .meta{margin-top:5px;color:var(--secondary)}
.card.blocked{background:rgba(var(--accent-rgb),.08);border:1px dashed var(--accent);border-left:5px solid var(--accent)}
.card.wait{background:rgba(var(--fg-rgb),.03);border:1px dashed var(--border);color:var(--muted)}
.card.wait b{color:var(--muted)}
.card.done{background:rgba(var(--secondary-rgb),.1)}
.legend{display:flex;flex-wrap:wrap;align-items:center;gap:8px 36px;border-top:1px solid var(--border);padding-top:10px;font-family:var(--font-body);font-size:15px;color:var(--muted)}
.legend>.eyebrow{flex-basis:100%;font-size:12px}
.legend>span{display:inline-flex;align-items:center;gap:8px}
.legend .node,.legend .card{display:block;width:28px;height:15px;padding:0;border-radius:3px}
.legend .card.blocked{border-left-width:4px}
.legend .badge{width:28px;height:15px;padding:0}
.key{display:block;width:28px;height:0;border-top:2px solid var(--primary)}
.key.accent{border-color:var(--accent)}
.key.soft{border-color:var(--border);border-top-width:3px}
svg .arrow,svg .bone,svg .tick{fill:none;stroke-width:1.5}
svg .arrow{stroke:var(--muted);marker-end:url(#arrow)}
svg .arrow.primary{stroke:var(--accent);marker-end:url(#arrow-primary)}
svg .arrow.link{stroke:var(--link,var(--secondary));marker-end:url(#arrow-link)}
svg .arrow.return{stroke-dasharray:5 4}
svg .bone{stroke:var(--primary);stroke-width:1.5}
svg .bone.accent{stroke:var(--accent)}
svg .bone.main{marker-end:url(#arrow)}
svg .tick{stroke:var(--border);stroke-width:2}
svg .dash{stroke-dasharray:5 4}
svg .dot{fill:var(--primary)}
svg .dot.hot{fill:var(--accent)}
:is(:lang(ja),:lang(zh),:lang(ko)) :is(.eyebrow,.label,.tag,.sub,.meta,.badge,.cat){font-family:var(--font-body);text-transform:none;letter-spacing:0;font-size:15px}
:is(:lang(ja),:lang(zh),:lang(ko)) .eyebrow{font-size:12px;letter-spacing:.16em}
"""
