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
    from ..theme import TokenValueError, canonical_token, normalize_token

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
