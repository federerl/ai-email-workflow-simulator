"""`aiews-eval` -- score the pipeline against a labeled eval set.

Runs classification and decisioning over a set of labeled emails and reports
accuracy, so prompt/model changes can be measured instead of eyeballed.

Two stages are scored independently:

* Classification -- the predicted category vs. the single correct category.
* Decision -- the predicted decision vs. an *acceptable set* of decisions.
  The decision stage is fed the **expected** category (not the predicted one),
  so a classification miss doesn't cascade into a decision miss; each stage is
  measured on its own. Decisions for auto-decided categories (Marketing,
  Internal, Other) come from config/rubric.yaml with no model call, so they
  test config; RFP/Follow-up are where model judgment shows.

Respects MOCK_LLM like the rest of the app -- run against the real model for a
meaningful baseline. This never writes to the state DB or audit log.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import config
from .ingestion import load_inbound_item
from .llm.bedrock_client import BedrockConfigError
from .pipeline import classify as classify_module
from .pipeline import decision as decision_module
from .pipeline import rubric as rubric_module

DEFAULT_LABELS = config.DATA_DIR / "eval" / "labels.yaml"
DEFAULT_BASELINE = config.DATA_DIR / "eval" / "baseline.json"

RUBRIC_JUDGED = {"RFP", "Follow-up"}


@dataclass
class ItemResult:
    file: str
    expected_category: str
    predicted_category: str
    category_correct: bool
    expected_decisions: list
    predicted_decision: str
    decision_correct: bool
    rubric_judged: bool


def load_labels(labels_path: Path) -> list[dict]:
    with open(labels_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["items"]


def _as_decision_set(value) -> list:
    """Normalize a label's `decision` (str or list) to a list of strings."""
    if isinstance(value, str):
        return [value]
    return list(value)


def run_eval(labels: list[dict], eval_dir: Path, rubric: dict) -> list[ItemResult]:
    results: list[ItemResult] = []
    for entry in labels:
        item = load_inbound_item(eval_dir / entry["file"])
        expected_category = entry["category"]
        acceptable = _as_decision_set(entry["decision"])

        classification = classify_module.classify(item)
        # Feed the EXPECTED category into the decision stage so it is measured
        # independently of classification errors.
        decision = decision_module.decide(item, expected_category, rubric)

        results.append(
            ItemResult(
                file=entry["file"],
                expected_category=expected_category,
                predicted_category=classification.category,
                category_correct=classification.category == expected_category,
                expected_decisions=acceptable,
                predicted_decision=decision.decision,
                decision_correct=decision.decision in acceptable,
                rubric_judged=expected_category in RUBRIC_JUDGED,
            )
        )
    return results


def summarize(results: list[ItemResult]) -> dict:
    n = len(results)
    cat_ok = sum(r.category_correct for r in results)
    dec_ok = sum(r.decision_correct for r in results)
    rubric = [r for r in results if r.rubric_judged]
    auto = [r for r in results if not r.rubric_judged]
    rubric_ok = sum(r.decision_correct for r in rubric)
    auto_ok = sum(r.decision_correct for r in auto)

    def pct(num, den):
        return round(num / den, 4) if den else None

    return {
        "n_items": n,
        "classification_correct": cat_ok,
        "classification_accuracy": pct(cat_ok, n),
        "decision_correct": dec_ok,
        "decision_accuracy": pct(dec_ok, n),
        "decision_rubric_total": len(rubric),
        "decision_rubric_correct": rubric_ok,
        "decision_rubric_accuracy": pct(rubric_ok, len(rubric)),
        "decision_auto_total": len(auto),
        "decision_auto_correct": auto_ok,
        "decision_auto_accuracy": pct(auto_ok, len(auto)),
    }


def format_report(results: list[ItemResult], summary: dict) -> str:
    mode = "MOCK" if config.MOCK_LLM else "LIVE"
    model = "mock" if config.MOCK_LLM else (config.BEDROCK_MODEL_ID or "(unset)")
    lines = [
        "AI Email Workflow -- Quality Eval",
        f"Model: {model}    Mode: {mode}",
        f"Items: {summary['n_items']}",
        "",
        f"{'file':<32}{'exp_cat':<11}{'pred_cat':<11}{'cat':<5}"
        f"{'exp_decision':<26}{'pred_decision':<22}{'dec'}",
        "-" * 118,
    ]
    for r in results:
        cat_mark = "OK" if r.category_correct else "XX"
        dec_mark = "OK" if r.decision_correct else "XX"
        exp_dec = "|".join(r.expected_decisions)
        lines.append(
            f"{r.file:<32}{r.expected_category:<11}{r.predicted_category:<11}{cat_mark:<5}"
            f"{exp_dec:<26}{r.predicted_decision:<22}{dec_mark}"
        )

    def line(label, num, den, acc):
        pct = f"{acc*100:.1f}%" if acc is not None else "n/a"
        return f"  {label:<34}{num}/{den}  ({pct})"

    lines += [
        "",
        line("Classification accuracy:", summary["classification_correct"],
             summary["n_items"], summary["classification_accuracy"]),
        line("Decision accuracy (overall):", summary["decision_correct"],
             summary["n_items"], summary["decision_accuracy"]),
        line("  rubric-judged (RFP/Follow-up):", summary["decision_rubric_correct"],
             summary["decision_rubric_total"], summary["decision_rubric_accuracy"])
        + "   <- model judgment",
        line("  auto-decided (config):", summary["decision_auto_correct"],
             summary["decision_auto_total"], summary["decision_auto_accuracy"]),
    ]

    disagreements = [r for r in results if not r.category_correct or not r.decision_correct]
    if disagreements:
        lines += ["", "Disagreements:"]
        for r in disagreements:
            parts = []
            if not r.category_correct:
                parts.append(f"category expected {r.expected_category} got {r.predicted_category}")
            if not r.decision_correct:
                parts.append(
                    f"decision expected {{{'|'.join(r.expected_decisions)}}} got {r.predicted_decision}"
                )
            lines.append(f"  - {r.file}: " + "; ".join(parts))
    else:
        lines += ["", "No disagreements."]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score the pipeline against a labeled eval set."
    )
    parser.add_argument(
        "--labels", type=Path, default=DEFAULT_LABELS,
        help=f"Path to labels YAML (default: {DEFAULT_LABELS})",
    )
    parser.add_argument(
        "--save-baseline", action="store_true",
        help=f"Write results to {DEFAULT_BASELINE} as the recorded baseline.",
    )
    parser.add_argument(
        "--baseline-path", type=Path, default=DEFAULT_BASELINE,
        help="Where to write the baseline JSON (with --save-baseline).",
    )
    args = parser.parse_args()

    labels_path = args.labels.resolve()
    eval_dir = labels_path.parent

    try:
        labels = load_labels(labels_path)
        rubric = rubric_module.load_rubric()
        results = run_eval(labels, eval_dir, rubric)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except BedrockConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)

    summary = summarize(results)
    print(format_report(results, summary))

    if args.save_baseline:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_id": "mock" if config.MOCK_LLM else config.BEDROCK_MODEL_ID,
            "mock": config.MOCK_LLM,
            "summary": summary,
            "items": [asdict(r) for r in results],
        }
        args.baseline_path.parent.mkdir(parents=True, exist_ok=True)
        args.baseline_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nBaseline written to {args.baseline_path}")


if __name__ == "__main__":
    main()
