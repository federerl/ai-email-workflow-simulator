"""Append-only JSONL audit trail of every pipeline decision and human review action."""

import json
from datetime import datetime, timezone

from .. import config


def _append(record: dict) -> None:
    config.ensure_dirs()
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **record}
    with open(config.AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def log_pipeline_decision(
    *,
    item_id: int,
    source_path: str,
    category: str,
    decision: str,
    rationale: str,
    model_id: str | None,
    prompt_version: str | None,
    draft_text: str | None,
) -> None:
    _append(
        {
            "event_type": "pipeline_decision",
            "item_id": item_id,
            "source_path": source_path,
            "category": category,
            "decision": decision,
            "rationale": rationale,
            "model_id": model_id,
            "prompt_version": prompt_version,
            "draft_text": draft_text,
        }
    )


def log_human_review(*, item_id: int, action: str, final_draft_text: str | None = None) -> None:
    _append(
        {
            "event_type": "human_review",
            "item_id": item_id,
            "action": action,
            "final_draft_text": final_draft_text,
        }
    )
