from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json
import os
from config.settings import *
from dotenv import load_dotenv
from src.orchestrator import orchestrate_issue
load_dotenv()
GITHUB_SECRET = os.environ.get("GITHUB_SECRET")

app = FastAPI()
GITHUB_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=403, detail="Missing signature")
    payload = await request.body()
    expected_sig = "sha256=" + hmac.new(GITHUB_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        raise HTTPException(status_code=403, detail="Invalid signature")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if data.get("action") != "opened" and 'issue' in data:
        orchestrate_issue(data)
    return {"status": "ok"}

