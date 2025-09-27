import asyncio
import hashlib
import hmac
import importlib
import json
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient


def _sign_payload(secret: str, payload: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_webhook_schedules_orchestrator(monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    secret = "test-secret"
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)

    # Reload the app module so it picks up the patched environment variable.
    main = importlib.import_module("src.main")
    importlib.reload(main)

    async def fake_orchestrate(payload):
        fake_orchestrate.called = True

    fake_orchestrate.called = False
    monkeypatch.setattr(main, "orchestrate_issue", fake_orchestrate)

    async def make_request():
        payload_dict = {
            "action": "opened",
            "issue": {"number": 123, "title": "Bug", "body": "Details"},
            "repository": {"full_name": "octo/repo"},
        }
        payload_bytes = json.dumps(payload_dict).encode()
        headers = {"X-Hub-Signature-256": _sign_payload(secret, payload_bytes)}

        transport = ASGITransport(app=main.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/webhook", content=payload_bytes, headers=headers)

        assert response.status_code == 200

    asyncio.run(make_request())
    assert fake_orchestrate.called
