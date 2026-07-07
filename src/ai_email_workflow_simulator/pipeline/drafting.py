"""Stage 3: draft a tailored response for "Pursue" items (no RAG -- static boilerplate)."""

from dataclasses import dataclass

from ..ingestion.models import InboundItem
from ..llm import bedrock_client, prompts


@dataclass
class DraftResult:
    draft_text: str


def draft_response(item: InboundItem, category: str, rationale: str, boilerplate: str) -> DraftResult:
    draft_text = bedrock_client.converse(
        prompts.build_drafting_system_prompt(boilerplate),
        prompts.build_drafting_prompt(item, category, rationale),
        max_tokens=1500,
    )
    return DraftResult(draft_text=draft_text.strip())
