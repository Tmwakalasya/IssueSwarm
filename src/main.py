from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
import hmac
import hashlib
import json
import os
from src.orchestrator import orchestrate_issue

load_dotenv()

app = FastAPI()
GITHUB_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    # Signature validation, between github and our own
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=403, detail="Missing signature")

    payload = await request.body()
    expected_sig = "sha256=" + hmac.new(GITHUB_SECRET.encode(), payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = json.loads(payload)

    # Run the main logic as a background task to avoid timeouts.
    if data.get("action") == "opened" and "issue" in data:
        background_tasks.add_task(orchestrate_issue, data)

    return {"status": "ok"}

