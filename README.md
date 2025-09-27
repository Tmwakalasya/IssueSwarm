# IssueSwarm: AI-Powered GitHub Issue Triage and Fix Bot

Automates issue labeling and bug fixes via Gemini AI and PyGithub.

## Setup
1. Copy .env.example to .env and fill in values. **GITHUB_WEBHOOK_SECRET is required** so the app can verify incoming webhook signatures.
2. pip install -r requirements.txt
3. uvicorn src.main:app --reload

## Demo Flow
- Create issue in GitHub repo.
- Webhook hits FastAPI.
- Orchestrator routes to agents.
- Triage labels; if bug, fix agent analyzes/posts comment.

## Reliability Check
Before demos or pushing changes, run the automated tests to verify the
mocked Gemini/PyGithub flows and webhook signature guardrails remain intact:

```bash
pytest
```