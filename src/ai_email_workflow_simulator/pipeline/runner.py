"""Orchestrates the full pipeline: ingest -> classify -> decide -> draft -> persist."""

from pathlib import Path

from ..ingestion import load_inbound_item
from ..ingestion.models import InboundItem
from ..llm import prompts
from ..storage import audit_log, db
from . import classify as classify_module
from . import decision as decision_module
from . import drafting as drafting_module
from . import rubric as rubric_module


def run_pipeline(path: str | Path) -> int:
    item = load_inbound_item(path)
    rubric = rubric_module.load_rubric()

    classification = classify_module.classify(item)
    decision = decision_module.decide(item, classification.category, rubric)

    draft_text = None
    if decision.decision == "Pursue":
        draft = drafting_module.draft_response(
            item, classification.category, decision.rationale, rubric_module.load_boilerplate()
        )
        draft_text = draft.draft_text

    item_id = db.insert_item(
        source_path=item.source_path,
        subject=item.subject,
        sender=item.sender,
        sent_at=item.sent_at,
        body_text=item.body_text,
        category=classification.category,
        decision=decision.decision,
        rationale=decision.rationale,
        draft_text=draft_text,
        model_id=_model_id(),
        prompt_version=prompts.PROMPT_VERSION,
    )
    audit_log.log_pipeline_decision(
        item_id=item_id,
        source_path=item.source_path,
        category=classification.category,
        decision=decision.decision,
        rationale=decision.rationale,
        model_id=_model_id(),
        prompt_version=prompts.PROMPT_VERSION,
        draft_text=draft_text,
    )
    return item_id


def resolve_needs_review(item_id: int, resolution: str) -> None:
    """Resolve a Needs-Human-Review item: 'pursue' (drafts a response) or 'decline'."""
    if resolution not in ("pursue", "decline"):
        raise ValueError(f"invalid resolution '{resolution}'")

    row = db.get_item(item_id)
    if row is None:
        raise ValueError(f"item {item_id} not found")

    item = InboundItem(
        source_type="unknown",
        source_path=row["source_path"],
        subject=row["subject"],
        sender=row["sender"],
        recipients=[],
        sent_at=row["sent_at"],
        body_text=row["body_text"],
    )

    if resolution == "decline":
        rationale = "Manually declined by reviewer during Needs-Human-Review resolution."
        db.update_item(item_id, decision="Decline", rationale=rationale, review_status="closed")
        audit_log.log_human_review(item_id=item_id, action="resolve_decline")
        return

    rationale = "Manually marked Pursue by reviewer during Needs-Human-Review resolution."
    draft = drafting_module.draft_response(
        item, row["category"], rationale, rubric_module.load_boilerplate()
    )
    db.update_item(
        item_id,
        decision="Pursue",
        rationale=rationale,
        draft_text=draft.draft_text,
        final_draft_text=draft.draft_text,
        review_status="pending_review",
    )
    audit_log.log_human_review(item_id=item_id, action="resolve_pursue", final_draft_text=draft.draft_text)


def _model_id() -> str | None:
    from .. import config

    if config.MOCK_LLM:
        return "mock"
    return config.BEDROCK_MODEL_ID
