import pytest

from ai_email_workflow_simulator.ingestion import (
    UnsupportedFileTypeError,
    load_inbound_item,
)

SAMPLES = "data/samples"


def test_parse_eml_plain_text():
    item = load_inbound_item(f"{SAMPLES}/sample_rfp_email.eml")
    assert item.source_type == "eml"
    assert "RFP-2026-0417" in item.subject
    assert "Maria Chen" in item.sender
    assert "OASIS+" in item.body_text


def test_load_text_file():
    item = load_inbound_item(f"{SAMPLES}/sample_rfp_attachment.txt")
    assert item.source_type == "text"
    assert item.sender == "local-file"
    assert "STATEMENT OF WORK" in item.body_text


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_inbound_item(f"{SAMPLES}/does_not_exist.eml")


def test_unsupported_extension_raises(tmp_path):
    fake_pdf = tmp_path / "attachment.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake")
    with pytest.raises(UnsupportedFileTypeError):
        load_inbound_item(fake_pdf)
