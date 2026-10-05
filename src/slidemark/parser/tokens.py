"""Header design tokens: ``colors:`` / ``fonts:`` / ``sizes:`` / ``style:`` lines and YAML maps."""

from __future__ import annotations

import re
from typing import Any

from ..ir import CssRule, Deck, Style
from .ctx import Ctx

TOKEN_GROUPS = ("colors", "fonts", "sizes", "style")
THEME_MAPS = ("classes", "layout", "render")  # full theme-like mappings in YAML front matter
_OPEN, _CLOSE = "([{", ")]}"


def split_pairs(text: str) -> list[str]:
    """Split on spaces; quotes and (...) groups keep their inner spaces. Tolerates unbalanced input."""
    out: list[str] = []
    cur: list[str] = []
    quote = ""
    depth = 0
    for ch in text:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
            cur.append(ch)
        elif ch in _OPEN:
            depth += 1
            cur.append(ch)
        elif ch in _CLOSE:
            depth = max(0, depth - 1)
            cur.append(ch)
        elif ch.isspace() and depth == 0:
            if cur:
                out.append("".join(cur))
                cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur))
    return out


def _unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v[:1] in "\"'":  # unbalanced opening quote: keep the rest
        return v[1:]
    return v


def _split_key(pair: str) -> tuple[str, str | None]:
    """``key=value`` -> (key, value); the first ``=`` outside quotes splits. No ``=`` -> (pair, None)."""
    key, eq, val = pair.partition("=")
    return key.strip(), (_unquote(val) if eq else None)


_CSS_ELEMENTS = {"slide", "h1", "h2", "p", "li", "table", "th", "td", "code", "img"}
_PT_PROPS = {
    "border-radius",
    "border-width",
    "letter-spacing",
    "font-size",
    "gap",
    "padding",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "margin",
}
_CSS_CLASSES = {"lead", "conclusion", "footnote", "subtitle", "box", "kpi", "chart"}


def _style_css_key(key: str) -> tuple[str, str] | None:
    """``h1.letter-spacing`` -> (selector ``h1``, css property); None when the key is not an element style."""
    from .css import SUPPORTED

    head, dot, rest = key.strip().partition(".")
    head = head.lower()
    if not dot or (head not in _CSS_ELEMENTS and head not in _CSS_CLASSES):
        return None
    prop = rest.strip().lower().replace("_", "-")
    if prop not in SUPPORTED:
        return None
    return (head if head in _CSS_ELEMENTS else "." + head), prop


def _style_css(deck: Deck, group: str, key: str, value: str, ctx: Ctx, line: int) -> bool:
    """Route ``style:`` keys like ``h1.letter-spacing=2pt`` into a deck-level CSS rule (True = handled)."""
    from ..theme import Theme, canonical_token

    if group != "style":
        return False
    hit = _style_css_key(key)
    if hit is None:
        return False
    sel, prop = hit
    if prop in _PT_PROPS and re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)", value.strip()):
        value = value.strip() + "pt"  # bare numbers are pt in tokens (css needs a unit)
    path, _ = canonical_token(group, key)
    if path is not None and (sel[0] == "." or path in Theme.model_fields):
        return False  # existing meanings win: class tokens (card.fill, kpi.color) and Theme fields
    deck.attrs.setdefault("_style_css", {}).setdefault(sel, []).append((prop, value, line))
    return True


def style_css_rules(deck: Deck, ctx: Ctx) -> list[CssRule]:
    """Rules from ``style: h1.x=y`` keys, one per selector (declarations merged). Never raises."""
    from .css import known_color_names, parse_declarations

    src = deck.attrs.pop("_style_css", {})
    names = known_color_names(deck)
    rules: list[CssRule] = []
    for sel, decls in src.items():
        merged: dict[str, tuple[str, int]] = {}
        for prop, value, line in decls:
            merged[prop] = (value, line)
        style = Style()
        for prop, (value, line) in merged.items():
            st, _ = parse_declarations(f"{prop}: {value}", line, ctx, names)
            style = style.model_copy(update={k: v for k, v in st.model_dump().items() if v is not None})
        if any(v is not None for v in style.model_dump().values()):
            rules.append(CssRule(selector=sel, style=style, line=min(ln for _, ln in merged.values())))
    return rules


def set_token(deck: Deck, group: str, key: str, value: str, ctx: Ctx, line: int) -> None:
    from ..theme import TokenValueError, canonical_token, normalize_token

    if _style_css(deck, group, key, value, ctx, line):
        return
    path, hint = canonical_token(group, key)
    if path is None:
        ctx.warn(f"unknown token '{key}' in {group}:", line, "unknown-token", hint.replace("\n", " "))
        return
    try:  # lenient: a bare word may be a color declared later; apply_tokens checks it again
        normalize_token(path, value, None)
    except TokenValueError as e:
        ctx.warn(f"token {key}={value}: {e}"[:140], line, "bad-token", e.hint)
        return
    if path.startswith("fonts.") and "," in value:  # PowerPoint stores one typeface per role
        first = value.split(",")[0].strip().strip("\"'")
        ctx.add(
            "info",
            f"font list '{value}': PowerPoint keeps one family per role, using '{first}'",
            line,
            "font-list",
            f'write {key}="{first}" (viewers without it substitute a similar font)',
        )
        value = first
    deck.tokens[path] = value
    deck.attrs.setdefault("_token_src", {})[path] = (line, key, value)


def finish_tokens(deck: Deck, ctx: Ctx) -> None:
    """After the header (and header CSS): re-check values whose bare words may be color names declared later.

    The parse-time check is lenient (any bare word passes); here names declared anywhere in the header (and
    every preset's color names) count. A word still unknown is dropped with one ``bad-token`` warning that
    carries the header line; ``apply_tokens`` re-checks against the chosen theme.
    """
    from ..theme import TokenValueError, normalize_token
    from .css import known_color_names

    src = deck.attrs.pop("_token_src", {})
    names = known_color_names(deck)
    for path, (line, key, value) in src.items():
        if deck.tokens.get(path) != value:
            continue
        try:
            normalize_token(path, value, names)
        except TokenValueError as e:
            del deck.tokens[path]
            ctx.warn(f"token {key}={value}: {e}"[:140], line, "bad-token", e.hint)


def parse_token_line(deck: Deck, group: str, value: str, ctx: Ctx, line: int) -> None:
    for pair in split_pairs(value):
        key, val = _split_key(pair)
        if val is None:
            ctx.warn(
                f"'{pair}' in {group}: is not key=value",
                line,
                "bad-token",
                "write key=value, e.g. primary=#7C5CFF",
            )
        else:
            set_token(deck, group, key, val, ctx, line)


def _flatten(prefix: str, data: Any) -> list[tuple[str, str]]:
    if isinstance(data, dict):
        out: list[tuple[str, str]] = []
        for k, v in data.items():
            out += _flatten(f"{prefix}.{k}" if prefix else str(k), v)
        return out
    return [(prefix, "" if data is None else str(data))]


def parse_token_map(deck: Deck, group: str, data: Any, ctx: Ctx, line: int) -> None:
    """YAML value of ``colors``/``fonts``/``sizes``/``style``/``classes``/``layout``/``render``."""
    if not isinstance(data, dict):
        if isinstance(data, str):
            parse_token_line(deck, group, data, ctx, line)
        return
    for key, val in _flatten("" if group in TOKEN_GROUPS else group, data):
        set_token(deck, group if group in TOKEN_GROUPS else "style", key, val, ctx, line)
