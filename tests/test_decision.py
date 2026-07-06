import json

import pytest

from ai_email_workflow_simulator.ingestion.models import InboundItem
from ai_email_workflow_simulator.llm import bedrock_client
from ai_email_workflow_simulator.pipeline import decision, rubric


def _item():
    return InboundItem(
        source_type="text",
        source_path="x.txt",
        subject="subj",
        sender="a@b.com",
        recipients=[],
        sent_at="2026-01-01",
        body_text="body",
    )


def test_non_rubric_category_short_circuits_without_llm_call(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("should not call the LLM for non-rubric categories")

    monkeypatch.setattr(bedrock_client, "converse", boom)
    r = rubric.load_rubric()
    result = decision.decide(_item(), "Marketing", r)
    assert result.decision == "Decline"
    assert "Marketing" in result.rationale
    assert result.raw_model_output is None


def test_rubric_category_calls_llm_and_parses_decision(monkeypatch):
    monkeypatch.setattr(
        bedrock_client,
        "converse",
        lambda *a, **k: json.dumps({"decision": "Pursue", "rationale": "strong mission fit"}),
    )
    r = rubric.load_rubric()
    result = decision.decide(_item(), "RFP", r)
    assert result.decision == "Pursue"
    assert result.rationale == "strong mission fit"


def test_malformed_decision_falls_back_to_needs_human_review(monkeypatch):
    monkeypatch.setattr(bedrock_client, "converse", lambda *a, **k: "not json")
    r = rubric.load_rubric()
    result = decision.decide(_item(), "RFP", r)
    assert result.decision == "Needs-Human-Review"
