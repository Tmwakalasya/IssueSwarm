import asyncio
import hashlib
import hmac
import importlib
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def triage_module(monkeypatch):
    """Reload the triage module with a mocked Gemini model."""
    fake_model = MagicMock()
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        "google.generativeai.GenerativeModel",
        MagicMock(return_value=fake_model),
    )
    module = importlib.import_module("agents.triage")
    module = importlib.reload(module)
    monkeypatch.setattr(module.genai, "configure", MagicMock())
    return module, fake_model


def test_triage_issue_normalizes_label(triage_module):
    module, fake_model = triage_module
    fake_model.generate_content.return_value = MagicMock(text="Bug\n")

    label = module.triage_issue("It crashes when I click")

    assert label == "bug"
    fake_model.generate_content.assert_called_once()


def test_triage_issue_defaults_on_unknown_label(triage_module):
    module, fake_model = triage_module
    fake_model.generate_content.return_value = MagicMock(text="other")

    label = module.triage_issue("Feature request: add dark mode")

    assert label == "question"


def test_triage_issue_handles_exceptions(triage_module):
    module, fake_model = triage_module
    fake_model.generate_content.side_effect = RuntimeError("boom")

    label = module.triage_issue("Any update?")

    assert label == "question"


def test_orchestrate_issue_labels_and_triggers_fix(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    orchestrator = importlib.import_module("src.orchestrator")
    orchestrator = importlib.reload(orchestrator)

    mock_repo = MagicMock()
    mock_issue = MagicMock()

    monkeypatch.setattr(orchestrator, "triage_issue", MagicMock(return_value="bug"))
    mock_fix = AsyncMock()
    monkeypatch.setattr(orchestrator, "fix_bug", mock_fix)

    async def fake_call_in_thread(func, *args, **kwargs):
        if func is orchestrator._fetch_repo_and_issue:
            return mock_repo, mock_issue
        if func is mock_issue.add_to_labels:
            return func(*args, **kwargs)
        raise AssertionError(f"Unexpected call_in_thread target: {func}")

    monkeypatch.setattr(orchestrator, "_call_in_thread", fake_call_in_thread)

    payload = {
        "action": "opened",
        "issue": {"number": 42, "title": "Bug", "body": "Steps"},
        "repository": {"full_name": "octo/demo"},
    }

    asyncio.run(orchestrator.orchestrate_issue(payload))

    mock_issue.add_to_labels.assert_called_once_with("bug")
    mock_fix.assert_awaited_once_with(42, "octo/demo", mock_issue)


@pytest.fixture
def main_module(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "super-secret")
    module = importlib.import_module("src.main")
    module = importlib.reload(module)
    return module


def _signature(secret: str, payload: bytes) -> str:
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_webhook_rejects_invalid_signature(monkeypatch, main_module):
    client = TestClient(main_module.app)
    monkeypatch.setattr(main_module, "orchestrate_issue", AsyncMock())

    payload = json.dumps({"action": "opened", "issue": {}, "repository": {}}).encode()
    headers = {"X-Hub-Signature-256": _signature("wrong", payload)}

    response = client.post("/webhook", data=payload, headers=headers)

    assert response.status_code == 403


def test_webhook_accepts_valid_signature(monkeypatch, main_module):
    orchestrate_mock = AsyncMock()
    monkeypatch.setattr(main_module, "orchestrate_issue", orchestrate_mock)
    client = TestClient(main_module.app)

    payload_dict = {
        "action": "opened",
        "issue": {"number": 5, "title": "Bug", "body": "Boom"},
        "repository": {"full_name": "octo/demo"},
    }
    payload = json.dumps(payload_dict).encode()
    headers = {"X-Hub-Signature-256": _signature("super-secret", payload)}

    response = client.post("/webhook", data=payload, headers=headers)

    assert response.status_code == 200
    orchestrate_mock.assert_awaited_once_with(payload_dict)


@pytest.mark.anyio("asyncio")
async def test_fix_bug_offloads_blocking_calls(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    fix_module = importlib.import_module("agents.fix")
    fix_module = importlib.reload(fix_module)

    fake_model = MagicMock()
    fake_model.generate_content.return_value = MagicMock(text="print('ok')")
    monkeypatch.setattr(fix_module, "model", fake_model)
    monkeypatch.setattr(fix_module.genai, "configure", MagicMock())

    repo = MagicMock()
    issue = MagicMock()
    issue.body = "See src/app.py"

    async def fake_call_in_thread(func, *args, **kwargs):
        if func is fix_module._get_repo:
            return repo
        if func is fix_module._get_file_snippets:
            return {"src/app.py": "print('hello')"}
        if func is fake_model.generate_content:
            return func(*args, **kwargs)
        if func is issue.create_comment:
            return func(*args, **kwargs)
        raise AssertionError(f"Unexpected thread target: {func}")

    monkeypatch.setattr(fix_module, "_call_in_thread", fake_call_in_thread)

    await fix_module.fix_bug(7, "octo/demo", issue)

    fake_model.generate_content.assert_called_once()
    issue.create_comment.assert_called_once()
