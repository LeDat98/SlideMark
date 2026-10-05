"""Stored design (``render.design_part``) -> header token lines, css fences and ``@html`` slides."""

from __future__ import annotations

import re
from collections import Counter
from html.parser import HTMLParser
from typing import Any

from ..ir import Diagnostic
from .emit import esc

_GROUPS = ("colors", "fonts", "sizes")


def _key_for(path: str) -> tuple[str, str]:
    """(group, shortest key) that ``canonical_token`` maps back to ``path``."""
    from ..theme import STYLE_ALIASES, canonical_token

    head, _, tail = path.partition(".")
    if head in _GROUPS and tail and canonical_token(head, tail)[0] == path:
        return head, tail
    cands = [a for a, p in STYLE_ALIASES.items() if p == path]
    if path.startswith("classes.") and path.count(".") == 2:
        cands.append(path.split(".", 1)[1])
    cands.append(path)
    cands.sort(key=len)
    for k in cands:
        if canonical_token("style", k)[0] == path:
            return "style", k
    return "style", path


def _val(v: str) -> str:
    if re.search(r"[\s\"'()]", v) or not v:
        return f"'{v}'" if '"' in v else f'"{v}"'
    return v


def token_lines(tokens: dict[str, str]) -> list[str]:
    """``colors: a=b ...`` / ``fonts:`` / ``sizes:`` / ``style:`` lines, in that order."""
    groups: dict[str, list[str]] = {g: [] for g in (*_GROUPS, "style")}
    for path, raw in tokens.items():
        g, k = _key_for(path)
        groups[g].append(f"{k}={_val(str(raw))}")
    return [f"{g}: {' '.join(items)}" for g, items in groups.items() if items]


def css_fence(rules: list[list[str]]) -> list[str]:
    """A ```css fence for stored ``[[selectors, declarations], ...]``; empty when there are no rules."""
    if not rules:
        return []
    return ["```css", *(f"{sel} {{ {decl} }}" for sel, decl in rules), "```"]


def is_template_path(theme: Any) -> bool:
    """True for a ``theme:`` that names a .pptx/.potx template file rather than a preset."""
    return isinstance(theme, str) and theme.lower().endswith((".pptx", ".potx"))


def design_header(design: dict[str, Any], src_name: str = "") -> tuple[list[str], list[str]]:
    """(``theme:`` + token lines, header css fence lines) of the stored design.

    A stored template path is relative to where the deck was first built; the imported file itself is the
    template that is always at hand (``src_name``).
    """
    head: list[str] = []
    theme = design.get("theme")
    if theme:
        head.append(f"theme: {src_name if src_name and is_template_path(theme) else theme}")
    head += token_lines(design.get("tokens") or {})
    return head, css_fence(design.get("css") or [])


# --------------------------------------------------------------------------- html slides


class _Visible(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    @staticmethod
    def text_of(html: str) -> list[str]:
        p = _Visible()
        try:
            p.feed(html)
            p.close()
        except Exception:  # noqa: S110 - best effort on broken markup
            pass
        return p.parts

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def _words(text: str) -> Counter[str]:
    return Counter(re.sub(r"\s+", " ", text).lower().split())


def html_words(html: str) -> Counter[str]:
    """Lower-cased word multiset of the visible text of ``html`` (scripts and styles skipped)."""
    p = _Visible()
    try:
        p.feed(html)
        p.close()
    except Exception:  # noqa: S110 - best effort on broken markup
        pass
    return _words(" ".join(p.parts))


def slide_words(sd) -> Counter[str]:
    """Word multiset of the text frames and table cells of an imported slide."""
    out: list[str] = []
    for it in sd.items:
        if it.kind == "text":
            out.append(it.text or "")
        elif it.kind == "table":
            out += [q.plain for r in it.rows for c in r for q in c.paras]
    return _words(" ".join(out))


def html_slide_lines(ent: dict[str, Any], sd, notes: list[str]) -> list[str]:
    """``# Title`` + ``@html`` + the html fence (+ slide css, notes) for a stored, unedited html slide."""
    title = ent.get("title")
    lines = ["# " + esc(title)] if title else ["---"]
    tokens = ["html", *ent.get("cls", [])]
    if sd.transition:
        tokens.append("t=" + sd.transition)
    if sd.hidden:
        tokens.append("hidden")
    lines.append("@" + " ".join(tokens))
    html = ent["html"]
    ticks = "`" * max(3, max((len(m) + 1 for m in re.findall(r"`+", html)), default=0))
    lines += [ticks + "html", html.rstrip("\n"), ticks]
    return lines + notes


def _chars(text: str) -> Counter[str]:
    """Letters and digits only: immune to how punctuation, tags and line breaks split words."""
    return Counter(c for c in text.lower() if c.isalnum())


def _item_words(it) -> Counter[str]:
    if it.kind == "table":
        return _chars(" ".join(q.plain for r in it.rows for c in r for q in c.paras))
    return _chars(it.text or "")


def _overlap(a, box) -> bool:
    x0, y0, x1, y1 = box
    return a.x < x1 and a.x + a.w > x0 and a.y < y1 and a.y + a.h > y0


def claim_fences(ent: dict[str, Any] | None, sd, n: int, diags: list[Diagnostic]) -> list[dict[str, Any]]:
    """Remove from ``sd`` the shapes that an unedited stored ```html fence produced; return those fences.

    A fence is claimed when the text items of the slide cover exactly its visible words; the text-less shapes
    (card fills, bars) inside their bounding box go with it. Otherwise the shapes stay (info diagnostic).
    """
    fences = [f for f in (ent or {}).get("fences") or [] if isinstance(f, dict) and f.get("src")]
    won: list[dict[str, Any]] = []
    for f in fences:
        try:
            need = _chars(" ".join(_Visible.text_of(f["src"])))
            if not need:
                continue
            left = Counter(need)
            hit = []
            for it in sd.items:
                if it.kind not in ("text", "table") or it.ph in (
                    "title",
                    "ctrTitle",
                    "subTitle",
                    "ftr",
                    "sldNum",
                ):
                    continue
                w = _item_words(it)
                if w and not (w - left):
                    left -= w
                    hit.append(it)
            if not hit or +left:
                diags.append(edited_diag(n, "html block"))
                continue
            box = (
                min(i.x for i in hit),
                min(i.y for i in hit),
                max(i.x + i.w for i in hit),
                max(i.y + i.h for i in hit),
            )
            gone = {id(i) for i in hit}
            for it in sd.items:
                if (
                    it.kind in ("shape", "line", "image")
                    and not it.ph
                    and not _item_words(it)
                    and _overlap(it, box)
                ):
                    gone.add(id(it))
            sd.items = [i for i in sd.items if id(i) not in gone]
            won.append(f)
        except Exception:  # noqa: S112 - best effort: keep the shapes
            continue
    return won


def fence_lines(f: dict[str, Any]) -> list[str]:
    src = str(f["src"])
    ticks = "`" * max(3, max((len(m) + 1 for m in re.findall(r"`+", src)), default=0))
    info = str(f.get("info") or "")
    return [f"{ticks}html {info}".rstrip(), src.rstrip("\n"), ticks]


def insert_fences(lines: list[str], won: list[dict[str, Any]], tail: int) -> list[str]:
    """Put the claimed fences back: right after the heading (``first``) or before the ``tail`` notes lines."""
    if not won:
        return lines
    head = 0
    if lines and (lines[0].startswith("# ") or lines[0] == "---"):
        head = 1
        while head < len(lines) and lines[head].startswith("@"):
            head += 1
    end = len(lines) - tail
    out = list(lines)
    first = [fence_lines(f) for f in won if f.get("first")]
    rest = [fence_lines(f) for f in won if not f.get("first")]
    for blk in reversed(rest):
        out[end:end] = blk
    for blk in reversed(first):
        out[head:head] = blk
    return out


def _key(text: str) -> str:
    return re.sub(r"[\W_]+", "", text).lower()


def tag_boxes(lines: list[str], ent: dict[str, Any] | None) -> list[str]:
    """Re-attach the stored classes and ids (``el``) to the ``##`` / ``###`` box headings they belonged to."""
    todo = [e for e in (ent or {}).get("el") or [] if isinstance(e, list) and len(e) > 1]
    if not todo:
        return lines
    out = list(lines)
    in_fence = False
    for k, ln in enumerate(out):
        if ln.startswith(("```", "~~~")):
            in_fence = not in_fence
        m = None if in_fence else re.match(r"(#{2,3} )(.*?)(?: \{([^{}]*)\})?$", ln)
        if not m:
            continue
        for e in todo:
            if _key(str(e[0])) == _key(m.group(2)):
                have = (m.group(3) or "").split()
                add = [("." + n if not n.startswith("#") else n) for n in map(str, e[1:])]
                add = [t for t in add if t not in have]
                out[k] = f"{m.group(1)}{m.group(2)} {{{' '.join([*add, *have])}}}" if add else ln
                todo.remove(e)
                break
    return out


def edited(ent: dict[str, Any], sd) -> bool:
    """True when the slide's text no longer matches the visible text of its stored HTML."""
    return html_words(ent["html"]) != slide_words(sd)


def match_slide(design: dict[str, Any], index: int, slide_id: int | None) -> dict[str, Any] | None:
    """The stored entry for a slide: by ``p:sldId`` id, else (ids unknown) by position."""
    ents = design.get("slides") or []
    for e in ents:
        if slide_id is not None and e.get("id") == slide_id:
            return e
    return (
        None
        if slide_id is not None and any("id" in e for e in ents)
        else next((e for e in ents if e.get("i") == index - 1 and "id" not in e), None)
    )


def edited_diag(n: int, what: str = "html slide") -> Diagnostic:
    return Diagnostic(
        level="info",
        message=f"{what} was edited in PowerPoint; the edited shapes were imported, not the stored HTML",
        slide=n,
        rule="import-html-edited",
        hint="re-write the slide as @html if the stored HTML should win",
    )
