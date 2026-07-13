# Plan — next steps

Tracking doc for moving the prototype from "plumbing works" to "product works."

## Where we are (2026-07-07)

- [x] Package installed (`pip install -e .[dev]`), Python 3.13.
- [x] Test suite passing (35/35).
- [x] Full pipeline exercised in **mock mode** (ingest → classify → decide → draft → review → audit log).
- [x] Default model set to **Claude Opus 4.8 via Amazon Bedrock** (`us.anthropic.claude-opus-4-8-v1:0` in `.env` / `.env.example` / README).
- [x] `bedrock_client.converse()` only sends `temperature` when explicitly set (Opus 4.8 rejects non-default sampling params).

> ⚠️ Mock mode (`MOCK_LLM=true`) returns canned heuristics from `mock_responses.py` and never calls Bedrock. It validates wiring only — **not** classification/decisioning quality. Items are tagged `model_id: mock` in the audit log.

---

## 1. Prove it works for real  ✅ DONE (2026-07-10)

Turns "it runs" into "it works." Nothing below is meaningful until this is green.

- [x] Confirmed AWS credentials (IAM user `liul4`, account `457466245173`, region `us-east-1`).
- [x] Found the real Opus 4.8 inference-profile ID: **`us.anthropic.claude-opus-4-8`** (no `-v1:0` suffix — the bare foundation-model ID `anthropic.claude-opus-4-8` rejects on-demand invoke; the `us.` inference profile is required).
- [x] Model enabled/reachable — a live `converse` call succeeds.
- [x] Set `MOCK_LLM=false` and `BEDROCK_MODEL_ID=us.anthropic.claude-opus-4-8` in `.env`.
- [x] Ran all three samples live: RFP→Pursue (+draft), Marketing→Decline, Follow-up→Needs-Human-Review.
- [x] Audit records show `model_id=us.anthropic.claude-opus-4-8` (not `mock`).

**Done when:** a real Bedrock call classifies/decides/drafts end-to-end without errors, and the review UI shows the live results. ✅

> Note: the IAM user's policy grants `bedrock:InvokeModel` / `InvokeModelWithResponseStream` / `ListFoundationModels` / `ListInferenceProfiles` only — Bedrock-only blast radius. Cost guardrail: a $10 monthly AWS Budget alert.

## 2. Measure quality, don't eyeball it  ✅ DONE (2026-07-13)

No ground truth exists today, so we can't tell if a change helps or hurts.

- [x] Built a 15-email labeled eval set (`data/eval/*.eml` + `labels.yaml`) across all 5 categories, with edge cases and acceptable-decision-sets on borderline items.
- [x] Added `aiews-eval` (`src/.../eval.py`): scores classification + decision (stage-isolated) over the set, prints per-item + aggregate accuracy and a disagreement list. Covered by `tests/test_eval.py` (mock mode).
- [x] Recorded the Opus 4.8 baseline in `data/eval/baseline.json` (`--save-baseline`).

**Done when:** `aiews-eval` prints per-item and aggregate accuracy against expectations. ✅

> **Baseline (Opus 4.8, 2026-07-13):** classification 14/15 (93.3%); decision 15/15 — rubric-judged RFP/Follow-up 7/7, auto-decided 8/8.
> Only miss: `followup_borderline.eml` classified RFP instead of Follow-up (a `RE:` about a *future* solicitation — genuinely on the RFP/Follow-up line; revisit the classify prompt or the label). Re-run `aiews-eval` after any prompt/model change to compare against this.

## 3. Harden model I/O for a reasoning model

`classify.py` / `decision.py` parse the model's **text** output inside `try/except`. Opus 4.8 may add preamble or format JSON differently than Claude 3.5 did — a silent parsing-break risk.

- [ ] Review `prompts.py` for prompts that assumed 3.5-style output.
- [ ] Decide: stricter prompting vs. Bedrock `converse` tool-use for guaranteed JSON schema.
- [ ] Add tests covering malformed/preamble-wrapped model output.

**Done when:** parsing is robust to Opus 4.8 output shape and covered by tests.

## 4. Close an in-scope guardrail: rubric cross-check

From the README "Not in scope" list — cheap and high-value. `config/rubric.yaml` already holds the weighted criteria.

- [ ] Compute the weighted rubric score independently of the model's stated decision.
- [ ] Flag Pursue/Decline items where the score and the model disagree (surface in the review UI / audit log).

**Done when:** disagreements between the computed score and the model's decision are visibly flagged for the human reviewer.

---

## Parking lot (later / out of current scope)

- Real email ingestion (mxHERO / SES) — replaced by local file ingestion.
- RAG-grounded drafting against past proposals — currently a static boilerplate blurb.
- PDF/DOCX attachment text extraction (`extract_text` seam + `docs` optional dep reserved).
- Auth on the review UI (local-only prototype).

## Notes

- Bedrock, not the first-party Anthropic API: different endpoint, AWS-cred auth, `us.anthropic.`-prefixed model IDs.
- Items 2 and 3 can be done offline in mock mode while AWS access is sorted.
