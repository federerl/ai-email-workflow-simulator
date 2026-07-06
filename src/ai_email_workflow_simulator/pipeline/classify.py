"""Stage 1: classify the inbound item's message type."""

import json
from dataclasses import dataclass

from ..ingestion.models import InboundItem
from ..llm import bedrock_client, prompts


@dataclass
class ClassificationResult:
    category: str
    notes: str
    raw_model_output: str


def classify(item: InboundItem) -> ClassificationResult:
    raw = bedrock_client.converse(
        prompts.CLASSIFY_SYSTEM_PROMPT,
        prompts.build_classify_prompt(item),
    )
    try:
        parsed = json.loads(raw)
        category = parsed["category"]
        if category not in prompts.CATEGORIES:
            raise ValueError(f"unknown category '{category}'")
        notes = parsed.get("notes", "")
    except (json.JSONDecodeError, KeyError, ValueError):
        category = "Other"
        notes = "Model output could not be parsed; defaulted to Other for human review."

    return ClassificationResult(category=category, notes=notes, raw_model_output=raw)
