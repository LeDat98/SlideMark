"""Lenient input: Marp / Slidev / reveal.js habits accepted with a warning and a hint.

``normalize`` runs once over the lines after the deck header. It never changes the number of lines (so
diagnostics keep their line numbers): foreign syntax is blanked or rewritten in place, and what it meant is
returned as ``Rec`` records tied to a source line. ``parse_deck`` hands each record to the slide it falls in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..ir import Deck

KV = re.compile(r"^([A-Za-z_][\w-]*)[ \t]*:[ \t]*(.*?)[ \t]*$")
H_RE = {n: re.compile(r"^" + "#" * n + r"(?:[ \t]|$)") for n in (1, 2, 3)}
SLOT_RE = re.compile(r"^::[\w-]+::[ \t]*$")
NOTE_RE = re.compile(r"^notes?[ \t]*:[ \t]*(.*)$", re.I)
STAR_RE = re.compile(r"^[ \t]*\*[ \t]+(?=\S)(.*)$")
BR_RE = re.compile(r"<br[ \t]*/?>", re.I)
CLASS_NAME = re.compile(r"^[A-Za-z_][\w-]*$")

MARP_KEYS = {
    "class",
    "paginate",
    "footer",
    "header",
    "theme",
    "size",
    "style",
    "headingdivider",
    "backgroundcolor",
    "backgroundimage",
    "color",
    "lang",
    "math",
    "marp",
}
SLIDEV_KEYS = {
    "layout",
    "class",
    "background",
    "transition",
    "hide",
    "hideintoc",
    "routealias",
    "clicks",
    "name",
}
SLIDEV_LAYOUTS = {"cover": "cover", "section": "section", "center": "center"}
COLUMNS_HINT = "use '@2' and one '## box' per column"


@dataclass
class Rec:
    """Something the pre-pass found at 0-based line ``idx``. kind: diag | note | at."""

    idx: int
    kind: str
    value: str = ""
    level: str = "warning"
    rule: str = ""
    hint: str = ""


def _truthy(v: str) -> bool:
    return v.strip().lower() in ("true", "on", "yes", "1")


def _names(val: str) -> str:
    return " ".join(c for c in val.split() if CLASS_NAME.match(c))


def normalize(lines: list[str], inside: list[bool], start: int, deck: Deck) -> list[Rec]:
    recs: list[Rec] = []
    n = len(lines)

    def diag(i: int, msg: str, rule: str, hint: str, level: str = "warning") -> None:
        recs.append(Rec(i, "diag", msg, level, rule, hint))

    def blank(a: int, b: int) -> None:
        for k in range(a, b + 1):
            lines[k] = ""

    # `###`-only deck: the `###` lines are the slide starts
    seen = {1: False, 2: False, 3: False}
    for i in range(start, n):
        if not inside[i]:
            for lv, rx in H_RE.items():
                if rx.match(lines[i]):
                    seen[lv] = True
    if seen[3] and not seen[1] and not seen[2]:
        first = True
        for i in range(start, n):
            if not inside[i] and H_RE[3].match(lines[i]):
                lines[i] = lines[i][2:]
                if first:
                    msg = "no '# ' headings: '### ' lines are used as slide titles"
                    diag(i, msg, "h3-slides", "start slides with '# Title'; '##' is a box inside a slide")
                    first = False

    def marp_directive(i: int, key: str, val: str) -> None:
        k = key.lstrip("_").lower()
        if k == "class":
            names = _names(val)
            if names:
                recs.append(Rec(i, "at", names))
            diag(i, f"Marp directive '{key}'", "marp-syntax", f"use a line '@{names or 'dense'}' instead")
        elif k == "paginate":
            if _truthy(val):
                deck.slide_number = True
            diag(i, f"Marp directive '{key}'", "marp-syntax", "use the header line 'num: on'")
        elif k == "footer" and not key.startswith("_"):
            deck.footer = val.strip("\"'") or None
            diag(i, f"Marp directive '{key}'", "marp-syntax", "use the header line 'footer: text'")
        else:
            diag(
                i,
                f"Marp directive '{key}' ignored",
                "marp-syntax",
                "SlideMark styles slides with theme and '@' classes",
            )

    def slidev_key(i: int, key: str, val: str) -> None:
        k = key.lower()
        val = val.strip().strip("\"'")
        if k == "layout":
            if val in SLIDEV_LAYOUTS:
                recs.append(Rec(i, "at", SLIDEV_LAYOUTS[val]))
            elif val != "default":
                diag(i, f"Slidev layout '{val}' ignored", "slidev-syntax", COLUMNS_HINT)
        elif k == "class":
            if _names(val):
                recs.append(Rec(i, "at", _names(val)))
        elif k == "background" and val:
            recs.append(Rec(i, "at", f'bg="{val}"' if " " in val else f"bg={val}"))
        elif k == "transition" and CLASS_NAME.match(val):
            recs.append(Rec(i, "at", f"t={val}"))
        elif k == "hide" and _truthy(val):
            recs.append(Rec(i, "at", "hidden"))
        else:
            diag(i, f"Slidev key '{key}' ignored", "slidev-syntax", "per-slide settings go on an '@' line")

    star_warned = br_warned = False
    i = start
    while i < n:
        if inside[i]:
            i += 1
            continue
        line = lines[i]
        s = line.strip()
        if H_RE[1].match(line) or s == "---":
            star_warned = br_warned = False

        if s == "---":  # Slidev per-slide frontmatter: `---` / key: value lines / `---`
            j = i + 1
            while j < n and not inside[j] and KV.match(lines[j]):
                j += 1
            if j > i + 1 and j < n and not inside[j] and lines[j].strip() == "---":
                first_kv = KV.match(lines[i + 1])
                if first_kv and first_kv.group(1).lower() in SLIDEV_KEYS:
                    diag(
                        i,
                        "Slidev per-slide frontmatter",
                        "slidev-syntax",
                        "put per-slide settings on an '@' line",
                    )
                    for k in range(i + 1, j):
                        m = KV.match(lines[k])
                        if m:
                            slidev_key(k, m.group(1), m.group(2))
                    blank(i + 1, j)
                    i = j + 1
                    continue
            i += 1
            continue

        if s.startswith("<!--"):  # Marp directives, otherwise speaker notes
            parts = [s[4:]]
            end_line = i if "-->" in s[4:] else -1
            if end_line < 0:
                for j in range(i + 1, n):
                    if inside[j]:
                        break
                    parts.append(lines[j])
                    if "-->" in lines[j]:
                        end_line = j
                        break
            if end_line < 0:
                diag(i, "HTML comment is never closed", "unclosed-comment", "close it with -->")
                i += 1
                continue
            body, _, tail = "\n".join(parts).partition("-->")
            text = "\n".join(p.strip() for p in body.splitlines()).strip()
            blank(i, end_line)
            lines[end_line] = tail
            kvs = [KV.match(p) for p in text.splitlines() if p.strip()]
            if kvs and all(kvs) and kvs[0] and kvs[0].group(1).lstrip("_").lower() in MARP_KEYS:
                for m in kvs:
                    if m:
                        marp_directive(i, m.group(1), m.group(2))
            elif text:
                recs.append(Rec(i, "note", text))
                diag(
                    i,
                    "HTML comment used as speaker notes",
                    "comment-notes",
                    "write speaker notes as '??? text'",
                    "info",
                )
            i = end_line + 1
            continue

        note = NOTE_RE.match(s)
        if SLOT_RE.match(s):
            diag(i, f"slot line '{s}' ignored", "slot-syntax", COLUMNS_HINT)
            lines[i] = ""
        elif note:
            parts = [note.group(1)] if note.group(1) else []
            j = i + 1
            while (
                j < n
                and not inside[j]
                and lines[j].strip()
                and not lines[j].startswith(("#", "@", "---", "※", "???", "<!--"))
            ):
                parts.append(lines[j].strip())
                j += 1
            recs.append(Rec(i, "note", "\n".join(parts)))
            diag(i, "'Note:' line used as speaker notes", "note-line", "write speaker notes as '??? text'")
            blank(i, j - 1)
            i = j
            continue
        else:
            m = STAR_RE.match(line)
            if m and m.group(1).strip(" *") and not star_warned:
                diag(i, "'* ' bullet", "bullet-star", "use '- ' for bullets")
                star_warned = True
            if BR_RE.search(line) and not br_warned:
                diag(
                    i,
                    "<br> in text",
                    "html-br",
                    "use two trailing spaces or a new paragraph for a line break",
                )
                br_warned = True
        i += 1
    return recs
