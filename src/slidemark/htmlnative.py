"""Raw HTML block -> native, editable shapes, measured by headless Chromium (extra ``slidemark[html]``).

The HTML is laid out in a Chromium page whose viewport equals the block (96 dpi). One ``page.evaluate`` walk
returns boxes (background / border / radius), text groups (runs with bold, italic, color, size, family),
lists and ``<img>`` rects; :func:`html_to_placed` maps them to ``Placed`` items (Shape / Text / Image) offset by
the block origin. Text frames have zero padding and no autofit so they sit where the browser put the text.

Never raises: returns ``None`` when the browser is unavailable or nothing could be measured, and the caller
keeps the image fallback. See :func:`convertible` for what is deliberately left to the image path.
"""

# ruff: noqa: E501  (the embedded JavaScript keeps long lines)
from __future__ import annotations

import atexit
import base64
import re
import shutil
import tempfile
from pathlib import Path

from .ir import Diagnostic, Image, Paragraph, Placed, Run, Shape, Style, Text
from .theme import Theme

__all__ = ["convertible", "html_to_placed"]

EMU_PER_PX = 9525
PT_PER_PX = 0.75
MAX_ITEMS = 600

# Constructs that Chromium can draw but PowerPoint shapes cannot: keep the picture for these.
_UNSUPPORTED_TAGS = re.compile(
    r"<\s*(svg|canvas|video|audio|iframe|object|embed|math|picture|input|select|textarea)\b", re.I
)
_UNSUPPORTED_CSS = re.compile(
    r"gradient\s*\(|\btransform\s*:|\bfilter\s*:|backdrop-filter|clip-path|mask(-image)?\s*:|"
    r"background(-image)?\s*:[^;\"}]*url\s*\(|\bmix-blend-mode|\bwriting-mode\s*:\s*vertical",
    re.I,
)


def convertible(html: str) -> bool:
    """True when the HTML only uses things that map to native shapes.

    Image fallback is kept for ``<canvas>``, ``<svg>``, ``<video>``/``<audio>``, ``<iframe>``/``<object>``/
    ``<embed>``, MathML, form controls, gradients, CSS transforms/filters/masks/clip-path, CSS background
    images and vertical writing modes.
    """
    return not (_UNSUPPORTED_TAGS.search(html) or _UNSUPPORTED_CSS.search(html))


_JS = r"""
() => {
const out = [];
const px = (v) => parseFloat(v) || 0;
const hex = (c) => {
  const m = /rgba?\(([^)]+)\)/.exec(c || '');
  if (!m) return null;
  const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
  const a = p.length > 3 ? p[3] : 1;
  if (a < 0.02) return null;
  return ['#' + [0, 1, 2].map((i) => Math.round(p[i]).toString(16).padStart(2, '0')).join(''), a];
};
const SKIP = new Set(['SCRIPT', 'STYLE', 'HEAD', 'TEMPLATE', 'NOSCRIPT', 'META', 'LINK', 'TITLE']);
const BLOCKISH = 'img,ul,ol,div,p,table,h1,h2,h3,h4,h5,h6,li,section,pre,blockquote,header,footer';
const SIDES = ['Top', 'Right', 'Bottom', 'Left'];

function emitBox(cs, r) {
  if (r.width < 1 || r.height < 1) return;
  const bg = hex(cs.backgroundColor);
  const bw = SIDES.map((s) => (['none', 'hidden'].includes(cs['border' + s + 'Style']) ? 0 : px(cs['border' + s + 'Width'])));
  const bc = SIDES.map((s) => hex(cs['border' + s + 'Color']));
  const uniform = bw[0] > 0 && bw.every((v) => v === bw[0]) && bc[0] && bc.every((c) => c && c[0] === bc[0][0]);
  let rad = cs.borderTopLeftRadius || '0px';
  rad = rad.endsWith('%') ? (parseFloat(rad) / 100) * Math.min(r.width, r.height) : px(rad);
  if (bg || uniform) {
    out.push({k: 'rect', x: r.left, y: r.top, w: r.width, h: r.height,
      fill: bg && bg[0], alpha: bg ? bg[1] : 1,
      line: uniform ? bc[0][0] : null, lw: uniform ? bw[0] : 0, rad});
  }
  if (!uniform) {
    const g = [[0, r.left, r.top, r.width, bw[0]], [2, r.left, r.bottom - bw[2], r.width, bw[2]],
               [3, r.left, r.top, bw[3], r.height], [1, r.right - bw[1], r.top, bw[1], r.height]];
    for (const [i, x, y, w, h] of g) {
      if (bw[i] > 0 && bc[i]) out.push({k: 'rect', x, y, w, h, fill: bc[i][0], alpha: 1, line: null, lw: 0, rad: 0});
    }
  }
}

function fam(cs) {
  const f = (cs.fontFamily || '').split(',')[0].trim().replace(/^['"]|['"]$/g, '');
  return f;
}

function runOf(text, el, cs) {
  const tt = cs.textTransform;
  if (tt === 'uppercase') text = text.toUpperCase();
  else if (tt === 'lowercase') text = text.toLowerCase();
  const col = hex(cs.color);
  const bgc = el.tagName !== 'BODY' && cs.display === 'inline' ? hex(cs.backgroundColor) : null;
  const deco = cs.textDecorationLine || '';
  let href = null;
  for (let e = el; e && e.tagName !== 'BODY'; e = e.parentElement) {
    if (e.tagName === 'A' && e.getAttribute('href')) { href = e.getAttribute('href'); break; }
  }
  const f = fam(cs);
  return {t: text, b: parseInt(cs.fontWeight, 10) >= 600 || cs.fontWeight === 'bold',
    i: cs.fontStyle === 'italic' || cs.fontStyle === 'oblique', u: deco.includes('underline'),
    s: deco.includes('line-through'), c: col && col[0], hl: bgc && bgc[0],
    sup: cs.verticalAlign === 'super', sub: cs.verticalAlign === 'sub',
    mono: /mono|courier|consolas/i.test(cs.fontFamily || ''), href, fs: px(cs.fontSize), ff: f};
}

function collect(node, runs, skipLists) {
  if (node.nodeType === 3) {
    const cs = getComputedStyle(node.parentElement);
    const pre = cs.whiteSpace.startsWith('pre');
    let t = node.nodeValue;
    if (!pre) t = t.replace(/[ \t\r\n\f]+/g, ' ');
    if (t) runs.push(runOf(t, node.parentElement, cs));
  } else if (node.nodeType === 1) {
    const cs = getComputedStyle(node);
    if (cs.display === 'none' || SKIP.has(node.tagName)) return;
    if (skipLists && (node.tagName === 'UL' || node.tagName === 'OL')) return;
    if (node.tagName === 'BR') { runs.push(runOf('\n', node, cs)); return; }
    if (node.tagName === 'IMG') return;
    if (!cs.display.startsWith('inline') && runs.length && runs[runs.length - 1].t !== '\n') runs.push(runOf(' ', node, cs));
    for (const c of node.childNodes) collect(c, runs, skipLists);
  }
}

function tidy(runs) {
  // collapse whitespace across run boundaries, trim the ends
  let prevSpace = true;
  for (const r of runs) {
    if (r.t === '\n') { prevSpace = true; continue; }
    if (prevSpace) r.t = r.t.replace(/^ +/, '');
    prevSpace = r.t.endsWith(' ');
  }
  for (let i = runs.length - 1; i >= 0; i--) {
    if (runs[i].t === '\n') continue;
    runs[i].t = runs[i].t.replace(/ +$/, '');
    if (runs[i].t) break;
  }
  const res = runs.filter((r) => r.t !== '');
  while (res.length && res[res.length - 1].t === '\n') res.pop();
  return res;
}

function lineH(cs) {
  const fs = px(cs.fontSize);
  return cs.lineHeight === 'normal' ? fs * 1.2 : px(cs.lineHeight);
}

function content(el, cs, r) {
  return {l: r.left + px(cs.borderLeftWidth) + px(cs.paddingLeft), rt: r.right - px(cs.borderRightWidth) - px(cs.paddingRight),
          b: r.bottom - px(cs.borderBottomWidth) - px(cs.paddingBottom)};
}

function emitGroup(el, cs, nodes) {
  const runs = [];
  for (const n of nodes) collect(n, runs, false);
  const rs = tidy(runs);
  if (!rs.length) return;
  const range = document.createRange();
  range.setStartBefore(nodes[0]);
  range.setEndAfter(nodes[nodes.length - 1]);
  const rr = range.getBoundingClientRect();
  if (rr.width < 0.5 || rr.height < 0.5) return;
  const r = el.getBoundingClientRect();
  const c = content(el, cs, r);
  const first = rs.find((x) => x.t !== '\n');
  const lh = lineH(cs);
  let x = Math.min(c.l, rr.left), w = Math.max(c.rt, rr.right) - x;
  const align = cs.textAlign === 'start' ? 'left' : cs.textAlign === 'end' ? 'right' : cs.textAlign;
  if (rr.height < lh * 1.6) {  // one line: a little slack so font differences do not wrap it
    const slack = 8;
    w += slack;
    if (align === 'right' || align === 'center') x -= align === 'right' ? slack : slack / 2;
  }
  out.push({k: 'text', x, y: rr.top, w, h: rr.height, align, lh, fs: first.fs, ff: first.ff,
    paras: [{runs: rs, marker: null, level: 0, fs: first.fs}]});
}

function listItems(listEl, level, paras, st) {
  const ordered = listEl.tagName === 'OL';
  for (const li of listEl.children) {
    if (li.tagName !== 'LI') continue;
    const cs = getComputedStyle(li);
    if (cs.display === 'none') continue;
    const none = getComputedStyle(listEl).listStyleType === 'none' && cs.listStyleType === 'none';
    const runs = tidy((() => { const a = []; for (const n of li.childNodes) collect(n, a, true); return a; })());
    const r = li.getBoundingClientRect();
    if (runs.length) {
      const first = runs.find((x) => x.t !== '\n');
      paras.push({runs, marker: none ? null : (ordered ? 'number' : 'bullet'), level, fs: first.fs});
      if (!st.n) { st.n = 1; st.x = r.left; st.y = r.top; st.lh = lineH(cs); st.fs = first.fs; st.ff = first.ff;
                   st.align = cs.textAlign === 'start' ? 'left' : cs.textAlign; st.none = none; }
      st.bottom = Math.max(st.bottom || 0, r.bottom);
    }
    for (const sub of li.children) {
      if (sub.tagName === 'UL' || sub.tagName === 'OL') listItems(sub, level + 1, paras, st);
    }
  }
}

function emitList(el, cs, r) {
  const paras = [], st = {};
  listItems(el, 0, paras, st);
  if (!paras.length) return;
  const hang = st.none ? 0 : st.fs * 1.3;
  const c = content(el, cs, r);
  const x = st.x - hang;
  out.push({k: 'text', x, y: st.y, w: Math.max(c.rt - x, r.right - x), h: Math.max(st.bottom - st.y, 1),
    align: st.align, lh: st.lh, fs: st.fs, ff: st.ff, paras});
}

function emitImg(el, r) {
  const src = el.getAttribute('src') || '';
  if (!src || /^[a-z][a-z0-9+.-]*:/i.test(src) && !src.startsWith('data:')) return;
  if (r.width < 1 || r.height < 1) return;
  out.push({k: 'img', x: r.left, y: r.top, w: r.width, h: r.height, src, alt: el.getAttribute('alt') || ''});
}

function walk(el) {
  if (SKIP.has(el.tagName)) return;
  const cs = getComputedStyle(el);
  if (cs.display === 'none' || cs.visibility === 'hidden') return;
  const r = el.getBoundingClientRect();
  if (el !== document.body) emitBox(cs, r);
  if (el.tagName === 'IMG') { emitImg(el, r); return; }
  if (el.tagName === 'UL' || el.tagName === 'OL') { emitList(el, cs, r); return; }
  let group = [];
  const flush = () => { if (group.length) emitGroup(el, cs, group); group = []; };
  for (const n of el.childNodes) {
    if (n.nodeType === 3) group.push(n);
    else if (n.nodeType === 1) {
      if (SKIP.has(n.tagName)) continue;
      const ncs = getComputedStyle(n);
      if (ncs.display === 'none') continue;
      const inline = ncs.display === 'inline' && n.tagName !== 'IMG' && !n.querySelector(BLOCKISH);
      if (inline) group.push(n); else { flush(); walk(n); }
    }
  }
  flush();
}

walk(document.body);
return {items: out.slice(0, 2000), count: out.length, sw: document.documentElement.scrollWidth,
        sh: document.documentElement.scrollHeight};
}
"""


def _color(c: str | None) -> str | None:
    return c.upper() if c else None


def _tmpdir() -> Path:
    d = tempfile.mkdtemp(prefix="slidemark-html-")
    atexit.register(shutil.rmtree, d, ignore_errors=True)
    return Path(d)


def _runs(raw: list[dict], default_color: str | None) -> list[Run]:
    runs: list[Run] = []
    for r in raw:
        link = r.get("href")
        runs.append(
            Run(
                text=r["t"],
                bold=bool(r["b"]),
                italic=bool(r["i"]),
                underline=bool(r["u"]),
                strike=bool(r["s"]),
                sup=bool(r["sup"]),
                sub=bool(r["sub"]),
                code=bool(r["mono"]),
                color=_color(r["c"]) or default_color,
                highlight=_color(r["hl"]),
                link=link if link and link.startswith(("http://", "https://", "mailto:")) else None,
            )
        )
    return runs


def _text(it: dict, ox: int, oy: int, theme: Theme) -> Placed:
    first = it["paras"][0]["runs"][0]
    fs_pt = round(it["fs"] * PT_PER_PX, 2)
    spacing = it["lh"] / (it["fs"] * 1.2) if it["fs"] else 1.0
    st = Style(
        font_size=fs_pt,
        color=_color(first["c"]),
        align=it["align"] if it["align"] in ("left", "center", "right", "justify") else "left",
        line_spacing=round(spacing, 2) if abs(spacing - 1.0) > 0.04 else None,
        font=it["ff"] if it["ff"] and it["ff"].lower() not in {"sans-serif", "serif", "monospace"} else None,
        padding=0,
    )
    paras = [
        Paragraph(
            runs=_runs(p["runs"], None),
            marker=p["marker"],
            level=min(p["level"], 3),
            style=Style(font_size=round(p["fs"] * PT_PER_PX, 2)),
        )
        for p in it["paras"]
    ]
    return Placed(
        element=Text(role="body", paragraphs=paras),
        x=ox + round(it["x"] * EMU_PER_PX),
        y=oy + round(it["y"] * EMU_PER_PX),
        w=round(it["w"] * EMU_PER_PX),
        h=round(it["h"] * EMU_PER_PX),
        style=st,
    )


def _rect(it: dict, ox: int, oy: int) -> Placed:
    w, h, rad = it["w"], it["h"], it["rad"]
    shape = "rect"
    if rad > 0.5:
        shape = "ellipse" if abs(w - h) < 1 and rad >= min(w, h) / 2 - 0.5 else "rounded-rect"
    st = Style(
        fill=_color(it["fill"]),
        line=_color(it["line"]),
        line_width=round(it["lw"] * PT_PER_PX, 2) if it["line"] else None,
        radius=round(min(rad, min(w, h) / 2) * PT_PER_PX, 2) if shape == "rounded-rect" else None,
        opacity=it["alpha"] if it["fill"] and it["alpha"] < 0.99 else None,
    )
    return Placed(
        element=Shape(shape=shape),
        x=ox + round(it["x"] * EMU_PER_PX),
        y=oy + round(it["y"] * EMU_PER_PX),
        w=max(round(w * EMU_PER_PX), 1),
        h=max(round(h * EMU_PER_PX), 1),
        style=st,
    )


def _image(it: dict, ox: int, oy: int, tmp: list[Path]) -> Placed | None:
    src = it["src"]
    if src.startswith("data:"):
        m = re.match(r"data:image/([a-z0-9.+-]+)(;base64)?,(.*)$", src, re.S | re.I)
        if not m:
            return None
        ext = {"jpeg": "jpg", "svg+xml": "svg"}.get(m.group(1).lower(), m.group(1).lower())
        if ext not in ("png", "jpg", "gif", "bmp", "webp"):
            return None
        try:
            data = base64.b64decode(m.group(3)) if m.group(2) else m.group(3).encode("latin-1")
        except Exception:
            return None
        if not tmp:
            tmp.append(_tmpdir())
        path = tmp[0] / f"img{len(list(tmp[0].iterdir())) + 1}.{ext}"
        path.write_bytes(data)
        src = str(path)
    return Placed(
        element=Image(src=src, alt=it.get("alt", ""), fit="stretch"),
        x=ox + round(it["x"] * EMU_PER_PX),
        y=oy + round(it["y"] * EMU_PER_PX),
        w=round(it["w"] * EMU_PER_PX),
        h=round(it["h"] * EMU_PER_PX),
    )


def html_to_placed(
    html: str,
    x: int,
    y: int,
    w: int,
    h: int,
    theme: Theme,
    base_dir: str = ".",
    *,
    renderer=None,
) -> tuple[list[Placed], list[Diagnostic]] | None:
    """Lay ``html`` out in Chromium at ``w`` x ``h`` EMU and return native Placed items (absolute EMU).

    ``None`` when Playwright/Chromium is unavailable or nothing visible was measured. Pass a shared
    ``renderer`` (``HtmlRenderer``) so a deck launches one browser. Never raises.
    """
    own = None
    try:
        if renderer is None:
            from .render.htmlimg import HtmlRenderer

            renderer = own = HtmlRenderer()
        w_px, h_px = max(round(w / EMU_PER_PX), 1), max(round(h / EMU_PER_PX), 1)
        data = renderer.evaluate(html, w_px, h_px, theme, _JS)
        if not data or not data.get("items"):
            return None
        placed: list[Placed] = []
        diags: list[Diagnostic] = []
        tmp: list[Path] = []
        clipped = 0
        for it in data["items"]:
            if it["x"] >= w_px or it["y"] >= h_px:
                clipped += 1
                continue
            try:
                if it["k"] == "rect":
                    placed.append(_rect(it, x, y))
                elif it["k"] == "text":
                    placed.append(_text(it, x, y, theme))
                elif it["k"] == "img":
                    pl = _image(it, x, y, tmp)
                    if pl is not None:
                        placed.append(pl)
            except Exception:
                continue
        if data.get("count", 0) > len(data["items"]) or len(placed) > MAX_ITEMS:
            return None
        if clipped or data.get("sh", 0) > h_px + 2 or data.get("sw", 0) > w_px + 2:
            diags.append(
                Diagnostic(
                    level="warning",
                    message="HTML content is larger than its block and was cut off",
                    rule="html-native-overflow",
                    hint="shorten the HTML, split it over two blocks, or give the block more room ({h=...})",
                )
            )
        return (placed, diags) if placed else None
    except Exception:
        return None
    finally:
        if own is not None:
            own.close()
