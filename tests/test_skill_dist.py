"""The distributable skill folder ``skills/slidemark/``: what skill installers copy to an agent.

``npx skills add LeDat98/SlideMark`` and the Claude Code marketplace (``.claude-plugin/marketplace.json``)
copy that folder and nothing else from the repo. It holds one file, so an agent that installs the skill sees
one page (docs/AGENT_COST.md). The CLI ships ``src/slidemark/skill/SKILL.md``; the two must stay equal.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "skills" / "slidemark"
SOURCE = ROOT / "src" / "slidemark" / "skill" / "SKILL.md"


def test_dist_skill_equals_the_packaged_skill():
    # After editing the packaged page: cp src/slidemark/skill/SKILL.md skills/slidemark/SKILL.md
    assert (DIST / "SKILL.md").read_text(encoding="utf-8") == SOURCE.read_text(encoding="utf-8")


def test_dist_skill_folder_holds_only_skill_md():
    assert sorted(p.name for p in DIST.iterdir()) == ["SKILL.md"]


def test_marketplace_entry_points_at_the_dist_skill():
    data = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    entry = next(p for p in data["plugins"] if p["name"] == "slidemark")
    assert entry["source"] == "./skills/slidemark"
    assert (ROOT / entry["source"] / "SKILL.md").is_file()
