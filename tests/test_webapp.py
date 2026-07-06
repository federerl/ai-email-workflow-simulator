from ai_email_workflow_simulator.pipeline import drafting
from ai_email_workflow_simulator.storage import db
from ai_email_workflow_simulator.webapp.app import create_app


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
        draft_text="Dear customer, ...",
        model_id="m",
        prompt_version="v1",
    )
    fields.update(overrides)
    return db.insert_item(**fields)


def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_queue_page_empty():
    resp = client().get("/queue")
    assert resp.status_code == 200
    assert b"No items yet" in resp.data


def test_queue_and_detail_show_item():
    item_id = _insert()
    c = client()
    resp = c.get("/queue")
    assert f"#{item_id}".encode() in resp.data

    resp = c.get(f"/items/{item_id}")
    assert resp.status_code == 200
    assert b"Dear customer" in resp.data


def test_detail_missing_item_404():
    resp = client().get("/items/999")
    assert resp.status_code == 404


def test_approve_pending_pursue_item():
    item_id = _insert()
    c = client()
    resp = c.post(f"/items/{item_id}/approve", follow_redirects=True)
    assert resp.status_code == 200
    assert db.get_item(item_id)["review_status"] == "approved"


def test_edit_approve_updates_final_text():
    item_id = _insert()
    c = client()
    c.post(
        f"/items/{item_id}/edit-approve",
        data={"final_draft_text": "Edited draft text"},
        follow_redirects=True,
    )
    row = db.get_item(item_id)
    assert row["review_status"] == "edited_approved"
    assert row["final_draft_text"] == "Edited draft text"
    assert row["edited"] == 1


def test_reject_pending_pursue_item():
    item_id = _insert()
    c = client()
    c.post(f"/items/{item_id}/reject", follow_redirects=True)
    assert db.get_item(item_id)["review_status"] == "rejected"


def test_cannot_approve_non_pending_item():
    item_id = _insert(decision="Decline", draft_text=None)
    resp = client().post(f"/items/{item_id}/approve")
    assert resp.status_code == 400


def test_resolve_needs_review_to_pursue_drafts_response(monkeypatch):
    monkeypatch.setattr(
        drafting,
        "draft_response",
        lambda *a, **k: drafting.DraftResult(draft_text="Freshly drafted response"),
    )
    item_id = _insert(decision="Needs-Human-Review", draft_text=None)
    c = client()
    c.post(f"/items/{item_id}/resolve", data={"resolution": "pursue"}, follow_redirects=True)
    row = db.get_item(item_id)
    assert row["decision"] == "Pursue"
    assert row["review_status"] == "pending_review"
    assert row["draft_text"] == "Freshly drafted response"


def test_resolve_needs_review_to_decline():
    item_id = _insert(decision="Needs-Human-Review", draft_text=None)
    c = client()
    c.post(f"/items/{item_id}/resolve", data={"resolution": "decline"}, follow_redirects=True)
    row = db.get_item(item_id)
    assert row["decision"] == "Decline"
    assert row["review_status"] == "closed"
