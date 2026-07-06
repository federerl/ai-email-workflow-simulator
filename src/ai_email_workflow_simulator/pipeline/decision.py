"""Stage 2: decide Pursue / Decline / Needs-Human-Review against the rubric."""

import json
from dataclasses import dataclass

from ..ingestion.models import InboundItem
from ..llm import bedrock_client, prompts
from . import rubric as rubric_module

VALID_DECISIONS = {"Pursue", "Decline", "Needs-Human-Review"}


@dataclass
class DecisionResult:
    decision: str
    rationale: str
    raw_model_output: str | None


def decide(item: InboundItem, category: str, rubric: dict) -> DecisionResult:
    if not rubric_module.category_applies_rubric(rubric, category):
        auto_decision = rubric_module.category_auto_decision(rubric, category)
        return DecisionResult(
            decision=auto_decision,
            rationale=(
                f"Auto-{auto_decision.lower()}: category '{category}' is excluded "
                "from rubric evaluation per config/rubric.yaml."
            ),
            raw_model_output=None,
        )

    rubric_block = rubric_module.build_rubric_block(rubric)
    raw = bedrock_client.converse(
        prompts.build_decision_system_prompt(rubric_block),
        prompts.build_decision_prompt(item, category),
    )
    try:
        parsed = json.loads(raw)
        decision = parsed["decision"]
        if decision not in VALID_DECISIONS:
            raise ValueError(f"unknown decision '{decision}'")
        rationale = parsed.get("rationale", "")
    except (json.JSONDecodeError, KeyError, ValueError):
        decision = "Needs-Human-Review"
        rationale = "Model output could not be parsed; routed to human review."

    return DecisionResult(decision=decision, rationale=rationale, raw_model_output=raw)
