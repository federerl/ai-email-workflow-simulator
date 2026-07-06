import pytest

from ai_email_workflow_simulator import config


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Point the SQLite state DB and JSONL audit log at a per-test tmp dir."""
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "state.db")
    monkeypatch.setattr(config, "AUDIT_LOG_PATH", tmp_path / "audit.jsonl")
    yield
