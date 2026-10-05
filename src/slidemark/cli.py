"""Command line: ``slidemark build|check|review|import|preview|docs|schema|skill|version``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ir import Deck, Diagnostic


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"error: cannot read {path}: {e}", file=sys.stderr)
        return None


def _say(text: str, file=None) -> None:
    """print() that cannot raise on text the terminal encoding cannot show."""
    try:
        print(text, file=file or sys.stdout)
    except UnicodeEncodeError:
        print(text.encode("ascii", "backslashreplace").decode("ascii"), file=file or sys.stdout)


def _print_diagnostics(deck: Deck, file=None) -> None:
    for d in deck.diagnostics:
        _say(str(d), file or sys.stderr)


def _has_errors(deck: Deck) -> bool:
    return any(d.level == "error" for d in deck.diagnostics)


def _is_json(path: str) -> bool:
    return Path(path).suffix.lower() == ".json"


def _add_layout_diagnostics(deck: Deck, input_path: str) -> None:
    """Run layout + lint like build() does and append their diagnostics (deduped by rule and slide)."""
    try:
        from .layout import layout_slide
        from .lint import lint
        from .template import deck_theme, template_size

        deck.attrs.setdefault("base_dir", str(Path(input_path).resolve().parent))
        theme, diags = deck_theme(deck, deck.attrs["base_dir"])
        deck.diagnostics.extend(diags)
        if size := template_size(theme):
            deck.size = size
        placed = [layout_slide(slide, deck, theme, i) for i, slide in enumerate(deck.slides)]
        seen = {(d.rule, d.slide) for d in deck.diagnostics}
        deck.diagnostics.extend(d for d in lint(deck, placed, theme) if (d.rule, d.slide) not in seen)
    except NotImplementedError:
        pass  # layout/lint not available in this build: parser diagnostics only
    except Exception as e:  # check must not traceback on a layout bug
        deck.diagnostics.append(
            Diagnostic(
                level="warning",
                message=f"layout check failed: {type(e).__name__}: {e}",
                rule="check-layout",
                hint="report this deck as a bug; parser diagnostics above are still valid",
            )
        )


def cmd_check(args: argparse.Namespace) -> int:
    from .parser import parse

    text = _read(args.input)
    if text is None:
        return 2
    fixed: list = []
    if args.output and not args.fix:
        print("error: -o needs --fix", file=sys.stderr)
        return 2
    if args.fix and not _is_json(args.input):
        from .fix import fix_text

        new_text, fixed = fix_text(text, lambda t: parse(t).diagnostics)
        dest = Path(args.output) if args.output else Path(args.input)
        if fixed or args.output:
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(new_text, encoding="utf-8", newline="")
            except OSError as e:
                print(f"error: cannot write {dest}: {e}", file=sys.stderr)
                return 2
        text = new_text
    elif args.fix:
        print("note: --fix applies to Markdown decks only", file=sys.stderr)
    if _is_json(args.input):
        from .jsonio import load_deck

        deck = load_deck(text)
        if not _has_errors(deck):
            _add_layout_diagnostics(deck, args.input)
    else:
        deck = parse(text)
        _add_layout_diagnostics(deck, args.input)
    if args.fix and args.format == "json":
        payload = {
            "fixed": [f.model_dump() for f in fixed],
            "diagnostics": [d.model_dump() for d in deck.diagnostics],
        }
        _say(json.dumps(payload, ensure_ascii=False))
    elif args.format == "json":
        _say(json.dumps([d.model_dump() for d in deck.diagnostics], ensure_ascii=False))
    else:
        for f in fixed:
            _say(str(f))
        for d in deck.diagnostics:
            _say(str(d))
        if not deck.diagnostics:
            print(f"ok: {len(deck.slides)} slides")
    return 1 if _has_errors(deck) else 0


def cmd_review(args: argparse.Namespace) -> int:
    """Parse, lay out, lint and critique a deck; print diagnostics and a score. Never fails a build."""
    from .parser import parse

    text = _read(args.input)
    if text is None:
        return 2
    if _is_json(args.input):
        from .jsonio import load_deck

        deck = load_deck(text)
    else:
        deck = parse(text)
    diags = list(deck.diagnostics)
    if not _has_errors(deck):
        try:
            from .critique import critique
            from .layout import layout_slide
            from .lint import lint
            from .template import deck_theme, template_size

            deck.attrs.setdefault("base_dir", str(Path(args.input).resolve().parent))
            theme, tdiags = deck_theme(deck, deck.attrs["base_dir"])
            diags.extend(tdiags)
            if size := template_size(theme):
                deck.size = size
            placed = [layout_slide(s, deck, theme, i) for i, s in enumerate(deck.slides)]
            seen = {(d.rule, d.slide) for d in diags}
            diags.extend(d for d in lint(deck, placed, theme) if (d.rule, d.slide) not in seen)
            diags.extend(critique(deck, placed, theme))
        except NotImplementedError:
            pass
        except Exception as e:
            diags.append(
                Diagnostic(
                    level="warning",
                    message=f"review failed: {type(e).__name__}: {e}",
                    rule="check-layout",
                    hint="report this deck as a bug; the diagnostics above are still valid",
                )
            )
    from .critique import review_score

    score = review_score(diags, len(deck.slides))
    if args.format == "json":
        _say(json.dumps({"score": score, "diagnostics": [d.model_dump() for d in diags]}, ensure_ascii=False))
    else:
        for d in diags:
            _say(str(d))
        print(f"score: {score}/100")
    if args.png and not _has_errors(deck):
        _review_png(args)
    return 0


def _review_png(args: argparse.Namespace) -> None:
    try:
        import tempfile

        from .build import build
        from .preview import have_soffice, pptx_to_pngs

        if not have_soffice():
            print("note: --png skipped: LibreOffice (soffice) not found", file=sys.stderr)
            return
        src = Path(args.input)
        with tempfile.TemporaryDirectory(prefix="slidemark-") as tmp:
            pptx = Path(tmp) / (src.stem + ".pptx")
            if _is_json(args.input):
                from .jsonio import build_deck, load_deck

                build_deck(load_deck(src), pptx, src.resolve().parent)
            else:
                build(src, pptx)
            for p in pptx_to_pngs(pptx, Path(args.png)):
                print(p, file=sys.stderr)
    except Exception as e:
        print(f"note: --png failed: {type(e).__name__}: {e}", file=sys.stderr)


def cmd_build(args: argparse.Namespace) -> int:
    from .build import build

    src = Path(args.input)
    if _read(args.input) is None:
        return 2
    out = Path(args.output) if args.output else src.with_suffix(".pptx")
    try:
        if _is_json(args.input):
            from .jsonio import build_deck, load_deck

            deck = load_deck(src)
            if _has_errors(deck):
                _print_diagnostics(deck)
                return 1
            deck = build_deck(deck, out, src.resolve().parent)
        else:
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


def cmd_import(args: argparse.Namespace) -> int:
    from .importer import import_pptx

    src = Path(args.input)
    if not src.is_file():
        print(f"error: cannot read {args.input}: no such file", file=sys.stderr)
        return 2
    out = Path(args.output) if args.output else None
    text, diags = import_pptx(src, out.parent if out else None)
    for d in diags:
        _say(str(d), sys.stderr)
    if any(d.rule == "import-unreadable" for d in diags):
        return 2
    if out is None:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
    else:
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
        except OSError as e:
            print(f"error: cannot write {out}: {e}", file=sys.stderr)
            return 2
        print(f"wrote {out}")
    return 1 if any(d.level == "error" for d in diags) else 0


def cmd_preview(args: argparse.Namespace) -> int:
    try:
        from .preview import pptx_to_pngs
    except ImportError:
        print("error: preview is not available (module slidemark.preview is missing)", file=sys.stderr)
        return 2
    import tempfile

    from .build import build

    src = Path(args.input)
    is_pptx = src.suffix.lower() == ".pptx"
    if is_pptx and not src.is_file():
        print(f"error: cannot read {args.input}: no such file", file=sys.stderr)
        return 2
    if not is_pptx and _read(args.input) is None:
        return 2
    out_dir = Path(args.output) if args.output else src.with_suffix("").parent / (src.stem + "-preview")
    deck = Deck()
    try:
        if is_pptx:  # already a deck: render it as it is
            pngs = pptx_to_pngs(src, out_dir)
        else:
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


def _skill_files() -> list[tuple[str, str]]:
    """(relative path, text) of SKILL.md and reference/*.md, read from package data."""
    from importlib.resources import files

    root = files("slidemark").joinpath("skill")
    out = [("SKILL.md", root.joinpath("SKILL.md").read_text(encoding="utf-8"))]
    for f in sorted(root.joinpath("reference").iterdir(), key=lambda x: x.name):
        if f.name.endswith(".md"):
            out.append((f"reference/{f.name}", f.read_text(encoding="utf-8")))
    return out


def cmd_docs(args: argparse.Namespace) -> int:
    docs = dict(_skill_files())
    if not args.topic:
        _say(docs["SKILL.md"].rstrip("\n"))
        return 0
    topics = sorted(k[len("reference/") : -3] for k in docs if k.startswith("reference/"))
    key = f"reference/{args.topic}.md"
    if key not in docs:
        import difflib

        near = difflib.get_close_matches(args.topic, topics, n=1)
        dym = f" (did you mean '{near[0]}'?)" if near else ""
        print(f"error: unknown topic '{args.topic}'; topics: {', '.join(topics)}{dym}", file=sys.stderr)
        return 2
    _say(docs[key].rstrip("\n"))
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    seps = (",", ":") if args.indent is None else None
    _say(json.dumps(Deck.model_json_schema(), ensure_ascii=False, indent=args.indent, separators=seps))
    return 0


def cmd_skill_install(args: argparse.Namespace) -> int:
    dest = Path(args.dir).expanduser() if args.dir else Path.home() / ".claude" / "skills" / "slidemark"
    for rel, text in _skill_files():
        target = dest / rel
        if args.print:
            _say(str(target))
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        except OSError as e:
            print(f"error: cannot write {target}: {e}", file=sys.stderr)
            return 2
    if not args.print:
        _say(str(dest))
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    from . import __version__

    print(__version__)
    return 0


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="slidemark", description="Markdown to native, editable .pptx")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="build a .pptx from a Markdown or JSON deck file")
    b.add_argument("input")
    b.add_argument("-o", "--output", help="output .pptx (default: next to the input)")
    b.set_defaults(func=cmd_build)

    c = sub.add_parser("check", help="print diagnostics for a .md or .json deck, one per line")
    c.add_argument("input")
    c.add_argument("--format", choices=["text", "json"], default="text")
    c.add_argument(
        "--fix", action="store_true", help="rewrite the source for mechanical fixes, then re-check"
    )
    c.add_argument("-o", "--output", help="with --fix: write the fixed deck here, leave the input alone")
    c.set_defaults(func=cmd_check)

    r = sub.add_parser("review", help="design critique: check + layout/design rules + score (never fails)")
    r.add_argument("input")
    r.add_argument("--format", choices=["text", "json"], default="text")
    r.add_argument("--png", metavar="DIR", help="also write slide-NN.png previews here (needs LibreOffice)")
    r.set_defaults(func=cmd_review)

    im = sub.add_parser("import", help="convert a .pptx to SlideMark text (stdout, or -o file + images/)")
    im.add_argument("input")
    im.add_argument("-o", "--output", help="output .md (pictures go to images/ next to it)")
    im.set_defaults(func=cmd_import)

    v = sub.add_parser("preview", help="render slides to PNG images (needs LibreOffice)")
    v.add_argument("input", help=".md, .json, .html or .pptx")
    v.add_argument("-o", "--output", help="output directory for slide-NN.png")
    v.set_defaults(func=cmd_preview)

    d = sub.add_parser("docs", help="print the agent guide (SKILL.md) or a reference topic")
    d.add_argument("topic", nargs="?", help="reference topic, e.g. syntax")
    d.set_defaults(func=cmd_docs)

    sc = sub.add_parser("schema", help="print the JSON schema of a Deck")
    sc.add_argument("--indent", type=int, help="pretty-print with this indent (default: compact)")
    sc.set_defaults(func=cmd_schema)

    sk = sub.add_parser("skill", help="manage the Claude skill files")
    sksub = sk.add_subparsers(dest="skill_command", required=True)
    si = sksub.add_parser("install", help="copy SKILL.md and reference/ to ~/.claude/skills/slidemark")
    si.add_argument("--dir", help="target directory (default: ~/.claude/skills/slidemark)")
    si.add_argument("--print", action="store_true", help="list the files it would write, write nothing")
    si.set_defaults(func=cmd_skill_install)

    sub.add_parser("version", help="print the version").set_defaults(func=cmd_version)
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = make_parser().parse_args(argv)
    except SystemExit as e:  # argparse exits itself on bad usage / --help
        return int(e.code) if isinstance(e.code, int) else 2
    try:
        return int(args.func(args))
    except Exception as e:  # the CLI contract: a message and an exit code, never a traceback
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
