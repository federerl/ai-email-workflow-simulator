import json

import pytest

from ai_email_workflow_simulator import config
from ai_email_workflow_simulator.llm import bedrock_client, prompts
from ai_email_workflow_simulator.pipeline.runner import run_pipeline
from ai_email_workflow_simulator.storage import db


@pytest.fixture(autouse=True)
def mock_llm_enabled(monkeypatch):
    monkeypatch.setattr(config, "MOCK_LLM", True)
    yield


def test_converse_never_touches_boto3_in_mock_mode(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("should not create a real boto3 client in mock mode")

    monkeypatch.setattr(bedrock_client, "get_client", boom)
    result = bedrock_client.converse(
        prompts.CLASSIFY_SYSTEM_PROMPT,
        "Subject: test\nBody: this is an RFP solicitation",
    )
    assert json.loads(result)["category"] == "RFP"


def test_run_pipeline_rfp_email_end_to_end_with_no_aws():
    item_id = run_pipeline("data/samples/sample_rfp_email.eml")
    row = db.get_item(item_id)
    assert row["category"] == "RFP"
    assert row["decision"] == "Pursue"
    assert row["review_status"] == "pending_review"
    assert row["draft_text"] is not None
    assert row["model_id"] == "mock"


def test_run_pipeline_marketing_email_auto_declines_with_no_model_call():
    item_id = run_pipeline("data/samples/sample_marketing_email.eml")
    row = db.get_item(item_id)
    assert row["category"] == "Marketing"
    assert row["decision"] == "Decline"
    assert row["review_status"] == "closed"


def test_run_pipeline_followup_email_needs_human_review():
    item_id = run_pipeline("data/samples/sample_followup_email.eml")
    row = db.get_item(item_id)
    assert row["category"] == "Follow-up"
    assert row["decision"] == "Needs-Human-Review"
    assert row["review_status"] == "needs_review"
