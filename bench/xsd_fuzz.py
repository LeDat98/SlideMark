"""L6 gate "XSD-valid on 10k fuzzed decks": build random decks and validate every XML part against ECMA-376.

Usage: python bench/xsd_fuzz.py [N] [--seed S]
Prints a summary of distinct schema errors (message with numbers stripped) and one input per error kind.
"""

from __future__ import annotations

import random
import re
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench"))

from fuzz_long import sample  # noqa: E402

from slidemark.build import build_deck  # noqa: E402
from slidemark.parser import parse  # noqa: E402
from slidemark.xsd import validate_pptx  # noqa: E402


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(args[0]) if args else 10_000
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    rng = random.Random(seed)
    kinds: Counter[str] = Counter()
    example: dict[str, str] = {}
    invalid = 0
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "f.pptx"
        for _ in range(n):
            text = sample(rng)
            build_deck(parse(text), out)
            errors = validate_pptx(out)
            if errors is None:
                print("schemas unavailable", file=sys.stderr)
                return 2
            invalid += bool(errors)
            for e in errors:
                key = re.sub(r"\d+", "N", e.split(": ", 1)[1])[:160]
                kinds[key] += 1
                example.setdefault(key, text)
    print(f"{n} decks, {invalid} invalid, {len(kinds)} error kinds, {time.time() - t0:.0f} s")
    for key, count in kinds.most_common():
        print(f"{count:6d}  {key}")
        print("        input: " + example[key][:300].replace("\n", "\\n"))
    return 1 if invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
