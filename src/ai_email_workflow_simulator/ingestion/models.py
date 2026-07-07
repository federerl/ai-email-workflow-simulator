from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class InboundItem:
    """A single inbound item (email or generic text attachment) ready for the pipeline."""

    source_type: str  # "eml" | "text"
    source_path: str
    subject: str
    sender: str
    recipients: list[str]
    sent_at: str
    body_text: str
    ingested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
