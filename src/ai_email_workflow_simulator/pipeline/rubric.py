"""Load and apply the configurable qualification rubric."""

from functools import lru_cache

import yaml

from .. import config


@lru_cache(maxsize=1)
def load_rubric() -> dict:
    with open(config.RUBRIC_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_boilerplate() -> str:
    return config.BOILERPLATE_PATH.read_text(encoding="utf-8")


def category_applies_rubric(rubric: dict, category: str) -> bool:
    entry = rubric["categories"].get(category, {"applies_rubric": True})
    return entry.get("applies_rubric", True)


def category_auto_decision(rubric: dict, category: str) -> str:
    entry = rubric["categories"][category]
    return entry["auto_decision"]


def build_rubric_block(rubric: dict) -> str:
    lines = ["Qualification rubric:"]
    for criterion in rubric["criteria"]:
        lines.append(
            f"- {criterion['label']} (weight {criterion['weight']}): {criterion['description']}"
        )
    return "\n".join(lines)
