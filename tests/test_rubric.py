from ai_email_workflow_simulator.pipeline import rubric


def test_load_rubric_has_expected_categories():
    r = rubric.load_rubric()
    assert set(r["categories"]) == {"RFP", "Follow-up", "Marketing", "Internal", "Other"}
    assert r["categories"]["RFP"]["applies_rubric"] is True
    assert r["categories"]["Marketing"]["applies_rubric"] is False


def test_category_applies_rubric():
    r = rubric.load_rubric()
    assert rubric.category_applies_rubric(r, "RFP") is True
    assert rubric.category_applies_rubric(r, "Marketing") is False


def test_category_auto_decision():
    r = rubric.load_rubric()
    assert rubric.category_auto_decision(r, "Marketing") == "Decline"
    assert rubric.category_auto_decision(r, "Other") == "Needs-Human-Review"


def test_build_rubric_block_includes_all_criteria():
    r = rubric.load_rubric()
    block = rubric.build_rubric_block(r)
    for criterion in r["criteria"]:
        assert criterion["label"] in block


def test_load_boilerplate_nonempty():
    assert len(rubric.load_boilerplate().strip()) > 0
