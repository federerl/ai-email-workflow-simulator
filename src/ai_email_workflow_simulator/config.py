"""Environment and path configuration for the simulator."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"
LOGS_DIR = DATA_DIR / "logs"

RUBRIC_PATH = CONFIG_DIR / "rubric.yaml"
BOILERPLATE_PATH = CONFIG_DIR / "company_boilerplate.txt"

DB_PATH = LOGS_DIR / "state.db"
AUDIT_LOG_PATH = LOGS_DIR / "audit.jsonl"

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID")

# When set, bedrock_client.converse() returns canned heuristic responses
# instead of calling AWS -- lets the full pipeline/UI be exercised with no
# AWS credentials or Bedrock access. Never use this as a stand-in for real
# classification/decisioning quality.
MOCK_LLM = os.environ.get("MOCK_LLM", "").strip().lower() in ("1", "true", "yes", "on")


def ensure_dirs() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
