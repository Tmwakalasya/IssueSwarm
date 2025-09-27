import asyncio
import logging
import os
import re
from typing import Dict, Iterable

from github import Github
import google.generativeai as genai


logger = logging.getLogger(__name__)
model = genai.GenerativeModel("gemini-2.5-pro")


def _get_repo(token: str, repo_full_name: str):
    github = Github(token)
    return github.get_repo(repo_full_name)


def _get_file_snippets(repo, file_paths: Iterable[str]) -> Dict[str, str]:
    contents: Dict[str, str] = {}
    for path in file_paths:
        try:
            raw = repo.get_contents(path)
            contents[path] = raw.decoded_content.decode()[:4000]
        except Exception:
            logger.debug("Unable to fetch contents for %s", path, exc_info=True)
    return contents


async def _call_in_thread(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


async def fix_bug(issue_number, repo_full_name, gh_issue):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.error("GITHUB_TOKEN is not configured; skipping fix attempt.")
        return

    issue_body = gh_issue.body or ""

    file_paths = re.findall(r"[\w/]+\.(py|js|ts|md)", issue_body)[:3]
    repo = await _call_in_thread(_get_repo, token, repo_full_name)
    file_contents = await _call_in_thread(_get_file_snippets, repo, file_paths)

    prompt = (
        f"Analyze bug: {gh_issue.title} {issue_body}. "
        f"Files: {file_contents}. Suggest fix code."
    )

    try:
        response = await _call_in_thread(model.generate_content, prompt)
        fix_suggestion = response.text
        comment = (
            f"🤖 AI Fix Suggestion for #{issue_number}:\n"
            f"```python\n{fix_suggestion}\n```"
        )
        await _call_in_thread(gh_issue.create_comment, comment)
        logger.info("Posted AI fix suggestion for issue #%s", issue_number)
    except Exception:
        logger.exception(
            "fix_bug: AI suggestion or comment failed for issue #%s", issue_number
        )
        await _call_in_thread(
            gh_issue.create_comment, "🤖 Fix attempt failed—human needed."
        )
