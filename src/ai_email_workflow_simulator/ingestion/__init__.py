"""Ingestion: turn a file on disk into an InboundItem."""

from pathlib import Path

from .eml_parser import parse_eml
from .models import InboundItem
from .text_loader import load_text_file

EML_EXTENSIONS = {".eml"}
TEXT_EXTENSIONS = {".txt"}
UNSUPPORTED_EXTENSIONS = {".pdf", ".docx"}


class UnsupportedFileTypeError(ValueError):
    """Raised when the input file's text cannot yet be extracted."""


def load_inbound_item(path: str | Path) -> InboundItem:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    if suffix in EML_EXTENSIONS:
        return parse_eml(path)
    if suffix in UNSUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"'{suffix}' attachments are not supported in this prototype yet. "
            "Extract the text to a .txt file first, or add an extractor in "
            "ingestion/text_loader.py (see the 'docs' optional dependency group)."
        )
    # Anything else -- .txt or an unrecognized extension -- is treated as a
    # generic text attachment.
    return load_text_file(path)


__all__ = ["InboundItem", "load_inbound_item", "UnsupportedFileTypeError"]
