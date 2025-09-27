import asyncio
import logging
import os

from github import Github

from agents.triage import triage_issue
from agents.fix import fix_bug


logger = logging.getLogger(__name__)


async def _call_in_thread(func, *args, **kwargs):
    """Proxy around asyncio.to_thread to simplify testing."""
    return await asyncio.to_thread(func, *args, **kwargs)


def _fetch_repo_and_issue(token: str, repo_full: str, issue_num: int):
    github = Github(token)
    repo = github.get_repo(repo_full)
    issue = repo.get_issue(number=issue_num)
    return repo, issue


async def orchestrate_issue(payload: dict):
    issue_data = payload.get("issue", {})
    repo_full = payload.get("repository", {}).get("full_name")
    issue_num = issue_data.get("number")

    if not repo_full or not issue_num:
        logger.warning("Orchestrator: Missing repo/issue info.")
        return

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.error("GITHUB_TOKEN is not configured; cannot interact with GitHub.")
        return

    issue_text = f"{issue_data.get('title', '')}\n\n{issue_data.get('body', '')}"
    label = triage_issue(issue_text)

    try:
        _, gh_issue = await _call_in_thread(_fetch_repo_and_issue, token, repo_full, issue_num)

        if label:
            await _call_in_thread(gh_issue.add_to_labels, label)
            logger.info("Orchestrator: Added label '%s' to issue #%s.", label, issue_num)

        if label == "bug":
            logger.info("Orchestrator: Label is 'bug', handing off to fix_bug agent.")
            await fix_bug(issue_num, repo_full, gh_issue)

    except Exception:
        logger.exception(
            "Orchestrator: An error occurred while processing issue #%s", issue_num
        )
