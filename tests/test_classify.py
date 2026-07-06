import json

from ai_email_workflow_simulator.ingestion.models import InboundItem
from ai_email_workflow_simulator.llm import bedrock_client
from ai_email_workflow_simulator.pipeline import classify


def _item(body="hello"):
    return InboundItem(
        source_type="text",
        source_path="x.txt",
        subject="subj",
        sender="a@b.com",
        recipients=[],
        sent_at="2026-01-01",
        body_text=body,
    )


def test_classify_valid_json(monkeypatch):
    monkeypatch.setattr(
        bedrock_client,
        "converse",
        lambda *a, **k: json.dumps({"category": "RFP", "notes": "looks like a solicitation"}),
    )
    result = classify.classify(_item())
    assert result.category == "RFP"
    assert result.notes == "looks like a solicitation"


def test_classify_malformed_json_falls_back_to_other(monkeypatch):
    monkeypatch.setattr(bedrock_client, "converse", lambda *a, **k: "not json")
    result = classify.classify(_item())
    assert result.category == "Other"


def test_classify_unknown_category_falls_back_to_other(monkeypatch):
    monkeypatch.setattr(
        bedrock_client, "converse", lambda *a, **k: json.dumps({"category": "Spam"})
    )
    result = classify.classify(_item())
    assert result.category == "Other"
