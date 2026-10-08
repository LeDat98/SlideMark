"""JSON Deck input: load a Deck from JSON text or a file, and build it without the Markdown parser."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from .ir import Deck, Diagnostic


def _bad(message: str, hint: str) -> Deck:
    deck = Deck()
    deck.diagnostics.append(Diagnostic(level="error", message=message, rule="bad-json", hint=hint))
    return deck


def _from_validation_error(e: ValidationError) -> Deck:
    deck = Deck()
    for err in e.errors()[:20]:
        loc = ".".join(str(x) for x in err.get("loc", ())) or "<root>"
        deck.diagnostics.append(
            Diagnostic(
                level="error",
                message=f"{loc}: {err.get('msg', 'invalid value')}",
                rule="bad-json",
                hint="fix this field; run `slidemark schema` for the expected shape",
            )
        )
    return deck


def load_deck(path_or_text: str | Path) -> Deck:
    """Load a Deck from a JSON file path or JSON text. Never raises: errors become `bad-json` diagnostics."""
    text = path_or_text
    if isinstance(path_or_text, Path) or not str(path_or_text).lstrip().startswith(("{", "[")):
        try:
            text = Path(path_or_text).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, ValueError) as e:
            return _bad(f"cannot read JSON: {e}", "pass a JSON object or the path of a UTF-8 .json file")
    try:
        return Deck.model_validate_json(str(text))
    except ValidationError as e:
        return _from_validation_error(e)
    except Exception as e:  # defensive: never traceback on user input
        return _bad(f"{type(e).__name__}: {e}", "input must be a JSON object produced by `slidemark schema`")


def build_deck(deck: Deck, out: str | Path, base_dir: str | Path | None = None) -> Deck:
    """Layout + lint + render an existing Deck (see ``slidemark.build.build_deck``)."""
    from .build import build_deck as _build_deck

    return _build_deck(deck, out, base_dir)
