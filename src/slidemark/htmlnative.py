"""HTML -> native, editable shapes, measured by headless Chromium (extra ``slidemark[html]``).

The HTML is laid out in a Chromium page whose viewport equals the block (96 dpi). One ``page.evaluate`` walk
returns boxes (solid / gradient background, border, radius, shadow, opacity), text groups (runs with bold,
italic, color, size, family; inline pills become rounded rectangles behind the run), lists, ``<img>`` rects and
inline ``<svg>`` shapes; :func:`html_to_placed` maps them to ``Placed`` items (Shape / Text / Image) offset by
the block origin. Text frames have zero padding and no autofit so they sit where the browser put the text.

Mapped natively: ``linear-/radial-gradient`` (``Style.fill`` carries the CSS string), ``box-shadow``
(``Style.shadow``), ``opacity`` (fill alpha; text colors are blended with the background below them),
``transform: rotate()/scale()/translate()`` (``Style.rotation``; children of a rotated element move with it),
``border-radius`` 50% (ellipse), ``clip-path`` pentagon / chevron polygons or ``circle()``, SVG ``rect`` /
``circle`` / ``ellipse`` / ``line`` / ``text``, stroked ``polyline`` / ``polygon`` / ``path`` (chains of lines),
isosceles-triangle polygons. What PowerPoint cannot draw (``<canvas>``-like elements, filters, masks, blend
modes, other clip paths, background images, skew, vertical text, filled free-form SVG paths) becomes a
*per-element picture* (a transparent PNG of just that element) plus an ``html-element-image`` info
diagnostic naming the element, never a whole-slide picture.

Never raises: returns ``None`` when the browser is unavailable or nothing could be measured, and the caller
keeps the image fallback. See :func:`convertible` for the few things that still go to the image path.
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
MAX_PICTURES = 40

# Elements whose content is not markup Chromium can lay out for us (replaced / scripted media): the whole
# block stays one picture. Everything else Chromium draws and shapes cannot is a per-element picture.
_UNSUPPORTED_TAGS = re.compile(r"<\s*(canvas|video|audio|iframe|object|embed)\b", re.I)


def convertible(html: str) -> bool:
    """False for ``<canvas>``, ``<video>``/``<audio>``, ``<iframe>``/``<object>``/``<embed>`` (kept as one image).

    Gradients, shadows, transforms, ``<svg>``, clip paths, filters, masks and background images are handled
    per element by :func:`html_to_placed`.
    """
    return not _UNSUPPORTED_TAGS.search(html)


_JS = r"""
() => {
const out = [];
const picEls = [];
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
const PIC_TAGS = new Set(['canvas', 'video', 'audio', 'iframe', 'object', 'embed', 'math', 'select', 'textarea', 'input', 'picture']);
const BLOCKISH = 'img,ul,ol,div,p,table,h1,h2,h3,h4,h5,h6,li,section,pre,blockquote,header,footer';
const SIDES = ['Top', 'Right', 'Bottom', 'Left'];
const PILL = new Set();
const CLIPTEXT = new Map();
let chain = [];

function splitTop(s) {
  const parts = []; let depth = 0, cur = '';
  for (const ch of s) {
    if (ch === '(') depth++;
    else if (ch === ')') depth = Math.max(0, depth - 1);
    if (ch === ',' && depth === 0) { parts.push(cur.trim()); cur = ''; } else cur += ch;
  }
  if (cur.trim()) parts.push(cur.trim());
  return parts;
}

// ---- transforms: measure everything untransformed, then map centers through the ancestors' matrices
const T = new Map();
const saved = [];
for (const el of document.body.querySelectorAll('*')) {
  if (el.ownerSVGElement) continue;
  const cs = getComputedStyle(el);
  if (!cs.transform || cs.transform === 'none') continue;
  const m = /^matrix\(([^)]+)\)$/.exec(cs.transform);
  const o = (cs.transformOrigin || '0 0').split(' ').map(parseFloat);
  let t = {bad: true};
  if (m) {
    const [a, b, c, d, e, f] = m[1].split(',').map(Number);
    if (Math.abs(a - d) < 1e-3 && Math.abs(b + c) < 1e-3) {
      t = {s: Math.hypot(a, b), th: Math.atan2(b, a), e, f, ox: o[0] || 0, oy: o[1] || 0};
    }
  }
  T.set(el, t);
  saved.push([el, el.style.getPropertyValue('transform'), el.style.getPropertyPriority('transform')]);
}
for (const [el] of saved) el.style.setProperty('transform', 'none', 'important');

function xf(x, y, w, h) {
  let cx = x + w / 2, cy = y + h / 2, rot = 0, sc = 1;
  for (let i = chain.length - 1; i >= 0; i--) {
    const t = chain[i];
    const vx = cx - t.px, vy = cy - t.py, c = Math.cos(t.th), sn = Math.sin(t.th);
    cx = t.px + t.e + t.s * (c * vx - sn * vy);
    cy = t.py + t.f + t.s * (sn * vx + c * vy);
    rot += t.th; sc *= t.s;
  }
  w *= sc; h *= sc;
  return {x: cx - w / 2, y: cy - h / 2, w, h, rot: rot * 180 / Math.PI, sc};
}

function put(o) {
  if (chain.length) {
    const a = xf(o.x, o.y, o.w, o.h);
    Object.assign(o, {x: a.x, y: a.y, w: a.w, h: a.h});
    if (Math.abs(a.rot) > 0.01) o.rot = (a.rot % 360 + 360) % 360;
    if (a.sc !== 1) {
      if (o.k === 'text') { o.fs *= a.sc; o.lh *= a.sc; for (const p of o.paras) p.fs *= a.sc; }
      if (o.k === 'rect') { o.rad *= a.sc; o.lw *= a.sc; }
    }
  }
  out.push(o);
}

// ---- opacity and the background below an element (for blending text colors)
function effOp(el) {
  let v = 1;
  for (let e = el; e && e.nodeType === 1; e = e.parentElement) v *= parseFloat(getComputedStyle(e).opacity);
  return isNaN(v) ? 1 : v;
}
function bgUnder(el) {
  for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
    const h = hex(getComputedStyle(e).backgroundColor);
    if (h && h[1] >= 0.95) return h[0];
  }
  return '#ffffff';
}
function blend(h, a, el) {
  if (!h || a >= 0.98) return h;
  const b = bgUnder(el);
  const ch = (s, i) => parseInt(s.slice(1 + 2 * i, 3 + 2 * i), 16);
  return '#' + [0, 1, 2].map((i) => Math.round(ch(h, i) * a + ch(b, i) * (1 - a)).toString(16).padStart(2, '0')).join('');
}

function shadowOf(cs, op) {
  const v = cs.boxShadow;
  if (!v || v === 'none') return null;
  for (const part of splitTop(v)) {
    if (/\binset\b/.test(part)) continue;
    const m = /(rgba?\([^)]*\))/.exec(part);
    if (!m) continue;
    const col = hex(m[1]);
    if (!col) continue;
    const n = part.replace(m[1], '').trim().split(/\s+/).map(parseFloat).filter((x) => !isNaN(x));
    if (n.length < 2) continue;
    const f = (x) => +(x * 0.75).toFixed(2);
    const al = Math.round(Math.min(col[1] * op, 1) * 255).toString(16).padStart(2, '0');
    return [f(n[0]), f(n[1]), f(n[2] || 0), f(n[3] || 0), col[0] + al].join(' ');
  }
  return null;
}

function clipShape(cs, r) {
  const v = cs.clipPath;
  if (!v || v === 'none') return null;
  if (/^circle\(/.test(v) && /50%/.test(v) && !/at (?!50% 50%)/.test(v)) return 'ellipse';
  const m = /^polygon\((.*)\)$/.exec(v);
  if (!m) return null;
  const pts = splitTop(m[1]).map((p) => p.split(/\s+/).map((q, i) => (q.endsWith('%') ? parseFloat(q) / 100 : px(q) / (i ? r.height : r.width))));
  const near = (a, b) => Math.abs(a - b) < 0.02;
  if (pts.length === 5 && near(pts[0][0], 0) && near(pts[0][1], 0) && near(pts[1][1], 0) && near(pts[2][0], 1) && near(pts[2][1], 0.5) && near(pts[3][1], 1) && near(pts[4][0], 0) && near(pts[4][1], 1)) return 'pentagon';
  if (pts.length === 6 && near(pts[0][0], 0) && near(pts[0][1], 0) && near(pts[2][0], 1) && near(pts[2][1], 0.5) && near(pts[4][0], 0) && near(pts[4][1], 1) && pts[5][0] > 0.01 && near(pts[5][1], 0.5)) return 'chevron';
  return null;
}

function addPic(el, why, mode) {
  const r = el.getBoundingClientRect();
  if (r.width < 1 || r.height < 1) return;
  const n = picEls.length;
  picEls.push(el);
  el.setAttribute('data-sm-pic', String(n));
  out.push({k: 'pic', n, mode, why, tag: el.tagName.toLowerCase(), alt: (el.getAttribute('alt') || el.getAttribute('aria-label') || '')});
}

function emitBox(el, cs, r, allowPic) {
  if (r.width < 1 || r.height < 1) return;
  const op = effOp(el);
  const bg = hex(cs.backgroundColor);
  const bw = SIDES.map((s) => (['none', 'hidden'].includes(cs['border' + s + 'Style']) ? 0 : px(cs['border' + s + 'Width'])));
  const bc = SIDES.map((s) => hex(cs['border' + s + 'Color']));
  const uniform = bw[0] > 0 && bw.every((v) => v === bw[0]) && bc[0] && bc.every((c) => c && c[0] === bc[0][0]);
  const clipText = /text/.test(cs.webkitBackgroundClip || cs.backgroundClip || '');
  let grad = null, urlbg = false;
  const bi = cs.backgroundImage;
  if (bi && bi !== 'none') {
    const first = splitTop(bi)[0] || '';
    if (/^(linear|radial)-gradient\(/.test(first)) grad = first; else urlbg = true;
  }
  if (clipText) {
    if (grad) { const m = /rgba?\([^)]*\)/.exec(grad); const h = m && hex(m[0]); if (h) CLIPTEXT.set(el, h[0]); }
    grad = null; urlbg = false;
  }
  if (urlbg && allowPic) { addPic(el, 'background image', 'self'); return; }
  let rad = cs.borderTopLeftRadius || '0px';
  let pct = 0;
  if (rad.endsWith('%')) { pct = parseFloat(rad); rad = (pct / 100) * Math.min(r.width, r.height); } else rad = px(rad);
  const clip = clipShape(cs, r);
  const shape = clip === 'pentagon' || clip === 'chevron' || clip === 'ellipse' ? clip : (pct >= 50 ? 'ellipse' : null);
  const shadow = shadowOf(cs, op);
  if (bg || grad || uniform) {
    put({k: 'rect', x: r.left, y: r.top, w: r.width, h: r.height, shape,
      fill: grad ? null : bg && bg[0], grad, alpha: (bg && !grad ? bg[1] : 1) * op,
      line: uniform ? bc[0][0] : null, lw: uniform ? bw[0] : 0, rad, shadow: bg || grad ? shadow : null,
      ld: uniform ? ({dashed: 'dash', dotted: 'dot'}[cs.borderTopStyle] || null) : null});
  }
  if (!uniform) {
    const g = [[0, r.left, r.top, r.width, bw[0]], [2, r.left, r.bottom - bw[2], r.width, bw[2]],
               [3, r.left, r.top, bw[3], r.height], [1, r.right - bw[1], r.top, bw[1], r.height]];
    for (const [i, x, y, w, h] of g) {
      if (bw[i] > 0 && bc[i]) put({k: 'rect', x, y, w, h, fill: bc[i][0], alpha: 1, line: null, lw: 0, rad: 0});
    }
  }
}

function fam(cs) {
  const f = (cs.fontFamily || '').split(',')[0].trim().replace(/^['"]|['"]$/g, '');
  return f;
}

function inPill(el) {
  for (let e = el; e && e.tagName !== 'BODY'; e = e.parentElement) if (PILL.has(e)) return true;
  return false;
}

function runOf(text, el, cs) {
  const tt = cs.textTransform;
  if (tt === 'uppercase') text = text.toUpperCase();
  else if (tt === 'lowercase') text = text.toLowerCase();
  const col = hex(cs.color);
  let c = col && blend(col[0], col[1] * effOp(el), el);
  for (let e = el; e && e.tagName !== 'BODY'; e = e.parentElement) if (CLIPTEXT.has(e)) { c = CLIPTEXT.get(e); break; }
  const bgc = el.tagName !== 'BODY' && cs.display === 'inline' && !inPill(el) ? hex(cs.backgroundColor) : null;
  const deco = cs.textDecorationLine || '';
  let href = null;
  for (let e = el; e && e.tagName !== 'BODY'; e = e.parentElement) {
    if (e.tagName === 'A' && e.getAttribute('href')) { href = e.getAttribute('href'); break; }
  }
  const f = fam(cs);
  return {t: text, b: parseInt(cs.fontWeight, 10) >= 600 || cs.fontWeight === 'bold',
    i: cs.fontStyle === 'italic' || cs.fontStyle === 'oblique', u: deco.includes('underline'),
    s: deco.includes('line-through'), c, hl: bgc && bgc[0],
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
    const start = runs.length;
    for (const c of node.childNodes) collect(c, runs, skipLists);
    if (PILL.has(node) && runs.length > start) {  // keep the pill's inner padding as non-breaking spaces
      const fs = px(cs.fontSize) || 16;
      const nl = Math.round(px(cs.paddingLeft) / (0.28 * fs)), nr = Math.round(px(cs.paddingRight) / (0.28 * fs));
      runs[start].t = ' '.repeat(nl) + runs[start].t;
      runs[runs.length - 1].t += ' '.repeat(nr);
    }
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

function pills(nodes) {
  const visit = (n) => {
    if (n.nodeType !== 1) return;
    const cs = getComputedStyle(n);
    if (cs.display === 'none') return;
    if (cs.display === 'inline') {
      const bg = hex(cs.backgroundColor);
      const decorated = px(cs.borderTopLeftRadius) > 0 || px(cs.paddingLeft) + px(cs.paddingRight) > 0 || px(cs.borderTopWidth) > 0;
      if (bg && decorated) {
        PILL.add(n);
        for (const rc of n.getClientRects()) if (rc.width > 1 && rc.height > 1) emitBox(n, cs, rc, false);
      }
    }
    for (const c of n.childNodes) visit(c);
  };
  nodes.forEach(visit);
}

function emitGroup(el, cs, nodes) {
  pills(nodes);
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
  put({k: 'text', x, y: rr.top, w, h: rr.height, align, lh, fs: first.fs, ff: first.ff, ls: px(cs.letterSpacing),
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
  put({k: 'text', x, y: st.y, w: Math.max(c.rt - x, r.right - x), h: Math.max(st.bottom - st.y, 1),
    align: st.align, lh: st.lh, fs: st.fs, ff: st.ff, ls: 0, paras});
}

function emitImg(el, r) {
  const src = el.getAttribute('src') || '';
  if (!src || /^[a-z][a-z0-9+.-]*:/i.test(src) && !src.startsWith('data:')) return;
  if (r.width < 1 || r.height < 1) return;
  put({k: 'img', x: r.left, y: r.top, w: r.width, h: r.height, src, alt: el.getAttribute('alt') || ''});
}

// ---- inline SVG: simple shapes become native shapes, anything else keeps the <svg> as one picture
function rdp(pts, eps) {
  if (pts.length < 3) return pts;
  const keep = new Array(pts.length).fill(false);
  keep[0] = keep[pts.length - 1] = true;
  const stack = [[0, pts.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop();
    let dmax = 0, idx = -1;
    const [x1, y1] = pts[a], [x2, y2] = pts[b];
    const len = Math.hypot(x2 - x1, y2 - y1) || 1e-9;
    for (let i = a + 1; i < b; i++) {
      const d = Math.abs((x2 - x1) * (y1 - pts[i][1]) - (x1 - pts[i][0]) * (y2 - y1)) / len;
      if (d > dmax) { dmax = d; idx = i; }
    }
    if (dmax > eps && idx > 0) { keep[idx] = true; stack.push([a, idx], [idx, b]); }
  }
  return pts.filter((_, i) => keep[i]);
}

function emitSvg(el, cs, r) {
  if (r.width < 1 || r.height < 1) return;
  if (chain.length) { addPic(el, 'svg inside a transformed element', 'tree'); return; }
  const items = [];
  let bad = null;
  const SKIPT = new Set(['defs', 'title', 'desc', 'metadata', 'style', 'lineargradient', 'radialgradient', 'clippath', 'marker', 'symbol', 'pattern', 'mask']);
  const tpt = (m, x, y) => [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f];
  const col = (v) => (v && v !== 'none' ? hex(v) : null);
  const visit = (n) => {
    if (bad) return;
    const t = n.tagName.toLowerCase();
    if (SKIPT.has(t)) return;
    const g = getComputedStyle(n);
    if (g.display === 'none' || g.visibility === 'hidden') return;
    const m = n.getScreenCTM && n.getScreenCTM();
    if (!m) { bad = 'no geometry'; return; }
    if (Math.abs(m.b) > 1e-3 || Math.abs(m.c) > 1e-3) { bad = 'rotated or skewed shape'; return; }
    if (t === 'g' || t === 'a') { for (const c of n.children) visit(c); return; }
    if (/url\(/.test(g.fill + g.stroke) || (g.filter && g.filter !== 'none') || (g.clipPath && g.clipPath !== 'none')) { bad = 'gradient, filter or clip'; return; }
    const op = parseFloat(g.opacity);
    const f = col(g.fill), s = col(g.stroke);
    const fa = f ? f[1] * parseFloat(g.fillOpacity) * op : 0;
    const sc = Math.hypot(m.a, m.b);
    const lw = s ? parseFloat(g.strokeWidth) * sc : 0;
    const base = {fill: f && f[0], alpha: fa || 1, line: s && s[0], lw, rad: 0};
    const arrow = g.markerEnd && g.markerEnd !== 'none';
    if (t === 'rect') {
      const [x, y] = tpt(m, n.x.baseVal.value, n.y.baseVal.value);
      const w = n.width.baseVal.value * Math.abs(m.a), h = n.height.baseVal.value * Math.abs(m.d);
      if (!f && !s) return;
      const rx = (n.rx.baseVal.value || n.ry.baseVal.value) * Math.abs(m.a);
      items.push({k: 'rect', x, y, w, h, ...base, rad: rx});
    } else if (t === 'circle' || t === 'ellipse') {
      const rx = (t === 'circle' ? n.r.baseVal.value : n.rx.baseVal.value) * Math.abs(m.a);
      const ry = (t === 'circle' ? n.r.baseVal.value : n.ry.baseVal.value) * Math.abs(m.d);
      const [cx, cy] = tpt(m, n.cx.baseVal.value, n.cy.baseVal.value);
      if (!f && !s) return;
      items.push({k: 'rect', x: cx - rx, y: cy - ry, w: 2 * rx, h: 2 * ry, shape: 'ellipse', ...base});
    } else if (t === 'line') {
      if (!s) return;
      const [x1, y1] = tpt(m, n.x1.baseVal.value, n.y1.baseVal.value), [x2, y2] = tpt(m, n.x2.baseVal.value, n.y2.baseVal.value);
      items.push({k: 'line', x1, y1, x2, y2, color: s[0], lw, head: arrow ? 'arrow' : 'none'});
    } else if (t === 'polyline' || t === 'polygon' || t === 'path') {
      let pts = [];
      let closed = t === 'polygon';
      if (t === 'path') {
        const len = n.getTotalLength();
        if (!(len > 0)) return;
        const N = Math.min(Math.ceil(len / 2), 400);
        for (let i = 0; i <= N; i++) { const p = n.getPointAtLength(len * i / N); pts.push(tpt(m, p.x, p.y)); }
        closed = /[zZ]\s*$/.test(n.getAttribute('d') || '');
        pts = rdp(pts, 0.6);
      } else {
        for (let i = 0; i < n.points.numberOfItems; i++) { const p = n.points.getItem(i); pts.push(tpt(m, p.x, p.y)); }
      }
      if (closed && pts.length > 1 && Math.hypot(pts[0][0] - pts[pts.length - 1][0], pts[0][1] - pts[pts.length - 1][1]) < 0.5) pts.pop();
      let area = 0;
      for (let i = 0; i < pts.length; i++) { const a = pts[i], b = pts[(i + 1) % pts.length]; area += a[0] * b[1] - b[0] * a[1]; }
      if (!f && !s) return;
      if (f && fa > 0.02 && Math.abs(area) / 2 > 2) {  // an open straight path has no area: its default black fill is invisible
        let tri = null;
        if (pts.length === 3) {
          for (let i = 0; i < 3 && !tri; i++) {
            const a = pts[i], b = pts[(i + 1) % 3], c = pts[(i + 2) % 3];
            const d1 = Math.hypot(a[0] - b[0], a[1] - b[1]), d2 = Math.hypot(a[0] - c[0], a[1] - c[1]);
            if (Math.abs(d1 - d2) <= 0.06 * Math.max(d1, d2)) tri = [a, b, c];
          }
        }
        if (!tri) { bad = 'filled free-form path'; return; }
        const [a, b, c] = tri;
        const mx = (b[0] + c[0]) / 2, my = (b[1] + c[1]) / 2;
        const bw = Math.hypot(b[0] - c[0], b[1] - c[1]), bh = Math.hypot(a[0] - mx, a[1] - my);
        const cx = (a[0] + mx) / 2, cy = (a[1] + my) / 2;
        const rot = (Math.atan2(a[0] - mx, -(a[1] - my)) * 180 / Math.PI + 360) % 360;
        items.push({k: 'rect', x: cx - bw / 2, y: cy - bh / 2, w: bw, h: bh, shape: 'triangle', rot, ...base});
        return;
      }
      const segs = pts.length - 1 + (closed && pts.length > 2 ? 1 : 0);
      if (segs > 24) { bad = 'path with many segments'; return; }
      for (let i = 0; i < segs; i++) {
        const a = pts[i], b = pts[(i + 1) % pts.length];
        items.push({k: 'line', x1: a[0], y1: a[1], x2: b[0], y2: b[1], color: s[0], lw, head: i === segs - 1 && arrow ? 'arrow' : 'none'});
      }
    } else if (t === 'text') {
      const txt = n.textContent.replace(/\s+/g, ' ').trim();
      if (!txt || !f) return;
      if (n.querySelector('[dy],[y]')) { bad = 'multi-line svg text'; return; }
      const b = n.getBoundingClientRect();
      const fs = parseFloat(g.fontSize) * Math.abs(m.d);
      const anchor = g.textAnchor === 'middle' ? 'center' : g.textAnchor === 'end' ? 'right' : 'left';
      const run = {t: txt, b: parseInt(g.fontWeight, 10) >= 600, i: g.fontStyle === 'italic', u: false, s: false, c: f[0],
        hl: null, sup: false, sub: false, mono: /mono|courier|consolas/i.test(g.fontFamily || ''), href: null, fs, ff: fam(g)};
      let x = b.left, w = b.width + 8;
      if (anchor === 'center') x -= 4; else if (anchor === 'right') x -= 8;
      items.push({k: 'text', x, y: b.top, w, h: b.height, align: anchor, lh: b.height, fs, ff: run.ff, ls: 0,
        paras: [{runs: [run], marker: null, level: 0, fs}]});
    } else {
      bad = '<' + t + '>';
    }
  };
  for (const c of el.children) visit(c);
  if (bad) { addPic(el, 'svg: ' + bad, 'tree'); return; }
  for (const it of items) put(it);
}

function treeReason(cs, r) {
  if (cs.filter && cs.filter !== 'none') return 'filter';
  if ((cs.webkitMaskImage && cs.webkitMaskImage !== 'none') || (cs.maskImage && cs.maskImage !== 'none')) return 'mask';
  if (cs.mixBlendMode && cs.mixBlendMode !== 'normal') return 'mix-blend-mode';
  if ((cs.writingMode || '').startsWith('vertical')) return 'vertical text';
  if (cs.clipPath && cs.clipPath !== 'none' && !clipShape(cs, r)) return 'clip-path';
  return null;
}

function walkInner(el, cs, r) {
  const tag = el.tagName.toLowerCase();
  if (PIC_TAGS.has(tag)) { addPic(el, '<' + tag + '>', 'tree'); return; }
  if (tag === 'svg') { emitSvg(el, cs, r); return; }
  const why = treeReason(cs, r);
  if (why) { addPic(el, why, 'tree'); return; }
  if (el !== document.body) emitBox(el, cs, r, true);
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
      const nt = n.tagName.toLowerCase();
      const inline = ncs.display === 'inline' && n.tagName !== 'IMG' && !PIC_TAGS.has(nt) && nt !== 'svg' && !n.querySelector(BLOCKISH) && !treeReason(ncs, n.getBoundingClientRect());
      if (inline) group.push(n); else { flush(); walk(n); }
    }
  }
  flush();
}

function walk(el) {
  if (SKIP.has(el.tagName)) return;
  const cs = getComputedStyle(el);
  if (cs.display === 'none' || cs.visibility === 'hidden') return;
  const r = el.getBoundingClientRect();
  const t = T.get(el);
  if (t && t.bad) { addPic(el, 'transform (skew or non-uniform scale)', 'tree'); return; }
  if (t) chain.push({...t, px: r.left + t.ox, py: r.top + t.oy});
  try { walkInner(el, cs, r); } finally { if (t) chain.pop(); }
}

walk(document.body);
for (const [el, old, pr] of saved) { if (old) el.style.setProperty('transform', old, pr); else el.style.removeProperty('transform'); }
for (const it of out) {
  if (it.k !== 'pic') continue;
  const r = picEls[it.n].getBoundingClientRect();
  Object.assign(it, {x: r.left, y: r.top, w: r.width, h: r.height});
}
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


def _rotation(it: dict) -> float | None:
    rot = it.get("rot")
    return round(float(rot) % 360, 2) if rot and abs(float(rot)) > 0.01 else None


def _text(it: dict, ox: int, oy: int, theme: Theme) -> Placed:
    first = it["paras"][0]["runs"][0]
    fs_pt = round(it["fs"] * PT_PER_PX, 2)
    spacing = it["lh"] / (it["fs"] * 1.2) if it["fs"] else 1.0
    ls = it.get("ls") or 0
    st = Style(
        font_size=fs_pt,
        color=_color(first["c"]),
        align=it["align"] if it["align"] in ("left", "center", "right", "justify") else "left",
        line_spacing=round(spacing, 2) if abs(spacing - 1.0) > 0.04 else None,
        font=it["ff"] if it["ff"] and it["ff"].lower() not in {"sans-serif", "serif", "monospace"} else None,
        padding=0,
        letter_spacing=round(ls * PT_PER_PX, 2) if ls and abs(ls) > 0.01 else None,
        rotation=_rotation(it),
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
    # Chromium already measured this text: lint must not re-measure it, and a single line must not wrap when
    # PowerPoint substitutes a wider font (attrs read by lint and render)
    one_line = len(paras) == 1 and it["lh"] and it["h"] < 1.6 * it["lh"]
    attrs = {"measured": "html", **({"nowrap": True} if one_line else {})}
    return Placed(
        element=Text(role="body", paragraphs=paras, attrs=attrs),
        x=ox + round(it["x"] * EMU_PER_PX),
        y=oy + round(it["y"] * EMU_PER_PX),
        w=round(it["w"] * EMU_PER_PX),
        h=round(it["h"] * EMU_PER_PX),
        style=st,
    )


def _rect(it: dict, ox: int, oy: int) -> Placed:
    w, h, rad = it["w"], it["h"], it["rad"]
    shape = it.get("shape") or "rect"
    if shape == "rect" and rad > 0.5:
        shape = "ellipse" if abs(w - h) < 1 and rad >= min(w, h) / 2 - 0.5 else "rounded-rect"
    st = Style(
        fill=it["grad"] if it.get("grad") else _color(it["fill"]),
        line=_color(it["line"]),
        line_width=round(it["lw"] * PT_PER_PX, 2) if it["line"] else None,
        line_dash=it.get("ld") or None,
        radius=round(min(rad, min(w, h) / 2) * PT_PER_PX, 2) if shape == "rounded-rect" else None,
        opacity=round(it["alpha"], 3) if (it["fill"] or it.get("grad")) and it["alpha"] < 0.99 else None,
        shadow=it.get("shadow") or None,
        rotation=_rotation(it),
    )
    return Placed(
        element=Shape(shape=shape),
        x=ox + round(it["x"] * EMU_PER_PX),
        y=oy + round(it["y"] * EMU_PER_PX),
        w=max(round(w * EMU_PER_PX), 1),
        h=max(round(h * EMU_PER_PX), 1),
        style=st,
    )


def _line(it: dict, ox: int, oy: int) -> Placed:
    x1, y1, x2, y2 = it["x1"], it["y1"], it["x2"], it["y2"]
    attrs = {"head": it.get("head", "none")}
    if x2 < x1:
        attrs["flip_h"] = True
    if y2 < y1:
        attrs["flip_v"] = True
    return Placed(
        element=Shape(shape="line", attrs=attrs),
        x=ox + round(min(x1, x2) * EMU_PER_PX),
        y=oy + round(min(y1, y2) * EMU_PER_PX),
        w=round(abs(x2 - x1) * EMU_PER_PX),
        h=round(abs(y2 - y1) * EMU_PER_PX),
        style=Style(line=_color(it["color"]), line_width=round(max(it["lw"], 0.5) * PT_PER_PX, 2)),
    )


def _save_png(data: bytes, tmp: list[Path]) -> str:
    if not tmp:
        tmp.append(_tmpdir())
    path = tmp[0] / f"img{len(list(tmp[0].iterdir())) + 1}.png"
    path.write_bytes(data)
    return str(path)


def _picture(it: dict, ox: int, oy: int, png: bytes, tmp: list[Path]) -> Placed:
    alt = it.get("alt") or f"HTML <{it['tag']}> ({it['why']}), kept as a picture"
    return Placed(
        element=Image(src=_save_png(png, tmp), alt=alt, fit="stretch"),
        x=ox + round(it["x"] * EMU_PER_PX),
        y=oy + round(it["y"] * EMU_PER_PX),
        w=max(round(it["w"] * EMU_PER_PX), 1),
        h=max(round(it["h"] * EMU_PER_PX), 1),
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


_PIC_CSS = (
    "body *{visibility:hidden!important}html,body{background:transparent!important}"
    "{sel}{visibility:visible!important}"
)
_SET_CSS = (
    "(css)=>{let s=document.getElementById('sm-pic-css');"
    "if(!s){s=document.createElement('style');s.id='sm-pic-css';document.head.appendChild(s);}"
    "s.textContent=css;}"
)


def _snap(page, it: dict, w_px: int, h_px: int) -> bytes | None:
    """Transparent PNG of one element: only it (``tree``) or only its own box (``self``) stays visible."""
    n = it["n"]
    sel = f'[data-sm-pic="{n}"]' + (f',[data-sm-pic="{n}"] *' if it["mode"] == "tree" else "")
    x0, y0 = max(it["x"], 0.0), max(it["y"], 0.0)
    x1, y1 = min(it["x"] + it["w"], w_px), min(it["y"] + it["h"], h_px)
    if x1 - x0 < 1 or y1 - y0 < 1:
        return None
    try:
        page.evaluate(_SET_CSS, _PIC_CSS.replace("{sel}", sel))
        return page.screenshot(
            type="png",
            clip={"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0},
            omit_background=True,
            timeout=15_000,
        )
    except Exception:
        return None


def _measure(renderer, html: str, w_px: int, h_px: int, theme: Theme) -> dict | None:
    """Walk the page once; element pictures are screenshotted from the same page. ``None`` on any failure."""
    with renderer._session(html, w_px, h_px, theme, scale=2) as page:
        if page is None:
            return None
        try:
            data = page.evaluate(_JS)
        except Exception:
            return None
        if not data:
            return None
        pics = [it for it in data.get("items", []) if it.get("k") == "pic"]
        for it in pics[:MAX_PICTURES]:
            it["png"] = _snap(page, it, w_px, h_px)
        for it in pics[MAX_PICTURES:]:
            it["png"] = None
        return data


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
    ``renderer`` (``HtmlRenderer``) so a deck launches one browser. Never raises. Elements that shapes cannot
    express are pictures of just that element, reported once each as an ``html-element-image`` info.
    """
    own = None
    try:
        if renderer is None:
            from .render.htmlimg import HtmlRenderer

            renderer = own = HtmlRenderer()
        w_px, h_px = max(round(w / EMU_PER_PX), 1), max(round(h / EMU_PER_PX), 1)
        data = _measure(renderer, html, w_px, h_px, theme)
        if not data or not data.get("items"):
            return None
        placed: list[Placed] = []
        diags: list[Diagnostic] = []
        tmp: list[Path] = []
        clipped = 0
        seen: set[tuple[str, str]] = set()
        for it in data["items"]:
            if it["k"] != "line" and (it["x"] >= w_px or it["y"] >= h_px):
                clipped += 1
                continue
            try:
                if it["k"] == "rect":
                    placed.append(_rect(it, x, y))
                elif it["k"] == "line":
                    placed.append(_line(it, x, y))
                elif it["k"] == "text":
                    placed.append(_text(it, x, y, theme))
                elif it["k"] == "img":
                    pl = _image(it, x, y, tmp)
                    if pl is not None:
                        placed.append(pl)
                elif it["k"] == "pic":
                    key = (it["tag"], it["why"])
                    if key not in seen:
                        seen.add(key)
                        diags.append(
                            Diagnostic(
                                level="info",
                                message=f"<{it['tag']}> kept as a picture ({it['why']})",
                                rule="html-element-image",
                                hint="solid or gradient fills, shadows, rotate(), border-radius and simple svg "
                                "stay editable shapes; simplify this element to make it native",
                            )
                        )
                    if it.get("png"):
                        placed.append(_picture(it, x, y, it["png"], tmp))
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
