"""Command line: ``slidemark build|check|preview|version``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ir import Deck


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"error: cannot read {path}: {e}", file=sys.stderr)
        return None


def _print_diagnostics(deck: Deck, file=sys.stderr) -> None:
    for d in deck.diagnostics:
        print(str(d), file=file)


def _has_errors(deck: Deck) -> bool:
    return any(d.level == "error" for d in deck.diagnostics)


def cmd_check(args: argparse.Namespace) -> int:
    from .parser import parse

    text = _read(args.input)
    if text is None:
        return 2
    deck = parse(text)
    if args.format == "json":
        print(json.dumps([d.model_dump() for d in deck.diagnostics], ensure_ascii=False))
    elif deck.diagnostics:
        for d in deck.diagnostics:
            print(str(d))
    else:
        print(f"ok: {len(deck.slides)} slides")
    return 1 if _has_errors(deck) else 0


def cmd_build(args: argparse.Namespace) -> int:
    from .build import build

    src = Path(args.input)
    if _read(args.input) is None:
        return 2
    out = Path(args.output) if args.output else src.with_suffix(".pptx")
    try:
        deck = build(src, out)
    except NotImplementedError:
        print("error: layout/render are not available in this build yet", file=sys.stderr)
        return 2
    except Exception as e:  # keep the CLI contract: a message and an exit code, never a traceback
        print(f"error: build failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    _print_diagnostics(deck)
    print(f"wrote {out} ({len(deck.slides)} slides)")
    return 1 if _has_errors(deck) else 0


def cmd_preview(args: argparse.Namespace) -> int:
    try:
        from .preview import pptx_to_pngs
    except ImportError:
        print("error: preview is not available (module slidemark.preview is missing)", file=sys.stderr)
        return 2
    import tempfile

    from .build import build

    src = Path(args.input)
    if _read(args.input) is None:
        return 2
    out_dir = Path(args.output) if args.output else src.with_suffix("").parent / (src.stem + "-preview")
    try:
        with tempfile.TemporaryDirectory(prefix="slidemark-") as tmp:
            pptx = Path(tmp) / (src.stem + ".pptx")
            deck = build(src, pptx)
            _print_diagnostics(deck)
            pngs = pptx_to_pngs(pptx, out_dir)
    except NotImplementedError:
        print("error: layout/render are not available in this build yet", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"error: preview failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    for p in pngs:
        print(p)
    return 1 if _has_errors(deck) else 0


def cmd_version(args: argparse.Namespace) -> int:
    from . import __version__

    print(__version__)
    return 0


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="slidemark", description="Markdown to native, editable .pptx")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="build a .pptx from a Markdown file")
    b.add_argument("input")
    b.add_argument("-o", "--output", help="output .pptx (default: next to the input)")
    b.set_defaults(func=cmd_build)

    c = sub.add_parser("check", help="parse and print diagnostics, one per line")
    c.add_argument("input")
    c.add_argument("--format", choices=["text", "json"], default="text")
    c.set_defaults(func=cmd_check)

    v = sub.add_parser("preview", help="render slides to PNG images (needs LibreOffice)")
    v.add_argument("input")
    v.add_argument("-o", "--output", help="output directory for slide-NN.png")
    v.set_defaults(func=cmd_preview)

    sub.add_parser("version", help="print the version").set_defaults(func=cmd_version)
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = make_parser().parse_args(argv)
    except SystemExit as e:  # argparse exits itself on bad usage / --help
        return int(e.code) if isinstance(e.code, int) else 2
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
