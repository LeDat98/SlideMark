"""``slidemark check --fix``: rewrite the source for diagnostics whose fix is mechanical and unambiguous.

One function per rule works on the source lines and returns ``Edit`` records; ``fix_text`` applies them
bottom to top so line numbers stay valid, and repeats while new fixes appear (a few passes at most).
Content text is never changed: only structure, tokens, alt text of images and lenient syntax variants.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import icons
from .ir import Diagnostic
from .parser.attrs import AT_KEYS, KNOWN_CLASSES, KNOWN_WORDS, STANDALONE, VALID_KEYS
from .parser.core import FENCE_RE, H1_RE, HEADER_KEYS, HR_RE, fence_map, split_lines
from .parser.ctx import unique_near

MAX_PASSES = 4
_GRID = re.compile(r"^(\d+|\d+x\d+|\d+(?:\.\d+)?(?::\d+(?:\.\d+)?)+|[a-z.]+(?:/[a-z.]+)+)$")


@dataclass
class Edit:
    """Replace ``lines[start:end]`` with ``new`` (0-based; start == end inserts); empty ``what`` = silent."""

    start: int
    end: int
    new: list[str]
    line: int  # 1-based line of the diagnostic
    rule: str
    what: str = ""


@dataclass
class Fixed:
    line: int
    rule: str
    what: str

    def __str__(self) -> str:
        return f"fixed L{self.line} {self.rule}: {self.what}"

    def model_dump(self) -> dict[str, object]:
        return {"line": self.line, "rule": self.rule, "what": self.what}


@dataclass
class _Src:
    lines: list[str]
    inside: list[bool]
    dym: dict[str, str] = field(default_factory=dict)


def _quoted(text: str, which: int = 0) -> str | None:
    found = re.findall(r"'([^']*)'", text)
    return found[which] if found and -len(found) <= which < len(found) else None


def _did_you_mean(d: Diagnostic) -> str | None:
    m = re.match(r"did you mean '([^']+)'", d.hint or "")
    return m.group(1) if m else None


def _safe(old: str, near: str, universe: list[str] | tuple[str, ...]) -> bool:
    """A did-you-mean fix is applied only when ``near`` is the one name of ``universe`` within edit distance 1
    of ``old`` (one letter off): ``shiled`` -> ``shield``, never ``eye`` -> ``yen``."""
    got = unique_near(old.rstrip("="), [u.rstrip("=") for u in universe])
    return got is not None and got.lower() == near.rstrip("=").lower()


def _swap_token(line: str, old: str, new: str) -> str | None:
    """Replace the whitespace-delimited token ``old`` once; ``None`` when it is not there."""
    m = re.search(r"(?<![^\s@])" + re.escape(old) + r"(?!\S)", line)
    return line[: m.start()] + new + line[m.end() :] if m else None


def _slide_end(src: _Src, start: int) -> int:
    """Index of the line that starts the next slide (a `---` or `# ` line outside fences), or the end."""
    for k in range(start + 1, len(src.lines)):
        if not src.inside[k] and (HR_RE.match(src.lines[k]) or H1_RE.match(src.lines[k])):
            return k
    return len(src.lines)


# --------------------------------------------------------------------------- rules


def _missing_end(src: _Src, d: Diagnostic) -> list[Edit]:
    i = (d.line or 0) - 1
    if not 0 < i < len(src.lines) or not src.lines[i].strip() or src.lines[i].strip().lower() == "@end":
        return []
    while i > 0 and STANDALONE.match(src.lines[i - 1]):
        i -= 1  # keep a `{...}` attribute line together with its block
    if src.lines[i - 1].strip().lower() == "@end":
        return []
    return [Edit(i, i, ["@end"], d.line or 0, "missing-end", "inserted '@end'")]


def _unknown_token(src: _Src, d: Diagnostic) -> list[Edit]:
    i, near = (d.line or 0) - 1, _did_you_mean(d)
    old = _quoted(d.message, -1)  # the message starts with the quoted '@'
    if not near or not old or not 0 <= i < len(src.lines) or not src.lines[i].startswith("@"):
        return []
    if not _safe(old, near, [*KNOWN_WORDS, *AT_KEYS]):
        return []
    if "' key '" in d.message:  # `foo=1` -> `bg=1`: the token starts with the key
        m = re.search(r"(?<![^\s@])" + re.escape(old) + r"=", src.lines[i])
        new = src.lines[i][: m.start()] + near + src.lines[i][m.end() :] if m and near.endswith("=") else None
    else:
        new = _swap_token(src.lines[i], old, near)
    if new is None:
        return []
    return [Edit(i, i + 1, [new], d.line or 0, d.rule or "", f"'{old}' -> '{near.rstrip('=')}'")]


def _unknown_attr(src: _Src, d: Diagnostic) -> list[Edit]:
    near, old = _did_you_mean(d), _quoted(d.message)
    i = (d.line or 0) - 1
    if not near or not old:
        return []
    classes = d.message.startswith("unknown class")
    if not _safe(old.lstrip("."), near.lstrip("."), KNOWN_CLASSES if classes else VALID_KEYS):
        return []
    if classes:
        pat, rep = re.compile(r"(?<=[{\s])" + re.escape(old) + r"(?=[\s}])"), near
    else:
        pat, rep = re.compile(r"(?<=[{\s])" + re.escape(old) + r"=(?!=)"), near
    for k in (i, i - 1, i + 1):
        if 0 <= k < len(src.lines) and "{" in src.lines[k] and not src.inside[k]:
            new, n = pat.subn(rep, src.lines[k], count=1)
            if n:
                return [Edit(k, k + 1, [new], d.line or 0, "unknown-attr", f"'{old}' -> '{rep}'")]
    return []


def _unknown_icon(src: _Src, d: Diagnostic) -> list[Edit]:
    near, old = _did_you_mean(d), _quoted(d.message)
    i = (d.line or 0) - 1
    if not near or not old or not _safe(old, near, icons.names()):
        return []
    for k in (i, i - 1, i + 1):
        if 0 <= k < len(src.lines) and not src.inside[k]:
            new, n = re.subn(
                r"\bicon=" + re.escape(old) + r"(?![\w-])", "icon=" + near, src.lines[k], count=1
            )
            if n:
                return [Edit(k, k + 1, [new], d.line or 0, "unknown-icon", f"icon '{old}' -> '{near}'")]
    return []


def _unknown_callout(src: _Src, d: Diagnostic) -> list[Edit]:
    m = re.search(r"\[!([^\]]+)\]", d.message)
    near = _quoted(d.hint or "")
    i = (d.line or 0) - 1
    if not m or not near or not 0 <= i < len(src.lines):
        return []
    new, n = re.subn(re.escape(m.group(0)), near, src.lines[i], count=1, flags=re.I)
    if not n:
        return []
    return [Edit(i, i + 1, [new], d.line or 0, "unknown-callout", f"{m.group(0)} -> {near}")]


def _unknown_header(src: _Src, d: Diagnostic) -> list[Edit]:
    near, old = _did_you_mean(d), _quoted(d.message)
    if not near or not old or not _safe(old, near, HEADER_KEYS):
        return []
    pat = re.compile(r"^(\s*)" + re.escape(old) + r"(\s*:)")
    for k in range((d.line or 1) - 1, min(len(src.lines), (d.line or 1) + 40)):
        if H1_RE.match(src.lines[k]):
            break
        if pat.match(src.lines[k]):
            new = pat.sub(lambda m: m.group(1) + near + m.group(2), src.lines[k], count=1)
            return [Edit(k, k + 1, [new], d.line or 0, "unknown-header", f"'{old}' -> '{near}'")]
    return []


def _second_grid(src: _Src, d: Diagnostic) -> list[Edit]:
    tok, i = _quoted(d.message), (d.line or 0) - 1
    if not d.message.startswith("second grid") or not 0 <= i < len(src.lines):
        return []
    line = src.lines[i]
    if not line.startswith("@"):
        return []
    if tok is None:  # grids on two `@` lines: the first one wins, drop this line's grid token
        grid = next((t for t in line[1:].split() if _GRID.match(t)), None)
        if grid is None:
            return []
        tok = grid
    hits = list(re.finditer(r"(?<![^\s@])" + re.escape(tok) + r"(?!\S)", line))
    if len(hits) < 1:
        return []
    m = hits[-1]
    new = re.sub(r"[ \t]{2,}", " ", (line[: m.start()] + line[m.end() :]).rstrip()).rstrip()
    out = [] if new.strip() == "@" else [new]
    return [Edit(i, i + 1, out, d.line or 0, "bad-grid", f"dropped the ignored grid '{tok}'")]


def _image_alt(src: _Src, d: Diagnostic) -> list[Edit]:
    i = (d.line or 0) - 1
    if not 0 <= i < len(src.lines):
        return []
    m = re.search(r"!\[\s*\]\(([^)\s]+)", src.lines[i])
    if not m:
        return []
    stem = Path(re.split(r"[?#]", m.group(1))[0].rstrip("/")).stem
    alt = re.sub(r"[-_.\s]+", " ", stem).strip()
    if not alt:
        return []
    new = src.lines[i][: m.start()] + f"![{alt}](" + src.lines[i][m.start() + 4 :]
    return [Edit(i, i + 1, [new], d.line or 0, "image-alt", f"alt text '{alt}'")]


def _unclosed_fence(src: _Src, d: Diagnostic) -> list[Edit]:
    i = (d.line or 0) - 1
    m = FENCE_RE.match(src.lines[i]) if 0 <= i < len(src.lines) else None
    if not m:
        return []
    end = len(src.lines)
    for k in range(i + 1, len(src.lines)):  # the fence swallowed the slide border: find it textually
        if HR_RE.match(src.lines[k]) or H1_RE.match(src.lines[k]):
            end = k
            break
    while end - 1 > i and not src.lines[end - 1].strip():
        end -= 1
    return [
        Edit(
            end,
            end,
            [m.group(1)],
            d.line or 0,
            "unclosed-fence",
            f"closed the code fence with '{m.group(1)}'",
        )
    ]


def _bullet_star(src: _Src, d: Diagnostic) -> list[Edit]:
    start = (d.line or 0) - 1
    if not 0 <= start < len(src.lines):
        return []
    out: list[Edit] = []
    for k in range(start, _slide_end(src, start)):
        m = re.match(r"^([ \t]*)\*([ \t]+)(?=\S)(.*)$", src.lines[k])
        if src.inside[k] or not m or not m.group(3).strip(" *"):
            continue
        out.append(Edit(k, k + 1, [f"{m.group(1)}-{m.group(2)}{m.group(3)}"], k + 1, "bullet-star", ""))
    if out:
        out[0].what = "'* ' bullets -> '- '"
        out[0].line = d.line or 0
    return out


def _rest_blank(src: _Src, a: int) -> bool:
    return all(not x.strip() for x in src.lines[a : _slide_end(src, a - 1)])


def _note_line(src: _Src, d: Diagnostic) -> list[Edit]:
    i = (d.line or 0) - 1
    if not 0 <= i < len(src.lines):
        return []
    m = re.match(r"^\s*notes?[ \t]*:[ \t]*(.*)$", src.lines[i], re.I)
    if not m:
        return []
    parts = [m.group(1).strip()] if m.group(1).strip() else []
    j = i + 1
    while (
        j < len(src.lines)
        and not src.inside[j]
        and src.lines[j].strip()
        and not src.lines[j].startswith(("#", "@", "---", "※", "???", "<!--"))
    ):
        parts.append(src.lines[j].strip())
        j += 1
    if not parts or not _rest_blank(src, j):  # `???` runs to the end of the slide: only safe there
        return []
    new = ["??? " + parts[0], *parts[1:]]
    return [Edit(i, j, new, d.line or 0, "note-line", "'Note:' -> '???'")]


def _comment_notes(src: _Src, d: Diagnostic) -> list[Edit]:
    i = (d.line or 0) - 1
    if not 0 <= i < len(src.lines) or not src.lines[i].strip().startswith("<!--"):
        return []
    k = i
    while k < len(src.lines) and "-->" not in src.lines[k]:
        k += 1
    if k >= len(src.lines) or not _rest_blank(src, k + 1):
        return []
    block = "\n".join(src.lines[i : k + 1])
    m = re.match(r"^\s*<!--(.*?)-->\s*$", block, re.S)
    if not m:
        return []
    parts = [p.strip() for p in m.group(1).strip().splitlines() if p.strip()]
    if not parts:
        return []
    return [
        Edit(i, k + 1, ["??? " + parts[0], *parts[1:]], d.line or 0, "comment-notes", "<!-- -->  -> '???'")
    ]


def _marp_class(src: _Src, d: Diagnostic) -> list[Edit]:
    i = (d.line or 0) - 1
    if not 0 <= i < len(src.lines):
        return []
    m = re.match(
        r"^\s*<!--\s*_?class\s*:\s*([A-Za-z_][\w-]*(?:[ \t]+[A-Za-z_][\w-]*)*)\s*-->\s*$", src.lines[i]
    )
    if not m or not d.message.startswith("Marp directive") or "class" not in d.message:
        return []
    return [
        Edit(
            i,
            i + 1,
            ["@" + " ".join(m.group(1).split())],
            d.line or 0,
            "marp-syntax",
            "class comment -> '@' line",
        )
    ]


RULES: dict[str, Callable[[_Src, Diagnostic], list[Edit]]] = {
    "missing-end": _missing_end,
    "unknown-token": _unknown_token,
    "unknown-attr": _unknown_attr,
    "unknown-icon": _unknown_icon,
    "unknown-callout": _unknown_callout,
    "unknown-header": _unknown_header,
    "bad-grid": _second_grid,
    "image-alt": _image_alt,
    "unclosed-fence": _unclosed_fence,
    "bullet-star": _bullet_star,
    "note-line": _note_line,
    "comment-notes": _comment_notes,
    "marp-syntax": _marp_class,
}


# --------------------------------------------------------------------------- driver


def _collect(lines: list[str], diagnostics: list[Diagnostic]) -> list[Edit]:
    inside, _ = fence_map(lines)
    src = _Src(lines, inside)
    edits: list[Edit] = []
    seen_fence = False
    for d in diagnostics:
        fn = RULES.get(d.rule or "")
        if fn is None:
            continue
        if d.rule == "unclosed-fence":  # later fences depend on the first one: one per pass
            if seen_fence:
                continue
            seen_fence = True
        try:
            edits.extend(fn(src, d))
        except Exception:  # a fixer must never break the check
            continue
    return edits


def _apply(lines: list[str], edits: list[Edit]) -> tuple[list[str], list[Edit]]:
    """Apply non-overlapping edits bottom-up; returns the new lines and the edits that were applied."""
    out, applied = list(lines), []
    taken: list[tuple[int, int]] = []
    for e in sorted(edits, key=lambda e: (e.start, e.end), reverse=True):
        lo, hi = e.start, max(e.end, e.start + (1 if e.start == e.end else 0))
        if any(lo < b and a < hi or e.start == a for a, b in taken):
            continue
        taken.append((e.start, hi))
        out[e.start : e.end] = e.new
        applied.append(e)
    return out, applied


def fix_text(text: str, diagnostics_of: Callable[[str], list[Diagnostic]]) -> tuple[str, list[Fixed]]:
    """Fix ``text`` until nothing mechanical is left. ``diagnostics_of`` parses and returns diagnostics."""
    fixed: list[Fixed] = []
    eol = "\r\n" if "\r\n" in text else "\n"
    for _ in range(MAX_PASSES):
        lines = split_lines(text)
        edits = _collect(lines, diagnostics_of(text))
        new, applied = _apply(lines, edits)
        if not applied or new == lines:
            break
        fixed.extend(Fixed(e.line, e.rule, e.what) for e in sorted(applied, key=lambda e: e.start) if e.what)
        text = eol.join(new)
    return text, fixed
