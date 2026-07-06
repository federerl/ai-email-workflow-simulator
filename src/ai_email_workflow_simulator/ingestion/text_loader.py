"""Load a generic text file as an inbound item.

`extract_text` is the seam for future non-plaintext attachment support
(PDF/DOCX) -- see the `docs` optional dependency group in pyproject.toml.
"""

from datetime import datetime, timezone
from pathlib import Path

from .models import InboundItem


def extract_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_text_file(path: Path) -> InboundItem:
    body_text = extract_text(path)
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()

    return InboundItem(
        source_type="text",
        source_path=str(path),
        subject=path.name,
        sender="local-file",
        recipients=[],
        sent_at=mtime,
        body_text=body_text.strip(),
    )
