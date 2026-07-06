from ai_email_workflow_simulator.ingestion.models import InboundItem
from ai_email_workflow_simulator.llm import bedrock_client
from ai_email_workflow_simulator.pipeline import drafting


def test_draft_response_strips_whitespace(monkeypatch):
    monkeypatch.setattr(bedrock_client, "converse", lambda *a, **k: "  Dear Maria, ...  \n")
    item = InboundItem(
        source_type="eml",
        source_path="x.eml",
        subject="RFP",
        sender="a@b.com",
        recipients=[],
        sent_at="2026-01-01",
        body_text="body",
    )
    result = drafting.draft_response(item, "RFP", "strong fit", "Company boilerplate.")
    assert result.draft_text == "Dear Maria, ..."
