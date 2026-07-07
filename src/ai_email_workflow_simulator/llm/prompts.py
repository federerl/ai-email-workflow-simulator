"""Prompt builders for each pipeline stage. Bump PROMPT_VERSION on any
change to prompt wording/schema so it can be tracked in the audit log."""

PROMPT_VERSION = "v1"

CATEGORIES = ["RFP", "Follow-up", "Marketing", "Internal", "Other"]

CLASSIFY_SYSTEM_PROMPT = f"""You triage inbound email for a defense-sector company.
Classify the message into exactly one of: {", ".join(CATEGORIES)}.

- RFP: a request for proposal, teaming inquiry, or solicitation the company
  could respond to.
- Follow-up: a follow-up on a prior proposal, opportunity, or conversation.
- Marketing: unsolicited vendor/sales marketing.
- Internal: internal company correspondence.
- Other: anything that doesn't fit the above.

Respond with ONLY a JSON object, no other text, matching this schema:
{{"category": "<one of the categories above>", "notes": "<one sentence why>"}}"""


def build_classify_prompt(item) -> str:
    return (
        f"Subject: {item.subject}\n"
        f"From: {item.sender}\n"
        f"Date: {item.sent_at}\n\n"
        f"Body:\n{item.body_text}"
    )


DECISION_SYSTEM_PROMPT = """You decide whether an inbound opportunity is worth
a reply, using the qualification rubric below. Weigh each criterion using
your best judgment based on the message content -- if the message doesn't
give enough information for a criterion, say so in your rationale.

{rubric_block}

Respond with ONLY a JSON object, no other text, matching this schema:
{{"decision": "Pursue" | "Decline" | "Needs-Human-Review", "rationale": "<2-4 sentence written rationale referencing the rubric criteria>"}}"""


def build_decision_system_prompt(rubric_block: str) -> str:
    return DECISION_SYSTEM_PROMPT.format(rubric_block=rubric_block)


def build_decision_prompt(item, category: str) -> str:
    return (
        f"Category: {category}\n"
        f"Subject: {item.subject}\n"
        f"From: {item.sender}\n"
        f"Date: {item.sent_at}\n\n"
        f"Body:\n{item.body_text}"
    )


DRAFTING_SYSTEM_PROMPT = """You draft a tailored initial response email for an
opportunity the company has decided to pursue. Use the company background
below to ground the response. Include a brief cover message, a short
capability summary, and direct answers to any explicit questions in the
original message where possible. This is a draft for human review before
sending -- do not invent commitments, dates, or figures not present in the
source message or company background.

Company background:
{boilerplate}

Respond with ONLY the plain-text body of the draft email, no subject line,
no other commentary."""


def build_drafting_system_prompt(boilerplate: str) -> str:
    return DRAFTING_SYSTEM_PROMPT.format(boilerplate=boilerplate)


def build_drafting_prompt(item, category: str, rationale: str) -> str:
    return (
        f"Original message category: {category}\n"
        f"Subject: {item.subject}\n"
        f"From: {item.sender}\n\n"
        f"Body:\n{item.body_text}\n\n"
        f"Reason this was marked worth pursuing: {rationale}"
    )
