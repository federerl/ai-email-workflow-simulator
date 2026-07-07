"""Parse .eml files using the Python standard library."""

import email
import email.policy
from html.parser import HTMLParser
from pathlib import Path

from .models import InboundItem


class _TextExtractor(HTMLParser):
    """Minimal HTML-to-text fallback for messages with only a text/html body."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def text(self) -> str:
        return "".join(self._chunks)


def _html_to_text(html: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(html)
    return extractor.text()


def parse_eml(path: Path) -> InboundItem:
    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=email.policy.default)

    body_part = msg.get_body(preferencelist=("plain", "html"))
    if body_part is None:
        body_text = ""
    else:
        content = body_part.get_content()
        body_text = (
            _html_to_text(content)
            if body_part.get_content_type() == "text/html"
            else content
        )

    for part in msg.iter_attachments():
        if part.get_content_type() == "text/plain":
            body_text += "\n\n--- attachment: " + (part.get_filename() or "unnamed") + " ---\n"
            body_text += part.get_content()

    recipients = [addr.addr_spec for addr in msg.get("to", "").addresses] if msg.get("to") else []

    return InboundItem(
        source_type="eml",
        source_path=str(path),
        subject=msg.get("subject", "(no subject)"),
        sender=msg.get("from", "(unknown sender)"),
        recipients=recipients,
        sent_at=msg.get("date", ""),
        body_text=body_text.strip(),
    )
