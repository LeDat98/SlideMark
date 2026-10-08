"""Validate the XML parts of a .pptx against the ECMA-376 schemas (PresentationML, DrawingML, charts).

The schemas are not shipped: `fetch_schemas()` downloads them once into a cache directory. Markup
Compatibility (`mc:AlternateContent`, `mc:Ignorable`) is resolved the way an Office 2007 reader would: the
fallback branch is kept and ignorable namespaces are dropped, then the part is validated.

    python -m slidemark.xsd deck.pptx [more.pptx ...]
"""

from __future__ import annotations

import os
import sys
import urllib.request
import zipfile
from pathlib import Path

SCHEMA_URL = "https://raw.githubusercontent.com/python-openxml/python-docx/master/ref/xsd/"
SCHEMA_FILES = (
    "pml.xsd",
    "dml-main.xsd",
    "dml-chart.xsd",
    "dml-chartDrawing.xsd",
    "dml-diagram.xsd",
    "dml-lockedCanvas.xsd",
    "dml-picture.xsd",
    "shared-commonSimpleTypes.xsd",
    "shared-relationshipReference.xsd",
)
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
# root namespace -> validated; parts with other roots (docProps, rels, embeddings) are skipped
ROOT_NS = (
    "http://schemas.openxmlformats.org/presentationml/2006/main",
    "http://schemas.openxmlformats.org/drawingml/2006/main",
    "http://schemas.openxmlformats.org/drawingml/2006/chart",
)

_schema = None


def cache_dir() -> Path:
    base = os.environ.get("SLIDEMARK_XSD_DIR")
    if base:
        return Path(base)
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "slidemark" / "xsd"


def fetch_schemas(directory: Path | None = None) -> Path | None:
    """Download the schemas once. Returns the directory, or None when they cannot be fetched."""
    directory = directory or cache_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for name in SCHEMA_FILES:
            target = directory / name
            if not target.exists():
                with urllib.request.urlopen(SCHEMA_URL + name, timeout=30) as resp:
                    target.write_bytes(resp.read())
    except OSError:
        return None
    return directory


def _load_schema():
    global _schema
    if _schema is None:
        from lxml import etree

        directory = fetch_schemas()
        if directory is None:
            return None
        imports = "".join(
            f'<xs:import namespace="{ns}" schemaLocation="{(directory / f).as_uri()}"/>'
            for ns, f in zip(ROOT_NS, ("pml.xsd", "dml-main.xsd", "dml-chart.xsd"), strict=True)
        )
        wrapper = f'<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">{imports}</xs:schema>'
        _schema = etree.XMLSchema(etree.fromstring(wrapper.encode(), base_url=directory.as_uri() + "/"))
    return _schema


def _resolve_mc(root) -> None:
    """Keep the `mc:Fallback` branch of every AlternateContent and drop ignorable namespaces."""
    for alt in list(root.iter(f"{{{MC}}}AlternateContent")):
        parent = alt.getparent()
        if parent is None:
            continue
        fallback = alt.find(f"{{{MC}}}Fallback")
        index = parent.index(alt)
        for child in list(fallback) if fallback is not None else []:
            parent.insert(index, child)
            index += 1
        parent.remove(alt)
    ignorable: set[str] = set()
    for el in root.iter():
        prefixes = el.get(f"{{{MC}}}Ignorable")
        if prefixes:
            ignorable.update(el.nsmap.get(p) for p in prefixes.split() if el.nsmap.get(p))
            del el.attrib[f"{{{MC}}}Ignorable"]
    if not ignorable:
        return
    for el in list(root.iter()):
        if not isinstance(el.tag, str):
            continue
        if el.tag.startswith("{") and el.tag[1:].split("}")[0] in ignorable and el.getparent() is not None:
            el.getparent().remove(el)
            continue
        for name in list(el.attrib):
            if name.startswith("{") and name[1:].split("}")[0] in ignorable:
                del el.attrib[name]


def validate_pptx(path: str | Path) -> list[str] | None:
    """Return a list of `part:line: message` errors (empty = valid), or None when no schemas are available."""
    from lxml import etree

    schema = _load_schema()
    if schema is None:
        return None
    errors: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for name in sorted(zf.namelist()):
            if not name.endswith(".xml"):
                continue
            root = etree.fromstring(zf.read(name))
            ns = root.tag[1:].split("}")[0] if root.tag.startswith("{") else ""
            if ns not in ROOT_NS:
                continue
            _resolve_mc(root)
            if not schema.validate(etree.ElementTree(root)):
                errors += [f"{name}:{e.line}: {e.message}" for e in schema.error_log]
    return errors


def main(argv: list[str] | None = None) -> int:
    paths = argv if argv is not None else sys.argv[1:]
    bad = 0
    for p in paths:
        errors = validate_pptx(p)
        if errors is None:
            print("schemas unavailable (no network?)", file=sys.stderr)
            return 2
        bad += bool(errors)
        print(f"{p}: {'ok' if not errors else f'{len(errors)} errors'}")
        for e in errors[:20]:
            print("  " + e)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
