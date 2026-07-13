import json

from ai_email_workflow_simulator import eval as eval_module
from ai_email_workflow_simulator.llm import bedrock_client
from ai_email_workflow_simulator.pipeline import rubric as rubric_module


def _write_eml(path, subject, body):
    path.write_text(
        "From: a@b.example.com\n"
        "To: intake@bubodefense.example.com\n"
        f"Subject: {subject}\n"
        "Date: Mon, 11 May 2026 09:00:00 -0500\n"
        'Content-Type: text/plain; charset="utf-8"\n\n'
        f"{body}\n",
        encoding="utf-8",
    )


def _stub_converse(monkeypatch):
    """Route classify/decide to canned JSON based on which system prompt is used."""
    def fake(system_prompt, user_prompt, **kwargs):
        if "Classify the message" in system_prompt:
            return json.dumps({"category": "RFP", "notes": "solicitation"})
        return json.dumps({"decision": "Pursue", "rationale": "good fit"})

    monkeypatch.setattr(bedrock_client, "converse", fake)


def test_run_eval_scores_stages(tmp_path, monkeypatch):
    _stub_converse(monkeypatch)
    _write_eml(tmp_path / "a.eml", "RFP-1", "solicitation body")
    _write_eml(tmp_path / "b.eml", "Marketing", "buy our product")

    labels = [
        {"file": "a.eml", "category": "RFP", "decision": ["Pursue"]},
        # Classifier stub always says RFP, so this Marketing item is a miss;
        # its decision is auto-declined from the expected (Marketing) category.
        {"file": "b.eml", "category": "Marketing", "decision": ["Decline"]},
    ]
    rubric = rubric_module.load_rubric()
    results = eval_module.run_eval(labels, tmp_path, rubric)

    assert results[0].category_correct is True
    assert results[0].decision_correct is True  # stub decides Pursue, expected Pursue
    assert results[1].category_correct is False  # stub says RFP, expected Marketing
    assert results[1].predicted_decision == "Decline"  # auto-declined by config
    assert results[1].decision_correct is True


def test_acceptable_decision_set(tmp_path, monkeypatch):
    _stub_converse(monkeypatch)  # decision stub returns Pursue
    _write_eml(tmp_path / "c.eml", "RFP borderline", "maybe")

    labels = [{"file": "c.eml", "category": "RFP", "decision": ["Decline", "Pursue"]}]
    rubric = rubric_module.load_rubric()
    results = eval_module.run_eval(labels, tmp_path, rubric)

    # Pursue is in the acceptable set -> correct.
    assert results[0].decision_correct is True


def test_summarize_splits_rubric_and_auto(tmp_path, monkeypatch):
    _stub_converse(monkeypatch)
    _write_eml(tmp_path / "a.eml", "RFP-1", "solicitation")
    _write_eml(tmp_path / "m.eml", "Marketing", "sale")

    labels = [
        {"file": "a.eml", "category": "RFP", "decision": ["Pursue"]},
        {"file": "m.eml", "category": "Marketing", "decision": ["Decline"]},
    ]
    rubric = rubric_module.load_rubric()
    results = eval_module.run_eval(labels, tmp_path, rubric)
    summary = eval_module.summarize(results)

    assert summary["n_items"] == 2
    assert summary["decision_rubric_total"] == 1  # only the RFP
    assert summary["decision_auto_total"] == 1  # only the Marketing
    assert summary["classification_correct"] == 1  # RFP hit, Marketing miss
