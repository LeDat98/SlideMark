"""DF1: no hard-coded design in layout/ and render/ (docs/DESIGN_FREEDOM.md, rule 1).

Scans every module with ``ast`` and fails on
- color literals: a string that is exactly a hex color (``#RRGGBB``, ``#RRGGBBAA`` or bare ``RRGGBB``);
- fixed point sizes: ``Pt(<number>)`` and ``font_size=<number>`` keyword arguments.

Looks belong in design tokens (``theme.py``: ``colors``, ``sizes``, ``layout``, ``render``). The allowlist
holds the few literals that are not looks; each entry says why.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import slidemark

ROOT = Path(slidemark.__file__).parent
SCANNED = [*sorted((ROOT / "layout").rglob("*.py")), *sorted((ROOT / "render").rglob("*.py"))]
HEX = re.compile(r"#?(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6})")

# (file relative to src/slidemark, literal) -> reason
ALLOWED_LITERALS: dict[tuple[str, str], str] = {
    (
        "render/util.py",
        "#000000",
    ): "last-resort fallback of hex6/rgb when nothing resolves (not a design choice)",
    ("render/util.py", "FFFFFF"): "CSS named color table (white, transparent): the CSS standard, not a look",
    ("render/util.py", "000000"): "CSS named color table (black) and the unresolvable-value result",
    ("render/util.py", "FF0000"): "CSS named color table (red)",
    ("render/util.py", "008000"): "CSS named color table (green)",
    ("render/util.py", "0000FF"): "CSS named color table (blue)",
    ("render/util.py", "FFFF00"): "CSS named color table (yellow)",
    ("render/util.py", "808080"): "CSS named color table (gray, grey)",
    ("render/util.py", "FFA500"): "CSS named color table (orange)",
}
# files whose Pt(...)/font_size numbers are not slide looks (none today)
ALLOWED_SIZES: dict[tuple[str, int], str] = {}


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def _findings() -> list[str]:
    out: list[str] = []
    for path in SCANNED:
        rel = _rel(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if HEX.fullmatch(node.value) and (rel, node.value.upper()) not in {
                    (f, v.upper()) for f, v in ALLOWED_LITERALS
                }:
                    out.append(f"{rel}:{node.lineno}: hex color literal {node.value!r} (use a theme token)")
            elif isinstance(node, ast.Call):
                fn = node.func
                name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else ""
                if name == "Pt" and node.args and _is_number(node.args[0]):
                    if (rel, node.lineno) not in ALLOWED_SIZES:
                        out.append(f"{rel}:{node.lineno}: Pt({node.args[0].value}) (use a size token)")  # type: ignore[attr-defined]
                for kw in node.keywords:
                    if (
                        kw.arg == "font_size"
                        and _is_number(kw.value)
                        and (rel, node.lineno) not in ALLOWED_SIZES
                    ):
                        out.append(f"{rel}:{node.lineno}: font_size={kw.value.value} (use theme.sizes)")  # type: ignore[attr-defined]
    return out


def _is_number(node: ast.AST) -> bool:
    """A non-zero number literal (``Pt(0)`` is "no spacing", not a size)."""
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
        and node.value != 0
    )


def test_scan_covers_the_layout_and_render_packages():
    names = {_rel(p) for p in SCANNED}
    assert {"layout/engine.py", "layout/measure.py", "render/__init__.py", "render/text.py"} <= names


def test_no_hex_colors_or_fixed_font_sizes_in_layout_and_render():
    found = _findings()
    assert not found, "hard-coded design (move it into tokens):\n" + "\n".join(found)


def test_scanner_detects_violations(tmp_path):
    src = 'x = "#FF00AA"\ny = Pt(12)\nz = Style(font_size=11)\nw = "ok"\n'
    tree = ast.parse(src)
    hits = [
        n
        for n in ast.walk(tree)
        if (isinstance(n, ast.Constant) and isinstance(n.value, str) and HEX.fullmatch(n.value))
        or (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "Pt" and _is_number(n.args[0]))
        or (isinstance(n, ast.Call) and any(k.arg == "font_size" and _is_number(k.value) for k in n.keywords))
    ]
    assert len(hits) == 3


def test_allowlist_entries_are_still_needed():
    """A stale allowlist entry hides a future violation: every entry must match a literal that exists."""
    present: set[tuple[str, str]] = set()
    for path in SCANNED:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and HEX.fullmatch(node.value):
                present.add((_rel(path), node.value.upper()))
    stale = [k for k in ALLOWED_LITERALS if (k[0], k[1].upper()) not in present]
    assert not stale, f"remove stale allowlist entries: {stale}"
