"""Source edits for ``slidemark review --fix``: split a dense slide, add ``dense``, swap a failing declared
color, move a long title's tail into the ``>`` lead.

Every function is pure text -> text on one slide's source lines (a *region*: from its ``# Title`` or ``---``
line up to the next slide) and returns candidates; ``selfreview`` trial-builds them and keeps the one that
helps. Content text is never edited: splitting only moves whole list items / boxes / table rows to another
slide (a table header and a box heading are repeated), and a title's tail moves into the lead.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from .parser.core import FENCE_RE, H1_RE, HN_RE, HR_RE, fence_map, parse_header, split_lines, split_slides
from .parser.css import extract_fences
from .parser.ctx import Ctx

_GRID = re.compile(r"^(\d+|\d+x\d+|\d+(?:\.\d+)?(?::\d+(?:\.\d+)?)+|[a-z.]+(?:/[a-z.]+)+)$")
_LINK = re.compile(r"^[a-z0-9][>-][a-z0-9]$", re.I)
_BULLET = re.compile(r"^([-*+]|\d+[.)])[ \t]+")
_STANDALONE = re.compile(r"^\{([^{}]*)\}[ \t]*$")
_TOKEN = re.compile(r'(?:[^\s"]|"[^"]*")+')
_SEP_ROW = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
_FOOT = re.compile(r"^(※|\^[ \t])")
_CALLOUT = re.compile(r"^>\s*\[!")
MAX_PARTS = 6


# --------------------------------------------------------------------------- slide regions


@dataclass
class Region:
    lines: list[str]
    flags: list[bool]  # inside a code fence
    start: int  # 0-based index of the first line in the whole text


def regions(text: str) -> tuple[list[str], list[Region]] | None:
    """(header lines, one Region per slide in parser order), or None when the structure is unsafe
    (an unclosed fence: the mechanical fixes close it first)."""
    lines = split_lines(text)
    inside, unclosed = fence_map(lines)
    if unclosed is not None:
        return None
    work = list(lines)
    extract_fences(work)  # css fences are blanked by the parser before slides are split
    w_inside, _ = fence_map(work)
    from .ir import Deck

    deck = Deck()
    start = parse_header(work, w_inside, deck, Ctx(deck.diagnostics))
    chunks = split_slides(work, w_inside, start)
    if not chunks:
        return lines, []
    firsts = []
    for c in chunks:
        if c.title_idx is not None:
            firsts.append(c.title_idx)
        elif c.start > 0 and HR_RE.match(work[c.start - 1]) and not w_inside[c.start - 1]:
            firsts.append(c.start - 1)
        else:
            firsts.append(c.start)
    out = []
    for k, f in enumerate(firsts):
        end = firsts[k + 1] if k + 1 < len(firsts) else len(lines)
        out.append(Region(lines[f:end], inside[f:end], f))
    return lines[: firsts[0]], out


def join(parts: list[list[str]]) -> str:
    return "\n".join(x for p in parts for x in p)


# --------------------------------------------------------------------------- source model


def _width(s: str) -> int:
    return sum(2 if ord(c) > 0x2E7F else 1 for c in s)


@dataclass
class Leaf:
    lines: list[str]
    kind: str = "block"  # box | item | row | block
    gap: bool = False  # a blank line precedes it in the source
    pre: list[str] = field(default_factory=list)  # attr / `@` lines glued before it
    box: int | None = None  # the expanded box it sits in
    table: int | None = None
    expand: int | None = None  # for a whole-box leaf: its id in SlideSrc.boxes
    sticky: bool = False  # never start a part here (a `^` merge cell)
    bid: int | None = None  # list block whose attr lines (SlideSrc.bpre) repeat in every part holding items

    @property
    def weight(self) -> int:
        return 24 + sum(_width(x) for x in self.lines) + sum(_width(x) for x in self.pre) // 2


@dataclass
class Box:
    head: list[str]  # glued attr lines + the `## ` line
    end: bool  # an `@end` closed it
    inner: list[Leaf] = field(default_factory=list)


@dataclass
class TableSrc:
    pre: list[str]
    open: list[str]  # fence open line (CSV table) or []
    header: list[str]  # header row (+ separator row for GFM)
    close: list[str]


@dataclass
class SlideSrc:
    first: str | None
    sep: bool
    at: list[str] = field(default_factory=list)
    lead: list[str] = field(default_factory=list)
    leaves: list[Leaf] = field(default_factory=list)
    boxes: dict[int, Box] = field(default_factory=dict)
    tables: dict[int, TableSrc] = field(default_factory=dict)
    bpre: dict[int, list[str]] = field(default_factory=dict)
    conclusion: list[str] = field(default_factory=list)
    foot: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    stray: list[str] = field(default_factory=list)  # `@`/attr lines with no block after them
    trail: list[str] = field(default_factory=list)  # blank / `---` lines that end the region


def _is_row(s: str) -> bool:
    return s.lstrip().startswith("|")


def _blocks(lines: list[str], flags: list[bool]) -> list[tuple[list[str], bool]]:
    """Blank-separated blocks as (lines, blank before). A ``###`` line starts a section that runs to the
    next ``###``; a table / quote change starts a block; fence lines never split."""
    out: list[tuple[list[str], bool]] = []
    cur: list[str] | None = None
    gap = False
    section = False
    for s, ins in zip(lines, flags, strict=True):
        if ins:
            if cur is None:
                cur = []
                out.append((cur, gap))
                gap = False
            cur.append(s)
            continue
        m = HN_RE.match(s)
        if m and len(m.group(1)) == 3:
            cur = [s]
            out.append((cur, gap))
            gap, section = False, True
            continue
        if not s.strip():
            if section and cur is not None:
                cur.append(s)
            else:
                cur = None
            gap = True
            continue
        if cur is None:
            cur = [s]
            out.append((cur, gap))
            gap = False
            continue
        prev = cur[-1]
        if (
            not section
            and prev.strip()
            and (_is_row(s) != _is_row(prev) or s.startswith(">") != prev.startswith(">"))
        ):
            cur = [s]
            out.append((cur, False))
            continue
        cur.append(s)
    return out


def _leaves(lines: list[str], src: SlideSrc, box: int | None, tid: list[int]) -> list[Leaf]:
    """Leaves of a body: list items, table rows, other blocks."""
    flags, _ = fence_map(lines)
    out: list[Leaf] = []
    pending: list[str] = []
    for blk, gap in _blocks(lines, flags):
        while blk and not blk[-1].strip():
            blk = blk[:-1]
        if not blk:
            continue
        if len(blk) == 1 and _STANDALONE.match(blk[0]):
            pending.append(blk[0])
            continue
        pre, pending = pending, []
        k = 0
        while k < len(blk) - 1 and _STANDALONE.match(blk[k]):
            pre.append(blk[k])
            k += 1
        body = blk[k:]
        first = body[0]
        mf = FENCE_RE.match(first)
        if _is_row(first) and len(body) >= 3 and _SEP_ROW.match(body[1]):
            tid[0] += 1
            src.tables[tid[0]] = TableSrc(pre, [], body[:2], [])
            for row in body[2:]:
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                out.append(Leaf([row], "row", box=box, table=tid[0], sticky="^" in cells))
        elif mf and len(body) >= 4 and re.match(r"table\b", mf.group(2).strip()) and FENCE_RE.match(body[-1]):
            tid[0] += 1
            src.tables[tid[0]] = TableSrc(pre, [first], [body[1]], [body[-1]])
            for row in body[2:-1]:
                out.append(Leaf([row], "row", box=box, table=tid[0]))
        elif any(_BULLET.match(x) for x in body):
            head: list[str] = []
            items: list[Leaf] = []
            for x in body:
                if _BULLET.match(x):
                    items.append(Leaf([x], "item", box=box))
                elif items:
                    items[-1].lines.append(x)
                else:
                    head.append(x)
            if head:
                out.append(Leaf(head, "block", gap, pre, box))
                pre, gap = [], False
            items[0].gap = gap
            if pre:
                bid = len(src.bpre) + 1
                src.bpre[bid] = pre
                for it in items:
                    it.bid = bid
            out.extend(items)
        else:
            out.append(Leaf(body, "block", gap, pre, box))
    src.stray.extend(pending)
    return out


def parse_slide(region: Region) -> SlideSrc | None:
    """Structured view of one slide's source (None when the region is empty)."""
    R, F = region.lines, region.flags
    if not R:
        return None
    first, sep, i0 = None, False, 0
    if not F[0] and H1_RE.match(R[0]):
        first, i0 = R[0], 1
    elif not F[0] and HR_RE.match(R[0]):
        sep, i0 = True, 1
    src = SlideSrc(first, sep)
    end = len(R)
    while end > i0 and (not R[end - 1].strip() or (HR_RE.match(R[end - 1]) and not F[end - 1])):
        end -= 1
    src.trail = R[end:]
    body, flags = R[i0:end], F[i0:end]
    n = len(body)
    # unit: [kind, lines, gap, pre, closed]
    units: list[list] = []
    cur: list[str] | None = None
    cur_kind = ""
    gap = False
    pending: list[str] = []
    saw = lead_done = False
    i = 0
    while i < n:
        line, ins = body[i], flags[i]
        if ins:
            if cur is None:
                cur, cur_kind = [], "block"
                units.append(["block", cur, gap, pending, False])
                pending, gap, saw = [], False, True
            cur.append(line)
            i += 1
            continue
        s = line.strip()
        if line.startswith("???"):
            src.notes = body[i:]
            while src.notes and not src.notes[-1].strip():
                src.notes.pop()
            break
        if not s:
            if cur is not None and cur_kind == "box":
                cur.append(line)
            else:
                cur = None
            gap = True
        elif _FOOT.match(line):
            src.foot.append(line)
            if cur_kind != "box":
                cur = None
        elif s.lower() == "@end":
            if cur is not None and cur_kind == "box":
                units[-1][4] = True
                cur = None
            else:
                pending.append(line)
        elif line.startswith("@"):
            if cur is not None and cur_kind == "box":
                cur.append(line)
            elif not saw:
                src.at.append(line)
            else:
                pending.append(line)
                cur = None
        elif (m := HN_RE.match(line)) and len(m.group(1)) == 2:
            cur, cur_kind = [line], "box"
            units.append(["box", cur, gap, pending, False])
            pending, gap, saw = [], False, True
        elif cur is not None and cur_kind == "box":
            cur.append(line)
        elif not saw and not lead_done and line.startswith(">") and not _CALLOUT.match(line):
            run = []
            while i < n and not flags[i] and body[i].startswith(">"):
                run.append(body[i])
                i += 1
            src.lead, lead_done = run, True
            continue
        elif _STANDALONE.match(line) and cur is None:
            pending.append(line)
        elif cur is None:
            cur, cur_kind = [line], "block"
            units.append(["block", cur, gap, pending, False])
            pending, gap, saw = [], False, True
        else:
            cur.append(line)
        i += 1
    src.stray.extend(pending)
    if units:  # a trailing `>` run (not a callout) is the conclusion
        ul = units[-1][1]
        while ul and not ul[-1].strip():
            ul.pop()
        k = len(ul)
        while k > 0 and ul[k - 1].startswith(">") and not _CALLOUT.match(ul[k - 1]):
            k -= 1
        if k < len(ul) and not (units[-1][0] == "box" and k == 0):
            src.conclusion = ul[k:]
            del ul[k:]
            if not ul:
                units.pop()
    tid = [0]
    for kind, ul, ugap, upre, closed in units:
        while ul and not ul[-1].strip():
            ul = ul[:-1]
        if kind == "box":
            b = len(src.boxes) + 1
            box = Box([*upre, ul[0]], closed)
            body_flags, _ = fence_map(ul[1:])
            nested = any(
                not f and (x.startswith("@") or (HN_RE.match(x) and len(HN_RE.match(x).group(1)) == 3))  # type: ignore[union-attr]
                for x, f in zip(ul[1:], body_flags, strict=True)
            )
            box.inner = [] if nested else _leaves(ul[1:], src, b, tid)
            src.boxes[b] = box
            src.leaves.append(Leaf([*ul, *(["@end"] if closed else [])], "box", ugap, upre, expand=b))
        else:
            got = _leaves(ul, src, None, tid)
            if got:
                if got[0].table is not None:  # a table repeats its attr lines in every part
                    t = src.tables[got[0].table]
                    t.pre = [*upre, *t.pre]
                else:
                    got[0].pre = [*upre, *got[0].pre]
                got[0].gap = ugap
            src.leaves.extend(got)
    return src


# --------------------------------------------------------------------------- splitting


def _partition(weights: list[int], ok: list[bool], k: int) -> list[int] | None:
    """Start indices of ``k`` contiguous parts minimizing the heaviest part; a part may start at i only if
    ``ok[i]``. None when impossible."""
    n = len(weights)
    if k < 2 or n < k:
        return None
    pre = [0]
    for w in weights:
        pre.append(pre[-1] + w)
    inf = float("inf")
    dp = [[inf] * (n + 1) for _ in range(k + 1)]
    cut = [[0] * (n + 1) for _ in range(k + 1)]
    dp[0][0] = 0
    for j in range(1, k + 1):
        for i in range(j, n + 1):
            for m in range(j - 1, i):
                if (m > 0 and not ok[m]) or (m == 0 and j > 1) or (j == 1 and m != 0):
                    continue
                v = max(dp[j - 1][m], pre[i] - pre[m])
                if v < dp[j][i]:
                    dp[j][i], cut[j][i] = v, m
    if dp[k][n] == inf:
        return None
    starts, i = [], n
    for j in range(k, 0, -1):
        m = cut[j][i]
        starts.append(m)
        i = m
    return sorted(starts)


def _at_line(line: str) -> str | None:
    toks = [t for t in _TOKEN.findall(line[1:]) if not _GRID.match(t) and not _LINK.match(t)]
    return "@" + " ".join(toks) if toks else None


def _retitle(first: str, i: int, k: int) -> str:
    m = H1_RE.match(first)
    text = (m.group(1) if m else first[1:]) or ""
    am = re.search(r"\s*\{[^{}]*\}\s*$", text)
    base, attrs = (text[: am.start()], text[am.start() :]) if am else (text, "")
    return f"# {base.strip()} ({i}/{k}){attrs}".replace("#  (", "# (")


def _sequence(src: SlideSrc, expand: set[int]) -> list[Leaf]:
    out: list[Leaf] = []
    for lf in src.leaves:
        if lf.kind == "box" and lf.expand in expand and src.boxes[lf.expand].inner:
            out.extend(src.boxes[lf.expand].inner)
        else:
            out.append(lf)
    return out


def _assemble(src: SlideSrc, leaves: list[Leaf], idx: int, k: int) -> list[str]:
    out: list[str] = []
    if idx == 0:
        if src.first is not None:
            out.append(_retitle(src.first, 1, k))
        elif src.sep:
            out.append("---")
    elif src.first is not None:
        out.append(_retitle(src.first, idx + 1, k))
    else:
        out.append("---")
    for a in src.at:
        if (kept := _at_line(a)) is not None:
            out.append(kept)
    if idx == 0:
        out.extend(src.lead)
    cur_box: int | None = None
    cur_tab: int | None = None
    started = False
    done_b: set[int] = set()

    def close_box() -> None:
        nonlocal cur_box
        if cur_box is not None and src.boxes[cur_box].end:
            out.append("@end")
        cur_box = None

    def close_tab() -> None:
        nonlocal cur_tab
        if cur_tab is not None:
            out.extend(src.tables[cur_tab].close)
        cur_tab = None

    for lf in leaves:
        if lf.table != cur_tab:
            close_tab()
        if lf.box != cur_box:
            close_box()
        new_box = lf.box is not None and lf.box != cur_box
        if new_box:
            cur_box = lf.box
            out.extend(src.boxes[lf.box].head)  # type: ignore[index]
        if lf.table is not None and lf.table != cur_tab:
            cur_tab = lf.table
            t = src.tables[lf.table]
            if started and not new_box:
                out.append("")
            out.extend([*t.pre, *t.open, *t.header])
        elif lf.table is None:
            if lf.gap and started and not new_box:
                out.append("")
            out.extend(lf.pre)
            if lf.bid is not None and lf.bid not in done_b:
                done_b.add(lf.bid)
                out.extend(src.bpre[lf.bid])
        out.extend(lf.lines)
        started = True
    close_tab()
    close_box()
    if idx == k - 1:
        out.extend(src.stray)
        out.extend(src.conclusion)
        out.extend(src.foot)
    if idx == 0:
        out.extend(src.notes)
    return out


def split_candidates(region: Region) -> Iterator[tuple[str, list[str]]]:
    """Candidate replacements of the region, smallest split first: ``(what, new lines)``."""
    src = parse_slide(region)
    if src is None:
        return
    base = _sequence(src, set())
    seen: set[tuple[tuple[int, ...], int]] = set()
    for k in range(2, MAX_PARTS + 1):
        total = sum(lf.weight for lf in base) or 1
        variants = [set()]
        big = {lf.expand for lf in src.leaves if lf.kind == "box" and lf.weight > 1.3 * total / k}
        if big:
            variants.append({b for b in big if b is not None})
        variants.append({lf.expand for lf in src.leaves if lf.kind == "box" and lf.expand is not None})
        for exp in variants:
            seq = _sequence(src, exp)
            ok = [True] + [not lf.sticky for lf in seq[1:]]
            starts = _partition([lf.weight for lf in seq], ok, k)
            if starts is None:
                continue
            key = (tuple(starts), len(seq))
            if key in seen:
                continue
            seen.add(key)
            bounds = [*starts, len(seq)]
            parts = [_assemble(src, seq[bounds[i] : bounds[i + 1]], i, k) for i in range(k)]
            lines: list[str] = []
            for p in parts:
                if lines:
                    lines.append("")
                lines.extend(p)
            lines.extend(src.trail)
            yield f"split into {k} slides", lines


# --------------------------------------------------------------------------- dense / title / contrast


def add_dense(region: Region) -> list[str] | None:
    """``dense`` on the slide's ``@`` line (a new ``@dense`` line under the title when there is none)."""
    R, F = region.lines, region.flags
    if not R:
        return None
    i0 = 1 if (not F[0] and (H1_RE.match(R[0]) or HR_RE.match(R[0]))) else 0
    for i in range(i0, len(R)):
        if F[i] or HN_RE.match(R[i]):
            break
        if R[i].startswith("@") and R[i].strip().lower() != "@end":
            if re.search(r"(?<![^\s@])dense(?!\S)", R[i]):
                return None
            return [*R[:i], R[i].rstrip() + " dense", *R[i + 1 :]]
    return [*R[:i0], "@dense", *R[i0:]]


_SEPS = [
    (r"\s[-–—―]\s", False),
    (r"[:：]\s*", False),
    (r"[、，,]\s*", False),
    (r"\s*[（(]", True),
    (r"\s*[|/／]\s*", False),
    (r"。", False),
]


def title_candidates(region: Region) -> Iterator[list[str]]:
    """Region variants with a shorter title; the removed tail goes to the front of the lead (a new ``>`` line
    under the title when there is none)."""
    R, F = region.lines, region.flags
    if not R or F[0] or not (m := H1_RE.match(R[0])) or not m.group(1):
        return
    text = m.group(1)
    am = re.search(r"\s*\{[^{}]*\}\s*$", text)
    attrs = text[am.start() :] if am else ""
    base = text[: am.start()] if am else text
    cands: list[tuple[str, str, bool]] = []
    for pat, keep in _SEPS:
        for sm in re.finditer(pat, base):
            head = base[: sm.start()].rstrip()
            tail = (base[sm.start() :] if keep else base[sm.end() :]).strip()
            if len(head) >= 4 and tail:
                cands.append((head, tail, True))
    wide = sum(1 for c in base if ord(c) > 0x2E7F) > len(base) / 3
    limit = 18 if wide else 28
    if wide:
        for n in range(min(limit, len(base) - 1), 5, -2):
            cands.append((base[:n], base[n:], False))
    else:
        for sm in re.finditer(r"\s+", base):
            if 8 <= sm.start() <= limit + 4:
                cands.append((base[: sm.start()], base[sm.end() :], False))
    cands.sort(key=lambda c: (len(c[0]) > limit + 6, not c[2], -len(c[0])))
    lead_i = None
    j = 1
    while j < len(R) and not F[j] and (not R[j].strip() or R[j].startswith("@") or _STANDALONE.match(R[j])):
        j += 1
    if j < len(R) and not F[j] and R[j].startswith(">") and not _CALLOUT.match(R[j]):
        lead_i = j
    seen = set()
    for head, tail, _sep in cands[:10]:
        if head in seen:
            continue
        seen.add(head)
        new_title = f"# {head}{attrs}"
        if lead_i is None:
            yield [new_title, f"> {tail}", *R[1:]]
        else:
            lead = R[lead_i]
            body = lead[1:].lstrip()
            glue = "。" if wide else ". "
            if tail.endswith(("。", ".", "!", "?", "！", "？")):
                glue = "" if wide else " "
            yield [new_title, *R[1:lead_i], f"> {tail}{glue}{body}", *R[lead_i + 1 :]]


_COLOR_ATTR = re.compile(r"(?<=[{\s])color=(\"[^\"]*\"|[^\s}]+)")
_FILL_ATTR = re.compile(r"(?<=[{\s])(?:fill|bg)=(\"[^\"]*\"|[^\s}]+)")
_CSS_COLOR = re.compile(r"(?<![-\w])color\s*:\s*([^;}]+?)(?=\s*(?:;|\}|$))")


def _near(R: list[str], F: list[bool], line: int | None) -> list[int]:
    """Indices to try for a diagnostic at 1-based global ``line`` (relative to the region): the line, the one
    before (an attribute line), the heading above, then every other line."""
    order: list[int] = []
    if line is not None and 0 <= line < len(R):
        order += [line, line - 1]
        k = line
        while k > 0 and not (HN_RE.match(R[k]) and not F[k]):
            k -= 1
        order.append(k)
        order += [line + 1]
    order += list(range(len(R)))
    seen, out = set(), []
    for i in order:
        if 0 <= i < len(R) and i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _css_lines(R: list[str], F: list[bool]) -> set[int]:
    """Indices of lines inside ```css fences of the region."""
    out: set[int] = set()
    css = False
    for i, line in enumerate(R):
        if not F[i]:
            css = False
            continue
        if i == 0 or not F[i - 1]:  # a fence opens here
            m = FENCE_RE.match(line)
            css = bool(m and m.group(2).strip().lower().split("{")[0].strip() == "css")
        elif css:
            out.add(i)
    return out


def contrast_candidates(region: Region, line: int | None, inks: list[str]) -> Iterator[list[str]]:
    """Region variants where a declared text color (``{color=..}`` or a ``color:`` in a slide css fence) is
    swapped for each of ``inks``; a declared ``fill=`` with no color gets ``color=<ink>``. ``line`` is the
    0-based region line of the failing element (or None)."""
    R, F = region.lines, region.flags
    css = _css_lines(R, F)
    tried = 0
    for i in _near(R, F, line):
        s = R[i]
        if F[i] and (i not in css or not _CSS_COLOR.search(s)):
            continue
        for ink in inks:
            new = None
            if "{" in s and _COLOR_ATTR.search(s) and not F[i]:
                new = _COLOR_ATTR.sub(f"color={ink}", s, count=1)
            elif F[i] and _CSS_COLOR.search(s):
                new = _CSS_COLOR.sub(f"color: {ink}", s, count=1)
            elif "{" in s and _FILL_ATTR.search(s) and not F[i] and not _COLOR_ATTR.search(s):
                new = re.sub(r"\}(?=[^{}]*$)", f" color={ink}}}", s, count=1)
            if new is not None and new != s:
                yield [*R[:i], new, *R[i + 1 :]]
                tried += 1
        if tried >= 12:
            return


def color_decl(region: Region, line: int | None) -> int | None:
    """Region index of the nearest line that declares a text color (or a fill) for the element, or None."""
    R, F = region.lines, region.flags
    css = _css_lines(R, F)
    for i in _near(R, F, line):
        s = R[i]
        if (not F[i] and "{" in s and (_COLOR_ATTR.search(s) or _FILL_ATTR.search(s))) or (
            i in css and _CSS_COLOR.search(s)
        ):
            return i
    return None
