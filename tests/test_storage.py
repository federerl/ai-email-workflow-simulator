import json

from ai_email_workflow_simulator import config
from ai_email_workflow_simulator.storage import audit_log, db


def _insert(**overrides):
    fields = dict(
        source_path="x.eml",
        subject="subj",
        sender="a@b.com",
        sent_at="2026-01-01",
        body_text="body",
        category="RFP",
        decision="Pursue",
        rationale="good fit",
        draft_text="draft",
        model_id="anthropic.claude-3-5-sonnet",
        prompt_version="v1",
    )
    fields.update(overrides)
    return db.insert_item(**fields)


def test_insert_and_get_item_sets_initial_review_status():
    item_id = _insert()
    row = db.get_item(item_id)
    assert row["review_status"] == "pending_review"
    assert row["decision"] == "Pursue"


def test_decline_gets_closed_status():
    item_id = _insert(decision="Decline", draft_text=None)
    row = db.get_item(item_id)
    assert row["review_status"] == "closed"


def test_needs_review_gets_needs_review_status():
    item_id = _insert(decision="Needs-Human-Review", draft_text=None)
    row = db.get_item(item_id)
    assert row["review_status"] == "needs_review"


def test_list_items_orders_newest_first():
    first = _insert(subject="first")
    second = _insert(subject="second")
    rows = db.list_items()
    assert rows[0]["id"] == second
    assert rows[1]["id"] == first


def test_update_item():
    item_id = _insert()
    db.update_item(item_id, review_status="approved")
    assert db.get_item(item_id)["review_status"] == "approved"


def test_audit_log_appends_jsonl_lines():
    audit_log.log_pipeline_decision(
        item_id=1,
        source_path="x.eml",
        category="RFP",
        decision="Pursue",
        rationale="good fit",
        model_id="m",
        prompt_version="v1",
        draft_text="draft",
    )
    audit_log.log_human_review(item_id=1, action="approve", final_draft_text="draft")

    lines = config.AUDIT_LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    events = [json.loads(line) for line in lines]
    assert events[0]["event_type"] == "pipeline_decision"
    assert events[1]["event_type"] == "human_review"
