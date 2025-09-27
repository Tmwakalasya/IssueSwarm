from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
import hmac
import hashlib
import json
import logging
import os
from src.orchestrator import orchestrate_issue

load_dotenv()

app = FastAPI()
logger = logging.getLogger(__name__)

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    # Signature validation, between github and our own
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=403, detail="Missing signature")

    github_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not github_secret:
        logger.error(
            "GITHUB_WEBHOOK_SECRET is not set; unable to validate webhook signature."
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Server misconfiguration: GITHUB_WEBHOOK_SECRET is required to verify "
                "GitHub webhook signatures."
            ),
        )

    payload = await request.body()
    expected_sig = "sha256=" + hmac.new(
        github_secret.encode(), payload, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = json.loads(payload)

    # Run the main logic as a background task to avoid timeouts.
    if data.get("action") == "opened" and "issue" in data:
        background_tasks.add_task(orchestrate_issue, data)

    return {"status": "ok"}

