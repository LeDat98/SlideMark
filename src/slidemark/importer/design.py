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


def edited_diag(n: int) -> Diagnostic:
    return Diagnostic(
        level="info",
        message="html slide was edited in PowerPoint; the edited shapes were imported, not the stored HTML",
        slide=n,
        rule="import-html-edited",
        hint="re-write the slide as @html if the stored HTML should win",
    )
