# IssueSwarm: AI-Powered GitHub Issue Triage and Fix Bot

IssueSwarm is a FastAPI-based webhook service that validates GitHub signatures, triages new issues with Gemini, and posts automated fix suggestions back to GitHub using PyGithub, giving teams instant, AI-assisted feedback when bugs are reported.

## Table of Contents
1. [Project Structure](#project-structure)
2. [Key Features](#key-features)
3. [Architecture Overview](#architecture-overview)
4. [Requirements](#requirements)
5. [Quick Start](#quick-start)
6. [Environment Configuration](#environment-configuration)
7. [Running the Webhook Service](#running-the-webhook-service)
8. [Configuring GitHub Webhooks](#configuring-github-webhooks)
9. [Agent Responsibilities](#agent-responsibilities)
10. [Background Processing & Concurrency](#background-processing--concurrency)
11. [Testing & Quality Assurance](#testing--quality-assurance)
12. [Operational Notes & Troubleshooting](#operational-notes--troubleshooting)

## Project Structure

| Path | Description |
| ---- | ----------- |
| `src/main.py` | FastAPI application exposing the `/webhook` endpoint and enforcing GitHub HMAC signature validation before queuing work for the orchestrator. |
| `src/orchestrator.py` | Central coordinator that reads webhook payloads, calls the triage agent, adds labels, and triggers fix generation for confirmed bugs. |
| `agents/triage.py` | Gemini-powered classifier that normalizes issue labels to `bug`, `feature`, or `question`, with defensive fallbacks for errors or unknown responses. |
| `agents/fix.py` | Gemini-based fix suggester that inspects issue text, fetches referenced files from GitHub, and posts an AI-generated patch preview as a comment. |
| `tests/test_triage.py` | End-to-end unit tests covering triage normalization, orchestrator flows, webhook signature enforcement, and fix agent threading behavior. |
| `requirements.txt` | Python dependencies including FastAPI, Uvicorn, PyGithub, Google Generative AI SDK, and supporting libraries. |
| `.env.example` | Template for required secrets and API keys used across the service and agents. |

## Key Features

- **Secure webhook ingestion** – Every GitHub callback must include a valid `X-Hub-Signature-256`; mismatches immediately return `403` responses to block spoofed requests.
- **Asynchronous orchestration** – Issue processing is deferred to a background task to keep webhook responses fast and resilient under load.
- **Automatic issue triage** – Gemini classifies issues into consistent labels and falls back to `question` on unexpected outputs or model failures.
- **AI-assisted fixes** – When an issue is labeled `bug`, the fix agent gathers referenced file snippets and posts a structured fix suggestion comment through GitHub’s API.
- **Robust unit tests** – The test suite mocks external services to confirm label assignment, webhook security, and thread offloading remain reliable without network calls.

## Architecture Overview

1. **GitHub issue opened** – GitHub sends the webhook payload configured with your shared secret.
2. **FastAPI webhook handler** – Validates the HMAC signature, parses the payload, and schedules asynchronous processing.
3. **Orchestrator** – Loads secrets, triangulates repository metadata, executes the triage agent, and applies labels through PyGithub.
4. **Fix agent (conditional)** – If the triaged label is `bug`, the agent composes a Gemini prompt, gathers file context, and comments with a code-block fix suggestion.
5. **Error handling** – Any failure results in logged exceptions and a human-handoff comment to ensure issues never stall silently.

## Requirements

Install the project dependencies into a Python environment (3.10+ recommended) using the packages listed in `requirements.txt`, which include FastAPI, Uvicorn, PyGithub, Google Generative AI, and supporting tools.

## Quick Start

1. **Clone the repository** and create a virtual environment.
2. **Copy the sample environment file** and fill in your credentials:

   ```bash
   cp .env.example .env
   ```

   Populate `GITHUB_TOKEN`, `GEMINI_API_KEY`, and `GITHUB_WEBHOOK_SECRET` with valid values before running the service.

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Start the FastAPI webhook service**:

   ```bash
   uvicorn src.main:app --reload
   ```

## Environment Configuration

- `GITHUB_TOKEN` – Personal access token or GitHub App installation token with `repo` scope, used for labeling issues and posting comments.
- `GEMINI_API_KEY` – Google Generative AI credential needed by both triage and fix agents before invoking Gemini models.
- `GITHUB_WEBHOOK_SECRET` – Shared secret for HMAC verification of inbound webhook payloads; missing values trigger explicit errors to prevent insecure operation.

Load these variables via `.env` (thanks to `python-dotenv`) or your preferred secrets manager.

## Running the Webhook Service

1. Ensure your `.env` file is populated.
2. Start Uvicorn with auto-reload for local development: `uvicorn src.main:app --reload`
3. Expose your local server (e.g., via ngrok) and set the public URL as the webhook endpoint in GitHub.

The `/webhook` route returns `{ "status": "ok" }` immediately after queuing work, so GitHub receives a response within the timeout window while processing continues asynchronously.

## Configuring GitHub Webhooks

1. Navigate to **Repository Settings → Webhooks** in GitHub.
2. Use your public URL plus `/webhook` as the payload URL.
3. Select `application/json` and subscribe to the **Issues** event.
4. Provide the same secret stored in `GITHUB_WEBHOOK_SECRET`; mismatches will produce `403 Forbidden` responses as enforced in `src/main.py`.
5. Create a test issue to verify that labels and AI comments appear automatically.

## Agent Responsibilities

### Triage Agent
- Configures Gemini with your API key.
- Prompts the model to return only `bug`, `feature`, or `question`.
- Normalizes casing and defaults to `question` for unknown outputs or exceptions to avoid propagating errors downstream.

### Fix Agent
- Activated only when triage returns `bug`.
- Extracts up to three referenced file paths from the issue body, fetches their content snippets via PyGithub, and constructs a Gemini prompt with context.
- Posts a formatted comment containing the suggested fix inside a Python code block, or a fallback message if generation fails.

## Background Processing & Concurrency

The webhook handler delegates heavy work to `asyncio.create_task`, keeping the HTTP response fast and preventing GitHub timeout retries.

All blocking GitHub and Gemini interactions execute through `asyncio.to_thread` helpers to avoid blocking the event loop, a behavior enforced in both orchestrator and fix-agent logic as well as the test suite.

## Testing & Quality Assurance

Run the full suite with:

```bash
pytest
```

The tests validate:
- Triage normalization and exception handling using mocked Gemini responses.
- Orchestrator’s ability to apply labels and trigger fix generation for bugs.
- Webhook signature enforcement for both valid and invalid signatures.
- Fix agent’s offloading of blocking calls and successful comment posting under mocked conditions.

## Operational Notes & Troubleshooting

- **Missing secrets** – If `GITHUB_WEBHOOK_SECRET` or `GITHUB_TOKEN` are unset, the service logs explicit errors and aborts processing to prevent insecure or unauthorized operations.
- **Gemini errors** – Triage defaults to `question` and fix-agent posts a fallback human-needed message when generation fails, ensuring users receive a clear signal that manual attention is required.
- **Logging** – Both orchestrator and fix agent emit structured log messages to aid debugging and monitoring of label assignments and comment posting.

---

## Testing
⚠️ `pytest` – Not run (read-only QA mode; execution disabled).
