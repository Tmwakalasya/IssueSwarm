import logging
import os
from github import Github
from agents.triage import triage_issue
from agents.fix import fix_bug


# Made the function async to handle async agent calls.
logger = logging.getLogger(__name__)


async def orchestrate_issue(payload: dict):
    g = Github(os.getenv("GITHUB_TOKEN"))

    issue_data = payload.get("issue", {})
    repo_full = payload.get("repository", {}).get("full_name")
    issue_num = issue_data.get("number")

    if not repo_full or not issue_num:
        logger.warning("Orchestrator: Missing repo/issue info.")
        return

    issue_text = f"{issue_data.get('title', '')}\n\n{issue_data.get('body', '')}"
    label = triage_issue(issue_text)

    try:
        repo = g.get_repo(repo_full)
        gh_issue = repo.get_issue(number=issue_num)

        if label:
            gh_issue.add_to_labels(label)
            logger.info("Orchestrator: Added label '%s' to issue #%s.", label, issue_num)

        if label == "bug":
            logger.info("Orchestrator: Label is 'bug', handing off to fix_bug agent.")
            # await the async fix_bug function.
            await fix_bug(issue_num, repo_full, gh_issue)

    except Exception as e:
        logger.exception("Orchestrator: An error occurred while processing issue #%s", issue_num)
