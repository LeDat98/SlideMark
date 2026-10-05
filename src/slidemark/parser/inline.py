"""Markdown-it configuration and inline text -> ``Run`` conversion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from ..ir import Run
from .attrs import Attrs, parse_attr_body, split_trailing_attrs  # noqa: F401

_SOFT = "\x00soft\x00"
BR_SPLIT = re.compile(r"<br[ \t]*/?>", re.I)


# --------------------------------------------------------------------------- custom inline rules


def _tokenize_range(state: Any, start: int, end: int) -> None:
    old_pos, old_max = state.pos, state.posMax
    state.pos, state.posMax = start, end
    state.md.inline.tokenize(state)
    state.pos, state.posMax = old_pos, old_max


def _mark_rule(state: Any, silent: bool) -> bool:
    """``==text==`` -> mark_open ... mark_close."""
    start, src = state.pos, state.src
    if src[start : start + 2] != "==":
        return False
    end = src.find("==", start + 2, state.posMax)
    if end < 0 or end == start + 2:
        return False
    inner = src[start + 2 : end]
    if inner[0].isspace() or inner[-1].isspace():
        return False
    if not silent:
        state.push("mark_open", "mark", 1)
        _tokenize_range(state, start + 2, end)
        state.push("mark_close", "mark", -1)
    state.pos = end + 2
    return True


def _span_rule(state: Any, silent: bool) -> bool:
    """``[text]{.class key=value}`` -> span_open ... span_close."""
    start, src = state.pos, state.src
    if src[start] != "[":
        return False
    end = state.md.helpers.parseLinkLabel(state, start, True)
    if end < 0:
        return False
    p = end + 1
    if p >= state.posMax or src[p] != "{":
        return False
    close = src.find("}", p, state.posMax)
    if close < 0:
        return False
    attrs = parse_attr_body(src[p + 1 : close])
    if attrs is None:
        return False
    if not silent:
        tok = state.push("span_open", "span", 1)
        tok.meta = {"attrs": attrs}
        _tokenize_range(state, start + 1, end)
        state.push("span_close", "span", -1)
    state.pos = close + 1
    return True


def _script_rule(ch: str, name: str):
    def rule(state: Any, silent: bool) -> bool:
        start, src = state.pos, state.src
        if src[start] != ch or start + 1 >= state.posMax or src[start + 1] == ch:
            return False
        end = start + 1
        while end < state.posMax and src[end] != ch:
            if src[end].isspace():
                return False
            end += 1
        if end >= state.posMax or end == start + 1:
            return False
        if not silent:
            state.push(f"{name}_open", name, 1)
            t = state.push("text", "", 0)
            t.content = src[start + 1 : end]
            state.push(f"{name}_close", name, -1)
        state.pos = end + 1
        return True

    return rule


def make_md() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])
    md.disable(["code", "lheading", "reference"])
    md.inline.ruler.before("emphasis", "mark", _mark_rule)
    md.inline.ruler.before("link", "span", _span_rule)
    md.inline.ruler.before("strikethrough", "sub", _script_rule("~", "sub"))
    md.inline.ruler.before("strikethrough", "sup", _script_rule("^", "sup"))
    return md


MD = make_md()


# --------------------------------------------------------------------------- runs


@dataclass
class ImageRef:
    src: str
    alt: str
    attrs: Attrs | None


def _is_cjk(ch: str) -> bool:
    return bool(ch) and ord(ch) >= 0x2E80


def _finish(runs: list[Run]) -> list[Run]:
    """Resolve soft breaks (a space, nothing between two CJK characters) and merge equal neighbours."""
    for i, r in enumerate(runs):
        if r.text != _SOFT:
            continue
        prev = next((runs[j].text[-1:] for j in range(i - 1, -1, -1) if runs[j].text != _SOFT), "")
        nxt = next((runs[j].text[:1] for j in range(i + 1, len(runs)) if runs[j].text != _SOFT), "")
        r.text = "" if _is_cjk(prev) and _is_cjk(nxt) else " "
    out: list[Run] = []
    for r in runs:
        if not r.text:
            continue
        if out and r.text != "\n" and out[-1].text != "\n":
            a = out[-1].model_dump(exclude={"text"})
            if a == r.model_dump(exclude={"text"}):
                out[-1].text += r.text
                continue
        out.append(r)
    return out


def inline_items(children: list[Token] | None, allow_images: bool = False) -> list[Run | ImageRef]:
    """Convert inline tokens to runs; with ``allow_images`` images are returned as ``ImageRef`` items."""
    items: list[Run | ImageRef] = []
    buf: list[Run] = []
    bold = italic = strike = mark = sub = sup = 0
    links: list[str | None] = []
    colors: list[str | None] = []

    def flush() -> None:
        if buf:
            items.extend(_finish(buf))
            buf.clear()

    def run(text: str, **extra: Any) -> None:
        buf.append(
            Run(
                text=text,
                bold=bold > 0,
                italic=italic > 0,
                strike=strike > 0,
                sub=sub > 0,
                sup=sup > 0,
                color=next((c for c in reversed(colors) if c), "accent" if mark else None),
                link=links[-1] if links else None,
                **extra,
            )
        )

    kids = children or []
    i = 0
    while i < len(kids):
        t = kids[i]
        ty = t.type
        if ty == "text":
            for k, part in enumerate(BR_SPLIT.split(t.content)):
                if k:
                    run("\n")  # <br> is a line break
                if part:
                    run(part)
        elif ty == "code_inline":
            run(t.content, code=True)
        elif ty == "softbreak":
            buf.append(Run(text=_SOFT))
        elif ty == "hardbreak":
            buf.append(Run(text="\n"))
        elif ty == "strong_open":
            bold += 1
        elif ty == "strong_close":
            bold -= 1
        elif ty == "em_open":
            italic += 1
        elif ty == "em_close":
            italic -= 1
        elif ty == "s_open":
            strike += 1
        elif ty == "s_close":
            strike -= 1
        elif ty == "mark_open":
            mark += 1
        elif ty == "mark_close":
            mark -= 1
        elif ty == "sub_open":
            sub += 1
        elif ty == "sub_close":
            sub -= 1
        elif ty == "sup_open":
            sup += 1
        elif ty == "sup_close":
            sup -= 1
        elif ty == "link_open":
            links.append(t.attrGet("href") if t.attrs else None)  # type: ignore[arg-type]
        elif ty == "link_close":
            if links:
                links.pop()
        elif ty == "span_open":
            a: Attrs = (t.meta or {}).get("attrs") or Attrs()
            colors.append(a.kv.get("color") or (a.classes[0] if a.classes else None))
        elif ty == "span_close":
            if colors:
                colors.pop()
        elif ty == "image":
            alt = t.content or ""
            if allow_images:
                attrs = None
                nxt = kids[i + 1] if i + 1 < len(kids) else None
                if nxt is not None and nxt.type == "text" and nxt.content.startswith("{"):
                    end = nxt.content.find("}")
                    if end > 0:
                        attrs = parse_attr_body(nxt.content[1:end])
                        if attrs is not None:
                            nxt.content = nxt.content[end + 1 :]
                flush()
                items.append(ImageRef(src=str(t.attrGet("src") or ""), alt=alt, attrs=attrs))
            elif alt:
                run(alt)
        i += 1
    flush()
    return items


def inline_runs(text: str) -> list[Run]:
    """Parse a single line of inline Markdown into runs (images become their alt text)."""
    toks = MD.parseInline(text)
    children = toks[0].children if toks else []
    return [r for r in inline_items(children) if isinstance(r, Run)]
