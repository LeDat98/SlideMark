"""Long fuzz run for the L4 gate "0 crashes in 100k inputs": parse + layout + lint on random fragment mixes.

Usage: python bench/fuzz_long.py [N] [--seed S] [--render-every K]
Every K-th input is also rendered to .pptx (slow). Prints crashes with the input that caused them.
"""

from __future__ import annotations

import random
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from slidemark.build import build_deck  # noqa: E402
from slidemark.layout import layout_slide  # noqa: E402
from slidemark.lint import lint  # noqa: E402
from slidemark.parser import parse  # noqa: E402
from slidemark.theme import get_theme  # noqa: E402
from tests.test_parser_fuzz import FRAGMENTS, HTML, LENIENT, MERMAID  # noqa: E402

POOL = FRAGMENTS + LENIENT + MERMAID + HTML
NOISE = "#@>|-*`{}[]()<>^~=!?※:/\\\n 　、。全角ABC123%,\"'"


def sample(rng: random.Random) -> str:
    parts = [rng.choice(POOL) for _ in range(rng.randint(0, 30))]
    if rng.random() < 0.3:  # corrupt a few characters
        text = "\n".join(parts)
        chars = list(text)
        for _ in range(rng.randint(1, 8)):
            if chars:
                chars[rng.randrange(len(chars))] = rng.choice(NOISE)
        return "".join(chars)
    return rng.choice(["\n", "", " "]).join(parts)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(args[0]) if args else 100_000
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    every = int(sys.argv[sys.argv.index("--render-every") + 1]) if "--render-every" in sys.argv else 500
    rng = random.Random(seed)
    crashes = 0
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(n):
            text = sample(rng)
            try:
                if i % every == 0:
                    build_deck(parse(text), Path(tmp) / "f.pptx")
                else:
                    deck = parse(text)
                    theme = get_theme("default")
                    placed = [layout_slide(s, deck, theme, k) for k, s in enumerate(deck.slides)]
                    lint(deck, placed, theme)
                    if any(d.rule in ("layout-error", "lint-error") for d in deck.diagnostics):
                        raise RuntimeError(str([d for d in deck.diagnostics if d.rule == "layout-error"][0]))
            except Exception:
                crashes += 1
                if crashes <= 5:
                    print(f"CRASH #{crashes} at input {i}:\n{text!r}\n{traceback.format_exc()}")
            if i and i % 10_000 == 0:
                print(f"{i} inputs, {crashes} crashes, {time.time() - t0:.0f}s", flush=True)
    print(f"done: {n} inputs, {crashes} crashes, {time.time() - t0:.0f}s")
    return 1 if crashes else 0


if __name__ == "__main__":
    raise SystemExit(main())
