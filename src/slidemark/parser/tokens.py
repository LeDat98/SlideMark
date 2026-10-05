"""Header design tokens: ``colors:`` / ``fonts:`` / ``sizes:`` / ``style:`` lines and YAML maps."""

from __future__ import annotations

from typing import Any

from ..ir import Deck
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


def set_token(deck: Deck, group: str, key: str, value: str, ctx: Ctx, line: int) -> None:
    from ..theme import canonical_token

    path, hint = canonical_token(group, key)
    if path is None:
        ctx.warn(f"unknown token '{key}' in {group}:", line, "unknown-token", hint.replace("\n", " "))
    else:
        deck.tokens[path] = value


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
