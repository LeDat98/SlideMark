import contextlib
import io
import tempfile
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from slidemark.cli import main
from slidemark.ir import Deck
from slidemark.parser import parse

CORPUS = [
    p.read_text(encoding="utf-8")
    for p in sorted((Path(__file__).parent.parent / "bench" / "corpus").glob("*/slidemark.md"))
]
SYNTAX = Path(__file__).parent.parent / "docs" / "SYNTAX.md"

FRAGMENTS = [
    "```column {legend=sideways labels=maybe fmt= min=x max=1e999 colors=red,#zz axis=2 titel=x}",
    "```pie {colors=primary,#abc,#12345G legend=none labels=percent}",
    "```table {widths=3:x:-1 align=lxr header=-2 hcol=99}",
    "{widths=1:1 align=lcrrr header=0 hcol=1}",
    '"1,240","１２．５",▲3,－3,12%,(4),\ufeff',
    ",Q1,Q2\ns;1;2\nt\t3\t4\n\n\n",
    '"unclosed,1,2',
    "a,b\n1\n1,2,3,4",
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
    "@end",
    "\n@end\n",
    "@chevorn",
    "@bgg=1",
    "@2X2",
    "{colour=red .dnager}",
    "marp: true",
    "paginate: true",
    "<!--",
    "-->",
    "<!-- _class: lead -->",
    "<!-- paginate: true -->",
    "<!-- note -->",
    "Note: ",
    "::right::",
    "layout: cover",
    "class: x",
    "* ",
    "<br>",
    "![w:200](a.png)",
    "![w:1 h:2 bg](a.png){w=3}",
    "\n---\nlayout: cover\n---\n",
    "\n###",
    "@a>b",
    "@1>9",
    "@2 a-b a>b",
    "@aab/aac a>c",
    "> [!warn] x",
    "> [!",
    "> [!xyz]",
    "[x]{.badge}",
    "[x]{.badge .danger}",
    "## K {.kpi}",
]


LENIENT = [
    "---",
    "# T",
    "## B",
    "### H",
    "@end",
    "@3 flow",
    "@bgg=#fff",
    "marp: true",
    "paginate: true",
    "layout: cover",
    "class: lead x",
    "<!-- _class: lead -->",
    "<!-- paginate: true -->",
    "<!-- a note",
    "-->",
    "<!--",
    "Note: say hi",
    "::right::",
    "* item",
    "- item",
    "text<br>more<br/>",
    "![w:200 h:10%](a.png)",
    "![bg](a.png){w=1}",
    "| a | b |",
    "|-|-|",
    "```",
    "```column",
    "???",
    "> q",
    "※ n",
    "@2 a>b",
    "@1>9",
    "> [!warn] x",
    "[x]{.badge}",
    "## K {.kpi}",
    "日本語<br>テキスト",
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


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(st.sampled_from(LENIENT), max_size=40).map("\n".join))
def test_lenient_line_mixes_never_crash(text):
    check(text)


_TMP = Path(tempfile.mkdtemp(prefix="slidemark-fuzz-"))


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.one_of(st.text(), st.lists(st.sampled_from(LENIENT + FRAGMENTS), max_size=40).map("\n".join)))
def test_cli_check_never_tracebacks(text):
    f = _TMP / "fuzz.md"
    f.write_text(text, encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(["check", str(f)])
        code_json = main(["check", str(f), "--format", "json"])
    assert code in (0, 1) and code_json in (0, 1)
    assert "Traceback" not in out.getvalue() + err.getvalue()


MERMAID = [
    "graph TD",
    "flowchart LR",
    "graph BT;",
    "graph RL",
    "A",
    "B[text]",
    "C(round)",
    "D{why}",
    "E((dot))",
    'F["q a"]',
    "G([s])",
    "-->",
    "---",
    "-.->",
    "==>",
    "-->|yes|",
    "-- no -->",
    "--",
    "&",
    ";",
    "\n",
    " ",
    "%% c",
    "subgraph S",
    "end",
    "classDef x fill:#f00",
    "style A fill:#fff",
    "click A cb",
    "A-->B-->C",
    "A-->A",
    "B-->A",
    "[",
    "]",
    "(",
    '"',
    "|",
    ":::c",
    "<br/>",
    "日本語",
    "sequenceDiagram",
    "N1-->N2\n",
]

HTML = [
    '<section class="slide">',
    "</section>",
    "<h1>T</h1>",
    "<h2>B</h2>",
    '<p class="lead">l</p>',
    '<p class="note">※ n</p>',
    '<div class="card">',
    '<div class="kpi">',
    '<div class="chevron">',
    '<div class="callout warn">',
    '<div class="chart" data-type="pie" data-categories="a,b" data-series=\'[{"name":"s","data":[1,null]}]\'>',  # noqa: E501
    '<div class="chart" data-series="{">',
    '<div class="arrow" data-from="a" data-to="b">',
    '<div id="a" style="display:grid;grid-template-columns:2fr 1fr;grid-template-rows:1fr 1fr">',
    '<div style="display:grid;grid-template-columns:repeat(4,1fr)">',
    '<div style="grid-row:span 2;grid-column:1 / 3">',
    '<div style="display:grid;grid-template-columns:repeat(99,1fr)">',
    "</div>",
    "<ul>",
    "<ol>",
    "<li>",
    "</li>",
    "</ul>",
    "<table>",
    "<tr>",
    "<th>",
    "<td colspan=2>",
    "<td rowspan=0>",
    "<td colspan=abc rowspan=-3>",
    "</table>",
    "<mark>m</mark>",
    "<b>",
    "</i>",
    '<span class="badge danger">x</span>',
    "<svg><path/></svg>",
    "<pre class=mermaid>graph TD\nA-->B</pre>",
    "<br>",
    "<",
    ">",
    "&amp;",
    "&#xZZ;",
    "<!--",
    "-->",
    "<script>",
    "</script>",
    "<style>x{}",
    "text",
    "日本語",
    "\n",
]


def check_html(text: str) -> None:
    from slidemark.parser import parse_html

    deck = parse_html(text)
    assert isinstance(deck, Deck)
    Deck.model_validate_json(deck.model_dump_json())
    assert not [d for d in deck.diagnostics if d.rule == "internal"], deck.diagnostics


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(st.sampled_from(MERMAID), max_size=40).map(" ".join))
def test_mermaid_soup_never_crashes(body):
    check("# T\n```mermaid\n" + body + "\n```\n")


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.text())
def test_mermaid_random_text_never_crashes(body):
    check("# T\n```mermaid\ngraph TD\n" + body.replace("```", "") + "\n```\n")


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(st.sampled_from(HTML), max_size=40).map("".join))
def test_html_soup_never_crashes(body):
    check_html(body)
    check("# T\n```html\n" + body.replace("```", "") + "\n```\n")


@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.text())
def test_html_random_text_never_crashes(text):
    check_html(text)
    check("<section class=slide>" + text)


def test_html_corpus_never_crashes():
    for p in sorted((Path(__file__).parent.parent / "bench" / "corpus").glob("*/html.html")):
        check_html(p.read_text(encoding="utf-8"))
