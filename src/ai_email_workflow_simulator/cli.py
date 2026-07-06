"""`aiews-ingest <path>` -- run one file through the pipeline."""

import argparse
import sys

from .ingestion import UnsupportedFileTypeError
from .llm.bedrock_client import BedrockConfigError
from .pipeline.runner import run_pipeline
from .storage import db


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest an email or text attachment through the AI email workflow pipeline.")
    parser.add_argument("path", help="Path to a .eml file or a generic text attachment")
    args = parser.parse_args()

    try:
        item_id = run_pipeline(args.path)
    except (FileNotFoundError, UnsupportedFileTypeError, BedrockConfigError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)

    row = db.get_item(item_id)
    print(f"item #{item_id}: category={row['category']} decision={row['decision']}")
    print(f"rationale: {row['rationale']}")
    if row["draft_text"]:
        print("draft response generated -- run `aiews-review` to review it.")


if __name__ == "__main__":
    main()
