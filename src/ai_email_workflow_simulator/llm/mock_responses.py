"""Canned heuristic responses standing in for real Bedrock calls when
MOCK_LLM is enabled, so the pipeline/UI can be exercised with no AWS access.
Keyword-matching only -- not a substitute for real classification/decisioning.
"""

import json


def mock_converse(system_prompt: str, user_prompt: str) -> str:
    # Matched on the literal JSON schema markers embedded in each system
    # prompt (see prompts.py) rather than prose, so line-wrapping edits to
    # the prompt copy don't silently break mock dispatch.
    if '"category":' in system_prompt:
        return _mock_classify(user_prompt)
    if '"decision":' in system_prompt:
        return _mock_decision(user_prompt)
    if "draft a tailored initial response email" in system_prompt:
        return _mock_draft(user_prompt)
    raise ValueError("mock_converse: could not identify prompt type")


def _mock_classify(user_prompt: str) -> str:
    text = user_prompt.lower()
    # Order matters: a status check-in can still mention "RFP" in passing
    # (e.g. "no formal RFP issued yet"), so check for follow-up/marketing
    # signals before the broader RFP keyword match.
    if any(k in text for k in ("checking in", "follow up", "following up", "any update", "status?", "haven't heard back")):
        category, notes = "Follow-up", "mock: message reads like a status check-in"
    elif any(k in text for k in ("% off", "discount", "free trial", "limited time", "sign up", "schedule a demo")):
        category, notes = "Marketing", "mock: message reads like vendor marketing"
    elif any(k in text for k in ("rfp", "solicitation", "statement of work", "contract vehicle", "teaming")):
        category, notes = "RFP", "mock: message contains RFP/solicitation language"
    else:
        category, notes = "Other", "mock: no strong category signal matched"
    return json.dumps({"category": category, "notes": notes})


def _mock_decision(user_prompt: str) -> str:
    category_line = next((l for l in user_prompt.splitlines() if l.startswith("Category:")), "")
    category = category_line.replace("Category:", "").strip()

    if category == "RFP":
        decision = "Pursue"
        rationale = (
            "mock: RFP includes rubric-relevant signals (deadline, contract "
            "vehicle, or incumbency mention) -- treated as a good fit."
        )
    else:
        decision = "Needs-Human-Review"
        rationale = "mock: not enough information in the message to confidently score the rubric criteria."
    return json.dumps({"decision": decision, "rationale": rationale})


def _mock_draft(user_prompt: str) -> str:
    subject_line = next((l for l in user_prompt.splitlines() if l.startswith("Subject:")), "Subject: your message")
    subject = subject_line.replace("Subject:", "").strip()
    return (
        f"Thank you for reaching out regarding \"{subject}\".\n\n"
        "[mock draft -- MOCK_LLM is enabled, no real model call was made]\n\n"
        "We've reviewed your message and are interested in discussing this "
        "further. We'll follow up shortly with a detailed response addressing "
        "your requirements.\n\n"
        "Best regards,\nBubo Defense"
    )
