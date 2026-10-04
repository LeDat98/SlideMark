from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from slidemark.ir import Deck
from slidemark.parser import parse

CORPUS = [
    p.read_text(encoding="utf-8")
    for p in sorted((Path(__file__).parent.parent / "bench" / "corpus").glob("*/slidemark.md"))
]
SYNTAX = Path(__file__).parent.parent / "docs" / "SYNTAX.md"

FRAGMENTS = [
    "# ",
    "## ",
    "### ",
    "---",
    "@",
    "@aab/aac",
    "@3 flow",
    "{",
    "}",
    "{.a #b c=d}",
    "```",
    "```column",
    "```table",
    "~~~",
    "|",
    "|-|-|",
    "< ",
    "^",
    "==",
    "[",
    "](",
    "![",
    ">",
    "※",
    "???",
    "\n",
    "\n\n",
    "  ",
    "\t",
    "**",
    "~",
    "*",
    "日本語",
    "\x00",
    " ",
    "1.",
    "- ",
    "http://x",
    "#5",
    "$$",
]


def check(text: str) -> None:
    deck = parse(text)
    assert isinstance(deck, Deck)
    # the IR must survive a JSON round trip (valid pydantic model, no stray objects)
    Deck.model_validate_json(deck.model_dump_json())
    assert not [d for d in deck.diagnostics if d.rule == "internal"], deck.diagnostics


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.text())
def test_random_text_never_crashes(text):
    check(text)


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(st.sampled_from(FRAGMENTS), max_size=40).map("".join))
def test_random_syntax_soup_never_crashes(text):
    check(text)


@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.integers(0, len(CORPUS) - 1),
    st.lists(
        st.tuples(st.integers(0, 10_000), st.integers(0, 40), st.sampled_from(FRAGMENTS + [""])),
        min_size=1,
        max_size=8,
    ),
)
def test_mutated_corpus_never_crashes(which, mutations):
    text = CORPUS[which]
    for pos, cut, ins in mutations:
        pos %= len(text) + 1
        text = text[:pos] + ins + text[pos + cut :]
    check(text)


def test_syntax_doc_never_crashes():
    if SYNTAX.exists():
        check(SYNTAX.read_text(encoding="utf-8"))
