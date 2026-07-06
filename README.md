# ai-email-workflow-simulator

Prototype for simulating an end-to-end AI email workflow: mock email ingestion, classification, pursue/decline decisioning, response drafting, and human review.

This is a local prototype of the classify → decide → draft → review pipeline
from the Bubo Defense AI Email Tool MVP, without the real mxHERO/AWS
ingestion or SES send steps. You feed it a `.eml` file or a plain-text
attachment directly instead of a live mailbox, and review decisions/drafts
through a small local web UI instead of a real inbox.

## Setup

1. Python 3.11+, and access to at least one Bedrock model (e.g. a Claude
   model) enabled in your AWS account/region.
2. Install:
   ```
   pip install -e .[dev]
   ```
3. Configure AWS credentials the normal way (`aws configure`, env vars, or
   an `AWS_PROFILE`) -- never commit credentials.
4. Copy `.env.example` to `.env` and set `AWS_REGION` / `BEDROCK_MODEL_ID`
   to a model enabled for your account.

### Try it without AWS access

No AWS account or Bedrock access yet? Set `MOCK_LLM=true` in `.env` (or
`export MOCK_LLM=true`) to bypass Bedrock entirely and use canned heuristic
responses instead, so you can exercise the full ingest → classify → decide →
draft → review flow immediately:

```
MOCK_LLM=true aiews-ingest data/samples/sample_rfp_email.eml
MOCK_LLM=true aiews-ingest data/samples/sample_marketing_email.eml
MOCK_LLM=true aiews-ingest data/samples/sample_followup_email.eml
MOCK_LLM=true aiews-review
```

Items processed this way are tagged `model_id: mock` in the queue/audit log
so mocked runs are never mistaken for real model output. Mock mode is a
smoke test for the plumbing, not a stand-in for real classification/
decisioning quality.

## Configuration

- `config/rubric.yaml` -- the "worth replying to?" rubric: which message
  categories go through rubric-based decisioning vs. get auto-decided, and
  the weighted criteria (mission fit, response window, contract vehicle,
  dollar value, incumbency) used in the decision prompt.
- `config/company_boilerplate.txt` -- a static capability/company blurb
  folded into drafted responses. (No retrieval/RAG in this prototype --
  see "Not in scope" below.)

## Usage

Ingest a sample file through the pipeline:

```
aiews-ingest data/samples/sample_rfp_email.eml
aiews-ingest data/samples/sample_marketing_email.eml
aiews-ingest data/samples/sample_followup_email.eml
aiews-ingest data/samples/sample_rfp_attachment.txt
```

Each run prints the classification, decision, and rationale, and appends a
record to `data/logs/audit.jsonl`.

Start the review UI:

```
aiews-review
```

Then open http://127.0.0.1:5000/queue to see the queue, open an item to see
its classification rationale and (for "Pursue" items) the drafted response,
and approve / edit-and-approve / reject drafts, or resolve
"Needs-Human-Review" items to Pursue or Decline.

## Tests

```
pytest
```

All Bedrock calls are mocked in the test suite -- no AWS credentials or
network access are needed to run `pytest`.

## Not in scope for this prototype

- Real email ingestion (mxHERO/SES) -- replaced by local file ingestion.
- RAG-grounded drafting against a knowledge base of past proposals --
  replaced by a static boilerplate blurb.
- PDF/DOCX attachment text extraction (an `extract_text` seam and a `docs`
  optional dependency group are reserved for this).
- Authentication on the review UI (local-only prototype).
- Weighted rubric-score recomputation/cross-check against the model's own
  stated decision.
